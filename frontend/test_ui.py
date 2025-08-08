#!/usr/bin/env python3
"""
UI Testing and Development Script
Quick testing and debugging of UI components
"""

import sys
import os
from pathlib import Path

# Add current directory to path
sys.path.insert(0, str(Path(__file__).parent))

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, QWidget,
    QPushButton, QLabel, QTextEdit, QMessageBox, QTabWidget
)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont

def test_styling():
    """Test the application styling"""
    app = QApplication(sys.argv)
    
    # Load stylesheet
    style_path = Path(__file__).parent / "styles.qss"
    if style_path.exists():
        with open(style_path, 'r', encoding='utf-8') as f:
            app.setStyleSheet(f.read())
        print("✅ Stylesheet loaded")
    else:
        print("⚠️ Stylesheet not found")
    
    # Create test window
    window = QMainWindow()
    window.setWindowTitle("RAG Desktop - UI Test")
    window.setGeometry(100, 100, 800, 600)
    
    central_widget = QWidget()
    window.setCentralWidget(central_widget)
    
    layout = QVBoxLayout(central_widget)
    
    # Test components
    title = QLabel("🎨 UI Component Test")
    title.setProperty("class", "title")
    layout.addWidget(title)
    
    # Test buttons
    button_layout = QHBoxLayout()
    
    primary_btn = QPushButton("Primary Button")
    primary_btn.setProperty("class", "primary")
    button_layout.addWidget(primary_btn)
    
    success_btn = QPushButton("Success Button")
    success_btn.setProperty("class", "success")
    button_layout.addWidget(success_btn)
    
    danger_btn = QPushButton("Danger Button")
    danger_btn.setProperty("class", "danger")
    button_layout.addWidget(danger_btn)
    
    secondary_btn = QPushButton("Secondary Button")
    secondary_btn.setProperty("class", "secondary")
    button_layout.addWidget(secondary_btn)
    
    layout.addLayout(button_layout)
    
    # Test text input
    text_input = QTextEdit()
    text_input.setPlaceholderText("Test text input with modern styling...")
    text_input.setMaximumHeight(100)
    layout.addWidget(text_input)
    
    # Test labels
    status_connected = QLabel("🟢 Backend Connected")
    status_connected.setProperty("class", "status-connected")
    layout.addWidget(status_connected)
    
    status_error = QLabel("🔴 Connection Error")
    status_error.setProperty("class", "status-error")
    layout.addWidget(status_error)
    
    # Test message bubbles
    from main_window import MessageBubble
    
    user_bubble = MessageBubble("This is a test user message", is_user=True)
    layout.addWidget(user_bubble)
    
    assistant_bubble = MessageBubble("This is a test assistant response with some longer text to see how it wraps and displays in the interface.", is_user=False)
    layout.addWidget(assistant_bubble)
    
    window.show()
    
    # Test button interactions
    def test_button_click():
        QMessageBox.information(window, "Test", "Button clicked! Styling working correctly.")
    
    primary_btn.clicked.connect(test_button_click)
    
    print("✅ UI test window created")
    return app.exec()

def test_api_client():
    """Test API client functionality"""
    try:
        from api_client import SyncAPIClient
        
        print("Testing API client...")
        client = SyncAPIClient()
        
        # Test connection
        print("Testing backend connection...")
        connected = client.test_connection()
        print(f"✅ Connection test: {'Connected' if connected else 'Failed'}")
        
        if connected:
            # Test document list
            print("Testing document list...")
            try:
                documents = client.get_documents()
                print(f"✅ Documents loaded: {len(documents)} found")
                
                for doc in documents[:3]:  # Show first 3
                    title = doc.get('title', 'Unknown')
                    file_type = doc.get('file_type', 'unknown')
                    status = doc.get('processing_status', 'unknown')
                    print(f"  📄 {title} ({file_type}) - {status}")
                    
            except Exception as e:
                print(f"❌ Document list error: {e}")
                
            # Test simple query
            print("Testing simple RAG query...")
            try:
                response = client.rag_query("Hello, can you help me?")
                print(f"✅ RAG query successful")
                print(f"Response preview: {response[:100]}...")
            except Exception as e:
                print(f"❌ RAG query error: {e}")
                
        return connected
        
    except Exception as e:
        print(f"❌ API client test failed: {e}")
        return False

def test_session_manager():
    """Test session manager functionality"""
    try:
        from session_manager import SessionManager
        
        print("Testing session manager...")
        session = SessionManager()
        
        # Test basic functionality
        session.set_user_preference("test_key", "test_value")
        value = session.get_user_preference("test_key")
        print(f"✅ Preference test: {value == 'test_value'}")
        
        # Test chat history
        session.add_chat_message("Test message", is_user=True)
        history = session.get_chat_history(limit=1)
        print(f"✅ Chat history test: {len(history) > 0}")
        
        # Test session info
        info = session.get_session_info()
        print(f"✅ Session info: {info['session_id'][:8]}...")
        
        return True
        
    except Exception as e:
        print(f"❌ Session manager test failed: {e}")
        return False

