import os
import pandas as pd
import logging
from datetime import datetime, timedelta
from alpaca.trading.client import TradingClient
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from alpaca.data.timeframe import TimeFrame

class SmaEmaCrossoverAlgorithm:
    """
    Simple Moving Average (SMA) and Exponential Moving Average (EMA) crossover trading algorithm.
    
    Buy signal: When fast EMA crosses above slow SMA
    Sell signal: When fast EMA crosses below slow SMA
    """
    
    def __init__(self, symbol, interval_minutes=5, initial_equity=1000, paper=True):
        """
        Initialize the SMA/EMA crossover algorithm with trading capabilities.
        
        :param symbol: The trading symbol (e.g., 'SPY')
        :param interval_minutes: How often (in minutes) to recalculate the signal
        :param initial_equity: Dollar amount to begin the day with.
        :param paper: Whether to use paper trading
        """
        # Configure logging
        self.logger = logging.getLogger(__name__)
        if not self.logger.handlers:
            # Set up logging if not already configured
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        
        # Get API credentials from environment variables
        self.api_key = os.getenv('ALPACA_KEY')
        self.api_secret = os.getenv('ALPACA_SECRET')
        
        if not self.api_key or not self.api_secret:
            raise ValueError("ALPACA_KEY and ALPACA_SECRET environment variables must be set")
        
        # Indicator periods defined locally
        # Define indicator period constants
        FAST_EMA_PERIOD = 9
        SLOW_SMA_PERIOD = 21
        
        # Assign to instance variables for use throughout the class
        self.ema_period = FAST_EMA_PERIOD
        self.sma_period = SLOW_SMA_PERIOD
        
        self.symbol = symbol
        self.interval_minutes = interval_minutes
        self.initial_equity = initial_equity
        self.current_equity = initial_equity
        self.paper = paper
        
        # Initialize Alpaca clients
        self.data_client = StockHistoricalDataClient(self.api_key, self.api_secret)
        self.trading_client = TradingClient(self.api_key, self.api_secret, paper=paper)
        
        # Track when we last calculated a signal
        self.last_calculation_time = None
        self.cached_signal = None
        self.cached_price = None
        
        # Trading state
        self.daily_pnl_threshold = 0.0025  # 0.25% daily loss limit
        self.daily_gain_target = 0.01      # 1% daily gain target
    
    def reconnect(self):
        """Recreate clients in case of connection issues"""
        self.data_client = StockHistoricalDataClient(self.api_key, self.api_secret)
        self.trading_client = TradingClient(self.api_key, self.api_secret, paper=self.paper)
    
    def _should_recalculate(self):
        """Determine if enough time has passed to recalculate the signal."""
        if self.last_calculation_time is None:
            return True
        
        elapsed_time = datetime.now() - self.last_calculation_time
        return elapsed_time > timedelta(minutes=self.interval_minutes)
    
    def _fetch_market_data(self):
        """Fetch the latest market data for analysis."""
        # Calculate how many bars to request based on which period is longer
        lookback = max(self.ema_period, self.sma_period) * 2  # Double to ensure enough data
        
        # Get historical data
        request_params = StockBarsRequest(
            symbol_or_symbols=self.symbol,
            timeframe=TimeFrame.Minute,
            start=pd.Timestamp.now() - pd.Timedelta(days=5),
            limit=lookback
        )
        
        bars = self.data_client.get_stock_bars(request_params)
        df = bars.df.reset_index()
        
        return df
    
    def _calculate_signal(self, df):
        """Calculate trading signal based on SMA/EMA crossover."""
        # Calculate indicators
        df['sma'] = df['close'].rolling(window=self.sma_period).mean()
        df['ema'] = df['close'].ewm(span=self.ema_period, adjust=False).mean()
        
        # Get the last two rows to check for a crossover
        last_two = df.iloc[-2:].copy()
        
        # Determine if there's a crossover
        if len(last_two) < 2:
            return {"signal": "NONE", "price": df['close'].iloc[-1]}
        
        # Check for crossovers
        prev_ema_above_sma = last_two['ema'].iloc[0] > last_two['sma'].iloc[0]
        curr_ema_above_sma = last_two['ema'].iloc[1] > last_two['sma'].iloc[1]
        
        # EMA crosses above SMA: Buy signal
        if not prev_ema_above_sma and curr_ema_above_sma:
            return {"signal": "BUY", "price": df['close'].iloc[-1]}
        
        # EMA crosses below SMA: Sell signal
        elif prev_ema_above_sma and not curr_ema_above_sma:
            return {"signal": "SELL", "price": df['close'].iloc[-1]}
        
        # No crossover
        return {"signal": "NONE", "price": df['close'].iloc[-1]}
    
    def get_signal(self):
        """
        Calculate and get the current trading signal.
        """
        try:
            # Time to refresh the signal
            df = self._fetch_market_data()
            signal_data = self._calculate_signal(df)
            
            # Update cache and timestamp
            self.last_calculation_time = datetime.now()
            self.cached_signal = signal_data["signal"]
            self.cached_price = signal_data["price"]
            
            self.logger.info(f"Calculated new signal: {self.cached_signal} at {self.cached_price}")
            return signal_data
                
        except Exception as e:
            self.logger.info(f"Error calculating signal: {str(e)}")
            # Return NONE signal in case of error
            return {"signal": "NONE", "price": None}
    
    def get_cached_signal(self):
        """
        Returns the most recently cached signal without recalculating.
        """
        if self.cached_signal is None:
            # No cached signal available
            return {"signal": "NONE", "price": None}
        
        elapsed = datetime.now() - self.last_calculation_time
        self.logger.info(f"Using cached signal ({elapsed.seconds}s old): {self.cached_signal}")
        return {"signal": self.cached_signal, "price": self.cached_price}

    def get_current_equity(self):
        """Get current equity value"""
        return float(self.current_equity)
    
    def calculate_pnl(self):
        """Calculate daily P&L percentage"""
        return (self.current_equity - self.initial_equity) / self.initial_equity
    
    def exit_all_positions(self):
        """Liquidate all positions"""
        self.trading_client.close_all_positions(cancel_orders=True)
        self.logger.info("Closed all positions")
    
    def get_open_position(self):
        """
        Get current open position for the symbol.
        Returns position quantity or 0 if no position exists.
        """
        try:
            position = self.trading_client.get_open_position(self.symbol)
            if (position.qty > 0):
                self.current_equity = float(position.market_value)

            return float(position.qty)
        except Exception:
            # No position exists
            return 0

    def close_position(self):
        """
        Close the position for the symbol.
        Returns True if position was closed successfully.
        """
        try:
            self.trading_client.close_position(self.symbol)
            self.logger.info(f"Closed position for {self.symbol}")
            return True
        except Exception as e:
            self.logger.info(f"Error closing position for {self.symbol}: {str(e)}")
            return False
    
    def execute_trade(self, signal):
        """Execute a trade based on the given signal"""
        # Get current position using the new method
        current_position = self.get_open_position()
        
        if signal['signal'] == "BUY" and current_position == 0:
            self.logger.info(f"BUY signal at {signal['price']}")
            self.trading_client.submit_order(
                MarketOrderRequest(
                    symbol=self.symbol,
                    notional=str(self.current_equity),
                    side=OrderSide.BUY,
                    time_in_force=TimeInForce.DAY
                )
            )
            return True
        
        elif signal['signal'] == "SELL" and current_position > 0:
            self.logger.info(f"SELL signal at {signal['price']}")
            # Use close_position instead of submitting a sell order
            return self.close_position()
            
        return False
    
    def run(self):
        """Run one trading cycle"""
        # Get current open position and update current equity
        self.get_open_position()
        
        # Check if we need to recalculate the signal
        if not self._should_recalculate():
            # Not time to recalculate yet, return early with cached signal
            cached_signal = self.get_cached_signal()
            return {
                'signal': cached_signal['signal'],
                'price': cached_signal['price'],
                'trade_executed': False,
                'pnl': self.calculate_pnl() * 100,  # Return as percentage
                'recalculated': False
            }
        
        # Time to recalculate - get a fresh signal
        signal = self.get_signal()
        
        # Execute trade based on signal
        trade_executed = self.execute_trade(signal)
        
        return {
            'signal': signal['signal'],
            'price': signal['price'],
            'trade_executed': trade_executed,
            'pnl': self.calculate_pnl() * 100,  # Return as percentage
            'recalculated': True
        }