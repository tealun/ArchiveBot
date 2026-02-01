"""
Trash callbacks
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from ...utils.language_context import with_language_context, get_language_context
from ...utils.config import get_config

logger = logging.getLogger(__name__)

from ...core.trash_manager import TrashManager

@with_language_context
async def handle_delete_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, lang_ctx) -> None:
    """
    处理删除归档（移动到垃圾箱）
    
    Callback data format: delete:archive_id
    """
    try:
        query = update.callback_query
        callback_data = query.data
        
        # 解析归档ID
        archive_id = int(callback_data.split(':', 1)[1])
        
        # 获取trash_manager
        trash_manager = context.bot_data.get('trash_manager')
        if not trash_manager:
            await query.edit_message_text(lang_ctx.t('trash_manager_not_initialized'))
            return
        
        # 移动到垃圾箱
        if trash_manager.move_to_trash(archive_id):
            await query.edit_message_text(lang_ctx.t('archive_moved_to_trash', archive_id=archive_id))
        else:
            await query.edit_message_text(lang_ctx.t('archive_delete_failed', archive_id=archive_id))
        
        logger.info(f"Archive {archive_id} moved to trash via callback")
        
    except Exception as e:
        logger.error(f"Error handling delete callback: {e}", exc_info=True)


@with_language_context
async def handle_trash_restore_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, lang_ctx) -> None:
    """
    处理恢复归档
    
    Callback data format: trash_restore:archive_id
    """
    try:
        query = update.callback_query
        callback_data = query.data
        
        # 解析归档ID
        archive_id = int(callback_data.split(':', 1)[1])
        
        # 获取trash_manager
        trash_manager = context.bot_data.get('trash_manager')
        if not trash_manager:
            await query.edit_message_text(lang_ctx.t('trash_manager_not_initialized'))
            return
        
        # 恢复归档
        if trash_manager.restore_archive(archive_id):
            await query.edit_message_text(lang_ctx.t('trash_restore_success', archive_id=archive_id))
        else:
            await query.edit_message_text(lang_ctx.t('trash_restore_failed', archive_id=archive_id))
        
        logger.info(f"Archive {archive_id} restored from trash via callback")
        
    except Exception as e:
        logger.error(f"Error handling restore callback: {e}", exc_info=True)


@with_language_context
async def handle_trash_delete_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, lang_ctx) -> None:
    """
    处理永久删除归档
    
    Callback data format: trash_delete:archive_id
    """
    try:
        query = update.callback_query
        callback_data = query.data
        
        # 解析归档ID
        archive_id = int(callback_data.split(':', 1)[1])
        
        # 获取trash_manager
        trash_manager = context.bot_data.get('trash_manager')
        if not trash_manager:
            await query.edit_message_text(lang_ctx.t('trash_manager_not_initialized'))
            return
        
        # 永久删除
        if trash_manager.delete_permanently(archive_id):
            await query.edit_message_text(lang_ctx.t('trash_delete_success', archive_id=archive_id))
        else:
            await query.edit_message_text(lang_ctx.t('trash_delete_failed', archive_id=archive_id))
        
        logger.info(f"Archive {archive_id} permanently deleted via callback")
        
    except Exception as e:
        logger.error(f"Error handling permanent delete callback: {e}", exc_info=True)
