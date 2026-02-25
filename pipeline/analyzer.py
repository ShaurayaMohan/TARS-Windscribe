"""
Main analysis pipeline orchestrator.
Coordinates the full TARS workflow: fetch → analyze → store → post to Slack.

Step order (intentional):
  1. Fetch tickets from SupportPal
  2. Analyze with AI (two-phase)
  3. Save to MongoDB   ← BEFORE Slack so a Slack failure never loses data
  4. Post main Slack message
  5. Post threaded ticket breakdown to Slack
"""
import re
import logging
from html import unescape
from typing import Dict, Optional

from pipeline.supportpal_client import SupportPalClient
from pipeline.ai_analyzer import AIAnalyzer
from utils.slack_formatter import SlackFormatter

logger = logging.getLogger(__name__)

_TAG_RE = re.compile(r"<[^>]+>")
# Matches CSS/VML behavior blocks like: v\: {behavior:url(#default#VML);}
# and any {...} block that contains "behavior" or is all CSS selectors
_CSS_BEHAVIOR_RE = re.compile(r"[\w\\*.:]+\s*\{[^}]*\}", re.DOTALL)
# Matches leftover Microsoft Office / VML artifacts that survive tag removal
_VML_ARTIFACT_RE = re.compile(
    r"\b(?:behavior|url\(#default#\w+\)|mso-\w[\w-]*|panose-\d|font-face"
    r"|@font-face|@page|WordSection|MsoNormal|MsoBodyText)\b[^;}\n]*[;}\n]?",
    re.IGNORECASE,
)


def _strip_html(text: str) -> str:
    """
    Remove HTML tags, CSS/VML artifacts, decode entities, collapse whitespace.

    Handles:
    - Standard HTML tags: <div>, <br>, <pre> etc.
    - CSS behavior blocks: v\\: {behavior:url(#default#VML);}
    - Microsoft Office / VML leftovers from rich-text emails
    - HTML entities: &quot; &#039; &amp; etc.
    """
    text = _TAG_RE.sub(" ", text)           # <tags> → space
    text = _CSS_BEHAVIOR_RE.sub(" ", text)  # CSS {...} blocks → space
    text = _VML_ARTIFACT_RE.sub(" ", text)  # VML/MSO artifacts → space
    text = unescape(text)                   # &quot; &#039; etc → real chars
    text = re.sub(r"\s+", " ", text)        # collapse whitespace
    return text.strip()


