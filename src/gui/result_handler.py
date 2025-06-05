import os
import time
import json
import threading
import re
from typing import Tuple, Dict, List, Any
from .config import AppConfig

class ResultHandler:
    def __init__(self, gui):
        self.gui = gui
        self.ssh_connection = gui.ssh_connection
        self.logger = gui.logger
        
    def wait_for_result_file(self, base_filename: str, result_dir: str, upload_time: float, 
                           timeout: int = 300, is_network_test: bool = False) -> Tuple[str, str]:
        """Wait for any new result file to appear after test file upload"""
        start_wait = time.time()
        check_interval = 3
        last_log_time = 0
        
        self.gui.log_message(f"Waiting for result file in {result_dir} (timeout: {timeout}s)")
        
        while time.time() - start_wait < timeout:
            elapsed = time.time() - start_wait
            
            try:
                # Simple method: find newest JSON file
                cmd = f"find {result_dir} -name '*.json' -type f -printf '%T@ %p\\n' | sort -nr | head -1 | cut -d' ' -f2-"
                success, stdout, _ = self.ssh_connection.execute_command(cmd)
                
                if success and stdout.strip():
                    file_path = stdout.strip()
                    file_name = os.path.basename(file_path)
                    
                    if self._verify_file_ready(file_path):
                        self.gui.log_message(f"Found result file: {file_name}")
                        return file_path, file_name
                
            except Exception as e:
                self.gui.log_message(f"Error checking for result file: {str(e)}")
            
            # Log progress periodically
            if elapsed - last_log_time >= 15:
                self.gui.log_message(f"[{elapsed:.0f}s] Still waiting for result file...")
                last_log_time = elapsed
            
            # Check if processing was cancelled
            if not self.gui.processing:
                raise Exception("Processing cancelled by user")
            
            time.sleep(check_interval)
        
        raise Exception(f"Timeout waiting for result file after {timeout} seconds")
        
    def _verify_file_ready(self, file_path: str, min_size: int = 10) -> bool:
        """Verify file is ready and stable"""
        try:
            # Check file exists
            exists_cmd = f"test -f '{file_path}' && echo 'exists'"
            success, stdout, _ = self.ssh_connection.execute_command(exists_cmd)
            
            if not (success and "exists" in stdout):
                return False
            
            # Check file size
            size1 = self.ssh_connection.get_file_size(file_path)
            if size1 < min_size:
                return False
            
            # Check file stability
            time.sleep(0.5)
            size2 = self.ssh_connection.get_file_size(file_path)
            
            return size1 == size2 and size1 >= min_size
        except Exception as e:
            self.gui.log_message(f"Error checking if file is ready: {str(e)}")
            return False
    
    def convert_result_format(self, openwrt_result, input_file_name=None):
        """Convert OpenWrt result format to our expected format"""
        try:
            converted_results = []
            
            # Try to read service and action info from original file
            service_name = "unknown"
            action_name = ""
            
            # Extract from filename if possible
            if input_file_name:
                filename = os.path.basename(input_file_name)
                base_name = os.path.splitext(filename)[0]
                parts = base_name.split('_')
                if len(parts) > 0:
                    service_name = parts[0]
                    if len(parts) > 1:
                        action_name = '_'.join(parts[1:])
            
            # Process failed test cases
            failed_by_service = openwrt_result.get("failed_by_service", {})
            for service, tests in failed_by_service.items():
                for test in tests:
                    test_service = test.get("service", service)
                    test_action = test.get("action", "")
                    message = test.get("message", f"{test_service} {test_action} failed")
                    
                    converted_results.append({
                        "service": test_service,
                        "action": test_action,
                        "status": "fail",
                        "details": message,
                        "execution_time": test.get("execution_time_ms", 0) / 1000.0
                    })
            
            # Get info from summary
            summary = openwrt_result.get("summary", {})
            pass_count = summary.get("passed", 0)
            fail_count = summary.get("failed", 0)
            
            # Process passed test cases
            if pass_count > 0 and fail_count == 0:
                status_text = "completed successfully"
                details = f"{service_name} {action_name} {status_text}"
                
                converted_results.append({
                    "service": service_name,
                    "action": action_name,
                    "status": "pass",
                    "details": details,
                    "execution_time": summary.get("total_duration_ms", 0) / 1000.0
                })
            
            # If no results, create a default result
            if not converted_results:
                status = "pass" if fail_count == 0 else "fail"
                status_text = "completed successfully" if status == "pass" else "failed"
                details = f"{service_name} {action_name} {status_text}"
                
                converted_results.append({
                    "service": service_name,
                    "action": action_name,
                    "status": status,
                    "details": details,
                    "execution_time": 0.0
                })
            
            return converted_results
            
        except Exception as e:
            self.gui.log_message(f"Error in convert_result_format: {str(e)}")
            
            # Fallback
            return [{
                "service": "unknown",
                "action": "",
                "status": "error",
                "details": f"Error processing result: {str(e)}",
                "execution_time": 0.0
            }]
        
    def determine_overall_result(self, result_data):
        """Determine overall result from test result data"""
        if "summary" in result_data:
            summary = result_data["summary"]
            total = summary.get("total_test_cases", 0)
            passed = summary.get("passed", 0)
            failed = summary.get("failed", 0)
            
            if total == passed:
                return "Pass"
            elif passed == 0:
                return "Fail"
            else:
                return f"Partial ({passed}/{total})"
        
        return "Unknown"
