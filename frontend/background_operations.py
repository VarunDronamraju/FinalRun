"""
Background Operations Manager for RAG Desktop Application
Handles automatic document processing, health monitoring, and background tasks
"""

import logging
import asyncio
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Callable
from pathlib import Path

from PyQt6.QtCore import QThread, QTimer, pyqtSignal, QObject
from PyQt6.QtWidgets import QApplication

from api_client import SyncAPIClient, APIError
from session_manager import SessionManager

logger = logging.getLogger(__name__)

class BackgroundTaskType:
    """Background task type constants"""
    DOCUMENT_PROCESSING = "document_processing"
    HEALTH_CHECK = "health_check"
    SESSION_SYNC = "session_sync"
    CACHE_CLEANUP = "cache_cleanup"
    MODEL_WARMUP = "model_warmup"
    BACKUP_CREATE = "backup_create"

class BackgroundTask:
    """Background task definition"""
    
    def __init__(self, task_id: str, task_type: str, priority: int = 5, 
                 auto_retry: bool = True, max_retries: int = 3):
        self.task_id = task_id
        self.task_type = task_type
        self.priority = priority
        self.auto_retry = auto_retry
        self.max_retries = max_retries
        self.created_at = datetime.now()
        self.started_at: Optional[datetime] = None
        self.completed_at: Optional[datetime] = None
        self.status = "pending"
        self.progress = 0
        self.error_message: Optional[str] = None
        self.retry_count = 0
        
    def start(self):
        """Mark task as started"""
        self.started_at = datetime.now()
        self.status = "running"
        
    def complete(self, success: bool = True, error: str = None):
        """Mark task as completed"""
        self.completed_at = datetime.now()
        self.status = "completed" if success else "failed"
        if error:
            self.error_message = error
            
    def get_duration(self) -> Optional[float]:
        """Get task duration in seconds"""
        if self.started_at and self.completed_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None

class DocumentProcessingWorker(QThread):
    """Worker thread for background document processing"""
    
    progress_updated = pyqtSignal(str, int)  # task_id, progress
    task_completed = pyqtSignal(str, bool, str)  # task_id, success, message
    
    def __init__(self, api_client: SyncAPIClient, document_id: str, task_id: str):
        super().__init__()
        self.api_client = api_client
        self.document_id = document_id
        self.task_id = task_id
        self.should_stop = False
        
    def run(self):
        """Process document in background"""
        try:
            self.progress_updated.emit(self.task_id, 10)
            
            # Step 1: Get document info
            doc_info = self.get_document_info()
            if self.should_stop:
                return
                
            self.progress_updated.emit(self.task_id, 30)
            
            # Step 2: Process document (chunking)
            if doc_info.get("processing_status") != "completed":
                self.process_document_chunks()
                if self.should_stop:
                    return
                    
            self.progress_updated.emit(self.task_id, 60)
            
            # Step 3: Generate embeddings
            self.generate_embeddings()
            if self.should_stop:
                return
                
            self.progress_updated.emit(self.task_id, 80)
            
            # Step 4: Store in vector database
            self.store_embeddings()
            if self.should_stop:
                return
                
            self.progress_updated.emit(self.task_id, 100)
            self.task_completed.emit(self.task_id, True, "Document processed successfully")
            
        except Exception as e:
            logger.error(f"Document processing failed for {self.document_id}: {e}")
            self.task_completed.emit(self.task_id, False, str(e))
            
    def get_document_info(self) -> Dict[str, Any]:
        """Get document information"""
        # In a real implementation, this would call the API
        return {"id": self.document_id, "processing_status": "pending"}
        
    def process_document_chunks(self):
        """Process document into chunks"""
        time.sleep(1)  # Simulate processing
        
    def generate_embeddings(self):
        """Generate embeddings for document chunks"""
        time.sleep(1)  # Simulate embedding generation
        
    def store_embeddings(self):
        """Store embeddings in vector database"""
        time.sleep(0.5)  # Simulate storage
        
    def stop(self):
        """Stop the worker"""
        self.should_stop = True

