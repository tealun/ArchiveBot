"""
Note Storage Helper
将笔记转发到Telegram频道的公共函数
"""

import logging
from typing import Optional, Tuple
from telegram.ext import ContextTypes
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

logger = logging.getLogger(__name__)


def _select_note_channel_id(config) -> Optional[int]:
    """
    选择笔记存储频道ID
    优先级：NOTE频道 → TEXT频道 → 默认频道 → 旧配置兼容
    
    Args:
        config: 配置对象
        
    Returns:
        频道ID或None
    """
    # 优先直接获取NOTE频道
    note_channel_id = config.get('storage.telegram.channels.note', 0)
    
    # 如果NOTE频道未配置，降级到TEXT频道
    if not note_channel_id:
        note_channel_id = config.get('storage.telegram.channels.text', 0)
    
    # 如果TEXT频道也未配置，使用默认频道
    if not note_channel_id:
        note_channel_id = config.get('storage.telegram.channels.default', 0)
        if not note_channel_id:
            # 兼容旧配置
            note_channel_id = config.get('storage.telegram.channel_id', 0)
    
    return note_channel_id if note_channel_id else None


def _build_note_buttons(note_id: int, archive_id: Optional[int], is_favorite: bool) -> InlineKeyboardMarkup:
    """
    构建笔记按钮
    
    Args:
        note_id: 笔记ID
        archive_id: 关联的存档ID（可选）
        is_favorite: 是否精选
        
    Returns:
        按钮markup
    """
    keyboard = []
    fav_icon = "❤️" if is_favorite else "🤍"
    
    # 如果有关联存档，添加查看存档按钮
    if archive_id:
        keyboard.append([
            InlineKeyboardButton("📄 查看存档", callback_data=f"ch_archive:{archive_id}"),
            InlineKeyboardButton(fav_icon, callback_data=f"note_fav:{note_id}"),
            InlineKeyboardButton("🗑️ 删除", callback_data=f"ch_del_note:{note_id}")
        ])
    else:
        # 独立笔记（没有关联存档）
        keyboard.append([
            InlineKeyboardButton(fav_icon, callback_data=f"note_fav:{note_id}"),
            InlineKeyboardButton("🗑️ 删除", callback_data=f"ch_del_note:{note_id}")
        ])
    
    return InlineKeyboardMarkup(keyboard)


def _generate_storage_path(channel_id: int, message_id: int) -> str:
    """
    生成Telegram频道消息链接
    
    Args:
        channel_id: 频道ID（格式：-100XXXXXXXXXX）
        message_id: 消息ID
        
    Returns:
        storage_path链接（格式：https://t.me/c/XXXXXXXXXX/message_id）
    """
    channel_id_str = str(channel_id)
    if channel_id_str.startswith('-100'):
        # 移除-100前缀
        channel_id_numeric = channel_id_str[4:]
    else:
        # 处理其他格式（理论上不应该出现）
        channel_id_numeric = channel_id_str.lstrip('-')
    
    return f"https://t.me/c/{channel_id_numeric}/{message_id}"


def _get_note_info(note_id: int, note_manager) -> Tuple[Optional[int], bool]:
    """
    获取笔记关联信息
    
    Args:
        note_id: 笔记ID
        note_manager: 笔记管理器
        
    Returns:
        (archive_id, is_favorite) 元组
    """
    archive_id = None
    is_favorite = False
    
    if not note_manager:
        return archive_id, is_favorite
    
    try:
        # 获取archive_id
        note_data = note_manager.db.execute(
            "SELECT archive_id FROM notes WHERE id = ?",
            (note_id,)
        ).fetchone()
        if note_data:
            archive_id = note_data['archive_id']
        
        # 查询精选状态
        fav_result = note_manager.db.execute(
            "SELECT favorite FROM notes WHERE id = ?",
            (note_id,)
        ).fetchone()
        is_favorite = fav_result['favorite'] == 1 if fav_result else False
    except Exception as e:
        logger.warning(f"Failed to get note info: {e}")
    
    return archive_id, is_favorite


