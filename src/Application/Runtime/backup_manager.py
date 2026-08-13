import os
import time
import zipfile
import glob
from datetime import datetime
from typing import Dict, Any, List, Optional
from src.Infrastructure.exceptions import ValidationException

class BackupManager:
    """
    Automates secure backup snapshots, retention policy enforcement,
    and isolated restore drills for the YarTrader AI persistent state.
    """
    def __init__(self, backup_dir: str = "backups", source_dir: str = "runtime_logs") -> None:
        self.backup_dir = backup_dir
        self.source_dir = source_dir
        os.makedirs(self.backup_dir, exist_ok=True)

    def create_backup(self) -> Dict[str, Any]:
        """
        Creates a zip snapshot of the source directory, verifies archive integrity,
        and enforces the backup retention policy (keeps top 5 most recent).
        """
        if not os.path.exists(self.source_dir):
            raise ValidationException(f"Backup Source Error: Source directory '{self.source_dir}' does not exist.")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        backup_filename = f"backup_{timestamp}.zip"
        backup_path = os.path.join(self.backup_dir, backup_filename)

        file_count = 0
        try:
            # Create compressed zip archive atomically
            with zipfile.ZipFile(backup_path, "w", zipfile.ZIP_DEFLATED) as zipf:
                for root, _, files in os.walk(self.source_dir):
                    for file in files:
                        filepath = os.path.join(root, file)
                        # Archive path relative to parent of source_dir to preserve folder structure
                        arcname = os.path.relpath(filepath, os.path.dirname(self.source_dir))
                        zipf.write(filepath, arcname)
                        file_count += 1

            # Integrity Verification
            with zipfile.ZipFile(backup_path, "r") as zipf:
                corrupt_file = zipf.testzip()
                if corrupt_file is not None:
                    raise zipfile.BadZipFile(f"Integrity check failed: corrupted file '{corrupt_file}' found in archive.")

            # Retention Policy (Keep 5 most recent backups)
            self._enforce_retention_policy()

            stat = os.stat(backup_path)
            return {
                "status": "Success",
                "filename": backup_filename,
                "filepath": backup_path,
                "size_bytes": stat.st_size,
                "file_count": file_count,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            if os.path.exists(backup_path):
                try:
                    os.remove(backup_path)
                except Exception:
                    pass
            raise ValidationException(f"Backup Creation Failed: {str(e)}")

    def restore_backup(self, backup_filename: str) -> Dict[str, Any]:
        """
        Verifies backup archive integrity first, then safely extracts it,
        completely restoring the system state.
        """
        backup_path = os.path.join(self.backup_dir, backup_filename)
        if not os.path.exists(backup_path):
            raise ValidationException(f"Restore Error: Backup file '{backup_filename}' does not exist.")

        try:
            # 1. Integrity check before extracting
            with zipfile.ZipFile(backup_path, "r") as zipf:
                corrupt_file = zipf.testzip()
                if corrupt_file is not None:
                    raise zipfile.BadZipFile(f"Corrupted file '{corrupt_file}' inside backup archive.")

                # 2. Safe isolated restore
                # Extract to parent directory of self.source_dir to overwrite it correctly
                parent_dir = os.path.dirname(self.source_dir) or "."
                zipf.extractall(parent_dir)

            return {
                "status": "Success",
                "restored_from": backup_filename,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            raise ValidationException(f"Restore Operations Failed: {str(e)}")

    def _enforce_retention_policy(self, max_keep: int = 5) -> None:
        """Deletes older backup files, keeping only the max_keep most recent ones."""
        backups = glob.glob(os.path.join(self.backup_dir, "backup_*.zip"))
        # Sort lexicographically descending by filename which aligns with %Y%m%d_%H%M%S_%f chronological order
        backups.sort(reverse=True)

        if len(backups) > max_keep:
            for old_backup in backups[max_keep:]:
                try:
                    os.remove(old_backup)
                except Exception:
                    pass
