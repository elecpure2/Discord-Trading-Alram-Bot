"""
Channel settings storage for Discord alerts
Stores channel IDs for different alert types
"""

import json
import os
from typing import Dict, Optional

CHANNEL_SETTINGS_FILE = "channel_settings.json"


def load_channel_settings() -> Dict[str, Optional[int]]:
    """Load channel settings from file"""
    if os.path.exists(CHANNEL_SETTINGS_FILE):
        try:
            with open(CHANNEL_SETTINGS_FILE, "r") as f:
                return json.load(f)
        except Exception as e:
            print(f"Error loading channel settings: {e}")
    
    return {
        "crypto": None,
        "whale": None,
        "volume": None,
        "us_stock": None,
        "kr_stock": None
    }


def save_channel_settings(settings: Dict[str, Optional[int]]):
    """Save channel settings to file"""
    try:
        with open(CHANNEL_SETTINGS_FILE, "w") as f:
            json.dump(settings, f, indent=2)
    except Exception as e:
        print(f"Error saving channel settings: {e}")


def set_channel(alert_type: str, channel_id: int):
    """Set channel for specific alert type"""
    settings = load_channel_settings()
    settings[alert_type] = channel_id
    save_channel_settings(settings)


def get_channel(alert_type: str) -> Optional[int]:
    """Get channel ID for specific alert type"""
    settings = load_channel_settings()
    return settings.get(alert_type)


def reset_channel(alert_type: str):
    """Reset channel for specific alert type (use webhook instead)"""
    settings = load_channel_settings()
    settings[alert_type] = None
    save_channel_settings(settings)


def reset_all_channels():
    """Reset all channels (use webhook instead)"""
    settings = {
        "crypto": None,
        "whale": None,
        "volume": None,
        "us_stock": None,
        "kr_stock": None
    }
    save_channel_settings(settings)
