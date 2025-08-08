#!/usr/bin/env python3
"""
Frontend Setup Script for RAG Desktop Application
Handles installation, validation, and initial setup
"""

import sys
import subprocess
import os
from pathlib import Path

def print_header():
    """Print setup header"""
    print("🚀 RAG Desktop Frontend Setup")
    print("=" * 50)

def check_python_version():
    """Check Python version compatibility"""
    print("📋 Checking Python version...")
    
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 8):
        print(f"❌ Python 3.8+ required, found {version.major}.{version.minor}.{version.micro}")
        return False
        
    print(f"✅ Python {version.major}.{version.minor}.{version.micro} (compatible)")
    return True

def install_dependencies():
    """Install required dependencies"""
    print("\n📦 Installing dependencies...")
    
    requirements_file = Path(__file__).parent / "requirements-frontend.txt"
    
    if not requirements_file.exists():
        print("❌ requirements-frontend.txt not found")
        return False
    
    try:
        # Upgrade pip first
        print("🔄 Upgrading pip...")
        subprocess.run([sys.executable, "-m", "pip", "install", "--upgrade", "pip"], 
                      check=True, capture_output=True)
        
        # Install requirements
        print("🔄 Installing PyQt6 and dependencies...")
        result = subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", str(requirements_file)],
            check=True,
            capture_output=True,
            text=True
        )
        
        print("✅ Dependencies installed successfully")
        return True
        
    except subprocess.CalledProcessError as e:
        print(f"❌ Installation failed: {e}")
        if e.stderr:
            print(f"Error details: {e.stderr}")
        return False

def validate_installation():
    """Validate that all components are working"""
    print("\n🔍 Validating installation...")
    
    # Test PyQt6 import
    try:
        from PyQt6.QtWidgets import QApplication
        from PyQt6.QtCore import Qt
        print("✅ PyQt6 framework")
    except ImportError as e:
        print(f"❌ PyQt6 import failed: {e}")
        return False
    
    # Test httpx import
    try:
        import httpx
        print("✅ HTTP client (httpx)")
    except ImportError as e:
        print(f"❌ httpx import failed: {e}")
        return False
    
    # Test application modules
    try:
        # Temporarily add current directory to path
        current_dir = Path(__file__).parent
        if str(current_dir) not in sys.path:
            sys.path.insert(0, str(current_dir))
            
        from api_client import SyncAPIClient
        print("✅ API client module")
        
        from session_manager import SessionManager
        print("✅ Session manager module")
        
        from main_window import MainWindow
        print("✅ Main window module")
        
    except ImportError as e:
        print(f"❌ Application module import failed: {e}")
        return False
    except Exception as e:
        print(f"⚠️  Module validation warning: {e}")
        # Continue anyway
    
    return True

def test_ui_basic():
    """Basic UI test"""
    print("\n🎨 Testing UI components...")
    
    try:
        from PyQt6.QtWidgets import QApplication, QLabel
        from PyQt6.QtCore import Qt
        
        # Create minimal application (don't show window)
        app = QApplication([])
        label = QLabel("Test")
        
        print("✅ Basic UI components working")
        return True
        
    except Exception as e:
        print(f"❌ UI test failed: {e}")
        return False

def create_desktop_shortcut():
    """Create desktop shortcut (optional)"""
    print("\n🔗 Creating desktop shortcut...")
    
    try:
        desktop = Path.home() / "Desktop"
        if not desktop.exists():
            print("⚠️  Desktop folder not found, skipping shortcut")
            return True
            
        current_dir = Path(__file__).parent
        main_script = current_dir / "main.py"
        
        if sys.platform.startswith('win'):
            # Windows shortcut (.bat file)
            shortcut_path = desktop / "RAG Desktop.bat"
            with open(shortcut_path, 'w') as f:
                f.write(f'@echo off\n')
                f.write(f'cd /d "{current_dir}"\n')
                f.write(f'python "{main_script}"\n')
                f.write(f'pause\n')
            print("✅ Windows shortcut created")
            
        elif sys.platform.startswith('darwin'):
            # macOS shortcut (shell script)
            shortcut_path = desktop / "RAG Desktop.command"
            with open(shortcut_path, 'w') as f:
                f.write(f'#!/bin/bash\n')
                f.write(f'cd "{current_dir}"\n')
                f.write(f'python3 "{main_script}"\n')
            
            # Make executable
            os.chmod(shortcut_path, 0o755)
            print("✅ macOS shortcut created")
            
        else:
            # Linux desktop entry
            shortcut_path = desktop / "RAG Desktop.desktop"
            with open(shortcut_path, 'w') as f:
                f.write(f'[Desktop Entry]\n')
                f.write(f'Name=RAG Desktop\n')
                f.write(f'Comment=AI Document Assistant\n')
                f.write(f'Exec=python3 "{main_script}"\n')
                f.write(f'Path={current_dir}\n')
                f.write(f'Icon=computer\n')
                f.write(f'Terminal=false\n')
                f.write(f'Type=Application\n')
                f.write(f'Categories=Office;Utility;\n')
            
            # Make executable
            os.chmod(shortcut_path, 0o755)
            print("✅ Linux desktop entry created")
            
        return True
        
    except Exception as e:
        print(f"⚠️  Shortcut creation failed: {e}")
        return True  # Not critical

def print_next_steps():
    """Print next steps for user"""
    print("\n" + "=" * 50)
    print("🎉 Setup completed successfully!")
    print("\n📋 Next steps:")
    print("1. Ensure your RAG backend is running:")
    print("   cd /path/to/backend")
    print("   docker-compose up -d")
    print("   uvicorn backend.main:app --reload --port 8000")
    print("")
    print("2. Start the RAG Desktop application:")
    print("   python main.py")
    print("")
    print("3. Or run tests first:")
    print("   python test_ui.py full")
    print("")
    print("🔧 Troubleshooting:")
    print("- Check backend at: http://localhost:8000/api/v1/health")
    print("- View logs in: rag_desktop.log")
    print("- Report issues: Check console output and logs")

def main():
    """Main setup function"""
    print_header()
    
    # Step 1: Check Python version
    if not check_python_version():
        return 1
    
    # Step 2: Install dependencies
    if not install_dependencies():
        return 1
    
    # Step 3: Validate installation
    if not validate_installation():
        print("\n❌ Installation validation failed")
        print("Please check error messages above and try again")
        return 1
    
    # Step 4: Test basic UI
    if not test_ui_basic():
        print("\n⚠️  UI test failed, but continuing...")
    
    # Step 5: Create desktop shortcut (optional)
    create_desktop_shortcut()
    
    # Step 6: Print success message
    print_next_steps()
    
    return 0

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n⏹️  Setup interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Setup failed with error: {e}")
        sys.exit(1)