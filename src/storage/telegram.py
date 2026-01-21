"""
Telegram channel storage provider
Stores files in a private Telegram channel
"""

import logging
from typing import Optional, Any
from telegram import Bot

from .base import BaseStorage

logger = logging.getLogger(__name__)


class TelegramStorage(BaseStorage):
    """
    Telegram channel storage provider
    Stores files in a private Telegram channel (< 10MB)
    """
    
    def __init__(self, bot: Bot, channel_id: int):
        """
        Initialize Telegram storage
        
        Args:
            bot: Telegram bot instance
            channel_id: Channel ID for storage
        """
        self.bot = bot
        self.channel_id = channel_id
    
    async def store(self, file_data: Any, metadata: dict) -> Optional[str]:
        """
        Store file to Telegram channel
        
        Args:
            file_data: File to store (file_id or file object)
            metadata: File metadata (title, caption, etc.)
            
        Returns:
            Storage path in format "channel_id:message_id" or None
        """
        try:
            file_id = metadata.get('file_id')
            content_type = metadata.get('content_type')
            caption = metadata.get('caption')
            
            logger.info(f"Forwarding to channel: content_type={content_type}, file_id={file_id[:20] if file_id else 'None'}...")
            
            if not file_id:
                logger.error(f"No file_id provided")
                return None
            
            if not content_type:
                logger.error(f"No content_type provided")
                return None
            
            # 直接使用file_id转发（简单、快速、可靠、支持2GB）
            message = None
            
            # 直接使用file_id转发（简单、快速、可靠、支持2GB）
            message = None
            
            try:
                if content_type == 'image':
                    message = await self.bot.send_photo(
                        chat_id=self.channel_id,
                        photo=file_id,
                        caption=caption
                    )
                elif content_type == 'video':
                    message = await self.bot.send_video(
                        chat_id=self.channel_id,
                        video=file_id,
                        caption=caption
                    )
                elif content_type == 'document':
                    message = await self.bot.send_document(
                        chat_id=self.channel_id,
                        document=file_id,
                        caption=caption
                    )
                elif content_type == 'audio':
                    message = await self.bot.send_audio(
                        chat_id=self.channel_id,
                        audio=file_id,
                        caption=caption
                    )
                elif content_type == 'voice':
                    message = await self.bot.send_voice(
                        chat_id=self.channel_id,
                        voice=file_id,
                        caption=caption
                    )
                elif content_type == 'animation':
                    message = await self.bot.send_animation(
                        chat_id=self.channel_id,
                        animation=file_id,
                        caption=caption
                    )
                else:
                    # 默认作为文档发送
                    logger.warning(f"Unknown content_type '{content_type}', sending as document")
                    message = await self.bot.send_document(
                        chat_id=self.channel_id,
                        document=file_id,
                        caption=caption
                    )
            except Exception as e:
                logger.error(f"Failed to forward to channel: {e}")
                raise
            
            if message:
                # 从频道消息中提取新的file_id（重要：这样即使原消息删除，频道file_id仍然有效）
                channel_file_id = None
                if content_type == 'image' and message.photo:
                    channel_file_id = message.photo[-1].file_id  # 最大尺寸
                elif content_type == 'video' and message.video:
                    channel_file_id = message.video.file_id
                elif content_type == 'document' and message.document:
                    channel_file_id = message.document.file_id
                elif content_type == 'audio' and message.audio:
                    channel_file_id = message.audio.file_id
                elif content_type == 'voice' and message.voice:
                    channel_file_id = message.voice.file_id
                elif content_type == 'animation' and message.animation:
                    channel_file_id = message.animation.file_id
                
                # Return storage path as "channel_id:message_id:file_id"
                # 格式：channel_id:message_id:channel_file_id
                storage_path = f"{self.channel_id}:{message.message_id}:{channel_file_id}" if channel_file_id else f"{self.channel_id}:{message.message_id}"
                logger.info(f"File stored in Telegram channel: {storage_path}")
                return storage_path
            
            return None
            
        except Exception as e:
            logger.error(f"Error storing file in Telegram: {e}", exc_info=True)
            return None
    
    async def retrieve(self, storage_path: str) -> Optional[Any]:
        """
        Retrieve file from Telegram channel
        
        Args:
            storage_path: Storage path in format "channel_id:message_id:file_id" or "channel_id:message_id"
            
        Returns:
            Dict with channel_id, message_id, and optionally file_id
        """
        try:
            parts = storage_path.split(':')
            if len(parts) < 2:
                logger.error(f"Invalid storage path format: {storage_path}")
                return None
            
            result = {
                'channel_id': int(parts[0]),
                'message_id': int(parts[1])
            }
            
            # 如果有file_id（新格式），也返回
            if len(parts) >= 3:
                result['file_id'] = parts[2]
            
            return result
            
        except Exception as e:
            logger.error(f"Error retrieving file from Telegram: {e}", exc_info=True)
            return None
    
    async def delete(self, storage_path: str) -> bool:
        """
        Delete file from Telegram channel
        
        Args:
            storage_path: Storage path in format "channel_id:message_id"
            
        Returns:
            True if deleted, False otherwise
        """
        try:
            parts = storage_path.split(':')
            if len(parts) != 2:
                logger.error(f"Invalid storage path format: {storage_path}")
                return False
            
            channel_id = int(parts[0])
            message_id = int(parts[1])
            
            # Delete message from channel
            await self.bot.delete_message(
                chat_id=channel_id,
                message_id=message_id
            )
            
            logger.info(f"File deleted from Telegram channel: {storage_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting file from Telegram: {e}", exc_info=True)
            return False
    
    def is_available(self) -> bool:
        """
        Check if Telegram storage is available
        
        Returns:
            True if channel ID is configured, False otherwise
        """
        return self.channel_id is not None and self.channel_id != 0
