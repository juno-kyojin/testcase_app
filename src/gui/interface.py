#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Module: interface.py
# Purpose: Main GUI window for the application

import os
import sys
import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import time
import random  # For demo only, remove in production

class ApplicationGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Test Case Manager")
        self.root.geometry("900x700")
        self.root.minsize(800, 600)
        
        # Style configuration
        self.style = ttk.Style()
        self.style.configure("TButton", padding=6)
        self.style.configure("TLabel", padding=3)
        self.style.configure("TFrame", padding=5)
        
        # Variables
        self.lan_ip_var = tk.StringVar(value="192.168.88.1")
        self.wan_ip_var = tk.StringVar()
        self.username_var = tk.StringVar(value="testuser")
        self.password_var = tk.StringVar()
        self.config_path_var = tk.StringVar(value="/root/config")
        self.result_path_var = tk.StringVar(value="/root/result")
        self.connection_status = tk.StringVar(value="Not Connected")
        self.selected_files = []
        self.current_file_index = -1
        self.processing = False
        
        # Create UI components
        self.create_menu()
        self.create_notebook()
        self.create_status_bar()
        
        # Load demo data for preview (remove in production)
        self.load_demo_data()
    
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
        file_menu.add_command(label="Exit", command=self.root.quit)
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
        date_combo = ttk.Combobox(filter_frame, width=15, values=["All", "Today", "Last 7 Days", "Last 30 Days"])
        date_combo.current(0)
        date_combo.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(filter_frame, text="Status:").pack(side=tk.LEFT, padx=5)
        status_combo = ttk.Combobox(filter_frame, width=15, values=["All", "Pass", "Fail", "Error"])
        status_combo.current(0)
        status_combo.pack(side=tk.LEFT, padx=5)
        
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
    
    # Event handlers and actions
    
    def load_config(self):
        """Load configuration from file"""
        self.log_message("Loading configuration...")
        messagebox.showinfo("Info", "Configuration loaded")
    
    def save_config(self):
        """Save configuration to file"""
        self.log_message("Saving configuration...")
        messagebox.showinfo("Info", "Configuration saved successfully")
    
    def export_results(self):
        """Export test results to a file"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if filename:
            self.log_message(f"Exporting results to {filename}...")
            messagebox.showinfo("Export", f"Results exported to {filename}")
    
    def refresh_view(self):
        """Refresh the current view"""
        self.log_message("Refreshing view...")
    
    def clear_history(self):
        """Clear history data"""
        confirm = messagebox.askyesno("Confirm", "Are you sure you want to clear all history?")
        if confirm:
            for item in self.history_table.get_children():
                self.history_table.delete(item)
            self.log_message("History cleared")
    
    def test_connection(self):
        """Test connection to the remote server"""
        self.log_message("Testing connection to " + self.lan_ip_var.get() + "...")
        
        # Validate connection fields
        if not self.validate_connection_fields():
            return
        
        # Update status
        self.connection_status.set("Connecting...")
        self.update_status_circle("yellow")
        
        def _test_connection():
            # Simulate connection (in production, use actual SSH connection)
            time.sleep(2)
            
            # For demo: 80% chance of success
            success = random.random() > 0.2
            
            if success:
                self.root.after(0, lambda: self.connection_status.set("Connected"))
                self.root.after(0, lambda: self.update_status_circle("green"))
                self.root.after(0, lambda: self.log_message("Connection successful"))
                self.root.after(0, lambda: messagebox.showinfo("Connection", "Connection successful!"))
            else:
                self.root.after(0, lambda: self.connection_status.set("Connection failed"))
                self.root.after(0, lambda: self.update_status_circle("red"))
                self.root.after(0, lambda: self.log_message("Connection failed: Authentication error"))
                self.root.after(0, lambda: messagebox.showerror("Connection", "Connection failed. Check credentials."))
        
        # Run in a separate thread to avoid freezing the UI
        threading.Thread(target=_test_connection, daemon=True).start()
    
    def check_remote_folders(self):
        """Check if remote folders exist and are accessible"""
        self.log_message("Checking remote folders...")
        
        if not self.validate_connection_fields():
            return
        
        # For demo, just show success
        messagebox.showinfo("Folders", f"Folders exist and are accessible:\n{self.config_path_var.get()}\n{self.result_path_var.get()}")
    
    def show_documentation(self):
        """Show application documentation"""
        messagebox.showinfo("Documentation", "Please refer to docs/user_guide.md for detailed documentation.")
    
    def show_about(self):
        """Show about dialog"""
        messagebox.showinfo("About", "Test Case Manager v1.0\n© 2025 juno-kyojin")
    
    def select_files(self):
        """Open file dialog to select JSON test files"""
        files = filedialog.askopenfilenames(
            title="Select JSON Test Files",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if not files:
            return
        
        # Clear existing selection
        self.clear_files()
        
        # Store selected files
        self.selected_files = list(files)
        
        # Parse and add files to the table
        for file_path in self.selected_files:
            try:
                # In production, use file_manager to parse the file
                # For now, simulate parsing
                file_name = os.path.basename(file_path)
                file_size = os.path.getsize(file_path)
                size_str = f"{file_size / 1024:.1f} KB" if file_size < 1024*1024 else f"{file_size / (1024*1024):.1f} MB"
                
                # Try to load the file to count tests
                try:
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                    test_count = len(data.get("test_cases", []))
                except:
                    test_count = "?"
                
                # Add to table
                self.file_table.insert("", "end", values=(file_name, size_str, test_count, "Waiting", "", ""))
                
            except Exception as e:
                self.log_message(f"Error loading file {file_path}: {str(e)}")
        
        self.log_message(f"Selected {len(self.selected_files)} files")
    
    def clear_files(self):
        """Clear selected files"""
        self.selected_files = []
        for item in self.file_table.get_children():
            self.file_table.delete(item)
        
        for item in self.detail_table.get_children():
            self.detail_table.delete(item)
    
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
        
        # Clear detail table
        for item in self.detail_table.get_children():
            self.detail_table.delete(item)
        
        # Load file and populate detail table
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            test_cases = data.get("test_cases", [])
            
            for i, test_case in enumerate(test_cases):
                service = test_case.get("service", "")
                action = test_case.get("action", "-")
                
                # Format parameters as a compact string
                params = test_case.get("params", {})
                params_str = self.format_params(params)
                
                # For demo, status and details are empty
                status = "-"
                details = "-"
                
                self.detail_table.insert("", "end", values=(service, action, params_str, status, details))
            
        except Exception as e:
            self.log_message(f"Error loading test details: {str(e)}")
    
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
    
    def send_files(self):
        """Send selected files to the remote server"""
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
        
        # Disable buttons and update UI
        self.send_button.configure(state=tk.DISABLED)
        self.cancel_button.configure(state=tk.NORMAL)
        self.processing = True
        self.current_file_index = 0
        self.progress_var.set(0)
        
        # Start processing thread
        threading.Thread(target=self.process_files, daemon=True).start()
    
    def cancel_processing(self):
        """Cancel the file processing"""
        if self.processing:
            self.processing = False
            self.log_message("Processing cancelled by user")
            self.send_button.configure(state=tk.NORMAL)
            self.cancel_button.configure(state=tk.DISABLED)
    
    def process_files(self):
        """Process files sequentially"""
        # Test connection first
        self.log_message("Testing connection...")
        self.root.after(0, lambda: self.connection_status.set("Connecting..."))
        self.root.after(0, lambda: self.update_status_circle("yellow"))
        
        # Simulate connection
        time.sleep(1)
        
        # For demo, assume connection succeeds
        self.root.after(0, lambda: self.connection_status.set("Connected"))
        self.root.after(0, lambda: self.update_status_circle("green"))
        
        # Process each file
        total_files = len(self.selected_files)
        
        for i, file_path in enumerate(self.selected_files):
            if not self.processing:
                break
                
            file_name = os.path.basename(file_path)
            self.log_message(f"Processing file {i+1}/{total_files}: {file_name}")
            
            # Update progress bar
            progress = int((i / total_files) * 100)
            self.root.after(0, lambda p=progress: self.progress_var.set(p))
            
            # Update file status in the table
            for item_id in self.file_table.get_children():
                if self.file_table.index(item_id) == i:
                    self.root.after(0, lambda id=item_id: self.file_table.item(
                        id, values=(
                            self.file_table.item(id)["values"][0],  # filename
                            self.file_table.item(id)["values"][1],  # size
                            self.file_table.item(id)["values"][2],  # tests
                            "Sending",  # status
                            "",  # result
                            ""   # time
                        )
                    ))
            
            # 1. Simulate sending file (1-2 seconds)
            time.sleep(1 + random.random())
            
            if not self.processing:
                break
            
            # Update status to "Testing"
            for item_id in self.file_table.get_children():
                if self.file_table.index(item_id) == i:
                    self.root.after(0, lambda id=item_id: self.file_table.item(
                        id, values=(
                            self.file_table.item(id)["values"][0],  # filename
                            self.file_table.item(id)["values"][1],  # size
                            self.file_table.item(id)["values"][2],  # tests
                            "Testing",  # status
                            "",  # result
                            ""   # time
                        )
                    ))
            
            # 2. Simulate test execution (3-5 seconds)
            time.sleep(3 + 2 * random.random())
            
            if not self.processing:
                break
            
            # 3. Simulate result retrieval
            # For demo, randomly generate result
            result = "Pass" if random.random() > 0.3 else "Fail"
            elapsed = f"{4 + random.random():.1f}s"
            
            # Update file status in the table with result
            for item_id in self.file_table.get_children():
                if self.file_table.index(item_id) == i:
                    self.root.after(0, lambda id=item_id, res=result, tm=elapsed: self.file_table.item(
                        id, values=(
                            self.file_table.item(id)["values"][0],  # filename
                            self.file_table.item(id)["values"][1],  # size
                            self.file_table.item(id)["values"][2],  # tests
                            "Completed",  # status
                            res,  # result
                            tm    # time
                        )
                    ))
            
            # 4. Update detail table with results if this file is selected
            selection = self.file_table.selection()
            if selection and self.file_table.index(selection[0]) == i:
                try:
                    with open(file_path, 'r') as f:
                        data = json.load(f)
                    
                    test_cases = data.get("test_cases", [])
                    
                    # For each test case in the detail table, update status and details
                    for j, test_case in enumerate(test_cases):
                        detail_items = self.detail_table.get_children()
                        if j < len(detail_items):
                            item_id = detail_items[j]
                            
                            # Generate random result for each test case
                            test_result = "Pass" if random.random() > 0.3 else "Fail"
                            if test_result == "Pass":
                                details = "Test completed successfully"
                            else:
                                details = "Test failed: Error code " + str(random.randint(1000, 9999))
                            
                            self.root.after(0, lambda id=item_id, res=test_result, det=details: self.detail_table.item(
                                id, values=(
                                    self.detail_table.item(id)["values"][0],  # service
                                    self.detail_table.item(id)["values"][1],  # action
                                    self.detail_table.item(id)["values"][2],  # params
                                    res,   # status
                                    det    # details
                                )
                            ))
                except Exception as e:
                    self.log_message(f"Error updating test results: {str(e)}")
            
            # 5. Add to history table
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            date, time_str = timestamp.split(" ")
            
            with open(file_path, 'r') as f:
                data = json.load(f)
            
            test_count = len(data.get("test_cases", []))
            
            self.root.after(0, lambda fn=file_name, d=date, t=time_str, tc=test_count, r=result: self.history_table.insert(
                "", 0,  # Insert at the top
                values=(d, t, fn, tc, r, "Tests completed with " + r.lower())
            ))
            
            # Log result
            self.log_message(f"File {file_name} processed: {result}")
        
        # All files processed or cancelled
        if self.processing:
            self.log_message(f"All {total_files} files processed")
            self.root.after(0, lambda: messagebox.showinfo("Complete", f"All {total_files} files processed"))
        else:
            self.log_message("Processing stopped. Some files may not have been processed.")
            
        # Reset UI
        self.processing = False
        self.root.after(0, lambda: self.send_button.configure(state=tk.NORMAL))
        self.root.after(0, lambda: self.cancel_button.configure(state=tk.DISABLED))
        self.root.after(0, lambda: self.progress_var.set(100))
    
    def apply_history_filter(self):
        """Apply filter to history table"""
        self.log_message("Filtering history...")
        # In a real application, this would query the database
    
    def clear_history_filter(self):
        """Clear history filters"""
        self.log_message("Clearing history filters...")
        # In a real application, this would reset the query
    
    def export_history(self):
        """Export history data to CSV"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")]
        )
        
        if filename:
            self.log_message(f"Exporting history to {filename}...")
            messagebox.showinfo("Export", f"History exported to {filename}")
    
    def view_history_details(self):
        """View details of a selected history item"""
        selection = self.history_table.selection()
        if selection:
            item_id = selection[0]
            filename = self.history_table.item(item_id)["values"][2]
            messagebox.showinfo("Details", f"Details for {filename}")
    
    def clear_logs(self):
        """Clear the log text area"""
        self.log_text.delete("1.0", tk.END)
    
    def export_logs(self):
        """Export logs to a text file"""
        filename = filedialog.asksaveasfilename(
            defaultextension=".log",
            filetypes=[("Log files", "*.log"), ("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                with open(filename, 'w') as f:
                    f.write(self.log_text.get("1.0", tk.END))
                messagebox.showinfo("Export", f"Logs exported to {filename}")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to export logs: {str(e)}")
    
    def log_message(self, message):
        """Add a message to the log with timestamp"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        log_entry = f"[{timestamp}] {message}\n"
        
        self.log_text.insert(tk.END, log_entry)
        self.log_text.see(tk.END)  # Scroll to the bottom
    
    def update_status_circle(self, color):
        """Update the connection status indicator color"""
        self.status_canvas.itemconfig(self.status_circle, fill=color)
    
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
    
    # Demo data for preview
    def load_demo_data(self):
        """Load demo data for preview"""
        # Add some demo files to the file table
        demo_files = [
            ("test_ping.json", "1.2 KB", "3", "Completed", "Pass", "4.5s"),
            ("test_wan.json", "0.8 KB", "2", "Completed", "Fail", "3.2s"),
            ("test_lan.json", "1.0 KB", "1", "Waiting", "", ""),
        ]
        
        for file_data in demo_files:
            self.file_table.insert("", "end", values=file_data)
        
        # Add demo test cases to the detail table
        demo_test_cases = [
            ("ping", "-", "host1=youtube.com, host2=google.com", "Pass", "All hosts reachable"),
            ("wan", "create", "interface1={type=pppoe, username=user1, password=pass1}", "Fail", "Authentication failed"),
            ("lan", "create", "interface1={interface=lan1, ip=192.168.1.1}", "-", "-"),
        ]
        
        for test_case in demo_test_cases:
            self.detail_table.insert("", "end", values=test_case)
        
        # Add demo history entries
        demo_history = [
            ("2025-05-26", "09:55", "test_ping.json", "3", "Pass", "All tests passed successfully"),
            ("2025-05-26", "09:30", "test_wan.json", "2", "Fail", "1 test failed: WAN authentication"),
            ("2025-05-25", "15:22", "test_firewall.json", "5", "Pass", "All tests passed successfully"),
            ("2025-05-24", "11:15", "test_dhcp.json", "2", "Pass", "All tests passed successfully"),
            ("2025-05-24", "10:05", "test_dns.json", "3", "Fail", "2 tests failed: DNS resolution"),
        ]
        
        for history_entry in demo_history:
            self.history_table.insert("", "end", values=history_entry)
        
        # Add some demo logs
        demo_logs = [
            "Application started",
            "Configuration loaded from config/settings.ini",
            "Testing connection to 192.168.88.1...",
            "Connection successful",
            "Selected 3 files",
            "Processing file 1/3: test_ping.json",
            "File test_ping.json processed: Pass",
            "Processing file 2/3: test_wan.json",
            "File test_wan.json processed: Fail",
            "All 3 files processed"
        ]
        
        for log_entry in demo_logs:
            self.log_message(log_entry)
        
        # Set connection status
        self.connection_status.set("Connected")
        self.update_status_circle("green")


def main():
    root = tk.Tk()
    app = ApplicationGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()