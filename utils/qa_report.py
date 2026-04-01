"""
QA Report for TARS.

Pulls QA-scored tickets from MongoDB, aggregates clusters by
platform + feature_area, and posts flagged clusters to Slack
with colored attachments and hyperlinked ticket numbers.
"""
import logging
from datetime import datetime
from typing import Dict

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

logger = logging.getLogger(__name__)

CLUSTER_COLORS = [
    "#2563EB",  # blue
    "#059669",  # green
    "#D97706",  # amber
    "#7C3AED",  # violet
    "#0891B2",  # cyan
]

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
    """Build Slack blocks + colored attachments for the QA report."""
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
                    f"*{total_bugs}* bug ticket(s) identified over the past *{days}* day(s).\n"
                    f"*{len(clusters)}* cluster(s) flagged below."
                ),
            },
        },
    ]

    attachments = []

    for i, c in enumerate(clusters):
        platform = PLATFORM_LABELS.get(c["platform"], c["platform"])
        feature = FEATURE_AREA_LABELS.get(c["feature_area"], c["feature_area"])
        count = c["count"]
        tickets = c.get("tickets", [])
        color = CLUSTER_COLORS[i % len(CLUSTER_COLORS)]

        ticket_lines = []
        for t in tickets[:10]:
            num = t.get("ticket_number", "?")
            sp_id = t.get("supportpal_id")
            subj = t.get("subject", "")[:55]
            pattern = t.get("error_pattern", "")

            if base_url and sp_id:
                url = f"{base_url}/en/admin/ticket/view/{sp_id}"
                ticket_lines.append(f"  • <{url}|#{num}> — {subj}")
            else:
                ticket_lines.append(f"  • *#{num}* — {subj}")

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
                            f"`{platform}` · *{feature}* — *{count} ticket(s)*\n"
                            + "\n".join(ticket_lines)
                        ),
                    },
                },
            ],
        })

    return blocks, attachments
