import psutil
import socket
import logging
from dataclasses import dataclass
from typing import Dict, List, Optional, Set
import json
import time
from pathlib import Path
from datetime import datetime

@dataclass
class FirewallRule:
    name: str
    protocol: str  # tcp/udp
    port: int
    action: str  # allow/block
    direction: str  # in/out
    priority: int
    enabled: bool = True

class NetworkMonitor:
    def __init__(self):
        self.rules_dir = Path("firewall_rules")
        self.rules: Dict[str, FirewallRule] = {}
        self.suspicious_ips: Set[str] = set()
        self.connection_history: List[Dict] = []
        self.max_history = 1000  # Maximum number of historical entries
        
        # Create rules directory if it doesn't exist
        self.rules_dir.mkdir(exist_ok=True)
        
        # Load default rules
        self._create_default_rules()
        self.load_rules()
    
    def _create_default_rules(self):
        """Create default firewall rules"""
        default_rules = {
            "block_telnet": FirewallRule(
                name="block_telnet",
                protocol="tcp",
                port=23,
                action="block",
                direction="in",
                priority=1
            ),
            "allow_http": FirewallRule(
                name="allow_http",
                protocol="tcp",
                port=80,
                action="allow",
                direction="both",
                priority=2
            ),
            "allow_https": FirewallRule(
                name="allow_https",
                protocol="tcp",
                port=443,
                action="allow",
                direction="both",
                priority=2
            )
        }
        
        for rule in default_rules.values():
            self.save_rule(rule)
    
    def load_rules(self):
        """Load all firewall rules"""
        for rule_file in self.rules_dir.glob("*.json"):
            try:
                with open(rule_file, "r") as f:
                    data = json.load(f)
                    rule = FirewallRule(**data)
                    self.rules[rule.name] = rule
            except Exception as e:
                logging.error(f"Error loading rule {rule_file}: {e}")
    
    def save_rule(self, rule: FirewallRule):
        """Save a firewall rule"""
        rule_path = self.rules_dir / f"{rule.name}.json"
        try:
            with open(rule_path, "w") as f:
                json.dump(rule.__dict__, f, indent=4)
            self.rules[rule.name] = rule
            logging.info(f"Saved firewall rule: {rule.name}")
        except Exception as e:
            logging.error(f"Error saving rule {rule.name}: {e}")
    
    def create_rule(
        self,
        name: str,
        protocol: str,
        port: int,
        action: str,
        direction: str,
        priority: int = 10,
        enabled: bool = True
    ) -> Optional[FirewallRule]:
        """Create a new firewall rule"""
        try:
            if name in self.rules:
                raise ValueError(f"Rule {name} already exists")
            
            rule = FirewallRule(
                name=name,
                protocol=protocol.lower(),
                port=port,
                action=action.lower(),
                direction=direction.lower(),
                priority=priority,
                enabled=enabled
            )
            
            self.save_rule(rule)
            return rule
        except Exception as e:
            logging.error(f"Error creating firewall rule: {e}")
            return None
    
    def delete_rule(self, rule_name: str) -> bool:
        """Delete a firewall rule"""
        if rule_name in ["block_telnet", "allow_http", "allow_https"]:
            raise ValueError("Cannot delete default rules")
        
        rule_path = self.rules_dir / f"{rule_name}.json"
        try:
            if rule_path.exists():
                rule_path.unlink()
                del self.rules[rule_name]
                logging.info(f"Deleted firewall rule: {rule_name}")
                return True
            return False
        except Exception as e:
            logging.error(f"Error deleting rule {rule_name}: {e}")
            return False
    
    def get_active_connections(self) -> List[Dict]:
        """Get list of active network connections"""
        try:
            connections = []
            for conn in psutil.net_connections(kind='inet'):
                if conn.status == 'ESTABLISHED':
                    connection = {
                        'local_ip': conn.laddr.ip if conn.laddr else None,
                        'local_port': conn.laddr.port if conn.laddr else None,
                        'remote_ip': conn.raddr.ip if conn.raddr else None,
                        'remote_port': conn.raddr.port if conn.raddr else None,
                        'status': conn.status,
                        'pid': conn.pid
                    }
                    
                    # Check if connection matches any rules
                    connection['allowed'] = self._check_connection_rules(
                        connection['local_port'],
                        connection['remote_port']
                    )
                    
                    connections.append(connection)
                    
                    # Add to history
                    self._add_to_history(connection)
                    
                    # Check for suspicious activity
                    self._check_suspicious(connection)
            
            return connections
        except Exception as e:
            logging.error(f"Error getting active connections: {e}")
            return []
    
    def _check_connection_rules(self, local_port: int, remote_port: int) -> bool:
        """Check if a connection is allowed by firewall rules"""
        # Sort rules by priority
        sorted_rules = sorted(
            [rule for rule in self.rules.values() if rule.enabled],
            key=lambda x: x.priority
        )
        
        for rule in sorted_rules:
            if rule.port in (local_port, remote_port):
                return rule.action == "allow"
        
        return True  # Allow by default if no matching rules
    
    def _add_to_history(self, connection: Dict):
        """Add connection to history"""
        connection['timestamp'] = datetime.now().isoformat()
        self.connection_history.append(connection)
        
        # Trim history if too long
        if len(self.connection_history) > self.max_history:
            self.connection_history = self.connection_history[-self.max_history:]
    
    def _check_suspicious(self, connection: Dict):
        """Check for suspicious network activity"""
        if connection['remote_ip']:
            # Check for common suspicious ports
            suspicious_ports = {21, 22, 23, 25, 3389}  # FTP, SSH, Telnet, SMTP, RDP
            if connection['remote_port'] in suspicious_ports:
                self.suspicious_ips.add(connection['remote_ip'])
                logging.warning(
                    f"Suspicious connection detected from {connection['remote_ip']}:"
                    f"{connection['remote_port']}"
                )
    
    def get_network_usage(self) -> Dict:
        """Get current network usage statistics"""
        try:
            net_io = psutil.net_io_counters()
            return {
                'bytes_sent': net_io.bytes_sent,
                'bytes_recv': net_io.bytes_recv,
                'packets_sent': net_io.packets_sent,
                'packets_recv': net_io.packets_recv,
                'errin': net_io.errin,
                'errout': net_io.errout,
                'dropin': net_io.dropin,
                'dropout': net_io.dropout
            }
        except Exception as e:
            logging.error(f"Error getting network usage: {e}")
            return {}
    
    def get_network_interfaces(self) -> List[Dict]:
        """Get information about network interfaces"""
        try:
            interfaces = []
            for name, addrs in psutil.net_if_addrs().items():
                interface = {'name': name, 'addresses': []}
                for addr in addrs:
                    interface['addresses'].append({
                        'address': addr.address,
                        'netmask': addr.netmask,
                        'family': str(addr.family)
                    })
                interfaces.append(interface)
            return interfaces
        except Exception as e:
            logging.error(f"Error getting network interfaces: {e}")
            return []
    
    def get_connection_history(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None
    ) -> List[Dict]:
        """Get connection history within time range"""
        if not (start_time or end_time):
            return self.connection_history
        
        filtered_history = []
        for conn in self.connection_history:
            conn_time = datetime.fromisoformat(conn['timestamp'])
            if start_time and conn_time < start_time:
                continue
            if end_time and conn_time > end_time:
                continue
            filtered_history.append(conn)
        
        return filtered_history
    
    def get_suspicious_ips(self) -> Set[str]:
        """Get list of suspicious IPs"""
        return self.suspicious_ips.copy()
    
    def clear_suspicious_ips(self):
        """Clear the list of suspicious IPs"""
        self.suspicious_ips.clear()
    
    def get_all_rules(self) -> List[FirewallRule]:
        """Get list of all firewall rules"""
        return list(self.rules.values())
