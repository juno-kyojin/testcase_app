# Module: connection.py
# Purpose: Windows-specific SSH connection implementation for OpenWrt devices
# Last updated: 2025-06-02 by juno-kyojin

import paramiko
import logging
import time
import os
import subprocess
import tempfile
import base64
from typing import Optional, Tuple

class SSHConnection:
    def __init__(self):
        self.client: Optional[paramiko.SSHClient] = None
        self.logger = logging.getLogger(__name__)
        self.connected = False
        self.hostname = None
        self.username = None
        self.password = None
    
    def connect(self, hostname: str, username: str, password: str, port: int = 22, timeout: int = 10) -> bool:
        """
        Establish SSH connection and store credentials for file transfers
        """
        try:
            self.disconnect()
            
            # Store connection details
            self.hostname = hostname
            self.username = username
            self.password = password
            self.port = port
            
            self.client = paramiko.SSHClient()
            self.client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            
            self.logger.info(f"Connecting to {hostname}:{port} as {username}")
            self.client.connect(
                hostname=hostname,
                port=port,
                username=username,
                password=password,
                timeout=timeout,
                allow_agent=False,
                look_for_keys=False
            )
            
            # Test connection
            stdin, stdout, stderr = self.client.exec_command("echo 'connection_test'", timeout=5)
            result = stdout.read().decode().strip()
            
            if result == "connection_test":
                self.connected = True
                self.logger.info("SSH connection established successfully")
                return True
            else:
                self.logger.error("SSH connection test failed")
                return False
                
        except Exception as e:
            self.logger.error(f"Connection error: {e}")
            return False
    
    def disconnect(self):
        """Close SSH connection"""
        try:
            if self.client:
                self.client.close()
                self.client = None
            self.connected = False
            self.hostname = None
            self.username = None
            self.password = None
            self.logger.info("SSH connection closed")
        except Exception as e:
            self.logger.error(f"Error closing connection: {e}")
    
    def is_connected(self) -> bool:
        """Check if connection is still active"""
        if not self.connected or not self.client:
            return False
        
        try:
            # Sử dụng biến trung gian để Pylance hiểu rằng client không phải None
            client = self.client  # Tại đây, type của client là paramiko.SSHClient
            
            stdin, stdout, stderr = client.exec_command("echo 'keepalive'", timeout=3)
            result = stdout.read().decode().strip()
            return result == "keepalive"
        except:
            self.connected = False
            return False
    
    def execute_command(self, command: str, timeout: int = 30) -> Tuple[bool, str, str]:
        """Execute a command on the remote server with auto-retry"""
        retry_count = 0
        max_retries = 2  # Số lần thử lại tối đa
        
        while retry_count <= max_retries:
            if not self.is_connected():
                return False, "", "Not connected"
            
            try:
                client = self.client
                if client is None:
                    return False, "", "Client is None"
                    
                stdin, stdout, stderr = client.exec_command(command, timeout=timeout)
                
                stdout_data = stdout.read().decode('utf-8', errors='replace')
                stderr_data = stderr.read().decode('utf-8', errors='replace')
                exit_code = stdout.channel.recv_exit_status()
                
                success = exit_code == 0
                return success, stdout_data, stderr_data
                
            except Exception as e:
                retry_count += 1
                error_msg = f"Command execution error: {e}"
                
                # Nếu đã hết số lần thử, hoặc lỗi khác timeout, trả về lỗi
                if retry_count > max_retries or "timed out" not in str(e).lower():
                    self.logger.error(error_msg)
                    return False, "", str(e)
                
                # Đánh dấu kết nối đã mất để kích hoạt việc kết nối lại
                self.connected = False
                self.logger.warning(f"{error_msg} - Retrying ({retry_count}/{max_retries})...")
                time.sleep(2)  # Đợi một chút trước khi thử lại
    
    def ensure_remote_directory(self, remote_dir: str) -> bool:
        """Ensure remote directory exists"""
        try:
            success, stdout, stderr = self.execute_command(f"mkdir -p '{remote_dir}'")
            if not success:
                self.logger.error(f"Failed to create directory {remote_dir}: {stderr}")
                return False
            
            success, stdout, stderr = self.execute_command(f"chmod 755 '{remote_dir}'")
            if not success:
                self.logger.warning(f"Failed to set permissions on {remote_dir}: {stderr}")
            
            self.logger.info(f"Directory ensured: {remote_dir}")
            return True
                
        except Exception as e:
            self.logger.error(f"Error ensuring directory {remote_dir}: {e}")
            return False

    def upload_file_via_ssh_exec(self, local_path: str, remote_path: str) -> bool:
        """Upload file using established SSH connection and base64 encoding (best method)"""
        try:
            if not os.path.exists(local_path):
                self.logger.error(f"Local file not found: {local_path}")
                return False

            # Read file as binary
            with open(local_path, 'rb') as f:
                file_content = f.read()
            
            # Base64 encode content
            encoded_content = base64.b64encode(file_content).decode('utf-8')
            
            # Create target directory if needed
            remote_dir = os.path.dirname(remote_path)
            if remote_dir and remote_dir != '/':
                if not self.ensure_remote_directory(remote_dir):
                    return False
            
            # Command to decode and create file on device
            decode_cmd = f"echo '{encoded_content}' | base64 -d > '{remote_path}'"
            
            # Execute through existing SSH connection
            success, stdout, stderr = self.execute_command(decode_cmd, timeout=60)
            
            if success:
                self.logger.info(f"File uploaded via SSH exec: {local_path} -> {remote_path}")
                return True
            else:
                self.logger.error(f"SSH exec upload failed: {stderr}")
                return False
                    
        except Exception as e:
            self.logger.error(f"SSH exec upload error: {e}")
            return False
    
    def upload_file_via_pscp(self, local_path: str, remote_path: str) -> bool:
        """Upload file using PuTTY's PSCP (Windows-only method)"""
        try:
            if not self.hostname or not self.username or not self.password:
                self.logger.error("Connection details not available for PSCP")
                return False
            
            # Create remote directory first
            remote_dir = os.path.dirname(remote_path)
            if remote_dir and remote_dir != '/':
                if not self.ensure_remote_directory(remote_dir):
                    return False
            
            # Prepare for PSCP
            remote_target = f"{self.username}@{self.hostname}:{remote_path}"
            
            try:
                pscp_cmd = [
                    "pscp", 
                    "-scp",          # Use SCP protocol
                    "-batch",        # Non-interactive mode
                    "-pw", self.password,  # Password from memory
                    local_path, 
                    remote_target
                ]
                
                result = subprocess.run(
                    pscp_cmd,
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                if result.returncode == 0:
                    self.logger.info(f"File uploaded via PSCP: {local_path} -> {remote_path}")
                    return True
                else:
                    self.logger.warning(f"PSCP upload failed: {result.stderr}")
                    return False
                    
            except FileNotFoundError:
                self.logger.warning("PSCP not found - please install PuTTY tools")
                return False
            except Exception as e:
                self.logger.warning(f"PSCP error: {e}")
                return False
                
        except Exception as e:
            self.logger.error(f"PSCP setup error: {e}")
            return False
    
    def upload_file_via_ssh_cat(self, local_path: str, remote_path: str) -> bool:
        """Upload text file using SSH cat (fallback method for text files)"""
        try:
            with open(local_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Create remote directory
            remote_dir = os.path.dirname(remote_path)
            if remote_dir and remote_dir != '/':
                if not self.ensure_remote_directory(remote_dir):
                    return False
            
            # Escape content for shell
            content_escaped = content.replace("'", "'\"'\"'")
            
            # Write file using cat
            command = f"cat > '{remote_path}' << 'EOF_CONTENT_MARKER'\n{content}\nEOF_CONTENT_MARKER"
            
            success, stdout, stderr = self.execute_command(command, timeout=60)
            
            if success:
                self.logger.info(f"File uploaded via SSH cat: {local_path} -> {remote_path}")
                return True
            else:
                self.logger.error(f"SSH cat upload failed: {stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"SSH cat upload error: {e}")
            return False
    
    def upload_file(self, local_path: str, remote_path: str) -> bool:
        """Upload file using the best available method for Windows"""
        self.logger.info(f"Attempting to upload: {local_path} -> {remote_path}")
        
        # Ensure proper remote path format
        remote_path = remote_path.replace('\\', '/')
        
        # Method 1: SSH exec with base64 (preferred - uses existing connection)
        if self.upload_file_via_ssh_exec(local_path, remote_path):
            return True
        
        # Method 2: PSCP (PuTTY tool)
        if self.upload_file_via_pscp(local_path, remote_path):
            return True
        
        # Method 3: SSH cat (text files only - fallback)
        if self.upload_file_via_ssh_cat(local_path, remote_path):
            return True
        
        self.logger.error("All upload methods failed")
        return False
    
    def download_file_via_ssh_exec(self, remote_path: str, local_path: str) -> bool:
        """Download file using established SSH connection and base64 encoding (best method)"""
        try:
            if not self.is_connected():
                self.logger.error("No active SSH connection for download")
                return False
            
            # Ensure local directory exists
            local_dir = os.path.dirname(local_path)
            if local_dir:
                os.makedirs(local_dir, exist_ok=True)
            
            # Check if file exists
            if not self.file_exists(remote_path):
                self.logger.error(f"Remote file not found: {remote_path}")
                return False
            
            # Get file content using base64 to support binary files
            cmd = f"cat '{remote_path}' | base64"
            success, stdout, stderr = self.execute_command(cmd, timeout=60)
            
            if not success:
                self.logger.error(f"Failed to get file content: {stderr}")
                return False
            
            # Decode base64 content
            try:
                file_content = base64.b64decode(stdout)
                
                # Write to local file
                with open(local_path, 'wb') as f:
                    f.write(file_content)
                    
                self.logger.info(f"File downloaded via SSH exec: {remote_path} -> {local_path}")
                return True
            except Exception as e:
                self.logger.error(f"Failed to decode file content: {e}")
                return False
                
        except Exception as e:
            self.logger.error(f"SSH exec download error: {e}")
            return False
    
    def download_file_via_pscp(self, remote_path: str, local_path: str) -> bool:
        """Download file using PuTTY's PSCP (Windows-only method)"""
        try:
            if not self.hostname or not self.username or not self.password:
                self.logger.error("Connection details not available for PSCP")
                return False
            
            # Ensure local directory exists
            local_dir = os.path.dirname(local_path)
            if local_dir:
                os.makedirs(local_dir, exist_ok=True)
            
            # Prepare for PSCP
            remote_source = f"{self.username}@{self.hostname}:{remote_path}"
            
            try:
                pscp_cmd = [
                    "pscp",
                    "-batch",
                    "-pw", self.password,
                    "-scp",
                    remote_source,
                    local_path
                ]
                
                result = subprocess.run(
                    pscp_cmd,
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                if result.returncode == 0:
                    self.logger.info(f"File downloaded via PSCP: {remote_path} -> {local_path}")
                    return True
                else:
                    self.logger.warning(f"PSCP download failed: {result.stderr}")
                    return False
                    
            except FileNotFoundError:
                self.logger.warning("PSCP not found - please install PuTTY tools")
                return False
            except Exception as e:
                self.logger.warning(f"PSCP download error: {e}")
                return False
                
        except Exception as e:
            self.logger.error(f"PSCP download setup error: {e}")
            return False
    
    def download_file_via_ssh_cat(self, remote_path: str, local_path: str) -> bool:
        """Download text file using SSH cat (fallback method for text files)"""
        try:
            success, content, stderr = self.execute_command(f"cat '{remote_path}'")
            
            if success:
                # Ensure local directory exists
                local_dir = os.path.dirname(local_path)
                if local_dir:
                    os.makedirs(local_dir, exist_ok=True)
                
                # Write content to local file
                with open(local_path, 'w', encoding='utf-8') as f:
                    f.write(content)
                
                self.logger.info(f"File downloaded via SSH cat: {remote_path} -> {local_path}")
                return True
            else:
                self.logger.error(f"SSH cat download failed: {stderr}")
                return False
                
        except Exception as e:
            self.logger.error(f"SSH cat download error: {e}")
            return False
    
    def download_file(self, remote_path: str, local_path: str) -> bool:
        """Download file using the best available method for Windows"""
        self.logger.info(f"Attempting to download: {remote_path} -> {local_path}")
        
        # Ensure proper path formats
        remote_path = remote_path.replace('\\', '/')
        local_path = local_path.replace('/', '\\')
        
        # Method 1: SSH exec with base64 (preferred - uses existing connection)
        if self.download_file_via_ssh_exec(remote_path, local_path):
            return True
        
        # Method 2: PSCP (PuTTY tool)
        if self.download_file_via_pscp(remote_path, local_path):
            return True
        
        # Method 3: SSH cat (text files only - fallback)
        if self.download_file_via_ssh_cat(remote_path, local_path):
            return True
        
        self.logger.error("All download methods failed")
        return False
    
    def file_exists(self, remote_path: str) -> bool:
        """Check if file exists using ls command"""
        try:
            success, stdout, stderr = self.execute_command(f"ls '{remote_path}' 2>/dev/null")
            return success and stdout.strip() != ""
        except Exception as e:
            self.logger.error(f"Error checking file existence: {e}")
            return False
    
    def get_file_size(self, remote_path: str) -> int:
        """Get file size using stat command"""
        try:
            success, stdout, stderr = self.execute_command(f"stat -c%s '{remote_path}' 2>/dev/null")
            if success and stdout.strip().isdigit():
                return int(stdout.strip())
            return 0
        except Exception as e:
            self.logger.error(f"Error getting file size: {e}")
            return 0