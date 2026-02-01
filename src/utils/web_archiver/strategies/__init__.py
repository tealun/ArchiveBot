"""
Web fetching strategies
"""

from .base import FetchStrategy, FetchResult
from .http_strategy import HttpStrategy
from .telegram_strategy import TelegramStrategy

__all__ = ['FetchStrategy', 'FetchResult', 'HttpStrategy', 'TelegramStrategy']
