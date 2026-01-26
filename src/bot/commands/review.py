"""
Review commands
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from ...utils.language_context import with_language_context
from ...utils.config import get_config

logger = logging.getLogger(__name__)

from ...core.review_manager import ReviewManager

@with_language_context
async def review_command(update: Update, context: ContextTypes.DEFAULT_TYPE, lang_ctx) -> None:
    """
    Handle /review command - 活动回顾与统计
    
    Usage:
        /review              - 显示期间选择按钮
    
    Args:
        update: Telegram update
        context: Bot context
        lang_ctx: Language context
    """
    try:
        review_manager = context.bot_data.get('review_manager')

        if not review_manager:
            await update.message.reply_text(lang_ctx.t('review_manager_not_initialized'))
            return

        # 显示期间选择按钮
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        
        keyboard = [
            [
                InlineKeyboardButton(
                    f"📅 {lang_ctx.t('review_period_week')}",
                    callback_data='review:week'
                ),
                InlineKeyboardButton(
                    f"📅 {lang_ctx.t('review_period_month')}",
                    callback_data='review:month'
                )
            ],
            [
                InlineKeyboardButton(
                    f"📅 {lang_ctx.t('review_period_year')}",
                    callback_data='review:year'
                )
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            lang_ctx.t('review_usage'),
            reply_markup=reply_markup,
            parse_mode='HTML'
        )

    except Exception as e:
        logger.error(f"Error in review_command: {e}", exc_info=True)
        await update.message.reply_text(lang_ctx.t('error_occurred', error=str(e)))
