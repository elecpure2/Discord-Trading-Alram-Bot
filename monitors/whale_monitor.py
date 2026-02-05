"""
Multi-Exchange Whale Alert Monitor
Monitors large trades on Binance, OKX, Bybit, and Upbit
"""
import json
import time
import threading
import os
from typing import Optional, Set, Dict
from datetime import datetime
from dataclasses import dataclass
import websocket

from notifier import DiscordNotifier
from utils.logger import setup_logger

logger = setup_logger(__name__, "whale_monitor.log")

# Default thresholds in USD
DEFAULT_WHALE_THRESHOLD_BTC = 1_000_000  # $1M for BTC
DEFAULT_WHALE_THRESHOLD_ETH = 500_000   # $500K for ETH

# Settings file path
WHALE_SETTINGS_FILE = os.path.join(os.path.dirname(__file__), "..", "whale_settings.json")


@dataclass
class WhaleTradeInfo:
    """Information about a whale trade"""
    exchange: str
    symbol: str
    side: str  # "BUY" or "SELL"
    price: float
    quantity: float
    value_usd: float
    timestamp: datetime
    
    def __str__(self) -> str:
        side_emoji = "🟢" if self.side == "BUY" else "🔴"
        return f"[{self.exchange}] {side_emoji} {self.symbol}: {self.quantity:.4f} @ ${self.price:,.2f} = ${self.value_usd:,.0f}"


class ExchangeMonitor:
    """Base class for exchange-specific monitors"""
    
    def __init__(self, exchange_name: str, callback):
        self.exchange_name = exchange_name
        self.callback = callback
        self.running = False
        self.ws = None
        self.thread = None
    
    def start(self):
        if self.running:
            return
        self.running = True
        self.thread = threading.Thread(
            target=self._run,
            name=f"Whale-{self.exchange_name}",
            daemon=True
        )
        self.thread.start()
        logger.info(f"{self.exchange_name} whale monitor started")
    
    def stop(self):
        self.running = False
        if self.ws:
            self.ws.close()
    
    def _run(self):
        while self.running:
            try:
                self._connect()
            except Exception as e:
                logger.error(f"{self.exchange_name} error: {e}")
                if self.running:
                    time.sleep(5)
    
    def _connect(self):
        raise NotImplementedError


class BinanceMonitor(ExchangeMonitor):
    """Binance WebSocket Monitor"""
    
    def __init__(self, symbols: Set[str], callback):
        super().__init__("Binance", callback)
        self.symbols = symbols
    
    def _connect(self):
        streams = "/".join([f"{s.lower()}usdt@aggTrade" for s in self.symbols])
        ws_url = f"wss://stream.binance.com:9443/stream?streams={streams}"
        
        def on_message(ws, message):
            try:
                data = json.loads(message)
                if "data" in data:
                    self._handle_trade(data["data"])
            except Exception as e:
                logger.error(f"Binance parse error: {e}")
        
        self.ws = websocket.WebSocketApp(
            ws_url,
            on_message=on_message,
            on_error=lambda ws, e: logger.error(f"Binance WS error: {e}"),
            on_close=lambda ws, c, m: logger.info("Binance WS closed"),
            on_open=lambda ws: logger.info(f"Binance WS connected")
        )
        self.ws.run_forever()
    
    def _handle_trade(self, data: dict):
        symbol = data.get("s", "").replace("USDT", "")
        price = float(data.get("p", 0))
        quantity = float(data.get("q", 0))
        is_buyer_maker = data.get("m", False)
        
        trade = WhaleTradeInfo(
            exchange="Binance",
            symbol=symbol,
            side="SELL" if is_buyer_maker else "BUY",
            price=price,
            quantity=quantity,
            value_usd=price * quantity,
            timestamp=datetime.now()
        )
        self.callback(trade)


