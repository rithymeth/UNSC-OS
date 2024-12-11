import logging
import json
from pathlib import Path
from typing import Dict, List, Optional
import threading
import queue
import time
from datetime import datetime

class AIAssistant:
    def __init__(self):
        self.config_file = Path("config/ai_assistant.json")
        self.config = self.load_config()
        self.command_history: List[Dict] = []
        self.message_queue = queue.Queue()
        self.processing_thread = None
        self.running = True
        
        # Command patterns for natural language processing
        self.command_patterns = {
            'system': ['status', 'health', 'performance', 'resources'],
            'network': ['connection', 'bandwidth', 'traffic', 'ports'],
            'security': ['threats', 'vulnerabilities', 'firewall', 'attacks'],
            'storage': ['space', 'disk', 'memory', 'usage']
        }
        
        # Start processing thread
        self.start_processing()
    
    def load_config(self) -> dict:
        """Load AI assistant configuration"""
        try:
            if self.config_file.exists():
                with open(self.config_file, 'r') as f:
                    return json.load(f)
            return {
                "response_delay": 0.5,
                "confidence_threshold": 0.7,
                "max_history": 100
            }
        except Exception as e:
            logging.error(f"Error loading AI config: {e}")
            return {}

    def process_command(self, args: List[str]) -> str:
        """Process natural language commands"""
        if not args:
            return "Please provide a command."
            
        command = " ".join(args).lower()
        
        # Check for system commands
        if any(word in command for word in self.command_patterns['system']):
            return self.analyze_system()
            
        # Check for network commands
        if any(word in command for word in self.command_patterns['network']):
            return self.analyze_network()
            
        # Check for security commands
        if any(word in command for word in self.command_patterns['security']):
            return self.analyze_security()
            
        # Check for storage commands
        if any(word in command for word in self.command_patterns['storage']):
            return self.analyze_storage()
            
        return "I'm not sure how to help with that. Try asking about system, network, security, or storage."

    def analyze_system(self) -> str:
        """Analyze system health and performance"""
        try:
            import psutil
            cpu_percent = psutil.cpu_percent(interval=1)
            memory = psutil.virtual_memory()
            disk = psutil.disk_usage('/')
            
            return f"""System Analysis:
- CPU Usage: {cpu_percent}%
- Memory Usage: {memory.percent}%
- Disk Usage: {disk.percent}%
Recommendation: {"System resources are optimal" if all(x < 80 for x in [cpu_percent, memory.percent, disk.percent]) else "Consider optimizing resource usage"}"""
        except Exception as e:
            return f"Error analyzing system: {e}"

    def analyze_network(self) -> str:
        """Analyze network status and performance"""
        try:
            import psutil
            net_io = psutil.net_io_counters()
            connections = len(psutil.net_connections())
            
            return f"""Network Analysis:
- Active Connections: {connections}
- Bytes Sent: {net_io.bytes_sent / 1024 / 1024:.2f} MB
- Bytes Received: {net_io.bytes_recv / 1024 / 1024:.2f} MB
Recommendation: {"Network activity is normal" if connections < 100 else "High number of connections detected"}"""
        except Exception as e:
            return f"Error analyzing network: {e}"

    def analyze_security(self) -> str:
        """Analyze security status"""
        try:
            import psutil
            connections = len([conn for conn in psutil.net_connections() if conn.status == 'ESTABLISHED'])
            processes = len(psutil.pids())
            
            return f"""Security Analysis:
- Active Connections: {connections}
- Running Processes: {processes}
Recommendation: {"System appears secure" if connections < 50 and processes < 200 else "Consider reviewing active connections and processes"}"""
        except Exception as e:
            return f"Error analyzing security: {e}"

    def analyze_storage(self) -> str:
        """Analyze storage usage"""
        try:
            import psutil
            disk = psutil.disk_usage('/')
            
            return f"""Storage Analysis:
- Total Space: {disk.total / 1024 / 1024 / 1024:.2f} GB
- Used Space: {disk.used / 1024 / 1024 / 1024:.2f} GB
- Free Space: {disk.free / 1024 / 1024 / 1024:.2f} GB
Recommendation: {"Storage space is adequate" if disk.percent < 80 else "Consider freeing up disk space"}"""
        except Exception as e:
            return f"Error analyzing storage: {e}"

    def start_processing(self):
        """Start the message processing thread"""
        self.processing_thread = threading.Thread(target=self._process_messages)
        self.processing_thread.daemon = True
        self.processing_thread.start()

    def _process_messages(self):
        """Process messages in the queue"""
        while self.running:
            try:
                if not self.message_queue.empty():
                    message = self.message_queue.get()
                    self.command_history.append({
                        'timestamp': datetime.now().isoformat(),
                        'message': message
                    })
                    if len(self.command_history) > self.config.get('max_history', 100):
                        self.command_history.pop(0)
                time.sleep(self.config.get('response_delay', 0.5))
            except Exception as e:
                logging.error(f"Error processing message: {e}")

    def stop(self):
        """Stop the AI assistant"""
        self.running = False
        if self.processing_thread:
            self.processing_thread.join()
