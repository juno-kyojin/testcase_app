#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Module: main.py
# Purpose: Application entry point for Test Case Manager (Windows Edition)
# Last updated: 2025-06-05 by juno-kyojin

import os
import sys
import logging
import tkinter as tk
import sqlite3

# Thêm thư mục hiện tại vào Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
parent_dir = os.path.dirname(current_dir)
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

# Thay đổi cách import
from gui.interface import ApplicationGUI
from network.connection import SSHConnection
from files.manager import TestFileManager
from storage.database import TestDatabase

def ensure_database():
    """Ensure database structure is set up correctly"""
    db_path = "data/history.db"
    os.makedirs(os.path.dirname(db_path), exist_ok=True)
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check if tables exist
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='test_file_results'")
    has_file_table = cursor.fetchone() is not None
    
    if not has_file_table:
        logging.info("Creating test_file_results table")
        cursor.execute('''
        CREATE TABLE test_file_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_name TEXT,
            file_size INTEGER,
            test_count INTEGER,
            timestamp TEXT,
            send_status TEXT,
            overall_result TEXT,
            affects_wan BOOLEAN,
            affects_lan BOOLEAN,
            execution_time REAL,
            target_ip TEXT,
            target_username TEXT
        )
        ''')
    
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='test_case_results'")
    has_case_table = cursor.fetchone() is not None
    
    if not has_case_table:
        logging.info("Creating test_case_results table")
        cursor.execute('''
        CREATE TABLE test_case_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            file_result_id INTEGER,
            service TEXT,
            action TEXT,
            status TEXT,
            details TEXT,
            execution_time REAL,
            FOREIGN KEY (file_result_id) REFERENCES test_file_results (id)
        )
        ''')
    
    conn.commit()
    conn.close()
    logging.info("Database structure verified")

def setup_directories():
    """Setup required directories"""
    directories = [
        "data",
        "data/temp",
        "data/temp/results",
        "logs"
    ]
    
    for directory in directories:
        os.makedirs(directory, exist_ok=True)

def setup_logging():
    """Setup basic logging configuration"""
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
    
    logger = logging.getLogger(__name__)
    logger.info("Test Case Manager (Windows Edition) starting up...")

def check_windows():
    """Verify running on Windows"""
    import platform
    if platform.system().lower() != "windows":
        print("Error: This application is designed to run on Windows only.")
        print("Current platform:", platform.system())
        sys.exit(1)

def configure_logging(log_file="data/app_log.txt"):
    """Configure logging with proper encoding for Vietnamese characters"""
    import logging
    import sys
    
    # Đảm bảo thư mục tồn tại
    import os
    os.makedirs(os.path.dirname(log_file), exist_ok=True)
    
    # Cấu hình logging
    log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # File handler với UTF-8 encoding
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setFormatter(log_formatter)
    
    # Stream handler với UTF-8 encoding cho console (nếu console hỗ trợ)
    try:
        # Cố gắng thiết lập UTF-8 cho console Windows
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleCP(65001)
        kernel32.SetConsoleOutputCP(65001)
    except:
        pass
    
    # Tạo stream handler với encoding phù hợp
    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(log_formatter)
    stream_handler.setLevel(logging.INFO)
    
    # Lớp bọc an toàn cho StreamHandler để tránh lỗi Unicode
    class SafeStreamHandler(logging.StreamHandler):
        def emit(self, record):
            try:
                super().emit(record)
            except UnicodeEncodeError:
                msg = record.getMessage()
                try:
                    # Cố gắng encode bằng ASCII với thay thế
                    safe_msg = msg.encode('ascii', 'replace').decode('ascii')
                    record.msg = safe_msg
                    record.args = ()
                    super().emit(record)
                except:
                    pass  # Bỏ qua nếu vẫn không thể ghi log
    
    # Sử dụng SafeStreamHandler thay cho StreamHandler
    safe_console = SafeStreamHandler()
    safe_console.setFormatter(log_formatter)
    
    # Cấu hình root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(safe_console)
    
    return root_logger

def main():
    """Main application entry point"""
    try:
        # Check if running on Windows
        check_windows()
        
        # Setup required directories
        setup_directories()
        
        # Initialize logging with Unicode support
        configure_logging()  # Thay thế setup_logging() bằng configure_logging()
        
        # Đảm bảo database được khởi tạo đúng cách
        ensure_database()
        
        # Start GUI
        root = tk.Tk()
        app = ApplicationGUI(root)
        root.mainloop()
        
    except Exception as e:
        logging.error(f"Failed to start application: {e}")
        print(f"Error starting application: {e}")
        sys.exit(1)
        
if __name__ == "__main__":
    main()