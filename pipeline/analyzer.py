"""
Main analysis pipeline orchestrator
Coordinates the full TARS workflow: fetch → analyze → format → post
"""
import logging
import requests
from typing import Dict, Optional
from datetime import datetime

from pipeline.supportpal_client import SupportPalClient
from pipeline.ai_analyzer import AIAnalyzer
from utils.slack_formatter import SlackFormatter

logger = logging.getLogger(__name__)


class TARSPipeline:
    """Main pipeline orchestrator for TARS analysis"""
    
    def __init__(
        self,
        supportpal_api_key: str,
        supportpal_api_url: str,
        openai_api_key: str,
        slack_webhook_url: str
    ):
        """
        Initialize TARS pipeline
        
        Args:
            supportpal_api_key: SupportPal API token
            supportpal_api_url: SupportPal API base URL
            openai_api_key: OpenAI API key
            slack_webhook_url: Slack webhook URL for posting
        """
        self.supportpal_client = SupportPalClient(supportpal_api_url, supportpal_api_key)
        self.ai_analyzer = AIAnalyzer(openai_api_key)
        
        # Extract base URL for ticket links
        base_url = supportpal_api_url.replace('/api', '')
        self.slack_formatter = SlackFormatter(base_url)
        
        self.slack_webhook_url = slack_webhook_url
        
    def run_analysis(self, hours: int = 24) -> bool:
        """
        Run the complete TARS analysis pipeline
        
        Args:
            hours: Number of hours to look back for tickets (default: 24)
            
        Returns:
            True if successful, False otherwise
        """
        try:
            logger.info(f"Starting TARS analysis pipeline (last {hours} hours)")
            
            # Step 1: Fetch tickets
            logger.info("Step 1/4: Fetching tickets from SupportPal...")
            tickets = self.supportpal_client.get_tickets_for_analysis(hours=hours)
            
            if not tickets:
                logger.warning(f"No tickets found in the last {hours} hours")
                self._post_no_tickets_message(hours)
                return True  # Not an error, just no tickets
            
            logger.info(f"Fetched {len(tickets)} tickets for analysis")
            
            # Step 2: AI Analysis
            logger.info("Step 2/4: Analyzing tickets with AI...")
            analysis = self.ai_analyzer.analyze_tickets(tickets)
            
            if not analysis:
                logger.error("AI analysis failed")
                self._post_error_message("AI analysis failed")
                return False
            
            num_clusters = len(analysis.get('clusters', []))
            logger.info(f"Analysis complete: {num_clusters} clusters identified")
            
            # Step 3: Format for Slack
            logger.info("Step 3/4: Formatting message for Slack...")
            slack_message = self.slack_formatter.format_analysis(analysis)
            
            # Step 4: Post to Slack
            logger.info("Step 4/4: Posting to Slack...")
            success = self._post_to_slack(slack_message)
            
            if success:
                logger.info("✅ TARS analysis pipeline completed successfully")
                return True
            else:
                logger.error("Failed to post to Slack")
                return False
                
        except Exception as e:
            logger.error(f"Pipeline error: {e}", exc_info=True)
            self._post_error_message(f"Pipeline error: {str(e)}")
            return False
    
    def _post_to_slack(self, message: Dict) -> bool:
        """
        Post message to Slack webhook
        
        Args:
            message: Formatted Slack message payload
            
        Returns:
            True if successful, False otherwise
        """
        try:
            response = requests.post(
                self.slack_webhook_url,
                json=message,
                headers={'Content-Type': 'application/json'},
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info("Successfully posted to Slack")
                return True
            else:
                logger.error(f"Slack API error: {response.status_code} - {response.text}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to post to Slack: {e}")
            return False
    
    def _post_no_tickets_message(self, hours: int):
        """Post a message to Slack when no tickets are found"""
        message = {
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"ℹ️ *TARS Daily Report*\n\nNo new tickets found in the last {hours} hours.\n\n_The system is working normally - just no new support requests!_"
                    }
                }
            ]
        }
        self._post_to_slack(message)
    
    def _post_error_message(self, error_text: str):
        """Post an error message to Slack"""
        message = {
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"❌ *TARS Error*\n\n{error_text}\n\n_Please check the logs for more details._"
                    }
                }
            ]
        }
        self._post_to_slack(message)
