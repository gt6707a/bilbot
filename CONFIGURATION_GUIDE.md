# Configuration System

The trading bot system now supports JSON-based configuration for running multiple bots concurrently with different parameters and algorithms.

## Configuration File Structure

The `config.json` file contains:

### Global Settings
- `check_interval`: How often to check market conditions (seconds)
- `paper_trading`: Whether to use paper trading (always true for safety)
- `log_level`: Logging verbosity (DEBUG, INFO, WARNING, ERROR)
- `market_timezone`: Timezone for market hours

### Bot Configurations
Each bot in the `bots` array supports:
- `symbol`: Stock/ETF symbol to trade
- `algorithm`: Algorithm to use (currently "sma_ema_crossover")
- `interval_minutes`: How often to recalculate signals
- `initial_value`: Starting portfolio value
- `signal_timespan`: Timespan for signal data ("minute", "hour", "day")
- `signal_multiplier`: Multiplier for signal timespan
- `signal_days_back`: Days of historical data to analyze
- `daily_pnl_threshold`: Daily loss limit (negative decimal, e.g., -0.05 = -5%)
- `daily_gain_target`: Daily gain target (positive decimal, e.g., 0.10 = 10%)
- `description`: Human-readable description of the bot configuration

## Running the System

### Run All Bots
```bash
python bling.py
```
This starts all configured bots in separate threads.

### Run a Single Bot (for testing)
```bash
python run_single_bot.py SPY
```
This runs only the bot configured for the specified symbol.

## Adding New Algorithms

1. Create your algorithm class following the interface in `sma_ema_crossover_algo.py`
2. Add it to the `ALGORITHMS` dictionary in `bling.py`
3. Update your bot configurations to use the new algorithm name

## Example Algorithm Interface

```python
class MyAlgorithm:
    def __init__(self):
        # Initialize your algorithm
        pass
    
    def get_signal(self, symbol, timespan, multiplier, days_back):
        # Return 'BUY', 'SELL', or None
        # The bot will handle signal persistence
        pass
```

## Safety Features

- All trading is done in paper mode by default
- Daily P&L limits prevent excessive losses
- Market hours checking prevents after-hours trading
- Signal persistence ensures consistent trading decisions
- Individual bot error handling prevents system-wide failures

## Monitoring

Each bot logs its activities with the symbol prefix, making it easy to track multiple bots in the combined log output.
