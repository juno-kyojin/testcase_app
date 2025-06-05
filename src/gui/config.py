import os
import logging
import platform
from tkinter import ttk

class AppConfig:
    DEFAULT_TIMEOUT = 120
    RESULT_CHECK_INTERVAL = 3
    MAX_RECONNECT_ATTEMPTS = 3
    CONNECTION_RETRY_DELAY = 2
    FILE_SIZE_THRESHOLD = 50
    TEMP_CLEANUP_HOURS = 1
    MAX_FILE_RETRIES = 2
    
    # File patterns
    RESULT_FILE_PATTERN = "{base}_*.json"
    
    # Timeouts
    SSH_CONNECT_TIMEOUT = 15
    FILE_UPLOAD_TIMEOUT = 60
    COMMAND_TIMEOUT = 30

class GUIConfig:
    @staticmethod
    def setup_window_geometry(root):
        """Calculate and set appropriate window size and position"""
        screen_width = root.winfo_screenwidth()
        screen_height = root.winfo_screenheight()
        
        window_width = min(int(screen_width * 0.8), 1200)
        window_height = min(int(screen_height * 0.8), 800)
        window_width = max(window_width, 800)
        window_height = max(window_height, 600)
        
        x_position = (screen_width - window_width) // 2
        y_position = (screen_height - window_height) // 2
        
        root.geometry(f"{window_width}x{window_height}+{x_position}+{y_position}")
        root.minsize(800, 650)
    
    @staticmethod
    def setup_styles():
        """Setup enhanced UI styles"""
        style = ttk.Style()
        
        try:
            style.theme_use('vista')
        except:
            pass
            
        style.configure("TButton", padding=6)
        style.configure("TLabel", padding=3)
        style.configure("TFrame", padding=5)
        
        style.configure("Success.TLabel", foreground="green")
        style.configure("Error.TLabel", foreground="red")
        style.configure("Warning.TLabel", foreground="orange")
        
        return style
    
    @staticmethod
    def setup_logging():
        """Setup enhanced logging configuration"""
        log_dir = "logs"
        os.makedirs(log_dir, exist_ok=True)
        
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(os.path.join(log_dir, 'app.log')),
                logging.StreamHandler()
            ]
        )
        logger = logging.getLogger(__name__)
        logger.info(f"Windows application started by {os.environ.get('USERNAME', 'unknown')}")
        return logger