class OKXMonitor(ExchangeMonitor):
    """OKX WebSocket Monitor"""
    
    def __init__(self, symbols: Set[str], callback):
        super().__init__("OKX", callback)
        self.symbols = symbols
    
    def _connect(self):
        ws_url = "wss://ws.okx.com:8443/ws/v5/public"
        
        def on_message(ws, message):
            try:
                data = json.loads(message)
                if "data" in data:
                    for trade in data["data"]:
                        self._handle_trade(trade)
            except Exception as e:
                logger.error(f"OKX parse error: {e}")
        
        def on_open(ws):
            logger.info("OKX WS connected")
            # Subscribe to trades
            for symbol in self.symbols:
                sub_msg = {
                    "op": "subscribe",
                    "args": [{"channel": "trades", "instId": f"{symbol}-USDT"}]
                }
                ws.send(json.dumps(sub_msg))
        
        self.ws = websocket.WebSocketApp(
            ws_url,
            on_message=on_message,
            on_error=lambda ws, e: logger.error(f"OKX WS error: {e}"),
            on_close=lambda ws, c, m: logger.info("OKX WS closed"),
            on_open=on_open
        )
        self.ws.run_forever()
    
    def _handle_trade(self, data: dict):
        inst_id = data.get("instId", "")
        symbol = inst_id.split("-")[0] if inst_id else ""
        price = float(data.get("px", 0))
        quantity = float(data.get("sz", 0))
        side = data.get("side", "").upper()
        
        trade = WhaleTradeInfo(
            exchange="OKX",
            symbol=symbol,
            side=side if side in ["BUY", "SELL"] else "BUY",
            price=price,
            quantity=quantity,
            value_usd=price * quantity,
            timestamp=datetime.now()
        )
        self.callback(trade)


class BybitMonitor(ExchangeMonitor):
    """Bybit WebSocket Monitor"""
    
    def __init__(self, symbols: Set[str], callback):
        super().__init__("Bybit", callback)
        self.symbols = symbols
    
    def _connect(self):
        ws_url = "wss://stream.bybit.com/v5/public/spot"
        
        def on_message(ws, message):
            try:
                data = json.loads(message)
                if data.get("topic", "").startswith("publicTrade"):
                    for trade in data.get("data", []):
                        self._handle_trade(trade)
            except Exception as e:
                logger.error(f"Bybit parse error: {e}")
        
        def on_open(ws):
            logger.info("Bybit WS connected")
            # Subscribe to trades
            args = [f"publicTrade.{s}USDT" for s in self.symbols]
            sub_msg = {"op": "subscribe", "args": args}
            ws.send(json.dumps(sub_msg))
        
        self.ws = websocket.WebSocketApp(
            ws_url,
            on_message=on_message,
            on_error=lambda ws, e: logger.error(f"Bybit WS error: {e}"),
            on_close=lambda ws, c, m: logger.info("Bybit WS closed"),
            on_open=on_open
        )
        self.ws.run_forever()
    
    def _handle_trade(self, data: dict):
        symbol_pair = data.get("s", "")
        symbol = symbol_pair.replace("USDT", "")
        price = float(data.get("p", 0))
        quantity = float(data.get("v", 0))
        side = data.get("S", "").upper()
        
        trade = WhaleTradeInfo(
            exchange="Bybit",
            symbol=symbol,
            side="BUY" if side == "BUY" else "SELL",
            price=price,
            quantity=quantity,
            value_usd=price * quantity,
            timestamp=datetime.now()
        )
        self.callback(trade)


class UpbitMonitor(ExchangeMonitor):
    """Upbit WebSocket Monitor (KRW market)"""
    
    def __init__(self, symbols: Set[str], callback):
        super().__init__("Upbit", callback)
        self.symbols = symbols
        self.krw_rate = 1350  # Approximate KRW/USD rate
    
    def _connect(self):
        ws_url = "wss://api.upbit.com/websocket/v1"
        
        def on_message(ws, message):
            try:
                data = json.loads(message)
                if data.get("type") == "trade":
                    self._handle_trade(data)
            except Exception as e:
                logger.error(f"Upbit parse error: {e}")
        
        def on_open(ws):
            logger.info("Upbit WS connected")
            # Subscribe to trades
            codes = [f"KRW-{s}" for s in self.symbols]
            sub_msg = [
                {"ticket": "whale-monitor"},
                {"type": "trade", "codes": codes}
            ]
            ws.send(json.dumps(sub_msg))
        
        self.ws = websocket.WebSocketApp(
            ws_url,
            on_message=on_message,
            on_error=lambda ws, e: logger.error(f"Upbit WS error: {e}"),
            on_close=lambda ws, c, m: logger.info("Upbit WS closed"),
            on_open=on_open
        )
        self.ws.run_forever()
    
    def _handle_trade(self, data: dict):
        code = data.get("code", "")
        symbol = code.replace("KRW-", "")
        price_krw = float(data.get("trade_price", 0))
        quantity = float(data.get("trade_volume", 0))
        ask_bid = data.get("ask_bid", "")
        
        # Convert KRW to USD
        price_usd = price_krw / self.krw_rate
        value_usd = price_usd * quantity
        
        trade = WhaleTradeInfo(
            exchange="Upbit",
            symbol=symbol,
            side="BUY" if ask_bid == "BID" else "SELL",
            price=price_usd,
            quantity=quantity,
            value_usd=value_usd,
            timestamp=datetime.now()
        )
        self.callback(trade)


