# ⚡ Listrik Bot

Telegram bot that monitors electricity usage via a Tuya smart plug, tracks prepaid token (kWh) balance, and sends alerts when running low.

## Features

- 🔌 Real-time power monitoring (voltage, current, wattage)
- 💰 kWh balance tracking with top-up history
- 📊 Daily/monthly usage analytics
- ⚠️ Low balance alerts via Telegram
- ☁️ Tuya Cloud API or 🏠 Local LAN connection

## Quick Start

1. **Clone and configure:**
   ```bash
   cp .env.example .env
   # Edit .env with your credentials
   ```

2. **Run with Docker:**
   ```bash
   docker compose up -d --build
   ```

3. **Or run locally:**
   ```bash
   pip install -r requirements.txt
   python src/bot.py
   ```

4. **Set your initial balance:**
   ```
   /setbalance 50.0
   ```

## Bot Commands

| Command | Description |
|---------|-------------|
| `/status` | Current reading + balance + estimate |
| `/topup <kwh>` | Record token purchase |
| `/setbalance <kwh>` | Set balance manually |
| `/usage` | Monthly usage report |
| `/today` | Today's hourly breakdown |
| `/history` | Top-up history |

## Configuration

See [.env.example](.env.example) for all options. Key settings:

- `CONNECTION_MODE` — `cloud` (default) or `local`
- `POLL_INTERVAL_SECONDS` — reading frequency (default: 60)
- `LOW_BALANCE_KWH` — alert threshold (default: 10)

## Cloud Mode Setup

1. Go to [iot.tuya.com](https://iot.tuya.com)
2. Get your **API Key** and **API Secret** from the Cloud project
3. Make sure your device is linked to the project
4. Set `TUYA_API_KEY`, `TUYA_API_SECRET`, `TUYA_API_REGION` in `.env`
