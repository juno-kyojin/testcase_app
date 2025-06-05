import os
import time
import datetime
import csv
import tkinter as tk
from tkinter import messagebox, filedialog
from .config import AppConfig

class GUIUtils:
    def __init__(self, gui):
        self.gui = gui
        self.database = gui.database
        self.logger = gui.logger
        # Don't reference other handlers during initialization
        
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
                self.gui.log_message(f"Cleaned up {cleaned_count} old temporary files")
                
        except Exception as e:
            self.logger.error(f"Cleanup failed: {e}")
    
    def validate_connection_fields(self) -> bool:
        """Validate connection fields"""
        if not self.gui.lan_ip_var.get().strip():
            messagebox.showerror("Validation Error", "LAN IP address is required")
            return False
        
        if not self.gui.username_var.get().strip():
            messagebox.showerror("Validation Error", "Username is required")
            return False
        
        if not self.gui.password_var.get():
            messagebox.showerror("Validation Error", "Password is required")
            return False
        
        return True
    
    def update_status_circle(self, color: str):
        """Update connection status circle color"""
        color_mapping = {
            "green": "#00AA00",
            "yellow": "#FFB000", 
            "red": "#CC0000",
            "gray": "#808080"
        }
        
        actual_color = color_mapping.get(color, color)
        if hasattr(self.gui, 'status_canvas') and hasattr(self.gui, 'status_circle'):
            self.gui.status_canvas.itemconfig(self.gui.status_circle, fill=actual_color)
    
    def update_file_status(self, file_index: int, status: str, result: str = "", time_str: str = ""):
        """Update file status in the table"""
        try:
            if not hasattr(self.gui, 'file_table'):
                return
            
            items = self.gui.file_table.get_children()
            if file_index < len(items):
                item_id = items[file_index]
                current_values = list(self.gui.file_table.item(item_id)["values"])
                current_values[3] = status  # Status column
                if result:
                    current_values[4] = result  # Result column
                if time_str:
                    current_values[5] = time_str  # Time column
                
                self.gui.root.after(0, lambda: self.gui.file_table.item(item_id, values=tuple(current_values)))
        except Exception as e:
            self.logger.error(f"Error updating file status: {e}")
    
    def update_detail_table_with_results(self, file_index: int, result_data: dict):
        """Update detail table with test results"""
        # Simple implementation
        pass
    
    def save_config(self):
        """Save configuration"""
        try:
            self.database.save_setting("lan_ip", self.gui.lan_ip_var.get())
            self.database.save_setting("username", self.gui.username_var.get())
            self.database.save_setting("config_path", self.gui.config_path_var.get())
            self.database.save_setting("result_path", self.gui.result_path_var.get())
            
            self.gui.log_message("Configuration saved successfully")
            messagebox.showinfo("Success", "Configuration saved successfully")
            
        except Exception as e:
            error_msg = f"Failed to save configuration: {str(e)}"
            self.gui.log_message(error_msg)
            messagebox.showerror("Error", error_msg)
    
    def load_config(self):
        """Load configuration"""
        try:
            self.gui.lan_ip_var.set(self.database.get_setting("lan_ip", "192.168.88.1"))
            self.gui.username_var.set(self.database.get_setting("username", "root"))
            self.gui.config_path_var.set(self.database.get_setting("config_path", "/root/config"))
            self.gui.result_path_var.set(self.database.get_setting("result_path", "/root/result"))
            
            self.gui.log_message("Configuration loaded successfully")
            
        except Exception as e:
            error_msg = f"Failed to load configuration: {str(e)}"
            self.gui.log_message(error_msg)
            messagebox.showerror("Error", error_msg)
    
    def load_history(self):
        """Load history from database"""
        try:
            if not hasattr(self.gui, 'history_table'):
                return
                
            # Clear existing history
            for item in self.gui.history_table.get_children():
                self.gui.history_table.delete(item)
            
            # Load recent history
            history_data = self.database.get_recent_history(100)
            
            for record in history_data:
                timestamp = record.get("timestamp", "")
                if " " in timestamp:
                    date, time_str = timestamp.split(" ", 1)
                else:
                    date = timestamp
                    time_str = ""
                
                self.gui.history_table.insert("", "end", values=(
                    date,
                    time_str,
                    record.get("file_name", ""),
                    record.get("test_count", 0),
                    record.get("overall_result", "Unknown"),
                    f"Execution time: {record.get('execution_time', 0):.1f}s"
                ))
                
        except Exception as e:
            self.gui.log_message(f"Error loading history: {str(e)}")
    
    def clear_history(self):
        """Clear history with confirmation"""
        confirm = messagebox.askyesno("Confirm", "Clear all history?")
        if confirm:
            try:
                self.database.clear_history()
                if hasattr(self.gui, 'history_table'):
                    for item in self.gui.history_table.get_children():
                        self.gui.history_table.delete(item)
                self.gui.log_message("History cleared")
                messagebox.showinfo("Success", "History cleared successfully")
            except Exception as e:
                messagebox.showerror("Error", f"Failed to clear history: {str(e)}")
    
    def refresh_view(self):
        """Refresh all views"""
        self.load_history()
        self.gui.log_message("View refreshed")
    
    def export_results(self):
        """Export current results to CSV"""
        # Simple implementation
        self.gui.log_message("Export results not implemented yet")
    
    def export_history(self):
        """Export history to CSV"""
        # Simple implementation
        self.gui.log_message("Export history not implemented yet")
    
    def export_logs(self):
        """Export logs to file"""
        # Simple implementation
        self.gui.log_message("Export logs not implemented yet")
    
    def apply_history_filter(self):
        """Apply filters to history view"""
        # Simple implementation
        self.gui.log_message("History filter not implemented yet")
    
    def clear_history_filter(self):
        """Clear history filters"""
        # Simple implementation
        if hasattr(self.gui, 'date_combo'):
            self.gui.date_combo.current(0)
        if hasattr(self.gui, 'status_combo'):
            self.gui.status_combo.current(0)
        self.load_history()
    
    def view_history_details(self):
        """View detailed information for selected history item"""
        # Simple implementation
        self.gui.log_message("View history details not implemented yet")
    
    def clear_logs(self):
        """Clear the log display"""
        if hasattr(self.gui, 'log_text'):
            confirm = messagebox.askyesno("Clear Logs", "Clear all log messages?")
            if confirm:
                self.gui.log_text.delete("1.0", tk.END)
                self.gui.log_message("Log display cleared")
    
    def refresh_logs(self):
        """Refresh the logs display"""
        self.gui.log_message("Logs refreshed")
    
    def show_documentation(self):
        """Show documentation"""
        doc_msg = (
            "Test Case Manager v2.0 (Windows Edition)\n\n"
            "Usage Instructions:\n"
            "1. Configure connection settings\n"
            "2. Test connection to verify access\n"
            "3. Select test files to run\n"
            "4. Click 'Send Files' to run tests\n"
            "5. View results and history"
        )
        messagebox.showinfo("Documentation", doc_msg)
    
    def show_about(self):
        """Show about dialog"""
        about_msg = (
            "Test Case Manager v2.0\n"
            "Windows Edition\n\n"
            "© 2025 juno-kyojin\n\n"
            f"User: {os.environ.get('USERNAME', 'unknown')}"
        )
        messagebox.showinfo("About", about_msg)
