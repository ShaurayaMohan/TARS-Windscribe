"""
Test script for SupportPal API connection
Run this to verify your API credentials and test ticket fetching
"""
import sys
import os
import logging
from datetime import datetime
from dotenv import load_dotenv
from pipeline.supportpal_client import SupportPalClient

# Load environment variables
load_dotenv()

# Set up logging to see what's happening
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_connection():
    """Test SupportPal API connection and fetch recent tickets"""
    
    print("=" * 60)
    print("TARS - SupportPal Connection Test")
    print("=" * 60)
    print()
    
    # Get API credentials from environment
    api_url = os.getenv('SUPPORTPAL_API_URL')
    api_token = os.getenv('SUPPORTPAL_API_KEY')
    
    if not api_url or not api_token:
        print("❌ Error: Missing environment variables!")
        print("   Please create a .env file with:")
        print("   - SUPPORTPAL_API_URL")
        print("   - SUPPORTPAL_API_KEY")
        return False
    
    print(f"🔗 Using API URL: {api_url}")
    print(f"🔑 API Key configured: {'*' * 10}{api_token[-4:]}")
    print()
    print("Testing connection...")
    print()
    
    # Initialize client
    client = SupportPalClient(api_url, api_token)
    
    # Test 1: Fetch tickets from last 24 hours
    print("📊 Test 1: Fetching tickets from last 24 hours...")
    tickets = client.get_tickets_since(hours=24, limit=10)
    
    if not tickets:
        print("⚠️  No tickets found in the last 24 hours")
        print("   Trying last 7 days instead...")
        tickets = client.get_tickets_since(hours=168, limit=10)
    
    if not tickets:
        print("❌ No tickets found. This could mean:")
        print("   - Your API credentials are incorrect")
        print("   - There are no tickets in your system")
        print("   - The API URL is wrong")
        return False
    
    print(f"✅ Successfully fetched {len(tickets)} tickets!")
    print()
    
    # Show sample ticket data
    print("=" * 60)
    print("Sample Tickets:")
    print("=" * 60)
    
    for i, ticket in enumerate(tickets[:3], 1):  # Show first 3 tickets
        print(f"\n{i}. Ticket #{ticket.get('number', ticket.get('id'))}")
        print(f"   Subject: {ticket.get('subject', 'N/A')}")
        print(f"   Status: {ticket.get('status', 'N/A')}")
        print(f"   Priority: {ticket.get('priority', 'N/A')}")
        created = ticket.get('created_at')
        if created:
            created_date = datetime.fromtimestamp(created)
            print(f"   Created: {created_date}")
    
    print()
    print("=" * 60)
    
    # Test 2: Fetch messages for first ticket
    if tickets:
        first_ticket_id = tickets[0].get('id')
        print(f"\n📝 Test 2: Fetching messages for ticket #{first_ticket_id}...")
        
        messages = client.get_ticket_messages(first_ticket_id)
        
        if messages:
            print(f"✅ Successfully fetched {len(messages)} messages")
            first_message = messages[0].get('text', '')
            if first_message:
                # Show preview of first message (first 200 chars)
                preview = first_message[:200] + "..." if len(first_message) > 200 else first_message
                print(f"\n   First message preview:")
                print(f"   {preview}")
        else:
            print("⚠️  No messages found for this ticket")
    
    print()
    print("=" * 60)
    
    # Test 3: Get enriched tickets for analysis
    print("\n🔍 Test 3: Preparing tickets for analysis (with first messages)...")
    enriched = client.get_tickets_for_analysis(hours=24)
    
    if not enriched:
        print("⚠️  Trying with last 7 days...")
        enriched = client.get_tickets_for_analysis(hours=168)
    
    if enriched:
        print(f"✅ Successfully prepared {len(enriched)} tickets for analysis")
        print(f"\n   Sample enriched ticket:")
        sample = enriched[0]
        print(f"   - ID: {sample['id']}")
        print(f"   - Number: {sample['number']}")
        print(f"   - Subject: {sample['subject']}")
        print(f"   - First message length: {len(sample['first_message'])} characters")
    else:
        print("❌ Could not prepare tickets for analysis")
        return False
    
    print()
    print("=" * 60)
    print("✅ All tests passed! SupportPal integration is working.")
    print("=" * 60)
    print()
    
    return True


if __name__ == "__main__":
    try:
        success = test_connection()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
