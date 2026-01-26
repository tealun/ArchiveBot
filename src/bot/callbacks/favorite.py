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
        
        # 切换精选状态
        is_fav = db.is_favorite(archive_id)
        success = db.set_favorite(archive_id, not is_fav)
        
        if success:
            new_status = not is_fav
            
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
