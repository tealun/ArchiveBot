"""
消息构建框架
提供统一的消息格式化和资源发送功能
"""

import logging
from typing import List, Dict, Any, Optional
from telegram import Bot, Message
from telegram.constants import ParseMode

from ..utils.helpers import truncate_text, get_content_type_emoji
from ..utils.config import get_config

logger = logging.getLogger(__name__)


class MessageBuilder:
    """消息构建器 - 统一处理列表消息和资源发送"""
    
    @staticmethod
    def build_archive_success_message(
        archive_data: Dict[str, Any],
        i18n,
        include_ai_info: bool = True
    ) -> str:
        """
        构建归档成功消息（统一格式）
        
        Args:
            archive_data: 归档数据，包含：
                - title: 标题
                - content_type: 内容类型
                - file_size: 文件大小（可选）
                - tags: 标签列表
                - storage_type: 存储类型
                - storage_provider: 存储提供者
                - storage_path: 存储路径
                - source: 来源信息
                - ai_summary: AI摘要（可选）
                - ai_category: AI分类（可选）
            i18n: 国际化对象
            include_ai_info: 是否包含AI分析信息
            
        Returns:
            格式化的HTML消息文本
        """
        from ..utils.helpers import format_file_size, format_datetime
        
        content_type = archive_data.get('content_type', '')
        storage_type = archive_data.get('storage_type', '')
        storage_provider = archive_data.get('storage_provider', '')
        storage_path = archive_data.get('storage_path', '')
        
        # 获取频道信息和链接
        storage_display = i18n.t(f'storage_{storage_type}')
        
        if storage_provider == 'telegram_channel' and storage_path:
            parts = storage_path.split(':')
            if len(parts) >= 2:
                channel_id_from_path = int(parts[0])
                message_id = parts[1]
                
                # 获取频道名称
                from ..utils.config import get_config
                config = get_config()
                all_channels = config.get('storage.telegram.channels', {})
                
                # 查找频道名称
                channel_name = None
                for name, ch_id in all_channels.items():
                    if ch_id == channel_id_from_path:
                        channel_name_map = {
                            'default': 'Archive Default',
                            'text': 'Archive Text',
                            'ebook': 'Archive Ebook',
                            'document': 'Archive File',
                            'image': 'Archive Image',
                            'media': 'Archive Media'
                        }
                        channel_name = channel_name_map.get(name, f'Archive {name.title()}')
                        break
                
                if channel_name:
                    channel_id_str = str(channel_id_from_path).replace('-100', '')
                    channel_url = f"https://t.me/c/{channel_id_str}/{message_id}"
                    storage_display = f"<a href='{channel_url}'>{channel_name}</a> 频道"
        
        # 构建标题
        title = archive_data.get('title', '')
        if not title and archive_data.get('content'):
            # 如果没有标题，截取内容前32字符作为标题
            title = archive_data['content'][:32] + ('...' if len(archive_data['content']) > 32 else '')
        
        title_link = ''
        if title and storage_path and storage_provider == 'telegram_channel':
            parts = storage_path.split(':')
            if len(parts) >= 2:
                channel_id_str = parts[0].replace('-100', '')
                message_id = parts[1]
                file_link = f"https://t.me/c/{channel_id_str}/{message_id}"
                title_link = f"📚 标题: <a href='{file_link}'>{title}</a>\n"
        elif title:
            title_link = f"📚 标题: {title}\n"
        
        # 构建标签显示
        tags = archive_data.get('tags', [])
        tags_display = ' '.join([f'#{tag}' for tag in tags]) if tags else i18n.t('tag_text')
        
        # 构建消息
        source_display = archive_data.get('source', '直接发送')
        file_size = archive_data.get('file_size', 0)
        
        if content_type not in ['text', 'link'] and file_size > 0:
            success_msg = i18n.t(
                'archive_success_with_size',
                title_link=title_link,
                content_type=i18n.t(f'tag_{content_type}'),
                file_size=format_file_size(file_size),
                tags=tags_display,
                storage_type=storage_display,
                source=source_display,
                time=format_datetime()
            )
        else:
            success_msg = i18n.t(
                'archive_success',
                title_link=title_link,
                content_type=i18n.t(f'tag_{content_type}'),
                tags=tags_display,
                storage_type=storage_display,
                source=source_display,
                time=format_datetime()
            )
        
        # 添加AI分析信息（如果有）
        if include_ai_info:
            ai_summary = archive_data.get('ai_summary', '')
            ai_category = archive_data.get('ai_category', '')
            ai_key_points = archive_data.get('ai_key_points', [])
            
            if ai_summary or ai_category or ai_key_points:
                success_msg += "\n\n🤖 AI智能分析："
                
                if ai_category:
                    success_msg += f"\n📁 分类：{ai_category}"
                
                if ai_summary:
                    success_msg += f"\n📝 摘要：{ai_summary}"
                
                if ai_key_points:
                    success_msg += "\n🔑 关键点："
                    for i, point in enumerate(ai_key_points[:3], 1):
                        success_msg += f"\n  {i}. {point}"
        
        return success_msg
    
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
    
    @staticmethod
    def format_note_detail_reply(
        note: Dict[str, Any],
        archive: Optional[Dict[str, Any]] = None
    ) -> tuple[str, Optional[Any]]:
        """
        构建单条笔记的详情展示格式
        
        Args:
            note: 笔记数据，包含：
                - id: 笔记ID
                - content: 笔记内容
                - title: 笔记标题（可选）
                - created_at: 创建时间
                - archive_id: 关联的存档ID（可选）
            archive: 关联的存档数据（可选）
            
        Returns:
            (格式化的消息文本, InlineKeyboardMarkup按钮或None)
        """
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        
        note_id = note.get('id')
        note_title = note.get('title', '')
        note_content = note.get('content', '')
        created_at = note.get('created_at', '')
        archive_id = note.get('archive_id')
        
        # 构建笔记链接（如果有storage_path）
        storage_path = note.get('storage_path', '')
        note_link = ''
        
        if storage_path:
            parts = storage_path.split(':')
            if len(parts) >= 2:
                channel_id_str = parts[0].replace('-100', '')
                message_id = parts[1]
                link = f"https://t.me/c/{channel_id_str}/{message_id}"
                note_link = f"<a href='{link}'>#{note_id}</a>"
            else:
                note_link = f"#{note_id}"
        else:
            note_link = f"#{note_id}"
        
        # 构建消息文本
        if note_title:
            # 有标题的笔记
            text = f"📝 [笔记 {note_link}] {note_title}\n"
            text += "----------------------------------\n"
            text += f"{note_content}\n"
            text += "----------------------------------\n"
            text += f"📅 {created_at}"
        else:
            # 没有标题的笔记
            text = f"📝 [笔记 {note_link}]\n"
            text += "----------------------------------\n"
            text += f"{note_content}\n"
            text += "----------------------------------\n"
            text += f"📅 {created_at}"
        
        # 构建按钮
        keyboard = []
        if archive_id:
            # 关联了存档的笔记
            keyboard.append([
                InlineKeyboardButton("✏️ 编辑", callback_data=f"note_edit:{archive_id}:{note_id}"),
                InlineKeyboardButton("➕ 追加", callback_data=f"note_append:{archive_id}:{note_id}")
            ])
            keyboard.append([
                InlineKeyboardButton("📤 分享", callback_data=f"note_share:{archive_id}:{note_id}"),
                InlineKeyboardButton("🗑️ 删除", callback_data=f"note_delete:{note_id}")
            ])
        else:
            # 独立笔记
            keyboard.append([
                InlineKeyboardButton("✏️ 编辑", callback_data=f"note_quick_edit:{note_id}"),
                InlineKeyboardButton("➕ 追加", callback_data=f"note_quick_append:{note_id}")
            ])
            keyboard.append([
                InlineKeyboardButton("🗑️ 删除", callback_data=f"note_quick_delete:{note_id}")
            ])
        
        reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
        
        return text, reply_markup
    
    @staticmethod
    def format_text_archive_reply(
        archive: Dict[str, Any],
        notes: Optional[List[Dict[str, Any]]] = None,
        db_instance=None
    ) -> tuple[str, Optional[Any]]:
        """
        构建单条文本存档的详情展示格式
        区分带笔记和不带笔记两种情况
        
        Args:
            archive: 存档数据，包含：
                - id: 存档ID
                - title: 标题
                - content: 文本内容
                - storage_path: 存储路径
                - created_at: 创建时间
            notes: 关联的笔记列表（可选）
            db_instance: 数据库实例（用于检查笔记状态）
            
        Returns:
            (格式化的消息文本, InlineKeyboardMarkup按钮或None)
        """
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        
        archive_id = archive.get('id')
        title = archive.get('title', '')
        content = archive.get('content', '')
        storage_path = archive.get('storage_path', '')
        created_at = archive.get('archived_at', archive.get('created_at', ''))
        
        # 构建存档链接
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
        
        # 检查是否有笔记
        has_notes = False
        if notes:
            has_notes = len(notes) > 0
        elif db_instance:
            has_notes = db_instance.has_notes(archive_id)
        
        # 构建消息文本
        if title:
            # 有标题的文本存档
            text = f"📝 [文本 {archive_link}] {title}\n"
        else:
            # 没有标题的文本存档
            text = f"📝 [文本 {archive_link}]\n"
        
        text += "----------------------------------\n"
        text += f"{truncate_text(content, 500)}\n"
        text += "----------------------------------\n"
        text += f"📅 {created_at}\n"
        
        # 如果有笔记，显示笔记摘要
        if has_notes and notes:
            text += "\n💬 关联笔记：\n"
            for note in notes[:2]:  # 最多显示2条
                note_preview = truncate_text(note.get('content', ''), 100)
                text += f"  • {note_preview}\n"
            if len(notes) > 2:
                text += f"  ...还有 {len(notes) - 2} 条笔记\n"
        
        # 构建按钮
        keyboard = []
        if has_notes:
            # 有笔记的情况
            keyboard.append([
                InlineKeyboardButton("✏️ 编辑", callback_data=f"edit_text:{archive_id}"),
                InlineKeyboardButton("📝 查看笔记", callback_data=f"note:{archive_id}")
            ])
            keyboard.append([
                InlineKeyboardButton("➕ 追加笔记", callback_data=f"note_add:{archive_id}"),
                InlineKeyboardButton("🗑️ 删除", callback_data=f"delete:{archive_id}")
            ])
        else:
            # 没有笔记的情况
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
    def format_media_archive_caption(
        archive: Dict[str, Any],
        notes: Optional[List[Dict[str, Any]]] = None,
        max_length: int = 200
    ) -> str:
        """
        构建媒体存档的caption（笔记内容）
        
        Args:
            archive: 存档数据
            notes: 关联的笔记列表
            max_length: caption最大长度（字符数）
            
        Returns:
            格式化的caption文本
        """
        archive_id = archive.get('id')
        title = archive.get('title', '')
        
        caption = f"📚 {title}\n" if title else f"📚 存档 #{archive_id}\n"
        
        if notes and len(notes) > 0:
            # 合并所有笔记内容
            all_notes_content = "\n---\n".join([note.get('content', '') for note in notes])
            
            # 截断到max_length
            if len(all_notes_content) > max_length:
                caption += truncate_text(all_notes_content, max_length - len(caption) - 10)
                caption += "\n\n💬 [查看完整笔记]"
            else:
                caption += all_notes_content
        
        return caption
    
    @staticmethod
    def build_media_archive_buttons(
        archive: Dict[str, Any],
        has_notes: bool = False
    ) -> Optional[Any]:
        """
        构建媒体存档的操作按钮
        
        Args:
            archive: 存档数据
            has_notes: 是否有关联笔记
            
        Returns:
            InlineKeyboardMarkup按钮或None
        """
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        
        archive_id = archive.get('id')
        storage_path = archive.get('storage_path', '')
        
        keyboard = []
        
        # 第一行：查看频道消息 | 笔记按钮
        row1 = []
        if storage_path:
            parts = storage_path.split(':')
            if len(parts) >= 2:
                channel_id_str = parts[0].replace('-100', '')
                message_id = parts[1]
                # 使用callback来跳转，因为InlineKeyboardButton的url参数不支持t.me/c/格式
                row1.append(InlineKeyboardButton("🔗 查看", callback_data=f"view_channel:{archive_id}"))
        
        if has_notes:
            row1.append(InlineKeyboardButton("📝 笔记", callback_data=f"note:{archive_id}"))
        else:
            row1.append(InlineKeyboardButton("📝 添加笔记", callback_data=f"note_add:{archive_id}"))
        
        if row1:
            keyboard.append(row1)
        
        # 第二行：删除按钮
        keyboard.append([
            InlineKeyboardButton("🗑️ 删除", callback_data=f"delete:{archive_id}")
        ])
        
        return InlineKeyboardMarkup(keyboard) if keyboard else None
    
    @staticmethod
    def format_other_archive_reply(
        archive: Dict[str, Any],
        has_notes: bool = False
    ) -> tuple[str, Optional[Any]]:
        """
        构建其他类型存档的详情展示格式
        用于非文本非媒体类型（如链接、文档等）
        
        Args:
            archive: 存档数据
            has_notes: 是否有关联笔记
            
        Returns:
            (格式化的消息文本, InlineKeyboardMarkup按钮或None)
        """
        from telegram import InlineKeyboardButton, InlineKeyboardMarkup
        
        archive_id = archive.get('id')
        title = archive.get('title', f"存档 #{archive_id}")
        storage_path = archive.get('storage_path', '')
        content_type = archive.get('content_type', '')
        emoji = get_content_type_emoji(content_type)
        
        # 构建标题链接
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
        
        # 构建按钮
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
