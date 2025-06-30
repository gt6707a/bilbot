import os
import time
import pandas as pd
import pytz
import holidays
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('bilbot')

# Import our Polygon-based trading bot
from polygon_trading_bot import PolygonTradingBot

# Configuration
CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', 60))  # Seconds
SYMBOL = "SPY"  # Low-cost, liquid ETF

nyse = pytz.timezone('America/New_York')

# Initialize the Polygon-based trading bot with required parameters
trading_bot = PolygonTradingBot(
    symbol=SYMBOL,
    interval_minutes=5,  # Recalculate signal every 5 minutes
    paper=True           # Use paper trading
)

def market_is_open():
    """Check if market is open using NYSE hours and holidays"""
    now = pd.Timestamp.now(tz=nyse)
    if now.date() in holidays.NYSE():
        return False
    if now.weekday() >= 5:  # Saturday(5) or Sunday(6)
        return False
    market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = now.replace(hour=16, minute=0, second=0, microsecond=0)
    return market_open <= now <= market_close

if __name__ == "__main__":
    logger.info(f"Polygon Trading Bot starting at {pd.Timestamp.now(tz=nyse)}")
    logger.info(f"Symbol: {SYMBOL}")

    # Set initial equity
    logger.info(f"💰 Initial equity: ${trading_bot.get_current_equity():.2f}")
    
    trading_active = True
    
    # Monitor market and trade until market closes or limits reached
    while trading_active:
        # Check if market is open - bot's responsibility
        if not market_is_open():
            logger.info(f"Market is closed at {datetime.now(tz=nyse)}")
            # Exit all positions as a safety measure before terminating
            trading_bot.exit_all_positions()
            # Break out of the loop which will end the program
            break
            
        # Check risk limits - bot's responsibility
        pnl = trading_bot.calculate_pnl()
        if pnl <= -trading_bot.daily_pnl_threshold or pnl >= trading_bot.daily_gain_target:
            logger.info(f"Daily P&L limit reached: {pnl*100:.2f}%")
            trading_bot.exit_all_positions()
            trading_active = False
            break
        
        # Let the algorithm run its trading logic
        try:
            trading_bot.run()
        except Exception as e:
            logger.info(f"Error in trading cycle: {str(e)}")
            # Handle reconnection if needed
            if isinstance(e, OSError) and getattr(e, 'errno', None) == 9:  # Bad file descriptor
                logger.info("Recreating Alpaca clients due to connection error...")
                trading_bot.reconnect()
        
        time.sleep(CHECK_INTERVAL)
    
    # Clean up at end of day
    trading_bot.exit_all_positions()
    
    logger.info(f"Trading day complete at {pd.Timestamp.now(tz=nyse)}")
    final_pnl = trading_bot.calculate_pnl()
    logger.info(f"Daily P&L: {final_pnl*100:.2f}%")
