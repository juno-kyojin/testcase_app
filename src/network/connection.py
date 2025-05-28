# Module: connection.py
# Purpose: SSH connection with SCP support for OpenWrt

import paramiko
import logging
import time
import os
import subprocess
import tempfile
from typing import Optional, Tuple

class SSHConnection:
    def __init__(self):
        self.client = None
        self.logger = logging.getLogger(__name__)
        self.connected = False
        self.hostname = None
        self.username = None
        self.password = None
    
    def connect(self, hostname: str, username: str, password: str, port: int = 22, timeout: int = 10) -> bool:
        """
        Establish SSH connection and store credentials for SCP
        """
        try:
            self.disconnect()
            
            # Store connection details for SCP
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
            stdin, stdout, stderr = self.client.exec_command("echo 'keepalive'", timeout=3)
            result = stdout.read().decode().strip()
            return result == "keepalive"
        except:
            self.connected = False
            return False
    
    def execute_command(self, command: str, timeout: int = 30) -> Tuple[bool, str, str]:
        """Execute a command on the remote server"""
        if not self.is_connected():
            return False, "", "Not connected"
        
        try:
            stdin, stdout, stderr = self.client.exec_command(command, timeout=timeout)
            
            stdout_data = stdout.read().decode('utf-8', errors='replace')
            stderr_data = stderr.read().decode('utf-8', errors='replace')
            exit_code = stdout.channel.recv_exit_status()
            
            success = exit_code == 0
            return success, stdout_data, stderr_data
            
        except Exception as e:
            self.logger.error(f"Command execution error: {e}")
            return False, "", str(e)
    
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
    
    def upload_file_via_scp(self, local_path: str, remote_path: str) -> bool:
        """Upload file using scp command"""
        try:
            if not self.hostname or not self.username or not self.password:
                self.logger.error("Connection details not available for SCP")
                return False
            
            # Create remote directory first
            remote_dir = os.path.dirname(remote_path)
            if remote_dir and remote_dir != '/':
                if not self.ensure_remote_directory(remote_dir):
                    return False
            
            # Prepare scp command
            remote_target = f"{self.username}@{self.hostname}:{remote_path}"
            
            # Use scp with -O flag (legacy mode) and password via sshpass if available
            try:
                # Try with sshpass first (if available)
                scp_cmd = [
                    "sshpass", "-p", self.password,
                    "scp", "-O", "-o", "StrictHostKeyChecking=no",
                    "-o", "UserKnownHostsFile=/dev/null",
                    "-o", "LogLevel=ERROR",
                    local_path, remote_target
                ]
                
                result = subprocess.run(
                    scp_cmd,
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                if result.returncode == 0:
                    self.logger.info(f"File uploaded via scp (sshpass): {local_path} -> {remote_path}")
                    return True
                else:
                    self.logger.warning(f"sshpass scp failed: {result.stderr}")
                    
            except FileNotFoundError:
                self.logger.info("sshpass not available, trying expect")
            except Exception as e:
                self.logger.warning(f"sshpass scp error: {e}")
            
            # Fallback: Use expect script
            return self.upload_file_via_expect_scp(local_path, remote_path)
                
        except Exception as e:
            self.logger.error(f"SCP upload error: {e}")
            return False
    
    def upload_file_via_expect_scp(self, local_path: str, remote_path: str) -> bool:
        """Upload file using expect script for SCP password automation"""
        try:
            # Create temporary expect script
            expect_script = f"""#!/usr/bin/expect -f
set timeout 60
spawn scp -O -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null {local_path} {self.username}@{self.hostname}:{remote_path}
expect {{
    "password:" {{
        send "{self.password}\\r"
        expect "100%"
        expect eof
    }}
    "Password:" {{
        send "{self.password}\\r"
        expect "100%"
        expect eof
    }}
    timeout {{
        exit 1
    }}
}}
exit 0
"""
            
            # Write expect script to temporary file
            with tempfile.NamedTemporaryFile(mode='w', suffix='.exp', delete=False) as f:
                f.write(expect_script)
                expect_file = f.name
            
            try:
                # Make script executable
                os.chmod(expect_file, 0o755)
                
                # Run expect script
                result = subprocess.run(
                    [expect_file],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                if result.returncode == 0:
                    self.logger.info(f"File uploaded via expect scp: {local_path} -> {remote_path}")
                    return True
                else:
                    self.logger.error(f"Expect SCP failed: {result.stderr}")
                    return False
                    
            finally:
                # Clean up expect script
                try:
                    os.unlink(expect_file)
                except:
                    pass
                    
        except FileNotFoundError:
            self.logger.warning("expect not available")
            return False
        except Exception as e:
            self.logger.error(f"Expect SCP error: {e}")
            return False
    
    def upload_file_via_ssh_cat(self, local_path: str, remote_path: str) -> bool:
        """Upload file using SSH with cat (fallback method)"""
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
        """Upload file with multiple methods"""
        self.logger.info(f"Attempting to upload: {local_path} -> {remote_path}")
        
        # Method 1: Try SCP (preferred)
        if self.upload_file_via_scp(local_path, remote_path):
            return True
        
        # Method 2: Fallback to SSH cat for text files
        try:
            if self.upload_file_via_ssh_cat(local_path, remote_path):
                return True
        except Exception as e:
            self.logger.warning(f"SSH cat method failed: {e}")
        
        self.logger.error("All upload methods failed")
        return False
    
    def download_file_via_scp(self, remote_path: str, local_path: str) -> bool:
        """Download file using scp command"""
        try:
            if not self.hostname or not self.username or not self.password:
                self.logger.error("Connection details not available for SCP")
                return False
            
            # Ensure local directory exists
            local_dir = os.path.dirname(local_path)
            if local_dir:
                os.makedirs(local_dir, exist_ok=True)
            
            # Prepare scp command
            remote_source = f"{self.username}@{self.hostname}:{remote_path}"
            
            # Try with sshpass first
            try:
                scp_cmd = [
                    "sshpass", "-p", self.password,
                    "scp", "-O", "-o", "StrictHostKeyChecking=no",
                    "-o", "UserKnownHostsFile=/dev/null",
                    "-o", "LogLevel=ERROR",
                    remote_source, local_path
                ]
                
                result = subprocess.run(
                    scp_cmd,
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                if result.returncode == 0:
                    self.logger.info(f"File downloaded via scp: {remote_path} -> {local_path}")
                    return True
                else:
                    self.logger.warning(f"sshpass scp download failed: {result.stderr}")
                    
            except FileNotFoundError:
                self.logger.info("sshpass not available for download")
            except Exception as e:
                self.logger.warning(f"sshpass scp download error: {e}")
            
            # Fallback to expect method (similar to upload)
            return self.download_file_via_expect_scp(remote_path, local_path)
                
        except Exception as e:
            self.logger.error(f"SCP download error: {e}")
            return False
    
    def download_file_via_expect_scp(self, remote_path: str, local_path: str) -> bool:
        """Download file using expect script for SCP"""
        try:
            expect_script = f"""#!/usr/bin/expect -f
set timeout 60
spawn scp -O -o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null {self.username}@{self.hostname}:{remote_path} {local_path}
expect {{
    "password:" {{
        send "{self.password}\\r"
        expect "100%"
        expect eof
    }}
    "Password:" {{
        send "{self.password}\\r"
        expect "100%"
        expect eof
    }}
    timeout {{
        exit 1
    }}
}}
exit 0
"""
            
            with tempfile.NamedTemporaryFile(mode='w', suffix='.exp', delete=False) as f:
                f.write(expect_script)
                expect_file = f.name
            
            try:
                os.chmod(expect_file, 0o755)
                
                result = subprocess.run(
                    [expect_file],
                    capture_output=True,
                    text=True,
                    timeout=60
                )
                
                if result.returncode == 0:
                    self.logger.info(f"File downloaded via expect scp: {remote_path} -> {local_path}")
                    return True
                else:
                    self.logger.error(f"Expect SCP download failed: {result.stderr}")
                    return False
                    
            finally:
                try:
                    os.unlink(expect_file)
                except:
                    pass
                    
        except Exception as e:
            self.logger.error(f"Expect SCP download error: {e}")
            return False
    
    def download_file_via_ssh_cat(self, remote_path: str, local_path: str) -> bool:
        """Download file using SSH cat command"""
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
        """Download file with multiple methods"""
        self.logger.info(f"Attempting to download: {remote_path} -> {local_path}")
        
        # Method 1: Try SCP (preferred)
        if self.download_file_via_scp(remote_path, local_path):
            return True
        
        # Method 2: Fallback to SSH cat
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