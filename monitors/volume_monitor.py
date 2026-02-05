"""
Volume Spike Monitor for Binance
Detects unusual trading volume spikes and sends Discord alerts
"""

import time
import requests
from datetime import datetime
from typing import Dict, Optional
from utils.logger import logger


class VolumeMonitor:
    """Monitor for detecting volume spikes on Binance"""
    
    def __init__(self, notifier, symbols=None, threshold_percent=200):
        """
        Initialize volume monitor
        
        Args:
            notifier: DiscordNotifier instance
            symbols: List of symbols to monitor (e.g., ['BTC', 'ETH'])
            threshold_percent: Volume increase threshold (default 200% = 3x normal)
        """
        self.notifier = notifier
        self.symbols = symbols or ['BTC', 'ETH']
        self.threshold_percent = threshold_percent
        self.enabled = False
        self.running = False
        
        # Store average volumes for each symbol
        self.avg_volumes: Dict[str, float] = {}
        
        # Cooldown tracking (symbol -> timestamp)
        self.last_alert: Dict[str, float] = {}
        self.cooldown_seconds = 300  # 5 minutes
        
    def calculate_average_volume(self, symbol: str) -> Optional[float]:
        """
        Calculate average 4-hour volume from last 20 candles
        
        Args:
            symbol: Trading pair symbol (e.g., 'BTCUSDT')
            
        Returns:
            Average volume or None if error
        """
        try:
            # Get 20 4-hour candles from Binance
            url = "https://api.binance.com/api/v3/klines"
            params = {
                "symbol": f"{symbol}USDT",
                "interval": "4h",
                "limit": 20
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            candles = response.json()
            
            # Extract volumes (index 5 in each candle)
            volumes = [float(candle[5]) for candle in candles]
            
            # Calculate average
            avg_volume = sum(volumes) / len(volumes)
            
            logger.info(f"Calculated avg volume for {symbol}: {avg_volume:.2f}")
            return avg_volume
            
        except Exception as e:
            logger.error(f"Error calculating average volume for {symbol}: {e}")
            return None
    
    def get_current_volume(self, symbol: str) -> Optional[float]:
        """
        Get current 1-minute volume and convert to 4-hour equivalent
        
        Args:
            symbol: Trading pair symbol
            
        Returns:
            4-hour equivalent volume or None
        """
        try:
            # Get last 1-minute candle
            url = "https://api.binance.com/api/v3/klines"
            params = {
                "symbol": f"{symbol}USDT",
                "interval": "1m",
                "limit": 1
            }
            
            response = requests.get(url, params=params, timeout=10)
            response.raise_for_status()
            
            candle = response.json()[0]
            volume_1m = float(candle[5])
            
            # Convert to 4-hour equivalent (240 minutes)
            volume_4h_equiv = volume_1m * 240
            
            return volume_4h_equiv
            
        except Exception as e:
            logger.error(f"Error getting current volume for {symbol}: {e}")
            return None
    
    def check_volume_spike(self, symbol: str) -> bool:
        """
        Check if current volume is spiking
        
        Args:
            symbol: Symbol to check
            
        Returns:
            True if spike detected
        """
        # Update average volume if not cached
        if symbol not in self.avg_volumes:
            avg_vol = self.calculate_average_volume(symbol)
            if avg_vol:
                self.avg_volumes[symbol] = avg_vol
            else:
                return False
        
        # Get current volume
        current_vol = self.get_current_volume(symbol)
        if not current_vol:
            return False
        
        avg_vol = self.avg_volumes[symbol]
        
        # Calculate percentage increase
        percent_increase = (current_vol / avg_vol) * 100
        
        # Check if spike detected
        if percent_increase >= self.threshold_percent:
            # Check cooldown
            last_alert_time = self.last_alert.get(symbol, 0)
            if time.time() - last_alert_time < self.cooldown_seconds:
                return False
            
            logger.info(
                f"Volume spike detected for {symbol}: "
                f"{percent_increase:.0f}% of average"
            )
            
            self._send_alert(symbol, avg_vol, current_vol, percent_increase)
            self.last_alert[symbol] = time.time()
            return True
        
        return False
    
    def _send_alert(self, symbol: str, avg_vol: float, current_vol: float, percent: float):
        """Send volume spike alert to Discord"""
        
        # Get current price
        try:
            url = "https://api.binance.com/api/v3/ticker/price"
            params = {"symbol": f"{symbol}USDT"}
            response = requests.get(url, params=params, timeout=5)
            price = float(response.json()["price"])
            price_str = f"${price:,.2f}"
        except:
            price_str = "N/A"
        
        # Format volumes
        if avg_vol >= 1000:
            avg_str = f"{avg_vol/1000:.1f}K"
        else:
            avg_str = f"{avg_vol:.0f}"
            
        if current_vol >= 1000:
            current_str = f"{current_vol/1000:.1f}K"
        else:
            current_str = f"{current_vol:.0f}"
        
        message = (
            f"📊 **거래량 급증!** [{symbol}/USDT] 📊\n\n"
            f"💰 현재가: {price_str}\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"📈 4시간 평균: {avg_str} {symbol}\n"
            f"🔥 현재 추정: {current_str} {symbol}\n"
            f"📊 증가율: **{percent:.0f}%**\n"
            f"⏰ 시간: {datetime.now().strftime('%H:%M:%S')}"
        )
        
        self.notifier.send_crypto_alert(message)
        logger.info(f"Volume spike alert sent for {symbol}")
    
    def monitor_loop(self):
        """Main monitoring loop"""
        logger.info("Volume monitor started")
        
        # Initial calculation of averages
        for symbol in self.symbols:
            avg = self.calculate_average_volume(symbol)
            if avg:
                self.avg_volumes[symbol] = avg
        
        while self.running:
            try:
                for symbol in self.symbols:
                    if self.enabled:
                        self.check_volume_spike(symbol)
                
                # Sleep 30 seconds between checks
                time.sleep(30)
                
                # Recalculate averages every 10 minutes
                if int(time.time()) % 600 == 0:
                    for symbol in self.symbols:
                        avg = self.calculate_average_volume(symbol)
                        if avg:
                            self.avg_volumes[symbol] = avg
                            
            except Exception as e:
                logger.error(f"Error in volume monitor loop: {e}")
                time.sleep(30)
    
    def start(self):
        """Start the monitor"""
        if self.running:
            logger.warning("Volume monitor already running")
            return
        
        self.running = True
        
        import threading
        thread = threading.Thread(target=self.monitor_loop, daemon=True)
        thread.start()
        
        logger.info("Volume monitor thread started")
    
    def stop(self):
        """Stop the monitor"""
        self.running = False
        logger.info("Volume monitor stopped")
    
    def enable(self):
        """Enable volume alerts"""
        self.enabled = True
        if not self.running:
            self.start()
        logger.info("Volume alerts enabled")
    
    def disable(self):
        """Disable volume alerts"""
        self.enabled = False
        logger.info("Volume alerts disabled")
    
    def set_threshold(self, percent: int):
        """Set volume spike threshold percentage"""
        self.threshold_percent = percent
        logger.info(f"Volume threshold set to {percent}%")
    
    def get_status(self) -> dict:
        """Get current monitor status"""
        return {
            "enabled": self.enabled,
            "running": self.running,
            "symbols": self.symbols,
            "threshold_percent": self.threshold_percent,
            "avg_volumes": self.avg_volumes
        }


# Global instance
_volume_monitor = None


def get_volume_monitor():
    """Get the global volume monitor instance"""
    return _volume_monitor


def set_volume_monitor(monitor):
    """Set the global volume monitor instance"""
    global _volume_monitor
    _volume_monitor = monitor
