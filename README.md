# 🤖 Trading Alert Bot

Unlimited price alerts + RSI divergence detection + Multi-exchange whale monitoring

> Free alternative to TradingView premium alerts with AI-powered technical analysis

[English](#english) | [한국어](./README.ko.md)

---

## ✨ Features

### 📊 Price Alerts
- 🪙 **Cryptocurrency**: Real-time monitoring on Upbit (KRW) & Binance (USDT)
- 🇺🇸 **US Stocks**: yfinance API integration
- 🇰🇷 **Korean Stocks**: Korea Investment & Securities (KIS) API
- 📢 **Discord Notifications**: Market-specific channel alerts
- 💾 **Unlimited Alerts**: JSON-based storage (no 20-alert limit!)

### 📈 RSI Indicators & Divergence Detection
- RSI level alerts (overbought/oversold)
- Automatic RSI divergence detection (bullish/bearish)
- Multi-timeframe support (1h, 4h, 1d)
- Binance & yfinance data integration

### 🐋 Multi-Exchange Whale Alerts
- **Real-time monitoring across 4 exchanges**
  - 🟡 Binance (USDT)
  - 🔵 OKX (USDT)
  - 🟣 Bybit (USDT)
  - 🟢 Upbit (KRW)
- Instant alerts for large trades (customizable thresholds per exchange)
- Exchange-specific on/off controls
- Persistent settings storage

### 🎮 Discord Bot Commands
- Fast `!` prefix-based commands
- Real-time price lookup with mini charts
- RSI queries and alert setup
- Whale alert controls

## 🚀 Quick Start

### 1. Installation

```bash
# Install dependencies
pip install -r requirements.txt
```

**Required packages:**
- discord.py
- websocket-client
- pandas, numpy
- requests, yfinance

### 2. Environment Setup

Copy `.env.example` to `.env`:

```env
# Discord Bot Token (for bot commands)
DISCORD_BOT_TOKEN=your_bot_token_here

# Discord Webhooks (for alerts)
DISCORD_WEBHOOK_CRYPTO=https://discord.com/api/webhooks/YOUR_WEBHOOK
DISCORD_WEBHOOK_US_STOCK=https://discord.com/api/webhooks/YOUR_WEBHOOK
DISCORD_WEBHOOK_KR_STOCK=https://discord.com/api/webhooks/YOUR_WEBHOOK

# Korea Investment & Securities API (optional)
KIS_APP_KEY=your_app_key
KIS_APP_SECRET=your_app_secret
```

**Discord Bot Setup:**
1. Create a bot at [Discord Developer Portal](https://discord.com/developers/applications)
2. Enable **MESSAGE CONTENT INTENT** in Bot settings ✅
3. Copy bot token → paste in `.env`

### 3. Run Discord Bot

```bash
python discord_bot.py
```

### 4. Run Price Monitor (Optional)

```bash
python main.py
```

## 🎮 Discord Commands

### 💰 Price Lookup
```
!현재가 BTC          # Current price + 24h mini chart
!rsi BTC 4h          # RSI value lookup
```

### 🔔 Price Alerts
```
!알람추가 crypto BTC above 100000    # Add price alert
!알람목록                            # List alerts
!알람삭제 [ID]                       # Delete alert
!상태                                # System status
```

### 📊 Indicator Alerts
```
!다이버전스 BTC 4h                   # RSI divergence alert
!rsi알람 BTC below 30 4h             # RSI level alert
!지표목록                            # List indicator alerts
!지표삭제 [ID]                       # Delete indicator alert
```

### 🐋 Whale Alerts
```
!고래 on                             # Enable whale alerts
!고래 off                            # Disable whale alerts
!고래 상태                           # Check status
!고래임계값 BTC 1000000              # Set threshold ($1M)
!거래소 Binance off                  # Disable specific exchange
```

### ⚙️ Other
```
!도움말                              # Show all commands
```

## 📋 Advanced Configuration

### Whale Alert Thresholds

| Threshold | Description | Recommended For |
|-----------|-------------|-----------------|
| $100K | Small whales | Frequent updates |
| $500K | Medium whales | General use |
| $1M+ | Large whales only | Important trades only |

### Exchange Controls

```bash
# In Discord:
!거래소 Binance on      # Enable Binance
!거래소 Upbit off       # Disable Upbit
```

Settings are automatically saved to `whale_settings.json`.

## 📁 Project Structure

```
Alram Bot/
├── discord_bot.py           # Discord bot (! commands)
├── main.py                  # Price monitor main
├── config.py                # Configuration
├── alert_manager.py         # Alert management
├── notifier.py              # Discord notifications
├── monitors/                # Market monitors
│   ├── crypto_monitor.py    # Crypto monitor
│   ├── us_stock_monitor.py  # US stock monitor
│   ├── kr_stock_monitor.py  # KR stock monitor
│   ├── indicator_monitor.py # RSI/divergence monitor
│   └── whale_monitor.py     # Multi-exchange whale monitor
├── utils/                   # Utilities
│   ├── logger.py
│   └── indicators.py        # Technical indicators
├── requirements.txt
├── .env.example
├── alerts.json              # Price alert data
└── whale_settings.json      # Whale alert settings
```

## 🐋 How Whale Alerts Work

1. **Real-time WebSocket connections**: Simultaneous connections to 4 exchanges
2. **Large trade detection**: Triggers when trades exceed configured thresholds
3. **Instant notifications**: Sends exchange name + trade details to Discord

**Alert Example:**
```
🐋 Whale Detected! [Binance] 🐋

BTC/USDT 🟢 BUY
━━━━━━━━━━━━━━━━
💰 Trade Amount: $1.5M (~$1.5M USD)
📊 Quantity: 15.38 BTC
💵 Price: $97,500.00
⏰ Time: 14:23:15
```

## 🔧 Check Intervals

Adjust check intervals in `.env`:

```env
CRYPTO_CHECK_INTERVAL=1      # Crypto (seconds)
US_STOCK_CHECK_INTERVAL=60   # US stocks (seconds)
KR_STOCK_CHECK_INTERVAL=5    # KR stocks (seconds)
```

## 📝 Notes

- US stock data may have 15-min delay (yfinance free tier)
- Korean stocks require KIS API configuration
- Alerts have a 5-minute cooldown after triggering
- Discord bot requires `MESSAGE CONTENT INTENT` enabled

## 🆘 Troubleshooting

### Discord notifications not working
- Check webhook URLs in `.env`
- Test with `python test_webhook.py`

### ! commands not responding
- Verify `MESSAGE CONTENT INTENT` is enabled in Discord bot settings
- Check if `discord_bot.py` is running

### Whale alerts not working
- Activate with `!고래 on`
- Check threshold isn't too high (`!고래 상태`)
- Restart bot (`Ctrl+C` then re-run)

## 🛠️ Tech Stack

- **Python 3.8+**
- **Discord.py**: Bot commands
- **WebSocket**: Real-time data (exchange-specific WS APIs)
- **Pandas/NumPy**: Indicator calculations
- **Requests**: REST API calls

## 📄 License

MIT License

## 🙏 Contributing

Issues and PRs are always welcome!

## 🌟 Support

If you find this project helpful, please give it a star! ⭐

---

**Made with ❤️ for Crypto Traders**
