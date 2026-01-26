"""
Basic commands
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from ...utils.language_context import with_language_context
from ...utils.config import get_config

logger = logging.getLogger(__name__)


@with_language_context
async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE, lang_ctx) -> None:
    """
    Handle /start command
    
    Args:
        update: Telegram update
        context: Bot context
        lang_ctx: Language context
    """
    try:
        config = get_config()
        
        welcome_msg = lang_ctx.t('welcome')
        await update.message.reply_text(welcome_msg, parse_mode=ParseMode.HTML)
        
        logger.info(f"Start command executed by user {update.effective_user.id}")
        
    except Exception as e:
        logger.error(f"Error in start_command: {e}", exc_info=True)
        await update.message.reply_text(f"Error: {e}")


@with_language_context
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE, lang_ctx) -> None:
    """
    Handle /help command
    
    Args:
        update: Telegram update
        context: Bot context
        lang_ctx: Language context
    """
    try:
        help_msg = lang_ctx.t('help')
        
        await update.message.reply_text(
            help_msg,
            parse_mode=ParseMode.HTML
        )
        
        logger.info(f"Help command executed by user {update.effective_user.id}")
        
    except Exception as e:
        logger.error(f"Error in help_command: {e}", exc_info=True)
        await update.message.reply_text(f"Error: {e}")
