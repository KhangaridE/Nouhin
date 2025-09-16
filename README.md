# Nouhin - Slack Delivery System

A web-based Slack delivery system with Streamlit interface and automatic scheduling.

## Features

- 📨 **Manual Delivery**: Send reports immediately via web interface
- ⏰ **Automatic Scheduling**: Set daily delivery times for reports
- 📋 **Report Management**: Create, edit, and manage delivery templates
- 🔄 **Real-time Scheduler**: Background service for automatic deliveries
- 📊 **Status Monitoring**: Track scheduled jobs and system status

## Quick Start

### 🌐 **Streamlit Cloud + GitHub Actions (Recommended)**
For automatic scheduling with free cloud deployment:

```bash
# 1. Push to GitHub
git add .
git commit -m "Deploy to cloud"
git push origin main

# 2. Deploy to Streamlit Cloud
# - Go to share.streamlit.io
# - Connect your GitHub repo
# - Set main file: app/streamlit_app.py
# - Add SLACK_BOT_TOKEN environment variable

# 3. Setup GitHub Actions scheduling
# - Add SLACK_BOT_TOKEN to repository secrets
# - GitHub Actions will run automatically every hour
```

See [DEPLOYMENT_GUIDE.md](DEPLOYMENT_GUIDE.md) for detailed instructions.

### 🖥️ **Local Development**
```bash
# 1. Copy environment template
cp .env.example .env

# 2. Edit .env with your tokens
# SLACK_BOT_TOKEN=your-actual-token-here

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the complete system (recommended)
python run.py

# OR run just the web interface
streamlit run app/streamlit_app.py
```

## Scheduling System

The system includes an automatic scheduler that can send reports daily at configured times:

### ⚠️ **Important for Streamlit Cloud Users**
If you deploy the web interface on Streamlit Cloud, the built-in scheduler won't work reliably because cloud platforms don't support persistent background processes. 

**Solution**: Use the web interface on Streamlit Cloud for report management, but run the scheduler separately using one of these methods:
- **Local server/VPS**: Run `python scheduler_service.py`
- **Cron jobs**: System-level scheduling 
- **GitHub Actions**: Free cloud scheduling (included)

See [SCHEDULING_SETUP.md](SCHEDULING_SETUP.md) for detailed setup instructions.

### Setup Scheduled Reports
1. Go to "Report Management" page
2. Create or edit a report
3. Enable "Automatic daily delivery"
4. Set the delivery time
5. The scheduler will automatically send the report daily

### Monitor Scheduling
- Check scheduler status in the sidebar
- Use `python check_scheduler.py` for detailed status
- Start/stop scheduler from the web interface

## Structure

- `app/` - Streamlit web interface and scheduler
- `delivery/` - Core Slack delivery logic
- `run.py` - Complete system startup (web + scheduler)
- `check_scheduler.py` - Scheduler status checker
- `.env` - Environment variables (create from `.env.example`)

## Files

- **Main Interface**: `streamlit run app/streamlit_app.py`
- **With Scheduler**: `python run.py`
- **Check Status**: `python check_scheduler.py`

See [README_APP.md](README_APP.md) for detailed documentation.
