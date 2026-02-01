"""
Internationalization (i18n) support module
Supports English, Simplified Chinese, Traditional Chinese
"""

import json
import logging
from pathlib import Path
from typing import Dict, Optional

logger = logging.getLogger(__name__)


class I18n:
    """
    Internationalization manager
    Loads and manages translations for multiple languages
    """
    
    SUPPORTED_LANGUAGES = {
        'en': 'English',
        'zh-CN': '简体中文',
        'zh-TW': '繁體中文',
        'ja': '日本語',
        'ko': '한국어',
        'es': 'Español'
    }
    
    # 语言代码映射表：简化代码 -> 完整代码
    LANGUAGE_CODE_MAPPING = {
        'zh': 'zh-CN',          # 简体中文
        'zh-cn': 'zh-CN',       # 容错：小写
        'zh-Hans': 'zh-CN',     # 简体中文（ISO标准）
        'zh-tw': 'zh-TW',       # 容错：小写
        'zh-Hant': 'zh-TW',     # 繁体中文（ISO标准）
        'en': 'en',             # 英文
        'en-US': 'en',          # 美式英语
        'en-GB': 'en',          # 英式英语
    }
    
    def __init__(self, default_language: str = None):
        """
        Initialize i18n manager
        
        Args:
            default_language: Default language code, None uses system default
        """
        from .language_context import DEFAULT_LANGUAGE
        
        # Use provided language or system default
        lang = default_language if default_language else DEFAULT_LANGUAGE
        
        # Normalize language code using mapping
        self.default_language = self.LANGUAGE_CODE_MAPPING.get(lang, lang)
        self.current_language = self.default_language
        self._translations: Dict[str, Dict[str, str]] = {}
        
        # Load all translations
        self._load_translations()
    
    def _load_translations(self) -> None:
        """Load all language files"""
        locales_dir = Path(__file__).parent.parent / 'locales'
        
        if not locales_dir.exists():
            logger.error(f"Locales directory not found: {locales_dir}")
            return
        
        for lang_code in self.SUPPORTED_LANGUAGES.keys():
            lang_file = locales_dir / f"{lang_code}.json"
            
            if lang_file.exists():
                try:
                    with open(lang_file, 'r', encoding='utf-8') as f:
                        self._translations[lang_code] = json.load(f)
                    logger.info(f"Loaded translations for {lang_code}")
                except Exception as e:
                    logger.error(f"Error loading {lang_code} translations: {e}")
            else:
                logger.warning(f"Translation file not found: {lang_file}")
    
    def set_language(self, language: str) -> bool:
        """
        Set current language
        
        Args:
            language: Language code (en, zh-CN, zh-TW) or simplified code (zh, en)
            
        Returns:
            True if language was set successfully, False otherwise
        """
        # 尝试映射简化的语言代码到完整代码
        mapped_language = self.LANGUAGE_CODE_MAPPING.get(language, language)
        
        if mapped_language in self.SUPPORTED_LANGUAGES:
            self.current_language = mapped_language
            logger.info(f"Language set to: {mapped_language}" + (f" (from {language})" if language != mapped_language else ""))
            return True
        else:
            logger.warning(f"Unsupported language: {language}")
            return False
    
    def get_language(self) -> str:
        """Get current language code"""
        return self.current_language
    
    def get_language_name(self, language: Optional[str] = None) -> str:
        """
        Get language name
        
        Args:
            language: Language code (if None, use current language)
            
        Returns:
            Language name
        """
        lang = language or self.current_language
        return self.SUPPORTED_LANGUAGES.get(lang, lang)
    
    def t(self, key: str, language: Optional[str] = None, **kwargs) -> str:
        """
        Translate a key to current language
        
        Args:
            key: Translation key
            language: Language code (if None, use current language)
            **kwargs: Format parameters
            
        Returns:
            Translated string
        """
        lang = language or self.current_language
        
        # Get translation for the language
        translations = self._translations.get(lang, {})
        text = translations.get(key)
        
        # Fallback to default language
        if text is None and lang != self.default_language:
            translations = self._translations.get(self.default_language, {})
            text = translations.get(key)
        
        # Fallback to key itself
        if text is None:
            logger.warning(f"Translation key not found: {key} for language: {lang}")
            text = key
        
        # Format with parameters
        if kwargs:
            try:
                text = text.format(**kwargs)
            except KeyError as e:
                logger.error(f"Missing format parameter for key '{key}': {e}")
        
        return text
    
    def get_all_languages(self) -> Dict[str, str]:
        """
        Get all supported languages
        
        Returns:
            Dictionary of language code -> language name
        """
        return self.SUPPORTED_LANGUAGES.copy()


# Global i18n instance
_i18n: Optional[I18n] = None


def get_i18n(default_language: str = 'zh-CN') -> I18n:
    """
    Get global i18n instance
    
    Args:
        default_language: Default language code
        
    Returns:
        I18n instance
    """
    global _i18n
    if _i18n is None:
        _i18n = I18n(default_language)
    return _i18n


def t(key: str, language: Optional[str] = None, **kwargs) -> str:
    """
    Shortcut function for translation
    
    Args:
        key: Translation key
        language: Language code (if None, use current language)
        **kwargs: Format parameters
        
    Returns:
        Translated string
    """
    return get_i18n().t(key, language, **kwargs)
