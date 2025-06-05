#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Module: result_handler.py
# Purpose: Handle test result files for Test Case Manager
# Last updated: 2025-06-05 by juno-kyojin

import os
import time
from typing import Tuple, Optional

class ResultHandler:
    def __init__(self, gui):
        self.gui = gui
        self.ssh_connection = gui.ssh_connection
    
    def wait_for_result_file(self, base_filename: str, result_dir: str, upload_time: float, 
                        timeout: int = 120, is_network_test: bool = False) -> Tuple[str, str]:
        """Wait for result file using more compatible commands with reconnection handling"""
        start_wait = time.time()
        check_interval = 3
        last_log_time = 0
        reconnect_attempts = 0
        max_reconnect_attempts = 3
        upload_timestamp = time.strftime("%Y%m%d_%H%M%S", time.localtime(upload_time))
        
        self.gui.log_result(f"Waiting for result file in {result_dir} (timeout: {timeout}s)")
        
        # Create a timestamp that's slightly before our upload time to catch any files created around same time
        base_name = os.path.splitext(base_filename)[0]
        pattern = f"{base_name}_*.json"
        self.gui.log_result(f"Looking for result file matching: {pattern}")
        
        # Get initial files
        cmd = f"find {result_dir} -name '{pattern}' -type f 2>/dev/null || echo ''"
        success, initial_files_str, _ = self.ssh_connection.execute_command(cmd)
        initial_files = set(initial_files_str.strip().split('\n') if initial_files_str.strip() else [])
        
        # Log initial state
        self.gui.log_debug(f"Initial file count: {len(initial_files)}")
        if initial_files:
            sample_files = sorted(list(initial_files))[-3:]  # Get last 3 files
            self.gui.log_debug(f"Initial files: {', '.join([os.path.basename(f) for f in sample_files])}")
        
        # Get timestamp of the latest existing file for the test
        latest_timestamp = None
        if initial_files:
            try:
                latest_file = sorted(list(initial_files))[-1]
                file_name = os.path.basename(latest_file)
                # Extract timestamp from filename (format: base_20250605_141606.json)
                parts = file_name.split('_')
                if len(parts) >= 3:
                    latest_timestamp = f"{parts[-2]}_{parts[-1].split('.')[0]}"
                    self.gui.log_debug(f"Latest existing file timestamp: {latest_timestamp}")
            except Exception as e:
                self.gui.log_error(f"Error extracting timestamp: {str(e)}")
        
        while time.time() - start_wait < timeout:
            elapsed = time.time() - start_wait
            
            try:
                # Kiểm tra kết nối trước khi thực hiện lệnh
                if not self.ssh_connection.is_connected():
                    self.gui.log_error("SSH connection lost. Attempting to reconnect...")
                    self.gui.status_summary.set("Connection lost. Attempting to reconnect...")
                    self.gui.update_status_circle("yellow")
                    
                    if reconnect_attempts >= max_reconnect_attempts:
                        raise Exception(f"Failed to reconnect after {max_reconnect_attempts} attempts")
                    
                    reconnect_attempts += 1
                    success = self.ssh_connection.connect(
                        self.gui.lan_ip_var.get(),
                        self.gui.username_var.get(),
                        self.gui.password_var.get()
                    )
                    
                    if not success:
                        self.gui.log_error(f"Reconnect attempt {reconnect_attempts}/{max_reconnect_attempts} failed")
                        self.gui.status_summary.set(f"Reconnect attempt {reconnect_attempts}/{max_reconnect_attempts} failed")
                        time.sleep(5)  # Đợi lâu hơn trước khi thử lại
                        continue
                    else:
                        self.gui.log_result(f"Reconnected successfully, continuing to wait for result file")
                        self.gui.status_summary.set("Reconnected successfully. Waiting for result...")
                        self.gui.update_status_circle("green")
                
                # Look for newer files - use ls with timestamp sorting
                cmd = f"ls -lt {result_dir}/{pattern} 2>/dev/null | head -1"
                success, newest_file_info, _ = self.ssh_connection.execute_command(cmd)
                
                if not success or not newest_file_info.strip():
                    time.sleep(check_interval)
                    continue
                    
                # Extract filename from ls output (format varies by system)
                # Typically: -rw-r--r-- 1 root root 1234 Jun 5 14:37 filename.json
                parts = newest_file_info.strip().split()
                newest_file = parts[-1]  # Last part should be filename
                full_path = os.path.join(result_dir, newest_file)
                
                # Check if this is a new file by comparing filename
                is_new_file = full_path not in initial_files
                
                # Or check by timestamp in filename
                timestamp_in_name = None
                try:
                    name_parts = newest_file.split('_')
                    if len(name_parts) >= 3:
                        timestamp_in_name = f"{name_parts[-2]}_{name_parts[-1].split('.')[0]}"
                        
                        # Compare with latest timestamp from initial scan
                        if latest_timestamp and timestamp_in_name > latest_timestamp:
                            is_new_file = True
                            self.gui.log_debug(f"Found newer timestamp: {timestamp_in_name} > {latest_timestamp}")
                except Exception:
                    pass
                    
                if is_new_file:
                    self.gui.log_result(f"Found potential new result file: {full_path}")
                    
                    # Verify file is ready
                    self.gui.log_result(f"Waiting for file to stabilize...")
                    time.sleep(2)
                    
                    if self._verify_file_ready(full_path):
                        self.gui.log_result(f"New result file confirmed: {full_path}")
                        self.gui.status_summary.set("Result file found. Processing results...")
                        return full_path, newest_file
                
            except Exception as e:
                self.gui.log_error(f"Error checking for result file: {str(e)}")
                # Đánh dấu kết nối có thể đã mất để lần lặp tiếp theo sẽ thử kết nối lại
                self.ssh_connection.connected = False
                time.sleep(check_interval)
                continue
            
            # Log progress periodically
            if elapsed - last_log_time >= 15:
                self.gui.log_result(f"[{int(elapsed)}s] Still waiting for result file...")
                last_log_time = elapsed
                
                # Cập nhật UI để người dùng biết ứng dụng vẫn đang hoạt động
                self.gui.status_summary.set(f"Waiting for result file... {int(elapsed)}s")
            
            # Check for cancellation
            if not self.gui.processing:
                self.gui.status_summary.set("Processing cancelled by user")
                raise Exception("Processing cancelled by user")
            
            time.sleep(check_interval)
        
        self.gui.status_summary.set("Timeout waiting for result file")
        raise Exception(f"Timeout waiting for result file after {timeout} seconds")
    
    def _verify_file_ready(self, file_path: str) -> bool:
        """Verify file is stable and ready for download"""
        try:
            # Check if file exists
            cmd = f"test -f {file_path} && echo 'exists' || echo 'missing'"
            success, output, _ = self.ssh_connection.execute_command(cmd)
            
            if not success or output.strip() != "exists":
                return False
            
            # Check if file size is stable (not currently being written)
            size1_cmd = f"stat -c %s {file_path}"
            success1, size1, _ = self.ssh_connection.execute_command(size1_cmd)
            
            if not success1 or not size1.strip():
                return False
                
            time.sleep(1)
            
            size2_cmd = f"stat -c %s {file_path}"
            success2, size2, _ = self.ssh_connection.execute_command(size2_cmd)
            
            if not success2 or size1.strip() != size2.strip():
                return False
            
            return True
            
        except Exception as e:
            self.gui.log_error(f"Error verifying file readiness: {str(e)}")
            return False
    
    def extract_result_data(self, result_file_path: str):
        """Extract and process data from a result file"""
        try:
            import json
            
            with open(result_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            return data
            
        except Exception as e:
            self.gui.log_error(f"Failed to extract result data: {str(e)}")
            return None