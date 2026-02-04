# Project TARS

**T**icket **A**nalysis & **R**eporting **S**ystem

An automated intelligence officer for support teams that analyzes tickets, identifies critical issues, and reports findings to Slack.

## Features

- **Automated Analysis**: Fetches tickets from the last 24 hours and clusters them by root cause using AI
- **Slack Integration**: Trigger analysis via `/tars` slash command or automatic scheduled reports
- **Smart Clustering**: Uses OpenAI to group similar issues and identify patterns
- **Flexible Deployment**: Run locally, in Docker, or on any cloud platform

## Setup

### 1. Install Dependencies

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install packages
pip install -r requirements.txt
```

### 2. Configure Environment

```bash
# Copy example config
cp .env.example .env

# Edit .env with your API credentials
nano .env
```

Required credentials:
- **SupportPal API Key**: From your SupportPal admin panel
- **OpenAI API Key**: From https://platform.openai.com/api-keys
- **Slack Webhook URL**: Create an incoming webhook in your Slack workspace
- **Slack Signing Secret**: From your Slack app's basic information page

### 3. Run the Application

```bash
# Development mode
python app.py

# Production mode with Gunicorn
gunicorn -w 4 -b 0.0.0.0:5000 app:app
```

## Usage

### Slack Slash Command

1. In Slack, type: `/tars analyze`
2. TARS will respond immediately with "Analyzing tickets..."
3. Within a few moments, the full analysis report will be posted to your configured channel

### Scheduled Reports

Configure the `SCHEDULE_CRON` variable in `.env` to automatically run reports:
- `0 9 * * *` - Daily at 9 AM
- `0 */6 * * *` - Every 6 hours
- `0 * * * *` - Every hour

## Architecture

```
TARS/
├── app.py                 # Flask web server & Slack endpoint
├── scheduler.py           # Background job scheduler
├── config.py              # Configuration loader
├── pipeline/
│   └── analyzer.py        # Core analysis pipeline
└── utils/
    └── slack_formatter.py # Slack message formatting
```

## How It Works

1. **Fetch**: Retrieves tickets from SupportPal API (last 24 hours)
2. **Analyze**: Sends ticket data to OpenAI for clustering
3. **Format**: Converts AI analysis into rich Slack blocks
4. **Report**: Posts findings to Slack via webhook

## Development

### Running Tests
```bash
pytest
```

### Docker Deployment
```bash
docker build -t tars .
docker run -p 5000:5000 --env-file .env tars
```

## License

Proprietary - Windscribe Internal Use Only
