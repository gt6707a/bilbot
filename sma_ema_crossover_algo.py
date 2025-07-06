import os
import pandas as pd
import logging
from datetime import datetime, timedelta
from polygon import RESTClient
import time

class SmaEmaCrossoverAlgo:
    """
    Fetch stock market data from Polygon API and calculate technical indicators.
    Detects EMA/SMA crossovers for trading signals.
    """
    
    def __init__(self, api_key=None):
        """
        Initialize the SMA/EMA crossover algorithm.
        
        :param api_key: Polygon API key (if not provided, will look for POLYGON_API_KEY env var)
        """
        # Set up logging
        self.logger = logging.getLogger(__name__)
        if not self.logger.handlers:
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        
        # Get API key
        self.api_key = api_key or os.getenv('POLYGON_API_KEY')
        if not self.api_key:
            raise ValueError("Polygon API key required. Set POLYGON_API_KEY environment variable or pass api_key parameter.")
        
        # Initialize Polygon client
        try:
            self.client = RESTClient(api_key=self.api_key)
            self.logger.info("✅ Polygon client initialized successfully")
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize Polygon client: {e}")
            raise
        
        # Technical indicator periods
        self.ema_period = 9
        self.sma_period = 21
        
        # Signal state tracking
        self.current_signal = None  # Will be 'BUY' or 'SELL'
        
    def get_sma(self, symbol, window=5, limit=21):
        """
        Get Simple Moving Average values
        :param symbol: Stock symbol (e.g., 'SPY', 'AAPL')
        :param window: SMA window/period for 5-minute intervals (default: 5)
        :param limit: Number of SMA values to fetch (default: 21)
        :return: Mean of SMA values or None
        """
        try:
            self.logger.info(f"Fetching {limit} SMA({window}) values at 5-minute intervals for {symbol}")
            
            # Use Polygon's SMA endpoint with 5-minute intervals
            sma_response = self.client.get_sma(
                ticker=symbol,
                timespan='minute',
                adjusted=True,
                window=window,  # 5-minute window
                series_type='close',
                order='desc',  # Get most recent values first
                limit=limit    # Fetch 21 values
            )
            
            # Extract SMA values from response
            sma_values = []

            for item in sma_response.values:
                sma_values.append(float(item.value))

            if sma_values and len(sma_values) == limit:
                mean_sma = sum(sma_values) / len(sma_values)
                
                self.logger.info(f"✅ Fetched {len(sma_values)} SMA values, mean SMA: ${mean_sma:.2f}")
                return mean_sma
            else:
                self.logger.warning(f"Expected {limit} SMA values but got {len(sma_values)} for {symbol}")
                return None
                
        except Exception as e:
            self.logger.error(f"❌ Error fetching SMA from Polygon for {symbol}: {e}")
            return None
    
    def get_ema(self, symbol, window=5, limit=9):
        """
        Get Exponential Moving Average values from Polygon API at 5-minute intervals.
        Fetches 9 EMA values and returns their mean.
        
        :param symbol: Stock symbol (e.g., 'SPY', 'AAPL')
        :param window: EMA window/period for 5-minute intervals (default: 5)
        :param limit: Number of EMA values to fetch (default: 9)
        :return: Mean of EMA values or None
        """
        try:
            self.logger.info(f"Fetching {limit} EMA({window}) values at 5-minute intervals for {symbol}")
            
            # Use Polygon's EMA endpoint with 5-minute intervals
            ema_response = self.client.get_ema(
                ticker=symbol,
                timespan='minute',
                adjusted=True,
                window=window,  # 5-minute window
                series_type='close',
                order='desc',  # Get most recent values first
                limit=limit
            )
            
            # Extract EMA values from response
            ema_values = []

            for item in ema_response.values:
                ema_values.append(float(item.value))
            
            if ema_values and len(ema_values) == limit:
                mean_ema = sum(ema_values) / len(ema_values)
                self.logger.info(f"✅ Fetched {len(ema_values)} EMA values, mean EMA: ${mean_ema:.2f}")
                return mean_ema
            else:
                self.logger.warning(f"Expected {limit} EMA values but got {len(ema_values)} for {symbol}")
                return None
                
        except Exception as e:
            self.logger.error(f"❌ Error fetching EMA from Polygon for {symbol}: {e}")
            return None
    
    def get_current_indicators(self, symbol):
        """
        Get current SMA and EMA values
        :param symbol: Stock symbol
        :return: Dict with current SMA and EMA values, or None if failed
        """
        try:
            current_sma = self.get_sma(symbol, window=5, limit=21)
            current_ema = self.get_ema(symbol, window=5, limit=9)
            
            if current_sma is not None and current_ema is not None:
                return {
                    'sma': current_sma,
                    'ema': current_ema,
                    'timestamp': pd.Timestamp.now()
                }
            else:
                self.logger.warning(f"Failed to get indicators from Polygon for {symbol}")
                return None
                
        except Exception as e:
            self.logger.error(f"❌ Error getting current indicators for {symbol}: {e}")
            return None
    
    def get_signal(self, symbol):
        """
        Get trading signal for a symbol based on EMA/SMA crossover.
        Uses direct Polygon API calls for current indicators instead of fetching aggregates.
        
        :param symbol: Stock symbol
        :return: Dict with signal information
        """
        try:
            # Try to get current indicators directly from Polygon
            indicators = self.get_current_indicators(symbol)
            
            if indicators:
                # We have current SMA and EMA values
                current_sma = indicators['sma']
                current_ema = indicators['ema']
                current_timestamp = indicators['timestamp']
                                
                # Determine signal based on EMA vs SMA position
                if current_ema < current_sma:
                    # EMA below SMA - bearish signal
                    self.current_signal = "SELL"
                    reason = f"EMA(5-min avg) below SMA(5-min avg) - bearish trend"
                    crossover_type = "bearish"
                else:
                    # EMA above SMA - bullish signal
                    # Signal changed to BUY
                    self.current_signal = "BUY"
                    reason = f"EMA(5-min avg) above SMA(5-min avg) - bullish trend"
                    crossover_type = "bullish"
                
                signal_info = {
                    "signal": self.current_signal,
                    "reason": reason,
                    "timestamp": current_timestamp,
                    "ema": current_ema,
                    "sma": current_sma,
                    "ema_above_sma": current_ema > current_sma,
                    "crossover_type": crossover_type
                }
                
                self.logger.info(f"🎯 Signal for {symbol}: {signal_info['signal']} - {signal_info['reason']}")
                return signal_info
            
            else:
                # No indicators available
                self.logger.info(f"🎯 Signal not found {symbol}")
                return {
                    "signal": self.current_signal or "NONE",
                }
            
        except Exception as e:
            self.logger.error(f"❌ Error getting signal for {symbol}: {e}")
            return {
                "signal": self.current_signal or "NONE", 
                "price": None, 
                "reason": f"Error: {str(e)}",
                "timestamp": None
            }


