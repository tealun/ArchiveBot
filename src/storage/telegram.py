"""
Telegram channel storage provider
Stores files in a private Telegram channel
"""

import logging
from typing import Optional, Any
from telegram import Bot, InlineKeyboardButton, InlineKeyboardMarkup

from .base import BaseStorage

logger = logging.getLogger(__name__)


class TelegramStorage(BaseStorage):
    """
    Telegram channel storage provider
    Stores files in a private Telegram channel (< 2GB)
    Supports multiple channels by content type
    """
    
    def __init__(self, bot: Bot, config: dict):
        """
        Initialize Telegram storage
        
        Args:
            bot: Telegram bot instance
            config: Storage config with channels mapping
                - channels: dict with channel IDs (default, text, document, ebook, image, media)
                - type_mapping: dict mapping content_type to channel key
        """
        self.bot = bot
        self.config = config
        
        # 兼容旧配置：如果传入的是int，当作默认频道
        if isinstance(config, int):
            self.channels = {'default': config}
            self.type_mapping = {}
        else:
            # 新配置格式
            self.channels = config.get('channels', {})
            self.type_mapping = config.get('type_mapping', {})
            
            # 向后兼容：如果有旧的channel_id配置，作为默认频道
            if 'channel_id' in config and config['channel_id']:
                if 'default' not in self.channels:
                    self.channels['default'] = config['channel_id']
        
        # 确保有默认频道
        self.default_channel = self.channels.get('default')
        logger.info(f"TelegramStorage initialized with {len(self.channels)} channels, default: {self.default_channel}")
    
    def _create_archive_buttons(self, archive_id: int, has_notes: bool = False, is_favorite: bool = False) -> InlineKeyboardMarkup:
        """
        创建存档消息的按钮
        
        Args:
            archive_id: 存档ID
            has_notes: 是否已有笔记
            is_favorite: 是否已精选
            
        Returns:
            InlineKeyboardMarkup
        """
        note_text = "📝 查看笔记" if has_notes else "📝 添加笔记"
        fav_icon = "❤️" if is_favorite else "🤍"
        keyboard = [
            [
                InlineKeyboardButton(note_text, callback_data=f"ch_note:{archive_id}"),
                InlineKeyboardButton(fav_icon, callback_data=f"fav:{archive_id}"),
                InlineKeyboardButton("🗑️ 删除", callback_data=f"ch_del:{archive_id}")
            ]
        ]
        return InlineKeyboardMarkup(keyboard)
    
    def _get_channel_id(self, content_type: str) -> int:
        """
        根据content_type获取对应的频道ID
        
        Args:
            content_type: 内容类型
            
        Returns:
            频道ID
        """
        # 1. 查找type_mapping映射
        channel_key = self.type_mapping.get(content_type)
        
        # 2. 如果没有映射，直接用content_type作为key
        if not channel_key:
            channel_key = content_type
        
        # 3. 获取频道ID
        channel_id = self.channels.get(channel_key)
        
        # 4. 如果没有配置，使用默认频道
        if not channel_id:
            channel_id = self.default_channel
            logger.debug(f"No specific channel for {content_type}, using default channel")
        else:
            logger.debug(f"Using {channel_key} channel for {content_type}")
        
        return channel_id
    
    async def store(self, file_data: Any, metadata: dict) -> Optional[str]:
        """
        Store file to Telegram channel
        
        Args:
            file_data: File to store (file_id or file object)
            metadata: File metadata (title, caption, content_type, override_channel_id, archive_id, has_notes, etc.)
            
        Returns:
            Storage path in format "channel_id:message_id:file_id" or None
        """
        try:
            file_id = metadata.get('file_id')
            content_type = metadata.get('content_type')
            caption = metadata.get('caption')
            override_channel_id = metadata.get('override_channel_id')
            archive_id = metadata.get('archive_id')
            has_notes = metadata.get('has_notes', False)
            is_favorite = metadata.get('is_favorite', False)
            
            # 根据content_type选择频道（可被override_channel_id覆盖）
            channel_id = override_channel_id if override_channel_id else self._get_channel_id(content_type)
            
            if not channel_id:
                logger.error(f"No channel configured for content_type: {content_type}")
                return None
            
            logger.info(f"Forwarding to channel {channel_id}: content_type={content_type}, file_id={file_id[:20] if file_id else 'None'}...")
            
            # 文本和链接类型：发送文本消息（不需要file_id）
            if content_type in ['text', 'link']:
                content = metadata.get('content') or caption or ''
                if not content:
                    logger.error("No content for text/link type")
                    return None
                
                # 添加标题（如果有）
                title = metadata.get('title', '')
                if title and title != content[:100]:
                    formatted_text = f"<b>{title}</b>\n\n{content}"
                else:
                    formatted_text = content
                
                # 生成按钮（如果有archive_id）
                reply_markup = None
                if archive_id:
                    reply_markup = self._create_archive_buttons(archive_id, has_notes, is_favorite)
                
                # 超长文本(>8192字符)改用document形式存储
                if len(formatted_text) > 8192:
                    try:
                        import io
                        from datetime import datetime
                        
                        # 创建文本文件
                        text_file = io.BytesIO(formatted_text.encode('utf-8'))
                        file_name = f"{title[:50] if title else 'text'}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
                        text_file.name = file_name
                        
                        # 作为document发送
                        message = await self.bot.send_document(
                            chat_id=channel_id,
                            document=text_file,
                            caption=f"📄 长文本文档\n\n{title if title else '无标题'}" if title else "📄 长文本文档",
                            filename=file_name,
                            reply_markup=reply_markup
                        )
                        
                        if message and message.document:
                            storage_path = f"{channel_id}:{message.message_id}:{message.document.file_id}"
                            logger.info(f"Long text stored as document in Telegram channel: {storage_path} ({len(formatted_text)} chars)")
                            return storage_path
                        
                    except Exception as e:
                        logger.warning(f"Failed to store long text as document: {e}, falling back to split messages")
                        # 失败则回退到分片发送
                
                # 使用智能分割处理超长文本（不截断）
                from ..utils.helpers import split_long_message
                text_parts = split_long_message(formatted_text, max_length=4096, preserve_newlines=True)
                
                # 发送第一条消息
                first_message = await self.bot.send_message(
                    chat_id=channel_id,
                    text=text_parts[0],
                    parse_mode='HTML',
                    disable_web_page_preview=False,  # 链接类型显示预览
                    reply_markup=reply_markup  # 按钮只在第一条消息上
                )
                
                if not first_message:
                    logger.error("Failed to send first message part")
                    return None
                
                # 发送后续消息（如果有）
                if len(text_parts) > 1:
                    for i, part in enumerate(text_parts[1:], start=2):
                        await self.bot.send_message(
                            chat_id=channel_id,
                            text=f"[续 {i}/{len(text_parts)}]\n\n{part}",
                            parse_mode='HTML',
                            disable_web_page_preview=False,
                            reply_to_message_id=first_message.message_id  # 回复第一条消息，形成线程
                        )
                    logger.info(f"{content_type} split into {len(text_parts)} messages for channel")
                
                # 返回第一条消息的路径
                storage_path = f"{channel_id}:{first_message.message_id}"
                logger.info(f"Text/Link stored in Telegram channel: {storage_path}")
                return storage_path
            
            # 媒体文件类型：需要file_id
            if not file_id:
                logger.error(f"No file_id provided for {content_type}")
                return None
            
            if not content_type:
                logger.error(f"No content_type provided")
                return None
            
            # Telegram caption 长度限制：1024字符
            # 如果 caption 过长，截断并添加省略标记
            if caption and len(caption) > 1024:
                logger.warning(f"Caption too long ({len(caption)} chars), truncating to 1024")
                caption = caption[:1020] + "..."
            
            # 生成按钮（如果有archive_id）
            reply_markup = None
            if archive_id:
                reply_markup = self._create_archive_buttons(archive_id, has_notes, is_favorite)
            
            # 直接使用file_id转发（简单、快速、可靠、支持2GB）
            message = None
            
            try:
                # ebook类型按document发送
                send_type = content_type
                if content_type == 'ebook':
                    send_type = 'document'
                
                if send_type == 'image':
                    message = await self.bot.send_photo(
                        chat_id=channel_id,
                        photo=file_id,
                        caption=caption,
                        reply_markup=reply_markup
                    )
                elif send_type == 'video':
                    message = await self.bot.send_video(
                        chat_id=channel_id,
                        video=file_id,
                        caption=caption,
                        reply_markup=reply_markup
                    )
                elif send_type in ['document', 'ebook']:
                    message = await self.bot.send_document(
                        chat_id=channel_id,
                        document=file_id,
                        caption=caption,
                        reply_markup=reply_markup
                    )
                elif send_type == 'audio':
                    message = await self.bot.send_audio(
                        chat_id=channel_id,
                        audio=file_id,
                        caption=caption,
                        reply_markup=reply_markup
                    )
                elif send_type == 'voice':
                    message = await self.bot.send_voice(
                        chat_id=channel_id,
                        voice=file_id,
                        caption=caption,
                        reply_markup=reply_markup
                    )
                elif send_type == 'animation':
                    message = await self.bot.send_animation(
                        chat_id=channel_id,
                        animation=file_id,
                        caption=caption,
                        reply_markup=reply_markup
                    )
                else:
                    # 默认作为文档发送
                    logger.warning(f"Unknown content_type '{content_type}', sending as document")
                    message = await self.bot.send_document(
                        chat_id=channel_id,
                        document=file_id,
                        caption=caption,
                        reply_markup=reply_markup
                    )
            except Exception as e:
                logger.error(f"Failed to forward to channel: {e}")
                raise
            
            if message:
                # 从频道消息中提取新的file_id（重要：这样即使原消息删除，频道file_id仍然有效）
                channel_file_id = None
                if send_type == 'image' and message.photo:
                    channel_file_id = message.photo[-1].file_id  # 最大尺寸
                elif send_type == 'video' and message.video:
                    channel_file_id = message.video.file_id
                elif send_type in ['document', 'ebook'] and message.document:
                    channel_file_id = message.document.file_id
                elif send_type == 'audio' and message.audio:
                    channel_file_id = message.audio.file_id
                elif send_type == 'voice' and message.voice:
                    channel_file_id = message.voice.file_id
                elif send_type == 'animation' and message.animation:
                    channel_file_id = message.animation.file_id
                
                # Return storage path as "channel_id:message_id:file_id"
                # 格式：channel_id:message_id:channel_file_id
                storage_path = f"{channel_id}:{message.message_id}:{channel_file_id}" if channel_file_id else f"{channel_id}:{message.message_id}"
                logger.info(f"File stored in Telegram channel: {storage_path}")
                return storage_path
            
            return None
            
        except Exception as e:
            logger.error(f"Error storing file in Telegram: {e}", exc_info=True)
            return None
    
    async def batch_store(self, metadata_list: list) -> list:
        """
        批量存储文件到Telegram频道（保持媒体群组完整性，按优先级判断存档频道）
        
        优先级规则：视频>音频>图片>文档>文本>其他
        
        Args:
            metadata_list: 元数据列表
            
        Returns:
            storage_path列表（成功的路径，失败为None）
        """
        from telegram import InputMediaPhoto, InputMediaVideo, InputMediaDocument, InputMediaAudio
        
        logger.info(f"Batch storing {len(metadata_list)} files to Telegram channel")
        
        # 初始化结果列表
        storage_paths = [None] * len(metadata_list)
        
        # 检查是否所有项都是可以作为media_group的类型
        media_types = [meta.get('content_type') for meta in metadata_list]
        can_be_media_group = all(mt in ['photo', 'video', 'image', 'audio'] for mt in media_types)
        
        # 如果可以作为media_group且数量在2-10之间
        if can_be_media_group and 2 <= len(metadata_list) <= 10:
            # 按优先级确定频道：视频>音频>图片>其他
            priority_order = {'video': 4, 'audio': 3, 'image': 2, 'photo': 2}
            max_priority = max(priority_order.get(mt, 0) for mt in media_types)
            
            # 确定存档频道（使用第一个item的override_channel_id，或根据最高优先级类型决定）
            first_override = metadata_list[0].get('override_channel_id')
            if first_override:
                channel_id = first_override
            else:
                # 根据最高优先级类型确定频道
                priority_type = None
                for mt in ['video', 'audio', 'image', 'photo']:
                    if priority_order.get(mt, 0) == max_priority and mt in media_types:
                        priority_type = mt
                        break
                channel_id = self._get_channel_id(priority_type) if priority_type else self.default_channel
            
            if not channel_id:
                logger.error("No channel ID configured for media group")
                # 降级为逐个发送
                for i, metadata in enumerate(metadata_list):
                    storage_paths[i] = await self.store(None, metadata)
                return storage_paths
            
            # 构建media_group
            media_group = []
            for i, metadata in enumerate(metadata_list):
                file_id = metadata.get('file_id')
                # 只有第一个item有caption
                caption = metadata.get('caption', '') if i == 0 else None
                content_type = metadata.get('content_type')
                
                if content_type in ['photo', 'image']:
                    media_group.append(InputMediaPhoto(media=file_id, caption=caption))
                elif content_type == 'video':
                    media_group.append(InputMediaVideo(media=file_id, caption=caption))
                elif content_type == 'audio':
                    media_group.append(InputMediaAudio(media=file_id, caption=caption))
            
            # 发送media_group
            try:
                logger.info(f"Sending media_group to channel {channel_id} with {len(media_group)} items (types: {set(media_types)})")
                messages = await self.bot.send_media_group(
                    chat_id=channel_id,
                    media=media_group
                )
                
                # 记录每个消息的storage_path
                for i, msg in enumerate(messages):
                    if i < len(metadata_list):
                        file_id = None
                        if msg.photo:
                            file_id = msg.photo[-1].file_id
                        elif msg.video:
                            file_id = msg.video.file_id
                        elif msg.audio:
                            file_id = msg.audio.file_id
                        
                        storage_path = f"{msg.chat_id}:{msg.message_id}:{file_id}" if file_id else f"{msg.chat_id}:{msg.message_id}"
                        storage_paths[i] = storage_path
                
                # 为第一条消息添加按钮（如果有archive_id）
                if messages and len(metadata_list) > 0:
                    first_metadata = metadata_list[0]
                    archive_id = first_metadata.get('archive_id')
                    has_notes = first_metadata.get('has_notes', False)
                    
                    if archive_id:
                        try:
                            reply_markup = self._create_archive_buttons(archive_id, has_notes)
                            await self.bot.edit_message_reply_markup(
                                chat_id=channel_id,
                                message_id=messages[0].message_id,
                                reply_markup=reply_markup
                            )
                            logger.debug(f"Added buttons to first message of media_group")
                        except Exception as e:
                            logger.warning(f"Failed to add buttons to media_group: {e}")
                
                logger.info(f"Successfully sent media_group with {len(messages)} items")
                return storage_paths
                
            except Exception as e:
                logger.error(f"Failed to send media_group: {e}", exc_info=True)
                # 降级为逐个发送
                for i, metadata in enumerate(metadata_list):
                    storage_paths[i] = await self.store(None, metadata)
                return storage_paths
        
        # 不能作为media_group或数量不符合，逐个发送
        for i, metadata in enumerate(metadata_list):
            storage_paths[i] = await self.store(None, metadata)
        
        return storage_paths
    
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
            True if default channel ID is configured, False otherwise
        """
        return self.default_channel is not None and self.default_channel != 0
    
    async def delete_message(self, storage_path: str) -> bool:
        """
        Delete a message from Telegram channel
        
        Args:
            storage_path: Storage path in format "channel_id:message_id" or "channel_id:message_id:file_id"
            
        Returns:
            True if successful, False otherwise
        """
        try:
            if not storage_path:
                logger.warning("No storage_path provided for delete")
                return False
            
            # Parse storage_path
            parts = storage_path.split(':')
            if len(parts) < 2:
                logger.warning(f"Invalid storage_path format: {storage_path}")
                return False
            
            channel_id = int(parts[0])
            message_id = int(parts[1])
            
            # Delete the message
            await self.bot.delete_message(chat_id=channel_id, message_id=message_id)
            logger.info(f"Deleted message from channel: {channel_id}:{message_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to delete message {storage_path}: {e}", exc_info=True)
            return False
