"""
Note Favorite callbacks
处理笔记精选/取消精选功能
"""

import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


async def handle_note_favorite_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
    处理笔记精选/取消精选按钮点击
    
    Callback data format: note_fav:note_id
    """
    query = update.callback_query
    
    try:
        # 解析 callback data: note_fav:note_id
        note_id = int(query.data.split(':')[1])
        
        # 获取数据库
        db_storage = context.bot_data.get('db_storage')
        if not db_storage:
            await query.answer("数据库不可用", show_alert=True)
            logger.error("Database storage not initialized")
            return
        
        db = db_storage.db
        
        # 获取笔记信息
        note = db.execute(
            "SELECT id, content, storage_path, archive_id, favorite, featured_channel_message_id FROM notes WHERE id = ? AND deleted = 0",
            (note_id,)
        ).fetchone()
        
        if not note:
            await query.answer("笔记不存在", show_alert=True)
            logger.error(f"Note {note_id} not found")
            return
        
        # 切换精选状态
        is_fav = note['favorite'] == 1
        new_status = not is_fav
        
        # 处理精选频道同步
        featured_message_id = None
        if new_status:
            # 标记为精选：转发到精选频道（如果配置了）
            featured_message_id = await _forward_note_to_featured_channel(
                context, note, note_id
            )
        else:
            # 取消精选：从精选频道删除（如果存在）
            await _delete_note_from_featured_channel(
                context, note, note_id
            )
        
        # 更新数据库
        success = db.set_note_favorite(note_id, new_status)
        
        # 如果精选成功且有featured_message_id，更新到数据库
        if success and new_status and featured_message_id:
            try:
                with db._lock:
                    db.execute(
                        "UPDATE notes SET featured_channel_message_id = ? WHERE id = ?",
                        (featured_message_id, note_id)
                    )
                    db.commit()
                    logger.info(f"Updated featured_channel_message_id for note {note_id}: {featured_message_id}")
            except Exception as e:
                logger.error(f"Failed to update featured_channel_message_id: {e}")
        
        # 如果取消精选，清空featured_channel_message_id
        if success and not new_status:
            try:
                with db._lock:
                    db.execute(
                        "UPDATE notes SET featured_channel_message_id = NULL WHERE id = ?",
                        (note_id,)
                    )
                    db.commit()
                    logger.info(f"Cleared featured_channel_message_id for note {note_id}")
            except Exception as e:
                logger.error(f"Failed to clear featured_channel_message_id: {e}")
        
        if success:
            # 更新按钮显示
            try:
                original_markup = query.message.reply_markup
                if original_markup and original_markup.inline_keyboard:
                    new_keyboard = []
                    for row in original_markup.inline_keyboard:
                        new_row = []
                        for button in row:
                            callback_data = button.callback_data
                            if callback_data and callback_data.startswith(f'note_fav:{note_id}'):
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
                await query.answer("❤️ 笔记已添加到精选")
            else:
                await query.answer("🤍 笔记已取消精选")
            
            logger.info(f"Note {note_id} favorite toggled to {new_status}")
        else:
            await query.answer("操作失败", show_alert=True)
            logger.error(f"Failed to toggle favorite for note {note_id}")
        
    except Exception as e:
        logger.error(f"Error handling note favorite callback: {e}", exc_info=True)
        await query.answer(f"错误: {str(e)}", show_alert=True)


async def _forward_note_to_featured_channel(context: ContextTypes.DEFAULT_TYPE, note: dict, note_id: int) -> str:
    """
    转发笔记到精选频道
    
    Returns:
        featured_message_id in format "channel_id:message_id" or None
    """
    try:
        from src.utils.config import get_config
        config = get_config()
        
        featured_channel_id = config.get('storage.telegram.channels.featured')
        
        if not featured_channel_id:
            logger.debug("No featured channel configured, skipping forward")
            return None
        
        # 从 storage_path解析消息信息
        storage_path = note['storage_path']
        if not storage_path:
            logger.warning(f"Note {note_id} has no storage_path")
            return None
        
        # 解析storage_path格式：https://t.me/c/CHANNEL/MESSAGE_ID
        source_channel_id = None
        message_id = None
        
        if storage_path.startswith('https://t.me/c/'):
            parts = storage_path.replace('https://t.me/c/', '').split('/')
            if len(parts) >= 2:
                channel_numeric = parts[0]
                message_id = int(parts[1])
                # 恢复完整频道ID格式
                source_channel_id = f"-100{channel_numeric}"
        
        if not source_channel_id or not message_id:
            logger.warning(f"Invalid storage_path format: {storage_path}")
            return None
        
        # 转发消息到精选频道
        try:
            forwarded_message = await context.bot.forward_message(
                chat_id=featured_channel_id,
                from_chat_id=source_channel_id,
                message_id=message_id
            )
            
            if forwarded_message:
                featured_message_id = f"{featured_channel_id}:{forwarded_message.message_id}"
                logger.info(f"Forwarded note {note_id} to featured channel: {featured_message_id}")
                return featured_message_id
            
        except Exception as e:
            logger.error(f"Failed to forward note to featured channel: {e}", exc_info=True)
        
        return None
        
    except Exception as e:
        logger.error(f"Error in _forward_note_to_featured_channel: {e}", exc_info=True)
        return None


async def _delete_note_from_featured_channel(context: ContextTypes.DEFAULT_TYPE, note: dict, note_id: int):
    """
    从精选频道删除笔记
    """
    try:
        featured_message_id = note['featured_channel_message_id']
        if not featured_message_id:
            logger.debug(f"Note {note_id} has no featured_channel_message_id, nothing to delete")
            return
        
        # Parse featured_message_id: "channel_id:message_id"
        parts = featured_message_id.split(':')
        if len(parts) >= 2:
            channel_id = int(parts[0])
            message_id = int(parts[1])
            
            try:
                await context.bot.delete_message(
                    chat_id=channel_id,
                    message_id=message_id
                )
                logger.info(f"Deleted note {note_id} from featured channel: {featured_message_id}")
            except Exception as e:
                logger.warning(f"Failed to delete note {note_id} from featured channel: {e}")
        else:
            logger.warning(f"Invalid featured_message_id format: {featured_message_id}")
            
    except Exception as e:
        logger.error(f"Error in _delete_note_from_featured_channel: {e}", exc_info=True)
