"""
Database storage implementation
Handles database operations for archives, tags, and config
"""

import sqlite3
import logging
import json
from typing import List, Optional, Dict, Any, Tuple
from datetime import datetime

from ..models.database import Database
from ..utils.helpers import format_datetime

logger = logging.getLogger(__name__)


class DatabaseStorage:
    """
    Database storage operations
    Single-user design - no user filtering needed
    """
    
    def __init__(self, db: Database):
        """
        Initialize database storage
        
        Args:
            db: Database instance
        """
        self.db = db
    
    def create_archive(
        self,
        content_type: str,
        storage_type: str,
        title: Optional[str] = None,
        content: Optional[str] = None,
        file_id: Optional[str] = None,
        storage_provider: Optional[str] = None,
        storage_path: Optional[str] = None,
        file_size: Optional[int] = None,
        metadata: Optional[Dict[str, Any]] = None,
        source: Optional[str] = None
    ) -> int:
        """
        Create a new archive entry
        
        Args:
            content_type: Type of content (text, image, video, etc.)
            storage_type: Storage type (database, telegram, cloud, reference)
            title: Title or filename
            content: Text content
            file_id: Telegram file_id
            storage_provider: Storage provider name
            storage_path: Storage path or ID
            file_size: File size in bytes
            metadata: Additional metadata as dictionary
            source: Source of content
            
        Returns:
            Archive ID
        """
        with self.db._lock:
            try:
                now = format_datetime()
                metadata_json = json.dumps(metadata, ensure_ascii=False) if metadata else None
                
                cursor = self.db.execute(
                    """
                    INSERT INTO archives (
                        content_type, title, content, file_id,
                        storage_type, storage_provider, storage_path,
                        file_size, metadata, source,
                        created_at, archived_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        content_type, title, content, file_id,
                        storage_type, storage_provider, storage_path,
                        file_size, metadata_json, source,
                        now, now
                    )
                )
                
                self.db.commit()
                archive_id = cursor.lastrowid
                
                logger.info(f"Created archive: ID={archive_id}, type={content_type}, storage={storage_type}")
                return archive_id
                
            except sqlite3.Error as e:
                logger.error(f"Error creating archive: {e}", exc_info=True)
                self.db.rollback()
                raise
    
    def get_archive(self, archive_id: int) -> Optional[Dict[str, Any]]:
        """
        Get archive by ID
        
        Args:
            archive_id: Archive ID
            
        Returns:
            Archive dictionary or None
        """
        try:
            cursor = self.db.execute(
                "SELECT * FROM archives WHERE id = ?",
                (archive_id,)
            )
            
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
            
        except sqlite3.Error as e:
            logger.error(f"Error getting archive: {e}", exc_info=True)
            return None
    
    def search_archives(
        self,
        keyword: Optional[str] = None,
        content_type: Optional[str] = None,
        tag_names: Optional[List[str]] = None,
        limit: int = 10,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Search archives with filters
        
        Args:
            keyword: Search keyword (searches in title and content)
            content_type: Filter by content type
            tag_names: Filter by tag names
            limit: Maximum results
            offset: Results offset for pagination
            
        Returns:
            List of archive dictionaries
        """
        try:
            query_parts = ["SELECT DISTINCT a.* FROM archives a"]
            params = []
            where_clauses = []
            
            # Join with tags if tag filter is specified
            if tag_names:
                query_parts.append("""
                    INNER JOIN archive_tags at ON a.id = at.archive_id
                    INNER JOIN tags t ON at.tag_id = t.id
                """)
                tag_placeholders = ','.join('?' * len(tag_names))
                where_clauses.append(f"t.tag_name IN ({tag_placeholders})")
                params.extend(tag_names)
            
            # Keyword search - escape special characters for LIKE
            if keyword:
                # Escape SQL LIKE wildcards
                escaped_keyword = keyword.replace('%', '\\%').replace('_', '\\_')
                where_clauses.append("(a.title LIKE ? ESCAPE '\\' OR a.content LIKE ? ESCAPE '\\')")
                params.extend([f"%{escaped_keyword}%", f"%{escaped_keyword}%"])
            
            # Content type filter
            if content_type:
                where_clauses.append("a.content_type = ?")
                params.append(content_type)
            
            # Build WHERE clause
            if where_clauses:
                query_parts.append("WHERE " + " AND ".join(where_clauses))
            
            # Order and limit
            query_parts.append("ORDER BY a.archived_at DESC LIMIT ? OFFSET ?")
            params.extend([limit, offset])
            
            query = " ".join(query_parts)
            
            cursor = self.db.execute(query, tuple(params))
            results = [dict(row) for row in cursor.fetchall()]
            
            logger.debug(f"Search found {len(results)} results")
            return results
            
        except sqlite3.Error as e:
            logger.error(f"Error searching archives: {e}", exc_info=True)
            return []
    
    def delete_archive(self, archive_id: int) -> bool:
        """
        Delete archive by ID
        
        Args:
            archive_id: Archive ID
            
        Returns:
            True if deleted, False otherwise
        """
        try:
            self.db.execute("DELETE FROM archives WHERE id = ?", (archive_id,))
            self.db.commit()
            
            logger.info(f"Deleted archive: ID={archive_id}")
            return True
            
        except sqlite3.Error as e:
            logger.error(f"Error deleting archive: {e}", exc_info=True)
            self.db.rollback()
            return False
    
    def create_tag(
        self,
        tag_name: str,
        tag_type: str = 'manual',
        parent_tag_id: Optional[int] = None
    ) -> int:
        """
        Create a new tag
        
        Args:
            tag_name: Tag name
            tag_type: Tag type (auto, ai, manual)
            parent_tag_id: Parent tag ID for hierarchical tags
            
        Returns:
            Tag ID
        """
        try:
            now = format_datetime()
            
            cursor = self.db.execute(
                """
                INSERT INTO tags (tag_name, tag_type, parent_tag_id, count, created_at)
                VALUES (?, ?, ?, 0, ?)
                """,
                (tag_name, tag_type, parent_tag_id, now)
            )
            
            self.db.commit()
            tag_id = cursor.lastrowid
            
            logger.info(f"Created tag: ID={tag_id}, name={tag_name}")
            return tag_id
            
        except sqlite3.IntegrityError:
            # Tag already exists, get its ID
            cursor = self.db.execute(
                "SELECT id FROM tags WHERE tag_name = ?",
                (tag_name,)
            )
            row = cursor.fetchone()
            return row[0] if row else None
        except sqlite3.Error as e:
            logger.error(f"Error creating tag: {e}", exc_info=True)
            self.db.rollback()
            raise
    
    def get_or_create_tag(self, tag_name: str, tag_type: str = 'manual') -> int:
        """
        Get existing tag or create new one
        
        Args:
            tag_name: Tag name
            tag_type: Tag type
            
        Returns:
            Tag ID
        """
        try:
            cursor = self.db.execute(
                "SELECT id FROM tags WHERE tag_name = ?",
                (tag_name,)
            )
            row = cursor.fetchone()
            
            if row:
                return row[0]
            else:
                return self.create_tag(tag_name, tag_type)
                
        except sqlite3.Error as e:
            logger.error(f"Error getting/creating tag: {e}", exc_info=True)
            raise
    
    def associate_tag(self, archive_id: int, tag_id: int) -> bool:
        """
        Associate tag with archive
        
        Args:
            archive_id: Archive ID
            tag_id: Tag ID
            
        Returns:
            True if associated, False otherwise
        """
        try:
            self.db.execute(
                "INSERT OR IGNORE INTO archive_tags (archive_id, tag_id) VALUES (?, ?)",
                (archive_id, tag_id)
            )
            
            # Increment tag count
            self.db.execute(
                "UPDATE tags SET count = count + 1 WHERE id = ?",
                (tag_id,)
            )
            
            self.db.commit()
            return True
            
        except sqlite3.Error as e:
            logger.error(f"Error associating tag: {e}", exc_info=True)
            self.db.rollback()
            return False
    
    def get_archive_tags(self, archive_id: int) -> List[str]:
        """
        Get tags for an archive
        
        Args:
            archive_id: Archive ID
            
        Returns:
            List of tag names
        """
        try:
            cursor = self.db.execute(
                """
                SELECT t.tag_name FROM tags t
                INNER JOIN archive_tags at ON t.id = at.tag_id
                WHERE at.archive_id = ?
                """,
                (archive_id,)
            )
            
            return [row[0] for row in cursor.fetchall()]
            
        except sqlite3.Error as e:
            logger.error(f"Error getting archive tags: {e}", exc_info=True)
            return []
    
    def get_all_tags(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get all tags with counts
        
        Args:
            limit: Maximum number of tags
            
        Returns:
            List of tag dictionaries
        """
        try:
            cursor = self.db.execute(
                "SELECT * FROM tags ORDER BY count DESC, tag_name ASC LIMIT ?",
                (limit,)
            )
            
            return [dict(row) for row in cursor.fetchall()]
            
        except sqlite3.Error as e:
            logger.error(f"Error getting tags: {e}", exc_info=True)
            return []
    
    def get_config(self, key: str) -> Optional[str]:
        """
        Get configuration value
        
        Args:
            key: Configuration key
            
        Returns:
            Configuration value or None
        """
        try:
            cursor = self.db.execute(
                "SELECT value FROM config WHERE key = ?",
                (key,)
            )
            row = cursor.fetchone()
            return row[0] if row else None
            
        except sqlite3.Error as e:
            logger.error(f"Error getting config: {e}", exc_info=True)
            return None
    
    def set_config(self, key: str, value: str, description: Optional[str] = None) -> bool:
        """
        Set configuration value
        
        Args:
            key: Configuration key
            value: Configuration value
            description: Configuration description
            
        Returns:
            True if set, False otherwise
        """
        try:
            now = format_datetime()
            
            self.db.execute(
                """
                INSERT OR REPLACE INTO config (key, value, description, updated_at)
                VALUES (?, ?, ?, ?)
                """,
                (key, value, description, now)
            )
            
            self.db.commit()
            return True
            
        except sqlite3.Error as e:
            logger.error(f"Error setting config: {e}", exc_info=True)
            self.db.rollback()
            return False
