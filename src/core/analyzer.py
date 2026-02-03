"""
Content analyzer module
Identifies and analyzes different types of content
"""

import logging
from typing import Dict, List, Optional, Any
from datetime import datetime
from telegram import Message

from ..utils.helpers import is_url, extract_urls, extract_hashtags
from ..utils.constants import EBOOK_EXTENSIONS
from ..utils.config import get_config

logger = logging.getLogger(__name__)


class ContentAnalyzer:
    """
    Analyzes Telegram messages and extracts metadata
    """
    
    @staticmethod
    def _extract_telegram_link_preview(message: Message) -> Optional[Dict[str, Any]]:
        """
        提取 Telegram 自动生成的链接预览信息
        
        Args:
            message: Telegram message object
            
        Returns:
            包含预览信息的字典，如果没有预览则返回 None
        """
        try:
            # Telegram Bot API 的 link_preview_options (7.0+)
            # 但预览内容（标题、描述等）通常不直接提供给 bot
            # 需要通过其他方式获取
            
            # 检查消息实体中是否有 URL 的 text_link
            if message.entities:
                for entity in message.entities:
                    if entity.type == 'text_link' and entity.url:
                        logger.debug(f"Found text_link entity: {entity.url}")
                        # 可以记录但无法获取预览内容
            
            # 检查 web_page 字段（某些 Telegram 客户端可能有）
            if hasattr(message, 'web_page') and message.web_page:
                web_page = message.web_page
                preview_data = {
                    'source': 'telegram_preview',
                    'title': getattr(web_page, 'title', None),
                    'description': getattr(web_page, 'description', None),
                    'url': getattr(web_page, 'url', None),
                    'site_name': getattr(web_page, 'site_name', None),
                }
                
                # 过滤空值
                preview_data = {k: v for k, v in preview_data.items() if v}
                
                if len(preview_data) > 1:  # 至少有 source 和一个其他字段
                    logger.info(f"✓ Extracted Telegram link preview: {preview_data.get('title', 'No title')}")
                    return preview_data
            
            return None
            
        except Exception as e:
            logger.debug(f"Failed to extract Telegram link preview: {e}")
            return None
    
    @staticmethod
    def analyze(message: Message) -> Dict[str, Any]:
        """
        Analyze message and extract metadata
        
        Args:
            message: Telegram message object
            
        Returns:
            Dictionary containing analysis results
        """
        try:
            config = get_config()
            
            result = {
                'content_type': None,
                'title': None,
                'content': None,
                'file_id': None,
                'file_size': None,
                'file_name': None,
                'mime_type': None,
                'url': None,
                'hashtags': [],
                'source': None,
                'created_at': message.date.isoformat() if message.date else datetime.now().isoformat(),
            }
            
            # Extract hashtags from caption or text (根据配置)
            text = message.caption or message.text or ''
            extract_from_caption = config.get('features.extract_tags_from_caption', False)
            
            # 如果启用从caption提取，或者是非转发消息（用户自己输入的），才提取标签
            is_forwarded = bool(message.forward_origin)
            should_extract = extract_from_caption or not is_forwarded
            
            if should_extract and text:
                result['hashtags'] = extract_hashtags(text)
            else:
                result['hashtags'] = []
            
            # Determine source (收藏来源)
            source_parts = []
            
            # 检查是否是转发的消息
            if message.forward_origin:
                origin = message.forward_origin
                if hasattr(origin, 'sender_user') and origin.sender_user:
                    # 从用户转发
                    user = origin.sender_user
                    source_parts.append(f"转发自用户: {user.first_name or ''} {user.last_name or ''}".strip())
                    if user.username:
                        source_parts.append(f"@{user.username}")
                elif hasattr(origin, 'chat') and origin.chat:
                    # 从频道/群组转发
                    chat = origin.chat
                    source_parts.append(f"转发自: {chat.title}")
                    if hasattr(chat, 'username') and chat.username:
                        source_parts.append(f"@{chat.username}")
                elif hasattr(origin, 'sender_user_name'):
                    # 隐藏用户名的转发
                    source_parts.append(f"转发自: {origin.sender_user_name}")
                
                # 添加转发日期
                if hasattr(origin, 'date') and origin.date:
                    source_parts.append(f"原始时间: {origin.date.strftime('%Y-%m-%d %H:%M')}")
            else:
                # 直接发送的消息，记录发送者
                if message.from_user:
                    user = message.from_user
                    source_parts.append(f"用户: {user.first_name or ''} {user.last_name or ''}".strip())
                    if user.username:
                        source_parts.append(f"@{user.username}")
                
                # 如果在群组或频道中
                if message.chat and message.chat.type in ['group', 'supergroup', 'channel']:
                    source_parts.append(f"来自: {message.chat.title}")
            
            result['source'] = " | ".join(source_parts) if source_parts else None
            
            # Analyze by message type
            if message.text:
                result.update(ContentAnalyzer._analyze_text(message))
            elif message.photo:
                result.update(ContentAnalyzer._analyze_photo(message))
            elif message.video:
                result.update(ContentAnalyzer._analyze_video(message))
            elif message.document:
                result.update(ContentAnalyzer._analyze_document(message))
            elif message.audio:
                result.update(ContentAnalyzer._analyze_audio(message))
            elif message.voice:
                result.update(ContentAnalyzer._analyze_voice(message))
            elif message.animation:
                result.update(ContentAnalyzer._analyze_animation(message))
            elif message.sticker:
                result.update(ContentAnalyzer._analyze_sticker(message))
            elif message.contact:
                result.update(ContentAnalyzer._analyze_contact(message))
            elif message.location:
                result.update(ContentAnalyzer._analyze_location(message))
            else:
                logger.warning(f"Unknown message type: {message}")
                result['content_type'] = 'unknown'
            
            return result
            
        except Exception as e:
            logger.error(f"Error analyzing message: {e}", exc_info=True)
            return {'content_type': 'error', 'error': str(e)}
    
    @staticmethod
    async def analyze_async(message: Message) -> Dict[str, Any]:
        """
        异步分析消息（支持link类型的深度提取）
        
        Args:
            message: Telegram message object
            
        Returns:
            Dictionary containing analysis results
        """
        try:
            # 先用同步方法做基础分析
            result = ContentAnalyzer.analyze(message)
            
            # 如果是link类型，尝试提取 Telegram 的链接预览
            if result.get('content_type') == 'link':
                url = result.get('url')
                if url:
                    telegram_preview = ContentAnalyzer._extract_telegram_link_preview(message)
                    if telegram_preview:
                        # 使用 Telegram 的预览数据
                        result['title'] = telegram_preview.get('title') or result.get('title')
                        result['telegram_preview'] = telegram_preview
                        
                        if telegram_preview.get('description'):
                            # 添加描述到内容中
                            existing_content = result.get('content', '')
                            result['content'] = f"{existing_content}\n\n📝 {telegram_preview['description']}".strip()
                        
                        logger.info("✓ Using Telegram link preview data")
            
            return result
            
        except Exception as e:
            logger.error(f"Error in async analyze: {e}", exc_info=True)
            # Fallback到同步分析
            return ContentAnalyzer.analyze(message)
    
    @staticmethod
    def _analyze_text(message: Message) -> Dict[str, Any]:
        """Analyze text message (synchronous wrapper)"""
        text = message.text or ''
        
        # 优先检查消息实体中的链接
        detected_url = None
        
        # 1. 检查 entities 中的 URL 实体
        if message.entities:
            for entity in message.entities:
                if entity.type in ['url', 'text_link']:
                    if entity.type == 'url':
                        # 从文本中提取URL
                        detected_url = text[entity.offset:entity.offset + entity.length]
                    elif entity.type == 'text_link':
                        # 使用实体的URL属性
                        detected_url = entity.url
                    break
        
        # 2. 检查是否有链接预览
        if not detected_url and hasattr(message, 'link_preview_options'):
            if message.link_preview_options and hasattr(message.link_preview_options, 'url'):
                detected_url = message.link_preview_options.url
        
        # 3. 使用正则表达式提取URL
        if not detected_url:
            urls = extract_urls(text)
            if urls:
                detected_url = urls[0]
            elif is_url(text.strip()):
                detected_url = text.strip()
        
        # 判断是纯URL还是包含URL的文本
        # 纯URL：去除空格后整个文本就是URL
        text_stripped = text.strip()
        is_pure_url = detected_url and is_url(text_stripped) and text_stripped == detected_url
        
        # 只有纯URL才判定为link类型
        if is_pure_url:
            return {
                'content_type': 'link',
                'title': detected_url,
                'content': text,
                'url': detected_url,
                '_needs_metadata_extraction': True  # 标记需要异步提取
            }
        
        # 包含URL的文本或纯文本消息
        result = {
            'content_type': 'text',
            'title': text[:100] if len(text) > 100 else text,
            'content': text,
            '_needs_ai_title': True  # 标记需要AI生成标题
        }
        
        # 如果包含URL，保存为元数据（但类型仍为text）
        if detected_url and not is_pure_url:
            result['urls'] = [detected_url]  # 提取的URL列表
            result['_has_embedded_url'] = True  # 标记包含URL
        
        return result
    
    @staticmethod
    def _analyze_photo(message: Message) -> Dict[str, Any]:
        """Analyze photo message"""
        # Get largest photo
        photo = message.photo[-1]
        
        return {
            'content_type': 'image',
            'title': message.caption or f"Photo_{message.date.strftime('%Y%m%d_%H%M%S')}",
            'content': message.caption,
            'file_id': photo.file_id,
            'file_size': photo.file_size,
            'file_name': f"photo_{photo.file_id[:10]}.jpg"
        }
    
    @staticmethod
    def _analyze_video(message: Message) -> Dict[str, Any]:
        """Analyze video message"""
        video = message.video
        
        return {
            'content_type': 'video',
            'title': message.caption or video.file_name or f"Video_{message.date.strftime('%Y%m%d_%H%M%S')}",
            'content': message.caption,
            'file_id': video.file_id,
            'file_size': video.file_size,
            'file_name': video.file_name or f"video_{video.file_id[:10]}.mp4",
            'mime_type': video.mime_type
        }
    
    @staticmethod
    def _analyze_document(message: Message) -> Dict[str, Any]:
        """Analyze document message"""
        document = message.document
        
        file_name = document.file_name or f"Document_{message.date.strftime('%Y%m%d_%H%M%S')}"
        file_ext = ''
        if document.file_name and '.' in document.file_name:
            file_ext = '.' + document.file_name.rsplit('.', 1)[1].lower()
        
        # 判断是否为电子书
        content_type = 'document'
        needs_ai_ebook_check = False
        
        # 1. 扩展名直接判断
        if file_ext in EBOOK_EXTENSIONS:
            content_type = 'ebook'
        # 2. 文档类型，可能需要AI判断是否为电子书
        elif file_ext in ['.pdf', '.doc', '.docx']:
            content_type = 'document'
            needs_ai_ebook_check = True
        
        result = {
            'content_type': content_type,
            'title': file_name,
            'content': message.caption,
            'file_id': document.file_id,
            'file_size': document.file_size,
            'file_name': file_name,
            'mime_type': document.mime_type
        }
        
        # 如果需要AI判断，添加标记
        if needs_ai_ebook_check:
            result['_needs_ai_ebook_check'] = True
        
        return result
    
    @staticmethod
    def _analyze_audio(message: Message) -> Dict[str, Any]:
        """Analyze audio message"""
        audio = message.audio
        
        title = audio.title or audio.file_name or f"Audio_{message.date.strftime('%Y%m%d_%H%M%S')}"
        if audio.performer:
            title = f"{audio.performer} - {title}"
        
        return {
            'content_type': 'audio',
            'title': title,
            'content': message.caption,
            'file_id': audio.file_id,
            'file_size': audio.file_size,
            'file_name': audio.file_name or f"audio_{audio.file_id[:10]}.mp3",
            'mime_type': audio.mime_type
        }
    
    @staticmethod
    def _analyze_voice(message: Message) -> Dict[str, Any]:
        """Analyze voice message"""
        voice = message.voice
        
        return {
            'content_type': 'voice',
            'title': f"Voice_{message.date.strftime('%Y%m%d_%H%M%S')}",
            'content': message.caption,
            'file_id': voice.file_id,
            'file_size': voice.file_size,
            'file_name': f"voice_{voice.file_id[:10]}.ogg",
            'mime_type': voice.mime_type
        }
    
    @staticmethod
    def _analyze_animation(message: Message) -> Dict[str, Any]:
        """Analyze animation (GIF) message"""
        animation = message.animation
        
        return {
            'content_type': 'animation',
            'title': animation.file_name or f"Animation_{message.date.strftime('%Y%m%d_%H%M%S')}",
            'content': message.caption,
            'file_id': animation.file_id,
            'file_size': animation.file_size,
            'file_name': animation.file_name or f"animation_{animation.file_id[:10]}.gif",
            'mime_type': animation.mime_type
        }
    
    @staticmethod
    def _analyze_sticker(message: Message) -> Dict[str, Any]:
        """Analyze sticker message"""
        sticker = message.sticker
        
        return {
            'content_type': 'sticker',
            'title': f"Sticker_{sticker.set_name or message.date.strftime('%Y%m%d_%H%M%S')}",
            'content': sticker.emoji,
            'file_id': sticker.file_id,
            'file_size': sticker.file_size,
            'file_name': f"sticker_{sticker.file_id[:10]}.webp"
        }
    
    @staticmethod
    def _analyze_contact(message: Message) -> Dict[str, Any]:
        """Analyze contact message"""
        contact = message.contact
        
        name = f"{contact.first_name} {contact.last_name or ''}".strip()
        
        return {
            'content_type': 'contact',
            'title': name,
            'content': f"Phone: {contact.phone_number}\nUser ID: {contact.user_id or 'N/A'}"
        }
    
    @staticmethod
    def _analyze_location(message: Message) -> Dict[str, Any]:
        """Analyze location message"""
        location = message.location
        
        return {
            'content_type': 'location',
            'title': f"Location_{message.date.strftime('%Y%m%d_%H%M%S')}",
            'content': f"Lat: {location.latitude}, Lon: {location.longitude}"
        }
