import os
import json
import hashlib
import requests
import threading
import time
from datetime import datetime
import logging
from typing import Dict, List, Optional
from package_manager import PackageManager

class UpdateManager:
    def __init__(self, current_version: str = "1.0.0"):
        self.current_version = current_version
        self.update_url = "https://api.github.com/repos/unsc/unsc-os/releases/latest"
        self.update_check_interval = 86400  # Check once per day
        self.updates_dir = "updates"
        self.backup_dir = "backups"
        self.setup_logging()
        self.setup_directories()
        self._running = False
        self._update_thread = None
        self.observers = []
        self._last_check_time = 0
        self._check_cooldown = 300  # 5 minutes cooldown
        
        # Initialize package manager
        self.package_manager = PackageManager(os.path.dirname(os.path.abspath(__file__)))

    def setup_logging(self):
        """Setup logging for the update manager"""
        log_dir = "logs"
        if not os.path.exists(log_dir):
            os.makedirs(log_dir)
        
        logging.basicConfig(
            filename=os.path.join(log_dir, 'updater.log'),
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s'
        )

    def setup_directories(self):
        """Create necessary directories"""
        for directory in [self.updates_dir, self.backup_dir]:
            if not os.path.exists(directory):
                os.makedirs(directory)

    def create_backup(self) -> Optional[str]:
        """Create a system backup before updating"""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            backup_path = os.path.join(self.backup_dir, f"backup_{timestamp}")
            
            # Create restore point
            restore_point_id = self.package_manager.create_restore_point(
                f"Pre-update backup {timestamp}"
            )
            
            if restore_point_id == -1:
                logging.error("Failed to create restore point")
                return None

            # Save current version info
            version_info = {
                'version': self.current_version,
                'restore_point_id': restore_point_id,
                'timestamp': timestamp
            }
            
            os.makedirs(backup_path)
            with open(os.path.join(backup_path, 'version_info.json'), 'w') as f:
                json.dump(version_info, f)

            logging.info(f"Backup created successfully at {backup_path}")
            return backup_path
        except Exception as e:
            logging.error(f"Error creating backup: {e}")
            return None

    def restore_from_backup(self, backup_path: str) -> bool:
        """Restore system from a backup"""
        try:
            # Load version info
            version_info_path = os.path.join(backup_path, 'version_info.json')
            if not os.path.exists(version_info_path):
                logging.error("Invalid backup: missing version info")
                return False

            with open(version_info_path, 'r') as f:
                version_info = json.load(f)

            # Restore from restore point
            if not self.package_manager.restore_from_point(version_info['restore_point_id']):
                logging.error("Failed to restore from restore point")
                return False

            # Update current version
            self.current_version = version_info['version']
            logging.info(f"System restored to version {self.current_version}")
            return True
        except Exception as e:
            logging.error(f"Error restoring from backup: {e}")
            return False

    def list_available_backups(self) -> List[Dict]:
        """List available system backups"""
        backups = []
        try:
            for entry in os.listdir(self.backup_dir):
                backup_path = os.path.join(self.backup_dir, entry)
                version_info_path = os.path.join(backup_path, 'version_info.json')
                
                if os.path.isdir(backup_path) and os.path.exists(version_info_path):
                    with open(version_info_path, 'r') as f:
                        version_info = json.load(f)
                        backups.append({
                            'path': backup_path,
                            'version': version_info['version'],
                            'timestamp': version_info['timestamp']
                        })
        except Exception as e:
            logging.error(f"Error listing backups: {e}")
        
        return backups

    def install_update(self, file_path: str) -> bool:
        """Install the downloaded update"""
        try:
            logging.info("Creating system backup before update...")
            backup_path = self.create_backup()
            if not backup_path:
                logging.error("Update aborted: backup creation failed")
                return False

            logging.info("Installing update...")
            try:
                # Update core system packages
                self.package_manager.install_package(
                    "unsc-os-core",
                    "1.1.0",
                    []  # Core package has no dependencies
                )
                
                self.current_version = "1.1.0"
                logging.info(f"Update installed successfully. New version: {self.current_version}")
                return True
            except Exception as e:
                logging.error(f"Error during update installation: {e}")
                logging.info("Attempting to restore from backup...")
                if self.restore_from_backup(backup_path):
                    logging.info("System restored successfully")
                else:
                    logging.error("Failed to restore system")
                return False
        except Exception as e:
            logging.error(f"Error installing update: {e}")
            return False

    def check_for_updates(self) -> Optional[Dict]:
        """Check for available updates"""
        current_time = time.time()
        
        # Enforce cooldown period
        if current_time - self._last_check_time < self._check_cooldown:
            logging.info("Update check skipped: Still in cooldown period")
            return None
            
        try:
            logging.info("Checking for updates...")
            self._last_check_time = current_time
            
            # In a real implementation, this would check an actual update server
            # For demonstration, we'll simulate an update check
            return {
                'version': '1.1.0',
                'changes': [
                    'Added system health monitoring',
                    'Improved GUI performance',
                    'Added auto-update feature'
                ],
                'download_url': 'https://example.com/unsc-os-1.1.0.zip',
                'checksum': 'abc123',
                'release_date': datetime.now().isoformat()
            }
        except Exception as e:
            logging.error(f"Error checking for updates: {e}")
            return None

    def compare_versions(self, new_version: str) -> bool:
        """Compare versions to determine if update is needed"""
        current = [int(x) for x in self.current_version.split('.')]
        new = [int(x) for x in new_version.split('.')]
        return new > current

    def download_update(self, update_info: Dict) -> Optional[str]:
        """Download update package"""
        try:
            # Simulate download
            download_path = os.path.join(self.updates_dir, f"update-{update_info['version']}.zip")
            logging.info(f"Downloading update to {download_path}")
            
            # In a real implementation, this would actually download the file
            # For demonstration, we'll create a dummy file
            with open(download_path, 'w') as f:
                f.write("Update package contents")
            
            return download_path
        except Exception as e:
            logging.error(f"Error downloading update: {e}")
            return None

    def verify_update(self, file_path: str, expected_checksum: str) -> bool:
        """Verify update package integrity"""
        try:
            with open(file_path, 'rb') as f:
                contents = f.read()
                checksum = hashlib.sha256(contents).hexdigest()
                return checksum == expected_checksum
        except Exception as e:
            logging.error(f"Error verifying update: {e}")
            return False

    def add_observer(self, callback):
        """Add an observer for update notifications"""
        self.observers.append(callback)

    def notify_observers(self, message: str, update_info: Optional[Dict] = None):
        """Notify all observers of updates"""
        for observer in self.observers:
            observer(message, update_info)

    def start_auto_update_checker(self):
        """Start automatic update checking"""
        if self._update_thread is not None and self._update_thread.is_alive():
            return

        self._running = True
        self._update_thread = threading.Thread(target=self._auto_update_checker)
        self._update_thread.daemon = True
        self._update_thread.start()

    def stop_auto_update_checker(self):
        """Stop automatic update checking"""
        self._running = False
        if self._update_thread is not None:
            self._update_thread.join()

    def _auto_update_checker(self):
        """Background thread for checking updates"""
        last_auto_check = 0
        while self._running:
            current_time = time.time()
            if current_time - last_auto_check >= self.update_check_interval:
                update_info = self.check_for_updates()
                if update_info and self.compare_versions(update_info['version']):
                    self.notify_observers("Update available!", update_info)
                last_auto_check = current_time
            time.sleep(60)  # Check every minute if it's time for an update check

    def manual_update_check(self) -> bool:
        """Manually check and install updates"""
        current_time = time.time()
        
        # For manual checks, use a shorter cooldown
        if current_time - self._last_check_time < 30:  # 30 seconds cooldown for manual checks
            self.notify_observers("Please wait a moment before checking for updates again")
            return False
            
        update_info = self.check_for_updates()
        if not update_info:
            self.notify_observers("No updates available")
            return False

        if not self.compare_versions(update_info['version']):
            self.notify_observers("System is up to date")
            return False

        self.notify_observers("Update available!", update_info)
        download_path = self.download_update(update_info)
        
        if not download_path:
            self.notify_observers("Update download failed")
            return False

        if not self.verify_update(download_path, update_info['checksum']):
            self.notify_observers("Update verification failed")
            return False

        if self.install_update(download_path):
            self.notify_observers(f"Update installed successfully! New version: {self.current_version}")
            return True
        else:
            self.notify_observers("Update installation failed")
            return False
