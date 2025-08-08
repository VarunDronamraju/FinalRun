#!/usr/bin/env python3
"""
RAG Desktop Application - Main Entry Point
Professional PyQt6 desktop interface for RAG system
"""

import sys
import os
import logging
import signal
from pathlib import Path
from typing import Optional

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from PyQt6.QtWidgets import QApplication, QMessageBox, QSplashScreen
from PyQt6.QtCore import Qt, QTimer, QThread, pyqtSignal
from PyQt6.QtGui import QPixmap, QPainter, QFont, QIcon

from main_window import MainWindow
from session_manager import SessionManager

# Configure logging
def setup_logging():
    """Setup application logging"""
    log_dir = Path(__file__).parent
    log_file = log_dir / "rag_desktop.log"
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # File handler
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    
    # Console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(formatter)
    
    # Root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    
    # Suppress some noisy loggers
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('httpcore').setLevel(logging.WARNING)
    
    return logging.getLogger(__name__)

class SplashScreen(QSplashScreen):
    """Custom splash screen for application startup"""
    
    def __init__(self):
        # Create a simple colored pixmap for splash
        pixmap = QPixmap(400, 300)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Background gradient
        from PyQt6.QtGui import QLinearGradient, QBrush
        gradient = QLinearGradient(0, 0, 400, 300)
        gradient.setColorAt(0, Qt.GlobalColor.darkBlue)
        gradient.setColorAt(1, Qt.GlobalColor.darkCyan)
        painter.fillRect(pixmap.rect(), QBrush(gradient))
        
        # Title text
        painter.setPen(Qt.GlobalColor.white)
        painter.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        painter.drawText(pixmap.rect(), Qt.AlignmentFlag.AlignCenter, "RAG Desktop\n\nLoading...")
        
        painter.end()
        
        super().__init__(pixmap)
        self.setWindowFlags(Qt.WindowType.SplashScreen | Qt.WindowType.FramelessWindowHint)
        
    def showMessage(self, message: str):
        """Show message on splash screen"""
        super().showMessage(
            message, 
            Qt.AlignmentFlag.AlignBottom | Qt.AlignmentFlag.AlignCenter,
            Qt.GlobalColor.white
        )
        QApplication.processEvents()

class StartupWorker(QThread):
    """Worker thread for application startup tasks"""
    
    progress_updated = pyqtSignal(str)
    startup_completed = pyqtSignal(bool, str)
    
    def __init__(self):
        super().__init__()
        
    def run(self):
        """Run startup tasks"""
        try:
            self.progress_updated.emit("Initializing session manager...")
            self.msleep(500)
            
            # Initialize session manager
            session_manager = SessionManager()
            
            self.progress_updated.emit("Checking dependencies...")
            self.msleep(300)
            
            # Check if required modules are available
            try:
                import httpx
                import json
            except ImportError as e:
                self.startup_completed.emit(False, f"Missing dependency: {e}")
                return
                
            self.progress_updated.emit("Loading application settings...")
            self.msleep(300)
            
            # Cleanup old cache
            session_manager.cleanup_old_cache(days=7)
            
            self.progress_updated.emit("Ready to launch!")
            self.msleep(200)
            
            self.startup_completed.emit(True, "Startup completed successfully")
            
        except Exception as e:
            self.startup_completed.emit(False, f"Startup failed: {e}")

class RAGDesktopApp(QApplication):
    """Main application class"""
    
    def __init__(self, sys_argv):
        super().__init__(sys_argv)
        
        # Application properties
        self.setApplicationName("RAG Desktop")
        self.setApplicationDisplayName("RAG Desktop - AI Document Assistant")
        self.setApplicationVersion("1.0.0")
        self.setOrganizationName("RAG Desktop")
        self.setOrganizationDomain("ragdesktop.local")
        
        # High DPI support (PyQt6 handles this automatically)
        
        # Set application icon (if available)
        self.setWindowIcon(self.style().standardIcon(self.style().StandardPixmap.SP_ComputerIcon))
        
        # Main window
        self.main_window: Optional[MainWindow] = None
        self.splash: Optional[SplashScreen] = None
        
        # Setup signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)
        
        # Timer to process signals
        self.signal_timer = QTimer()
        self.signal_timer.timeout.connect(lambda: None)
        self.signal_timer.start(500)
        
    def signal_handler(self, signum, frame):
        """Handle system signals for graceful shutdown"""
        logger.info(f"Received signal {signum}, initiating shutdown...")
        self.quit()
        
    def show_splash(self):
        """Show splash screen during startup"""
        self.splash = SplashScreen()
        self.splash.show()
        
        # Start startup worker
        self.startup_worker = StartupWorker()
        self.startup_worker.progress_updated.connect(self.splash.showMessage)
        self.startup_worker.startup_completed.connect(self.on_startup_completed)
        self.startup_worker.start()
        
    def on_startup_completed(self, success: bool, message: str):
        """Handle startup completion"""
        if success:
            logger.info("Application startup completed successfully")
            self.launch_main_window()
        else:
            logger.error(f"Startup failed: {message}")
            self.show_startup_error(message)
            
    def launch_main_window(self):
        """Launch the main application window"""
        try:
            # Hide splash screen
            if self.splash:
                self.splash.close()
                self.splash = None
                
            # Create and show main window
            self.main_window = MainWindow()
            self.main_window.show()
            
            logger.info("Main window launched successfully")
            
        except Exception as e:
            logger.error(f"Failed to launch main window: {e}")
            self.show_startup_error(f"Failed to launch application: {e}")
            
    def show_startup_error(self, error_message: str):
        """Show startup error dialog"""
        if self.splash:
            self.splash.close()
            self.splash = None
            
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Icon.Critical)
        msg.setWindowTitle("Startup Error")
        msg.setText("Failed to start RAG Desktop")
        msg.setInformativeText(f"Error: {error_message}")
        msg.setDetailedText(
            "Please ensure:\n"
            "• Python 3.8+ is installed\n"
            "• All dependencies are installed (pip install -r requirements-frontend.txt)\n"
            "• PyQt6 is properly configured\n"
            "• No other instance is running\n\n"
            "Check the log file for more details."
        )
        msg.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg.exec()
        
        self.quit()

