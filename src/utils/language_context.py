"""
Language Context Manager

Manages user language preferences and provides language-aware context throughout the application.
Solves the problem of language consistency across UI, AI prompts, and business logic.
"""

import logging
from typing import Optional, Dict, Any
from telegram.ext import ContextTypes
from .config import get_config

logger = logging.getLogger(__name__)

# System default language
DEFAULT_LANGUAGE = 'en'


class LanguageContext:
    """
    Language context for a specific user session
    
    Provides:
    - User's language preference
    - Language-aware i18n translation
    - Language info for AI prompts
    - Language context for business logic
    """
    
    def __init__(self, user_id: int, language: str = None, context: ContextTypes.DEFAULT_TYPE = None):
        """
        Initialize language context
        
        Args:
            user_id: Telegram user ID
            language: Language code (zh-CN, en, zh-TW), if None, will try to load from storage
            context: Bot context (for accessing storage)
        """
        self.user_id = user_id
        self._language = language
        self._context = context
        self._i18n = None
        
        # If language not provided, try to load from storage
        if not language and context:
            self._language = self._load_user_language(context)
        
        # Fallback to default
        if not self._language:
            config = get_config()
            self._language = config.language
    
    def _load_user_language(self, context: ContextTypes.DEFAULT_TYPE) -> Optional[str]:
        """Load user's language preference from storage (database first, then user_data)"""
        try:
            # Priority 1: Load from database for persistence
            db_storage = context.bot_data.get('db_storage')
            if db_storage and db_storage.db:
                try:
                    cursor = db_storage.db.conn.cursor()
                    cursor.execute("""
                        SELECT value FROM config WHERE key = 'user_language'
                    """)
                    row = cursor.fetchone()
                    if row:
                        lang = row[0]
                        # Cache in user_data for quick access
                        context.user_data['language'] = lang
                        logger.debug(f"Loaded user language from database: {lang}")
                        return lang
                except Exception as e:
                    logger.debug(f"Failed to load from database: {e}")
            
            # Priority 2: Fallback to user_data (for current session)
            lang = context.user_data.get('language')
            if lang:
                logger.debug(f"Loaded user language from user_data: {lang}")
                return lang
                
        except Exception as e:
            logger.debug(f"Failed to load user language: {e}")
        return None
    
    def _save_user_language(self, context: ContextTypes.DEFAULT_TYPE):
        """Save user's language preference to storage (both database and user_data)"""
        try:
            # Save to user_data for quick access (session cache)
            context.user_data['language'] = self._language
            
            # Save to database for persistence across bot restarts
            db_storage = context.bot_data.get('db_storage')
            if db_storage and db_storage.db:
                try:
                    cursor = db_storage.db.conn.cursor()
                    cursor.execute("""
                        INSERT INTO config (key, value, description, updated_at)
                        VALUES ('user_language', ?, 'User language preference', datetime('now'))
                        ON CONFLICT(key) DO UPDATE SET
                            value = excluded.value,
                            updated_at = excluded.updated_at
                    """, (self._language,))
                    db_storage.db.conn.commit()
                    logger.info(f"Saved user language to database: {self._language}")
                except Exception as e:
                    logger.warning(f"Failed to save language to database: {e}")
        except Exception as e:
            logger.warning(f"Failed to save user language: {e}")
    
    @property
    def language(self) -> str:
        """Get current language code"""
        return self._language
    
    @language.setter
    def language(self, lang: str):
        """Set language and save preference"""
        # 尝试映射简化的语言代码
        from .i18n import I18n
        mapped_lang = I18n.LANGUAGE_CODE_MAPPING.get(lang, lang)
        
        if mapped_lang in ['zh-CN', 'zh-TW', 'en', 'ja', 'ko', 'es']:
            self._language = mapped_lang
            self._i18n = None  # Reset i18n instance
            if self._context:
                self._save_user_language(self._context)
        else:
            logger.warning(f"Invalid language code: {lang}")
    
    def get_i18n(self):
        """Get i18n instance for current language"""
        if not self._i18n:
            from .i18n import I18n
            self._i18n = I18n(self._language)
        return self._i18n
    
    def t(self, key: str, **kwargs) -> str:
        """
        Translate key to current language
        
        Args:
            key: Translation key
            **kwargs: Formatting parameters
            
        Returns:
            Translated text
        """
        i18n = self.get_i18n()
        return i18n.t(key, **kwargs)
    
    def get_ai_language_hint(self) -> str:
        """
        Get language hint for AI prompts
        
        Returns:
            Language instruction for AI (in the target language)
        """
        language_hints = {
            'zh-CN': '请用简体中文回复',
            'zh-TW': '請用繁體中文回覆',
            'en': 'Please reply in English',
            'ja': '日本語で返信してください',
            'ko': '한국어로 답변해 주세요',
            'es': 'Por favor responde en español'
        }
        return language_hints.get(self._language, language_hints['zh-CN'])
    
    def get_tag_generation_language(self) -> str:
        """
        Get language for tag generation
        
        Returns:
            Language code for AI tag generation
        """
        return self._language
    
    def should_translate_content(self, content_language: str = None) -> bool:
        """
        Check if content should be translated to user's language
        
        Args:
            content_language: Detected language of the content
            
        Returns:
            True if translation is needed
        """
        if not content_language:
            return False
        
        # Normalize language codes
        lang_map = {
            'zh-CN': 'zh',
            'zh-TW': 'zh',
            'en': 'en'
        }
        
        user_lang = lang_map.get(self._language, self._language)
        content_lang = lang_map.get(content_language, content_language)
        
        return user_lang != content_lang
    
    def get_summary_language_instruction(self) -> str:
        """
        Get language instruction for content summarization
        
        Returns:
            Instruction text for AI summarization
        """
        instructions = {
            'zh-CN': '请用简体中文总结要点',
            'zh-TW': '請用繁體中文總結要點',
            'en': 'Please summarize key points in English'
        }
        return instructions.get(self._language, instructions['zh-CN'])
    
    def to_dict(self) -> Dict[str, Any]:
        """Export language context as dictionary"""
        return {
            'user_id': self.user_id,
            'language': self._language,
            'language_name': self.get_language_name()
        }
    
    def get_language_name(self) -> str:
        """Get human-readable language name"""
        names = {
            'zh-CN': '简体中文',
            'zh-TW': '繁體中文',
            'en': 'English'
        }
        return names.get(self._language, self._language)


