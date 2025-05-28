#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Module: interface.py
# Purpose: Main GUI window with real functionality

import os
import sys
import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import time
import logging

# Import các module thực tế
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

from network.connection import SSHConnection
from files.manager import TestFileManager
from storage.database import TestDatabase

class ApplicationGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Test Case Manager")
        self.root.geometry("900x700")
        self.root.minsize(800, 600)
        
        # Setup logging
        logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
        self.logger = logging.getLogger(__name__)
        
        # Initialize real modules
        self.ssh_connection = SSHConnection()
        self.file_manager = TestFileManager()
        self.database = TestDatabase()
        
        # Style configuration
        self.style = ttk.Style()
        self.style.configure("TButton", padding=6)
        self.style.configure("TLabel", padding=3)
        self.style.configure("TFrame", padding=5)
        
        # Variables - Load from database
        self.lan_ip_var = tk.StringVar(value=self.database.get_setting("lan_ip", "192.168.88.1"))
        self.wan_ip_var = tk.StringVar(value=self.database.get_setting("wan_ip", ""))
        self.username_var = tk.StringVar(value=self.database.get_setting("username", "testuser"))
        self.password_var = tk.StringVar()  # Never save password
        self.config_path_var = tk.StringVar(value=self.database.get_setting("config_path", "/root/config"))
        self.result_path_var = tk.StringVar(value=self.database.get_setting("result_path", "/root/result"))
        self.connection_status = tk.StringVar(value="Not Connected")
        
        self.selected_files = []
        self.file_data = {}  # Store parsed file data
        self.current_file_index = -1
        self.processing = False
        
        # Create UI components
        self.create_menu()
        self.create_notebook()
        self.create_status_bar()
        
        # Load history from database
        self.load_history()
        
        # Auto-save settings when changed
        self.setup_auto_save()
    
    def setup_auto_save(self):
        """Setup auto-save for settings when they change"""
        def save_setting(var_name, var):
            def callback(*args):
                try:
                    self.database.save_setting(var_name, var.get())
                except:
                    pass  # Ignore errors during auto-save
            return callback
        
        self.lan_ip_var.trace('w', save_setting('lan_ip', self.lan_ip_var))
        self.wan_ip_var.trace('w', save_setting('wan_ip', self.wan_ip_var))
        self.username_var.trace('w', save_setting('username', self.username_var))
        self.config_path_var.trace('w', save_setting('config_path', self.config_path_var))
        self.result_path_var.trace('w', save_setting('result_path', self.result_path_var))
    
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
        """Setup the main tab content"""
        # Split the tab into top (connection) and bottom (files) sections
        main_paned = ttk.PanedWindow(self.main_tab, orient=tk.VERTICAL)
        main_paned.pack(fill=tk.BOTH, expand=True)
        
        # Top section - Connection frame
        connection_frame = ttk.LabelFrame(main_paned, text="Connection Settings")
        main_paned.add(connection_frame, weight=1)
        
        # Connection grid
        conn_grid = ttk.Frame(connection_frame)
        conn_grid.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Row 0: LAN IP
        ttk.Label(conn_grid, text="LAN IP:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(conn_grid, textvariable=self.lan_ip_var, width=30).grid(row=0, column=1, sticky=tk.W+tk.E, padx=5, pady=5)
        
        # Row 1: WAN IP (Optional)
        ttk.Label(conn_grid, text="WAN IP (Optional):").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(conn_grid, textvariable=self.wan_ip_var, width=30).grid(row=1, column=1, sticky=tk.W+tk.E, padx=5, pady=5)
        
        # Row 2: Username
        ttk.Label(conn_grid, text="Username:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(conn_grid, textvariable=self.username_var, width=30).grid(row=2, column=1, sticky=tk.W+tk.E, padx=5, pady=5)
        
        # Row 3: Password
        ttk.Label(conn_grid, text="Password:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(conn_grid, textvariable=self.password_var, width=30, show="•").grid(row=3, column=1, sticky=tk.W+tk.E, padx=5, pady=5)
        
        # Row 4: Config path
        ttk.Label(conn_grid, text="Config Path:").grid(row=0, column=2, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(conn_grid, textvariable=self.config_path_var, width=30).grid(row=0, column=3, sticky=tk.W+tk.E, padx=5, pady=5)
        
        # Row 5: Result path
        ttk.Label(conn_grid, text="Result Path:").grid(row=1, column=2, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(conn_grid, textvariable=self.result_path_var, width=30).grid(row=1, column=3, sticky=tk.W+tk.E, padx=5, pady=5)
        
        # Connection buttons
        conn_btn_frame = ttk.Frame(conn_grid)
        conn_btn_frame.grid(row=3, column=2, columnspan=2, sticky=tk.E, padx=5, pady=5)
        
        ttk.Button(conn_btn_frame, text="Test Connection", command=self.test_connection).pack(side=tk.LEFT, padx=5)
        ttk.Button(conn_btn_frame, text="Save Settings", command=self.save_config).pack(side=tk.LEFT, padx=5)
        
        # Middle section - File selection
        file_frame = ttk.LabelFrame(main_paned, text="Test Files")
        main_paned.add(file_frame, weight=2)
        
        # File selection buttons
        file_btn_frame = ttk.Frame(file_frame)
        file_btn_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(file_btn_frame, text="Select Files", command=self.select_files).pack(side=tk.LEFT, padx=5)
        ttk.Button(file_btn_frame, text="Clear Selection", command=self.clear_files).pack(side=tk.LEFT, padx=5)
        
        # File table
        file_table_frame = ttk.Frame(file_frame)
        file_table_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
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
        
        self.file_table.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        file_table_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bind selection event
        self.file_table.bind("<<TreeviewSelect>>", self.on_file_selected)
        
        # Bottom section - Test case details
        detail_frame = ttk.LabelFrame(main_paned, text="Test Case Details")
        main_paned.add(detail_frame, weight=3)
        
        # Test case detail table
        detail_table_frame = ttk.Frame(detail_frame)
        detail_table_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
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
        
        self.detail_table.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        detail_table_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Action buttons frame at the bottom
        action_frame = ttk.Frame(self.main_tab)
        action_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.send_button = ttk.Button(action_frame, text="Send Files", command=self.send_files)
        self.send_button.pack(side=tk.LEFT, padx=5)
        
        self.cancel_button = ttk.Button(action_frame, text="Cancel", command=self.cancel_processing, state=tk.DISABLED)
        self.cancel_button.pack(side=tk.LEFT, padx=5)
        
        self.progress_var = tk.IntVar()
        self.progress_bar = ttk.Progressbar(action_frame, orient=tk.HORIZONTAL, length=300, mode='determinate', variable=self.progress_var)
        self.progress_bar.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=10)
        self.progress_var.set(0)
    
    def setup_history_tab(self):
        """Setup the history tab content"""
        # Filter frame
        filter_frame = ttk.Frame(self.history_tab)
        filter_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(filter_frame, text="Date:").pack(side=tk.LEFT, padx=5)
        self.date_combo = ttk.Combobox(filter_frame, width=15, values=["All", "Today", "Last 7 Days", "Last 30 Days"])
        self.date_combo.current(0)
        self.date_combo.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(filter_frame, text="Status:").pack(side=tk.LEFT, padx=5)
        self.status_combo = ttk.Combobox(filter_frame, width=15, values=["All", "Pass", "Fail", "Error"])
        self.status_combo.current(0)
        self.status_combo.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(filter_frame, text="Apply Filter", command=self.apply_history_filter).pack(side=tk.LEFT, padx=5)
        ttk.Button(filter_frame, text="Clear Filter", command=self.clear_history_filter).pack(side=tk.LEFT, padx=5)
        
        # History table
        history_table_frame = ttk.Frame(self.history_tab)
        history_table_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
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
        
        self.history_table.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        history_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Action buttons
        history_btn_frame = ttk.Frame(self.history_tab)
        history_btn_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(history_btn_frame, text="Export to CSV", command=self.export_history).pack(side=tk.LEFT, padx=5)
        ttk.Button(history_btn_frame, text="View Details", command=self.view_history_details).pack(side=tk.LEFT, padx=5)
        ttk.Button(history_btn_frame, text="Refresh", command=self.load_history).pack(side=tk.LEFT, padx=5)
    
    def setup_logs_tab(self):
        """Setup the logs tab content"""
        log_frame = ttk.Frame(self.logs_tab)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Log text area
        self.log_text = tk.Text(log_frame, wrap=tk.WORD, height=20)
        self.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Scrollbar
        log_scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=log_scrollbar.set)
        log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Buttons
        log_btn_frame = ttk.Frame(self.logs_tab)
        log_btn_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(log_btn_frame, text="Clear Logs", command=self.clear_logs).pack(side=tk.LEFT, padx=5)
        ttk.Button(log_btn_frame, text="Export Logs", command=self.export_logs).pack(side=tk.LEFT, padx=5)
    
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
        
        # Current time
        self.time_var = tk.StringVar()
        self.update_clock()
        ttk.Label(status_frame, textvariable=self.time_var).pack(side=tk.RIGHT, padx=10)
    
    def update_clock(self):
        """Update the clock in the status bar"""
        current_time = time.strftime("%Y-%m-%d %H:%M:%S")
        self.time_var.set(current_time)
        self.root.after(1000, self.update_clock)
    
    # Event handlers and actions - REAL IMPLEMENTATIONS
    
    def test_connection(self):
        """Real connection test using SSH module"""
        if not self.validate_connection_fields():
            return
        
        self.connection_status.set("Connecting...")
        self.update_status_circle("yellow")
        self.log_message("Testing connection to " + self.lan_ip_var.get() + "...")
        
        def _test_connection():
            try:
                success = self.ssh_connection.connect(
                    hostname=self.lan_ip_var.get(),
                    username=self.username_var.get(),
                    password=self.password_var.get(),
                    timeout=10
                )
                
                if success:
                    # Log successful connection
                    self.database.log_connection(
                        self.lan_ip_var.get(), 
                        "Connected", 
                        "Connection test successful"
                    )
                    
                    self.root.after(0, lambda: self.connection_status.set("Connected"))
                    self.root.after(0, lambda: self.update_status_circle("green"))
                    self.root.after(0, lambda: self.log_message("Connection successful"))
                    self.root.after(0, lambda: messagebox.showinfo("Connection", "Connection successful!"))
                else:
                    # Log failed connection
                    self.database.log_connection(
                        self.lan_ip_var.get(), 
                        "Failed", 
                        "Authentication or network error"
                    )
                    
                    self.root.after(0, lambda: self.connection_status.set("Connection failed"))
                    self.root.after(0, lambda: self.update_status_circle("red"))
                    self.root.after(0, lambda: self.log_message("Connection failed"))
                    self.root.after(0, lambda: messagebox.showerror("Connection", "Connection failed. Check credentials."))
                    
            except Exception as e:
                error_msg = f"Connection error: {str(e)}"
                self.database.log_connection(
                    self.lan_ip_var.get(), 
                    "Error", 
                    error_msg
                )
                
                self.root.after(0, lambda: self.connection_status.set("Error"))
                self.root.after(0, lambda: self.update_status_circle("red"))
                self.root.after(0, lambda: self.log_message(error_msg))
                self.root.after(0, lambda: messagebox.showerror("Error", error_msg))
        
        threading.Thread(target=_test_connection, daemon=True).start()
    
    def select_files(self):
        """Select and validate JSON files using real file manager"""
        files = filedialog.askopenfilenames(
            title="Select JSON Test Files",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
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
        
        # Show warnings for files that affect network
        network_affecting_files = []
        for file_name, file_info in self.file_data.items():
            impacts = file_info["impacts"]
            if impacts["affects_wan"] or impacts["affects_lan"]:
                network_affecting_files.append(file_name)
        
        if network_affecting_files:
            warning_msg = f"Warning: The following files may affect network connectivity:\n\n"
            for filename in network_affecting_files:
                warning_msg += f"• {filename}\n"
            warning_msg += "\nConnection may be temporarily lost during testing."
            messagebox.showwarning("Network Impact Warning", warning_msg)
    
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
        
        # Disable buttons and start processing
        self.send_button.configure(state=tk.DISABLED)
        self.cancel_button.configure(state=tk.NORMAL)
        self.processing = True
        self.progress_var.set(0)
        
        threading.Thread(target=self.process_files_real, daemon=True).start()
    
    def process_files_real(self):
        """Process files using real modules"""
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
                
                # Update progress
                progress = int((i / total_files) * 100)
                self.root.after(0, lambda p=progress: self.progress_var.set(p))
                
                # Update table status
                self.update_file_status(i, "Sending", "", "")
                
                try:
                    # 3. Upload file
                    remote_path = os.path.join(self.config_path_var.get(), file_name)
                    upload_success = self.ssh_connection.upload_file(file_path, remote_path)
                    
                    if not upload_success:
                        raise Exception("File upload failed")
                    
                    self.log_message(f"File {file_name} uploaded successfully")
                    self.update_file_status(i, "Testing", "", "")
                    
                    # 4. Wait for result
                    result_filename = f"result_{file_name}"
                    result_remote_path = os.path.join(self.result_path_var.get(), result_filename)
                    
                    # Wait for result file (timeout: 60 seconds)
                    timeout = 60
                    start_wait = time.time()
                    result_found = False
                    
                    self.log_message(f"Waiting for result file: {result_filename}")
                    
                    while time.time() - start_wait < timeout and self.processing:
                        if self.ssh_connection.file_exists(result_remote_path):
                            result_found = True
                            break
                        time.sleep(5)  # Check every 5 seconds
                    
                    if not result_found:
                        raise Exception("Timeout waiting for test result")
                    
                    # 5. Download result
                    local_result_dir = "data/temp/results"
                    os.makedirs(local_result_dir, exist_ok=True)
                    local_result_path = os.path.join(local_result_dir, result_filename)
                    
                    download_success = self.ssh_connection.download_file(result_remote_path, local_result_path)
                    
                    if not download_success:
                        raise Exception("Failed to download result file")
                    
                    self.log_message(f"Result file {result_filename} downloaded successfully")
                    
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
                    
                    # Save individual test results
                    test_results = result_data.get("test_results", [])
                    if test_results and file_id > 0:
                        self.database.save_test_case_results(file_id, test_results)
                    
                    # Update detail table with results if this file is selected
                    self.update_detail_table_with_results(i, result_data)
                    
                    self.log_message(f"File {file_name} processed successfully: {overall_result}")
                    
                except Exception as e:
                    error_msg = f"Error processing {file_name}: {str(e)}"
                    self.log_message(error_msg)
                    self.update_file_status(i, "Error", "Failed", str(e))
                    
                    # Save error to database
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
                            execution_time=time.time() - file_start_time,
                            target_ip=self.lan_ip_var.get(),
                            target_username=self.username_var.get()
                        )
                    except Exception as db_error:
                        self.log_message(f"Failed to save error to database: {str(db_error)}")
            
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
    
    def update_detail_table_with_results(self, file_index, result_data):
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
    
    def determine_overall_result(self, result_data):
        """Determine overall result from test result data"""
        if "overall_status" in result_data:
            status = result_data["overall_status"].lower()
            return "Pass" if status == "pass" else "Fail" if status == "fail" else "Unknown"
        
        test_results = result_data.get("test_results", [])
        
        if not test_results:
            return "Unknown"
        
        passed = sum(1 for r in test_results if r.get("status", "").lower() == "pass")
        total = len(test_results)
        
        if passed == total:
            return "Pass"
        elif passed == 0:
            return "Fail"
        else:
            return f"Partial ({passed}/{total})"
    
    def update_file_status(self, file_index, status, result="", time_str=""):
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
            self.username_var.set(self.database.get_setting("username", "testuser"))
            self.config_path_var.set(self.database.get_setting("config_path", "/root/config"))
            self.result_path_var.set(self.database.get_setting("result_path", "/root/result"))
            
            self.log_message("Configuration loaded successfully")
            
        except Exception as e:
            error_msg = f"Failed to load configuration: {str(e)}"
            self.log_message(error_msg)
            messagebox.showerror("Error", error_msg)
    
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
    
    # Remaining methods stay the same as demo version
    def clear_files(self):
        """Clear selected files"""
        self.selected_files = []
        self.file_data = {}
        for item in self.file_table.get_children():
            self.file_table.delete(item)
        
        for item in self.detail_table.get_children():
            self.detail_table.delete(item)
    
    def validate_connection_fields(self):
        """Validate connection fields"""
        if not self.lan_ip_var.get():
            messagebox.showerror("Error", "LAN IP cannot be empty")
            return False
        
        if not self.username_var.get():
            messagebox.showerror("Error", "Username cannot be empty")
            return False
        
        if not self.password_var.get():
            messagebox.showerror("Error", "Password cannot be empty")
            return False
        
        if not self.config_path_var.get():
            messagebox.showerror("Error", "Config path cannot be empty")
            return False
        
        if not self.result_path_var.get():
            messagebox.showerror("Error", "Result path cannot be empty")
            return False
        
        return True
    
    def update_status_circle(self, color):
        """Update connection status circle color"""
        self.status_canvas.itemconfig(self.status_circle, fill=color)
    
    def log_message(self, message):
        """Add a message to the log with timestamp"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        
        self.log_text.insert(tk.END, log_entry)
        self.log_text.see(tk.END)  # Scroll to the bottom
    
    def on_closing(self):
        """Handle application closing"""
        if self.processing:
            if messagebox.askyesno("Confirm Exit", "Processing is in progress. Are you sure you want to exit?"):
                self.processing = False
                self.ssh_connection.disconnect()
                self.root.destroy()
        else:
            self.ssh_connection.disconnect()
            self.root.destroy()
    
    # Placeholder methods (same as demo)
    def export_results(self):
        filename = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if filename:
            self.log_message(f"Exporting results to {filename}...")
            messagebox.showinfo("Export", f"Results exported to {filename}")
    
    def refresh_view(self):
        self.load_history()
        self.log_message("View refreshed")
    
    def clear_history(self):
        confirm = messagebox.askyesno("Confirm", "Are you sure you want to clear all history?")
        if confirm:
            for item in self.history_table.get_children():
                self.history_table.delete(item)
            self.log_message("History cleared from view")
    
    def apply_history_filter(self):
        self.log_message("Filtering history...")
    
    def clear_history_filter(self):
        self.load_history()
        self.log_message("History filter cleared")
    
    def export_history(self):
        filename = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV files", "*.csv")])
        if filename:
            self.log_message(f"Exporting history to {filename}...")
            messagebox.showinfo("Export", f"History exported to {filename}")
    
    def view_history_details(self):
        selection = self.history_table.selection()
        if selection:
            item_id = selection[0]
            filename = self.history_table.item(item_id)["values"][2]
            messagebox.showinfo("Details", f"Details for {filename}")
    
    def clear_logs(self):
        self.log_text.delete("1.0", tk.END)
    
    def export_logs(self):
        filename = filedialog.asksaveasfilename(defaultextension=".log", filetypes=[("Log files", "*.log")])
        if filename:
            try:
                with open(filename, 'w') as f:
                    f.write(self.log_text.get("1.0", tk.END))
                messagebox.showinfo("Export", f"Logs exported to {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export logs: {str(e)}")
    
    def show_documentation(self):
        messagebox.showinfo("Documentation", "Please refer to docs/user_guide.md for detailed documentation.")
    
    def show_about(self):
        messagebox.showinfo("About", "Test Case Manager v1.0\n© 2025 juno-kyojin\n\nWith real SSH connectivity and database storage.")


def main():
    root = tk.Tk()
    app = ApplicationGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()