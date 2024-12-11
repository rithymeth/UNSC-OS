import os
import logging
import json
from pathlib import Path
from typing import Dict, List, Optional, Union
import docker
from docker.models.containers import Container
from docker.models.images import Image
import kubernetes
from kubernetes import client, config
import threading
import queue
import time
from datetime import datetime
import psutil
import shutil

class VirtualizationManager:
    def __init__(self):
        self.config_file = Path("config/virtualization.json")
        self.config = self.load_config()
        self.docker_client = None
        self.k8s_client = None
        self.monitoring_thread = None
        self.running = True
        
        # Initialize virtualization
        self.initialize_virtualization()
        
        # Start monitoring
        self.start_monitoring()
    
    def load_config(self) -> dict:
        """Load virtualization configuration"""
        default_config = {
            "docker": {
                "enabled": True,
                "max_containers": 10,
                "default_network": "bridge",
                "resource_limits": {
                    "cpu": 2.0,
                    "memory": "2g",
                    "storage": "10g"
                }
            },
            "kubernetes": {
                "enabled": False,
                "context": "docker-desktop",
                "namespace": "default",
                "resource_limits": {
                    "cpu": "4",
                    "memory": "4Gi",
                    "storage": "20Gi"
                }
            },
            "monitoring": {
                "interval": 30,  # seconds
                "resource_threshold": 80  # percent
            }
        }
        
        try:
            if self.config_file.exists():
                with open(self.config_file, "r") as f:
                    return {**default_config, **json.load(f)}
            return default_config
        except Exception as e:
            logging.error(f"Error loading virtualization config: {e}")
            return default_config
    
    def save_config(self):
        """Save virtualization configuration"""
        try:
            self.config_file.parent.mkdir(exist_ok=True)
            with open(self.config_file, "w") as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            logging.error(f"Error saving virtualization config: {e}")
    
    def initialize_virtualization(self):
        """Initialize virtualization components"""
        try:
            # Initialize Docker client
            if self.config["docker"]["enabled"]:
                self.docker_client = docker.from_env()
                logging.info("Docker client initialized")
            
            # Initialize Kubernetes client
            if self.config["kubernetes"]["enabled"]:
                config.load_kube_config(context=self.config["kubernetes"]["context"])
                self.k8s_client = client.CoreV1Api()
                logging.info("Kubernetes client initialized")
            
        except Exception as e:
            logging.error(f"Error initializing virtualization: {e}")
            raise
    
    def start_monitoring(self):
        """Start virtualization monitoring"""
        def monitor():
            while self.running:
                try:
                    # Monitor Docker containers
                    if self.docker_client:
                        self.monitor_containers()
                    
                    # Monitor Kubernetes resources
                    if self.k8s_client:
                        self.monitor_kubernetes()
                    
                    time.sleep(self.config["monitoring"]["interval"])
                    
                except Exception as e:
                    logging.error(f"Error in virtualization monitoring: {e}")
                    time.sleep(60)
        
        self.monitoring_thread = threading.Thread(target=monitor)
        self.monitoring_thread.daemon = True
        self.monitoring_thread.start()
    
    def stop_monitoring(self):
        """Stop virtualization monitoring"""
        self.running = False
        if self.monitoring_thread:
            self.monitoring_thread.join()
    
    def monitor_containers(self):
        """Monitor Docker containers"""
        try:
            containers = self.docker_client.containers.list()
            
            for container in containers:
                stats = container.stats(stream=False)
                
                # Calculate CPU usage
                cpu_delta = stats["cpu_stats"]["cpu_usage"]["total_usage"] - \
                           stats["precpu_stats"]["cpu_usage"]["total_usage"]
                system_delta = stats["cpu_stats"]["system_cpu_usage"] - \
                             stats["precpu_stats"]["system_cpu_usage"]
                cpu_percent = (cpu_delta / system_delta) * 100.0
                
                # Calculate memory usage
                memory_usage = stats["memory_stats"]["usage"]
                memory_limit = stats["memory_stats"]["limit"]
                memory_percent = (memory_usage / memory_limit) * 100.0
                
                # Check resource thresholds
                if cpu_percent > self.config["monitoring"]["resource_threshold"] or \
                   memory_percent > self.config["monitoring"]["resource_threshold"]:
                    logging.warning(
                        f"Container {container.name} exceeding resource limits: "
                        f"CPU: {cpu_percent:.1f}%, Memory: {memory_percent:.1f}%"
                    )
                
        except Exception as e:
            logging.error(f"Error monitoring containers: {e}")
    
    def monitor_kubernetes(self):
        """Monitor Kubernetes resources"""
        try:
            pods = self.k8s_client.list_namespaced_pod(
                namespace=self.config["kubernetes"]["namespace"]
            )
            
            for pod in pods.items:
                # Check pod status
                if pod.status.phase not in ["Running", "Succeeded"]:
                    logging.warning(
                        f"Pod {pod.metadata.name} in non-running state: "
                        f"{pod.status.phase}"
                    )
                
                # Check container statuses
                if pod.status.container_statuses:
                    for container in pod.status.container_statuses:
                        if not container.ready:
                            logging.warning(
                                f"Container {container.name} in pod "
                                f"{pod.metadata.name} not ready"
                            )
                
        except Exception as e:
            logging.error(f"Error monitoring Kubernetes: {e}")
    
    def create_container(
        self,
        image: str,
        name: Optional[str] = None,
        command: Optional[str] = None,
        environment: Optional[Dict[str, str]] = None,
        ports: Optional[Dict[str, str]] = None,
        volumes: Optional[Dict[str, Dict[str, str]]] = None
    ) -> Optional[Container]:
        """Create and start a Docker container"""
        try:
            # Check container limit
            current_containers = len(self.docker_client.containers.list())
            if current_containers >= self.config["docker"]["max_containers"]:
                raise ValueError("Maximum container limit reached")
            
            # Create container
            container = self.docker_client.containers.run(
                image,
                name=name,
                command=command,
                environment=environment,
                ports=ports,
                volumes=volumes,
                detach=True,
                network=self.config["docker"]["default_network"],
                cpu_count=float(self.config["docker"]["resource_limits"]["cpu"]),
                mem_limit=self.config["docker"]["resource_limits"]["memory"]
            )
            
            logging.info(f"Created container: {container.name}")
            return container
            
        except Exception as e:
            logging.error(f"Error creating container: {e}")
            return None
    
    def stop_container(self, container_id: str) -> bool:
        """Stop a Docker container"""
        try:
            container = self.docker_client.containers.get(container_id)
            container.stop()
            logging.info(f"Stopped container: {container.name}")
            return True
            
        except Exception as e:
            logging.error(f"Error stopping container: {e}")
            return False
    
    def remove_container(self, container_id: str, force: bool = False) -> bool:
        """Remove a Docker container"""
        try:
            container = self.docker_client.containers.get(container_id)
            container.remove(force=force)
            logging.info(f"Removed container: {container.name}")
            return True
            
        except Exception as e:
            logging.error(f"Error removing container: {e}")
            return False
    
    def create_kubernetes_deployment(
        self,
        name: str,
        image: str,
        replicas: int = 1,
        ports: Optional[List[int]] = None,
        environment: Optional[Dict[str, str]] = None
    ) -> bool:
        """Create a Kubernetes deployment"""
        try:
            # Create deployment object
            container = client.V1Container(
                name=name,
                image=image,
                ports=[client.V1ContainerPort(container_port=p) for p in (ports or [])],
                env=[
                    client.V1EnvVar(name=k, value=v)
                    for k, v in (environment or {}).items()
                ],
                resources=client.V1ResourceRequirements(
                    limits={
                        "cpu": self.config["kubernetes"]["resource_limits"]["cpu"],
                        "memory": self.config["kubernetes"]["resource_limits"]["memory"]
                    }
                )
            )
            
            template = client.V1PodTemplateSpec(
                metadata=client.V1ObjectMeta(labels={"app": name}),
                spec=client.V1PodSpec(containers=[container])
            )
            
            spec = client.V1DeploymentSpec(
                replicas=replicas,
                template=template,
                selector=client.V1LabelSelector(
                    match_labels={"app": name}
                )
            )
            
            deployment = client.V1Deployment(
                api_version="apps/v1",
                kind="Deployment",
                metadata=client.V1ObjectMeta(name=name),
                spec=spec
            )
            
            # Create deployment
            api = client.AppsV1Api()
            api.create_namespaced_deployment(
                body=deployment,
                namespace=self.config["kubernetes"]["namespace"]
            )
            
            logging.info(f"Created Kubernetes deployment: {name}")
            return True
            
        except Exception as e:
            logging.error(f"Error creating Kubernetes deployment: {e}")
            return False
    
    def delete_kubernetes_deployment(self, name: str) -> bool:
        """Delete a Kubernetes deployment"""
        try:
            api = client.AppsV1Api()
            api.delete_namespaced_deployment(
                name=name,
                namespace=self.config["kubernetes"]["namespace"]
            )
            
            logging.info(f"Deleted Kubernetes deployment: {name}")
            return True
            
        except Exception as e:
            logging.error(f"Error deleting Kubernetes deployment: {e}")
            return False
    
    def create_snapshot(self, container_id: str) -> Optional[str]:
        """Create a container snapshot"""
        try:
            container = self.docker_client.containers.get(container_id)
            snapshot = container.commit()
            
            # Save snapshot details
            snapshot_id = snapshot.id
            snapshot_path = Path(f"snapshots/{container.name}")
            snapshot_path.parent.mkdir(exist_ok=True)
            
            with open(snapshot_path / f"{snapshot_id}.json", "w") as f:
                json.dump({
                    "id": snapshot_id,
                    "container": container.name,
                    "created": datetime.now().isoformat(),
                    "config": container.attrs["Config"]
                }, f, indent=4)
            
            logging.info(f"Created snapshot for container {container.name}: {snapshot_id}")
            return snapshot_id
            
        except Exception as e:
            logging.error(f"Error creating snapshot: {e}")
            return None
    
    def restore_snapshot(self, snapshot_id: str) -> Optional[Container]:
        """Restore a container from snapshot"""
        try:
            # Find snapshot image
            image = self.docker_client.images.get(snapshot_id)
            
            # Load snapshot config
            snapshot_files = list(Path("snapshots").rglob(f"{snapshot_id}.json"))
            if not snapshot_files:
                raise ValueError(f"Snapshot config not found: {snapshot_id}")
            
            with open(snapshot_files[0], "r") as f:
                config = json.load(f)
            
            # Create new container from snapshot
            container = self.docker_client.containers.run(
                image.id,
                detach=True,
                **config["config"]
            )
            
            logging.info(f"Restored container from snapshot: {snapshot_id}")
            return container
            
        except Exception as e:
            logging.error(f"Error restoring snapshot: {e}")
            return None
    
    def get_container_logs(self, container_id: str, tail: int = 100) -> Optional[str]:
        """Get container logs"""
        try:
            container = self.docker_client.containers.get(container_id)
            return container.logs(tail=tail).decode()
            
        except Exception as e:
            logging.error(f"Error getting container logs: {e}")
            return None
    
    def get_container_stats(self, container_id: str) -> Optional[Dict]:
        """Get container resource statistics"""
        try:
            container = self.docker_client.containers.get(container_id)
            stats = container.stats(stream=False)
            
            return {
                "id": container.id,
                "name": container.name,
                "status": container.status,
                "cpu_usage": stats["cpu_stats"]["cpu_usage"]["total_usage"],
                "memory_usage": stats["memory_stats"]["usage"],
                "network_rx": stats["networks"]["eth0"]["rx_bytes"],
                "network_tx": stats["networks"]["eth0"]["tx_bytes"]
            }
            
        except Exception as e:
            logging.error(f"Error getting container stats: {e}")
            return None
    
    def get_kubernetes_resources(self) -> Dict[str, List]:
        """Get Kubernetes resource usage"""
        try:
            resources = {
                "pods": [],
                "services": [],
                "deployments": []
            }
            
            # Get pods
            pods = self.k8s_client.list_namespaced_pod(
                namespace=self.config["kubernetes"]["namespace"]
            )
            resources["pods"] = [
                {
                    "name": pod.metadata.name,
                    "status": pod.status.phase,
                    "ip": pod.status.pod_ip,
                    "node": pod.spec.node_name
                }
                for pod in pods.items
            ]
            
            # Get services
            services = self.k8s_client.list_namespaced_service(
                namespace=self.config["kubernetes"]["namespace"]
            )
            resources["services"] = [
                {
                    "name": svc.metadata.name,
                    "type": svc.spec.type,
                    "cluster_ip": svc.spec.cluster_ip,
                    "ports": [
                        {
                            "port": port.port,
                            "target_port": port.target_port
                        }
                        for port in svc.spec.ports
                    ]
                }
                for svc in services.items
            ]
            
            # Get deployments
            api = client.AppsV1Api()
            deployments = api.list_namespaced_deployment(
                namespace=self.config["kubernetes"]["namespace"]
            )
            resources["deployments"] = [
                {
                    "name": dep.metadata.name,
                    "replicas": dep.spec.replicas,
                    "available": dep.status.available_replicas
                }
                for dep in deployments.items
            ]
            
            return resources
            
        except Exception as e:
            logging.error(f"Error getting Kubernetes resources: {e}")
            return {}
