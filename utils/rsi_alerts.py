"""
RSI Alert Storage
Simple JSON storage for RSI alerts
"""

import json
import os
from typing import List, Dict, Optional
from datetime import datetime


RSI_ALERTS_FILE = "rsi_alerts.json"


class RSIAlert:
    """RSI Alert class"""
    
    def __init__(
        self,
        alert_id: str,
        market: str,
        symbol: str,
        timeframe: str,
        condition: str,
        rsi_value: float,
        enabled: bool = True,
        created_at: str = None,
        last_triggered: str = None
    ):
        self.id = alert_id
        self.market = market
        self.symbol = symbol
        self.timeframe = timeframe
        self.condition = condition  # 'above' or 'below'
        self.rsi_value = rsi_value
        self.enabled = enabled
        self.created_at = created_at or datetime.now().isoformat()
        self.last_triggered = last_triggered
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "market": self.market,
            "symbol": self.symbol,
            "timeframe": self.timeframe,
            "condition": self.condition,
            "rsi_value": self.rsi_value,
            "enabled": self.enabled,
            "created_at": self.created_at,
            "last_triggered": self.last_triggered
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "RSIAlert":
        return cls(
            alert_id=data["id"],
            market=data["market"],
            symbol=data["symbol"],
            timeframe=data["timeframe"],
            condition=data["condition"],
            rsi_value=data["rsi_value"],
            enabled=data.get("enabled", True),
            created_at=data.get("created_at"),
            last_triggered=data.get("last_triggered")
        )
    
    def should_trigger(self, current_rsi: float) -> bool:
        """Check if alert should trigger"""
        if not self.enabled:
            return False
        
        if self.condition == "above":
            return current_rsi > self.rsi_value
        else:  # below
            return current_rsi < self.rsi_value
    
    def mark_triggered(self):
        """Mark alert as triggered"""
        self.last_triggered = datetime.now().isoformat()


def load_rsi_alerts() -> List[RSIAlert]:
    """Load RSI alerts from file"""
    if not os.path.exists(RSI_ALERTS_FILE):
        return []
    
    try:
        with open(RSI_ALERTS_FILE, "r") as f:
            data = json.load(f)
            return [RSIAlert.from_dict(a) for a in data.get("alerts", [])]
    except Exception as e:
        print(f"Error loading RSI alerts: {e}")
        return []


def save_rsi_alerts(alerts: List[RSIAlert]):
    """Save RSI alerts to file"""
    try:
        data = {
            "alerts": [alert.to_dict() for alert in alerts],
            "last_updated": datetime.now().isoformat()
        }
        with open(RSI_ALERTS_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception as e:
        print(f"Error saving RSI alerts: {e}")


def add_rsi_alert(market: str, symbol: str, timeframe: str, condition: str, rsi_value: float) -> RSIAlert:
    """Add new RSI alert"""
    import uuid
    
    alert = RSIAlert(
        alert_id=str(uuid.uuid4()),
        market=market,
        symbol=symbol.upper(),
        timeframe=timeframe,
        condition=condition,
        rsi_value=rsi_value
    )
    
    alerts = load_rsi_alerts()
    alerts.append(alert)
    save_rsi_alerts(alerts)
    
    return alert


def remove_rsi_alert(alert_id: str) -> bool:
    """Remove RSI alert"""
    alerts = load_rsi_alerts()
    original_count = len(alerts)
    alerts = [a for a in alerts if a.id != alert_id]
    
    if len(alerts) < original_count:
        save_rsi_alerts(alerts)
        return True
    return False


def get_rsi_alerts(market: str = None, symbol: str = None) -> List[RSIAlert]:
    """Get RSI alerts with optional filters"""
    alerts = load_rsi_alerts()
    
    if market:
        alerts = [a for a in alerts if a.market == market]
    
    if symbol:
        alerts = [a for a in alerts if a.symbol == symbol.upper()]
    
    return alerts
