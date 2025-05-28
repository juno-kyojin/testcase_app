# Module: manager.py
# Purpose: Real file management for test cases

import json
import os
import logging
from typing import Dict, List, Any, Optional, Tuple

class TestFileManager:
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def validate_json_file(self, file_path: str) -> Tuple[bool, str, Optional[Dict]]:
        """
        Validate a JSON test case file
        Returns: (is_valid, error_message, parsed_data)
        """
        try:
            # Check file exists and size
            if not os.path.exists(file_path):
                return False, "File does not exist", None
            
            file_size = os.path.getsize(file_path)
            if file_size > 1024 * 1024:  # 1MB limit
                return False, "File size exceeds 1MB limit", None
            
            if file_size == 0:
                return False, "File is empty", None
            
            # Parse JSON
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Validate structure
            if not isinstance(data, dict):
                return False, "Root element must be an object", None
            
            if "test_cases" not in data:
                return False, "Missing 'test_cases' array", None
            
            test_cases = data["test_cases"]
            if not isinstance(test_cases, list):
                return False, "'test_cases' must be an array", None
            
            if len(test_cases) == 0:
                return False, "No test cases found", None
            
            # Validate each test case
            for i, test_case in enumerate(test_cases):
                if not isinstance(test_case, dict):
                    return False, f"Test case #{i} must be an object", None
                
                if "service" not in test_case:
                    return False, f"Test case #{i} missing 'service' field", None
                
                service = test_case["service"]
                if not isinstance(service, str) or not service.strip():
                    return False, f"Test case #{i} 'service' must be a non-empty string", None
            
            self.logger.info(f"File validation successful: {file_path}")
            return True, "", data
            
        except json.JSONDecodeError as e:
            return False, f"Invalid JSON format: {e}", None
        except Exception as e:
            return False, f"File validation error: {e}", None
    
    def analyze_test_impacts(self, data: Dict[str, Any]) -> Dict[str, bool]:
        """
        Analyze test cases to determine network impacts
        Returns: {'affects_wan': bool, 'affects_lan': bool}
        """
        impacts = {"affects_wan": False, "affects_lan": False}
        
        test_cases = data.get("test_cases", [])
        
        for test_case in test_cases:
            service = test_case.get("service", "").lower()
            action = test_case.get("action", "").lower()
            
            # Check for WAN-affecting operations
            if service == "wan":
                if action in ["delete", "remove", "disable", "stop"]:
                    impacts["affects_wan"] = True
            
            # Check for LAN-affecting operations
            if service == "lan":
                if action in ["delete", "remove", "disable", "stop"]:
                    impacts["affects_lan"] = True
            
            # Check for network restart operations
            if service in ["network", "networking"]:
                if action in ["restart", "reload", "reset"]:
                    impacts["affects_wan"] = True
                    impacts["affects_lan"] = True
        
        return impacts
    
    def get_test_case_count(self, data: Dict[str, Any]) -> int:
        """Get number of test cases in the data"""
        return len(data.get("test_cases", []))
    
    def format_test_case_summary(self, data: Dict[str, Any]) -> str:
        """Create a summary string of test cases"""
        test_cases = data.get("test_cases", [])
        
        service_counts = {}
        for test_case in test_cases:
            service = test_case.get("service", "unknown")
            service_counts[service] = service_counts.get(service, 0) + 1
        
        summary_parts = []
        for service, count in service_counts.items():
            summary_parts.append(f"{service}({count})")
        
        return ", ".join(summary_parts)