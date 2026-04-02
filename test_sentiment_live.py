"""
Live test: run sentiment analysis on 50 real tickets with full conversations.
Prints results to console so you can evaluate quality.
"""
import os
import json
import logging
from dotenv import load_dotenv
from pipeline.supportpal_client import SupportPalClient
from pipeline.sentiment_analyzer import SentimentAnalyzer
from pipeline.analyzer import _strip_html

load_dotenv()
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

client = SupportPalClient(
    os.getenv("SUPPORTPAL_API_URL"),
    os.getenv("SUPPORTPAL_API_KEY"),
)
brand_id = int(os.getenv("SUPPORTPAL_BRAND_ID", "0")) or None

logger.info("Fetching tickets from SupportPal (last 48 hours)...")
raw_tickets = client.get_tickets_for_analysis(hours=48, brand_id=brand_id)
tickets = raw_tickets[:50]
logger.info(f"Using {len(tickets)} tickets for sentiment test")

# Fetch full conversations (same logic as analyzer.py Step 2.5a)
logger.info("Fetching full customer conversations...")
for t in tickets:
    try:
        msgs = client.get_ticket_messages(int(t["id"]))
        customer_texts = []
        for m in msgs:
            if m.get("user_id"):
                customer_texts.append(_strip_html(m.get("text", "")))
        full_convo = "\n---\n".join(customer_texts)
        t["full_conversation"] = full_convo[:8000]
    except Exception as e:
        logger.warning(f"Could not fetch messages for ticket #{t.get('number')}: {e}")
        t["full_conversation"] = t.get("first_message", "")[:8000]

convo_lens = [len(t.get("full_conversation", "")) for t in tickets]
logger.info(
    f"Conversation lengths: min={min(convo_lens)}, "
    f"avg={sum(convo_lens)//len(convo_lens)}, max={max(convo_lens)}"
)

# Run sentiment analysis
analyzer = SentimentAnalyzer(os.getenv("OPENAI_API_KEY"))
logger.info("Running sentiment analysis (batched)...")
results = analyzer.analyze(tickets)

# Print results
print("\n" + "=" * 100)
print(f"SENTIMENT RESULTS — {len(results)}/{len(tickets)} tickets scored")
print("=" * 100)

for t in tickets:
    num = str(t["number"])
    r = results.get(num)
    if not r:
        print(f"\n#{num} — NO RESULT")
        continue

    subj = t["subject"][:70]
    convo_len = len(t.get("full_conversation", ""))
    print(
        f"\n#{num} — {subj}"
        f"\n  Sentiment: {r['sentiment']:<12}  Urgency: {r['urgency']:<10}  "
        f"Churn: {r['churn_risk']:<8}  Convo: {convo_len} chars"
        f"\n  Summary: {r['summary']}"
    )

# Print distribution
print("\n" + "=" * 100)
print("DISTRIBUTION")
print("=" * 100)

from collections import Counter
sentiments = Counter(r["sentiment"] for r in results.values())
urgencies = Counter(r["urgency"] for r in results.values())
churns = Counter(r["churn_risk"] for r in results.values())

print(f"\nSentiment:  {dict(sentiments)}")
print(f"Urgency:    {dict(urgencies)}")
print(f"Churn Risk: {dict(churns)}")
