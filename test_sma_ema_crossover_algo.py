#!/usr/bin/env python3
def test_get_signal():
    """Test the get_signal method of SmaEmaCrossoverAlgo"""
    from sma_ema_crossover_algo import SmaEmaCrossoverAlgo
    from sma_ema_crossover_algo_agg import SmaEmaCrossoverAlgo as SmaEmaCrossoverAlgoAgg

    algo = SmaEmaCrossoverAlgo()
    algo_agg = SmaEmaCrossoverAlgoAgg()
    symbol = 'SPY'

    # Test get_signal with no previous signal
    signal = algo.get_signal(symbol)
    signal_agg = algo_agg.get_signal(symbol)
    print(f"Initial signal: {signal}")
    print(f"Initial signal (agg): {signal_agg}")

if __name__ == "__main__":
    # Import pandas here to avoid import issues
    test_get_signal()
