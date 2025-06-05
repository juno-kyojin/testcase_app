# src/storage/database.py
import os
import sqlite3
import logging
import time
from typing import Dict, List, Any

class TestDatabase:
    """Database handler for test results and settings"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
        self.db_path = os.path.join("data", "history.db")
        
        # Ensure directory exists
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        
        # Initialize database
        self._init_db()
    
    def _init_db(self):
        """Initialize database tables if they don't exist"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Settings table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT
                )
            ''')
            
            # Test results table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS test_results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_name TEXT,
                    file_size INTEGER,
                    test_count INTEGER,
                    send_status TEXT,
                    overall_result TEXT,
                    affects_wan BOOLEAN,
                    affects_lan BOOLEAN,
                    execution_time REAL,
                    target_ip TEXT,
                    target_username TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Test case details table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS test_cases (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    result_id INTEGER,
                    service TEXT,
                    action TEXT,
                    status TEXT,
                    details TEXT,
                    execution_time REAL,
                    FOREIGN KEY (result_id) REFERENCES test_results(id)
                )
            ''')
            
            # Connection log table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS connection_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ip_address TEXT,
                    status TEXT,
                    details TEXT,
                    timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            conn.commit()
            conn.close()
            
        except Exception as e:
            self.logger.error(f"Database initialization error: {e}")
    
    def save_setting(self, key: str, value: str) -> bool:
        """Save a setting to the database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                (key, value)
            )
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving setting {key}: {e}")
            return False
    
    def get_setting(self, key: str, default: str = "") -> str:
        """Get a setting from the database"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
            result = cursor.fetchone()
            
            conn.close()
            
            return result[0] if result else default
            
        except Exception as e:
            self.logger.error(f"Error retrieving setting {key}: {e}")
            return default
    
    def log_connection(self, ip_address: str, status: str, details: str) -> bool:
        """Log a connection attempt"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute(
                "INSERT INTO connection_log (ip_address, status, details) VALUES (?, ?, ?)",
                (ip_address, status, details)
            )
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            self.logger.error(f"Error logging connection: {e}")
            return False
    
    def save_test_file_result(self, **kwargs) -> int:
        """Save test file execution results"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Insert the test result
            cursor.execute(
                """
                INSERT INTO test_results (
                    file_name, file_size, test_count, send_status, overall_result,
                    affects_wan, affects_lan, execution_time, target_ip, target_username
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    kwargs.get("file_name", ""),
                    kwargs.get("file_size", 0),
                    kwargs.get("test_count", 0),
                    kwargs.get("send_status", ""),
                    kwargs.get("overall_result", ""),
                    kwargs.get("affects_wan", False),
                    kwargs.get("affects_lan", False),
                    kwargs.get("execution_time", 0),
                    kwargs.get("target_ip", ""),
                    kwargs.get("target_username", "")
                )
            )
            
            # Get the inserted ID and ensure it's an int
            result_id = cursor.lastrowid
            final_id = result_id if result_id is not None else -1
            
            conn.commit()
            conn.close()
            
            return final_id
            
        except Exception as e:
            self.logger.error(f"Error saving test result: {e}")
            return -1
    
    def save_test_case_results(self, result_id: int, test_cases: List[Dict]) -> bool:
        """Save individual test case results with more detailed information"""
        try:
            if not test_cases:
                return True
                
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Get file name for this result ID
            cursor.execute("SELECT file_name FROM test_results WHERE id = ?", (result_id,))
            row = cursor.fetchone()
            if row:
                file_name = row[0]
                # Extract service and action from filename if test case has "unknown" service
                base_name = os.path.splitext(file_name)[0]
                parts = base_name.split('_')
                default_service = parts[0] if parts else "unknown"
                default_action = '_'.join(parts[1:]) if len(parts) > 1 else ""
                
                # Log extracted information
                self.logger.info(f"Extracted from filename {file_name}: service={default_service}, action={default_action}")
                
                # Update test cases with unknown service
                for test in test_cases:
                    if test.get("service") == "unknown":
                        test["service"] = default_service
                        test["action"] = default_action
                        # Cập nhật thông báo chi tiết với service và action mới
                        status = test.get("status", "pass")
                        status_text = "completed successfully" if status == "pass" else "failed"
                        test["details"] = f"{default_service} {default_action} {status_text}"
                        
                        self.logger.info(f"Updated test case: {test['service']}.{test['action']} - {test['details']}")
            
            # Insert test cases
            for test in test_cases:
                cursor.execute(
                    """
                    INSERT INTO test_cases (
                        result_id, service, action, status, details, execution_time
                    ) VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    (
                        result_id,
                        test.get("service", "unknown"),
                        test.get("action", ""),
                        test.get("status", "unknown"),
                        test.get("details", ""),
                        test.get("execution_time", 0)
                    )
                )
            
            # Kiểm tra số bản ghi đã được thêm vào
            cursor.execute("SELECT COUNT(*) FROM test_cases WHERE result_id = ?", (result_id,))
            count = cursor.fetchone()[0]
            self.logger.info(f"Total {count} test cases saved for result ID {result_id}")
            
            conn.commit()
            conn.close()
            return True
            
        except Exception as e:
            self.logger.error(f"Error saving test case results: {e}")
            return False
    
    def get_recent_history(self, limit: int = 100) -> List[Dict]:
        """Get recent test history"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Return rows as dictionaries
            cursor = conn.cursor()
            
            cursor.execute(
                """
                SELECT * FROM test_results 
                ORDER BY timestamp DESC 
                LIMIT ?
                """,
                (limit,)
            )
            
            results = [dict(row) for row in cursor.fetchall()]
            conn.close()
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error retrieving history: {e}")
            return []
    
    def get_filtered_history(self, where_clause: str = "", limit: int = 100) -> List[Dict]:
        """Get filtered test history"""
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row  # Return rows as dictionaries
            cursor = conn.cursor()
            
            query = f"SELECT * FROM test_results {where_clause} ORDER BY timestamp DESC LIMIT {limit}"
            cursor.execute(query)
            
            results = [dict(row) for row in cursor.fetchall()]
            conn.close()
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error retrieving filtered history: {e}")
            return []
    
    def get_test_details(self, file_name, timestamp=None):
        """Get test case details for a specific file and timestamp"""
        try:
            # Sử dụng self.db_path thay vì hardcode đường dẫn
            connection = sqlite3.connect(self.db_path)
            cursor = connection.cursor()
            
            query = """
            SELECT tc.service, tc.action, tc.status, tc.details, tc.execution_time
            FROM test_cases tc
            JOIN test_results tr ON tc.result_id = tr.id
            WHERE tr.file_name = ?
            """
            
            params = [file_name]
            
            if timestamp:
                query += " AND tr.timestamp LIKE ?"
                params.append(f"{timestamp}%")
                    
            query += " ORDER BY tc.id"
            
            cursor.execute(query, params)
            results = cursor.fetchall()
            
            details = []
            for row in results:
                details.append({
                    "service": row[0],
                    "action": row[1],
                    "status": row[2],
                    "details": row[3],
                    "execution_time": row[4]
                })
                    
            connection.close()
            return details
                
        except Exception as e:
            self.logger.error(f"Error getting test details: {e}")
            return []
    
    def clear_history(self) -> bool:
        """Clear all history data"""
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            cursor.execute("DELETE FROM test_cases")
            cursor.execute("DELETE FROM test_results")
            
            conn.commit()
            conn.close()
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error clearing history: {e}")
            return False