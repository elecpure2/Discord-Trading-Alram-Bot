"""
RSI Level Alert Monitor
Checks RSI levels at candle close times
"""

import time
import requests
from datetime import datetime
from typing import Dict, List, Optional
from utils.logger import logger


class RSIAlertMonitor:
    """Monitor RSI levels and trigger alerts at candle close"""
    
    # Timeframe to minutes mapping
    TIMEFRAMES = {
        '1m': 1,
        '5m': 5,
        '15m': 15,
        '30m': 30,
        '1h': 60,
        '4h': 240,
        '1d': 1440
    }
    
    def __init__(self, notifier, alert_manager):
        """
        Initialize RSI alert monitor
        
        Args:
            notifier: DiscordNotifier instance
            alert_manager: AlertManager instance
        """
        self.notifier = notifier
        self.alert_manager = alert_manager
        self.enabled = False
        self.running = False
        
        # Track last check times for each timeframe
        self.last_check: Dict[str, int] = {}
    
    def calculate_rsi(self, symbol: str, timeframe: str, market: str, period: int = 14) -> Optional[float]:
        """
        Calculate RSI for given symbol and timeframe
        
        Args:
            symbol: Trading symbol
            timeframe: Timeframe (1h, 4h, 1d, etc.)
            market: Market type (crypto, us_stock, kr_stock)
            period: RSI period (default 14)
            
        Returns:
            RSI value or None if error
        """
        try:
            if market == "crypto":
                # Use Binance
                url = "https://api.binance.com/api/v3/klines"
                
                # Convert symbol format
                if '/' in symbol:
                    symbol = symbol.replace('/', '')
                elif not symbol.endswith('USDT'):
                    symbol = f"{symbol}USDT"
                
                params = {
                    "symbol": symbol,
                    "interval": timeframe,
                    "limit": period + 1
                }
                
                response = requests.get(url, params=params, timeout=10)
                response.raise_for_status()
                
                candles = response.json()
                
                # Extract close prices
                closes = [float(candle[4]) for candle in candles]
                
            elif market in ["us_stock", "kr_stock"]:
                # Use yfinance for both US and KR stocks
                import yfinance as yf
                
                # Convert timeframe
                interval_map = {
                    '1m': '1m', '5m': '5m', '15m': '15m', '30m': '30m',
                    '1h': '1h', '4h': '1h', '1d': '1d'
                }
                interval = interval_map.get(timeframe, '1h')
                
                ticker = yf.Ticker(symbol)
                hist = ticker.history(period=f"{period + 5}d", interval=interval)
                
                if hist.empty:
                    logger.error(f"No data for {symbol}")
                    return None
                
                closes = hist['Close'].tolist()[-period-1:]
            
            else:
                logger.error(f"Unsupported market: {market}")
                return None
            
            # Calculate RSI
            if len(closes) < period + 1:
                logger.warning(f"Not enough data for RSI calculation: {len(closes)}")
                return None
            
            # Calculate price changes
            deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
            
            # Separate gains and losses
            gains = [d if d > 0 else 0 for d in deltas]
            losses = [-d if d < 0 else 0 for d in deltas]
            
            # Calculate average gains and losses
            avg_gain = sum(gains[:period]) / period
            avg_loss = sum(losses[:period]) / period
            
            # Calculate RS and RSI
            if avg_loss == 0:
                return 100.0
            
            rs = avg_gain / avg_loss
            rsi = 100 - (100 / (1 + rs))
            
            logger.info(f"RSI for {symbol} ({timeframe}): {rsi:.2f}")
            return rsi
            
        except Exception as e:
            logger.error(f"Error calculating RSI for {symbol}: {e}")
            return None
    
    def should_check_timeframe(self, timeframe: str) -> bool:
        """
        Check if it's time to check this timeframe (at candle close)
        
        Args:
            timeframe: Timeframe to check
            
        Returns:
            True if should check now
        """
        minutes = self.TIMEFRAMES.get(timeframe)
        if not minutes:
            return False
        
        current_time = int(time.time())
        current_minute = (current_time // 60) % (24 * 60)
        
        # Check if we're at the start of a new candle
        if current_minute % minutes == 0:
            # Check if we haven't checked this minute yet
            last_check_minute = self.last_check.get(timeframe, 0)
            if current_minute != last_check_minute:
                self.last_check[timeframe] = current_minute
                return True
        
        return False
    
    def check_rsi_alerts(self):
        """Check all RSI alerts"""
        from utils.rsi_alerts import get_rsi_alerts, save_rsi_alerts
        
        # Get all enabled RSI alerts
        all_alerts = get_rsi_alerts()
        
        if not all_alerts:
            return
        
        # Group alerts by timeframe and symbol
        alerts_by_tf = {}
        for alert in all_alerts:
            if not alert.enabled:
                continue
            
            key = (alert.market, alert.symbol, alert.timeframe)
            if key not in alerts_by_tf:
                alerts_by_tf[key] = []
            alerts_by_tf[key].append(alert)
        
        # Check each group
        for (market, symbol, timeframe), alerts in alerts_by_tf.items():
            if not self.should_check_timeframe(timeframe):
                continue
            
            # Calculate RSI
            rsi = self.calculate_rsi(symbol, timeframe, market)
            if rsi is None:
                continue
            
            # Check each alert
            for alert in alerts:
                if alert.should_trigger(rsi):
                    # Send notification
                    self._send_rsi_alert(alert, rsi)
                    
                    # Mark as triggered
                    alert.mark_triggered()
        
        # Save updated alerts
        save_rsi_alerts(all_alerts)
    
    def _send_rsi_alert(self, alert: 'RSIAlert', current_rsi: float):
        """Send RSI alert notification"""
        condition_text = "초과" if alert.condition == "above" else "미만"
        
        market_emojis = {
            "crypto": "🪙",
            "us_stock": "🇺🇸", 
            "kr_stock": "🇰🇷"
        }
        emoji = market_emojis.get(alert.market, "📊")
        
        message = (
            f"📊 **RSI 알람!** {emoji}\n\n"
            f"**{alert.symbol}** ({alert.timeframe})\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"📈 현재 RSI: **{current_rsi:.2f}**\n"
            f"🎯 설정값: {alert.rsi_value} {condition_text}\n"
            f"⏰ 시간: {datetime.now().strftime('%H:%M:%S')}"
        )
        
        self.notifier.send_crypto_alert(message)
        logger.info(f"RSI alert sent for {alert.symbol}")
    
    def monitor_loop(self):
        """Main monitoring loop"""
        logger.info("RSI alert monitor started")
        
        while self.running:
            try:
                if self.enabled:
                    # Check each timeframe
                    for timeframe in self.TIMEFRAMES.keys():
                        if self.should_check_timeframe(timeframe):
                            logger.info(f"Checking {timeframe} RSI alerts")
                            self.check_rsi_alerts()
                
                # Sleep 30 seconds between checks
                time.sleep(30)
                
            except Exception as e:
                logger.error(f"Error in RSI monitor loop: {e}")
                time.sleep(30)
    
    def start(self):
        """Start the monitor"""
        if self.running:
            logger.warning("RSI monitor already running")
            return
        
        self.running = True
        
        import threading
        thread = threading.Thread(target=self.monitor_loop, daemon=True)
        thread.start()
        
        logger.info("RSI monitor thread started")
    
    def stop(self):
        """Stop the monitor"""
        self.running = False
        logger.info("RSI monitor stopped")
    
    def enable(self):
        """Enable RSI alerts"""
        self.enabled = True
        if not self.running:
            self.start()
        logger.info("RSI alerts enabled")
    
    def disable(self):
        """Disable RSI alerts"""
        self.enabled = False
        logger.info("RSI alerts disabled")


# Global instance
_rsi_monitor = None


def get_rsi_monitor():
    """Get the global RSI monitor instance"""
    return _rsi_monitor


def set_rsi_monitor(monitor):
    """Set the global RSI monitor instance"""
    global _rsi_monitor
    _rsi_monitor = monitor
