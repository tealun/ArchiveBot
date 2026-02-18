"""
Favorite callbacks
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from ...utils.language_context import with_language_context, get_language_context
from ...utils.config import get_config

logger = logging.getLogger(__name__)


@with_language_context
async def handle_favorite_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, lang_ctx) -> None:
    """
    Handle favorite/unfavorite button click
    
    Callback data format: fav:archive_id
    
    Args:
        update: Telegram update
        context: Bot context
    """
    query = update.callback_query
    
    try:
        # 解析 callback data: fav:archive_id
        archive_id = int(query.data.split(':')[1])
        
        # 获取数据库
        db_storage = context.bot_data.get('db_storage')
        if not db_storage:
            await query.answer("Database not initialized", show_alert=True)
            logger.error("Database storage not initialized")
            return
        
        db = db_storage.db
        telegram_storage = context.bot_data.get('telegram_storage')
        
        # 获取当前精选状态和存档信息
        is_fav = db.is_favorite(archive_id)
        archive = db_storage.get_archive(archive_id)
        
        if not archive:
            await query.answer("存档不存在", show_alert=True)
            logger.error(f"Archive {archive_id} not found")
            return
        
        # 切换精选状态
        new_status = not is_fav
        
        # 处理精选频道同步
        featured_message_id = None
        if new_status:
            # 标记为精选：转发到精选频道（如果配置了）
            featured_message_id = await _forward_to_featured_channel(
                context, archive, archive_id
            )
        else:
            # 取消精选：从精选频道删除（如果存在）
            await _delete_from_featured_channel(
                context, archive, archive_id
            )
        
        # 更新数据库
        success = db.set_favorite(archive_id, new_status)
        
        # 如果精选成功且有featured_message_id，更新到数据库
        if success and new_status and featured_message_id:
            try:
                with db._lock:
                    db.execute(
                        "UPDATE archives SET featured_channel_message_id = ? WHERE id = ?",
                        (featured_message_id, archive_id)
                    )
                    db.commit()
                    logger.info(f"Updated featured_channel_message_id for archive {archive_id}: {featured_message_id}")
            except Exception as e:
                logger.error(f"Failed to update featured_channel_message_id: {e}")
        
        # 如果取消精选，清空featured_channel_message_id
        if success and not new_status:
            try:
                with db._lock:
                    db.execute(
                        "UPDATE archives SET featured_channel_message_id = NULL WHERE id = ?",
                        (archive_id,)
                    )
                    db.commit()
                    logger.info(f"Cleared featured_channel_message_id for archive {archive_id}")
            except Exception as e:
                logger.error(f"Failed to clear featured_channel_message_id: {e}")
        
        if success:
            # 更新按钮显示
            try:
                # 获取当前消息的按钮
                original_markup = query.message.reply_markup
                if original_markup and original_markup.inline_keyboard:
                    # 重建按钮，更新精选按钮的图标
                    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
                    
                    new_keyboard = []
                    for row in original_markup.inline_keyboard:
                        new_row = []
                        for button in row:
                            callback_data = button.callback_data
                            if callback_data and callback_data.startswith(f'fav:{archive_id}'):
                                # 更新精选按钮图标
                                fav_icon = "❤️" if new_status else "🤍"
                                new_row.append(InlineKeyboardButton(fav_icon, callback_data=callback_data))
                            else:
                                new_row.append(button)
                        new_keyboard.append(new_row)
                    
                    # 更新消息的按钮
                    await query.edit_message_reply_markup(reply_markup=InlineKeyboardMarkup(new_keyboard))
            except Exception as e:
                logger.debug(f"Failed to update button markup: {e}")
            
            # 给用户反馈
            if new_status:
                await query.answer("❤️ 已添加到精选")
            else:
                await query.answer("🤍 已取消精选")
            
            logger.info(f"Archive {archive_id} favorite toggled to {new_status}")
        else:
            await query.answer("操作失败", show_alert=True)
            logger.error(f"Failed to toggle favorite for archive {archive_id}")
        
    except Exception as e:
        logger.error(f"Error handling favorite callback: {e}", exc_info=True)
        await query.answer(f"错误: {str(e)}", show_alert=True)


async def _forward_to_featured_channel(context: ContextTypes.DEFAULT_TYPE, archive: dict, archive_id: int) -> str:
    """
    Forward archive to featured channel
    
    Returns:
        featured_message_id in format "channel_id:message_id" or None
    """
    try:
        config = get_config()
        # 使用 config.get() 方法或 telegram_channels 属性获取频道配置
        channels = config.telegram_channels
        featured_channel_id = channels.get('featured')
        
        if not featured_channel_id:
            logger.debug("No featured channel configured, skipping forward")
            return None
        
        telegram_storage = context.bot_data.get('telegram_storage')
        if not telegram_storage:
            logger.warning("Telegram storage not available")
            return None
        
        # 从原始storage_path解析消息信息
        storage_path = archive.get('storage_path')
        if not storage_path:
            logger.warning(f"Archive {archive_id} has no storage_path")
            return None
        
        # Parse storage_path: "channel_id:message_id" or "channel_id:message_id:file_id"
        parts = storage_path.split(':')
        if len(parts) < 2:
            logger.warning(f"Invalid storage_path format: {storage_path}")
            return None
        
        source_channel_id = int(parts[0])
        source_message_id = int(parts[1])
        
        # 转发消息到精选频道
        try:
            forwarded_message = await context.bot.forward_message(
                chat_id=featured_channel_id,
                from_chat_id=source_channel_id,
                message_id=source_message_id
            )
            
            if forwarded_message:
                featured_message_id = f"{featured_channel_id}:{forwarded_message.message_id}"
                logger.info(f"Forwarded archive {archive_id} to featured channel: {featured_message_id}")
                return featured_message_id
            
        except Exception as e:
            logger.error(f"Failed to forward to featured channel: {e}", exc_info=True)
        
        return None
        
    except Exception as e:
        logger.error(f"Error in _forward_to_featured_channel: {e}", exc_info=True)
        return None


async def _delete_from_featured_channel(context: ContextTypes.DEFAULT_TYPE, archive: dict, archive_id: int):
    """
    Delete archive from featured channel
    """
    try:
        featured_message_id = archive.get('featured_channel_message_id')
        if not featured_message_id:
            logger.debug(f"Archive {archive_id} has no featured_channel_message_id, nothing to delete")
            return
        
        telegram_storage = context.bot_data.get('telegram_storage')
        if not telegram_storage:
            logger.warning("Telegram storage not available")
            return
        
        # 删除精选频道中的消息
        success = await telegram_storage.delete_message(featured_message_id)
        if success:
            logger.info(f"Deleted archive {archive_id} from featured channel: {featured_message_id}")
        else:
            logger.warning(f"Failed to delete archive {archive_id} from featured channel")
            
    except Exception as e:
        logger.error(f"Error in _delete_from_featured_channel: {e}", exc_info=True)


@with_language_context
async def handle_forward_callback(update: Update, context: ContextTypes.DEFAULT_TYPE, lang_ctx) -> None:
    """
    Handle forward button click - 转发归档消息到频道
    
    Callback data format: forward:archive_id
    
    Args:
        update: Telegram update
        context: Bot context
    """
    query = update.callback_query
    
    try:
        # 解析 callback data: forward:archive_id
        archive_id = int(query.data.split(':')[1])
        
        # 获取归档信息
        db_storage = context.bot_data.get('db_storage')
        if not db_storage:
            await query.answer("Database not initialized", show_alert=True)
            return
        
        # 查询归档
        archive = db_storage.db.execute(
            "SELECT storage_path, storage_type FROM archives WHERE id = ? AND deleted = 0",
            (archive_id,)
        ).fetchone()
        
        if not archive:
            await query.answer("归档不存在", show_alert=True)
            return
        
        storage_path = archive['storage_path']
        storage_type = archive['storage_type']
        
        if storage_type != 'telegram' or not storage_path:
            await query.answer("此归档无法转发", show_alert=True)
            return
        
        # 解析storage_path获取消息ID
        parts = storage_path.split(':')
        if len(parts) >= 2:
            channel_id = int(parts[0]) if parts[0].startswith('-') else int(f"-100{parts[0]}")
            message_id = int(parts[1])
        else:
            from ..utils.config import get_config
            config = get_config()
            channel_id = config.telegram_channel_id
            message_id = int(storage_path)
        
        # 转发消息到用户
        try:
            await context.bot.forward_message(
                chat_id=update.effective_chat.id,
                from_chat_id=channel_id,
                message_id=message_id
            )
            await query.answer("✅ 已转发")
            logger.info(f"Forwarded archive {archive_id} to user {update.effective_user.id}")
        except Exception as fwd_error:
            logger.error(f"Forward error: {fwd_error}")
            await query.answer("转发失败，可能是权限问题", show_alert=True)
        
    except Exception as e:
        logger.error(f"Error handling forward callback: {e}", exc_info=True)
