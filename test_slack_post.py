"""
End-to-end test: Fetch tickets → AI Analysis → Post to Slack
Tests the complete TARS pipeline
"""
import sys
import os
import logging
import requests
from dotenv import load_dotenv
from pipeline.supportpal_client import SupportPalClient
from pipeline.ai_analyzer import AIAnalyzer
from utils.slack_formatter import SlackFormatter

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_full_pipeline():
    """Test the complete TARS pipeline end-to-end"""
    
    print("=" * 60)
    print("TARS - Full Pipeline Test (→ Slack)")
    print("=" * 60)
    print()
    
    # Check for required API keys
    supportpal_key = os.getenv('SUPPORTPAL_API_KEY')
    supportpal_url = os.getenv('SUPPORTPAL_API_URL')
    openai_key = os.getenv('OPENAI_API_KEY')
    slack_webhook = os.getenv('SLACK_WEBHOOK_URL')
    
    if not all([supportpal_key, supportpal_url, openai_key, slack_webhook]):
        print("❌ Missing required environment variables:")
        if not supportpal_key:
            print("   - SUPPORTPAL_API_KEY")
        if not supportpal_url:
            print("   - SUPPORTPAL_API_URL")
        if not openai_key:
            print("   - OPENAI_API_KEY")
        if not slack_webhook:
            print("   - SLACK_WEBHOOK_URL")
        return False
    
    print("✅ All API keys configured")
    print()
    
    # Step 1: Fetch tickets
    print("📊 Step 1: Fetching tickets from SupportPal...")
    client = SupportPalClient(supportpal_url, supportpal_key)
    tickets = client.get_tickets_for_analysis(hours=24)
    
    if not tickets:
        print("⚠️  No tickets found in last 24 hours, trying last 7 days...")
        tickets = client.get_tickets_for_analysis(hours=168)
    
    if not tickets:
        print("❌ No tickets available for analysis")
        return False
    
    print(f"✅ Fetched {len(tickets)} tickets")
    print()
    
    # Step 2: AI Analysis
    print("🧠 Step 2: Analyzing tickets with OpenAI...")
    print(f"   This may take 20-40 seconds...")
    print()
    
    analyzer = AIAnalyzer(openai_key)
    analysis = analyzer.analyze_tickets(tickets)
    
    if not analysis:
        print("❌ AI analysis failed")
        return False
    
    print("✅ AI analysis complete!")
    print(f"   Found {len(analysis.get('clusters', []))} critical clusters")
    print()
    
    # Step 3: Format for Slack
    print("💬 Step 3: Formatting message for Slack...")
    
    # Extract base URL from full API URL
    # e.g., https://support.int.windscribe.com/api → https://support.int.windscribe.com
    base_url = supportpal_url.replace('/api', '')
    
    formatter = SlackFormatter(base_url)
    slack_message = formatter.format_analysis(analysis)
    
    print("✅ Slack message formatted")
    print()
    
    # Step 4: Post to Slack
    print("🚀 Step 4: Posting to Slack...")
    print(f"   Webhook: {slack_webhook[:50]}...")
    print()
    
    try:
        response = requests.post(
            slack_webhook,
            json=slack_message,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        if response.status_code == 200:
            print("✅ Successfully posted to Slack!")
            print()
            print("=" * 60)
            print("🎉 Check your Slack channel for the report!")
            print("=" * 60)
            print()
            return True
        else:
            print(f"❌ Slack API returned error: {response.status_code}")
            print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Failed to post to Slack: {e}")
        return False


if __name__ == "__main__":
    try:
        success = test_full_pipeline()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
