"""
File handling utilities
"""

import logging
import hashlib
from pathlib import Path
from typing import Optional, BinaryIO
import mimetypes

logger = logging.getLogger(__name__)


def get_file_hash(file_path: str, algorithm: str = 'md5') -> Optional[str]:
    """
    Calculate file hash
    
    Args:
        file_path: Path to file
        algorithm: Hash algorithm (md5, sha1, sha256)
        
    Returns:
        Hash string or None if error
    """
    try:
        hash_obj = hashlib.new(algorithm)
        
        with open(file_path, 'rb') as f:
            while chunk := f.read(8192):
                hash_obj.update(chunk)
        
        return hash_obj.hexdigest()
        
    except Exception as e:
        logger.error(f"Error calculating file hash: {e}", exc_info=True)
        return None


def get_mime_type(filename: str) -> Optional[str]:
    """
    Get MIME type from filename
    
    Args:
        filename: Filename
        
    Returns:
        MIME type string or None
    """
    mime_type, _ = mimetypes.guess_type(filename)
    return mime_type


def ensure_dir(directory: str) -> Path:
    """
    Ensure directory exists, create if not
    
    Args:
        directory: Directory path
        
    Returns:
        Path object
    """
    dir_path = Path(directory)
    dir_path.mkdir(parents=True, exist_ok=True)
    return dir_path


def get_file_extension(filename: str) -> str:
    """
    Get file extension
    
    Args:
        filename: Filename
        
    Returns:
        Extension (with dot) or empty string
    """
    return Path(filename).suffix


def is_image(filename: str) -> bool:
    """
    Check if file is an image
    
    Args:
        filename: Filename
        
    Returns:
        True if image, False otherwise
    """
    mime_type = get_mime_type(filename)
    return mime_type is not None and mime_type.startswith('image/')


def is_video(filename: str) -> bool:
    """
    Check if file is a video
    
    Args:
        filename: Filename
        
    Returns:
        True if video, False otherwise
    """
    mime_type = get_mime_type(filename)
    return mime_type is not None and mime_type.startswith('video/')


def is_audio(filename: str) -> bool:
    """
    Check if file is audio
    
    Args:
        filename: Filename
        
    Returns:
        True if audio, False otherwise
    """
    mime_type = get_mime_type(filename)
    return mime_type is not None and mime_type.startswith('audio/')


def is_document(filename: str) -> bool:
    """
    Check if file is a document
    
    Args:
        filename: Filename
        
    Returns:
        True if document, False otherwise
    """
    doc_extensions = {
        '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx',
        '.txt', '.rtf', '.odt', '.ods', '.odp', '.csv'
    }
    
    ext = get_file_extension(filename).lower()
    return ext in doc_extensions


def clean_temp_files(temp_dir: str, max_age_hours: int = 24) -> None:
    """
    Clean old temporary files
    
    Args:
        temp_dir: Temporary directory path
        max_age_hours: Maximum age in hours
    """
    try:
        from datetime import datetime, timedelta
        
        temp_path = Path(temp_dir)
        if not temp_path.exists():
            return
        
        cutoff_time = datetime.now() - timedelta(hours=max_age_hours)
        
        for file_path in temp_path.iterdir():
            if file_path.is_file():
                file_mtime = datetime.fromtimestamp(file_path.stat().st_mtime)
                if file_mtime < cutoff_time:
                    try:
                        file_path.unlink()
                        logger.debug(f"Deleted old temp file: {file_path}")
                    except Exception as e:
                        logger.warning(f"Failed to delete temp file {file_path}: {e}")
        
    except Exception as e:
        logger.error(f"Error cleaning temp files: {e}", exc_info=True)
