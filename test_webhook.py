"""
Test script for Discord webhook integration
"""
from notifier import DiscordNotifier
from utils.logger import setup_logger

logger = setup_logger(__name__)


def main():
    print("=" * 60)
    print("Discord Webhook Test")
    print("=" * 60)
    
    notifier = DiscordNotifier()
    
    # Test each market webhook
    markets = ["crypto", "us_stock", "kr_stock"]
    
    for market in markets:
        print(f"\nTesting {market} webhook...")
        success = notifier.send_test_message(market)
        
        if success:
            print(f"✅ {market} webhook working!")
        else:
            print(f"❌ {market} webhook failed!")
    
    # Test alert notification
    print("\nTesting alert notification (crypto)...")
    success = notifier.send_alert(
        market="crypto",
        symbol="BTC/USDT",
        current_price=51234.56,
        target_price=50000.00,
        condition="above",
        additional_info={"Exchange": "Binance"}
    )
    
    if success:
        print("✅ Alert notification sent!")
    else:
        print("❌ Alert notification failed!")
    
    print("\n" + "=" * 60)
    print("Test completed!")
    print("=" * 60)


if __name__ == "__main__":
    main()