class WhaleMonitor:
    """Multi-exchange whale monitor"""
    
    def __init__(self, notifier: DiscordNotifier):
        self.notifier = notifier
        self.running = False
        
        # Thresholds per symbol (in USD)
        self.thresholds = {
            "BTC": DEFAULT_WHALE_THRESHOLD_BTC,
            "ETH": DEFAULT_WHALE_THRESHOLD_ETH,
        }
        
        # Symbols to monitor
        self.symbols: Set[str] = {"BTC", "ETH"}
        
        # Enabled exchanges
        self.exchanges: Dict[str, bool] = {
            "Binance": True,
            "OKX": True,
            "Bybit": True,
            "Upbit": True,
        }
        
        # Enabled state
        self.enabled = False
        
        # Exchange monitors
        self.monitors: Dict[str, ExchangeMonitor] = {}
        
        # Load saved settings
        self._load_settings()
    
    def _load_settings(self) -> None:
        """Load settings from file"""
        try:
            if os.path.exists(WHALE_SETTINGS_FILE):
                with open(WHALE_SETTINGS_FILE, "r") as f:
                    settings = json.load(f)
                    self.thresholds = settings.get("thresholds", self.thresholds)
                    self.enabled = settings.get("enabled", False)
                    self.exchanges = settings.get("exchanges", self.exchanges)
                    logger.info(f"Loaded whale settings: enabled={self.enabled}")
        except Exception as e:
            logger.error(f"Failed to load whale settings: {e}")
    
    def _save_settings(self) -> None:
        """Save settings to file"""
        try:
            settings = {
                "thresholds": self.thresholds,
                "enabled": self.enabled,
                "exchanges": self.exchanges,
            }
            with open(WHALE_SETTINGS_FILE, "w") as f:
                json.dump(settings, f, indent=2)
            logger.info("Whale settings saved")
        except Exception as e:
            logger.error(f"Failed to save whale settings: {e}")
    
    def set_threshold(self, symbol: str, threshold_usd: float) -> None:
        """Set whale threshold for a symbol"""
        self.thresholds[symbol.upper()] = threshold_usd
        self._save_settings()
        logger.info(f"Whale threshold for {symbol} set to ${threshold_usd:,.0f}")
    
    def get_threshold(self, symbol: str) -> float:
        """Get whale threshold for a symbol"""
        return self.thresholds.get(symbol.upper(), DEFAULT_WHALE_THRESHOLD_BTC)
    
    def toggle_exchange(self, exchange: str, enabled: bool) -> None:
        """Enable or disable an exchange"""
        if exchange in self.exchanges:
            self.exchanges[exchange] = enabled
            self._save_settings()
            logger.info(f"Exchange {exchange} {'enabled' if enabled else 'disabled'}")
    
    def enable(self) -> None:
        """Enable whale monitoring"""
        self.enabled = True
        self._save_settings()
        if not self.running:
            self.start()
        logger.info("Whale monitoring enabled")
    
    def disable(self) -> None:
        """Disable whale monitoring"""
        self.enabled = False
        self._save_settings()
        logger.info("Whale monitoring disabled")
    
    def start(self) -> None:
        """Start all exchange monitors"""
        if self.running:
            return
        
        self.running = True
        
        # Create and start monitors for enabled exchanges
        if self.exchanges.get("Binance", True):
            self.monitors["Binance"] = BinanceMonitor(self.symbols, self._handle_trade)
            self.monitors["Binance"].start()
        
        if self.exchanges.get("OKX", True):
            self.monitors["OKX"] = OKXMonitor(self.symbols, self._handle_trade)
            self.monitors["OKX"].start()
        
        if self.exchanges.get("Bybit", True):
            self.monitors["Bybit"] = BybitMonitor(self.symbols, self._handle_trade)
            self.monitors["Bybit"].start()
        
        if self.exchanges.get("Upbit", True):
            self.monitors["Upbit"] = UpbitMonitor(self.symbols, self._handle_trade)
            self.monitors["Upbit"].start()
        
        logger.info(f"Whale monitor started with exchanges: {list(self.monitors.keys())}")
    
    def stop(self) -> None:
        """Stop all exchange monitors"""
        self.running = False
        for monitor in self.monitors.values():
            monitor.stop()
        self.monitors.clear()
        logger.info("Whale monitor stopped")
    
    def _handle_trade(self, trade: WhaleTradeInfo) -> None:
        """Handle incoming trade from any exchange"""
        if not self.enabled:
            return
        
        if trade.symbol not in self.symbols:
            return
        
        threshold = self.thresholds.get(trade.symbol, DEFAULT_WHALE_THRESHOLD_BTC)
        
        if trade.value_usd < threshold:
            return
        
        # Send alert
        self._send_whale_alert(trade)
    
    def _send_whale_alert(self, trade: WhaleTradeInfo) -> None:
        """Send whale trade alert to Discord"""
        side_emoji = "🟢 매수" if trade.side == "BUY" else "🔴 매도"
        
        # Format value
        if trade.value_usd >= 1_000_000_000:
            value_str = f"${trade.value_usd/1_000_000_000:.2f}B"
            value_krw = f"약 {trade.value_usd * 1350 / 1_000_000_000:.1f}조원"
        elif trade.value_usd >= 1_000_000:
            value_str = f"${trade.value_usd/1_000_000:.2f}M"
            value_krw = f"약 {trade.value_usd * 1350 / 100_000_000:.0f}억원"
        else:
            value_str = f"${trade.value_usd:,.0f}"
            value_krw = f"약 {trade.value_usd * 1350 / 100_000_000:.1f}억원"
        
        message = (
            f"🐋 **고래 발견!** [{trade.exchange}] 🐋\n\n"
            f"**{trade.symbol}/USDT** {side_emoji}\n"
            f"━━━━━━━━━━━━━━━━\n"
            f"💰 거래 금액: **{value_str}** ({value_krw})\n"
            f"📊 수량: {trade.quantity:,.4f} {trade.symbol}\n"
            f"💵 체결가: ${trade.price:,.2f}\n"
            f"⏰ 시간: {trade.timestamp.strftime('%H:%M:%S')}"
        )
        
        self.notifier.send_whale_alert(message)
        logger.info(f"Whale alert sent: {trade}")
    
    def get_status(self) -> dict:
        """Get whale monitor status"""
        return {
            "enabled": self.enabled,
            "running": self.running,
            "symbols": list(self.symbols),
            "thresholds": {s: f"${v:,.0f}" for s, v in self.thresholds.items()},
            "exchanges": self.exchanges,
            "active_monitors": list(self.monitors.keys()),
        }


# Global instance
_whale_monitor: Optional[WhaleMonitor] = None


def get_whale_monitor() -> Optional[WhaleMonitor]:
    """Get the global whale monitor instance"""
    return _whale_monitor


def set_whale_monitor(monitor: WhaleMonitor) -> None:
    """Set the global whale monitor instance"""
    global _whale_monitor
    _whale_monitor = monitor


if __name__ == "__main__":
    from notifier import DiscordNotifier
    
    print("Starting whale monitor in test mode...")
    notifier = DiscordNotifier()
    monitor = WhaleMonitor(notifier)
    monitor.enable()
    
    try:
        print("Monitoring for whale trades. Press Ctrl+C to stop...")
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nStopping...")
        monitor.stop()
