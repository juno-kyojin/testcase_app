#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Module: utils.py  
# Purpose: Utility functions for Test Case Manager GUI
# Last updated: 2025-06-05 by juno-kyojin

import os
import time
import datetime
import csv
import tkinter as tk
from tkinter import messagebox, filedialog, ttk
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
                self.gui.log_debug(f"Cleaned up {cleaned_count} old temporary files")
                
        except Exception as e:
            self.gui.log_error(f"Cleanup failed: {e}")
    
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
            self.gui.log_error(f"Error updating file status: {e}")
    
    def update_detail_table_with_results(self, file_index: int, result_data: dict):
        """Update detail table with test results"""
        try:
            if not hasattr(self.gui, 'detail_table'):
                return
            
            # Clear existing details
            for item in self.gui.detail_table.get_children():
                self.gui.detail_table.delete(item)
                
            # Add results if available
            test_results = result_data.get("test_results", [])
            
            if not test_results:
                # Handle case without test_results array
                service = result_data.get("service", "unknown")
                action = result_data.get("action", "")
                status = result_data.get("overall_result", "Unknown")
                details = result_data.get("details", "")
                
                item_id = self.gui.detail_table.insert("", "end", values=(
                    service,
                    action,
                    "",  # parameters
                    status,
                    details
                ))
                
                # Add color based on status
                if "Pass" in status:
                    self.gui.detail_table.tag_configure("pass", background="#e8f5e9")
                    self.gui.detail_table.item(item_id, tags=("pass",))
                elif "Fail" in status:
                    self.gui.detail_table.tag_configure("fail", background="#ffebee")
                    self.gui.detail_table.item(item_id, tags=("fail",))
                    
                return
                
            for result in test_results:
                service = result.get("service", "")
                action = result.get("action", "")
                status = result.get("status", "unknown")
                details = result.get("details", "")
                parameters = result.get("parameters", "")
                
                # Format status
                status_text = status.capitalize()
                
                item_id = self.gui.detail_table.insert("", "end", values=(
                    service,
                    action,
                    parameters,
                    status_text,
                    details
                ))
                
                # Add color based on status
                if status.lower() == "pass":
                    self.gui.detail_table.tag_configure("pass", background="#e8f5e9")
                    self.gui.detail_table.item(item_id, tags=("pass",))
                elif status.lower() == "fail":
                    self.gui.detail_table.tag_configure("fail", background="#ffebee")
                    self.gui.detail_table.item(item_id, tags=("fail",))
                
        except Exception as e:
            self.gui.log_error(f"Error updating detail table: {str(e)}")
    
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
            self.gui.log_error(error_msg)
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
            self.gui.log_error(error_msg)
            messagebox.showerror("Error", error_msg)
    
    def load_history(self):
        """Load history from database with timezone conversion"""
        try:
            if not hasattr(self.gui, 'history_table'):
                return
                
            # Clear existing history
            for item in self.gui.history_table.get_children():
                self.gui.history_table.delete(item)
            
            # Kiểm tra database có bảng nào
            import sqlite3
            conn = sqlite3.connect("data/history.db")
            cursor = conn.cursor()
            
            # Kiểm tra các bảng trong database
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [t[0] for t in cursor.fetchall()]
            self.gui.log_debug(f"Database tables: {', '.join(tables)}")
            
            # Chọn bảng phù hợp
            if "test_results" in tables:
                table_name = "test_results"
            elif "test_file_results" in tables:
                table_name = "test_file_results"
            else:
                self.gui.log_message("No history tables found in database")
                conn.close()
                return
                
            # Debug: kiểm tra cột của bảng
            cursor.execute(f"PRAGMA table_info({table_name})")
            columns = [c[1] for c in cursor.fetchall()]
            self.gui.log_debug(f"Table {table_name} columns: {', '.join(columns)}")
            
            # Load recent history
            cursor.execute(f"SELECT * FROM {table_name} ORDER BY timestamp DESC LIMIT 100")
            history_data = cursor.fetchall()
            
            # Get column names
            column_names = [d[0] for d in cursor.description]
            
            # Find indexes of columns we need
            timestamp_idx = column_names.index("timestamp") if "timestamp" in column_names else 0
            file_name_idx = column_names.index("file_name") if "file_name" in column_names else 1
            test_count_idx = column_names.index("test_count") if "test_count" in column_names else 2
            result_idx = column_names.index("overall_result") if "overall_result" in column_names else 3
            time_idx = column_names.index("execution_time") if "execution_time" in column_names else 4
            wan_idx = column_names.index("affects_wan") if "affects_wan" in column_names else 5
            lan_idx = column_names.index("affects_lan") if "affects_lan" in column_names else 6
            
            for record in history_data:
                # Chuyển đổi timestamp từ UTC sang múi giờ địa phương
                timestamp = record[timestamp_idx] if timestamp_idx < len(record) else ""
                local_timestamp = self.convert_to_local_time(timestamp)
                
                if " " in local_timestamp:
                    date, time_str = local_timestamp.split(" ", 1)
                else:
                    date = local_timestamp
                    time_str = ""
                
                # Lấy kết quả tổng thể, đảm bảo không là None
                overall_result = record[result_idx] if result_idx < len(record) and record[result_idx] else "Unknown"
                
                # Tạo thông tin chi tiết
                exec_time = record[time_idx] if time_idx < len(record) else 0
                affects_wan = record[wan_idx] if wan_idx < len(record) else False
                affects_lan = record[lan_idx] if lan_idx < len(record) else False
                
                details = f"Execution time: {exec_time:.1f}s"
                if affects_wan or affects_lan:
                    details += " (Network affecting)"
                
                self.gui.history_table.insert("", "end", values=(
                    date,
                    time_str,
                    record[file_name_idx] if file_name_idx < len(record) else "",
                    record[test_count_idx] if test_count_idx < len(record) else 0,
                    overall_result,
                    details
                ))
            
            conn.close()
                
        except Exception as e:
            self.gui.log_error(f"Error loading history: {str(e)}")

    def convert_to_local_time(self, utc_timestamp):
        """Convert UTC timestamp to local timezone (UTC+7)"""
        try:
            import datetime
            
            if not utc_timestamp:
                return ""
                
            # Phân tích chuỗi thời gian UTC
            if " " in utc_timestamp:
                utc_dt = datetime.datetime.strptime(utc_timestamp, "%Y-%m-%d %H:%M:%S")
            else:
                # Nếu chỉ có ngày không có giờ
                utc_dt = datetime.datetime.strptime(utc_timestamp, "%Y-%m-%d")
                
            # Thêm thông tin múi giờ (UTC)
            utc_dt = utc_dt.replace(tzinfo=datetime.timezone.utc)
            
            # Chuyển đổi sang múi giờ địa phương
            local_tz = datetime.timezone(datetime.timedelta(hours=7))  # UTC+7
            local_dt = utc_dt.astimezone(local_tz)
            
            # Format theo định dạng ban đầu
            if " " in utc_timestamp:
                return local_dt.strftime("%Y-%m-%d %H:%M:%S")
            else:
                return local_dt.strftime("%Y-%m-%d")
                
        except Exception as e:
            self.gui.log_error(f"Error converting timestamp: {str(e)}")
            return utc_timestamp  # Trả về giá trị ban đầu nếu có lỗi
    
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
        if not hasattr(self.gui, 'file_table'):
            return
            
        file_path = filedialog.asksaveasfilename(
            defaultextension=".csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
            initialfile="test_results.csv"
        )
        
        if not file_path:
            return
            
        try:
            with open(file_path, 'w', newline='') as csvfile:
                fieldnames = ['File', 'Type', 'Size', 'Status', 'Result', 'Time']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for item in self.gui.file_table.get_children():
                    values = self.gui.file_table.item(item, "values")
                    if len(values) >= 6:
                        writer.writerow({
                            'File': values[0],
                            'Type': values[1],
                            'Size': values[2],
                            'Status': values[3],
                            'Result': values[4],
                            'Time': values[5]
                        })
                
            self.gui.log_result(f"Results exported to {file_path}")
            messagebox.showinfo("Export Complete", f"Results exported to {file_path}")
            
        except Exception as e:
            self.gui.log_error(f"Error exporting results: {str(e)}")
            messagebox.showerror("Export Error", f"Failed to export results: {str(e)}")
    
    def export_history(self):
        """Export history to CSV file"""
        try:
            if not hasattr(self.gui, 'history_table'):
                return
                
            file_path = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
                initialfile="test_history.csv"
            )
            
            if not file_path:
                return
                
            # Get all items from history table
            all_items = self.gui.history_table.get_children()
            if not all_items:
                messagebox.showinfo("No Data", "No history data to export")
                return
            
            with open(file_path, 'w', newline='') as csvfile:
                fieldnames = ['Date', 'Time', 'File Name', 'Test Count', 'Result', 'Details']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for item in all_items:
                    values = self.gui.history_table.item(item, "values")
                    if len(values) >= 6:
                        writer.writerow({
                            'Date': values[0],
                            'Time': values[1],
                            'File Name': values[2],
                            'Test Count': values[3],
                            'Result': values[4],
                            'Details': values[5]
                        })
                    
            self.gui.log_result(f"History exported to {file_path}")
            messagebox.showinfo("Export Complete", f"History data exported to {file_path}")
            
        except Exception as e:
            self.gui.log_error(f"Error exporting history: {str(e)}")
            messagebox.showerror("Export Error", f"Failed to export history: {str(e)}")
    
    def export_logs(self):
        """Export logs to file"""
        try:
            if not hasattr(self.gui, 'log_text'):
                return
                
            file_path = filedialog.asksaveasfilename(
                defaultextension=".log",
                filetypes=[("Log files", "*.log"), ("Text files", "*.txt"), ("All files", "*.*")],
                initialfile=f"app_log_{time.strftime('%Y%m%d_%H%M%S')}.log"
            )
            
            if not file_path:
                return
                
            log_content = self.gui.log_text.get("1.0", tk.END)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(log_content)
                
            self.gui.log_result(f"Logs exported to {file_path}")
            messagebox.showinfo("Export Complete", f"Logs exported to {file_path}")
            
        except Exception as e:
            self.gui.log_error(f"Error exporting logs: {str(e)}")
            messagebox.showerror("Export Error", f"Failed to export logs: {str(e)}")
    
    def apply_history_filter(self):
        """Apply filters to history view"""
        try:
            if not hasattr(self.gui, 'history_table') or not hasattr(self.gui, 'date_combo') or not hasattr(self.gui, 'status_combo'):
                return
            
            # Clear existing history
            for item in self.gui.history_table.get_children():
                self.gui.history_table.delete(item)
            
            # Get filter values
            date_filter = self.gui.date_combo.get()
            status_filter = self.gui.status_combo.get()
            
            # Debug current filters
            self.gui.log_debug(f"Applying filter - Date: {date_filter}, Status: {status_filter}")
            
            # Connect to database
            import sqlite3
            conn = sqlite3.connect("data/history.db")
            cursor = conn.cursor()
            
            # Check which tables exist
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = [t[0] for t in cursor.fetchall()]
            
            # Select appropriate table
            if "test_results" in tables:
                table_name = "test_results"
            elif "test_file_results" in tables:
                table_name = "test_file_results"
            else:
                self.gui.log_message("No history tables found in database")
                conn.close()
                return
                
            # Get date range based on filter
            date_condition = ""
            params = []
            
            import datetime
            today = datetime.datetime.now().strftime("%Y-%m-%d")
            
            if date_filter == "Today":
                date_condition = f"WHERE {table_name}.timestamp LIKE ?"
                params.append(f"{today}%")
            elif date_filter == "Last 7 Days":
                date_condition = f"WHERE {table_name}.timestamp >= date('now', '-7 days')"
            elif date_filter == "Last 30 Days":
                date_condition = f"WHERE {table_name}.timestamp >= date('now', '-30 days')"
            
            # Add status filter if needed
            if status_filter != "All":
                if date_condition:
                    date_condition += " AND "
                else:
                    date_condition = "WHERE "
                
                date_condition += f"{table_name}.overall_result LIKE ?"
                params.append(f"%{status_filter}%")
            
            # Get filtered history
            query = f"""
            SELECT timestamp, file_name, test_count, overall_result, execution_time, 
                   affects_wan, affects_lan
            FROM {table_name}
            {date_condition}
            ORDER BY timestamp DESC
            """
            
            self.gui.log_debug(f"Executing filter query: {query} with params: {params}")
            cursor.execute(query, params)
            history_data = cursor.fetchall()
            
            # Debug count
            self.gui.log_debug(f"Filter query returned {len(history_data)} records")
            
            # Display filtered data
            for record in history_data:
                timestamp = record[0]
                if " " in timestamp:
                    date, time_str = timestamp.split(" ", 1)
                else:
                    date = timestamp
                    time_str = ""
                
                # Ensure overall_result is not None
                overall_result = record[3] if record[3] is not None else "Unknown"
                
                details = f"Execution time: {record[4]:.1f}s"
                if record[5] or record[6]:  # affects_wan or affects_lan
                    details += " (Network affecting)"
                
                self.gui.history_table.insert("", "end", values=(
                    date,
                    time_str,
                    record[1],  # file_name
                    record[2],  # test_count
                    overall_result,  # overall_result
                    details
                ))
            
            conn.close()
            
            filtered_count = len(self.gui.history_table.get_children())
            self.gui.log_result(f"Filtered history: showing {filtered_count} records")
            
        except Exception as e:
            self.gui.log_error(f"Error applying history filter: {str(e)}")
    
    def clear_history_filter(self):
        """Clear history filters"""
        if hasattr(self.gui, 'date_combo'):
            self.gui.date_combo.current(0)
        if hasattr(self.gui, 'status_combo'):
            self.gui.status_combo.current(0)
        self.load_history()
        self.gui.log_result("History filters cleared")
    
    def view_history_details(self):
        """View detailed information for selected history item"""
        try:
            import tkinter as tk
            from tkinter import ttk

            if not hasattr(self.gui, 'history_table'):
                return
                
            selection = self.gui.history_table.selection()
            if not selection:
                messagebox.showinfo("No Selection", "Please select a history item to view details")
                return
                
            item = selection[0]
            values = self.gui.history_table.item(item, "values")
            
            if len(values) < 3:
                messagebox.showinfo("Error", "Invalid history item selected")
                return
            
            # Lấy chỉ tên file để tìm kiếm, không dùng timestamp
            file_name = values[2]
            
            # Chỉ sử dụng file_name để tìm kiếm (lấy bản ghi gần nhất)
            test_details = self.database.get_test_details(file_name)
            
            if not test_details:
                messagebox.showinfo("No Details", f"No detailed information found for {file_name}")
                return
            
            # Lấy thông tin ngày và giờ
            date_str = values[0] if len(values) > 0 else ""
            time_str = values[1] if len(values) > 1 else ""
            
            # Create details window
            details_window = tk.Toplevel(self.gui.root)
            details_window.title(f"Test Details: {file_name}")
            details_window.geometry("800x600")
            details_window.minsize(600, 400)
            
            # Set icon if available
            try:
                details_window.iconbitmap("assets/app_icon.ico")
            except:
                pass
                
            # Basic info frame
            info_frame = ttk.LabelFrame(details_window, text="Test Information")
            info_frame.pack(fill=tk.X, padx=10, pady=5)
            
            # Info grid
            ttk.Label(info_frame, text="File:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
            ttk.Label(info_frame, text=file_name, font=("Segoe UI", 9, "bold")).grid(row=0, column=1, sticky=tk.W, padx=5, pady=2)
            
            ttk.Label(info_frame, text="Date:").grid(row=0, column=2, sticky=tk.W, padx=5, pady=2)
            ttk.Label(info_frame, text=f"{date_str} {time_str}").grid(row=0, column=3, sticky=tk.W, padx=5, pady=2)
            
            ttk.Label(info_frame, text="Result:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
            result_text = values[4] if len(values) > 4 else "Unknown"
            result_label = ttk.Label(info_frame, text=result_text, font=("Segoe UI", 9, "bold"))
            result_label.grid(row=1, column=1, sticky=tk.W, padx=5, pady=2)
            
            # Set color based on result
            if "Pass" in result_text:
                result_label.configure(foreground="green")
            elif "Fail" in result_text:
                result_label.configure(foreground="red")
            
            ttk.Label(info_frame, text="Test Count:").grid(row=1, column=2, sticky=tk.W, padx=5, pady=2)
            ttk.Label(info_frame, text=values[3] if len(values) > 3 else "Unknown").grid(row=1, column=3, sticky=tk.W, padx=5, pady=2)
            
            # Details table frame
            details_frame = ttk.LabelFrame(details_window, text="Test Case Details")
            details_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=5)
            
            # Create table
            columns = ("service", "action", "status", "details", "time")
            details_table = ttk.Treeview(details_frame, columns=columns, show="headings")
            
            details_table.heading("service", text="Service")
            details_table.heading("action", text="Action")
            details_table.heading("status", text="Status")
            details_table.heading("details", text="Details")
            details_table.heading("time", text="Execution Time")
            
            details_table.column("service", width=100)
            details_table.column("action", width=100)
            details_table.column("status", width=80)
            details_table.column("details", width=350)
            details_table.column("time", width=100)
            
            # Add vertical scrollbar
            scrollbar = ttk.Scrollbar(details_frame, orient=tk.VERTICAL, command=details_table.yview)
            details_table.configure(yscrollcommand=scrollbar.set)
            
            details_table.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
            scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
            
            # Fill the table with data
            for detail in test_details:
                status = detail.get("status", "unknown")
                status_text = status.capitalize()
                
                # Format execution time
                exec_time = detail.get("execution_time", 0)
                time_text = f"{exec_time:.2f}s" if exec_time else ""
                
                item_id = details_table.insert("", "end", values=(
                    detail.get("service", ""),
                    detail.get("action", ""),
                    status_text,
                    detail.get("details", ""),
                    time_text
                ))
                
                # Set row colors based on status
                if status.lower() == "pass":
                    details_table.tag_configure("pass", background="#e8f5e9")
                    details_table.item(item_id, tags=("pass",))
                elif status.lower() == "fail":
                    details_table.tag_configure("fail", background="#ffebee")
                    details_table.item(item_id, tags=("fail",))
            
            # Bottom buttons
            btn_frame = ttk.Frame(details_window)
            btn_frame.pack(fill=tk.X, padx=10, pady=10)
            
            ttk.Button(
                btn_frame, 
                text="Export Details", 
                command=lambda: self.export_test_details(file_name, test_details)
            ).pack(side=tk.LEFT, padx=5)
            
            ttk.Button(
                btn_frame, 
                text="Close", 
                command=details_window.destroy
            ).pack(side=tk.RIGHT, padx=5)
            
            # Make window modal
            details_window.transient(self.gui.root)
            details_window.grab_set()
            self.gui.root.wait_window(details_window)
            
        except Exception as e:
            self.gui.log_error(f"Error viewing history details: {str(e)}")
            messagebox.showerror("Error", f"Failed to display details: {str(e)}")
    
    def export_test_details(self, file_name, test_details):
        """Export test details to CSV file"""
        try:
            file_path = filedialog.asksaveasfilename(
                defaultextension=".csv",
                filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
                initialfile=f"{file_name}_details.csv"
            )
            
            if not file_path:
                return
                
            with open(file_path, 'w', newline='', encoding='utf-8') as csvfile:
                fieldnames = ['Service', 'Action', 'Status', 'Details', 'Execution Time (s)']
                writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
                
                writer.writeheader()
                for detail in test_details:
                    writer.writerow({
                        'Service': detail.get("service", ""),
                        'Action': detail.get("action", ""),
                        'Status': detail.get("status", "").capitalize(),
                        'Details': detail.get("details", ""),
                        'Execution Time (s)': f"{detail.get('execution_time', 0):.2f}"
                    })
                    
            self.gui.log_result(f"Test details exported to {file_path}")
            messagebox.showinfo("Export Complete", f"Test details exported to {file_path}")
            
        except Exception as e:
            self.gui.log_error(f"Error exporting test details: {str(e)}")
            messagebox.showerror("Export Error", f"Failed to export details: {str(e)}")
    
    def filter_logs(self):
        """Filter logs based on selected log level"""
        if not hasattr(self.gui, 'log_text') or not hasattr(self.gui, 'log_level_var'):
            return
            
        selected_level = self.gui.log_level_var.get()
        
        if selected_level == "All":
            # Reload all logs
            self.refresh_logs()
            return
        
        # Map level name to emoji/prefix
        level_prefix = {
            "Connection": "🔌 CONNECTION:",
            "File": "📄 FILE:",
            "Result": "✅ RESULT:",
            "Error": "❌ ERROR:",
            "Debug": "🔍 DEBUG:",
        }
        
        # Get current log content
        log_content = self.gui.log_text.get("1.0", tk.END)
        
        # Clear current content
        self.gui.log_text.delete("1.0", tk.END)
        
        # Filter and re-insert relevant lines
        for line in log_content.splitlines():
            if level_prefix.get(selected_level, "") in line:
                self.gui.log_text.insert(tk.END, line + "\n")
        
        # Scroll to end
        self.gui.log_text.see(tk.END)
        
        self.gui.log_debug(f"Log filtered to show only {selected_level} entries")
    
    def clear_logs(self):
        """Clear the log display"""
        if hasattr(self.gui, 'log_text'):
            confirm = messagebox.askyesno("Clear Logs", "Clear all log messages?")
            if confirm:
                self.gui.log_text.delete("1.0", tk.END)
                self.gui.log_message("Log display cleared")
    
    def refresh_logs(self):
        """Refresh the logs display"""
        # This method currently just logs a message
        # In the future, it could reload logs from a file
        self.gui.log_message("Logs refreshed")
    
    def debug_database(self):
        """Debug database structure and content"""
        try:
            import sqlite3
            conn = sqlite3.connect("data/history.db")
            cursor = conn.cursor()
            
            # Get list of tables
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            
            self.gui.log_debug("Database tables: " + ', '.join([t[0] for t in tables]))
            
            # Get columns for each table
            for table in tables:
                table_name = table[0]
                cursor.execute(f"PRAGMA table_info({table_name})")
                columns = cursor.fetchall()
                column_names = [col[1] for col in columns]
                self.gui.log_debug(f"Table {table_name} columns: {', '.join(column_names)}")
                
            # Get recent records from relevant tables
            for table_name in ["test_results", "test_file_results"]:
                if table_name in [t[0] for t in tables]:
                    cursor.execute(f"SELECT file_name, overall_result FROM {table_name} ORDER BY id DESC LIMIT 5")
                    records = cursor.fetchall()
                    self.gui.log_debug(f"Recent {table_name} records:")
                    for rec in records:
                        self.gui.log_debug(f"  {rec[0]}: {rec[1]}")
                
            conn.close()
            
            self.gui.log_message("Database analysis complete")
        except Exception as e:
            self.gui.log_error(f"Error checking database structure: {str(e)}")
    
    def show_documentation(self):
        """Show documentation"""
        doc_msg = (
            "Test Case Manager v2.0 (Windows Edition)\n\n"
            "Usage Instructions:\n"
            "1. Configure connection settings\n"
            "2. Test connection to verify access\n"
            "3. Select test files to run\n"
            "4. Click 'Send Files' to run tests\n"
            "5. View results and history\n\n"
            "Log Types:\n"
            "🔌 CONNECTION - Connection status and events\n"
            "📄 FILE - File operations and processing\n"
            "✅ RESULT - Test results and outcomes\n"
            "❌ ERROR - Error messages\n"
            "🔍 DEBUG - Detailed debug information"
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