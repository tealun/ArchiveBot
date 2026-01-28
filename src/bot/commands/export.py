"""
Export commands
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

from ...core.export_manager import ExportManager
from ...utils.helpers import format_file_size

@intercept_in_note_mode
@with_language_context
async def export_command(update: Update, context: ContextTypes.DEFAULT_TYPE, lang_ctx) -> None:
    """
    Handle /export command - 导出数据
    
    Usage:
        /export - 显示格式选择菜单
        /export tag <tag_name> - 按标签导出（显示格式选择）
    
    Args:
        update: Telegram update
        context: Bot context
        lang_ctx: Language context
    """
    try:
        # 获取export_manager
        export_manager = context.bot_data.get('export_manager')
        if not export_manager:
            await send_or_update_reply(update, context, lang_ctx.t('export_manager_not_initialized'), 'export')
            return
        
        # 解析命令参数
        tag_name = None
        
        if context.args:
            if context.args[0] == 'tag':
                # 按标签导出
                if len(context.args) < 2:
                    await send_or_update_reply(update, context, lang_ctx.t('export_tag_usage'), 'export')
                    return
                tag_name = context.args[1]
        
        # 显示格式选择按钮
        keyboard = [
            [
                InlineKeyboardButton(
                    "📄 Markdown",
                    callback_data=f"export_format:markdown:{tag_name or 'all'}"
                )
            ],
            [
                InlineKeyboardButton(
                    "📊 JSON",
                    callback_data=f"export_format:json:{tag_name or 'all'}"
                )
            ],
            [
                InlineKeyboardButton(
                    "📋 CSV",
                    callback_data=f"export_format:csv:{tag_name or 'all'}"
                )
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if tag_name:
            message = f"📦 导出标签 #{tag_name} 的归档\n\n请选择导出格式："
        else:
            message = "📦 导出所有归档\n\n请选择导出格式："
        
        await send_or_update_reply(
            update, 
            context, 
            message, 
            'export',
            reply_markup=reply_markup
        )
        
        logger.info(f"Export command: showing format selection, tag={tag_name}")
        
    except Exception as e:
        logger.error(f"Error in export_command: {e}", exc_info=True)
        try:
            await send_or_update_reply(update, context, lang_ctx.t('error_occurred', error=str(e)), 'export')
        except Exception as reply_err:
            logger.error(f"Failed to send error message: {reply_err}")
