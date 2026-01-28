"""
Backup manager module
Manages database backups and restoration
"""

import logging
import shutil
import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime

from ..utils.helpers import format_datetime

logger = logging.getLogger(__name__)


class BackupManager:
    """
    Manages database backup and restoration
    Supports manual and automatic backups
    """
    
    def __init__(self, db_path: str, backup_dir: str = "data/backups"):
        """
        Initialize backup manager
        
        Args:
            db_path: Path to database file
            backup_dir: Directory to store backups
        """
        self.db_path = Path(db_path)
        self.backup_dir = Path(backup_dir)
        
        # Create backup directory if not exists
        self.backup_dir.mkdir(parents=True, exist_ok=True)
        
        logger.info(f"BackupManager initialized: backup_dir={self.backup_dir}")
    
    def create_backup(self, description: str = "") -> Optional[str]:
        """
        Create a database backup
        
        Args:
            description: Optional backup description
            
        Returns:
            Backup filename if successful, None otherwise
        """
        try:
            # Generate backup filename with timestamp
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            backup_filename = f"archivebot_backup_{timestamp}.db"
            backup_path = self.backup_dir / backup_filename
            
            # Create backup using SQLite backup API (safer than file copy)
            source_conn = sqlite3.connect(str(self.db_path))
            backup_conn = sqlite3.connect(str(backup_path))
            
            with backup_conn:
                source_conn.backup(backup_conn)
            
            source_conn.close()
            backup_conn.close()
            
            # Create metadata file
            metadata = {
                'filename': backup_filename,
                'created_at': format_datetime(),
                'description': description,
                'size': backup_path.stat().st_size,
                'source_db': str(self.db_path)
            }
            
            import json
            metadata_path = self.backup_dir / f"{backup_filename}.meta"
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)
            
            logger.info(f"Backup created: {backup_filename} ({metadata['size']} bytes)")
            return backup_filename
            
        except Exception as e:
            logger.error(f"Error creating backup: {e}", exc_info=True)
            return None
    
    def restore_backup(self, backup_filename: str) -> bool:
        """
        Restore database from backup
        
        Args:
            backup_filename: Backup filename
            
        Returns:
            True if successful, False otherwise
        """
        try:
            backup_path = self.backup_dir / backup_filename
            
            if not backup_path.exists():
                logger.error(f"Backup file not found: {backup_filename}")
                return False
            
            # Create a backup of current database before restore
            current_backup = self.create_backup(description="Pre-restore backup")
            if not current_backup:
                logger.warning("Failed to create pre-restore backup")
            
            # Verify backup integrity
            if not self._verify_backup(backup_path):
                logger.error(f"Backup verification failed: {backup_filename}")
                return False
            
            # Replace current database with backup
            shutil.copy2(backup_path, self.db_path)
            
            logger.info(f"Database restored from backup: {backup_filename}")
            return True
            
        except Exception as e:
            logger.error(f"Error restoring backup: {e}", exc_info=True)
            return False
    
    def list_backups(self) -> List[Dict[str, Any]]:
        """
        List all available backups
        
        Returns:
            List of backup metadata
        """
        try:
            backups = []
            
            # Find all .db files in backup directory
            for backup_file in sorted(self.backup_dir.glob("*.db"), reverse=True):
                metadata = {}
                
                # Try to load metadata
                metadata_file = backup_file.with_suffix('.db.meta')
                if metadata_file.exists():
                    try:
                        import json
                        with open(metadata_file, 'r', encoding='utf-8') as f:
                            metadata = json.load(f)
                    except Exception as e:
                        logger.debug(f"Failed to load backup metadata: {e}")
                
                # Fallback to file stats if no metadata
                if not metadata:
                    stat = backup_file.stat()
                    metadata = {
                        'filename': backup_file.name,
                        'created_at': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                        'description': '',
                        'size': stat.st_size
                    }
                
                backups.append(metadata)
            
            return backups
            
        except Exception as e:
            logger.error(f"Error listing backups: {e}", exc_info=True)
            return []
    
    def delete_backup(self, backup_filename: str) -> bool:
        """
        Delete a backup file
        
        Args:
            backup_filename: Backup filename
            
        Returns:
            True if successful, False otherwise
        """
        try:
            backup_path = self.backup_dir / backup_filename
            metadata_path = self.backup_dir / f"{backup_filename}.meta"
            
            if not backup_path.exists():
                logger.error(f"Backup file not found: {backup_filename}")
                return False
            
            # Delete backup file
            backup_path.unlink()
            
            # Delete metadata if exists
            if metadata_path.exists():
                metadata_path.unlink()
            
            logger.info(f"Backup deleted: {backup_filename}")
            return True
            
        except Exception as e:
            logger.error(f"Error deleting backup: {e}", exc_info=True)
            return False
    
    def cleanup_old_backups(self, keep_count: int = 10) -> int:
        """
        Clean up old backups, keeping only the most recent ones
        
        Args:
            keep_count: Number of backups to keep
            
        Returns:
            Number of backups deleted
        """
        try:
            backups = self.list_backups()
            
            if len(backups) <= keep_count:
                return 0
            
            # Delete old backups
            deleted_count = 0
            for backup in backups[keep_count:]:
                if self.delete_backup(backup['filename']):
                    deleted_count += 1
            
            logger.info(f"Cleaned up {deleted_count} old backups")
            return deleted_count
            
        except Exception as e:
            logger.error(f"Error cleaning up backups: {e}", exc_info=True)
            return 0
    
    def get_backup_info(self, backup_filename: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed info about a backup
        
        Args:
            backup_filename: Backup filename
            
        Returns:
            Backup metadata dict or None
        """
        try:
            backup_path = self.backup_dir / backup_filename
            
            if not backup_path.exists():
                return None
            
            # Load metadata
            metadata_file = backup_path.with_suffix('.db.meta')
            if metadata_file.exists():
                import json
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    metadata = json.load(f)
            else:
                stat = backup_path.stat()
                metadata = {
                    'filename': backup_filename,
                    'created_at': datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'),
                    'description': '',
                    'size': stat.st_size
                }
            
            # Add verification status
            metadata['verified'] = self._verify_backup(backup_path)
            
            return metadata
            
        except Exception as e:
            logger.error(f"Error getting backup info: {e}", exc_info=True)
            return None
    
    def _verify_backup(self, backup_path: Path) -> bool:
        """
        Verify backup integrity by checking SQLite database
        
        Args:
            backup_path: Path to backup file
            
        Returns:
            True if valid, False otherwise
        """
        try:
            conn = sqlite3.connect(str(backup_path))
            cursor = conn.cursor()
            
            # Quick integrity check
            cursor.execute("PRAGMA integrity_check")
            result = cursor.fetchone()
            
            conn.close()
            
            return result[0] == 'ok'
            
        except Exception as e:
            logger.error(f"Backup verification failed: {e}")
            return False
    
    def get_database_stats(self) -> Dict[str, Any]:
        """
        Get current database statistics
        
        Returns:
            Database stats dict
        """
        try:
            conn = sqlite3.connect(str(self.db_path))
            cursor = conn.cursor()
            
            stats = {}
            
            # Get database size
            stats['size'] = self.db_path.stat().st_size
            
            # Get table counts
            cursor.execute("SELECT COUNT(*) FROM archives WHERE deleted = 0")
            stats['archives_count'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM notes")
            stats['notes_count'] = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM archives WHERE deleted = 1")
            stats['deleted_count'] = cursor.fetchone()[0]
            
            # Get last modified time
            cursor.execute("SELECT MAX(created_at) FROM archives")
            last_archive = cursor.fetchone()[0]
            stats['last_archive'] = last_archive or 'N/A'
            
            conn.close()
            
            return stats
            
        except Exception as e:
            logger.error(f"Error getting database stats: {e}", exc_info=True)
            return {}
    
    def auto_backup_check(self, interval_hours: int = 24) -> bool:
        """
        Check if automatic backup is needed based on interval
        
        Args:
            interval_hours: Backup interval in hours
            
        Returns:
            True if backup is needed, False otherwise
        """
        try:
            backups = self.list_backups()
            
            if not backups:
                return True
            
            # Get most recent backup
            latest_backup = backups[0]
            latest_time = datetime.strptime(latest_backup['created_at'], '%Y-%m-%d %H:%M:%S')
            
            # Check if interval has passed
            now = datetime.now()
            hours_since_backup = (now - latest_time).total_seconds() / 3600
            
            return hours_since_backup >= interval_hours
            
        except Exception as e:
            logger.error(f"Error checking auto backup: {e}", exc_info=True)
            return False
