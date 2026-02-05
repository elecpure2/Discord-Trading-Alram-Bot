"""
Cryptocurrency price monitor using WebSocket connections
Supports Upbit (KRW pairs) and Binance (USDT pairs)
"""
import json
import time
import threading
from typing import Dict, Callable, Optional
import websocket

from alert_manager import AlertManager
from notifier import DiscordNotifier
from config import UPBIT_WEBSOCKET_URL, BINANCE_WEBSOCKET_URL
from utils.logger import setup_logger

logger = setup_logger(__name__, "crypto_monitor.log")


class CryptoMonitor:
    """Monitor cryptocurrency prices via WebSocket"""
    
    def __init__(self, alert_manager: AlertManager, notifier: DiscordNotifier):
        self.alert_manager = alert_manager
        self.notifier = notifier
        self.running = False
        self.threads = []
        
        # Track current prices
        self.prices: Dict[str, float] = {}
        self._price_lock = threading.Lock()
    
    def start(self) -> None:
        """Start monitoring cryptocurrency prices"""
        self.running = True
        
        # Start Upbit monitor
        upbit_thread = threading.Thread(
            target=self._run_upbit_monitor,
            name="UpbitMonitor",
            daemon=True
        )
        upbit_thread.start()
        self.threads.append(upbit_thread)
        
        # Start Binance monitor
        binance_thread = threading.Thread(
            target=self._run_binance_monitor,
            name="BinanceMonitor",
            daemon=True
        )
        binance_thread.start()
        self.threads.append(binance_thread)
        
        logger.info("Crypto monitor started")
    
    def stop(self) -> None:
        """Stop monitoring"""
        self.running = False
        logger.info("Crypto monitor stopped")
    
    def _run_upbit_monitor(self) -> None:
        """Run Upbit WebSocket monitor with auto-reconnect"""
        while self.running:
            try:
                self._connect_upbit()
            except Exception as e:
                logger.error(f"Upbit monitor error: {e}")
                if self.running:
                    logger.info("Reconnecting to Upbit in 5 seconds...")
                    time.sleep(5)
    
    def _connect_upbit(self) -> None:
        """Connect to Upbit WebSocket"""
        # Get symbols to monitor from alerts
        symbols = self._get_upbit_symbols()
        
        if not symbols:
            logger.info("No Upbit alerts configured, waiting...")
            time.sleep(10)
            return
        
        # Build subscription message
        codes = [f"KRW-{symbol}" for symbol in symbols]
        subscribe_msg = [
            {"ticket": "trading-alert-bot"},
            {"type": "ticker", "codes": codes}
        ]
        
        def on_message(ws, message):
            try:
                data = json.loads(message)
                self._handle_upbit_message(data)
            except Exception as e:
                logger.error(f"Error handling Upbit message: {e}")
        
        def on_error(ws, error):
            logger.error(f"Upbit WebSocket error: {error}")
        
        def on_close(ws, close_status_code, close_msg):
            logger.info("Upbit WebSocket closed")
        
        def on_open(ws):
            logger.info(f"Upbit WebSocket connected, monitoring {len(symbols)} symbols")
            ws.send(json.dumps(subscribe_msg))
        
        ws = websocket.WebSocketApp(
            UPBIT_WEBSOCKET_URL,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
            on_open=on_open
        )
        
        ws.run_forever()
    
    def _handle_upbit_message(self, data: Dict) -> None:
        """Handle Upbit ticker message"""
        if data.get("type") != "ticker":
            return
        
        code = data.get("code", "")  # e.g., "KRW-BTC"
        price = data.get("trade_price", 0)
        
        if not code or not price:
            return
        
        # Extract symbol (e.g., "BTC" from "KRW-BTC")
        symbol = code.split("-")[1] if "-" in code else code
        
        # Update price
        with self._price_lock:
            self.prices[symbol] = price
        
        # Check alerts
        self._check_alerts("crypto", symbol, price)
    
    def _run_binance_monitor(self) -> None:
        """Run Binance WebSocket monitor with auto-reconnect"""
        while self.running:
            try:
                self._connect_binance()
            except Exception as e:
                logger.error(f"Binance monitor error: {e}")
                if self.running:
                    logger.info("Reconnecting to Binance in 5 seconds...")
                    time.sleep(5)
    
    def _connect_binance(self) -> None:
        """Connect to Binance WebSocket"""
        # Get symbols to monitor from alerts
        symbols = self._get_binance_symbols()
        
        if not symbols:
            logger.info("No Binance alerts configured, waiting...")
            time.sleep(10)
            return
        
        # Build stream URL (e.g., btcusdt@ticker/ethusdt@ticker)
        streams = "/".join([f"{s.lower()}usdt@ticker" for s in symbols])
        ws_url = f"{BINANCE_WEBSOCKET_URL}/{streams}"
        
        def on_message(ws, message):
            try:
                data = json.loads(message)
                self._handle_binance_message(data)
            except Exception as e:
                logger.error(f"Error handling Binance message: {e}")
        
        def on_error(ws, error):
            logger.error(f"Binance WebSocket error: {error}")
        
        def on_close(ws, close_status_code, close_msg):
            logger.info("Binance WebSocket closed")
        
        def on_open(ws):
            logger.info(f"Binance WebSocket connected, monitoring {len(symbols)} symbols")
        
        ws = websocket.WebSocketApp(
            ws_url,
            on_message=on_message,
            on_error=on_error,
            on_close=on_close,
            on_open=on_open
        )
        
        ws.run_forever()
    
    def _handle_binance_message(self, data: Dict) -> None:
        """Handle Binance ticker message"""
        if "s" not in data or "c" not in data:
            return
        
        symbol_pair = data["s"]  # e.g., "BTCUSDT"
        price = float(data["c"])  # Current price
        
        # Extract base symbol (e.g., "BTC" from "BTCUSDT")
        symbol = symbol_pair.replace("USDT", "")
        
        # Update price
        with self._price_lock:
            self.prices[symbol] = price
        
        # Check alerts
        self._check_alerts("crypto", symbol, price)
    
    def _check_alerts(self, market: str, symbol: str, price: float) -> None:
        """Check if any alerts should trigger"""
        triggered = self.alert_manager.check_price(market, symbol, price)
        
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
    
    def _get_upbit_symbols(self) -> list:
        """Get unique symbols from Upbit alerts"""
        alerts = self.alert_manager.get_alerts(market="crypto", enabled_only=True)
        # Filter for KRW pairs (Upbit uses KRW)
        symbols = set()
        for alert in alerts:
            # Assume symbols like "BTC", "ETH" are for Upbit (KRW market)
            if "/" not in alert.symbol or "KRW" in alert.symbol:
                symbol = alert.symbol.replace("KRW-", "").replace("/KRW", "")
                symbols.add(symbol)
        return list(symbols)
    
    def _get_binance_symbols(self) -> list:
        """Get unique symbols from Binance alerts"""
        alerts = self.alert_manager.get_alerts(market="crypto", enabled_only=True)
        # Filter for USDT pairs
        symbols = set()
        for alert in alerts:
            if "USDT" in alert.symbol or "/USDT" in alert.symbol:
                symbol = alert.symbol.replace("/USDT", "").replace("USDT", "")
                symbols.add(symbol)
        return list(symbols)
    
    def get_price(self, symbol: str) -> Optional[float]:
        """Get current price for a symbol"""
        with self._price_lock:
            return self.prices.get(symbol.upper())
    
    @staticmethod
    def _fetch_upbit_price_static(symbol: str) -> Optional[float]:
        """
        Fetch current price from Upbit REST API (for one-off queries)
        
        Args:
            symbol: Cryptocurrency symbol (e.g., "BTC", "ETH")
        
        Returns:
            Current price in KRW or None if failed
        """
        import requests
        
        try:
            market = f"KRW-{symbol.upper()}"
            url = f"https://api.upbit.com/v1/ticker?markets={market}"
            
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if data and len(data) > 0:
                return float(data[0].get("trade_price", 0))
            
            return None
        except Exception as e:
            logger.error(f"Error fetching Upbit price for {symbol}: {e}")
            return None


if __name__ == "__main__":
    # Test mode
    from alert_manager import AlertManager
    from notifier import DiscordNotifier
    
    print("Starting crypto monitor in test mode...")
    
    alert_mgr = AlertManager()
    notifier = DiscordNotifier()
    monitor = CryptoMonitor(alert_mgr, notifier)
    
    # Add test alert
    alert_mgr.add_alert("crypto", "BTC", "above", 50000)
    
    try:
        monitor.start()
        print("Monitor running. Press Ctrl+C to stop...")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping monitor...")
        monitor.stop()
