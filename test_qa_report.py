"""Post a sample QA report to Slack for visual preview."""
import os
from dotenv import load_dotenv
from slack_sdk import WebClient
from utils.qa_report import _build_report

load_dotenv()

base_url = os.getenv("SUPPORTPAL_API_URL", "").replace("/api", "")

sample_clusters = [
    {
        "platform": "android",
        "feature_area": "protocol_wireguard",
        "count": 5,
        "tickets": [
            {"ticket_number": 98412, "supportpal_id": 44012, "subject": "WireGuard keeps disconnecting on Android 14", "error_pattern": "WireGuard handshake timeout after 30s on Android 14 Samsung S24"},
            {"ticket_number": 98387, "supportpal_id": 43987, "subject": "Can't connect with WireGuard - Pixel 8", "error_pattern": "WireGuard tunnel setup fails with EPERM on Android 14"},
            {"ticket_number": 98201, "supportpal_id": 43801, "subject": "VPN drops every 5 minutes on WireGuard", "error_pattern": "Recurring WireGuard keepalive failure on Android 14"},
            {"ticket_number": 98150, "supportpal_id": 43750, "subject": "WireGuard protocol not working since update", "error_pattern": "WireGuard interface creation fails post app update v3.8.1"},
            {"ticket_number": 98033, "supportpal_id": 43633, "subject": "Android WireGuard broken after OS update", "error_pattern": "WireGuard permission denied after Android 14 QPR2 update"},
        ],
    },
    {
        "platform": "windows",
        "feature_area": "split_tunneling",
        "count": 4,
        "tickets": [
            {"ticket_number": 98455, "supportpal_id": 44055, "subject": "Split tunnel not excluding Chrome", "error_pattern": "Exclusive mode still routes Chrome traffic through VPN"},
            {"ticket_number": 98302, "supportpal_id": 43902, "subject": "Split tunneling stopped working after update", "error_pattern": "Split tunnel driver fails to load on Windows 11 23H2"},
            {"ticket_number": 98188, "supportpal_id": 43788, "subject": "Apps in split tunnel list still go through VPN", "error_pattern": "Inclusive mode not routing specified apps outside tunnel"},
            {"ticket_number": 98099, "supportpal_id": 43699, "subject": "Split tunnel breaks when switching networks", "error_pattern": "Split tunnel rules lost on network adapter change"},
        ],
    },
    {
        "platform": "ios",
        "feature_area": "app_crash",
        "count": 3,
        "tickets": [
            {"ticket_number": 98401, "supportpal_id": 44001, "subject": "App crashes on launch iOS 17.3", "error_pattern": "Crash on launch — NSInternalInconsistencyException on iOS 17.3"},
            {"ticket_number": 98350, "supportpal_id": 43950, "subject": "Windscribe keeps force closing", "error_pattern": "Repeated crash when opening server list on iPhone 15 Pro"},
            {"ticket_number": 98210, "supportpal_id": 43810, "subject": "Cannot open app after latest update", "error_pattern": "App crashes immediately after splash screen on iOS 17.3.1"},
        ],
    },
    {
        "platform": "macos",
        "feature_area": "localization",
        "count": 1,
        "tickets": [
            {"ticket_number": 98477, "supportpal_id": 44077, "subject": "New anti-censorship menu not translated to Spanish", "error_pattern": "Anti-censorship settings screen shows English text in Spanish UI"},
        ],
    },
]

total_bugs = 42
blocks, attachments = _build_report(sample_clusters, total_bugs, days=7, base_url=base_url)

# Add a note that this is a test
blocks.insert(1, {
    "type": "context",
    "elements": [{"type": "mrkdwn", "text": ":test_tube: *This is a sample report with fake data for visual preview*"}],
})

client = WebClient(token=os.getenv("SLACK_BOT_TOKEN"))
client.chat_postMessage(
    channel=os.getenv("SLACK_CHANNEL_ID"),
    text="TARS Weekly QA Report — Sample Preview",
    blocks=blocks,
    attachments=attachments,
    unfurl_links=False,
    unfurl_media=False,
)
print("Sample QA report posted to Slack!")
