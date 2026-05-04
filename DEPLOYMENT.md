# Deployment Guide

TARS runs as a systemd service on a Linux host, behind nginx, accessed over Tailscale.

## Initial Setup

### 1. Clone and install Python dependencies

```bash
ssh <your-server>
cd ~
git clone https://github.com/<your-fork>/TARS.git
cd TARS
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Build the dashboard

The frontend bundle isn't in git — it's built on the server.

```bash
# Node 20+ is required (Vite 7 + Tailwind v4)
node --version  # if < 20, install via NodeSource:
# curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash - && sudo apt install -y nodejs

cd dashboard
npm install
npm run build
cd ..
```

### 3. Configure environment

```bash
cp env.template .env
nano .env
```

Required:

```
SUPPORTPAL_API_KEY=...
SUPPORTPAL_API_URL=https://support.example.com/api
SUPPORTPAL_BRAND_ID=1
OPENAI_API_KEY=...
SLACK_BOT_TOKEN=xoxb-...
SLACK_APP_TOKEN=xapp-...
SLACK_CHANNEL_ID=C0...
MONGODB_URI=mongodb+srv://...
SCHEDULE_CRON=0 9 * * *
```

### 4. Create systemd service

```bash
sudo nano /etc/systemd/system/tars.service
```

```ini
[Unit]
Description=TARS - Ticket Analysis & Reporting System
After=network.target

[Service]
Type=simple
User=<your-user>
WorkingDirectory=/home/<your-user>/TARS
Environment="PATH=/home/<your-user>/TARS/venv/bin:/usr/local/bin:/usr/bin:/bin"
ExecStart=/home/<your-user>/TARS/venv/bin/python3 main.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable tars
sudo systemctl start tars
```

### 5. nginx reverse proxy

```bash
sudo nano /etc/nginx/sites-available/tars
```

```nginx
server {
    listen 80;
    server_name <your-host>;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 300;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/tars /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

## Updating

```bash
ssh <your-server>
cd ~/TARS
git pull
cd dashboard && npm install && npm run build && cd ..
sudo systemctl restart tars
```

If `requirements.txt` changed:

```bash
source venv/bin/activate
pip install -r requirements.txt
sudo systemctl restart tars
```

## Monitoring

```bash
sudo systemctl status tars               # is it running?
sudo journalctl -u tars -f                # follow logs
sudo journalctl -u tars --since "1h ago"  # recent
curl http://localhost:5000/health         # liveness
```

## Scheduled jobs

| Job | Schedule | Notes |
|-----|----------|-------|
| Daily analysis + QA report | 9:00 AM UTC | QA report posts inline after analysis |
| Weekly sentiment report | Tuesday 10:00 AM UTC | Standalone cron job |

## Troubleshooting

**Dashboard returns "Dashboard not built"** — `cd dashboard && npm run build`. The built bundle isn't in git.

**MongoDB connection errors** — verify `MONGODB_URI` and your IP is allowlisted in Atlas.

**No daily reports** — check `sudo journalctl -u tars` for "Scheduler started" line; verify `SCHEDULE_CRON` and Slack tokens.

**QA report not posting** — it runs inline after the daily analysis. If the daily analysis failed, the QA report won't run. Check logs.

**Frontend not reachable from teammates** — make sure the host is on your Tailscale network (`sudo tailscale up` once to authenticate).
