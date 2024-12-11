import os
import psutil
import logging
import json
from pathlib import Path
from typing import Dict, List, Optional
import shutil
from datetime import datetime, timedelta
import threading
import time

class PerformanceOptimizer:
    def __init__(self):
        self.config_file = Path("config/performance.json")
        self.config = self.load_config()
        self.monitoring_thread = None
        self.running = True
        
        # Start monitoring
        self.start_monitoring()
    
    def load_config(self) -> dict:
        """Load performance configuration"""
        default_config = {
            "memory": {
                "warning_threshold": 80,  # Percentage
                "critical_threshold": 90
            },
            "cpu": {
                "warning_threshold": 70,
                "critical_threshold": 85
            },
            "disk": {
                "warning_threshold": 80,
                "critical_threshold": 90,
                "cleanup_threshold": 85
            },
            "process": {
                "max_idle_time": 3600,  # 1 hour
                "max_memory_percent": 25
            }
        }
        
        try:
            if self.config_file.exists():
                with open(self.config_file, "r") as f:
                    return {**default_config, **json.load(f)}
            return default_config
        except Exception as e:
            logging.error(f"Error loading performance config: {e}")
            return default_config
    
    def save_config(self):
        """Save performance configuration"""
        try:
            self.config_file.parent.mkdir(exist_ok=True)
            with open(self.config_file, "w") as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            logging.error(f"Error saving performance config: {e}")
    
    def optimize_memory(self) -> bool:
        """Optimize system memory usage"""
        try:
            memory = psutil.virtual_memory()
            if memory.percent >= self.config["memory"]["warning_threshold"]:
                # Get list of memory-intensive processes
                processes = []
                for proc in psutil.process_iter(['pid', 'name', 'memory_percent']):
                    try:
                        if proc.info['memory_percent'] > self.config["process"]["max_memory_percent"]:
                            processes.append(proc.info)
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                
                # Sort by memory usage and terminate most intensive ones
                processes.sort(key=lambda x: x['memory_percent'], reverse=True)
                for proc in processes[:3]:  # Terminate top 3 memory-intensive processes
                    try:
                        p = psutil.Process(proc['pid'])
                        p.terminate()
                        logging.info(f"Terminated memory-intensive process: {proc['name']}")
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        pass
                
                return True
        except Exception as e:
            logging.error(f"Error optimizing memory: {e}")
        return False
    
    def optimize_disk_space(self) -> bool:
        """Optimize disk space usage"""
        try:
            # Check disk usage
            disk = psutil.disk_usage('/')
            if disk.percent >= self.config["disk"]["cleanup_threshold"]:
                # Clean temporary files
                temp_dirs = [
                    os.environ.get('TEMP'),
                    os.environ.get('TMP'),
                    'C:/Windows/Temp'
                ]
                
                for temp_dir in temp_dirs:
                    if temp_dir and os.path.exists(temp_dir):
                        try:
                            # Remove files older than 7 days
                            cutoff = datetime.now() - timedelta(days=7)
                            for root, dirs, files in os.walk(temp_dir):
                                for file in files:
                                    file_path = os.path.join(root, file)
                                    try:
                                        if datetime.fromtimestamp(os.path.getctime(file_path)) < cutoff:
                                            os.remove(file_path)
                                    except (OSError, PermissionError):
                                        pass
                        except Exception as e:
                            logging.error(f"Error cleaning temp directory {temp_dir}: {e}")
                
                return True
        except Exception as e:
            logging.error(f"Error optimizing disk space: {e}")
        return False
    
    def optimize_startup(self) -> bool:
        """Optimize system startup"""
        try:
            # Get list of startup programs
            startup_paths = [
                os.path.join(os.environ['APPDATA'], 'Microsoft/Windows/Start Menu/Programs/Startup'),
                os.path.join(os.environ['PROGRAMDATA'], 'Microsoft/Windows/Start Menu/Programs/Startup')
            ]
            
            startup_items = []
            for path in startup_paths:
                if os.path.exists(path):
                    startup_items.extend([
                        os.path.join(path, item)
                        for item in os.listdir(path)
                        if os.path.isfile(os.path.join(path, item))
                    ])
            
            # Analyze and optimize startup items
            for item in startup_items:
                try:
                    # Check if the startup item is necessary
                    # This is a simplified example - in practice, you'd need more sophisticated analysis
                    file_stats = os.stat(item)
                    if datetime.fromtimestamp(file_stats.st_atime) < datetime.now() - timedelta(days=30):
                        # If the item hasn't been accessed in 30 days, disable it
                        backup_dir = Path("backup/startup")
                        backup_dir.mkdir(parents=True, exist_ok=True)
                        shutil.move(item, backup_dir / os.path.basename(item))
                        logging.info(f"Disabled unused startup item: {item}")
                except Exception as e:
                    logging.error(f"Error processing startup item {item}: {e}")
            
            return True
        except Exception as e:
            logging.error(f"Error optimizing startup: {e}")
        return False
    
    def analyze_performance(self) -> Dict[str, dict]:
        """Analyze system performance"""
        try:
            # Get CPU usage
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_freq = psutil.cpu_freq()
            cpu_stats = {
                "usage_percent": cpu_percent,
                "frequency": cpu_freq.current if cpu_freq else None,
                "status": "critical" if cpu_percent >= self.config["cpu"]["critical_threshold"]
                        else "warning" if cpu_percent >= self.config["cpu"]["warning_threshold"]
                        else "normal"
            }
            
            # Get memory usage
            memory = psutil.virtual_memory()
            memory_stats = {
                "total": memory.total,
                "available": memory.available,
                "used_percent": memory.percent,
                "status": "critical" if memory.percent >= self.config["memory"]["critical_threshold"]
                        else "warning" if memory.percent >= self.config["memory"]["warning_threshold"]
                        else "normal"
            }
            
            # Get disk usage
            disk = psutil.disk_usage('/')
            disk_stats = {
                "total": disk.total,
                "used": disk.used,
                "free": disk.free,
                "used_percent": disk.percent,
                "status": "critical" if disk.percent >= self.config["disk"]["critical_threshold"]
                        else "warning" if disk.percent >= self.config["disk"]["warning_threshold"]
                        else "normal"
            }
            
            return {
                "cpu": cpu_stats,
                "memory": memory_stats,
                "disk": disk_stats,
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            logging.error(f"Error analyzing performance: {e}")
            return {}
    
    def start_monitoring(self):
        """Start performance monitoring"""
        def monitor():
            while self.running:
                try:
                    stats = self.analyze_performance()
                    
                    # Check if optimization is needed
                    if stats.get("memory", {}).get("status") in ["warning", "critical"]:
                        self.optimize_memory()
                    
                    if stats.get("disk", {}).get("status") in ["warning", "critical"]:
                        self.optimize_disk_space()
                    
                    time.sleep(300)  # Check every 5 minutes
                    
                except Exception as e:
                    logging.error(f"Error in performance monitoring: {e}")
                    time.sleep(60)  # Wait a minute before retrying
        
        self.monitoring_thread = threading.Thread(target=monitor)
        self.monitoring_thread.daemon = True
        self.monitoring_thread.start()
    
    def stop_monitoring(self):
        """Stop performance monitoring"""
        self.running = False
        if self.monitoring_thread:
            self.monitoring_thread.join()
    
    def get_process_list(self) -> List[Dict[str, any]]:
        """Get list of running processes with resource usage"""
        processes = []
        try:
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'create_time']):
                try:
                    proc_info = proc.info
                    proc_info['running_time'] = datetime.now() - datetime.fromtimestamp(proc_info['create_time'])
                    processes.append(proc_info)
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except Exception as e:
            logging.error(f"Error getting process list: {e}")
        
        return sorted(processes, key=lambda x: x.get('cpu_percent', 0), reverse=True)
    
    def optimize_system(self) -> Dict[str, bool]:
        """Run all optimization tasks"""
        results = {
            "memory": self.optimize_memory(),
            "disk": self.optimize_disk_space(),
            "startup": self.optimize_startup()
        }
        return results
