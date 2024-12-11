import os
import sys
import psutil
import platform
import socket
import getpass
import schedule
import time
import threading
import logging
import shutil
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path
from cloud_manager import CloudManager
from virtualization_manager import VirtualizationManager
from security_manager import SecurityManager

class UNSCOS:
    def __init__(self):
        self.version = "1.8.0"
        self.current_dir = os.getcwd()
        self.running = True
        self.current_user = getpass.getuser()
        self.scheduler_thread = None
        self.cloud = None
        self.virtualization = None
        self.ai_assistant = None
        self.security = None
        self.setup_logging()
        self.commands = {
            # Basic commands
            'help': self.help,
            'ls': self.list_directory,
            'cd': self.change_directory,
            'mkdir': self.make_directory,
            'touch': self.create_file,
            'rm': self.remove,
            'cat': self.view_file,
            'ps': self.list_processes,
            'kill': self.kill_process,
            'clear': self.clear_screen,
            
            # System information
            'sysinfo': self.system_info,
            'meminfo': self.memory_info,
            'netinfo': self.network_info,
            'diskinfo': self.disk_info,
            
            # Task management
            'schedule': self.schedule_task,
            'tasks': self.list_tasks,
            
            # Package management
            'pkg': self.package_manager,
            
            # User management
            'whoami': self.user_info,
            'users': self.list_users,
            
            # File operations
            'find': self.find_files,
            'backup': self.backup_system,
            'restore': self.restore_system,
            
            # Service management
            'service': self.manage_service,
            'services': self.list_services,
            
            # Cloud features
            'cloud': self.cloud_manager,
            'cloudsync': self.cloud_sync,
            'cloudstatus': self.cloud_status,
            
            # Virtualization features
            'docker': self.docker_manager,
            
            # AI features
            'ai': self.ai_command,
            'analyze': self.ai_analyze,
            
            # Security features
            'secure': self.security_manager,
            'scan': self.security_scan,
            'firewall': self.firewall_manager,
            
            'exit': self.shutdown
        }
        self.scheduled_tasks = {}
        self.services = {}
        self.startup()
        self.start_scheduler()

    def setup_logging(self):
        """Setup system logging"""
        log_dir = os.path.join(self.current_dir, 'logs')
        os.makedirs(log_dir, exist_ok=True)
        log_file = os.path.join(log_dir, f'unsc_os_{datetime.now().strftime("%Y%m%d")}.log')
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s [%(levelname)s] %(message)s',
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler(sys.stdout)
            ]
        )
        self.logger = logging.getLogger('UNSC_OS')
        self.logger.info('UNSC OS Starting...')

    def startup(self):
        """Initialize the OS"""
        print(f"UNSC OS v{self.version}")
        print("Type 'help' for a list of commands")
        
        # Initialize managers
        try:
            self.cloud = CloudManager()
            self.virtualization = VirtualizationManager()
            self.security = SecurityManager()
            logging.info("Managers initialized successfully")
        except Exception as e:
            logging.error(f"Error initializing managers: {e}")

    def start_scheduler(self):
        """Start the task scheduler thread"""
        self.scheduler_thread = threading.Thread(target=self._run_scheduler, daemon=True)
        self.scheduler_thread.start()

    def _run_scheduler(self):
        """Run the scheduler loop"""
        while self.running:
            schedule.run_pending()
            time.sleep(1)

    def network_info(self, args: List[str] = None) -> None:
        """Display network information"""
        try:
            print("\nNetwork Information:")
            # Get hostname and IP address
            hostname = socket.gethostname()
            print(f"Hostname: {hostname}")
            print(f"IP Address: {socket.gethostbyname(hostname)}")

            # Get network interfaces
            print("\nNetwork Interfaces:")
            for interface, addrs in psutil.net_if_addrs().items():
                print(f"\n{interface}:")
                for addr in addrs:
                    print(f"  {addr.family.name}: {addr.address}")

            # Get network usage
            net_io = psutil.net_io_counters()
            print("\nNetwork Usage:")
            print(f"Bytes sent: {net_io.bytes_sent / (1024**2):.2f} MB")
            print(f"Bytes received: {net_io.bytes_recv / (1024**2):.2f} MB")
            print(f"Packets sent: {net_io.packets_sent}")
            print(f"Packets received: {net_io.packets_recv}")
        except Exception as e:
            print(f"Error getting network info: {e}")

    def disk_info(self, args: List[str] = None) -> None:
        """Display disk usage information"""
        try:
            print("\nDisk Information:")
            partitions = psutil.disk_partitions()
            for partition in partitions:
                try:
                    usage = psutil.disk_usage(partition.mountpoint)
                    print(f"\nDevice: {partition.device}")
                    print(f"Mountpoint: {partition.mountpoint}")
                    print(f"File system: {partition.fstype}")
                    print(f"Total: {usage.total / (1024**3):.2f} GB")
                    print(f"Used: {usage.used / (1024**3):.2f} GB")
                    print(f"Free: {usage.free / (1024**3):.2f} GB")
                    print(f"Usage: {usage.percent}%")
                except PermissionError:
                    print(f"Permission denied for {partition.mountpoint}")
        except Exception as e:
            print(f"Error getting disk info: {e}")

    def schedule_task(self, args: List[str]) -> None:
        """Schedule a task to run at specific intervals
        Usage: schedule [task_name] [interval] [command]
        Example: schedule backup 1h mkdir backup"""
        if len(args) < 3:
            print("Error: Required format: schedule [task_name] [interval] [command]")
            return

        task_name = args[0]
        interval = args[1]
        command = args[2:]

        try:
            interval_value = int(interval[:-1])
            interval_unit = interval[-1]

            if interval_unit == 'm':
                schedule.every(interval_value).minutes.do(
                    self.process_command, ' '.join(command)
                ).tag(task_name)
            elif interval_unit == 'h':
                schedule.every(interval_value).hours.do(
                    self.process_command, ' '.join(command)
                ).tag(task_name)
            else:
                print("Error: Interval must end with 'm' (minutes) or 'h' (hours)")
                return

            self.scheduled_tasks[task_name] = {
                'interval': interval,
                'command': ' '.join(command)
            }
            print(f"Task '{task_name}' scheduled successfully")
        except ValueError:
            print("Error: Invalid interval format")

    def list_tasks(self, args: List[str] = None) -> None:
        """List all scheduled tasks"""
        if not self.scheduled_tasks:
            print("No scheduled tasks")
            return

        print("\nScheduled Tasks:")
        for name, task in self.scheduled_tasks.items():
            print(f"Name: {name}")
            print(f"Interval: {task['interval']}")
            print(f"Command: {task['command']}")
            print("-" * 30)

    def package_manager(self, args: List[str]) -> None:
        """Simple package manager (install/uninstall Python packages)
        Usage: pkg install/uninstall package_name"""
        if len(args) < 2:
            print("Error: Required format: pkg install/uninstall package_name")
            return

        action = args[0]
        package = args[1]

        try:
            if action == "install":
                os.system(f"pip install {package}")
                print(f"Package {package} installed successfully")
            elif action == "uninstall":
                os.system(f"pip uninstall -y {package}")
                print(f"Package {package} uninstalled successfully")
            else:
                print("Error: Unknown action. Use 'install' or 'uninstall'")
        except Exception as e:
            print(f"Error managing package: {e}")

    def user_info(self, args: List[str] = None) -> None:
        """Display current user information"""
        print(f"\nCurrent user: {self.current_user}")
        print(f"Home directory: {str(Path.home())}")
        print(f"Shell: {os.environ.get('SHELL', 'N/A')}")

    def list_users(self, args: List[str] = None) -> None:
        """List all users on the system"""
        try:
            users = psutil.users()
            print("\nActive Users:")
            for user in users:
                print(f"Username: {user.name}")
                print(f"Terminal: {user.terminal or 'N/A'}")
                print(f"Host: {user.host}")
                started = datetime.fromtimestamp(user.started)
                print(f"Started: {started.strftime('%Y-%m-%d %H:%M:%S')}")
                print("-" * 30)
        except Exception as e:
            print(f"Error listing users: {e}")

    def help(self, args: List[str] = None) -> None:
        """Display available commands"""
        print("\nAvailable commands:")
        for cmd, func in self.commands.items():
            print(f"- {cmd}: {func.__doc__}")

    def list_directory(self, args: List[str] = None) -> None:
        """List files and directories in current path"""
        try:
            path = args[0] if args else self.current_dir
            items = os.listdir(path)
            for item in items:
                full_path = os.path.join(path, item)
                if os.path.isdir(full_path):
                    print(f"[DIR] {item}")
                else:
                    size = os.path.getsize(full_path)
                    print(f"[FILE] {item} ({size} bytes)")
        except Exception as e:
            print(f"Error listing directory: {e}")

    def change_directory(self, args: List[str]) -> None:
        """Change current directory"""
        if not args:
            print("Error: Directory path required")
            return
        
        try:
            path = args[0]
            if os.path.exists(path):
                os.chdir(path)
                self.current_dir = os.getcwd()
                print(f"Changed directory to: {self.current_dir}")
            else:
                print(f"Error: Directory '{path}' does not exist")
        except Exception as e:
            print(f"Error changing directory: {e}")

    def make_directory(self, args: List[str]) -> None:
        """Create a new directory"""
        if not args:
            print("Error: Directory name required")
            return
        
        try:
            os.makedirs(args[0])
            print(f"Created directory: {args[0]}")
        except Exception as e:
            print(f"Error creating directory: {e}")

    def create_file(self, args: List[str]) -> None:
        """Create a new empty file"""
        if not args:
            print("Error: Filename required")
            return
        
        try:
            with open(args[0], 'w') as f:
                pass
            print(f"Created file: {args[0]}")
        except Exception as e:
            print(f"Error creating file: {e}")

    def remove(self, args: List[str]) -> None:
        """Remove a file or directory"""
        if not args:
            print("Error: Path required")
            return
        
        try:
            path = args[0]
            if os.path.isdir(path):
                os.rmdir(path)
                print(f"Removed directory: {path}")
            else:
                os.remove(path)
                print(f"Removed file: {path}")
        except Exception as e:
            print(f"Error removing path: {e}")

    def view_file(self, args: List[str]) -> None:
        """View contents of a file"""
        if not args:
            print("Error: Filename required")
            return
        
        try:
            with open(args[0], 'r') as f:
                print(f.read())
        except Exception as e:
            print(f"Error reading file: {e}")

    def list_processes(self, args: List[str] = None) -> None:
        """List running processes"""
        try:
            print(f"{'PID':>7} {'CPU%':>7} {'Memory%':>8} {'Name':<20}")
            print("-" * 45)
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
                try:
                    info = proc.info
                    print(f"{info['pid']:>7} {info['cpu_percent']:>7.1f} {info['memory_percent']:>8.1f} {info['name']:<20}")
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
        except Exception as e:
            print(f"Error listing processes: {e}")

    def kill_process(self, args: List[str]) -> None:
        """Kill a process by PID"""
        if not args:
            print("Error: PID required")
            return
        
        try:
            pid = int(args[0])
            process = psutil.Process(pid)
            process.terminate()
            print(f"Process {pid} terminated")
        except psutil.NoSuchProcess:
            print(f"Process {pid} not found")
        except Exception as e:
            print(f"Error killing process: {e}")

    def system_info(self, args: List[str] = None) -> None:
        """Display system information"""
        print("\nSystem Information:")
        print(f"OS: {platform.system()} {platform.release()}")
        print(f"Machine: {platform.machine()}")
        print(f"Processor: {platform.processor()}")
        print(f"Python version: {platform.python_version()}")
        
        cpu_freq = psutil.cpu_freq()
        print(f"\nCPU Information:")
        print(f"Physical cores: {psutil.cpu_count(logical=False)}")
        print(f"Total cores: {psutil.cpu_count(logical=True)}")
        print(f"Max Frequency: {cpu_freq.max:.2f}Mhz")
        print(f"Current Frequency: {cpu_freq.current:.2f}Mhz")
        print(f"CPU Usage Per Core:")
        for i, percentage in enumerate(psutil.cpu_percent(percpu=True, interval=1)):
            print(f"Core {i}: {percentage}%")

    def memory_info(self, args: List[str] = None) -> None:
        """Display memory usage information"""
        memory = psutil.virtual_memory()
        print("\nMemory Information:")
        print(f"Total: {memory.total / (1024**3):.2f} GB")
        print(f"Available: {memory.available / (1024**3):.2f} GB")
        print(f"Used: {memory.used / (1024**3):.2f} GB")
        print(f"Percentage: {memory.percent}%")

    def find_files(self, args: List[str]) -> None:
        """Find files by name or content
        Usage: find [name/content] [pattern]"""
        if len(args) < 2:
            print("Error: Required format: find [name/content] [pattern]")
            return

        search_type = args[0]
        pattern = args[1]

        try:
            if search_type == 'name':
                for root, _, files in os.walk(self.current_dir):
                    for file in files:
                        if pattern in file:
                            print(os.path.join(root, file))
            elif search_type == 'content':
                for root, _, files in os.walk(self.current_dir):
                    for file in files:
                        try:
                            with open(os.path.join(root, file), 'r') as f:
                                if pattern in f.read():
                                    print(os.path.join(root, file))
                        except Exception:
                            continue
            else:
                print("Error: Search type must be 'name' or 'content'")
        except Exception as e:
            print(f"Error searching files: {e}")

    def backup_system(self, args: List[str]) -> None:
        """Backup system files
        Usage: backup [destination]"""
        if not args:
            print("Error: Backup destination required")
            return

        dest = args[0]
        try:
            backup_dir = os.path.join(dest, f'backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}')
            os.makedirs(backup_dir)

            # Backup system files
            shutil.copytree(self.current_dir, os.path.join(backup_dir, 'system'), 
                          ignore=shutil.ignore_patterns('*.pyc', '__pycache__', 'logs'))

            # Backup logs
            log_dir = os.path.join(self.current_dir, 'logs')
            if os.path.exists(log_dir):
                shutil.copytree(log_dir, os.path.join(backup_dir, 'logs'))

            print(f"System backed up to: {backup_dir}")
            self.logger.info(f"System backup created at {backup_dir}")
        except Exception as e:
            print(f"Error creating backup: {e}")
            self.logger.error(f"Backup failed: {e}")

    def restore_system(self, args: List[str]) -> None:
        """Restore system from backup
        Usage: restore [backup_path]"""
        if not args:
            print("Error: Backup path required")
            return

        backup_path = args[0]
        try:
            if not os.path.exists(backup_path):
                print(f"Error: Backup not found at {backup_path}")
                return

            # Restore system files
            system_backup = os.path.join(backup_path, 'system')
            if os.path.exists(system_backup):
                shutil.rmtree(self.current_dir, ignore_errors=True)
                shutil.copytree(system_backup, self.current_dir)

            print("System restored successfully")
            self.logger.info(f"System restored from {backup_path}")
        except Exception as e:
            print(f"Error restoring system: {e}")
            self.logger.error(f"Restore failed: {e}")

    def manage_service(self, args: List[str]) -> None:
        """Manage system services
        Usage: service [start/stop/restart] [service_name]"""
        if len(args) < 2:
            print("Error: Required format: service [start/stop/restart] [service_name]")
            return

        action = args[0]
        service_name = args[1]

        try:
            if action == 'start':
                if service_name in self.services and self.services[service_name]['status'] == 'running':
                    print(f"Service {service_name} is already running")
                    return

                # Start the service
                self.services[service_name] = {
                    'status': 'running',
                    'pid': os.getpid(),  # In a real OS, this would be the service's PID
                    'start_time': datetime.now()
                }
                print(f"Service {service_name} started")
                self.logger.info(f"Service {service_name} started")

            elif action == 'stop':
                if service_name not in self.services or self.services[service_name]['status'] != 'running':
                    print(f"Service {service_name} is not running")
                    return

                # Stop the service
                self.services[service_name]['status'] = 'stopped'
                print(f"Service {service_name} stopped")
                self.logger.info(f"Service {service_name} stopped")

            elif action == 'restart':
                self.manage_service(['stop', service_name])
                self.manage_service(['start', service_name])

            else:
                print("Error: Unknown action. Use 'start', 'stop', or 'restart'")
        except Exception as e:
            print(f"Error managing service: {e}")
            self.logger.error(f"Service management failed: {e}")

    def list_services(self, args: List[str] = None) -> None:
        """List all system services"""
        if not self.services:
            print("No services running")
            return

        print("\nSystem Services:")
        print(f"{'Service Name':<20} {'Status':<10} {'PID':<8} {'Start Time':<20}")
        print("-" * 60)
        for name, info in self.services.items():
            start_time = info.get('start_time', 'N/A')
            if isinstance(start_time, datetime):
                start_time = start_time.strftime('%Y-%m-%d %H:%M:%S')
            print(f"{name:<20} {info['status']:<10} {info['pid']:<8} {start_time:<20}")

    def clear_screen(self, args: List[str] = None):
        """Clear the terminal screen"""
        os.system('cls' if os.name == 'nt' else 'clear')

    def shutdown(self, args: List[str] = None) -> None:
        """Shutdown the OS"""
        print("Shutting down UNSC OS...")
        self.running = False

    def process_command(self, command: str) -> None:
        """Process user input commands"""
        parts = command.strip().split()
        if not parts:
            return

        cmd = parts[0].lower()
        args = parts[1:] if len(parts) > 1 else []

        if cmd in self.commands:
            try:
                self.commands[cmd](args)
            except Exception as e:
                print(f"Error executing command '{cmd}': {e}")
        else:
            print(f"Unknown command: '{cmd}'")
            print("Type 'help' for available commands")

    def cloud_manager(self, args: List[str]) -> None:
        """Manage cloud storage settings and providers
        Usage: cloud [action] [provider] [options]
        Actions: enable, disable, config
        Example: cloud enable aws"""
        if not args:
            print("Error: Required format: cloud [action] [provider] [options]")
            return

        if not self.cloud:
            print("Error: Cloud manager is not initialized")
            return

        action = args[0]
        if action == "enable" and len(args) >= 2:
            provider = args[1]
            if provider in self.cloud.config["providers"]:
                self.cloud.config["providers"][provider]["enabled"] = True
                self.cloud.save_config()
                print(f"{provider.upper()} cloud storage enabled")
            else:
                print(f"Unknown provider: {provider}")
        
        elif action == "disable" and len(args) >= 2:
            provider = args[1]
            if provider in self.cloud.config["providers"]:
                self.cloud.config["providers"][provider]["enabled"] = False
                self.cloud.save_config()
                print(f"{provider.upper()} cloud storage disabled")
            else:
                print(f"Unknown provider: {provider}")
        
        elif action == "config":
            print("\nCloud Configuration:")
            for provider, settings in self.cloud.config["providers"].items():
                print(f"\n{provider.upper()}:")
                for key, value in settings.items():
                    print(f"  {key}: {value}")
            print("\nSync Settings:")
            for key, value in self.cloud.config["sync"].items():
                print(f"  {key}: {value}")
        
        else:
            print("Unknown action. Available actions: enable, disable, config")

    def cloud_sync(self, args: List[str]) -> None:
        """Manually trigger cloud synchronization
        Usage: cloudsync [force]"""
        if not self.cloud:
            print("Error: Cloud manager is not initialized")
            return

        try:
            print("Starting cloud synchronization...")
            if args and args[0] == "force":
                self.cloud.sync_all()
            else:
                self.cloud.sync_queue.put({"action": "sync", "path": None, "provider": None})
            print("Synchronization task started")
        except Exception as e:
            print(f"Error during synchronization: {e}")

    def cloud_status(self, args: List[str]) -> None:
        """Show cloud storage status and usage
        Usage: cloudstatus"""
        if not self.cloud:
            print("Error: Cloud manager is not initialized")
            return

        try:
            usage = self.cloud.get_storage_usage()
            print("\nCloud Storage Status:")
            for provider, stats in usage.items():
                if self.cloud.config["providers"][provider]["enabled"]:
                    print(f"\n{provider.upper()}:")
                    print(f"  Files: {stats['files']}")
                    print(f"  Total Size: {stats['size'] / (1024**2):.2f} MB")
        except Exception as e:
            print(f"Error getting cloud status: {e}")

    def docker_manager(self, args: List[str]) -> None:
        """Manage Docker containers and images
        Usage: docker [action] [name] [options]
        Actions: pull, run, stop, rm, ps, images"""
        if not self.virtualization:
            print("Error: Virtualization manager is not initialized")
            return
            
        if not args:
            print("Error: Required format: docker [action] [name] [options]")
            return
            
        try:
            result = self.virtualization.manage_docker(args)
            print(result)
        except Exception as e:
            print(f"Error managing Docker: {e}")

    def ai_command(self, args: List[str]) -> None:
        """Execute AI assistant commands
        Usage: ai [command] [options]"""
        try:
            from ai_assistant import AIAssistant
            if self.ai_assistant is None:
                self.ai_assistant = AIAssistant()
        except Exception as e:
            print(f"Error: AI features are not available: {e}")
            return
            
        if not args:
            print("Error: Required format: ai [command] [options]")
            return
            
        try:
            result = self.ai_assistant.process_command(args)
            print(result)
        except Exception as e:
            print(f"Error processing AI command: {e}")

    def ai_analyze(self, args: List[str]) -> None:
        """Analyze system state with AI
        Usage: analyze [component]"""
        try:
            from ai_assistant import AIAssistant
            if self.ai_assistant is None:
                self.ai_assistant = AIAssistant()
        except Exception as e:
            print(f"Error: AI features are not available: {e}")
            return
            
        if not args:
            print("Error: Required format: analyze [component]")
            return
            
        try:
            result = self.ai_assistant.analyze_system(args[0])
            print(result)
        except Exception as e:
            print(f"Error analyzing system: {e}")

    def security_manager(self, args: List[str]) -> None:
        """Manage security settings
        Usage: secure [action] [options]
        Actions: status, config, update"""
        if not self.security:
            print("Error: Security manager is not initialized")
            return
            
        if not args:
            print("Error: Required format: secure [action] [options]")
            return
            
        try:
            result = self.security.manage_security(args)
            print(result)
        except Exception as e:
            print(f"Error managing security: {e}")

    def security_scan(self, args: List[str]) -> None:
        """Run security scan
        Usage: scan [target]"""
        try:
            from security_manager import SecurityManager
            if self.security is None:
                self.security = SecurityManager()
        except Exception as e:
            print(f"Error: Security features are not available: {e}")
            return
            
        if not args:
            print("Error: Required format: scan [target]")
            return
            
        try:
            result = self.security.scan_network(args[0])
            print(result)
        except Exception as e:
            print(f"Error scanning network: {e}")

    def firewall_manager(self, args: List[str]) -> None:
        """Manage firewall rules
        Usage: firewall [action] [rule]"""
        try:
            from security_manager import SecurityManager
            if self.security is None:
                self.security = SecurityManager()
        except Exception as e:
            print(f"Error: Security features are not available: {e}")
            return
            
        if not args:
            print("Error: Required format: firewall [action] [rule]")
            return
            
        try:
            result = self.security.manage_firewall(args)
            print(result)
        except Exception as e:
            print(f"Error managing firewall: {e}")

    def run(self):
        """Main OS loop"""
        while self.running:
            sys.stdout.write(f"{self.current_dir}> ")
            sys.stdout.flush()

            try:
                command = sys.stdin.readline()
                if not command:  # EOF
                    print("\nShutting down UNSC OS...")
                    break

                command = command.strip()
                if command:
                    self.process_command(command)
            except KeyboardInterrupt:
                print("\nUse 'exit' command to shutdown the OS")
                continue
            except Exception as e:
                print(f"\nError: {e}")
                continue

def main():
    try:
        os_instance = UNSCOS()
        os_instance.run()
    except Exception as e:
        print(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
