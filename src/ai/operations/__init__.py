"""
AI Operations - Organized by functionality
"""
from .summarize import summarize_operation
from .tags import generate_tags_operation, batch_generate_tags_operation
from .notes import (
    generate_note_from_content_operation,
    generate_note_from_ai_analysis_operation
)
from .titles import generate_title_from_text_operation
from .ebook import is_ebook_operation
from .executor import execute_confirmed_action
from .safe_executor import execute_safe_operation

__all__ = [
    'summarize_operation',
    'generate_tags_operation',
    'batch_generate_tags_operation',
    'generate_note_from_content_operation',
    'generate_note_from_ai_analysis_operation',
    'generate_title_from_text_operation',
    'is_ebook_operation',
    'execute_confirmed_action',
    'execute_safe_operation',
]
