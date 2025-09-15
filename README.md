# Nouhin - Slack Delivery System

A web-based Slack delivery system with Streamlit interface.

## Quick Start

```bash
# 1. Copy environment template
cp .env.example .env

# 2. Edit .env with your tokens
# SLACK_BOT_TOKEN=your-actual-token-here

# 3. Install dependencies
pip install -r requirements.txt

# 4. Run the app
streamlit run app/streamlit_app.py
```

## Structure

- `app/` - Streamlit web interface
- `delivery/` - Core Slack delivery logic
- `.env` - Environment variables (create from `.env.example`)

See [README_APP.md](README_APP.md) for detailed documentation.
