import os
import logging
import json
from pathlib import Path
from typing import Dict, List, Optional, Union, BinaryIO
import threading
import queue
import time
from datetime import datetime
import boto3
from azure.storage.blob import BlobServiceClient
from google.cloud import storage
import hashlib
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor

@dataclass
class CloudFile:
    name: str
    size: int
    last_modified: datetime
    cloud_provider: str
    path: str
    hash: Optional[str] = None

class CloudManager:
    def __init__(self):
        self.config_file = Path("config/cloud.json")
        self.config = self.load_config()
        self.sync_queue = queue.Queue()
        self.sync_thread = None
        self.running = True
        
        # Initialize cloud clients
        self.initialize_cloud_clients()
        
        # Start sync thread
        self.start_sync_thread()
    
    def load_config(self) -> dict:
        """Load cloud configuration"""
        default_config = {
            "providers": {
                "aws": {
                    "enabled": False,
                    "region": "us-west-2",
                    "bucket": "unsc-os-storage"
                },
                "azure": {
                    "enabled": False,
                    "connection_string": "",
                    "container": "unsc-os-storage"
                },
                "gcp": {
                    "enabled": False,
                    "project": "",
                    "bucket": "unsc-os-storage"
                }
            },
            "sync": {
                "interval": 300,  # 5 minutes
                "max_file_size": 1024 * 1024 * 100,  # 100MB
                "excluded_extensions": [".tmp", ".log"],
                "sync_folders": ["documents", "pictures"]
            }
        }
        
        try:
            if self.config_file.exists():
                with open(self.config_file, "r") as f:
                    return {**default_config, **json.load(f)}
            return default_config
        except Exception as e:
            logging.error(f"Error loading cloud config: {e}")
            return default_config
    
    def save_config(self):
        """Save cloud configuration"""
        try:
            self.config_file.parent.mkdir(exist_ok=True)
            with open(self.config_file, "w") as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            logging.error(f"Error saving cloud config: {e}")
    
    def initialize_cloud_clients(self):
        """Initialize cloud service clients"""
        try:
            # Initialize AWS S3 client
            if self.config["providers"]["aws"]["enabled"]:
                self.s3_client = boto3.client("s3")
                logging.info("AWS S3 client initialized")
            else:
                self.s3_client = None
            
            # Initialize Azure Blob client
            if self.config["providers"]["azure"]["enabled"]:
                self.azure_client = BlobServiceClient.from_connection_string(
                    self.config["providers"]["azure"]["connection_string"]
                )
                logging.info("Azure Blob client initialized")
            else:
                self.azure_client = None
            
            # Initialize Google Cloud Storage client
            if self.config["providers"]["gcp"]["enabled"]:
                self.gcs_client = storage.Client(
                    project=self.config["providers"]["gcp"]["project"]
                )
                logging.info("Google Cloud Storage client initialized")
            else:
                self.gcs_client = None
            
        except Exception as e:
            logging.error(f"Error initializing cloud clients: {e}")
            raise
    
    def start_sync_thread(self):
        """Start cloud sync thread"""
        def sync():
            while self.running:
                try:
                    # Process sync queue
                    while not self.sync_queue.empty():
                        sync_item = self.sync_queue.get()
                        self.process_sync_item(sync_item)
                    
                    # Run scheduled sync
                    self.sync_all()
                    
                    time.sleep(self.config["sync"]["interval"])
                    
                except Exception as e:
                    logging.error(f"Error in cloud sync: {e}")
                    time.sleep(60)
        
        self.sync_thread = threading.Thread(target=sync)
        self.sync_thread.daemon = True
        self.sync_thread.start()
    
    def stop_sync_thread(self):
        """Stop cloud sync thread"""
        self.running = False
        if self.sync_thread:
            self.sync_thread.join()
    
    def process_sync_item(self, item: Dict):
        """Process sync queue item"""
        try:
            action = item.get("action")
            file_path = item.get("path")
            provider = item.get("provider")
            
            if action == "upload":
                self.upload_file(file_path, provider)
            elif action == "download":
                self.download_file(file_path, provider)
            elif action == "delete":
                self.delete_file(file_path, provider)
            
        except Exception as e:
            logging.error(f"Error processing sync item: {e}")
    
    def sync_all(self):
        """Synchronize all configured folders with cloud storage"""
        try:
            for folder in self.config["sync"]["sync_folders"]:
                local_path = Path(folder)
                if not local_path.exists():
                    continue
                
                # Get local files
                local_files = self._get_local_files(local_path)
                
                # Get cloud files
                cloud_files = self._get_cloud_files(folder)
                
                # Compare and sync
                self._sync_files(local_files, cloud_files, folder)
            
        except Exception as e:
            logging.error(f"Error in full sync: {e}")
    
    def _get_local_files(self, path: Path) -> Dict[str, CloudFile]:
        """Get list of local files"""
        files = {}
        try:
            for file_path in path.rglob("*"):
                if file_path.is_file():
                    if any(file_path.suffix == ext for ext in self.config["sync"]["excluded_extensions"]):
                        continue
                    
                    relative_path = str(file_path.relative_to(path))
                    files[relative_path] = CloudFile(
                        name=file_path.name,
                        size=file_path.stat().st_size,
                        last_modified=datetime.fromtimestamp(file_path.stat().st_mtime),
                        cloud_provider="local",
                        path=str(file_path),
                        hash=self._calculate_file_hash(file_path)
                    )
            
            return files
            
        except Exception as e:
            logging.error(f"Error getting local files: {e}")
            return {}
    
    def _get_cloud_files(self, prefix: str) -> Dict[str, Dict[str, CloudFile]]:
        """Get list of files from all cloud providers"""
        files = {
            "aws": {},
            "azure": {},
            "gcp": {}
        }
        
        try:
            # Get AWS S3 files
            if self.s3_client:
                response = self.s3_client.list_objects_v2(
                    Bucket=self.config["providers"]["aws"]["bucket"],
                    Prefix=prefix
                )
                for obj in response.get("Contents", []):
                    files["aws"][obj["Key"]] = CloudFile(
                        name=Path(obj["Key"]).name,
                        size=obj["Size"],
                        last_modified=obj["LastModified"],
                        cloud_provider="aws",
                        path=obj["Key"]
                    )
            
            # Get Azure Blob files
            if self.azure_client:
                container = self.azure_client.get_container_client(
                    self.config["providers"]["azure"]["container"]
                )
                for blob in container.list_blobs(name_starts_with=prefix):
                    files["azure"][blob.name] = CloudFile(
                        name=Path(blob.name).name,
                        size=blob.size,
                        last_modified=blob.last_modified,
                        cloud_provider="azure",
                        path=blob.name
                    )
            
            # Get Google Cloud Storage files
            if self.gcs_client:
                bucket = self.gcs_client.bucket(
                    self.config["providers"]["gcp"]["bucket"]
                )
                for blob in bucket.list_blobs(prefix=prefix):
                    files["gcp"][blob.name] = CloudFile(
                        name=Path(blob.name).name,
                        size=blob.size,
                        last_modified=blob.updated,
                        cloud_provider="gcp",
                        path=blob.name
                    )
            
            return files
            
        except Exception as e:
            logging.error(f"Error getting cloud files: {e}")
            return files
    
    def _sync_files(
        self,
        local_files: Dict[str, CloudFile],
        cloud_files: Dict[str, Dict[str, CloudFile]],
        base_path: str
    ):
        """Synchronize files between local and cloud storage"""
        try:
            # Process each cloud provider
            for provider, provider_files in cloud_files.items():
                if not self.config["providers"][provider]["enabled"]:
                    continue
                
                # Find files to upload
                for path, local_file in local_files.items():
                    if path not in provider_files:
                        self.sync_queue.put({
                            "action": "upload",
                            "path": local_file.path,
                            "provider": provider
                        })
                    else:
                        cloud_file = provider_files[path]
                        if local_file.hash and local_file.hash != cloud_file.hash:
                            self.sync_queue.put({
                                "action": "upload",
                                "path": local_file.path,
                                "provider": provider
                            })
                
                # Find files to download
                for path, cloud_file in provider_files.items():
                    if path not in local_files:
                        self.sync_queue.put({
                            "action": "download",
                            "path": cloud_file.path,
                            "provider": provider
                        })
            
        except Exception as e:
            logging.error(f"Error syncing files: {e}")
    
    def upload_file(self, file_path: str, provider: str) -> bool:
        """Upload file to cloud storage"""
        try:
            file_path = Path(file_path)
            if not file_path.exists():
                return False
            
            relative_path = str(file_path.relative_to(Path.cwd()))
            
            if provider == "aws":
                self.s3_client.upload_file(
                    str(file_path),
                    self.config["providers"]["aws"]["bucket"],
                    relative_path
                )
            elif provider == "azure":
                blob_client = self.azure_client.get_blob_client(
                    container=self.config["providers"]["azure"]["container"],
                    blob=relative_path
                )
                with open(file_path, "rb") as data:
                    blob_client.upload_blob(data, overwrite=True)
            elif provider == "gcp":
                bucket = self.gcs_client.bucket(
                    self.config["providers"]["gcp"]["bucket"]
                )
                blob = bucket.blob(relative_path)
                blob.upload_from_filename(str(file_path))
            
            logging.info(f"Uploaded {file_path} to {provider}")
            return True
            
        except Exception as e:
            logging.error(f"Error uploading file: {e}")
            return False
    
    def download_file(self, file_path: str, provider: str) -> bool:
        """Download file from cloud storage"""
        try:
            local_path = Path(file_path)
            local_path.parent.mkdir(parents=True, exist_ok=True)
            
            if provider == "aws":
                self.s3_client.download_file(
                    self.config["providers"]["aws"]["bucket"],
                    file_path,
                    str(local_path)
                )
            elif provider == "azure":
                blob_client = self.azure_client.get_blob_client(
                    container=self.config["providers"]["azure"]["container"],
                    blob=file_path
                )
                with open(local_path, "wb") as data:
                    data.write(blob_client.download_blob().readall())
            elif provider == "gcp":
                bucket = self.gcs_client.bucket(
                    self.config["providers"]["gcp"]["bucket"]
                )
                blob = bucket.blob(file_path)
                blob.download_to_filename(str(local_path))
            
            logging.info(f"Downloaded {file_path} from {provider}")
            return True
            
        except Exception as e:
            logging.error(f"Error downloading file: {e}")
            return False
    
    def delete_file(self, file_path: str, provider: str) -> bool:
        """Delete file from cloud storage"""
        try:
            if provider == "aws":
                self.s3_client.delete_object(
                    Bucket=self.config["providers"]["aws"]["bucket"],
                    Key=file_path
                )
            elif provider == "azure":
                blob_client = self.azure_client.get_blob_client(
                    container=self.config["providers"]["azure"]["container"],
                    blob=file_path
                )
                blob_client.delete_blob()
            elif provider == "gcp":
                bucket = self.gcs_client.bucket(
                    self.config["providers"]["gcp"]["bucket"]
                )
                blob = bucket.blob(file_path)
                blob.delete()
            
            logging.info(f"Deleted {file_path} from {provider}")
            return True
            
        except Exception as e:
            logging.error(f"Error deleting file: {e}")
            return False
    
    def _calculate_file_hash(self, file_path: Path) -> Optional[str]:
        """Calculate SHA-256 hash of a file"""
        try:
            sha256_hash = hashlib.sha256()
            with open(file_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except Exception as e:
            logging.error(f"Error calculating file hash: {e}")
            return None
    
    def get_storage_usage(self) -> Dict[str, Dict]:
        """Get storage usage for each cloud provider"""
        usage = {}
        
        try:
            # Get AWS S3 usage
            if self.s3_client:
                response = self.s3_client.list_objects_v2(
                    Bucket=self.config["providers"]["aws"]["bucket"]
                )
                usage["aws"] = {
                    "files": response.get("KeyCount", 0),
                    "size": sum(obj["Size"] for obj in response.get("Contents", []))
                }
            
            # Get Azure Blob usage
            if self.azure_client:
                container = self.azure_client.get_container_client(
                    self.config["providers"]["azure"]["container"]
                )
                blobs = list(container.list_blobs())
                usage["azure"] = {
                    "files": len(blobs),
                    "size": sum(blob.size for blob in blobs)
                }
            
            # Get Google Cloud Storage usage
            if self.gcs_client:
                bucket = self.gcs_client.bucket(
                    self.config["providers"]["gcp"]["bucket"]
                )
                blobs = list(bucket.list_blobs())
                usage["gcp"] = {
                    "files": len(blobs),
                    "size": sum(blob.size for blob in blobs)
                }
            
            return usage
            
        except Exception as e:
            logging.error(f"Error getting storage usage: {e}")
            return {}
