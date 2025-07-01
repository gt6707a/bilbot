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
        
    def fetch_aggregates(self, symbol, timespan='minute', multiplier=5, days_back=5):
        """
        Fetch aggregate data from Polygon.
        
        :param symbol: Stock symbol (e.g., 'SPY', 'AAPL')
        :param timespan: Timespan for aggregates ('minute', 'hour', 'day')
        :param multiplier: Multiplier for timespan (5 for 5-minute intervals)
        :param days_back: Number of days to look back
        :return: DataFrame with OHLCV data
        """
        # Calculate date range
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days_back)
        
        # Format dates for Polygon API (YYYY-MM-DD)
        start_date_str = start_date.strftime('%Y-%m-%d')
        end_date_str = end_date.strftime('%Y-%m-%d')
        
        self.logger.info(f"Fetching {multiplier}-{timespan} aggregates for {symbol}")
        self.logger.info(f"Date range: {start_date_str} to {end_date_str}")
        
        try:
            # Fetch aggregates
            aggs = self.client.get_aggs(
                ticker=symbol,
                multiplier=multiplier,
                timespan=timespan,
                from_=start_date_str,
                to=end_date_str,
                adjusted=True,
                sort="asc",
                limit=50000  # Max limit to get all data
            )
            
            # Convert to DataFrame
            data = []
            for agg in aggs:
                data.append({
                    'timestamp': pd.to_datetime(agg.timestamp, unit='ms'),
                    'open': float(agg.open),
                    'high': float(agg.high),
                    'low': float(agg.low),
                    'close': float(agg.close),
                    'volume': int(agg.volume),
                    'vwap': float(getattr(agg, 'vwap', 0)) or None,
                    'transactions': int(getattr(agg, 'transactions', 0)) or None
                })
            
            if not data:
                self.logger.warning(f"No data received for {symbol}")
                return pd.DataFrame()
            
            df = pd.DataFrame(data)
            
            # Sort by timestamp
            df = df.sort_values('timestamp').reset_index(drop=True)
            
            self.logger.info(f"✅ Fetched {len(df)} aggregates for {symbol}")
            self.logger.info(f"Data range: {df['timestamp'].min()} to {df['timestamp'].max()}")
            
            return df
            
        except Exception as e:
            self.logger.error(f"❌ Error fetching data for {symbol}: {e}")
            return pd.DataFrame()
    
    def calculate_sma(self, df, period=None, column='close'):
        """
        Calculate Simple Moving Average.
        
        :param df: DataFrame with price data
        :param period: SMA period (default: self.sma_period)
        :param column: Column to calculate SMA on
        :return: Series with SMA values
        """
        if period is None:
            period = self.sma_period
        
        return df[column].rolling(window=period).mean()
    
    def calculate_ema(self, df, period=None, column='close'):
        """
        Calculate Exponential Moving Average.
        
        :param df: DataFrame with price data
        :param period: EMA period (default: self.ema_period)
        :param column: Column to calculate EMA on
        :return: Series with EMA values
        """
        if period is None:
            period = self.ema_period
        
        return df[column].ewm(span=period, adjust=False).mean()
    
    def add_technical_indicators(self, df):
        """
        Add EMA and SMA indicators to the DataFrame.
        
        :param df: DataFrame with OHLCV data
        :return: DataFrame with added indicators
        """
        if df.empty:
            return df
        
        # Calculate indicators
        df['sma_21'] = self.calculate_sma(df, self.sma_period)
        df['ema_9'] = self.calculate_ema(df, self.ema_period)
        
        # Log indicator statistics
        valid_sma = df['sma_21'].notna().sum()
        valid_ema = df['ema_9'].notna().sum()
        
        self.logger.info(f"Technical indicators calculated:")
        self.logger.info(f"  SMA({self.sma_period}): {valid_sma} valid values")
        self.logger.info(f"  EMA({self.ema_period}): {valid_ema} valid values")
        
        return df
    
    def detect_crossover(self, df):
        """
        Detect EMA/SMA crossover signals.
        Only returns BUY when EMA crosses above SMA, SELL when EMA crosses below SMA.
        Maintains the last crossover signal when no new crossover is detected.
        
        :param df: DataFrame with 'ema_9' and 'sma_21' columns
        :return: Dict with signal information
        """
        if df.empty or len(df) < 2:
            return {
                "signal": self.current_signal or "SELL",  # Default to SELL if no signal yet
                "price": None, 
                "reason": "Insufficient data",
                "timestamp": None
            }
        
        # Get last two rows to check for crossover
        last_two = df.tail(2).copy()
        
        # Check if we have valid indicator values
        if last_two['ema_9'].isna().any() or last_two['sma_21'].isna().any():
            # If we don't have a current signal, look back through the data to find the last crossover
            if self.current_signal is None:
                self.current_signal = self._find_last_crossover_signal(df)
            
            return {
                "signal": self.current_signal or "SELL",
                "price": df['close'].iloc[-1] if not df.empty else None,
                "reason": "Invalid indicators (NaN values) - maintaining last signal",
                "timestamp": df['timestamp'].iloc[-1] if not df.empty else None
            }
        
        # Check for crossovers
        prev_ema_above_sma = last_two['ema_9'].iloc[0] > last_two['sma_21'].iloc[0]
        curr_ema_above_sma = last_two['ema_9'].iloc[1] > last_two['sma_21'].iloc[1]
        
        current_price = last_two['close'].iloc[-1]
        current_timestamp = last_two['timestamp'].iloc[-1]
        current_ema = last_two['ema_9'].iloc[-1]
        current_sma = last_two['sma_21'].iloc[-1]
        
        # EMA crosses above SMA: Buy signal
        if not prev_ema_above_sma and curr_ema_above_sma:
            self.current_signal = "BUY"
            return {
                "signal": "BUY", 
                "price": current_price,
                "reason": f"EMA({self.ema_period}) crossed above SMA({self.sma_period})",
                "timestamp": current_timestamp,
                "ema": current_ema,
                "sma": current_sma,
                "crossover_type": "bullish"
            }
        
        # EMA crosses below SMA: Sell signal
        elif prev_ema_above_sma and not curr_ema_above_sma:
            self.current_signal = "SELL"
            return {
                "signal": "SELL", 
                "price": current_price,
                "reason": f"EMA({self.ema_period}) crossed below SMA({self.sma_period})",
                "timestamp": current_timestamp,
                "ema": current_ema,
                "sma": current_sma,
                "crossover_type": "bearish"
            }
        
        # No crossover detected - maintain current signal
        # If we don't have a current signal, look back to find the last crossover
        if self.current_signal is None:
            self.current_signal = self._find_last_crossover_signal(df)
        
        return {
            "signal": self.current_signal or "SELL",  # Default to SELL if still no signal found
            "price": current_price,
            "reason": f"No crossover detected - maintaining {self.current_signal or 'SELL'} signal",
            "timestamp": current_timestamp,
            "ema": current_ema,
            "sma": current_sma,
            "ema_above_sma": curr_ema_above_sma
        }
    
    def get_stock_data_with_indicators(self, symbol, timespan='minute', multiplier=5, days_back=5):
        """
        Fetch stock data and calculate EMA/SMA indicators.
        
        :param symbol: Stock symbol
        :param timespan: Timespan for aggregates
        :param multiplier: Multiplier for timespan (5 for 5-minute intervals)
        :param days_back: Days to look back
        :return: DataFrame with OHLCV data plus EMA/SMA indicators
        """
        # Fetch raw data
        df = self.fetch_aggregates(symbol, timespan, multiplier, days_back)
        
        if df.empty:
            self.logger.warning(f"No data received for {symbol}")
            return df
        
        # Add technical indicators
        df = self.add_technical_indicators(df)
        
        # Show latest values
        if not df.empty:
            latest = df.iloc[-1]
            self.logger.info(f"Latest data for {symbol}:")
            self.logger.info(f"  Time: {latest['timestamp']}")
            self.logger.info(f"  Close: ${latest['close']:.2f}")
            if not pd.isna(latest['sma_21']):
                self.logger.info(f"  SMA({self.sma_period}): ${latest['sma_21']:.2f}")
            if not pd.isna(latest['ema_9']):
                self.logger.info(f"  EMA({self.ema_period}): ${latest['ema_9']:.2f}")
        
        return df
    
    def get_signal(self, symbol, timespan='minute', multiplier=5, days_back=5):
        """
        Get trading signal for a symbol based on EMA/SMA crossover.
        
        :param symbol: Stock symbol
        :param timespan: Timespan for aggregates
        :param multiplier: Multiplier for timespan (5 for 5-minute intervals)
        :param days_back: Days to look back
        :return: Dict with signal information
        """
        try:
            # Get data with indicators
            df = self.get_stock_data_with_indicators(symbol, timespan, multiplier, days_back)
            
            if df.empty:
                return {
                    "signal": self.current_signal or "SELL",
                    "price": None,
                    "reason": "No data available",
                    "timestamp": None
                }
            
            # Detect crossover
            signal_info = self.detect_crossover(df)
            
            self.logger.info(f"🎯 Signal for {symbol}: {signal_info['signal']} - {signal_info['reason']}")
            
            return signal_info
            
        except Exception as e:
            self.logger.error(f"❌ Error getting signal for {symbol}: {e}")
            return {
                "signal": self.current_signal or "SELL", 
                "price": None, 
                "reason": f"Error: {str(e)}",
                "timestamp": None
            }
    
    def get_latest_price(self, symbol):
        """
        Get the latest price for a symbol.
        
        :param symbol: Stock symbol
        :return: Latest price or None
        """
        try:
            # Get last trade
            trade = self.client.get_last_trade(symbol)
            if trade:
                return trade.price
            return None
        except Exception as e:
            self.logger.error(f"Error getting latest price for {symbol}: {e}")
            return None
    
    def _find_last_crossover_signal(self, df):
        """
        Look back through the data to find the most recent crossover signal.
        
        :param df: DataFrame with 'ema_9' and 'sma_21' columns
        :return: 'BUY' or 'SELL' based on last crossover, or 'BUY' as default
        """
        if df.empty or len(df) < 2:
            return "SELL"  # Default to SELL
        
        # Get valid data (non-NaN indicators)
        valid_data = df.dropna(subset=['ema_9', 'sma_21'])
        
        if len(valid_data) < 2:
            return "SELL"  # Default to SELL
        
        # Look through the data backwards to find the last crossover
        for i in range(len(valid_data) - 1, 0, -1):
            curr_ema_above_sma = valid_data['ema_9'].iloc[i] > valid_data['sma_21'].iloc[i]
            prev_ema_above_sma = valid_data['ema_9'].iloc[i-1] > valid_data['sma_21'].iloc[i-1]
            
            # Found a crossover
            if prev_ema_above_sma != curr_ema_above_sma:
                if curr_ema_above_sma:
                    self.logger.info("Found historical BUY crossover signal")
                    return "BUY"
                else:
                    self.logger.info("Found historical SELL crossover signal")
                    return "SELL"
        
        # No crossover found, determine signal based on current position
        latest_ema = valid_data['ema_9'].iloc[-1]
        latest_sma = valid_data['sma_21'].iloc[-1]
        
        if latest_ema > latest_sma:
            self.logger.info("No crossover found - EMA above SMA, defaulting to BUY")
            return "BUY"
        else:
            self.logger.info("No crossover found - EMA below SMA, defaulting to SELL")
            return "SELL"


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
