"""
Korean Stock price monitor using KIS (Korea Investment & Securities) API
"""
import time
import threading
from typing import Dict, Optional
import requests
import json

from alert_manager import AlertManager
from notifier import DiscordNotifier
from config import CHECK_INTERVALS, KIS_CONFIG
from utils.logger import setup_logger

logger = setup_logger(__name__, "kr_stock_monitor.log")


class KRStockMonitor:
    """Monitor Korean stock prices using KIS API"""
    
    # KIS API endpoints
    BASE_URL = "https://openapi.koreainvestment.com:9443"
    
    def __init__(self, alert_manager: AlertManager, notifier: DiscordNotifier):
        self.alert_manager = alert_manager
        self.notifier = notifier
        self.running = False
        self.thread = None
        self.check_interval = CHECK_INTERVALS["kr_stock"]
        
        # API configuration
        self.app_key = KIS_CONFIG["app_key"]
        self.app_secret = KIS_CONFIG["app_secret"]
        self.access_token = None
        
        # Track current prices
        self.prices: Dict[str, float] = {}
        self._price_lock = threading.Lock()
        
        # Check if API is configured
        self.is_configured = bool(self.app_key and self.app_secret)
        if not self.is_configured:
            logger.warning("KIS API not configured. Set KIS_APP_KEY and KIS_APP_SECRET in .env")
    
    def start(self) -> None:
        """Start monitoring Korean stock prices"""
        if not self.is_configured:
            logger.error("Cannot start KR stock monitor: API not configured")
            return
        
        # Get access token
        if not self._get_access_token():
            logger.error("Failed to get KIS access token")
            return
        
        self.running = True
        self.thread = threading.Thread(
            target=self._run_monitor,
            name="KRStockMonitor",
            daemon=True
        )
        self.thread.start()
        logger.info(f"KR stock monitor started (interval: {self.check_interval}s)")
    
    def stop(self) -> None:
        """Stop monitoring"""
        self.running = False
        logger.info("KR stock monitor stopped")
    
    def _get_access_token(self) -> bool:
        """Get OAuth access token from KIS API"""
        url = f"{self.BASE_URL}/oauth2/tokenP"
        
        headers = {"content-type": "application/json"}
        body = {
            "grant_type": "client_credentials",
            "appkey": self.app_key,
            "appsecret": self.app_secret
        }
        
        try:
            response = requests.post(url, headers=headers, json=body, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            self.access_token = data.get("access_token")
            
            if self.access_token:
                logger.info("Successfully obtained KIS access token")
                return True
            else:
                logger.error("No access token in response")
                return False
                
        except Exception as e:
            logger.error(f"Failed to get access token: {e}")
            return False
    
    def _run_monitor(self) -> None:
        """Main monitoring loop"""
        while self.running:
            try:
                self._check_all_symbols()
            except Exception as e:
                logger.error(f"Error in KR stock monitor: {e}")
            
            # Wait for next check
            time.sleep(self.check_interval)
    
    def _check_all_symbols(self) -> None:
        """Check prices for all symbols with active alerts"""
        alerts = self.alert_manager.get_alerts(market="kr_stock", enabled_only=True)
        
        if not alerts:
            return
        
        # Get unique symbols
        symbols = list(set(alert.symbol for alert in alerts))
        
        logger.debug(f"Checking {len(symbols)} KR stock symbols")
        
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
        Fetch current price for a Korean stock symbol
        
        Args:
            symbol: Stock code (e.g., "005930" for Samsung Electronics)
        
        Returns:
            Current price or None if failed
        """
        if not self.access_token:
            logger.error("No access token available")
            return None
        
        # Current price inquiry endpoint
        url = f"{self.BASE_URL}/uapi/domestic-stock/v1/quotations/inquire-price"
        
        headers = {
            "content-type": "application/json",
            "authorization": f"Bearer {self.access_token}",
            "appkey": self.app_key,
            "appsecret": self.app_secret,
            "tr_id": "FHKST01010100"  # Transaction ID for current price inquiry
        }
        
        params = {
            "fid_cond_mrkt_div_code": "J",  # Market division (J: Stock)
            "fid_input_iscd": symbol  # Stock code
        }
        
        try:
            response = requests.get(url, headers=headers, params=params, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            if data.get("rt_cd") == "0":  # Success
                output = data.get("output", {})
                price = float(output.get("stck_prpr", 0))  # Current price
                
                if price > 0:
                    logger.debug(f"{symbol}: ₩{price:,.0f}")
                    return price
            else:
                logger.warning(f"API error for {symbol}: {data.get('msg1', 'Unknown error')}")
            
            return None
            
        except Exception as e:
            logger.error(f"Failed to fetch price for {symbol}: {e}")
            return None
    
    def _check_alerts(self, symbol: str, price: float) -> None:
        """Check if any alerts should trigger for this symbol"""
        triggered = self.alert_manager.check_price("kr_stock", symbol, price)
        
        for alert in triggered:
            logger.info(f"Alert triggered: {alert}")
            
            # Send notification
            success = self.notifier.send_alert(
                market=alert.market,
                symbol=alert.symbol,
                current_price=price,
                target_price=alert.price,
                condition=alert.condition
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
    
    print("Starting KR stock monitor in test mode...")
    
    alert_mgr = AlertManager()
    notifier = DiscordNotifier()
    monitor = KRStockMonitor(alert_mgr, notifier)
    
    # Add test alert (Samsung Electronics)
    alert_mgr.add_alert("kr_stock", "005930", "above", 70000)
    
    try:
        monitor.start()
        print("Monitor running. Press Ctrl+C to stop...")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping monitor...")
        monitor.stop()