def check_single_instance():
    """Check if another instance is already running"""
    import tempfile
    import fcntl
    
    try:
        # Create lock file
        lock_file_path = Path(tempfile.gettempdir()) / "rag_desktop.lock"
        lock_file = open(lock_file_path, 'w')
        fcntl.lockf(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
        
        # Write PID to lock file
        lock_file.write(str(os.getpid()))
        lock_file.flush()
        
        return True, lock_file
        
    except (IOError, OSError):
        return False, None

def show_already_running_dialog():
    """Show dialog when another instance is already running"""
    app = QApplication(sys.argv)
    
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Icon.Information)
    msg.setWindowTitle("RAG Desktop")
    msg.setText("RAG Desktop is already running")
    msg.setInformativeText(
        "Another instance of RAG Desktop is already running.\n\n"
        "Please check your system tray or taskbar."
    )
    msg.setStandardButtons(QMessageBox.StandardButton.Ok)
    msg.exec()
    
    sys.exit(0)

def check_dependencies():
    """Check if all required dependencies are available"""
    required_modules = [
        ('PyQt6', 'PyQt6.QtWidgets'),
        ('httpx', 'httpx'),
        ('pathlib', 'pathlib'),
        ('json', 'json'),
    ]
    
    missing_modules = []
    
    for module_name, import_name in required_modules:
        try:
            __import__(import_name)
        except ImportError:
            missing_modules.append(module_name)
    
    if missing_modules:
        print(f"❌ Missing required dependencies: {', '.join(missing_modules)}")
        print("\nPlease install them using:")
        print("pip install -r requirements-frontend.txt")
        return False
        
    return True

def main():
    """Main application entry point"""
    print("🚀 Starting RAG Desktop Application...")
    
    # Check dependencies first
    if not check_dependencies():
        sys.exit(1)
        
    # Setup logging
    global logger
    logger = setup_logging()
    logger.info("=== RAG Desktop Application Starting ===")
    
    try:
        # Check for single instance (Unix-like systems only)
        if hasattr(os, 'fork'):
            is_single, lock_file = check_single_instance()
            if not is_single:
                show_already_running_dialog()
                return 1
        
        # Create application
        app = RAGDesktopApp(sys.argv)
        
        # Set up exception handling
        def handle_exception(exc_type, exc_value, exc_traceback):
            if issubclass(exc_type, KeyboardInterrupt):
                logger.info("Application interrupted by user")
                sys.__excepthook__(exc_type, exc_value, exc_traceback)
                return
                
            logger.error(
                "Unhandled exception:",
                exc_info=(exc_type, exc_value, exc_traceback)
            )
            
        sys.excepthook = handle_exception
        
        # Show splash screen and start application
        app.show_splash()
        
        # Run application
        logger.info("Entering application event loop")
        exit_code = app.exec()
        
        logger.info(f"Application exited with code: {exit_code}")
        return exit_code
        
    except Exception as e:
        logger.error(f"Critical error during startup: {e}", exc_info=True)
        print(f"❌ Critical error: {e}")
        return 1
        
    finally:
        logger.info("=== RAG Desktop Application Shutdown ===")

if __name__ == "__main__":
    # Ensure proper encoding for Windows
    if sys.platform.startswith('win'):
        import locale
        try:
            locale.setlocale(locale.LC_ALL, 'en_US.UTF-8')
        except locale.Error:
            pass
    
    # Run application
    exit_code = main()
    sys.exit(exit_code)