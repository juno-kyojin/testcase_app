#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Module: interface.py  
# Purpose: Main GUI window for Test Case Manager (Windows Edition) - Refactored
# Last updated: 2025-06-05 by juno-kyojin

import os
import sys
import json
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import time
import datetime
import logging
import sqlite3
import csv
import platform
from typing import Optional, Tuple, List, Dict

# Import các module windows-specific
from files.manager import TestFileManager
from network.connection import SSHConnection
from storage.database import TestDatabase

# Import GUI modules
from .config import AppConfig, GUIConfig
from .connection_handler import ConnectionHandler
from .file_processor import FileProcessor
from .result_handler import ResultHandler
from .ui_components import UIComponents
from .utils import GUIUtils

class ApplicationGUI:
    def __init__(self, root):
        self.root = root
        self.root.title("Test Case Manager v2.0 - Windows Edition")
        
        # Setup window geometry and styles
        GUIConfig.setup_window_geometry(root)
        self.style = GUIConfig.setup_styles()
        self.logger = GUIConfig.setup_logging()
        
        # Initialize real modules
        self.ssh_connection = SSHConnection()
        self.file_manager = TestFileManager()
        self.database = TestDatabase()
        
        # Setup variables and state first
        self.setup_variables()
        self.selected_files = []
        self.file_data = {}
        self.current_file_index = -1
        self.processing = False
        self.file_retry_count = {}
        self.debug_mode = False  # Set to True to enable debug logs
        
        # Initialize handlers after all basic attributes are set
        self._initialize_handlers()
        
        # Create UI components
        self.create_menu()
        self.create_notebook()
        self.create_status_bar()
        
        # Load history and setup auto-save
        self.load_history()
        self.setup_auto_save()
        self.schedule_cleanup()
        
        # Set Windows-specific icon
        try:
            self.root.iconbitmap("assets/app_icon.ico")
        except:
            pass
        
        # Handle window closing
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)
    
    def _initialize_handlers(self):
        """Initialize all handler modules in the correct order"""
        try:
            # Initialize handlers step by step to avoid circular dependencies
            self.result_handler = ResultHandler(self)
            self.connection_handler = ConnectionHandler(self)
            self.file_processor = FileProcessor(self)
            self.ui_components = UIComponents(self)
            self.utils = GUIUtils(self)
            
            self.logger.info("All handlers initialized successfully")
            
        except Exception as e:
            self.logger.error(f"Failed to initialize handlers: {e}")
            raise
    
    def setup_variables(self):
        """Setup and load variables from database"""
        self.lan_ip_var = tk.StringVar(value=self.database.get_setting("lan_ip", "192.168.88.1"))
        self.wan_ip_var = tk.StringVar(value=self.database.get_setting("wan_ip", ""))
        self.username_var = tk.StringVar(value=self.database.get_setting("username", "root"))
        self.password_var = tk.StringVar()
        self.config_path_var = tk.StringVar(value=self.database.get_setting("config_path", "/root/config"))
        self.result_path_var = tk.StringVar(value=self.database.get_setting("result_path", "/root/result"))
        self.connection_status = tk.StringVar(value="Not Connected")
        self.progress_var = tk.IntVar()
        self.time_var = tk.StringVar()
        self.status_summary = tk.StringVar(value="Ready")
        self.log_level_var = tk.StringVar(value="All")
    
    def setup_auto_save(self):
        """Setup auto-save for settings when they change"""
        def save_setting(var_name, var):
            def callback(*args):
                try:
                    self.database.save_setting(var_name, var.get())
                except Exception as e:
                    self.log_error(f"Auto-save failed for {var_name}: {e}")
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
                self.utils.cleanup_temp_files()
            except Exception as e:
                self.log_error(f"Cleanup task failed: {e}")
            self.root.after(3600000, cleanup_task)  # 1 hour
        
        self.root.after(300000, cleanup_task)  # Start after 5 minutes
    
    # Enhanced logging methods
    def log_message(self, message: str, log_type: str = "INFO"):
        """Add a message to the log with timestamp and proper formatting"""
        timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
        
        # Định dạng dựa trên loại log
        if log_type == "CONNECTION":
            formatted_msg = f"[{timestamp}] 🔌 CONNECTION: {message}"
        elif log_type == "FILE":
            formatted_msg = f"[{timestamp}] 📄 FILE: {message}"
        elif log_type == "RESULT":
            formatted_msg = f"[{timestamp}] ✅ RESULT: {message}" 
        elif log_type == "ERROR":
            formatted_msg = f"[{timestamp}] ❌ ERROR: {message}"
        elif log_type == "DEBUG":
            formatted_msg = f"[{timestamp}] 🔍 DEBUG: {message}"
        else:
            formatted_msg = f"[{timestamp}] ℹ️ INFO: {message}"
        
        # Log ra logger chính thức trước
        if log_type == "ERROR":
            self.logger.error(message)
        elif log_type == "DEBUG":
            self.logger.debug(message)
        else:
            self.logger.info(message)
        
        # Sau đó kiểm tra xem log_text đã được tạo chưa
        log_entry = formatted_msg + "\n"
        
        # Sử dụng getattr() để tránh AttributeError nếu log_text chưa tồn tại
        log_text = getattr(self, 'log_text', None)
        if log_text is not None:
            try:
                log_text.insert(tk.END, log_entry)
                log_text.see(tk.END)
            except Exception as e:
                self.logger.error(f"Error writing to log display: {e}")

    def log_connection(self, message: str):
        """Log connection related message"""
        self.log_message(message, "CONNECTION")
        
    def log_file(self, message: str):
        """Log file operation related message"""
        self.log_message(message, "FILE")
        
    def log_result(self, message: str):
        """Log test result related message"""
        self.log_message(message, "RESULT")
        
    def log_error(self, message: str):
        """Log error message"""
        self.log_message(message, "ERROR")
        
    def log_debug(self, message: str):
        """Log debug message - only shown in debug mode"""
        if self.debug_mode:
            self.log_message(message, "DEBUG")
    
    def filter_logs(self):
        """Filter logs based on selected log level"""
        # Sử dụng getattr để kiểm tra an toàn
        log_text = getattr(self, 'log_text', None)
        log_level_var = getattr(self, 'log_level_var', None)
        
        if log_text is None or log_level_var is None:
            self.logger.warning("Log text or level variable not initialized yet")
            return
            
        selected_level = log_level_var.get()
        
        if selected_level == "All":
            return  # No filtering needed
        
        # Map level name to emoji/prefix
        level_prefix = {
            "Connection": "🔌 CONNECTION:",
            "File": "📄 FILE:",
            "Result": "✅ RESULT:",
            "Error": "❌ ERROR:",
            "Debug": "🔍 DEBUG:",
        }
        
        try:
            # Get current log content
            log_content = log_text.get("1.0", tk.END)
            
            # Clear current content
            log_text.delete("1.0", tk.END)
            
            # Filter and re-insert relevant lines
            for line in log_content.splitlines():
                if level_prefix.get(selected_level, "") in line:
                    log_text.insert(tk.END, line + "\n")
            
            # Scroll to end
            log_text.see(tk.END)
        except Exception as e:
            self.logger.error(f"Error filtering logs: {e}")
    def test_connection(self):
        """Test connection using connection handler"""
        self.connection_handler.test_connection()
    
    def check_remote_folders(self):
        """Check remote folders using connection handler"""
        self.connection_handler.check_remote_folders()
    
    def select_files(self):
        """Select files using UI components"""
        self.ui_components.select_files()
    
    def send_files(self):
        """Send files using file processor"""
        self.file_processor.send_files()
    
    def cancel_processing(self):
        """Cancel processing using file processor"""
        self.file_processor.cancel_processing()
    
    # UI Creation methods (delegate to ui_components)
    def create_menu(self):
        """Create application menu bar"""
        self.ui_components.create_menu()
    
    def create_notebook(self):
        """Create the main notebook/tabs interface"""
        self.ui_components.create_notebook()
    
    def create_status_bar(self):
        """Create status bar at the bottom of the window"""
        self.ui_components.create_status_bar()
    
    # Utility methods
    def update_status_summary(self):
        """Update status summary with current information"""
        try:
            status_text = f"Connection: {self.connection_status.get()} | "
            
            if hasattr(self, 'selected_files'):
                status_text += f"Files: {len(self.selected_files)} selected | "
            
            if self.processing:
                if hasattr(self, 'current_file_index') and self.current_file_index >= 0:
                    status_text += f"Processing: {self.current_file_index + 1}/{len(self.selected_files)}"
            else:
                status_text += "Ready"
                
            self.status_summary.set(status_text)
            
            # Schedule next update
            self.root.after(1000, self.update_status_summary)
        except Exception:
            pass  # Avoid errors in status update
    
    def validate_connection_fields(self) -> bool:
        """Validate connection fields"""
        return self.utils.validate_connection_fields()
    
    def update_status_circle(self, color: str):
        """Update connection status circle color"""
        self.utils.update_status_circle(color)
    
    def update_file_status(self, file_index: int, status: str, result: str = "", time_str: str = ""):
        """Update file status in the table"""
        self.utils.update_file_status(file_index, status, result, time_str)
    
    def update_detail_table_with_results(self, file_index: int, result_data: Dict):
        """Update detail table with test results"""
        self.utils.update_detail_table_with_results(file_index, result_data)
    
    # Configuration methods
    def save_config(self):
        """Save configuration using database"""
        self.utils.save_config()
    
    def load_config(self):
        """Load configuration from database"""
        self.utils.load_config()
    
    # History and view methods
    def load_history(self):
        """Load history from database"""
        self.utils.load_history()
    
    def clear_history(self):
        """Clear history with confirmation"""
        self.utils.clear_history()
    
    def refresh_view(self):
        """Refresh all views"""
        self.utils.refresh_view()
    
    # File management methods
    def clear_files(self):
        """Clear selected files"""
        self.ui_components.clear_files()
    
    def move_file_up(self):
        """Move selected file up in the list"""
        self.ui_components.move_file_up()
    
    def move_file_down(self):
        """Move selected file down in the list"""
        self.ui_components.move_file_down()
    
    def on_file_selected(self, event):
        """Handle file selection to show test case details"""
        self.ui_components.on_file_selected(event)
    
    # Export methods
    def export_results(self):
        """Export current results to CSV"""
        self.utils.export_results()
    
    def export_history(self):
        """Export history to CSV"""
        self.utils.export_history()
    
    def export_logs(self):
        """Export logs to file"""
        self.utils.export_logs()
    
    # Filter methods
    def apply_history_filter(self):
        """Apply filters to history view"""
        self.utils.apply_history_filter()
    
    def clear_history_filter(self):
        """Clear history filters"""
        self.utils.clear_history_filter()
    
    def view_history_details(self):
        """View detailed information for selected history item"""
        self.utils.view_history_details()
    
    # Log methods
    def clear_logs(self):
        """Clear the log display"""
        self.utils.clear_logs()
    
    def refresh_logs(self):
        """Refresh the logs display"""
        self.utils.refresh_logs()
        
    def debug_database(self):
        """Debug database structure and content"""
        self.utils.debug_database()
    
    # Help methods
    def show_documentation(self):
        """Show documentation"""
        self.utils.show_documentation()
    
    def show_about(self):
        """Show about dialog"""
        self.utils.show_about()
    
    def update_clock(self):
        """Update the clock in the status bar"""
        current_time = time.strftime("%Y-%m-%d %H:%M:%S")
        self.time_var.set(current_time)
        self.root.after(1000, self.update_clock)
    
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
            
            if result is None:
                return
            elif result:
                self.processing = False
                self.log_message("Waiting for current operation to complete...")
            else:
                self.processing = False
                self.ssh_connection.disconnect()
                self.logger.info("Application closed by user (immediate)")
                self.root.destroy()
                return
        
        try:
            self.ssh_connection.disconnect()
            self.logger.info(f"Application closed normally by {os.environ.get('USERNAME', 'unknown')}")
        except Exception as e:
            self.logger.warning(f"Error during cleanup: {e}")
        
        self.root.destroy()