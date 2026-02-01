"""
Ai commands
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

from ...ai.summarizer import get_ai_summarizer

@intercept_in_note_mode
@with_language_context
async def ai_status_command(update: Update, context: ContextTypes.DEFAULT_TYPE, lang_ctx) -> None:
    """
    Handle /ai command - 显示AI功能状态
    
    Args:
        update: Telegram update
        context: Bot context
        lang_ctx: Language context
    """
    try:
        config = get_config()
        ai_config = config.ai
        
        # 使用MessageBuilder格式化AI状态
        from ...utils.message_builder import MessageBuilder
        # 添加user_id到context以便MessageBuilder访问
        context._user_id = update.effective_user.id
        status_text = MessageBuilder.format_ai_status(ai_config, context, lang_ctx)
        
        await send_or_update_reply(
            update,
            context,
            status_text,
            'ai',
            parse_mode=ParseMode.MARKDOWN
        )
        
        logger.info(f"AI status command executed")
        
    except Exception as e:
        logger.error(f"Error in ai_status_command: {e}", exc_info=True)
        await send_or_update_reply(update, context, f"❌ 获取AI状态失败: {str(e)}", 'ai')
