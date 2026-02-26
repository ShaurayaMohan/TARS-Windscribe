"""
SupportPal API Client
Handles fetching tickets and messages from SupportPal
"""
import requests
from datetime import datetime, timedelta, timezone
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
        
    def list_brands(self) -> List[Dict]:
        """
        List all brands configured in SupportPal.
        Use this once to discover the numeric brand_id for Windscribe.

        Returns:
            List of brand dicts with at least 'id' and 'name' keys.
        """
        try:
            response = self.session.get(
                f"{self.api_url}/core/brand",
                timeout=30,
            )
            response.raise_for_status()
            data = response.json()
            brands = data.get("data", [])
            logger.info(f"Brands: {[(b.get('id'), b.get('name')) for b in brands]}")
            return brands
        except Exception as e:
            logger.error(f"Error fetching brands: {e}")
            return []

    def get_tickets_since(
        self, hours: int = 24, limit: int = 100, brand_id: Optional[int] = None
    ) -> List[Dict]:
        """
        Fetch tickets created in the last N hours.

        Args:
            hours: Number of hours to look back (default: 24)
            limit: Maximum number of tickets per page (default: 100)
            brand_id: If set, only return tickets belonging to this brand.
                      Find the correct ID by calling list_brands() once.

        Returns:
            List of ticket dictionaries
        """
        # Calculate UNIX timestamp for N hours ago
        # Use UTC timezone-aware datetime to ensure consistent timestamp calculation
        now_utc = datetime.now(timezone.utc)
        since_time = now_utc - timedelta(hours=hours)
        created_at_min = int(since_time.timestamp())

        brand_msg = f" (brand_id={brand_id})" if brand_id else " (all brands)"
        logger.info(
            f"Fetching tickets created since {since_time}"
            f" (timestamp: {created_at_min}){brand_msg}"
        )

        all_tickets = []
        start = 1

        while True:
            # Fetch page of tickets
            params = {
                'created_at_min': created_at_min,
                'start': start,
                'limit': limit,
                'order_column': 'created_at',
                'order_direction': 'desc',
            }
            if brand_id is not None:
                params['brand_id'] = brand_id
            
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
    
    def get_tickets_for_analysis(
        self, hours: int = 24, brand_id: Optional[int] = None
    ) -> List[Dict]:
        """
        Fetch tickets and enrich with first message body for analysis.

        Args:
            hours: Number of hours to look back (default: 24)
            brand_id: If set, only include tickets for this brand.

        Returns:
            List of tickets with 'id', 'subject', and 'first_message' fields
        """
        tickets = self.get_tickets_since(hours=hours, brand_id=brand_id)

        if not tickets:
            logger.warning("No tickets found in the specified time range")
            return []

        # ── Client-side brand filter ───────────────────────────────────────
        # Always filter client-side even if brand_id was sent as an API param,
        # because not all SupportPal versions honour that query parameter.
        if brand_id is not None:
            before = len(tickets)
            tickets = [t for t in tickets if t.get('brand_id') == brand_id]
            filtered = before - len(tickets)
            logger.info(
                f"Brand filter (brand_id={brand_id}): "
                f"kept {len(tickets)}/{before} tickets"
                + (f", dropped {filtered} non-Windscribe tickets" if filtered else "")
            )
            if not tickets:
                logger.warning(
                    f"All {before} tickets were filtered out by brand_id={brand_id}. "
                    "Check that SUPPORTPAL_BRAND_ID is correct (run list_brands() to verify)."
                )
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
