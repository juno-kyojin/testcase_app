#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Module: ui_components.py
# Purpose: UI components for Test Case Manager GUI
# Last updated: 2025-06-05 by juno-kyojin

import os
import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from .config import GUIConfig, AppConfig

class UIComponents:
    def __init__(self, gui):
        self.gui = gui
    
    def create_menu(self):
        """Create application menu bar"""
        menubar = tk.Menu(self.gui.root)
        self.gui.root.config(menu=menubar)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Select Files...", command=self.gui.select_files)
        file_menu.add_command(label="Send Files", command=self.gui.send_files)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.gui.on_closing)
        menubar.add_cascade(label="File", menu=file_menu)
        
        # Edit menu
        edit_menu = tk.Menu(menubar, tearoff=0)
        edit_menu.add_command(label="Clear Files", command=self.gui.clear_files)
        edit_menu.add_separator()
        edit_menu.add_command(label="Settings...", command=self.create_settings_dialog)
        menubar.add_cascade(label="Edit", menu=edit_menu)
        
        # View menu
        view_menu = tk.Menu(menubar, tearoff=0)
        view_menu.add_command(label="Refresh", command=self.gui.refresh_view)
        view_menu.add_separator()
        view_menu.add_command(label="Export Results...", command=self.gui.export_results)
        view_menu.add_command(label="Export History...", command=self.gui.export_history)
        view_menu.add_command(label="Export Logs...", command=self.gui.export_logs)
        menubar.add_cascade(label="View", menu=view_menu)
        
        # Tools menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        tools_menu.add_command(label="Connection Test...", command=self.gui.test_connection)
        tools_menu.add_command(label="Check Remote Folders...", command=self.gui.check_remote_folders)
        tools_menu.add_separator()
        tools_menu.add_command(label="Debug Database", command=self.gui.debug_database)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="Documentation", command=self.gui.show_documentation)
        help_menu.add_command(label="About", command=self.gui.show_about)
        menubar.add_cascade(label="Help", menu=help_menu)
    
    def create_notebook(self):
        """Create the main notebook/tabs interface"""
        self.notebook = ttk.Notebook(self.gui.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create each tab
        self.create_connection_tab()
        self.create_files_tab()
        self.create_history_tab()
        self.create_log_tab()
    
    def create_connection_tab(self):
        """Create the connection settings tab"""
        self.connection_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.connection_tab, text="Connection")
        
        # Connection settings frame
        settings_frame = ttk.LabelFrame(self.connection_tab, text="Connection Settings")
        settings_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # LAN IP
        ttk.Label(settings_frame, text="LAN IP:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(settings_frame, textvariable=self.gui.lan_ip_var, width=15).grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        # WAN IP (Optional)
        ttk.Label(settings_frame, text="WAN IP (Optional):").grid(row=0, column=2, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(settings_frame, textvariable=self.gui.wan_ip_var, width=15).grid(row=0, column=3, sticky=tk.W, padx=5, pady=5)
        
        # Username
        ttk.Label(settings_frame, text="Username:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(settings_frame, textvariable=self.gui.username_var, width=15).grid(row=1, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Password
        ttk.Label(settings_frame, text="Password:").grid(row=1, column=2, sticky=tk.W, padx=5, pady=5)
        password_entry = ttk.Entry(settings_frame, textvariable=self.gui.password_var, show="*", width=15)
        password_entry.grid(row=1, column=3, sticky=tk.W, padx=5, pady=5)
        
        # Remote paths
        ttk.Label(settings_frame, text="Config Path:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(settings_frame, textvariable=self.gui.config_path_var, width=25).grid(row=2, column=1, columnspan=1, sticky=tk.W+tk.E, padx=5, pady=5)
        
        ttk.Label(settings_frame, text="Result Path:").grid(row=2, column=2, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(settings_frame, textvariable=self.gui.result_path_var, width=25).grid(row=2, column=3, columnspan=1, sticky=tk.W+tk.E, padx=5, pady=5)
        
        # Button frame
        button_frame = ttk.Frame(self.connection_tab)
        button_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(button_frame, text="Test Connection", command=self.gui.test_connection).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Check Remote Folders", command=self.gui.check_remote_folders).pack(side=tk.LEFT, padx=5)
        ttk.Button(button_frame, text="Save Settings", command=self.gui.save_config).pack(side=tk.RIGHT, padx=5)
        ttk.Button(button_frame, text="Load Settings", command=self.gui.load_config).pack(side=tk.RIGHT, padx=5)
        
        # Connection info frame
        info_frame = ttk.LabelFrame(self.connection_tab, text="Connection Information")
        info_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Add a text widget for connection info
        self.gui.connection_info_text = tk.Text(info_frame, height=10, wrap=tk.WORD)
        self.gui.connection_info_text.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Initial connection info
        self.gui.connection_info_text.insert(tk.END, "Connection Status: Not connected\n")
        self.gui.connection_info_text.insert(tk.END, "Use 'Test Connection' to verify connection to device.\n")
        self.gui.connection_info_text.insert(tk.END, "Use 'Check Remote Folders' to verify required paths exist.\n")
        self.gui.connection_info_text.config(state=tk.DISABLED)
    
    def create_files_tab(self):
        """Create the files tab for selecting and queuing files"""
        self.files_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.files_tab, text="Test Queue")
        
        # Control frame
        control_frame = ttk.Frame(self.files_tab)
        control_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(control_frame, text="Select Files...", command=self.gui.select_files).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Clear All", command=self.gui.clear_files).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Move Up", command=self.gui.move_file_up).pack(side=tk.LEFT, padx=5)
        ttk.Button(control_frame, text="Move Down", command=self.gui.move_file_down).pack(side=tk.LEFT, padx=5)
        
        ttk.Button(control_frame, text="Send Files", command=self.gui.send_files).pack(side=tk.RIGHT, padx=5)
        ttk.Button(control_frame, text="Cancel", command=self.gui.cancel_processing).pack(side=tk.RIGHT, padx=5)
        
        # Create frame for file list
        file_frame = ttk.LabelFrame(self.files_tab, text="Selected Test Files")
        file_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Create treeview for files
        columns = ("file", "type", "size", "status", "result", "time")
        self.gui.file_table = ttk.Treeview(file_frame, columns=columns, show="headings", selectmode="browse")
        
        self.gui.file_table.heading("file", text="File")
        self.gui.file_table.heading("type", text="Type")
        self.gui.file_table.heading("size", text="Size")
        self.gui.file_table.heading("status", text="Status")
        self.gui.file_table.heading("result", text="Result")
        self.gui.file_table.heading("time", text="Time")
        
        self.gui.file_table.column("file", width=200)
        self.gui.file_table.column("type", width=80)
        self.gui.file_table.column("size", width=80)
        self.gui.file_table.column("status", width=100)
        self.gui.file_table.column("result", width=100)
        self.gui.file_table.column("time", width=80)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(file_frame, orient=tk.VERTICAL, command=self.gui.file_table.yview)
        self.gui.file_table.configure(yscrollcommand=scrollbar.set)
        
        self.gui.file_table.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Bind selection event
        self.gui.file_table.bind("<<TreeviewSelect>>", self.gui.on_file_selected)
        
        # Add progress bar
        progress_frame = ttk.LabelFrame(self.files_tab, text="Processing Progress")
        progress_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Progressbar(
            progress_frame, 
            orient=tk.HORIZONTAL, 
            length=100, 
            mode='determinate',
            variable=self.gui.progress_var
        ).pack(fill=tk.X, padx=5, pady=5)
        
        # Add test case details frame
        detail_frame = ttk.LabelFrame(self.files_tab, text="Test Case Details")
        detail_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # Create treeview for test case details
        columns = ("service", "action", "parameters", "status", "details")
        self.gui.detail_table = ttk.Treeview(detail_frame, columns=columns, show="headings")
        
        self.gui.detail_table.heading("service", text="Service")
        self.gui.detail_table.heading("action", text="Action")
        self.gui.detail_table.heading("parameters", text="Parameters")
        self.gui.detail_table.heading("status", text="Status")
        self.gui.detail_table.heading("details", text="Details")
        
        self.gui.detail_table.column("service", width=100)
        self.gui.detail_table.column("action", width=100)
        self.gui.detail_table.column("parameters", width=150)
        self.gui.detail_table.column("status", width=80)
        self.gui.detail_table.column("details", width=300)
        
        # Add scrollbar
        detail_scrollbar = ttk.Scrollbar(detail_frame, orient=tk.VERTICAL, command=self.gui.detail_table.yview)
        self.gui.detail_table.configure(yscrollcommand=detail_scrollbar.set)
        
        self.gui.detail_table.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        detail_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def create_history_tab(self):
        """Create the history tab"""
        self.history_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.history_tab, text="History")
        
        # Filter frame
        filter_frame = ttk.LabelFrame(self.history_tab, text="Filters")
        filter_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Date filter
        ttk.Label(filter_frame, text="Date:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.gui.date_combo = ttk.Combobox(
            filter_frame, 
            values=["All", "Today", "Last 7 Days", "Last 30 Days"], 
            width=12
        )
        self.gui.date_combo.current(0)
        self.gui.date_combo.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Status filter
        ttk.Label(filter_frame, text="Status:").grid(row=0, column=2, sticky=tk.W, padx=5, pady=5)
        self.gui.status_combo = ttk.Combobox(
            filter_frame, 
            values=["All", "Pass", "Fail", "Partial"], 
            width=12
        )
        self.gui.status_combo.current(0)
        self.gui.status_combo.grid(row=0, column=3, sticky=tk.W, padx=5, pady=5)
        
        # Filter buttons
        ttk.Button(filter_frame, text="Apply Filter", command=self.gui.apply_history_filter).grid(row=0, column=4, sticky=tk.W, padx=5, pady=5)
        ttk.Button(filter_frame, text="Clear Filter", command=self.gui.clear_history_filter).grid(row=0, column=5, sticky=tk.W, padx=5, pady=5)
        
        # History action buttons
        action_frame = ttk.Frame(self.history_tab)
        action_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Button(action_frame, text="View Details", command=self.gui.view_history_details).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="Export History", command=self.gui.export_history).pack(side=tk.LEFT, padx=5)
        ttk.Button(action_frame, text="Clear History", command=self.gui.clear_history).pack(side=tk.RIGHT, padx=5)
        
        # History table
        history_frame = ttk.Frame(self.history_tab)
        history_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        columns = ("date", "time", "file", "count", "result", "details")
        self.gui.history_table = ttk.Treeview(history_frame, columns=columns, show="headings")
        
        self.gui.history_table.heading("date", text="Date")
        self.gui.history_table.heading("time", text="Time")
        self.gui.history_table.heading("file", text="File")
        self.gui.history_table.heading("count", text="Test Count")
        self.gui.history_table.heading("result", text="Result")
        self.gui.history_table.heading("details", text="Details")
        
        self.gui.history_table.column("date", width=100)
        self.gui.history_table.column("time", width=100)
        self.gui.history_table.column("file", width=200)
        self.gui.history_table.column("count", width=80)
        self.gui.history_table.column("result", width=80)
        self.gui.history_table.column("details", width=200)
        
        # Add scrollbar
        scrollbar = ttk.Scrollbar(history_frame, orient=tk.VERTICAL, command=self.gui.history_table.yview)
        self.gui.history_table.configure(yscrollcommand=scrollbar.set)
        
        self.gui.history_table.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
    
    def create_log_tab(self):
        """Create log tab with filtering options"""
        self.log_tab = ttk.Frame(self.notebook)
        self.notebook.add(self.log_tab, text="Logs")
        
        # Log filter controls
        filter_frame = ttk.Frame(self.log_tab)
        filter_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Label(filter_frame, text="Log level:").pack(side=tk.LEFT, padx=5)
        
        log_level_combo = ttk.Combobox(
            filter_frame, 
            textvariable=self.gui.log_level_var,
            values=["All", "Connection", "File", "Result", "Error", "Debug"], 
            width=10
        )
        log_level_combo.pack(side=tk.LEFT, padx=5)
        log_level_combo.bind("<<ComboboxSelected>>", lambda e: self.gui.filter_logs())
        
        ttk.Button(
            filter_frame,
            text="Clear Logs",
            command=self.gui.clear_logs
        ).pack(side=tk.RIGHT, padx=5)
        
        ttk.Button(
            filter_frame,
            text="Export Logs",
            command=self.gui.export_logs
        ).pack(side=tk.RIGHT, padx=5)
        
        # Log text area
        log_frame = ttk.Frame(self.log_tab)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # Add vertical scrollbar
        scrollbar = ttk.Scrollbar(log_frame)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Text widget for logs
        self.gui.log_text = tk.Text(log_frame, wrap=tk.WORD, height=10)
        self.gui.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        # Configure scrollbar
        self.gui.log_text.config(yscrollcommand=scrollbar.set)
        scrollbar.config(command=self.gui.log_text.yview)
    
    def create_status_bar(self):
        """Create status bar at the bottom of the window"""
        status_frame = ttk.Frame(self.gui.root)
        status_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Thông tin kết nối
        self.gui.connection_frame = ttk.Frame(status_frame)
        self.gui.connection_frame.pack(side=tk.LEFT, padx=5)
        
        self.gui.status_canvas = tk.Canvas(self.gui.connection_frame, width=10, height=10)
        self.gui.status_circle = self.gui.status_canvas.create_oval(2, 2, 8, 8, fill="#808080")
        self.gui.status_canvas.pack(side=tk.LEFT)
        
        ttk.Label(self.gui.connection_frame, textvariable=self.gui.connection_status).pack(side=tk.LEFT, padx=5)
        
        # Status summary
        ttk.Label(status_frame, textvariable=self.gui.status_summary).pack(side=tk.LEFT, padx=10)
        
        # Đồng hồ thời gian
        time_frame = ttk.Frame(status_frame)
        time_frame.pack(side=tk.RIGHT, padx=5)
        
        ttk.Label(time_frame, textvariable=self.gui.time_var).pack(side=tk.RIGHT)
        
        # Start status summary updates
        self.gui.update_status_summary()
        self.gui.update_clock()
    
    def select_files(self):
        """Open file dialog to select test files"""
        file_paths = filedialog.askopenfilenames(
            title="Select Test Files",
            filetypes=[("JSON Files", "*.json"), ("All Files", "*.*")]
        )
        
        if not file_paths:
            return
        
        # Clear current selection if needed
        if self.gui.selected_files:
            self.clear_files()
            
        self.gui.log_file("File selection cleared")
        
        # Add selected files
        for path in file_paths:
            self.add_file_to_queue(path)
            
        self.gui.log_file(f"Selected {len(self.gui.selected_files)} valid files")
    
    def add_file_to_queue(self, file_path):
        """Add a file to the queue"""
        if not os.path.isfile(file_path):
            return False
            
        file_name = os.path.basename(file_path)
        file_size = os.path.getsize(file_path)
        file_type = os.path.splitext(file_name)[1].lower()[1:]  # Remove dot
        
        size_str = f"{file_size / 1024:.1f} KB" if file_size >= 1024 else f"{file_size} B"
        
        # Add to selected files list
        self.gui.selected_files.append(file_path)
        
        # Try to determine file impacts
        impacts = {"affects_lan": False, "affects_wan": False}
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                file_data = json.load(f)
                impacts = file_data.get("impacts", impacts)
                self.gui.file_data[file_name] = file_data
        except:
            pass
            
        # Add to table
        self.gui.file_table.insert("", tk.END, values=(
            file_name,
            file_type,
            size_str,
            "Queued",
            "",
            ""
        ))
        
        return True
    
    def clear_files(self):
        """Clear all selected files"""
        for item in self.gui.file_table.get_children():
            self.gui.file_table.delete(item)
            
        self.gui.selected_files = []
        self.gui.file_data = {}
        
        # Clear detail table
        for item in self.gui.detail_table.get_children():
            self.gui.detail_table.delete(item)
            
        self.gui.log_file("File selection cleared")
    
    def move_file_up(self):
        """Move selected file up in the list"""
        selected = self.gui.file_table.selection()
        if not selected:
            return
            
        idx = self.gui.file_table.index(selected[0])
        if idx > 0:
            # Get values
            values = self.gui.file_table.item(selected[0], "values")
            # Delete current item
            self.gui.file_table.delete(selected[0])
            # Insert at new position
            item_id = self.gui.file_table.insert("", idx-1, values=values)
            # Select the moved item
            self.gui.file_table.selection_set(item_id)
            # Update selected_files list
            self.gui.selected_files.insert(idx-1, self.gui.selected_files.pop(idx))
    
    def move_file_down(self):
        """Move selected file down in the list"""
        selected = self.gui.file_table.selection()
        if not selected:
            return
            
        idx = self.gui.file_table.index(selected[0])
        if idx < len(self.gui.selected_files) - 1:
            # Get values
            values = self.gui.file_table.item(selected[0], "values")
            # Delete current item
            self.gui.file_table.delete(selected[0])
            # Insert at new position
            item_id = self.gui.file_table.insert("", idx+1, values=values)
            # Select the moved item
            self.gui.file_table.selection_set(item_id)
            # Update selected_files list
            self.gui.selected_files.insert(idx+1, self.gui.selected_files.pop(idx))
    
    def on_file_selected(self, event):
        """Handle file selection to show test case details"""
        selected = self.gui.file_table.selection()
        if not selected:
            return
            
        idx = self.gui.file_table.index(selected[0])
        if idx < 0 or idx >= len(self.gui.selected_files):
            return
            
        # Get file name
        values = self.gui.file_table.item(selected[0], "values")
        if not values:
            return
            
        file_name = values[0]
        
        # Get file data and display test details if available
        file_data = self.gui.file_data.get(file_name, {})
        test_cases = file_data.get("test_cases", [])
        
        # Clear detail table
        for item in self.gui.detail_table.get_children():
            self.gui.detail_table.delete(item)
            
        # Add test cases to detail table
        if test_cases:
            for test in test_cases:
                self.gui.detail_table.insert("", tk.END, values=(
                    test.get("service", ""),
                    test.get("action", ""),
                    test.get("parameters", ""),
                    "",  # Status (empty until run)
                    test.get("description", "")
                ))
        else:
            # Try to extract from filename
            parts = os.path.splitext(file_name)[0].split('_')
            if len(parts) >= 2:
                service = parts[0]
                action = parts[1] if len(parts) > 1 else ""
                self.gui.detail_table.insert("", tk.END, values=(
                    service,
                    action,
                    "",
                    "",
                    f"Test file: {file_name}"
                ))
            else:
                self.gui.detail_table.insert("", tk.END, values=(
                    "",
                    "",
                    "",
                    "",
                    f"No test case details available for {file_name}"
                ))
    
    def create_settings_dialog(self):
        """Create and show settings dialog"""
        settings_dialog = tk.Toplevel(self.gui.root)
        settings_dialog.title("Application Settings")
        settings_dialog.geometry("500x400")
        settings_dialog.grab_set()  # Modal dialog
        
        # Set icon if available
        try:
            settings_dialog.iconbitmap("assets/app_icon.ico")
        except:
            pass
        
        # Application settings
        app_frame = ttk.LabelFrame(settings_dialog, text="Application Settings")
        app_frame.pack(fill=tk.X, padx=10, pady=10)
        
        # Debug mode
        debug_var = tk.BooleanVar(value=self.gui.debug_mode)
        ttk.Checkbutton(
            app_frame, 
            text="Enable Debug Mode", 
            variable=debug_var,
            command=lambda: setattr(self.gui, 'debug_mode', debug_var.get())
        ).pack(anchor=tk.W, padx=10, pady=5)
        
        # Timeout settings
        timeout_frame = ttk.Frame(app_frame)
        timeout_frame.pack(fill=tk.X, padx=10, pady=5)
        
        ttk.Label(timeout_frame, text="Default timeout (seconds):").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        timeout_var = tk.IntVar(value=AppConfig.DEFAULT_TIMEOUT)
        timeout_entry = ttk.Entry(timeout_frame, textvariable=timeout_var, width=5)
        timeout_entry.grid(row=0, column=1, sticky=tk.W, padx=5, pady=5)
        
        # Buttons
        button_frame = ttk.Frame(settings_dialog)
        button_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(
            button_frame,
            text="Save",
            command=lambda: [
                setattr(AppConfig, 'DEFAULT_TIMEOUT', timeout_var.get()),
                settings_dialog.destroy(),
                self.gui.log_message("Settings updated")
            ]
        ).pack(side=tk.RIGHT, padx=5)
        
        ttk.Button(
            button_frame,
            text="Cancel",
            command=settings_dialog.destroy
        ).pack(side=tk.RIGHT, padx=5)