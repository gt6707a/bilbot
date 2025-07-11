import os
import logging
from datetime import datetime
from alpaca.trading.client import TradingClient
from alpaca.trading.requests import MarketOrderRequest
from alpaca.trading.enums import OrderSide, TimeInForce
from sma_ema_crossover_algo import SmaEmaCrossoverAlgo
from config_manager import ConfigManager

class BlingBot:
    """
    Trading bot that uses pluggable trading algorithms for signal generation and Alpaca for trade execution.
    Uses per-symbol value tracking: starts with initial_value, updates based on position market value.
    """
    
    @classmethod
    def from_config_id(cls, bot_id: int, config_path: str = "config.json"):
        """
        Create a BlingBot instance from configuration using bot ID.
        
        :param bot_id: Bot ID from config.json
        :param config_path: Path to config file
        :return: BlingBot instance
        """
        config_manager = ConfigManager(config_path)
        bot_config = config_manager.get_bot_config_by_id(bot_id)
        
        if not bot_config:
            raise ValueError(f"Bot with ID {bot_id} not found in config")
        
        # Import algorithm class
        from sma_ema_crossover_algo import SmaEmaCrossoverAlgo
        from sma_ema_crossover_algo_agg import SmaEmaCrossoverAlgoAgg
        
        # Create algorithm instance
        algorithm_map = {
            'sma_ema_crossover': SmaEmaCrossoverAlgo,
            'sma_ema_crossover_agg': SmaEmaCrossoverAlgoAgg
        }
        
        algorithm_name = bot_config.get('algorithm', 'sma_ema_crossover')
        if algorithm_name not in algorithm_map:
            raise ValueError(f"Unknown algorithm: {algorithm_name}")
        
        algorithm = algorithm_map[algorithm_name]()
        
        # Create bot instance with config parameters
        return cls(
            bot_id=bot_id,
            symbol=bot_config['symbol'],
            interval_minutes=bot_config.get('interval_minutes', 5),
            initial_value=bot_config.get('initial_value', 1000),
            paper=True,  # Always use paper trading for safety
            algorithm=algorithm,
            signal_timespan=bot_config.get('signal_timespan', 'minute'),
            signal_multiplier=bot_config.get('signal_multiplier', 5),
            signal_days_back=bot_config.get('signal_days_back', 3),
            daily_pnl_threshold=bot_config.get('daily_pnl_threshold', -0.05),
            daily_gain_target=bot_config.get('daily_gain_target', 0.10)
        )
    
    def __init__(self, symbol, interval_minutes=5, initial_value=1000, paper=True, algorithm=None, 
                 signal_timespan='minute', signal_multiplier=5, signal_days_back=3,
                 daily_pnl_threshold=-0.05, daily_gain_target=0.10, bot_id=None):
        """
        Initialize the trading bot.
        
        :param symbol: The trading symbol (e.g., 'SPY')
        :param interval_minutes: How often (in minutes) to recalculate the signal
        :param initial_value: Dollar amount to begin the day with
        :param paper: Whether to use paper trading
        :param algorithm: Trading algorithm instance (defaults to SmaEmaCrossoverAlgo)
        :param signal_timespan: Timespan for signal calculation ('minute', 'hour', 'day')
        :param signal_multiplier: Multiplier for timespan (5 for 5-minute intervals)
        :param signal_days_back: Number of days of data to use for signal calculation
        :param daily_pnl_threshold: Daily loss limit (negative value, e.g., -0.05 for -5%)
        :param daily_gain_target: Daily gain target (positive value, e.g., 0.10 for 10%)
        :param bot_id: Bot ID from config.json (optional, used for persistence)
        """
        # Configure logging
        self.logger = logging.getLogger(__name__)
        if not self.logger.handlers:
            logging.basicConfig(
                level=logging.INFO,
                format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
        
        # Trading parameters
        self.symbol = symbol
        self.bot_id = bot_id
        self.interval_minutes = interval_minutes
        self.initial_value = initial_value
        self.current_value = initial_value
        self.paper = paper
        
        # Signal parameters
        self.signal_timespan = signal_timespan
        self.signal_multiplier = signal_multiplier
        self.signal_days_back = signal_days_back
        
        # Risk management
        self.daily_pnl_threshold = daily_pnl_threshold
        self.daily_gain_target = daily_gain_target
        
        # Signal caching
        self.last_signal_time = None
        self.cached_signal = None
        
        # Current position tracking
        self.current_position = 0
        
        # Initialize config manager for value persistence
        self.config_manager = ConfigManager()
        
        # Load persisted current value if available, otherwise use initial_value
        if self.bot_id is not None:
            persisted_value = self.config_manager.get_current_value_by_id(self.bot_id)
        else:
            persisted_value = self.config_manager.get_current_value(symbol)
            
        if persisted_value is not None:
            self.current_value = persisted_value
            self.logger.info(f"Loaded persisted current value: ${self.current_value:.2f}")
        else:
            self.current_value = initial_value
            self.logger.info(f"No persisted value found, using initial value: ${self.current_value:.2f}")
        
        # Initialize trading algorithm
        try:
            self.algo = algorithm or SmaEmaCrossoverAlgo()
            self.logger.info("✅ Trading algorithm initialized")
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize trading algorithm: {e}")
            raise
        
        # Initialize Alpaca trading client
        self.api_key = os.getenv('ALPACA_API_KEY') or os.getenv('ALPACA_KEY')
        self.api_secret = os.getenv('ALPACA_API_SECRET') or os.getenv('ALPACA_SECRET')
        
        if not self.api_key or not self.api_secret:
            raise ValueError("ALPACA_API_KEY/ALPACA_KEY and ALPACA_API_SECRET/ALPACA_SECRET environment variables must be set")
        
        try:
            self.trading_client = TradingClient(
                api_key=self.api_key,
                secret_key=self.api_secret,
                paper=self.paper
            )
            self.logger.info(f"✅ Alpaca trading client initialized ({'paper' if self.paper else 'live'} trading)")
        except Exception as e:
            self.logger.error(f"❌ Failed to initialize Alpaca client: {e}")
            raise
        
        self.logger.info(f"🤖 BlingBot initialized for {symbol}")
        self.logger.info(f"   Initial value: ${self.current_value:.2f}")
        self.logger.info(f"   Signal interval: {interval_minutes} minutes")
        self.logger.info(f"   Signal parameters: {signal_multiplier}-{signal_timespan}, {signal_days_back} days back")
        self.logger.info(f"   Risk management: {daily_pnl_threshold*100:.1f}% loss limit, {daily_gain_target*100:.1f}% gain target")
        self.logger.info(f"   Trading mode: {'Paper' if paper else 'Live'}")
    
    def load_config(self):
        """Load configuration from file"""
        try:
            config = self.config_manager.load_config()
            self.current_value = config.get('current_value', self.initial_value)
            self.logger.info(f"🔧 Config loaded: current_value=${self.current_value:.2f}")
        except Exception as e:
            self.logger.warning(f"❌ Error loading config: {e} - using initial values")
    
    def save_config(self):
        """Save configuration to file"""
        try:
            self.config_manager.save_config({
                'current_value': self.current_value
            })
            self.logger.info("💾 Config saved")
        except Exception as e:
            self.logger.error(f"❌ Error saving config: {e}")
    
    def _update_current_value(self, new_value):
        """Update current_value and persist to config"""
        if abs(new_value - self.current_value) > 0.01:  # Only update if significant change
            self.current_value = new_value
            
            # Use bot_id if available, otherwise fallback to symbol
            if self.bot_id is not None:
                self.config_manager.update_current_value_by_id(self.bot_id, new_value)
            else:
                self.config_manager.update_current_value(self.symbol, new_value)
                
            self.logger.debug(f"Updated and persisted current value: ${self.current_value:.2f}")
    
    def reconnect(self):
        """Reconnect to Alpaca API (for error recovery)"""
        try:
            self.trading_client = TradingClient(
                api_key=self.api_key,
                secret_key=self.api_secret,
                paper=self.paper
            )
            self.logger.info("✅ Alpaca client reconnected")
        except Exception as e:
            self.logger.error(f"❌ Failed to reconnect Alpaca client: {e}")
            raise
    
    def _should_recalculate(self):
        """Check if it's time to recalculate the signal"""
        if self.last_signal_time is None:
            return True
        
        time_since_last = datetime.now() - self.last_signal_time
        return time_since_last.total_seconds() >= (self.interval_minutes * 60)
    
    def get_signal(self):
        """Get fresh trading signal from the configured algorithm"""
        try:
            self.logger.info(f"🔄 Fetching fresh signal for {self.symbol}")
            
            # Get signal from trading algorithm
            signal_info = self.algo.get_signal(
                symbol=self.symbol
            )
            
            # Cache the signal
            self.cached_signal = signal_info
            self.last_signal_time = datetime.now()
            
            self.logger.info(f"📊 Signal: {signal_info['signal']} - {signal_info['reason']}")
            
            return signal_info
            
        except Exception as e:
            self.logger.error(f"❌ Error getting signal: {e}")
            return {
                'signal': 'SELL',  # Default to SELL signal on error
                'price': None,
                'reason': str(e),
                'timestamp': None
            }
    
    def get_cached_signal(self):
        """Get the last cached signal"""
        if self.cached_signal is None:
            return self.get_signal()
        return self.cached_signal
    
    def get_current_equity(self):
        """Get current per-symbol value"""
        self.get_open_position()
        return float(self.current_value)
    
    def calculate_pnl(self):
        """Calculate daily P&L percentage"""
        return (self.current_value - self.initial_value) / self.initial_value
    
    def get_open_position(self):
        """
        Get current open position for the symbol and update current_position and current_value.
        Returns position quantity or 0 if no position exists.
        """
        try:
            position = self.trading_client.get_open_position(self.symbol)
            qty = float(position.qty)
            self.current_position = qty
            
            # Update current_value using market_value from position
            if position.market_value:
                market_value = float(position.market_value)
                new_value = abs(market_value)  # Use abs for short positions
                self._update_current_value(new_value)
                self.logger.debug(f"Open position: {qty} shares, Market value: ${market_value:.2f}")
            else:
                self.logger.debug(f"Open position: {qty} shares (no market value)")
            
            return qty
        except Exception:
            # No position exists - reset to initial value
            self.current_position = 0
            self._update_current_value(self.initial_value)
            self.logger.debug("No open position - reset to initial value")
            return 0
    
    def close_position(self):
        """Close current position using Alpaca's close_position method"""
        try:
            # Use Alpaca's close_position method - it handles checking if position exists
            close_response = self.trading_client.close_position(symbol_or_asset_id=self.symbol)
            
            if hasattr(close_response, 'order_id') and close_response.order_id:
                self.logger.info(f"✅ Position close order submitted: {close_response.order_id}")
            else:
                self.logger.info(f"✅ Position close request submitted for {self.symbol}")
            
            # Reset position tracking - current_value will be updated on next get_open_position call
            self.current_position = 0
            
            return True
            
        except Exception as e:
            self.logger.error(f"❌ Error closing position: {e}")
            return False
    
    def execute_trade(self, signal):
        """Execute trade based on signal"""
        try:
            # Update current position
            current_position = self.get_open_position()
            
            # Handle BUY signal
            if signal['signal'] == 'BUY':
                if current_position == 0:  # No position, can buy
                    order_data = MarketOrderRequest(
                        symbol=self.symbol,
                        notional=str(self.current_value),
                        side=OrderSide.BUY,
                        time_in_force=TimeInForce.DAY
                    )
                    
                    self.trading_client.submit_order(order_data=order_data)
                    self.logger.info(f"✅ BUY order submitted: ${self.current_value:.2f} of {self.symbol}")
                    return True
                else:
                    self.logger.info(f"Already have position of {current_position} shares, skipping BUY")
                    return False

            # Handle SELL signal
            elif signal['signal'] == 'SELL':
                if current_position > 0:  # Have long position, can sell
                    self.logger.info(f"SELL signal received, closing position of {current_position} shares")
                    return self.close_position()
                else:
                    self.logger.info(f"No position to sell for {self.symbol}")
                    return False

            return False
            
        except Exception as e:
            self.logger.error(f"❌ Error executing trade: {e}")
            return False
    
    def run(self):
        """Run one trading cycle"""
        try:
            # Update position info and per-symbol equity
            self.get_open_position()
            
            # Check if we need to recalculate the signal
            if not self._should_recalculate():
                # Not time to recalculate yet, return cached signal
                cached_signal = self.get_cached_signal()
                return {
                    'signal': cached_signal['signal'],
                    'price': cached_signal.get('price'),
                    'trade_executed': False,
                    'pnl': self.calculate_pnl() * 100,  # Return as percentage
                    'per_symbol_value': self.current_value,
                    'recalculated': False
                }
            
            # Time to recalculate - get a fresh signal
            signal = self.get_signal()
            
            # Execute trade based on signal
            trade_executed = self.execute_trade(signal)
            
            return {
                'signal': signal['signal'],
                'price': signal.get('price'),
                'trade_executed': trade_executed,
                'pnl': self.calculate_pnl() * 100,  # Return as percentage
                'per_symbol_value': self.current_value,
                'recalculated': True
            }
            
        except Exception as e:
            self.logger.error(f"❌ Error in trading cycle: {e}")
            return {
                'signal': 'SELL',  # Default to SELL signal on error
                'price': None,
                'trade_executed': False,
                'pnl': 0,
                'per_symbol_value': self.current_value,
                'recalculated': False
            }
