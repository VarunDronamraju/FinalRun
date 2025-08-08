"""
Advanced System Tray Manager for RAG Desktop Application
Professional system tray integration with background operations
"""

import logging
import os
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional, Dict, Any, Callable

from PyQt6.QtWidgets import (
    QSystemTrayIcon, QMenu, QApplication, QWidget, QVBoxLayout,
    QHBoxLayout, QLabel, QPushButton, QFrame, QProgressBar,
    QTextEdit, QDialog, QDialogButtonBox, QCheckBox, QSpinBox,
    QComboBox, QGroupBox, QFormLayout, QSlider
)
from PyQt6.QtCore import (
    Qt, QTimer, QThread, pyqtSignal, QObject, QPropertyAnimation,
    QEasingCurve, QRect, QPoint, QSize
)
from PyQt6.QtGui import (
    QIcon, QPixmap, QPainter, QLinearGradient, QBrush, QColor,
    QFont, QAction, QPen, QCursor
)

logger = logging.getLogger(__name__)

class NotificationLevel:
    """Notification importance levels"""
    INFO = "info"
    SUCCESS = "success"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"

class TrayNotification:
    """Enhanced notification with metadata"""
    
    def __init__(self, title: str, message: str, level: str = NotificationLevel.INFO, 
                 duration: int = 5000, action_callback: Optional[Callable] = None):
        self.title = title
        self.message = message
        self.level = level
        self.duration = duration
        self.action_callback = action_callback
        self.timestamp = datetime.now()
        self.id = f"{self.timestamp.timestamp()}_{hash(message)}"

class BackgroundTaskManager(QObject):
    """Manages background tasks and monitoring"""
    
    task_completed = pyqtSignal(str, dict)  # task_id, result
    task_failed = pyqtSignal(str, str)      # task_id, error
    status_updated = pyqtSignal(str, str)   # task_id, status
    
    def __init__(self):
        super().__init__()
        self.active_tasks: Dict[str, QThread] = {}
        self.task_history = []
        
    def start_task(self, task_id: str, task_thread: QThread):
        """Start a background task"""
        if task_id in self.active_tasks:
            logger.warning(f"Task {task_id} already running")
            return False
            
        self.active_tasks[task_id] = task_thread
        task_thread.finished.connect(lambda: self.on_task_finished(task_id))
        task_thread.start()
        
        self.status_updated.emit(task_id, "started")
        logger.info(f"Background task started: {task_id}")
        return True
        
    def on_task_finished(self, task_id: str):
        """Handle task completion"""
        if task_id in self.active_tasks:
            del self.active_tasks[task_id]
            
        self.task_history.append({
            "task_id": task_id,
            "completed_at": datetime.now(),
            "status": "completed"
        })
        
        self.status_updated.emit(task_id, "completed")
        
    def stop_task(self, task_id: str) -> bool:
        """Stop a running task"""
        if task_id in self.active_tasks:
            thread = self.active_tasks[task_id]
            thread.terminate()
            thread.wait(3000)  # Wait up to 3 seconds
            
            if thread.isRunning():
                thread.kill()
                
            del self.active_tasks[task_id]
            self.status_updated.emit(task_id, "stopped")
            return True
        return False
        
    def get_active_tasks(self) -> Dict[str, str]:
        """Get currently active tasks"""
        return {task_id: "running" for task_id in self.active_tasks.keys()}

