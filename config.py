"""
Configuration management for Trading Alert Bot
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Project paths
BASE_DIR = Path(__file__).parent
ALERTS_FILE = BASE_DIR / "alerts.json"
LOGS_DIR = BASE_DIR / "logs"

# Ensure directories exist
LOGS_DIR.mkdir(exist_ok=True)

# Discord Bot Token
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN", "")

# Discord Webhook URLs
DISCORD_WEBHOOKS = {
    "crypto": os.getenv("DISCORD_WEBHOOK_CRYPTO", ""),
    "us_stock": os.getenv("DISCORD_WEBHOOK_US_STOCK", ""),
    "kr_stock": os.getenv("DISCORD_WEBHOOK_KR_STOCK", ""),
}

# Korean Investment & Securities API
KIS_CONFIG = {
    "app_key": os.getenv("KIS_APP_KEY", ""),
    "app_secret": os.getenv("KIS_APP_SECRET", ""),
    "account_number": os.getenv("KIS_ACCOUNT_NUMBER", ""),
}

# Check intervals (seconds)
CHECK_INTERVALS = {
    "crypto": int(os.getenv("CRYPTO_CHECK_INTERVAL", "1")),
    "us_stock": int(os.getenv("US_STOCK_CHECK_INTERVAL", "60")),
    "kr_stock": int(os.getenv("KR_STOCK_CHECK_INTERVAL", "5")),
}

# Market configurations
UPBIT_WEBSOCKET_URL = "wss://api.upbit.com/websocket/v1"
BINANCE_WEBSOCKET_URL = "wss://stream.binance.com:9443/ws"

# Logging configuration
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

# Alert configuration
MAX_ALERTS_PER_SYMBOL = 10  # Prevent spam
ALERT_COOLDOWN_SECONDS = 300  # 5 minutes cooldown after trigger


def validate_config() -> bool:
    """Validate that required configuration is present"""
    errors = []
    
    # Check Discord webhooks
    if not any(DISCORD_WEBHOOKS.values()):
        errors.append("At least one Discord webhook URL must be configured")
    
    # Check if alerts file is writable
    try:
        ALERTS_FILE.touch(exist_ok=True)
    except Exception as e:
        errors.append(f"Cannot write to alerts file: {e}")
    
    if errors:
        print("Configuration errors:")
        for error in errors:
            print(f"  - {error}")
        return False
    
    return True
