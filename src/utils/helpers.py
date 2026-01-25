"""
Helper utility functions
"""

import logging
import re
from datetime import datetime
from typing import List, Optional
from urllib.parse import urlparse
from .config import get_config

logger = logging.getLogger(__name__)


def format_file_size(size_bytes: int) -> str:
    """
    Format file size in human-readable format
    
    Args:
        size_bytes: File size in bytes
        
    Returns:
        Formatted string (e.g., "1.5 MB")
    """
    if size_bytes == 0:
        return "0 B"
    
    units = ['B', 'KB', 'MB', 'GB', 'TB']
    unit_index = 0
    size = float(size_bytes)
    
    while size >= 1024.0 and unit_index < len(units) - 1:
        size /= 1024.0
        unit_index += 1
    
    if unit_index == 0:
        return f"{int(size)} {units[unit_index]}"
    else:
        return f"{size:.2f} {units[unit_index]}"


def extract_hashtags(text: str) -> List[str]:
    """
    Extract hashtags from text
    
    Args:
        text: Input text
        
    Returns:
        List of hashtags (without # symbol)
    """
    if not text:
        return []
    
    # Match hashtags (support English, Chinese, numbers, underscore)
    pattern = r'#([\w\u4e00-\u9fa5]+)'
    matches = re.findall(pattern, text)
    
    # Remove duplicates while preserving order
    seen = set()
    unique_tags = []
    for tag in matches:
        tag_lower = tag.lower()
        if tag_lower not in seen:
            seen.add(tag_lower)
            unique_tags.append(tag)
    
    return unique_tags


def should_create_note(content: str) -> tuple:
    """
    判断内容是否应该创建笔记以及笔记类型
    
    Args:
        content: 输入内容
        
    Returns:
        (is_short_note, note_type)
        - is_short_note: True=直接作为笔记（不归档），False=归档并可能生成AI笔记
        - note_type: 'short'（短文本）| 'long'（长文本）| 'none'（空内容）
    """
    if not content:
        return False, 'none'
    
    # 从配置获取阈值
    config = get_config()
    ai_config = config.get('ai', {})
    text_thresholds = ai_config.get('text_thresholds', {})
    
    # 检测中英文字符
    chinese_chars = len(re.findall(r'[\u4e00-\u9fff]', content))
    english_chars = len(re.findall(r'[a-zA-Z]', content))
    
    # 判断阈值（聊天友好型）
    if chinese_chars > english_chars:
        # 中文为主
        threshold = int(text_thresholds.get('note_chinese', 150))
    else:
        # 英文为主
        threshold = int(text_thresholds.get('note_english', 250))
    
    char_count = len(content)
    
    if char_count < threshold:
        return True, 'short'  # 短文本，直接作为笔记
    else:
        return False, 'long'  # 长文本，需要归档并可能生成AI笔记


def is_url(text: str) -> bool:
    """
    Check if text is a URL
    
    Args:
        text: Input text
        
    Returns:
        True if text is a URL, False otherwise
    """
    if not text:
        return False
    
    try:
        result = urlparse(text.strip())
        return all([result.scheme, result.netloc])
    except Exception:
        return False


def extract_urls(text: str) -> List[str]:
    """
    Extract URLs from text
    
    Args:
        text: Input text
        
    Returns:
        List of URLs
    """
    if not text:
        return []
    
    # URL pattern
    url_pattern = r'http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\\(\\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+'
    urls = re.findall(url_pattern, text)
    
    return urls


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """
    Truncate text to max length
    
    Args:
        text: Input text
        max_length: Maximum length
        suffix: Suffix to add if truncated
        
    Returns:
        Truncated text
    """
    if not text or len(text) <= max_length:
        return text
    
    return text[:max_length - len(suffix)] + suffix


def format_datetime(dt: Optional[datetime] = None, format_str: str = "%Y-%m-%d %H:%M:%S") -> str:
    """
    Format datetime object
    
    Args:
        dt: Datetime object (if None, use current time)
        format_str: Format string
        
    Returns:
        Formatted datetime string
    """
    if dt is None:
        dt = datetime.now()
    elif isinstance(dt, str):
        try:
            dt = datetime.fromisoformat(dt)
        except ValueError:
            return dt
    
    return dt.strftime(format_str)


def parse_datetime(dt_str: str) -> Optional[datetime]:
    """
    Parse datetime string
    
    Args:
        dt_str: Datetime string
        
    Returns:
        Datetime object or None if parsing failed
    """
    if not dt_str:
        return None
    
    try:
        return datetime.fromisoformat(dt_str)
    except ValueError:
        logger.warning(f"Failed to parse datetime: {dt_str}")
        return None


def sanitize_filename(filename: str) -> str:
    """
    Sanitize filename by removing invalid characters
    
    Args:
        filename: Original filename
        
    Returns:
        Sanitized filename
    """
    if not filename:
        return "untitled"
    
    # Remove invalid characters
    invalid_chars = r'[<>:"/\\|?*]'
    sanitized = re.sub(invalid_chars, '_', filename)
    
    # Limit length
    max_length = 255
    if len(sanitized) > max_length:
        name, ext = splitext(sanitized)
        if len(ext) > 10:
            ext = ext[:10]
        max_name_length = max_length - len(ext)
        sanitized = name[:max_name_length] + ext
    
    return sanitized


def splitext(filename: str) -> tuple:
    """
    Split filename into name and extension
    
    Args:
        filename: Filename
        
    Returns:
        Tuple of (name, extension)
    """
    if '.' in filename:
        parts = filename.rsplit('.', 1)
        return parts[0], '.' + parts[1]
    return filename, ''


def escape_markdown(text: str) -> str:
    """
    Escape special characters for Telegram MarkdownV2
    
    Args:
        text: Input text
        
    Returns:
        Escaped text
    """
    if not text:
        return ""
    
    # Characters that need to be escaped in MarkdownV2
    special_chars = r'_*[]()~`>#+-=|{}.!'
    
    escaped = text
    for char in special_chars:
        escaped = escaped.replace(char, '\\' + char)
    
    return escaped


def validate_telegram_id(telegram_id: int) -> bool:
    """
    Validate Telegram user/chat ID
    
    Args:
        telegram_id: Telegram ID
        
    Returns:
        True if valid, False otherwise
    """
    # Telegram IDs are positive integers for users
    # Negative integers for groups/channels
    # Must be non-zero
    return telegram_id != 0 and isinstance(telegram_id, int)


def get_content_type_emoji(content_type: str) -> str:
    """
    Get emoji for content type
    
    Args:
        content_type: Content type
        
    Returns:
        Emoji string
    """
    emoji_map = {
        'text': '📝',
        'image': '🖼️',
        'video': '🎬',
        'document': '📄',
        'link': '🔗',
        'audio': '🎵',
        'voice': '🎤',
        'sticker': '🎨',
        'animation': '🎞️',
        'contact': '👤',
        'location': '📍',
    }
    
    return emoji_map.get(content_type, '📦')
