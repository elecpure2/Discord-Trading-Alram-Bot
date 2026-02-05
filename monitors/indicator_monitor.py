"""
Technical Indicator Monitor
Monitors RSI and divergence for cryptocurrency and stock indices
"""
import time
import threading
from typing import Dict, List, Optional, Literal
from datetime import datetime
from dataclasses import dataclass, field
import requests

from alert_manager import AlertManager
from notifier import DiscordNotifier
from utils.indicators import calculate_rsi, detect_divergence, get_rsi_status, DivergenceType
from utils.logger import setup_logger

logger = setup_logger(__name__, "indicator_monitor.log")

TimeframeType = Literal["1h", "4h", "1d"]


@dataclass
class IndicatorAlert:
    """Represents a technical indicator alert"""
    id: str
    symbol: str
    market: str  # "crypto" or "index"
    indicator: str  # "rsi" or "divergence"
    timeframe: TimeframeType
    condition: Optional[str] = None  # "above" or "below" for RSI level
    threshold: Optional[float] = None  # RSI level threshold
    enabled: bool = True
    created_at: str = field(default_factory=lambda: datetime.now().isoformat())
    last_triggered: Optional[str] = None
    cooldown_seconds: int = 3600  # 1 hour cooldown for indicator alerts
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "symbol": self.symbol,
            "market": self.market,
            "indicator": self.indicator,
            "timeframe": self.timeframe,
            "condition": self.condition,
            "threshold": self.threshold,
            "enabled": self.enabled,
            "created_at": self.created_at,
            "last_triggered": self.last_triggered,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "IndicatorAlert":
        return cls(
            id=data["id"],
            symbol=data["symbol"],
            market=data["market"],
            indicator=data["indicator"],
            timeframe=data["timeframe"],
            condition=data.get("condition"),
            threshold=data.get("threshold"),
            enabled=data.get("enabled", True),
            created_at=data.get("created_at", datetime.now().isoformat()),
            last_triggered=data.get("last_triggered"),
        )


