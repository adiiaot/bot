# Analyzer Bot

XAU/USD trading signal generator powered by TradingView data and Nvidia Vision AI, delivered via Telegram and a FastAPI web API.

## Overview

Implements a **4-timeframe framework** that scans XAU/USD across 1H/4H (trend), 15M (levels), 5M (pullback), and 1M (entry) to generate structured trading signals with 4 stacked entry legs and take-profit targets.

### Signal Pipeline

- **Level 1 — Trend** (1H/4H): Higher highs/lows analysis on two timeframes must agree
- **Level 2 — Levels** (15M): Swing-point detection for support/resistance
- **Level 3 — Pullback** (5M): Price proximity to key level with volatility check
- **Level 4 — Entry** (1M): Reversal candle confirmation (pin bar or engulfing)

## Features

- **Telegram bot** — `/signal`, `/analyze` (chart upload), `/log_trade`, `/stats`, `/dashboard`, `/help`
- **Dual verification** — API signal is cross-checked against Nvidia Vision AI chart analysis for confidence scoring
- **Trade logging** — Persist completed trades to Firestore with PnL calculation and streak tracking
- **Trading statistics** — Win rate, profit factor, average win/loss, consecutive streaks
- **REST API** — Endpoints for signals, trades, and stats via FastAPI
- **Rate-limited** — TradingView API request tracking against free-tier caps

## Tech Stack

| Layer | Technology |
|-------|-----------|
| Runtime | Python 3.12 |
| Web framework | FastAPI + uvicorn |
| Telegram | python-telegram-bot (polling) |
| Market data | TradingView via RapidAPI |
| Vision AI | Nvidia NIM (Llama vision models) |
| Database | Firestore (Firebase) |
| Deployment | Railway |

## Prerequisites

- Python 3.12
- A Telegram bot token (from [@BotFather](https://t.me/BotFather))
- TradingView API key from [RapidAPI](https://rapidapi.com/)
- Firebase service account (or environment-based credentials)
- Nvidia NIM API key (for chart screenshot analysis)

## Setup

### 1. Clone and install

```bash
git clone <repo-url>
cd bot
python -m venv venv
venv\Scripts\activate      # Windows
pip install -r requirements.txt
```

### 2. Configure environment

Create a `.env` file in the `bot/` directory:

```env
TELEGRAM_BOT_TOKEN=your_bot_token
TELEGRAM_CHAT_ID=your_chat_id

TRADINGVIEW_API_KEY=your_rapidapi_key
TRADINGVIEW_API_HOST=tradingview-data1.p.rapidapi.com

FIREBASE_PROJECT_ID=your_project_id
FIREBASE_PRIVATE_KEY="-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----"
FIREBASE_CLIENT_EMAIL=your_service_account_email

NVIDIA_NIM_API_KEY=your_nvidia_key
```

Alternatively, place a Firebase service account JSON file in the project root as `aot-analyzer-bot-firebase-adminsdk-fbsvc-96f7cb0ea5.json`.

### 3. Run

```bash
python main.py
```

The API starts at `http://localhost:8000` and the Telegram bot begins polling on startup.

## API Endpoints

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | Root with available endpoints |
| GET | `/health` | Health check |
| POST | `/api/signal` | Generate a new XAU/USD signal |
| GET | `/api/signal/{id}` | Retrieve a signal by ID |
| POST | `/api/trades` | Log a completed trade |
| GET | `/api/trades` | List all trades |
| GET | `/api/stats` | Trading statistics |
| GET | `/api/api-stats` | TradingView API request usage |

## Telegram Commands

| Command | Description |
|---------|-------------|
| `/signal` | Generate signal from TradingView API data |
| `/analyze` | Upload chart screenshot for dual-verified signal |
| `/log_trade` | Log a completed trade (`/log_trade entry:2345.50 exit:2365.50 result:win`) |
| `/stats` | View aggregated trading statistics |
| `/dashboard` | Link to web dashboard |
| `/help` | Show all commands |

## Deployment (Railway)

Push to a GitHub repo and connect it to Railway. Required environment variables (set in Railway dashboard):

- `TELEGRAM_BOT_TOKEN`
- `TELEGRAM_CHAT_ID`
- `TRADINGVIEW_API_KEY`, `TRADINGVIEW_API_HOST`
- `FIREBASE_PROJECT_ID`, `FIREBASE_PRIVATE_KEY`, `FIREBASE_CLIENT_EMAIL`
- `NVIDIA_NIM_API_KEY`

The repo includes `Procfile`, `railway.json`, and `runtime.txt` — Railway auto-detects these.
