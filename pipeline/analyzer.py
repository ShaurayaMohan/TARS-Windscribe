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
import logging
from typing import Dict, Optional

from pipeline.supportpal_client import SupportPalClient
from pipeline.ai_analyzer import AIAnalyzer
from utils.slack_formatter import SlackFormatter

logger = logging.getLogger(__name__)


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
    ):
        self.supportpal_client = SupportPalClient(supportpal_api_url, supportpal_api_key)
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
            tickets = self.supportpal_client.get_tickets_for_analysis(hours=hours)

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
