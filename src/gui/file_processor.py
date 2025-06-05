import os
import time
import json
import threading
from tkinter import messagebox
from .config import AppConfig

class FileProcessor:
    def __init__(self, gui):
        self.gui = gui
        self.ssh_connection = gui.ssh_connection
        self.file_manager = gui.file_manager
        self.database = gui.database
        # Don't reference result_handler in __init__ to avoid circular dependency
        # self.result_handler = gui.result_handler
        
    @property
    def result_handler(self):
        """Lazy property to get result_handler when needed"""
        return self.gui.result_handler
        
    def send_files(self):
        """Send files using real SSH connection and file transfer"""
        if not self.gui.selected_files:
            messagebox.showinfo("Info", "No files selected")
            return
        
        if not self.gui.validate_connection_fields():
            return
        
        confirm = messagebox.askyesno(
            "Confirm", 
            f"Send {len(self.gui.selected_files)} files? Files will be processed sequentially."
        )
        
        if not confirm:
            return
        
        self.gui.file_retry_count = {}
        self.gui.send_button.configure(state='disabled')
        self.gui.cancel_button.configure(state='normal')
        self.gui.processing = True
        self.gui.progress_var.set(0)
        
        threading.Thread(target=self.process_files_real, daemon=True).start()
    
    def process_files_real(self):
        """Process files using real modules with enhanced error handling"""
        start_time = time.time()
        total_files = len(self.gui.selected_files)
        
        try:
            self.gui.log_message("Establishing SSH connection...")
            
            if not self.ssh_connection.is_connected():
                success = self.ssh_connection.connect(
                    hostname=self.gui.lan_ip_var.get(),
                    username=self.gui.username_var.get(),
                    password=self.gui.password_var.get()
                )
                
                if not success:
                    raise Exception("Failed to establish SSH connection")
            
            self.gui.root.after(0, lambda: self.gui.connection_status.set("Connected"))
            self.gui.root.after(0, lambda: self.gui.update_status_circle("green"))
            
            for i, file_path in enumerate(self.gui.selected_files):
                if not self.gui.processing:
                    break
                
                file_name = os.path.basename(file_path)
                file_start_time = time.time()
                self.gui.log_message(f"Processing file {i+1}/{total_files}: {file_name}")
                
                try:
                    self._process_single_file(i, file_path, file_start_time)
                except Exception as e:
                    self._handle_file_error(i, file_path, e, file_start_time)
            
            if self.gui.processing:
                total_time = time.time() - start_time
                self.gui.log_message(f"All {total_files} files processed in {total_time:.1f} seconds")
                self.gui.root.after(0, lambda: messagebox.showinfo("Complete", f"All {total_files} files processed successfully"))
            
        except Exception as e:
            error_msg = f"Processing error: {str(e)}"
            self.gui.log_message(error_msg)
            self.gui.root.after(0, lambda: messagebox.showerror("Error", error_msg))
        
        finally:
            self._reset_ui()
    
    def _process_single_file(self, file_index, file_path, file_start_time):
        """Process a single file"""
        file_name = os.path.basename(file_path)
        
        progress = int((file_index / len(self.gui.selected_files)) * 100)
        self.gui.root.after(0, lambda p=progress: self.gui.progress_var.set(p))
        self.gui.update_file_status(file_index, "Sending", "", "")
        
        # Upload file
        remote_path = os.path.join(self.gui.config_path_var.get(), file_name)
        upload_success = self.ssh_connection.upload_file(file_path, remote_path)
        
        if not upload_success:
            raise Exception("File upload failed")
        
        self.gui.log_message(f"File {file_name} uploaded successfully")
        self.gui.update_file_status(file_index, "Testing", "", "")
        
        time.sleep(1)  # Wait after upload
        
        # Wait for result
        timeout = AppConfig.DEFAULT_TIMEOUT
        
        result_remote_path, actual_result_filename = self.result_handler.wait_for_result_file(
            base_filename=os.path.splitext(file_name)[0],
            result_dir=self.gui.result_path_var.get(),
            upload_time=time.time(),
            timeout=timeout
        )
        
        # Download and process result
        self._download_and_process_result(
            file_index, file_path, file_name, file_start_time,
            result_remote_path, actual_result_filename
        )
    
    def _download_and_process_result(self, file_index, file_path, file_name, file_start_time,
                                   result_remote_path, actual_result_filename):
        """Download and process result file"""
        local_result_dir = "data/temp/results"
        os.makedirs(local_result_dir, exist_ok=True)
        local_result_path = os.path.join(local_result_dir, actual_result_filename)
        
        download_success = self.ssh_connection.download_file(result_remote_path, local_result_path)
        if not download_success:
            raise Exception("Failed to download result file")
        
        self.gui.log_message(f"Result file {actual_result_filename} downloaded successfully")
        
        # Parse result
        try:
            with open(local_result_path, 'r') as f:
                result_data = json.load(f)
        except Exception as e:
            raise Exception(f"Failed to parse result file: {str(e)}")
        
        overall_result = self.result_handler.determine_overall_result(result_data)
        execution_time = time.time() - file_start_time
        
        self.gui.update_file_status(file_index, "Completed", overall_result, f"{execution_time:.1f}s")
        
        # Save to database
        self._save_results_to_database(file_path, file_name, overall_result, execution_time, result_data)
        
        self.gui.log_message(f"File {file_name} processed successfully: {overall_result}")
    
    def _save_results_to_database(self, file_path, file_name, overall_result, execution_time, result_data):
        """Save results to database"""
        try:
            file_info = self.gui.file_data.get(file_name, {})
            if file_info:
                impacts = file_info.get("impacts", {})
                test_count = self.file_manager.get_test_case_count(file_info.get("data", {}))
            else:
                impacts = {"affects_wan": False, "affects_lan": False}
                test_count = 1
            
            file_id = self.database.save_test_file_result(
                file_name=file_name,
                file_size=os.path.getsize(file_path),
                test_count=test_count,
                send_status="Completed",
                overall_result=overall_result,
                affects_wan=impacts.get("affects_wan", False),
                affects_lan=impacts.get("affects_lan", False),
                execution_time=execution_time,
                target_ip=self.gui.lan_ip_var.get(),
                target_username=self.gui.username_var.get()
            )
            
            converted_results = self.result_handler.convert_result_format(result_data, file_path)
            if converted_results and file_id > 0:
                self.database.save_test_case_results(file_id, converted_results)
            
            self.gui.update_detail_table_with_results(file_index, {"test_results": converted_results})
        except Exception as e:
            self.gui.log_message(f"Error saving to database: {str(e)}")
    
    def _handle_file_error(self, file_index, file_path, error, file_start_time):
        """Handle file processing error"""
        file_name = os.path.basename(file_path)
        error_msg = f"Error processing {file_name}: {str(error)}"
        self.gui.log_message(error_msg)
        
        self.gui.update_file_status(file_index, "Error", "Failed", "Error")
    
    def _reset_ui(self):
        """Reset UI after processing"""
        self.gui.processing = False
        self.gui.root.after(0, lambda: self.gui.send_button.configure(state='normal'))
        self.gui.root.after(0, lambda: self.gui.cancel_button.configure(state='disabled'))
        self.gui.root.after(0, lambda: self.gui.progress_var.set(0))
        self.gui.root.after(0, self.gui.load_history)
    
    def cancel_processing(self):
        """Cancel the file processing"""
        if self.gui.processing:
            self.gui.processing = False
            self.gui.log_message("Processing cancelled by user")