class SystemResourceMonitor(QThread):
    """Monitor system resources and application health"""
    
    resource_update = pyqtSignal(dict)
    health_alert = pyqtSignal(str, str)  # level, message
    
    def __init__(self):
        super().__init__()
        self.monitoring = False
        self.interval = 30  # seconds
        
    def run(self):
        """Monitor system resources"""
        self.monitoring = True
        
        while self.monitoring:
            try:
                # Get system metrics
                metrics = self.collect_metrics()
                self.resource_update.emit(metrics)
                
                # Check for alerts
                self.check_health_alerts(metrics)
                
                self.msleep(self.interval * 1000)
                
            except Exception as e:
                logger.error(f"Resource monitoring error: {e}")
                self.msleep(5000)  # Brief pause on error
                
    def collect_metrics(self) -> Dict[str, Any]:
        """Collect system and application metrics"""
        import psutil
        
        # Get current process
        process = psutil.Process()
        
        return {
            "timestamp": datetime.now(),
            "cpu_percent": psutil.cpu_percent(interval=1),
            "memory_percent": psutil.virtual_memory().percent,
            "disk_percent": psutil.disk_usage('/').percent if os.name != 'nt' else psutil.disk_usage('C:\\').percent,
            "app_memory_mb": process.memory_info().rss / 1024 / 1024,
            "app_cpu_percent": process.cpu_percent(),
            "app_threads": process.num_threads(),
            "network_active": self.check_network_activity()
        }
        
    def check_network_activity(self) -> bool:
        """Check if there's network activity"""
        try:
            import psutil
            net_io = psutil.net_io_counters()
            return net_io.bytes_sent > 0 or net_io.bytes_recv > 0
        except:
            return False
            
    def check_health_alerts(self, metrics: Dict[str, Any]):
        """Check for health alerts based on metrics"""
        # High memory usage
        if metrics["memory_percent"] > 90:
            self.health_alert.emit("critical", f"System memory usage high: {metrics['memory_percent']:.1f}%")
        elif metrics["memory_percent"] > 80:
            self.health_alert.emit("warning", f"System memory usage: {metrics['memory_percent']:.1f}%")
            
        # High app memory usage
        if metrics["app_memory_mb"] > 500:
            self.health_alert.emit("warning", f"RAG Desktop using {metrics['app_memory_mb']:.1f} MB memory")
            
        # High CPU usage
        if metrics["cpu_percent"] > 90:
            self.health_alert.emit("warning", f"High CPU usage: {metrics['cpu_percent']:.1f}%")
            
    def stop_monitoring(self):
        """Stop resource monitoring"""
        self.monitoring = False

class TrayTooltipWidget(QWidget):
    """Custom tooltip widget for system tray"""
    
    def __init__(self, metrics: Dict[str, Any]):
        super().__init__()
        self.metrics = metrics
        self.setup_ui()
        
    def setup_ui(self):
        """Setup tooltip UI"""
        self.setWindowFlags(Qt.WindowType.ToolTip | Qt.WindowType.FramelessWindowHint)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 10, 10, 10)
        
        # Background frame
        frame = QFrame()
        frame.setStyleSheet("""
            QFrame {
                background: rgba(31, 41, 55, 0.95);
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 8px;
                padding: 8px;
            }
        """)
        
        frame_layout = QVBoxLayout(frame)
        
        # Title
        title = QLabel("🤖 RAG Desktop Status")
        title.setStyleSheet("color: #3b82f6; font-weight: bold; font-size: 14px;")
        frame_layout.addWidget(title)
        
        # Metrics
        if self.metrics:
            cpu_label = QLabel(f"💻 CPU: {self.metrics.get('cpu_percent', 0):.1f}%")
            memory_label = QLabel(f"🧠 Memory: {self.metrics.get('memory_percent', 0):.1f}%")
            app_memory_label = QLabel(f"📱 App: {self.metrics.get('app_memory_mb', 0):.1f} MB")
            
            for label in [cpu_label, memory_label, app_memory_label]:
                label.setStyleSheet("color: #e5e5e5; font-size: 12px;")
                frame_layout.addWidget(label)
        
        # Status
        status_label = QLabel("✅ Running")
        status_label.setStyleSheet("color: #10b981; font-size: 12px;")
        frame_layout.addWidget(status_label)
        
        layout.addWidget(frame)