def main():
    """
    Example usage of the SmaEmaCrossoverAlgo.
    """
    # Check if API key is available
    if not os.getenv('POLYGON_API_KEY'):
        print("Please set POLYGON_API_KEY environment variable")
        print("You can get a free API key from: https://polygon.io/")
        return
    
    # Initialize algorithm
    try:
        algo = SmaEmaCrossoverAlgo()
    except Exception as e:
        print(f"Failed to initialize SMA/EMA crossover algorithm: {e}")
        return
    
    # Test symbols
    symbols = ['SPY', 'AAPL', 'MSFT', 'GOOGL']
    
    for symbol in symbols:
        print(f"\n--- Analyzing {symbol} with SMA/EMA Crossover Algorithm ---")
        
        try:
            # Get signal (5-minute intervals)
            signal = algo.get_signal(symbol, multiplier=5, days_back=3)
            
            print(f"📊 Signal: {signal['signal']}")
            print(f"💰 Price: ${signal['price']:.2f}" if signal['price'] else "💰 Price: N/A")
            print(f"📅 Time: {signal['timestamp']}" if signal['timestamp'] else "📅 Time: N/A")
            print(f"📝 Reason: {signal['reason']}")
            
            if 'ema' in signal and 'sma' in signal:
                print(f"📈 EMA({algo.ema_period}): ${signal['ema']:.2f}")
                print(f"📊 SMA({algo.sma_period}): ${signal['sma']:.2f}")
                
                if 'ema_above_sma' in signal:
                    trend = "🟢 Bullish" if signal['ema_above_sma'] else "🔴 Bearish"
                    print(f"📈 Trend: {trend}")
            
            # Small delay to avoid rate limiting
            time.sleep(0.5)
            
        except Exception as e:
            print(f"❌ Error analyzing {symbol}: {e}")


if __name__ == "__main__":
    main()
