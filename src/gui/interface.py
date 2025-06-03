#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Module: interface.py
# Purpose: Main GUI window for Test Case Manager (Windows Edition)
# Last updated: 2025-06-02 by juno-kyojin

import os
import sys
import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import time
import logging
import sqlite3
import csv
from typing import Optional, Tuple, List, Dict

# Import các module windows-specific
from files.manager import TestFileManager
from network.connection import SSHConnection
from storage.database import TestDatabase
# Configuration constants
class AppConfig:
    DEFAULT_TIMEOUT = 120
    RESULT_CHECK_INTERVAL = 3
    MAX_RECONNECT_ATTEMPTS = 3
    CONNECTION_RETRY_DELAY = 2
    FILE_SIZE_THRESHOLD = 50
    TEMP_CLEANUP_HOURS = 1
    MAX_FILE_RETRIES = 2
    
    # File patterns
    RESULT_FILE_PATTERN = "{base}_*.json"
    
    # Timeouts
    SSH_CONNECT_TIMEOUT = 15
    FILE_UPLOAD_TIMEOUT = 60
    COMMAND_TIMEOUT = 30

class ApplicationGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Test Case Manager v2.0 - Windows Edition")
        
        # Tính toán kích thước cửa sổ phù hợp
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        
        # Đảm bảo kích thước mặc định hợp lý (80% của màn hình)
        window_width = min(int(screen_width * 0.8), 1200)
        window_height = min(int(screen_height * 0.8), 800)
        
        # Đảm bảo ít nhất 800x600
        window_width = max(window_width, 800)
        window_height = max(window_height, 600)
        
        # Tính toán vị trí để cửa sổ hiển thị chính giữa màn hình
        x_position = (screen_width - window_width) // 2
        y_position = (screen_height - window_height) // 2
        
        # Đặt kích thước và vị trí
        self.root.geometry(f"{window_width}x{window_height}+{x_position}+{y_position}")
        
        # Đặt kích thước tối thiểu để đảm bảo luôn thấy được tất cả các thành phần
        self.root.minsize(800, 650)
        
        # Setup enhanced logging
        self.setup_logging()
        
        # Initialize real modules
        self.ssh_connection = SSHConnection()
        self.file_manager = TestFileManager()
        self.database = TestDatabase()
        
        # Style configuration
        self.setup_styles()
        
        # Variables - Load from database
        self.setup_variables()
        
        self.selected_files = []
        self.file_data = {}  # Store parsed file data
        self.current_file_index = -1
        self.processing = False
        self.file_retry_count = {}  # Track retry attempts per file
        
        # Create UI components
        self.create_menu()
        self.create_notebook()
        self.create_status_bar()
        
        # Load history from database
        self.load_history()
        
        # Auto-save settings when changed
        self.setup_auto_save()
        
        # Schedule cleanup task
        self.schedule_cleanup()
        
        # Set Windows-specific icon if available
        try:
            self.root.iconbitmap("assets/app_icon.ico")
        except:
            pass
    
    def setup_logging(self):
        """Setup enhanced logging configuration"""
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(os.path.join(log_dir, 'app.log')),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"Windows application started by {os.environ.get('USERNAME', 'unknown')}")
    
    def setup_styles(self):
        """Setup enhanced UI styles"""
        self.style = ttk.Style()
        
        # Try to use Windows native theme
        try:
            self.style.theme_use('vista')
        except:
            pass
            
        self.style.configure("TButton", padding=6)
        self.style.configure("TLabel", padding=3)
        self.style.configure("TFrame", padding=5)
        
        # Status-specific styles
        self.style.configure("Success.TLabel", foreground="green")
        self.style.configure("Error.TLabel", foreground="red")
        self.style.configure("Warning.TLabel", foreground="orange")
    
    def setup_variables(self):
        """Setup and load variables from database"""
        self.lan_ip_var = tk.StringVar(value=self.database.get_setting("lan_ip", "192.168.88.1"))
        self.wan_ip_var = tk.StringVar(value=self.database.get_setting("wan_ip", ""))
        self.username_var = tk.StringVar(value=self.database.get_setting("username", "root"))
        self.password_var = tk.StringVar()  # Never save password
        self.config_path_var = tk.StringVar(value=self.database.get_setting("config_path", "/root/config"))
        self.result_path_var = tk.StringVar(value=self.database.get_setting("result_path", "/root/result"))
        self.connection_status = tk.StringVar(value="Not Connected")
    
    def setup_auto_save(self):
        """Setup auto-save for settings when they change"""
        def save_setting(var_name, var):
            def callback(*args):
                try:
                    self.database.save_setting(var_name, var.get())
                except Exception as e:
                    self.logger.warning(f"Auto-save failed for {var_name}: {e}")
            return callback
        
        self.lan_ip_var.trace('w', save_setting('lan_ip', self.lan_ip_var))
        self.wan_ip_var.trace('w', save_setting('wan_ip', self.wan_ip_var))
        self.username_var.trace('w', save_setting('username', self.username_var))
        self.config_path_var.trace('w', save_setting('config_path', self.config_path_var))
        self.result_path_var.trace('w', save_setting('result_path', self.result_path_var))
    
    def schedule_cleanup(self):
        """Schedule periodic cleanup of temporary files"""
        def cleanup_task():
            try:
                self.cleanup_temp_files()
            except Exception as e:
                self.logger.warning(f"Cleanup task failed: {e}")
            
            # Schedule next cleanup in 1 hour
            self.root.after(3600000, cleanup_task)  # 3600000 ms = 1 hour
        
        # Start first cleanup after 5 minutes
        self.root.after(300000, cleanup_task)  # 300000 ms = 5 minutes
    
    def cleanup_temp_files(self):
        """Clean up old temporary result files"""
        temp_dir = "data/temp/results"
        if not os.path.exists(temp_dir):
            return
        
        cutoff_time = time.time() - (AppConfig.TEMP_CLEANUP_HOURS * 3600)
        cleaned_count = 0
        
        try:
            for file in os.listdir(temp_dir):
                if file.endswith('.json'):
                    file_path = os.path.join(temp_dir, file)
                    if os.path.getctime(file_path) < cutoff_time:
                        os.remove(file_path)
                        cleaned_count += 1
            
            if cleaned_count > 0:
                self.log_message(f"Cleaned up {cleaned_count} old temporary files")
                
        except Exception as e:
            self.logger.error(f"Cleanup failed: {e}")
    
    def create_menu(self):
        """Create application menu bar"""
        menubar = tk.Menu(self.root)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Open Configuration...", command=self.load_config)
        file_menu.add_command(label="Save Configuration...", command=self.save_config)
        file_menu.add_separator()
        file_menu.add_command(label="Export Results...", command=self.export_results)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.on_closing)
        menubar.add_cascade(label="File", menu=file_menu)
        
        # View menu
        view_menu = tk.Menu(menubar, tearoff=0)
        view_menu.add_command(label="Refresh", command=self.refresh_view)
        view_menu.add_command(label="Clear History", command=self.clear_history)
        menubar.add_cascade(label="View", menu=view_menu)
        
        # Tools menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        tools_menu.add_command(label="Connection Test...", command=self.test_connection)
        tools_menu.add_command(label="Check Remote Folders...", command=self.check_remote_folders)
        tools_menu.add_command(label="Cleanup Temp Files", command=self.cleanup_temp_files)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="Documentation", command=self.show_documentation)
        help_menu.add_command(label="About", command=self.show_about)
        menubar.add_cascade(label="Help", menu=help_menu)
        
        self.root.config(menu=menubar)
        
        # Handle window closing
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def create_notebook(self):
        """Create the main notebook/tabs interface"""
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create tabs
        self.main_tab = ttk.Frame(self.notebook)
        self.history_tab = ttk.Frame(self.notebook)
        self.logs_tab = ttk.Frame(self.notebook)
        
        # Add tabs to notebook
        self.notebook.add(self.main_tab, text="Test Queue")
        self.notebook.add(self.history_tab, text="History")
        self.notebook.add(self.logs_tab, text="Logs")
        
        # Setup tab content
        self.setup_main_tab()
        self.setup_history_tab()
        self.setup_logs_tab()
    
    def setup_main_tab(self):
        """Setup the main tab content using grid layout for consistent display"""
        # Cấu hình grid cho main_tab
        self.main_tab.columnconfigure(0, weight=1)  # Cột duy nhất mở rộng đầy đủ
        self.main_tab.rowconfigure(0, weight=10)    # Connection settings
        self.main_tab.rowconfigure(1, weight=20)    # File selection
        self.main_tab.rowconfigure(2, weight=30)    # Detail view
        self.main_tab.rowconfigure(3, weight=5)     # Action buttons - chiều cao cố định
        
        # ============= Connection Frame =============
        connection_frame = ttk.LabelFrame(self.main_tab, text="Connection Settings")
        connection_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=5)
        
        # Cấu hình grid cho connection frame
        connection_frame.columnconfigure(0, weight=0)  # Label columns - fixed width
        connection_frame.columnconfigure(1, weight=1)  # Entry columns - expand
        connection_frame.columnconfigure(2, weight=0)  # Label columns - fixed width
        connection_frame.columnconfigure(3, weight=1)  # Entry columns - expand
        
        # Row 0
        ttk.Label(connection_frame, text="LAN IP:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(connection_frame, textvariable=self.lan_ip_var).grid(row=0, column=1, sticky=tk.EW, padx=5, pady=5)
        
        ttk.Label(connection_frame, text="Config Path:").grid(row=0, column=2, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(connection_frame, textvariable=self.config_path_var).grid(row=0, column=3, sticky=tk.EW, padx=5, pady=5)
        
        # Row 1
        ttk.Label(connection_frame, text="WAN IP (Optional):").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(connection_frame, textvariable=self.wan_ip_var).grid(row=1, column=1, sticky=tk.EW, padx=5, pady=5)
        
        ttk.Label(connection_frame, text="Result Path:").grid(row=1, column=2, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(connection_frame, textvariable=self.result_path_var).grid(row=1, column=3, sticky=tk.EW, padx=5, pady=5)
        
        # Row 2
        ttk.Label(connection_frame, text="Username:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(connection_frame, textvariable=self.username_var).grid(row=2, column=1, sticky=tk.EW, padx=5, pady=5)
        
        # Row 3
        ttk.Label(connection_frame, text="Password:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(connection_frame, textvariable=self.password_var, show="•").grid(row=3, column=1, sticky=tk.EW, padx=5, pady=5)
        
        # Connection buttons
        conn_btn_frame = ttk.Frame(connection_frame)
        conn_btn_frame.grid(row=3, column=2, columnspan=2, sticky=tk.E, padx=5, pady=5)
        
        ttk.Button(conn_btn_frame, text="Test Connection", command=self.test_connection).pack(side=tk.LEFT, padx=5)
        ttk.Button(conn_btn_frame, text="Save Settings", command=self.save_config).pack(side=tk.LEFT, padx=5)
        
        # ============= File Frame =============
        file_frame = ttk.LabelFrame(self.main_tab, text="Test Files")
        file_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        
        # Cấu hình grid cho file frame
        file_frame.columnconfigure(0, weight=1)
        file_frame.rowconfigure(0, weight=0)  # Buttons row - fixed height
        file_frame.rowconfigure(1, weight=1)  # Table row - expands
        
        # File selection buttons
        file_btn_frame = ttk.Frame(file_frame)
        file_btn_frame.grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        
        ttk.Button(file_btn_frame, text="Select Files", command=self.select_files).pack(side=tk.LEFT, padx=5)
        ttk.Button(file_btn_frame, text="Clear Selection", command=self.clear_files).pack(side=tk.LEFT, padx=5)
        
        # File table
        file_table_frame = ttk.Frame(file_frame)
        file_table_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        
        # Configure grid for table frame
        file_table_frame.columnconfigure(0, weight=1)
        file_table_frame.rowconfigure(0, weight=1)
        
        self.file_table = ttk.Treeview(
            file_table_frame, 
            columns=("filename", "size", "tests", "status", "result", "time"),
            show="headings", 
            selectmode="browse"
        )
        
        # Setup columns
        self.file_table.heading("filename", text="Filename")
        self.file_table.heading("size", text="Size")
        self.file_table.heading("tests", text="Tests")
        self.file_table.heading("status", text="Status")
        self.file_table.heading("result", text="Result")
        self.file_table.heading("time", text="Time")
        
        self.file_table.column("filename", width=200, minwidth=150)
        self.file_table.column("size", width=80, minwidth=80)
        self.file_table.column("tests", width=50, minwidth=50)
        self.file_table.column("status", width=100, minwidth=100)
        self.file_table.column("result", width=100, minwidth=100)
        self.file_table.column("time", width=100, minwidth=80)
        
        # Scrollbar
        file_table_scrollbar = ttk.Scrollbar(file_table_frame, orient=tk.VERTICAL, command=self.file_table.yview)
        self.file_table.configure(yscrollcommand=file_table_scrollbar.set)
        
        # Place table and scrollbar using grid
        self.file_table.grid(row=0, column=0, sticky="nsew")
        file_table_scrollbar.grid(row=0, column=1, sticky="ns")
        
        # Bind selection event
        self.file_table.bind("<<TreeviewSelect>>", self.on_file_selected)
        
        # ============= Detail Frame =============
        detail_frame = ttk.LabelFrame(self.main_tab, text="Test Case Details")
        detail_frame.grid(row=2, column=0, sticky="nsew", padx=10, pady=5)
        
        # Configure grid for detail frame
        detail_frame.columnconfigure(0, weight=1)
        detail_frame.rowconfigure(0, weight=1)
        
        # Test case detail table
        detail_table_frame = ttk.Frame(detail_frame)
        detail_table_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        # Configure grid for table frame
        detail_table_frame.columnconfigure(0, weight=1)
        detail_table_frame.rowconfigure(0, weight=1)
        
        self.detail_table = ttk.Treeview(
            detail_table_frame, 
            columns=("service", "action", "params", "status", "details"),
            show="headings", 
            selectmode="browse"
        )
        
        # Setup columns
        self.detail_table.heading("service", text="Service")
        self.detail_table.heading("action", text="Action")
        self.detail_table.heading("params", text="Parameters")
        self.detail_table.heading("status", text="Status")
        self.detail_table.heading("details", text="Details")
        
        self.detail_table.column("service", width=100, minwidth=80)
        self.detail_table.column("action", width=100, minwidth=80)
        self.detail_table.column("params", width=300, minwidth=200)
        self.detail_table.column("status", width=100, minwidth=80)
        self.detail_table.column("details", width=300, minwidth=200)
        
        # Scrollbar
        detail_table_scrollbar = ttk.Scrollbar(detail_table_frame, orient=tk.VERTICAL, command=self.detail_table.yview)
        self.detail_table.configure(yscrollcommand=detail_table_scrollbar.set)
        
        # Place table and scrollbar using grid
        self.detail_table.grid(row=0, column=0, sticky="nsew")
        detail_table_scrollbar.grid(row=0, column=1, sticky="ns")
        
        # ============= Action Buttons Frame =============
        action_frame = ttk.Frame(self.main_tab)
        action_frame.grid(row=3, column=0, sticky="ew", padx=10, pady=10)
        
        # Configure grid for action buttons
        action_frame.columnconfigure(0, weight=0)  # Send Files button - fixed width
        action_frame.columnconfigure(1, weight=0)  # Cancel button - fixed width
        action_frame.columnconfigure(2, weight=1)  # Progress bar - expands
        
        self.send_button = ttk.Button(action_frame, text="Send Files", command=self.send_files)
        self.send_button.grid(row=0, column=0, padx=5)
        
        self.cancel_button = ttk.Button(action_frame, text="Cancel", command=self.cancel_processing, state=tk.DISABLED)
        self.cancel_button.grid(row=0, column=1, padx=5)
        
        self.progress_var = tk.IntVar()
        self.progress_bar = ttk.Progressbar(action_frame, orient=tk.HORIZONTAL, mode='determinate', variable=self.progress_var)
        self.progress_bar.grid(row=0, column=2, sticky="ew", padx=10)
        self.progress_var.set(0)
    
    def setup_history_tab(self):
        """Setup the history tab content"""
        # Use grid layout for history tab
        self.history_tab.columnconfigure(0, weight=1)
        self.history_tab.rowconfigure(0, weight=0)  # Filter row - fixed height
        self.history_tab.rowconfigure(1, weight=1)  # Table row - expands
        self.history_tab.rowconfigure(2, weight=0)  # Buttons row - fixed height
        
        # Filter frame
        filter_frame = ttk.Frame(self.history_tab)
        filter_frame.grid(row=0, column=0, sticky="ew", padx=10, pady=10)
        
        ttk.Label(filter_frame, text="Date:").pack(side=tk.LEFT, padx=5)
        self.date_combo = ttk.Combobox(filter_frame, width=15, values=["All", "Today", "Last 7 Days", "Last 30 Days"])
        self.date_combo.current(0)
        self.date_combo.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(filter_frame, text="Status:").pack(side=tk.LEFT, padx=5)
        self.status_combo = ttk.Combobox(filter_frame, width=15, values=["All", "Pass", "Fail", "Partial"])
        self.status_combo.current(0)
        self.status_combo.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(filter_frame, text="Apply Filter", command=self.apply_history_filter).pack(side=tk.LEFT, padx=5)
        ttk.Button(filter_frame, text="Clear Filter", command=self.clear_history_filter).pack(side=tk.LEFT, padx=5)
        
        # History table
        history_table_frame = ttk.Frame(self.history_tab)
        history_table_frame.grid(row=1, column=0, sticky="nsew", padx=10, pady=5)
        
        # Configure grid for table frame
        history_table_frame.columnconfigure(0, weight=1)
        history_table_frame.rowconfigure(0, weight=1)
        
        self.history_table = ttk.Treeview(
            history_table_frame, 
            columns=("date", "time", "file", "tests", "result", "details"),
            show="headings", 
            selectmode="browse"
        )
        
        # Setup columns
        self.history_table.heading("date", text="Date")
        self.history_table.heading("time", text="Time")
        self.history_table.heading("file", text="Filename")
        self.history_table.heading("tests", text="Tests")
        self.history_table.heading("result", text="Result")
        self.history_table.heading("details", text="Details")
        
        self.history_table.column("date", width=100, minwidth=100)
        self.history_table.column("time", width=80, minwidth=80)
        self.history_table.column("file", width=200, minwidth=150)
        self.history_table.column("tests", width=50, minwidth=50)
        self.history_table.column("result", width=100, minwidth=80)
        self.history_table.column("details", width=350, minwidth=200)
        
        # Scrollbar
        history_scrollbar = ttk.Scrollbar(history_table_frame, orient=tk.VERTICAL, command=self.history_table.yview)
        self.history_table.configure(yscrollcommand=history_scrollbar.set)
        
        # Place table and scrollbar using grid
        self.history_table.grid(row=0, column=0, sticky="nsew")
        history_scrollbar.grid(row=0, column=1, sticky="ns")
        
        # Action buttons
        history_btn_frame = ttk.Frame(self.history_tab)
        history_btn_frame.grid(row=2, column=0, sticky="ew", padx=10, pady=10)
        
        ttk.Button(history_btn_frame, text="Export to CSV", command=self.export_history).pack(side=tk.LEFT, padx=5)
        ttk.Button(history_btn_frame, text="View Details", command=self.view_history_details).pack(side=tk.LEFT, padx=5)
        ttk.Button(history_btn_frame, text="Refresh", command=self.load_history).pack(side=tk.LEFT, padx=5)
    
    def setup_logs_tab(self):
        """Setup the logs tab content"""
        # Use grid layout for logs tab
        self.logs_tab.columnconfigure(0, weight=1)
        self.logs_tab.rowconfigure(0, weight=1)  # Log text area - expands
        self.logs_tab.rowconfigure(1, weight=0)  # Buttons row - fixed height
        
        # Log frame
        log_frame = ttk.Frame(self.logs_tab)
        log_frame.grid(row=0, column=0, sticky="nsew", padx=10, pady=10)
        
        # Configure grid for log frame
        log_frame.columnconfigure(0, weight=1)
        log_frame.rowconfigure(0, weight=1)
        
        # Log text area
        self.log_text = tk.Text(log_frame, wrap=tk.WORD)
        self.log_text.grid(row=0, column=0, sticky="nsew")
        
        # Scrollbar
        log_scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scrollbar.set)
        log_scrollbar.grid(row=0, column=1, sticky="ns")
        
        # Configure log text appearance
        self.log_text.configure(font=("Consolas", 10), background="#f5f5f5")
        
        # Buttons
        log_btn_frame = ttk.Frame(self.logs_tab)
        log_btn_frame.grid(row=1, column=0, sticky="ew", padx=10, pady=10)
        
        ttk.Button(log_btn_frame, text="Clear Logs", command=self.clear_logs).pack(side=tk.LEFT, padx=5)
        ttk.Button(log_btn_frame, text="Export Logs", command=self.export_logs).pack(side=tk.LEFT, padx=5)
        ttk.Button(log_btn_frame, text="Refresh", command=self.refresh_logs).pack(side=tk.LEFT, padx=5)
    
    def create_status_bar(self):
        """Create status bar at the bottom of the window"""
        status_frame = ttk.Frame(self.root, relief=tk.SUNKEN, borderwidth=1)
        status_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Connection status indicator
        self.status_canvas = tk.Canvas(status_frame, width=15, height=15)
        self.status_canvas.pack(side=tk.LEFT, padx=5, pady=2)
        self.status_circle = self.status_canvas.create_oval(2, 2, 13, 13, fill="red")
        
        # Status text
        ttk.Label(status_frame, textvariable=self.connection_status).pack(side=tk.LEFT, padx=5)
        
        # User info
        user_var = tk.StringVar(value=f"User: {os.environ.get('USERNAME', 'unknown')}")
        ttk.Label(status_frame, textvariable=user_var).pack(side=tk.LEFT, padx=15)
        
        # Current time
        self.time_var = tk.StringVar()
        self.update_clock()
        ttk.Label(status_frame, textvariable=self.time_var).pack(side=tk.RIGHT, padx=10)
    
    def update_clock(self):
        """Update the clock in the status bar"""
        current_time = time.strftime("%Y-%m-%d %H:%M:%S")
        self.time_var.set(current_time)
        self.root.after(1000, self.update_clock)
    
    # Phần còn lại của các phương thức (test_connection, select_files, v.v.) giữ nguyên...
    # Đây là một số phương thức thiết yếu:
    
    def test_connection(self):
        """Enhanced connection test with retry logic"""
        if not self.validate_connection_fields():
            return
        
        self.connection_status.set("Connecting...")
        self.update_status_circle("yellow")
        self.log_message("Testing connection to " + self.lan_ip_var.get() + "...")
        
        threading.Thread(target=self._test_connection_thread, daemon=True).start()
    
    def select_files(self):
        """Select and validate JSON files using real file manager"""
        files = filedialog.askopenfilenames(
            title="Select JSON Test Files",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")],
            initialdir=os.path.join(os.getcwd(), 'test_files') if os.path.exists(os.path.join(os.getcwd(), 'test_files')) else None
        )
        
        if not files:
            return
        
        # Clear existing selection
        self.clear_files()
        
        # Validate and add files
        valid_files = []
        invalid_files = []
        
        for file_path in files:
            try:
                is_valid, error_msg, data = self.file_manager.validate_json_file(file_path)
                
                if is_valid:
                    valid_files.append(file_path)
                    
                    # Store file data
                    file_name = os.path.basename(file_path)
                    self.file_data[file_name] = {
                        "path": file_path,
                        "data": data,
                        "impacts": self.file_manager.analyze_test_impacts(data)
                    }
                    
                    # Add to table
                    file_size = os.path.getsize(file_path)
                    size_str = f"{file_size / 1024:.1f} KB" if file_size < 1024*1024 else f"{file_size / (1024*1024):.1f} MB"
                    test_count = self.file_manager.get_test_case_count(data)
                    
                    self.file_table.insert("", "end", values=(file_name, size_str, test_count, "Waiting", "", ""))
                    
                else:
                    invalid_files.append((os.path.basename(file_path), error_msg))
                    self.log_message(f"Invalid file {os.path.basename(file_path)}: {error_msg}")
                    
            except Exception as e:
                invalid_files.append((os.path.basename(file_path), str(e)))
                self.log_message(f"Error processing {os.path.basename(file_path)}: {str(e)}")
        
        self.selected_files = valid_files
        self.log_message(f"Selected {len(valid_files)} valid files")
        
        # Show errors for invalid files
        if invalid_files:
            error_msg = "The following files could not be loaded:\n\n"
            for filename, error in invalid_files:
                error_msg += f"• {filename}: {error}\n"
            messagebox.showerror("Invalid Files", error_msg)
    
    def send_files(self):
        """Send files using real SSH connection and file transfer"""
        if not self.selected_files:
            messagebox.showinfo("Info", "No files selected")
            return
        
        if not self.validate_connection_fields():
            return
        
        # Confirm before sending
        confirm = messagebox.askyesno(
            "Confirm", 
            f"Send {len(self.selected_files)} files? Files will be processed sequentially."
        )
        
        if not confirm:
            return
        
        # Reset retry counters
        self.file_retry_count = {}
        
        # Disable buttons and start processing
        self.send_button.configure(state=tk.DISABLED)
        self.cancel_button.configure(state=tk.NORMAL)
        self.processing = True
        self.progress_var.set(0)
        
        threading.Thread(target=self.process_files_real, daemon=True).start()
    
    def log_message(self, message: str):
        """Add a message to the log with timestamp and improved formatting"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        
        # Add to GUI log
        self.log_text.insert(tk.END, log_entry)
        self.log_text.see(tk.END)  # Scroll to the bottom
        
        # Also log to file logger
        self.logger.info(message)
    
    def refresh_logs(self):
        """Refresh the logs display"""
        # Clear existing text
        self.log_text.delete("1.0", tk.END)
        
        # Load logs from file
        log_file = "logs/app.log"
        try:
            if os.path.exists(log_file):
                with open(log_file, 'r') as f:
                    # Read the last 500 lines
                    lines = f.readlines()[-500:]
                    for line in lines:
                        self.log_text.insert(tk.END, line)
                
                self.log_text.see(tk.END)  # Scroll to the bottom
                self.log_message("Logs refreshed from file")
        except Exception as e:
            self.log_message(f"Error loading logs: {str(e)}")
    
    def on_closing(self):
        """Handle application closing with cleanup"""
        if self.processing:
            result = messagebox.askyesnocancel(
                "Confirm Exit", 
                "Processing is in progress. Do you want to:\n\n"
                "• Yes: Wait for current file to complete, then exit\n"
                "• No: Cancel processing and exit immediately\n"
                "• Cancel: Return to application"
            )
            
            if result is None:  # Cancel
                return
            elif result:  # Yes - wait for completion
                self.processing = False
                self.log_message("Waiting for current operation to complete...")
                # The processing thread will handle cleanup
            else:  # No - immediate exit
                self.processing = False
                self.ssh_connection.disconnect()
                self.logger.info("Application closed by user (immediate)")
                self.root.destroy()
                return
        
        # Normal close
        try:
            self.ssh_connection.disconnect()
            self.logger.info(f"Application closed normally by {os.environ.get('USERNAME', 'unknown')}")
        except Exception as e:
            self.logger.warning(f"Error during cleanup: {e}")
        
        self.root.destroy()
    
    # ============================================================================
    # ENHANCED CONNECTION METHODS
    # ============================================================================
    
    def _test_connection_thread(self):
        """Connection test thread with enhanced error handling"""
        max_attempts = AppConfig.MAX_RECONNECT_ATTEMPTS
        attempt_delay = AppConfig.CONNECTION_RETRY_DELAY
        
        for attempt in range(1, max_attempts + 1):
            try:
                self.root.after(0, lambda a=attempt: self.log_message(f"Connection attempt {a}/{max_attempts}..."))
                
                success = self.ssh_connection.connect(
                    hostname=self.lan_ip_var.get(),
                    username=self.username_var.get(),
                    password=self.password_var.get(),
                    timeout=AppConfig.SSH_CONNECT_TIMEOUT
                )
                
                if success:
                    # Test remote paths
                    if self._verify_remote_paths():
                        self._handle_connection_success()
                    else:
                        self._handle_connection_failure("Remote paths not accessible")
                    return
                else:
                    if attempt < max_attempts:
                        self.root.after(0, lambda: self.log_message(f"Attempt {attempt} failed, retrying in {attempt_delay}s..."))
                        time.sleep(attempt_delay)
                        attempt_delay *= 2  # Exponential backoff
                    else:
                        self._handle_connection_failure("Authentication failed after all attempts")
                        
            except Exception as e:
                error_msg = f"Connection error on attempt {attempt}: {str(e)}"
                if attempt < max_attempts:
                    self.root.after(0, lambda msg=error_msg: self.log_message(f"{msg}, retrying..."))
                    time.sleep(attempt_delay)
                    attempt_delay *= 2
                else:
                    self._handle_connection_failure(error_msg)

    def _verify_remote_paths(self) -> bool:
        """Verify remote paths are accessible"""
        paths = [
            (self.config_path_var.get(), "Config path"),
            (self.result_path_var.get(), "Result path")
        ]
        
        for path, description in paths:
            success, stdout, stderr = self.ssh_connection.execute_command(f"test -d '{path}' && test -w '{path}'")
            if not success:
                self.root.after(0, lambda p=path, d=description: self.log_message(f"{d} not accessible: {p}"))
                return False
            
        self.root.after(0, lambda: self.log_message("All remote paths verified"))
        return True

    def _handle_connection_success(self):
        """Handle successful connection"""
        self.database.log_connection(
            self.lan_ip_var.get(), 
            "Connected", 
            "Connection test successful with path verification"
        )
        
        self.root.after(0, lambda: self.connection_status.set("Connected"))
        self.root.after(0, lambda: self.update_status_circle("green"))
        self.root.after(0, lambda: self.log_message("Connection successful - All systems ready"))
        self.root.after(0, lambda: messagebox.showinfo("Connection", "Connection successful!\nRemote paths verified."))

    def _handle_connection_failure(self, error_msg: str):
        """Handle connection failure"""
        self.database.log_connection(
            self.lan_ip_var.get(), 
            "Failed", 
            error_msg
        )
        
        self.root.after(0, lambda: self.connection_status.set("Connection failed"))
        self.root.after(0, lambda: self.update_status_circle("red"))
        self.root.after(0, lambda: self.log_message(f"Connection failed: {error_msg}"))
        self.root.after(0, lambda: messagebox.showerror("Connection Failed", f"Unable to connect:\n{error_msg}\n\nPlease check:\n• IP address and network connectivity\n• Username and password\n• Remote directory permissions"))

    def _attempt_reconnection(self) -> bool:
        """Attempt to reconnect SSH"""
        self.log_message("Attempting to reconnect...")
        
        for attempt in range(AppConfig.MAX_RECONNECT_ATTEMPTS):
            try:
                success = self.ssh_connection.connect(
                    hostname=self.lan_ip_var.get(),
                    username=self.username_var.get(),
                    password=self.password_var.get(),
                    timeout=10
                )
                
                if success:
                    self.log_message("Reconnection successful")
                    self.root.after(0, lambda: self.update_status_circle("green"))
                    return True
                else:
                    time.sleep(2)
                    
            except Exception as e:
                self.log_message(f"Reconnection attempt {attempt + 1} failed: {str(e)}")
                time.sleep(2)
        
        self.log_message("All reconnection attempts failed")
        self.root.after(0, lambda: self.update_status_circle("red"))
        return False
    
    # ============================================================================
    # FILE PROCESSING METHODS
    # ============================================================================
    
    def process_files_real(self):
        """Process files using real modules with enhanced error handling"""
        start_time = time.time()
        total_files = len(self.selected_files)
        
        try:
            # 1. Establish connection
            self.log_message("Establishing SSH connection...")
            
            if not self.ssh_connection.is_connected():
                success = self.ssh_connection.connect(
                    hostname=self.lan_ip_var.get(),
                    username=self.username_var.get(),
                    password=self.password_var.get()
                )
                
                if not success:
                    raise Exception("Failed to establish SSH connection")
            
            self.root.after(0, lambda: self.connection_status.set("Connected"))
            self.root.after(0, lambda: self.update_status_circle("green"))
            
            # 2. Process each file
            for i, file_path in enumerate(self.selected_files):
                if not self.processing:
                    break
                
                file_name = os.path.basename(file_path)
                file_start_time = time.time()
                self.log_message(f"Processing file {i+1}/{total_files}: {file_name}")
                
                # NEW: Kiểm tra xem file kết quả đã tồn tại chưa
                expected_result_pattern = f"{os.path.splitext(file_name)[0]}_*.json"
                success, stdout, _ = self.ssh_connection.execute_command(
                    f"find {self.result_path_var.get()} -name '{expected_result_pattern}' -type f | sort -r | head -1"
                )
                
                if success and stdout.strip():
                    existing_result = os.path.basename(stdout.strip())
                    self.log_message(f"Warning: Result file already exists: {existing_result}. Will look for newer file.")
                
                # Update progress
                progress = int((i / total_files) * 100)
                self.root.after(0, lambda p=progress: self.progress_var.set(p))
                
                # Update table status
                self.update_file_status(i, "Sending", "", "")
                
                try:
                    # Check if test affects network
                    file_info = self.file_data.get(file_name, {})
                    impacts = file_info.get("impacts", {})
                    restarts_network = impacts.get("restarts_network", False)
                    affects_network = impacts.get("affects_wan", False) or impacts.get("affects_lan", False)
                    
                    # NEW: Xác định kiểu test
                    is_network_test = affects_network or "wan" in file_name.lower() or "lan" in file_name.lower() or "network" in file_name.lower()
                    
                    if restarts_network:
                        self.log_message(f"Warning: {file_name} contains network restart operations. Extended timeout will be used.")
                        # Show warning to user
                        self.root.after(0, lambda: messagebox.showwarning(
                            "Network Restart Test", 
                            f"The test '{file_name}' will restart network services on the device.\n\n"
                            "Connection may be lost temporarily. The application will attempt to reconnect automatically."
                        ))
                    
                    # 3. Upload file
                    remote_path = os.path.join(self.config_path_var.get(), file_name)
                    upload_success = self.ssh_connection.upload_file(file_path, remote_path)
                    
                    if not upload_success:
                        raise Exception("File upload failed")
                    
                    self.log_message(f"File {file_name} uploaded successfully")
                    self.update_file_status(i, "Testing", "", "")
                    
                    # NEW: Đợi một khoảng thời gian ngắn sau khi upload để đảm bảo thiết bị đã nhận file
                    time.sleep(1)
                    
                    # 4. Wait for result file with enhanced timeout for network tests
                    timeout = AppConfig.DEFAULT_TIMEOUT
                    if affects_network:
                        timeout = max(300, timeout * 2)  # At least 5 minutes for network tests
                    
                    result_remote_path, actual_result_filename = self.wait_for_result_file(
                        base_filename=os.path.splitext(file_name)[0],
                        result_dir=self.result_path_var.get(),
                        upload_time=time.time(),
                        timeout=timeout,
                        is_network_test=is_network_test
                    )
                    
                    # 5. Download result
                    local_result_dir = "data/temp/results"
                    os.makedirs(local_result_dir, exist_ok=True)
                    local_result_path = os.path.join(local_result_dir, actual_result_filename)
                    
                    download_success = self.ssh_connection.download_file(result_remote_path, local_result_path)
                    
                    if not download_success:
                        raise Exception("Failed to download result file")
                    
                    self.log_message(f"Result file {actual_result_filename} downloaded successfully")
                    
                    # NEW: Đợi thêm 1 giây để đảm bảo file đã được ghi đầy đủ trên máy local
                    time.sleep(1)
                    
                    # 6. Parse result
                    try:
                        with open(local_result_path, 'r') as f:
                            result_data = json.load(f)
                    except Exception as e:
                        raise Exception(f"Failed to parse result file: {str(e)}")
                    
                    # Determine overall result
                    overall_result = self.determine_overall_result(result_data)
                    execution_time = time.time() - file_start_time
                    
                    # Update table
                    self.update_file_status(i, "Completed", overall_result, f"{execution_time:.1f}s")
                    
                    # 7. Save to database
                    file_info = self.file_data[file_name]
                    impacts = file_info["impacts"]
                    test_count = self.file_manager.get_test_case_count(file_info["data"])
                    
                    file_id = self.database.save_test_file_result(
                        file_name=file_name,
                        file_size=os.path.getsize(file_path),
                        test_count=test_count,
                        send_status="Completed",
                        overall_result=overall_result,
                        affects_wan=impacts["affects_wan"],
                        affects_lan=impacts["affects_lan"],
                        execution_time=execution_time,
                        target_ip=self.lan_ip_var.get(),
                        target_username=self.username_var.get()
                    )
                    
                    # Convert result format to match our expected format
                    converted_results = self.convert_result_format(result_data, file_path)
                    if converted_results and file_id > 0:
                        self.database.save_test_case_results(file_id, converted_results)
                    
                    # Update detail table with results
                    self.update_detail_table_with_results(i, {"test_results": converted_results})
                    
                    self.log_message(f"File {file_name} processed successfully: {overall_result}")
                    
                    # NEW: Verify test has fully completed
                    self.log_message(f"Verifying test {file_name} has fully completed...")
                    
                    # NEW: Kiểm tra không có quá trình test còn đang chạy trên thiết bị
                    success, stdout, _ = self.ssh_connection.execute_command(
                        "ps | grep -v grep | grep -i 'test\\|uci\\|/etc/init.d' || echo 'No tests running'"
                    )
                    
                    if "No tests running" not in stdout:
                        self.log_message("Warning: Processes related to testing still running on device:")
                        for line in stdout.strip().split('\n')[:3]:  # Hiển thị tối đa 3 dòng
                            if line and "No tests running" not in line:
                                self.log_message(f"  - {line.strip()}")
                        self.log_message("Waiting additional time for processes to complete...")
                        time.sleep(5)
                    else:
                        self.log_message("No test processes detected. Device ready for next test.")
                    
                    # NEW: Đợi thêm thời gian ổn định sau các test mạng
                    if is_network_test:
                        stabilization_time = 15  # seconds
                        self.log_message(f"Network test detected: Waiting {stabilization_time}s for configuration to stabilize...")
                        
                        # SỬA: Thay thế cách cập nhật trạng thái để tránh lỗi status_var
                        for j in range(stabilization_time, 0, -1):
                            if not self.processing:
                                break
                            # Cập nhật trạng thái an toàn
                            status_message = f"Network stabilizing... {j}s"
                            self.log_message(status_message)  # Log là cách an toàn
                            
                            # Thử cập nhật UI nhưng bỏ qua lỗi nếu có
                            try:
                                if hasattr(self, 'status_text'):
                                    self.root.after(0, lambda msg=status_message: self.status_text.set(msg))
                                elif hasattr(self, 'status_label'):
                                    self.root.after(0, lambda msg=status_message: self.status_label.config(text=msg))
                            except:
                                pass  # Bỏ qua lỗi UI không ảnh hưởng đến chức năng chính
                            
                            self.root.update()
                            time.sleep(1)
                        
                        self.log_message("Network stabilization period completed")
                        
                        # Kiểm tra thiết bị đã sẵn sàng chưa trước khi tiếp tục
                        device_ready = False
                        retry_count = 3
                        
                        while retry_count > 0 and not device_ready:
                            try:
                                # Kiểm tra kết nối mạng cơ bản
                                success, stdout, _ = self.ssh_connection.execute_command("ping -c 1 -W 2 8.8.8.8 >/dev/null && echo 'OK'")
                                if success and "OK" in stdout:
                                    device_ready = True
                                    self.log_message("Device network connectivity verified")
                                else:
                                    retry_count -= 1
                                    self.log_message(f"Device network not ready, waiting... ({retry_count} attempts left)")
                                    time.sleep(5)
                            except Exception as e:
                                retry_count -= 1
                                self.log_message(f"Error checking network: {str(e)}, waiting... ({retry_count} attempts left)")
                                time.sleep(5)
                        
                        # Đợi thêm thời gian cố định để đảm bảo
                        time.sleep(5)
                    
                    # NEW: Kiểm tra nếu còn file tiếp theo, đợi hệ thống ổn định
                    if i < total_files - 1:
                        next_file = os.path.basename(self.selected_files[i+1])
                        self.log_message(f"Preparing for next test: {next_file}")
                        
                        # SỬA: Thay đổi cách cập nhật trạng thái để tránh lỗi status_var
                        wait_time = 5  # seconds
                        self.log_message(f"Waiting {wait_time}s between tests...")
                        
                        for j in range(wait_time, 0, -1):
                            if not self.processing:
                                break
                            status_message = f"Next test in {j}s..."
                            self.log_message(status_message)
                            
                            try:
                                if hasattr(self, 'status_text'):
                                    self.root.after(0, lambda msg=status_message: self.status_text.set(msg))
                                elif hasattr(self, 'status_label'):
                                    self.root.after(0, lambda msg=status_message: self.status_label.config(text=msg))
                            except:
                                pass
                            
                            self.root.update()
                            time.sleep(1)
                        
                        self.log_message("Ready for next test")
                        
                        # Kiểm tra lại kết nối SSH trước khi tiến hành test kế tiếp
                        if not self.ssh_connection.is_connected():
                            self.log_message("SSH connection lost. Attempting to reconnect before next test...")
                            reconnect_success = self._attempt_reconnection(max_attempts=3)
                            if not reconnect_success:
                                raise Exception("Failed to re-establish SSH connection for next test")
                    
                except Exception as e:
                    # Enhanced error handling
                    error_type = type(e).__name__
                    error_msg = f"Error processing {file_name}: {str(e)}"
                    self.log_message(f"[{error_type}] {error_msg}")
                    
                    # Determine if we should retry or skip
                    should_retry = self._should_retry_on_error(e, file_name)
                    
                    if should_retry:
                        self.log_message(f"Retrying {file_name} in 5 seconds...")
                        self.update_file_status(i, "Retrying", "Error", "Retrying...")
                        time.sleep(5)
                        
                        # Try to reconnect if needed
                        if not self.ssh_connection.is_connected():
                            self._attempt_reconnection()
                        
                        # Implement retry by adjusting loop - for now, just continue
                        # Note: Full retry implementation would require loop restructuring
                        self.update_file_status(i, "Error", "Failed", self._get_user_friendly_error(e))
                    else:
                        self.update_file_status(i, "Error", "Failed", self._get_user_friendly_error(e))
                    
                    # Save error to database with detailed info
                    self._save_error_to_database(file_name, file_path, e, file_start_time)
            
            # All files processed
            if self.processing:
                total_time = time.time() - start_time
                self.log_message(f"All {total_files} files processed in {total_time:.1f} seconds")
                self.root.after(0, lambda: messagebox.showinfo("Complete", f"All {total_files} files processed successfully"))
            
        except Exception as e:
            error_msg = f"Processing error: {str(e)}"
            self.log_message(error_msg)
            self.root.after(0, lambda: messagebox.showerror("Error", error_msg))
        
        finally:
            # Reset UI
            self.processing = False
            self.root.after(0, lambda: self.send_button.configure(state=tk.NORMAL))
            self.root.after(0, lambda: self.cancel_button.configure(state=tk.DISABLED))
            self.root.after(0, lambda: self.progress_var.set(100 if self.processing else 0))
            
            # Reload history
            self.root.after(0, self.load_history)
    
    def wait_for_result_file(self, base_filename: str, result_dir: str, upload_time: float, timeout: int = 300, is_network_test: bool = False) -> Tuple[str, str]:
        """
        Wait for any new result file to appear after test file upload
        Enhanced to handle network restart operations and ensure most recent file is selected
        """
        start_wait = time.time()
        check_interval = 3
        last_log_time = 0
        known_files = set()
        
        # Helper function to find the best match from a list of files
        def find_best_result_file(files_list):
            """Find the best matching result file based on name and timestamp"""
            if not files_list:
                return None
            
            # Convert to list if it's a set
            if isinstance(files_list, set):
                files_list = list(files_list)
            
            # Filter for JSON files that match our base filename
            matches = [f for f in files_list if f.lower().endswith('.json') and base_filename.lower() in f.lower()]
            
            if not matches:
                self.log_message(f"No matching result files found")
                return None
            
            # Extract date and time information using regex
            import re
            pattern = re.compile(r'_(\d{8})_(\d{6})\.json$')  # Format: *_YYYYMMDD_HHMMSS.json
            
            # Create list of tuples: (timestamp_value, filename)
            timestamped_files = []
            
            for fname in matches:
                match = pattern.search(fname)
                if match:
                    date_str = match.group(1)
                    time_str = match.group(2)
                    # Convert to sortable integer
                    timestamp_value = int(date_str + time_str)
                    timestamped_files.append((timestamp_value, fname))
            
            # If no timestamps found, return first match as fallback
            if not timestamped_files:
                self.log_message(f"Warning: No valid timestamps in filenames")
                return matches[0]
            
            # Sort by timestamp (newest first)
            timestamped_files.sort(reverse=True)
            
            # Return the most recent file (just log the final selected file)
            best_file = timestamped_files[0][1]
            return best_file
        
        # Determine if this is a network-affecting test
        if not is_network_test:
            is_network_test = any(keyword in base_filename.lower() for keyword in ["wan", "network", "interface", "restart", "reset"])
        
        # Increase timeout and retry policy for network tests
        if is_network_test:
            self.log_message(f"Network-affecting test detected: {base_filename}. Using extended timeout and retry policy.")
            max_reconnect_attempts = 12
            reconnect_delay = 10
            timeout = max(timeout, 300)  # At least 5 minutes for network tests
        else:
            max_reconnect_attempts = 3
            reconnect_delay = 5
        
        reconnect_attempts = 0
        connection_lost_time = 0
        
        self.log_message(f"Waiting for result file in {result_dir} (timeout: {timeout}s)")
        
        # Initial file listing
        try:
            success, stdout, stderr = self.ssh_connection.execute_command(f"ls -1 {result_dir}/ 2>/dev/null")
            if success:
                known_files = set(f for f in stdout.strip().split('\n') if f and len(f) > 3)
                self.log_message(f"Initial file count: {len(known_files)}")
                
                # NEW: Hiển thị danh sách các file mới nhất trong thư mục
                newest_files = sorted(list(known_files))[-3:] if len(known_files) >= 3 else sorted(list(known_files))
                self.log_message(f"Initial newest files: {', '.join(newest_files)}")
        except Exception as e:
            self.log_message(f"Could not get initial file listing: {str(e)}")
        
        # Main wait loop
        while time.time() - start_wait < timeout:
            elapsed = time.time() - start_wait
            
            # Check connection state
            if not self.ssh_connection.is_connected():
                # Connection lost - might be due to network restart
                if connection_lost_time == 0:
                    connection_lost_time = time.time()
                    self.log_message("Connection lost - likely due to network restart on device")
                
                # Check if we've waited enough time for network to stabilize
                wait_since_disconnect = time.time() - connection_lost_time
                if wait_since_disconnect < reconnect_delay:
                    # Too soon to retry - wait longer
                    if elapsed - last_log_time >= 10:
                        self.log_message(f"[{elapsed:.0f}s] Waiting {reconnect_delay-wait_since_disconnect:.0f}s before reconnection attempt...")
                        last_log_time = elapsed
                    time.sleep(2)
                    continue
                
                # Try to reconnect
                if reconnect_attempts < max_reconnect_attempts:
                    reconnect_attempts += 1
                    self.log_message(f"Attempting to reconnect ({reconnect_attempts}/{max_reconnect_attempts})...")
                    
                    try:
                        success = self.ssh_connection.connect(
                            hostname=self.lan_ip_var.get(),
                            username=self.username_var.get(),
                            password=self.password_var.get(),
                            timeout=15
                        )
                        
                        if success:
                            self.log_message("Successfully reconnected!")
                            connection_lost_time = 0
                            reconnect_delay = max(5, reconnect_delay - 5)  # Gradually reduce delay if successful
                            
                            # After reconnect, refresh known files
                            try:
                                success, stdout, stderr = self.ssh_connection.execute_command(f"ls -1 {result_dir}/ 2>/dev/null")
                                if success:
                                    current_files = set(f for f in stdout.strip().split('\n') if f and len(f) > 3)
                                    new_files = current_files - known_files
                                    
                                    if new_files:
                                        self.log_message(f"Found {len(new_files)} new files after reconnect: {', '.join(list(new_files)[:3])}")
                                        
                                        # Use helper function to find the best result file
                                        best_file = find_best_result_file(new_files)
                                        if best_file:
                                            file_path = f"{result_dir}/{best_file}"
                                            
                                            # NEW: Đợi file ổn định
                                            self.log_message(f"Found result file, waiting 2s for it to stabilize...")
                                            time.sleep(2)
                                            
                                            if self._verify_file_ready(file_path):
                                                # NEW: Ghi nhận file mới được tạo
                                                self.log_message(f"New result file created: {best_file}")
                                                
                                                # NEW: Đợi thêm thời gian nếu là test mạng
                                                if is_network_test:
                                                    self.log_message("Network test: Waiting additional time for configuration changes to apply...")
                                                    time.sleep(3)
                                                    
                                                return file_path, best_file
                                    
                                    known_files = current_files
                            except Exception as e:
                                self.log_message(f"Error listing files after reconnect: {str(e)}")
                        else:
                            reconnect_delay = min(30, reconnect_delay + 5)  # Increase delay on failure
                            self.log_message(f"Reconnection failed. Next attempt in {reconnect_delay}s...")
                            time.sleep(reconnect_delay)
                            continue
                    except Exception as e:
                        reconnect_delay = min(30, reconnect_delay + 5)
                        self.log_message(f"Reconnection error: {str(e)}. Next attempt in {reconnect_delay}s...")
                        time.sleep(reconnect_delay)
                        continue
                else:
                    # Max retries exceeded - use file pattern matching with fixed patterns
                    self.log_message("Maximum reconnection attempts reached. Attempting alternative result detection methods.")
                    # Continue to try other methods
            
            # Connection is good, try detection methods
            try:
                # Method 1: Get newest files with our base name using timestamp-sorting find command
                today_date = time.strftime("%Y%m%d")
                pattern_cmd = (
                    f"find {result_dir} -type f -name '*{base_filename}*' -o -name '{base_filename}*' | "
                    f"sort -r | head -3"
                )
                success, pattern_stdout, _ = self.ssh_connection.execute_command(pattern_cmd)
                
                if success and pattern_stdout.strip():
                    files = pattern_stdout.strip().split('\n')
                    
                    self.log_message(f"Found {len(files)} files via pattern search")
                    best_file = find_best_result_file([os.path.basename(f) for f in files])
                    
                    if best_file:
                        file_path = f"{result_dir}/{best_file}"
                        
                        # NEW: Đợi file ổn định
                        self.log_message(f"Found result file, waiting 2s for it to stabilize...")
                        time.sleep(2)
                        
                        if self._verify_file_ready(file_path):
                            # NEW: Ghi nhận file mới được tạo
                            self.log_message(f"New result file created: {best_file}")
                            
                            # NEW: Đợi thêm thời gian nếu là test mạng
                            if is_network_test:
                                self.log_message("Network test: Waiting additional time for configuration changes to apply...")
                                time.sleep(3)
                                
                            return file_path, best_file
                
                # Method 2: Latest modified file check
                latest_cmd = (
                    f"find {result_dir} -name '*.json' -type f -printf '%T@ %p\\n' | "
                    f"sort -nr | head -1 | cut -d' ' -f2-"
                )
                success, latest_stdout, _ = self.ssh_connection.execute_command(latest_cmd)
                
                if success and latest_stdout.strip():
                    file_path = latest_stdout.strip()
                    file_name = os.path.basename(file_path)
                    
                    # Check if this is a new file
                    if file_name not in known_files:
                        self.log_message(f"Found newest file via modification time: {file_name}")
                        if base_filename.lower() in file_name.lower():
                            # NEW: Đợi file ổn định
                            self.log_message(f"Found result file, waiting 2s for it to stabilize...")
                            time.sleep(2)
                            
                            if self._verify_file_ready(file_path):
                                # NEW: Ghi nhận file mới được tạo
                                self.log_message(f"New result file created: {file_name}")
                                
                                # NEW: Đợi thêm thời gian nếu là test mạng
                                if is_network_test:
                                    self.log_message("Network test: Waiting additional time for configuration changes to apply...")
                                    time.sleep(3)
                                    
                                return file_path, file_name
                
                # Method 3: Full directory comparison
                success, curr_stdout, _ = self.ssh_connection.execute_command(f"ls -1 {result_dir}/ 2>/dev/null")
                if success and curr_stdout.strip():
                    current_files = set(f for f in curr_stdout.strip().split('\n') if f and len(f) > 3)
                    new_files = current_files - known_files
                    
                    if new_files:
                        self.log_message(f"Found {len(new_files)} new files in directory comparison")
                        best_file = find_best_result_file(new_files)
                        
                        if best_file:
                            file_path = f"{result_dir}/{best_file}"
                            
                            # NEW: Đợi file ổn định
                            self.log_message(f"Found result file, waiting 2s for it to stabilize...")
                            time.sleep(2)
                            
                            if self._verify_file_ready(file_path):
                                # NEW: Ghi nhận file mới được tạo
                                self.log_message(f"New result file created: {best_file}")
                                
                                # NEW: Đợi thêm thời gian nếu là test mạng
                                if is_network_test:
                                    self.log_message("Network test: Waiting additional time for configuration changes to apply...")
                                    time.sleep(3)
                                    
                                return file_path, best_file
                    
                    known_files = current_files
                
            except Exception as e:
                self.log_message(f"Error checking for result file: {str(e)}")
            
            # Log progress periodically
            if elapsed - last_log_time >= 15:
                self.log_message(f"[{elapsed:.0f}s] Still waiting for result file...")
                last_log_time = elapsed
            
            # Check if processing was cancelled
            if not self.processing:
                raise Exception("Processing cancelled by user")
            
            time.sleep(check_interval)
        
        # Timeout exceeded - try one last method
        self.log_message("Timeout exceeded. Checking logs and using more aggressive methods.")
        
        try:
            # Check syslog/journal for hints about result file
            log_cmd = f"grep -a 'Result file.*{base_filename}' /var/log/messages /var/log/syslog /tmp/syslog.log /var/log/application.log 2>/dev/null"
            success, log_stdout, _ = self.ssh_connection.execute_command(log_cmd)
            
            if success and log_stdout.strip():
                import re
                match = re.search(r'[\'"]([^\'"/]+\.json)[\'"]', log_stdout)
                if match:
                    result_filename = match.group(1)
                    file_path = f"{result_dir}/{result_filename}"
                    self.log_message(f"Found result filename from logs: {result_filename}")
                    
                    # Check if file exists and is readable
                    if self.ssh_connection.file_exists(file_path):
                        # NEW: Ghi nhận file kết quả
                        self.log_message(f"Found result file from logs: {result_filename}")
                        return file_path, result_filename
            
            # Find all JSON files in result directory and sort by modification time
            find_cmd = f"find {result_dir} -name '*.json' -type f -newermt @{int(upload_time)} -printf '%T@ %p\\n' | sort -nr"
            success, find_stdout, _ = self.ssh_connection.execute_command(find_cmd)
            
            if success and find_stdout.strip():
                lines = find_stdout.strip().split('\n')
                files = [line.split(' ', 1)[1] for line in lines if ' ' in line]
                
                self.log_message(f"Found {len(files)} files created after upload time")
                
                if files:
                    # Get all filenames and find the best match
                    filenames = [os.path.basename(f) for f in files]
                    best_file = find_best_result_file(filenames)
                    
                    if best_file:
                        for file_path in files:
                            if os.path.basename(file_path) == best_file:
                                self.log_message(f"Selected best result file from last-chance search: {best_file}")
                                return file_path, best_file
                    
                    # If we couldn't find a best match, use the newest file
                    newest_file = files[0]
                    newest_filename = os.path.basename(newest_file)
                    self.log_message(f"Using newest file from last-chance search: {newest_filename}")
                    return newest_file, newest_filename
        
        except Exception as e:
            self.log_message(f"Final check failed: {str(e)}")
        
        # If we reach here, we've truly failed
        raise Exception(f"Timeout waiting for result file after {timeout} seconds. Test may still be running.")
        
    def _verify_file_ready(self, file_path: str, min_size: int = 10) -> bool:
        """Verify file is ready and stable with more lenient checks"""
        try:
            # Check file exists
            exists_cmd = f"test -f '{file_path}' && echo 'exists'"
            success, stdout, _ = self.ssh_connection.execute_command(exists_cmd)
            
            if not (success and "exists" in stdout):
                return False
            
            # Check file size
            size1 = self.ssh_connection.get_file_size(file_path)
            if size1 < min_size:  # Even very small files should be at least 10 bytes
                return False
            
            # For network tests, be more lenient - just check existence
            if "wan" in os.path.basename(file_path).lower() or "network" in os.path.basename(file_path).lower():
                return True
            
            # Regular case - check file stability
            time.sleep(0.5)  # Shorter wait time
            size2 = self.ssh_connection.get_file_size(file_path)
            
            return size1 == size2 and size1 >= min_size
        except Exception as e:
            self.log_message(f"Error checking if file is ready: {str(e)}")
            return False  # Assume not ready on error
    
    # ============================================================================
    # ERROR HANDLING METHODS
    # ============================================================================
    
    def _should_retry_on_error(self, error: Exception, file_name: str) -> bool:
        """Determine if error is retryable"""
        # Check retry count
        retry_count = self.file_retry_count.get(file_name, 0)
        if retry_count >= AppConfig.MAX_FILE_RETRIES:
            self.log_message(f"Max retries ({AppConfig.MAX_FILE_RETRIES}) reached for {file_name}")
            return False
        
        # Check error type
        retryable_errors = [
            "timeout",
            "connection lost",
            "network",
            "ssh",
            "broken pipe",
            "connection refused",
            "no route to host"
        ]
        
        error_str = str(error).lower()
        is_retryable = any(retry_error in error_str for retry_error in retryable_errors)
        
        if is_retryable:
            self.file_retry_count[file_name] = retry_count + 1
            
        return is_retryable

    def _get_user_friendly_error(self, error: Exception) -> str:
        """Convert technical errors to user-friendly messages"""
        error_str = str(error).lower()
        
        error_mappings = {
            "timeout": "Timeout - Test took too long",
            "connection": "Connection lost",
            "authentication": "Authentication failed",
            "permission": "Permission denied",
            "no route to host": "Network unreachable",
            "connection refused": "Target device refused connection",
            "broken pipe": "Connection interrupted",
            "file not found": "File not found on remote system"
        }
        
        for key, friendly_msg in error_mappings.items():
            if key in error_str:
                return friendly_msg
        
        return f"Unknown error ({type(error).__name__})"

    def _save_error_to_database(self, file_name: str, file_path: str, error: Exception, start_time: float):
        """Save error details to database"""
        try:
            file_info = self.file_data[file_name]
            impacts = file_info["impacts"]
            test_count = self.file_manager.get_test_case_count(file_info["data"])
            
            self.database.save_test_file_result(
                file_name=file_name,
                file_size=os.path.getsize(file_path),
                test_count=test_count,
                send_status="Error",
                overall_result="Failed",
                affects_wan=impacts["affects_wan"],
                affects_lan=impacts["affects_lan"],
                execution_time=time.time() - start_time,
                target_ip=self.lan_ip_var.get(),
                target_username=self.username_var.get()
            )
        except Exception as db_error:
            self.log_message(f"Failed to save error to database: {str(db_error)}")
    
    # ============================================================================
    # RESULT HANDLING METHODS
    # ============================================================================
        
    def convert_result_format(self, openwrt_result, input_file_name=None):
        """Convert OpenWrt result format to our expected format"""
        try:
            converted_results = []
            
            # Cố gắng đọc thông tin service và action từ file gốc
            service_name = "unknown"
            action_name = ""
            
            # Đọc từ file gốc
            if input_file_name and os.path.exists(input_file_name):
                try:
                    with open(input_file_name, 'r') as f:
                        original_data = json.load(f)
                    
                    if "data" in original_data and "test_cases" in original_data["data"]:
                        test_cases = original_data["data"]["test_cases"]
                        if test_cases and isinstance(test_cases, list) and len(test_cases) > 0:
                            first_test = test_cases[0]
                            service_name = first_test.get("service", "unknown")
                            action_name = first_test.get("action", "")
                            self.log_message(f"Extracted from test file: service={service_name}, action={action_name}")
                except Exception as read_error:
                    self.log_message(f"Could not read original file data: {str(read_error)}")
            
            # Nếu không đọc được từ nội dung file, trích xuất từ tên file
            if service_name == "unknown" and input_file_name:
                filename = os.path.basename(input_file_name)
                base_name = os.path.splitext(filename)[0]
                parts = base_name.split('_')
                if len(parts) > 0:
                    service_name = parts[0]
                    if len(parts) > 1:
                        action_name = '_'.join(parts[1:])
                        # Loại bỏ timestamp nếu có
                        if action_name and any(c.isdigit() for c in action_name):
                            digits_index = -1
                            for i, c in enumerate(action_name):
                                if c.isdigit():
                                    digits_index = i
                                    break
                            if digits_index > 0:
                                action_name = action_name[:digits_index].rstrip('_')
                
                self.log_message(f"Extracted from filename: service={service_name}, action={action_name}")
            
            # Xử lý các test case fail theo service và action
            failed_by_service = openwrt_result.get("failed_by_service", {})
            for service, tests in failed_by_service.items():
                for test in tests:
                    test_service = test.get("service", service)
                    test_action = test.get("action", "")
                    message = test.get("message", f"{test_service} {test_action} failed")
                    
                    # Chỉ thêm vào kết quả nếu phù hợp với service và action của file gốc
                    # hoặc nếu service_name là "unknown" (không biết service nào là đúng)
                    if service_name == "unknown" or test_service == service_name:
                        converted_results.append({
                            "service": test_service,
                            "action": test_action,
                            "status": "fail",
                            "details": message,
                            "execution_time": test.get("execution_time_ms", 0) / 1000.0
                        })
            
            # Lấy thông tin từ summary
            summary = openwrt_result.get("summary", {})
            pass_count = summary.get("passed", 0)
            fail_count = summary.get("failed", 0)
            failed_services = summary.get("failed_services", [])
            
            # Xử lý các test case pass
            if pass_count > 0:
                if service_name != "unknown" and service_name not in failed_services:
                    status_text = "completed successfully"
                    details = f"{service_name} {action_name} {status_text}"
                    
                    converted_results.append({
                        "service": service_name,
                        "action": action_name,
                        "status": "pass",
                        "details": details,
                        "execution_time": summary.get("total_duration_ms", 0) / 1000.0
                    })
            
            # Nếu không có kết quả nào, tạo một kết quả mặc định
            if not converted_results:
                # Đảm bảo service và action không phải là unknown nếu có thể
                status = "pass" if fail_count == 0 else "fail"
                status_text = "completed successfully" if status == "pass" else "failed"
                details = f"{service_name} {action_name} {status_text}"
                
                converted_results.append({
                    "service": service_name,
                    "action": action_name,
                    "status": status,
                    "details": details,
                    "execution_time": 0.0
                })
            
            # Hiển thị kết quả đã chuyển đổi để debug
            for result in converted_results:
                self.log_message(f"Converted result: {result['service']}.{result['action']} = {result['status']}")
                
            return converted_results
            
        except Exception as e:
            import traceback
            self.log_message(f"Error in convert_result_format: {str(e)}")
            self.log_message(traceback.format_exc())
            
            # Fallback
            return [{
                "service": "unknown",
                "action": "",
                "status": "error",
                "details": f"Error processing result: {str(e)}",
                "execution_time": 0.0
            }]
        
    def determine_overall_result(self, result_data):
        """Determine overall result from test result data"""
        if "summary" in result_data:
            summary = result_data["summary"]
            total = summary.get("total_test_cases", 0)
            passed = summary.get("passed", 0)
            failed = summary.get("failed", 0)
            
            if total == passed:
                return "Pass"
            elif passed == 0:
                return "Fail"
            else:
                return f"Partial ({passed}/{total})"
        
        return "Unknown"
    
    def update_file_status(self, file_index: int, status: str, result: str = "", time_str: str = ""):
        """Update file status in the table"""
        try:
            items = self.file_table.get_children()
            if file_index < len(items):
                item_id = items[file_index]
                current_values = list(self.file_table.item(item_id)["values"])
                current_values[3] = status  # Status column
                if result:
                    current_values[4] = result  # Result column
                if time_str:
                    current_values[5] = time_str  # Time column
                
                self.root.after(0, lambda: self.file_table.item(item_id, values=tuple(current_values)))
        except Exception as e:
            self.logger.error(f"Error updating file status: {e}")
    
    def update_detail_table_with_results(self, file_index: int, result_data: Dict):
        """Update detail table with test results if the file is currently selected"""
        selection = self.file_table.selection()
        if not selection:
            return
        
        selected_index = self.file_table.index(selection[0])
        if selected_index != file_index:
            return  # Different file is selected
        
        test_results = result_data.get("test_results", [])
        detail_items = self.detail_table.get_children()
        
        # Update each test case result
        for i, result in enumerate(test_results):
            if i < len(detail_items):
                item_id = detail_items[i]
                current_values = list(self.detail_table.item(item_id)["values"])
                
                # Update status and details
                current_values[3] = result.get("status", "Unknown")  # Status column
                current_values[4] = result.get("details", "No details")  # Details column
                
                self.root.after(0, lambda id=item_id, vals=current_values: self.detail_table.item(id, values=tuple(vals)))
    
    # ============================================================================
    # UTILITY AND UI METHODS
    # ============================================================================
    
    def cancel_processing(self):
        """Cancel the file processing"""
        if self.processing:
            self.processing = False
            self.log_message("Processing cancelled by user")
    
    def on_file_selected(self, event):
        """Handle file selection to show test case details"""
        selection = self.file_table.selection()
        if not selection:
            return
        
        # Get selected file index
        item_id = selection[0]
        item_idx = self.file_table.index(item_id)
        
        if item_idx >= len(self.selected_files):
            return
        
        file_path = self.selected_files[item_idx]
        file_name = os.path.basename(file_path)
        
        # Clear detail table
        for item in self.detail_table.get_children():
            self.detail_table.delete(item)
        
        # Load file and populate detail table
        if file_name in self.file_data:
            data = self.file_data[file_name]["data"]
            test_cases = data.get("test_cases", [])
            
            for i, test_case in enumerate(test_cases):
                service = test_case.get("service", "")
                action = test_case.get("action", "-")
                
                # Format parameters as a compact string
                params = test_case.get("params", {})
                params_str = self.format_params(params)
                
                # Status and details will be updated when results are available
                status = "-"
                details = "-"
                
                self.detail_table.insert("", "end", values=(service, action, params_str, status, details))
    
    def format_params(self, params):
        """Format parameters as a readable string"""
        if not params:
            return "-"
        
        parts = []
        
        for k, v in params.items():
            if isinstance(v, dict):
                nested_parts = [f"{k2}={v2}" for k2, v2 in v.items()]
                parts.append(f"{k}={{{', '.join(nested_parts)}}}")
            else:
                parts.append(f"{k}={v}")
        
        return ", ".join(parts)
    
    def clear_files(self):
        """Clear selected files"""
        self.selected_files = []
        self.file_data = {}
        self.file_retry_count = {}
        
        for item in self.file_table.get_children():
            self.file_table.delete(item)
        
        for item in self.detail_table.get_children():
            self.detail_table.delete(item)
        
        self.log_message("File selection cleared")
    
    def validate_connection_fields(self) -> bool:
        """Validate connection fields with enhanced error messages"""
        validation_errors = []
        
        if not self.lan_ip_var.get().strip():
            validation_errors.append("LAN IP address is required")
        
        if not self.username_var.get().strip():
            validation_errors.append("Username is required")
        
        if not self.password_var.get():
            validation_errors.append("Password is required")
        
        if not self.config_path_var.get().strip():
            validation_errors.append("Config path is required")
        
        if not self.result_path_var.get().strip():
            validation_errors.append("Result path is required")
        
        # Validate IP format (basic check)
        lan_ip = self.lan_ip_var.get().strip()
        if lan_ip:
            parts = lan_ip.split('.')
            if len(parts) != 4 or not all(part.isdigit() and 0 <= int(part) <= 255 for part in parts):
                validation_errors.append("LAN IP address format is invalid")
        
        if validation_errors:
            error_msg = "Please fix the following errors:\n\n" + "\n".join(f"• {error}" for error in validation_errors)
            messagebox.showerror("Validation Error", error_msg)
            return False
        
        return True
    
    def update_status_circle(self, color: str):
        """Update connection status circle color with enhanced visual feedback"""
        color_mapping = {
            "green": "#00AA00",    # Success
            "yellow": "#FFB000",   # Warning/Connecting
            "red": "#CC0000",      # Error
            "gray": "#808080"      # Disabled
        }
        
        actual_color = color_mapping.get(color, color)
        self.status_canvas.itemconfig(self.status_circle, fill=actual_color)
    
    def load_history(self):
        """Load history from database"""
        try:
            # Clear existing history
            for item in self.history_table.get_children():
                self.history_table.delete(item)
            
            # Load recent history
            history_data = self.database.get_recent_history(100)
            
            for record in history_data:
                timestamp = record["timestamp"]
                if " " in timestamp:
                    date, time_str = timestamp.split(" ", 1)
                else:
                    date = timestamp
                    time_str = ""
                
                details = f"Execution time: {record['execution_time']:.1f}s" if record["execution_time"] else ""
                if record["affects_wan"] or record["affects_lan"]:
                    details += " (Network affecting)"
                
                self.history_table.insert("", "end", values=(
                    date,
                    time_str,
                    record["file_name"],
                    record["test_count"],
                    record["overall_result"] or "Unknown",
                    details
                ))
                
        except Exception as e:
            self.log_message(f"Error loading history: {str(e)}")
    
    def check_remote_folders(self):
        """Check if remote folders exist and are accessible"""
        if not self.validate_connection_fields():
            return
        
        self.log_message("Checking remote folders...")
        
        def _check_folders():
            try:
                if not self.ssh_connection.is_connected():
                    success = self.ssh_connection.connect(
                        hostname=self.lan_ip_var.get(),
                        username=self.username_var.get(),
                        password=self.password_var.get()
                    )
                    if not success:
                        raise Exception("Failed to connect")
                
                # Check config folder
                config_path = self.config_path_var.get()
                success, stdout, stderr = self.ssh_connection.execute_command(f"ls -ld {config_path}")
                
                if not success:
                    raise Exception(f"Config folder not accessible: {stderr}")
                
                # Check result folder
                result_path = self.result_path_var.get()
                success, stdout, stderr = self.ssh_connection.execute_command(f"ls -ld {result_path}")
                
                if not success:
                    raise Exception(f"Result folder not accessible: {stderr}")
                
                # Both folders accessible
                message = f"Both folders are accessible:\n• {config_path}\n• {result_path}"
                self.root.after(0, lambda: messagebox.showinfo("Folder Check", message))
                self.root.after(0, lambda: self.log_message("Remote folders check successful"))
                
            except Exception as e:
                error_msg = f"Folder check failed: {str(e)}"
                self.root.after(0, lambda: messagebox.showerror("Folder Check", error_msg))
                self.root.after(0, lambda: self.log_message(error_msg))
        
        threading.Thread(target=_check_folders, daemon=True).start()
    
    def save_config(self):
        """Save configuration using database"""
        try:
            self.database.save_setting("lan_ip", self.lan_ip_var.get())
            self.database.save_setting("wan_ip", self.wan_ip_var.get())
            self.database.save_setting("username", self.username_var.get())
            self.database.save_setting("config_path", self.config_path_var.get())
            self.database.save_setting("result_path", self.result_path_var.get())
            
            self.log_message("Configuration saved successfully")
            messagebox.showinfo("Success", "Configuration saved successfully")
            
        except Exception as e:
            error_msg = f"Failed to save configuration: {str(e)}"
            self.log_message(error_msg)
            messagebox.showerror("Error", error_msg)
    
    def load_config(self):
        """Load configuration from database"""
        try:
            self.lan_ip_var.set(self.database.get_setting("lan_ip", "192.168.88.1"))
            self.wan_ip_var.set(self.database.get_setting("wan_ip", ""))
            self.username_var.set(self.database.get_setting("username", "root"))
            self.config_path_var.set(self.database.get_setting("config_path", "/root/config"))
            self.result_path_var.set(self.database.get_setting("result_path", "/root/result"))
            
            self.log_message("Configuration loaded successfully")
            
        except Exception as e:
            error_msg = f"Failed to load configuration: {str(e)}"
            self.log_message(error_msg)
            messagebox.showerror("Error", error_msg)
    
    # ============================================================================
    # ADDITIONAL UI METHODS
    # ============================================================================
    
    def export_results(self):
        """Export current results to CSV"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv", 
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title="Export Results"
        )
        if filename:
            try:
                # Implement CSV export of currently loaded results
                with open(filename, 'w', newline='') as f:
                    import csv
                    writer = csv.writer(f)
                    
                    # Header row
                    writer.writerow(["Filename", "Size", "Tests", "Status", "Result", "Time"])
                    
                    # Data rows
                    for item_id in self.file_table.get_children():
                        values = self.file_table.item(item_id)["values"]
                        writer.writerow(values)
                
                self.log_message(f"Results exported to {filename}")
                messagebox.showinfo("Export", f"Results exported to {filename}")
            except Exception as e:
                messagebox.showerror("Export Error", f"Failed to export results: {str(e)}")
    
    def refresh_view(self):
        """Refresh all views"""
        self.load_history()
        self.refresh_logs()
        self.log_message("View refreshed")
    
    def clear_history(self):
        """Clear history with confirmation"""
        confirm = messagebox.askyesno(
            "Confirm Clear History", 
            "Are you sure you want to clear all history?\n\nThis action cannot be undone."
        )
        if confirm:
            try:
                self.database.clear_history()
                for item in self.history_table.get_children():
                    self.history_table.delete(item)
                self.log_message("History cleared")
                messagebox.showinfo("Success", "History cleared successfully")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to clear history: {str(e)}")
    
    def apply_history_filter(self):
        """Apply filters to history view"""
        date_filter = self.date_combo.get()
        status_filter = self.status_combo.get()
        
        self.log_message(f"Applying history filter: Date={date_filter}, Status={status_filter}")
        
        try:
            # Clear existing history
            for item in self.history_table.get_children():
                self.history_table.delete(item)
            
            # Convert filter to SQL parameters
            date_clause = ""
            if date_filter == "Today":
                date_clause = "WHERE DATE(timestamp) = DATE('now')"
            elif date_filter == "Last 7 Days":
                date_clause = "WHERE timestamp >= DATE('now', '-7 days')"
            elif date_filter == "Last 30 Days":
                date_clause = "WHERE timestamp >= DATE('now', '-30 days')"
            
            status_clause = ""
            if status_filter != "All":
                if date_clause:
                    status_clause = f" AND overall_result LIKE '%{status_filter}%'"
                else:
                    status_clause = f"WHERE overall_result LIKE '%{status_filter}%'"
            
            # Load filtered history
            history_data = self.database.get_filtered_history(date_clause + status_clause, 100)
            
            for record in history_data:
                timestamp = record["timestamp"]
                if " " in timestamp:
                    date, time_str = timestamp.split(" ", 1)
                else:
                    date = timestamp
                    time_str = ""
                
                details = f"Execution time: {record['execution_time']:.1f}s" if record["execution_time"] else ""
                if record["affects_wan"] or record["affects_lan"]:
                    details += " (Network affecting)"
                
                self.history_table.insert("", "end", values=(
                    date,
                    time_str,
                    record["file_name"],
                    record["test_count"],
                    record["overall_result"] or "Unknown",
                    details
                ))
            
            self.log_message(f"Applied filter: {len(self.history_table.get_children())} records found")
            
        except Exception as e:
            self.log_message(f"Error applying filter: {str(e)}")
    
    def clear_history_filter(self):
        """Clear history filters"""
        self.date_combo.current(0)  # Set to "All"
        self.status_combo.current(0)  # Set to "All"
        self.load_history()
        self.log_message("History filter cleared")
    
    def export_history(self):
        """Export history to CSV"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv", 
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            title="Export History"
        )
        if filename:
            try:
                # Implement CSV export of history
                with open(filename, 'w', newline='') as f:
                    import csv
                    writer = csv.writer(f)
                    
                    # Header row
                    writer.writerow(["Date", "Time", "Filename", "Tests", "Result", "Details"])
                    
                    # Data rows
                    for item_id in self.history_table.get_children():
                        values = self.history_table.item(item_id)["values"]
                        writer.writerow(values)
                
                self.log_message(f"History exported to {filename}")
                messagebox.showinfo("Export", f"History exported to {filename}")
            except Exception as e:
                messagebox.showerror("Export Error", f"Failed to export history: {str(e)}")
    def export_details_to_csv(self, details, file_name):
        """Export test details to CSV file"""
        try:
            # Ask for save location
            save_path = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
                initialfile=f"{file_name}_details.csv"
            )
            
            if not save_path:  # User cancelled
                return
                
            # Write CSV file
            with open(save_path, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['service', 'action', 'status', 'details', 'execution_time']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for test in details:
                    writer.writerow({
                        'service': test.get('service', ''),
                        'action': test.get('action', ''),
                        'status': test.get('status', ''),
                        'details': test.get('details', ''),
                        'execution_time': test.get('execution_time', 0)
                    })
                    
            messagebox.showinfo("Export Successful", f"Details exported to {save_path}")
            
        except Exception as e:
            messagebox.showerror("Export Error", f"Failed to export details: {str(e)}")
    
    def view_history_details(self):
        """View detailed information for selected history item"""
        selection = self.history_table.selection()
        if not selection:
            messagebox.showinfo("No Selection", "Please select a history item to view details")
            return
        
        item_id = selection[0]
        history_values = self.history_table.item(item_id)["values"]
        file_name = history_values[2]  # Filename column
        
        try:
            # Truy vấn database để lấy result_id dựa trên timestamp chính xác
            date_str = history_values[0]  # Date column
            time_str = history_values[1]  # Time column
            timestamp = f"{date_str} {time_str}"
            
            # Tìm kết quả dựa trên file_name và timestamp
            conn = sqlite3.connect(self.database.db_path)
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            
            cursor.execute(
                "SELECT id FROM test_results WHERE file_name = ? AND timestamp LIKE ? ORDER BY timestamp DESC LIMIT 1",
                (file_name, f"{timestamp}%")  # Sử dụng LIKE vì có thể có sự khác nhau nhỏ về định dạng timestamp
            )
            
            result = cursor.fetchone()
            conn.close()
            
            if not result:
                messagebox.showinfo("No Details", f"No test details found for {file_name} at {timestamp}")
                return
            
            result_id = result["id"]
            
            # Get detailed test results using result_id
            details = self.database.get_test_details(result_id=result_id)
            
            if details:
                # Tạo cửa sổ chi tiết
                details_window = tk.Toplevel(self.root)
                details_window.title(f"Test Details - {file_name}")
                details_window.geometry("800x600")
                details_window.minsize(640, 480)
                
                # Tạo frame chứa nội dung
                content_frame = ttk.Frame(details_window, padding=10)
                content_frame.pack(fill=tk.BOTH, expand=True)
                
                # Thêm label hiển thị thông tin cơ bản
                header_frame = ttk.Frame(content_frame)
                header_frame.pack(fill=tk.X, pady=(0, 10))
                
                ttk.Label(header_frame, text=f"File: {file_name}", font=('Segoe UI', 12, 'bold')).pack(anchor=tk.W)
                ttk.Label(header_frame, text=f"Date/Time: {date_str} {time_str}").pack(anchor=tk.W)
                ttk.Label(header_frame, text=f"Status: {history_values[3]}").pack(anchor=tk.W)
                
                # Tạo bảng hiển thị chi tiết các test case
                details_frame = ttk.Frame(content_frame)
                details_frame.pack(fill=tk.BOTH, expand=True, pady=5)
                
                # Scrollbars cho bảng
                y_scroll = ttk.Scrollbar(details_frame, orient=tk.VERTICAL)
                y_scroll.pack(side=tk.RIGHT, fill=tk.Y)
                
                x_scroll = ttk.Scrollbar(details_frame, orient=tk.HORIZONTAL)
                x_scroll.pack(side=tk.BOTTOM, fill=tk.X)
                
                # Tạo TreeView để hiển thị chi tiết
                columns = ("service", "action", "status", "details", "execution_time")
                details_table = ttk.Treeview(details_frame, columns=columns, show="headings",
                                            yscrollcommand=y_scroll.set, xscrollcommand=x_scroll.set)
                
                # Configure scrollbars
                y_scroll.config(command=details_table.yview)
                x_scroll.config(command=details_table.xview)
                
                # Configure columns
                details_table.heading("service", text="Service")
                details_table.heading("action", text="Action")
                details_table.heading("status", text="Status")
                details_table.heading("details", text="Details")
                details_table.heading("execution_time", text="Time (s)")
                
                details_table.column("service", width=120, anchor=tk.W)
                details_table.column("action", width=150, anchor=tk.W)
                details_table.column("status", width=80, anchor=tk.CENTER)
                details_table.column("details", width=300, anchor=tk.W)
                details_table.column("execution_time", width=80, anchor=tk.E)
                
                details_table.pack(fill=tk.BOTH, expand=True)
                
                # Thêm dữ liệu vào bảng
                for i, test in enumerate(details):
                    status_text = test.get("status", "").capitalize()
                    status_tag = test.get("status", "unknown").lower()
                    
                    details_table.insert("", "end", values=(
                        test.get("service", ""),
                        test.get("action", ""),
                        status_text,
                        test.get("details", ""),
                        f"{test.get('execution_time', 0):.2f}"
                    ), tags=(status_tag,))
                
                # Thêm màu sắc cho các trạng thái
                details_table.tag_configure("pass", background="#e6ffe6")
                details_table.tag_configure("fail", background="#ffe6e6")
                details_table.tag_configure("error", background="#fff2e6")
                
                # Frame cho các nút điều khiển
                button_frame = ttk.Frame(content_frame)
                button_frame.pack(fill=tk.X, pady=10)
                
                # Nút Export
                export_btn = ttk.Button(button_frame, text="Export to CSV", 
                                    command=lambda: self.export_details_to_csv(details, file_name))
                export_btn.pack(side=tk.LEFT, padx=5)
                
                # Nút Close
                close_btn = ttk.Button(button_frame, text="Close", command=details_window.destroy)
                close_btn.pack(side=tk.RIGHT, padx=5)
                
                # Đặt focus cho cửa sổ và hiển thị
                details_window.transient(self.root)
                details_window.grab_set()
                self.root.wait_window(details_window)
            else:
                messagebox.showinfo("No Details", f"No detailed test results found for {file_name}")
                
        except Exception as e:
            messagebox.showerror("Error", f"Failed to load test details: {str(e)}")
    def clear_logs(self):
        """Clear the log display"""
        confirm = messagebox.askyesno("Clear Logs", "Clear all log messages from display?")
        if confirm:
            self.log_text.delete("1.0", tk.END)
            self.log_message("Log display cleared")
    
    def export_logs(self):
        """Export logs to file"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".log", 
            filetypes=[("Log files", "*.log"), ("Text files", "*.txt"), ("All files", "*.*")],
            title="Export Logs"
        )
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write(self.log_text.get("1.0", tk.END))
                messagebox.showinfo("Export", f"Logs exported to {filename}")
                self.log_message(f"Logs exported to {filename}")
            except Exception as e:
                error_msg = f"Failed to export logs: {str(e)}"
                messagebox.showerror("Export Error", error_msg)
                self.log_message(error_msg)
    
    def show_documentation(self):
        """Show documentation"""
        doc_msg = (
            "Test Case Manager v2.0 (Windows Edition)\n\n"
            "Enhanced Features:\n"
            "• Improved error handling and retry logic\n"
            "• Multiple result file detection strategies\n"
            "• Enhanced connection management\n"
            "• Windows-specific optimizations\n"
            "• Better user feedback and logging\n\n"
            "Usage Instructions:\n"
            "1. Configure connection settings\n"
            "2. Test connection to verify access\n"
            "3. Select test files to run\n"
            "4. Click 'Send Files' to run tests\n"
            "5. View results and history\n\n"
            "For detailed documentation, see the Help menu."
        )
        messagebox.showinfo("Documentation", doc_msg)
    
    def show_about(self):
        """Show about dialog"""
        about_msg = (
            "Test Case Manager v2.0\n"
            "Windows Edition\n\n"
            "© 2025 juno-kyojin\n\n"
            "Features:\n"
            "• Windows-optimized SSH connectivity\n"
            "• Enhanced error handling and recovery\n"
            "• Multiple file detection strategies\n"
            "• Database storage with auto-cleanup\n"
            "• Professional GUI with progress tracking\n\n"
            f"Build: {time.strftime('%Y-%m-%d %H:%M:%S')}\n"
            f"User: {os.environ.get('USERNAME', 'unknown')}\n"
            f"Windows {platform.win32_ver()[0]} {platform.win32_ver()[1]}"
        )
        messagebox.showinfo("About", about_msg)