class SystemTraySettings(QDialog):
    """Settings dialog for system tray preferences"""
    
    def __init__(self, current_settings: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.current_settings = current_settings
        self.setup_ui()
        
    def setup_ui(self):
        """Setup settings UI"""
        self.setWindowTitle("System Tray Settings")
        self.setModal(True)
        self.setFixedSize(400, 500)
        
        layout = QVBoxLayout(self)
        
        # Notifications group
        notifications_group = QGroupBox("Notifications")
        notifications_layout = QFormLayout(notifications_group)
        
        self.show_notifications = QCheckBox()
        self.show_notifications.setChecked(self.current_settings.get("show_notifications", True))
        notifications_layout.addRow("Show notifications:", self.show_notifications)
        
        self.notification_duration = QSpinBox()
        self.notification_duration.setRange(1000, 10000)
        self.notification_duration.setSuffix(" ms")
        self.notification_duration.setValue(self.current_settings.get("notification_duration", 5000))
        notifications_layout.addRow("Duration:", self.notification_duration)
        
        # Monitoring group
        monitoring_group = QGroupBox("System Monitoring")
        monitoring_layout = QFormLayout(monitoring_group)
        
        self.enable_monitoring = QCheckBox()
        self.enable_monitoring.setChecked(self.current_settings.get("enable_monitoring", True))
        monitoring_layout.addRow("Enable monitoring:", self.enable_monitoring)
        
        self.monitoring_interval = QSpinBox()
        self.monitoring_interval.setRange(10, 300)
        self.monitoring_interval.setSuffix(" seconds")
        self.monitoring_interval.setValue(self.current_settings.get("monitoring_interval", 30))
        monitoring_layout.addRow("Update interval:", self.monitoring_interval)
        
        # Behavior group
        behavior_group = QGroupBox("Behavior")
        behavior_layout = QFormLayout(behavior_group)
        
        self.minimize_to_tray = QCheckBox()
        self.minimize_to_tray.setChecked(self.current_settings.get("minimize_to_tray", True))
        behavior_layout.addRow("Minimize to tray:", self.minimize_to_tray)
        
        self.close_to_tray = QCheckBox()
        self.close_to_tray.setChecked(self.current_settings.get("close_to_tray", True))
        behavior_layout.addRow("Close to tray:", self.close_to_tray)
        
        self.start_minimized = QCheckBox()
        self.start_minimized.setChecked(self.current_settings.get("start_minimized", False))
        behavior_layout.addRow("Start minimized:", self.start_minimized)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel |
            QDialogButtonBox.StandardButton.RestoreDefaults
        )
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        buttons.button(QDialogButtonBox.StandardButton.RestoreDefaults).clicked.connect(self.restore_defaults)
        
        # Layout assembly
        layout.addWidget(notifications_group)
        layout.addWidget(monitoring_group)
        layout.addWidget(behavior_group)
        layout.addStretch()
        layout.addWidget(buttons)
        
    def get_settings(self) -> Dict[str, Any]:
        """Get current settings from UI"""
        return {
            "show_notifications": self.show_notifications.isChecked(),
            "notification_duration": self.notification_duration.value(),
            "enable_monitoring": self.enable_monitoring.isChecked(),
            "monitoring_interval": self.monitoring_interval.value(),
            "minimize_to_tray": self.minimize_to_tray.isChecked(),
            "close_to_tray": self.close_to_tray.isChecked(),
            "start_minimized": self.start_minimized.isChecked()
        }
        
    def restore_defaults(self):
        """Restore default settings"""
        self.show_notifications.setChecked(True)
        self.notification_duration.setValue(5000)
        self.enable_monitoring.setChecked(True)
        self.monitoring_interval.setValue(30)
        self.minimize_to_tray.setChecked(True)
        self.close_to_tray.setChecked(True)
        self.start_minimized.setChecked(False)

