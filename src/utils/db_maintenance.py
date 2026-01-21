"""
Database backup and maintenance utilities
"""

import shutil
import logging
from pathlib import Path
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)


def backup_database(
    db_path: str,
    backup_dir: Optional[str] = None,
    keep_backups: int = 7
) -> Optional[str]:
    """
    Create a backup of the database
    
    Args:
        db_path: Path to database file
        backup_dir: Backup directory (default: data/backups)
        keep_backups: Number of backups to keep
        
    Returns:
        Path to backup file or None if failed
    """
    try:
        db_file = Path(db_path)
        
        if not db_file.exists():
            logger.error(f"Database file not found: {db_path}")
            return None
        
        # Determine backup directory
        if backup_dir is None:
            backup_dir = db_file.parent / "backups"
        else:
            backup_dir = Path(backup_dir)
        
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        # Create backup filename with timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{db_file.stem}_backup_{timestamp}{db_file.suffix}"
        backup_path = backup_dir / backup_name
        
        # Copy database file
        shutil.copy2(db_file, backup_path)
        
        logger.info(f"Database backup created: {backup_path}")
        
        # Clean old backups
        cleanup_old_backups(backup_dir, keep_backups)
        
        return str(backup_path)
        
    except Exception as e:
        logger.error(f"Error creating database backup: {e}", exc_info=True)
        return None


def cleanup_old_backups(backup_dir: Path, keep_count: int) -> None:
    """
    Remove old backup files, keeping only the most recent ones
    
    Args:
        backup_dir: Backup directory
        keep_count: Number of backups to keep
    """
    try:
        # Get all backup files
        backup_files = list(backup_dir.glob("*_backup_*.db"))
        
        if len(backup_files) <= keep_count:
            return
        
        # Sort by modification time
        backup_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
        
        # Remove old backups
        for old_backup in backup_files[keep_count:]:
            try:
                old_backup.unlink()
                logger.info(f"Removed old backup: {old_backup.name}")
            except Exception as e:
                logger.warning(f"Failed to remove old backup {old_backup}: {e}")
        
    except Exception as e:
        logger.error(f"Error cleaning old backups: {e}", exc_info=True)


def verify_database(db_path: str) -> bool:
    """
    Verify database integrity
    
    Args:
        db_path: Path to database file
        
    Returns:
        True if database is valid, False otherwise
    """
    try:
        import sqlite3
        
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Run integrity check
        cursor.execute("PRAGMA integrity_check")
        result = cursor.fetchone()
        
        conn.close()
        
        is_valid = result and result[0] == 'ok'
        
        if is_valid:
            logger.info("Database integrity check passed")
        else:
            logger.error(f"Database integrity check failed: {result}")
        
        return is_valid
        
    except Exception as e:
        logger.error(f"Error verifying database: {e}", exc_info=True)
        return False


def optimize_database(db_path: str) -> bool:
    """
    Optimize database (VACUUM and ANALYZE)
    
    Args:
        db_path: Path to database file
        
    Returns:
        True if successful, False otherwise
    """
    try:
        import sqlite3
        
        conn = sqlite3.connect(db_path)
        
        # Vacuum to reclaim space
        logger.info("Running VACUUM...")
        conn.execute("VACUUM")
        
        # Analyze to update statistics
        logger.info("Running ANALYZE...")
        conn.execute("ANALYZE")
        
        conn.close()
        
        logger.info("Database optimization completed")
        return True
        
    except Exception as e:
        logger.error(f"Error optimizing database: {e}", exc_info=True)
        return False
