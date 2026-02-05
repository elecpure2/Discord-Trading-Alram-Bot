"""
Alert management system for Trading Alert Bot
"""
import json
import uuid
from typing import List, Dict, Optional, Literal
from datetime import datetime
from pathlib import Path
from threading import Lock

from config import ALERTS_FILE, ALERT_COOLDOWN_SECONDS, MAX_ALERTS_PER_SYMBOL
from utils.logger import setup_logger

logger = setup_logger(__name__, "alert_manager.log")

MarketType = Literal["crypto", "us_stock", "kr_stock"]
ConditionType = Literal["above", "below"]


class Alert:
    """Represents a single price alert"""
    
    def __init__(
        self,
        market: MarketType,
        symbol: str,
        condition: ConditionType,
        price: float,
        alert_id: Optional[str] = None,
        enabled: bool = True,
        created_at: Optional[str] = None,
        last_triggered: Optional[str] = None
    ):
        self.id = alert_id or str(uuid.uuid4())
        self.market = market
        self.symbol = symbol.upper()
        self.condition = condition
        self.price = float(price)
        self.enabled = enabled
        self.created_at = created_at or datetime.now().isoformat()
        self.last_triggered = last_triggered
    
    def to_dict(self) -> Dict:
        """Convert alert to dictionary"""
        return {
            "id": self.id,
            "market": self.market,
            "symbol": self.symbol,
            "condition": self.condition,
            "price": self.price,
            "enabled": self.enabled,
            "created_at": self.created_at,
            "last_triggered": self.last_triggered,
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Alert":
        """Create alert from dictionary"""
        return cls(
            alert_id=data["id"],
            market=data["market"],
            symbol=data["symbol"],
            condition=data["condition"],
            price=data["price"],
            enabled=data.get("enabled", True),
            created_at=data.get("created_at"),
            last_triggered=data.get("last_triggered"),
        )
    
    def should_trigger(self, current_price: float) -> bool:
        """Check if alert should trigger based on current price"""
        if not self.enabled:
            return False
        
        # Check cooldown
        if self.last_triggered:
            last_trigger_time = datetime.fromisoformat(self.last_triggered)
            time_since_trigger = (datetime.now() - last_trigger_time).total_seconds()
            if time_since_trigger < ALERT_COOLDOWN_SECONDS:
                return False
        
        # Check condition
        if self.condition == "above":
            return current_price >= self.price
        elif self.condition == "below":
            return current_price <= self.price
        
        return False
    
    def mark_triggered(self) -> None:
        """Mark alert as triggered"""
        self.last_triggered = datetime.now().isoformat()
    
    def __repr__(self) -> str:
        return f"Alert({self.symbol} {self.condition} {self.price})"


class AlertManager:
    """Manages all trading alerts"""
    
    def __init__(self, alerts_file: Path = ALERTS_FILE):
        self.alerts_file = alerts_file
        self.alerts: List[Alert] = []
        self._lock = Lock()
        self._load_alerts()
    
    def _load_alerts(self) -> None:
        """Load alerts from JSON file"""
        if not self.alerts_file.exists():
            logger.info("No existing alerts file, starting fresh")
            self._save_alerts()
            return
        
        try:
            with open(self.alerts_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                self.alerts = [Alert.from_dict(a) for a in data.get("alerts", [])]
            logger.info(f"Loaded {len(self.alerts)} alerts from file")
        except Exception as e:
            logger.error(f"Failed to load alerts: {e}")
            self.alerts = []
    
    def _save_alerts(self) -> None:
        """Save alerts to JSON file"""
        try:
            data = {
                "alerts": [alert.to_dict() for alert in self.alerts],
                "last_updated": datetime.now().isoformat(),
            }
            with open(self.alerts_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            logger.debug(f"Saved {len(self.alerts)} alerts to file")
        except Exception as e:
            logger.error(f"Failed to save alerts: {e}")
    
    def add_alert(
        self,
        market: MarketType,
        symbol: str,
        condition: ConditionType,
        price: float
    ) -> Optional[Alert]:
        """
        Add a new alert
        
        Args:
            market: Market type
            symbol: Trading symbol
            condition: Alert condition (above/below)
            price: Target price
        
        Returns:
            Created alert or None if failed
        """
        with self._lock:
            # Check if we've hit the limit for this symbol
            symbol_alerts = [a for a in self.alerts if a.symbol == symbol.upper()]
            if len(symbol_alerts) >= MAX_ALERTS_PER_SYMBOL:
                logger.warning(
                    f"Maximum alerts ({MAX_ALERTS_PER_SYMBOL}) reached for {symbol}"
                )
                return None
            
            alert = Alert(market, symbol, condition, price)
            self.alerts.append(alert)
            self._save_alerts()
            
            logger.info(f"Added alert: {alert}")
            return alert
    
    def remove_alert(self, alert_id: str) -> bool:
        """Remove an alert by ID"""
        with self._lock:
            original_count = len(self.alerts)
            self.alerts = [a for a in self.alerts if a.id != alert_id]
            
            if len(self.alerts) < original_count:
                self._save_alerts()
                logger.info(f"Removed alert: {alert_id}")
                return True
            
            logger.warning(f"Alert not found: {alert_id}")
            return False
    
    def get_alerts(
        self,
        market: Optional[MarketType] = None,
        symbol: Optional[str] = None,
        enabled_only: bool = False
    ) -> List[Alert]:
        """
        Get alerts with optional filtering
        
        Args:
            market: Filter by market type
            symbol: Filter by symbol
            enabled_only: Only return enabled alerts
        
        Returns:
            List of matching alerts
        """
        with self._lock:
            filtered = self.alerts.copy()
            
            if market:
                filtered = [a for a in filtered if a.market == market]
            
            if symbol:
                filtered = [a for a in filtered if a.symbol == symbol.upper()]
            
            if enabled_only:
                filtered = [a for a in filtered if a.enabled]
            
            return filtered
    
    def enable_alert(self, alert_id: str) -> bool:
        """Enable an alert"""
        return self._set_alert_enabled(alert_id, True)
    
    def disable_alert(self, alert_id: str) -> bool:
        """Disable an alert"""
        return self._set_alert_enabled(alert_id, False)
    
    def _set_alert_enabled(self, alert_id: str, enabled: bool) -> bool:
        """Set alert enabled status"""
        with self._lock:
            for alert in self.alerts:
                if alert.id == alert_id:
                    alert.enabled = enabled
                    self._save_alerts()
                    logger.info(f"Alert {alert_id} {'enabled' if enabled else 'disabled'}")
                    return True
            
            logger.warning(f"Alert not found: {alert_id}")
            return False
    
    def mark_triggered(self, alert_id: str) -> bool:
        """Mark an alert as triggered"""
        with self._lock:
            for alert in self.alerts:
                if alert.id == alert_id:
                    alert.mark_triggered()
                    self._save_alerts()
                    logger.info(f"Alert {alert_id} marked as triggered")
                    return True
            
            return False
    
    def check_price(self, market: MarketType, symbol: str, current_price: float) -> List[Alert]:
        """
        Check if any alerts should trigger for given price
        
        Args:
            market: Market type
            symbol: Trading symbol
            current_price: Current price to check
        
        Returns:
            List of alerts that should trigger
        """
        triggered_alerts = []
        
        with self._lock:
            for alert in self.alerts:
                if (alert.market == market and 
                    alert.symbol == symbol.upper() and 
                    alert.should_trigger(current_price)):
                    triggered_alerts.append(alert)
        
        return triggered_alerts
    
    def get_stats(self) -> Dict:
        """Get alert statistics"""
        with self._lock:
            total = len(self.alerts)
            enabled = len([a for a in self.alerts if a.enabled])
            by_market = {}
            
            for alert in self.alerts:
                by_market[alert.market] = by_market.get(alert.market, 0) + 1
            
            return {
                "total": total,
                "enabled": enabled,
                "disabled": total - enabled,
                "by_market": by_market,
            }
