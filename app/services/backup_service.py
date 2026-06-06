"""
Sanchay — Backup & Restore Service
=====================================
SQLite database backup and restore operations.
Uses SQLite's built-in backup API for safe, consistent backups.
"""

import shutil
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Optional

from loguru import logger

from app.config import config
from app.core.exceptions import BackupError
from app.core.database import get_db
from app.core.security import current_session
from app.models.audit import AuditLog
from app.constants import AuditAction


class BackupService:
    """
    Handles database backup and restore.
    
    Backup: Creates a timestamped copy using SQLite's backup API.
    Restore: Replaces the current database with a selected backup.
    """

    def create_backup(self, destination: Optional[Path] = None) -> Path:
        """
        Create a backup of the current database.
        
        Args:
            destination: Optional custom path. Defaults to backups/ folder.
            
        Returns:
            Path to the created backup file.
            
        Raises:
            BackupError: If backup fails.
        """
        if not config.DB_PATH.exists():
            raise BackupError("No database found to back up.")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"sanchay_backup_{timestamp}.db"

        if destination:
            backup_path = Path(destination) / backup_name
        else:
            config.BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
            backup_path = config.BACKUPS_DIR / backup_name

        try:
            # Use SQLite's backup API for a consistent hot-backup
            source = sqlite3.connect(str(config.DB_PATH))
            dest = sqlite3.connect(str(backup_path))
            with dest:
                source.backup(dest)
            dest.close()
            source.close()

            size_kb = backup_path.stat().st_size / 1024
            logger.info(f"Backup created: {backup_path} ({size_kb:.1f} KB)")

            # Audit log
            with get_db() as db:
                log = AuditLog(
                    user_id=current_session.user_id,
                    action=AuditAction.BACKUP.value,
                    module="system",
                    description=f"Database backed up to '{backup_name}' ({size_kb:.1f} KB).",
                )
                db.add(log)

            return backup_path

        except Exception as e:
            logger.error(f"Backup failed: {e}")
            if backup_path.exists():
                backup_path.unlink()
            raise BackupError(f"Backup failed: {str(e)}")

    def restore_backup(self, backup_path: Path) -> None:
        """
        Restore the database from a backup file.
        
        ⚠️  This REPLACES the current database.
        A safety copy of the current DB is made before replacing.
        
        Args:
            backup_path: Path to the .db backup file.
            
        Raises:
            BackupError: If restore fails.
        """
        backup_path = Path(backup_path)
        if not backup_path.exists():
            raise BackupError(f"Backup file not found: {backup_path}")

        if not backup_path.suffix.lower() == ".db":
            raise BackupError("Invalid backup file. Expected a .db file.")

        # Validate the backup is a valid SQLite DB
        try:
            conn = sqlite3.connect(str(backup_path))
            conn.execute("PRAGMA integrity_check")
            conn.close()
        except sqlite3.DatabaseError as e:
            raise BackupError(f"Backup file is corrupted or invalid: {e}")

        # Create a pre-restore safety copy
        if config.DB_PATH.exists():
            safety_stamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            safety_copy = config.BACKUPS_DIR / f"pre_restore_{safety_stamp}.db"
            try:
                shutil.copy2(str(config.DB_PATH), str(safety_copy))
                logger.info(f"Pre-restore safety copy: {safety_copy}")
            except Exception as e:
                logger.warning(f"Could not create safety copy: {e}")

        # Replace the database
        try:
            shutil.copy2(str(backup_path), str(config.DB_PATH))
            logger.info(f"Database restored from: {backup_path}")
        except Exception as e:
            raise BackupError(f"Restore failed: {e}")

    def list_backups(self) -> list[dict]:
        """
        List available backup files with metadata.
        
        Returns:
            List of dicts with: name, path, size_kb, created_at
        """
        config.BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
        backups = []
        for f in sorted(config.BACKUPS_DIR.glob("*.db"), reverse=True):
            if f.name.startswith("sanchay_backup_"):
                stat = f.stat()
                backups.append({
                    "name": f.name,
                    "path": f,
                    "size_kb": stat.st_size / 1024,
                    "created_at": datetime.fromtimestamp(stat.st_mtime),
                })
        return backups

    def delete_backup(self, backup_path: Path) -> None:
        """Delete a specific backup file."""
        backup_path = Path(backup_path)
        if backup_path.exists() and backup_path.suffix == ".db":
            backup_path.unlink()
            logger.info(f"Backup deleted: {backup_path.name}")

    def cleanup_old_backups(self, keep: int = 10) -> int:
        """Keep only the most recent N backups. Returns count deleted."""
        backups = self.list_backups()
        to_delete = backups[keep:]
        for b in to_delete:
            b["path"].unlink()
        if to_delete:
            logger.info(f"Cleaned up {len(to_delete)} old backup(s).")
        return len(to_delete)
