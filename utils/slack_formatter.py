"""
Slack message formatter for TARS analysis reports
Formats AI analysis into rich Slack Block Kit messages
"""
import logging
from typing import Dict, List
from datetime import datetime

logger = logging.getLogger(__name__)

# Windscribe blue color for message accents
WINDSCRIBE_BLUE = "#003E70"


class SlackFormatter:
    """Formats TARS analysis results into Slack Block Kit messages"""
    
    def __init__(self, supportpal_base_url: str):
        """
        Initialize Slack formatter
        
        Args:
            supportpal_base_url: Base URL for SupportPal (e.g., https://support.int.windscribe.com)
        """
        self.supportpal_base_url = supportpal_base_url.rstrip('/')
        
    def format_analysis(self, analysis: Dict) -> Dict:
        """
        Format analysis results into Slack Block Kit message
        
        Args:
            analysis: Analysis dictionary from AI analyzer
            
        Returns:
            Slack message payload ready to send via webhook
        """
        if not analysis:
            return self._create_error_message("No analysis data available")
        
        blocks = []
        
        # Header section
        blocks.extend(self._create_header(analysis))
        
        # Add divider
        blocks.append({"type": "divider"})
        
        # Each cluster card
        clusters = analysis.get('clusters', [])
        for i, cluster in enumerate(clusters, 1):
            blocks.extend(self._create_cluster_card(i, cluster))
            
            # Add divider between clusters (but not after last one)
            if i < len(clusters):
                blocks.append({"type": "divider"})
        
        # Footer
        blocks.extend(self._create_footer())
        
        return {
            "blocks": blocks,
            "attachments": [
                {
                    "color": WINDSCRIBE_BLUE,
                    "blocks": []
                }
            ]
        }
    
    def _create_header(self, analysis: Dict) -> List[Dict]:
        """Create the header section"""
        total_tickets = analysis.get('total_tickets_analyzed', 0)
        num_clusters = len(analysis.get('clusters', []))
        analysis_date = analysis.get('analysis_date', datetime.now().strftime('%Y-%m-%d'))
        
        # Format timestamp
        now = datetime.now()
        timestamp = now.strftime('%B %d, %Y • %I:%M %p')
        
        return [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "🚨 TARS Intelligence Report",
                    "emoji": True
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{timestamp}*\n{total_tickets} tickets analyzed | {num_clusters} critical issues identified"
                }
            }
        ]
    
    def _create_cluster_card(self, cluster_num: int, cluster: Dict) -> List[Dict]:
        """Create a rich card for a single cluster"""
        blocks = []
        
        # Cluster number and title
        emoji = self._get_cluster_emoji(cluster_num)
        title = cluster.get('title', 'Unknown Issue')
        
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"{emoji} *CLUSTER #{cluster_num}*\n*{title}*"
            }
        })
        
        # Volume, Region, Impact
        volume = cluster.get('volume', 0)
        region = cluster.get('geographic_pattern', 'Multiple/Unknown')
        impact = cluster.get('user_impact', 'Unknown impact')
        
        blocks.append({
            "type": "section",
            "fields": [
                {
                    "type": "mrkdwn",
                    "text": f"📊 *Volume:*\n{volume} tickets"
                },
                {
                    "type": "mrkdwn",
                    "text": f"🌍 *Region:*\n{region}"
                },
                {
                    "type": "mrkdwn",
                    "text": f"💥 *Impact:*\n{impact}"
                }
            ]
        })
        
        # Probable Root Cause
        root_cause = cluster.get('probable_root_cause', 'Unknown cause')
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"🔧 *Probable Root Cause:*\n{root_cause}"
            }
        })
        
        # Affected Tickets
        ticket_ids = cluster.get('ticket_ids', [])
        ticket_links = self._format_ticket_links(ticket_ids)
        
        blocks.append({
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"🎫 *Affected Tickets:*\n{ticket_links}"
            }
        })
        
        # Note: Action buttons will be added once Notion/Dashboard is ready
        
        return blocks
    
    def _format_ticket_links(self, ticket_ids: List[int], max_display: int = 5) -> str:
        """
        Format ticket IDs as clickable Slack links
        
        Args:
            ticket_ids: List of ticket IDs
            max_display: Maximum number of tickets to show before "+X more"
            
        Returns:
            Formatted string with ticket links
        """
        if not ticket_ids:
            return "None"
        
        links = []
        for ticket_id in ticket_ids[:max_display]:
            url = f"{self.supportpal_base_url}/en/admin/ticket/view/{ticket_id}"
            links.append(f"<{url}|#{ticket_id}>")
        
        result = " ".join(links)
        
        if len(ticket_ids) > max_display:
            remaining = len(ticket_ids) - max_display
            result += f" +{remaining} more"
        
        return result
    
    def _create_action_buttons(self, ticket_ids: List[int]) -> Dict:
        """Create action buttons for the cluster"""
        if not ticket_ids:
            return None
        
        # Create filter URL for all tickets in cluster
        # For now, we'll just link to the first ticket (can enhance later with filtered views)
        first_ticket_url = f"{self.supportpal_base_url}/en/admin/ticket/view/{ticket_ids[0]}"
        
        return {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {
                        "type": "plain_text",
                        "text": "View All Tickets",
                        "emoji": True
                    },
                    "url": first_ticket_url,
                    "action_id": "view_tickets"
                }
            ]
        }
    
    def _create_footer(self) -> List[Dict]:
        """Create footer section"""
        return [
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "🤖 Generated by TARS • Automated Ticket Intelligence System"
                    }
                ]
            }
        ]
    
    def _get_cluster_emoji(self, cluster_num: int) -> str:
        """Get emoji for cluster number"""
        emojis = {
            1: "🔥",
            2: "💳",
            3: "🛡️"
        }
        return emojis.get(cluster_num, "⚠️")
    
    def _create_error_message(self, error_text: str) -> Dict:
        """Create an error message block"""
        return {
            "blocks": [
                {
                    "type": "section",
                    "text": {
                        "type": "mrkdwn",
                        "text": f"❌ *TARS Error*\n{error_text}"
                    }
                }
            ]
        }
