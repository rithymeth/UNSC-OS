import os
import json
import logging
import shutil
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import py7zr
from dataclasses import dataclass
import hashlib
import schedule
import time
import threading

@dataclass
class RestorePoint:
    id: str
    name: str
    timestamp: str
    size: int
    description: Optional[str] = None
    auto_created: bool = False
    hash: Optional[str] = None

class RecoveryManager:
    def __init__(self):
        self.restore_points_dir = Path("restore_points")
        self.metadata_file = self.restore_points_dir / "metadata.json"
        self.restore_points: Dict[str, RestorePoint] = {}
        self.scheduler_thread = None
        self.running = True
        
        # Create restore points directory if it doesn't exist
        self.restore_points_dir.mkdir(exist_ok=True)
        
        # Load existing restore points metadata
        self.load_metadata()
        
        # Start scheduler
        self.start_scheduler()
    
    def load_metadata(self):
        """Load restore points metadata"""
        try:
            if self.metadata_file.exists():
                with open(self.metadata_file, "r") as f:
                    data = json.load(f)
                    self.restore_points = {
                        k: RestorePoint(**v) for k, v in data.items()
                    }
        except Exception as e:
            logging.error(f"Error loading restore points metadata: {e}")
            self.restore_points = {}
    
    def save_metadata(self):
        """Save restore points metadata"""
        try:
            with open(self.metadata_file, "w") as f:
                data = {
                    k: v.__dict__ for k, v in self.restore_points.items()
                }
                json.dump(data, f, indent=4)
        except Exception as e:
            logging.error(f"Error saving restore points metadata: {e}")
    
    def create_restore_point(
        self,
        name: str,
        paths: List[str],
        description: Optional[str] = None,
        auto_created: bool = False
    ) -> Optional[RestorePoint]:
        """Create a new restore point"""
        try:
            # Generate unique restore point ID
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            point_id = f"{name}_{timestamp}"
            
            # Create restore point archive
            archive_path = self.restore_points_dir / f"{point_id}.7z"
            
            total_size = 0
            with py7zr.SevenZipFile(archive_path, 'w') as archive:
                for path in paths:
                    src_path = Path(path)
                    if not src_path.exists():
                        logging.warning(f"Path not found: {path}")
                        continue
                    
                    if src_path.is_file():
                        archive.write(src_path, src_path.name)
                        total_size += src_path.stat().st_size
                    elif src_path.is_dir():
                        for file in src_path.rglob("*"):
                            if file.is_file():
                                archive.write(file, str(file.relative_to(src_path)))
                                total_size += file.stat().st_size
            
            # Calculate archive hash
            archive_hash = self._calculate_hash(archive_path)
            
            # Create restore point info
            restore_point = RestorePoint(
                id=point_id,
                name=name,
                timestamp=timestamp,
                size=total_size,
                description=description,
                auto_created=auto_created,
                hash=archive_hash
            )
            
            # Save restore point info
            self.restore_points[point_id] = restore_point
            self.save_metadata()
            
            logging.info(f"Created restore point: {point_id}")
            return restore_point
            
        except Exception as e:
            logging.error(f"Error creating restore point: {e}")
            return None
    
    def restore_system(
        self,
        point_id: str,
        target_path: Optional[str] = None
    ) -> bool:
        """Restore system from a restore point"""
        try:
            if point_id not in self.restore_points:
                raise ValueError(f"Restore point not found: {point_id}")
            
            point = self.restore_points[point_id]
            archive_path = self.restore_points_dir / f"{point_id}.7z"
            
            if not archive_path.exists():
                raise FileNotFoundError(f"Restore point archive not found: {archive_path}")
            
            # Verify archive integrity
            current_hash = self._calculate_hash(archive_path)
            if current_hash != point.hash:
                raise ValueError("Restore point integrity check failed")
            
            # Create temporary extraction directory
            extract_dir = self.restore_points_dir / f"restore_{point_id}"
            extract_dir.mkdir(exist_ok=True)
            
            # Extract archive
            with py7zr.SevenZipFile(archive_path, 'r') as archive:
                archive.extractall(extract_dir)
            
            # Restore files
            restore_base = Path(target_path) if target_path else Path()
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
            
            logging.info(f"Restored system from point: {point_id}")
            return True
            
        except Exception as e:
            logging.error(f"Error restoring system: {e}")
            return False
    
    def delete_restore_point(self, point_id: str) -> bool:
        """Delete a restore point"""
        try:
            if point_id not in self.restore_points:
                raise ValueError(f"Restore point not found: {point_id}")
            
            # Delete archive
            archive_path = self.restore_points_dir / f"{point_id}.7z"
            if archive_path.exists():
                archive_path.unlink()
            
            # Remove from metadata
            del self.restore_points[point_id]
            self.save_metadata()
            
            logging.info(f"Deleted restore point: {point_id}")
            return True
            
        except Exception as e:
            logging.error(f"Error deleting restore point: {e}")
            return False
    
    def get_restore_point_info(self, point_id: str) -> Optional[RestorePoint]:
        """Get information about a restore point"""
        return self.restore_points.get(point_id)
    
    def list_restore_points(self) -> List[RestorePoint]:
        """Get list of all restore points"""
        return list(self.restore_points.values())
    
    def verify_restore_point(self, point_id: str) -> bool:
        """Verify restore point integrity"""
        try:
            if point_id not in self.restore_points:
                raise ValueError(f"Restore point not found: {point_id}")
            
            point = self.restore_points[point_id]
            archive_path = self.restore_points_dir / f"{point_id}.7z"
            
            if not archive_path.exists():
                raise FileNotFoundError(f"Restore point archive not found: {archive_path}")
            
            current_hash = self._calculate_hash(archive_path)
            return current_hash == point.hash
            
        except Exception as e:
            logging.error(f"Error verifying restore point: {e}")
            return False
    
    def _calculate_hash(self, file_path: Path) -> str:
        """Calculate SHA-256 hash of a file"""
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    def get_total_restore_points_size(self) -> int:
        """Get total size of all restore points"""
        return sum(point.size for point in self.restore_points.values())
    
    def cleanup_old_restore_points(self, max_points: int = 5) -> int:
        """Remove oldest restore points if total exceeds max_points"""
        if len(self.restore_points) <= max_points:
            return 0
        
        # Sort restore points by timestamp
        sorted_points = sorted(
            self.restore_points.items(),
            key=lambda x: x[1].timestamp
        )
        
        # Delete oldest points
        deleted_count = 0
        for point_id, _ in sorted_points[:-max_points]:
            if self.delete_restore_point(point_id):
                deleted_count += 1
        
        return deleted_count
    
    def start_scheduler(self):
        """Start the scheduler for automatic restore points"""
        def run_scheduler():
            while self.running:
                schedule.run_pending()
                time.sleep(60)
        
        # Create weekly restore point
        schedule.every().sunday.at("00:00").do(
            self.create_restore_point,
            "weekly_auto",
            ["/"],
            "Weekly automatic restore point",
            True
        )
        
        # Create restore point before updates
        schedule.every().day.at("03:00").do(
            self.create_restore_point,
            "pre_update",
            ["/"],
            "Pre-update restore point",
            True
        )
        
        # Start scheduler thread
        self.scheduler_thread = threading.Thread(target=run_scheduler)
        self.scheduler_thread.daemon = True
        self.scheduler_thread.start()
    
    def stop_scheduler(self):
        """Stop the scheduler"""
        self.running = False
        if self.scheduler_thread:
            self.scheduler_thread.join()
            schedule.clear()
