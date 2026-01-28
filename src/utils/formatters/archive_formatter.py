"""
归档相关的消息格式化器
处理归档列表、详情、成功消息等格式化
"""
from __future__ import annotations

import logging
from typing import List, Dict, Any, Optional
from telegram import Bot, Message, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode

from ..helpers import truncate_text, get_content_type_emoji, format_file_size, format_datetime
from ..config import get_config

logger = logging.getLogger(__name__)


def _get_channel_name_from_path(storage_path: str) -> Optional[str]:
    """
    从storage_path提取频道ID并查找频道名称
    
    Args:
        storage_path: 格式如 "channel_id:message_id" 或 "channel_id:message_id:file_id"
        
    Returns:
        频道名称或None
    """
    if not storage_path or ':' not in storage_path:
        return None
    
    try:
        from ..config import get_config
        config = get_config()
        
        # 解析channel_id
        parts = storage_path.split(':')
        channel_id = int(parts[0])
        
        # 定义频道ID到名称的映射（从config读取）
        # 优先级：type_mapping > channels配置
        channels_config = config.get('storage.telegram.channels', {})
        type_mapping = config.get('storage.telegram.type_mapping', {})
        source_mapping = config.get('storage.telegram.source_mapping', [])
        tag_mapping = config.get('storage.telegram.tag_mapping', [])
        direct_send_config = config.get('storage.telegram.direct_send', {})
        
        # 创建ID到名称的映射表
        channel_names = {
            channels_config.get('default'): '默认频道',
            channels_config.get('text'): '文本频道',
            channels_config.get('image'): '图片频道',
            channels_config.get('video'): '视频频道',  
            channels_config.get('document'): '文档频道',
            channels_config.get('ebook'): '电子书频道',
            channels_config.get('media'): '媒体频道',
            channels_config.get('note'): '笔记频道',
        }
        
        # 从direct_send配置添加
        if direct_send_config and direct_send_config.get('channels'):
            ds_channels = direct_send_config['channels']
            channel_names[ds_channels.get('default')] = '私人频道'
        
        # 从source_mapping添加
        for mapping in source_mapping or []:
            ch_id = mapping.get('channel_id')
            if ch_id:
                # 使用第一个来源作为名称提示
                sources = mapping.get('sources', [])
                if sources:
                    channel_names[ch_id] = f'转发频道'
        
        # 查找匹配的频道名
        channel_name = channel_names.get(channel_id)
        if channel_name:
            return channel_name
        
        # 如果没找到，返回ID
        return f"频道 {channel_id}"
        
    except Exception as e:
        logger.debug(f"Error getting channel name: {e}")
        return None


