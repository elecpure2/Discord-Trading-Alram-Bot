"""
Discord notification system for Trading Alert Bot
"""
import requests
from typing import Dict, Optional, Literal
from datetime import datetime

from config import DISCORD_WEBHOOKS
from utils.logger import setup_logger

logger = setup_logger(__name__, "notifier.log")

MarketType = Literal["crypto", "us_stock", "kr_stock"]


class DiscordNotifier:
    """Handles sending notifications to Discord via webhooks"""
    
    # Color codes for different alert types
    COLORS = {
        "crypto": 0xF7931A,      # Bitcoin orange
        "us_stock": 0x0066CC,    # Blue
        "kr_stock": 0xFF6B6B,    # Red
        "success": 0x00FF00,     # Green
        "warning": 0xFFAA00,     # Orange
        "error": 0xFF0000,       # Red
    }
    
    # Emoji for different markets
    EMOJIS = {
        "crypto": "🪙",
        "us_stock": "🇺🇸",
        "kr_stock": "🇰🇷",
    }
    
    def __init__(self):
        self.webhooks = DISCORD_WEBHOOKS
        self._validate_webhooks()
    
    def _validate_webhooks(self) -> None:
        """Validate that at least one webhook is configured"""
        if not any(self.webhooks.values()):
            logger.warning("No Discord webhooks configured!")
    
    def send_alert(
        self,
        market: MarketType,
        symbol: str,
        current_price: float,
        target_price: float,
        condition: str,
        additional_info: Optional[Dict] = None
    ) -> bool:
        """
        Send a price alert notification to Discord
        
        Args:
            market: Market type (crypto, us_stock, kr_stock)
            symbol: Trading symbol (e.g., "BTC/USDT", "AAPL")
            current_price: Current price
            target_price: Target price that triggered the alert
            condition: Alert condition (e.g., "above", "below")
            additional_info: Optional additional information
        
        Returns:
            True if notification was sent successfully
        """
        webhook_url = self.webhooks.get(market)
        
        if not webhook_url:
            logger.error(f"No webhook configured for market: {market}")
            return False
        
        # Build embed message
        embed = self._build_alert_embed(
            market, symbol, current_price, target_price, condition, additional_info
        )
        
        payload = {
            "embeds": [embed],
            "username": "Trading Alert Bot",
        }
        
        try:
            response = requests.post(webhook_url, json=payload, timeout=10)
            response.raise_for_status()
            logger.info(f"Alert sent for {symbol} ({market})")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send Discord notification: {e}")
            return False
    
    def _build_alert_embed(
        self,
        market: MarketType,
        symbol: str,
        current_price: float,
        target_price: float,
        condition: str,
        additional_info: Optional[Dict] = None
    ) -> Dict:
        """Build Discord embed for price alert"""
        emoji = self.EMOJIS.get(market, "📊")
        color = self.COLORS.get(market, 0x808080)
        
        # Calculate price change
        price_diff = current_price - target_price
        price_diff_pct = (price_diff / target_price) * 100 if target_price else 0
        
        # Determine direction emoji
        direction_emoji = "📈" if current_price > target_price else "📉"
        
        embed = {
            "title": f"{emoji} Price Alert Triggered!",
            "color": color,
            "fields": [
                {
                    "name": "📊 Symbol",
                    "value": f"`{symbol}`",
                    "inline": True
                },
                {
                    "name": "💰 Current Price",
                    "value": f"`{self._format_price(current_price)}`",
                    "inline": True
                },
                {
                    "name": "🎯 Target Price",
                    "value": f"`{self._format_price(target_price)}`",
                    "inline": True
                },
                {
                    "name": "📍 Condition",
                    "value": f"`{condition.upper()}`",
                    "inline": True
                },
                {
                    "name": f"{direction_emoji} Price Change",
                    "value": f"`{self._format_price(price_diff)} ({price_diff_pct:+.2f}%)`",
                    "inline": True
                },
                {
                    "name": "⏰ Time",
                    "value": f"`{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}`",
                    "inline": True
                },
            ],
            "footer": {
                "text": f"Market: {market.replace('_', ' ').title()}"
            }
        }
        
        # Add additional info if provided
        if additional_info:
            for key, value in additional_info.items():
                embed["fields"].append({
                    "name": key,
                    "value": str(value),
                    "inline": True
                })
        
        return embed
    
    def send_test_message(self, market: MarketType) -> bool:
        """Send a test message to verify webhook configuration"""
        webhook_url = self.webhooks.get(market)
        
        if not webhook_url:
            logger.error(f"No webhook configured for market: {market}")
            return False
        
        embed = {
            "title": "✅ Test Message",
            "description": "Trading Alert Bot is configured correctly!",
            "color": self.COLORS["success"],
            "fields": [
                {
                    "name": "Market",
                    "value": market.replace("_", " ").title(),
                    "inline": True
                },
                {
                    "name": "Status",
                    "value": "🟢 Online",
                    "inline": True
                },
                {
                    "name": "Time",
                    "value": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                    "inline": False
                }
            ]
        }
        
        payload = {
            "embeds": [embed],
            "username": "Trading Alert Bot",
        }
        
        try:
            response = requests.post(webhook_url, json=payload, timeout=10)
            response.raise_for_status()
            logger.info(f"Test message sent to {market}")
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send test message: {e}")
            return False
    
    def send_system_message(
        self,
        message: str,
        level: Literal["info", "warning", "error"] = "info"
    ) -> bool:
        """Send a system message to all configured webhooks"""
        color_map = {
            "info": self.COLORS["success"],
            "warning": self.COLORS["warning"],
            "error": self.COLORS["error"],
        }
        
        emoji_map = {
            "info": "ℹ️",
            "warning": "⚠️",
            "error": "❌",
        }
        
        embed = {
            "title": f"{emoji_map[level]} System Message",
            "description": message,
            "color": color_map[level],
            "timestamp": datetime.utcnow().isoformat()
        }
        
        payload = {
            "embeds": [embed],
            "username": "Trading Alert Bot",
        }
        
        success = False
        for market, webhook_url in self.webhooks.items():
            if webhook_url:
                try:
                    response = requests.post(webhook_url, json=payload, timeout=10)
                    response.raise_for_status()
                    success = True
                except requests.exceptions.RequestException as e:
                    logger.error(f"Failed to send system message to {market}: {e}")
        
        return success
    
    @staticmethod
    def _format_price(price: float) -> str:
        """Format price with appropriate decimal places"""
        if price >= 1000:
            return f"${price:,.2f}"
        elif price >= 1:
            return f"${price:.4f}"
        else:
            return f"${price:.8f}"
    
    def send_whale_alert(self, message: str) -> bool:
        """Send whale alert to crypto webhook only (avoids duplicate messages)"""
        webhook_url = self.webhooks.get("crypto")
        
        if not webhook_url:
            logger.error("No crypto webhook configured for whale alerts")
            return False
        
        embed = {
            "title": "⚠️ System Message",
            "description": message,
            "color": self.COLORS["warning"],
            "timestamp": datetime.utcnow().isoformat()
        }
        
        payload = {
            "embeds": [embed],
            "username": "Trading Alert Bot",
        }
        
        try:
            response = requests.post(webhook_url, json=payload, timeout=10)
            response.raise_for_status()
            return True
        except requests.exceptions.RequestException as e:
            logger.error(f"Failed to send whale alert: {e}")
            return False

