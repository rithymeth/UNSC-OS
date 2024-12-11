# UNSC OS

A powerful operating system implementation in Python with advanced features including GUI interface, system monitoring, task scheduling, and comprehensive system management.

## Features
- Graphical User Interface
- Command-line interface
- File system operations
- Process management
- System monitoring
- Network monitoring
- Disk usage tracking
- Task scheduling
- Package management
- User management
- System logging
- File search capabilities
- Service management
- System backup/restore
- Memory usage tracking
- File editing capabilities

## Requirements
- Python 3.8+
- psutil>=5.9.0
- schedule>=1.2.0
- tk>=8.6

## Installation
1. Install the required dependencies:
```bash
pip install -r requirements.txt
```

2. Run the OS:
```bash
python main.py
```

## Available Commands

### File Operations
- `help`: Display available commands
- `ls`: List files and directories
- `cd`: Change directory
- `mkdir`: Create directory
- `touch`: Create file
- `rm`: Remove file/directory
- `edit`: Edit a file
- `cat`: View file contents
- `find`: Search for files by name or content

### Process Management
- `ps`: List running processes
- `kill`: Terminate a process by PID

### System Information
- `sysinfo`: Display detailed system information
- `meminfo`: Show memory usage statistics
- `netinfo`: Display network information and statistics
- `diskinfo`: Show disk usage and partition information

### Task Management
- `schedule`: Schedule tasks to run at intervals
- `tasks`: List all scheduled tasks

### Package Management
- `pkg install`: Install a Python package
- `pkg uninstall`: Remove a Python package

### User Management
- `whoami`: Display current user information
- `users`: List all system users

### Service Management
- `service`: Manage system services (start/stop/restart)
- `services`: List all system services

### System Management
- `backup`: Create system backup
- `restore`: Restore system from backup
- `gui`: Launch graphical user interface

### System Control
- `exit`: Shutdown the OS

## Usage Examples

1. Search for files:
```bash
find name example.txt
find content "search text"
```

2. Manage services:
```bash
service start myservice
service stop myservice
services
```

3. Create system backup:
```bash
backup /path/to/backup/location
```

4. Start GUI:
```bash
gui
```

## Features in Detail

### Graphical User Interface
- Multiple tabs for different functions
- System monitoring graphs
- File manager
- Service manager
- Interactive terminal

### System Logging
- Detailed event logging
- Error tracking
- Activity monitoring
- Log rotation

### File Search
- Search by filename
- Search file contents
- Recursive directory search
- Error handling

### Service Management
- Start/stop services
- Service status monitoring
- Automatic restart
- Service logs

### Backup and Restore
- Full system backup
- Log backup
- Selective restore
- Backup verification

### GUI Features
- Real-time system monitoring
- File operations
- Service management
- Process monitoring
- User-friendly interface
