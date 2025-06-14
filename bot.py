import os
import time
import pandas as pd
import pytz
import holidays
from datetime import datetime

# Import our algorithm
from algos.smaEmaCrossoverAlgorithm import SmaEmaCrossoverAlgorithm

# Configuration
CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', 60))  # Seconds
SYMBOL = "SPY"  # Low-cost, liquid ETF
EMA_PERIOD = 9   # Fast EMA
SMA_PERIOD = 21  # Slow SMA

nyse = pytz.timezone('America/New_York')

# Initialize the algorithm with required parameters (no API credentials)
trading_algorithm = SmaEmaCrossoverAlgorithm(
    symbol=SYMBOL,
    ema_period=EMA_PERIOD,
    sma_period=SMA_PERIOD,
    interval_minutes=5,  # Recalculate signal every 5 minutes
    position_size=1,     # Trade 1 share at a time
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
    print(f"Bot starting at {pd.Timestamp.now(tz=nyse)}")
    
    trading_active = True
    
    # Monitor market and trade until market closes or limits reached
    while trading_active:
        # Check if market is open - bot's responsibility
        if not market_is_open():
            print(f"Market is closed at {datetime.now(tz=nyse)}")
            print("Market is closed. Terminating the process.")
            # Exit all positions as a safety measure before terminating
            trading_algorithm.exit_all_positions()
            # Break out of the loop which will end the program
            break
            
        # Check risk limits - bot's responsibility
        pnl = trading_algorithm.calculate_pnl()
        if pnl <= -trading_algorithm.daily_pnl_threshold or pnl >= trading_algorithm.daily_gain_target:
            print(f"Daily P&L limit reached: {pnl*100:.2f}%")
            trading_algorithm.exit_all_positions()
            trading_active = False
            break
        
        # Let the algorithm run its trading logic
        try:
            trading_algorithm.run()
        except Exception as e:
            print(f"Error in trading cycle: {str(e)}")
            # Handle reconnection if needed
            if isinstance(e, OSError) and getattr(e, 'errno', None) == 9:  # Bad file descriptor
                print("Recreating Alpaca clients due to connection error...")
                trading_algorithm.reconnect()
        
        time.sleep(CHECK_INTERVAL)
    
    # Clean up at end of day
    trading_algorithm.exit_all_positions()
    
    print(f"Trading day complete at {pd.Timestamp.now(tz=nyse)}")
    final_pnl = trading_algorithm.calculate_pnl()
    print(f"Daily P&L: {final_pnl*100:.2f}%")
