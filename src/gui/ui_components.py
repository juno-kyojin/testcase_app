import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import time

class UIComponents:
    def __init__(self, gui):
        self.gui = gui
        self.file_manager = gui.file_manager
        # Don't reference other handlers during initialization
        
    def create_menu(self):
        """Create application menu bar"""
        menubar = tk.Menu(self.gui.root)
        
        # File menu
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="Save Configuration...", command=self.gui.save_config)
        file_menu.add_command(label="Export Results...", command=self.gui.export_results)
        file_menu.add_separator()
        file_menu.add_command(label="Exit", command=self.gui.on_closing)
        menubar.add_cascade(label="File", menu=file_menu)
        
        # View menu
        view_menu = tk.Menu(menubar, tearoff=0)
        view_menu.add_command(label="Refresh", command=self.gui.refresh_view)
        view_menu.add_command(label="Clear History", command=self.gui.clear_history)
        menubar.add_cascade(label="View", menu=view_menu)
        
        # Tools menu
        tools_menu = tk.Menu(menubar, tearoff=0)
        tools_menu.add_command(label="Connection Test...", command=self.gui.test_connection)
        tools_menu.add_command(label="Check Remote Folders...", command=self.gui.check_remote_folders)
        menubar.add_cascade(label="Tools", menu=tools_menu)
        
        # Help menu
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="Documentation", command=self.gui.show_documentation)
        help_menu.add_command(label="About", command=self.gui.show_about)
        menubar.add_cascade(label="Help", menu=help_menu)
        
        self.gui.root.config(menu=menubar)
    
    def create_notebook(self):
        """Create the main notebook/tabs interface"""
        self.gui.notebook = ttk.Notebook(self.gui.root)
        self.gui.notebook.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Create tabs
        self.gui.main_tab = ttk.Frame(self.gui.notebook)
        self.gui.history_tab = ttk.Frame(self.gui.notebook)
        self.gui.logs_tab = ttk.Frame(self.gui.notebook)
        
        # Add tabs to notebook
        self.gui.notebook.add(self.gui.main_tab, text="Test Queue")
        self.gui.notebook.add(self.gui.history_tab, text="History")
        self.gui.notebook.add(self.gui.logs_tab, text="Logs")
        
        # Setup tab content
        self.setup_main_tab()
        self.setup_history_tab()
        self.setup_logs_tab()
    
    def setup_main_tab(self):
        """Setup the main tab content"""
        # Connection Frame
        connection_frame = ttk.LabelFrame(self.gui.main_tab, text="Connection Settings")
        connection_frame.pack(fill=tk.X, padx=10, pady=5)
        
        # Connection fields in grid
        ttk.Label(connection_frame, text="LAN IP:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(connection_frame, textvariable=self.gui.lan_ip_var, width=20).grid(row=0, column=1, padx=5, pady=5)
        
        ttk.Label(connection_frame, text="Username:").grid(row=0, column=2, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(connection_frame, textvariable=self.gui.username_var, width=15).grid(row=0, column=3, padx=5, pady=5)
        
        ttk.Label(connection_frame, text="Password:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(connection_frame, textvariable=self.gui.password_var, show="•", width=20).grid(row=1, column=1, padx=5, pady=5)
        
        ttk.Label(connection_frame, text="Config Path:").grid(row=1, column=2, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(connection_frame, textvariable=self.gui.config_path_var, width=25).grid(row=1, column=3, padx=5, pady=5)
        
        ttk.Label(connection_frame, text="Result Path:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=5)
        ttk.Entry(connection_frame, textvariable=self.gui.result_path_var, width=25).grid(row=2, column=1, padx=5, pady=5)
        
        # Connection buttons
        btn_frame = ttk.Frame(connection_frame)
        btn_frame.grid(row=2, column=2, columnspan=2, pady=5)
        ttk.Button(btn_frame, text="Test Connection", command=self.gui.test_connection).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="Save Settings", command=self.gui.save_config).pack(side=tk.LEFT, padx=5)
        
        # File Frame
        file_frame = ttk.LabelFrame(self.gui.main_tab, text="Test Files")
        file_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        # File buttons
        file_btn_frame = ttk.Frame(file_frame)
        file_btn_frame.pack(fill=tk.X, padx=5, pady=5)
        
        ttk.Button(file_btn_frame, text="Select Files", command=self.select_files).pack(side=tk.LEFT, padx=5)
        ttk.Button(file_btn_frame, text="Clear Selection", command=self.clear_files).pack(side=tk.LEFT, padx=5)
        
        # File table
        table_frame = ttk.Frame(file_frame)
        table_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.gui.file_table = ttk.Treeview(
            table_frame, 
            columns=("filename", "size", "tests", "status", "result", "time"),
            show="headings", 
            selectmode="browse"
        )
        
        # Setup columns
        self.gui.file_table.heading("filename", text="Filename")
        self.gui.file_table.heading("size", text="Size")
        self.gui.file_table.heading("tests", text="Tests")
        self.gui.file_table.heading("status", text="Status")
        self.gui.file_table.heading("result", text="Result")
        self.gui.file_table.heading("time", text="Time")
        
        self.gui.file_table.column("filename", width=200)
        self.gui.file_table.column("size", width=80)
        self.gui.file_table.column("tests", width=50)
        self.gui.file_table.column("status", width=100)
        self.gui.file_table.column("result", width=100)
        self.gui.file_table.column("time", width=100)
        
        scrollbar = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self.gui.file_table.yview)
        self.gui.file_table.configure(yscrollcommand=scrollbar.set)
        
        self.gui.file_table.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Detail table
        detail_frame = ttk.LabelFrame(self.gui.main_tab, text="Test Case Details")
        detail_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        detail_table_frame = ttk.Frame(detail_frame)
        detail_table_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        self.gui.detail_table = ttk.Treeview(
            detail_table_frame, 
            columns=("service", "action", "params", "status", "details"),
            show="headings"
        )
        
        self.gui.detail_table.heading("service", text="Service")
        self.gui.detail_table.heading("action", text="Action")
        self.gui.detail_table.heading("params", text="Parameters")
        self.gui.detail_table.heading("status", text="Status")
        self.gui.detail_table.heading("details", text="Details")
        
        detail_scrollbar = ttk.Scrollbar(detail_table_frame, orient=tk.VERTICAL, command=self.gui.detail_table.yview)
        self.gui.detail_table.configure(yscrollcommand=detail_scrollbar.set)
        
        self.gui.detail_table.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        detail_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Action buttons
        action_frame = ttk.Frame(self.gui.main_tab)
        action_frame.pack(fill=tk.X, padx=10, pady=10)
        
        self.gui.send_button = ttk.Button(action_frame, text="Send Files", command=self.gui.send_files)
        self.gui.send_button.pack(side=tk.LEFT, padx=5)
        
        self.gui.cancel_button = ttk.Button(action_frame, text="Cancel", command=self.gui.cancel_processing, state=tk.DISABLED)
        self.gui.cancel_button.pack(side=tk.LEFT, padx=5)
        
        self.gui.progress_bar = ttk.Progressbar(action_frame, orient=tk.HORIZONTAL, mode='determinate', variable=self.gui.progress_var)
        self.gui.progress_bar.pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=10)
    
    def setup_history_tab(self):
        """Setup the history tab content"""
        # Filter frame
        filter_frame = ttk.Frame(self.gui.history_tab)
        filter_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Label(filter_frame, text="Date:").pack(side=tk.LEFT, padx=5)
        self.gui.date_combo = ttk.Combobox(filter_frame, width=15, values=["All", "Today", "Last 7 Days", "Last 30 Days"])
        self.gui.date_combo.current(0)
        self.gui.date_combo.pack(side=tk.LEFT, padx=5)
        
        ttk.Label(filter_frame, text="Status:").pack(side=tk.LEFT, padx=5)
        self.gui.status_combo = ttk.Combobox(filter_frame, width=15, values=["All", "Pass", "Fail", "Partial"])
        self.gui.status_combo.current(0)
        self.gui.status_combo.pack(side=tk.LEFT, padx=5)
        
        ttk.Button(filter_frame, text="Apply Filter", command=self.gui.apply_history_filter).pack(side=tk.LEFT, padx=5)
        ttk.Button(filter_frame, text="Clear Filter", command=self.gui.clear_history_filter).pack(side=tk.LEFT, padx=5)
        
        # History table
        history_frame = ttk.Frame(self.gui.history_tab)
        history_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
        
        self.gui.history_table = ttk.Treeview(
            history_frame, 
            columns=("date", "time", "file", "tests", "result", "details"),
            show="headings"
        )
        
        self.gui.history_table.heading("date", text="Date")
        self.gui.history_table.heading("time", text="Time")
        self.gui.history_table.heading("file", text="Filename")
        self.gui.history_table.heading("tests", text="Tests")
        self.gui.history_table.heading("result", text="Result")
        self.gui.history_table.heading("details", text="Details")
        
        history_scrollbar = ttk.Scrollbar(history_frame, orient=tk.VERTICAL, command=self.gui.history_table.yview)
        self.gui.history_table.configure(yscrollcommand=history_scrollbar.set)
        
        self.gui.history_table.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        history_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # History buttons
        history_btn_frame = ttk.Frame(self.gui.history_tab)
        history_btn_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(history_btn_frame, text="Export to CSV", command=self.gui.export_history).pack(side=tk.LEFT, padx=5)
        ttk.Button(history_btn_frame, text="View Details", command=self.gui.view_history_details).pack(side=tk.LEFT, padx=5)
        ttk.Button(history_btn_frame, text="Refresh", command=self.gui.load_history).pack(side=tk.LEFT, padx=5)
    
    def setup_logs_tab(self):
        """Setup the logs tab content"""
        log_frame = ttk.Frame(self.gui.logs_tab)
        log_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # Log text area
        self.gui.log_text = tk.Text(log_frame, wrap=tk.WORD, font=("Consolas", 10))
        log_scrollbar = ttk.Scrollbar(log_frame, orient=tk.VERTICAL, command=self.gui.log_text.yview)
        self.gui.log_text.configure(yscrollcommand=log_scrollbar.set)
        
        self.gui.log_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        log_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        
        # Log buttons
        log_btn_frame = ttk.Frame(self.gui.logs_tab)
        log_btn_frame.pack(fill=tk.X, padx=10, pady=10)
        
        ttk.Button(log_btn_frame, text="Clear Logs", command=self.gui.clear_logs).pack(side=tk.LEFT, padx=5)
        ttk.Button(log_btn_frame, text="Export Logs", command=self.gui.export_logs).pack(side=tk.LEFT, padx=5)
        ttk.Button(log_btn_frame, text="Refresh", command=self.gui.refresh_logs).pack(side=tk.LEFT, padx=5)
    
    def create_status_bar(self):
        """Create status bar at the bottom of the window"""
        status_frame = ttk.Frame(self.gui.root, relief=tk.SUNKEN, borderwidth=1)
        status_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        # Connection status indicator
        self.gui.status_canvas = tk.Canvas(status_frame, width=15, height=15)
        self.gui.status_canvas.pack(side=tk.LEFT, padx=5, pady=2)
        self.gui.status_circle = self.gui.status_canvas.create_oval(2, 2, 13, 13, fill="red")
        
        # Status text
        ttk.Label(status_frame, textvariable=self.gui.connection_status).pack(side=tk.LEFT, padx=5)
        
        # User info
        user_var = tk.StringVar(value=f"User: {os.environ.get('USERNAME', 'unknown')}")
        ttk.Label(status_frame, textvariable=user_var).pack(side=tk.LEFT, padx=15)
        
        # Current time
        self.gui.update_clock()
        ttk.Label(status_frame, textvariable=self.gui.time_var).pack(side=tk.RIGHT, padx=10)
    
    def select_files(self):
        """Select and validate JSON files"""
        files = filedialog.askopenfilenames(
            title="Select JSON Test Files",
            filetypes=[("JSON files", "*.json"), ("All files", "*.*")]
        )
        
        if not files:
            return
        
        self.clear_files()
        
        valid_files = []
        for file_path in files:
            try:
                is_valid, error_msg, data = self.file_manager.validate_json_file(file_path)
                
                if is_valid:
                    valid_files.append(file_path)
                    
                    file_name = os.path.basename(file_path)
                    self.gui.file_data[file_name] = {
                        "path": file_path,
                        "data": data,
                        "impacts": self.file_manager.analyze_test_impacts(data)
                    }
                    
                    file_size = os.path.getsize(file_path)
                    size_str = f"{file_size / 1024:.1f} KB"
                    test_count = self.file_manager.get_test_case_count(data)
                    
                    self.gui.file_table.insert("", "end", values=(file_name, size_str, test_count, "Waiting", "", ""))
                else:
                    self.gui.log_message(f"Invalid file {os.path.basename(file_path)}: {error_msg}")
                    
            except Exception as e:
                self.gui.log_message(f"Error processing {os.path.basename(file_path)}: {str(e)}")
        
        self.gui.selected_files = valid_files
        self.gui.log_message(f"Selected {len(valid_files)} valid files")
    
    def clear_files(self):
        """Clear selected files"""
        self.gui.selected_files = []
        self.gui.file_data = {}
        
        for item in self.gui.file_table.get_children():
            self.gui.file_table.delete(item)
        
        for item in self.gui.detail_table.get_children():
            self.gui.detail_table.delete(item)
        
        self.gui.log_message("File selection cleared")
    
    def move_file_up(self):
        """Move selected file up in the list"""
        # Simple implementation
        pass
    
    def move_file_down(self):
        """Move selected file down in the list"""
        # Simple implementation
        pass
    
    def on_file_selected(self, event):
        """Handle file selection to show test case details"""
        # Simple implementation
        pass
