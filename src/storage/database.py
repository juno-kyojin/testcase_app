# Module: database.py
# Purpose: Real SQLite database operations

import sqlite3
import logging
import os
from datetime import datetime
from typing import List, Dict, Any, Optional

class TestDatabase:
    def __init__(self, db_path: str = "data/history.db"):
        self.db_path = db_path
        self.logger = logging.getLogger(__name__)
        self.ensure_database_exists()
    
    def ensure_database_exists(self):
        """Create database and tables if they don't exist"""
        try:
            # Create directory if needed
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            
            with sqlite3.connect(self.db_path) as conn:
                self.create_default_schema(conn)
                conn.commit()
                self.logger.info(f"Database initialized: {self.db_path}")
                
        except Exception as e:
            self.logger.error(f"Database initialization error: {e}")
            # Don't raise - create in-memory fallback
            self.db_path = ":memory:"
    
    def create_default_schema(self, conn):
        """Create default database schema"""
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS test_files (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL DEFAULT (datetime('now')),
                file_name TEXT NOT NULL,
                file_size INTEGER NOT NULL,
                test_count INTEGER NOT NULL,
                send_status TEXT NOT NULL,
                overall_result TEXT,
                affects_wan INTEGER DEFAULT 0,
                affects_lan INTEGER DEFAULT 0,
                execution_time REAL,
                target_ip TEXT NOT NULL,
                target_username TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS test_case_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                test_file_id INTEGER NOT NULL,
                service TEXT NOT NULL,
                action TEXT,
                status TEXT NOT NULL,
                details TEXT,
                execution_time REAL,
                FOREIGN KEY (test_file_id) REFERENCES test_files(id)
            );

            CREATE TABLE IF NOT EXISTS connection_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL DEFAULT (datetime('now')),
                target_ip TEXT NOT NULL,
                connection_type TEXT DEFAULT 'LAN',
                status TEXT NOT NULL,
                details TEXT
            );

            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL,
                updated_at TEXT NOT NULL DEFAULT (datetime('now'))
            );
        """)
    
    def log_connection(self, target_ip: str, status: str, details: str = "", connection_type: str = "LAN"):
        """Log a connection event"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT INTO connection_log (target_ip, connection_type, status, details)
                    VALUES (?, ?, ?, ?)
                """, (target_ip, connection_type, status, details))
                conn.commit()
        except Exception as e:
            self.logger.error(f"Error logging connection: {e}")
    
    def save_test_file_result(self, file_name: str, file_size: int, test_count: int, 
                             send_status: str, overall_result: str, affects_wan: bool, 
                             affects_lan: bool, execution_time: float, target_ip: str, 
                             target_username: str) -> int:
        """
        Save test file result and return the file ID
        """
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("""
                    INSERT INTO test_files 
                    (file_name, file_size, test_count, send_status, overall_result, 
                     affects_wan, affects_lan, execution_time, target_ip, target_username)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (file_name, file_size, test_count, send_status, overall_result,
                      int(affects_wan), int(affects_lan), execution_time, target_ip, target_username))
                
                file_id = cursor.lastrowid
                conn.commit()
                return file_id
                
        except Exception as e:
            self.logger.error(f"Error saving test file result: {e}")
            return -1
    
    def save_test_case_results(self, test_file_id: int, test_results: List[Dict[str, Any]]):
        """Save individual test case results"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                for result in test_results:
                    conn.execute("""
                        INSERT INTO test_case_results 
                        (test_file_id, service, action, status, details, execution_time)
                        VALUES (?, ?, ?, ?, ?, ?)
                    """, (
                        test_file_id,
                        result.get("service", ""),
                        result.get("action", ""),
                        result.get("status", ""),
                        result.get("details", ""),
                        result.get("execution_time", 0.0)
                    ))
                conn.commit()
        except Exception as e:
            self.logger.error(f"Error saving test case results: {e}")
    
    def get_recent_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Get recent test history"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.execute("""
                    SELECT * FROM test_files 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                """, (limit,))
                
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
                
        except Exception as e:
            self.logger.error(f"Error getting history: {e}")
            return []
    
    def save_setting(self, key: str, value: str):
        """Save an application setting"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute("""
                    INSERT OR REPLACE INTO settings (key, value, updated_at)
                    VALUES (?, ?, datetime('now'))
                """, (key, value))
                conn.commit()
        except Exception as e:
            self.logger.error(f"Error saving setting: {e}")
    
    def get_setting(self, key: str, default: str = "") -> str:
        """Get an application setting"""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.execute("SELECT value FROM settings WHERE key = ?", (key,))
                row = cursor.fetchone()
                return row[0] if row else default
        except Exception as e:
            self.logger.error(f"Error getting setting: {e}")
            return default