"""
Trash manager module
Manages deleted archives (soft delete)
"""

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta

from ..utils.helpers import format_datetime

logger = logging.getLogger(__name__)


class TrashManager:
    """
    Manages trash bin for deleted archives
    Supports viewing, restoring, and permanently deleting archives
    """
    
    def __init__(self, db, telegram_storage=None):
        """
        Initialize trash manager
        
        Args:
            db: Database instance
            telegram_storage: TelegramStorage instance (optional, for deleting channel messages)
        """
        self.db = db
        self.telegram_storage = telegram_storage
        self.ai_cache = None  # Will be set by main.py
        logger.info("TrashManager initialized")
    
    def set_ai_cache(self, ai_cache):
        """Set AI data cache instance"""
        self.ai_cache = ai_cache
    
    def _invalidate_ai_cache(self):
        """失效AI数据缓存"""
        if self.ai_cache:
            self.ai_cache.invalidate('statistics', 'recent_samples')
            logger.debug("AI cache invalidated (trash operation)")
    
    def _delete_channel_messages(self, storage_path: str, featured_message_id: Optional[str] = None):
        """
        Delete messages from Telegram channels (main and featured)
        
        Args:
            storage_path: Storage path of main channel message
            featured_message_id: Storage path of featured channel message (optional)
        """
        import asyncio
        
        if not self.telegram_storage:
            logger.debug("No telegram_storage configured, skipping channel message deletion")
            return
        
        try:
            # Create event loop if needed
            try:
                loop = asyncio.get_event_loop()
            except RuntimeError:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
            
            # Delete main channel message
            if storage_path:
                try:
                    loop.run_until_complete(self.telegram_storage.delete_message(storage_path))
                    logger.info(f"Deleted main channel message: {storage_path}")
                except Exception as e:
                    logger.warning(f"Failed to delete main channel message {storage_path}: {e}")
            
            # Delete featured channel message if exists
            if featured_message_id:
                try:
                    loop.run_until_complete(self.telegram_storage.delete_message(featured_message_id))
                    logger.info(f"Deleted featured channel message: {featured_message_id}")
                except Exception as e:
                    logger.warning(f"Failed to delete featured channel message {featured_message_id}: {e}")
                    
        except Exception as e:
            logger.error(f"Error deleting channel messages: {e}", exc_info=True)
    
    def move_to_trash(self, archive_id: int) -> bool:
        """
        Move an archive to trash (soft delete)
        
        Args:
            archive_id: Archive ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self.db._lock:
                # Check if archive exists and not already deleted
                cursor = self.db.execute(
                    "SELECT id FROM archives WHERE id = ? AND deleted = 0",
                    (archive_id,)
                )
                if not cursor.fetchone():
                    logger.warning(f"Archive {archive_id} not found or already deleted")
                    return False
                
                # Mark as deleted
                now = format_datetime()
                self.db.execute(
                    "UPDATE archives SET deleted = 1, deleted_at = ? WHERE id = ?",
                    (now, archive_id)
                )
                self.db.commit()
                
                # 触发AI缓存失效
                self._invalidate_ai_cache()
                
                logger.info(f"Archive {archive_id} moved to trash")
                return True
                
        except Exception as e:
            logger.error(f"Error moving archive to trash: {e}", exc_info=True)
            return False
    
    def restore_archive(self, archive_id: int) -> bool:
        """
        Restore an archive from trash
        
        Args:
            archive_id: Archive ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self.db._lock:
                # Check if archive exists and is deleted
                cursor = self.db.execute(
                    "SELECT id FROM archives WHERE id = ? AND deleted = 1",
                    (archive_id,)
                )
                if not cursor.fetchone():
                    logger.warning(f"Archive {archive_id} not found in trash")
                    return False
                
                # Restore archive
                self.db.execute(
                    "UPDATE archives SET deleted = 0, deleted_at = NULL WHERE id = ?",
                    (archive_id,)
                )
                self.db.commit()
                
                # 触发AI缓存失效
                self._invalidate_ai_cache()
                
                logger.info(f"Archive {archive_id} restored from trash")
                return True
                
        except Exception as e:
            logger.error(f"Error restoring archive: {e}", exc_info=True)
            return False
    
    def delete_permanently(self, archive_id: int) -> bool:
        """
        Permanently delete an archive from trash
        
        Args:
            archive_id: Archive ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self.db._lock:
                # Check if archive exists and is deleted
                cursor = self.db.execute(
                    "SELECT id, storage_path, featured_channel_message_id FROM archives WHERE id = ? AND deleted = 1",
                    (archive_id,)
                )
                row = cursor.fetchone()
                if not row:
                    logger.warning(f"Archive {archive_id} not found in trash")
                    return False
                
                storage_path = row[1] if len(row) > 1 else None
                featured_message_id = row[2] if len(row) > 2 else None
                
                # Delete channel messages if storage is telegram
                if storage_path:
                    self._delete_channel_messages(storage_path, featured_message_id)
                
                # Delete associated notes first
                self.db.execute(
                    "DELETE FROM notes WHERE archive_id = ?",
                    (archive_id,)
                )
                
                # Delete archive
                self.db.execute(
                    "DELETE FROM archives WHERE id = ?",
                    (archive_id,)
                )
                self.db.commit()
                
                logger.info(f"Archive {archive_id} permanently deleted")
                return True
                
        except Exception as e:
            logger.error(f"Error permanently deleting archive: {e}", exc_info=True)
            return False
    
    def list_trash(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        List all archives in trash
        
        Args:
            limit: Maximum number of results
            
        Returns:
            List of deleted archives
        """
        try:
            with self.db._lock:
                cursor = self.db.execute(
                    """
                    SELECT 
                        id, title, content_type, 
                        deleted_at, created_at
                    FROM archives
                    WHERE deleted = 1
                    ORDER BY deleted_at DESC
                    LIMIT ?
                    """,
                    (limit,)
                )
                
                results = []
                for row in cursor.fetchall():
                    archive_id = row[0]
                    # 通过tag_manager获取标签
                    tags = self.tag_manager.get_archive_tags(archive_id) if self.tag_manager else []
                    
                    results.append({
                        'id': archive_id,
                        'title': row[1],
                        'content_type': row[2],
                        'tags': tags,
                        'deleted_at': row[3],
                        'created_at': row[4]
                    })
                
                logger.info(f"Listed {len(results)} items in trash")
                return results
                
        except Exception as e:
            logger.error(f"Error listing trash: {e}", exc_info=True)
            return []
    
    def empty_trash(self, days_old: Optional[int] = None) -> int:
        """
        Empty trash (permanently delete all items)
        
        Args:
            days_old: Only delete items older than this many days (optional)
            
        Returns:
            Number of archives permanently deleted
        """
        try:
            with self.db._lock:
                if days_old:
                    # Calculate cutoff date
                    from datetime import timedelta
                    cutoff_date = datetime.now() - timedelta(days=days_old)
                    cutoff_str = cutoff_date.strftime('%Y-%m-%d %H:%M:%S')
                    
                    # Get archives to delete
                    cursor = self.db.execute(
                        "SELECT id FROM archives WHERE deleted = 1 AND deleted_at <= ?",
                        (cutoff_str,)
                    )
                else:
                    # Get all deleted archives
                    cursor = self.db.execute(
                        "SELECT id FROM archives WHERE deleted = 1"
                    )
                
                archive_ids = [row[0] for row in cursor.fetchall()]
                
                if not archive_ids:
                    logger.info("No archives to delete in trash")
                    return 0
                
                # Delete associated notes
                placeholders = ','.join('?' * len(archive_ids))
                self.db.execute(
                    f"DELETE FROM notes WHERE archive_id IN ({placeholders})",
                    archive_ids
                )
                
                # Delete archives
                self.db.execute(
                    f"DELETE FROM archives WHERE id IN ({placeholders})",
                    archive_ids
                )
                self.db.commit()
                
                count = len(archive_ids)
                logger.info(f"Emptied trash: {count} archives permanently deleted")
                return count
                
        except Exception as e:
            logger.error(f"Error emptying trash: {e}", exc_info=True)
            return 0
    
    def get_trash_count(self) -> int:
        """
        Get count of archives in trash
        
        Returns:
            Number of deleted archives
        """
        try:
            with self.db._lock:
                cursor = self.db.execute(
                    "SELECT COUNT(*) FROM archives WHERE deleted = 1"
                )
                count = cursor.fetchone()[0]
                return count
                
        except Exception as e:
            logger.error(f"Error getting trash count: {e}", exc_info=True)
            return 0
    
    def get_archive_info(self, archive_id: int) -> Optional[Dict[str, Any]]:
        """
        Get detailed info about a deleted archive
        
        Args:
            archive_id: Archive ID
            
        Returns:
            Archive info dict or None
        """
        try:
            with self.db._lock:
                cursor = self.db.execute(
                    """
                    SELECT 
                        id, title, content, content_type, tags,
                        file_name, file_size, storage_type,
                        deleted_at, created_at
                    FROM archives
                    WHERE id = ? AND deleted = 1
                    """,
                    (archive_id,)
                )
                
                row = cursor.fetchone()
                if not row:
                    return None
                
                return {
                    'id': row[0],
                    'title': row[1],
                    'content': row[2],
                    'content_type': row[3],
                    'tags': row[4].split(',') if row[4] else [],
                    'file_name': row[5],
                    'file_size': row[6],
                    'storage_type': row[7],
                    'deleted_at': row[8],
                    'created_at': row[9]
                }
                
        except Exception as e:
            logger.error(f"Error getting archive info: {e}", exc_info=True)
            return None
    
    # ==================== Note Trash Management ====================
    
    def restore_note(self, note_id: int) -> bool:
        """
        Restore a note from trash
        
        Args:
            note_id: Note ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self.db._lock:
                # Check if note exists and is deleted
                cursor = self.db.execute(
                    "SELECT id FROM notes WHERE id = ? AND deleted = 1",
                    (note_id,)
                )
                if not cursor.fetchone():
                    logger.warning(f"Note {note_id} not found in trash")
                    return False
                
                # Restore note
                self.db.execute(
                    "UPDATE notes SET deleted = 0, deleted_at = NULL WHERE id = ?",
                    (note_id,)
                )
                self.db.commit()
                
                logger.info(f"Note {note_id} restored from trash")
                return True
                
        except Exception as e:
            logger.error(f"Error restoring note: {e}", exc_info=True)
            return False
    
    def delete_note_permanently(self, note_id: int) -> bool:
        """
        Permanently delete a note from trash
        
        Args:
            note_id: Note ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with self.db._lock:
                # Check if note exists and is deleted
                cursor = self.db.execute(
                    "SELECT id FROM notes WHERE id = ? AND deleted = 1",
                    (note_id,)
                )
                if not cursor.fetchone():
                    logger.warning(f"Note {note_id} not found in trash")
                    return False
                
                # Permanently delete
                self.db.execute(
                    "DELETE FROM notes WHERE id = ?",
                    (note_id,)
                )
                self.db.commit()
                
                logger.info(f"Note {note_id} permanently deleted")
                return True
                
        except Exception as e:
            logger.error(f"Error permanently deleting note: {e}", exc_info=True)
            return False
    
    def get_deleted_notes(self, limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
        """
        Get all deleted notes in trash
        
        Args:
            limit: Maximum results
            offset: Offset for pagination
            
        Returns:
            List of deleted note dictionaries
        """
        try:
            with self.db._lock:
                cursor = self.db.execute(
                    """
                    SELECT 
                        n.id, n.archive_id, n.content, n.title,
                        n.created_at, n.deleted_at,
                        a.title as archive_title
                    FROM notes n
                    LEFT JOIN archives a ON n.archive_id = a.id
                    WHERE n.deleted = 1
                    ORDER BY n.deleted_at DESC
                    LIMIT ? OFFSET ?
                    """,
                    (limit, offset)
                )
                
                notes = [dict(row) for row in cursor.fetchall()]
                logger.debug(f"Retrieved {len(notes)} deleted notes from trash")
                return notes
                
        except Exception as e:
            logger.error(f"Error getting deleted notes: {e}", exc_info=True)
            return []
    
    def get_deleted_notes_count(self) -> int:
        """
        Get count of deleted notes in trash
        
        Returns:
            Number of deleted notes
        """
        try:
            with self.db._lock:
                cursor = self.db.execute(
                    "SELECT COUNT(*) FROM notes WHERE deleted = 1"
                )
                return cursor.fetchone()[0]
                
        except Exception as e:
            logger.error(f"Error getting deleted notes count: {e}", exc_info=True)
            return 0
    
    def empty_notes_trash(self, days: Optional[int] = None) -> int:
        """
        Permanently delete all notes in trash (optionally older than N days)
        
        Args:
            days: Only delete notes older than N days (None = all)
            
        Returns:
            Number of notes deleted
        """
        try:
            with self.db._lock:
                if days:
                    # Calculate cutoff date
                    cutoff_date = datetime.now() - timedelta(days=days)
                    cutoff_str = format_datetime(cutoff_date)
                    
                    # Get note IDs to delete
                    cursor = self.db.execute(
                        "SELECT id FROM notes WHERE deleted = 1 AND deleted_at <= ?",
                        (cutoff_str,)
                    )
                else:
                    # Get all deleted note IDs
                    cursor = self.db.execute(
                        "SELECT id FROM notes WHERE deleted = 1"
                    )
                
                note_ids = [row[0] for row in cursor.fetchall()]
                
                if not note_ids:
                    return 0
                
                # Delete notes
                placeholders = ','.join('?' * len(note_ids))
                self.db.execute(
                    f"DELETE FROM notes WHERE id IN ({placeholders})",
                    note_ids
                )
                
                self.db.commit()
                
                logger.info(f"Permanently deleted {len(note_ids)} notes from trash")
                return len(note_ids)
                
        except Exception as e:
            logger.error(f"Error emptying notes trash: {e}", exc_info=True)
            return 0
