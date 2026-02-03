"""
归档相关的消息格式化器
处理归档列表、详情、成功消息等格式化
"""
from __future__ import annotations

import html
import logging
from typing import List, Dict, Any, Optional
from telegram import Bot, Message, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode

from ..helpers import truncate_text, get_content_type_emoji, format_file_size, format_datetime
from ..config import get_config

logger = logging.getLogger(__name__)


async def _get_channel_name_from_path(storage_path: str, bot: Optional[Any] = None) -> Optional[str]:
    """
    从storage_path提取频道ID并查找频道名称
    
    Args:
        storage_path: 格式如 "channel_id:message_id" 或 "channel_id:message_id:file_id"
        bot: Telegram Bot实例（可选）
        
    Returns:
        频道名称或None
    """
    if not storage_path or ':' not in storage_path:
        return None
    
    try:
        # 解析channel_id
        parts = storage_path.split(':')
        channel_id = int(parts[0])
        
        # 尝试从Telegram Bot API获取频道信息
        if bot:
            try:
                chat = await bot.get_chat(channel_id)
                if chat.title:
                    return chat.title
            except Exception as e:
                logger.debug(f"Failed to get chat info from Bot API: {e}")
        
        # 如果Bot API获取失败，从config读取映射
        from ..config import get_config
        config = get_config()
        
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
        
        # 如果没找到，返回None让调用方处理
        return None
        
    except Exception as e:
        logger.debug(f"Error getting channel name: {e}")
        return None


