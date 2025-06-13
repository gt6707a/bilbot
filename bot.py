import os
import time
import pandas as pd
import pytz
import holidays
from alpaca.trading.client import TradingClient
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.data.timeframe import TimeFrame, TimeFrameUnit

# Import our algorithm
from algos.smaEmaCrossoverAlgo import SmaEmaCrossoverAlgo

# Configuration
API_KEY = os.getenv('ALPACA_KEY')
API_SECRET = os.getenv('ALPACA_SECRET')
CHECK_INTERVAL = int(os.getenv('CHECK_INTERVAL', 60))  # Seconds
SYMBOL = "SPY"  # Low-cost, liquid ETF
EMA_PERIOD = 9   # Fast EMA
SMA_PERIOD = 21  # Slow SMA

trading_client = TradingClient(API_KEY, API_SECRET, paper=True)
stock_historical_client = StockHistoricalDataClient(API_KEY, API_SECRET)

nyse = pytz.timezone('America/New_York')
daily_pnl_threshold = 0.0025  # 0.25% daily loss limit
daily_gain_target = 0.01       # 1% daily gain target

# Initialize the algorithm
trading_algorithm = SmaEmaCrossoverAlgo(EMA_PERIOD, SMA_PERIOD)

# Track daily performance - initialized at script start
initial_equity = None
trading_active = True

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

def calculate_pnl():
    """Calculate daily P&L percentage"""
    global initial_equity
    account = trading_client.get_account()
    current_equity = float(account.equity)
    
    # Set initial equity at market open
    if initial_equity is None:
        initial_equity = current_equity
        return 0.0
        
    return (current_equity - initial_equity) / initial_equity

def get_positions():
    """Get current positions as {symbol: qty}"""
    return {p.symbol: float(p.qty) for p in trading_client.get_all_positions()}

def exit_all_positions():
    """Liquidate all positions"""
    trading_client.close_all_positions(cancel_orders=True)
    print("Closed all positions")

def run_trading_cycle():
    global trading_active, trading_client, stock_historical_client
    
    # Skip if market is closed
    if not market_is_open():
        print("Market is closed. Exiting.")
        return False

    try:
        # Check daily P&L limits
        pnl = calculate_pnl()
        if pnl <= -daily_pnl_threshold or pnl >= daily_gain_target:
            print(f"Daily P&L limit reached: {pnl*100:.2f}%")
            exit_all_positions()
            trading_active = False
            return False

        # Get historical data (last 50 bars)
        stock_bars_request = StockBarsRequest(
            symbol_or_symbols=SYMBOL,
            timeframe=TimeFrame(5, TimeFrameUnit.Minute),
            limit=50
        )
        bars = stock_historical_client.get_stock_bars(stock_bars_request).df
        
        # Verify data exists
        if bars.empty:
            print("No historical data available")
            return True
        
        # Get current position
        positions = get_positions()
        current_position = positions.get(SYMBOL, 0)
        
        # Process data with our algorithm
        signal_data = trading_algorithm.analyze(bars)
        
        # Act on signals
        if signal_data['signal'] == "BUY" and current_position == 0:
            print(f"BUY signal at {signal_data['price']}")
            trading_client.submit_order(
                MarketOrderRequest(
                    symbol=SYMBOL,
                    qty=1,  # Adjust based on account size
                    side=OrderSide.BUY,
                    time_in_force=TimeInForce.DAY
                )
            )
        
        elif signal_data['signal'] == "SELL" and current_position > 0:
            print(f"SELL signal at {signal_data['price']}")
            trading_client.submit_order(
                MarketOrderRequest(
                    symbol=SYMBOL,
                    qty=current_position,
                    side=OrderSide.SELL,
                    time_in_force=TimeInForce.DAY
                )
            )

        return True  # Continue trading

    except OSError as e:
        if e.errno == 9:  # Bad file descriptor
            print("Recreating Alpaca clients due to connection error...")
            trading_client = TradingClient(API_KEY, API_SECRET, paper=True)
            stock_historical_client = StockHistoricalDataClient(API_KEY, API_SECRET)
            return True  # Try again after recreating clients
        else:
            print(f"Error in trading cycle: {str(e)}")
            return False
    except Exception as e:
        print(f"Error in trading cycle: {str(e)}")
        return False

if __name__ == "__main__":
    print(f"Bot starting at {pd.Timestamp.now(tz=nyse)}")
    
    # Run once upon starting (when cron starts it at 9:30 AM)
    # Set initial equity
    account = trading_client.get_account()
    initial_equity = float(account.equity)
    print(f"Initial equity: ${initial_equity:.2f}")
    
    # Monitor market and trade until market closes
    while market_is_open() and trading_active:
        if not run_trading_cycle():
            break
        time.sleep(CHECK_INTERVAL)
    
    # Clean up at end of day
    if trading_active:  # If we haven't already exited positions due to P&L limits
        exit_all_positions()
    
    print(f"Trading day complete at {pd.Timestamp.now(tz=nyse)}")
    final_pnl = calculate_pnl()
    print(f"Daily P&L: {final_pnl*100:.2f}%")