class HealthCheckWorker(QThread):
    """Worker thread for system health monitoring"""
    
    health_status_updated = pyqtSignal(dict)
    health_alert = pyqtSignal(str, str)  # level, message
    
    def __init__(self, api_client: SyncAPIClient):
        super().__init__()
        self.api_client = api_client
        self.monitoring = False
        self.check_interval = 60  # seconds
        
    def run(self):
        """Monitor system health"""
        self.monitoring = True
        
        while self.monitoring:
            try:
                health_status = self.check_system_health()
                self.health_status_updated.emit(health_status)
                
                # Check for issues
                self.analyze_health_status(health_status)
                
                # Wait before next check
                for _ in range(self.check_interval):
                    if not self.monitoring:
                        break
                    self.msleep(1000)
                    
            except Exception as e:
                logger.error(f"Health check failed: {e}")
                self.msleep(5000)  # Brief pause on error
                
    def check_system_health(self) -> Dict[str, Any]:
        """Check system health status"""
        try:
            # Check backend connection
            backend_healthy = self.api_client.test_connection()
            
            # Check API endpoints
            endpoints_status = {}
            if backend_healthy:
                endpoints_status = self.check_api_endpoints()
                
            # Get system metrics
            system_metrics = self.get_system_metrics()
            
            return {
                "timestamp": datetime.now(),
                "backend_healthy": backend_healthy,
                "endpoints": endpoints_status,
                "system": system_metrics,
                "overall_status": "healthy" if backend_healthy else "degraded"
            }
            
        except Exception as e:
            return {
                "timestamp": datetime.now(),
                "backend_healthy": False,
                "error": str(e),
                "overall_status": "error"
            }
            
    def check_api_endpoints(self) -> Dict[str, bool]:
        """Check individual API endpoints"""
        endpoints = {
            "health": False,
            "documents": False,
            "rag": False,
            "search": False
        }
        
        try:
            # Health endpoint
            endpoints["health"] = self.api_client.test_connection()
            
            # Documents endpoint
            try:
                self.api_client.get_documents()
                endpoints["documents"] = True
            except:
                pass
                
            # RAG endpoint
            try:
                self.api_client.rag_query("test")
                endpoints["rag"] = True
            except:
                pass
                
            # Search endpoint
            try:
                self.api_client.semantic_search("test")
                endpoints["search"] = True
            except:
                pass
                
        except Exception as e:
            logger.error(f"Endpoint check failed: {e}")
            
        return endpoints
        
    def get_system_metrics(self) -> Dict[str, Any]:
        """Get basic system metrics"""
        try:
            import psutil
            return {
                "cpu_percent": psutil.cpu_percent(interval=1),
                "memory_percent": psutil.virtual_memory().percent,
                "disk_percent": psutil.disk_usage('/').percent if hasattr(psutil.disk_usage, '/') else 0,
                "network_active": True  # Simplified
            }
        except ImportError:
            return {"cpu_percent": 0, "memory_percent": 0, "disk_percent": 0}
            
    def analyze_health_status(self, status: Dict[str, Any]):
        """Analyze health status and emit alerts"""
        if not status.get("backend_healthy", False):
            self.health_alert.emit("error", "Backend connection lost")
            
        system = status.get("system", {})
        if system.get("memory_percent", 0) > 90:
            self.health_alert.emit("warning", f"High memory usage: {system['memory_percent']:.1f}%")
            
    def stop_monitoring(self):
        """Stop health monitoring"""
        self.monitoring = False

class SessionSyncWorker(QThread):
    """Worker thread for session synchronization"""
    
    sync_completed = pyqtSignal(bool, str)  # success, message
    
    def __init__(self, session_manager: SessionManager):
        super().__init__()
        self.session_manager = session_manager
        
    def run(self):
        """Synchronize session data"""
        try:
            # Save current session
            self.session_manager.save_session()
            
            # Cleanup old cache
            self.session_manager.cleanup_old_cache(days=7)
            
            # Sync complete
            self.sync_completed.emit(True, "Session synchronized successfully")
            
        except Exception as e:
            logger.error(f"Session sync failed: {e}")
            self.sync_completed.emit(False, str(e))

