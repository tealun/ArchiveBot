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
        lang_ctx
    ) -> tuple[str, Optional[Any]]:
        """
        构建笔记列表的格式化展示（命令场景，完整版）
        
        Args:
            notes: 笔记列表
            config: 配置对象
            lang_ctx: 语言上下文
            
        Returns:
            (格式化的消息文本, InlineKeyboardMarkup按钮或None)
        """
        if not notes:
            return lang_ctx.t('notes_list_empty'), None
        
        result_text = lang_ctx.t('notes_list_header', count=len(notes)) + "\n"
        
        keyboard = []
        for idx, note in enumerate(notes, 1):
            note_id = note['id']
            created_at = note['created_at']
            content = note['content']
            archive_id = note.get('archive_id')
            title = note.get('title', '')
            
            result_text += "\n━━━━━━━━━━━━━━━━━━━━\n\n"
            
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
                    f"{idx}. 查看完整内容",
                    callback_data=f"note_view:{note_id}"
                )
            ])
        
        result_text += "\n━━━━━━━━━━━━━━━━━━━━\n"
        result_text += f"\n📊 共 {len(notes)} 条笔记"
        
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
        
        if note_title:
            text = f"📝 [笔记 {note_link}] {note_title}\n"
            text += "----------------------------------\n"
            text += f"{note_content}\n"
            text += "----------------------------------\n"
            text += f"📅 {created_at}"
        else:
            text = f"📝 [笔记 {note_link}]\n"
            text += "----------------------------------\n"
            text += f"{note_content}\n"
            text += "----------------------------------\n"
            text += f"📅 {created_at}"
        
        keyboard = []
        if archive_id:
            keyboard.append([
                InlineKeyboardButton("✏️ 编辑", callback_data=f"note_edit:{archive_id}:{note_id}"),
                InlineKeyboardButton("➕ 追加", callback_data=f"note_append:{archive_id}:{note_id}")
            ])
            keyboard.append([
                InlineKeyboardButton("📤 分享", callback_data=f"note_share:{archive_id}:{note_id}"),
                InlineKeyboardButton("🗑️ 删除", callback_data=f"note_delete:{note_id}")
            ])
        else:
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
