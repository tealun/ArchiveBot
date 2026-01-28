"""
Backup commands
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from ...utils.language_context import with_language_context
from .note_mode_interceptor import intercept_in_note_mode
from ...utils.config import get_config

logger = logging.getLogger(__name__)

from ...core.backup_manager import BackupManager
from ...utils.helpers import format_file_size, send_or_update_reply

@intercept_in_note_mode
@with_language_context
async def backup_command(update: Update, context: ContextTypes.DEFAULT_TYPE, lang_ctx) -> None:
    """
    Handle /backup command - 备份与恢复
    
    Usage:
        /backup              - 查看备份列表
        /backup create [desc]- 创建备份，可附描述
        /backup restore <file> - 从备份恢复
        /backup delete <file>  - 删除备份
        /backup cleanup [keep] - 只保留最近N个（默认10）
        /backup status       - 查看数据库状态
    
    Args:
        update: Telegram update
        context: Bot context
        lang_ctx: Language context
    """
    try:
        backup_manager = context.bot_data.get('backup_manager')

        if not backup_manager:
            await update.message.reply_text(lang_ctx.t('backup_manager_not_initialized'))
            return

        # 无参数 -> 列表
        if not context.args:
            backups = backup_manager.list_backups()
            if not backups:
                # 没有备份时，显示提示信息和立即备份按钮
                keyboard = [[
                    InlineKeyboardButton(
                        "🆕 立即备份",
                        callback_data="backup_create_now"
                    )
                ]]
                reply_markup = InlineKeyboardMarkup(keyboard)
                
                await send_or_update_reply(
                    update, context,
                    lang_ctx.t('backup_none'),
                    'backup',
                    reply_markup=reply_markup
                )
                return

            lines = [lang_ctx.t('backup_list_header', count=len(backups))]
            lines.append("")
            
            for idx, b in enumerate(backups[:10], 1):
                filename = b.get('filename', 'unknown')
                created_at = b.get('created_at', '')
                size = b.get('size', 0)
                description = b.get('description', '')
                
                # 格式化文件大小
                size_str = format_file_size(size)
                
                # 构建单个备份条目
                lines.append(f"📦 <b>{idx}. {filename}</b>")
                lines.append(f"   📅 {created_at}")
                lines.append(f"   📊 {size_str}")
                if description:
                    lines.append(f"   💬 {description}")
                lines.append("")
            
            if len(backups) > 10:
                lines.append(lang_ctx.t('backup_list_more', count=len(backups) - 10))

            # 添加操作按钮
            keyboard = [
                [
                    InlineKeyboardButton(
                        "🆕 立即备份",
                        callback_data="backup_create_now"
                    )
                ],
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
            
            await send_or_update_reply(
                update, context,
                '\n'.join(lines),
                'backup',
                parse_mode=ParseMode.HTML,
                reply_markup=reply_markup
            )
            return

        subcmd = context.args[0].lower()

        if subcmd == 'create':
            desc = ' '.join(context.args[1:]) if len(context.args) > 1 else ''
            result = backup_manager.create_backup(description=desc)
            if result:
                await update.message.reply_text(lang_ctx.t('backup_created', filename=result))
            else:
                await update.message.reply_text(lang_ctx.t('backup_create_failed'))
            return

        if subcmd == 'restore':
            if len(context.args) < 2:
                await update.message.reply_text(lang_ctx.t('backup_restore_usage'))
                return
            filename = context.args[1]
            ok = backup_manager.restore_backup(filename)
            if ok:
                await update.message.reply_text(lang_ctx.t('backup_restored', filename=filename))
            else:
                await update.message.reply_text(lang_ctx.t('backup_restore_failed', filename=filename))
            return

        if subcmd == 'delete':
            if len(context.args) < 2:
                await update.message.reply_text(lang_ctx.t('backup_delete_usage'))
                return
            filename = context.args[1]
            ok = backup_manager.delete_backup(filename)
            if ok:
                await update.message.reply_text(lang_ctx.t('backup_deleted', filename=filename))
            else:
                await update.message.reply_text(lang_ctx.t('backup_delete_failed', filename=filename))
            return

        if subcmd == 'cleanup':
            keep = 10
            if len(context.args) > 1:
                try:
                    keep = int(context.args[1])
                except ValueError:
                    await update.message.reply_text(lang_ctx.t('backup_invalid_keep'))
                    return
            deleted = backup_manager.cleanup_old_backups(keep_count=keep)
            await update.message.reply_text(lang_ctx.t('backup_cleanup_done', deleted=deleted, keep=keep))
            return

        if subcmd == 'status':
            stats = backup_manager.get_database_stats()
            if not stats:
                await update.message.reply_text(lang_ctx.t('backup_status_failed'))
                return
            msg = lang_ctx.t(
                'backup_status',
                size=stats.get('size', 0),
                archives=stats.get('archives_count', 0),
                notes=stats.get('notes_count', 0),
                deleted=stats.get('deleted_count', 0),
                last=stats.get('last_archive', 'N/A')
            )
            await update.message.reply_text(msg)
            return

        # 未知子命令
        await update.message.reply_text(lang_ctx.t('backup_invalid_command'))

    except Exception as e:
        logger.error(f"Error in backup_command: {e}", exc_info=True)
        await update.message.reply_text(lang_ctx.t('error_occurred', error=str(e)))
