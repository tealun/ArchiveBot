"""
AI package
AI智能功能模块
"""

from .summarizer import (
    AISummarizer,
    get_ai_summarizer,
    summarize_link
)

__all__ = [
    'AISummarizer',
    'get_ai_summarizer',
    'summarize_link'
]