class TARSPipeline:
    """Main pipeline orchestrator for TARS analysis."""

    def __init__(
        self,
        supportpal_api_key: str,
        supportpal_api_url: str,
        openai_api_key: str,
        slack_bot_token: str,
        slack_channel_id: str,
        mongodb_storage=None,
        # Legacy webhook kept for fallback / error messages only
        slack_webhook_url: Optional[str] = None,
        # Optional brand_id to restrict to Windscribe tickets only
        supportpal_brand_id: Optional[int] = None,
    ):
        self.supportpal_client = SupportPalClient(supportpal_api_url, supportpal_api_key)
        self.supportpal_brand_id = supportpal_brand_id
        self.ai_analyzer = AIAnalyzer(openai_api_key)

        # Extract base URL for SupportPal ticket links
        base_url = supportpal_api_url.replace("/api", "")
        self.slack_formatter = SlackFormatter(
            supportpal_base_url=base_url,
            slack_bot_token=slack_bot_token,
            slack_channel_id=slack_channel_id,
        )

        self.slack_bot_token = slack_bot_token
        self.slack_channel_id = slack_channel_id
        self.slack_webhook_url = slack_webhook_url
        self.mongodb_storage = mongodb_storage

    # ── Public API ─────────────────────────────────────────────────────────────

    def run_analysis(self, hours: int = 24) -> bool:
        """
        Run the complete TARS analysis pipeline.

        Args:
            hours: How far back to look for tickets (default 24).

        Returns:
            True on full success, False if any critical step failed.
        """
        try:
            logger.info(f"Starting TARS analysis pipeline (last {hours} hours)")

            # ── Step 1: Fetch tickets ──────────────────────────────────────────
            logger.info("Step 1/5: Fetching tickets from SupportPal...")
            tickets = self.supportpal_client.get_tickets_for_analysis(
                hours=hours, brand_id=self.supportpal_brand_id
            )

            if not tickets:
                logger.warning(f"No tickets found in the last {hours} hours")
                self.slack_formatter.post_no_tickets_message(hours)
                return True  # Not an error

            logger.info(f"Fetched {len(tickets)} tickets for analysis")

            # Build number→id lookup so the Slack formatter can generate correct URLs.
            # The AI only sees ticket numbers; we never expose internal IDs to the model.
            number_to_id: Dict[int, int] = {
                int(t["number"]): int(t["id"]) for t in tickets
            }
            # Also keep number→subject for the thread breakdown
            number_to_subject: Dict[int, str] = {
                int(t["number"]): t.get("subject", "No Subject") for t in tickets
            }

            # Strip HTML + VML/CSS from first_message before AI sees it or it
            # ends up in fallback snippets.
            for t in tickets:
                raw = t.get("first_message", "")
                t["first_message"] = _strip_html(raw)

            # Build fallback ticket_details from pipeline data.
            # These are used ONLY if the AI does not provide a summary for a ticket.
            fallback_details: Dict[str, str] = {}
            for t in tickets:
                num = str(t["number"])
                subject = t.get("subject", "")
                msg = t.get("first_message", "")
                snippet = msg[:120].strip()
                if snippet and snippet.lower() != subject.lower():
                    fallback_details[num] = snippet
                else:
                    fallback_details[num] = subject

            # ── Step 2: AI Analysis ────────────────────────────────────────────
            logger.info("Step 2/5: Analyzing tickets with AI...")
            custom_template = None
            if self.mongodb_storage:
                try:
                    custom_template = self.mongodb_storage.get_prompt_template()
                except Exception as e:
                    logger.warning(f"Could not load prompt template from MongoDB: {e}")

            analysis = self.ai_analyzer.analyze_tickets(
                tickets, template=custom_template
            )

            if not analysis:
                logger.error("AI analysis failed")
                self.slack_formatter.post_error_message("AI analysis failed — check logs.")
                return False

            # Attach mapping so the formatter can build links without re-fetching
            analysis["_number_to_id"] = number_to_id
            analysis["_number_to_subject"] = number_to_subject

            # Merge ticket_details: prefer AI-generated one-liners, fall back to
            # the cleaned message snippet for any ticket the AI missed.
            ai_summaries: Dict[str, str] = analysis.pop("ticket_summaries", {})
            ticket_details: Dict[str, str] = {}
            for t in tickets:
                num = str(t["number"])
                ai_summary = ai_summaries.get(num, "").strip()
                if ai_summary:
                    ticket_details[num] = ai_summary
                else:
                    ticket_details[num] = fallback_details.get(num, t.get("subject", ""))

            analysis["ticket_details"] = ticket_details
            logger.info(
                f"ticket_details: {len(ai_summaries)} AI summaries, "
                f"{len(ticket_details) - len(ai_summaries)} fallbacks"
            )

            num_known_active = len(
                [c for c in analysis.get("known_categories", []) if c.get("volume", 0) > 0]
            )
            num_trends = len(analysis.get("new_trends", []))
            logger.info(
                f"Analysis complete: {num_known_active} active known categories, "
                f"{num_trends} new trends"
            )

            # ── Step 3: Save to MongoDB (BEFORE Slack) ─────────────────────────
            if self.mongodb_storage:
                try:
                    logger.info("Step 3/5: Saving analysis to MongoDB...")
                    # Strip internal mappings (int keys) that MongoDB can't store,
                    # and stringify any remaining int keys in ticket_details.
                    save_copy = {
                        k: v for k, v in analysis.items()
                        if not k.startswith("_")
                    }
                    # Ensure ticket_details keys are strings (AI sometimes uses ints)
                    if "ticket_details" in save_copy:
                        save_copy["ticket_details"] = {
                            str(k): v
                            for k, v in save_copy["ticket_details"].items()
                        }
                    self.mongodb_storage.save_analysis(save_copy)
                    logger.info("Analysis saved to database")
                except Exception as e:
                    logger.error(f"Failed to save to MongoDB: {e}")
                    # Non-fatal — continue to Slack

            # ── Step 4 + 5: Post to Slack ──────────────────────────────────────
            logger.info("Step 4/5: Posting to Slack...")
            success = self.slack_formatter.post_analysis(analysis)

            if not success:
                logger.error("Failed to post to Slack")
                return False

            logger.info("TARS analysis pipeline completed successfully")
            return True

        except Exception as e:
            logger.error(f"Pipeline error: {e}", exc_info=True)
            try:
                self.slack_formatter.post_error_message(f"Pipeline error: {str(e)}")
            except Exception:
                pass
            return False
