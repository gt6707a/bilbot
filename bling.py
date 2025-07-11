import os
import time
import json
import pandas as pd
import pytz
import holidays
import logging
from datetime import datetime
from threading import Thread

# Import our trading bot and algorithms
from bling_bot import BlingBot
from config_manager import ConfigManager

# Timezone for NYSE
nyse = pytz.timezone('America/New_York')

def load_config(config_path='config.json'):
    """Load configuration from JSON file"""
    with open(config_path, 'r') as f:
        return json.load(f)

def setup_logging(log_level='INFO'):
    """Setup logging configuration"""
    logging.basicConfig(
        level=getattr(logging, log_level.upper()),
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    return logging.getLogger('bling')

def create_bot_from_config_id(bot_id):
    """Create a BlingBot instance from configuration using bot ID"""
    return BlingBot.from_config_id(bot_id)

def market_is_open():
    """Check if market is open using NYSE hours and holidays"""
    now = pd.Timestamp.now(tz=nyse)
    if now.date() in holidays.NYSE():
        return False
    if now.weekday() >= 5:  # Saturday(5) or Sunday(6)
        return False
    market_open = now.replace(hour=9, minute=30, second=0, microsecond=0)
    market_close = now.replace(hour=16, minute=0, second=0, microsecond=0)
    return market_open <= now <= market_close

def run_bot(bot, logger, check_interval):
    """Run a single bot's trading logic"""
    logger.info(f"Starting bot for {bot.symbol}")
    logger.info(f"💰 Initial equity: ${bot.get_current_equity():.2f}")
    
    trading_active = True
    
    # Monitor market and trade until market closes or limits reached
    while trading_active:
        # Check if market is open - bot's responsibility
        if not market_is_open():
            logger.info(f"Market is closed at {datetime.now(tz=nyse)} for {bot.symbol}")
            # Exit all positions as a safety measure before terminating
            bot.close_position()
            # Break out of the loop which will end the program
            break
            
        # Check risk limits - bot's responsibility
        pnl = bot.calculate_pnl()
        if pnl <= bot.daily_pnl_threshold or pnl >= bot.daily_gain_target:
            logger.info(f"Daily P&L limit reached for {bot.symbol}: {pnl*100:.2f}%")
            bot.close_position()
            trading_active = False
            break
        
        # Let the algorithm run its trading logic
        try:
            bot.run()
        except Exception as e:
            logger.info(f"Error in trading cycle for {bot.symbol}: {str(e)}")
            # Handle reconnection if needed
            if isinstance(e, OSError) and getattr(e, 'errno', None) == 9:  # Bad file descriptor
                logger.info(f"Recreating Alpaca clients for {bot.symbol} due to connection error...")
                bot.reconnect()
        
        time.sleep(check_interval)
    
    # Clean up at end of day
    bot.close_position()
    
    logger.info(f"Trading day complete for {bot.symbol} at {pd.Timestamp.now(tz=nyse)}")
    final_pnl = bot.calculate_pnl()
    logger.info(f"Daily P&L for {bot.symbol}: {final_pnl*100:.2f}%")

def run_multiple_bots(config=None):
    """Run multiple bots concurrently using ID-based configuration"""
    
    # Initialize config manager and get bot IDs
    config_manager = ConfigManager()
    bot_ids = config_manager.get_all_bot_ids()
    
    # Get global settings from config if provided, otherwise load from file
    if config is None:
        config = load_config()
    
    logger = setup_logging(config['global_settings']['log_level'])
    check_interval = int(os.getenv('CHECK_INTERVAL', 600))
    
    logger.info(f"Bling Bot system starting at {pd.Timestamp.now(tz=nyse)}")
    logger.info(f"Found {len(bot_ids)} bot IDs: {bot_ids}")
    
    # Create all bots from configuration using IDs
    bots = []
    for bot_id in bot_ids:
        try:
            bot = create_bot_from_config_id(bot_id)
            bots.append(bot)
            logger.info(f"Created bot ID {bot_id} for {bot.symbol} using {bot.algo.__class__.__name__} algorithm")
        except Exception as e:
            logger.error(f"Failed to create bot for ID {bot_id}: {e}")
    
    if not bots:
        logger.error("No bots created successfully. Exiting.")
        return
    
    # Start threads for each bot
    threads = []
    for bot in bots:
        thread = Thread(target=run_bot, args=(bot, logger, check_interval))
        thread.daemon = True
        threads.append(thread)
        thread.start()
    
    # Wait for all threads to complete
    for thread in threads:
        thread.join()
    
    logger.info("All bots have completed trading.")

if __name__ == "__main__":
    try:
        run_multiple_bots()
    except Exception as e:
        logger = setup_logging()
        logger.error(f"Failed to start bot system: {e}")
        raise
