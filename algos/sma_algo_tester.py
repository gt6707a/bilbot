import os
import sys
import logging
from datetime import datetime
import pandas as pd
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame

# Add the parent directory to sys.path to allow importing from parent directory
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import the SmaEmaCrossoverAlgorithm class
from smaEmaCrossoverAlgorithm import SmaEmaCrossoverAlgorithm

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('sma_algo_tester')

def debug_data_feed():
    """Debug the raw data feed to see what's happening"""
    logger.info("=== DEBUGGING DATA FEED ===")
    
    api_key = os.getenv('ALPACA_API_KEY') or os.getenv('ALPACA_KEY')
    api_secret = os.getenv('ALPACA_API_SECRET') or os.getenv('ALPACA_SECRET')
    
    if not api_key or not api_secret:
        logger.error("No API credentials found")
        return
    
    data_client = StockHistoricalDataClient(api_key, api_secret)
    
    # Test multiple symbols to see if it's symbol-specific
    symbols = ["SPY", "AAPL", "MSFT"]
    
    for symbol in symbols:
        logger.info(f"\n--- Testing {symbol} ---")
        
        # Get recent data
        request_params = StockBarsRequest(
            symbol_or_symbols=symbol,
            timeframe=TimeFrame.Minute,
            start=pd.Timestamp.now() - pd.Timedelta(hours=2),
            limit=10
        )
        
        try:
            bars = data_client.get_stock_bars(request_params)
            df = bars.df.reset_index()
            
            if df.empty:
                logger.info(f"  No data returned for {symbol}")
                continue
                
            logger.info(f"  Received {len(df)} bars")
            logger.info(f"  Time range: {df['timestamp'].min()} to {df['timestamp'].max()}")
            
            # Show last 5 prices
            last_5 = df.tail(5)[['timestamp', 'close']].values
            logger.info(f"  Last 5 prices:")
            for timestamp, price in last_5:
                logger.info(f"    {timestamp}: ${price:.2f}")
                
            # Check for price changes
            price_changes = df['close'].diff().abs().sum()
            logger.info(f"  Total price movement: ${price_changes:.4f}")
            
            if price_changes == 0:
                logger.warning(f"  ⚠️  NO PRICE MOVEMENT in {symbol}")
            else:
                logger.info(f"  ✅ Price movement detected in {symbol}")
                
        except Exception as e:
            logger.error(f"  Error fetching {symbol}: {e}")

def test_sma_algo():
    """
    Test function to debug the run() method of the SmaEmaCrossoverAlgorithm class.
    Just executes once.
    """
    logger.info("Starting SMA/EMA Crossover Algorithm Tester")
    
    # First, debug the data feed
    debug_data_feed()
    
    # Check if API credentials are available
    api_key = os.getenv('ALPACA_API_KEY') or os.getenv('ALPACA_KEY')
    api_secret = os.getenv('ALPACA_API_SECRET') or os.getenv('ALPACA_SECRET')
    
    if not api_key or not api_secret:
        logger.error("Alpaca API credentials not found in environment variables.")
        logger.error("Please set ALPACA_API_KEY/ALPACA_KEY and ALPACA_API_SECRET/ALPACA_SECRET environment variables.")
        return
        
    # Initialize the algorithm with test parameters
    symbol = "SPY"
    initial_equity = 10000
    interval_minutes = 1

    logger.info(f"Initializing algorithm for {symbol} with {initial_equity:.2f} initial equity")
    
    algo = SmaEmaCrossoverAlgorithm(
        symbol=symbol,
        interval_minutes=interval_minutes,
        initial_equity=initial_equity,
        paper=True  # Always use paper trading for testing
    )
    
    try:
        logger.info(f"Executing algorithm run at {datetime.now()}")
        
        # Execute the run method
        result = algo.run()
        
        # Log detailed results
        logger.info(f"Signal: {result['signal']}")
        if result['price']:
            logger.info(f"Price: ${result['price']:.2f}")
        else:
            logger.info("Price: None")
        logger.info(f"Trade executed: {result['trade_executed']}")
        logger.info(f"Current PnL: {result['pnl']:.2f}%")
        logger.info(f"Signal recalculated: {result['recalculated']}")
        
        # Get current position
        position = algo.get_open_position()
        logger.info(f"Current position: {position} shares")
        
        # Get current equity
        equity = algo.get_current_equity()
        logger.info(f"Current equity: ${equity:.2f}")
        
    except Exception as e:
        logger.error(f"Error during algorithm execution: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
    
    finally:
        logger.info("Testing completed")

if __name__ == "__main__":
    test_sma_algo()