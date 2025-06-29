#!/usr/bin/env python3
"""
Test script for debugging the Polygon Data Fetcher.
This script allows you to test the Polygon API integration and EMA/SMA calculations.
"""

import os
import sys
import logging
from datetime import datetime

# Add current directory to path to import polygon_data_fetcher
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from polygon_data_fetcher import PolygonDataFetcher

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger('polygon_tester')

def test_api_connection():
    """Test basic API connection and authentication."""
    logger.info("=== TESTING API CONNECTION ===")
    
    # Check if API key is available
    api_key = os.getenv('POLYGON_API_KEY')
    if not api_key:
        logger.error("❌ POLYGON_API_KEY environment variable not found!")
        logger.error("Please set it with: export POLYGON_API_KEY=your_api_key")
        logger.error("Get a free API key from: https://polygon.io/")
        return False
    
    logger.info(f"✅ API Key found: {api_key[:10]}...")
    
    try:
        # Initialize fetcher
        fetcher = PolygonDataFetcher()
        logger.info("✅ PolygonDataFetcher initialized successfully")
        return fetcher
    except Exception as e:
        logger.error(f"❌ Failed to initialize PolygonDataFetcher: {e}")
        return False

def test_data_fetching(fetcher, symbol="SPY"):
    """Test raw data fetching."""
    logger.info(f"=== TESTING DATA FETCHING FOR {symbol} ===")
    
    try:
        # Fetch 5-minute aggregate data
        df = fetcher.fetch_aggregates(symbol, timespan='minute', multiplier=5, days_back=2)
        
        if df.empty:
            logger.error(f"❌ No data received for {symbol}")
            return False
        
        logger.info(f"✅ Received {len(df)} data points for {symbol}")
        logger.info(f"📊 Data columns: {list(df.columns)}")
        logger.info(f"📅 Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
        
        # Show sample data
        logger.info("📈 Sample data (last 3 rows):")
        for idx, row in df.tail(3).iterrows():
            logger.info(f"  {row['timestamp']}: O=${row['open']:.2f} H=${row['high']:.2f} L=${row['low']:.2f} C=${row['close']:.2f} V={row['volume']:,}")
        
        return df
        
    except Exception as e:
        logger.error(f"❌ Error fetching data for {symbol}: {e}")
        return False

def test_indicators(fetcher, symbol="SPY"):
    """Test EMA/SMA calculation."""
    logger.info(f"=== TESTING INDICATORS FOR {symbol} ===")
    
    try:
        # Get data with indicators
        df = fetcher.get_stock_data_with_indicators(symbol, multiplier=5, days_back=3)
        
        if df.empty:
            logger.error(f"❌ No data with indicators for {symbol}")
            return False
        
        # Check if indicators were calculated
        has_sma = 'sma_21' in df.columns and df['sma_21'].notna().any()
        has_ema = 'ema_9' in df.columns and df['ema_9'].notna().any()
        
        logger.info(f"✅ Data with indicators received for {symbol}")
        logger.info(f"📊 SMA(21) calculated: {has_sma}")
        logger.info(f"📈 EMA(9) calculated: {has_ema}")
        
        # Count valid indicator values
        if has_sma:
            sma_count = df['sma_21'].notna().sum()
            logger.info(f"📊 SMA valid values: {sma_count}/{len(df)}")
        
        if has_ema:
            ema_count = df['ema_9'].notna().sum()
            logger.info(f"📈 EMA valid values: {ema_count}/{len(df)}")
        
        # Show latest values with indicators
        latest = df.iloc[-1]
        logger.info("🎯 Latest data point:")
        logger.info(f"  📅 Time: {latest['timestamp']}")
        logger.info(f"  💰 Close: ${latest['close']:.2f}")
        
        if has_sma and not pd.isna(latest['sma_21']):
            logger.info(f"  📊 SMA(21): ${latest['sma_21']:.2f}")
        else:
            logger.warning("  📊 SMA(21): Not available")
            
        if has_ema and not pd.isna(latest['ema_9']):
            logger.info(f"  📈 EMA(9): ${latest['ema_9']:.2f}")
        else:
            logger.warning("  📈 EMA(9): Not available")
        
        # Show indicator relationship
        if has_sma and has_ema and not pd.isna(latest['sma_21']) and not pd.isna(latest['ema_9']):
            if latest['ema_9'] > latest['sma_21']:
                logger.info("  🟢 EMA above SMA (Bullish trend)")
            else:
                logger.info("  🔴 EMA below SMA (Bearish trend)")
        
        return df
        
    except Exception as e:
        logger.error(f"❌ Error calculating indicators for {symbol}: {e}")
        return False

def test_signal_detection(fetcher, symbol="SPY"):
    """Test crossover signal detection."""
    logger.info(f"=== TESTING SIGNAL DETECTION FOR {symbol} ===")
    
    try:
        # Get trading signal
        signal = fetcher.get_signal(symbol, multiplier=5, days_back=3)
        
        logger.info(f"✅ Signal generated for {symbol}")
        logger.info(f"🎯 Signal: {signal['signal']}")
        logger.info(f"💰 Price: ${signal['price']:.2f}" if signal['price'] else "💰 Price: N/A")
        logger.info(f"📅 Time: {signal['timestamp']}" if signal['timestamp'] else "📅 Time: N/A")
        logger.info(f"📝 Reason: {signal['reason']}")
        
        if 'ema' in signal and 'sma' in signal:
            logger.info(f"📈 EMA(9): ${signal['ema']:.2f}")
            logger.info(f"📊 SMA(21): ${signal['sma']:.2f}")
            
            # Show relationship and signal type
            if signal['ema'] > signal['sma']:
                logger.info("📈 EMA is above SMA (Bullish)")
            else:
                logger.info("📉 EMA is below SMA (Bearish)")
                
            if 'crossover_type' in signal:
                logger.info(f"🔄 Crossover type: {signal['crossover_type']}")
        
        return signal
        
    except Exception as e:
        logger.error(f"❌ Error detecting signal for {symbol}: {e}")
        return False

def test_multiple_symbols(fetcher):
    """Test with multiple symbols - now asks for symbol input."""
    logger.info("=== SYMBOL TESTING ===")
    
    while True:
        try:
            symbol = input("Enter a stock symbol to test (or 'quit' to exit): ").strip().upper()
            
            if symbol in ['QUIT', 'EXIT', 'Q', '']:
                break
            
            logger.info(f"\n--- Testing {symbol} ---")
            
            try:
                signal = fetcher.get_signal(symbol, multiplier=5, days_back=2)
                
                status = "✅" if signal['signal'] != "ERROR" else "❌"
                price_str = f"${signal['price']:.2f}" if signal['price'] else "N/A"
                logger.info(f"{status} {symbol}: {signal['signal']} at {price_str}")
                logger.info(f"📝 Reason: {signal['reason']}")
                
                if 'ema' in signal and 'sma' in signal:
                    logger.info(f"📈 EMA(9): ${signal['ema']:.2f}")
                    logger.info(f"📊 SMA(21): ${signal['sma']:.2f}")
                    trend = "🟢 Bullish" if signal['ema'] > signal['sma'] else "🔴 Bearish"
                    logger.info(f"📈 Trend: {trend}")
                
                # Add delay to avoid rate limiting
                import time
                time.sleep(1)
                
            except Exception as e:
                logger.error(f"❌ Error testing {symbol}: {e}")
            
            print()  # Add spacing between tests
            
        except KeyboardInterrupt:
            break
    
    return {}

def interactive_test(fetcher):
    """Interactive testing mode - now integrated into main function."""
    pass  # This function is no longer needed as it's integrated into main()

def main():
    """Main test function."""
    logger.info(f"🚀 Starting Polygon Data Fetcher Test at {datetime.now()}")
    
    # Test API connection
    fetcher = test_api_connection()
    if not fetcher:
        return
    
    # Ask for symbol to test
    print("\n" + "="*50)
    print("📊 POLYGON API STOCK TESTER")
    print("="*50)
    
    while True:
        try:
            test_symbol = input("\nEnter a stock symbol to test (e.g., SPY, AAPL) or 'quit' to exit: ").strip().upper()
            
            if test_symbol in ['QUIT', 'EXIT', 'Q', '']:
                break
            
            print(f"\n🔍 Testing {test_symbol}...")
            
            # Test data fetching
            df = test_data_fetching(fetcher, test_symbol)
            if df is False:
                logger.error(f"❌ Data fetching failed for {test_symbol}")
                continue
            
            # Test indicators
            df_with_indicators = test_indicators(fetcher, test_symbol)
            if df_with_indicators is False:
                logger.error(f"❌ Indicator calculation failed for {test_symbol}")
                continue
            
            # Test signal detection
            signal = test_signal_detection(fetcher, test_symbol)
            if signal is False:
                logger.error(f"❌ Signal detection failed for {test_symbol}")
                continue
            
            # Show summary
            print(f"\n🎯 SUMMARY FOR {test_symbol}:")
            print(f"   Signal: {signal['signal']}")
            print(f"   Price: ${signal['price']:.2f}" if signal['price'] else "   Price: N/A")
            print(f"   Reason: {signal['reason']}")
            
            if 'ema' in signal and 'sma' in signal:
                print(f"   EMA(9): ${signal['ema']:.2f}")
                print(f"   SMA(21): ${signal['sma']:.2f}")
                trend = "🟢 Bullish" if signal['ema'] > signal['sma'] else "🔴 Bearish"
                print(f"   Trend: {trend}")
            
            # Add delay to avoid rate limiting
            import time
            time.sleep(1)
            
        except KeyboardInterrupt:
            break
        except Exception as e:
            logger.error(f"❌ Error testing {test_symbol}: {e}")
    
    logger.info("🎉 Testing completed!")

if __name__ == "__main__":
    # Import pandas here to avoid import issues
    import pandas as pd
    main()
