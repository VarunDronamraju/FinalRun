"""
Session Manager for RAG Desktop Application
Handles local session persistence, window state, and offline mode
"""

import json
import logging
import os
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Any, Optional, List
from PyQt6.QtCore import QSettings, QByteArray, QStandardPaths
from PyQt6.QtWidgets import QMainWindow
import hashlib

logger = logging.getLogger(__name__)

class SessionManager:
    """Manages application sessions and local storage"""
    
    def __init__(self, app_name: str = "RAGDesktop"):
        self.app_name = app_name
        self.settings = QSettings("RAGDesktop", "MainApp")
        self.app_data_dir = self._get_app_data_directory()
        self.session_file = self.app_data_dir / "session.json"
        self.cache_dir = self.app_data_dir / "cache"
        self.logs_dir = self.app_data_dir / "logs"
        
        # Create directories
        self._ensure_directories()
        
        # Current session data
        self.current_session = self._load_session()
        
        logger.info(f"Session manager initialized. Data dir: {self.app_data_dir}")
    
    def _get_app_data_directory(self) -> Path:
        """Get platform-specific application data directory"""
        app_data = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)
        return Path(app_data) / self.app_name
    
    def _ensure_directories(self):
        """Create necessary directories if they don't exist"""
        directories = [self.app_data_dir, self.cache_dir, self.logs_dir]
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    def _load_session(self) -> Dict[str, Any]:
        """Load session data from file"""
        default_session = {
            "session_id": str(uuid.uuid4()),
            "created_at": datetime.now().isoformat(),
            "last_active": datetime.now().isoformat(),
            "user_preferences": {},
            "chat_history": [],
            "document_cache": {},
            "window_state": {},
            "api_settings": {
                "base_url": "http://localhost:8000",
                "timeout": 30,
                "retry_count": 3
            }
        }
        
        if not self.session_file.exists():
            logger.info("Creating new session")
            return default_session
            
        try:
            with open(self.session_file, 'r', encoding='utf-8') as f:
                session_data = json.load(f)
                
            # Validate session age (expire after 30 days)
            last_active = datetime.fromisoformat(session_data.get("last_active", ""))
            if datetime.now() - last_active > timedelta(days=30):
                logger.info("Session expired, creating new one")
                return default_session
                
            # Update last active time
            session_data["last_active"] = datetime.now().isoformat()
            logger.info(f"Loaded existing session: {session_data.get('session_id', 'unknown')[:8]}...")
            return session_data
            
        except (json.JSONDecodeError, KeyError, ValueError) as e:
            logger.warning(f"Failed to load session, creating new one: {e}")
            return default_session
    
    def save_session(self):
        """Save current session to file"""
        try:
            self.current_session["last_active"] = datetime.now().isoformat()
            
            with open(self.session_file, 'w', encoding='utf-8') as f:
                json.dump(self.current_session, f, indent=2, ensure_ascii=False)
                
            logger.debug("Session saved successfully")
            
        except Exception as e:
            logger.error(f"Failed to save session: {e}")
    
    def clear_session(self):
        """Clear current session and create new one"""
        try:
            if self.session_file.exists():
                self.session_file.unlink()
            self.current_session = self._load_session()
            logger.info("Session cleared and reset")
        except Exception as e:
            logger.error(f"Failed to clear session: {e}")
    
    # User Preferences Management
    def get_user_preference(self, key: str, default=None) -> Any:
        """Get user preference value"""
        return self.current_session["user_preferences"].get(key, default)
    
    def set_user_preference(self, key: str, value: Any):
        """Set user preference value"""
        self.current_session["user_preferences"][key] = value
        self.save_session()
    
    def get_all_preferences(self) -> Dict[str, Any]:
        """Get all user preferences"""
        return self.current_session["user_preferences"].copy()
    
    # Window State Management
    def save_window_state(self, window: QMainWindow):
        """Save window geometry and state"""
        try:
            self.current_session["window_state"] = {
                "geometry": window.saveGeometry().data().hex(),
                "window_state": window.saveState().data().hex(),
                "is_maximized": window.isMaximized(),
                "is_minimized": window.isMinimized()
            }
            self.save_session()
            logger.debug("Window state saved")
        except Exception as e:
            logger.error(f"Failed to save window state: {e}")
    
    def restore_window_state(self, window: QMainWindow) -> bool:
        """Restore window geometry and state"""
        try:
            window_state = self.current_session.get("window_state", {})
            
            if "geometry" in window_state:
                geometry = QByteArray.fromHex(window_state["geometry"].encode())
                window.restoreGeometry(geometry)
            
            if "window_state" in window_state:
                state = QByteArray.fromHex(window_state["window_state"].encode())
                window.restoreState(state)
            
            # Handle maximized/minimized states
            if window_state.get("is_maximized", False):
                window.showMaximized()
            elif window_state.get("is_minimized", False):
                window.showMinimized()
            
            logger.debug("Window state restored")
            return True
            
        except Exception as e:
            logger.error(f"Failed to restore window state: {e}")
            return False
    
    # Chat History Management
    def add_chat_message(self, message: str, is_user: bool, timestamp: Optional[str] = None):
        """Add message to chat history"""
        if timestamp is None:
            timestamp = datetime.now().isoformat()
            
        chat_entry = {
            "message": message,
            "is_user": is_user,
            "timestamp": timestamp,
            "id": str(uuid.uuid4())
        }
        
        self.current_session["chat_history"].append(chat_entry)
        
        # Limit chat history to last 1000 messages
        if len(self.current_session["chat_history"]) > 1000:
            self.current_session["chat_history"] = self.current_session["chat_history"][-1000:]
        
        self.save_session()
    
    def get_chat_history(self, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """Get chat history with optional limit"""
        history = self.current_session["chat_history"]
        if limit:
            return history[-limit:]
        return history
    
    def clear_chat_history(self):
        """Clear all chat history"""
        self.current_session["chat_history"] = []
        self.save_session()
        logger.info("Chat history cleared")
    
    def search_chat_history(self, query: str) -> List[Dict[str, Any]]:
        """Search chat history for messages containing query"""
        query_lower = query.lower()
        results = []
        
        for message in self.current_session["chat_history"]:
            if query_lower in message["message"].lower():
                results.append(message)
        
        return results
    
    # Document Cache Management
    def cache_document_info(self, doc_id: str, doc_info: Dict[str, Any]):
        """Cache document information"""
        self.current_session["document_cache"][doc_id] = {
            **doc_info,
            "cached_at": datetime.now().isoformat()
        }
        self.save_session()
    
    def get_cached_document_info(self, doc_id: str) -> Optional[Dict[str, Any]]:
        """Get cached document information"""
        doc_info = self.current_session["document_cache"].get(doc_id)
        if doc_info:
            # Check if cache is still valid (24 hours)
            cached_at = datetime.fromisoformat(doc_info["cached_at"])
            if datetime.now() - cached_at < timedelta(hours=24):
                return doc_info
            else:
                # Remove expired cache
                del self.current_session["document_cache"][doc_id]
                self.save_session()
        return None
    
    def clear_document_cache(self):
        """Clear all cached document information"""
        self.current_session["document_cache"] = {}
        self.save_session()
        logger.info("Document cache cleared")
    
    # API Settings Management
    def get_api_setting(self, key: str, default=None) -> Any:
        """Get API setting"""
        return self.current_session["api_settings"].get(key, default)
    
    def set_api_setting(self, key: str, value: Any):
        """Set API setting"""
        self.current_session["api_settings"][key] = value
        self.save_session()
    
    def get_api_base_url(self) -> str:
        """Get API base URL"""
        return self.get_api_setting("base_url", "http://localhost:8000")
    
    def set_api_base_url(self, url: str):
        """Set API base URL"""
        self.set_api_setting("base_url", url)
    
    # File Management
    def get_cache_file_path(self, filename: str) -> Path:
        """Get path for cache file"""
        return self.cache_dir / filename
    
    def get_log_file_path(self, filename: str) -> Path:
        """Get path for log file"""
        return self.logs_dir / filename
    
    def cache_file(self, filename: str, data: bytes) -> bool:
        """Cache binary data to file"""
        try:
            cache_path = self.get_cache_file_path(filename)
            with open(cache_path, 'wb') as f:
                f.write(data)
            logger.debug(f"File cached: {filename}")
            return True
        except Exception as e:
            logger.error(f"Failed to cache file {filename}: {e}")
            return False
    
    def get_cached_file(self, filename: str) -> Optional[bytes]:
        """Get cached file data"""
        try:
            cache_path = self.get_cache_file_path(filename)
            if cache_path.exists():
                with open(cache_path, 'rb') as f:
                    return f.read()
        except Exception as e:
            logger.error(f"Failed to read cached file {filename}: {e}")
        return None
    
    # Cleanup and Maintenance
    def cleanup_old_cache(self, days: int = 7):
        """Clean up cache files older than specified days"""
        try:
            cutoff_time = datetime.now() - timedelta(days=days)
            cleaned_count = 0
            
            for file_path in self.cache_dir.glob("*"):
                if file_path.is_file():
                    file_time = datetime.fromtimestamp(file_path.stat().st_mtime)
                    if file_time < cutoff_time:
                        file_path.unlink()
                        cleaned_count += 1
            
            logger.info(f"Cleaned up {cleaned_count} old cache files")
            
        except Exception as e:
            logger.error(f"Failed to cleanup cache: {e}")
    
    def get_session_info(self) -> Dict[str, Any]:
        """Get session information for debugging"""
        return {
            "session_id": self.current_session["session_id"],
            "created_at": self.current_session["created_at"],
            "last_active": self.current_session["last_active"],
            "chat_messages": len(self.current_session["chat_history"]),
            "cached_documents": len(self.current_session["document_cache"]),
            "preferences": list(self.current_session["user_preferences"].keys()),
            "data_directory": str(self.app_data_dir),
            "cache_size": sum(f.stat().st_size for f in self.cache_dir.glob("*") if f.is_file())
        }
    
    def export_session(self, export_path: str) -> bool:
        """Export session data to a file"""
        try:
            export_data = {
                "exported_at": datetime.now().isoformat(),
                "session_data": self.current_session
            }
            
            with open(export_path, 'w', encoding='utf-8') as f:
                json.dump(export_data, f, indent=2, ensure_ascii=False)
            
            logger.info(f"Session exported to {export_path}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to export session: {e}")
            return False
    
    def import_session(self, import_path: str) -> bool:
        """Import session data from a file"""
        try:
            with open(import_path, 'r', encoding='utf-8') as f:
                imported_data = json.load(f)
            
            # Validate imported data
            if "session_data" in imported_data:
                self.current_session = imported_data["session_data"]
                self.current_session["last_active"] = datetime.now().isoformat()
                self.save_session()
                logger.info(f"Session imported from {import_path}")
                return True
            else:
                logger.error("Invalid session file format")
                return False
                
        except Exception as e:
            logger.error(f"Failed to import session: {e}")
            return False

# Global session manager instance
session_manager = SessionManager()