class BackgroundOperationsManager(QObject):
    """Main background operations coordinator"""
    
    # Signals
    task_started = pyqtSignal(str, str)  # task_id, task_type
    task_progress = pyqtSignal(str, int)  # task_id, progress
    task_completed = pyqtSignal(str, bool, str)  # task_id, success, message
    health_status_changed = pyqtSignal(dict)
    
    def __init__(self, api_client: SyncAPIClient, session_manager: SessionManager):
        super().__init__()
        self.api_client = api_client
        self.session_manager = session_manager
        
        # Task management
        self.active_tasks: Dict[str, BackgroundTask] = {}
        self.task_queue: List[BackgroundTask] = []
        self.task_workers: Dict[str, QThread] = {}
        
        # Monitoring
        self.health_worker: Optional[HealthCheckWorker] = None
        self.last_health_status: Dict[str, Any] = {}
        
        # Timers for periodic tasks (initialized later to avoid thread issues)
        self.session_sync_timer = None
        self.cache_cleanup_timer = None
        self._initialize_timers()
        
        # Settings
        self.settings = self.load_settings()
        
    def _initialize_timers(self):
        """Initialize timers in the main thread"""
        try:
            # Only initialize if we're in the main thread
            from PyQt6.QtCore import QThread
            if QThread.currentThread() == QApplication.instance().thread():
                self.session_sync_timer = QTimer()
                self.session_sync_timer.timeout.connect(self.schedule_session_sync)
                self.session_sync_timer.start(300000)  # 5 minutes
                
                self.cache_cleanup_timer = QTimer()
                self.cache_cleanup_timer.timeout.connect(self.schedule_cache_cleanup)
                self.cache_cleanup_timer.start(3600000)  # 1 hour
                
                logger.info("Background operation timers initialized")
            else:
                logger.warning("Timers not initialized - not in main thread")
        except Exception as e:
            logger.error(f"Failed to initialize timers: {e}")
        
    def load_settings(self) -> Dict[str, Any]:
        """Load background operations settings"""
        return self.session_manager.get_user_preference("background_ops", {
            "auto_process_documents": True,
            "health_monitoring": True,
            "auto_session_sync": True,
            "auto_cache_cleanup": True,
            "max_concurrent_tasks": 3,
            "health_check_interval": 60
        })
        
    def save_settings(self):
        """Save background operations settings"""
        self.session_manager.set_user_preference("background_ops", self.settings)
        
    def start_health_monitoring(self):
        """Start background health monitoring"""
        if self.settings.get("health_monitoring", True) and not self.health_worker:
            self.health_worker = HealthCheckWorker(self.api_client)
            self.health_worker.health_status_updated.connect(self.on_health_status_updated)
            self.health_worker.health_alert.connect(self.on_health_alert)
            self.health_worker.check_interval = self.settings.get("health_check_interval", 60)
            self.health_worker.start()
            
            logger.info("Background health monitoring started")
            
    def stop_health_monitoring(self):
        """Stop background health monitoring"""
        if self.health_worker:
            self.health_worker.stop_monitoring()
            self.health_worker.wait(3000)
            self.health_worker = None
            
    def schedule_document_processing(self, document_id: str, priority: int = 5) -> str:
        """Schedule document processing task"""
        if not self.settings.get("auto_process_documents", True):
            return ""
            
        task_id = f"doc_process_{document_id}_{int(time.time())}"
        task = BackgroundTask(task_id, BackgroundTaskType.DOCUMENT_PROCESSING, priority)
        
        self.task_queue.append(task)
        self.process_task_queue()
        
        return task_id
        
    def schedule_session_sync(self):
        """Schedule session synchronization"""
        if not self.settings.get("auto_session_sync", True):
            return
            
        task_id = f"session_sync_{int(time.time())}"
        task = BackgroundTask(task_id, BackgroundTaskType.SESSION_SYNC, priority=2)
        
        self.task_queue.append(task)
        self.process_task_queue()
        
    def schedule_cache_cleanup(self):
        """Schedule cache cleanup"""
        if not self.settings.get("auto_cache_cleanup", True):
            return
            
        task_id = f"cache_cleanup_{int(time.time())}"
        task = BackgroundTask(task_id, BackgroundTaskType.CACHE_CLEANUP, priority=1)
        
        self.task_queue.append(task)
        self.process_task_queue()
        
    def process_task_queue(self):
        """Process pending tasks"""
        max_concurrent = self.settings.get("max_concurrent_tasks", 3)
        
        if len(self.active_tasks) >= max_concurrent:
            return
            
        if not self.task_queue:
            return
            
        # Sort by priority (higher priority first)
        self.task_queue.sort(key=lambda t: t.priority, reverse=True)
        
        # Start next task
        task = self.task_queue.pop(0)
        self.start_task(task)
        
    def start_task(self, task: BackgroundTask):
        """Start a background task"""
        task.start()
        self.active_tasks[task.task_id] = task
        
        # Create appropriate worker
        worker = self.create_worker(task)
        if worker:
            self.task_workers[task.task_id] = worker
            
            # Connect signals
            if hasattr(worker, 'progress_updated'):
                worker.progress_updated.connect(self.on_task_progress)
            if hasattr(worker, 'task_completed'):
                worker.task_completed.connect(self.on_task_completed)
            if hasattr(worker, 'sync_completed'):
                worker.sync_completed.connect(self.on_task_completed)
                
            # Start worker
            worker.start()
            
            self.task_started.emit(task.task_id, task.task_type)
            logger.info(f"Started background task: {task.task_id} ({task.task_type})")
            
    def create_worker(self, task: BackgroundTask) -> Optional[QThread]:
        """Create appropriate worker for task type"""
        if task.task_type == BackgroundTaskType.DOCUMENT_PROCESSING:
            # Extract document ID from task ID
            doc_id = task.task_id.split("_")[2]
            return DocumentProcessingWorker(self.api_client, doc_id, task.task_id)
            
        elif task.task_type == BackgroundTaskType.SESSION_SYNC:
            return SessionSyncWorker(self.session_manager)
            
        elif task.task_type == BackgroundTaskType.CACHE_CLEANUP:
            # For cache cleanup, we can do it directly
            try:
                self.session_manager.cleanup_old_cache(days=7)
                # Simulate completion with safer timer approach
                def complete_success():
                    self.on_task_completed(task.task_id, True, "Cache cleaned")
                
                if QApplication.instance():
                    QTimer.singleShot(1000, complete_success)
                else:
                    complete_success()
            except Exception as e:
                def complete_error():
                    self.on_task_completed(task.task_id, False, str(e))
                
                if QApplication.instance():
                    QTimer.singleShot(1000, complete_error)
                else:
                    complete_error()
            return None
            
        return None
        
    def on_task_progress(self, task_id: str, progress: int):
        """Handle task progress update"""
        if task_id in self.active_tasks:
            self.active_tasks[task_id].progress = progress
            self.task_progress.emit(task_id, progress)
            
    def on_task_completed(self, task_id: str, success: bool, message: str):
        """Handle task completion"""
        if task_id in self.active_tasks:
            task = self.active_tasks[task_id]
            task.complete(success, message if not success else None)
            
            # Clean up
            del self.active_tasks[task_id]
            
            if task_id in self.task_workers:
                worker = self.task_workers[task_id]
                worker.quit()
                worker.wait(3000)
                del self.task_workers[task_id]
                
            self.task_completed.emit(task_id, success, message)
            logger.info(f"Background task completed: {task_id} ({'success' if success else 'failed'})")
            
            # Process next task in queue
            self.process_task_queue()
            
    def on_health_status_updated(self, status: Dict[str, Any]):
        """Handle health status update"""
        self.last_health_status = status
        self.health_status_changed.emit(status)
        
    def on_health_alert(self, level: str, message: str):
        """Handle health alert"""
        # Could emit notification signal or handle directly
        logger.warning(f"Health alert ({level}): {message}")
        
    def get_task_status(self, task_id: str) -> Optional[BackgroundTask]:
        """Get status of a specific task"""
        return self.active_tasks.get(task_id)
        
    def get_active_tasks(self) -> Dict[str, BackgroundTask]:
        """Get all active tasks"""
        return self.active_tasks.copy()
        
    def get_pending_tasks(self) -> List[BackgroundTask]:
        """Get pending tasks in queue"""
        return self.task_queue.copy()
        
    def cancel_task(self, task_id: str) -> bool:
        """Cancel a running or pending task"""
        # Check if task is active
        if task_id in self.active_tasks:
            if task_id in self.task_workers:
                worker = self.task_workers[task_id]
                if hasattr(worker, 'stop'):
                    worker.stop()
                worker.quit()
                worker.wait(3000)
                del self.task_workers[task_id]
                
            del self.active_tasks[task_id]
            self.task_completed.emit(task_id, False, "Task cancelled")
            return True
            
        # Check if task is in queue
        for i, task in enumerate(self.task_queue):
            if task.task_id == task_id:
                del self.task_queue[i]
                return True
                
        return False
        
    def update_settings(self, new_settings: Dict[str, Any]):
        """Update background operations settings"""
        self.settings.update(new_settings)
        self.save_settings()
        
        # Apply changes
        if new_settings.get("health_monitoring", True) and not self.health_worker:
            self.start_health_monitoring()
        elif not new_settings.get("health_monitoring", True) and self.health_worker:
            self.stop_health_monitoring()
            
    def cleanup(self):
        """Cleanup background operations"""
        # Stop health monitoring
        self.stop_health_monitoring()
        
        # Cancel all active tasks
        for task_id in list(self.active_tasks.keys()):
            self.cancel_task(task_id)
            
        # Stop timers
        self.session_sync_timer.stop()
        self.cache_cleanup_timer.stop()
        
        logger.info("Background operations manager cleaned up")

# Global background operations manager
background_ops_manager: Optional[BackgroundOperationsManager] = None

def initialize_background_operations(api_client: SyncAPIClient, session_manager: SessionManager) -> BackgroundOperationsManager:
    """Initialize global background operations manager"""
    global background_ops_manager
    
    if background_ops_manager is None:
        background_ops_manager = BackgroundOperationsManager(api_client, session_manager)
        
    return background_ops_manager

def get_background_operations_manager() -> Optional[BackgroundOperationsManager]:
    """Get global background operations manager"""
    return background_ops_manager

def cleanup_background_operations():
    """Cleanup global background operations manager"""
    global background_ops_manager
    
    if background_ops_manager:
        background_ops_manager.cleanup()
        background_ops_manager = None