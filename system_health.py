import psutil
import time
import logging
from typing import Dict, List, Tuple
from datetime import datetime

class SystemHealthMonitor:
    def __init__(self):
        self.setup_logging()
        self.thresholds = {
            'cpu_percent': 80.0,  # Alert if CPU usage > 80%
            'memory_percent': 85.0,  # Alert if memory usage > 85%
            'disk_percent': 90.0,  # Alert if disk usage > 90%
            'temperature': 80.0,  # Alert if CPU temp > 80°C
        }
        self.history_size = 100  # Keep last 100 measurements
        self.history = []

    def setup_logging(self):
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            filename='system_health.log'
        )
        self.logger = logging.getLogger('SystemHealth')

    def get_cpu_stats(self) -> Dict:
        """Get CPU statistics"""
        try:
            cpu_percent = psutil.cpu_percent(interval=1)
            cpu_freq = psutil.cpu_freq()
            cpu_count = psutil.cpu_count()
            
            return {
                'usage_percent': cpu_percent,
                'frequency_mhz': cpu_freq.current if cpu_freq else None,
                'core_count': cpu_count
            }
        except Exception as e:
            self.logger.error(f"Error getting CPU stats: {e}")
            return {}

    def get_memory_stats(self) -> Dict:
        """Get memory statistics"""
        try:
            memory = psutil.virtual_memory()
            return {
                'total_gb': memory.total / (1024**3),
                'available_gb': memory.available / (1024**3),
                'used_percent': memory.percent
            }
        except Exception as e:
            self.logger.error(f"Error getting memory stats: {e}")
            return {}

    def get_disk_stats(self) -> List[Dict]:
        """Get disk statistics for all partitions"""
        try:
            disks = []
            for partition in psutil.disk_partitions():
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    disks.append({
                        'device': partition.device,
                        'mountpoint': partition.mountpoint,
                        'total_gb': usage.total / (1024**3),
                        'used_gb': usage.used / (1024**3),
                        'used_percent': usage.percent
                    })
                except Exception:
                    continue
            return disks
        except Exception as e:
            self.logger.error(f"Error getting disk stats: {e}")
            return []

    def get_network_stats(self) -> Dict:
        """Get network statistics"""
        try:
            net_io = psutil.net_io_counters()
            return {
                'bytes_sent': net_io.bytes_sent,
                'bytes_recv': net_io.bytes_recv,
                'packets_sent': net_io.packets_sent,
                'packets_recv': net_io.packets_recv
            }
        except Exception as e:
            self.logger.error(f"Error getting network stats: {e}")
            return {}

    def check_system_health(self) -> Tuple[bool, List[str]]:
        """Check system health against thresholds"""
        warnings = []
        is_healthy = True

        # Check CPU
        cpu_stats = self.get_cpu_stats()
        if cpu_stats.get('usage_percent', 0) > self.thresholds['cpu_percent']:
            warnings.append(f"High CPU usage: {cpu_stats['usage_percent']}%")
            is_healthy = False

        # Check Memory
        memory_stats = self.get_memory_stats()
        if memory_stats.get('used_percent', 0) > self.thresholds['memory_percent']:
            warnings.append(f"High memory usage: {memory_stats['used_percent']}%")
            is_healthy = False

        # Check Disks
        for disk in self.get_disk_stats():
            if disk.get('used_percent', 0) > self.thresholds['disk_percent']:
                warnings.append(f"High disk usage on {disk['mountpoint']}: {disk['used_percent']}%")
                is_healthy = False

        return is_healthy, warnings

    def get_system_snapshot(self) -> Dict:
        """Get a complete snapshot of system health"""
        snapshot = {
            'timestamp': datetime.now().isoformat(),
            'cpu': self.get_cpu_stats(),
            'memory': self.get_memory_stats(),
            'disks': self.get_disk_stats(),
            'network': self.get_network_stats()
        }

        # Add to history and maintain history size
        self.history.append(snapshot)
        if len(self.history) > self.history_size:
            self.history.pop(0)

        return snapshot

    def get_health_report(self) -> Dict:
        """Generate a complete health report"""
        is_healthy, warnings = self.check_system_health()
        snapshot = self.get_system_snapshot()

        return {
            'status': 'healthy' if is_healthy else 'warning',
            'warnings': warnings,
            'snapshot': snapshot,
            'history_size': len(self.history)
        }

    def set_threshold(self, metric: str, value: float):
        """Update threshold for a specific metric"""
        if metric in self.thresholds:
            self.thresholds[metric] = value
            self.logger.info(f"Updated {metric} threshold to {value}")
        else:
            self.logger.error(f"Unknown metric: {metric}")

    def get_performance_trends(self) -> Dict:
        """Analyze system performance trends"""
        if not self.history:
            return {}

        cpu_trend = []
        memory_trend = []
        
        for snapshot in self.history:
            cpu_trend.append(snapshot['cpu'].get('usage_percent', 0))
            memory_trend.append(snapshot['memory'].get('used_percent', 0))

        return {
            'cpu_trend': {
                'average': sum(cpu_trend) / len(cpu_trend),
                'max': max(cpu_trend),
                'min': min(cpu_trend)
            },
            'memory_trend': {
                'average': sum(memory_trend) / len(memory_trend),
                'max': max(memory_trend),
                'min': min(memory_trend)
            }
        }
