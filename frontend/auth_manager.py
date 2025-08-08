"""
Authentication Manager for RAG Desktop Application
Handles Google OAuth flow, JWT tokens, and user session management
"""

import json
import logging
import webbrowser
import urllib.parse
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, Callable
from pathlib import Path

from PyQt6.QtCore import QObject, pyqtSignal, QTimer, QThread
from PyQt6.QtWidgets import QMessageBox, QInputDialog, QDialog, QVBoxLayout, QLabel, QPushButton, QHBoxLayout
from PyQt6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from PyQt6.QtCore import QUrl, QByteArray

import httpx
import secrets
import hashlib
import base64

logger = logging.getLogger(__name__)

class AuthState:
    """Authentication state management"""
    
    def __init__(self):
        self.is_authenticated = False
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.user_info: Optional[Dict[str, Any]] = None
        self.token_expires_at: Optional[datetime] = None
        
    def is_token_valid(self) -> bool:
        """Check if current token is still valid"""
        if not self.access_token or not self.token_expires_at:
            return False
        return datetime.now() < self.token_expires_at - timedelta(minutes=5)  # 5min buffer
        
    def clear(self):
        """Clear all auth state"""
        self.is_authenticated = False
        self.access_token = None
        self.refresh_token = None
        self.user_info = None
        self.token_expires_at = None

