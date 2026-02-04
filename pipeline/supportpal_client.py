"""
SupportPal API Client
Handles fetching tickets and messages from SupportPal
"""
import requests
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class SupportPalClient:
    """Client for interacting with SupportPal API"""
    
    def __init__(self, api_url: str, api_token: str):
        """
        Initialize SupportPal client
        
        Args:
            api_url: Base URL for SupportPal API (e.g., https://support.example.com/api)
            api_token: API token for authentication
        """
        self.api_url = api_url.rstrip('/')
        self.auth = (api_token, 'X')  # Basic auth with token as username
        self.session = requests.Session()
        self.session.auth = self.auth
        
    def get_tickets_since(self, hours: int = 24, limit: int = 100) -> List[Dict]:
        """
        Fetch tickets created in the last N hours
        
        Args:
            hours: Number of hours to look back (default: 24)
            limit: Maximum number of tickets per page (default: 100)
            
        Returns:
            List of ticket dictionaries
        """
        # Calculate UNIX timestamp for N hours ago
        since_time = datetime.now() - timedelta(hours=hours)
        created_at_min = int(since_time.timestamp())
        
        logger.info(f"Fetching tickets created since {since_time} (timestamp: {created_at_min})")
        
        all_tickets = []
        start = 1
        
        while True:
            # Fetch page of tickets
            params = {
                'created_at_min': created_at_min,
                'start': start,
                'limit': limit,
                'order_column': 'created_at',
                'order_direction': 'desc'
            }
            
            try:
                response = self.session.get(
                    f"{self.api_url}/ticket/ticket",
                    params=params,
                    timeout=30
                )
                response.raise_for_status()
                
                data = response.json()
                
                if data.get('status') != 'success':
                    logger.error(f"API returned non-success status: {data}")
                    break
                
                tickets = data.get('data', [])
                
                if not tickets:
                    # No more tickets
                    break
                
                all_tickets.extend(tickets)
                logger.info(f"Fetched {len(tickets)} tickets (total so far: {len(all_tickets)})")
                
                # Check if we've fetched all tickets (less than limit means last page)
                if len(tickets) < limit:
                    break
                
                start += limit
                
            except requests.exceptions.RequestException as e:
                logger.error(f"Error fetching tickets: {e}")
                break
        
        logger.info(f"Total tickets fetched: {len(all_tickets)}")
        return all_tickets
    
    def get_ticket_messages(self, ticket_id: int) -> List[Dict]:
        """
        Fetch all messages for a specific ticket
        
        Args:
            ticket_id: The ticket ID
            
        Returns:
            List of message dictionaries
        """
        try:
            params = {
                'ticket_id': ticket_id,
                'include_draft': 0,
                'type': 0,  # Only ticket messages, not notes
                'order_column': 'created_at',
                'order_direction': 'asc'
            }
            
            response = self.session.get(
                f"{self.api_url}/ticket/message",
                params=params,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            
            if data.get('status') != 'success':
                logger.error(f"API returned non-success status for ticket {ticket_id}: {data}")
                return []
            
            return data.get('data', [])
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Error fetching messages for ticket {ticket_id}: {e}")
            return []
    
    def get_first_message_body(self, ticket_id: int) -> Optional[str]:
        """
        Get the body of the first message in a ticket (the user's initial complaint)
        
        Args:
            ticket_id: The ticket ID
            
        Returns:
            Message text or None if no messages found
        """
        messages = self.get_ticket_messages(ticket_id)
        
        if messages:
            # Get the first message (sorted by created_at asc)
            first_message = messages[0]
            return first_message.get('text', '')
        
        return None
    
    def get_tickets_for_analysis(self, hours: int = 24) -> List[Dict]:
        """
        Fetch tickets and enrich with first message body for analysis
        
        Args:
            hours: Number of hours to look back (default: 24)
            
        Returns:
            List of tickets with 'id', 'subject', and 'first_message' fields
        """
        tickets = self.get_tickets_since(hours=hours)
        
        if not tickets:
            logger.warning("No tickets found in the specified time range")
            return []
        
        enriched_tickets = []
        
        for ticket in tickets:
            ticket_id = ticket.get('id')
            subject = ticket.get('subject', 'No Subject')
            
            # Fetch first message
            first_message = self.get_first_message_body(ticket_id)
            
            if first_message:
                enriched_tickets.append({
                    'id': ticket_id,
                    'number': ticket.get('number', ticket_id),
                    'subject': subject,
                    'first_message': first_message,
                    'created_at': ticket.get('created_at'),
                    'status': ticket.get('status_name', 'Unknown'),
                    'priority': ticket.get('priority_name', 'Unknown'),
                })
            else:
                logger.warning(f"Ticket {ticket_id} has no messages, skipping")
        
        logger.info(f"Prepared {len(enriched_tickets)} tickets for analysis")
        return enriched_tickets
