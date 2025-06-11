import os
import time
import schedule
import pandas as pd
import pytz
import holidays
from alpaca.trading.client import TradingClient
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.trading.requests import MarketOrderRequest, LimitOrderRequest
from alpaca.trading.enums import OrderSide, OrderType, TimeInForce

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

# Track daily performance
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

def work():
    global trading_active
    if not trading_active or not market_is_open():
        return

    try:
        # Check daily P&L limits
        pnl = calculate_pnl()
        if pnl <= -daily_pnl_threshold or pnl >= daily_gain_target:
            print(f"Daily P&L limit reached: {pnl*100:.2f}%")
            exit_all_positions()
            trading_active = False
            return

        # Get historical data (last 50 bars)
        bars = stock_historical_client.get_stock_bars(
            SYMBOL, 
            timeframe="5Min", 
            limit=50
        ).df
        
        # Calculate indicators
        bars['ema'] = bars.close.ewm(span=EMA_PERIOD, adjust=False).mean()
        bars['sma'] = bars.close.rolling(SMA_PERIOD).mean()
        
        # Get current position
        positions = get_positions()
        current_position = positions.get(SYMBOL, 0)

        # Generate signals
        last_close = bars.close[-1]
        ema_current = bars.ema[-1]
        sma_current = bars.sma[-1]
        
        # Buy signal: EMA crosses above SMA
        if ema_current > sma_current and current_position == 0:
            print(f"BUY signal at {last_close}")
            trading_client.submit_order(
                MarketOrderRequest(
                    symbol=SYMBOL,
                    qty=1,  # Adjust based on account size
                    side=OrderSide.BUY,
                    time_in_force=TimeInForce.DAY
                )
            )
        
        # Sell signal: EMA crosses below SMA
        elif ema_current < sma_current and current_position > 0:
            print(f"SELL signal at {last_close}")
            trading_client.submit_order(
                MarketOrderRequest(
                    symbol=SYMBOL,
                    qty=current_position,
                    side=OrderSide.SELL,
                    time_in_force=TimeInForce.DAY
                )
            )

    except Exception as e:
        print(f"Error in work cycle: {str(e)}")

def reset_daily():
    """Reset daily tracking at market close"""
    global initial_equity, trading_active
    initial_equity = None
    trading_active = True

# Schedule daily reset
schedule.every().day.at("09:30", "America/New_York").do(reset_daily)
schedule.every(CHECK_INTERVAL).seconds.do(work)

if __name__ == "__main__":
    while True:
        schedule.run_pending()
        time.sleep(1)
