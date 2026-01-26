"""
Handler utility functions
"""

import logging
from typing import List, Optional, Dict
from telegram import Update, Message
from telegram.ext import ContextTypes
from telegram.constants import ParseMode

from ...utils.language_context import get_language_context
from ...utils.helpers import format_file_size, truncate_text

logger = logging.getLogger(__name__)


def _cleanup_user_data(user_data: dict, threshold: int = 15) -> None:
    """
    清理user_data中的临时数据，防止内存泄漏
    
    Args:
        user_data: 用户数据字典
        threshold: 触发清理的键数量阈值
    """
    if len(user_data) <= threshold:
        return
    
    # 定义需要保留的持久化键（只保留语言设置）
    persistent_keys = {'language'}
    
    # 定义临时键（会自动清理）
    temporary_keys = [
        'waiting_note_for_archive', 'note_modify_mode', 'note_id_to_modify',
        'note_append_mode', 'note_id_to_append', 'pending_command',
        'refine_note_context', 'pending_short_text'
    ]
    
    # 清理临时键（跳过持久化键和笔记模式相关键）
    removed_count = 0
    for key in list(user_data.keys()):
        # 保留持久化键
        if key in persistent_keys:
            continue
        # 保留笔记模式活跃时的相关键
        if user_data.get('note_mode') and key in ['note_mode', 'note_messages', 'note_archives', 'note_timeout_job', 'note_start_time']:
            continue
        # 清理临时键
        if key in temporary_keys:
            user_data.pop(key, None)
            removed_count += 1
    
    if removed_count > 0:
        logger.info(f"Cleaned up {removed_count} temporary keys from user_data (size: {len(user_data)})")


def _is_media_message(message: Message) -> bool:
    """判断是否为媒体消息"""
    return any([
        message.photo, message.video, message.document,
        message.audio, message.voice, message.animation,
        message.sticker, message.contact, message.location
    ])
