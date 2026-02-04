"""
Slack slash command handler for TARS
Handles /tars commands with signature verification
"""
import hmac
import hashlib
import time
import re
from typing import Dict, Tuple, Optional
import logging

logger = logging.getLogger(__name__)


class SlackCommandHandler:
    """Handles Slack slash command parsing and responses"""
    
    def __init__(self, signing_secret: str, static_url: str):
        """
        Initialize command handler
        
        Args:
            signing_secret: Slack app signing secret for verification
            static_url: Base URL for static assets (e.g., https://tars.onrender.com)
        """
        self.signing_secret = signing_secret
        self.static_url = static_url.rstrip('/')
        
    def verify_signature(self, timestamp: str, signature: str, body: str) -> bool:
        """
        Verify Slack request signature
        
        Args:
            timestamp: X-Slack-Request-Timestamp header
            signature: X-Slack-Signature header  
            body: Raw request body
            
        Returns:
            True if signature is valid, False otherwise
        """
        # Check timestamp is recent (within 5 minutes)
        current_time = int(time.time())
        if abs(current_time - int(timestamp)) > 60 * 5:
            logger.warning("Request timestamp too old")
            return False
        
        # Compute expected signature
        sig_basestring = f"v0:{timestamp}:{body}"
        my_signature = 'v0=' + hmac.new(
            self.signing_secret.encode(),
            sig_basestring.encode(),
            hashlib.sha256
        ).hexdigest()
        
        # Compare signatures
        return hmac.compare_digest(my_signature, signature)
    
    def parse_command(self, text: str) -> Tuple[str, Optional[int]]:
        """
        Parse /tars command text
        
        Args:
            text: Command text (e.g., "analyze", "analyze 7d", "help")
            
        Returns:
            Tuple of (command, hours) where command is the action and hours is the time range
        """
        text = text.strip().lower()
        
        # Empty or just "analyze"
        if not text or text == "analyze":
            return ("analyze", 24)
        
        # Help command
        if text == "help":
            return ("help", None)
        
        # Analyze with time specification
        if text.startswith("analyze"):
            parts = text.split()
            if len(parts) == 1:
                return ("analyze", 24)
            
            time_spec = parts[1]
            
            # Days format (e.g., "7d", "30d")
            if time_spec.endswith('d'):
                try:
                    days = int(time_spec[:-1])
                    if days <= 0:
                        return ("error", None)
                    if days > 90:  # Max 90 days
                        return ("error", None)
                    return ("analyze", days * 24)
                except ValueError:
                    return ("error", None)
            
            # Hours format (e.g., "6", "12", "48")
            try:
                hours = int(time_spec)
                if hours <= 0:
                    return ("error", None)
                if hours > 2160:  # Max 90 days in hours
                    return ("error", None)
                return ("analyze", hours)
            except ValueError:
                return ("error", None)
        
        # Unknown command
        return ("unknown", None)
    
    def format_help_response(self) -> Dict:
        """
        Format help command response with GIF
        
        Returns:
            Slack message payload
        """
        gif_url = f"{self.static_url}/static/tars.gif"
        
        return {
            "response_type": "in_channel",  # Public message
            "blocks": [
                {
                    "type": "image",
                    "image_url": gif_url,
                    "alt_text": "TARS"
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "🦇 *TARS - Your Robin to the Support Team's Batman*\n\nI'm here to help you spot critical issues before they become problems!"
                    }
                },
                {
                    "type": "divider"
                },
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": "*📚 Commands:*\n\n"
                                "`/tars analyze`\n"
                                "→ Analyzes tickets from last 24 hours (default)\n\n"
                                "`/tars analyze [hours]`\n"
                                "→ Custom time range in hours\n"
                                "_Examples: /tars analyze 6, /tars analyze 12, /tars analyze 48_\n\n"
                                "`/tars analyze [days]d`\n"
                                "→ Custom time range in days\n"
                                "_Examples: /tars analyze 7d, /tars analyze 30d_\n\n"
                                "`/tars help`\n"
                                "→ Shows this message"
                    }
                },
                {
                    "type": "divider"
                },
                {
                    "type": "context",
                    "elements": [
                        {
                            "type": "mrkdwn",
                            "text": "⚡ Analysis typically takes 30-60 seconds\n"
                                    "📊 Reports are posted to the current channel\n"
                                    "🤖 Powered by OpenAI GPT-4o and Support Team's Determination"
                        }
                    ]
                }
            ]
        }
    
    def format_analyzing_response(self, hours: int) -> Dict:
        """
        Format initial acknowledgment response
        
        Args:
            hours: Number of hours being analyzed
            
        Returns:
            Slack message payload
        """
        if hours < 24:
            time_text = f"last {hours} hours"
        elif hours == 24:
            time_text = "last 24 hours"
        elif hours % 24 == 0:
            days = hours // 24
            time_text = f"last {days} day{'s' if days > 1 else ''}"
        else:
            time_text = f"last {hours} hours"
        
        return {
            "response_type": "in_channel",
            "text": f"🔄 Analyzing tickets from {time_text}... This will take 30-60 seconds."
        }
    
    def format_error_response(self, error_type: str) -> Dict:
        """
        Format error response
        
        Args:
            error_type: Type of error ("invalid", "unknown", etc.)
            
        Returns:
            Slack message payload
        """
        if error_type == "invalid":
            text = "❌ Invalid time format. Use `/tars help` for examples.\n\n" \
                   "Valid formats: `/tars analyze 6`, `/tars analyze 7d`"
        elif error_type == "unknown":
            text = "❌ Unknown command. Use `/tars help` to see available commands."
        else:
            text = "❌ An error occurred. Please try again or use `/tars help`."
        
        return {
            "response_type": "ephemeral",  # Only visible to user
            "text": text
        }
