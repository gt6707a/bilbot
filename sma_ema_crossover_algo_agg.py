import os
import pandas as pd
import logging
from datetime import datetime, timedelta
from polygon import RESTClient
import time

class SmaEmaCrossoverAlgoAgg:
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
        
    def get_sma(self, aggs):
        """
        Calculate Simple Moving Average from aggregates
        :param aggs: List of aggregate objects from list_aggs
        :return: Latest SMA value or None
        """
        try:
            if not aggs:
                return None
                
            # Extract close prices from aggregates
            close_prices = [agg.close for agg in aggs]
            
            if len(close_prices) >= self.sma_period:
                # Calculate SMA from the most recent prices
                # Take the first sma_period prices (since sorted desc, these are most recent)
                latest_sma = sum(close_prices) / len(close_prices)
                return latest_sma
            else:
                # Use all available prices if we don't have enough for the full period
                latest_sma = sum(close_prices) / len(close_prices)
                return latest_sma
                
        except Exception as e:
            return None
    
    def get_ema(self, aggs):
        """
        Calculate Exponential Moving Average from aggregates
        :param aggs: List of aggregate objects from list_aggs
        :return: Latest EMA value or None
        """
        try:
            if not aggs:
                return None
                
            # EMA only needs the first 9 aggregates (most recent since sorted desc)
            close_prices = list(reversed([agg.close for agg in aggs[:self.ema_period]]))
            
            if len(close_prices) >= self.ema_period:
                # Calculate EMA using exponential smoothing
                alpha = 2.0 / (self.ema_period + 1)
                ema = close_prices[0]  # Start with first price
                
                for price in close_prices[1:]:
                    ema = alpha * price + (1 - alpha) * ema
                
                return ema
            else:
                # Use simple average if we don't have enough data points
                return sum(close_prices) / len(close_prices)
                
        except Exception as e:
            return None


    def get_current_indicators(self, symbol, multiplier=5, limit=21):
        """
        Get current SMA and EMA values
        :param symbol: Stock symbol
        :param multiplier: Multiplier for timespan (default: 5 for 5-minute intervals)
        :param limit: Number of aggregates to fetch (default: 21)
        :return: Dict with current SMA and EMA values, or None if failed
        """
        try:
            self.logger.info(f"Fetching aggregates for {symbol} to calculate SMA({self.sma_period}) and EMA({self.ema_period})")
            
            # Calculate date range - get enough data for SMA calculation
            end_date = datetime.now()
            start_date = end_date - timedelta(days=1)  # Get a day of data
            
            # Use list_aggs to get aggregates
            aggs = []
            count = 0
            latest_timestamp = None
            
            for a in self.client.list_aggs(
                symbol,
                multiplier,  # 5-minute intervals
                "minute",
                int(start_date.timestamp() * 1000),
                int(end_date.timestamp() * 1000),
                adjusted="false",
                sort="desc",  # Most recent first
            ):
                if count >= limit:
                    break
                aggs.append(a)
                if not latest_timestamp:
                    latest_timestamp = a.timestamp
                count += 1
            
            if aggs:
                self.logger.info(f"✅ Fetched {len(aggs)} aggregates for {symbol}")
                
                # Calculate SMA and EMA from the aggregates
                current_sma = self.get_sma(aggs)
                current_ema = self.get_ema(aggs)
                
                if current_sma is not None and current_ema is not None:
                    if latest_timestamp:
                        local_time = datetime.fromtimestamp(latest_timestamp/1000).strftime('%Y-%m-%d %H:%M:%S')
                        self.logger.info(f"✅ Calculated SMA({self.sma_period}): ${current_sma:.4f}, EMA({self.ema_period}): ${current_ema:.4f}. Local time: {local_time}")
                    else:
                        self.logger.info(f"✅ Calculated SMA({self.sma_period}): ${current_sma:.4f}, EMA({self.ema_period}): ${current_ema:.4f}")
                    
                    return {
                        'sma': current_sma,
                        'ema': current_ema,
                        'timestamp': pd.Timestamp.now()
                    }
                else:
                    self.logger.warning(f"Failed to calculate indicators from aggregates for {symbol}")
                    return None
            else:
                self.logger.warning(f"No aggregates retrieved for {symbol}")
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
    symbols = ['SPY']
    
    for symbol in symbols:
        print(f"\n--- Analyzing {symbol} with SMA/EMA Crossover Algorithm ---")
        
        try:
            # Get signal (5-minute intervals)
            signal = algo.get_signal(symbol)
            
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
