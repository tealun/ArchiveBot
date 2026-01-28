"""
Note mode interceptor

Intercepts commands when user is in note mode and shows choice dialog.
"""

import logging
from functools import wraps
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


def intercept_in_note_mode(func):
    """
    Decorator to intercept command execution when user is in note mode
    
    If user is in note mode, show choice dialog instead of executing command.
    Otherwise, execute command normally.
    
    Usage:
        @intercept_in_note_mode
        @with_language_context
        async def my_command(update, context, lang_ctx):
            ...
    """
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE, *args, **kwargs):
        # Check if user is in note mode
        if context.user_data.get('note_mode'):
            # User is in note mode - show choice dialog
            command_text = update.message.text if update.message else ''
            
            keyboard = [
                [
                    InlineKeyboardButton(
                        "🚪 立即退出并保存笔记，然后执行命令",
                        callback_data=f"note_exit_save:{command_text}"
                    )
                ],
                [
                    InlineKeyboardButton(
                        "✍️ 继续记录笔记（忽略命令）",
                        callback_data="note_continue"
                    )
                ]
            ]
            reply_markup = InlineKeyboardMarkup(keyboard)
            
            await update.message.reply_text(
                f"⚠️ 您正在笔记模式中\n\n"
                f"检测到命令：{command_text}\n\n"
                f"请选择操作：",
                reply_markup=reply_markup
            )
            
            # Store pending command
            context.user_data['pending_command'] = command_text
            
            logger.info(f"Command {command_text} intercepted in note mode")
            return  # Don't execute the command
        
        # Not in note mode - execute command normally
        return await func(update, context, *args, **kwargs)
    
    return wrapper