def get_language_context(update, context: ContextTypes.DEFAULT_TYPE) -> LanguageContext:
    """
    Get or create language context for current user
    
    Args:
        update: Telegram update
        context: Bot context
        
    Returns:
        LanguageContext instance
    """
    user_id = update.effective_user.id
    
    # Try to get cached language context
    cache_key = f'lang_ctx_{user_id}'
    lang_ctx = context.bot_data.get(cache_key)
    
    if not lang_ctx:
        # Create new language context
        lang_ctx = LanguageContext(user_id, context=context)
        context.bot_data[cache_key] = lang_ctx
    
    return lang_ctx


def get_user_language(context: ContextTypes.DEFAULT_TYPE) -> str:
    """
    Get user's preferred language or default language
    
    Priority:
    1. User's language preference from context.user_data
    2. Bot's configured default language
    3. System DEFAULT_LANGUAGE (en)
    
    Args:
        context: Bot context
        
    Returns:
        Language code (e.g., 'en', 'zh-CN', 'zh-TW')
    """
    # Try to get from user_data
    if hasattr(context, 'user_data') and context.user_data.get('language'):
        return context.user_data['language']
    
    # Try to get from bot config
    try:
        config = get_config()
        if hasattr(config, 'language') and config.language:
            return config.language
    except Exception:
        pass
    
    # Fallback to system default
    return DEFAULT_LANGUAGE
    
    return lang_ctx


def with_language_context(func):
    """
    Decorator to inject language context into handler functions
    
    Usage:
        @with_language_context
        async def my_handler(update, context, lang_ctx):
            await update.message.reply_text(lang_ctx.t('welcome'))
    """
    async def wrapper(update, context, *args, **kwargs):
        lang_ctx = get_language_context(update, context)
        return await func(update, context, lang_ctx, *args, **kwargs)
    return wrapper
