"""
Language commands
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from ...utils.language_context import with_language_context
from .note_mode_interceptor import intercept_in_note_mode
from ...utils.config import get_config
from ...utils.helpers import send_or_update_reply

logger = logging.getLogger(__name__)


@intercept_in_note_mode
@with_language_context
async def language_command(update: Update, context: ContextTypes.DEFAULT_TYPE, lang_ctx) -> None:
    """
    Handle /language command
    
    Args:
        update: Telegram update
        context: Bot context
        lang_ctx: Language context
    """
    try:
        # Get current language name
        current_lang_key = f"language_name_{lang_ctx.language}"
        current_language = lang_ctx.t(current_lang_key)
        
        # Create language selection keyboard
        keyboard = [
            [
                InlineKeyboardButton("English", callback_data="lang_en"),
                InlineKeyboardButton("简体中文", callback_data="lang_zh-CN"),
            ],
            [
                InlineKeyboardButton("繁體中文", callback_data="lang_zh-TW"),
                InlineKeyboardButton("日本語", callback_data="lang_ja"),
            ],
            [
                InlineKeyboardButton("한국어", callback_data="lang_ko"),
                InlineKeyboardButton("Español", callback_data="lang_es"),
            ]
        ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await send_or_update_reply(
            update,
            context,
            lang_ctx.t('language_select', current_language=current_language),
            'language',
            reply_markup=reply_markup
        )
        
        logger.info(f"Language command executed")
        
    except Exception as e:
        logger.error(f"Error in language_command: {e}", exc_info=True)
        await send_or_update_reply(update, context, f"Error: {e}", 'language')
