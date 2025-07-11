import json
import os
from typing import Dict, Any, Optional

class ConfigManager:
    """
    Manages reading and writing configuration data, specifically for persisting bot values.
    """
    
    def __init__(self, config_path: str = None):
        """
        Initialize the ConfigManager.
        
        :param config_path: Path to the config.json file
        """
        if config_path is None:
            config_path = os.getenv('CONFIG_PATH')
            if not config_path:
                raise ValueError("CONFIG_PATH environment variable is not set")
        
        self.config_path = config_path
        self.config_data = None
        self.load_config()
    
    def load_config(self) -> Dict[str, Any]:
        """
        Load configuration from the JSON file.
        
        :return: Configuration dictionary
        """
        try:
            with open(self.config_path, 'r') as f:
                self.config_data = json.load(f)
            return self.config_data
        except FileNotFoundError:
            raise FileNotFoundError(f"Config file not found: {self.config_path}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON in config file: {e}")
    
    def save_config(self) -> None:
        """
        Save the current configuration back to the JSON file.
        """
        try:
            with open(self.config_path, 'w') as f:
                json.dump(self.config_data, f, indent=2)
        except Exception as e:
            raise RuntimeError(f"Failed to save config file: {e}")
    
    def get_bot_config(self, symbol: str) -> Optional[Dict[str, Any]]:
        """
        Get configuration for a specific bot by symbol.
        
        :param symbol: Stock symbol (e.g., 'SPY', 'QQQ')
        :return: Bot configuration dictionary or None if not found
        """
        if not self.config_data:
            self.load_config()
        
        for bot in self.config_data.get('bots', []):
            if bot.get('symbol') == symbol:
                return bot
        return None
    
    def get_current_value(self, symbol: str) -> Optional[float]:
        """
        Get the current persisted value for a symbol.
        
        :param symbol: Stock symbol
        :return: Current value or None if not found
        """
        bot_config = self.get_bot_config(symbol)
        if bot_config:
            return bot_config.get('current_value')
        return None
    
    def update_current_value(self, symbol: str, new_value: float) -> bool:
        """
        Update the current value for a symbol and persist to file.
        
        :param symbol: Stock symbol
        :param new_value: New value to persist
        :return: True if successful, False otherwise
        """
        try:
            if not self.config_data:
                self.load_config()
            
            # Find and update the bot configuration
            for bot in self.config_data.get('bots', []):
                if bot.get('symbol') == symbol:
                    bot['current_value'] = round(new_value, 2)
                    
                    # Save to file
                    self.save_config()
                    return True
            
            return False  # Symbol not found
            
        except Exception as e:
            print(f"Error updating current value for {symbol}: {e}")
            return False
    
    def get_all_bot_symbols(self) -> list:
        """
        Get a list of all bot symbols in the configuration.
        
        :return: List of symbols
        """
        if not self.config_data:
            self.load_config()
        
        return [bot.get('symbol') for bot in self.config_data.get('bots', []) if bot.get('symbol')]
    
    def get_bot_config_by_id(self, bot_id: int) -> Optional[Dict[str, Any]]:
        """
        Get configuration for a specific bot by ID.
        
        :param bot_id: Bot ID (e.g., 1, 2, 3)
        :return: Bot configuration dictionary or None if not found
        """
        if not self.config_data:
            self.load_config()
        
        for bot in self.config_data.get('bots', []):
            if bot.get('id') == bot_id:
                return bot
        return None
    
    def get_all_bot_ids(self) -> list:
        """
        Get a list of all bot IDs in the configuration.
        
        :return: List of bot IDs
        """
        if not self.config_data:
            self.load_config()
        
        return [bot.get('id') for bot in self.config_data.get('bots', []) if bot.get('id') is not None]
    
    def update_current_value_by_id(self, bot_id: int, new_value: float) -> bool:
        """
        Update the current value for a bot by ID and persist to file.
        
        :param bot_id: Bot ID
        :param new_value: New value to persist
        :return: True if successful, False otherwise
        """
        try:
            if not self.config_data:
                self.load_config()
            
            # Find and update the bot configuration by ID
            for bot in self.config_data.get('bots', []):
                if bot.get('id') == bot_id:
                    bot['current_value'] = round(new_value, 2)
                    
                    # Save to file
                    self.save_config()
                    return True
            
            return False  # Bot ID not found
            
        except Exception as e:
            print(f"Error updating current value for bot ID {bot_id}: {e}")
            return False
    
    def get_current_value_by_id(self, bot_id: int) -> Optional[float]:
        """
        Get the current persisted value for a bot by ID.
        
        :param bot_id: Bot ID
        :return: Current value or None if not found
        """
        bot_config = self.get_bot_config_by_id(bot_id)
        if bot_config:
            return bot_config.get('current_value')
        return None


# Example usage functions
def update_bot_value(symbol: str, new_value: float, config_path: str = None) -> bool:
    """
    Convenience function to update a bot's current value.
    
    :param symbol: Stock symbol
    :param new_value: New value to persist
    :param config_path: Path to config file
    :return: True if successful
    """
    config_manager = ConfigManager(config_path)
    return config_manager.update_current_value(symbol, new_value)

def get_bot_current_value(symbol: str, config_path: str = None) -> Optional[float]:
    """
    Convenience function to get a bot's current value.
    
    :param symbol: Stock symbol
    :param config_path: Path to config file
    :return: Current value or None
    """
    config_manager = ConfigManager(config_path)
    return config_manager.get_current_value(symbol)


if __name__ == "__main__":
    # Example usage
    config_manager = ConfigManager()
    
    # Get current value for SPY
    spy_value = config_manager.get_current_value("SPY")
    print(f"Current SPY value: ${spy_value}")
    
    # Update value (example: gained $50)
    if spy_value:
        new_value = spy_value + 50
        success = config_manager.update_current_value("SPY", new_value)
        print(f"Updated SPY value to ${new_value}: {'Success' if success else 'Failed'}")
    
    # Get updated value
    updated_value = config_manager.get_current_value("SPY")
    print(f"Updated SPY value: ${updated_value}")
