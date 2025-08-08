"""
Main Window for RAG Desktop Application
Professional PyQt6 interface with modern UI components
"""

import os
import sys
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QTabWidget,
    QScrollArea, QTextEdit, QPushButton, QLabel, QFrame, QSplitter,
    QListWidget, QListWidgetItem, QProgressBar, QFileDialog, QMessageBox,
    QStatusBar, QMenuBar, QMenu, QSystemTrayIcon, QApplication, QGridLayout,
    QSizePolicy, QSpacerItem, QDialog, QDialogButtonBox, QFormLayout,
    QLineEdit, QCheckBox, QSlider, QComboBox, QStackedWidget, QGroupBox
)
from PyQt6.QtCore import (
    Qt, QThread, pyqtSignal, QTimer, QPropertyAnimation, QEasingCurve,
    QRect, QSize, QUrl, QPoint, QEvent
)
from PyQt6.QtGui import (
    QFont, QPixmap, QIcon, QPalette, QColor, QPainter, QLinearGradient,
    QBrush, QAction, QDesktopServices, QKeySequence, QShortcut, QPen,
    QTextCharFormat, QSyntaxHighlighter, QTextDocument
)

from api_client import SyncAPIClient, APIError
from session_manager import SessionManager
from auth_manager import AuthenticationManager
from login_widget import AuthenticationWidget, UserProfileWidget
from system_tray_manager import (
    initialize_system_tray, get_system_tray_manager, cleanup_system_tray,
    NotificationLevel
)
from background_operations import (
    initialize_background_operations, get_background_operations_manager, 
    cleanup_background_operations
)

logger = logging.getLogger(__name__)

class MessageBubble(QFrame):
    """Custom message bubble widget with modern styling"""
    
    def __init__(self, message: str, is_user: bool = False, timestamp: Optional[str] = None):
        super().__init__()
        self.message = message
        self.is_user = is_user
        self.timestamp = timestamp or datetime.now().strftime("%H:%M")
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the message bubble UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)
        
        # Message content
        self.message_label = QLabel(self.message)
        self.message_label.setWordWrap(True)
        self.message_label.setTextInteractionFlags(
            Qt.TextInteractionFlag.TextSelectableByMouse | 
            Qt.TextInteractionFlag.LinksAccessibleByMouse
        )
        self.message_label.setOpenExternalLinks(True)
        
        # Timestamp
        self.time_label = QLabel(self.timestamp)
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignRight if self.is_user else Qt.AlignmentFlag.AlignLeft)
        
        # Apply styling
        if self.is_user:
            self.setProperty("class", "message-bubble-user")
            self.message_label.setStyleSheet("color: #ffffff; font-size: 14px; background: transparent;")
            self.time_label.setStyleSheet("color: rgba(255, 255, 255, 0.7); font-size: 11px;")
        else:
            self.setProperty("class", "message-bubble-assistant")
            self.message_label.setStyleSheet("color: #e5e5e5; font-size: 14px; background: transparent;")
            self.time_label.setStyleSheet("color: rgba(229, 229, 229, 0.6); font-size: 11px;")
        
        layout.addWidget(self.message_label)
        layout.addWidget(self.time_label)
        
        # Set maximum width for better readability
        self.setMaximumWidth(600)

