"""
笔记相关的消息格式化器
处理笔记列表、详情、输入提示、分享等格式化
"""
from __future__ import annotations

import logging
from typing import List, Dict, Any, Optional
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from ..helpers import truncate_text

logger = logging.getLogger(__name__)


class NoteFormatter:
    """笔记格式化器 - 处理笔记相关的消息格式化"""
    
    @staticmethod
    def format_list(
        notes: List[Dict[str, Any]],
        config,
        lang_ctx,
        page: int = 0,
        total_count: int = None
    ) -> tuple[str, Optional[Any]]:
        """
        构建笔记列表的格式化展示（命令场景，完整版）
        
        Args:
            notes: 笔记列表
            config: 配置对象
            lang_ctx: 语言上下文
            page: 当前页码（从0开始）
            total_count: 总笔记数（可选）
            
        Returns:
            (格式化的消息文本, InlineKeyboardMarkup按钮或None)
        """
        if not notes:
            return lang_ctx.t('notes_list_empty'), None
        
        # 使用总数，如果未提供则使用当前页的数量
        display_total = total_count if total_count is not None else len(notes)
        result_text = lang_ctx.t('notes_list_header', count=display_total) + "\n"
        
        keyboard = []
        for idx, note in enumerate(notes, 1):
            note_id = note['id']
            created_at = note['created_at']
            content = note['content']
            archive_id = note.get('archive_id')
            title = note.get('title', '')
            
            result_text += "\n" + "="*40 + "\n\n"
            
            if title:
                result_text += f"📝 <b>笔记 #{note_id}</b> - {title}\n"
            else:
                result_text += f"📝 <b>笔记 #{note_id}</b>\n"
            
            note_type = "自动" if archive_id else "手动"
            result_text += f"📅 {created_at} | 🏷️ {note_type}\n"
            
            content_preview = truncate_text(content, 80)
            result_text += f"💬 {content_preview}\n"
            
            if archive_id:
                archive_title = note.get('archive_title', f'归档 #{archive_id}')
                storage_path = note.get('storage_path')
                storage_type = note.get('storage_type')
                
                if storage_path and storage_type == 'telegram':
                    parts = storage_path.split(':')
                    if len(parts) >= 2:
                        channel_id = parts[0].replace('-100', '')
                        message_id = parts[1]
                    else:
                        channel_id = str(config.telegram_channel_id).replace('-100', '')
                        message_id = storage_path
                    
                    link = f"https://t.me/c/{channel_id}/{message_id}"
                    result_text += f"📎 归档：<a href='{link}'>{archive_title}</a>\n"
                else:
                    result_text += f"📎 归档：{archive_title}\n"
            
            keyboard.append([
                InlineKeyboardButton(
                    f"{idx}. 查看笔记 #{note_id} 详情",
                    callback_data=f"note_view:{note_id}"
                )
            ])
        
        result_text += "\n" + "="*40 + "\n"
        result_text += f"\n📊 共 {display_total} 条笔记"
        
        # 添加分页按钮（只在多页时显示）
        page_size = 10
        if total_count and total_count > page_size:
            total_pages = (total_count + page_size - 1) // page_size
            nav_row = []
            
            if page > 0:
                nav_row.append(InlineKeyboardButton(
                    lang_ctx.t('button_previous_page'),
                    callback_data=f"notes_page:{page-1}"
                ))
            
            nav_row.append(InlineKeyboardButton(
                lang_ctx.t('pagination_page_of', current=page+1, total=total_pages),
                callback_data="notes_noop"
            ))
            
            if (page + 1) * page_size < total_count:
                nav_row.append(InlineKeyboardButton(
                    lang_ctx.t('button_next_page'),
                    callback_data=f"notes_page:{page+1}"
                ))
            
            keyboard.append(nav_row)
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        return result_text, reply_markup
    
    @staticmethod
    def format_detail(
        note: Dict[str, Any],
        archive: Optional[Dict[str, Any]] = None
    ) -> tuple[str, Optional[Any]]:
        """
        构建单条笔记的详情展示格式
        
        Args:
            note: 笔记数据
            archive: 关联的存档数据（可选）
            
        Returns:
            (格式化的消息文本, InlineKeyboardMarkup按钮或None)
        """
        note_id = note.get('id')
        note_title = note.get('title', '')
        note_content = note.get('content', '')
        created_at = note.get('created_at', '')
        archive_id = note.get('archive_id')
        
        # 构建标题
        if note_title:
            title_line = f"📝 [{note_title}]"
        else:
            title_line = f"📝 [笔记 #{note_id} 详情]"
        
        # 构建消息
        text = f"{title_line}\n"
        text += "-" * 51 + "\n"
        text += f"📎 id：#{note_id} 📅 创建时间：{created_at}\n\n"
        text += f"{note_content}\n"
        text += "-" * 51
        
        # 构建按钮
        keyboard = []
        if archive_id:
            keyboard.append([
                InlineKeyboardButton("✏️ 编辑", callback_data=f"note_edit:{archive_id}:{note_id}"),
                InlineKeyboardButton("➕ 追加", callback_data=f"note_append:{archive_id}")
            ])
            keyboard.append([
                InlineKeyboardButton("📤 分享", callback_data=f"note_share:{archive_id}:{note_id}"),
                InlineKeyboardButton("🗑️ 删除", callback_data=f"note_delete:{note_id}")
            ])
            keyboard.append([
                InlineKeyboardButton("❌ 关闭", callback_data=f"note_close")
            ])
        else:
            keyboard.append([
                InlineKeyboardButton("✏️ 编辑", callback_data=f"note_quick_edit:{note_id}"),
                InlineKeyboardButton("🗑️ 删除", callback_data=f"note_quick_delete:{note_id}")
            ])
            keyboard.append([
                InlineKeyboardButton("❌ 关闭", callback_data=f"note_close")
            ])
        
        reply_markup = InlineKeyboardMarkup(keyboard) if keyboard else None
        
        return text, reply_markup
    
    @staticmethod
    def format_list_multi(
        notes: List[Dict[str, Any]],
        archive_id: int,
        lang_ctx
    ) -> tuple[str, Any]:
        """
        格式化多条笔记的简单列表（回调场景，简化版）
        
        Args:
            notes: 笔记列表
            archive_id: 归档ID
            lang_ctx: 语言上下文
            
        Returns:
            (格式化的消息文本, InlineKeyboardMarkup)
        """
        notes_text = f"📝 归档 #{archive_id} 的笔记 (共{len(notes)}条)\n\n"
        
        for idx, note in enumerate(notes, 1):
            content = note['content']
            notes_text += f"{idx}. {content}\n"
            notes_text += f"   📅 {note['created_at']}\n\n"
        
        keyboard = [[
            InlineKeyboardButton("✏️ 编辑最新", callback_data=f"note_edit:{archive_id}:{notes[-1]['id']}"),
            InlineKeyboardButton("🗑️ 删除最新", callback_data=f"note_delete:{notes[-1]['id']}")
        ]]
        keyboard.append([InlineKeyboardButton("📤 分享最新", callback_data=f"note_share:{archive_id}:{notes[-1]['id']}")])
        keyboard.append([InlineKeyboardButton("✖️ 关闭", callback_data=f"note_close")])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        return notes_text, reply_markup
    
    @staticmethod
    def format_input_prompt(
        archive_id: int,
        prompt_type: str = 'add',
        note_content: str = None
    ) -> str:
        """
        格式化笔记输入提示
        
        Args:
            archive_id: 归档ID
            prompt_type: 提示类型 ('add', 'modify', 'append', 'edit_menu', 'quick_edit')
            note_content: 笔记内容（用于modify和quick_edit类型）
            
        Returns:
            格式化的提示文本
        """
        if prompt_type == 'add':
            return f"📝 归档 #{archive_id} 还没有笔记\n\n💬 请回复此消息输入笔记内容"
        elif prompt_type == 'modify':
            return f"📝 当前笔记内容：\n\n{note_content}\n\n💡 请复制上方内容，修改后回复此消息发送"
        elif prompt_type == 'append':
            return "➕ 追加笔记内容\n\n请回复此消息输入要追加的内容"
        elif prompt_type == 'edit_menu':
            return f"📝 编辑归档 #{archive_id} 的笔记\n\n请选择操作："
        elif prompt_type == 'quick_edit':
            return f"📝 当前笔记内容：\n\n{note_content}\n\n💡 请发送新内容来替换此笔记"
        else:
            return f"📝 归档 #{archive_id}\n\n💬 请输入笔记内容"
    
    @staticmethod
    def format_share(
        note_content: str,
        note_created_at: str,
        archive_id: int,
        archive_title: str = None
    ) -> str:
        """
        格式化笔记分享文本
        
        Args:
            note_content: 笔记内容
            note_created_at: 笔记创建时间
            archive_id: 归档ID
            archive_title: 归档标题（可选）
            
        Returns:
            格式化的分享文本
        """
        share_text = "📝 笔记分享\n\n"
        
        if archive_title:
            share_text += f"📌 {archive_title}\n\n"
        
        share_text += f"{note_content}\n\n"
        share_text += f"---\n"
        share_text += f"📅 {note_created_at}\n"
        share_text += f"🔖 来自归档 #{archive_id}"
        
        return share_text
    
    @staticmethod
    def format_ai_summary(
        notes: List[Dict],
        language: str = 'zh-CN',
        max_items: int = 10,
        total_count: int = None
    ) -> str:
        """
        格式化笔记列表摘要（用于AI上下文）
        
        Args:
            notes: 笔记列表（返回的样本）
            language: 语言代码
            max_items: 最多显示条数
            total_count: 笔记总数（如果提供，会显示"共X条，显示Y条"）
            
        Returns:
            格式化后的笔记摘要文本
        """
        if not notes:
            if language == 'en':
                return "No notes available"
            elif language == 'zh-TW':
                return "暫無筆記"
            else:
                return "暂无笔记"
        
        # 使用total_count（如果提供），否则使用notes长度
        if total_count is None:
            total_count = len(notes)
        
        display_count = len(notes[:max_items])
        
        # 根据是否显示全部，调整header文本
        if total_count > display_count:
            if language == 'en':
                header = f"📝 {total_count} Notes Found (showing {display_count}):\n"
            elif language == 'zh-TW':
                header = f"📝 共 {total_count} 條筆記（顯示 {display_count} 條）：\n"
            else:
                header = f"📝 共 {total_count} 条笔记（显示 {display_count} 条）：\n"
        else:
            if language == 'en':
                header = f"📝 {total_count} Notes Found:\n"
            elif language == 'zh-TW':
                header = f"📝 找到 {total_count} 條筆記：\n"
            else:
                header = f"📝 找到 {total_count} 条笔记：\n"
        
        text = header
        for i, note in enumerate(notes[:max_items], 1):
            note_id = note.get('id', '?')
            content = note.get('content', '')
            title = note.get('title', '')
            
            # 优先显示标题，没有标题则显示内容摘要
            if title:
                display_text = title
            elif content:
                display_text = content
            else:
                display_text = '(无内容)' if language.startswith('zh') else '(No content)'
            
            # 截断过长文本
            if len(display_text) > 50:
                display_text = display_text[:50] + '...'
            
            # 显示是否有链接
            has_link = note.get('storage_path') or note.get('archive_storage_path')
            link_icon = '🔗' if has_link else ''
            
            text += f"{i}. #{note_id} {link_icon}{display_text}\n"
        
        return text.rstrip()
