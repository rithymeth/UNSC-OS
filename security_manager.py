import os
import logging
import json
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import threading
import queue
import time
from datetime import datetime
import hashlib
import hmac
import base64
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import psutil
import socket
import winreg
import win32security
import nmap
from dataclasses import dataclass

@dataclass
class SecurityEvent:
    timestamp: str
    event_type: str
    severity: str
    description: str
    source: str
    details: Dict

class SecurityManager:
    def __init__(self):
        self.config_file = Path("config/security.json")
        self.config = self.load_config()
        self.events: List[SecurityEvent] = []
        self.event_queue = queue.Queue()
        self.monitoring_thread = None
        self.running = True
        
        # Initialize security components
        self.initialize_security()
        
        # Start monitoring
        self.start_monitoring()
    
    def load_config(self) -> dict:
        """Load security configuration"""
        default_config = {
            "monitoring": {
                "network_scan_interval": 3600,  # 1 hour
                "file_scan_interval": 7200,     # 2 hours
                "registry_scan_interval": 3600,  # 1 hour
                "process_scan_interval": 300     # 5 minutes
            },
            "thresholds": {
                "failed_login_attempts": 3,
                "suspicious_connections": 10,
                "high_cpu_usage": 90,
                "high_memory_usage": 90
            },
            "encryption": {
                "algorithm": "AES-256-GCM",
                "key_iterations": 100000,
                "salt_size": 16
            },
            "firewall": {
                "enabled": True,
                "default_action": "deny",
                "allowed_ports": [80, 443, 22],
                "blocked_ips": []
            }
        }
        
        try:
            if self.config_file.exists():
                with open(self.config_file, "r") as f:
                    return {**default_config, **json.load(f)}
            return default_config
        except Exception as e:
            logging.error(f"Error loading security config: {e}")
            return default_config
    
    def save_config(self):
        """Save security configuration"""
        try:
            self.config_file.parent.mkdir(exist_ok=True)
            with open(self.config_file, "w") as f:
                json.dump(self.config, f, indent=4)
        except Exception as e:
            logging.error(f"Error saving security config: {e}")
    
    def initialize_security(self):
        """Initialize security components"""
        try:
            # Initialize encryption
            self.initialize_encryption()
            
            # Initialize firewall
            self.initialize_firewall()
            
            # Initialize network scanner
            self.initialize_network_scanner()
            
            logging.info("Security components initialized successfully")
            
        except Exception as e:
            logging.error(f"Error initializing security components: {e}")
            raise
    
    def initialize_encryption(self):
        """Initialize encryption components"""
        try:
            # Generate encryption key if not exists
            key_file = Path("config/encryption.key")
            if not key_file.exists():
                key = Fernet.generate_key()
                key_file.parent.mkdir(exist_ok=True)
                with open(key_file, "wb") as f:
                    f.write(key)
            
            # Load encryption key
            with open(key_file, "rb") as f:
                self.encryption_key = f.read()
            
            self.fernet = Fernet(self.encryption_key)
            
        except Exception as e:
            logging.error(f"Error initializing encryption: {e}")
            raise
    
    def initialize_firewall(self):
        """Initialize firewall settings"""
        try:
            # Set firewall rules
            if self.config["firewall"]["enabled"]:
                for port in self.config["firewall"]["allowed_ports"]:
                    self.add_firewall_rule(port)
                
                for ip in self.config["firewall"]["blocked_ips"]:
                    self.block_ip(ip)
            
        except Exception as e:
            logging.error(f"Error initializing firewall: {e}")
            raise
    
    def initialize_network_scanner(self):
        """Initialize network scanner"""
        try:
            self.scanner = nmap.PortScanner()
        except Exception as e:
            logging.error(f"Error initializing network scanner: {e}")
            raise
    
    def start_monitoring(self):
        """Start security monitoring"""
        def monitor():
            while self.running:
                try:
                    # Process security events
                    while not self.event_queue.empty():
                        event = self.event_queue.get()
                        self.process_security_event(event)
                    
                    # Run security scans
                    self.run_security_scans()
                    
                    time.sleep(10)  # Check every 10 seconds
                    
                except Exception as e:
                    logging.error(f"Error in security monitoring: {e}")
                    time.sleep(60)
        
        self.monitoring_thread = threading.Thread(target=monitor)
        self.monitoring_thread.daemon = True
        self.monitoring_thread.start()
    
    def stop_monitoring(self):
        """Stop security monitoring"""
        self.running = False
        if self.monitoring_thread:
            self.monitoring_thread.join()
    
    def run_security_scans(self):
        """Run various security scans"""
        try:
            current_time = time.time()
            
            # Network scan
            if (current_time % self.config["monitoring"]["network_scan_interval"]) < 10:
                self.scan_network()
            
            # File system scan
            if (current_time % self.config["monitoring"]["file_scan_interval"]) < 10:
                self.scan_file_system()
            
            # Registry scan
            if (current_time % self.config["monitoring"]["registry_scan_interval"]) < 10:
                self.scan_registry()
            
            # Process scan
            if (current_time % self.config["monitoring"]["process_scan_interval"]) < 10:
                self.scan_processes()
            
        except Exception as e:
            logging.error(f"Error running security scans: {e}")
    
    def scan_network(self):
        """Scan network for suspicious activity"""
        try:
            # Get local network address
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            network = local_ip.rsplit('.', 1)[0] + '.0/24'
            
            # Scan network
            self.scanner.scan(network, arguments='-sn')
            
            # Check for unauthorized devices
            for host in self.scanner.all_hosts():
                if host not in self.config.get("trusted_devices", []):
                    self.add_security_event(
                        "network",
                        "warning",
                        f"Unknown device detected: {host}",
                        {"ip": host}
                    )
            
        except Exception as e:
            logging.error(f"Error scanning network: {e}")
    
    def scan_file_system(self):
        """Scan file system for suspicious changes"""
        try:
            protected_dirs = [
                "C:/Windows/System32",
                "C:/Program Files",
                "C:/Program Files (x86)"
            ]
            
            for directory in protected_dirs:
                if os.path.exists(directory):
                    for root, _, files in os.walk(directory):
                        for file in files:
                            file_path = os.path.join(root, file)
                            try:
                                # Check file permissions
                                if os.access(file_path, os.W_OK):
                                    self.add_security_event(
                                        "filesystem",
                                        "warning",
                                        f"Writable system file detected: {file_path}",
                                        {"path": file_path}
                                    )
                            except Exception:
                                pass
            
        except Exception as e:
            logging.error(f"Error scanning file system: {e}")
    
    def scan_registry(self):
        """Scan registry for suspicious changes"""
        try:
            # Check startup entries
            startup_keys = [
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\Run",
                r"SOFTWARE\Microsoft\Windows\CurrentVersion\RunOnce"
            ]
            
            for key_path in startup_keys:
                try:
                    key = winreg.OpenKey(
                        winreg.HKEY_LOCAL_MACHINE,
                        key_path,
                        0,
                        winreg.KEY_READ
                    )
                    
                    idx = 0
                    while True:
                        try:
                            name, value, _ = winreg.EnumValue(key, idx)
                            # Check if startup entry is trusted
                            if value not in self.config.get("trusted_startup", []):
                                self.add_security_event(
                                    "registry",
                                    "warning",
                                    f"Suspicious startup entry: {name}",
                                    {"name": name, "value": value}
                                )
                            idx += 1
                        except WindowsError:
                            break
                    
                    winreg.CloseKey(key)
                    
                except WindowsError:
                    pass
            
        except Exception as e:
            logging.error(f"Error scanning registry: {e}")
    
    def scan_processes(self):
        """Scan running processes"""
        try:
            for proc in psutil.process_iter(['pid', 'name', 'username']):
                try:
                    # Check if process is trusted
                    if proc.info['name'] not in self.config.get("trusted_processes", []):
                        # Check process privileges
                        try:
                            ph = win32security.OpenProcess(
                                win32security.PROCESS_QUERY_INFORMATION,
                                False,
                                proc.info['pid']
                            )
                            tk = win32security.OpenProcessToken(ph, win32security.TOKEN_QUERY)
                            privileges = win32security.GetTokenInformation(
                                tk,
                                win32security.TokenPrivileges
                            )
                            
                            if len(privileges) > 5:  # Process has many privileges
                                self.add_security_event(
                                    "process",
                                    "warning",
                                    f"Process with high privileges: {proc.info['name']}",
                                    {"pid": proc.info['pid'], "name": proc.info['name']}
                                )
                        except Exception:
                            pass
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            
        except Exception as e:
            logging.error(f"Error scanning processes: {e}")
    
    def add_security_event(
        self,
        event_type: str,
        severity: str,
        description: str,
        details: Dict
    ):
        """Add new security event"""
        event = SecurityEvent(
            timestamp=datetime.now().isoformat(),
            event_type=event_type,
            severity=severity,
            description=description,
            source="SecurityManager",
            details=details
        )
        
        self.events.append(event)
        self.event_queue.put(event)
    
    def process_security_event(self, event: SecurityEvent):
        """Process security event"""
        try:
            # Log event
            logging.warning(f"Security event: {event.description}")
            
            # Take action based on severity
            if event.severity == "critical":
                self.handle_critical_event(event)
            elif event.severity == "warning":
                self.handle_warning_event(event)
            
        except Exception as e:
            logging.error(f"Error processing security event: {e}")
    
    def handle_critical_event(self, event: SecurityEvent):
        """Handle critical security event"""
        try:
            if event.event_type == "network":
                # Block suspicious IP
                if "ip" in event.details:
                    self.block_ip(event.details["ip"])
            elif event.event_type == "process":
                # Terminate suspicious process
                if "pid" in event.details:
                    try:
                        psutil.Process(event.details["pid"]).terminate()
                    except psutil.NoSuchProcess:
                        pass
            
        except Exception as e:
            logging.error(f"Error handling critical event: {e}")
    
    def handle_warning_event(self, event: SecurityEvent):
        """Handle warning security event"""
        # Log warning events for review
        pass
    
    def add_firewall_rule(self, port: int):
        """Add firewall rule"""
        try:
            # Add Windows Firewall rule
            os.system(
                f'netsh advfirewall firewall add rule name="UNSC_OS_{port}"'
                f' dir=in action=allow protocol=TCP localport={port}'
            )
        except Exception as e:
            logging.error(f"Error adding firewall rule: {e}")
    
    def block_ip(self, ip: str):
        """Block IP address"""
        try:
            # Add Windows Firewall block rule
            os.system(
                f'netsh advfirewall firewall add rule name="UNSC_OS_BLOCK_{ip}"'
                f' dir=in action=block remoteip={ip}'
            )
        except Exception as e:
            logging.error(f"Error blocking IP: {e}")
    
    def encrypt_data(self, data: bytes) -> bytes:
        """Encrypt data using Fernet"""
        try:
            return self.fernet.encrypt(data)
        except Exception as e:
            logging.error(f"Error encrypting data: {e}")
            raise
    
    def decrypt_data(self, encrypted_data: bytes) -> bytes:
        """Decrypt data using Fernet"""
        try:
            return self.fernet.decrypt(encrypted_data)
        except Exception as e:
            logging.error(f"Error decrypting data: {e}")
            raise
    
    def get_security_status(self) -> Dict:
        """Get current security status"""
        try:
            return {
                "firewall_enabled": self.config["firewall"]["enabled"],
                "encryption_enabled": True,
                "monitoring_active": self.running,
                "recent_events": len(self.events),
                "critical_events": sum(
                    1 for event in self.events
                    if event.severity == "critical"
                ),
                "warning_events": sum(
                    1 for event in self.events
                    if event.severity == "warning"
                )
            }
        except Exception as e:
            logging.error(f"Error getting security status: {e}")
            return {}
