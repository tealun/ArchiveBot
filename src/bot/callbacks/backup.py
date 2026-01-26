"""
Backup callbacks
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from ...utils.language_context import with_language_context, get_language_context
from ...utils.config import get_config

logger = logging.getLogger(__name__)


@with_language_context
async def handle_backup_keep_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, lang_ctx) -> None:
    """
    Handle backup keep button click - 保留指定数量的备份
    
    Callback data format: backup_keep:N
    
    Args:
        update: Telegram update
        context: Bot context
        lang_ctx: Language context
    """
    query = update.callback_query
    
    try:
        # 解析保留数量
        keep_count = int(query.data.split(':')[1])
        
        backup_manager = context.bot_data.get('backup_manager')
        
        if not backup_manager:
            await query.answer(lang_ctx.t('backup_manager_not_initialized'), show_alert=True)
            return
        
        # 执行清理
        deleted = backup_manager.cleanup_old_backups(keep_count=keep_count)
        
        await query.answer(
            f"✅ 已删除 {deleted} 个旧备份，保留最新 {keep_count} 份",
            show_alert=True
        )
        
        # 刷新备份列表
        backups = backup_manager.list_backups()
        lines = [lang_ctx.t('backup_list_header', count=len(backups))]
        for b in backups[:10]:
            lines.append(lang_ctx.t(
                'backup_list_item',
                filename=b.get('filename'),
                created_at=b.get('created_at'),
                size=b.get('size'),
                description=b.get('description', '')
            ))
        if len(backups) > 10:
            lines.append(lang_ctx.t('backup_list_more', count=len(backups) - 10))
        
        # 重建按钮
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        keyboard = [
            [
                InlineKeyboardButton(
                    "💾 保留1份",
                    callback_data="backup_keep:1"
                ),
                InlineKeyboardButton(
                    "💾 保留3份",
                    callback_data="backup_keep:3"
                )
            ],
            [
                InlineKeyboardButton(
                    "🗑️ 全部删除",
                    callback_data="backup_delete_all"
                )
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            '\n'.join(lines),
            reply_markup=reply_markup
        )
        
        logger.info(f"Kept {keep_count} backups, deleted {deleted}")
        
    except Exception as e:
        logger.error(f"Error handling backup keep callback: {e}", exc_info=True)
        await query.answer(f"错误: {str(e)}", show_alert=True)


@with_language_context
async def handle_backup_delete_all_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, lang_ctx) -> None:
    """
    Handle backup delete all button click - 删除所有备份
    
    Callback data format: backup_delete_all
    
    Args:
        update: Telegram update
        context: Bot context
        lang_ctx: Language context
    """
    query = update.callback_query
    
    try:
        backup_manager = context.bot_data.get('backup_manager')
        
        if not backup_manager:
            await query.answer(lang_ctx.t('backup_manager_not_initialized'), show_alert=True)
            return
        
        # 获取所有备份
        backups = backup_manager.list_backups()
        total = len(backups)
        
        if total == 0:
            await query.answer("没有备份可删除", show_alert=True)
            return
        
        # 删除所有备份
        deleted = 0
        for backup in backups:
            if backup_manager.delete_backup(backup['filename']):
                deleted += 1
        
        await query.answer(
            f"✅ 已删除全部 {deleted}/{total} 个备份",
            show_alert=True
        )
        
        # 更新消息
        await query.edit_message_text(
            lang_ctx.t('backup_none')
        )
        
        logger.info(f"Deleted all {deleted} backups")
        
    except Exception as e:
        logger.error(f"Error handling backup delete all callback: {e}", exc_info=True)
        await query.answer(f"错误: {str(e)}", show_alert=True)


# ==================== Quick Note Operations ====================
