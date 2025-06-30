#!/usr/bin/env python3
"""
Test script for the new Polygon Trading Bot with per-symbol equity tracking.
This script tests        # Show value tracki        print(f"💰 Per-Symbol Value: ${result.get('per_symbol_value', 'N/A')}")g details
        if position != 0:
            print("📊 Note: Value reflects current market value of position")
        else:
            print("📊 Note: No position - value shows initial allocation") bot's signal generation and per-symbol equity functionality without executing real trades.
"""

import os
import sys
import time
import logging

# Load environment variables (if available)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    # dotenv not available, continue without it
    pass

# Add current directory to path to import our modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from trading_bot import TradingBot

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('test_polygon_bot')

def test_bot_initialization():
    """Test that the bot initializes correctly"""
    print("\n" + "="*60)
    print("🔧 Testing Bot Initialization")
    print("="*60)
    
    try:
        bot = TradingBot(
            symbol='SPY',
            interval_minutes=5,
            initial_equity=10000,
            paper=True
        )
        print("✅ Bot initialized successfully")
        print(f"   Symbol: {bot.symbol}")
        print(f"   Interval: {bot.interval_minutes} minutes")
        print(f"   Initial Equity: ${bot.initial_equity:,.2f}")
        print(f"   Paper Trading: {bot.paper}")
        return bot
    except Exception as e:
        print(f"❌ Bot initialization failed: {e}")
        return None

def test_signal_generation(bot, symbol='SPY'):
    """Test signal generation"""
    print(f"\n🎯 Testing Signal Generation for {symbol}")
    print("-" * 40)
    
    try:
        # Get a fresh signal
        signal = bot.get_signal()
        
        print(f"📊 Signal: {signal['signal']}")
        print(f"💰 Price: ${signal['price']:.2f}" if signal['price'] else "💰 Price: N/A")
        print(f"📅 Time: {signal['timestamp']}" if signal['timestamp'] else "📅 Time: N/A")
        print(f"📝 Reason: {signal['reason']}")
        
        if 'ema' in signal and 'sma' in signal:
            print(f"📈 EMA(9): ${signal['ema']:.2f}")
            print(f"📊 SMA(21): ${signal['sma']:.2f}")
            
        if 'ema_above_sma' in signal:
            trend = "🟢 Bullish" if signal['ema_above_sma'] else "🔴 Bearish"
            print(f"📈 Trend: {trend}")
        
        return signal
        
    except Exception as e:
        print(f"❌ Signal generation failed: {e}")
        return None

def test_cached_signal(bot):
    """Test cached signal functionality"""
    print(f"\n🔄 Testing Cached Signal")
    print("-" * 40)
    
    try:
        # Get cached signal (should be immediate)
        cached_signal = bot.get_cached_signal()
        print(f"📊 Cached Signal: {cached_signal['signal']}")
        print(f"📝 Reason: {cached_signal['reason']}")
        return cached_signal
    except Exception as e:
        print(f"❌ Cached signal test failed: {e}")
        return None

def test_account_info(bot):
    """Test account information retrieval and per-symbol equity tracking"""
    print(f"\n💼 Testing Account Information & Per-Symbol Equity")
    print("-" * 40)
    
    try:
        equity = bot.get_current_equity()
        pnl = bot.calculate_pnl()
        position = bot.get_open_position()
        
        print(f"💰 Initial Value: ${bot.initial_value:,.2f}")
        print(f"💰 Current Per-Symbol Value: ${equity:,.2f}")
        print(f"💰 Bot.current_value: ${bot.current_value:,.2f}")
        print(f"📊 P&L: {pnl*100:+.2f}%")
        print(f"📈 Position: {position} shares")
        
        # Test value consistency
        if abs(equity - bot.current_value) < 0.01:
            print("✅ Per-symbol value tracking is consistent")
        else:
            print("❌ Per-symbol value tracking inconsistency detected")
            print(f"   get_current_equity(): ${equity:.2f}")
            print(f"   bot.current_value: ${bot.current_value:.2f}")
        
        # Show equity tracking details
        print(f"📈 Current Position: {position} shares")
        if position != 0:
            print("� Note: Equity shows initial value until position is closed (realized P&L)")
        
        return True
    except Exception as e:
        print(f"❌ Account info test failed: {e}")
        return False

