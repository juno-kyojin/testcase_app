# src/files/manager.py
import os
import json
import logging

class TestFileManager:
    """Test file manager - validates and analyzes test files"""
    
    def __init__(self):
        self.logger = logging.getLogger(__name__)
    
    def validate_json_file(self, file_path):
        """Validate a JSON file and return its contents"""
        try:
            if not os.path.exists(file_path):
                return False, "File not found", None
                
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Check if the file has required structure
            if "test_cases" not in data:
                return False, "Missing 'test_cases' section", None
                
            # Basic validation passed
            return True, "", data
            
        except json.JSONDecodeError as e:
            return False, f"Invalid JSON: {str(e)}", None
        except Exception as e:
            return False, f"Error: {str(e)}", None
    
    def analyze_test_impacts(self, data):
        """Analyze if the test affects network connectivity"""
        impacts = {
            "affects_wan": False,
            "affects_lan": False,
            "restarts_network": False  # Thêm flag cho restart mạng
        }
        
        try:
            test_cases = data.get("test_cases", [])
            
            for test in test_cases:
                service = test.get("service", "").lower()
                action = test.get("action", "").lower()
                params = test.get("params", {})
                
                # Check network restarts
                if "network" in service and any(word in action for word in ["restart", "reset", "reboot"]):
                    impacts["restarts_network"] = True
                    impacts["affects_wan"] = True
                    impacts["affects_lan"] = True
                    
                # Check WAN impacts
                elif any(keyword in service for keyword in ["wan", "internet", "ppp", "dhcp", "modem"]):
                    impacts["affects_wan"] = True
                    
                # Check LAN impacts
                elif any(keyword in service for keyword in ["lan", "network", "interface", "wifi", "ethernet"]):
                    impacts["affects_lan"] = True
                    
                # Check by commands in params
                if isinstance(params, dict):
                    cmd = str(params.get("command", "")).lower()
                    if cmd:
                        if "restart" in cmd and any(svc in cmd for svc in ["network", "wan", "firewall", "interface"]):
                            impacts["restarts_network"] = True
                            impacts["affects_wan"] = True
                            impacts["affects_lan"] = True
            
        except Exception as e:
            self.logger.error(f"Error analyzing test impacts: {e}")
        
        return impacts
    
    def get_test_case_count(self, data):
        """Get the number of test cases in a file"""
        try:
            return len(data.get("test_cases", []))
        except:
            return 0