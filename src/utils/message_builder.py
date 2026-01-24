"""
消息构建框架
提供统一的消息格式化和资源发送功能
"""

import logging
from typing import List, Dict, Any, Optional
from telegram import Bot, Message
from telegram.constants import ParseMode

from ..utils.helpers import truncate_text, get_content_type_emoji

logger = logging.getLogger(__name__)


class MessageBuilder:
    """消息构建器 - 统一处理列表消息和资源发送"""
    
    @staticmethod
    def format_archive_list(
        archives: List[Dict[str, Any]],
        i18n,
        db_instance=None,
        with_links: bool = True
    ) -> str:
        """
        格式化归档列表 - 复用搜索结果的格式
        
        Args:
            archives: 归档列表
            i18n: 国际化对象
            db_instance: 数据库实例（用于检查精选和笔记状态）
            with_links: 是否包含Telegram跳转链接
            
        Returns:
            格式化的消息文本
        """
        if not archives:
            return i18n.t('search_no_results', keyword='')
        
        formatted_results = []
        
        for idx, archive in enumerate(archives, 1):
            archive_id = archive.get('id')
            emoji = get_content_type_emoji(archive.get('content_type', ''))
            title = archive.get('title', 'Untitled')
            title_truncated = truncate_text(title, 50)
            
            # 构建跳转链接（如果有storage_path）
            storage_path = archive.get('storage_path')
            storage_type = archive.get('storage_type')
            
            if with_links and storage_path and storage_type == 'telegram':
                # 解析 storage_path: 可能是 "message_id" 或 "channel_id:message_id" 或 "channel_id:message_id:file_id"
                parts = storage_path.split(':')
                if len(parts) >= 2:
                    # 格式: channel_id:message_id[:file_id]
                    channel_id = parts[0].replace('-100', '')  # 移除-100前缀
                    message_id = parts[1]
                else:
                    # 格式: message_id（需要从配置获取channel_id）
                    from ..utils.config import get_config
                    config = get_config()
                    channel_id = str(config.telegram_channel_id).replace('-100', '')
                    message_id = storage_path
                
                # Telegram链接格式：https://t.me/c/{channel_id}/{message_id}
                link = f"https://t.me/c/{channel_id}/{message_id}"
                title_truncated = f"<a href='{link}'>{title_truncated}</a>"
            
            # Get tags for this archive
            tags = archive.get('tags', [])
            tags_str = ' '.join(f"#{tag}" for tag in tags) if tags else ''
            
            archived_at = archive.get('archived_at', '')
            
            # 检查精选和笔记状态
            is_favorite = db_instance.is_favorite(archive_id) if db_instance else False
            has_notes = db_instance.has_notes(archive_id) if db_instance else False
            
            # 构建状态图标
            fav_icon = "❤️ 已精选" if is_favorite else "🤍 未精选"
            note_icon = "📝 √ 有笔记" if has_notes else "📝 无笔记"
            
            # 格式化结果为一行
            result_text = f"{idx}. {emoji} {title_truncated}"
            if tags_str:
                result_text += f"\n   {tags_str}"
            result_text += f"\n   {fav_icon} | {note_icon} | 📅 {archived_at}"
            
            formatted_results.append(result_text)
        
        results_text = '\n---------------------\n'.join(formatted_results)
        
        return results_text
    
    @staticmethod
    async def send_archive_resource(
        bot: Bot,
        chat_id: int,
        archive: Dict[str, Any],
        caption: Optional[str] = None
    ) -> Optional[Message]:
        """
        发送归档资源文件
        
        Args:
            bot: Telegram Bot实例
            chat_id: 接收者chat_id
            archive: 归档记录（包含storage_path, content_type等）
            caption: 可选的说明文字
            
        Returns:
            发送的消息对象，失败返回None
        """
        try:
            storage_path = archive.get('storage_path')
            storage_type = archive.get('storage_type')
            content_type = archive.get('content_type')
            title = archive.get('title', '')
            
            # 只支持telegram存储的资源
            if storage_type != 'telegram' or not storage_path:
                logger.warning(f"Cannot send resource: storage_type={storage_type}, storage_path={storage_path}")
                return None
            
            # 解析storage_path获取file_id
            # 格式: "channel_id:message_id:file_id" 或 "message_id:file_id" 或仅 "message_id"
            parts = storage_path.split(':')
            file_id = None
            
            if len(parts) >= 3:
                # 格式: channel_id:message_id:file_id
                file_id = parts[2]
            elif len(parts) == 2:
                # 可能是 channel_id:message_id 或 message_id:file_id
                # 尝试判断：如果第一个是负数，则是channel_id
                if parts[0].startswith('-'):
                    # channel_id:message_id，没有file_id，需要从archive中获取
                    file_id = archive.get('file_id')
                else:
                    # message_id:file_id
                    file_id = parts[1]
            else:
                # 仅message_id，从archive获取file_id
                file_id = archive.get('file_id')
            
            if not file_id:
                logger.warning(f"No file_id found for archive {archive.get('id')}")
                return None
            
            # 构建caption（如果没有提供）
            if not caption:
                caption = f"📚 {title}" if title else None
            
            # 根据content_type选择发送方法
            if content_type == 'photo':
                return await bot.send_photo(chat_id=chat_id, photo=file_id, caption=caption)
            elif content_type == 'video':
                return await bot.send_video(chat_id=chat_id, video=file_id, caption=caption)
            elif content_type == 'audio':
                return await bot.send_audio(chat_id=chat_id, audio=file_id, caption=caption)
            elif content_type == 'voice':
                return await bot.send_voice(chat_id=chat_id, voice=file_id, caption=caption)
            elif content_type in ['document', 'ebook']:
                return await bot.send_document(chat_id=chat_id, document=file_id, caption=caption)
            else:
                # 其他类型尝试作为document发送
                logger.info(f"Sending {content_type} as document")
                return await bot.send_document(chat_id=chat_id, document=file_id, caption=caption)
        
        except Exception as e:
            logger.error(f"Failed to send archive resource: {e}", exc_info=True)
            return None
    
    @staticmethod
    async def send_archive_resources_batch(
        bot: Bot,
        chat_id: int,
        archives: List[Dict[str, Any]],
        max_count: int = 10
    ) -> int:
        """
        批量发送归档资源文件
        
        Args:
            bot: Telegram Bot实例
            chat_id: 接收者chat_id
            archives: 归档列表
            max_count: 最大发送数量（Telegram限制，建议不超过10）
            
        Returns:
            成功发送的数量
        """
        sent_count = 0
        
        for archive in archives[:max_count]:
            result = await MessageBuilder.send_archive_resource(bot, chat_id, archive)
            if result:
                sent_count += 1
        
        return sent_count
