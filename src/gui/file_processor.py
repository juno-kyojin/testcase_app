#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# Module: file_processor.py
# Purpose: Process test files for Test Case Manager
# Last updated: 2025-06-05 by juno-kyojin

import os
import time
import json
import threading
from typing import List, Dict, Tuple, Optional

from .config import AppConfig

class FileProcessor:
    def __init__(self, gui):
        self.gui = gui
        self.ssh_connection = gui.ssh_connection
        self.database = gui.database
    
    def send_files(self):
        """Send selected files to the remote device for processing"""
        if not self.gui.selected_files:
            self.gui.log_error("No files selected")
            return
            
        if not self.gui.validate_connection_fields():
            return
            
        # Test connection before sending
        self.gui.log_connection("Establishing SSH connection...")
        
        if not self.ssh_connection.is_connected():
            success = self.ssh_connection.connect(
                hostname=self.gui.lan_ip_var.get(),
                username=self.gui.username_var.get(),
                password=self.gui.password_var.get(),
                timeout=10
            )
            
            if not success:
                self.gui.log_error("Failed to establish SSH connection")
                return
        
        # Start processing thread
        self.gui.processing = True
        self.gui.file_retry_count = {}
        
        processing_thread = threading.Thread(
            target=self._process_files,
            args=(self.gui.selected_files,)
        )
        processing_thread.daemon = True
        processing_thread.start()
    
    def cancel_processing(self):
        """Cancel file processing"""
        if self.gui.processing:
            self.gui.processing = False
            self.gui.log_file("Processing cancelled by user")
    
    def _process_files(self, file_paths: List[str]):
        """Process all selected files with special handling for network tests"""
        start_time = time.time()
        
        try:
            # Reset progress bar
            self.gui.root.after(0, lambda: self.gui.progress_var.set(0))
            
            for i, file_path in enumerate(file_paths):
                # Update current file index for status reporting
                self.gui.current_file_index = i
                
                # Process file
                file_start_time = time.time()
                file_name = os.path.basename(file_path)
                
                # Hiển thị thông tin file đang xử lý
                self.gui.status_summary.set(f"Processing file {i+1}/{len(file_paths)}: {file_name}")
                self.gui.log_file(f"Processing file {i+1}/{len(file_paths)}: {file_name}")
                
                try:
                    success = self._process_single_file(i, file_path, file_start_time)
                    
                    # Đảm bảo kết nối ổn định trước khi chuyển sang file tiếp theo
                    if i < len(file_paths) - 1:
                        # Kiểm tra kết nối trước khi tiếp tục
                        if not self.ssh_connection.is_connected():
                            self.gui.log_connection("Kết nối đã mất, đang thử kết nối lại trước khi xử lý file tiếp...")
                            reconnect_success = False
                            
                            for attempt in range(1, 4):  # Thử tối đa 3 lần
                                try:
                                    reconnect_success = self.ssh_connection.connect(
                                        hostname=self.gui.lan_ip_var.get(),
                                        username=self.gui.username_var.get(),
                                        password=self.gui.password_var.get(),
                                        timeout=10
                                    )
                                    if reconnect_success:
                                        self.gui.log_connection("Đã kết nối lại thành công")
                                        break
                                except Exception as e:
                                    self.gui.log_error(f"Lỗi kết nối lần {attempt}: {str(e)}")
                                    time.sleep(3)
                            
                            if not reconnect_success:
                                self.gui.log_error("Không thể kết nối lại sau nhiều lần thử. Dừng xử lý.")
                                break
                        
                        # Đợi một chút giữa các file
                        time.sleep(2)
                    
                except Exception as e:
                    if "cancelled by user" in str(e):
                        self.gui.log_file("Xử lý bị hủy bởi người dùng")
                        break
                    else:
                        self.gui.log_error(f"Lỗi xử lý file {file_name}: {str(e)}")
                        self.gui.update_file_status(i, "Error", str(e)[:20], "")
                    
                if not self.gui.processing:
                    self.gui.log_file("Xử lý bị hủy bởi người dùng")
                    break
                
                # Cập nhật thanh tiến trình
                progress = int(((i + 1) / len(file_paths)) * 100)
                self.gui.root.after(0, lambda p=progress: self.gui.progress_var.set(p))
            
            # Update final progress
            self.gui.root.after(0, lambda: self.gui.progress_var.set(100))
            
            # Update status
            total_time = time.time() - start_time
            file_count = len(file_paths)
            self.gui.log_result(f"All {file_count} files processed in {total_time:.1f} seconds")
            self.gui.status_summary.set(f"Đã hoàn thành {file_count} file trong {total_time:.1f} giây")
            
        except Exception as e:
            self.gui.log_error(f"Lỗi trong quá trình xử lý file: {str(e)}")
        finally:
            self.gui.processing = False
            self.gui.current_file_index = -1
    
    def _process_single_file(self, file_index, file_path, file_start_time):
        """Process a single file with special handling for network-affecting tests"""
        file_name = os.path.basename(file_path)
        max_retries = 2
        
        progress = int((file_index / len(self.gui.selected_files)) * 100)
        self.gui.root.after(0, lambda p=progress: self.gui.progress_var.set(p))
        self.gui.update_file_status(file_index, "Sending", "", "")
        
        # Kiểm tra file có ảnh hưởng đến mạng không
        file_info = self.gui.file_data.get(file_name, {})
        impacts = file_info.get("impacts", {})
        affects_network = impacts.get("affects_wan", False) or impacts.get("affects_lan", False)
        
        if affects_network:
            self.gui.log_warning(f"⚠️ Test {file_name} có thể làm mất kết nối mạng tạm thời")
            self.gui.status_summary.set("⚠️ Test có thể làm mất kết nối tạm thời")
            
            # Thời gian chờ dài hơn cho test mạng
            network_timeout = AppConfig.DEFAULT_TIMEOUT * 2
        else:
            network_timeout = AppConfig.DEFAULT_TIMEOUT
        
        # Retry logic for upload
        for attempt in range(1, max_retries + 1):
            try:
                # Kiểm tra hủy xử lý trước mỗi lần thử
                if not self.gui.processing:
                    raise Exception("Processing cancelled by user")
                    
                # Kiểm tra kết nối trước khi tải lên
                if not self.ssh_connection.is_connected():
                    self.gui.log_connection("SSH connection lost, attempting to reconnect...")
                    self.gui.status_summary.set("Connection lost. Attempting to reconnect...")
                    
                    success = self.ssh_connection.connect(
                        hostname=self.gui.lan_ip_var.get(),
                        username=self.gui.username_var.get(),
                        password=self.gui.password_var.get(),
                        timeout=10
                    )
                    if not success:
                        if attempt == max_retries:
                            raise Exception("Failed to reconnect SSH")
                        else:
                            time.sleep(5)
                            continue
                
                # Upload file
                remote_path = os.path.join(self.gui.config_path_var.get(), file_name)
                upload_success = self.ssh_connection.upload_file(file_path, remote_path)
                
                if not upload_success:
                    raise Exception("File upload failed")
                
                self.gui.log_file(f"{file_name} uploaded successfully")
                self.gui.update_file_status(file_index, "Testing", "", "")
                
                if affects_network:
                    # Xử lý đặc biệt cho test gây mất kết nối
                    self.gui.log_connection("Test này ảnh hưởng đến kết nối mạng, đang đợi mạng khôi phục...")
                    self.gui.status_summary.set("Đợi mạng khôi phục sau khi test...")
                    
                    result = self._wait_for_result_with_reconnect(
                        file_name=file_name,
                        file_path=file_path,
                        file_index=file_index,
                        upload_time=time.time(),
                        timeout=network_timeout
                    )
                    return result
                else:
                    # Xử lý bình thường cho test không ảnh hưởng mạng
                    try:
                        result_remote_path, actual_result_filename = self.gui.result_handler.wait_for_result_file(
                            base_filename=os.path.splitext(file_name)[0],
                            result_dir=self.gui.result_path_var.get(),
                            upload_time=time.time(),
                            timeout=network_timeout
                        )
                        
                        # Download and process result
                        return self._download_and_process_result(
                            file_index, file_path, file_name, file_start_time,
                            result_remote_path, actual_result_filename
                        )
                    except Exception as e:
                        if attempt < max_retries and not "cancelled by user" in str(e):
                            self.gui.log_error(f"Error waiting for result: {str(e)}. Retrying...")
                            time.sleep(2)
                            continue
                        else:
                            raise
                
            except Exception as e:
                if "cancelled by user" in str(e):
                    raise
                elif attempt < max_retries:
                    self.gui.log_error(f"Attempt {attempt} failed for {file_name}, retrying: {str(e)}")
                    time.sleep(2)
                else:
                    raise
    def _wait_for_result_with_reconnect(self, file_name, file_path, file_index, upload_time, timeout):
        """Đợi kết quả với xử lý đặc biệt cho test gây mất kết nối"""
        max_reconnect_attempts = 6
        reconnect_interval = 10
        start_time = time.time()
        result_dir = self.gui.result_path_var.get()
        base_name = os.path.splitext(file_name)[0]
        
        self.gui.log_connection(f"Bắt đầu đợi mạng khôi phục sau khi gửi {file_name}...")
        self.gui.update_file_status(file_index, "Network Reset", "", "")
        
        # Đợi mạng mất và kết nối lại
        connected = False
        reconnect_attempt = 0
        result_found = False
        
        while time.time() - start_time < timeout:
            # Kiểm tra hủy xử lý
            if not self.gui.processing:
                raise Exception("Processing cancelled by user")
            
            elapsed = time.time() - start_time
            
            # Thử kết nối mỗi khoảng thời gian
            if not connected:
                reconnect_attempt += 1
                
                if reconnect_attempt > 1:
                    self.gui.log_connection(f"Đang thử kết nối lại lần {reconnect_attempt}/{max_reconnect_attempts}...")
                    self.gui.status_summary.set(f"Đang thử kết nối lại ({reconnect_attempt}/{max_reconnect_attempts})...")
                
                try:
                    success = self.ssh_connection.connect(
                        hostname=self.gui.lan_ip_var.get(),
                        username=self.gui.username_var.get(),
                        password=self.gui.password_var.get(),
                        timeout=10
                    )
                    
                    if success:
                        self.gui.log_connection("Kết nối đã được khôi phục!")
                        self.gui.status_summary.set("Đã khôi phục kết nối. Đang tìm file kết quả...")
                        connected = True
                        
                        # Sau khi kết nối lại, tìm file kết quả
                        pattern = f"{base_name}_*.json"
                        self.gui.log_result(f"Tìm kiếm file kết quả cho {file_name}...")
                        
                        # Tìm file kết quả mới nhất sau khi upload
                        cmd = f"ls -lt {result_dir}/{pattern} 2>/dev/null | head -1"
                        success, newest_file_info, _ = self.ssh_connection.execute_command(cmd)
                        
                        if success and newest_file_info.strip():
                            # Trích xuất tên file từ kết quả command ls
                            parts = newest_file_info.strip().split()
                            newest_file = parts[-1]  # Phần cuối là tên file
                            result_file_path = os.path.join(result_dir, newest_file)
                            
                            # Kiểm tra file được tạo sau khi upload
                            cmd_check = f"find {result_dir} -name '{pattern}' -type f -newermt \"$(date -d @{int(upload_time)} '+%Y-%m-%d %H:%M:%S')\" | grep '{newest_file}'"
                            check_success, check_output, _ = self.ssh_connection.execute_command(cmd_check)
                            
                            if check_success and check_output.strip():
                                self.gui.log_result(f"Tìm thấy file kết quả: {newest_file}")
                                
                                # Tải xuống và xử lý kết quả
                                return self._download_and_process_result(
                                    file_index, file_path, file_name, start_time,
                                    result_file_path, newest_file
                                )
                except Exception as e:
                    self.gui.log_error(f"Lỗi khi thử kết nối lại: {str(e)}")
                    connected = False
            
            # Nếu vượt quá số lần thử kết nối lại
            if reconnect_attempt >= max_reconnect_attempts:
                self.gui.log_error(f"Đã thử kết nối lại {max_reconnect_attempts} lần nhưng không thành công")
                break
            
            # Log tiến trình
            minutes, seconds = divmod(int(elapsed), 60)
            self.gui.status_summary.set(f"Đợi mạng khôi phục ({minutes:02d}:{seconds:02d})...")
            
            # Đợi trước khi thử lại
            time.sleep(reconnect_interval)
        
        # Nếu timeout mà vẫn không tìm thấy kết quả
        self.gui.log_error(f"Hết thời gian chờ {timeout}s cho {file_name}")
        self.gui.update_file_status(file_index, "Failed", "Timeout", f"{int(timeout)}s")
        
        return False    
    def _wait_for_device_after_network_test(self, wait_interval):
        """Wait for device to restart and stabilize after network affecting test"""
        self.gui.log_connection(f"Waiting for device to restart and stabilize...")
        self.gui.status_summary.set(f"Waiting for device to restart ({wait_interval}s)...")
        time.sleep(wait_interval)
        
        # Try to reconnect
        self.gui.log_connection(f"Attempting to reconnect after {wait_interval}s...")
        self.gui.status_summary.set("Attempting to reconnect...")
        
        max_reconnect_attempts = 6
        for attempt in range(1, max_reconnect_attempts + 1):
            if not self.gui.processing:
                raise Exception("Processing cancelled by user")
                
            # Update UI during reconnect attempts
            self.gui.status_summary.set(f"Reconnection attempt {attempt}/{max_reconnect_attempts}")
            
            # Try to connect
            self.ssh_connection.disconnect()  # Ensure we're disconnected first
            success = self.ssh_connection.connect(
                hostname=self.gui.lan_ip_var.get(),
                username=self.gui.username_var.get(),
                password=self.gui.password_var.get(),
                timeout=10
            )
            
            if success:
                self.gui.log_connection("Connection re-established successfully")
                self.gui.status_summary.set("Connection re-established")
                self.gui.update_status_circle("green")
                break
                
            if attempt < max_reconnect_attempts:
                self.gui.log_connection(f"Reconnection attempt {attempt} failed, waiting {wait_interval}s")
                self.gui.status_summary.set(f"Reconnection failed. Retry in {wait_interval}s...")
                self.gui.update_status_circle("yellow")
                time.sleep(wait_interval)
            else:
                self.gui.status_summary.set("Failed to reconnect after multiple attempts")
                self.gui.update_status_circle("red")
                raise Exception(f"Failed to reconnect after {attempt} attempts")
    
    def _find_result_after_reconnect(self, file_index, file_path, file_name, file_start_time, 
                                   pre_test_time, timeout):
        """Find result file after reconnecting to device"""
        # Wait for stabilization
        time.sleep(5)
        
        # Build pattern for result file search
        base_name = os.path.splitext(file_name)[0]
        pattern = f"{base_name}_*.json"
        
        # Search for result files
        self.gui.log_result(f"Searching for result files matching {pattern}")
        
        cmd = f"find {self.gui.result_path_var.get()} -name '{pattern}' -type f -newermt \"$(date -d @{int(pre_test_time)} '+%Y-%m-%d %H:%M:%S')\" | sort | tail -1"
        success, output, _ = self.ssh_connection.execute_command(cmd)
        
        if not success or not output.strip():
            raise Exception(f"No result file found after reconnect")
            
        result_path = output.strip()
        result_file = os.path.basename(result_path)
        
        self.gui.log_result(f"Found result file after reconnect: {result_file}")
        
        # Download and process
        local_result_dir = os.path.join("data", "temp", "results")
        os.makedirs(local_result_dir, exist_ok=True)
        local_result_path = os.path.join(local_result_dir, result_file)
        
        download_success = self.ssh_connection.download_file(result_path, local_result_path)
        
        if not download_success:
            raise Exception(f"Failed to download result file {result_file}")
            
        self.gui.log_result(f"Result file {result_file} downloaded successfully")
        
        # Process result
        with open(local_result_path, 'r', encoding='utf-8') as f:
            result_data = json.load(f)
            
        # Save and display results
        self._process_downloaded_result(file_index, file_path, file_name, file_start_time, 
                                       result_data, result_file)
    
    def _download_and_process_result(self, file_index, file_path, file_name, file_start_time, remote_result_path, result_file_name):
        """Download and process a result file"""
        try:
            # Setup local path for the result
            local_result_dir = os.path.join("data", "temp", "results")
            os.makedirs(local_result_dir, exist_ok=True)
            local_result_path = os.path.join(local_result_dir, result_file_name)
            
            # Download result file
            download_success = self.ssh_connection.download_file(remote_result_path, local_result_path)
            
            if not download_success:
                raise Exception(f"Failed to download result file {result_file_name}")
                
            self.gui.log_result(f"Result file {result_file_name} downloaded successfully")
            
            # Parse result file
            with open(local_result_path, 'r', encoding='utf-8') as f:
                result_data = json.load(f)
                
            # Determine overall_result if it's "Unknown" or empty
            overall_result = result_data.get("overall_result", "Unknown")
            
            if not overall_result or overall_result == "Unknown":
                # Kiểm tra trực tiếp trường "pass" nếu có
                if "pass" in result_data:
                    overall_result = "Pass" if result_data["pass"] else "Fail"
                else:
                    # Kiểm tra các test cases
                    test_cases = result_data.get("test_results", [])
                    if test_cases:
                        all_pass = all(case.get("status", "").lower() == "pass" for case in test_cases)
                        overall_result = "Pass" if all_pass else "Fail"
                    else:
                        # Mặc định nếu không có thông tin khác
                        overall_result = "Pass"  # Giả định là Pass nếu không có thông tin ngược lại
            
            # Log kết quả xác định được
            self.gui.log_result(f"Determined test result: {overall_result}")
            
            # Save and display results
            self._process_downloaded_result(file_index, file_path, file_name, file_start_time, 
                                          result_data, result_file_name, overall_result)
            
            return True
            
        except Exception as e:
            self.gui.log_error(f"Error processing result for {file_name}: {str(e)}")
            self.gui.update_file_status(file_index, "Error", f"Failed: {str(e)}", "")
            return False
    
    def _process_downloaded_result(self, file_index, file_path, file_name, file_start_time, 
                                  result_data, result_file_name, overall_result=None):
        """Process downloaded result data"""
        try:
            # Get basic result info if not provided
            if overall_result is None:
                overall_result = result_data.get("overall_result", "Unknown")
                
                # Determine overall_result if it's "Unknown" or empty
                if not overall_result or overall_result == "Unknown":
                    # Kiểm tra trực tiếp trường "pass" nếu có
                    if "pass" in result_data:
                        overall_result = "Pass" if result_data["pass"] else "Fail"
                    else:
                        # Kiểm tra các test cases
                        test_cases = result_data.get("test_results", [])
                        if test_cases:
                            all_pass = all(case.get("status", "").lower() == "pass" for case in test_cases)
                            overall_result = "Pass" if all_pass else "Fail"
                        else:
                            overall_result = "Pass"  # Giả định là Pass nếu không có thông tin ngược lại
            
            execution_time = time.time() - file_start_time
            time_str = f"{execution_time:.1f}s"
            
            # Extract basic information
            file_size = os.path.getsize(file_path) if os.path.exists(file_path) else 0
            
            # Extract test cases
            test_cases = result_data.get("test_results", [])
            test_count = len(test_cases) if test_cases else 1
            
            # Check if the test affects network
            impacts = self.gui.file_data.get(file_name, {}).get("impacts", {})
            affects_wan = impacts.get("affects_wan", False)
            affects_lan = impacts.get("affects_lan", False)
            
            # Save result to database
            result_id = self.gui.database.save_test_file_result(
                file_name=file_name,
                file_size=file_size,
                test_count=test_count,
                send_status="Complete",
                overall_result=overall_result,
                affects_wan=affects_wan,
                affects_lan=affects_lan,
                execution_time=execution_time,
                target_ip=self.gui.lan_ip_var.get(),
                target_username=self.gui.username_var.get()
            )
            
            # If test cases exist, save them too
            if test_cases:
                self.gui.database.save_test_case_results(result_id, test_cases)
            else:
                # Create synthetic test case from overall result
                synthetic_case = {
                    "service": result_data.get("service", "unknown"),
                    "action": result_data.get("action", ""),
                    "status": "pass" if "Pass" in overall_result else "fail",
                    "details": result_data.get("details", ""),
                    "execution_time": execution_time
                }
                self.gui.database.save_test_case_results(result_id, [synthetic_case])
            
            # Update UI
            self.gui.update_file_status(file_index, "Complete", overall_result, time_str)
            
            # Display result details
            if hasattr(self.gui, 'detail_table'):
                # Clear existing details
                for item in self.gui.detail_table.get_children():
                    self.gui.detail_table.delete(item)
                    
                # Add test case information
                if not test_cases:
                    # Handle case without test_results array
                    service = result_data.get("service", "unknown")
                    action = result_data.get("action", "")
                    status = overall_result
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
                else:
                    for result in test_cases:
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
            
            self.gui.log_result(f"File {file_name} processed successfully: {overall_result}")
            return True
            
        except Exception as e:
            self.gui.log_error(f"Error processing result data for {file_name}: {str(e)}")
            self.gui.update_file_status(file_index, "Error", f"Failed: {str(e)}", "")
            return False