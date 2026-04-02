# TARS Deployment Guide — Demerzel

TARS runs on **Demerzel** (`demerzel.ca3.dev.windscribe.org`) as a systemd service.

## Initial Setup

### 1. Clone and install

```bash
ssh demerzel.ca3.dev.windscribe.org
cd /opt
git clone https://github.com/ShaurayaMohan/TARS-Windscribe.git tars
cd tars
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure environment

```bash
cp .env.example .env
nano .env
```

Required variables:

```
SUPPORTPAL_API_KEY=<key>
SUPPORTPAL_API_URL=https://support.int.windscribe.com/api
SUPPORTPAL_BRAND_ID=1
OPENAI_API_KEY=<key>
SLACK_BOT_TOKEN=xoxb-...
SLACK_CHANNEL_ID=C0ACXMD0KAA
SLACK_APP_TOKEN=xapp-...
MONGODB_URI=mongodb://...
SCHEDULE_CRON=0 9 * * *
```

### 3. Create systemd service

```bash
sudo nano /etc/systemd/system/tars.service
```

```ini
[Unit]
Description=TARS Ticket Analysis & Reporting System
After=network.target mongod.service

[Service]
Type=simple
User=root
WorkingDirectory=/opt/tars
EnvironmentFile=/opt/tars/.env
ExecStart=/opt/tars/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable tars
sudo systemctl start tars
```

## Deploying Updates

```bash
ssh demerzel.ca3.dev.windscribe.org
cd /opt/tars
git pull
sudo systemctl restart tars
```

If new Python dependencies were added:

```bash
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart tars
```

## Monitoring

### Service status

```bash
sudo systemctl status tars
```

### Live logs

```bash
sudo journalctl -u tars -f
```

### Recent logs

```bash
sudo journalctl -u tars --since "1 hour ago"
```

### Health check

```bash
curl http://localhost:5000/health
```

### Manual analysis trigger

```bash
curl -X POST http://localhost:5000/analyze \
  -H "Content-Type: application/json" \
  -d '{"hours": 24}'
```

## Troubleshooting

### Service won't start
- Check logs: `sudo journalctl -u tars -n 50`
- Verify `.env` exists and has all required variables
- Verify venv has all dependencies: `source venv/bin/activate && pip install -r requirements.txt`

### No daily reports
- Check scheduler is running: look for "Scheduler started" in logs
- Verify `SCHEDULE_CRON` is set (default: `0 9 * * *`)
- Verify Slack token and channel ID are correct

### QA report not posting
- The QA report runs inline after the daily analysis completes — check that the daily analysis itself succeeded
- Look for "Daily QA report triggered" in logs

### MongoDB connection errors
- Verify `MONGODB_URI` is correct
- Check MongoDB is running: `sudo systemctl status mongod`

## Scheduled Jobs

| Job | Schedule | Notes |
|-----|----------|-------|
| Daily analysis + QA report | 9:00 AM UTC | QA report posts after analysis completes |
| Weekly sentiment report | Tuesday 10:00 AM UTC | Separate cron job |