class ChatInputWidget(QWidget):
    """Custom chat input widget with send button and file attachment"""
    
    message_sent = pyqtSignal(str)
    file_attached = pyqtSignal(list)
    
    def __init__(self):
        super().__init__()
        self.setup_ui()
        
    def setup_ui(self):
        """Setup the chat input UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(16, 16, 16, 16)
        layout.setSpacing(12)
        
        # Input container
        input_container = QFrame()
        input_container.setProperty("class", "glass-panel")
        input_layout = QHBoxLayout(input_container)
        input_layout.setContentsMargins(8, 8, 8, 8)
        input_layout.setSpacing(8)
        
        # Text input
        self.text_input = QTextEdit()
        self.text_input.setProperty("class", "chat-input")
        self.text_input.setPlaceholderText("Ask anything about your documents... (Ctrl+Enter to send)")
        self.text_input.setMaximumHeight(120)
        self.text_input.installEventFilter(self)
        
        # Button container
        button_container = QWidget()
        button_layout = QVBoxLayout(button_container)
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(4)
        
        # Attach button
        self.attach_button = QPushButton("📎")
        self.attach_button.setProperty("class", "secondary")
        self.attach_button.setFixedSize(40, 40)
        self.attach_button.setToolTip("Attach files")
        self.attach_button.clicked.connect(self.attach_files)
        
        # Send button
        self.send_button = QPushButton("⚡")
        self.send_button.setProperty("class", "primary")
        self.send_button.setFixedSize(40, 40)
        self.send_button.setToolTip("Send message (Ctrl+Enter)")
        self.send_button.clicked.connect(self.send_message)
        
        button_layout.addWidget(self.attach_button)
        button_layout.addWidget(self.send_button)
        button_layout.addStretch()
        
        input_layout.addWidget(self.text_input)
        input_layout.addWidget(button_container)
        
        layout.addWidget(input_container)
        
    def eventFilter(self, obj, event):
        """Handle keyboard events"""
        if obj == self.text_input and event.type() == QEvent.Type.KeyPress:
            if event.key() == Qt.Key.Key_Return:
                if event.modifiers() == Qt.KeyboardModifier.ControlModifier:
                    self.send_message()
                    return True
                elif event.modifiers() == Qt.KeyboardModifier.ShiftModifier:
                    # Allow Shift+Enter for new line
                    return False
                else:
                    # Default Enter behavior (new line)
                    return False
        return super().eventFilter(obj, event)
        
    def send_message(self):
        """Send the current message"""
        text = self.text_input.toPlainText().strip()
        if text:
            self.message_sent.emit(text)
            self.text_input.clear()
            
    def attach_files(self):
        """Open file dialog for attachments"""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Select files to attach",
            "",
            "Documents (*.pdf *.docx *.txt *.md);;All Files (*)"
        )
        if file_paths:
            self.file_attached.emit(file_paths)
            
    def set_enabled(self, enabled: bool):
        """Enable/disable input controls"""
        self.text_input.setEnabled(enabled)
        self.send_button.setEnabled(enabled)
        self.attach_button.setEnabled(enabled)

class ChatWidget(QWidget):
    """Main chat interface widget"""
    
    def __init__(self, api_client: SyncAPIClient, session_manager: SessionManager):
        super().__init__()
        self.api_client = api_client
        self.session_manager = session_manager
        self.current_response_bubble = None
        self.setup_ui()
        self.load_chat_history()
        
    def setup_ui(self):
        """Setup the chat interface"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Chat history area
        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        
        self.chat_widget = QWidget()
        self.chat_layout = QVBoxLayout(self.chat_widget)
        self.chat_layout.setContentsMargins(20, 20, 20, 20)
        self.chat_layout.setSpacing(12)
        self.chat_layout.addStretch()  # Push messages to bottom initially
        
        self.scroll_area.setWidget(self.chat_widget)
        
        # Welcome message
        if not self.session_manager.get_chat_history():
            self.add_welcome_message()
        
        # Input area
        self.input_widget = ChatInputWidget()
        self.input_widget.message_sent.connect(self.send_message)
        self.input_widget.file_attached.connect(self.handle_file_attachment)
        
        layout.addWidget(self.scroll_area)
        layout.addWidget(self.input_widget)
        
    def add_welcome_message(self):
        """Add welcome message to chat"""
        welcome_text = """👋 Welcome to RAG Desktop!

I'm your AI assistant powered by your documents. Here's what I can help you with:

• **Ask questions** about your uploaded documents
• **Search** across all your files semantically  
• **Get answers** with citations and sources
• **Web search** fallback for current information

Upload some documents and start chatting! 🚀"""
        
        self.add_message(welcome_text, is_user=False, save_to_history=False)
        
    def load_chat_history(self):
        """Load chat history from session manager"""
        history = self.session_manager.get_chat_history(limit=50)
        for entry in history:
            self.add_message(
                entry["message"], 
                entry["is_user"], 
                timestamp=entry.get("timestamp", ""),
                save_to_history=False
            )
            
    def add_message(self, message: str, is_user: bool = False, timestamp: Optional[str] = None, save_to_history: bool = True):
        """Add a message bubble to the chat"""
        # Create message bubble
        bubble = MessageBubble(message, is_user, timestamp)
        
        # Add to layout (before the stretch)
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, bubble)
        
        # Save to history
        if save_to_history:
            self.session_manager.add_chat_message(message, is_user, timestamp)
        
        # Auto-scroll to bottom
        QTimer.singleShot(100, self.scroll_to_bottom)
        
    def scroll_to_bottom(self):
        """Scroll chat to bottom"""
        scrollbar = self.scroll_area.verticalScrollBar()
        scrollbar.setValue(scrollbar.maximum())
        
    def send_message(self, message: str):
        """Send message to RAG system"""
        # Add user message
        self.add_message(message, is_user=True)
        
        # Disable input
        self.input_widget.set_enabled(False)
        
        # Create thinking bubble
        self.current_response_bubble = MessageBubble("🤔 Thinking...", is_user=False)
        self.chat_layout.insertWidget(self.chat_layout.count() - 1, self.current_response_bubble)
        self.scroll_to_bottom()
        
        # Start worker thread
        self.worker_thread = ChatWorkerThread(self.api_client, message)
        self.worker_thread.response_received.connect(self.handle_response)
        self.worker_thread.error_occurred.connect(self.handle_error)
        self.worker_thread.start()
        
    def handle_file_attachment(self, file_paths: List[str]):
        """Handle file attachment"""
        upload_thread = UploadWorkerThread(self.api_client, file_paths)
        upload_thread.upload_completed.connect(self.handle_upload_completed)
        upload_thread.error_occurred.connect(self.handle_upload_error)
        upload_thread.start()
        
        # Show upload status
        file_names = [Path(fp).name for fp in file_paths]
        status_msg = f"📤 Uploading {len(file_paths)} file(s): {', '.join(file_names)}"
        self.add_message(status_msg, is_user=False)
        
    def handle_upload_completed(self, results: List[Dict[str, Any]]):
        """Handle upload completion"""
        successful = [r for r in results if r.get("success")]
        failed = [r for r in results if not r.get("success")]
        
        if successful:
            msg = f"✅ Successfully uploaded {len(successful)} document(s)!"
            self.add_message(msg, is_user=False)
            
        if failed:
            msg = f"❌ Failed to upload {len(failed)} document(s)"
            self.add_message(msg, is_user=False)
            
    def handle_upload_error(self, error: str):
        """Handle upload error"""
        self.add_message(f"❌ Upload error: {error}", is_user=False)
        
    def handle_response(self, response: str):
        """Handle RAG response"""
        # Remove thinking bubble
        if self.current_response_bubble:
            self.current_response_bubble.setParent(None)
            self.current_response_bubble = None
            
        # Add response bubble
        self.add_message(response, is_user=False)
        
        # Re-enable input
        self.input_widget.set_enabled(True)
        
    def handle_error(self, error: str):
        """Handle chat error"""
        # Remove thinking bubble
        if self.current_response_bubble:
            self.current_response_bubble.setParent(None)
            self.current_response_bubble = None
            
        # Add error message
        self.add_message(f"❌ Error: {error}", is_user=False)
        
        # Re-enable input
        self.input_widget.set_enabled(True)
        
    def clear_chat(self):
        """Clear chat history"""
        # Remove all message bubbles
        for i in reversed(range(self.chat_layout.count())):
            item = self.chat_layout.itemAt(i)
            if item and item.widget() and isinstance(item.widget(), MessageBubble):
                item.widget().setParent(None)
                
        # Clear session history
        self.session_manager.clear_chat_history()
        
        # Add welcome message
        self.add_welcome_message()

