import pandas as pd
import numpy as np

class SmaEmaCrossoverAlgo:
    """
    Simple Moving Average (SMA) and Exponential Moving Average (EMA) crossover trading algorithm.
    
    Buy signal: When fast EMA crosses above slow SMA
    Sell signal: When fast EMA crosses below slow SMA
    """
    
    def __init__(self, ema_period=9, sma_period=21):
        """
        Initialize the algorithm with configurable parameters.
        
        Args:
            ema_period: Period for the fast EMA (default: 9)
            sma_period: Period for the slow SMA (default: 21)
        """
        self.name = "SMA-EMA Crossover"
        self.ema_period = ema_period
        self.sma_period = sma_period
    
    def calculate_indicators(self, df):
        """
        Calculate technical indicators for the given price data.
        
        Args:
            df: DataFrame with 'close' column containing price data
            
        Returns:
            DataFrame with added 'ema' and 'sma' columns
        """
        # Check if data exists and has required columns
        if df.empty or 'close' not in df.columns:
            raise ValueError("DataFrame must contain 'close' column with price data")
            
        # Deep copy to avoid modifying the original
        result = df.copy()
        
        # Calculate indicators
        result['ema'] = result['close'].ewm(span=self.ema_period, adjust=False).mean()
        result['sma'] = result['close'].rolling(self.sma_period).mean()
        
        return result
    
    def generate_signals(self, df):
        """
        Generate trading signals based on indicator values.
        
        Args:
            df: DataFrame with 'ema' and 'sma' columns
            
        Returns:
            Dictionary with signal details
        """
        # Check if we have enough data for signals
        if df.empty or 'ema' not in df.columns or 'sma' not in df.columns:
            raise ValueError("DataFrame must contain 'ema' and 'sma' columns")
        
        # Get latest values
        last_close = df['close'].iloc[-1]
        ema_current = df['ema'].iloc[-1]
        sma_current = df['sma'].iloc[-1]
        
        # Previous values (if available)
        ema_prev = df['ema'].iloc[-2] if len(df) > 1 else None
        sma_prev = df['sma'].iloc[-2] if len(df) > 1 else None
        
        # Default signal
        signal = "HOLD"
        
        # Current position of indicators
        if ema_current > sma_current:
            # Check for crossover (if we have previous values)
            if ema_prev is not None and sma_prev is not None:
                if ema_prev <= sma_prev:  # Crossover just happened
                    signal = "BUY"
                else:  # Already above
                    signal = "HOLD_LONG"
            else:  # No previous data, but EMA > SMA
                signal = "BUY"
        elif ema_current < sma_current:
            # Check for crossover (if we have previous values) 
            if ema_prev is not None and sma_prev is not None:
                if ema_prev >= sma_prev:  # Crossover just happened
                    signal = "SELL"
                else:  # Already below
                    signal = "HOLD_CASH"
            else:  # No previous data, but EMA < SMA
                signal = "SELL"
                
        return {
            'signal': signal,
            'price': last_close,
            'ema': ema_current,
            'sma': sma_current,
            'ema_minus_sma': ema_current - sma_current
        }
    
    def analyze(self, df):
        """
        Process price data and return trading signals.
        
        Args:
            df: DataFrame with 'close' column containing price data
            
        Returns:
            Dictionary with signal details
        """
        # Calculate indicators
        df_with_indicators = self.calculate_indicators(df)
        
        # Generate signals
        return self.generate_signals(df_with_indicators)