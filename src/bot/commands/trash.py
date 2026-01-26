"""
Trash commands
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from ...utils.language_context import with_language_context
from ...utils.config import get_config

logger = logging.getLogger(__name__)

from ...core.trash_manager import TrashManager

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
            await update.message.reply_text(lang_ctx.t('trash_manager_not_initialized'))
            return
        
        # 解析子命令
        if not context.args:
            # 查看垃圾箱
            items = trash_manager.list_trash()
            count = len(items)
            
            if count == 0:
                await update.message.reply_text(lang_ctx.t('trash_empty'))
                return
            
            result_text = lang_ctx.t('trash_list', count=count) + "\n\n"
            
            for item in items[:20]:  # 只显示前20条
                result_text += f"🗑️ ID: #{item['id']}\n"
                result_text += f"📝 {item['title']}\n"
                result_text += f"🏷️ {', '.join(item['tags'][:3])}{'...' if len(item['tags']) > 3 else ''}\n"
                result_text += f"🕐 {lang_ctx.t('deleted_at')}: {item['deleted_at']}\n\n"
            
            if count > 20:
                result_text += lang_ctx.t('trash_more', count=count-20)
            
            await update.message.reply_text(result_text)
            
        elif context.args[0] == 'restore':
            # 恢复归档
            if len(context.args) < 2:
                await update.message.reply_text(lang_ctx.t('trash_restore_usage'))
                return
            
            try:
                archive_id = int(context.args[1])
            except ValueError:
                await update.message.reply_text(lang_ctx.t('invalid_archive_id'))
                return
            
            if trash_manager.restore_archive(archive_id):
                await update.message.reply_text(lang_ctx.t('trash_restore_success', archive_id=archive_id))
            else:
                await update.message.reply_text(lang_ctx.t('trash_restore_failed', archive_id=archive_id))
        
        elif context.args[0] == 'delete':
            # 永久删除
            if len(context.args) < 2:
                await update.message.reply_text(lang_ctx.t('trash_delete_usage'))
                return
            
            try:
                archive_id = int(context.args[1])
            except ValueError:
                await update.message.reply_text(lang_ctx.t('invalid_archive_id'))
                return
            
            if trash_manager.delete_permanently(archive_id):
                await update.message.reply_text(lang_ctx.t('trash_delete_success', archive_id=archive_id))
            else:
                await update.message.reply_text(lang_ctx.t('trash_delete_failed', archive_id=archive_id))
        
        elif context.args[0] == 'empty':
            # 清空垃圾箱
            days_old = None
            if len(context.args) > 1:
                try:
                    days_old = int(context.args[1])
                except ValueError:
                    await update.message.reply_text(lang_ctx.t('invalid_days'))
                    return
            
            count = trash_manager.empty_trash(days_old)
            
            if days_old:
                await update.message.reply_text(lang_ctx.t('trash_empty_success_days', count=count, days=days_old))
            else:
                await update.message.reply_text(lang_ctx.t('trash_empty_success', count=count))
        
        else:
            await update.message.reply_text(lang_ctx.t('trash_invalid_command'))
        
        logger.info(f"Trash command executed: {' '.join(context.args) if context.args else 'list'}")
        
    except Exception as e:
        logger.error(f"Error in trash_command: {e}", exc_info=True)
        await update.message.reply_text(lang_ctx.t('error_occurred', error=str(e)))
