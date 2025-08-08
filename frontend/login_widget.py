"""
Login Widget for RAG Desktop Application
Modern authentication interface with Google OAuth
"""

import logging
from typing import Optional

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFrame, QGraphicsDropShadowEffect, QProgressBar, QSpacerItem,
    QSizePolicy
)
from PyQt6.QtCore import Qt, pyqtSignal, QPropertyAnimation, QEasingCurve, QRect
from PyQt6.QtGui import QPixmap, QPainter, QLinearGradient, QBrush, QColor, QFont

from auth_manager import AuthenticationManager

logger = logging.getLogger(__name__)

class AnimatedButton(QPushButton):
    """Custom animated button with hover effects"""
    
    def __init__(self, text: str, parent=None):
        super().__init__(text, parent)
        self.setup_animation()
        
    def setup_animation(self):
        """Setup hover animation"""
        self.animation = QPropertyAnimation(self, b"geometry")
        self.animation.setDuration(200)
        self.animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        
    def enterEvent(self, event):
        """Handle mouse enter"""
        super().enterEvent(event)
        current_rect = self.geometry()
        hover_rect = QRect(
            current_rect.x() - 2,
            current_rect.y() - 2,
            current_rect.width() + 4,
            current_rect.height() + 4
        )
        self.animation.setStartValue(current_rect)
        self.animation.setEndValue(hover_rect)
        self.animation.start()
        
    def leaveEvent(self, event):
        """Handle mouse leave"""
        super().leaveEvent(event)
        # Reset to original size
        self.animation.setEndValue(self.animation.startValue())
        self.animation.start()

