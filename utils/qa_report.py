"""
Weekly QA Report for TARS.

Pulls the last 7 days of QA-scored tickets from MongoDB, aggregates
clusters by platform + feature_area, and posts flagged clusters to Slack.
"""
import logging
from datetime import datetime
from typing import Dict

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

logger = logging.getLogger(__name__)

FEATURE_AREA_LABELS = {
    "connection_engine": "Core Connection Engine",
    "protocol_wireguard": "WireGuard",
    "protocol_ikev2": "IKEv2",
    "protocol_openvpn": "OpenVPN (UDP/TCP)",
    "protocol_stealth": "Stealth / WStunnel",
    "protocol_amnezia": "AmneziaWG",
    "app_crash": "App Crash / Won't Launch",
    "app_ui": "UI / UX Bugs",
    "localization": "Localization / Translation",
    "look_and_feel": "Look & Feel",
    "dns_robert": "DNS / R.O.B.E.R.T.",
    "split_tunneling": "Split Tunneling",
    "allow_lan_traffic": "Allow LAN Traffic",
    "authentication": "Authentication / Login",
    "billing_app_bugs": "Billing App Bugs",
    "static_ip_app_issues": "Static IP App Issues",
    "config_generation": "Config Generation / Upload",
    "other": "Other",
}

PLATFORM_LABELS = {
    "windows": "Windows",
    "macos": "macOS",
    "linux": "Linux",
    "android": "Android",
    "ios": "iOS",
    "router": "Router",
    "browser_extension": "Browser Extension",
    "tv": "TV",
    "unknown": "Unknown",
}


def post_qa_report(
    mongodb_storage,
    slack_bot_token: str,
    slack_channel_id: str,
    days: int = 7,
    min_count: int = 3,
) -> bool:
    """Build and post the weekly QA cluster report. Returns True on success."""

    data = mongodb_storage.get_qa_clusters(days=days, min_count=min_count)
    clusters = data.get("clusters", [])
    total_bugs = data.get("total_bugs", 0)

    if not clusters:
        logger.info("No QA clusters above threshold for the last %d days — skipping report", days)
        return False

    blocks = _build_report(clusters, total_bugs, days, min_count)

    client = WebClient(token=slack_bot_token)
    today = datetime.utcnow().strftime("%B %d, %Y")
    try:
        client.chat_postMessage(
            channel=slack_channel_id,
            text=f"TARS Weekly QA Report — {today}",
            blocks=blocks,
            unfurl_links=False,
            unfurl_media=False,
        )
        logger.info("Weekly QA report posted to Slack")
        return True
    except SlackApiError as e:
        logger.error(f"Failed to post weekly QA report: {e.response['error']}")
        return False


def _build_report(
    clusters: list,
    total_bugs: int,
    days: int,
    min_count: int,
) -> list:
    """Build Slack blocks for the QA report."""
    today = datetime.utcnow().strftime("%B %d, %Y")

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"TARS Weekly QA Report — {today}"},
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"*{total_bugs}* bug tickets identified over the past *{days}* days.\n"
                    f"*{len(clusters)}* cluster(s) with {min_count}+ tickets flagged below."
                ),
            },
        },
        {"type": "divider"},
    ]

    for c in clusters:
        platform = PLATFORM_LABELS.get(c["platform"], c["platform"])
        feature = FEATURE_AREA_LABELS.get(c["feature_area"], c["feature_area"])
        count = c["count"]
        tickets = c.get("tickets", [])

        ticket_lines = []
        for t in tickets[:10]:
            num = t.get("ticket_number", "?")
            subj = t.get("subject", "")[:55]
            pattern = t.get("error_pattern", "")
            ticket_lines.append(f"  • *#{num}* — {subj}")
            if pattern and pattern != "N/A":
                ticket_lines.append(f"    _{pattern}_")

        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"`{platform}` · *{feature}* — *{count} tickets*\n"
                    + "\n".join(ticket_lines)
                ),
            },
        })

    return blocks
