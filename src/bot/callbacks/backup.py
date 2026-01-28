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
async def handle_backup_create_now_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, lang_ctx) -> None:
    """
    Handle backup create now button click - 立即创建备份
    
    Callback data format: backup_create_now
    
    Args:
        update: Telegram update
        context: Bot context
        lang_ctx: Language context
    """
    query = update.callback_query
    
    try:
        # 防重复点击：检查是否正在创建备份
        user_id = query.from_user.id
        backup_lock_key = f'backup_creating_{user_id}'
        backup_time_key = f'backup_last_time_{user_id}'
        
        if context.bot_data.get(backup_lock_key):
            await query.answer("⚠️ 备份正在创建中，请稍候...", show_alert=True)
            return
        
        # 检查5分钟冷却时间
        import time
        last_backup_time = context.bot_data.get(backup_time_key, 0)
        current_time = time.time()
        cooldown_seconds = 300  # 5分钟
        
        if current_time - last_backup_time < cooldown_seconds:
            remaining_seconds = int(cooldown_seconds - (current_time - last_backup_time))
            remaining_minutes = remaining_seconds // 60
            remaining_secs = remaining_seconds % 60
            
            # 发送弹窗提示
            await query.answer(
                f"⏳ 备份冷却中，请稍后再试",
                show_alert=True
            )
            
            # 同时更新消息文本，提供更详细的冷却信息
            cooldown_message = (
                f"⏳ <b>备份冷却中</b>\n\n"
                f"为防止误操作创建过多备份，设置了5分钟冷却时间。\n\n"
                f"⏰ 剩余时间：<code>{remaining_minutes}</code> 分 <code>{remaining_secs}</code> 秒\n\n"
                f"💡 提示：请等待冷却结束后再次点击"
            )
            
            try:
                await query.edit_message_text(
                    cooldown_message,
                    parse_mode=ParseMode.HTML
                )
            except:
                # 如果编辑失败（例如消息内容相同），则发送新消息
                await context.bot.send_message(
                    chat_id=query.message.chat_id,
                    text=cooldown_message,
                    parse_mode=ParseMode.HTML
                )
            
            return
        
        backup_manager = context.bot_data.get('backup_manager')
        
        if not backup_manager:
            await query.answer(lang_ctx.t('backup_manager_not_initialized'), show_alert=True)
            return
        
        # 设置锁，防止重复点击
        context.bot_data[backup_lock_key] = True
        
        await query.answer("⏳ 正在创建备份...")
        
        try:
            # 创建备份
            result = backup_manager.create_backup(description="手动备份")
            
            if result:
                # 记录备份时间
                context.bot_data[backup_time_key] = time.time()
                
                await query.answer(f"✅ 备份创建成功：{result}", show_alert=True)
                
                # 刷新备份列表
                from ...utils.helpers import format_file_size
                backups = backup_manager.list_backups()
                lines = [lang_ctx.t('backup_list_header', count=len(backups))]
                lines.append("")
                
                for idx, b in enumerate(backups[:10], 1):
                    filename = b.get('filename', 'unknown')
                    created_at = b.get('created_at', '')
                    size = b.get('size', 0)
                    description = b.get('description', '')
                    
                    size_str = format_file_size(size)
                    
                    # 第一个备份（最新）添加 New 标识
                    if idx == 1:
                        lines.append(f"🆕 📦 <b>{idx}. {filename}</b>")
                    else:
                        lines.append(f"📦 <b>{idx}. {filename}</b>")
                    lines.append(f"   📅 {created_at}")
                    lines.append(f"   📊 {size_str}")
                    if description:
                        lines.append(f"   💬 {description}")
                    lines.append("")
                
                if len(backups) > 10:
                    lines.append(lang_ctx.t('backup_list_more', count=len(backups) - 10))
                
                # 重建按钮
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
                
                await query.edit_message_text(
                    '\n'.join(lines),
                    parse_mode=ParseMode.HTML,
                    reply_markup=reply_markup
                )
                
                logger.info(f"Manual backup created: {result}")
            else:
                await query.answer(lang_ctx.t('backup_create_failed'), show_alert=True)
        
        finally:
            # 无论成功失败，都释放锁
            context.bot_data.pop(backup_lock_key, None)
        
    except Exception as e:
        logger.error(f"Error creating backup: {e}", exc_info=True)
        await query.answer(f"错误: {str(e)}", show_alert=True)
        # 发生异常时也要释放锁
        context.bot_data.pop(backup_lock_key, None)
        context.bot_data.pop(backup_lock_key, None)


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
        from ...utils.helpers import format_file_size
        backups = backup_manager.list_backups()
        lines = [lang_ctx.t('backup_list_header', count=len(backups))]
        lines.append("")
        
        for idx, b in enumerate(backups[:10], 1):
            filename = b.get('filename', 'unknown')
            created_at = b.get('created_at', '')
            size = b.get('size', 0)
            description = b.get('description', '')
            
            size_str = format_file_size(size)
            
            # 第一个备份（最新）添加 New 标识
            if idx == 1:
                lines.append(f"🆕 📦 <b>{idx}. {filename}</b>")
            else:
                lines.append(f"📦 <b>{idx}. {filename}</b>")
            lines.append(f"   📅 {created_at}")
            lines.append(f"   📊 {size_str}")
            if description:
                lines.append(f"   💬 {description}")
            lines.append("")
        
        if len(backups) > 10:
            lines.append(lang_ctx.t('backup_list_more', count=len(backups) - 10))
        
        # 重建按钮
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
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
        
        await query.edit_message_text(
            '\n'.join(lines),
            parse_mode=ParseMode.HTML,
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
        
        # 更新消息，添加立即备份按钮
        keyboard = [[
            InlineKeyboardButton(
                "🆕 立即备份",
                callback_data="backup_create_now"
            )
        ]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.edit_message_text(
            lang_ctx.t('backup_none'),
            reply_markup=reply_markup
        )
        
        logger.info(f"Deleted all {deleted} backups")
        
    except Exception as e:
        logger.error(f"Error handling backup delete all callback: {e}", exc_info=True)
        await query.answer(f"错误: {str(e)}", show_alert=True)


# ==================== Quick Note Operations ====================
