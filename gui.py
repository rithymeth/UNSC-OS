import tkinter as tk
from tkinter import ttk, messagebox, scrolledtext
import matplotlib
matplotlib.use('TkAgg')
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import psutil
import queue
import threading
import json
import time
import logging
import os
import socket
from updater import UpdateManager
from system_health import SystemHealthMonitor
from theme_manager import ThemeManager

class UNSCGUI:
    def __init__(self, os_instance):
        self.os_instance = os_instance
        self.root = tk.Tk()
        self.root.title("UNSC OS")
        self.root.geometry("1024x768")
        
        # Initialize managers
        self.theme_manager = ThemeManager()
        self.system_health = SystemHealthMonitor()
        self.update_manager = UpdateManager()
        
        # Initialize monitoring variables
        self.output_queue = queue.Queue()
        self.running = True
        self.monitor_thread = None
        self.cpu_data = [0] * 60  # 60 seconds of data
        self.mem_data = [0] * 60
        self.net_data = {'sent': [0] * 60, 'recv': [0] * 60}
        self.last_net = psutil.net_io_counters()
        
        # Setup GUI
        self.setup_styles()
        self.setup_gui()
        self.start_monitoring()
        
        # Start update manager
        self.update_manager.add_observer(self.handle_update_notification)
        self.update_manager.start_auto_update_checker()

    def setup_styles(self):
        """Setup theme styles"""
        style = ttk.Style()
        current_theme = self.theme_manager.get_theme()
        colors = current_theme['colors']
        
        # Configure root window
        self.root.configure(background=colors['background'])
        
        # Configure basic styles
        style.configure('.',
            background=colors['background'],
            foreground=colors['text'])
        
        # Configure Frame
        style.configure('TFrame',
            background=colors['background'])
        
        # Configure Label
        style.configure('TLabel',
            background=colors['background'],
            foreground=colors['text'])
        
        # Configure Button
        style.configure('TButton',
            background=colors['primary'],
            foreground=colors['text'])
        
        # Configure Notebook
        style.configure('TNotebook',
            background=colors['background'])
        
        style.configure('TNotebook.Tab',
            background=colors['secondary'],
            foreground=colors['text'])
        
        # Configure Treeview
        style.configure('Treeview',
            background=colors['background'],
            foreground=colors['text'],
            fieldbackground=colors['background'])
        
        style.configure('Treeview.Heading',
            background=colors['secondary'],
            foreground=colors['text'])
        
        # Configure Entry
        style.configure('TEntry',
            fieldbackground=colors['background'],
            foreground=colors['text'])

        # Configure Text widget
        self.root.option_add('*Text*background', colors['background'])
        self.root.option_add('*Text*foreground', colors['text'])
        
        # Configure Scrolled Text
        style.configure('Scrolled.TFrame',
            background=colors['background'])
            
        # Configure Menu
        self.root.option_add('*Menu*background', colors['background'])
        self.root.option_add('*Menu*foreground', colors['text'])
        self.root.option_add('*Menu*activeBackground', colors['primary'])
        self.root.option_add('*Menu*activeForeground', colors['text'])

        # Update matplotlib style
        if current_theme.get('dark_mode', False):
            plt_bg = colors['background']
            plt_fg = colors['text']
        else:
            plt_bg = 'white'
            plt_fg = 'black'

        matplotlib.rcParams.update({
            'figure.facecolor': plt_bg,
            'axes.facecolor': plt_bg,
            'axes.edgecolor': plt_fg,
            'axes.labelcolor': plt_fg,
            'xtick.color': plt_fg,
            'ytick.color': plt_fg,
            'text.color': plt_fg,
            'grid.color': plt_fg,
            'grid.alpha': 0.3
        })

    def setup_gui(self):
        # Create main notebook
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(expand=True, fill='both', padx=5, pady=5)
        
        # Create tabs
        self.setup_terminal_tab()
        self.setup_system_health_tab()
        self.setup_settings_tab()
        
        # Create menu
        self.setup_menu()
        
        # Start monitoring
        self.start_monitoring()

    def setup_terminal_tab(self):
        """Setup terminal tab"""
        terminal_frame = ttk.Frame(self.notebook)
        self.notebook.add(terminal_frame, text='Terminal')
        
        # Create output text widget
        self.output_text = scrolledtext.ScrolledText(
            terminal_frame,
            wrap=tk.WORD,
            width=80,
            height=20
        )
        self.output_text.pack(expand=True, fill='both', padx=5, pady=5)
        
        # Create input frame
        input_frame = ttk.Frame(terminal_frame)
        input_frame.pack(fill='x', padx=5, pady=5)
        
        # Create prompt label
        prompt_label = ttk.Label(input_frame, text='>')
        prompt_label.pack(side='left', padx=(0, 5))
        
        # Create input entry
        self.input_entry = ttk.Entry(input_frame)
        self.input_entry.pack(side='left', fill='x', expand=True)
        self.input_entry.bind('<Return>', self.handle_input)

    def setup_system_health_tab(self):
        """Setup system health tab"""
        health_frame = ttk.Frame(self.notebook)
        self.notebook.add(health_frame, text='System Health')
        
        # Create graphs frame
        graphs_frame = ttk.Frame(health_frame)
        graphs_frame.pack(expand=True, fill='both', padx=5, pady=5)
        
        # Create CPU graph
        self.cpu_figure = Figure(figsize=(6, 2))
        self.cpu_plot = self.cpu_figure.add_subplot(111)
        self.cpu_plot.set_title('CPU Usage (%)')
        self.cpu_plot.set_ylim(0, 100)
        self.cpu_plot.grid(True, alpha=0.3)
        self.cpu_canvas = FigureCanvasTkAgg(self.cpu_figure, graphs_frame)
        self.cpu_canvas.get_tk_widget().pack(expand=True, fill='both')
        
        # Create memory graph
        self.mem_figure = Figure(figsize=(6, 2))
        self.mem_plot = self.mem_figure.add_subplot(111)
        self.mem_plot.set_title('Memory Usage (%)')
        self.mem_plot.set_ylim(0, 100)
        self.mem_plot.grid(True, alpha=0.3)
        self.mem_canvas = FigureCanvasTkAgg(self.mem_figure, graphs_frame)
        self.mem_canvas.get_tk_widget().pack(expand=True, fill='both')
        
        # Create network graph
        self.net_figure = Figure(figsize=(6, 2))
        self.net_plot = self.net_figure.add_subplot(111)
        self.net_plot.set_title('Network Usage (KB/s)')
        self.net_plot.grid(True, alpha=0.3)
        self.net_canvas = FigureCanvasTkAgg(self.net_figure, graphs_frame)
        self.net_canvas.get_tk_widget().pack(expand=True, fill='both')
        
        # Initialize plots with empty data
        self._update_cpu_plot()
        self._update_mem_plot()
        self._update_net_plot()

    def setup_settings_tab(self):
        """Setup settings tab"""
        settings_frame = ttk.Frame(self.notebook)
        self.notebook.add(settings_frame, text='Settings')
        
        # Create theme selection frame
        theme_frame = ttk.LabelFrame(settings_frame, text='Theme Settings')
        theme_frame.pack(fill='x', padx=5, pady=5)
        
        # Create theme selection dropdown
        theme_label = ttk.Label(theme_frame, text='Select Theme:')
        theme_label.pack(side='left', padx=5)
        
        self.theme_var = tk.StringVar(value=self.theme_manager.current_theme)
        theme_dropdown = ttk.Combobox(
            theme_frame,
            textvariable=self.theme_var,
            values=self.theme_manager.get_all_themes(),
            state='readonly'
        )
        theme_dropdown.pack(side='left', padx=5)
        theme_dropdown.bind('<<ComboboxSelected>>', self.handle_theme_change)
        
        # Create custom theme button
        custom_theme_btn = ttk.Button(
            theme_frame,
            text='Create Custom Theme',
            command=self.create_custom_theme
        )
        custom_theme_btn.pack(side='right', padx=5)

    def handle_theme_change(self, event=None):
        """Handle theme change"""
        new_theme = self.theme_var.get()
        if self.theme_manager.set_theme(new_theme):
            self.setup_styles()
            self.update_plots()

    def create_custom_theme(self):
        """Create custom theme dialog"""
        dialog = tk.Toplevel(self.root)
        dialog.title('Create Custom Theme')
        dialog.geometry('400x300')
        
        # Theme name
        name_frame = ttk.Frame(dialog)
        name_frame.pack(fill='x', padx=5, pady=5)
        
        name_label = ttk.Label(name_frame, text='Theme Name:')
        name_label.pack(side='left')
        
        name_entry = ttk.Entry(name_frame)
        name_entry.pack(side='left', fill='x', expand=True, padx=5)
        
        # Color pickers
        colors_frame = ttk.LabelFrame(dialog, text='Colors')
        colors_frame.pack(fill='x', padx=5, pady=5)
        
        color_vars = {}
        for color in ['background', 'text', 'primary', 'secondary', 'accent']:
            color_frame = ttk.Frame(colors_frame)
            color_frame.pack(fill='x', padx=5, pady=2)
            
            color_label = ttk.Label(color_frame, text=f'{color.title()}:')
            color_label.pack(side='left')
            
            color_entry = ttk.Entry(color_frame)
            color_entry.pack(side='left', fill='x', expand=True, padx=5)
            color_entry.insert(0, '#000000')
            color_vars[color] = color_entry
        
        # Dark mode toggle
        dark_mode_var = tk.BooleanVar(value=False)
        dark_mode_check = ttk.Checkbutton(
            dialog,
            text='Dark Mode',
            variable=dark_mode_var
        )
        dark_mode_check.pack(padx=5, pady=5)
        
        # Save button
        def save_theme():
            name = name_entry.get().strip()
            if not name:
                messagebox.showerror('Error', 'Theme name is required')
                return
                
            colors = {
                color: entry.get()
                for color, entry in color_vars.items()
            }
            
            try:
                self.theme_manager.create_custom_theme(
                    name,
                    colors=colors,
                    dark_mode=dark_mode_var.get()
                )
                theme_dropdown['values'] = self.theme_manager.get_all_themes()
                self.theme_var.set(name)
                self.handle_theme_change()
                dialog.destroy()
            except Exception as e:
                messagebox.showerror('Error', str(e))
        
        save_btn = ttk.Button(dialog, text='Save Theme', command=save_theme)
        save_btn.pack(side='bottom', pady=10)

    def setup_menu(self):
        """Setup menu bar"""
        menubar = tk.Menu(self.root)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label='Exit', command=self.root.quit)
        menubar.add_cascade(label='File', menu=file_menu)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label='About', command=self.show_about)
        menubar.add_cascade(label='Help', menu=help_menu)
        
        self.root.config(menu=menubar)

    def show_about(self):
        """Show about dialog"""
        about_text = """UNSC OS
Version 1.2.0

A modern operating system interface
with theme management and system monitoring.

 2024 UNSC"""
        messagebox.showinfo('About UNSC OS', about_text)

    def start_monitoring(self):
        """Start system monitoring"""
        self.monitor_thread = threading.Thread(target=self.monitor_system)
        self.monitor_thread.daemon = True
        self.monitor_thread.start()

    def monitor_system(self):
        """Monitor system resources"""
        while self.running:
            # Update CPU usage
            cpu_percent = psutil.cpu_percent()
            self.cpu_data.pop(0)
            self.cpu_data.append(cpu_percent)
            
            # Update memory usage
            memory = psutil.virtual_memory()
            self.mem_data.pop(0)
            self.mem_data.append(memory.percent)
            
            # Update network usage
            net = psutil.net_io_counters()
            sent = (net.bytes_sent - self.last_net.bytes_sent) / 1024
            recv = (net.bytes_recv - self.last_net.bytes_recv) / 1024
            self.last_net = net
            
            self.net_data['sent'].pop(0)
            self.net_data['sent'].append(sent)
            self.net_data['recv'].pop(0)
            self.net_data['recv'].append(recv)
            
            # Update plots
            self.update_plots()
            
            time.sleep(1)

    def update_plots(self):
        """Update system monitoring plots"""
        try:
            if not hasattr(self, 'cpu_plot') or not hasattr(self, 'mem_plot') or not hasattr(self, 'net_plot'):
                return
                
            self._update_cpu_plot()
            self._update_mem_plot()
            self._update_net_plot()
            
        except Exception as e:
            logging.error(f"Error updating plots: {e}")

    def _update_cpu_plot(self):
        """Update CPU plot"""
        if len(self.cpu_data) > 0:
            self.cpu_plot.clear()
            self.cpu_plot.plot(range(len(self.cpu_data)), self.cpu_data)
            self.cpu_plot.set_title('CPU Usage (%)')
            self.cpu_plot.set_ylim(0, 100)
            self.cpu_plot.grid(True, alpha=0.3)
            self.cpu_canvas.draw_idle()
    
    def _update_mem_plot(self):
        """Update memory plot"""
        if len(self.mem_data) > 0:
            self.mem_plot.clear()
            self.mem_plot.plot(range(len(self.mem_data)), self.mem_data)
            self.mem_plot.set_title('Memory Usage (%)')
            self.mem_plot.set_ylim(0, 100)
            self.mem_plot.grid(True, alpha=0.3)
            self.mem_canvas.draw_idle()
    
    def _update_net_plot(self):
        """Update network plot"""
        if len(self.net_data['sent']) > 0 and len(self.net_data['recv']) > 0:
            self.net_plot.clear()
            x_range = range(len(self.net_data['sent']))
            self.net_plot.plot(x_range, self.net_data['sent'], label='Sent')
            self.net_plot.plot(x_range, self.net_data['recv'], label='Received')
            self.net_plot.set_title('Network Usage (KB/s)')
            self.net_plot.grid(True, alpha=0.3)
            self.net_plot.legend()
            self.net_canvas.draw_idle()

    def handle_input(self, event):
        """Handle terminal input"""
        command = self.input_entry.get()
        self.input_entry.delete(0, tk.END)
        
        self.output_text.insert(tk.END, f"\n> {command}\n")
        try:
            result = self.os_instance.execute_command(command)
            if result:
                self.output_text.insert(tk.END, f"{result}\n")
        except Exception as e:
            self.output_text.insert(tk.END, f"Error: {e}\n")
        self.output_text.see(tk.END)

    def handle_update_notification(self, message, update_info=None):
        """Handle update notifications"""
        if update_info:
            changes = '\n'.join([f"- {change}" for change in update_info.get('changes', [])])
            msg = f"Version {update_info.get('version')} is available!\n\n"
            if changes:
                msg += f"Changes:\n{changes}"
            messagebox.showinfo('Update Available', msg)
        else:
            messagebox.showinfo('Update Available', message)

    def run(self):
        """Start the GUI"""
        try:
            self.root.mainloop()
        finally:
            self.running = False
            if self.monitor_thread:
                self.monitor_thread.join()
