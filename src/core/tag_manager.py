"""
Tag manager module
Handles automatic and manual tag management
"""

import logging
from typing import List, Set, Optional
from ..storage.database import DatabaseStorage
from ..utils.helpers import extract_hashtags
from ..utils.validators import sanitize_tag_name
from ..utils.i18n import get_i18n
from ..utils.config import get_config

logger = logging.getLogger(__name__)


class TagManager:
    """
    Manages tags for archives
    """
    
    def __init__(self, db_storage: DatabaseStorage):
        """
        Initialize tag manager
        
        Args:
            db_storage: DatabaseStorage instance
        """
        self.db_storage = db_storage
        self.i18n = get_i18n()
    
    def generate_auto_tags(self, content_type: str) -> List[str]:
        """
        Generate automatic tags based on content type
        
        Args:
            content_type: Content type
            
        Returns:
            List of tag names
        """
        # 检查是否启用文件类型标签
        config = get_config()
        auto_file_type_tag = config.get('features.auto_file_type_tag', False)
        
        if not auto_file_type_tag:
            return []
        
        # Get localized tag name
        tag_key = f"tag_{content_type}"
        tag_name = self.i18n.t(tag_key)
        
        # If translation not found, use English default
        if tag_name == tag_key:
            tag_name = content_type
        
        return [tag_name]
    
    def parse_manual_tags(self, text: str) -> List[str]:
        """
        Parse manual tags from text
        
        Args:
            text: Text containing hashtags
            
        Returns:
            List of tag names (without #)
        """
        raw_tags = extract_hashtags(text)
        
        # Sanitize and validate tags
        valid_tags = []
        for tag in raw_tags:
            sanitized = sanitize_tag_name(tag)
            if sanitized:
                valid_tags.append(sanitized)
        
        return valid_tags
    
    def add_tags_to_archive(
        self,
        archive_id: int,
        tag_names: List[str],
        tag_type: str = 'manual'
    ) -> int:
        """
        Add tags to archive
        
        Args:
            archive_id: Archive ID
            tag_names: List of tag names
            tag_type: Tag type (auto, manual, ai)
            
        Returns:
            Number of tags added
        """
        try:
            added_count = 0
            
            for tag_name in tag_names:
                if not tag_name:
                    continue
                
                # Sanitize tag name
                sanitized = sanitize_tag_name(tag_name)
                if not sanitized:
                    logger.warning(f"Skipping invalid tag: {tag_name}")
                    continue
                
                try:
                    # Get or create tag
                    tag_id = self.db_storage.get_or_create_tag(sanitized, tag_type)
                    
                    # Associate tag with archive
                    if self.db_storage.associate_tag(archive_id, tag_id):
                        added_count += 1
                except Exception as e:
                    logger.error(f"Error adding tag '{sanitized}' to archive {archive_id}: {e}")
                    # Continue with other tags
            
            logger.info(f"Added {added_count} tags to archive {archive_id}")
            return added_count
            
        except Exception as e:
            logger.error(f"Error adding tags to archive: {e}", exc_info=True)
            return 0
    
    def get_archive_tags(self, archive_id: int) -> List[str]:
        """
        Get all tags for an archive
        
        Args:
            archive_id: Archive ID
            
        Returns:
            List of tag names
        """
        return self.db_storage.get_archive_tags(archive_id)
    
    def get_all_tags(self, limit: int = 100) -> List[dict]:
        """
        Get all tags with usage counts
        
        Args:
            limit: Maximum number of tags
            
        Returns:
            List of tag dictionaries
        """
        return self.db_storage.get_all_tags(limit)
    
    def format_tags_for_display(self, tag_names: List[str]) -> str:
        """
        Format tags for display
        
        Args:
            tag_names: List of tag names
            
        Returns:
            Formatted string
        """
        if not tag_names:
            return ""
        
        return " ".join(f"#{tag}" for tag in tag_names)

    def remove_tag(self, tag_name: str, archive_ids: Optional[List[int]] = None) -> int:
        """Bulk-remove a tag from selected archives"""
        sanitized = sanitize_tag_name(tag_name)
        if not sanitized:
            return 0
        return self.db_storage.remove_tag_from_archives(sanitized, archive_ids)

    def replace_tag(self, old_tag: str, new_tag: str, archive_ids: Optional[List[int]] = None) -> int:
        """Replace an existing tag with a new one across archives"""
        old_sanitized = sanitize_tag_name(old_tag)
        new_sanitized = sanitize_tag_name(new_tag)
        if not old_sanitized or not new_sanitized:
            return 0
        return self.db_storage.replace_tag_in_archives(old_sanitized, new_sanitized, archive_ids)
