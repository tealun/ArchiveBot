"""
Unknown command handler
Handles unrecognized commands
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes

from ..utils.language_context import with_language_context

logger = logging.getLogger(__name__)


@with_language_context
async def handle_unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE, lang_ctx) -> None:
    """
    Handle unknown/invalid commands
    
    Args:
        update: Telegram update
        context: Bot context
        lang_ctx: Language context
    """
    try:
        command = update.message.text
        
        logger.warning(f"Unknown command from user {update.effective_user.id}: {command}")
        
        await update.message.reply_text(lang_ctx.t('unknown_command_message'))
        
    except Exception as e:
        logger.error(f"Error handling unknown command: {e}", exc_info=True)
