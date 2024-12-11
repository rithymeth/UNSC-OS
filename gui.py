import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import queue
import threading
import time
import psutil
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import numpy as np
from datetime import datetime
import json
import os
import socket
from updater import UpdateManager

class UNSCGUI:
    def __init__(self, os_instance):
        self.os = os_instance
        self.root = tk.Tk()
        self.root.title("UNSC OS GUI")
        self.root.geometry("1024x768")
        self.output_queue = queue.Queue()
        self.running = True
        self.monitor_thread = None
        self.theme = self.load_theme()
        self.dark_mode_var = tk.BooleanVar(value=self.theme['dark_mode'])
        self.cpu_data = [0] * 60  # 60 seconds of data
        self.mem_data = [0] * 60
        self.net_data = {'sent': [0] * 60, 'recv': [0] * 60}
        self.last_net = psutil.net_io_counters()
        
        # Initialize update manager
        self.update_manager = UpdateManager()
        self.update_manager.add_observer(self.handle_update_notification)
        self.update_manager.start_auto_update_checker()
        
        self.setup_styles()
        self.setup_gui()
        self.start_monitoring()

    def load_theme(self):
        """Load theme settings from file"""
        theme_file = os.path.join(self.os.current_dir, 'theme.json')
        try:
            if os.path.exists(theme_file):
                with open(theme_file, 'r') as f:
                    return json.load(f)
        except Exception:
            pass
        return {
            'dark_mode': False,
            'colors': {
                'bg': '#ffffff',
                'fg': '#000000',
                'accent': '#007acc'
            }
        }

    def save_theme(self):
        """Save theme settings to file"""
        theme_file = os.path.join(self.os.current_dir, 'theme.json')
        try:
            with open(theme_file, 'w') as f:
                json.dump(self.theme, f, indent=4)
        except Exception as e:
            print(f"Error saving theme: {e}")

    def setup_styles(self):
        """Setup theme styles"""
        style = ttk.Style()
        if self.theme['dark_mode']:
            self.root.configure(bg=self.theme['colors']['bg'])
            style.configure('TFrame', background=self.theme['colors']['bg'])
            style.configure('TLabel', background=self.theme['colors']['bg'], 
                          foreground=self.theme['colors']['fg'])
            style.configure('TButton', background=self.theme['colors']['accent'])
            style.configure('TNotebook', background=self.theme['colors']['bg'])
            style.configure('TNotebook.Tab', background=self.theme['colors']['bg'],
                          foreground=self.theme['colors']['fg'])

    def setup_gui(self):
        # Create main menu
        self.setup_menu()

        # Create notebook for tabs
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(expand=True, fill='both', padx=5, pady=5)

        # Terminal tab
        terminal_frame = ttk.Frame(self.notebook)
        self.notebook.add(terminal_frame, text='Terminal')
        self.setup_terminal(terminal_frame)

        # System Monitor tab
        monitor_frame = ttk.Frame(self.notebook)
        self.notebook.add(monitor_frame, text='System Monitor')
        self.setup_system_monitor(monitor_frame)

        # Network Monitor tab
        network_frame = ttk.Frame(self.notebook)
        self.notebook.add(network_frame, text='Network')
        self.setup_network_monitor(network_frame)

        # Task Manager tab
        task_frame = ttk.Frame(self.notebook)
        self.notebook.add(task_frame, text='Task Manager')
        self.setup_task_manager(task_frame)

        # File Manager tab
        file_frame = ttk.Frame(self.notebook)
        self.notebook.add(file_frame, text='File Manager')
        self.setup_file_manager(file_frame)

        # Services tab
        services_frame = ttk.Frame(self.notebook)
        self.notebook.add(services_frame, text='Services')
        self.setup_services(services_frame)

        # Package Manager tab
        package_frame = ttk.Frame(self.notebook)
        self.notebook.add(package_frame, text='Package Manager')
        self.setup_package_manager(package_frame)

        # System Restore tab
        restore_frame = ttk.Frame(self.notebook)
        self.notebook.add(restore_frame, text='System Restore')
        self.setup_system_restore(restore_frame)

        # Status bar
        self.setup_status_bar()

        # Set up window close handler
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def setup_menu(self):
        """Setup main menu bar"""
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)

        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="File", menu=file_menu)
        file_menu.add_command(label="New Window", command=self.new_window)
        file_menu.add_command(label="Settings", command=self.show_settings)
        file_menu.add_separator()
        file_menu.add_command(label="Check for Updates", command=self.check_for_updates)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_closing)

        # System menu
        system_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="System", menu=system_menu)
        system_menu.add_command(label="Package Manager", command=self.show_package_manager)
        system_menu.add_command(label="System Restore", command=self.show_system_restore)
        system_menu.add_command(label="Create Restore Point", command=self.create_restore_point)

        # View menu
        view_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="View", menu=view_menu)
        self.dark_mode_var = tk.BooleanVar(value=self.theme['dark_mode'])
        view_menu.add_checkbutton(label="Dark Mode", 
                                command=self.toggle_theme,
                                variable=self.dark_mode_var)

        # Tools menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        tools_menu.add_command(label="System Backup", command=lambda: self.os.backup_system(['.']))
        tools_menu.add_command(label="Process Explorer", command=self.show_process_explorer)

        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="Help", menu=help_menu)
        help_menu.add_command(label="About", command=self.show_about)
        help_menu.add_command(label="Documentation", command=self.show_docs)

    def setup_status_bar(self):
        """Setup status bar at bottom of window"""
        status_frame = ttk.Frame(self.root)
        status_frame.pack(side='bottom', fill='x')

        self.status_cpu = ttk.Label(status_frame, text="CPU: 0%")
        self.status_cpu.pack(side='left', padx=5)

        self.status_mem = ttk.Label(status_frame, text="Memory: 0%")
        self.status_mem.pack(side='left', padx=5)

        self.status_time = ttk.Label(status_frame, text="")
        self.status_time.pack(side='right', padx=5)

    def setup_system_monitor(self, parent):
        """Setup system monitoring with graphs"""
        # Create figure for plots
        self.fig = Figure(figsize=(8, 6), dpi=100)
        self.fig.patch.set_facecolor(self.theme['colors']['bg'])

        # CPU subplot
        self.cpu_plot = self.fig.add_subplot(311)
        self.cpu_plot.set_title('CPU Usage')
        self.cpu_line, = self.cpu_plot.plot(self.cpu_data, 'b-')
        self.cpu_plot.set_ylim(0, 100)
        self.cpu_plot.grid(True)

        # Memory subplot
        self.mem_plot = self.fig.add_subplot(312)
        self.mem_plot.set_title('Memory Usage')
        self.mem_line, = self.mem_plot.plot(self.mem_data, 'g-')
        self.mem_plot.set_ylim(0, 100)
        self.mem_plot.grid(True)

        # Network subplot
        self.net_plot = self.fig.add_subplot(313)
        self.net_plot.set_title('Network Usage')
        self.net_recv_line, = self.net_plot.plot(self.net_data['recv'], 'r-', label='Download')
        self.net_send_line, = self.net_plot.plot(self.net_data['sent'], 'b-', label='Upload')
        self.net_plot.legend()
        self.net_plot.grid(True)

        # Add canvas to window
        self.canvas = FigureCanvasTkAgg(self.fig, master=parent)
        self.canvas.draw()
        self.canvas.get_tk_widget().pack(side=tk.TOP, fill=tk.BOTH, expand=1)

    def setup_network_monitor(self, parent):
        """Setup network monitoring tab"""
        # Network interfaces
        interfaces_frame = ttk.LabelFrame(parent, text='Network Interfaces')
        interfaces_frame.pack(fill='x', padx=5, pady=5)
        
        self.interfaces_tree = ttk.Treeview(interfaces_frame, 
                                          columns=('IP', 'Sent', 'Received'),
                                          show='headings')
        self.interfaces_tree.heading('IP', text='IP Address')
        self.interfaces_tree.heading('Sent', text='Bytes Sent')
        self.interfaces_tree.heading('Received', text='Bytes Received')
        self.interfaces_tree.pack(fill='both', expand=True, padx=5, pady=5)

        # Connections
        conn_frame = ttk.LabelFrame(parent, text='Active Connections')
        conn_frame.pack(fill='both', expand=True, padx=5, pady=5)
        
        self.conn_tree = ttk.Treeview(conn_frame, 
                                    columns=('Local', 'Remote', 'Status'),
                                    show='headings')
        self.conn_tree.heading('Local', text='Local Address')
        self.conn_tree.heading('Remote', text='Remote Address')
        self.conn_tree.heading('Status', text='Status')
        self.conn_tree.pack(fill='both', expand=True, padx=5, pady=5)

    def setup_task_manager(self, parent):
        """Setup task manager tab"""
        # Process list
        self.process_tree = ttk.Treeview(parent, 
                                       columns=('PID', 'CPU', 'Memory', 'Status'),
                                       show='headings')
        self.process_tree.heading('PID', text='PID')
        self.process_tree.heading('CPU', text='CPU %')
        self.process_tree.heading('Memory', text='Memory %')
        self.process_tree.heading('Status', text='Status')
        self.process_tree.pack(fill='both', expand=True, padx=5, pady=5)

        # Control buttons
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill='x', padx=5, pady=5)
        ttk.Button(btn_frame, text='End Process', 
                  command=self.end_process).pack(side='left', padx=2)
        ttk.Button(btn_frame, text='Refresh', 
                  command=self.refresh_processes).pack(side='left', padx=2)

    def setup_terminal(self, parent):
        # Output area
        self.terminal_output = scrolledtext.ScrolledText(parent, wrap=tk.WORD, height=20)
        self.terminal_output.pack(expand=True, fill='both', padx=5, pady=5)

        # Input frame
        input_frame = ttk.Frame(parent)
        input_frame.pack(fill='x', padx=5, pady=5)

        # Command input
        self.command_input = ttk.Entry(input_frame)
        self.command_input.pack(side='left', expand=True, fill='x')
        self.command_input.bind('<Return>', self.execute_command)

        # Execute button
        execute_btn = ttk.Button(input_frame, text='Execute', command=lambda: self.execute_command(None))
        execute_btn.pack(side='right', padx=5)

    def setup_file_manager(self, parent):
        # Search frame
        search_frame = ttk.Frame(parent)
        search_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Label(search_frame, text='Search:').pack(side='left')
        self.search_entry = ttk.Entry(search_frame)
        self.search_entry.pack(side='left', expand=True, fill='x', padx=5)
        ttk.Button(search_frame, text='Search', command=self.search_files).pack(side='right')

        # File list
        self.file_list = ttk.Treeview(parent, columns=('Size', 'Modified'), show='headings')
        self.file_list.heading('Size', text='Size')
        self.file_list.heading('Modified', text='Modified')
        self.file_list.pack(expand=True, fill='both', padx=5, pady=5)

        # Buttons frame
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill='x', padx=5, pady=5)
        ttk.Button(btn_frame, text='Refresh', command=self.refresh_files).pack(side='left', padx=2)
        ttk.Button(btn_frame, text='New Folder', command=self.new_folder).pack(side='left', padx=2)
        ttk.Button(btn_frame, text='Delete', command=self.delete_selected).pack(side='left', padx=2)

    def setup_services(self, parent):
        # Services list
        self.services_list = ttk.Treeview(parent, columns=('Status', 'PID'), show='headings')
        self.services_list.heading('Status', text='Status')
        self.services_list.heading('PID', text='PID')
        self.services_list.pack(expand=True, fill='both', padx=5, pady=5)

        # Control buttons
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill='x', padx=5, pady=5)
        ttk.Button(btn_frame, text='Start', command=self.start_service).pack(side='left', padx=2)
        ttk.Button(btn_frame, text='Stop', command=self.stop_service).pack(side='left', padx=2)
        ttk.Button(btn_frame, text='Refresh', command=self.refresh_services).pack(side='left', padx=2)

    def setup_package_manager(self, parent):
        # Package list
        pkg_frame = ttk.Frame(parent)
        pkg_frame.pack(fill='both', expand=True, padx=5, pady=5)

        # Create package tree
        columns = ('Name', 'Version', 'Status', 'Install Date')
        self.pkg_tree = ttk.Treeview(pkg_frame, columns=columns, show='headings')
        for col in columns:
            self.pkg_tree.heading(col, text=col)
        self.pkg_tree.pack(fill='both', expand=True, padx=5, pady=5)

        # Control buttons
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Button(btn_frame, text='Install', 
                  command=lambda: self.install_package(self.pkg_tree)).pack(side='left', padx=2)
        ttk.Button(btn_frame, text='Uninstall', 
                  command=lambda: self.uninstall_package(self.pkg_tree)).pack(side='left', padx=2)
        ttk.Button(btn_frame, text='Refresh', 
                  command=lambda: self.refresh_packages(self.pkg_tree)).pack(side='left', padx=2)

        # Initial package list
        self.refresh_packages(self.pkg_tree)

    def setup_system_restore(self, parent):
        # Restore points list
        restore_frame = ttk.Frame(parent)
        restore_frame.pack(fill='both', expand=True, padx=5, pady=5)

        # Create restore points tree
        columns = ('Date', 'Description')
        self.restore_tree = ttk.Treeview(restore_frame, columns=columns, show='headings')
        for col in columns:
            self.restore_tree.heading(col, text=col)
        self.restore_tree.pack(fill='both', expand=True, padx=5, pady=5)

        # Control buttons
        btn_frame = ttk.Frame(parent)
        btn_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Button(btn_frame, text='Restore System', 
                  command=lambda: self.restore_system(self.restore_tree)).pack(side='left', padx=2)
        ttk.Button(btn_frame, text='Refresh', 
                  command=lambda: self.refresh_restore_points(self.restore_tree)).pack(side='left', padx=2)

        # Initial restore points list
        self.refresh_restore_points(self.restore_tree)

    def execute_command(self, event):
        command = self.command_input.get()
        if command:
            self.terminal_output.insert(tk.END, f"\n> {command}\n")
            try:
                self.os.process_command(command)
            except Exception as e:
                self.terminal_output.insert(tk.END, f"Error: {str(e)}\n")
            self.command_input.delete(0, tk.END)
            self.terminal_output.see(tk.END)

    def start_monitoring(self):
        """Start the system monitoring thread"""
        self.monitor_thread = threading.Thread(target=self.update_stats, daemon=True)
        self.monitor_thread.start()

    def update_stats(self):
        """Update system statistics and graphs"""
        try:
            while self.running:
                # Update CPU and memory data
                cpu_percent = psutil.cpu_percent()
                mem = psutil.virtual_memory()
                
                self.cpu_data.pop(0)
                self.cpu_data.append(cpu_percent)
                self.mem_data.pop(0)
                self.mem_data.append(mem.percent)

                # Update network data
                net = psutil.net_io_counters()
                sent = (net.bytes_sent - self.last_net.bytes_sent) / 1024  # KB/s
                recv = (net.bytes_recv - self.last_net.bytes_recv) / 1024  # KB/s
                self.last_net = net
                
                self.net_data['sent'].pop(0)
                self.net_data['sent'].append(sent)
                self.net_data['recv'].pop(0)
                self.net_data['recv'].append(recv)

                # Update plots
                self.cpu_line.set_ydata(self.cpu_data)
                self.mem_line.set_ydata(self.mem_data)
                self.net_recv_line.set_ydata(self.net_data['recv'])
                self.net_send_line.set_ydata(self.net_data['sent'])
                
                self.canvas.draw_idle()

                # Update status bar
                self.status_cpu['text'] = f"CPU: {cpu_percent}%"
                self.status_mem['text'] = f"Memory: {mem.percent}%"
                self.status_time['text'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                # Update process list
                self.update_process_list()
                
                # Update network interfaces
                self.update_network_info()

                time.sleep(1)
        except Exception as e:
            print(f"Error updating stats: {e}")

    def update_process_list(self):
        """Update process list in task manager"""
        try:
            # Clear current items
            for item in self.process_tree.get_children():
                self.process_tree.delete(item)

            # Add current processes
            for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent', 'status']):
                try:
                    info = proc.info
                    self.process_tree.insert('', 'end', text=info['name'],
                                           values=(info['pid'],
                                                 f"{info['cpu_percent']:.1f}",
                                                 f"{info['memory_percent']:.1f}",
                                                 info['status']))
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
        except Exception as e:
            print(f"Error updating process list: {e}")

    def update_network_info(self):
        """Update network information"""
        try:
            # Clear current items
            for item in self.interfaces_tree.get_children():
                self.interfaces_tree.delete(item)
            for item in self.conn_tree.get_children():
                self.conn_tree.delete(item)

            # Update interfaces
            for interface, addrs in psutil.net_if_addrs().items():
                for addr in addrs:
                    if hasattr(socket, 'AF_INET') and addr.family == socket.AF_INET:
                        try:
                            stats = psutil.net_if_stats().get(interface, None)
                            if stats:
                                self.interfaces_tree.insert('', 'end',
                                                         values=(addr.address,
                                                                f"{getattr(stats, 'speed', 'N/A')} Mbps",
                                                                "Up" if getattr(stats, 'isup', False) else "Down"))
                        except Exception as e:
                            print(f"Error processing interface {interface}: {e}")

            # Update connections
            try:
                for conn in psutil.net_connections(kind='inet'):
                    try:
                        laddr = f"{conn.laddr.ip}:{conn.laddr.port}" if conn.laddr else "N/A"
                        raddr = f"{conn.raddr.ip}:{conn.raddr.port}" if conn.raddr else "N/A"
                        self.conn_tree.insert('', 'end',
                                            values=(laddr, raddr, conn.status))
                    except (AttributeError, psutil.NoSuchProcess, psutil.AccessDenied) as e:
                        continue
            except psutil.AccessDenied:
                self.conn_tree.insert('', 'end',
                                    values=("Access Denied", "", ""))
        except Exception as e:
            print(f"Error updating network info: {e}")

    def search_files(self):
        query = self.search_entry.get()
        if query:
            try:
                self.os.find_files(['name', query])
            except Exception as e:
                messagebox.showerror("Error", f"Search failed: {str(e)}")

    def refresh_files(self):
        try:
            self.os.list_directory([])
        except Exception as e:
            messagebox.showerror("Error", f"Refresh failed: {str(e)}")

    def new_folder(self):
        try:
            self.os.make_directory(['New_Folder'])
        except Exception as e:
            messagebox.showerror("Error", f"Failed to create folder: {str(e)}")

    def delete_selected(self):
        selected = self.file_list.selection()
        if selected:
            if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete the selected items?"):
                try:
                    for item in selected:
                        self.os.remove([self.file_list.item(item, 'text')])
                except Exception as e:
                    messagebox.showerror("Error", f"Delete failed: {str(e)}")

    def start_service(self):
        selected = self.services_list.selection()
        if selected:
            try:
                service_name = self.services_list.item(selected[0], 'text')
                self.os.manage_service(['start', service_name])
                self.refresh_services()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to start service: {str(e)}")

    def stop_service(self):
        selected = self.services_list.selection()
        if selected:
            try:
                service_name = self.services_list.item(selected[0], 'text')
                self.os.manage_service(['stop', service_name])
                self.refresh_services()
            except Exception as e:
                messagebox.showerror("Error", f"Failed to stop service: {str(e)}")

    def refresh_services(self):
        try:
            self.os.list_services([])
        except Exception as e:
            messagebox.showerror("Error", f"Failed to refresh services: {str(e)}")

    def handle_update_notification(self, message, update_info=None):
        """Handle update notifications"""
        if update_info:
            changes = '\n'.join([f"- {change}" for change in update_info['changes']])
            response = messagebox.askyesno(
                "Update Available",
                f"Version {update_info['version']} is available!\n\n"
                f"Changes:\n{changes}\n\n"
                "Would you like to update now?"
            )
            if response:
                self.perform_update()
        else:
            messagebox.showinfo("Update Status", message)

    def check_for_updates(self):
        """Manually check for updates"""
        threading.Thread(target=self.update_manager.manual_update_check, daemon=True).start()

    def perform_update(self):
        """Perform the update process"""
        progress_window = tk.Toplevel(self.root)
        progress_window.title("Updating UNSC OS")
        progress_window.geometry("300x150")
        
        progress_label = ttk.Label(progress_window, text="Downloading update...")
        progress_label.pack(pady=20)
        
        progress_bar = ttk.Progressbar(progress_window, mode='indeterminate')
        progress_bar.pack(fill='x', padx=20)
        progress_bar.start()
        
        def update_process():
            if self.update_manager.manual_update_check():
                progress_window.destroy()
                messagebox.showinfo("Update Complete", 
                                  "The update has been installed successfully.\n"
                                  "Please restart the application to apply changes.")
            else:
                progress_window.destroy()
                messagebox.showerror("Update Failed", 
                                   "Failed to install the update.\n"
                                   "Please try again later.")
        
        threading.Thread(target=update_process, daemon=True).start()

    def on_closing(self):
        """Clean up and close the application"""
        self.running = False
        self.update_manager.stop_auto_update_checker()
        if self.monitor_thread:
            self.monitor_thread.join()
        self.root.destroy()

    def run(self):
        """Start the GUI"""
        try:
            self.root.mainloop()
        except Exception as e:
            print(f"Error running GUI: {e}")
        finally:
            self.running = False

    def new_window(self):
        # Create new window
        new_window = tk.Toplevel(self.root)
        new_window.title("New Window")
        new_window.geometry("800x600")

        # Create new terminal
        terminal_frame = ttk.Frame(new_window)
        terminal_frame.pack(fill='both', expand=True, padx=5, pady=5)
        self.setup_terminal(terminal_frame)

    def show_settings(self):
        # Create settings window
        settings_window = tk.Toplevel(self.root)
        settings_window.title("Settings")
        settings_window.geometry("400x300")

        # Create theme frame
        theme_frame = ttk.Frame(settings_window)
        theme_frame.pack(fill='x', padx=5, pady=5)

        # Create dark mode checkbox
        dark_mode_var = tk.BooleanVar(value=self.theme['dark_mode'])
        dark_mode_checkbox = ttk.Checkbutton(theme_frame, text="Dark Mode", variable=dark_mode_var, command=lambda: self.toggle_theme(dark_mode_var.get()))
        dark_mode_checkbox.pack(side='left', padx=5)

    def toggle_theme(self):
        """Toggle between dark and light theme"""
        dark_mode = self.dark_mode_var.get()
        self.theme['dark_mode'] = dark_mode
        self.save_theme()
        self.setup_styles()

    def show_process_explorer(self):
        # Create process explorer window
        process_explorer_window = tk.Toplevel(self.root)
        process_explorer_window.title("Process Explorer")
        process_explorer_window.geometry("800x600")

        # Create process list
        process_list_frame = ttk.Frame(process_explorer_window)
        process_list_frame.pack(fill='both', expand=True, padx=5, pady=5)

        # Create process tree
        process_tree = ttk.Treeview(process_list_frame, columns=('PID', 'Name', 'CPU', 'Memory'), show='headings')
        process_tree.heading('PID', text='PID')
        process_tree.heading('Name', text='Name')
        process_tree.heading('CPU', text='CPU %')
        process_tree.heading('Memory', text='Memory %')
        process_tree.pack(fill='both', expand=True, padx=5, pady=5)

        # Update process list
        for proc in psutil.process_iter(['pid', 'name', 'cpu_percent', 'memory_percent']):
            try:
                info = proc.info
                process_tree.insert('', 'end', text=info['name'],
                                   values=(info['pid'],
                                         f"{info['cpu_percent']:.1f}",
                                         f"{info['memory_percent']:.1f}"))
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

    def show_about(self):
        # Create about window
        about_window = tk.Toplevel(self.root)
        about_window.title("About")
        about_window.geometry("400x300")

        # Create about label
        about_label = ttk.Label(about_window, text="UNSC OS GUI\nVersion 1.0")
        about_label.pack(fill='both', expand=True, padx=5, pady=5)

    def show_docs(self):
        # Create docs window
        docs_window = tk.Toplevel(self.root)
        docs_window.title("Documentation")
        docs_window.geometry("800x600")

        # Create docs label
        docs_label = ttk.Label(docs_window, text="UNSC OS GUI Documentation")
        docs_label.pack(fill='both', expand=True, padx=5, pady=5)

    def end_process(self):
        selected = self.process_tree.selection()
        if selected:
            try:
                pid = int(self.process_tree.item(selected[0], 'values')[0])
                psutil.Process(pid).terminate()
                self.update_process_list()
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                messagebox.showerror("Error", "Failed to end process")

    def refresh_processes(self):
        self.update_process_list()

    def show_package_manager(self):
        """Show package manager window"""
        pkg_window = tk.Toplevel(self.root)
        pkg_window.title("Package Manager")
        pkg_window.geometry("800x600")

        # Package list
        pkg_frame = ttk.Frame(pkg_window)
        pkg_frame.pack(fill='both', expand=True, padx=5, pady=5)

        # Create package tree
        columns = ('Name', 'Version', 'Status', 'Install Date')
        pkg_tree = ttk.Treeview(pkg_frame, columns=columns, show='headings')
        for col in columns:
            pkg_tree.heading(col, text=col)
        pkg_tree.pack(fill='both', expand=True, padx=5, pady=5)

        # Control buttons
        btn_frame = ttk.Frame(pkg_window)
        btn_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Button(btn_frame, text='Install', 
                  command=lambda: self.install_package(pkg_tree)).pack(side='left', padx=2)
        ttk.Button(btn_frame, text='Uninstall', 
                  command=lambda: self.uninstall_package(pkg_tree)).pack(side='left', padx=2)
        ttk.Button(btn_frame, text='Refresh', 
                  command=lambda: self.refresh_packages(pkg_tree)).pack(side='left', padx=2)

        # Initial package list
        self.refresh_packages(pkg_tree)

    def show_system_restore(self):
        """Show system restore window"""
        restore_window = tk.Toplevel(self.root)
        restore_window.title("System Restore")
        restore_window.geometry("600x400")

        # Restore points list
        restore_frame = ttk.Frame(restore_window)
        restore_frame.pack(fill='both', expand=True, padx=5, pady=5)

        # Create restore points tree
        columns = ('Date', 'Description')
        restore_tree = ttk.Treeview(restore_frame, columns=columns, show='headings')
        for col in columns:
            restore_tree.heading(col, text=col)
        restore_tree.pack(fill='both', expand=True, padx=5, pady=5)

        # Control buttons
        btn_frame = ttk.Frame(restore_window)
        btn_frame.pack(fill='x', padx=5, pady=5)
        
        ttk.Button(btn_frame, text='Restore System', 
                  command=lambda: self.restore_system(restore_tree)).pack(side='left', padx=2)
        ttk.Button(btn_frame, text='Refresh', 
                  command=lambda: self.refresh_restore_points(restore_tree)).pack(side='left', padx=2)

        # Initial restore points list
        self.refresh_restore_points(restore_tree)

    def create_restore_point(self):
        """Create a new restore point"""
        description = tk.simpledialog.askstring(
            "Create Restore Point",
            "Enter description for restore point:"
        )
        if description:
            restore_id = self.update_manager.package_manager.create_restore_point(description)
            if restore_id != -1:
                messagebox.showinfo("Success", "Restore point created successfully")
            else:
                messagebox.showerror("Error", "Failed to create restore point")

    def refresh_packages(self, tree):
        """Refresh package list"""
        for item in tree.get_children():
            tree.delete(item)

        for pkg in self.update_manager.package_manager.list_installed_packages():
            tree.insert('', 'end', values=(
                pkg.name,
                pkg.version,
                pkg.status,
                pkg.installed_date
            ))

    def refresh_restore_points(self, tree):
        """Refresh restore points list"""
        for item in tree.get_children():
            tree.delete(item)

        for point in self.update_manager.package_manager.list_restore_points():
            tree.insert('', 'end', values=(
                point['date'],
                point['description']
            ))

    def install_package(self, tree):
        """Install selected package"""
        # In a real implementation, this would show a package selection dialog
        name = tk.simpledialog.askstring(
            "Install Package",
            "Enter package name:"
        )
        if name:
            if self.update_manager.package_manager.install_package(name, "1.0.0", []):
                messagebox.showinfo("Success", f"Package {name} installed successfully")
                self.refresh_packages(tree)
            else:
                messagebox.showerror("Error", f"Failed to install package {name}")

    def uninstall_package(self, tree):
        """Uninstall selected package"""
        selected = tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a package to uninstall")
            return

        pkg_name = tree.item(selected[0])['values'][0]
        if messagebox.askyesno("Confirm", f"Are you sure you want to uninstall {pkg_name}?"):
            if self.update_manager.package_manager.uninstall_package(pkg_name):
                messagebox.showinfo("Success", f"Package {pkg_name} uninstalled successfully")
                self.refresh_packages(tree)
            else:
                messagebox.showerror("Error", f"Failed to uninstall package {pkg_name}")

    def restore_system(self, tree):
        """Restore system to selected restore point"""
        selected = tree.selection()
        if not selected:
            messagebox.showwarning("Warning", "Please select a restore point")
            return

        if messagebox.askyesno("Confirm", "Are you sure you want to restore the system to this point?"):
            point_id = int(tree.item(selected[0])['values'][0])
            if self.update_manager.package_manager.restore_from_point(point_id):
                messagebox.showinfo("Success", "System restored successfully")
            else:
                messagebox.showerror("Error", "Failed to restore system")
