"""
Weekly Sentiment Report for TARS.

Pulls the last 7 days of sentiment-scored tickets from MongoDB,
aggregates the data, and posts a formatted summary to Slack.
"""
import logging
from datetime import datetime
from typing import Dict, Optional

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

logger = logging.getLogger(__name__)

# ── Color palette for sentiment blocks ────────────────────────────────────────
SENTIMENT_COLORS = {
    "positive": "#059669",
    "neutral": "#6B7280",
    "frustrated": "#D97706",
    "angry": "#DC2626",
}
CHURN_COLOR = "#DC2626"
URGENCY_COLOR = "#2563EB"


def _bar(label: str, count: int, total: int, max_width: int = 12) -> str:
    """Tiny text bar chart: ████░░░░ 42%"""
    pct = count / total if total else 0
    filled = round(pct * max_width)
    empty = max_width - filled
    return f"{label:<12} {'█' * filled}{'░' * empty}  {count}  ({pct:.0%})"


def post_weekly_sentiment_report(
    mongodb_storage,
    slack_bot_token: str,
    slack_channel_id: str,
    days: int = 7,
) -> bool:
    """Build and post the weekly sentiment report. Returns True on success."""

    stats = mongodb_storage.get_sentiment_stats(days=days)
    if not stats or not stats.get("total_scored"):
        logger.info("No sentiment data for the last %d days — skipping weekly report", days)
        return False

    total = stats["total_scored"]
    sentiment = stats.get("sentiment", {})
    urgency = stats.get("urgency", {})
    churn = stats.get("churn_risk", {})
    high_churn_tickets = stats.get("high_churn_tickets", [])

    today = datetime.utcnow().strftime("%B %d, %Y")

    blocks = [
        {
            "type": "header",
            "text": {
                "type": "plain_text",
                "text": f"TARS Weekly Sentiment Report — {today}",
            },
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*{total}* tickets scored over the past *{days}* days.",
            },
        },
        {"type": "divider"},
    ]

    # Sentiment breakdown
    sentiment_lines = [
        _bar(k.capitalize(), v, total)
        for k, v in sorted(sentiment.items(), key=lambda x: -x[1])
    ]
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": "*Sentiment Breakdown*\n```\n" + "\n".join(sentiment_lines) + "\n```",
        },
    })

    # Urgency breakdown
    urgency_order = ["critical", "high", "medium", "low"]
    urgency_lines = [
        _bar(u.capitalize(), urgency.get(u, 0), total)
        for u in urgency_order
        if urgency.get(u, 0) > 0
    ]
    if urgency_lines:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Urgency Breakdown*\n```\n" + "\n".join(urgency_lines) + "\n```",
            },
        })

    # Churn risk
    churn_order = ["high", "medium", "low"]
    churn_lines = [
        _bar(c.capitalize(), churn.get(c, 0), total)
        for c in churn_order
        if churn.get(c, 0) > 0
    ]
    if churn_lines:
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*Churn Risk*\n```\n" + "\n".join(churn_lines) + "\n```",
            },
        })

    # High churn tickets spotlight
    if high_churn_tickets:
        blocks.append({"type": "divider"})
        ticket_lines = []
        for t in high_churn_tickets[:10]:
            num = t.get("ticket_number", "?")
            subj = t.get("subject", "")[:60]
            summary = t.get("sentiment_summary", "")
            sent = t.get("sentiment", "")
            urg = t.get("urgency", "")
            ticket_lines.append(
                f"• *#{num}* — {subj}\n"
                f"   _{summary}_  |  {sent} · {urg}"
            )
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "*High Churn Risk Tickets*\n" + "\n".join(ticket_lines),
            },
        })

    # Post to Slack
    client = WebClient(token=slack_bot_token)
    try:
        client.chat_postMessage(
            channel=slack_channel_id,
            text=f"TARS Weekly Sentiment Report — {today}",
            blocks=blocks,
        )
        logger.info("Weekly sentiment report posted to Slack")
        return True
    except SlackApiError as e:
        logger.error(f"Failed to post weekly sentiment report: {e.response['error']}")
        return False