class DocumentWidget(QWidget):
    """Document management widget"""
    
    def __init__(self, api_client: SyncAPIClient, session_manager: SessionManager):
        super().__init__()
        self.api_client = api_client
        self.session_manager = session_manager
        self.setup_ui()
        self.refresh_documents()
        
    def setup_ui(self):
        """Setup document management UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(16)
        
        # Header
        header_layout = QHBoxLayout()
        
        title_label = QLabel("📄 Document Management")
        title_label.setProperty("class", "title")
        
        self.refresh_button = QPushButton("🔄 Refresh")
        self.refresh_button.setProperty("class", "secondary")
        self.refresh_button.clicked.connect(self.refresh_documents)
        
        header_layout.addWidget(title_label)
        header_layout.addStretch()
        header_layout.addWidget(self.refresh_button)
        
        # Upload area
        upload_frame = QFrame()
        upload_frame.setProperty("class", "card")
        upload_layout = QVBoxLayout(upload_frame)
        
        upload_label = QLabel("Upload Documents")
        upload_label.setProperty("class", "subtitle")
        
        self.upload_button = QPushButton("📁 Select Files")
        self.upload_button.setProperty("class", "success")
        self.upload_button.clicked.connect(self.upload_documents)
        
        self.drag_label = QLabel("or drag and drop files here")
        self.drag_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.drag_label.setStyleSheet("color: #a1a1aa; font-style: italic;")
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setStyleSheet("QProgressBar { margin: 8px 0; }")
        
        upload_layout.addWidget(upload_label)
        upload_layout.addWidget(self.upload_button)
        upload_layout.addWidget(self.drag_label)
        upload_layout.addWidget(self.progress_bar)
        
        # Documents list
        list_label = QLabel("Your Documents")
        list_label.setProperty("class", "subtitle")
        
        self.documents_list = QListWidget()
        self.documents_list.itemDoubleClicked.connect(self.view_document_details)
        
        # Document actions
        actions_layout = QHBoxLayout()
        
        self.delete_button = QPushButton("🗑️ Delete")
        self.delete_button.setProperty("class", "danger")
        self.delete_button.clicked.connect(self.delete_selected_document)
        self.delete_button.setEnabled(False)
        
        self.process_button = QPushButton("⚙️ Reprocess")
        self.process_button.setProperty("class", "secondary")
        self.process_button.clicked.connect(self.reprocess_selected_document)
        self.process_button.setEnabled(False)
        
        actions_layout.addWidget(self.delete_button)
        actions_layout.addWidget(self.process_button)
        actions_layout.addStretch()
        
        # Connect list selection
        self.documents_list.itemSelectionChanged.connect(self.on_selection_changed)
        
        # Layout assembly
        layout.addLayout(header_layout)
        layout.addWidget(upload_frame)
        layout.addWidget(list_label)
        layout.addWidget(self.documents_list)
        layout.addLayout(actions_layout)
        
        # Enable drag and drop
        self.setAcceptDrops(True)
        
    def dragEnterEvent(self, event):
        """Handle drag enter"""
        if event.mimeData().hasUrls():
            event.acceptProposedAction()
            
    def dropEvent(self, event):
        """Handle file drop"""
        file_paths = []
        for url in event.mimeData().urls():
            if url.isLocalFile():
                file_paths.append(url.toLocalFile())
        
        if file_paths:
            self.upload_files(file_paths)
            
    def upload_documents(self):
        """Open file dialog for document upload"""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Documents",
            "",
            "Documents (*.pdf *.docx *.txt *.md);;All Files (*)"
        )
        
        if file_paths:
            self.upload_files(file_paths)
            
    def upload_files(self, file_paths: List[str]):
        """Upload files to backend"""
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, len(file_paths))
        self.progress_bar.setValue(0)
        self.upload_button.setEnabled(False)
        
        # Start upload thread
        self.upload_thread = UploadWorkerThread(self.api_client, file_paths)
        self.upload_thread.upload_progress.connect(self.update_upload_progress)
        self.upload_thread.upload_completed.connect(self.handle_upload_completed)
        self.upload_thread.error_occurred.connect(self.handle_upload_error)
        self.upload_thread.start()
        
    def update_upload_progress(self, current: int, total: int):
        """Update upload progress"""
        self.progress_bar.setValue(current)
        
    def handle_upload_completed(self, results: List[Dict[str, Any]]):
        """Handle upload completion"""
        self.progress_bar.setVisible(False)
        self.upload_button.setEnabled(True)
        
        successful = sum(1 for r in results if r.get("success"))
        total = len(results)
        
        if successful == total:
            QMessageBox.information(self, "Success", f"Successfully uploaded {successful} document(s)!")
        else:
            failed = total - successful
            QMessageBox.warning(self, "Partial Success", f"Uploaded {successful}/{total} documents. {failed} failed.")
            
        self.refresh_documents()
        
    def handle_upload_error(self, error: str):
        """Handle upload error"""
        self.progress_bar.setVisible(False)
        self.upload_button.setEnabled(True)
        QMessageBox.critical(self, "Upload Error", f"Upload failed: {error}")
        
    def refresh_documents(self):
        """Refresh documents list"""
        self.refresh_button.setEnabled(False)
        self.refresh_button.setText("Loading...")
        
        self.list_thread = DocumentListWorkerThread(self.api_client)
        self.list_thread.documents_loaded.connect(self.handle_documents_loaded)
        self.list_thread.error_occurred.connect(self.handle_list_error)
        self.list_thread.start()
        
    def handle_documents_loaded(self, documents: List[Dict[str, Any]]):
        """Handle documents list loading"""
        self.refresh_button.setEnabled(True)
        self.refresh_button.setText("🔄 Refresh")
        
        self.documents_list.clear()
        
        for doc in documents:
            title = doc.get("title", "Unknown")
            file_type = doc.get("file_type", "unknown")
            status = doc.get("processing_status", "unknown")
            
            # Create list item
            item_text = f"📄 {title} ({file_type.upper()}) - {status.title()}"
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, doc)
            
            # Color coding based on status
            if status == "completed":
                item.setForeground(QColor("#10b981"))
            elif status == "processing":
                item.setForeground(QColor("#f59e0b"))
            else:
                item.setForeground(QColor("#ef4444"))
                
            self.documents_list.addItem(item)
            
    def handle_list_error(self, error: str):
        """Handle document list error"""
        self.refresh_button.setEnabled(True)
        self.refresh_button.setText("🔄 Refresh")
        QMessageBox.warning(self, "Error", f"Failed to load documents: {error}")
        
    def on_selection_changed(self):
        """Handle selection change"""
        has_selection = bool(self.documents_list.selectedItems())
        self.delete_button.setEnabled(has_selection)
        self.process_button.setEnabled(has_selection)
        
    def delete_selected_document(self):
        """Delete selected document"""
        item = self.documents_list.currentItem()
        if not item:
            return
            
        doc = item.data(Qt.ItemDataRole.UserRole)
        doc_id = doc.get("id")
        title = doc.get("title", "Unknown")
        
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete '{title}'?\n\nThis action cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Start delete thread
            self.delete_thread = DeleteDocumentWorkerThread(self.api_client, doc_id)
            self.delete_thread.deletion_completed.connect(self.handle_deletion_completed)
            self.delete_thread.error_occurred.connect(self.handle_deletion_error)
            self.delete_thread.start()
            
    def handle_deletion_completed(self, success: bool):
        """Handle document deletion"""
        if success:
            QMessageBox.information(self, "Success", "Document deleted successfully!")
            self.refresh_documents()
        else:
            QMessageBox.warning(self, "Error", "Failed to delete document")
            
    def handle_deletion_error(self, error: str):
        """Handle deletion error"""
        QMessageBox.critical(self, "Delete Error", f"Failed to delete document: {error}")
        
    def reprocess_selected_document(self):
        """Reprocess selected document"""
        item = self.documents_list.currentItem()
        if not item:
            return
            
        doc = item.data(Qt.ItemDataRole.UserRole)
        doc_id = doc.get("id")
        title = doc.get("title", "Unknown")
        
        reply = QMessageBox.question(
            self,
            "Confirm Reprocess",
            f"Reprocess '{title}'?\n\nThis will re-chunk and re-embed the document.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Start reprocess thread
            self.reprocess_thread = ReprocessDocumentWorkerThread(self.api_client, doc_id)
            self.reprocess_thread.reprocess_completed.connect(self.handle_reprocess_completed)
            self.reprocess_thread.error_occurred.connect(self.handle_reprocess_error)
            self.reprocess_thread.start()
            
    def handle_reprocess_completed(self, success: bool):
        """Handle document reprocessing"""
        if success:
            QMessageBox.information(self, "Success", "Document reprocessed successfully!")
            self.refresh_documents()
        else:
            QMessageBox.warning(self, "Error", "Failed to reprocess document")
            
    def handle_reprocess_error(self, error: str):
        """Handle reprocess error"""
        QMessageBox.critical(self, "Reprocess Error", f"Failed to reprocess document: {error}")
        
    def view_document_details(self, item: QListWidgetItem):
        """View document details"""
        doc = item.data(Qt.ItemDataRole.UserRole)
        dialog = DocumentDetailsDialog(doc, self)
        dialog.exec()

class SettingsWidget(QWidget):
    """Settings and preferences widget"""
    
    def __init__(self, session_manager: SessionManager):
        super().__init__()
        self.session_manager = session_manager
        self.setup_ui()
        self.load_settings()
        
    def setup_ui(self):
        """Setup settings UI"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        layout.setSpacing(20)
        
        # Title
        title_label = QLabel("⚙️ Settings")
        title_label.setProperty("class", "title")
        layout.addWidget(title_label)
        
        # API Settings
        api_group = QFrame()
        api_group.setProperty("class", "card")
        api_layout = QFormLayout(api_group)
        
        api_title = QLabel("API Configuration")
        api_title.setProperty("class", "subtitle")
        api_layout.addRow(api_title)
        
        self.api_url_input = QLineEdit()
        self.api_url_input.setPlaceholderText("http://localhost:8000")
        api_layout.addRow("Backend URL:", self.api_url_input)
        
        # UI Settings
        ui_group = QFrame()
        ui_group.setProperty("class", "card")
        ui_layout = QFormLayout(ui_group)
        
        ui_title = QLabel("Interface")
        ui_title.setProperty("class", "subtitle")
        ui_layout.addRow(ui_title)
        
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(["Dark", "Light", "Auto"])
        ui_layout.addRow("Theme:", self.theme_combo)
        
        self.auto_scroll_check = QCheckBox("Auto-scroll to new messages")
        ui_layout.addRow(self.auto_scroll_check)
        
        # Chat Settings
        chat_group = QFrame()
        chat_group.setProperty("class", "card")
        chat_layout = QFormLayout(chat_group)
        
        chat_title = QLabel("Chat Preferences")
        chat_title.setProperty("class", "subtitle")
        chat_layout.addRow(chat_title)
        
        self.save_history_check = QCheckBox("Save chat history")
        chat_layout.addRow(self.save_history_check)
        
        self.history_limit_slider = QSlider(Qt.Orientation.Horizontal)
        self.history_limit_slider.setRange(50, 1000)
        self.history_limit_slider.setValue(500)
        self.history_limit_label = QLabel("500 messages")
        self.history_limit_slider.valueChanged.connect(
            lambda v: self.history_limit_label.setText(f"{v} messages")
        )
        chat_layout.addRow("History limit:", self.history_limit_slider)
        chat_layout.addRow("", self.history_limit_label)
        
        # Action buttons
        button_layout = QHBoxLayout()
        
        self.save_button = QPushButton("💾 Save Settings")
        self.save_button.setProperty("class", "primary")
        self.save_button.clicked.connect(self.save_settings)
        
        self.reset_button = QPushButton("🔄 Reset to Defaults")
        self.reset_button.setProperty("class", "secondary")
        self.reset_button.clicked.connect(self.reset_settings)
        
        self.clear_cache_button = QPushButton("🗑️ Clear Cache")
        self.clear_cache_button.setProperty("class", "danger")
        self.clear_cache_button.clicked.connect(self.clear_cache)
        
        button_layout.addWidget(self.save_button)
        button_layout.addWidget(self.reset_button)
        button_layout.addStretch()
        button_layout.addWidget(self.clear_cache_button)
        
        # Layout assembly
        layout.addWidget(api_group)
        layout.addWidget(ui_group)
        layout.addWidget(chat_group)
        layout.addLayout(button_layout)
        layout.addStretch()
        
    def load_settings(self):
        """Load settings from session manager"""
        # API settings
        api_url = self.session_manager.get_api_base_url()
        self.api_url_input.setText(api_url)
        
        # UI settings
        theme = self.session_manager.get_user_preference("theme", "Dark")
        self.theme_combo.setCurrentText(theme)
        
        auto_scroll = self.session_manager.get_user_preference("auto_scroll", True)
        self.auto_scroll_check.setChecked(auto_scroll)
        
        # Chat settings
        save_history = self.session_manager.get_user_preference("save_history", True)
        self.save_history_check.setChecked(save_history)
        
        history_limit = self.session_manager.get_user_preference("history_limit", 500)
        self.history_limit_slider.setValue(history_limit)
        
    def save_settings(self):
        """Save current settings"""
        # API settings
        api_url = self.api_url_input.text().strip()
        if api_url:
            self.session_manager.set_api_base_url(api_url)
        
        # UI settings
        self.session_manager.set_user_preference("theme", self.theme_combo.currentText())
        self.session_manager.set_user_preference("auto_scroll", self.auto_scroll_check.isChecked())
        
        # Chat settings
        self.session_manager.set_user_preference("save_history", self.save_history_check.isChecked())
        self.session_manager.set_user_preference("history_limit", self.history_limit_slider.value())
        
        QMessageBox.information(self, "Success", "Settings saved successfully!")
        
    def reset_settings(self):
        """Reset settings to defaults"""
        reply = QMessageBox.question(
            self,
            "Confirm Reset",
            "Reset all settings to defaults?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Reset to defaults
            self.api_url_input.setText("http://localhost:8000")
            self.theme_combo.setCurrentText("Dark")
            self.auto_scroll_check.setChecked(True)
            self.save_history_check.setChecked(True)
            self.history_limit_slider.setValue(500)
            
            QMessageBox.information(self, "Reset", "Settings reset to defaults. Click Save to apply.")
            
    def clear_cache(self):
        """Clear application cache"""
        reply = QMessageBox.question(
            self,
            "Confirm Clear Cache",
            "Clear all cached data?\n\nThis will remove temporary files and cached document information.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.session_manager.clear_document_cache()
            self.session_manager.cleanup_old_cache(days=0)  # Clear all
            QMessageBox.information(self, "Success", "Cache cleared successfully!")

class UserMenuWidget(QWidget):
    """User menu widget for the top bar"""
    
    logout_requested = pyqtSignal()
    profile_requested = pyqtSignal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.user_info = {}
        self.setup_ui()
        
    def setup_ui(self):
        """Setup user menu UI"""
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 4, 8, 4)
        layout.setSpacing(8)
        
        # User avatar/name button
        self.user_button = QPushButton("👤 Guest")
        self.user_button.setProperty("class", "secondary")
        self.user_button.setFixedHeight(32)
        self.user_button.clicked.connect(self.profile_requested.emit)
        
        # Dropdown menu (will be implemented as context menu)
        self.user_button.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.user_button.customContextMenuRequested.connect(self.show_user_menu)
        
        layout.addWidget(self.user_button)
        
    def update_user_info(self, user_info: dict):
        """Update user information"""
        self.user_info = user_info
        
        if user_info:
            name = user_info.get("name", "User")
            is_demo = user_info.get("demo_mode", False)
            
            if is_demo:
                self.user_button.setText(f"🎯 {name}")
                self.user_button.setToolTip("Demo Mode - Full features available")
            else:
                first_name = name.split()[0] if name else "User"
                self.user_button.setText(f"👤 {first_name}")
                self.user_button.setToolTip(f"Authenticated as {user_info.get('email', 'unknown')}")
        else:
            self.user_button.setText("👤 Guest")
            self.user_button.setToolTip("Not authenticated")
            
    def show_user_menu(self, position):
        """Show user context menu"""
        menu = QMenu(self)
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
        """)
        
        if self.user_info:
            # User info header
            user_email = self.user_info.get("email", "unknown")
            info_action = menu.addAction(f"📧 {user_email}")
            info_action.setEnabled(False)
            
            menu.addSeparator()
            
            # Profile action
            profile_action = menu.addAction("👤 Profile")
            profile_action.triggered.connect(self.profile_requested.emit)
            
            menu.addSeparator()
            
            # Logout action
            logout_action = menu.addAction("🚪 Logout")
            logout_action.triggered.connect(self.logout_requested.emit)
        else:
            login_action = menu.addAction("🔑 Login")
            login_action.triggered.connect(self.profile_requested.emit)
            
        menu.exec(self.user_button.mapToGlobal(position))

# Worker Threads
class ChatWorkerThread(QThread):
    """Worker thread for chat operations"""
    response_received = pyqtSignal(str)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, api_client: SyncAPIClient, query: str):
        super().__init__()
        self.api_client = api_client
        self.query = query
        
    def run(self):
        try:
            response = self.api_client.rag_query(self.query)
            self.response_received.emit(response)
        except Exception as e:
            self.error_occurred.emit(str(e))

class UploadWorkerThread(QThread):
    """Worker thread for file uploads"""
    upload_progress = pyqtSignal(int, int)
    upload_completed = pyqtSignal(list)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, api_client: SyncAPIClient, file_paths: List[str]):
        super().__init__()
        self.api_client = api_client
        self.file_paths = file_paths
        
    def run(self):
        try:
            results = []
            for i, file_path in enumerate(self.file_paths):
                try:
                    result = self.api_client.upload_document(file_path)
                    results.append({"success": True, "data": result, "file": file_path})
                except Exception as e:
                    results.append({"success": False, "error": str(e), "file": file_path})
                
                self.upload_progress.emit(i + 1, len(self.file_paths))
                
            self.upload_completed.emit(results)
        except Exception as e:
            self.error_occurred.emit(str(e))

class DocumentListWorkerThread(QThread):
    """Worker thread for loading document list"""
    documents_loaded = pyqtSignal(list)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, api_client: SyncAPIClient):
        super().__init__()
        self.api_client = api_client
        
    def run(self):
        try:
            documents = self.api_client.get_documents()
            self.documents_loaded.emit(documents)
        except Exception as e:
            self.error_occurred.emit(str(e))

class DeleteDocumentWorkerThread(QThread):
    """Worker thread for document deletion"""
    deletion_completed = pyqtSignal(bool)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, api_client: SyncAPIClient, doc_id: str):
        super().__init__()
        self.api_client = api_client
        self.doc_id = doc_id
        
    def run(self):
        try:
            # Note: delete_document method needs to be implemented in SyncAPIClient
            success = True  # Placeholder
            self.deletion_completed.emit(success)
        except Exception as e:
            self.error_occurred.emit(str(e))

class ReprocessDocumentWorkerThread(QThread):
    """Worker thread for document reprocessing"""
    reprocess_completed = pyqtSignal(bool)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, api_client: SyncAPIClient, doc_id: str):
        super().__init__()
        self.api_client = api_client
        self.doc_id = doc_id
        
    def run(self):
        try:
            # Note: process_document method needs to be implemented in SyncAPIClient
            success = True  # Placeholder
            self.reprocess_completed.emit(success)
        except Exception as e:
            self.error_occurred.emit(str(e))

# Dialogs
class DocumentDetailsDialog(QDialog):
    """Dialog for viewing document details"""
    
    def __init__(self, document: Dict[str, Any], parent=None):
        super().__init__(parent)
        self.document = document
        self.setWindowTitle("Document Details")
        self.setModal(True)
        self.setup_ui()
        
    def setup_ui(self):
        """Setup dialog UI"""
        layout = QVBoxLayout(self)
        
        # Document info
        info_text = f"""
        <h3>{self.document.get('title', 'Unknown')}</h3>
        <p><b>Type:</b> {self.document.get('file_type', 'Unknown')}</p>
        <p><b>Size:</b> {self.document.get('size', 0)} bytes</p>
        <p><b>Upload Date:</b> {self.document.get('upload_time', 'Unknown')}</p>
        <p><b>Status:</b> {self.document.get('processing_status', 'Unknown')}</p>
        <p><b>Chunks:</b> {self.document.get('chunk_count', 0)}</p>
        """
        
        info_label = QLabel(info_text)
        info_label.setWordWrap(True)
        layout.addWidget(info_label)
        
        # Buttons
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

class MainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        self.api_client = SyncAPIClient()
        self.session_manager = SessionManager()
        
        # Authentication (Phase 12)
        self.auth_manager = AuthenticationManager(self.session_manager, self.api_client)
        self.is_authenticated = False
        self.current_user = {}
        
        # Phase 13: System Tray and Background Operations
        self.tray_manager = None
        self.background_ops = None
        self.minimize_to_tray_enabled = True
        self.close_to_tray_enabled = True
        
        self.setup_ui()
        self.setup_menu_bar()
        self.setup_status_bar()
        self.setup_authentication()
        
        # Phase 13: Initialize system tray and background operations
        self.setup_system_tray()
        self.setup_background_operations()
        
        self.load_styles()
        self.restore_window_state()
        self.check_backend_connection()
        
        # Apply tray settings
        self.apply_tray_settings()
        
    def setup_ui(self):
        """Setup main window UI"""
        self.setWindowTitle("RAG Desktop - AI Document Assistant")
        self.setMinimumSize(1000, 700)
        self.resize(1200, 800)
        
        # Central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Main layout
        layout = QVBoxLayout(central_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Top bar with connection status and user menu
        top_bar = QFrame()
        top_bar.setFixedHeight(50)
        top_bar.setStyleSheet("""
            QFrame {
                background: rgba(255, 255, 255, 0.05);
                border-bottom: 1px solid rgba(255, 255, 255, 0.1);
            }
        """)
        
        top_bar_layout = QHBoxLayout(top_bar)
        top_bar_layout.setContentsMargins(16, 8, 16, 8)
        
        # Connection status
        self.connection_label = QLabel("🔄 Checking connection...")
        self.connection_label.setStyleSheet("padding: 4px 12px; background: rgba(255, 193, 7, 0.1); color: #ffc107; border-radius: 4px; font-size: 12px;")
        
        # User menu
        self.user_menu = UserMenuWidget()
        self.user_menu.logout_requested.connect(self.logout_user)
        self.user_menu.profile_requested.connect(self.show_auth_dialog)
        
        top_bar_layout.addWidget(self.connection_label)
        top_bar_layout.addStretch()
        top_bar_layout.addWidget(self.user_menu)
        
        # Main content area
        self.content_stack = QStackedWidget()
        
        # Authentication widget (shown when not authenticated)
        self.auth_widget = AuthenticationWidget(self.auth_manager)
        self.auth_widget.authentication_changed.connect(self.on_authentication_changed)
        
        # Main app widget (shown when authenticated)
        self.main_app_widget = QWidget()
        self.setup_main_app_widget()
        
        # Add both to stack
        self.content_stack.addWidget(self.auth_widget)      # Index 0
        self.content_stack.addWidget(self.main_app_widget)  # Index 1
        
        # Initially show auth widget
        self.content_stack.setCurrentIndex(0)
        
        layout.addWidget(top_bar)
        layout.addWidget(self.content_stack)
        
    def setup_main_app_widget(self):
        """Setup the main application widget (tabs)"""
        layout = QVBoxLayout(self.main_app_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Tab widget
        self.tab_widget = QTabWidget()
        
        # Chat tab
        self.chat_widget = ChatWidget(self.api_client, self.session_manager)
        self.tab_widget.addTab(self.chat_widget, "💬 Chat")
        
        # Documents tab
        self.document_widget = DocumentWidget(self.api_client, self.session_manager)
        self.tab_widget.addTab(self.document_widget, "📄 Documents")
        
        # Settings tab
        self.settings_widget = SettingsWidget(self.session_manager)
        self.tab_widget.addTab(self.settings_widget, "⚙️ Settings")
        
        layout.addWidget(self.tab_widget)
        
    def setup_authentication(self):
        """Setup authentication system"""
        # Connect auth manager signals
        self.auth_manager.auth_state_changed.connect(self.on_auth_state_changed)
        self.auth_manager.user_info_updated.connect(self.on_user_info_updated)
        self.auth_manager.auth_error.connect(self.on_auth_error)
        
        # Check if already authenticated
        if self.auth_manager.is_authenticated():
            user_info = self.auth_manager.get_user_info()
            if user_info:
                self.on_user_info_updated(user_info)
                self.on_auth_state_changed(True)
                
    def on_authentication_changed(self, authenticated: bool, user_info: dict):
        """Handle authentication state change"""
        self.is_authenticated = authenticated
        self.current_user = user_info
        
        if authenticated:
            # Switch to main app
            self.content_stack.setCurrentIndex(1)
            self.user_menu.update_user_info(user_info)
            
            # Update window title
            user_name = user_info.get("name", "User")
            self.setWindowTitle(f"RAG Desktop - {user_name}")
            
            logger.info(f"User authenticated: {user_info.get('email', 'demo')}")
        else:
            # Switch to auth widget
            self.content_stack.setCurrentIndex(0)
            self.user_menu.update_user_info({})
            self.setWindowTitle("RAG Desktop - AI Document Assistant")
            
    def on_auth_state_changed(self, authenticated: bool):
        """Handle auth manager state change"""
        if not authenticated and self.is_authenticated:
            # User logged out
            self.on_authentication_changed(False, {})
            
    def on_user_info_updated(self, user_info: dict):
        """Handle user info update"""
        self.current_user = user_info
        self.user_menu.update_user_info(user_info)
        
    def on_auth_error(self, error_message: str):
        """Handle authentication error"""
        QMessageBox.warning(self, "Authentication Error", error_message)
        
    def logout_user(self):
        """Logout current user"""
        reply = QMessageBox.question(
            self,
            "Logout",
            "Are you sure you want to logout?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            self.auth_manager.logout()
            
    def show_auth_dialog(self):
        """Show authentication dialog"""
        if self.is_authenticated:
            # Show user profile
            self.show_user_profile()
        else:
            # Already showing auth widget, just ensure it's visible
            self.content_stack.setCurrentIndex(0)
            
    def show_user_profile(self):
        """Show user profile dialog"""
        dialog = QDialog(self)
        dialog.setWindowTitle("User Profile")
        dialog.setModal(True)
        dialog.setFixedSize(400, 300)
        
        layout = QVBoxLayout(dialog)
        
        # User profile widget
        profile_widget = UserProfileWidget()
        profile_widget.update_user_info(self.current_user)
        profile_widget.logout_requested.connect(dialog.accept)
        profile_widget.logout_requested.connect(self.logout_user)
        
        # Close button
        buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        buttons.rejected.connect(dialog.accept)
        
        layout.addWidget(profile_widget)
        layout.addWidget(buttons)
        
        dialog.exec()
        
    def setup_system_tray(self):
        """Setup system tray integration"""
        try:
            # Initialize system tray manager
            self.tray_manager = initialize_system_tray(self, self.session_manager)
            
            if self.tray_manager and self.tray_manager.is_initialized:
                # Connect tray signals
                self.tray_manager.tray_activated.connect(self.on_tray_activated)
                self.tray_manager.notification_clicked.connect(self.on_tray_notification_clicked)
                self.tray_manager.settings_changed.connect(self.on_tray_settings_changed)
                
                logger.info("System tray integration initialized")
                
                # Show startup notification if enabled
                self.show_tray_notification(
                    "RAG Desktop Started",
                    "Application is running in the system tray",
                    NotificationLevel.INFO
                )
            else:
                logger.warning("System tray not available")
                
        except Exception as e:
            logger.error(f"Failed to setup system tray: {e}")
            
    def setup_background_operations(self):
        """Setup background operations manager"""
        try:
            # Initialize background operations
            self.background_ops = initialize_background_operations(self.api_client, self.session_manager)
            
            if self.background_ops:
                # Connect background operation signals
                self.background_ops.task_started.connect(self.on_background_task_started)
                self.background_ops.task_progress.connect(self.on_background_task_progress)
                self.background_ops.task_completed.connect(self.on_background_task_completed)
                self.background_ops.health_status_changed.connect(self.on_health_status_changed)
                
                # Start health monitoring
                self.background_ops.start_health_monitoring()
                
                logger.info("Background operations initialized")
            else:
                logger.warning("Failed to initialize background operations")
                
        except Exception as e:
            logger.error(f"Failed to setup background operations: {e}")
            
    def apply_tray_settings(self):
        """Apply system tray settings"""
        if self.tray_manager:
            settings = self.tray_manager.settings
            
            self.minimize_to_tray_enabled = settings.get("minimize_to_tray", True)
            self.close_to_tray_enabled = settings.get("close_to_tray", True)
            
            # Start minimized if configured
            if settings.get("start_minimized", False):
                QTimer.singleShot(1000, self.hide)  # Hide after startup
                
    # System Tray Event Handlers
    def on_tray_activated(self, activation_type: str):
        """Handle system tray activation"""
        logger.debug(f"Tray activated: {activation_type}")
        
    def on_tray_notification_clicked(self, notification_id: str):
        """Handle tray notification click"""
        self.show()
        self.raise_()
        self.activateWindow()
        
    def on_tray_settings_changed(self, new_settings: Dict[str, Any]):
        """Handle tray settings change"""
        self.apply_tray_settings()
        
        # Show confirmation notification
        self.show_tray_notification(
            "Settings Updated",
            "System tray settings have been applied",
            NotificationLevel.SUCCESS
        )
        
    # Background Operations Event Handlers
    def on_background_task_started(self, task_id: str, task_type: str):
        """Handle background task start"""
        logger.info(f"Background task started: {task_id} ({task_type})")
        
        # Show notification for important tasks
        if task_type in ["document_processing"]:
            self.show_tray_notification(
                "Processing Document",
                "Document processing started in background",
                NotificationLevel.INFO,
                duration=3000
            )
            
    def on_background_task_progress(self, task_id: str, progress: int):
        """Handle background task progress"""
        logger.debug(f"Background task progress: {task_id} - {progress}%")
        
        # Update status bar or tray tooltip with progress
        if self.tray_manager and progress % 25 == 0:  # Update every 25%
            self.tray_manager.update_tray_icon()
            
    def on_background_task_completed(self, task_id: str, success: bool, message: str):
        """Handle background task completion"""
        logger.info(f"Background task completed: {task_id} - {'Success' if success else 'Failed'}: {message}")
        
        # Show completion notification
        if success:
            self.show_tray_notification(
                "Task Completed",
                message,
                NotificationLevel.SUCCESS,
                duration=3000
            )
        else:
            self.show_tray_notification(
                "Task Failed",
                message,
                NotificationLevel.ERROR,
                duration=5000
            )
            
    def on_health_status_changed(self, status: Dict[str, Any]):
        """Handle health status change"""
        overall_status = status.get("overall_status", "unknown")
        
        # Update UI based on health status
        if overall_status == "error":
            self.connection_label.setText("🔴 System Health: Error")
            self.connection_label.setStyleSheet("padding: 8px; background: rgba(239, 68, 68, 0.1); color: #ef4444;")
        elif overall_status == "degraded":
            self.connection_label.setText("🟡 System Health: Degraded")
            self.connection_label.setStyleSheet("padding: 8px; background: rgba(245, 158, 11, 0.1); color: #f59e0b;")
        else:
            self.connection_label.setText("🟢 System Health: Good")
            self.connection_label.setStyleSheet("padding: 8px; background: rgba(16, 185, 129, 0.1); color: #10b981;")
            
    # Utility Methods
    def show_tray_notification(self, title: str, message: str, level: str = NotificationLevel.INFO, duration: int = 5000):
        """Show system tray notification"""
        if self.tray_manager:
            self.tray_manager.show_notification(title, message, level, duration)
        else:
            logger.info(f"Notification: {title} - {message}")
            
    def schedule_document_processing(self, document_id: str):
        """Schedule document processing in background"""
        if self.background_ops:
            task_id = self.background_ops.schedule_document_processing(document_id)
            if task_id:
                logger.info(f"Scheduled document processing: {document_id} (task: {task_id})")
                return task_id
        return None
        
    def upload_documents(self):
        """Enhanced document upload with background processing"""
        # Switch to documents tab if we have tab_widget
        if hasattr(self, 'tab_widget'):
            self.tab_widget.setCurrentIndex(1)

        # Get file paths
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Documents",
            "",
            "Documents (*.pdf *.docx *.txt *.md);;All Files (*)"
        )

        if file_paths:
            # Upload files and schedule background processing
            for file_path in file_paths:
                try:
                    # Upload file
                    result = self.api_client.upload_document(file_path)
                    if result and "id" in result:
                        doc_id = result["id"]

                        # Schedule background processing
                        task_id = self.schedule_document_processing(doc_id)

                        if task_id:
                            self.show_tray_notification(
                                "Document Uploaded",
                                f"Processing {Path(file_path).name} in background",
                                NotificationLevel.INFO
                            )

                except Exception as e:
                    logger.error(f"Upload failed for {file_path}: {e}")
                    self.show_tray_notification(
                        "Upload Failed",
                        f"Failed to upload {Path(file_path).name}",
                        NotificationLevel.ERROR
                    )

            # Refresh document list
            if hasattr(self, 'document_widget'):
                self.document_widget.refresh_documents()
        
    # Override Window Event Handlers for Phase 13
    def closeEvent(self, event):
        """Handle window close event with tray integration"""
        if self.close_to_tray_enabled and self.tray_manager and self.tray_manager.is_initialized:
            # Minimize to tray instead of closing
            self.hide()
            
            # Show tray message on first minimize
            if not hasattr(self, '_first_tray_message_shown'):
                self.show_tray_notification(
                    "RAG Desktop",
                    "Application minimized to system tray. Right-click the tray icon to access options.",
                    NotificationLevel.INFO,
                    duration=4000
                )
                self._first_tray_message_shown = True
                
            event.ignore()
        else:
            # Normal close - save state and cleanup
            self.cleanup_and_exit()
            event.accept()
            
    def changeEvent(self, event):
        """Handle window state changes"""
        if event.type() == QEvent.Type.WindowStateChange:
            if self.isMinimized() and self.minimize_to_tray_enabled and self.tray_manager:
                # Hide window when minimized if tray is available
                QTimer.singleShot(0, self.hide)
        super().changeEvent(event)
        
    def cleanup_and_exit(self):
        """Cleanup resources before application exit"""
        try:
            # Save window state
            self.session_manager.save_window_state(self)
            
            # Cleanup background operations
            if self.background_ops:
                cleanup_background_operations()
                
            # Cleanup system tray
            if self.tray_manager:
                cleanup_system_tray()
                
            logger.info("Application cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            
    def setup_menu_bar(self):
        """Setup application menu bar with Phase 13 enhancements"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("&File")
        
        new_chat_action = QAction("&New Chat", self)
        new_chat_action.setShortcut(QKeySequence.StandardKey.New)
        new_chat_action.triggered.connect(self.new_chat)
        file_menu.addAction(new_chat_action)
        
        file_menu.addSeparator()
        
        upload_action = QAction("&Upload Documents...", self)
        upload_action.setShortcut(QKeySequence("Ctrl+U"))
        upload_action.triggered.connect(self.upload_documents)
        file_menu.addAction(upload_action)
        
        file_menu.addSeparator()
        
        # Phase 13: Background tasks menu
        tasks_action = QAction("Background &Tasks...", self)
        tasks_action.triggered.connect(self.show_background_tasks)
        file_menu.addAction(tasks_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut(QKeySequence.StandardKey.Quit)
        exit_action.triggered.connect(self.cleanup_and_exit)
        file_menu.addAction(exit_action)
        
        # Edit menu
        edit_menu = menubar.addMenu("&Edit")
        
        clear_chat_action = QAction("&Clear Chat", self)
        clear_chat_action.triggered.connect(self.clear_chat)
        edit_menu.addAction(clear_chat_action)
        
        # View menu
        view_menu = menubar.addMenu("&View")
        
        chat_action = QAction("&Chat", self)
        chat_action.setShortcut(QKeySequence("Ctrl+1"))
        chat_action.triggered.connect(lambda: self.tab_widget.setCurrentIndex(0))
        view_menu.addAction(chat_action)
        
        docs_action = QAction("&Documents", self)
        docs_action.setShortcut(QKeySequence("Ctrl+2"))
        docs_action.triggered.connect(lambda: self.tab_widget.setCurrentIndex(1))
        view_menu.addAction(docs_action)
        
        settings_action = QAction("&Settings", self)
        settings_action.setShortcut(QKeySequence("Ctrl+3"))
        settings_action.triggered.connect(lambda: self.tab_widget.setCurrentIndex(2))
        view_menu.addAction(settings_action)
        
        view_menu.addSeparator()
        
        # Phase 13: Window management
        minimize_tray_action = QAction("&Minimize to Tray", self)
        minimize_tray_action.setShortcut(QKeySequence("Ctrl+M"))
        minimize_tray_action.triggered.connect(self.hide)
        view_menu.addAction(minimize_tray_action)
        
        # Tools menu (Phase 13)
        tools_menu = menubar.addMenu("&Tools")
        
        system_status_action = QAction("&System Status", self)
        system_status_action.triggered.connect(self.show_system_status)
        tools_menu.addAction(system_status_action)
        
        tray_settings_action = QAction("&Tray Settings...", self)
        tray_settings_action.triggered.connect(self.show_tray_settings)
        tools_menu.addAction(tray_settings_action)
        
        tools_menu.addSeparator()
        
        background_settings_action = QAction("&Background Operations...", self)
        background_settings_action.triggered.connect(self.show_background_settings)
        tools_menu.addAction(background_settings_action)
        
        # Help menu
        help_menu = menubar.addMenu("&Help")
        
        about_action = QAction("&About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
        
    def setup_status_bar(self):
        """Setup status bar"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
    def new_chat(self):
        """Start a new chat session"""
        self.chat_widget.clear_chat()
        self.tab_widget.setCurrentIndex(0)  # Switch to chat tab
        
    def clear_chat(self):
        """Clear the chat history"""
        self.chat_widget.clear_chat()
        
    def show_about(self):
        """Show about dialog"""
        msg = QMessageBox(self)
        msg.setWindowTitle("About RAG Desktop")
        msg.setText("RAG Desktop - AI Document Assistant")
        msg.setInformativeText("Version 1.0.0\n\nA professional desktop application for RAG-powered document analysis and chat.")
        msg.setIcon(QMessageBox.Icon.Information)
        msg.exec()
        
    # New Menu Action Handlers (Phase 13)
    def show_background_tasks(self):
        """Show background tasks dialog"""
        if self.background_ops:
            dialog = QDialog(self)
            dialog.setWindowTitle("Background Tasks")
            dialog.setModal(True)
            dialog.setFixedSize(500, 400)
            
            layout = QVBoxLayout(dialog)
            
            # Active tasks
            active_label = QLabel("Active Tasks:")
            active_label.setStyleSheet("font-weight: bold; color: #ffffff; margin-bottom: 8px;")
            layout.addWidget(active_label)
            
            active_list = QListWidget()
            active_tasks = self.background_ops.get_active_tasks()
            
            if active_tasks:
                for task_id, task in active_tasks.items():
                    item_text = f"{task.task_type} - {task.progress}% - {task.status}"
                    active_list.addItem(item_text)
            else:
                active_list.addItem("No active tasks")
                
            layout.addWidget(active_list)
            
            # Pending tasks
            pending_label = QLabel("Pending Tasks:")
            pending_label.setStyleSheet("font-weight: bold; color: #ffffff; margin: 16px 0 8px 0;")
            layout.addWidget(pending_label)
            
            pending_list = QListWidget()
            pending_tasks = self.background_ops.get_pending_tasks()
            
            if pending_tasks:
                for task in pending_tasks:
                    item_text = f"{task.task_type} - Priority: {task.priority}"
                    pending_list.addItem(item_text)
            else:
                pending_list.addItem("No pending tasks")
                
            layout.addWidget(pending_list)
            
            # Close button
            buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
            buttons.rejected.connect(dialog.accept)
            layout.addWidget(buttons)
            
            dialog.exec()
        else:
            QMessageBox.information(self, "Background Tasks", "Background operations not available")
            
    def show_system_status(self):
        """Show system status dialog"""
        if self.tray_manager:
            self.tray_manager.show_system_status()
        else:
            QMessageBox.information(self, "System Status", "System monitoring not available")
            
    def show_tray_settings(self):
        """Show tray settings dialog"""
        if self.tray_manager:
            self.tray_manager.show_tray_settings()
        else:
            QMessageBox.information(self, "Tray Settings", "System tray not available")
            
    def show_background_settings(self):
        """Show background operations settings"""
        if not self.background_ops:
            QMessageBox.information(self, "Background Settings", "Background operations not available")
            return
            
        dialog = QDialog(self)
        dialog.setWindowTitle("Background Operations Settings")
        dialog.setModal(True)
        dialog.setFixedSize(400, 350)
        
        layout = QVBoxLayout(dialog)
        
        # Get current settings
        current_settings = self.background_ops.settings
        
        # Auto processing group
        processing_group = QGroupBox("Automatic Processing")
        processing_layout = QFormLayout(processing_group)
        
        auto_process_docs = QCheckBox()
        auto_process_docs.setChecked(current_settings.get("auto_process_documents", True))
        processing_layout.addRow("Auto-process documents:", auto_process_docs)
        
        # Monitoring group
        monitoring_group = QGroupBox("System Monitoring")
        monitoring_layout = QFormLayout(monitoring_group)
        
        health_monitoring = QCheckBox()
        health_monitoring.setChecked(current_settings.get("health_monitoring", True))
        monitoring_layout.addRow("Enable health monitoring:", health_monitoring)
        
        health_interval = QSpinBox()
        health_interval.setRange(30, 300)
        health_interval.setSuffix(" seconds")
        health_interval.setValue(current_settings.get("health_check_interval", 60))
        monitoring_layout.addRow("Check interval:", health_interval)
        
        # Task management group
        tasks_group = QGroupBox("Task Management")
        tasks_layout = QFormLayout(tasks_group)
        
        max_concurrent = QSpinBox()
        max_concurrent.setRange(1, 10)
        max_concurrent.setValue(current_settings.get("max_concurrent_tasks", 3))
        tasks_layout.addRow("Max concurrent tasks:", max_concurrent)
        
        auto_session_sync = QCheckBox()
        auto_session_sync.setChecked(current_settings.get("auto_session_sync", True))
        tasks_layout.addRow("Auto session sync:", auto_session_sync)
        
        auto_cache_cleanup = QCheckBox()
        auto_cache_cleanup.setChecked(current_settings.get("auto_cache_cleanup", True))
        tasks_layout.addRow("Auto cache cleanup:", auto_cache_cleanup)
        
        # Buttons
        buttons = QDialogButtonBox(
            QDialogButtonBox.StandardButton.Ok | 
            QDialogButtonBox.StandardButton.Cancel
        )
        
        def save_settings():
            new_settings = {
                "auto_process_documents": auto_process_docs.isChecked(),
                "health_monitoring": health_monitoring.isChecked(),
                "health_check_interval": health_interval.value(),
                "max_concurrent_tasks": max_concurrent.value(),
                "auto_session_sync": auto_session_sync.isChecked(),
                "auto_cache_cleanup": auto_cache_cleanup.isChecked()
            }
            self.background_ops.update_settings(new_settings)
            dialog.accept()
            
            self.show_tray_notification(
                "Settings Updated",
                "Background operations settings saved",
                NotificationLevel.SUCCESS
            )
            
        buttons.accepted.connect(save_settings)
        buttons.rejected.connect(dialog.reject)
        
        # Layout assembly
        layout.addWidget(processing_group)
        layout.addWidget(monitoring_group)
        layout.addWidget(tasks_group)
        layout.addStretch()
        layout.addWidget(buttons)
        
        dialog.exec()
        
    def load_styles(self):
        """Load application styles"""
        try:
            style_file = Path(__file__).parent / "styles.qss"
            if style_file.exists():
                with open(style_file, 'r', encoding='utf-8') as f:
                    self.setStyleSheet(f.read())
        except Exception as e:
            print(f"Failed to load styles: {e}")
            
    def restore_window_state(self):
        """Restore window state from session"""
        pass
        
    def check_backend_connection(self):
        """Check backend connection status"""
        # This will be implemented to show connection status
        pass


# Phase 13 integration functions (moved outside class)
def setup_phase13_integration():
    """Setup Phase 13 system integration"""
    # This function can be called to ensure Phase 13 is properly integrated
    logger.info("Phase 13 system integration initialized")

def cleanup_phase13_integration():
    """Cleanup Phase 13 system integration"""
    cleanup_background_operations()
    cleanup_system_tray()
    logger.info("Phase 13 system integration cleaned up")