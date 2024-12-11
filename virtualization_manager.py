import os
import logging
import json
from pathlib import Path
from typing import Dict, List, Optional
import docker
from docker.models.containers import Container
from docker.models.images import Image
import threading
import time
from datetime import datetime

class VirtualizationManager:
    def __init__(self):
        self.config_file = Path("config/virtualization.json")
        self.config = self.load_config()
        self.docker_client = None
        self.monitoring_thread = None
        self.running = True
        
        # Initialize Docker client
        self.initialize_docker()
        
        # Start monitoring if Docker is available
        if self.docker_client:
            self.start_monitoring()
    
    def load_config(self) -> dict:
        """Load virtualization configuration"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            return {
                "monitoring_interval": 30,
                "max_containers": 10,
                "default_network": "bridge",
                "resource_limits": {
                    "cpu": 1.0,
                    "memory": "2g"
                }
            }
        except Exception as e:
            logging.error(f"Error loading virtualization config: {e}")
            return {}

    def initialize_docker(self):
        """Initialize Docker client"""
        try:
            self.docker_client = docker.from_env()
            self.docker_client.ping()  # Test connection
            logging.info("Docker client initialized successfully")
        except Exception as e:
            logging.error(f"Error initializing Docker client: {e}")
            self.docker_client = None
            raise Exception("Docker service is not running. Please start Docker Desktop and run as administrator.")

    def list_containers(self) -> List[Dict]:
        """List all containers"""
        if not self.docker_client:
            return []
            
        try:
            containers = self.docker_client.containers.list(all=True)
            return [{
                'id': c.short_id,
                'name': c.name,
                'status': c.status,
                'image': c.image.tags[0] if c.image.tags else c.image.short_id,
                'created': c.attrs['Created']
            } for c in containers]
        except Exception as e:
            logging.error(f"Error listing containers: {e}")
            return []

    def list_images(self) -> List[Dict]:
        """List all images"""
        if not self.docker_client:
            return []
            
        try:
            images = self.docker_client.images.list()
            return [{
                'id': img.short_id,
                'tags': img.tags,
                'size': img.attrs['Size'],
                'created': img.attrs['Created']
            } for img in images]
        except Exception as e:
            logging.error(f"Error listing images: {e}")
            return []

    def create_container(self, image: str, name: Optional[str] = None, **kwargs) -> Optional[Container]:
        """Create a new container"""
        if not self.docker_client:
            return None
            
        try:
            # Apply resource limits from config
            if 'resource_limits' in self.config:
                kwargs.setdefault('cpu_quota', int(self.config['resource_limits']['cpu'] * 100000))
                kwargs.setdefault('mem_limit', self.config['resource_limits']['memory'])
            
            container = self.docker_client.containers.create(
                image,
                name=name,
                **kwargs
            )
            logging.info(f"Container created: {container.name}")
            return container
        except Exception as e:
            logging.error(f"Error creating container: {e}")
            return None

    def start_container(self, container_id: str) -> bool:
        """Start a container"""
        if not self.docker_client:
            return False
            
        try:
            container = self.docker_client.containers.get(container_id)
            container.start()
            logging.info(f"Container started: {container.name}")
            return True
        except Exception as e:
            logging.error(f"Error starting container: {e}")
            return False

    def stop_container(self, container_id: str) -> bool:
        """Stop a container"""
        if not self.docker_client:
            return False
            
        try:
            container = self.docker_client.containers.get(container_id)
            container.stop()
            logging.info(f"Container stopped: {container.name}")
            return True
        except Exception as e:
            logging.error(f"Error stopping container: {e}")
            return False

    def remove_container(self, container_id: str, force: bool = False) -> bool:
        """Remove a container"""
        if not self.docker_client:
            return False
            
        try:
            container = self.docker_client.containers.get(container_id)
            container.remove(force=force)
            logging.info(f"Container removed: {container.name}")
            return True
        except Exception as e:
            logging.error(f"Error removing container: {e}")
            return False

    def pull_image(self, image: str) -> Optional[Image]:
        """Pull a Docker image"""
        if not self.docker_client:
            return None
            
        try:
            image = self.docker_client.images.pull(image)
            logging.info(f"Image pulled: {image.tags[0] if image.tags else image.short_id}")
            return image
        except Exception as e:
            logging.error(f"Error pulling image: {e}")
            return None

    def remove_image(self, image: str, force: bool = False) -> bool:
        """Remove a Docker image"""
        if not self.docker_client:
            return False
            
        try:
            self.docker_client.images.remove(image, force=force)
            logging.info(f"Image removed: {image}")
            return True
        except Exception as e:
            logging.error(f"Error removing image: {e}")
            return False

    def get_container_stats(self, container_id: str) -> Dict:
        """Get container statistics"""
        if not self.docker_client:
            return {}
            
        try:
            container = self.docker_client.containers.get(container_id)
            stats = container.stats(stream=False)
            
            # Calculate CPU percentage
            cpu_delta = stats['cpu_stats']['cpu_usage']['total_usage'] - \
                       stats['precpu_stats']['cpu_usage']['total_usage']
            system_delta = stats['cpu_stats']['system_cpu_usage'] - \
                          stats['precpu_stats']['system_cpu_usage']
            cpu_percent = (cpu_delta / system_delta) * 100.0
            
            # Calculate memory usage
            mem_usage = stats['memory_stats']['usage']
            mem_limit = stats['memory_stats']['limit']
            mem_percent = (mem_usage / mem_limit) * 100.0
            
            return {
                'cpu_percent': round(cpu_percent, 2),
                'memory_usage': mem_usage,
                'memory_limit': mem_limit,
                'memory_percent': round(mem_percent, 2),
                'network_rx': stats['networks']['eth0']['rx_bytes'],
                'network_tx': stats['networks']['eth0']['tx_bytes']
            }
        except Exception as e:
            logging.error(f"Error getting container stats: {e}")
            return {}

    def start_monitoring(self):
        """Start the container monitoring thread"""
        self.monitoring_thread = threading.Thread(target=self._monitor_containers)
        self.monitoring_thread.daemon = True
        self.monitoring_thread.start()

    def _monitor_containers(self):
        """Monitor containers and log their status"""
        while self.running:
            if self.docker_client:
                try:
                    containers = self.list_containers()
                    for container in containers:
                        if container['status'] == 'running':
                            stats = self.get_container_stats(container['id'])
                            logging.info(f"Container {container['name']} stats: {stats}")
                except Exception as e:
                    logging.error(f"Error monitoring containers: {e}")
            time.sleep(self.config.get('monitoring_interval', 30))

    def stop(self):
        """Stop the virtualization manager"""
        self.running = False
        if self.monitoring_thread:
            self.monitoring_thread.join()