class AdvancedSystemTrayManager(QObject):
    """Advanced system tray manager with background operations"""
    
    # Signals
    tray_activated = pyqtSignal(str)  # activation_type
    notification_clicked = pyqtSignal(str)  # notification_id
    settings_changed = pyqtSignal(dict)  # new_settings
    
    def __init__(self, main_window, session_manager=None):
        super().__init__()
        self.main_window = main_window
        self.session_manager = session_manager
        
        # Components
        self.tray_icon: Optional[QSystemTrayIcon] = None
        self.task_manager = BackgroundTaskManager()
        self.resource_monitor = SystemResourceMonitor()
        
        # State
        self.is_initialized = False
        self.notification_queue = []
        self.current_metrics = {}
        self.settings = self.load_settings()
        
        # Timers (initialized later to avoid thread issues)
        self.notification_timer = None
        self._initialize_timers()
        
        # Initialize if system tray is available
        if QSystemTrayIcon.isSystemTrayAvailable():
            self.initialize_tray()
        else:
            logger.warning("System tray not available on this platform")
            
    def _initialize_timers(self):
        """Initialize timers in the main thread"""
        try:
            # Only initialize if we're in the main thread
            from PyQt6.QtCore import QThread
            if QThread.currentThread() == QApplication.instance().thread():
                self.notification_timer = QTimer()
                self.notification_timer.timeout.connect(self.process_notification_queue)
                self.notification_timer.start(1000)  # Check every second
                
                logger.info("System tray timers initialized")
            else:
                logger.warning("System tray timers not initialized - not in main thread")
        except Exception as e:
            logger.error(f"Failed to initialize system tray timers: {e}")
            
    def load_settings(self) -> Dict[str, Any]:
        """Load tray settings from session manager"""
        if self.session_manager:
            return self.session_manager.get_user_preference("tray_settings", {
                "show_notifications": True,
                "notification_duration": 5000,
                "enable_monitoring": True,
                "monitoring_interval": 30,
                "minimize_to_tray": True,
                "close_to_tray": True,
                "start_minimized": False
            })
        return {}
        
    def save_settings(self):
        """Save tray settings to session manager"""
        if self.session_manager:
            self.session_manager.set_user_preference("tray_settings", self.settings)
            
    def initialize_tray(self):
        """Initialize system tray icon and menu"""
        try:
            # Create tray icon
            self.tray_icon = QSystemTrayIcon()
            self.update_tray_icon()
            
            # Create context menu
            self.create_tray_menu()
            
            # Connect signals
            self.tray_icon.activated.connect(self.on_tray_activated)
            self.tray_icon.messageClicked.connect(self.on_notification_clicked)
            
            # Setup background monitoring
            if self.settings.get("enable_monitoring", True):
                self.start_resource_monitoring()
                
            # Show tray icon
            self.tray_icon.show()
            self.is_initialized = True
            
            logger.info("System tray initialized successfully")
            
            # Show startup notification
            if self.settings.get("show_notifications", True):
                self.show_notification(
                    "RAG Desktop Started",
                    "Application is running in the system tray",
                    NotificationLevel.INFO
                )
                
        except Exception as e:
            logger.error(f"Failed to initialize system tray: {e}")
            
    def create_tray_icon(self) -> QIcon:
        """Create dynamic tray icon based on status"""
        # Create 16x16 pixmap for tray icon
        pixmap = QPixmap(16, 16)
        pixmap.fill(Qt.GlobalColor.transparent)
        
        painter = QPainter(pixmap)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Background circle
        if self.main_window and hasattr(self.main_window, 'is_authenticated') and self.main_window.is_authenticated:
            # Green for authenticated
            painter.setBrush(QBrush(QColor(16, 185, 129)))
        else:
            # Blue for normal
            painter.setBrush(QBrush(QColor(59, 130, 246)))
            
        painter.setPen(QPen(QColor(255, 255, 255), 1))
        painter.drawEllipse(2, 2, 12, 12)
        
        # Inner dot
        painter.setBrush(QBrush(QColor(255, 255, 255)))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(6, 6, 4, 4)
        
        painter.end()
        
        return QIcon(pixmap)
        
    def update_tray_icon(self):
        """Update tray icon appearance"""
        if self.tray_icon:
            icon = self.create_tray_icon()
            self.tray_icon.setIcon(icon)
            
            # Update tooltip
            tooltip = "RAG Desktop - AI Document Assistant"
            if self.current_metrics:
                cpu = self.current_metrics.get("cpu_percent", 0)
                memory = self.current_metrics.get("app_memory_mb", 0)
                tooltip += f"\nCPU: {cpu:.1f}% | Memory: {memory:.1f} MB"
                
            self.tray_icon.setToolTip(tooltip)
            
    def create_tray_menu(self):
        """Create system tray context menu"""
        menu = QMenu()
        menu.setStyleSheet("""
            QMenu {
                background: rgba(31, 41, 55, 0.95);
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 8px;
                color: #e5e5e5;
                padding: 8px;
            }
            QMenu::item {
                background: transparent;
                padding: 8px 16px;
                border-radius: 4px;
            }
            QMenu::item:selected {
                background: rgba(59, 130, 246, 0.2);
            }
            QMenu::separator {
                height: 1px;
                background: rgba(255, 255, 255, 0.1);
                margin: 4px 0;
            }
        """)
        
        # Show/Hide window
        if self.main_window.isVisible():
            show_action = menu.addAction("🔽 Hide Window")
            show_action.triggered.connect(self.hide_window)
        else:
            show_action = menu.addAction("🔼 Show Window")
            show_action.triggered.connect(self.show_window)
            
        menu.addSeparator()
        
        # Quick actions
        new_chat_action = menu.addAction("💬 New Chat")
        new_chat_action.triggered.connect(self.start_new_chat)
        
        upload_action = menu.addAction("📄 Upload Documents")
        upload_action.triggered.connect(self.open_document_upload)
        
        menu.addSeparator()
        
        # Status and monitoring
        status_action = menu.addAction("📊 System Status")
        status_action.triggered.connect(self.show_system_status)
        
        if self.settings.get("enable_monitoring", True):
            if self.resource_monitor.isRunning():
                monitor_action = menu.addAction("⏸️ Pause Monitoring")
                monitor_action.triggered.connect(self.pause_monitoring)
            else:
                monitor_action = menu.addAction("▶️ Resume Monitoring")
                monitor_action.triggered.connect(self.resume_monitoring)
        
        menu.addSeparator()
        
        # Settings
        settings_action = menu.addAction("⚙️ Tray Settings")
        settings_action.triggered.connect(self.show_tray_settings)
        
        menu.addSeparator()
        
        # Quit
        quit_action = menu.addAction("🚪 Quit Application")
        quit_action.triggered.connect(self.quit_application)
        
        self.tray_icon.setContextMenu(menu)
        
    def start_resource_monitoring(self):
        """Start system resource monitoring"""
        if not self.resource_monitor.isRunning():
            self.resource_monitor.resource_update.connect(self.on_resource_update)
            self.resource_monitor.health_alert.connect(self.on_health_alert)
            self.resource_monitor.interval = self.settings.get("monitoring_interval", 30)
            self.resource_monitor.start()
            
    def on_resource_update(self, metrics: Dict[str, Any]):
        """Handle resource update"""
        self.current_metrics = metrics
        self.update_tray_icon()
        
    def on_health_alert(self, level: str, message: str):
        """Handle health alerts"""
        if self.settings.get("show_notifications", True):
            self.show_notification(
                "System Alert",
                message,
                level,
                duration=8000
            )
            
    def show_notification(self, title: str, message: str, level: str = NotificationLevel.INFO, 
                         duration: int = None, action_callback: Optional[Callable] = None):
        """Show system tray notification"""
        if not self.settings.get("show_notifications", True):
            return
            
        if duration is None:
            duration = self.settings.get("notification_duration", 5000)
            
        notification = TrayNotification(title, message, level, duration, action_callback)
        self.notification_queue.append(notification)
        
    def process_notification_queue(self):
        """Process pending notifications"""
        if not self.notification_queue or not self.tray_icon:
            return
            
        notification = self.notification_queue.pop(0)
        
        # Determine icon based on level
        icon_map = {
            NotificationLevel.INFO: QSystemTrayIcon.MessageIcon.Information,
            NotificationLevel.SUCCESS: QSystemTrayIcon.MessageIcon.Information,
            NotificationLevel.WARNING: QSystemTrayIcon.MessageIcon.Warning,
            NotificationLevel.ERROR: QSystemTrayIcon.MessageIcon.Critical,
            NotificationLevel.CRITICAL: QSystemTrayIcon.MessageIcon.Critical
        }
        
        icon = icon_map.get(notification.level, QSystemTrayIcon.MessageIcon.Information)
        
        # Show notification
        self.tray_icon.showMessage(
            notification.title,
            notification.message,
            icon,
            notification.duration
        )
        
        logger.info(f"Showed notification: {notification.title}")
        
    # Tray interaction handlers
    def on_tray_activated(self, reason):
        """Handle tray icon activation"""
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            # Single click - toggle window visibility
            if self.main_window.isVisible() and self.main_window.isActiveWindow():
                self.hide_window()
            else:
                self.show_window()
                
        elif reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            # Double click - always show window
            self.show_window()
            
        elif reason == QSystemTrayIcon.ActivationReason.MiddleClick:
            # Middle click - new chat
            self.start_new_chat()
            
        self.tray_activated.emit(str(reason))
        
    def on_notification_clicked(self):
        """Handle notification click"""
        self.show_window()
        self.notification_clicked.emit("notification_clicked")
        
    # Window management
    def show_window(self):
        """Show and activate main window"""
        self.main_window.show()
        self.main_window.raise_()
        self.main_window.activateWindow()
        
        # Update tray menu
        self.create_tray_menu()
        
    def hide_window(self):
        """Hide main window"""
        self.main_window.hide()
        
        # Update tray menu
        self.create_tray_menu()
        
    # Quick actions
    def start_new_chat(self):
        """Start new chat from tray"""
        self.show_window()
        if hasattr(self.main_window, 'new_chat'):
            self.main_window.new_chat()
            
    def open_document_upload(self):
        """Open document upload from tray"""
        self.show_window()
        if hasattr(self.main_window, 'upload_documents'):
            self.main_window.upload_documents()
            
    def show_system_status(self):
        """Show system status dialog"""
        status_dialog = SystemStatusDialog(self.current_metrics, self.task_manager, self.main_window)
        status_dialog.exec()
        
    def show_tray_settings(self):
        """Show tray settings dialog"""
        settings_dialog = SystemTraySettings(self.settings, self.main_window)
        if settings_dialog.exec() == QDialog.DialogCode.Accepted:
            new_settings = settings_dialog.get_settings()
            self.update_settings(new_settings)
            
    def update_settings(self, new_settings: Dict[str, Any]):
        """Update tray settings"""
        self.settings.update(new_settings)
        self.save_settings()
        
        # Apply changes
        if new_settings.get("enable_monitoring", True) and not self.resource_monitor.isRunning():
            self.start_resource_monitoring()
        elif not new_settings.get("enable_monitoring", True) and self.resource_monitor.isRunning():
            self.pause_monitoring()
            
        # Update monitoring interval
        if self.resource_monitor.isRunning():
            self.resource_monitor.interval = new_settings.get("monitoring_interval", 30)
            
        self.settings_changed.emit(new_settings)
        
    def pause_monitoring(self):
        """Pause resource monitoring"""
        if self.resource_monitor.isRunning():
            self.resource_monitor.stop_monitoring()
            self.create_tray_menu()  # Update menu
            
    def resume_monitoring(self):
        """Resume resource monitoring"""
        if not self.resource_monitor.isRunning():
            self.start_resource_monitoring()
            self.create_tray_menu()  # Update menu
            
    def quit_application(self):
        """Quit the entire application"""
        # Stop monitoring
        if self.resource_monitor.isRunning():
            self.resource_monitor.stop_monitoring()
            self.resource_monitor.wait(3000)
            
        # Stop any background tasks
        for task_id in list(self.task_manager.active_tasks.keys()):
            self.task_manager.stop_task(task_id)
            
        # Hide tray icon
        if self.tray_icon:
            self.tray_icon.hide()
            
        # Quit application
        QApplication.instance().quit()
        
    def cleanup(self):
        """Cleanup tray manager resources"""
        self.pause_monitoring()
        
        if self.tray_icon:
            self.tray_icon.hide()
            
        logger.info("System tray manager cleaned up")

