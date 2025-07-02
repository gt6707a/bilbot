#!/usr/bin/env python3
"""
Simple script to run a single bot for testing purposes.
This is useful for testing individual bot configurations without running all bots.
"""

import json
import sys
from bling import load_config, create_bot_from_config, setup_logging, run_bot

def main():
    if len(sys.argv) != 2:
        print("Usage: python run_single_bot.py <symbol>")
        print("Example: python run_single_bot.py SPY")
        return
    
    symbol = sys.argv[1].upper()
    
    # Load configuration
    config = load_config()
    
    # Find bot configuration for the specified symbol
    bot_config = None
    for bot_cfg in config['bots']:
        if bot_cfg['symbol'].upper() == symbol:
            bot_config = bot_cfg
            break
    
    if not bot_config:
        print(f"No configuration found for symbol: {symbol}")
        print(f"Available symbols: {[bot['symbol'] for bot in config['bots']]}")
        return
    
    # Set up logging
    logger = setup_logging(config['global_settings']['log_level'])
    check_interval = config['global_settings']['check_interval']
    
    # Create and run the bot
    try:
        bot = create_bot_from_config(bot_config)
        logger.info(f"Running single bot for {symbol}")
        run_bot(bot, logger, check_interval)
    except Exception as e:
        logger.error(f"Failed to run bot for {symbol}: {e}")
        raise

if __name__ == "__main__":
    main()
