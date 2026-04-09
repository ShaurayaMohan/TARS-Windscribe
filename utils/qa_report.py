"""
QA Report for TARS.

Pulls QA-scored tickets from MongoDB, aggregates clusters by
platform, and posts flagged clusters to Slack with one colored
attachment per platform and feature area shown inline per ticket.
"""
import logging
from datetime import datetime
from typing import Dict

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

logger = logging.getLogger(__name__)

PLATFORM_COLORS = {
    "windows": "#0078D4",
    "macos": "#A2AAAD",
    "linux": "#E95420",
    "android": "#3DDC84",
    "ios": "#147EFB",
    "router": "#FF6F00",
    "browser_extension": "#4285F4",
    "tv": "#7C3AED",
    "unknown": "#6B7280",
}

FEATURE_AREA_LABELS = {
    "connection_engine": "Connection Engine",
    "protocol_wireguard": "WireGuard",
    "protocol_ikev2": "IKEv2",
    "protocol_openvpn": "OpenVPN",
    "protocol_stealth": "Stealth",
    "protocol_amnezia": "AmneziaWG",
    "app_crash": "App Crash",
    "app_ui": "UI/UX",
    "localization": "Localization",
    "look_and_feel": "Look & Feel",
    "dns_robert": "DNS/ROBERT",
    "split_tunneling": "Split Tunneling",
    "allow_lan_traffic": "LAN Traffic",
    "authentication": "Auth",
    "billing_app_bugs": "Billing",
    "static_ip_app_issues": "Static IP",
    "config_generation": "Config Gen",
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
    "unknown": "Unknown Platform",
}


def post_qa_report(
    mongodb_storage,
    slack_bot_token: str,
    slack_channel_id: str,
    supportpal_base_url: str = "",
    days: int = 7,
    min_count: int = 1,
) -> bool:
    """Build and post the QA cluster report. Returns True on success."""

    data = mongodb_storage.get_qa_clusters(days=days, min_count=min_count)
    clusters = data.get("clusters", [])
    total_bugs = data.get("total_bugs", 0)

    if not clusters:
        logger.info("No QA bugs for the last %d day(s) — skipping report", days)
        return False

    blocks, attachments = _build_report(
        clusters, total_bugs, days, supportpal_base_url
    )

    client = WebClient(token=slack_bot_token)
    today = datetime.utcnow().strftime("%B %d, %Y")
    try:
        client.chat_postMessage(
            channel=slack_channel_id,
            text=f"TARS QA Report — {today}",
            blocks=blocks,
            attachments=attachments,
            unfurl_links=False,
            unfurl_media=False,
        )
        logger.info("QA report posted to Slack")
        return True
    except SlackApiError as e:
        logger.error(f"Failed to post QA report: {e.response['error']}")
        return False


def _build_report(
    clusters: list,
    total_bugs: int,
    days: int,
    base_url: str,
) -> tuple:
    """Build Slack blocks + one colored attachment per platform."""
    today = datetime.utcnow().strftime("%B %d, %Y")

    blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"TARS QA Report — {today}"},
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"*{total_bugs}* bug ticket(s) flagged over the past *{days}* day(s), "
                    f"across *{len(clusters)}* platform(s)."
                ),
            },
        },
    ]

    attachments = []

    for c in clusters:
        platform_key = c["platform"]
        platform = PLATFORM_LABELS.get(platform_key, platform_key)
        count = c["count"]
        tickets = c.get("tickets", [])
        color = PLATFORM_COLORS.get(platform_key, "#6B7280")

        ticket_lines = []
        for t in tickets[:15]:
            num = t.get("ticket_number", "?")
            sp_id = t.get("supportpal_id")
            subj = t.get("subject", "")[:55]
            fa = t.get("feature_area", "other")
            fa_label = FEATURE_AREA_LABELS.get(fa, fa)
            pattern = t.get("error_pattern", "")

            if base_url and sp_id:
                url = f"{base_url}/en/admin/ticket/view/{sp_id}"
                ticket_lines.append(f"  `{fa_label}` <{url}|#{num}> — {subj}")
            else:
                ticket_lines.append(f"  `{fa_label}` *#{num}* — {subj}")

            if pattern and pattern != "N/A":
                ticket_lines.append(f"    _{pattern}_")

        attachments.append({
            "color": color,
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": (
                            f"*{platform}* — *{count} ticket(s)*\n"
                            + "\n".join(ticket_lines)
                        ),
                    },
                },
            ],
        })

    return blocks, attachments
