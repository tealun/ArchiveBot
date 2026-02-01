"""
Configuration management module
Supports environment variable override for sensitive information
Priority: Environment Variables > YAML Config
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
        Supports environment variable override for sensitive fields
        
        Priority: Environment Variables > YAML Config
        
        Supported environment variables:
        - BOT_TOKEN: Bot token
        - OWNER_ID: Owner Telegram ID
        - SILENT_SOURCES: Silent archive sources (channel IDs/usernames, JSON or comma-separated)
        - CHANNEL_DEFAULT: Default Telegram channel ID
        - CHANNEL_TEXT: Text channel ID
        - CHANNEL_EBOOK: Ebook channel ID
        - CHANNEL_DOCUMENT: Document channel ID
        - CHANNEL_IMAGE: Image channel ID
        - CHANNEL_MEDIA: Media channel ID
        - CHANNEL_DIRECT_DEFAULT: Direct send default channel ID
        - AI_API_PROVIDER: AI API provider
        - AI_API_KEY: AI API key
        - AI_API_URL: AI API URL
        - AI_MODEL: AI model name
        - AI_REASONING_MODEL: AI reasoning model name
        - AI_EXCLUDE_CHANNELS: AI exclude channel IDs list
        - AI_EXCLUDE_TAGS: AI exclude tags list
        
        Args:
            key: Dot-separated key path (e.g., 'bot.token')
            default: Default value if key not found
            
        Returns:
            Configuration value (from env or YAML)
        """
        # 环境变量映射（敏感信息和频道配置）
        env_mapping = {
            'bot.token': 'BOT_TOKEN',
            'bot.owner_id': 'OWNER_ID',
            'storage.telegram.channels.default': 'CHANNEL_DEFAULT',
            'storage.telegram.channels.text': 'CHANNEL_TEXT',
            'storage.telegram.channels.ebook': 'CHANNEL_EBOOK',
            'storage.telegram.channels.document': 'CHANNEL_DOCUMENT',
            'storage.telegram.channels.image': 'CHANNEL_IMAGE',
            'storage.telegram.channels.media': 'CHANNEL_MEDIA',
            'storage.telegram.channels.note': 'CHANNEL_NOTE',
            'storage.telegram.direct_send.channels.default': 'CHANNEL_DIRECT_DEFAULT',
            'ai.api.provider': 'AI_API_PROVIDER',
            'ai.api.api_key': 'AI_API_KEY',
            'ai.api.api_url': 'AI_API_URL',
            'ai.api.model': 'AI_MODEL',
            'ai.api.reasoning_model': 'AI_REASONING_MODEL',
            'ai.exclude_from_context.channel_ids': 'AI_EXCLUDE_CHANNELS',
            'ai.exclude_from_context.tags': 'AI_EXCLUDE_TAGS',
            'bot.silent_sources': 'SILENT_SOURCES',
        }
        
        # 检查是否有对应的环境变量
        env_var = env_mapping.get(key)
        if env_var:
            env_value = os.getenv(env_var)
            if env_value is not None and env_value != '':
                # 类型转换
                if key == 'bot.owner_id':
                    try:
                        return int(env_value)
                    except ValueError:
                        logger.warning(f"Invalid {env_var} value: {env_value}, using YAML config")
                elif key.startswith('storage.telegram.channels.') or key.startswith('storage.telegram.direct_send.channels.'):
                    try:
                        val = int(env_value)
                        # 0表示未配置，返回None让系统使用默认逻辑
                        return val if val != 0 else None
                    except ValueError:
                        logger.warning(f"Invalid {env_var} value: {env_value}, using YAML config")
                elif key in ['ai.exclude_from_context.channel_ids', 'ai.exclude_from_context.tags', 'bot.silent_sources']:
                    # 处理列表类型的环境变量（JSON格式或逗号分隔）
                    try:
                        import json
                        # 优先尝试JSON格式
                        return json.loads(env_value)
                    except (json.JSONDecodeError, ValueError):
                        # 降级为逗号分隔格式
                        if ',' in env_value:
                            items = [item.strip() for item in env_value.split(',') if item.strip()]
                            # 尝试转换为整数（频道ID）
                            result = []
                            for item in items:
                                try:
                                    result.append(int(item))
                                except ValueError:
                                    result.append(item)  # 保留字符串（用户名）
                            return result
                        logger.warning(f"Invalid {env_var} value: {env_value}, using YAML config")
                else:
                    return env_value
        
        # 从 YAML 配置读取
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
    
    def set(self, key: str, value: Any) -> bool:
        """
        Set configuration value by dot-separated key path
        
        Args:
            key: Dot-separated key path
            value: Value to set
            
        Returns:
            True if successful, False otherwise
        """
        try:
            keys = key.split('.')
            config = self._config
            
            for k in keys[:-1]:
                if k not in config:
                    config[k] = {}
                config = config[k]
            
            config[keys[-1]] = value
            return True
        except Exception as e:
            logger.error(f"Error setting config key {key}: {e}")
            return False
    
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
        """Get Telegram channel ID (backward compatibility)"""
        # 优先使用新配置
        default_channel = self.get('storage.telegram.channels.default')
        if default_channel and default_channel != 0:
            return default_channel
        
        # 向后兼容：使用旧的channel_id
        channel_id = self.get('storage.telegram.channel_id')
        if channel_id and channel_id != 0:
            return channel_id
        return None
    
    @property
    def telegram_channels(self) -> Dict[str, int]:
        """Get all Telegram channel IDs"""
        return self.get('storage.telegram.channels', {})
    
    @property
    def telegram_type_mapping(self) -> Dict[str, str]:
        """Get Telegram type to channel mapping"""
        return self.get('storage.telegram.type_mapping', {})
    
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
