# TARS

> *"That's not possible."*
> *"No, it's necessary."*

**T**icket **A**nalysis & **R**eporting **S**ystem — an AI co-pilot for the Windscribe support team.

Every morning at 9 AM UTC, TARS pulls the last 24 hours of support tickets, runs them through three GPT-4o analysis layers, stores everything in MongoDB, drops a digest in Slack, and serves a live dashboard. The support team stops drowning in tickets. The QA team finds bugs they didn't know existed. The CS team sees the angry customers before they churn.

It's named after the robot from *Interstellar*. Honesty setting: 90%.

---

## What it does

Three brains in a trench coat:

### 1. Classification
Reads every ticket, buckets it into one of 16 categories (payment, connection, app crash, account, etc.), and surfaces emerging trends the system has never seen before. *"Hey, 14 people complained about Apple Pay in the last 24h — that's new."*

### 2. Sentiment & Churn Risk
Reads the **full conversation thread** (not just the first message — that's how you miss the people who got nicer after raging) and scores each ticket on:
- **Sentiment** — positive / neutral-confused / frustrated / angry
- **Urgency** — low / medium / high / critical
- **Churn risk** — low / medium / high

Then rolls it up into a **Customer Health Score (0-100)** with a tooltip explaining the math, because "vibes" isn't a metric you can put on a slide.

### 3. QA Bug Detection
This one is the QA team's favorite. It hunts for actual product bugs across **18 fixed feature areas** (WireGuard, split tunneling, DNS/ROBERT, app crashes, localization, etc.) and **9 platforms** (Windows, macOS, Linux, Android, iOS, router, browser ext, TV, unknown).

The prompt has been beaten into shape over many iterations to *not* flag things like:
- Bank-side payment rejections
- App store subscription glitches
- General "it's slow" complaints
- Network censorship in the user's country
- CAPTCHA failures

It posts a daily QA digest to Slack with **color-coded clusters per platform** and clickable ticket links straight to SupportPal.

---

## The Dashboard

Three tabs. Dark theme. The `glass-card` aesthetic.

| Tab | What's in it |
|-----|--------------|
| **Daily Runs** | Run selector dropdown, stats cards, category/trend panels for the chosen run, full ticket table with AI summaries, "Run Analysis Now" button |
| **QA** | Stats cards (bugs by status), date filter, color-coded platform badges, sortable bug list with editable status (`not_tested` / `reproduced` / `escalated`) and dismiss-to-trash |
| **Sentiment** | Customer Health Score with explainer tooltip, three donut charts (sentiment / urgency / churn), filterable ticket table |

Built with React 19 + Vite 7 + Tailwind CSS v4. Flask serves the built bundle from `dashboard/dist/`, so it's all one process.

---

## How it actually runs

```
                            9 AM UTC daily
                                  │
                                  ▼
        ┌──────────────────────────────────────────────────┐
        │              Step 1: Fetch tickets                │
        │       SupportPal API • Windscribe brand only       │
        └──────────────────────────────────────────────────┘
                                  │
                                  ▼
        ┌──────────────────────────────────────────────────┐
        │     Step 2: Three AI layers (parallel batches)     │
        │  ┌────────────┐  ┌─────────────┐  ┌──────────┐   │
        │  │ Classifier │  │  Sentiment  │  │    QA    │   │
        │  └────────────┘  └─────────────┘  └──────────┘   │
        └──────────────────────────────────────────────────┘
                                  │
                                  ▼
        ┌──────────────────────────────────────────────────┐
        │   Step 3: Save to MongoDB (BEFORE posting Slack)  │
        │     ← so a Slack outage never loses your data      │
        └──────────────────────────────────────────────────┘
                                  │
                                  ▼
        ┌──────────────────────────────────────────────────┐
        │  Step 4 + 5: Post to Slack — daily digest + QA   │
        │           Weekly sentiment report on Tuesdays     │
        └──────────────────────────────────────────────────┘
```

The sentiment layer fetches **full conversation threads** from SupportPal (up to 8000 chars per ticket) so it can see how a ticket actually evolved. The classification layer just uses the first message because that's enough to bucket it.

---

## Stack

| Layer | Tech |
|-------|------|
| AI | OpenAI GPT-4o (batched calls per layer) |
| Backend | Python 3.12, Flask, APScheduler, slack-bolt (Socket Mode) |
| Storage | MongoDB Atlas |
| Frontend | React 19, Vite 7, Tailwind v4, TypeScript, recharts |
| Deploy | systemd service on a Linux box, behind nginx, on a Tailscale network |

---

## Repo layout

```
TARS/
├── main.py                  start everything
├── app.py                   Flask + REST API
├── scheduler.py             cron jobs (daily run, weekly sentiment)
├── slack_socket_app.py      slash commands via Socket Mode
├── pipeline/
│   ├── analyzer.py          orchestrator — fetch → 3 AI layers → save → post
│   ├── ai_analyzer.py       classification (categories + trends)
│   ├── sentiment_analyzer.py    sentiment + urgency + churn (full threads)
│   ├── qa_analyzer.py       bug detection (18 areas × 9 platforms)
│   └── supportpal_client.py SupportPal API wrapper
├── storage/
│   └── mongodb_client.py    MongoDB queries + aggregation pipelines
├── utils/
│   ├── slack_formatter.py   daily classification report
│   ├── qa_report.py         daily QA report (colored clusters)
│   ├── weekly_report.py     weekly sentiment recap
│   └── slack_commands.py    /tars slash command handlers
└── dashboard/
    └── src/                 React app
        ├── api.ts           typed fetch client
        └── components/      DailyRuns, QA, Sentiment pages
```

---

## API endpoints

The dashboard talks to the same Flask app over JSON:

| Method | Path | Notes |
|--------|------|-------|
| GET | `/api/stats` | Top-of-page summary cards |
| GET | `/api/analyses` | Recent runs (date-range filterable) |
| GET | `/api/tickets?analysis_id=X` | Tickets for a single run |
| GET | `/api/sentiment` | Aggregated sentiment + health score |
| GET | `/api/sentiment/tickets` | Per-ticket sentiment scores |
| GET | `/api/qa/stats` | Bug counts by status |
| GET | `/api/qa/tickets` | Bug list (date + platform + status filters) |
| PATCH | `/api/qa/tickets/:id/status` | Update QA workflow state |
| PATCH | `/api/qa/tickets/:id/dismiss` | Soft-delete a false-positive bug |
| POST | `/analyze` | Manually trigger a run |
| GET | `/health` | systemd liveness check |

All endpoints accept `from_date` / `to_date` query params (ISO 8601). Datetimes come back as ISO strings, never raw `bson.ObjectId`.

---

## Setup

```bash
# 1. Backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt

# 2. Frontend
cd dashboard && npm install && npm run build && cd ..

# 3. Configure
cp env.template .env
# fill in OPENAI_API_KEY, SUPPORTPAL_*, SLACK_*, MONGODB_URI

# 4. Run
python3 main.py
```

Then hit `http://localhost:5000`.

For production deployment to a Linux box (systemd, nginx, Tailscale), see [DEPLOYMENT.md](DEPLOYMENT.md).

---

## Cost

Roughly **$1-2/day** in OpenAI API spend at current ticket volume (~70 tickets/day across three layers, batched). Cheaper than a coffee. Pays for itself the first time it catches a regression before QA does.

---

## Things this would not exist without

- **OpenAI** — for shipping a model that can actually read like a human
- **SupportPal** — for having an API
- **The Windscribe support team** — for the feedback loop that refined every prompt in here
- **`recharts`** — for making donut charts not look like 2014

---

## License

Proprietary — Windscribe internal use.
