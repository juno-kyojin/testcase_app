# Module: connection.py
# Purpose: Real SSH connection management

import paramiko
import logging
import time
from typing import Optional, Tuple

class SSHConnection:
    def __init__(self):
        self.client = None
        self.sftp = None
        self.logger = logging.getLogger(__name__)
        self.connected = False
    
    def connect(self, hostname: str, username: str, password: str, port: int = 22, timeout: int = 10) -> bool:
        """
        Establish SSH connection with password authentication
        Returns: True if successful, False otherwise
        """
        try:
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
            
            # Test connection with a simple command
            stdin, stdout, stderr = self.client.exec_command("echo 'connection_test'", timeout=5)
            result = stdout.read().decode().strip()
            
            if result == "connection_test":
                self.connected = True
                self.logger.info("SSH connection established successfully")
                return True
            else:
                self.logger.error("SSH connection test failed")
                return False
                
        except paramiko.AuthenticationException:
            self.logger.error("Authentication failed")
            return False
        except paramiko.SSHException as e:
            self.logger.error(f"SSH connection error: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Connection error: {e}")
            return False
    
    def disconnect(self):
        """Close SSH connection"""
        try:
            if self.sftp:
                self.sftp.close()
                self.sftp = None
            
            if self.client:
                self.client.close()
                self.client = None
            
            self.connected = False
            self.logger.info("SSH connection closed")
        except Exception as e:
            self.logger.error(f"Error closing connection: {e}")
    
    def is_connected(self) -> bool:
        """Check if connection is still active"""
        if not self.connected or not self.client:
            return False
        
        try:
            # Send a keep-alive packet
            self.client.exec_command("echo 'keepalive'", timeout=5)
            return True
        except:
            self.connected = False
            return False
    
    def execute_command(self, command: str, timeout: int = 30) -> Tuple[bool, str, str]:
        """
        Execute a command on the remote server
        Returns: (success, stdout, stderr)
        """
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
    
    def get_sftp(self):
        """Get SFTP client (create if needed)"""
        if not self.is_connected():
            raise Exception("SSH not connected")
        
        if not self.sftp:
            self.sftp = self.client.open_sftp()
        
        return self.sftp
    
    def upload_file(self, local_path: str, remote_path: str) -> bool:
        """Upload a file to remote server"""
        try:
            sftp = self.get_sftp()
            sftp.put(local_path, remote_path)
            self.logger.info(f"File uploaded: {local_path} -> {remote_path}")
            return True
        except Exception as e:
            self.logger.error(f"File upload error: {e}")
            return False
    
    def download_file(self, remote_path: str, local_path: str) -> bool:
        """Download a file from remote server"""
        try:
            sftp = self.get_sftp()
            sftp.get(remote_path, local_path)
            self.logger.info(f"File downloaded: {remote_path} -> {local_path}")
            return True
        except Exception as e:
            self.logger.error(f"File download error: {e}")
            return False
    
    def file_exists(self, remote_path: str) -> bool:
        """Check if a file exists on remote server"""
        try:
            sftp = self.get_sftp()
            sftp.stat(remote_path)
            return True
        except FileNotFoundError:
            return False
        except Exception as e:
            self.logger.error(f"Error checking file existence: {e}")
            return False