async def update_archive_message_buttons(
    context: ContextTypes.DEFAULT_TYPE,
    archive_id: int
) -> bool:
    """
    更新存档消息的按钮（当笔记状态变化时）
    
    Args:
        context: Bot context
        archive_id: 存档ID
        
    Returns:
        是否成功更新
    """
    try:
        telegram_storage = context.bot_data.get('telegram_storage')
        db_storage = context.bot_data.get('db_storage')
        
        if not telegram_storage or not db_storage:
            logger.debug("Storage not available for updating buttons")
            return False
        
        # 查询存档的storage_path
        archive = db_storage.db.execute(
            "SELECT storage_path FROM archives WHERE id = ? AND deleted = 0",
            (archive_id,)
        ).fetchone()
        
        if not archive or not archive['storage_path']:
            logger.debug(f"Archive {archive_id} has no storage_path")
            return False
        
        storage_path = archive['storage_path']
        
        # 解析storage_path: channel_id:message_id:file_id
        parts = storage_path.split(':')
        if len(parts) < 2:
            logger.debug(f"Invalid storage_path format: {storage_path}")
            return False
        
        channel_id = int(parts[0])
        message_id = int(parts[1])
        
        # 查询笔记和精选状态
        notes_result = db_storage.db.execute(
            "SELECT COUNT(*) as count FROM notes WHERE archive_id = ? AND deleted = 0",
            (archive_id,)
        ).fetchone()
        has_notes = notes_result['count'] > 0 if notes_result else False
        
        fav_result = db_storage.db.execute(
            "SELECT favorite FROM archives WHERE id = ?",
            (archive_id,)
        ).fetchone()
        is_favorite = fav_result['favorite'] == 1 if fav_result else False
        
        # 生成新按钮
        reply_markup = telegram_storage._create_archive_buttons(archive_id, has_notes, is_favorite)
        
        # 更新频道消息的按钮
        try:
            await context.bot.edit_message_reply_markup(
                chat_id=channel_id,
                message_id=message_id,
                reply_markup=reply_markup
            )
            logger.info(f"Updated buttons for archive {archive_id} (has_notes={has_notes})")
            return True
        except Exception as e:
            logger.warning(f"Failed to update message buttons: {e}")
            return False
            
    except Exception as e:
        logger.error(f"Error updating archive message buttons: {e}", exc_info=True)
        return False


async def forward_note_to_channel(
    context: ContextTypes.DEFAULT_TYPE,
    note_id: int,
    note_content: str,
    note_title: Optional[str] = None,
    note_manager = None
) -> Optional[str]:
    """
    将笔记转发到Telegram频道并更新storage_path
    
    统一的笔记频道存档逻辑，供自动生成笔记和手动笔记模式复用
    
    Args:
        context: Bot context
        note_id: 笔记ID
        note_content: 笔记内容
        note_title: 笔记标题（可选）
        note_manager: NoteManager实例（可选，如不提供则从context获取）
        
    Returns:
        storage_path: 频道消息链接 (https://t.me/c/xxx/xxx) 或 None（如果转发失败）
    """
    try:
        telegram_storage = context.bot_data.get('telegram_storage')
        if not telegram_storage:
            logger.warning("Telegram storage not available, skipping note forward")
            return None
        
        from .config import get_config
        config = get_config()
        
        # 选择笔记频道ID
        note_channel_id = _select_note_channel_id(config)
        if not note_channel_id:
            logger.warning("No Telegram channel configured for notes")
            return None
        
        # 准备转发的消息内容 - 格式：📝  [笔记 #X] 标题\n\n内容
        forward_header = f"📝  [笔记 #{note_id}] {note_title or '无标题'}\n\n"
        forward_content = forward_header + note_content
        
        # 使用智能分割（如果内容超过4096字符）
        from .helpers import split_long_message
        message_parts = split_long_message(forward_content, max_length=4096, preserve_newlines=True)
        
        # 获取笔记关联信息
        if not note_manager:
            note_manager = context.bot_data.get('note_manager')
        
        archive_id, is_favorite = _get_note_info(note_id, note_manager)
        
        # 生成按钮（笔记专用按钮）
        reply_markup = None
        try:
            reply_markup = _build_note_buttons(note_id, archive_id, is_favorite)
        except Exception as e:
            logger.warning(f"Failed to create buttons for note #{note_id}: {e}")
        
        # 发送第一条消息（获取链接，带按钮）
        first_msg = await context.bot.send_message(
            chat_id=note_channel_id,
            text=message_parts[0],
            parse_mode=None,
            reply_markup=reply_markup
        )
        
        # 发送后续消息（如果有）
        if len(message_parts) > 1:
            for i, part in enumerate(message_parts[1:], start=2):
                await context.bot.send_message(
                    chat_id=note_channel_id,
                    text=f"[续 {i}/{len(message_parts)}]\n\n{part}",
                    parse_mode=None,
                    reply_to_message_id=first_msg.message_id  # 回复第一条消息，形成线程
                )
            logger.info(f"Note #{note_id} split into {len(message_parts)} messages for channel")
        
        # 生成频道消息链接（使用第一条消息）
        storage_path = _generate_storage_path(note_channel_id, first_msg.message_id)
        
        # 更新笔记的storage_path
        if note_manager:
            note_manager.db.execute(
                "UPDATE notes SET storage_path = ? WHERE id = ?",
                (storage_path, note_id)
            )
            note_manager.db.commit()
            logger.info(f"Note #{note_id} forwarded to channel: {storage_path}")
        else:
            logger.warning(f"Note manager not available, storage_path not updated for note #{note_id}")
        
        return storage_path
        
    except Exception as e:
        logger.error(f"Failed to forward note #{note_id} to channel: {e}", exc_info=True)
        return None
