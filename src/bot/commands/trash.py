"""
Trash commands
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

from ...core.trash_manager import TrashManager

@intercept_in_note_mode
@with_language_context
async def trash_command(update: Update, context: ContextTypes.DEFAULT_TYPE, lang_ctx) -> None:
    """
    Handle /trash command - 管理垃圾箱
    
    Usage:
        /trash - 查看垃圾箱
        /trash restore <id> - 恢复归档
        /trash delete <id> - 永久删除
        /trash empty - 清空垃圾箱
        /trash empty <days> - 清空N天前的归档
    
    Args:
        update: Telegram update
        context: Bot context
        lang_ctx: Language context
    """
    try:
        # 获取trash_manager
        trash_manager = context.bot_data.get('trash_manager')
        if not trash_manager:
            await send_or_update_reply(update, context, lang_ctx.t('trash_manager_not_initialized'), 'trash')
            return
        
        # 解析子命令
        if not context.args:
            # 查看垃圾箱
            items = trash_manager.list_trash()
            
            # 使用MessageBuilder格式化垃圾箱列表
            from ...utils.message_builder import MessageBuilder
            result_text = MessageBuilder.format_trash_list(items, lang_ctx, max_display=20)
            
            await send_or_update_reply(update, context, result_text, 'trash')
            
        elif context.args[0] == 'restore':
            # 恢复归档
            if len(context.args) < 2:
                await send_or_update_reply(update, context, lang_ctx.t('trash_restore_usage'), 'trash')
                return
            
            try:
                archive_id = int(context.args[1])
            except ValueError:
                await send_or_update_reply(update, context, lang_ctx.t('invalid_archive_id'), 'trash')
                return
            
            if trash_manager.restore_archive(archive_id):
                await send_or_update_reply(update, context, lang_ctx.t('trash_restore_success', archive_id=archive_id), 'trash')
            else:
                await send_or_update_reply(update, context, lang_ctx.t('trash_restore_failed', archive_id=archive_id), 'trash')
        
        elif context.args[0] == 'delete':
            # 永久删除
            if len(context.args) < 2:
                await send_or_update_reply(update, context, lang_ctx.t('trash_delete_usage'), 'trash')
                return
            
            try:
                archive_id = int(context.args[1])
            except ValueError:
                await send_or_update_reply(update, context, lang_ctx.t('invalid_archive_id'), 'trash')
                return
            
            if trash_manager.delete_permanently(archive_id):
                await send_or_update_reply(update, context, lang_ctx.t('trash_delete_success', archive_id=archive_id), 'trash')
            else:
                await send_or_update_reply(update, context, lang_ctx.t('trash_delete_failed', archive_id=archive_id), 'trash')
        
        elif context.args[0] == 'empty':
            # 清空垃圾箱
            days_old = None
            if len(context.args) > 1:
                try:
                    days_old = int(context.args[1])
                except ValueError:
                    await send_or_update_reply(update, context, lang_ctx.t('invalid_days'), 'trash')
                    return
            
            count = trash_manager.empty_trash(days_old)
            
            if days_old:
                await send_or_update_reply(update, context, lang_ctx.t('trash_empty_success_days', count=count, days=days_old), 'trash')
            else:
                await send_or_update_reply(update, context, lang_ctx.t('trash_empty_success', count=count), 'trash')
        
        else:
            await send_or_update_reply(update, context, lang_ctx.t('trash_invalid_command'), 'trash')
        
        logger.info(f"Trash command executed: {' '.join(context.args) if context.args else 'list'}")
        
    except Exception as e:
        logger.error(f"Error in trash_command: {e}", exc_info=True)
        await send_or_update_reply(update, context, lang_ctx.t('error_occurred', error=str(e)), 'trash')
