"""
消息构建框架 - 兼容层
提供向后兼容的统一接口，实际实现已拆分到专门的格式化器
"""
from __future__ import annotations

import logging
from typing import List, Dict, Any, Optional
from telegram import Bot, Message

from .formatters.archive_formatter import ArchiveFormatter
from .formatters.note_formatter import NoteFormatter
from .formatters.system_formatter import SystemFormatter

logger = logging.getLogger(__name__)


class MessageBuilder:
    """
    消息构建器 - 向后兼容的统一接口
    
    实际实现已拆分到：
    - ArchiveFormatter: 归档相关格式化
    - NoteFormatter: 笔记相关格式化
    - SystemFormatter: 系统功能格式化
    """
    
    # ========== 归档相关方法（委托给 ArchiveFormatter）==========
    
    @staticmethod
    async def build_archive_success_message(
        archive_data: Dict[str, Any],
        i18n,
        include_ai_info: bool = True,
        bot: Optional[Any] = None
    ) -> str:
        """构建归档成功消息"""
        return await ArchiveFormatter.build_success_message(archive_data, i18n, include_ai_info, bot)
    
    @staticmethod
    def format_archive_list(
        archives: List[Dict[str, Any]],
        i18n,
        db_instance=None,
        with_links: bool = True
    ) -> str:
        """格式化归档列表"""
        return ArchiveFormatter.format_list(archives, i18n, db_instance, with_links)
    
    @staticmethod
    def format_text_archive_reply(
        archive: Dict[str, Any],
        notes: Optional[List[Dict[str, Any]]] = None,
        db_instance=None
    ) -> tuple[str, Optional[Any]]:
        """格式化文本归档详情"""
        return ArchiveFormatter.format_text_detail(archive, notes, db_instance)
    
    @staticmethod
    def format_media_archive_caption(
        archive: Dict[str, Any],
        notes: Optional[List[Dict[str, Any]]] = None,
        max_length: int = 200
    ) -> str:
        """格式化媒体归档caption"""
        return ArchiveFormatter.format_media_caption(archive, notes, max_length)
    
    @staticmethod
    def build_media_archive_buttons(
        archive: Dict[str, Any],
        has_notes: bool = False
    ) -> Optional[Any]:
        """构建媒体归档按钮"""
        return ArchiveFormatter.build_media_buttons(archive, has_notes)
    
    @staticmethod
    def format_other_archive_reply(
        archive: Dict[str, Any],
        has_notes: bool = False
    ) -> tuple[str, Optional[Any]]:
        """格式化其他类型归档详情"""
        return ArchiveFormatter.format_other_detail(archive, has_notes)
    
    @staticmethod
    async def send_archive_resource(
        bot: Bot,
        chat_id: int,
        archive: Dict[str, Any],
        caption: Optional[str] = None,
        reply_markup: Optional[Any] = None
    ) -> Optional[Message]:
        """发送归档资源文件"""
        return await ArchiveFormatter.send_resource(bot, chat_id, archive, caption, reply_markup)
    
    @staticmethod
    async def send_archive_resources_batch(
        bot: Bot,
        chat_id: int,
        archives: List[Dict[str, Any]],
        max_count: int = 10
    ) -> int:
        """批量发送归档资源文件"""
        return await ArchiveFormatter.send_resources_batch(bot, chat_id, archives, max_count)
    
    # ========== 笔记相关方法（委托给 NoteFormatter）==========
    
    @staticmethod
    def format_notes_list(
        notes: List[Dict[str, Any]],
        config,
        lang_ctx,
        page: int = 0,
        total_count: int = None
    ) -> tuple[str, Optional[Any]]:
        """构建笔记列表（命令场景）"""
        return NoteFormatter.format_list(notes, config, lang_ctx, page, total_count)
    
    @staticmethod
    def format_note_detail_reply(
        note: Dict[str, Any],
        archive: Optional[Dict[str, Any]] = None
    ) -> tuple[str, Optional[Any]]:
        """构建单条笔记详情"""
        return NoteFormatter.format_detail(note, archive)
    
    @staticmethod
    def format_note_list_multi(
        notes: List[Dict[str, Any]],
        archive_id: int,
        lang_ctx
    ) -> tuple[str, Any]:
        """格式化多条笔记列表（回调场景）"""
        return NoteFormatter.format_list_multi(notes, archive_id, lang_ctx)
    
    @staticmethod
    def format_note_input_prompt(
        archive_id: int,
        prompt_type: str = 'add',
        note_content: str = None
    ) -> str:
        """格式化笔记输入提示"""
        return NoteFormatter.format_input_prompt(archive_id, prompt_type, note_content)
    
    @staticmethod
    def format_note_share(
        note_content: str,
        note_created_at: str,
        archive_id: int,
        archive_title: str = None
    ) -> str:
        """格式化笔记分享文本"""
        return NoteFormatter.format_share(note_content, note_created_at, archive_id, archive_title)
    
    # ========== 系统功能方法（委托给 SystemFormatter）==========
    
    @staticmethod
    def format_trash_list(
        items: List[Dict[str, Any]],
        lang_ctx,
        max_display: int = 20
    ) -> str:
        """格式化垃圾箱列表"""
        return SystemFormatter.format_trash_list(items, lang_ctx, max_display)
    
    @staticmethod
    def format_ai_status(
        ai_config: Dict[str, Any],
        context,
        lang_ctx
    ) -> str:
        """格式化AI功能状态"""
        return SystemFormatter.format_ai_status(ai_config, context, lang_ctx)
    
    @staticmethod
    def format_setting_category_menu(
        category_key: str,
        category_info: Dict[str, Any],
        config_getter
    ) -> tuple[str, Any]:
        """格式化配置分类菜单"""
        return SystemFormatter.format_setting_category_menu(category_key, category_info, config_getter)
    
    @staticmethod
    def format_setting_item_prompt(
        item_info: Dict[str, Any],
        config_key: str,
        current_value: Any,
        category_key: str
    ) -> tuple[str, Any]:
        """格式化配置项输入提示"""
        return SystemFormatter.format_setting_item_prompt(item_info, config_key, current_value, category_key)
    
    @staticmethod
    def format_stats(stats: Dict[str, Any], language: str = 'zh-CN', db_size: int = 0) -> str:
        """格式化统计信息"""
        return SystemFormatter.format_stats(stats, language, db_size)
    
    @staticmethod
    def format_search_results_summary(
        results: List[Dict], 
        total_count: int, 
        query: str,
        language: str = 'zh-CN',
        max_items: int = 5
    ) -> str:
        """格式化搜索结果摘要"""
        return SystemFormatter.format_search_results_summary(results, total_count, query, language, max_items)
    
    @staticmethod
    def format_tag_analysis(
        tags: List[Dict], 
        language: str = 'zh-CN',
        max_tags: int = 10
    ) -> str:
        """格式化标签分析"""
        return SystemFormatter.format_tag_analysis(tags, language, max_tags)
    
    @staticmethod
    def format_recent_archives(
        archives: List[Dict],
        language: str = 'zh-CN',
        max_items: int = 5
    ) -> str:
        """格式化最近归档列表"""
        return SystemFormatter.format_recent_archives(archives, language, max_items)
    
    @staticmethod
    def format_ai_context_summary(
        data_context: Dict[str, Any],
        user_intent: str,
        language: str = 'zh-CN'
    ) -> str:
        """格式化AI上下文数据摘要"""
        return SystemFormatter.format_ai_context_summary(data_context, user_intent, language)
