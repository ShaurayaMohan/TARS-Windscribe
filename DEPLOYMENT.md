# TARS Deployment Guide

## Deploy to Render

### 1. Push to GitHub
```bash
cd /Users/shauraya/Desktop/TARS
git init
git add .
git commit -m "Initial TARS commit"
git branch -M main
git remote add origin YOUR_GITHUB_REPO_URL
git push -u origin main
```

### 2. Create Render Web Service
1. Go to https://render.com
2. Click "New +" → "Web Service"
3. Connect your GitHub repository
4. Configure:
   - **Name**: `tars` (or your choice)
   - **Environment**: `Python 3`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `python main.py`
   - **Plan**: Free (or paid for better performance)

### 3. Add Environment Variables in Render
Go to your service → Environment → Add the following:

```
SUPPORTPAL_API_KEY=your_key_here
SUPPORTPAL_API_URL=https://support.int.windscribe.com/api
OPENAI_API_KEY=your_key_here
SLACK_WEBHOOK_URL=your_webhook_here
SCHEDULE_CRON=0 9 * * *
PORT=10000
HOST=0.0.0.0
```

### 4. Deploy
- Click "Create Web Service"
- Render will automatically deploy
- Check logs to verify it started correctly

### 5. Verify It's Running
- Visit your Render URL (e.g., `https://tars.onrender.com`)
- You should see: `{"name":"TARS","status":"running"}`
- Check logs for: "✅ TARS is now running"
- Confirm scheduler shows: "Next run: [tomorrow at 9 AM]"

---

## Manual Trigger (Optional)
To manually trigger analysis via API:
```bash
curl -X POST https://your-tars-url.onrender.com/analyze \
  -H "Content-Type: application/json" \
  -d '{"hours": 24}'
```

---

## Monitoring
- **Render Dashboard**: Check logs, uptime, errors
- **Slack Channel**: Verify daily reports arrive at 9 AM
- **Health Endpoint**: `https://your-tars-url.onrender.com/health`

---

## Troubleshooting

### Server won't start
- Check Render logs for errors
- Verify all environment variables are set
- Make sure OpenAI/SupportPal/Slack APIs are accessible

### No reports appearing
- Check scheduler logs: "Next run time"
- Verify SCHEDULE_CRON is valid
- Test manual trigger endpoint

### Reports failing
- Check SupportPal API connectivity
- Verify OpenAI API key has credits
- Test Slack webhook URL manually
