"""
Configuration management module
"""

import os
import yaml
from pathlib import Path
from typing import Any, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class Config:
    """
    Configuration manager for ArchiveBot
    Loads configuration from YAML file
    """
    
    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize configuration
        
        Args:
            config_path: Path to config file (default: config/config.yaml)
        """
        if config_path is None:
            # Get project root directory
            project_root = Path(__file__).parent.parent.parent
            config_path = project_root / "config" / "config.yaml"
        
        self.config_path = Path(config_path)
        self._config: Dict[str, Any] = {}
        self.load()
    
    def load(self) -> None:
        """Load configuration from YAML file"""
        try:
            if not self.config_path.exists():
                raise FileNotFoundError(
                    f"Configuration file not found: {self.config_path}\n"
                    f"Please copy config.template.yaml to config.yaml and configure it."
                )
            
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self._config = yaml.safe_load(f) or {}
            
            logger.info(f"Configuration loaded from {self.config_path}")
            
            # Validate required fields
            self._validate()
            
        except FileNotFoundError as e:
            logger.error(f"Config file not found: {e}")
            raise
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML config: {e}")
            raise
        except Exception as e:
            logger.error(f"Error loading config: {e}", exc_info=True)
            raise
    
    def _validate(self) -> None:
        """Validate required configuration fields"""
        required_fields = [
            ('bot', 'token'),
            ('bot', 'owner_id'),
            ('storage', 'database', 'path'),
        ]
        
        for field_path in required_fields:
            value = self.get('.'.join(field_path))
            if value is None or value == "" or value == 0:
                raise ValueError(
                    f"Required configuration field is missing or empty: {'.'.join(field_path)}"
                )
        
        # Validate bot token format
        token = self.get('bot.token')
        if not token or token == "YOUR_BOT_TOKEN_HERE":
            raise ValueError(
                "Invalid bot token. Please configure your bot token from @BotFather"
            )
        
        # Validate owner ID
        owner_id = self.get('bot.owner_id')
        if not isinstance(owner_id, int) or owner_id <= 0:
            raise ValueError(
                "Invalid owner_id. Please configure your Telegram user ID from @userinfobot"
            )
        
        logger.info("Configuration validation passed")
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by dot-separated key path
        
        Args:
            key: Dot-separated key path (e.g., 'bot.token')
            default: Default value if key not found
            
        Returns:
            Configuration value
        """
        keys = key.split('.')
        value = self._config
        
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
            
            if value is None:
                return default
        
        return value
    
    def set(self, key: str, value: Any) -> None:
        """
        Set configuration value by dot-separated key path
        
        Args:
            key: Dot-separated key path
            value: Value to set
        """
        keys = key.split('.')
        config = self._config
        
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]
        
        config[keys[-1]] = value
    
    def save(self) -> None:
        """Save configuration to YAML file"""
        try:
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(self._config, f, default_flow_style=False, allow_unicode=True)
            
            logger.info(f"Configuration saved to {self.config_path}")
            
        except Exception as e:
            logger.error(f"Error saving config: {e}", exc_info=True)
            raise
    
    @property
    def bot_token(self) -> str:
        """Get bot token"""
        return self.get('bot.token')
    
    @property
    def owner_id(self) -> int:
        """Get owner ID"""
        return self.get('bot.owner_id')
    
    @property
    def language(self) -> str:
        """Get language setting"""
        return self.get('bot.language', 'zh-CN')
    
    @property
    def database_path(self) -> str:
        """Get database path"""
        return self.get('storage.database.path', 'data/archive.db')
    
    @property
    def telegram_channel_id(self) -> Optional[int]:
        """Get Telegram channel ID"""
        channel_id = self.get('storage.telegram.channel_id')
        if channel_id and channel_id != 0:
            return channel_id
        return None
    
    @property
    def telegram_storage_enabled(self) -> bool:
        """Check if Telegram storage is enabled"""
        return self.get('storage.telegram.enabled', True) and self.telegram_channel_id is not None
    
    @property
    def ai(self) -> Dict[str, Any]:
        """Get AI configuration"""
        return self.get('ai', {})


# Global config instance
_config: Optional[Config] = None


def get_config(config_path: Optional[str] = None) -> Config:
    """
    Get global configuration instance
    
    Args:
        config_path: Path to config file (only used for first call)
        
    Returns:
        Config instance
    """
    global _config
    if _config is None:
        _config = Config(config_path)
    return _config


def reload_config() -> Config:
    """
    Reload configuration from file
    
    Returns:
        Reloaded Config instance
    """
    global _config
    if _config is not None:
        _config.load()
    return get_config()