class UserProfileWidget(QWidget):
    """Widget showing authenticated user profile"""
    
    logout_requested = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.user_info = {}
        self.setup_ui()
        
    def setup_ui(self):
        """Setup user profile UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        
        # Profile card
        self.profile_card = QFrame()
        self.profile_card.setProperty("class", "glass-panel")
        self.profile_card.setFixedHeight(120)
        
        card_layout = QHBoxLayout(self.profile_card)
        card_layout.setContentsMargins(20, 20, 20, 20)
        card_layout.setSpacing(16)
        
        # Avatar placeholder
        self.avatar_label = QLabel("👤")
        self.avatar_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.avatar_label.setFixedSize(60, 60)
        self.avatar_label.setStyleSheet("""
            QLabel {
                background: rgba(59, 130, 246, 0.2);
                border: 2px solid rgba(59, 130, 246, 0.5);
                border-radius: 30px;
                font-size: 24px;
                color: #3b82f6;
            }
        """)
        
        # User info
        info_layout = QVBoxLayout()
        
        self.name_label = QLabel("Loading...")
        self.name_label.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffffff;")
        
        self.email_label = QLabel("user@example.com")
        self.email_label.setStyleSheet("font-size: 13px; color: #a1a1aa;")
        
        self.status_label = QLabel("✅ Authenticated")
        self.status_label.setStyleSheet("font-size: 12px; color: #10b981;")
        
        info_layout.addWidget(self.name_label)
        info_layout.addWidget(self.email_label)
        info_layout.addWidget(self.status_label)
        info_layout.addStretch()
        
        # Logout button
        self.logout_button = QPushButton("🚪 Logout")
        self.logout_button.setProperty("class", "secondary")
        self.logout_button.setFixedSize(80, 35)
        self.logout_button.clicked.connect(self.logout_requested.emit)
        
        card_layout.addWidget(self.avatar_label)
        card_layout.addLayout(info_layout)
        card_layout.addWidget(self.logout_button)
        
        layout.addWidget(self.profile_card)
        layout.addStretch()
        
    def update_user_info(self, user_info: dict):
        """Update displayed user information"""
        self.user_info = user_info
        
        name = user_info.get("name", "Unknown User")
        email = user_info.get("email", "unknown@example.com")
        
        self.name_label.setText(name)
        self.email_label.setText(email)
        
        # Update avatar with first letter of name
        if name and name != "Unknown User":
            first_letter = name[0].upper()
            self.avatar_label.setText(first_letter)

class LoginWidget(QWidget):
    """Main login widget with Google OAuth"""
    
    login_success = pyqtSignal(dict)  # user_info
    login_error = pyqtSignal(str)     # error_message
    
    def __init__(self, auth_manager: AuthenticationManager, parent=None):
        super().__init__(parent)
        self.auth_manager = auth_manager
        self.is_authenticating = False
        self.setup_ui()
        self.connect_signals()
        
    def setup_ui(self):
        """Setup login UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Main container
        container = QFrame()
        container.setFixedSize(400, 500)
        container.setProperty("class", "glass-panel")
        
        # Add drop shadow
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(20)
        shadow.setColor(QColor(0, 0, 0, 100))
        shadow.setOffset(0, 10)
        container.setGraphicsEffect(shadow)
        
        container_layout = QVBoxLayout(container)
        container_layout.setContentsMargins(40, 40, 40, 40)
        container_layout.setSpacing(30)
        
        # Logo and title
        logo_layout = QVBoxLayout()
        logo_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        logo_label = QLabel("🤖")
        logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        logo_label.setStyleSheet("font-size: 48px; margin-bottom: 10px;")
        
        title_label = QLabel("RAG Desktop")
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("""
            font-size: 24px;
            font-weight: bold;
            color: #ffffff;
            margin-bottom: 5px;
        """)
        
        subtitle_label = QLabel("AI Document Assistant")
        subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        subtitle_label.setStyleSheet("""
            font-size: 14px;
            color: #a1a1aa;
            margin-bottom: 20px;
        """)
        
        logo_layout.addWidget(logo_label)
        logo_layout.addWidget(title_label)
        logo_layout.addWidget(subtitle_label)
        
        # Login section
        login_section = QFrame()
        login_layout = QVBoxLayout(login_section)
        login_layout.setSpacing(20)
        
        welcome_label = QLabel("Welcome! Please sign in to continue.")
        welcome_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        welcome_label.setStyleSheet("color: #e5e5e5; font-size: 14px; margin-bottom: 10px;")
        
        # Google OAuth button
        self.google_button = AnimatedButton("🔑 Sign in with Google")
        self.google_button.setFixedHeight(50)
        self.google_button.setStyleSheet("""
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4285f4, stop:1 #1a73e8);
                border: none;
                border-radius: 25px;
                color: white;
                font-size: 16px;
                font-weight: bold;
                padding: 12px 24px;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #1a73e8, stop:1 #1557b0);
            }
            QPushButton:pressed {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #1557b0, stop:1 #0f4c75);
            }
            QPushButton:disabled {
                background: rgba(107, 114, 128, 0.5);
                color: rgba(255, 255, 255, 0.5);
            }
        """)
        self.google_button.clicked.connect(self.start_google_login)
        
        # Progress bar (hidden by default)
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 0)  # Indeterminate
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: none;
                border-radius: 8px;
                background: rgba(255, 255, 255, 0.1);
                height: 8px;
            }
            QProgressBar::chunk {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #3b82f6, stop:1 #1d4ed8);
                border-radius: 8px;
            }
        """)
        
        # Status label
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("color: #a1a1aa; font-size: 13px;")
        self.status_label.setVisible(False)
        
        # Demo mode button
        self.demo_button = QPushButton("🎯 Continue in Demo Mode")
        self.demo_button.setFixedHeight(45)
        self.demo_button.setStyleSheet("""
            QPushButton {
                background: rgba(255, 255, 255, 0.05);
                border: 2px solid rgba(255, 255, 255, 0.2);
                border-radius: 22px;
                color: #a1a1aa;
                font-size: 14px;
                font-weight: 500;
                padding: 10px 20px;
            }
            QPushButton:hover {
                background: rgba(255, 255, 255, 0.1);
                border: 2px solid rgba(255, 255, 255, 0.3);
                color: #e5e5e5;
            }
        """)
        self.demo_button.clicked.connect(self.start_demo_mode)
        
        login_layout.addWidget(welcome_label)
        login_layout.addWidget(self.google_button)
        login_layout.addWidget(self.progress_bar)
        login_layout.addWidget(self.status_label)
        login_layout.addSpacing(20)
        login_layout.addWidget(self.demo_button)
        
        # Features section
        features_layout = QVBoxLayout()
        features_label = QLabel("✨ What you'll get:")
        features_label.setStyleSheet("color: #e5e5e5; font-size: 13px; font-weight: bold; margin-bottom: 10px;")
        
        features_text = QLabel(
            "• 🤖 AI-powered document chat\n"
            "• 📄 Multi-format file support\n"
            "• 🔍 Semantic search & retrieval\n"
            "• 🌐 Web search integration\n"
            "• 💾 Secure session management"
        )
        features_text.setStyleSheet("color: #a1a1aa; font-size: 12px; line-height: 1.6;")
        
        features_layout.addWidget(features_label)
        features_layout.addWidget(features_text)
        
        # Assembly
        container_layout.addLayout(logo_layout)
        container_layout.addWidget(login_section)
        container_layout.addStretch()
        container_layout.addLayout(features_layout)
        
        layout.addWidget(container)
        
    def connect_signals(self):
        """Connect authentication manager signals"""
        self.auth_manager.auth_state_changed.connect(self.on_auth_state_changed)
        self.auth_manager.user_info_updated.connect(self.on_user_info_updated)
        self.auth_manager.auth_error.connect(self.on_auth_error)
        
    def start_google_login(self):
        """Start Google OAuth login process"""
        if self.is_authenticating:
            return
            
        self.is_authenticating = True
        self.google_button.setEnabled(False)
        self.demo_button.setEnabled(False)
        self.progress_bar.setVisible(True)
        self.status_label.setText("Starting authentication...")
        self.status_label.setVisible(True)
        
        # Start OAuth flow
        self.auth_manager.start_oauth_flow()
        
    def start_demo_mode(self):
        """Start in demo mode (no authentication)"""
        demo_user = {
            "id": "demo_user",
            "name": "Demo User",
            "email": "demo@ragdesktop.local",
            "picture": None,
            "demo_mode": True
        }
        
        self.login_success.emit(demo_user)
        
    def on_auth_state_changed(self, authenticated: bool):
        """Handle authentication state change"""
        self.is_authenticating = False
        self.google_button.setEnabled(True)
        self.demo_button.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.status_label.setVisible(False)
        
        if authenticated:
            logger.info("User authentication successful")
        else:
            logger.info("User logged out")
            
    def on_user_info_updated(self, user_info: dict):
        """Handle user info update"""
        self.login_success.emit(user_info)
        
    def on_auth_error(self, error_message: str):
        """Handle authentication error"""
        self.is_authenticating = False
        self.google_button.setEnabled(True)
        self.demo_button.setEnabled(True)
        self.progress_bar.setVisible(False)
        
        self.status_label.setText(f"❌ {error_message}")
        self.status_label.setStyleSheet("color: #ef4444; font-size: 13px;")
        self.status_label.setVisible(True)
        
        # Hide error after 5 seconds
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(5000, lambda: self.status_label.setVisible(False))
        
        self.login_error.emit(error_message)
        
    def reset_ui(self):
        """Reset UI to initial state"""
        self.is_authenticating = False
        self.google_button.setEnabled(True)
        self.demo_button.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.status_label.setVisible(False)

class AuthenticatedWidget(QWidget):
    """Widget shown when user is authenticated"""
    
    logout_requested = pyqtSignal()
    switch_user_requested = pyqtSignal()
    
    def __init__(self, auth_manager: AuthenticationManager, parent=None):
        super().__init__(parent)
        self.auth_manager = auth_manager
        self.setup_ui()
        
    def setup_ui(self):
        """Setup authenticated user UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # Welcome header
        header_frame = QFrame()
        header_frame.setProperty("class", "card")
        header_layout = QVBoxLayout(header_frame)
        
        welcome_label = QLabel("🎉 Welcome to RAG Desktop!")
        welcome_label.setStyleSheet("font-size: 18px; font-weight: bold; color: #10b981; margin-bottom: 5px;")
        
        subtitle_label = QLabel("You're now authenticated and ready to use all features.")
        subtitle_label.setStyleSheet("color: #e5e5e5; font-size: 14px;")
        
        header_layout.addWidget(welcome_label)
        header_layout.addWidget(subtitle_label)
        
        # User profile
        self.profile_widget = UserProfileWidget()
        self.profile_widget.logout_requested.connect(self.logout_requested.emit)
        
        # Quick actions
        actions_frame = QFrame()
        actions_frame.setProperty("class", "card")
        actions_layout = QVBoxLayout(actions_frame)
        
        actions_title = QLabel("🚀 Quick Actions")
        actions_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffffff; margin-bottom: 10px;")
        
        # Action buttons
        button_layout = QVBoxLayout()
        button_layout.setSpacing(10)
        
        chat_button = QPushButton("💬 Start Chatting")
        chat_button.setProperty("class", "primary")
        chat_button.setFixedHeight(45)
        
        upload_button = QPushButton("📄 Upload Documents")
        upload_button.setProperty("class", "success")
        upload_button.setFixedHeight(45)
        
        settings_button = QPushButton("⚙️ Settings")
        settings_button.setProperty("class", "secondary")
        settings_button.setFixedHeight(45)
        
        button_layout.addWidget(chat_button)
        button_layout.addWidget(upload_button)
        button_layout.addWidget(settings_button)
        
        actions_layout.addWidget(actions_title)
        actions_layout.addLayout(button_layout)
        
        # Account management
        account_frame = QFrame()
        account_frame.setProperty("class", "card")
        account_layout = QVBoxLayout(account_frame)
        
        account_title = QLabel("👤 Account")
        account_title.setStyleSheet("font-size: 16px; font-weight: bold; color: #ffffff; margin-bottom: 10px;")
        
        switch_user_button = QPushButton("🔄 Switch User")
        switch_user_button.setProperty("class", "secondary")
        switch_user_button.clicked.connect(self.switch_user_requested.emit)
        
        logout_button = QPushButton("🚪 Logout")
        logout_button.setProperty("class", "danger")
        logout_button.clicked.connect(self.logout_requested.emit)
        
        account_button_layout = QHBoxLayout()
        account_button_layout.addWidget(switch_user_button)
        account_button_layout.addWidget(logout_button)
        
        account_layout.addWidget(account_title)
        account_layout.addLayout(account_button_layout)
        
        # Assembly
        layout.addWidget(header_frame)
        layout.addWidget(self.profile_widget)
        layout.addWidget(actions_frame)
        layout.addWidget(account_frame)
        layout.addStretch()
        
    def update_user_info(self, user_info: dict):
        """Update user information display"""
        self.profile_widget.update_user_info(user_info)