class IndicatorMonitor:
    """Monitor technical indicators for alerts"""
    
    TIMEFRAME_SECONDS = {
        "1h": 3600,
        "4h": 14400,
        "1d": 86400,
    }
    
    BINANCE_INTERVALS = {
        "1h": "1h",
        "4h": "4h", 
        "1d": "1d",
    }
    
    def __init__(self, alert_manager: AlertManager, notifier: DiscordNotifier):
        self.alert_manager = alert_manager
        self.notifier = notifier
        self.running = False
        self.thread: Optional[threading.Thread] = None
        
        # Indicator alerts (separate from price alerts)
        self.indicator_alerts: List[IndicatorAlert] = []
        self._lock = threading.Lock()
        
        # Cache for OHLCV data
        self._price_cache: Dict[str, Dict] = {}
        self._cache_expiry: Dict[str, float] = {}
    
    def add_indicator_alert(
        self,
        symbol: str,
        market: str,
        indicator: str,
        timeframe: TimeframeType,
        condition: Optional[str] = None,
        threshold: Optional[float] = None,
    ) -> IndicatorAlert:
        """Add a new indicator alert"""
        import uuid
        
        alert = IndicatorAlert(
            id=str(uuid.uuid4()),
            symbol=symbol.upper(),
            market=market,
            indicator=indicator,
            timeframe=timeframe,
            condition=condition,
            threshold=threshold,
        )
        
        with self._lock:
            self.indicator_alerts.append(alert)
        
        logger.info(f"Added indicator alert: {alert}")
        return alert
    
    def remove_indicator_alert(self, alert_id: str) -> bool:
        """Remove an indicator alert"""
        with self._lock:
            original_count = len(self.indicator_alerts)
            self.indicator_alerts = [a for a in self.indicator_alerts if not a.id.startswith(alert_id)]
            removed = len(self.indicator_alerts) < original_count
        
        if removed:
            logger.info(f"Removed indicator alert: {alert_id}")
        return removed
    
    def get_indicator_alerts(self) -> List[IndicatorAlert]:
        """Get all indicator alerts"""
        with self._lock:
            return self.indicator_alerts.copy()
    
    def start(self) -> None:
        """Start the indicator monitor"""
        self.running = True
        self.thread = threading.Thread(
            target=self._monitor_loop,
            name="IndicatorMonitor",
            daemon=True
        )
        self.thread.start()
        logger.info("Indicator monitor started")
    
    def stop(self) -> None:
        """Stop the indicator monitor"""
        self.running = False
        logger.info("Indicator monitor stopped")
    
    def _monitor_loop(self) -> None:
        """Main monitoring loop"""
        while self.running:
            try:
                self._check_all_alerts()
            except Exception as e:
                logger.error(f"Error in indicator monitor loop: {e}")
            
            # Check every 5 minutes (indicators don't need real-time updates)
            time.sleep(300)
    
    def _check_all_alerts(self) -> None:
        """Check all indicator alerts"""
        with self._lock:
            alerts = [a for a in self.indicator_alerts if a.enabled]
        
        for alert in alerts:
            try:
                self._check_alert(alert)
            except Exception as e:
                logger.error(f"Error checking alert {alert.id}: {e}")
    
    def _check_alert(self, alert: IndicatorAlert) -> None:
        """Check a single indicator alert"""
        # Check cooldown
        if alert.last_triggered:
            last_trigger = datetime.fromisoformat(alert.last_triggered)
            if (datetime.now() - last_trigger).total_seconds() < alert.cooldown_seconds:
                return
        
        # Get OHLCV data
        ohlcv = self._get_ohlcv(alert.symbol, alert.market, alert.timeframe)
        if not ohlcv or len(ohlcv) < 50:
            logger.warning(f"Not enough data for {alert.symbol} {alert.timeframe}")
            return
        
        closes = [candle["close"] for candle in ohlcv]
        
        # Calculate RSI
        rsi_values = calculate_rsi(closes)
        if not rsi_values:
            return
        
        current_rsi = rsi_values[-1]
        
        if alert.indicator == "rsi" and alert.condition and alert.threshold:
            # RSI level alert
            triggered = False
            if alert.condition == "above" and current_rsi >= alert.threshold:
                triggered = True
            elif alert.condition == "below" and current_rsi <= alert.threshold:
                triggered = True
            
            if triggered:
                self._send_rsi_alert(alert, current_rsi, closes[-1])
                alert.last_triggered = datetime.now().isoformat()
        
        elif alert.indicator == "divergence":
            # Divergence alert
            divergence = detect_divergence(closes, rsi_values)
            
            if divergence and divergence.type != DivergenceType.NONE:
                self._send_divergence_alert(alert, divergence, current_rsi, closes[-1])
                alert.last_triggered = datetime.now().isoformat()
    
    def _get_ohlcv(self, symbol: str, market: str, timeframe: str) -> Optional[List[Dict]]:
        """Get OHLCV data from appropriate source"""
        cache_key = f"{symbol}_{market}_{timeframe}"
        
        # Check cache
        if cache_key in self._price_cache:
            if time.time() < self._cache_expiry.get(cache_key, 0):
                return self._price_cache[cache_key]
        
        # Fetch new data
        if market == "crypto":
            ohlcv = self._fetch_binance_ohlcv(symbol, timeframe)
        else:  # index
            ohlcv = self._fetch_yfinance_ohlcv(symbol, timeframe)
        
        if ohlcv:
            self._price_cache[cache_key] = ohlcv
            # Cache for half the timeframe
            cache_duration = self.TIMEFRAME_SECONDS.get(timeframe, 3600) / 2
            self._cache_expiry[cache_key] = time.time() + cache_duration
        
        return ohlcv
    
    def _fetch_binance_ohlcv(self, symbol: str, timeframe: str) -> Optional[List[Dict]]:
        """Fetch OHLCV data from Binance"""
        try:
            interval = self.BINANCE_INTERVALS.get(timeframe, "4h")
            pair = f"{symbol}USDT"
            url = f"https://api.binance.com/api/v3/klines?symbol={pair}&interval={interval}&limit=100"
            
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            ohlcv = []
            for candle in data:
                ohlcv.append({
                    "timestamp": candle[0],
                    "open": float(candle[1]),
                    "high": float(candle[2]),
                    "low": float(candle[3]),
                    "close": float(candle[4]),
                    "volume": float(candle[5]),
                })
            
            return ohlcv
        except Exception as e:
            logger.error(f"Error fetching Binance OHLCV for {symbol}: {e}")
            return None
    
    def _fetch_yfinance_ohlcv(self, symbol: str, timeframe: str) -> Optional[List[Dict]]:
        """Fetch OHLCV data from yfinance"""
        try:
            import yfinance as yf
            
            # Map symbol to yfinance ticker
            symbol_map = {
                "NASDAQ": "^IXIC",
                "SPX": "^GSPC",
                "SPY": "SPY",
                "QQQ": "QQQ",
            }
            ticker = symbol_map.get(symbol.upper(), symbol)
            
            # Map timeframe to yfinance period/interval
            period_map = {
                "1h": ("5d", "1h"),
                "4h": ("1mo", "1h"),  # yfinance doesn't have 4h, we'll resample
                "1d": ("3mo", "1d"),
            }
            period, interval = period_map.get(timeframe, ("1mo", "1d"))
            
            stock = yf.Ticker(ticker)
            df = stock.history(period=period, interval=interval)
            
            if df.empty:
                return None
            
            # Resample to 4h if needed
            if timeframe == "4h" and interval == "1h":
                df = df.resample("4H").agg({
                    "Open": "first",
                    "High": "max",
                    "Low": "min",
                    "Close": "last",
                    "Volume": "sum"
                }).dropna()
            
            ohlcv = []
            for idx, row in df.iterrows():
                ohlcv.append({
                    "timestamp": int(idx.timestamp() * 1000),
                    "open": float(row.get("Open", row.get("open", 0))),
                    "high": float(row.get("High", row.get("high", 0))),
                    "low": float(row.get("Low", row.get("low", 0))),
                    "close": float(row.get("Close", row.get("close", 0))),
                    "volume": float(row.get("Volume", row.get("volume", 0))),
                })
            
            return ohlcv
        except Exception as e:
            logger.error(f"Error fetching yfinance OHLCV for {symbol}: {e}")
            return None
    
    def _send_rsi_alert(self, alert: IndicatorAlert, rsi: float, price: float) -> None:
        """Send RSI level alert"""
        condition_text = "이상" if alert.condition == "above" else "이하"
        status = get_rsi_status(rsi)
        
        message = (
            f"📊 **RSI 알람 트리거**\n\n"
            f"**심볼**: {alert.symbol}\n"
            f"**타임프레임**: {alert.timeframe}\n"
            f"**현재 RSI**: {rsi:.1f} ({status})\n"
            f"**조건**: RSI {alert.threshold} {condition_text}\n"
            f"**현재가**: ${price:,.2f}"
        )
        
        self.notifier.send_system_message(message, level="warning")
        logger.info(f"RSI alert sent: {alert.symbol} RSI={rsi:.1f}")
    
    def _send_divergence_alert(
        self, 
        alert: IndicatorAlert, 
        divergence, 
        current_rsi: float, 
        current_price: float
    ) -> None:
        """Send divergence alert"""
        message = (
            f"📈 **다이버전스 감지!**\n\n"
            f"**심볼**: {alert.symbol}\n"
            f"**타임프레임**: {alert.timeframe}\n"
            f"**타입**: {divergence}\n"
            f"**강도**: {divergence.strength:.0%}\n"
            f"**현재 RSI**: {current_rsi:.1f}\n"
            f"**현재가**: ${current_price:,.2f}\n\n"
            f"⚠️ 다이버전스는 추세 반전 신호일 수 있습니다. 다른 지표와 함께 확인하세요."
        )
        
        self.notifier.send_system_message(message, level="warning")
        logger.info(f"Divergence alert sent: {alert.symbol} {divergence.type}")
    
    def get_current_rsi(self, symbol: str, market: str, timeframe: str) -> Optional[Dict]:
        """Get current RSI value for a symbol (for Discord command)"""
        ohlcv = self._get_ohlcv(symbol, market, timeframe)
        if not ohlcv or len(ohlcv) < 20:
            return None
        
        closes = [candle["close"] for candle in ohlcv]
        rsi_values = calculate_rsi(closes)
        
        if not rsi_values:
            return None
        
        current_rsi = rsi_values[-1]
        current_price = closes[-1]
        
        # Check for divergence
        divergence = detect_divergence(closes, rsi_values)
        
        return {
            "symbol": symbol,
            "timeframe": timeframe,
            "rsi": current_rsi,
            "status": get_rsi_status(current_rsi),
            "price": current_price,
            "divergence": divergence,
        }


# Global instance for Discord bot access
_indicator_monitor: Optional[IndicatorMonitor] = None


def get_indicator_monitor() -> Optional[IndicatorMonitor]:
    """Get the global indicator monitor instance"""
    return _indicator_monitor


def set_indicator_monitor(monitor: IndicatorMonitor) -> None:
    """Set the global indicator monitor instance"""
    global _indicator_monitor
    _indicator_monitor = monitor
