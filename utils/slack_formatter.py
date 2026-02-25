"""
Slack formatter for TARS analysis reports.

Design:
- Main message: header block + colored attachments per category + new trends
- Thread reply: per-category ticket breakdown with matching colors
- Colors assigned per category for visual grouping

Uses slack_sdk.WebClient (chat.postMessage) for threading support.
"""
import logging
from datetime import datetime
from typing import Dict, List, Optional

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

logger = logging.getLogger(__name__)

# ── Color palette ──────────────────────────────────────────────────────────────
# 5 rotating colors for top known categories + 1 for new trends
TOP5_COLORS = [
    "#2563EB",  # blue
    "#059669",  # green
    "#D97706",  # amber
    "#7C3AED",  # violet
    "#0891B2",  # cyan
]
NEW_TREND_COLOR = "#DC2626"  # red — stands out for new/emerging trends

# Max tickets shown per category in thread
_THREAD_MAX_PER_CATEGORY = 25


class SlackFormatter:
    """Formats and posts TARS analysis results to Slack."""

    def __init__(
        self,
        supportpal_base_url: str,
        slack_bot_token: str,
        slack_channel_id: str,
    ):
        self.base_url = supportpal_base_url.rstrip("/")
        self.channel = slack_channel_id
        self.client = WebClient(token=slack_bot_token)

    # ── Public posting interface ───────────────────────────────────────────────

    def post_analysis(self, analysis: Dict) -> bool:
        """
        Post the main summary, then threaded ticket breakdowns.
        Returns True if the main message posted successfully.
        """
        number_to_id: Dict[int, int] = analysis.get("_number_to_id", {})
        number_to_subject: Dict[int, str] = analysis.get("_number_to_subject", {})

        blocks, attachments = self._build_main_message(analysis)

        try:
            resp = self.client.chat_postMessage(
                channel=self.channel,
                blocks=blocks,
                attachments=attachments,
                text=f"TARS Support Summary — {analysis.get('analysis_date', 'today')}",
                unfurl_links=False,
                unfurl_media=False,
            )
            thread_ts = resp["ts"]
            logger.info(f"Main Slack message posted (ts={thread_ts})")
        except SlackApiError as e:
            logger.error(f"Slack API error posting main message: {e.response['error']}")
            return False

        # Post threaded breakdown (non-fatal)
        try:
            self._post_thread_breakdown(
                thread_ts=thread_ts,
                analysis=analysis,
                number_to_id=number_to_id,
                number_to_subject=number_to_subject,
            )
        except Exception as e:
            logger.warning(f"Failed to post thread breakdown: {e}")

        return True

    def post_no_tickets_message(self, hours: int) -> None:
        try:
            self.client.chat_postMessage(
                channel=self.channel,
                text=f"TARS: No new tickets found in the last {hours} hours.",
            )
        except SlackApiError as e:
            logger.error(f"Slack error: {e.response['error']}")

    def post_error_message(self, error_text: str) -> None:
        try:
            self.client.chat_postMessage(
                channel=self.channel,
                text=f"TARS Error: {error_text}",
            )
        except SlackApiError as e:
            logger.error(f"Slack error: {e.response['error']}")

    # ── Main message ───────────────────────────────────────────────────────────

    def _build_main_message(self, analysis: Dict):
        """
        Build top-level blocks + colored attachments for the main message.
        Returns (blocks, attachments).
        """
        total = analysis.get("total_tickets_analyzed", 0)
        date = analysis.get("analysis_date", datetime.now().strftime("%Y-%m-%d"))

        # Top-level blocks: just the header
        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": f"TARS Support Summary — {date}",
                    "emoji": False,
                },
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"{total} tickets analyzed",
                },
            },
        ]

        attachments = []

        # ── Top 5 known categories as colored attachments ──────────────────────
        known = sorted(
            [c for c in analysis.get("known_categories", []) if c.get("volume", 0) > 0],
            key=lambda c: c.get("volume", 0),
            reverse=True,
        )
        top5 = known[:5]
        remaining = known[5:]
        remaining_count = sum(c.get("volume", 0) for c in remaining)

        # Summary attachment: "Today's Top Categories"
        if top5:
            for i, cat in enumerate(top5):
                summary = cat.get("summary") or ""
                # Take first sentence for brevity
                if summary and "." in summary:
                    summary_short = summary.split(".")[0].strip() + "."
                else:
                    summary_short = summary.strip()

                color = TOP5_COLORS[i]
                cat["_color"] = color

                text = f"*{cat['title']}* — {cat['volume']} tickets"
                if summary_short:
                    text += f"\n_{summary_short}_"

                attachments.append({
                    "color": color,
                    "blocks": [
                        {
                            "type": "section",
                            "text": {"type": "mrkdwn", "text": text},
                        },
                    ],
                })

            if remaining_count > 0:
                attachments.append({
                    "color": "#CCCCCC",
                    "blocks": [
                        {
                            "type": "section",
                            "text": {
                                "type": "mrkdwn",
                                "text": f"_{len(remaining)} more categories ({remaining_count} tickets) — see thread for full breakdown_",
                            },
                        },
                    ],
                })

        # ── New / Emerging Trends ──────────────────────────────────────────────
        trends = analysis.get("new_trends", [])
        number_to_id: Dict[int, int] = analysis.get("_number_to_id", {})
        ticket_details: Dict[str, str] = analysis.get("ticket_details", {})

        if trends:
            trend_attachments = self._build_trend_attachments(
                trends, number_to_id, ticket_details
            )
            attachments.extend(trend_attachments)
        else:
            attachments.append({
                "color": "#22C55E",  # green = all good
                "blocks": [
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": "*New / Emerging Trends*\nNo unusual trends detected today.",
                        },
                    },
                ],
            })

        # Footer
        attachments.append({
            "color": "#E2E8F0",
            "blocks": [
                {
                    "type": "context",
                    "elements": [{
                        "type": "mrkdwn",
                        "text": "Full per-category ticket breakdown posted in thread below.",
                    }],
                },
            ],
        })

        return blocks, attachments

    def _build_trend_attachments(
        self,
        trends: List[Dict],
        number_to_id: Dict[int, int],
        ticket_details: Dict[str, str],
    ) -> List[Dict]:
        """Build red-colored attachments for new trends — always fully expanded."""
        attachments = []
        trend_count = sum(t.get("volume", 0) for t in trends)

        for i, trend in enumerate(trends, 1):
            title = trend.get("title", "Unknown Trend")
            volume = trend.get("volume", 0)
            description = trend.get("description", "")
            geo = trend.get("geographic_pattern")
            ticket_numbers = trend.get("ticket_numbers", [])

            geo_suffix = f" | {geo}" if geo else ""
            header = f"*New Trend: {title}* — {volume} tickets{geo_suffix}\n{description}"

            # Individual ticket lines
            ticket_lines = []
            for num in ticket_numbers[:10]:
                ticket_id = number_to_id.get(int(num))
                detail = ticket_details.get(str(num), "")
                if ticket_id:
                    url = f"{self.base_url}/en/admin/ticket/view/{ticket_id}"
                    line = f"<{url}|#{num}>"
                    if detail:
                        line += f": {detail}"
                    ticket_lines.append(f"• {line}")
                else:
                    ticket_lines.append(f"• #{num}: {detail}" if detail else f"• #{num}")

            if len(ticket_numbers) > 10:
                ticket_lines.append(f"_+{len(ticket_numbers) - 10} more — see thread_")

            full_text = header
            if ticket_lines:
                full_text += "\n" + "\n".join(ticket_lines)

            # Truncate if needed
            if len(full_text) > 2900:
                full_text = full_text[:2880] + "\n..."

            attachments.append({
                "color": NEW_TREND_COLOR,
                "blocks": [
                    {
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": full_text},
                    },
                ],
            })

        return attachments

    # ── Thread breakdown ───────────────────────────────────────────────────────

    def _post_thread_breakdown(
        self,
        thread_ts: str,
        analysis: Dict,
        number_to_id: Dict[int, int],
        number_to_subject: Dict[int, str],
    ) -> None:
        """
        Post one threaded reply per active known category with color-coded
        attachments matching the main message.
        """
        ticket_details: Dict[str, str] = analysis.get("ticket_details", {})
        known = sorted(
            [c for c in analysis.get("known_categories", []) if c.get("volume", 0) > 0],
            key=lambda c: c.get("volume", 0),
            reverse=True,
        )

        for cat in known:
            # Use the color assigned in the main message, or gray for non-top-5
            color = cat.get("_color", "#94A3B8")
            attachments = self._build_category_thread_attachments(
                cat, color, number_to_id, number_to_subject, ticket_details
            )
            if not attachments:
                continue

            try:
                self.client.chat_postMessage(
                    channel=self.channel,
                    thread_ts=thread_ts,
                    attachments=attachments,
                    text=f"{cat['title']} — {cat['volume']} tickets",
                    unfurl_links=False,
                    unfurl_media=False,
                )
            except SlackApiError as e:
                logger.warning(
                    f"Failed to post thread for {cat['title']}: {e.response['error']}"
                )

        logger.info(f"Thread breakdown posted ({len(known)} categories)")

    def _build_category_thread_attachments(
        self,
        cat: Dict,
        color: str,
        number_to_id: Dict[int, int],
        number_to_subject: Dict[int, str],
        ticket_details: Dict[str, str],
    ) -> List[Dict]:
        """Build color-coded attachments for a single category's thread reply."""
        ticket_numbers = cat.get("ticket_numbers", [])
        summary = cat.get("summary") or ""

        # Header: category title + summary
        header_text = f"*{cat['title']}* — {cat['volume']} tickets"
        if summary:
            header_text += f"\n_{summary}_"

        # Build a compact text block: one line per ticket
        # Format: • #NUMBER: Subject — Description  [link]
        display_numbers = ticket_numbers[:_THREAD_MAX_PER_CATEGORY]
        remainder = len(ticket_numbers) - len(display_numbers)

        ticket_lines = []
        for num in display_numbers:
            ticket_id = number_to_id.get(int(num))
            subject = number_to_subject.get(int(num), "No Subject")
            detail = ticket_details.get(str(num), "")

            if ticket_id:
                url = f"{self.base_url}/en/admin/ticket/view/{ticket_id}"
                line = f"• <{url}|*#{num}*>: {subject}"
            else:
                line = f"• *#{num}*: {subject}"

            if detail and detail.lower() != subject.lower():
                line += f"\n   _{detail}_"

            ticket_lines.append(line)

        if remainder > 0:
            ticket_lines.append(f"\n_+{remainder} more tickets in this category_")

        # Join into chunks of text that fit within Slack's 3000-char limit per block
        full_text = header_text + "\n\n" + "\n".join(ticket_lines)

        # Split into multiple text chunks if needed
        text_chunks = []
        current_chunk = ""
        for line in [header_text, ""] + ticket_lines:
            test = current_chunk + "\n" + line if current_chunk else line
            if len(test) > 2800:
                text_chunks.append(current_chunk)
                current_chunk = line
            else:
                current_chunk = test
        if current_chunk:
            text_chunks.append(current_chunk)

        # Each chunk becomes one attachment with the same color
        attachments = []
        for chunk_text in text_chunks:
            attachments.append({
                "color": color,
                "blocks": [
                    {
                        "type": "section",
                        "text": {"type": "mrkdwn", "text": chunk_text},
                    },
                ],
            })

        return attachments