class AuthenticationWidget(QWidget):
    """Main authentication widget that switches between login and authenticated states"""
    
    authentication_changed = pyqtSignal(bool, dict)  # authenticated, user_info
    
    def __init__(self, auth_manager: AuthenticationManager, parent=None):
        super().__init__(parent)
        self.auth_manager = auth_manager
        self.current_user_info = {}
        self.setup_ui()
        self.connect_signals()
        
        # Check initial auth state
        if self.auth_manager.is_authenticated():
            user_info = self.auth_manager.get_user_info()
            if user_info:
                self.show_authenticated_state(user_info)
            
    def setup_ui(self):
        """Setup main authentication UI"""
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(0, 0, 0, 0)
        
        # Login widget
        self.login_widget = LoginWidget(self.auth_manager)
        self.login_widget.login_success.connect(self.on_login_success)
        self.login_widget.login_error.connect(self.on_login_error)
        
        # Authenticated widget
        self.authenticated_widget = AuthenticatedWidget(self.auth_manager)
        self.authenticated_widget.logout_requested.connect(self.logout)
        self.authenticated_widget.switch_user_requested.connect(self.switch_user)
        
        # Initially show login
        self.layout.addWidget(self.login_widget)
        
    def connect_signals(self):
        """Connect authentication manager signals"""
        self.auth_manager.auth_state_changed.connect(self.on_auth_state_changed)
        self.auth_manager.user_info_updated.connect(self.on_user_info_updated)
        
    def show_login_state(self):
        """Show login interface"""
        # Clear layout
        while self.layout.count():
            child = self.layout.takeAt(0)
            if child.widget():
                child.widget().setParent(None)
                
        # Add login widget
        self.layout.addWidget(self.login_widget)
        self.login_widget.reset_ui()
        
    def show_authenticated_state(self, user_info: dict):
        """Show authenticated interface"""
        # Clear layout
        while self.layout.count():
            child = self.layout.takeAt(0)
            if child.widget():
                child.widget().setParent(None)
                
        # Add authenticated widget
        self.layout.addWidget(self.authenticated_widget)
        self.authenticated_widget.update_user_info(user_info)
        
    def on_login_success(self, user_info: dict):
        """Handle successful login"""
        self.current_user_info = user_info
        self.show_authenticated_state(user_info)
        self.authentication_changed.emit(True, user_info)
        
    def on_login_error(self, error_message: str):
        """Handle login error"""
        logger.error(f"Login error: {error_message}")
        
    def on_auth_state_changed(self, authenticated: bool):
        """Handle authentication state change"""
        if not authenticated:
            self.show_login_state()
            self.authentication_changed.emit(False, {})
            
    def on_user_info_updated(self, user_info: dict):
        """Handle user info update"""
        self.current_user_info = user_info
        if hasattr(self, 'authenticated_widget'):
            self.authenticated_widget.update_user_info(user_info)
            
    def logout(self):
        """Handle logout request"""
        self.auth_manager.logout()
        
    def switch_user(self):
        """Handle switch user request"""
        self.auth_manager.logout()
        # The auth_state_changed signal will trigger showing login state