"""
Database storage implementation
Handles database operations for archives, tags, and config
"""

from __future__ import annotations

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
        source: Optional[str] = None,
        ai_summary: Optional[str] = None,
        ai_key_points: Optional[List[str]] = None,
        ai_category: Optional[str] = None,
        media_group_id: Optional[str] = None
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
            ai_summary: AI generated summary
            ai_key_points: AI extracted key points
            ai_category: AI categorization
            media_group_id: Telegram media group ID (for grouping related media)
            
        Returns:
            Archive ID
        """
        with self.db._lock:
            try:
                now = format_datetime()
                metadata_json = json.dumps(metadata, ensure_ascii=False) if metadata else None
                ai_key_points_json = json.dumps(ai_key_points, ensure_ascii=False) if ai_key_points else None
                
                cursor = self.db.execute(
                    """
                    INSERT INTO archives (
                        content_type, title, content, file_id,
                        storage_type, storage_provider, storage_path,
                        file_size, metadata, source,
                        created_at, archived_at,
                        ai_summary, ai_key_points, ai_category, media_group_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        content_type, title, content, file_id,
                        storage_type, storage_provider, storage_path,
                        file_size, metadata_json, source,
                        now, now,
                        ai_summary, ai_key_points_json, ai_category, media_group_id
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
    
    def get_random_archive(self, exclude_deleted: bool = True, content_type: Optional[str] = None) -> Optional[Dict[str, Any]]:
        """Get a random archive for review use cases"""
        try:
            where_clauses = ["1=1"]
            params: List[Any] = []

            if exclude_deleted:
                where_clauses.append("(deleted IS NULL OR deleted = 0)")

            if content_type:
                where_clauses.append("content_type = ?")
                params.append(content_type)

            query = f"SELECT * FROM archives WHERE {' AND '.join(where_clauses)} ORDER BY RANDOM() LIMIT 1"
            cursor = self.db.execute(query, tuple(params))
            row = cursor.fetchone()
            return dict(row) if row else None
        except sqlite3.Error as e:
            logger.error(f"Error getting random archive: {e}", exc_info=True)
            return None
    
    def find_duplicate_file(
        self,
        file_id: Optional[str] = None,
        file_name: Optional[str] = None,
        file_size: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        """
        Check if a file already exists in archives
        
        Args:
            file_id: Telegram file_id (most reliable)
            file_name: File name
            file_size: File size in bytes
            
        Returns:
            Existing archive dictionary or None
        """
        try:
            # 优先使用file_id查询（最可靠）
            if file_id:
                cursor = self.db.execute(
                    "SELECT * FROM archives WHERE file_id = ? ORDER BY archived_at DESC LIMIT 1",
                    (file_id,)
                )
                row = cursor.fetchone()
                if row:
                    return dict(row)
            
            # 如果没有file_id，使用文件名+大小组合查询
            if file_name and file_size:
                cursor = self.db.execute(
                    """
                    SELECT * FROM archives 
                    WHERE title = ? AND file_size = ? 
                    ORDER BY archived_at DESC LIMIT 1
                    """,
                    (file_name, file_size)
                )
                row = cursor.fetchone()
                if row:
                    return dict(row)
            
            return None
            
        except sqlite3.Error as e:
            logger.error(f"Error finding duplicate file: {e}", exc_info=True)
            return None
    
    def search_archives(
        self,
        keyword: Optional[str] = None,
        content_type: Optional[str] = None,
        tag_names: Optional[List[str]] = None,
        limit: int = 10,
        offset: int = 0,
        return_total: bool = False
    ) -> List[Dict[str, Any]] | tuple[List[Dict[str, Any]], int]:
        """
        Search archives with filters
        增强搜索：支持标题、内容、标签、AI摘要、AI分类的全文搜索
        
        Args:
            keyword: Search keyword (searches in title, content, tags, AI summary, and AI category)
            content_type: Filter by content type
            tag_names: Filter by tag names
            limit: Maximum results
            offset: Results offset for pagination
            return_total: If True, return tuple of (results, total_count)
            
        Returns:
            List of archive dictionaries, or tuple of (results, total_count) if return_total is True
        """
        try:
            # 如果有关键词，使用FTS5全文搜索获取匹配的archive_id
            fts_archive_ids = []
            tag_matched_ids = []
            
            if keyword:
                # 1. 使用FTS5搜索标题和内容
                try:
                    # 转义FTS5特殊字符
                    fts_keyword = keyword.replace('"', '""')
                    fts_cursor = self.db.execute(
                        """
                        SELECT rowid FROM archives_fts 
                        WHERE archives_fts MATCH ?
                        ORDER BY rank
                        """,
                        (fts_keyword,)
                    )
                    fts_archive_ids = [row[0] for row in fts_cursor.fetchall()]
                    logger.debug(f"FTS5 matched {len(fts_archive_ids)} archives")
                except sqlite3.Error as e:
                    logger.warning(f"FTS5 search failed, fallback to LIKE: {e}")
                    # FTS5失败时降级到LIKE搜索
                    fts_archive_ids = []
                
                # 2. 搜索标签（关键词匹配标签名）
                try:
                    escaped_keyword = keyword.replace('%', '\\%').replace('_', '\\_')
                    tag_cursor = self.db.execute(
                        """
                        SELECT DISTINCT at.archive_id 
                        FROM archive_tags at
                        INNER JOIN tags t ON at.tag_id = t.id
                        WHERE t.tag_name LIKE ? ESCAPE '\\'
                        """,
                        (f"%{escaped_keyword}%",)
                    )
                    tag_matched_ids = [row[0] for row in tag_cursor.fetchall()]
                    logger.debug(f"Tag search matched {len(tag_matched_ids)} archives")
                except sqlite3.Error as e:
                    logger.warning(f"Tag search failed: {e}")
            
            # 构建主查询
            query_parts = ["SELECT DISTINCT a.* FROM archives a"]
            params = []
            where_clauses = []
            
            # 如果有FTS或标签匹配结果，限制在这些ID内
            if fts_archive_ids or tag_matched_ids:
                combined_ids = list(set(fts_archive_ids + tag_matched_ids))
                if combined_ids:
                    id_placeholders = ','.join('?' * len(combined_ids))
                    where_clauses.append(f"a.id IN ({id_placeholders})")
                    params.extend(combined_ids)
                else:
                    # 没有匹配结果
                    if return_total:
                        return [], 0
                    return []
            elif keyword:
                # FTS和标签都没有结果，使用LIKE作为后备
                escaped_keyword = keyword.replace('%', '\\%').replace('_', '\\_')
                where_clauses.append("(a.title LIKE ? ESCAPE '\\' OR a.content LIKE ? ESCAPE '\\')")
                params.extend([f"%{escaped_keyword}%", f"%{escaped_keyword}%"])
            
            # Join with tags if tag filter is specified
            if tag_names:
                query_parts.append("""
                    INNER JOIN archive_tags at ON a.id = at.archive_id
                    INNER JOIN tags t ON at.tag_id = t.id
                """)
                tag_placeholders = ','.join('?' * len(tag_names))
                where_clauses.append(f"t.tag_name IN ({tag_placeholders})")
                params.extend(tag_names)
            
            # Content type filter
            if content_type:
                where_clauses.append("a.content_type = ?")
                params.append(content_type)
            
            # Build WHERE clause
            if where_clauses:
                query_parts.append("WHERE " + " AND ".join(where_clauses))
            
            # Get total count if requested (before adding ORDER/LIMIT)
            total_count = 0
            if return_total:
                count_query_parts = query_parts.copy()
                count_query = " ".join(count_query_parts)
                count_query = count_query.replace("SELECT DISTINCT a.*", "SELECT COUNT(DISTINCT a.id)")
                count_cursor = self.db.execute(count_query, tuple(params))
                total_count = count_cursor.fetchone()[0]
            
            # Order and limit
            query_parts.append("ORDER BY a.archived_at DESC LIMIT ? OFFSET ?")
            params.extend([limit, offset])
            
            query = " ".join(query_parts)
            
            cursor = self.db.execute(query, tuple(params))
            results = [dict(row) for row in cursor.fetchall()]
            
            logger.debug(f"Search found {len(results)} results")
            
            if return_total:
                return results, total_count
            return results
            
        except sqlite3.Error as e:
            logger.error(f"Error searching archives: {e}", exc_info=True)
            if return_total:
                return [], 0
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

    def remove_tag_from_archives(self, tag_name: str, archive_ids: Optional[List[int]] = None) -> int:
        """Remove a tag from specified archives"""
        try:
            with self.db._lock:
                cursor = self.db.execute("SELECT id FROM tags WHERE tag_name = ?", (tag_name,))
                row = cursor.fetchone()
                if not row:
                    return 0
                tag_id = row[0]

                where_clause = ""
                params: List[Any] = [tag_id]
                if archive_ids:
                    placeholders = ",".join(["?"] * len(archive_ids))
                    where_clause = f"AND archive_id IN ({placeholders})"
                    params.extend(archive_ids)

                cursor = self.db.execute(
                    f"SELECT COUNT(*) FROM archive_tags WHERE tag_id = ? {where_clause}",
                    tuple(params)
                )
                remove_count = cursor.fetchone()[0]
                if remove_count == 0:
                    return 0

                self.db.execute(
                    f"DELETE FROM archive_tags WHERE tag_id = ? {where_clause}",
                    tuple(params)
                )

                self.db.execute(
                    "UPDATE tags SET count = MAX(count - ?, 0) WHERE id = ?",
                    (remove_count, tag_id)
                )
                self.db.commit()
                return remove_count
        except sqlite3.Error as e:
            logger.error(f"Error removing tag '{tag_name}': {e}", exc_info=True)
            self.db.rollback()
            return 0

    def replace_tag_in_archives(self, old_tag: str, new_tag: str, archive_ids: Optional[List[int]] = None) -> int:
        """Replace a tag with another across archives"""
        try:
            with self.db._lock:
                cursor = self.db.execute("SELECT id FROM tags WHERE tag_name = ?", (old_tag,))
                row = cursor.fetchone()
                if not row:
                    return 0
                old_tag_id = row[0]

                new_tag_id = self.get_or_create_tag(new_tag, tag_type='manual')

                where_clause = ""
                params: List[Any] = [old_tag_id]
                if archive_ids:
                    placeholders = ",".join(["?"] * len(archive_ids))
                    where_clause = f"AND archive_id IN ({placeholders})"
                    params.extend(archive_ids)

                cursor = self.db.execute(
                    f"SELECT archive_id FROM archive_tags WHERE tag_id = ? {where_clause}",
                    tuple(params)
                )
                archive_list = [row[0] for row in cursor.fetchall()]
                if not archive_list:
                    return 0

                inserted = 0
                for aid in archive_list:
                    try:
                        self.db.execute(
                            "INSERT OR IGNORE INTO archive_tags (archive_id, tag_id) VALUES (?, ?)",
                            (aid, new_tag_id)
                        )
                        inserted += 1
                    except sqlite3.Error:
                        pass

                # Remove old relations
                self.db.execute(
                    f"DELETE FROM archive_tags WHERE tag_id = ? {where_clause}",
                    tuple(params)
                )

                self.db.execute(
                    "UPDATE tags SET count = MAX(count - ?, 0) WHERE id = ?",
                    (len(archive_list), old_tag_id)
                )
                self.db.execute(
                    "UPDATE tags SET count = count + ? WHERE id = ?",
                    (inserted, new_tag_id)
                )

                self.db.commit()
                return inserted
        except sqlite3.Error as e:
            logger.error(f"Error replacing tag '{old_tag}'->'{new_tag}': {e}", exc_info=True)
            self.db.rollback()
            return 0
    
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

    def get_activity_summary(self, days: int = 7) -> Dict[str, Any]:
        """
        Get activity summary for recent days
        
        Args:
            days: Number of days to look back
            
        Returns:
            Dictionary with activity statistics
        """
        return self.db.get_activity_summary(days)
