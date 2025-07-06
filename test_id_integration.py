#!/usr/bin/env python3
"""
Test script for ID-based bot initialization and configuration system.
"""

from config_manager import ConfigManager
from bling_bot import BlingBot
from bling import create_bot_from_config_id
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_config_manager_id_functions():
    """Test ConfigManager ID-based functions"""
    print("🧪 Testing ConfigManager ID functions...")
    
    config_manager = ConfigManager()
    
    # Test getting all bot IDs
    bot_ids = config_manager.get_all_bot_ids()
    print(f"   Bot IDs found: {bot_ids}")
    
    if not bot_ids:
        print("   ❌ No bot IDs found in config")
        return False
    
    # Test getting bot config by ID
    bot_id = bot_ids[0]
    bot_config = config_manager.get_bot_config_by_id(bot_id)
    print(f"   Bot config for ID {bot_id}: {bot_config}")
    
    # Test getting current value by ID
    current_value = config_manager.get_current_value_by_id(bot_id)
    print(f"   Current value for ID {bot_id}: ${current_value:.2f}")
    
    # Test updating current value by ID
    new_value = current_value + 25.0
    success = config_manager.update_current_value_by_id(bot_id, new_value)
    print(f"   Update value to ${new_value:.2f}: {'✅ Success' if success else '❌ Failed'}")
    
    # Verify the update
    updated_value = config_manager.get_current_value_by_id(bot_id)
    print(f"   Verified persisted value: ${updated_value:.2f}")
    
    return success and updated_value == new_value

def test_bot_creation_from_id():
    """Test creating bots from config ID"""
    print("\n🤖 Testing bot creation from config ID...")
    
    config_manager = ConfigManager()
    bot_ids = config_manager.get_all_bot_ids()
    
    if not bot_ids:
        print("   ❌ No bot IDs found")
        return False
    
    success = True
    for bot_id in bot_ids:
        try:
            print(f"   Creating bot from ID {bot_id}...")
            bot = BlingBot.from_config_id(bot_id)
            
            print(f"   ✅ Bot created successfully:")
            print(f"      ID: {bot.bot_id}")
            print(f"      Symbol: {bot.symbol}")
            print(f"      Initial value: ${bot.initial_value:.2f}")
            print(f"      Current value: ${bot.current_value:.2f}")
            print(f"      Algorithm: {bot.algo.__class__.__name__}")
            print(f"      Interval: {bot.interval_minutes} minutes")
            
        except Exception as e:
            print(f"   ❌ Failed to create bot ID {bot_id}: {e}")
            success = False
    
    return success

def test_bling_integration():
    """Test bling.py integration with ID-based creation"""
    print("\n🎯 Testing bling.py integration...")
    
    config_manager = ConfigManager()
    bot_ids = config_manager.get_all_bot_ids()
    
    if not bot_ids:
        print("   ❌ No bot IDs found")
        return False
    
    success = True
    for bot_id in bot_ids:
        try:
            print(f"   Creating bot via bling.py from ID {bot_id}...")
            bot = create_bot_from_config_id(bot_id)
            
            print(f"   ✅ Bot created through bling.py:")
            print(f"      ID: {bot.bot_id}")
            print(f"      Symbol: {bot.symbol}")
            print(f"      Current value: ${bot.current_value:.2f}")
            
        except Exception as e:
            print(f"   ❌ Failed to create bot via bling.py ID {bot_id}: {e}")
            success = False
    
    return success

def test_value_persistence():
    """Test that value updates persist correctly"""
    print("\n💾 Testing value persistence...")
    
    config_manager = ConfigManager()
    bot_ids = config_manager.get_all_bot_ids()
    
    if not bot_ids:
        print("   ❌ No bot IDs found")
        return False
    
    bot_id = bot_ids[0]
    
    # Create a bot
    bot = BlingBot.from_config_id(bot_id)
    original_value = bot.current_value
    
    # Update the value
    new_value = original_value + 50.0
    print(f"   Original value: ${original_value:.2f}")
    print(f"   Updating to: ${new_value:.2f}")
    
    bot._update_current_value(new_value)
    
    # Create a new bot instance and verify it loads the updated value
    bot2 = BlingBot.from_config_id(bot_id)
    loaded_value = bot2.current_value
    
    print(f"   New bot loaded value: ${loaded_value:.2f}")
    
    success = abs(loaded_value - new_value) < 0.01
    print(f"   Persistence test: {'✅ Passed' if success else '❌ Failed'}")
    
    return success

def main():
    """Run all tests"""
    print("🚀 Starting ID-based bot initialization tests...\n")
    
    tests = [
        ("ConfigManager ID Functions", test_config_manager_id_functions),
        ("Bot Creation from ID", test_bot_creation_from_id),
        ("Bling.py Integration", test_bling_integration),
        ("Value Persistence", test_value_persistence),
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"   ❌ Test failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n📊 Test Results:")
    all_passed = True
    for test_name, passed in results:
        status = "✅ PASSED" if passed else "❌ FAILED"
        print(f"   {test_name}: {status}")
        if not passed:
            all_passed = False
    
    print(f"\n🏁 Overall result: {'✅ ALL TESTS PASSED' if all_passed else '❌ SOME TESTS FAILED'}")
    return all_passed

if __name__ == "__main__":
    main()
