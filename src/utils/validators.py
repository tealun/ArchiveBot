"""
Input validation and sanitization utilities
"""

import re
import logging
from typing import Optional

logger = logging.getLogger(__name__)


def sanitize_sql_like_pattern(pattern: str) -> str:
    """
    Sanitize SQL LIKE pattern by escaping special characters
    
    Args:
        pattern: Input pattern
        
    Returns:
        Sanitized pattern
    """
    if not pattern:
        return ""
    
    # Escape LIKE wildcards and backslash
    sanitized = pattern.replace('\\', '\\\\')
    sanitized = sanitized.replace('%', '\\%')
    sanitized = sanitized.replace('_', '\\_')
    
    return sanitized


def validate_tag_name(tag_name: str) -> bool:
    """
    Validate tag name
    
    Args:
        tag_name: Tag name to validate
        
    Returns:
        True if valid, False otherwise
    """
    if not tag_name:
        return False
    
    # Tag should be alphanumeric with underscores, hyphens, and unicode letters
    # Length between 1-50 characters
    if len(tag_name) > 50:
        return False
    
    # Allow letters (including unicode), numbers, underscore, hyphen
    pattern = r'^[\w\u4e00-\u9fa5\-]+$'
    return bool(re.match(pattern, tag_name))


def sanitize_tag_name(tag_name: str) -> Optional[str]:
    """
    Sanitize and validate tag name
    
    Args:
        tag_name: Raw tag name
        
    Returns:
        Sanitized tag name or None if invalid
    """
    if not tag_name:
        return None
    
    # Remove leading/trailing whitespace
    tag_name = tag_name.strip()
    
    # Remove # prefix if present
    if tag_name.startswith('#'):
        tag_name = tag_name[1:]
    
    # Convert to lowercase for consistency
    tag_name = tag_name.lower()
    
    # Validate
    if not validate_tag_name(tag_name):
        logger.warning(f"Invalid tag name: {tag_name}")
        return None
    
    return tag_name


def validate_file_size(file_size: Optional[int], max_size: int) -> bool:
    """
    Validate file size
    
    Args:
        file_size: File size in bytes
        max_size: Maximum allowed size in bytes
        
    Returns:
        True if valid, False otherwise
    """
    if file_size is None:
        return True  # No size limit for references
    
    return 0 < file_size <= max_size


def sanitize_text_input(text: str, max_length: int = 10000) -> str:
    """
    Sanitize text input
    
    Args:
        text: Input text
        max_length: Maximum length
        
    Returns:
        Sanitized text
    """
    if not text:
        return ""
    
    # Remove null bytes
    text = text.replace('\x00', '')
    
    # Truncate if too long
    if len(text) > max_length:
        text = text[:max_length]
    
    return text


def validate_storage_type(storage_type: str) -> bool:
    """
    Validate storage type
    
    Args:
        storage_type: Storage type
        
    Returns:
        True if valid, False otherwise
    """
    valid_types = {'database', 'telegram', 'cloud', 'reference'}
    return storage_type in valid_types


def validate_content_type(content_type: str) -> bool:
    """
    Validate content type
    
    Args:
        content_type: Content type
        
    Returns:
        True if valid, False otherwise
    """
    valid_types = {
        'text', 'image', 'video', 'document', 'link',
        'audio', 'voice', 'animation', 'sticker',
        'contact', 'location'
    }
    return content_type in valid_types
