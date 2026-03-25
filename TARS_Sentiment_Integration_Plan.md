# TARS Sentiment Intelligence — Integration Plan

## What is this

Adding an AI-powered sentiment analysis layer to TARS that scores every support ticket for **sentiment**, **urgency**, **churn risk**, and generates a **one-line summary**. This runs alongside the existing daily classification pipeline and produces a new **weekly sentiment report** every Monday.

---

## What TARS does today

- Runs daily at 9 AM
- Fetches the last 24 hours of tickets from SupportPal
- Classifies each ticket into one of 16 predefined categories (payment issues, connection failures, refund requests, etc.)
- Detects emerging new trends that don't fit existing categories
- Posts a formatted daily report to Slack with category breakdowns and per-ticket summaries
- Stores everything in MongoDB
- Has a React dashboard for visualization

---

## What changes

**The daily pipeline gains a new step.** After classification, each ticket gets scored for:

- **Sentiment** — positive, neutral, frustrated, or angry — to track customer mood across tickets
- **Urgency** — low, medium, high, or critical — to prioritize response effort
- **Churn risk** — low, medium, or high — to flag customers likely to cancel
- **One-line summary** — free text, quick human-readable issue description

**A new weekly job runs every Monday at 10 AM** and posts a sentiment rollup to Slack:

- Sentiment distribution (% frustrated/angry vs. neutral/positive) with week-over-week comparison
- Top 5 complaint topics by volume
- Churn risk breakdown (how many high-risk tickets this week)
- Spike detection (e.g. "frustrated tickets jumped 40% on Wednesday")
- Top 5 highest churn-risk tickets with summaries

---

## What does NOT change

- The existing daily Slack report — format stays the same, no sentiment clutter added to it
- The 16 category classification — untouched
- The new trend detection — untouched
- The Slack bot commands — untouched

---

## New pipeline flow

### Daily (9 AM, same as today)

1. Fetch tickets from SupportPal
2. **Step 2:** AI Classification (existing — categories, trends)
3. **Step 2.5:** Sentiment Analysis **(NEW)** — sentiment, urgency, churn, summary
4. **Step 3:** Save everything to MongoDB (existing + new fields per ticket)
5. **Step 4:** Post daily report to Slack (unchanged)

### Weekly (Monday 10 AM, new)

1. Query past 7 days of tickets from MongoDB
2. Aggregate sentiment trends, churn distribution, spikes
3. Post weekly sentiment report to Slack

---

## Technical implementation

- **Sentiment analyzer** — `pipeline/sentiment_analyzer.py` (new file) — Separate GPT-4o call with a focused prompt, isolated from classification
- **Pipeline integration** — `pipeline/analyzer.py` — New Step 2.5 between classification and MongoDB save
- **Storage** — `storage/mongodb_client.py` — 4 new fields per ticket doc + new indexes + weekly query method
- **Weekly report** — `utils/weekly_report.py` (new file) — Aggregation logic + Slack message formatting
- **Weekly scheduler** — `scheduler.py` — Second cron job: Monday 10 AM
- **Dashboard API** — `app.py` — New `GET /api/sentiment` endpoint for future dashboard use

---

## Cost impact

The sentiment prompt is lighter than the classification prompt (no category definitions, no trend logic). Estimated additional token usage for ~100 tickets/day:

- Sentiment analysis: ~5K–8K tokens/day (~$0.15–0.25/day)
- Weekly summary: ~2K tokens/week (negligible)
- **Estimated total: $5–10/month additional** on top of current GPT-4o usage

---

## What success looks like

### After 4 weeks

- Weekly sentiment report delivered automatically every Monday
- Ability to compare sentiment week-over-week and correlate with release dates
- Top 5 recurring complaint topics as actionable input for the product team
- At least one churn risk signal that leads to proactive outreach before cancellation

### After 3 months

- Tracked record of how sentiment has changed across app versions
- Data to support or challenge product roadmap decisions
- Reduced time spent on manual ticket review and reporting

---

## Rollout

1. Build and test sentiment analyzer locally
2. Wire into daily pipeline + MongoDB
3. Build weekly report formatter
4. Add weekly scheduler
5. Deploy to Demerzel
6. Dashboard sentiment views (future phase)
