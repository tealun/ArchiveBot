"""
AI Prompt 模板管理器
负责管理所有 AI 功能的 prompt 模板，与业务逻辑分离

模块结构：
- summarize.py: 内容摘要分析相关 prompts
- note.py: 笔记生成相关 prompts
- title.py: 标题生成相关 prompts
"""

from .summarize import SummarizePrompts
from .note import NotePrompts
from .title import TitlePrompts


class PromptManager:
    """统一管理所有 AI prompt 模板的管理器"""
    
    @staticmethod
    def get_summarize_prompt(
        content: str,
        is_formal: bool,
        language: str,
        language_instruction: str,
        context_info: str,
        example_categories: str,
        example_tags: str = ""
    ) -> str:
        """
        获取内容摘要分析的 prompt
        
        委托给 SummarizePrompts.get_prompt()
        """
        return SummarizePrompts.get_prompt(
            content=content,
            is_formal=is_formal,
            language=language,
            language_instruction=language_instruction,
            context_info=context_info,
            example_categories=example_categories,
            example_tags=example_tags
        )
    
    @staticmethod
    def get_note_prompt(
        content: str,
        content_type: str,
        max_length: int,
        is_formal: bool,
        language: str
    ) -> str:
        """
        获取笔记生成的 prompt
        
        委托给 NotePrompts.get_direct_prompt()
        """
        return NotePrompts.get_direct_prompt(
            content=content,
            content_type=content_type,
            max_length=max_length,
            is_formal=is_formal,
            language=language
        )
    
    @staticmethod
    def get_note_from_analysis_prompt(
        title: str,
        ai_category: str,
        ai_summary: str,
        key_points_text: str,
        is_formal: bool,
        language: str
    ) -> str:
        """
        获取从AI分析结果整理笔记的 prompt
        
        委托给 NotePrompts.get_from_analysis_prompt()
        """
        return NotePrompts.get_from_analysis_prompt(
            title=title,
            ai_category=ai_category,
            ai_summary=ai_summary,
            key_points_text=key_points_text,
            is_formal=is_formal,
            language=language
        )
    
    @staticmethod
    def get_title_prompt(
        content: str,
        max_length: int,
        is_formal: bool,
        language: str,
        detected_lang: str
    ) -> str:
        """
        获取标题生成的 prompt
        
        委托给 TitlePrompts.get_prompt()
        """
        return TitlePrompts.get_prompt(
            content=content,
            max_length=max_length,
            is_formal=is_formal,
            language=language,
            detected_lang=detected_lang
        )


__all__ = ['PromptManager', 'SummarizePrompts', 'NotePrompts', 'TitlePrompts']