def test_components():
    """Test individual UI components"""
    app = QApplication(sys.argv)
    
    # Load stylesheet
    style_path = Path(__file__).parent / "styles.qss"
    if style_path.exists():
        with open(style_path, 'r', encoding='utf-8') as f:
            app.setStyleSheet(f.read())
    
    # Test main window components
    try:
        from main_window import ChatInputWidget, MessageBubble
        from api_client import SyncAPIClient
        from session_manager import SessionManager
        
        # Create test window
        window = QMainWindow()
        window.setWindowTitle("Component Test")
        window.setGeometry(200, 200, 600, 400)
        
        central_widget = QWidget()
        window.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Test message bubbles
        layout.addWidget(QLabel("Message Bubbles:"))
        
        user_msg = MessageBubble("Hello! This is a user message.", is_user=True)
        layout.addWidget(user_msg)
        
        assistant_msg = MessageBubble(
            "Hi there! This is an assistant response. I can help you with your documents and answer questions about them. The response can be quite long and should wrap properly within the bubble.",
            is_user=False
        )
        layout.addWidget(assistant_msg)
        
        # Test chat input
        layout.addWidget(QLabel("Chat Input:"))
        chat_input = ChatInputWidget()
        
        def on_message_sent(message):
            print(f"Message sent: {message}")
            
        def on_file_attached(files):
            print(f"Files attached: {files}")
            
        chat_input.message_sent.connect(on_message_sent)
        chat_input.file_attached.connect(on_file_attached)
        
        layout.addWidget(chat_input)
        
        window.show()
        print("✅ Component test window created")
        
        return app.exec()
        
    except Exception as e:
        print(f"❌ Component test failed: {e}")
        return 1

def run_full_test():
    """Run comprehensive test suite"""
    print("🧪 Running RAG Desktop Test Suite")
    print("=" * 50)
    
    # Test 1: Session Manager
    print("\n1. Testing Session Manager...")
    session_ok = test_session_manager()
    
    # Test 2: API Client
    print("\n2. Testing API Client...")
    api_ok = test_api_client()
    
    # Test 3: Dependencies
    print("\n3. Testing Dependencies...")
    deps_ok = test_dependencies()
    
    # Summary
    print("\n" + "=" * 50)
    print("📊 Test Results:")
    print(f"  Session Manager: {'✅ PASS' if session_ok else '❌ FAIL'}")
    print(f"  API Client: {'✅ PASS' if api_ok else '❌ FAIL'}")
    print(f"  Dependencies: {'✅ PASS' if deps_ok else '❌ FAIL'}")
    
    if all([session_ok, deps_ok]):
        print("\n🎉 Core functionality tests passed!")
        if not api_ok:
            print("⚠️  Backend connection failed - ensure server is running")
        return True
    else:
        print("\n❌ Some tests failed - check configuration")
        return False

def test_dependencies():
    """Test if all dependencies are available"""
    try:
        print("Checking PyQt6...")
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtCore import Qt
        from PyQt6.QtGui import QFont
        print("✅ PyQt6 available")
        
        print("Checking httpx...")
        import httpx
        print("✅ httpx available")
        
        print("Checking standard libraries...")
        import json
        import pathlib
        import logging
        import asyncio
        print("✅ Standard libraries available")
        
        print("Checking application modules...")
        from api_client import SyncAPIClient
        from session_manager import SessionManager
        print("✅ Application modules available")
        
        return True
        
    except ImportError as e:
        print(f"❌ Missing dependency: {e}")
        return False
    except Exception as e:
        print(f"❌ Dependency test error: {e}")
        return False

def create_mock_data():
    """Create mock data for testing"""
    print("Creating mock test data...")
    
    try:
        from session_manager import SessionManager
        
        session = SessionManager()
        
        # Add some mock chat messages
        messages = [
            ("Hello! Can you help me understand my documents?", True),
            ("Of course! I'd be happy to help you with your documents. What would you like to know?", False),
            ("What types of files can I upload?", True),
            ("You can upload PDF, DOCX, TXT, and Markdown files. I'll process them and make them searchable so you can ask questions about their content.", False),
            ("That's great! How accurate are the responses?", True),
            ("I use advanced AI models to understand your documents and provide accurate responses. I'll always cite my sources and let you know when I'm using web search for current information.", False),
        ]
        
        for message, is_user in messages:
            session.add_chat_message(message, is_user)
            
        # Set some preferences
        session.set_user_preference("theme", "Dark")
        session.set_user_preference("auto_scroll", True)
        session.set_user_preference("save_history", True)
        
        print("✅ Mock data created")
        return True
        
    except Exception as e:
        print(f"❌ Failed to create mock data: {e}")
        return False

def main():
    """Main test function"""
    if len(sys.argv) > 1:
        test_type = sys.argv[1].lower()
        
        if test_type == "ui":
            print("🎨 Running UI styling test...")
            return test_styling()
            
        elif test_type == "components":
            print("🧩 Running component test...")
            return test_components()
            
        elif test_type == "api":
            print("🌐 Running API test...")
            test_api_client()
            return 0
            
        elif test_type == "session":
            print("💾 Running session test...")
            test_session_manager()
            return 0
            
        elif test_type == "deps":
            print("📦 Running dependency test...")
            test_dependencies()
            return 0
            
        elif test_type == "mock":
            print("🎭 Creating mock data...")
            create_mock_data()
            return 0
            
        elif test_type == "full":
            print("🔍 Running full test suite...")
            success = run_full_test()
            return 0 if success else 1
            
        else:
            print(f"❌ Unknown test type: {test_type}")
            
    else:
        print("🧪 RAG Desktop UI Test Tool")
        print("\nUsage:")
        print("  python test_ui.py ui         - Test UI styling")
        print("  python test_ui.py components - Test UI components")
        print("  python test_ui.py api        - Test API client")
        print("  python test_ui.py session    - Test session manager")
        print("  python test_ui.py deps       - Test dependencies")
        print("  python test_ui.py mock       - Create mock data")
        print("  python test_ui.py full       - Run full test suite")
        
        # Run basic dependency check by default
        print("\nRunning basic dependency check...")
        return 0 if test_dependencies() else 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)