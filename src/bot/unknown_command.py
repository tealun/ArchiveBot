"""
Unknown command handler
Handles unrecognized commands
"""

import logging
from telegram import Update
from telegram.ext import ContextTypes

from ..utils.i18n import get_i18n

logger = logging.getLogger(__name__)


async def handle_unknown_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """
    Handle unknown/invalid commands
    
    Args:
        update: Telegram update
        context: Bot context
    """
    try:
        command = update.message.text
        i18n = get_i18n()
        
        logger.warning(f"Unknown command from user {update.effective_user.id}: {command}")
        
        await update.message.reply_text(
            "⚠️ 这似乎是一个命令，但格式不正确或命令不存在。\n"
            "发送 /help 查看所有可用命令。"
        )
        
    except Exception as e:
        logger.error(f"Error handling unknown command: {e}", exc_info=True)
