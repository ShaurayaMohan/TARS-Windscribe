"""
Weekly Sentiment Report for TARS.

Pulls the last 7 days of sentiment-scored tickets from MongoDB,
aggregates the data, and posts a formatted summary to Slack.
"""
import logging
from datetime import datetime
from typing import Dict, List

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

logger = logging.getLogger(__name__)


def _pct(count: int, total: int) -> str:
    return f"{count / total:.0%}" if total else "0%"


def _bar(count: int, total: int, width: int = 10) -> str:
    pct = count / total if total else 0
    filled = round(pct * width)
    return "█" * filled + "░" * (width - filled)


def _build_breakdown(
    buckets: Dict[str, int], total: int, order: List[str]
) -> str:
    """Build a compact breakdown with inline code bars."""
    lines = []
    for key in order:
        count = buckets.get(key, 0)
        if count == 0:
            continue
        bar = _bar(count, total)
        label = "Neutral / Confused" if key == "neutral_confused" else key.capitalize()
        lines.append(f"`{bar}` *{label}* — {count}  ({_pct(count, total)})")
    return "\n".join(lines)


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

    blocks = _build_report(total, sentiment, urgency, churn, high_churn_tickets, days)

    client = WebClient(token=slack_bot_token)
    today = datetime.utcnow().strftime("%B %d, %Y")
    try:
        client.chat_postMessage(
            channel=slack_channel_id,
            text=f"TARS Weekly Sentiment Report — {today}",
            blocks=blocks,
            unfurl_links=False,
            unfurl_media=False,
        )
        logger.info("Weekly sentiment report posted to Slack")
        return True
    except SlackApiError as e:
        logger.error(f"Failed to post weekly sentiment report: {e.response['error']}")
        return False


def _build_report(
    total: int,
    sentiment: Dict[str, int],
    urgency: Dict[str, int],
    churn: Dict[str, int],
    high_churn_tickets: list,
    days: int,
) -> list:
    """Build Slack blocks for the report."""
    today = datetime.utcnow().strftime("%B %d, %Y")

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"TARS Weekly Sentiment Report — {today}"},
        },
        {
            "type": "section",
            "text": {"type": "mrkdwn", "text": f"*{total}* tickets scored over the past *{days}* days."},
        },
        {"type": "divider"},
    ]

    # ── Sentiment ─────────────────────────────────────────────────────────
    sentiment_order = sorted(sentiment.keys(), key=lambda k: sentiment.get(k, 0), reverse=True)
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": "*Sentiment*\n" + _build_breakdown(sentiment, total, sentiment_order),
        },
    })

    # ── Urgency ───────────────────────────────────────────────────────────
    urgency_order = ["critical", "high", "medium", "low"]
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": "*Urgency*\n" + _build_breakdown(urgency, total, urgency_order),
        },
    })

    # ── Churn risk ────────────────────────────────────────────────────────
    churn_order = ["high", "medium", "low"]
    blocks.append({
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": "*Churn Risk*\n" + _build_breakdown(churn, total, churn_order),
        },
    })

    # ── High churn spotlight ──────────────────────────────────────────────
    if high_churn_tickets:
        blocks.append({"type": "divider"})
        blocks.append({
            "type": "section",
            "text": {"type": "mrkdwn", "text": "*High Churn Risk Tickets*"},
        })
        for t in high_churn_tickets[:10]:
            num = t.get("ticket_number", "?")
            subj = t.get("subject", "")[:60]
            summary = t.get("sentiment_summary", "")
            sent = t.get("sentiment", "")
            urg = t.get("urgency", "")

            blocks.append({
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": (
                        f"*#{num}* — {subj}\n"
                        f"_{summary}_\n"
                        f"`{sent}` · `{urg}`"
                    ),
                },
            })

    return blocks
