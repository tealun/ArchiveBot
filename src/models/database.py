"""
Database models and initialization
Single-user design - no user_id field required
"""

import sqlite3
import logging
import threading
from pathlib import Path
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class Database:
    """
    SQLite database manager for ArchiveBot
    Manages archives, tags, and configuration
    """
    
    def __init__(self, db_path: str):
        """
        Initialize database connection
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.conn: Optional[sqlite3.Connection] = None
        self._lock = threading.RLock()  # Thread-safe lock
        self.connect()
        self.initialize()
    
    def connect(self) -> None:
        """Establish database connection"""
        try:
            self.conn = sqlite3.connect(
                self.db_path,
                timeout=30.0,
                isolation_level='DEFERRED'
            )
            self.conn.row_factory = sqlite3.Row  # Access columns by name
            self.conn.execute("PRAGMA foreign_keys = ON")  # Enable foreign keys
            self.conn.execute("PRAGMA journal_mode = WAL")  # Write-Ahead Logging for better concurrency
            logger.info(f"Connected to database: {self.db_path}")
        except sqlite3.Error as e:
            logger.error(f"Database connection error: {e}", exc_info=True)
            raise
    
    def close(self) -> None:
        """Close database connection"""
        if self.conn:
            self.conn.close()
            logger.info("Database connection closed")
    
    def initialize(self) -> None:
        """Create database tables if they don't exist"""
        try:
            cursor = self.conn.cursor()
            
            # Archives table - stores all archived content
            # Note: NO user_id field (single-user design)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS archives (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    content_type TEXT NOT NULL,
                    title TEXT,
                    content TEXT,
                    file_id TEXT,
                    storage_type TEXT NOT NULL,
                    storage_provider TEXT,
                    storage_path TEXT,
                    file_size INTEGER,
                    metadata TEXT,
                    source TEXT,
                    favorite INTEGER DEFAULT 0,
                    deleted INTEGER DEFAULT 0,
                    deleted_at TEXT,
                    created_at TEXT NOT NULL,
                    archived_at TEXT NOT NULL
                )
            """)
            
            # Tags table - stores unique tags
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tag_name TEXT NOT NULL UNIQUE,
                    tag_type TEXT NOT NULL,
                    parent_tag_id INTEGER,
                    count INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (parent_tag_id) REFERENCES tags (id) ON DELETE SET NULL
                )
            """)
            
            # Archive-Tags association table (many-to-many)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS archive_tags (
                    archive_id INTEGER NOT NULL,
                    tag_id INTEGER NOT NULL,
                    PRIMARY KEY (archive_id, tag_id),
                    FOREIGN KEY (archive_id) REFERENCES archives (id) ON DELETE CASCADE,
                    FOREIGN KEY (tag_id) REFERENCES tags (id) ON DELETE CASCADE
                )
            """)
            
            # Config table - stores global configuration
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS config (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    description TEXT,
                    updated_at TEXT NOT NULL
                )
            """)
            
            # Notes table - stores notes (can be standalone or attached to archives)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    archive_id INTEGER,
                    content TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (archive_id) REFERENCES archives (id) ON DELETE CASCADE
                )
            """)

            # Add soft delete columns if missing (for existing databases)
            try:
                cursor.execute("ALTER TABLE archives ADD COLUMN deleted INTEGER DEFAULT 0")
            except sqlite3.OperationalError:
                pass
            try:
                cursor.execute("ALTER TABLE archives ADD COLUMN deleted_at TEXT")
            except sqlite3.OperationalError:
                pass
            
            # Add favorite column if missing (for existing databases)
            try:
                cursor.execute("ALTER TABLE archives ADD COLUMN favorite INTEGER DEFAULT 0")
            except sqlite3.OperationalError:
                pass
            
            # Add featured_channel_message_id column if missing (for featured channel sync)
            try:
                cursor.execute("ALTER TABLE archives ADD COLUMN featured_channel_message_id TEXT")
                logger.info("Added featured_channel_message_id column to archives table")
            except sqlite3.OperationalError:
                pass
            
            # Add storage_path column to notes if missing (for channel message link)
            try:
                cursor.execute("ALTER TABLE notes ADD COLUMN storage_path TEXT")
                logger.info("Added storage_path column to notes table")
            except sqlite3.OperationalError:
                pass
            
            # Add title column to notes if missing (for AI-generated titles)
            try:
                cursor.execute("ALTER TABLE notes ADD COLUMN title TEXT")
                logger.info("Added title column to notes table")
            except sqlite3.OperationalError:
                pass
            
            # Add soft delete columns to notes if missing (for trash functionality)
            try:
                cursor.execute("ALTER TABLE notes ADD COLUMN deleted INTEGER DEFAULT 0")
                logger.info("Added deleted column to notes table")
            except sqlite3.OperationalError:
                pass
            
            try:
                cursor.execute("ALTER TABLE notes ADD COLUMN deleted_at TEXT")
                logger.info("Added deleted_at column to notes table")
            except sqlite3.OperationalError:
                pass
            
            # Add favorite column to notes if missing (for note favorites)
            try:
                cursor.execute("ALTER TABLE notes ADD COLUMN favorite INTEGER DEFAULT 0")
                logger.info("Added favorite column to notes table")
            except sqlite3.OperationalError:
                pass
            
            # Add featured_channel_message_id to notes if missing (for featured channel sync)
            try:
                cursor.execute("ALTER TABLE notes ADD COLUMN featured_channel_message_id TEXT")
                logger.info("Added featured_channel_message_id column to notes table")
            except sqlite3.OperationalError:
                pass
            
            # Add media_group_id column to archives if missing (for grouping media messages)
            try:
                cursor.execute("ALTER TABLE archives ADD COLUMN media_group_id TEXT")
                logger.info("Added media_group_id column to archives table")
            except sqlite3.OperationalError:
                pass
            
            # Migrate notes table to allow NULL archive_id (for standalone notes)
            # Check if migration is needed
            cursor.execute("PRAGMA table_info(notes)")
            columns = cursor.fetchall()
            archive_id_col = next((col for col in columns if col[1] == 'archive_id'), None)
            
            if archive_id_col and archive_id_col[3] == 1:  # notnull = 1
                logger.info("Migrating notes table to support standalone notes...")
                try:
                    # Create new table with correct schema
                    cursor.execute("""
                        CREATE TABLE notes_new (
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            archive_id INTEGER,
                            content TEXT NOT NULL,
                            created_at TEXT NOT NULL,
                            FOREIGN KEY (archive_id) REFERENCES archives (id) ON DELETE CASCADE
                        )
                    """)
                    
                    # Copy data from old table
                    cursor.execute("""
                        INSERT INTO notes_new (id, archive_id, content, created_at)
                        SELECT id, archive_id, content, created_at FROM notes
                    """)
                    
                    # Drop old table
                    cursor.execute("DROP TABLE notes")
                    
                    # Rename new table
                    cursor.execute("ALTER TABLE notes_new RENAME TO notes")
                    
                    # Recreate index
                    cursor.execute("""
                        CREATE INDEX IF NOT EXISTS idx_notes_archive_id 
                        ON notes (archive_id)
                    """)
                    
                    cursor.execute("""
                        CREATE INDEX IF NOT EXISTS idx_notes_created_at 
                        ON notes (created_at DESC)
                    """)
                    
                    logger.info("✓ Notes table migration completed successfully")
                except Exception as e:
                    logger.error(f"Failed to migrate notes table: {e}")
                    # If migration fails, continue with existing schema
                    try:
                        cursor.execute("DROP TABLE IF EXISTS notes_new")
                    except Exception as cleanup_err:
                        logger.debug(f"Failed to cleanup notes_new table: {cleanup_err}")
            
            # Storage stats table - tracks storage usage
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS storage_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    storage_type TEXT NOT NULL,
                    provider TEXT,
                    used_size INTEGER DEFAULT 0,
                    file_count INTEGER DEFAULT 0,
                    updated_at TEXT NOT NULL,
                    UNIQUE(storage_type, provider)
                )
            """)
            
            # Create indexes for better query performance
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_archives_content_type 
                ON archives (content_type)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_archives_created_at 
                ON archives (created_at DESC)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_archives_storage_type 
                ON archives (storage_type)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_tags_name 
                ON tags (tag_name)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_tags_count 
                ON tags (count DESC)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_notes_archive_id 
                ON notes (archive_id)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_notes_created_at 
                ON notes (created_at DESC)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_notes_deleted 
                ON notes (deleted)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_archives_deleted 
                ON archives (deleted)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_archives_favorite 
                ON archives (favorite)
            """)
            
            # Full-text search virtual table for archives
            # This enables fast full-text search on title, content, and AI analysis
            cursor.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS archives_fts 
                USING fts5(
                    title,
                    content,
                    ai_summary,
                    ai_category,
                    content='archives',
                    content_rowid='id'
                )
            """)
            
            # Triggers to keep FTS table in sync
            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS archives_fts_insert 
                AFTER INSERT ON archives 
                BEGIN
                    INSERT INTO archives_fts(rowid, title, content, ai_summary, ai_category)
                    VALUES (new.id, new.title, new.content, new.ai_summary, new.ai_category);
                END
            """)
            
            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS archives_fts_delete 
                AFTER DELETE ON archives 
                BEGIN
                    DELETE FROM archives_fts WHERE rowid = old.id;
                END
            """)
            
            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS archives_fts_update 
                AFTER UPDATE ON archives 
                BEGIN
                    DELETE FROM archives_fts WHERE rowid = old.id;
                    INSERT INTO archives_fts(rowid, title, content, ai_summary, ai_category)
                    VALUES (new.id, new.title, new.content, new.ai_summary, new.ai_category);
                END
            """)
            
            # Add AI analysis columns if they don't exist (for existing databases)
            try:
                cursor.execute("ALTER TABLE archives ADD COLUMN ai_summary TEXT")
            except sqlite3.OperationalError:
                pass  # Column already exists
            
            try:
                cursor.execute("ALTER TABLE archives ADD COLUMN ai_key_points TEXT")
            except sqlite3.OperationalError:
                pass
            
            try:
                cursor.execute("ALTER TABLE archives ADD COLUMN ai_category TEXT")
            except sqlite3.OperationalError:
                pass
            
            # Add favorite column if it doesn't exist (for existing databases)
            try:
                cursor.execute("ALTER TABLE archives ADD COLUMN favorite INTEGER DEFAULT 0")
                logger.info("Added favorite column to archives table")
            except sqlite3.OperationalError:
                pass  # Column already exists
            except sqlite3.OperationalError:
                pass
            
            try:
                cursor.execute("ALTER TABLE archives ADD COLUMN ai_category TEXT")
            except sqlite3.OperationalError:
                pass
            
            # 重建FTS表以包含AI字段（如果表结构已经存在但字段不同）
            try:
                # 检查FTS表是否需要重建（通过检查列是否存在）
                test_cursor = cursor.execute("SELECT * FROM archives_fts LIMIT 0")
                columns = [description[0] for description in test_cursor.description]
                
                # 如果FTS表缺少AI字段，需要重建
                if 'ai_summary' not in columns or 'ai_category' not in columns:
                    logger.info("Rebuilding FTS table to include AI fields...")
                    cursor.execute("DROP TABLE IF EXISTS archives_fts")
                    
                    # 重新创建FTS表
                    cursor.execute("""
                        CREATE VIRTUAL TABLE archives_fts 
                        USING fts5(
                            title,
                            content,
                            ai_summary,
                            ai_category,
                            content='archives',
                            content_rowid='id'
                        )
                    """)
                    
                    # 重建索引
                    cursor.execute("""
                        INSERT INTO archives_fts(rowid, title, content, ai_summary, ai_category)
                        SELECT id, title, content, ai_summary, ai_category FROM archives
                    """)
                    
                    logger.info("FTS table rebuilt successfully with AI fields")
            except Exception as e:
                logger.warning(f"FTS table rebuild check/update failed: {e}")
            
            # Full-text search virtual table for notes
            cursor.execute("""
                CREATE VIRTUAL TABLE IF NOT EXISTS notes_fts 
                USING fts5(
                    content,
                    content='notes',
                    content_rowid='id'
                )
            """)
            
            # Triggers to keep notes FTS table in sync
            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS notes_fts_insert 
                AFTER INSERT ON notes 
                BEGIN
                    INSERT INTO notes_fts(rowid, content)
                    VALUES (new.id, new.content);
                END
            """)
            
            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS notes_fts_delete 
                AFTER DELETE ON notes 
                BEGIN
                    DELETE FROM notes_fts WHERE rowid = old.id;
                END
            """)
            
            cursor.execute("""
                CREATE TRIGGER IF NOT EXISTS notes_fts_update 
                AFTER UPDATE ON notes 
                BEGIN
                    DELETE FROM notes_fts WHERE rowid = old.id;
                    INSERT INTO notes_fts(rowid, content)
                    VALUES (new.id, new.content);
                END
            """)
            
            # Add deleted columns if they don't exist (for existing databases)
            try:
                cursor.execute("ALTER TABLE archives ADD COLUMN deleted INTEGER DEFAULT 0")
            except sqlite3.OperationalError:
                pass  # Column already exists
            
            try:
                cursor.execute("ALTER TABLE archives ADD COLUMN deleted_at TEXT")
            except sqlite3.OperationalError:
                pass
            
            # Initialize default user language preference if not exists
            cursor.execute("""
                INSERT OR IGNORE INTO config (key, value, description, updated_at)
                VALUES ('user_language', 'zh-CN', 'User language preference', datetime('now'))
            """)
            
            self.conn.commit()
            logger.info("Database tables initialized successfully")
            
        except sqlite3.Error as e:
            logger.error(f"Database initialization error: {e}", exc_info=True)
            self.conn.rollback()
            raise
    
    @contextmanager
    def transaction(self):
        """
        Context manager for transactions with automatic commit/rollback
        
        Usage:
            with db.transaction():
                db.execute(...)
                db.execute(...)
        """
        with self._lock:
            try:
                yield
                self.conn.commit()
            except Exception:
                self.conn.rollback()
                raise
    
    def execute(self, query: str, params: tuple = ()) -> sqlite3.Cursor:
        """
        Execute a query and return cursor (thread-safe)
        
        Args:
            query: SQL query
            params: Query parameters
            
        Returns:
            Cursor object
        """
        with self._lock:
            try:
                cursor = self.conn.cursor()
                cursor.execute(query, params)
                return cursor
            except sqlite3.Error as e:
                logger.error(f"Query execution error: {e}\nQuery: {query}", exc_info=True)
                raise
    
    def commit(self) -> None:
        """Commit current transaction"""
        try:
            self.conn.commit()
        except sqlite3.Error as e:
            logger.error(f"Commit error: {e}", exc_info=True)
            raise
    
    def rollback(self) -> None:
        """Rollback current transaction"""
        try:
            self.conn.rollback()
        except sqlite3.Error as e:
            logger.error(f"Rollback error: {e}", exc_info=True)
    
    def get_stats(self) -> dict:
        """
        Get database statistics
        
        Returns:
            Dictionary with statistics
        """
        try:
            cursor = self.conn.cursor()
            
            # Total archives
            cursor.execute("SELECT COUNT(*) FROM archives WHERE deleted = 0")
            total_archives = cursor.fetchone()[0]
            
            # Total tags
            cursor.execute("SELECT COUNT(*) FROM tags")
            total_tags = cursor.fetchone()[0]
            
            # Total storage used
            cursor.execute("SELECT SUM(file_size) FROM archives WHERE file_size IS NOT NULL AND deleted = 0")
            total_size = cursor.fetchone()[0] or 0
            
            # Last archive time
            cursor.execute("SELECT MAX(archived_at) FROM archives WHERE deleted = 0")
            last_archive = cursor.fetchone()[0]
            
            # Type statistics
            cursor.execute("""
                SELECT content_type, COUNT(*) as count
                FROM archives
                WHERE deleted = 0
                GROUP BY content_type
                ORDER BY count DESC
            """)
            type_stats = {row[0]: row[1] for row in cursor.fetchall()}
            
            # Notes statistics
            cursor.execute("SELECT COUNT(*) FROM notes WHERE deleted = 0")
            total_notes = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM notes WHERE archive_id IS NOT NULL AND deleted = 0")
            linked_notes = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM notes WHERE archive_id IS NULL AND deleted = 0")
            standalone_notes = cursor.fetchone()[0]
            
            return {
                'total_archives': total_archives,
                'total_tags': total_tags,
                'total_size': total_size,
                'last_archive': last_archive,
                'type_stats': type_stats,
                'total_notes': total_notes,
                'linked_notes': linked_notes,
                'standalone_notes': standalone_notes
            }
            
        except sqlite3.Error as e:
            logger.error(f"Error getting stats: {e}", exc_info=True)
            return {
                'total_archives': 0,
                'total_tags': 0,
                'total_size': 0,
                'last_archive': None,
                'type_stats': {},
                'total_notes': 0,
                'linked_notes': 0,
                'standalone_notes': 0
            }

    def get_activity_summary(self, days: int = 7) -> Dict[str, Any]:
        """
        Get activity summary for recent days
        """
        try:
            with self._lock:
                cursor = self.conn.cursor()
                since = datetime.now() - timedelta(days=days)
                since_str = since.strftime("%Y-%m-%d %H:%M:%S")

                cursor.execute("SELECT COUNT(*) FROM archives WHERE archived_at >= ? AND deleted = 0", (since_str,))
                archives_count = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM archives WHERE deleted = 1 AND deleted_at >= ?", (since_str,))
                deleted_count = cursor.fetchone()[0]

                cursor.execute("SELECT COUNT(*) FROM notes WHERE created_at >= ?", (since_str,))
                notes_count = cursor.fetchone()[0]

                cursor.execute(
                    """
                    SELECT substr(archived_at,1,10) as day, COUNT(*) 
                    FROM archives 
                    WHERE archived_at >= ? AND deleted = 0
                    GROUP BY day ORDER BY day ASC
                    """,
                    (since_str,)
                )
                trend = [{'date': row[0], 'count': row[1]} for row in cursor.fetchall()]

                cursor.execute(
                    """
                    SELECT t.tag_name, COUNT(*) as cnt
                    FROM archive_tags at
                    INNER JOIN tags t ON at.tag_id = t.id
                    INNER JOIN archives a ON a.id = at.archive_id
                    WHERE a.archived_at >= ? AND a.deleted = 0
                    GROUP BY t.tag_name
                    ORDER BY cnt DESC
                    LIMIT 5
                    """,
                    (since_str,)
                )
                top_tags = [{'tag_name': row[0], 'count': row[1]} for row in cursor.fetchall()]

                return {
                    'days': days,
                    'archives': archives_count,
                    'deleted': deleted_count,
                    'notes': notes_count,
                    'trend': trend,
                    'top_tags': top_tags
                }
        except Exception as e:
            logger.error(f"Error getting activity summary: {e}", exc_info=True)
            return {
                'days': days,
                'archives': 0,
                'deleted': 0,
                'notes': 0,
                'trend': [],
                'top_tags': []
            }
    
    def set_favorite(self, archive_id: int, favorite: bool = True) -> bool:
        """
        Set or unset favorite status for an archive
        
        Args:
            archive_id: Archive ID
            favorite: True to favorite, False to unfavorite
            
        Returns:
            True if successful
        """
        try:
            with self._lock:
                cursor = self.execute(
                    "UPDATE archives SET favorite = ? WHERE id = ? AND deleted = 0",
                    (1 if favorite else 0, archive_id)
                )
                self.commit()
                
                if cursor.rowcount > 0:
                    logger.info(f"Archive {archive_id} favorite status set to {favorite}")
                    return True
                else:
                    logger.warning(f"Archive {archive_id} not found or deleted")
                    return False
        except Exception as e:
            logger.error(f"Error setting favorite: {e}", exc_info=True)
            self.rollback()
            return False
    
    def is_favorite(self, archive_id: int) -> bool:
        """
        Check if an archive is favorited
        
        Args:
            archive_id: Archive ID
            
        Returns:
            True if favorited
        """
        try:
            cursor = self.execute(
                "SELECT favorite FROM archives WHERE id = ? AND deleted = 0",
                (archive_id,)
            )
            row = cursor.fetchone()
            return bool(row and row[0])
        except Exception as e:
            logger.error(f"Error checking favorite: {e}", exc_info=True)
            return False
    
    def has_notes(self, archive_id: int) -> bool:
        """
        Check if an archive has notes
        
        Args:
            archive_id: Archive ID
            
        Returns:
            True if has notes
        """
        try:
            cursor = self.execute(
                "SELECT COUNT(*) FROM notes WHERE archive_id = ?",
                (archive_id,)
            )
            count = cursor.fetchone()[0]
            return count > 0
        except Exception as e:
            logger.error(f"Error checking notes: {e}", exc_info=True)
            return False
    
    def set_note_favorite(self, note_id: int, favorite: bool = True) -> bool:
        """
        Set or unset favorite status for a note
        
        Args:
            note_id: Note ID
            favorite: True to favorite, False to unfavorite
            
        Returns:
            True if successful
        """
        try:
            with self._lock:
                cursor = self.execute(
                    "UPDATE notes SET favorite = ? WHERE id = ? AND deleted = 0",
                    (1 if favorite else 0, note_id)
                )
                self.commit()
                
                if cursor.rowcount > 0:
                    logger.info(f"Note {note_id} favorite status set to {favorite}")
                    return True
                else:
                    logger.warning(f"Note {note_id} not found or deleted")
                    return False
        except Exception as e:
            logger.error(f"Error setting note favorite: {e}", exc_info=True)
            self.rollback()
            return False
    
    def is_note_favorite(self, note_id: int) -> bool:
        """
        Check if a note is favorited
        
        Args:
            note_id: Note ID
            
        Returns:
            True if favorited
        """
        try:
            cursor = self.execute(
                "SELECT favorite FROM notes WHERE id = ? AND deleted = 0",
                (note_id,)
            )
            row = cursor.fetchone()
            return bool(row and row[0])
        except Exception as e:
            logger.error(f"Error checking note favorite: {e}", exc_info=True)
            return False


def init_database(db_path: str) -> Database:
    """
    Initialize database
    
    Args:
        db_path: Path to database file
        
    Returns:
        Database instance
    """
    return Database(db_path)
