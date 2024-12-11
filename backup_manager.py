import os
import shutil
import logging
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import zipfile
from dataclasses import dataclass
import hashlib

@dataclass
class BackupInfo:
    id: str
    name: str
    timestamp: str
    size: int
    files: List[str]
    hash: str
    description: Optional[str] = None

class BackupManager:
    def __init__(self):
        self.backups_dir = Path("backups")
        self.metadata_file = self.backups_dir / "metadata.json"
        self.backups: Dict[str, BackupInfo] = {}
        
        # Create backups directory if it doesn't exist
        self.backups_dir.mkdir(exist_ok=True)
        
        # Load existing backups metadata
        self.load_metadata()
    
    def load_metadata(self):
        """Load backups metadata"""
        try:
            if self.metadata_file.exists():
                with open(self.metadata_file, "r") as f:
                    data = json.load(f)
                    self.backups = {
                        k: BackupInfo(**v) for k, v in data.items()
                    }
        except Exception as e:
            logging.error(f"Error loading backup metadata: {e}")
            self.backups = {}
    
    def save_metadata(self):
        """Save backups metadata"""
        try:
            with open(self.metadata_file, "w") as f:
                data = {
                    k: v.__dict__ for k, v in self.backups.items()
                }
                json.dump(data, f, indent=4)
        except Exception as e:
            logging.error(f"Error saving backup metadata: {e}")
    
    def create_backup(
        self,
        name: str,
        paths: List[str],
        description: Optional[str] = None
    ) -> Optional[BackupInfo]:
        """Create a new backup"""
        try:
            # Generate unique backup ID
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_id = f"{name}_{timestamp}"
            
            # Create backup directory
            backup_dir = self.backups_dir / backup_id
            backup_dir.mkdir(exist_ok=True)
            
            # Copy files to backup directory
            copied_files = []
            total_size = 0
            
            for path in paths:
                src_path = Path(path)
                if not src_path.exists():
                    logging.warning(f"Path not found: {path}")
                    continue
                
                if src_path.is_file():
                    dst_path = backup_dir / src_path.name
                    shutil.copy2(src_path, dst_path)
                    copied_files.append(str(src_path))
                    total_size += src_path.stat().st_size
                elif src_path.is_dir():
                    dst_path = backup_dir / src_path.name
                    shutil.copytree(src_path, dst_path)
                    for file in src_path.rglob("*"):
                        if file.is_file():
                            copied_files.append(str(file))
                            total_size += file.stat().st_size
            
            # Create zip archive
            zip_path = self.backups_dir / f"{backup_id}.zip"
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for file in backup_dir.rglob("*"):
                    if file.is_file():
                        zipf.write(file, file.relative_to(backup_dir))
            
            # Calculate backup hash
            backup_hash = self._calculate_hash(zip_path)
            
            # Create backup info
            backup_info = BackupInfo(
                id=backup_id,
                name=name,
                timestamp=timestamp,
                size=total_size,
                files=copied_files,
                hash=backup_hash,
                description=description
            )
            
            # Save backup info
            self.backups[backup_id] = backup_info
            self.save_metadata()
            
            # Clean up temporary directory
            shutil.rmtree(backup_dir)
            
            logging.info(f"Created backup: {backup_id}")
            return backup_info
            
        except Exception as e:
            logging.error(f"Error creating backup: {e}")
            return None
    
    def restore_backup(
        self,
        backup_id: str,
        restore_path: Optional[str] = None
    ) -> bool:
        """Restore a backup"""
        try:
            if backup_id not in self.backups:
                raise ValueError(f"Backup not found: {backup_id}")
            
            backup = self.backups[backup_id]
            zip_path = self.backups_dir / f"{backup_id}.zip"
            
            if not zip_path.exists():
                raise FileNotFoundError(f"Backup file not found: {zip_path}")
            
            # Verify backup integrity
            current_hash = self._calculate_hash(zip_path)
            if current_hash != backup.hash:
                raise ValueError("Backup integrity check failed")
            
            # Create temporary extraction directory
            extract_dir = self.backups_dir / f"restore_{backup_id}"
            extract_dir.mkdir(exist_ok=True)
            
            # Extract backup
            with zipfile.ZipFile(zip_path, 'r') as zipf:
                zipf.extractall(extract_dir)
            
            # Restore files
            restore_base = Path(restore_path) if restore_path else Path()
            for file in extract_dir.rglob("*"):
                if file.is_file():
                    relative_path = file.relative_to(extract_dir)
                    dst_path = restore_base / relative_path
                    
                    # Create parent directories
                    dst_path.parent.mkdir(parents=True, exist_ok=True)
                    
                    # Copy file
                    shutil.copy2(file, dst_path)
            
            # Clean up
            shutil.rmtree(extract_dir)
            
            logging.info(f"Restored backup: {backup_id}")
            return True
            
        except Exception as e:
            logging.error(f"Error restoring backup: {e}")
            return False
    
    def delete_backup(self, backup_id: str) -> bool:
        """Delete a backup"""
        try:
            if backup_id not in self.backups:
                raise ValueError(f"Backup not found: {backup_id}")
            
            # Delete backup file
            zip_path = self.backups_dir / f"{backup_id}.zip"
            if zip_path.exists():
                zip_path.unlink()
            
            # Remove from metadata
            del self.backups[backup_id]
            self.save_metadata()
            
            logging.info(f"Deleted backup: {backup_id}")
            return True
            
        except Exception as e:
            logging.error(f"Error deleting backup: {e}")
            return False
    
    def get_backup_info(self, backup_id: str) -> Optional[BackupInfo]:
        """Get information about a backup"""
        return self.backups.get(backup_id)
    
    def list_backups(self) -> List[BackupInfo]:
        """Get list of all backups"""
        return list(self.backups.values())
    
    def verify_backup(self, backup_id: str) -> bool:
        """Verify backup integrity"""
        try:
            if backup_id not in self.backups:
                raise ValueError(f"Backup not found: {backup_id}")
            
            backup = self.backups[backup_id]
            zip_path = self.backups_dir / f"{backup_id}.zip"
            
            if not zip_path.exists():
                raise FileNotFoundError(f"Backup file not found: {zip_path}")
            
            current_hash = self._calculate_hash(zip_path)
            return current_hash == backup.hash
            
        except Exception as e:
            logging.error(f"Error verifying backup: {e}")
            return False
    
    def _calculate_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of a file"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def get_total_backup_size(self) -> int:
        """Get total size of all backups"""
        return sum(backup.size for backup in self.backups.values())
    
    def cleanup_old_backups(self, max_backups: int = 10) -> int:
        """Remove oldest backups if total exceeds max_backups"""
        if len(self.backups) <= max_backups:
            return 0
        
        # Sort backups by timestamp
        sorted_backups = sorted(
            self.backups.items(),
            key=lambda x: x[1].timestamp
        )
        
        # Delete oldest backups
        deleted_count = 0
        for backup_id, _ in sorted_backups[:-max_backups]:
            if self.delete_backup(backup_id):
                deleted_count += 1
        
        return deleted_count