class SystemStatusDialog(QDialog):
    """Dialog showing system status and metrics"""
    
    def __init__(self, metrics: Dict[str, Any], task_manager: BackgroundTaskManager, parent=None):
        super().__init__(parent)
        self.metrics = metrics
        self.task_manager = task_manager
        self.setup_ui()
        
    def setup_ui(self):
        """Setup status dialog UI"""
        self.setWindowTitle("System Status")
        self.setModal(True)
        self.setFixedSize(500, 400)
        
        layout = QVBoxLayout(self)
        
        # System metrics
        metrics_group = QGroupBox("System Metrics")
        metrics_layout = QFormLayout(metrics_group)
        
        if self.metrics:
            cpu_label = QLabel(f"{self.metrics.get('cpu_percent', 0):.1f}%")
            memory_label = QLabel(f"{self.metrics.get('memory_percent', 0):.1f}%")
            disk_label = QLabel(f"{self.metrics.get('disk_percent', 0):.1f}%")
            app_memory_label = QLabel(f"{self.metrics.get('app_memory_mb', 0):.1f} MB")
            app_cpu_label = QLabel(f"{self.metrics.get('app_cpu_percent', 0):.1f}%")
            
            metrics_layout.addRow("System CPU:", cpu_label)
            metrics_layout.addRow("System Memory:", memory_label)
            metrics_layout.addRow("Disk Usage:", disk_label)
            metrics_layout.addRow("App Memory:", app_memory_label)
            metrics_layout.addRow("App CPU:", app_cpu_label)
        
        # Background tasks
        tasks_group = QGroupBox("Background Tasks")
        tasks_layout = QVBoxLayout(tasks_group)
        
        active_tasks = self.task_manager.get_active_tasks()
        if active_tasks:
            for task_id, status in active_tasks.items():
                task_label = QLabel(f"• {task_id}: {status}")
                task_label.setStyleSheet("color: #10b981;")
                tasks_layout.addWidget(task_label)
        else:
            no_tasks_label = QLabel("No active background tasks")
            no_tasks_label.setStyleSheet("color: #a1a1aa; font-style: italic;")
            tasks_layout.addWidget(no_tasks_label)
        
        # Application info
        app_group = QGroupBox("Application Info")
        app_layout = QFormLayout(app_group)
        
        version_label = QLabel("1.0.0")
        uptime_label = QLabel("Running")
        status_label = QLabel("✅ Healthy")
        status_label.setStyleSheet("color: #10b981;")
        
        app_layout.addRow("Version:", version_label)
        app_layout.addRow("Status:", status_label)
        app_layout.addRow("Uptime:", uptime_label)
        
        # Close button
        close_button = QPushButton("Close")
        close_button.clicked.connect(self.accept)
        
        # Layout assembly
        layout.addWidget(metrics_group)
        layout.addWidget(tasks_group)
        layout.addWidget(app_group)
        layout.addStretch()
        layout.addWidget(close_button)

# Global tray manager instance
tray_manager: Optional[AdvancedSystemTrayManager] = None

def initialize_system_tray(main_window, session_manager=None) -> AdvancedSystemTrayManager:
    """Initialize global system tray manager"""
    global tray_manager
    
    if tray_manager is None:
        tray_manager = AdvancedSystemTrayManager(main_window, session_manager)
        
    return tray_manager

def get_system_tray_manager() -> Optional[AdvancedSystemTrayManager]:
    """Get global system tray manager instance"""
    return tray_manager

def cleanup_system_tray():
    """Cleanup global system tray manager"""
    global tray_manager
    
    if tray_manager:
        tray_manager.cleanup()
        tray_manager = None