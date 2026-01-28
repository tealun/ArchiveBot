"""
Stats commands
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from ...utils.language_context import with_language_context
from ...utils.config import get_config
from ...utils.message_builder import MessageBuilder
from ...utils.helpers import format_file_size, send_or_update_reply
from .note_mode_interceptor import intercept_in_note_mode

logger = logging.getLogger(__name__)

from ...storage.database import DatabaseStorage

@intercept_in_note_mode
@with_language_context
async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE, lang_ctx) -> None:
    """
    Handle /stats command
    
    Args:
        update: Telegram update
        context: Bot context
        lang_ctx: Language context
    """
    try:
        db_storage: DatabaseStorage = context.bot_data.get('db_storage')
        
        if not db_storage:
            await send_or_update_reply(update, context, lang_ctx.t('error_database_not_initialized'), 'stats')
            return
        
        # Get stats from database
        stats = db_storage.db.get_stats()
        
        # Get database file size
        import os
        db_path = db_storage.db.db_path
        db_size = 0
        if os.path.exists(db_path):
            db_size = os.path.getsize(db_path)
        
        # Use unified formatter
        message = MessageBuilder.format_stats(stats, language=lang_ctx.language, db_size=db_size)
        
        await send_or_update_reply(update, context, message, 'stats')
        
        logger.info(f"Stats command executed")
        
    except Exception as e:
        logger.error(f"Error in stats_command: {e}", exc_info=True)
        await send_or_update_reply(update, context, lang_ctx.t('error_occurred', error=str(e)), 'stats')
