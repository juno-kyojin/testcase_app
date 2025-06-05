import threading
import time
import tkinter as tk
from tkinter import messagebox
from .config import AppConfig

class ConnectionHandler:
    def __init__(self, gui):
        self.gui = gui
        self.ssh_connection = gui.ssh_connection
        self.database = gui.database
        # Remove any references to other handlers during initialization
        
    def test_connection(self):
        """Enhanced connection test with retry logic"""
        if not self.gui.validate_connection_fields():
            return
        
        self.gui.connection_status.set("Connecting...")
        self.gui.update_status_circle("yellow")
        self.gui.log_message("Testing connection to " + self.gui.lan_ip_var.get() + "...")
        
        threading.Thread(target=self._test_connection_thread, daemon=True).start()
    
    def _test_connection_thread(self):
        """Connection test thread with enhanced error handling"""
        max_attempts = AppConfig.MAX_RECONNECT_ATTEMPTS
        attempt_delay = AppConfig.CONNECTION_RETRY_DELAY
        
        for attempt in range(1, max_attempts + 1):
            try:
                self.gui.root.after(0, lambda a=attempt: self.gui.log_message(f"Connection attempt {a}/{max_attempts}..."))
                
                success = self.ssh_connection.connect(
                    hostname=self.gui.lan_ip_var.get(),
                    username=self.gui.username_var.get(),
                    password=self.gui.password_var.get(),
                    timeout=AppConfig.SSH_CONNECT_TIMEOUT
                )
                
                if success:
                    if self._verify_remote_paths():
                        self._handle_connection_success()
                    else:
                        self._handle_connection_failure("Remote paths not accessible")
                    return
                else:
                    if attempt < max_attempts:
                        self.gui.root.after(0, lambda: self.gui.log_message(f"Attempt {attempt} failed, retrying in {attempt_delay}s..."))
                        time.sleep(attempt_delay)
                        attempt_delay *= 2
                    else:
                        self._handle_connection_failure("Authentication failed after all attempts")
                        
            except Exception as e:
                error_msg = f"Connection error on attempt {attempt}: {str(e)}"
                if attempt < max_attempts:
                    self.gui.root.after(0, lambda msg=error_msg: self.gui.log_message(f"{msg}, retrying..."))
                    time.sleep(attempt_delay)
                    attempt_delay *= 2
                else:
                    self._handle_connection_failure(error_msg)

    def _verify_remote_paths(self) -> bool:
        """Verify remote paths are accessible"""
        paths = [
            (self.gui.config_path_var.get(), "Config path"),
            (self.gui.result_path_var.get(), "Result path")
        ]
        
        for path, description in paths:
            success, stdout, stderr = self.ssh_connection.execute_command(f"test -d '{path}' && test -w '{path}'")
            if not success:
                self.gui.root.after(0, lambda p=path, d=description: self.gui.log_message(f"{d} not accessible: {p}"))
                return False
            
        self.gui.root.after(0, lambda: self.gui.log_message("All remote paths verified"))
        return True

    def _handle_connection_success(self):
        """Handle successful connection"""
        self.database.log_connection(
            self.gui.lan_ip_var.get(), 
            "Connected", 
            "Connection test successful with path verification"
        )
        
        self.gui.root.after(0, lambda: self.gui.connection_status.set("Connected"))
        self.gui.root.after(0, lambda: self.gui.update_status_circle("green"))
        self.gui.root.after(0, lambda: self.gui.log_message("Connection successful - All systems ready"))
        self.gui.root.after(0, lambda: messagebox.showinfo("Connection", "Connection successful!\nRemote paths verified."))

    def _handle_connection_failure(self, error_msg: str):
        """Handle connection failure"""
        self.database.log_connection(
            self.gui.lan_ip_var.get(), 
            "Failed", 
            error_msg
        )
        
        self.gui.root.after(0, lambda: self.gui.connection_status.set("Connection failed"))
        self.gui.root.after(0, lambda: self.gui.update_status_circle("red"))
        self.gui.root.after(0, lambda: self.gui.log_message(f"Connection failed: {error_msg}"))
        self.gui.root.after(0, lambda: messagebox.showerror("Connection Failed", f"Unable to connect:\n{error_msg}\n\nPlease check:\n• IP address and network connectivity\n• Username and password\n• Remote directory permissions"))

    def attempt_reconnection(self) -> bool:
        """Attempt to reconnect SSH"""
        self.gui.log_message("Attempting to reconnect...")
        
        for attempt in range(AppConfig.MAX_RECONNECT_ATTEMPTS):
            try:
                success = self.ssh_connection.connect(
                    hostname=self.gui.lan_ip_var.get(),
                    username=self.gui.username_var.get(),
                    password=self.gui.password_var.get(),
                    timeout=10
                )
                
                if success:
                    self.gui.log_message("Reconnection successful")
                    self.gui.root.after(0, lambda: self.gui.update_status_circle("green"))
                    return True
                else:
                    time.sleep(2)
                    
            except Exception as e:
                self.gui.log_message(f"Reconnection attempt {attempt + 1} failed: {str(e)}")
                time.sleep(2)
        
        self.gui.log_message("All reconnection attempts failed")
        self.gui.root.after(0, lambda: self.gui.update_status_circle("red"))
        return False
    
    def check_remote_folders(self):
        """Check if remote folders exist and are accessible"""
        if not self.gui.validate_connection_fields():
            return
        
        self.gui.log_message("Checking remote folders...")
        
        def _check_folders():
            try:
                if not self.ssh_connection.is_connected():
                    success = self.ssh_connection.connect(
                        hostname=self.gui.lan_ip_var.get(),
                        username=self.gui.username_var.get(),
                        password=self.gui.password_var.get()
                    )
                    if not success:
                        raise Exception("Failed to connect")
                
                config_path = self.gui.config_path_var.get()
                success, stdout, stderr = self.ssh_connection.execute_command(f"ls -ld {config_path}")
                
                if not success:
                    raise Exception(f"Config folder not accessible: {stderr}")
                
                result_path = self.gui.result_path_var.get()
                success, stdout, stderr = self.ssh_connection.execute_command(f"ls -ld {result_path}")
                
                if not success:
                    raise Exception(f"Result folder not accessible: {stderr}")
                
                message = f"Both folders are accessible:\n• {config_path}\n• {result_path}"
                self.gui.root.after(0, lambda: messagebox.showinfo("Folder Check", message))
                self.gui.root.after(0, lambda: self.gui.log_message("Remote folders check successful"))
                
            except Exception as e:
                error_msg = f"Folder check failed: {str(e)}"
                self.gui.root.after(0, lambda: messagebox.showerror("Folder Check", error_msg))
                self.gui.root.after(0, lambda: self.gui.log_message(error_msg))
        
        threading.Thread(target=_check_folders, daemon=True).start()
