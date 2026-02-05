"""
US Stock price monitor using yfinance
"""
import time
import threading
from typing import Dict, Optional
import yfinance as yf

from alert_manager import AlertManager
from notifier import DiscordNotifier
from config import CHECK_INTERVALS
from utils.logger import setup_logger

logger = setup_logger(__name__, "us_stock_monitor.log")


class USStockMonitor:
    """Monitor US stock prices using yfinance"""
    
    def __init__(self, alert_manager: AlertManager, notifier: DiscordNotifier):
        self.alert_manager = alert_manager
        self.notifier = notifier
        self.running = False
        self.thread = None
        self.check_interval = CHECK_INTERVALS["us_stock"]
        
        # Track current prices
        self.prices: Dict[str, float] = {}
        self._price_lock = threading.Lock()
    
    def start(self) -> None:
        """Start monitoring US stock prices"""
        self.running = True
        self.thread = threading.Thread(
            target=self._run_monitor,
            name="USStockMonitor",
            daemon=True
        )
        self.thread.start()
        logger.info(f"US stock monitor started (interval: {self.check_interval}s)")
    
    def stop(self) -> None:
        """Stop monitoring"""
        self.running = False
        logger.info("US stock monitor stopped")
    
    def _run_monitor(self) -> None:
        """Main monitoring loop"""
        while self.running:
            try:
                self._check_all_symbols()
            except Exception as e:
                logger.error(f"Error in US stock monitor: {e}")
            
            # Wait for next check
            time.sleep(self.check_interval)
    
    def _check_all_symbols(self) -> None:
        """Check prices for all symbols with active alerts"""
        alerts = self.alert_manager.get_alerts(market="us_stock", enabled_only=True)
        
        if not alerts:
            return
        
        # Get unique symbols
        symbols = list(set(alert.symbol for alert in alerts))
        
        logger.debug(f"Checking {len(symbols)} US stock symbols")
        
        for symbol in symbols:
            try:
                price = self._fetch_price(symbol)
                if price:
                    # Update price cache
                    with self._price_lock:
                        self.prices[symbol] = price
                    
                    # Check alerts
                    self._check_alerts(symbol, price)
            except Exception as e:
                logger.error(f"Error fetching price for {symbol}: {e}")
    
    def _fetch_price(self, symbol: str) -> Optional[float]:
        """
        Fetch current price for a symbol using yfinance
        
        Note: yfinance data may be delayed by 15 minutes for free tier
        """
        try:
            ticker = yf.Ticker(symbol)
            
            # Try to get real-time price from info
            info = ticker.info
            
            # Try different price fields (yfinance can be inconsistent)
            price = (
                info.get("currentPrice") or
                info.get("regularMarketPrice") or
                info.get("previousClose")
            )
            
            if price:
                logger.debug(f"{symbol}: ${price:.2f}")
                return float(price)
            
            logger.warning(f"No price data available for {symbol}")
            return None
            
        except Exception as e:
            logger.error(f"Failed to fetch price for {symbol}: {e}")
            return None
    
    def _check_alerts(self, symbol: str, price: float) -> None:
        """Check if any alerts should trigger for this symbol"""
        triggered = self.alert_manager.check_price("us_stock", symbol, price)
        
        for alert in triggered:
            logger.info(f"Alert triggered: {alert}")
            
            # Send notification
            success = self.notifier.send_alert(
                market=alert.market,
                symbol=alert.symbol,
                current_price=price,
                target_price=alert.price,
                condition=alert.condition,
                additional_info={"Note": "Data may be delayed 15 minutes"}
            )
            
            if success:
                # Mark as triggered to start cooldown
                self.alert_manager.mark_triggered(alert.id)
    
    def get_price(self, symbol: str) -> Optional[float]:
        """Get cached price for a symbol"""
        with self._price_lock:
            return self.prices.get(symbol.upper())


if __name__ == "__main__":
    # Test mode
    from alert_manager import AlertManager
    from notifier import DiscordNotifier
    
    print("Starting US stock monitor in test mode...")
    
    alert_mgr = AlertManager()
    notifier = DiscordNotifier()
    monitor = USStockMonitor(alert_mgr, notifier)
    
    # Add test alert
    alert_mgr.add_alert("us_stock", "AAPL", "above", 150)
    
    try:
        monitor.start()
        print("Monitor running. Press Ctrl+C to stop...")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping monitor...")
        monitor.stop()