def test_trading_cycle(bot):
    """Test a complete trading cycle (without executing trades)"""
    print(f"\n🔄 Testing Trading Cycle")
    print("-" * 40)
    
    try:
        # Run one cycle
        result = bot.run()
        
        print(f"📊 Signal: {result['signal']}")
        print(f"💰 Price: ${result['price']:.2f}" if result['price'] else "💰 Price: N/A")
        print(f"🔄 Trade Executed: {result['trade_executed']}")
        print(f"📊 P&L: {result['pnl']:+.2f}%")
        print(f"� Per-Symbol Equity: ${result.get('per_symbol_equity', 'N/A')}")
        print(f"�🔄 Recalculated: {result['recalculated']}")
        
        return result
    except Exception as e:
        print(f"❌ Trading cycle test failed: {e}")
        return None

def main():
    """Main test function"""
    print("🚀 Polygon Trading Bot Test Suite")
    print("=" * 60)
    
    # Check environment variables
    required_vars = ['POLYGON_API_KEY', 'ALPACA_API_KEY', 'ALPACA_API_SECRET']
    missing_vars = [var for var in required_vars if not os.getenv(var)]
    
    if missing_vars:
        print(f"❌ Missing environment variables: {', '.join(missing_vars)}")
        print("Please set these variables in your .env file")
        return
    
    print("✅ All required environment variables found")
    
    # Test bot initialization
    bot = test_bot_initialization()
    if not bot:
        print("❌ Cannot continue without bot initialization")
        return
    
    # Test signal generation
    signal = test_signal_generation(bot)
    if not signal:
        print("⚠️  Signal generation failed, continuing with other tests")
    
    # Test cached signal
    cached_signal = test_cached_signal(bot)
    
    # Test account info
    account_ok = test_account_info(bot)
    
    # Test trading cycle
    cycle_result = test_trading_cycle(bot)
    
    # Test with different symbols
    test_symbols = ['AAPL', 'MSFT']
    for symbol in test_symbols:
        print(f"\n🧪 Testing with {symbol}")
        print("-" * 30)
        
        # Create bot for this symbol
        try:
            symbol_bot = TradingBot(
                symbol=symbol,
                interval_minutes=5,
                initial_equity=1000,  # Use smaller initial equity for testing
                paper=True
            )
            
            print(f"   Initial value: ${symbol_bot.initial_value:.2f}")
            print(f"   Current value: ${symbol_bot.current_value:.2f}")
            
            signal = test_signal_generation(symbol_bot, symbol)
            
            # Small delay to avoid rate limiting
            time.sleep(1)
            
        except Exception as e:
            print(f"❌ Error testing {symbol}: {e}")
    
    print("\n" + "="*60)
    print("✅ Test Suite Complete")
    print("="*60)
    
    # Summary
    print(f"\n📋 Summary:")
    print(f"   Bot Initialization: {'✅ Pass' if bot else '❌ Fail'}")
    print(f"   Signal Generation: {'✅ Pass' if signal else '❌ Fail'}")
    print(f"   Cached Signal: {'✅ Pass' if cached_signal else '❌ Fail'}")
    print(f"   Account Info: {'✅ Pass' if account_ok else '❌ Fail'}")
    print(f"   Trading Cycle: {'✅ Pass' if cycle_result else '❌ Fail'}")
    
    if signal:
        print(f"\n🎯 Final Signal: {signal['signal']} - {signal['reason']}")

if __name__ == "__main__":
    main()