class ArchiveFormatter:
    """归档格式化器 - 处理归档相关的消息格式化"""
    
    @staticmethod
    def build_success_message(
        archive_data: Dict[str, Any],
        i18n,
        include_ai_info: bool = True
    ) -> str:
        """
        构建归档成功消息
        
        Args:
            archive_data: 归档数据
            i18n: 国际化对象
            include_ai_info: 是否包含AI分析信息
            
        Returns:
            格式化的HTML消息文本
        """
        content_type = archive_data.get('content_type', '')
        emoji = get_content_type_emoji(content_type)
        
        success_msg = f"{emoji} {i18n.t('archive_success')}"
        
        # ========== 标题：带存储位置跳转链接 ==========
        # 优先级：AI生成标题 > 内容截断(32字符，第一段) > 原标题 > 类型名
        title_text = None
        ai_title = archive_data.get('ai_title')  # 优先使用AI标题
        content = archive_data.get('content', '')
        caption = archive_data.get('caption', '')
        original_title = archive_data.get('title', '')
        
        # 判断是否有任何可用内容
        has_content = bool(ai_title or content or caption)
        
        if ai_title:
            title_text = ai_title
        elif content or caption:
            # 使用内容或caption的第一段落，截断32字符
            text_source = content or caption
            # 提取第一自然段（以换行符分割）
            first_para = text_source.split('\n')[0].strip()
            if len(first_para) > 32:
                title_text = first_para[:32] + '...'
            else:
                title_text = first_para if first_para else text_source[:32]
        elif original_title:
            # 如果没有AI/content/caption，使用原标题
            title_text = original_title
        else:
            # 最后才使用类型名
            content_type_key = f'content_type_{content_type}'
            title_text = i18n.t(content_type_key)
            if title_text == content_type_key:
                title_text = content_type
        
        # 构建存储位置链接
        storage_path = archive_data.get('storage_path')
        if storage_path and isinstance(storage_path, str) and ':' in storage_path:
            # 解析 storage_path: "channel_id:message_id" 或 "channel_id:message_id:file_id"
            parts = storage_path.split(':')
            if len(parts) >= 2:
                channel_id_str = parts[0].replace('-100', '')
                message_id = parts[1]
                storage_link = f"https://t.me/c/{channel_id_str}/{message_id}"
                title_display = f'<a href="{storage_link}">{title_text}</a>'
            else:
                title_display = title_text
        else:
            title_display = title_text
        
        success_msg += f"\n\n<b>{i18n.t('title')}</b>: {title_display}"
        
        # ========== 内容类型 ==========
        if content_type:
            content_type_key = f'content_type_{content_type}'
            content_type_display = i18n.t(content_type_key)
            if content_type_display == content_type_key:
                content_type_display = content_type
            success_msg += f"\n<b>{i18n.t('content_type')}</b>: {content_type_display}"
        
        # ========== 文件大小 ==========
        file_size = archive_data.get('file_size')
        if file_size and file_size > 0:
            success_msg += f"\n<b>{i18n.t('file_size')}</b>: {format_file_size(file_size)}"
        
        # ========== 标签 ==========
        tags = archive_data.get('tags', [])
        if tags:
            tags_str = ' '.join(f"#{tag}" for tag in tags[:5])
            if len(tags) > 5:
                tags_str += f" +{len(tags) - 5}"
            success_msg += f"\n<b>{i18n.t('tags')}</b>: {tags_str}"
        
        # ========== 存储：显示频道名称 ==========
        storage_path = archive_data.get('storage_path')
        if storage_path:
            # 获取频道名称（从config中查找）
            channel_name = _get_channel_name_from_path(storage_path)
            if channel_name:
                success_msg += f"\n<b>{i18n.t('storage')}</b>: {channel_name}"
        
        # ========== 来源 ==========
        source = archive_data.get('source')
        if source:
            success_msg += f"\n<b>{i18n.t('source')}</b>: {source}"
        
        # ========== AI分析信息 ==========
        if include_ai_info:
            ai_summary = archive_data.get('ai_summary')
            ai_category = archive_data.get('ai_category')
            ai_key_points = archive_data.get('ai_key_points', [])
            
            logger.debug(f"AI info check: include={include_ai_info}, summary={bool(ai_summary)}, category={bool(ai_category)}, points={len(ai_key_points)}")
            
            if ai_summary or ai_category:
                success_msg += f"\n\n{i18n.t('ai_analysis')}"
                
                if ai_category:
                    success_msg += f"\n{i18n.t('ai_category')}：{ai_category}"
                
                if ai_summary:
                    summary_text = truncate_text(ai_summary, 200)
                    success_msg += f"\n{i18n.t('ai_summary')} {summary_text}"
                
                if ai_key_points:
                    success_msg += f"\n{i18n.t('ai_key_points')}："
                    for i, point in enumerate(ai_key_points[:3], 1):
                        success_msg += f"\n  {i}. {point}"
        
        return success_msg
    
    @staticmethod
    def format_list(
        archives: List[Dict[str, Any]],
        i18n,
        db_instance=None,
        with_links: bool = True
    ) -> str:
        """
        格式化归档列表
        
        Args:
            archives: 归档列表
            i18n: 国际化对象
            db_instance: 数据库实例
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
            
            storage_path = archive.get('storage_path')
            storage_type = archive.get('storage_type')
            
            if with_links and storage_path and storage_type == 'telegram':
                parts = storage_path.split(':')
                if len(parts) >= 2:
                    channel_id = parts[0].replace('-100', '')
                    message_id = parts[1]
                else:
                    config = get_config()
                    channel_id = str(config.telegram_channel_id).replace('-100', '')
                    message_id = storage_path
                
                link = f"https://t.me/c/{channel_id}/{message_id}"
                title_truncated = f"<a href='{link}'>{title_truncated}</a>"
            
            tags = archive.get('tags', [])
            tags_str = ' '.join(f"#{tag}" for tag in tags) if tags else ''
            
            archived_at = archive.get('archived_at', '')
            
            is_favorite = db_instance.is_favorite(archive_id) if db_instance else False
            has_notes = db_instance.has_notes(archive_id) if db_instance else False
            
            fav_icon = "❤️ 已精选" if is_favorite else "🤍 未精选"
            note_icon = "📝 √ 有笔记" if has_notes else "📝 无笔记"
            
            result_text = f"{idx}. {emoji} {title_truncated}"
            if tags_str:
                result_text += f"\n   {tags_str}"
            result_text += f"\n   {fav_icon} | {note_icon} | 📅 {archived_at}"
            
            formatted_results.append(result_text)
        
        results_text = '\n---------------------\n'.join(formatted_results)
        
        return results_text
    
    @staticmethod
    def format_text_detail(
        archive: Dict[str, Any],
        notes: Optional[List[Dict[str, Any]]] = None,
        db_instance=None
    ) -> tuple[str, Optional[Any]]:
        """
        格式化文本归档详情
        
        Args:
            archive: 存档数据
            notes: 关联的笔记列表
            db_instance: 数据库实例
            
        Returns:
            (格式化的消息文本, InlineKeyboardMarkup按钮或None)
        """
        archive_id = archive.get('id')
        title = archive.get('title', '')
        content = archive.get('content', '')
        storage_path = archive.get('storage_path', '')
        created_at = archive.get('archived_at', archive.get('created_at', ''))
        
        archive_link = ''
        if storage_path:
            parts = storage_path.split(':')
            if len(parts) >= 2:
                channel_id_str = parts[0].replace('-100', '')
                message_id = parts[1]
                link = f"https://t.me/c/{channel_id_str}/{message_id}"
                archive_link = f"<a href='{link}'>#{archive_id}</a>"
            else:
                archive_link = f"#{archive_id}"
        else:
            archive_link = f"#{archive_id}"
        
        has_notes = False
        if notes:
            has_notes = len(notes) > 0
        elif db_instance:
            has_notes = db_instance.has_notes(archive_id)
        
        if title:
            text = f"📝 [文本 {archive_link}] {title}\n"
        else:
            text = f"📝 [文本 {archive_link}]\n"
        
        text += "----------------------------------\n"
        text += f"{truncate_text(content, 500)}\n"
        text += "----------------------------------\n"
        text += f"📅 {created_at}\n"
        
        if has_notes and notes:
            text += "\n💬 关联笔记：\n"
            for note in notes[:2]:
                note_preview = truncate_text(note.get('content', ''), 100)
                text += f"  • {note_preview}\n"
            if len(notes) > 2:
                text += f"  ...还有 {len(notes) - 2} 条笔记\n"
        
        keyboard = []
        if has_notes:
            keyboard.append([
                InlineKeyboardButton("✏️ 编辑", callback_data=f"edit_text:{archive_id}"),
                InlineKeyboardButton("📝 查看笔记", callback_data=f"note:{archive_id}")
            ])
            keyboard.append([
                InlineKeyboardButton("➕ 追加笔记", callback_data=f"note_add:{archive_id}"),
                InlineKeyboardButton("🗑️ 删除", callback_data=f"delete:{archive_id}")
            ])
        else:
            keyboard.append([
                InlineKeyboardButton("✏️ 编辑", callback_data=f"edit_text:{archive_id}"),
                InlineKeyboardButton("📝 添加笔记", callback_data=f"note_add:{archive_id}")
            ])
            keyboard.append([
                InlineKeyboardButton("🗑️ 删除", callback_data=f"delete:{archive_id}")
            ])
        
        reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
        
        return text, reply_markup
    
    @staticmethod
    def format_media_caption(
        archive: Dict[str, Any],
        notes: Optional[List[Dict[str, Any]]] = None,
        max_length: int = 200
    ) -> str:
        """
        格式化媒体归档的caption
        
        Args:
            archive: 存档数据
            notes: 关联的笔记列表
            max_length: caption最大长度
            
        Returns:
            格式化的caption文本
        """
        archive_id = archive.get('id')
        title = archive.get('title', '')
        
        caption = f"📚 {title}\n" if title else f"📚 存档 #{archive_id}\n"
        
        if notes and len(notes) > 0:
            all_notes_content = "\n---\n".join([note.get('content', '') for note in notes])
            
            if len(all_notes_content) > max_length:
                caption += truncate_text(all_notes_content, max_length - len(caption) - 10)
                caption += "\n\n💬 [查看完整笔记]"
            else:
                caption += all_notes_content
        
        return caption
    
    @staticmethod
    def build_media_buttons(
        archive: Dict[str, Any],
        has_notes: bool = False
    ) -> Optional[Any]:
        """
        构建媒体归档的操作按钮
        
        Args:
            archive: 存档数据
            has_notes: 是否有关联笔记
            
        Returns:
            InlineKeyboardMarkup按钮或None
        """
        archive_id = archive.get('id')
        storage_path = archive.get('storage_path', '')
        
        keyboard = []
        
        row1 = []
        if storage_path:
            parts = storage_path.split(':')
            if len(parts) >= 2:
                row1.append(InlineKeyboardButton("🔗 查看", callback_data=f"view_channel:{archive_id}"))
        
        if has_notes:
            row1.append(InlineKeyboardButton("📝 笔记", callback_data=f"note:{archive_id}"))
        else:
            row1.append(InlineKeyboardButton("📝 添加笔记", callback_data=f"note_add:{archive_id}"))
        
        if row1:
            keyboard.append(row1)
        
        keyboard.append([
            InlineKeyboardButton("🗑️ 删除", callback_data=f"delete:{archive_id}")
        ])
        
        return InlineKeyboardMarkup(keyboard) if keyboard else None
    
    @staticmethod
    def format_other_detail(
        archive: Dict[str, Any],
        has_notes: bool = False
    ) -> tuple[str, Optional[Any]]:
        """
        格式化其他类型归档详情
        
        Args:
            archive: 存档数据
            has_notes: 是否有关联笔记
            
        Returns:
            (格式化的消息文本, InlineKeyboardMarkup按钮或None)
        """
        archive_id = archive.get('id')
        title = archive.get('title', f"存档 #{archive_id}")
        storage_path = archive.get('storage_path', '')
        content_type = archive.get('content_type', '')
        emoji = get_content_type_emoji(content_type)
        
        if storage_path:
            parts = storage_path.split(':')
            if len(parts) >= 2:
                channel_id_str = parts[0].replace('-100', '')
                message_id = parts[1]
                link = f"https://t.me/c/{channel_id_str}/{message_id}"
                text = f"{emoji} <a href='{link}'>{title}</a>\n"
            else:
                text = f"{emoji} {title}\n"
        else:
            text = f"{emoji} {title}\n"
        
        text += "----------------------------------"
        
        keyboard = []
        if has_notes:
            keyboard.append([
                InlineKeyboardButton("📝 查看笔记", callback_data=f"note:{archive_id}"),
                InlineKeyboardButton("🗑️ 删除", callback_data=f"delete:{archive_id}")
            ])
        else:
            keyboard.append([
                InlineKeyboardButton("📝 添加笔记", callback_data=f"note_add:{archive_id}"),
                InlineKeyboardButton("🗑️ 删除", callback_data=f"delete:{archive_id}")
            ])
        
        reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
        
        return text, reply_markup
    
    @staticmethod
    async def send_resource(
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
            archive: 归档记录
            caption: 可选的说明文字
            
        Returns:
            发送的消息对象，失败返回None
        """
        try:
            storage_path = archive.get('storage_path')
            storage_type = archive.get('storage_type')
            content_type = archive.get('content_type')
            title = archive.get('title', '')
            
            if storage_type != 'telegram' or not storage_path:
                logger.warning(f"Cannot send resource: storage_type={storage_type}, storage_path={storage_path}")
                return None
            
            parts = storage_path.split(':')
            file_id = None
            
            if len(parts) >= 3:
                file_id = parts[2]
            elif len(parts) == 2:
                if parts[0].startswith('-'):
                    file_id = archive.get('file_id')
                else:
                    file_id = parts[1]
            else:
                file_id = archive.get('file_id')
            
            if not file_id:
                logger.warning(f"No file_id found for archive {archive.get('id')}")
                return None
            
            if not caption:
                caption = f"📚 {title}" if title else None
            
            # 根据准确的 content_type 发送对应类型的消息
            # content_type 来自 analyzer.py，确保类型匹配
            if content_type == 'image':  # photo 在 analyzer 中被标记为 'image'
                return await bot.send_photo(chat_id=chat_id, photo=file_id, caption=caption)
            elif content_type == 'video':
                return await bot.send_video(chat_id=chat_id, video=file_id, caption=caption)
            elif content_type == 'audio':
                return await bot.send_audio(chat_id=chat_id, audio=file_id, caption=caption)
            elif content_type == 'voice':
                return await bot.send_voice(chat_id=chat_id, voice=file_id, caption=caption)
            elif content_type == 'animation':  # GIF
                return await bot.send_animation(chat_id=chat_id, animation=file_id, caption=caption)
            elif content_type == 'sticker':
                return await bot.send_sticker(chat_id=chat_id, sticker=file_id)
            elif content_type in ['document', 'ebook']:
                return await bot.send_document(chat_id=chat_id, document=file_id, caption=caption)
            else:
                # 对于 text, link, contact, location, unknown 等类型不应该调用此方法
                # 如果到这里说明数据有问题，记录警告
                logger.warning(f"Unexpected content_type '{content_type}' in send_resource, cannot send")
                return None
        
        except Exception as e:
            logger.error(f"Failed to send archive resource: {e}", exc_info=True)
            return None
    
    @staticmethod
    async def send_resources_batch(
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
            max_count: 最大发送数量
            
        Returns:
            成功发送的数量
        """
        sent_count = 0
        
        for archive in archives[:max_count]:
            result = await ArchiveFormatter.send_resource(bot, chat_id, archive)
            if result:
                sent_count += 1
        
        return sent_count
