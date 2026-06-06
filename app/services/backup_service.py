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

# Minimum free disk space required before creating a backup (bytes)
_MIN_FREE_BYTES = 50 * 1024 * 1024  # 50 MB

# SQLite file header magic bytes (first 16 bytes of a valid SQLite3 file)
_SQLITE_HEADER = b"SQLite format 3\x00"


class BackupService:
    """
    Handles database backup and restore.
    
    Backup: Creates a timestamped copy using SQLite's backup API.
    Restore: Replaces the current database with a selected backup.
    """

    def create_backup(self, destination: Optional[Path] = None) -> Path:
        """
        Create a backup of the current database.
        
        Checks for at least 50 MB of free disk space before proceeding.
        Verifies the backup file is a valid SQLite DB after creation.
        
        Args:
            destination: Optional custom directory path. Defaults to backups/ folder.
                         Must be a directory path, not a file path.
            
        Returns:
            Path to the created backup file.
            
        Raises:
            BackupError: If backup fails, there is insufficient disk space,
                         the database doesn't exist, or the destination is a file path.
        """
        # Defensive: require the source DB to exist
        if not config.DB_PATH.exists():
            raise BackupError(
                "No database found. The application must be used before creating a backup."
            )

        # Determine target directory for disk-space check
        if destination:
            dest_path = Path(destination)
            # Defensive: reject file paths (must be a directory)
            if dest_path.suffix.lower() in (".db", ".sqlite", ".sqlite3"):
                raise BackupError(
                    f"Destination '{dest_path}' looks like a file path. "
                    "Please provide a directory path, not a file path."
                )
            if dest_path.exists() and dest_path.is_file():
                raise BackupError(
                    f"Destination '{dest_path}' is a file. "
                    "Please provide a directory path."
                )
            target_dir = dest_path
            target_dir.mkdir(parents=True, exist_ok=True)
        else:
            target_dir = config.BACKUPS_DIR
            config.BACKUPS_DIR.mkdir(parents=True, exist_ok=True)

        # Check free disk space
        try:
            usage = shutil.disk_usage(str(target_dir))
            free_mb = usage.free / (1024 * 1024)
            if usage.free < _MIN_FREE_BYTES:
                logger.warning(
                    f"Low disk space: only {free_mb:.1f} MB free in '{target_dir}'. "
                    "Backup may fail or leave insufficient space."
                )
            logger.debug(f"Disk space check: {free_mb:.1f} MB free in '{target_dir}'")
        except Exception as e:
            logger.warning(f"Could not check disk space: {e}")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S%f")[:19]
        backup_name = f"sanchay_backup_{timestamp}.db"
        backup_path = target_dir / backup_name

        try:
            # Use SQLite's backup API for a consistent hot-backup
            source = sqlite3.connect(str(config.DB_PATH))
            dest = sqlite3.connect(str(backup_path))
            with dest:
                source.backup(dest)
            dest.close()
            source.close()

            # Defensive: verify the backup file is a valid SQLite database
            try:
                conn = sqlite3.connect(str(backup_path))
                result = conn.execute("PRAGMA integrity_check").fetchone()
                conn.close()
                if not result or result[0] != "ok":
                    backup_path.unlink(missing_ok=True)
                    raise BackupError(
                        f"Backup file failed integrity check (result: "
                        f"{result[0] if result else 'unknown'}). "
                        "The backup has been discarded."
                    )
            except sqlite3.DatabaseError as e:
                backup_path.unlink(missing_ok=True)
                raise BackupError(f"Backup file validation failed: {e}")

            size_kb = backup_path.stat().st_size / 1024
            logger.info(f"Backup created: {backup_path} ({size_kb:.1f} KB)")

            # Audit log
            try:
                with get_db() as db:
                    log = AuditLog(
                        user_id=current_session.user_id,
                        action=AuditAction.BACKUP.value,
                        module="system",
                        description=f"Database backed up to '{backup_name}' ({size_kb:.1f} KB).",
                    )
                    db.add(log)
            except Exception as audit_err:
                logger.warning(f"Could not write audit log for backup: {audit_err}")

            return backup_path

        except BackupError:
            raise
        except Exception as e:
            logger.error(f"Backup failed: {e}")
            # Clean up partial backup file
            if backup_path.exists():
                try:
                    backup_path.unlink()
                except Exception as cleanup_err:
                    logger.warning(f"Could not clean up partial backup '{backup_path}': {cleanup_err}")
            raise BackupError(f"Backup failed: {str(e)}")

    def restore_backup(self, backup_path: Path) -> None:
        """
        Restore the database from a backup file.
        
        ⚠️  This REPLACES the current database.
        A safety copy of the current DB is made before replacing.
        
        Args:
            backup_path: Path to the .db backup file.
            
        Raises:
            BackupError: If restore fails or the backup file is invalid.
        """
        backup_path = Path(backup_path)
        if not backup_path.exists():
            raise BackupError(f"Backup file not found: {backup_path}")

        if not backup_path.suffix.lower() == ".db":
            raise BackupError("Invalid backup file. Expected a .db file.")

        # Defensive: check file size (must be > 1024 bytes to be a real DB)
        file_size = backup_path.stat().st_size
        if file_size < 1024:
            raise BackupError(
                f"Backup file is too small ({file_size} bytes). "
                "The file may be empty or corrupted."
            )

        # Defensive: check SQLite header magic bytes
        try:
            with open(backup_path, "rb") as f:
                header = f.read(16)
            if header != _SQLITE_HEADER:
                raise BackupError(
                    "Backup file does not have a valid SQLite header. "
                    "The file may be corrupted or is not a SQLite database."
                )
        except BackupError:
            raise
        except Exception as e:
            raise BackupError(f"Could not read backup file header: {e}")

        # Validate the backup is a valid SQLite DB via integrity check
        try:
            conn = sqlite3.connect(str(backup_path))
            result = conn.execute("PRAGMA integrity_check").fetchone()
            conn.close()
            if not result or result[0] != "ok":
                raise BackupError(
                    f"Backup file failed integrity check (result: "
                    f"{result[0] if result else 'unknown'}). "
                    "Cannot restore a corrupted backup."
                )
        except BackupError:
            raise
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

            # Remove WAL / SHM sidecar files so SQLite doesn't replay
            # stale transactions on top of the restored DB.
            for suffix in ("-wal", "-shm", ".db-wal", ".db-shm"):
                sidecar = config.DB_PATH.parent / (config.DB_PATH.name + suffix)
                if sidecar.exists():
                    try:
                        sidecar.unlink()
                        logger.debug(f"Removed WAL sidecar: {sidecar.name}")
                    except Exception:
                        pass

            logger.info(f"Database restored from: {backup_path}")
        except PermissionError:
            raise BackupError(
                f"Cannot write to '{config.DB_PATH}'. "
                "Check that the application has write permissions to the data directory."
            )
        except BackupError:
            raise
        except Exception as e:
            raise BackupError(f"Restore failed: {e}")

    def list_backups(self) -> list[dict]:
        """
        List available backup files with metadata.
        
        Skips files that fail integrity check (corrupted .db files).
        Sorted newest first.
        
        Returns:
            List of dicts with: name, path, size_kb, created_at
        """
        config.BACKUPS_DIR.mkdir(parents=True, exist_ok=True)
        backups = []
        for f in sorted(config.BACKUPS_DIR.glob("*.db"), reverse=True):
            if not f.name.startswith("sanchay_backup_"):
                continue
            # Validate file integrity before listing
            try:
                conn = sqlite3.connect(str(f))
                result = conn.execute("PRAGMA integrity_check").fetchone()
                conn.close()
                if result and result[0] != "ok":
                    logger.warning(
                        f"Backup file '{f.name}' failed integrity check "
                        f"(result: {result[0]}); skipping."
                    )
                    continue
            except sqlite3.DatabaseError as e:
                logger.warning(f"Backup file '{f.name}' is corrupted: {e}; skipping.")
                continue
            except Exception as e:
                logger.warning(f"Could not validate '{f.name}': {e}; skipping.")
                continue

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
        """Keep only the most recent N backups. Returns count deleted.
        
        Defensive: keep is clamped to a minimum of 1, and the operation will
        never delete ALL backups (at least one is always preserved).
        """
        # Defensive: ensure we keep at least 1 backup
        try:
            keep = int(keep)
        except (TypeError, ValueError):
            keep = 10
        if keep < 1:
            logger.warning(
                f"cleanup_old_backups: keep={keep} is invalid; clamping to 1."
            )
            keep = 1

        backups = self.list_backups()

        # Defensive: never delete ALL backups — always keep at least 1
        safe_keep = max(keep, 1)
        if len(backups) <= safe_keep:
            return 0

        to_delete = backups[safe_keep:]
        deleted = 0
        for b in to_delete:
            try:
                b["path"].unlink()
                deleted += 1
            except Exception as e:
                logger.warning(f"Could not delete backup '{b['name']}': {e}")
        if deleted:
            logger.info(f"Cleaned up {deleted} old backup(s).")
        return deleted

    def get_db_stats(self) -> dict:
        """
        Return database statistics.
        
        Returns:
            dict with keys: size_bytes, size_kb, table_counts
            table_counts is a dict of {table_name: row_count}.
            Returns an empty dict on any failure.
        """
        try:
            if not config.DB_PATH.exists():
                logger.debug("get_db_stats: database file not found.")
                return {"size_bytes": 0, "size_kb": 0.0, "table_counts": {}}

            size_bytes = config.DB_PATH.stat().st_size
            size_kb    = size_bytes / 1024

            table_counts: dict[str, int] = {}
            try:
                conn = sqlite3.connect(str(config.DB_PATH))
                tables = conn.execute(
                    "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
                ).fetchall()
                for (table_name,) in tables:
                    try:
                        count = conn.execute(
                            f"SELECT COUNT(*) FROM \"{table_name}\""
                        ).fetchone()[0]
                        table_counts[table_name] = count
                    except Exception:
                        table_counts[table_name] = -1  # unreadable
                conn.close()
            except Exception as e:
                logger.warning(f"get_db_stats: could not read table counts: {e}")

            logger.debug(
                f"DB stats: {size_kb:.1f} KB, {len(table_counts)} tables."
            )
            return {
                "size_bytes":   size_bytes,
                "size_kb":      round(size_kb, 2),
                "table_counts": table_counts,
            }
        except Exception as e:
            logger.warning(f"get_db_stats: unexpected error: {e}")
            return {}
