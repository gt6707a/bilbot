#!/usr/bin/env python3
"""
Test script to demonstrate the new signal persistence behavior.
This shows how signals are maintained between calls when no crossover occurs.
"""

import pandas as pd
from sma_ema_crossover_algo import SmaEmaCrossoverAlgo

def create_test_data():
    """Create synthetic test data to demonstrate signal persistence."""
    # Create test data with a clear crossover pattern
    dates = pd.date_range('2023-01-01', periods=50, freq='5min')
    
    # Create price data that will generate EMA/SMA crossover
    prices = []
    base_price = 100
    
    for i in range(50):
        if i < 20:
            # Declining trend - EMA will be below SMA
            price = base_price - (i * 0.5)
        elif i < 25:
            # Sharp upturn - will cause EMA to cross above SMA
            price = base_price - 10 + ((i - 20) * 2)
        elif i < 35:
            # Flat period - no new crossover
            price = base_price - 2 + (i % 3) * 0.1
        elif i < 40:
            # Decline - will cause EMA to cross below SMA
            price = base_price - 2 - ((i - 35) * 1.5)
        else:
            # Another flat period - no new crossover
            price = base_price - 10 + (i % 2) * 0.1
        
        prices.append(price)
    
    df = pd.DataFrame({
        'timestamp': dates,
        'open': prices,
        'high': [p + 0.5 for p in prices],
        'low': [p - 0.5 for p in prices],
        'close': prices,
        'volume': [1000] * 50,
        'vwap': prices,
        'transactions': [10] * 50
    })
    
    return df

def test_signal_persistence():
    """Test that signals persist when no crossover occurs."""
    print("🧪 Testing Signal Persistence")
    print("=" * 50)
    
    # Create algorithm instance
    algo = SmaEmaCrossoverAlgo()
    
    # Create test data
    df = create_test_data()
    
    # Add indicators
    df = algo.add_technical_indicators(df)
    
    print(f"📊 Created test data with {len(df)} points")
    print(f"📈 EMA and SMA calculated")
    
    # Test signal detection at different points
    test_points = [25, 30, 35, 42, 45, 48]
    
    for point in test_points:
        # Get subset of data up to this point
        subset_df = df.iloc[:point+1].copy()
        
        # Detect signal
        signal = algo.detect_crossover(subset_df)
        
        latest = subset_df.iloc[-1]
        ema_above_sma = latest['ema_9'] > latest['sma_21']
        
        print(f"\n📍 Point {point}:")
        print(f"  Signal: {signal['signal']}")
        print(f"  Reason: {signal['reason']}")
        print(f"  EMA: ${signal.get('ema', 0):.2f}")
        print(f"  SMA: ${signal.get('sma', 0):.2f}")
        print(f"  EMA > SMA: {ema_above_sma}")
        print(f"  Current algo signal state: {algo.current_signal}")
    
    print(f"\n✅ Final signal state: {algo.current_signal}")
    print("\n🎯 Key behaviors demonstrated:")
    print("- Signals change only on actual crossovers")
    print("- Last signal is maintained when no crossover occurs")
    print("- Algorithm looks back to find historical crossovers if needed")

if __name__ == "__main__":
    test_signal_persistence()
