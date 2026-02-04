"""
Test script for AI Analyzer
Tests OpenAI clustering with real ticket data
"""
import sys
import os
import logging
from dotenv import load_dotenv
from pipeline.supportpal_client import SupportPalClient
from pipeline.ai_analyzer import AIAnalyzer

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_ai_analysis():
    """Test the AI analyzer with real ticket data"""
    
    print("=" * 60)
    print("TARS - AI Analyzer Test")
    print("=" * 60)
    print()
    
    # Check for required API keys
    supportpal_key = os.getenv('SUPPORTPAL_API_KEY')
    supportpal_url = os.getenv('SUPPORTPAL_API_URL')
    openai_key = os.getenv('OPENAI_API_KEY')
    
    if not all([supportpal_key, supportpal_url, openai_key]):
        print("❌ Missing required environment variables:")
        if not supportpal_key:
            print("   - SUPPORTPAL_API_KEY")
        if not supportpal_url:
            print("   - SUPPORTPAL_API_URL")
        if not openai_key:
            print("   - OPENAI_API_KEY")
        print()
        print("Please add OPENAI_API_KEY to your .env file")
        return False
    
    print("✅ API keys configured")
    print()
    
    # Step 1: Fetch tickets
    print("📊 Step 1: Fetching tickets from SupportPal...")
    client = SupportPalClient(supportpal_url, supportpal_key)
    
    # Get tickets from last 24 hours
    tickets = client.get_tickets_for_analysis(hours=24)
    
    if not tickets:
        print("⚠️  No tickets found in last 24 hours, trying last 7 days...")
        tickets = client.get_tickets_for_analysis(hours=168)
    
    if not tickets:
        print("❌ No tickets available for analysis")
        return False
    
    print(f"✅ Fetched {len(tickets)} tickets")
    print()
    
    # Step 2: Analyze with AI
    print("🧠 Step 2: Analyzing tickets with OpenAI...")
    print(f"   Using model: gpt-4o")
    print(f"   This may take 10-30 seconds...")
    print()
    
    analyzer = AIAnalyzer(openai_key)
    analysis = analyzer.analyze_tickets(tickets)
    
    if not analysis:
        print("❌ AI analysis failed")
        return False
    
    print("✅ AI analysis complete!")
    print()
    
    # Step 3: Display results
    print("=" * 60)
    print("ANALYSIS RESULTS")
    print("=" * 60)
    print()
    
    summary = analyzer.format_analysis_summary(analysis)
    print(summary)
    
    print()
    print("=" * 60)
    print("✅ Test completed successfully!")
    print("=" * 60)
    print()
    
    return True


if __name__ == "__main__":
    try:
        success = test_ai_analysis()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
