# Project TARS

**T**icket **A**nalysis & **R**eporting **S**ystem

An automated intelligence system for Windscribe's support team. TARS fetches tickets from SupportPal, runs three AI analysis layers (classification, sentiment, QA), stores results in MongoDB, and reports findings to Slack daily.

## Features

- **Daily Ticket Classification** — Clusters tickets into 16 categories with trend detection using GPT-4o
- **Sentiment Analysis** — Scores every ticket for sentiment (positive / neutral-confused / frustrated / angry), urgency, and churn risk using full customer conversation threads
- **QA Bug Detection** — Flags product bugs with 18 fixed feature areas and 9 platforms, posts a daily QA report to Slack with hyperlinked tickets
- **Weekly Sentiment Report** — Aggregated sentiment trends posted to Slack every Tuesday at 10 AM UTC
- **Slack Integration** — `/tars` slash command, daily summaries with colored category breakdowns, threaded ticket details
- **MongoDB Storage** — Full historical data for all analyses, tickets, sentiment scores, and QA signals
- **React Dashboard** — Web UI for browsing analyses, trends, and ticket details
- **Scheduled Automation** — Runs daily at 9 AM UTC via APScheduler, deployed as a systemd service

## Architecture

```
TARS/
├── app.py                          # Flask web server + API endpoints
├── main.py                         # Entry point (starts Flask + scheduler)
├── scheduler.py                    # APScheduler: daily analysis, weekly sentiment, daily QA
├── config.py                       # Configuration loader
├── slack_socket_app.py             # Slack Socket Mode for slash commands
├── pipeline/
│   ├── analyzer.py                 # Main pipeline orchestrator (Steps 1–5)
│   ├── ai_analyzer.py              # GPT-4o ticket classification (categories + trends)
│   ├── sentiment_analyzer.py       # GPT-4o sentiment/urgency/churn scoring (batched)
│   ├── qa_analyzer.py              # GPT-4o QA bug extraction (batched, 18 feature areas)
│   └── supportpal_client.py        # SupportPal API client (tickets + messages)
├── storage/
│   └── mongodb_client.py           # MongoDB read/write, aggregation queries
├── utils/
│   ├── slack_formatter.py          # Daily Slack report (colored attachments + threads)
│   ├── slack_commands.py           # Slash command handlers
│   ├── weekly_report.py            # Weekly sentiment Slack report
│   └── qa_report.py                # Daily QA Slack report (colored clusters + ticket links)
├── dashboard/                      # React + TypeScript + Vite frontend
│   └── src/
│       └── api.ts                  # Frontend API client with TypeScript interfaces
├── requirements.txt                # Python dependencies
└── .env                            # API keys and config (not in git)
```

## Daily Pipeline Flow

```
Step 1:    Fetch tickets from SupportPal (Windscribe only, brand_id=1)
Step 2:    AI classification — 16 categories + new trend detection
Step 2.5a: Fetch full customer conversation threads (up to 8,000 chars per ticket)
Step 2.5b: Sentiment analysis — batched GPT-4o (sentiment, urgency, churn risk, summary)
Step 2.5c: QA bug extraction — batched GPT-4o (is_bug, feature_area, platform, error_pattern)
Step 3:    Save to MongoDB (classification + sentiment + QA fields per ticket)
Step 4:    Post daily classification report to Slack
Step 5:    Post daily QA report to Slack (colored clusters with ticket links)
```

## Scheduled Jobs

| Job | Schedule | Description |
|-----|----------|-------------|
| Daily analysis | 9:00 AM UTC daily | Full pipeline run (Steps 1–5) |
| Daily QA report | After daily analysis | Posted inline after pipeline completes |
| Weekly sentiment report | Tuesday 10:00 AM UTC | Aggregated sentiment trends for the past 7 days |

## QA Feature Areas (18 fixed categories)

`connection_engine`, `protocol_wireguard`, `protocol_ikev2`, `protocol_openvpn`, `protocol_stealth`, `protocol_amnezia`, `app_crash`, `app_ui`, `localization`, `look_and_feel`, `dns_robert`, `split_tunneling`, `allow_lan_traffic`, `authentication`, `billing_app_bugs`, `static_ip_app_issues`, `config_generation`, `other`

## QA Platforms (9 fixed values)

`windows`, `macos`, `linux`, `android`, `ios`, `router`, `browser_extension`, `tv`, `unknown`

## Sentiment Categories

| Category | Description |
|----------|-------------|
| positive | Satisfied, expressing gratitude, complimentary |
| neutral_confused | Factual bug reports, standard questions, simple confusion |
| frustrated | Clearly annoyed, repeated issues, losing patience |
| angry | Hostile, threatening, ALL CAPS, aggressive ultimatums |

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/api/stats` | Dashboard summary statistics |
| GET | `/api/analyses?limit=N` | Recent analyses |
| GET | `/api/analyses/:id` | Single analysis detail |
| GET | `/api/tickets?analysis_id=X` | Tickets for an analysis |
| GET | `/api/trends?days=N` | Trend data for charts |
| GET | `/api/sentiment?days=N` | Aggregated sentiment stats |
| GET | `/api/qa?days=N&min_count=M` | QA cluster data |
| GET | `/api/prompt` | Current AI prompt template |
| POST | `/api/prompt` | Save custom prompt template |
| POST | `/analyze` | Manually trigger analysis |
| GET | `/health` | Health check |

## Setup

### 1. Install Dependencies

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
cp .env.example .env
```

Required variables:
- `SUPPORTPAL_API_KEY` — SupportPal admin API key
- `SUPPORTPAL_API_URL` — e.g. `https://support.int.windscribe.com/api`
- `SUPPORTPAL_BRAND_ID` — `1` for Windscribe
- `OPENAI_API_KEY` — GPT-4o API key
- `SLACK_BOT_TOKEN` — Slack bot OAuth token (`xoxb-...`)
- `SLACK_CHANNEL_ID` — Channel for reports
- `SLACK_APP_TOKEN` — Slack app-level token for Socket Mode (`xapp-...`)
- `MONGODB_URI` — MongoDB connection string

### 3. Run

```bash
# Development
python3 app.py

# Production (Demerzel)
sudo systemctl start tars
```

## Cost Estimate

| Layer | Daily Cost |
|-------|-----------|
| Classification (GPT-4o) | ~$0.15 |
| Sentiment (GPT-4o) | ~$0.50 |
| QA extraction (GPT-4o) | ~$0.50 |
| **Total** | **~$1.15/day** |

## License

Proprietary — Windscribe Internal Use Only
