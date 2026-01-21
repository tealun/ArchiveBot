"""
Callback query handlers
Handles button clicks and inline keyboard callbacks
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes

from ..utils.i18n import get_i18n
from ..utils.config import get_config

logger = logging.getLogger(__name__)


async def handle_language_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle language selection callback
    
    Args:
        update: Telegram update
        context: Bot context
    """
    try:
        query = update.callback_query
        await query.answer()
        
        # Parse callback data
        callback_data = query.data
        
        if callback_data.startswith('lang_'):
            language = callback_data[5:]  # Remove 'lang_' prefix
            
            # Set language
            i18n = get_i18n()
            if i18n.set_language(language):
                # Save to config
                config = get_config()
                config.set('bot.language', language)
                config.save()
                
                # Send confirmation
                await query.edit_message_text(i18n.t('language_changed'))
                
                logger.info(f"Language changed to: {language}")
            else:
                await query.edit_message_text(f"Unsupported language: {language}")
        
    except Exception as e:
        logger.error(f"Error handling language callback: {e}", exc_info=True)
        try:
            await query.edit_message_text(f"Error: {e}")
        except:
            pass
