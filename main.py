"""
Trading Alert Bot - Main Application
Monitors cryptocurrency, US stocks, and Korean stocks for price alerts
"""
import signal
import sys
import time
from typing import List

from alert_manager import AlertManager
from notifier import DiscordNotifier
from monitors.crypto_monitor import CryptoMonitor
from monitors.us_stock_monitor import USStockMonitor
from monitors.kr_stock_monitor import KRStockMonitor
from config import validate_config
from utils.logger import setup_logger

logger = setup_logger(__name__, "main.log")


class TradingAlertBot:
    """Main application class"""
    
    def __init__(self):
        self.alert_manager = AlertManager()
        self.notifier = DiscordNotifier()
        
        # Initialize monitors
        self.crypto_monitor = CryptoMonitor(self.alert_manager, self.notifier)
        self.us_stock_monitor = USStockMonitor(self.alert_manager, self.notifier)
        self.kr_stock_monitor = KRStockMonitor(self.alert_manager, self.notifier)
        
        self.monitors = [
            self.crypto_monitor,
            self.us_stock_monitor,
            self.kr_stock_monitor
        ]
        
        self.running = False
    
    def start(self) -> None:
        """Start the bot"""
        logger.info("=" * 60)
        logger.info("Trading Alert Bot Starting...")
        logger.info("=" * 60)
        
        # Validate configuration
        if not validate_config():
            logger.error("Configuration validation failed!")
            sys.exit(1)
        
        # Display alert statistics
        stats = self.alert_manager.get_stats()
        logger.info(f"Loaded {stats['total']} alerts ({stats['enabled']} enabled)")
        for market, count in stats['by_market'].items():
            logger.info(f"  - {market}: {count} alerts")
        
        # Send startup notification
        self.notifier.send_system_message(
            f"🚀 Trading Alert Bot Started\n"
            f"Monitoring {stats['total']} alerts across {len(stats['by_market'])} markets",
            level="info"
        )
        
        # Start all monitors
        self.running = True
        for monitor in self.monitors:
            try:
                monitor.start()
            except Exception as e:
                logger.error(f"Failed to start monitor {monitor.__class__.__name__}: {e}")
        
        logger.info("All monitors started successfully")
        logger.info("Bot is now running. Press Ctrl+C to stop.")
    
    def stop(self) -> None:
        """Stop the bot gracefully"""
        if not self.running:
            return
        
        logger.info("Stopping Trading Alert Bot...")
        self.running = False
        
        # Stop all monitors
        for monitor in self.monitors:
            try:
                monitor.stop()
            except Exception as e:
                logger.error(f"Error stopping monitor: {e}")
        
        # Send shutdown notification
        self.notifier.send_system_message(
            "🛑 Trading Alert Bot Stopped",
            level="warning"
        )
        
        logger.info("Bot stopped successfully")
    
    def run(self) -> None:
        """Run the bot (blocking)"""
        self.start()
        
        try:
            # Keep main thread alive
            while self.running:
                time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
        finally:
            self.stop()


def signal_handler(signum, frame):
    """Handle shutdown signals"""
    logger.info(f"Received signal {signum}")
    sys.exit(0)


def main():
    """Main entry point"""
    # Register signal handlers for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Create and run bot
    bot = TradingAlertBot()
    bot.run()


if __name__ == "__main__":
    main()
