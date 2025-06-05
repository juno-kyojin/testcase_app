#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Module: connection_handler.py
# Purpose: Handle SSH connections for Test Case Manager
# Last updated: 2025-06-05 by juno-kyojin

import time
import threading
from typing import Tuple, List

class ConnectionHandler:
    def __init__(self, gui):
        self.gui = gui
        self.ssh_connection = gui.ssh_connection
    
    def test_connection(self):
        """Test SSH connection to remote device"""
        if not self.gui.validate_connection_fields():
            return
            
        # Update UI
        self.gui.connection_status.set("Connecting...")
        self.gui.update_status_circle("yellow")
        
        # Start connection test in background thread
        threading.Thread(target=self._run_connection_test, daemon=True).start()
    
    def _run_connection_test(self):
        """Run actual connection test in background"""
        try:
            hostname = self.gui.lan_ip_var.get()
            username = self.gui.username_var.get()
            password = self.gui.password_var.get()
            
            self.gui.log_connection(f"Testing connection to {hostname}...")
            
            # Ensure we're disconnected first
            self.ssh_connection.disconnect()
            
            # Try to connect with retries
            max_attempts = 3
            for attempt in range(1, max_attempts + 1):
                self.gui.log_connection(f"Connection attempt {attempt}/{max_attempts}...")
                
                success = self.ssh_connection.connect(
                    hostname=hostname,
                    username=username,
                    password=password,
                    timeout=10
                )
                
                if success:
                    break
                    
                if attempt < max_attempts:
                    time.sleep(1)  # Wait before retry
            
            # If not connected after all attempts
            if not self.ssh_connection.is_connected():
                self.gui.root.after(0, lambda: self.gui.connection_status.set("Connection Failed"))
                self.gui.root.after(0, lambda: self.gui.update_status_circle("red"))
                self.gui.log_error("Connection failed after multiple attempts")
                return
            
            # Verify required paths exist
            paths_exist = self.check_remote_folders()
            
            if paths_exist:
                self.gui.root.after(0, lambda: self.gui.connection_status.set("Connected"))
                self.gui.root.after(0, lambda: self.gui.update_status_circle("green"))
                self.gui.log_connection("Connection successful - All systems ready")
            else:
                self.gui.root.after(0, lambda: self.gui.connection_status.set("Path Error"))
                self.gui.root.after(0, lambda: self.gui.update_status_circle("yellow"))
                self.gui.log_error("Connection OK but required paths are missing")
            
        except Exception as e:
            self.gui.root.after(0, lambda: self.gui.connection_status.set("Error"))
            self.gui.root.after(0, lambda: self.gui.update_status_circle("red"))
            self.gui.log_error(f"Connection test error: {str(e)}")
    
    def check_remote_folders(self) -> bool:
        """Check if required remote folders exist"""
        try:
            if not self.gui.validate_connection_fields():
                return False
                
            if not self.ssh_connection.is_connected():
                hostname = self.gui.lan_ip_var.get()
                username = self.gui.username_var.get()
                password = self.gui.password_var.get()
                
                success = self.ssh_connection.connect(
                    hostname=hostname,
                    username=username,
                    password=password,
                    timeout=10
                )
                
                if not success:
                    self.gui.log_error("Cannot check folders: SSH connection failed")
                    return False
            
            # Check required paths
            config_path = self.gui.config_path_var.get()
            result_path = self.gui.result_path_var.get()
            
            # Verify config path exists
            cmd_config = f"test -d {config_path} && echo 'exists' || echo 'missing'"
            success, output, _ = self.ssh_connection.execute_command(cmd_config)
            config_exists = success and output.strip() == "exists"
            
            if not config_exists:
                self.gui.log_error(f"Config path does not exist: {config_path}")
                # Try to create it
                cmd_mkdir = f"mkdir -p {config_path}"
                success, _, _ = self.ssh_connection.execute_command(cmd_mkdir)
                if success:
                    self.gui.log_connection(f"Created missing config directory: {config_path}")
                    config_exists = True
                else:
                    self.gui.log_error(f"Failed to create config directory: {config_path}")
            
            # Verify result path exists
            cmd_result = f"test -d {result_path} && echo 'exists' || echo 'missing'"
            success, output, _ = self.ssh_connection.execute_command(cmd_result)
            result_exists = success and output.strip() == "exists"
            
            if not result_exists:
                self.gui.log_error(f"Result path does not exist: {result_path}")
                # Try to create it
                cmd_mkdir = f"mkdir -p {result_path}"
                success, _, _ = self.ssh_connection.execute_command(cmd_mkdir)
                if success:
                    self.gui.log_connection(f"Created missing result directory: {result_path}")
                    result_exists = True
                else:
                    self.gui.log_error(f"Failed to create result directory: {result_path}")
            
            # Log result
            if config_exists and result_exists:
                self.gui.log_connection("All remote paths verified")
                return True
            else:
                missing = []
                if not config_exists:
                    missing.append(f"config path ({config_path})")
                if not result_exists:
                    missing.append(f"result path ({result_path})")
                    
                self.gui.log_error(f"Missing remote paths: {', '.join(missing)}")
                return False
            
        except Exception as e:
            self.gui.log_error(f"Error checking remote folders: {str(e)}")
            return False

    def get_remote_file_list(self, remote_dir: str) -> List[str]:
        """Get list of files in a remote directory"""
        try:
            if not self.ssh_connection.is_connected():
                self.gui.log_error("Cannot get file list: SSH connection not established")
                return []
                
            cmd = f"ls -la {remote_dir} 2>/dev/null || echo 'Error: Directory not found'"
            success, output, _ = self.ssh_connection.execute_command(cmd)
            
            if not success or "Error:" in output:
                self.gui.log_error(f"Failed to list directory {remote_dir}")
                return []
                
            # Parse ls output
            files = []
            for line in output.splitlines():
                if line.startswith("total") or not line.strip():
                    continue
                parts = line.split()
                if len(parts) >= 9:
                    file_name = " ".join(parts[8:])
                    if file_name not in [".", ".."]:
                        files.append(file_name)
            
            return files
            
        except Exception as e:
            self.gui.log_error(f"Error getting remote file list: {str(e)}")
            return []