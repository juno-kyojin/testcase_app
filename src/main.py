#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Module: main.py
# Purpose: Application entry point for Test Case Manager (Windows Edition)
# Last updated: 2025-06-02 by juno-kyojin

import os
import sys
import logging
import tkinter as tk

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

def main():
    """Main application entry point"""
    try:
        # Check if running on Windows
        check_windows()
        
        # Setup required directories
        setup_directories()
        
        # Initialize logging
        setup_logging()
        
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