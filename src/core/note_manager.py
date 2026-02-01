"""
Note manager module
Manages notes attached to archives
"""

import logging
import json
from typing import List, Dict, Any, Optional
from datetime import datetime

from ..utils.helpers import format_datetime

logger = logging.getLogger(__name__)


class NoteManager:
    """
    Manages notes for archives
    Supports adding, viewing, and searching notes
    """
    
    def __init__(self, db):
        """
        Initialize note manager
        
        Args:
            db: Database instance
        """
        self.db = db
        logger.info("NoteManager initialized")
    
    def add_note(self, archive_id: Optional[int], content: str, title: Optional[str] = None, storage_path: Optional[str] = None) -> Optional[int]:
        """
        Add a note (with optional archive link)
        
        Args:
            archive_id: Archive ID (None for standalone note)
            content: Note content
            title: Note title (optional)
            storage_path: Telegram channel message link (optional)
            
        Returns:
            Note ID if successful, None otherwise
        """
        try:
            with self.db._lock:
                # Check if archive exists (if provided)
                if archive_id is not None:
                    archive_cursor = self.db.execute(
                        "SELECT id FROM archives WHERE id = ? AND deleted = 0",
                        (archive_id,)
                    )
                    if not archive_cursor.fetchone():
                        logger.warning(f"Archive {archive_id} not found or deleted")
                        return None
                
                # Insert note
                now = format_datetime()
                cursor = self.db.execute(
                    """
                    INSERT INTO notes (archive_id, content, title, storage_path, created_at)
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (archive_id, content, title, storage_path, now)
                )
                
                self.db.commit()
                note_id = cursor.lastrowid
                
                logger.info(f"Note added: id={note_id}, archive_id={archive_id}, title={title}, has_link={bool(storage_path)}")
                return note_id
                
        except Exception as e:
            logger.error(f"Error adding note: {e}", exc_info=True)
            self.db.rollback()
            return None
    
    def get_notes(self, archive_id: int) -> List[Dict[str, Any]]:
        """
        Get all notes for an archive
        
        Args:
            archive_id: Archive ID
            
        Returns:
            List of note dictionaries
        """
        try:
            cursor = self.db.execute(
                """
                SELECT id, archive_id, content, created_at
                FROM notes
                WHERE archive_id = ? AND deleted = 0
                ORDER BY created_at ASC
                """,
                (archive_id,)
            )
            
            notes = [dict(row) for row in cursor.fetchall()]
            logger.debug(f"Retrieved {len(notes)} notes for archive {archive_id}")
            return notes
            
        except Exception as e:
            logger.error(f"Error getting notes: {e}", exc_info=True)
            return []
    
    def get_notes_count(self) -> int:
        """
        Get total count of non-deleted notes
        
        Returns:
            Total number of notes
        """
        try:
            cursor = self.db.execute(
                "SELECT COUNT(*) as count FROM notes WHERE deleted = 0"
            )
            result = cursor.fetchone()
            count = result['count'] if result else 0
            logger.debug(f"Total notes count: {count}")
            return count
        except Exception as e:
            logger.error(f"Error getting notes count: {e}", exc_info=True)
            return 0
    
    def get_all_notes(self, limit: int = 20, offset: int = 0, include_archive_info: bool = True) -> List[Dict[str, Any]]:
        """
        Get all notes (with pagination)
        
        Args:
            limit: Maximum results
            offset: Offset for pagination
            include_archive_info: Whether to include archive info (default True)
            
        Returns:
            List of note dictionaries
        """
        try:
            # 优化：只在需要时才JOIN，减少数据库开销
            if include_archive_info:
                cursor = self.db.execute(
                    """
                    SELECT 
                        n.id, n.archive_id, n.content, n.title, n.storage_path, n.created_at,
                        a.title as archive_title, 
                        a.storage_type, 
                        a.storage_path as archive_storage_path
                    FROM notes n
                    LEFT JOIN archives a ON n.archive_id = a.id
                    WHERE n.deleted = 0
                    ORDER BY n.created_at DESC
                    LIMIT ? OFFSET ?
                    """,
                    (limit, offset)
                )
            else:
                cursor = self.db.execute(
                    """
                    SELECT id, archive_id, content, title, storage_path, created_at
                    FROM notes
                    WHERE deleted = 0
                    ORDER BY created_at DESC
                    LIMIT ? OFFSET ?
                    """,
                    (limit, offset)
                )
            
            notes = [dict(row) for row in cursor.fetchall()]
            logger.debug(f"Retrieved {len(notes)} notes (offset={offset}, with_info={include_archive_info})")
            return notes
            
        except Exception as e:
            logger.error(f"Error getting all notes: {e}", exc_info=True)
            return []
    
    def get_note(self, note_id: int) -> Optional[Dict[str, Any]]:
        """
        Get a single note by ID
        
        Args:
            note_id: Note ID
            
        Returns:
            Note dictionary or None
        """
        try:
            cursor = self.db.execute(
                """
                SELECT id, archive_id, content, created_at
                FROM notes
                WHERE id = ? AND deleted = 0
                """,
                (note_id,)
            )
            
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None
            
        except Exception as e:
            logger.error(f"Error getting note: {e}", exc_info=True)
            return None
    
    def update_note(self, note_id: int, content: str) -> bool:
        """
        Update a note's content
        
        Args:
            note_id: Note ID
            content: New content
            
        Returns:
            True if successful
        """
        try:
            with self.db._lock:
                cursor = self.db.execute(
                    """
                    UPDATE notes
                    SET content = ?
                    WHERE id = ?
                    """,
                    (content, note_id)
                )
                
                self.db.commit()
                
                if cursor.rowcount > 0:
                    logger.info(f"Note updated: id={note_id}")
                    return True
                else:
                    logger.warning(f"Note {note_id} not found")
                    return False
                    
        except Exception as e:
            logger.error(f"Error updating note: {e}", exc_info=True)
            self.db.rollback()
            return False
    
    def delete_note(self, note_id: int) -> bool:
        """
        Delete a note (soft delete)
        
        Args:
            note_id: Note ID
            
        Returns:
            True if successful
        """
        try:
            with self.db._lock:
                # Mark as deleted
                now = format_datetime()
                cursor = self.db.execute(
                    "UPDATE notes SET deleted = 1, deleted_at = ? WHERE id = ? AND deleted = 0",
                    (now, note_id)
                )
                
                self.db.commit()
                
                if cursor.rowcount > 0:
                    logger.info(f"Note soft deleted: id={note_id}")
                    return True
                else:
                    logger.warning(f"Note {note_id} not found or already deleted")
                    return False
                    
        except Exception as e:
            logger.error(f"Error deleting note: {e}", exc_info=True)
            self.db.rollback()
            return False
    
    def search_notes(self, keyword: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search notes by keyword using FTS5
        
        Args:
            keyword: Search keyword
            limit: Maximum results
            
        Returns:
            List of note dictionaries with archive info
        """
        try:
            # Escape FTS5 special characters
            fts_keyword = keyword.replace('"', '""')
            
            cursor = self.db.execute(
                """
                SELECT n.id, n.archive_id, n.content, n.created_at,
                       a.title as archive_title, a.content_type
                FROM notes_fts nf
                INNER JOIN notes n ON nf.rowid = n.id
                INNER JOIN archives a ON n.archive_id = a.id
                WHERE notes_fts MATCH ? AND a.deleted = 0
                ORDER BY rank
                LIMIT ?
                """,
                (fts_keyword, limit)
            )
            
            results = [dict(row) for row in cursor.fetchall()]
            logger.info(f"Note search found {len(results)} results for '{keyword}'")
            return results
            
        except Exception as e:
            logger.error(f"Error searching notes: {e}", exc_info=True)
            # Fallback to LIKE search
            try:
                escaped_keyword = keyword.replace('%', '\\%').replace('_', '\\_')
                cursor = self.db.execute(
                    """
                    SELECT n.id, n.archive_id, n.content, n.created_at,
                           a.title as archive_title, a.content_type
                    FROM notes n
                    INNER JOIN archives a ON n.archive_id = a.id
                    WHERE n.content LIKE ? ESCAPE '\\' AND a.deleted = 0
                    ORDER BY n.created_at DESC
                    LIMIT ?
                    """,
                    (f"%{escaped_keyword}%", limit)
                )
                return [dict(row) for row in cursor.fetchall()]
            except Exception as e2:
                logger.error(f"Fallback search also failed: {e2}", exc_info=True)
                return []
    
    def get_note_count(self, archive_id: int) -> int:
        """
        Get count of notes for an archive
        
        Args:
            archive_id: Archive ID
            
        Returns:
            Note count
        """
        try:
            cursor = self.db.execute(
                "SELECT COUNT(*) FROM notes WHERE archive_id = ? AND deleted = 0",
                (archive_id,)
            )
            return cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"Error getting note count: {e}", exc_info=True)
            return 0
    
    def get_archives_with_notes(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Get archives that have notes
        
        Args:
            limit: Maximum results
            
        Returns:
            List of archive dictionaries with note count
        """
        try:
            cursor = self.db.execute(
                """
                SELECT a.id, a.title, a.content_type, a.archived_at,
                       COUNT(n.id) as note_count
                FROM archives a
                INNER JOIN notes n ON a.id = n.archive_id
                WHERE a.deleted = 0 AND n.deleted = 0
                GROUP BY a.id
                ORDER BY MAX(n.created_at) DESC
                LIMIT ?
                """,
                (limit,)
            )
            
            results = [dict(row) for row in cursor.fetchall()]
            logger.debug(f"Found {len(results)} archives with notes")
            return results
            
        except Exception as e:
            logger.error(f"Error getting archives with notes: {e}", exc_info=True)
            return []
