#!/usr/bin/env python3
def test_get_signal():
    """Test the get_signal method of SmaEmaCrossoverAlgo"""
    from sma_ema_crossover_algo import SmaEmaCrossoverAlgo

    algo = SmaEmaCrossoverAlgo()
    symbol = 'SPY'

    # Test get_signal with no previous signal
    signal = algo.get_signal(symbol)
    print(f"Initial signal: {signal}")

if __name__ == "__main__":
    # Import pandas here to avoid import issues
    test_get_signal()