class GoogleOAuthDialog(QDialog):
    """Dialog for Google OAuth instructions"""
    
    def __init__(self, auth_url: str, parent=None):
        super().__init__(parent)
        self.auth_url = auth_url
        self.setup_ui()
        
    def setup_ui(self):
        """Setup OAuth dialog UI"""
        self.setWindowTitle("Google Authentication")
        self.setModal(True)
        self.setFixedSize(500, 300)
        
        layout = QVBoxLayout(self)
        
        # Instructions
        title = QLabel("🔐 Google Authentication Required")
        title.setStyleSheet("font-size: 16px; font-weight: bold; color: #3b82f6; margin-bottom: 10px;")
        layout.addWidget(title)
        
        instructions = QLabel(
            "1. Click 'Open Browser' to authenticate with Google\n"
            "2. Grant permissions in your browser\n"
            "3. Copy the authorization code\n"
            "4. Paste it in the next dialog"
        )
        instructions.setStyleSheet("color: #e5e5e5; line-height: 1.5; margin-bottom: 20px;")
        layout.addWidget(instructions)
        
        # Buttons
        button_layout = QHBoxLayout()
        
        self.open_browser_btn = QPushButton("🌐 Open Browser")
        self.open_browser_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #3b82f6, stop:1 #1d4ed8);
                border: none;
                border-radius: 8px;
                color: white;
                font-weight: bold;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #2563eb, stop:1 #1e40af);
            }
        """)
        self.open_browser_btn.clicked.connect(self.open_browser)
        
        self.continue_btn = QPushButton("✅ Continue")
        self.continue_btn.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #10b981, stop:1 #059669);
                border: none;
                border-radius: 8px;
                color: white;
                font-weight: bold;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #059669, stop:1 #047857);
            }
        """)
        self.continue_btn.clicked.connect(self.accept)
        
        cancel_btn = QPushButton("❌ Cancel")
        cancel_btn.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.1);
                border: 1px solid rgba(255, 255, 255, 0.2);
                border-radius: 8px;
                color: #e5e5e5;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.15);
            }
        """)
        cancel_btn.clicked.connect(self.reject)
        
        button_layout.addWidget(self.open_browser_btn)
        button_layout.addWidget(self.continue_btn)
        button_layout.addStretch()
        button_layout.addWidget(cancel_btn)
        
        layout.addLayout(button_layout)
        
    def open_browser(self):
        """Open browser with OAuth URL"""
        try:
            webbrowser.open(self.auth_url)
            self.open_browser_btn.setText("✅ Browser Opened")
            self.open_browser_btn.setEnabled(False)
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to open browser: {e}")

class AuthWorkerThread(QThread):
    """Worker thread for authentication operations"""
    
    auth_completed = pyqtSignal(bool, dict)  # success, result
    error_occurred = pyqtSignal(str)
    
    def __init__(self, operation: str, **kwargs):
        super().__init__()
        self.operation = operation
        self.kwargs = kwargs
        
    def run(self):
        """Run authentication operation"""
        try:
            if self.operation == "exchange_code":
                result = self.exchange_authorization_code()
            elif self.operation == "refresh_token":
                result = self.refresh_access_token()
            elif self.operation == "get_user_info":
                result = self.get_user_info()
            else:
                raise ValueError(f"Unknown operation: {self.operation}")
                
            self.auth_completed.emit(True, result)
            
        except Exception as e:
            logger.error(f"Auth operation '{self.operation}' failed: {e}")
            self.error_occurred.emit(str(e))
            
    def exchange_authorization_code(self) -> Dict[str, Any]:
        """Exchange authorization code for tokens"""
        # This would connect to your backend's OAuth endpoint
        # For now, simulate the flow
        auth_code = self.kwargs.get("auth_code")
        
        # In real implementation, call your backend:
        # POST /auth/google/callback with the auth_code
        
        # Mock response for development
        return {
            "access_token": f"mock_access_token_{secrets.token_hex(16)}",
            "refresh_token": f"mock_refresh_token_{secrets.token_hex(16)}",
            "expires_in": 3600,
            "token_type": "Bearer"
        }
        
    def refresh_access_token(self) -> Dict[str, Any]:
        """Refresh access token"""
        refresh_token = self.kwargs.get("refresh_token")
        
        # Call backend refresh endpoint
        # POST /auth/refresh with refresh_token
        
        return {
            "access_token": f"refreshed_token_{secrets.token_hex(16)}",
            "expires_in": 3600
        }
        
    def get_user_info(self) -> Dict[str, Any]:
        """Get user information"""
        access_token = self.kwargs.get("access_token")
        
        # Call backend user info endpoint
        # GET /auth/profile with Bearer token
        
        return {
            "id": "mock_user_123",
            "email": "user@example.com",
            "name": "Demo User",
            "picture": None,
            "verified_email": True
        }

class AuthenticationManager(QObject):
    """Main authentication manager"""
    
    # Signals
    auth_state_changed = pyqtSignal(bool)  # authenticated
    user_info_updated = pyqtSignal(dict)   # user_info
    auth_error = pyqtSignal(str)           # error_message
    
    def __init__(self, session_manager=None, api_client=None):
        super().__init__()
        self.session_manager = session_manager
        self.api_client = api_client
        self.auth_state = AuthState()
        
        # OAuth configuration - will be fetched from backend
        self.oauth_config = {
            "client_id": "mock_client_id",  # Will be updated from backend
            "client_secret": "mock_client_secret",
            "redirect_uri": "urn:ietf:wg:oauth:2.0:oob",
            "scope": "openid email profile",
            "auth_base_url": "https://accounts.google.com/o/oauth2/v2/auth",
            "token_url": "https://oauth2.googleapis.com/token"
        }
        
        # Token refresh timer
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self.auto_refresh_token)
        
        # Load saved auth state
        self.load_auth_state()
        
    def is_authenticated(self) -> bool:
        """Check if user is authenticated"""
        return self.auth_state.is_authenticated and self.auth_state.is_token_valid()
        
    def get_user_info(self) -> Optional[Dict[str, Any]]:
        """Get current user information"""
        return self.auth_state.user_info
        
    def get_access_token(self) -> Optional[str]:
        """Get current access token"""
        if self.auth_state.is_token_valid():
            return self.auth_state.access_token
        return None
        
    def start_oauth_flow(self):
        """Start Google OAuth authentication flow using backend"""
        try:
            # Use backend OAuth flow instead of direct Google OAuth
            if not self.api_client:
                self.auth_error.emit("API client not available")
                return
                
            # Get OAuth URL from backend
            oauth_response = self.api_client.google_oauth_login()
            
            if not oauth_response or "auth_url" not in oauth_response:
                self.auth_error.emit("Failed to get OAuth URL from backend")
                return
                
            auth_url = oauth_response["auth_url"]
            is_mock = oauth_response.get("is_mock", False)
            
            # Show OAuth dialog
            dialog = GoogleOAuthDialog(auth_url)
            if dialog.exec() == QDialog.DialogCode.Accepted:
                # Get authorization code from user
                auth_code, ok = QInputDialog.getText(
                    None,
                    "Authorization Code",
                    "Paste the authorization code from Google:",
                    text=""
                )
                
                if ok and auth_code.strip():
                    # Use backend to exchange code for tokens
                    self.exchange_code_for_tokens(auth_code.strip(), is_mock)
                else:
                    self.auth_error.emit("Authorization cancelled by user")
            else:
                self.auth_error.emit("OAuth flow cancelled")
                
        except Exception as e:
            logger.error(f"OAuth flow failed: {e}")
            self.auth_error.emit(f"Authentication failed: {e}")
            
    def exchange_code_for_tokens(self, auth_code: str, is_mock: bool = False):
        """Exchange authorization code for access tokens using backend"""
        if not self.api_client:
            self.auth_error.emit("API client not available")
            return
            
        try:
            # Use backend to exchange code for tokens
            token_response = self.api_client.google_oauth_callback(auth_code, is_mock)
            
            if token_response and "access_token" in token_response:
                self.handle_token_response(True, token_response)
            else:
                self.auth_error.emit("Failed to exchange authorization code")
                
        except Exception as e:
            logger.error(f"Token exchange failed: {e}")
            self.auth_error.emit(f"Token exchange failed: {e}")
        
    def handle_token_response(self, success: bool, result: Dict[str, Any]):
        """Handle token exchange response"""
        if success and result:
            # Store tokens
            self.auth_state.access_token = result.get("access_token")
            self.auth_state.refresh_token = result.get("refresh_token")
            
            # Calculate expiration
            expires_in = result.get("expires_in", 3600)
            self.auth_state.token_expires_at = datetime.now() + timedelta(seconds=expires_in)
            
            # Get user info
            self.get_user_profile()
            
        else:
            self.auth_error.emit("Failed to exchange authorization code")
            
    def get_user_profile(self):
        """Get user profile information from backend"""
        if not self.api_client:
            self.auth_error.emit("API client not available")
            return
            
        try:
            # Get user profile from backend
            user_info = self.api_client.get_user_profile()
            
            if user_info:
                self.handle_user_info(True, user_info)
            else:
                self.auth_error.emit("Failed to get user profile")
                
        except Exception as e:
            logger.error(f"Profile retrieval failed: {e}")
            self.auth_error.emit(f"Profile retrieval failed: {e}")
        
    def handle_user_info(self, success: bool, user_info: Dict[str, Any]):
        """Handle user info response"""
        if success and user_info:
            self.auth_state.user_info = user_info
            self.auth_state.is_authenticated = True
            
            # Save auth state
            self.save_auth_state()
            
            # Start token refresh timer
            self.start_refresh_timer()
            
            # Emit signals
            self.auth_state_changed.emit(True)
            self.user_info_updated.emit(user_info)
            
            # Update API client with token
            if self.api_client:
                self.api_client.set_auth_token(self.auth_state.access_token)
                
            logger.info(f"User authenticated: {user_info.get('email', 'unknown')}")
            
        else:
            self.auth_error.emit("Failed to get user profile")
            
    def logout(self):
        """Logout user and clear auth state"""
        try:
            # Clear API client token
            if self.api_client:
                self.api_client.clear_auth_token()
                
            # Stop refresh timer
            if self.refresh_timer.isActive():
                self.refresh_timer.stop()
                
            # Clear auth state
            self.auth_state.clear()
            
            # Clear saved state
            if self.session_manager:
                self.session_manager.set_user_preference("auth_tokens", None)
                self.session_manager.set_user_preference("user_info", None)
                
            # Emit signals
            self.auth_state_changed.emit(False)
            
            logger.info("User logged out successfully")
            
        except Exception as e:
            logger.error(f"Logout failed: {e}")
            
    def auto_refresh_token(self):
        """Automatically refresh access token"""
        if not self.auth_state.refresh_token:
            logger.warning("No refresh token available for auto-refresh")
            self.logout()  # Force re-authentication
            return
            
        self.refresh_worker = AuthWorkerThread(
            "refresh_token",
            refresh_token=self.auth_state.refresh_token
        )
        self.refresh_worker.auth_completed.connect(self.handle_token_refresh)
        self.refresh_worker.error_occurred.connect(self.handle_refresh_error)
        self.refresh_worker.start()
        
    def handle_token_refresh(self, success: bool, result: Dict[str, Any]):
        """Handle token refresh response"""
        if success and result:
            # Update access token
            self.auth_state.access_token = result.get("access_token")
            
            # Update expiration
            expires_in = result.get("expires_in", 3600)
            self.auth_state.token_expires_at = datetime.now() + timedelta(seconds=expires_in)
            
            # Update API client
            if self.api_client:
                self.api_client.set_auth_token(self.auth_state.access_token)
                
            # Save updated state
            self.save_auth_state()
            
            logger.info("Access token refreshed successfully")
            
        else:
            logger.error("Token refresh failed")
            self.handle_refresh_error("Token refresh failed")
            
    def handle_refresh_error(self, error: str):
        """Handle token refresh error"""
        logger.error(f"Token refresh error: {error}")
        
        # Force logout and re-authentication
        self.logout()
        self.auth_error.emit("Session expired. Please log in again.")
        
    def start_refresh_timer(self):
        """Start automatic token refresh timer"""
        if self.auth_state.token_expires_at:
            # Refresh 5 minutes before expiration
            refresh_time = self.auth_state.token_expires_at - timedelta(minutes=5)
            remaining_ms = int((refresh_time - datetime.now()).total_seconds() * 1000)
            
            if remaining_ms > 0:
                self.refresh_timer.start(remaining_ms)
                logger.info(f"Token refresh scheduled in {remaining_ms/1000/60:.1f} minutes")
                
    def save_auth_state(self):
        """Save authentication state to session manager"""
        if not self.session_manager:
            return
            
        try:
            # Only save non-sensitive data
            auth_data = {
                "access_token": self.auth_state.access_token,
                "refresh_token": self.auth_state.refresh_token,
                "expires_at": self.auth_state.token_expires_at.isoformat() if self.auth_state.token_expires_at else None,
                "is_authenticated": self.auth_state.is_authenticated
            }
            
            user_data = self.auth_state.user_info
            
            self.session_manager.set_user_preference("auth_tokens", auth_data)
            self.session_manager.set_user_preference("user_info", user_data)
            
        except Exception as e:
            logger.error(f"Failed to save auth state: {e}")
            
    def load_auth_state(self):
        """Load authentication state from session manager"""
        if not self.session_manager:
            return
            
        try:
            auth_data = self.session_manager.get_user_preference("auth_tokens")
            user_data = self.session_manager.get_user_preference("user_info")
            
            if auth_data and user_data:
                self.auth_state.access_token = auth_data.get("access_token")
                self.auth_state.refresh_token = auth_data.get("refresh_token")
                self.auth_state.user_info = user_data
                self.auth_state.is_authenticated = auth_data.get("is_authenticated", False)
                
                # Parse expiration time
                expires_str = auth_data.get("expires_at")
                if expires_str:
                    self.auth_state.token_expires_at = datetime.fromisoformat(expires_str)
                    
                # Check if token is still valid
                if self.auth_state.is_token_valid():
                    # Update API client
                    if self.api_client:
                        self.api_client.set_auth_token(self.auth_state.access_token)
                        
                    # Start refresh timer
                    self.start_refresh_timer()
                    
                    # Emit signals
                    self.auth_state_changed.emit(True)
                    self.user_info_updated.emit(user_data)
                    
                    logger.info("Authentication state restored from session")
                else:
                    # Token expired, try to refresh
                    if self.auth_state.refresh_token:
                        self.auto_refresh_token()
                    else:
                        self.logout()
                        
        except Exception as e:
            logger.error(f"Failed to load auth state: {e}")
            
    def force_refresh(self):
        """Force token refresh"""
        if self.auth_state.refresh_token:
            self.auto_refresh_token()
        else:
            self.auth_error.emit("No refresh token available. Please log in again.")