class ArchiveFormatter:
    """归档格式化器 - 处理归档相关的消息格式化"""
    
    @staticmethod
    async def build_success_message(
        archive_data: Dict[str, Any],
        i18n,
        include_ai_info: bool = True,
        bot: Optional[Any] = None
    ) -> str:
        """
        构建归档成功消息
        
        Args:
            archive_data: 归档数据
            i18n: 国际化对象
            include_ai_info: 是否包含AI分析信息
            bot: Telegram Bot实例（用于获取频道名称）
            
        Returns:
            格式化的HTML消息文本
        """
        content_type = archive_data.get('content_type', '')
        emoji = get_content_type_emoji(content_type)
        
        # ========== 顶部：成功状态 ==========
        success_msg = f"<b>{i18n.t('archive_success')}</b>"
        
        # ========== 标题：带存储位置跳转链接 ==========
        # 优先级：AI生成标题 > 内容截断(45字符，第一段) > 原标题 > 文件名 > 类型名
        title_text = None
        ai_title = archive_data.get('ai_title')
        content = archive_data.get('content', '')
        caption = archive_data.get('caption', '')
        original_title = archive_data.get('title', '')
        file_name = archive_data.get('file_name', '')
        
        if ai_title:
            title_text = ai_title
        elif content or caption:
            # 使用内容或caption的第一段落，截断45字符
            # 注意：content可能包含HTML格式的来源信息，需要跳过或使用纯文本部分
            text_source = content or caption
            
            # 如果content包含来源分隔符，提取实际内容部分
            if text_source and '--------------------' in text_source:
                # 跳过来源信息行，提取实际内容
                parts = text_source.split('--------------------', 1)
                if len(parts) > 1:
                    text_source = parts[1].strip()
            
            # 提取第一段（去除HTML标签）
            import re
            # 移除HTML标签
            text_source_plain = re.sub(r'<[^>]+>', '', text_source)
            first_para = text_source_plain.split('\n')[0].strip()
            if len(first_para) > 45:
                title_text = first_para[:45] + '...'
            else:
                title_text = first_para if first_para else text_source_plain[:45]
        elif original_title:
            title_text = original_title
        elif file_name:
            # 使用文件名作为标题
            title_text = file_name
        else:
            # 最后才使用类型名
            content_type_key = f'content_type_{content_type}'
            title_text = i18n.t(content_type_key)
            if title_text == content_type_key:
                title_text = content_type
        
        # 构建存储位置链接（需要转义title_text以防止HTML注入）
        storage_path = archive_data.get('storage_path')
        if storage_path and isinstance(storage_path, str) and ':' in storage_path:
            parts = storage_path.split(':')
            if len(parts) >= 2:
                channel_id_str = parts[0].replace('-100', '')
                message_id = parts[1]
                storage_link = f"https://t.me/c/{channel_id_str}/{message_id}"
                title_display = f'📄 <a href="{storage_link}">{html.escape(title_text)}</a>'
            else:
                title_display = f'{emoji} {html.escape(title_text)}'
        else:
            title_display = f'{emoji} {html.escape(title_text)}'
        
        success_msg += f"\n\n{title_display}"
        
        # ========== 基本信息区（紧凑显示） ==========
        info_parts = []
        
        # 内容类型 + 文件大小（同一行）
        if content_type:
            content_type_key = f'content_type_{content_type}'
            content_type_display = i18n.t(content_type_key)
            if content_type_display == content_type_key:
                content_type_display = content_type
            info_parts.append(f"📋 {content_type_display}")
        
        file_size = archive_data.get('file_size')
        if file_size and file_size > 0:
            info_parts.append(f"💾 {format_file_size(file_size)}")
        
        if info_parts:
            success_msg += f"\n<code>{' · '.join(info_parts)}</code>"
        
        # ========== 标签（换行独立显示） ==========
        tags = archive_data.get('tags', [])
        if tags:
            tags_str = ' '.join(f"#{tag}" for tag in tags[:6])
            if len(tags) > 6:
                tags_str += f" <i>+{len(tags) - 6}</i>"
            success_msg += f"\n🏷 {tags_str}"
        
        # ========== 存储位置（简化显示） ==========
        if storage_path:
            channel_name = await _get_channel_name_from_path(storage_path, bot)
            if channel_name:
                success_msg += f"\n📁 {channel_name}"
        
        # ========== 来源信息（使用HTML链接） ==========
        source = archive_data.get('source')
        if source:
            # 提取来源信息：格式可能是 "转发自: 频道名 | @username | 原始时间: xxx"
            if '转发自:' in source or 'Forwarded from:' in source or '转发自用户:' in source:
                # 提取主要来源部分（第一部分）
                source_parts = source.split('|')
                if len(source_parts) > 0:
                    main_source = source_parts[0].strip()
                    # 去掉前缀
                    for prefix in ['转发自:', 'Forwarded from:', '转发自用户:']:
                        if main_source.startswith(prefix):
                            main_source = main_source[len(prefix):].strip()
                            break
                    
                    # 构建显示文本（纯文本，不使用链接）
                    success_msg += f"\n🔗 来源 {html.escape(main_source)}"
            else:
                # 如果没有特定格式，直接显示（转义用户输入）
                success_msg += f"\n🔗 <i>{html.escape(source)}</i>"
        
        # ========== AI分析信息（分隔显示） ==========
        if include_ai_info:
            ai_summary = archive_data.get('ai_summary')
            ai_category = archive_data.get('ai_category')
            ai_key_points = archive_data.get('ai_key_points', [])
            
            logger.debug(f"AI info check: include={include_ai_info}, summary={bool(ai_summary)}, category={bool(ai_category)}, points={len(ai_key_points)}")
            
            if ai_summary or ai_category or ai_key_points:
                success_msg += f"\n\n{'─' * 25}"
                success_msg += f"\n<b>{i18n.t('ai_analysis')}</b>"
                
                if ai_category:
                    success_msg += f"\n📚 {ai_category}"
                
                if ai_summary:
                    summary_text = truncate_text(ai_summary, 180)
                    success_msg += f"\n\n💭 {summary_text}"
                
                if ai_key_points:
                    success_msg += f"\n\n<b>{i18n.t('ai_key_points')}</b>"
                    for i, point in enumerate(ai_key_points[:3], 1):
                        success_msg += f"\n  • {point}"
        
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
        
        # Group archives by media_group_id
        media_groups = {}  # media_group_id -> list of archives
        standalone_archives = []  # archives without media_group_id
        
        for archive in archives:
            media_group_id = archive.get('media_group_id')
            if media_group_id:
                if media_group_id not in media_groups:
                    media_groups[media_group_id] = []
                media_groups[media_group_id].append(archive)
            else:
                standalone_archives.append(archive)
        
        # Build flattened list: use first archive from each media group
        display_archives = []
        for media_group_id, group_archives in media_groups.items():
            # Sort by archive_id to get the first message in the group
            group_archives.sort(key=lambda x: x.get('id', 0))
            first_archive = group_archives[0]
            # Mark as media group and store count
            first_archive['_is_media_group'] = True
            first_archive['_media_group_count'] = len(group_archives)
            display_archives.append(first_archive)
        
        # Add standalone archives
        display_archives.extend(standalone_archives)
        
        # Sort by original order (archived_at)
        display_archives.sort(key=lambda x: x.get('archived_at', ''), reverse=True)
        
        formatted_results = []
        
        for idx, archive in enumerate(display_archives, 1):
            archive_id = archive.get('id')
            emoji = get_content_type_emoji(archive.get('content_type', ''))
            
            # Check if this is a media group representative
            is_media_group = archive.get('_is_media_group', False)
            media_group_count = archive.get('_media_group_count', 0)
            
            # Get title (priority: ai_title > title > content preview)
            title = archive.get('ai_title') or archive.get('title')
            if not title:
                content = archive.get('content', '')
                if content:
                    title = truncate_text(content, 50)
                else:
                    title = 'Untitled'
            
            # For media groups, append count indicator
            if is_media_group and media_group_count > 1:
                title = f"{title} ({media_group_count} items)"
            
            title_truncated = truncate_text(title, 50)
            
            storage_path = archive.get('storage_path')
            storage_type = archive.get('storage_type')
            
            # Build Telegram link if available
            if with_links and storage_path and storage_type == 'telegram':
                try:
                    # Parse storage_path format: "channel_id:message_id" or "channel_id:message_id:file_id"
                    parts = storage_path.split(':')
                    if len(parts) >= 2:
                        channel_id = parts[0]
                        message_id = parts[1]
                        
                        # Convert channel_id to short format for t.me/c/ links
                        # Remove -100 prefix if present
                        if channel_id.startswith('-100'):
                            channel_id_short = channel_id[4:]  # Remove '-100'
                        else:
                            channel_id_short = channel_id.lstrip('-')
                        
                        link = f"https://t.me/c/{channel_id_short}/{message_id}"
                        # HTML转义标题文本
                        import html
                        title_escaped = html.escape(title_truncated)
                        title_truncated = f"<a href='{link}'>{title_escaped}</a>"
                except Exception as e:
                    logger.debug(f"Failed to build link for archive {archive_id}: {e}")
            
            # Get tags
            tags = archive.get('tags', [])
            tags_str = ' '.join(f"#{tag}" for tag in tags) if tags else ''
            
            archived_at = archive.get('archived_at', '')
            
            is_favorite = db_instance.is_favorite(archive_id) if db_instance else False
            has_notes = db_instance.has_notes(archive_id) if db_instance else False
            
            fav_icon = "❤️ 已精选" if is_favorite else "🤍 未精选"
            note_icon = "📝 √ 有笔记" if has_notes else "📝 无笔记"
            
            # Build result text - 优化格式
            result_text = f"{idx}. {emoji} {title_truncated}"
            
            # 显示标签（如果有）
            if tags_str:
                result_text += f"\n   {tags_str}"
            
            # 元信息行
            result_text += f"\n   {fav_icon} | {note_icon} | 📅 {archived_at}"
            
            formatted_results.append(result_text)
        
        # 使用空行分隔每个条目，视觉更清晰
        results_text = '\n\n'.join(formatted_results)
        
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
        max_length: int = 1000
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
        content_type = archive.get('content_type', '')
        
        caption_parts = []
        
        # AI生成的内容
        ai_summary = archive.get('ai_summary')
        ai_key_points = archive.get('ai_key_points')
        ai_category = archive.get('ai_category')
        
        # 添加AI摘要
        if ai_summary and ai_summary.strip():
            caption_parts.append(f"📝 {ai_summary}")
        
        # 添加AI关键点
        if ai_key_points:
            try:
                import json
                if isinstance(ai_key_points, str):
                    key_points = json.loads(ai_key_points)
                else:
                    key_points = ai_key_points
                
                if key_points and isinstance(key_points, list):
                    points_text = "\n".join([f"• {point}" for point in key_points[:5]])  # 最多5个关键点
                    caption_parts.append(f"🔑 关键点:\n{points_text}")
            except:
                pass
        
        # 添加AI分类
        if ai_category and ai_category.strip():
            caption_parts.append(f"🏷 分类: {ai_category}")
        
        # 添加笔记
        if notes and len(notes) > 0:
            notes_content = "\n---\n".join([note.get('content', '') for note in notes if note.get('content', '').strip()])
            if notes_content:
                caption_parts.append(f"💬 笔记:\n{notes_content}")
        
        # 组合所有部分
        caption = "\n\n".join(caption_parts)
        
        # 如果超长，截断
        if len(caption) > max_length:
            caption = truncate_text(caption, max_length - 20)
            caption += "\n\n... [查看完整信息]"
        
        return caption if caption else ""
    
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
                text = f"{emoji} <a href='{link}'>{html.escape(title)}</a>\n"
            else:
                text = f"{emoji} {html.escape(title)}\n"
        else:
            text = f"{emoji} {html.escape(title)}\n"
        
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
        caption: Optional[str] = None,
        reply_markup: Optional[Any] = None
    ) -> Optional[Message]:
        """
        发送归档资源文件
        
        Args:
            bot: Telegram Bot实例
            chat_id: 接收者chat_id
            archive: 归档记录
            caption: 可选的说明文字
            reply_markup: 可选的按钮
            
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
                return await bot.send_photo(chat_id=chat_id, photo=file_id, caption=caption, reply_markup=reply_markup)
            elif content_type == 'video':
                return await bot.send_video(chat_id=chat_id, video=file_id, caption=caption, reply_markup=reply_markup)
            elif content_type == 'audio':
                return await bot.send_audio(chat_id=chat_id, audio=file_id, caption=caption, reply_markup=reply_markup)
            elif content_type == 'voice':
                return await bot.send_voice(chat_id=chat_id, voice=file_id, caption=caption, reply_markup=reply_markup)
            elif content_type == 'animation':  # GIF
                return await bot.send_animation(chat_id=chat_id, animation=file_id, caption=caption, reply_markup=reply_markup)
            elif content_type == 'sticker':
                return await bot.send_sticker(chat_id=chat_id, sticker=file_id, reply_markup=reply_markup)
            elif content_type in ['document', 'ebook']:
                return await bot.send_document(chat_id=chat_id, document=file_id, caption=caption, reply_markup=reply_markup)
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
