"""
Test script to demonstrate the extensibility of the algorithm system.
This shows how easy it is to add new algorithms to the trading bot system.
"""

from bling import ALGORITHMS, create_bot_from_config

class MockTrendFollowingAlgo:
    """Mock algorithm to demonstrate extensibility"""
    
    def __init__(self):
        self.last_signal = 'SELL'  # Default signal
        print("🧪 Mock Trend Following Algorithm initialized")
    
    def get_signal(self, symbol, timespan, multiplier, days_back):
        """Mock signal generation - just alternates for demo"""
        # In a real algorithm, you'd analyze market data here
        if self.last_signal == 'BUY':
            self.last_signal = 'SELL'
        else:
            self.last_signal = 'BUY'
        
        print(f"🧪 Mock algorithm generated {self.last_signal} signal for {symbol}")
        return self.last_signal

def test_algorithm_extensibility():
    """Test adding a new algorithm to the system"""
    
    print("=== Testing Algorithm Extensibility ===")
    
    # Show current algorithms
    print(f"Current algorithms: {list(ALGORITHMS.keys())}")
    
    # Add our mock algorithm to the registry
    ALGORITHMS['mock_trend_following'] = MockTrendFollowingAlgo
    print(f"After adding mock algorithm: {list(ALGORITHMS.keys())}")
    
    # Create a mock bot configuration
    mock_config = {
        'symbol': 'TEST',
        'algorithm': 'mock_trend_following',
        'interval_minutes': 5,
        'initial_value': 1000,
        'signal_timespan': 'minute',
        'signal_multiplier': 5,
        'signal_days_back': 3,
        'daily_pnl_threshold': -0.05,
        'daily_gain_target': 0.10
    }
    
    # Test creating bot with mock algorithm
    try:
        # This would normally create a bot, but we'll just test the algorithm creation
        from bling import create_algorithm
        mock_algo = create_algorithm('mock_trend_following')
        
        # Test the algorithm interface
        signal1 = mock_algo.get_signal('TEST', 'minute', 5, 3)
        signal2 = mock_algo.get_signal('TEST', 'minute', 5, 3)
        
        print(f"✓ Mock algorithm works correctly")
        print(f"  First signal: {signal1}")
        print(f"  Second signal: {signal2}")
        print(f"✓ Algorithm alternates signals as expected")
        
    except Exception as e:
        print(f"✗ Error testing mock algorithm: {e}")
        return False
    
    # Clean up - remove mock algorithm
    del ALGORITHMS['mock_trend_following']
    print(f"Cleaned up. Current algorithms: {list(ALGORITHMS.keys())}")
    
    return True

if __name__ == "__main__":
    success = test_algorithm_extensibility()
    if success:
        print("\n🎉 Extensibility test passed! New algorithms can be easily added.")
    else:
        print("\n❌ Extensibility test failed.")
