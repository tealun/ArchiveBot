"""
Stats commands
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from ...utils.language_context import with_language_context
from ...utils.config import get_config

logger = logging.getLogger(__name__)

from ...storage.database import DatabaseStorage
from ...utils.helpers import format_file_size

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
            await update.message.reply_text(lang_ctx.t('error_database_not_initialized'))
            return
        
        # Get stats from database
        stats = db_storage.db.get_stats()
        
        # Get database file size
        import os
        db_path = db_storage.db.db_path
        db_size = 0
        if os.path.exists(db_path):
            db_size = os.path.getsize(db_path)
        
        # Format stats
        total_archives = stats.get('total_archives', 0)
        total_tags = stats.get('total_tags', 0)
        total_size = format_file_size(stats.get('total_size', 0))
        db_size_formatted = format_file_size(db_size)
        last_archive = stats.get('last_archive', 'N/A')
        
        message = lang_ctx.t(
            'stats',
            total_archives=total_archives,
            total_tags=total_tags,
            storage_used=total_size,
            db_size=db_size_formatted,
            last_archive=last_archive
        )
        
        await update.message.reply_text(message)
        
        logger.info(f"Stats command executed")
        
    except Exception as e:
        logger.error(f"Error in stats_command: {e}", exc_info=True)
        await update.message.reply_text(lang_ctx.t('error_occurred', error=str(e)))
