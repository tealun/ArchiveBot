"""
Database models and initialization
Single-user design - no user_id field required
"""

import sqlite3
import logging
import threading
from pathlib import Path
from typing import Optional
from datetime import datetime
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
            cursor.execute("SELECT COUNT(*) FROM archives")
            total_archives = cursor.fetchone()[0]
            
            # Total tags
            cursor.execute("SELECT COUNT(*) FROM tags")
            total_tags = cursor.fetchone()[0]
            
            # Total storage used
            cursor.execute("SELECT SUM(file_size) FROM archives WHERE file_size IS NOT NULL")
            total_size = cursor.fetchone()[0] or 0
            
            # Last archive time
            cursor.execute("SELECT MAX(archived_at) FROM archives")
            last_archive = cursor.fetchone()[0]
            
            return {
                'total_archives': total_archives,
                'total_tags': total_tags,
                'total_size': total_size,
                'last_archive': last_archive
            }
            
        except sqlite3.Error as e:
            logger.error(f"Error getting stats: {e}", exc_info=True)
            return {
                'total_archives': 0,
                'total_tags': 0,
                'total_size': 0,
                'last_archive': None
            }


def init_database(db_path: str) -> Database:
    """
    Initialize database
    
    Args:
        db_path: Path to database file
        
    Returns:
        Database instance
    """
    return Database(db_path)
