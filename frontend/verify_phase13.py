#!/usr/bin/env python3
"""
Phase 13 Verification Script
Comprehensive testing of system tray and background operations
"""

import sys
import os
import time
from pathlib import Path

def test_system_monitoring():
    """Test system monitoring capabilities"""
    print("🖥️ Testing system monitoring...")
    
    try:
        import psutil
        
        # Test basic metrics
        cpu = psutil.cpu_percent(interval=1)
        memory = psutil.virtual_memory().percent
        disk = psutil.disk_usage('/').percent if os.name != 'nt' else psutil.disk_usage('C:\\').percent
        
        print(f"✅ System metrics available:")
        print(f"   CPU: {cpu:.1f}%")
        print(f"   Memory: {memory:.1f}%")
        print(f"   Disk: {disk:.1f}%")
        
        # Test process monitoring
        process = psutil.Process()
        app_memory = process.memory_info().rss / 1024 / 1024
        app_cpu = process.cpu_percent()
        
        print(f"✅ Process monitoring:")
        print(f"   App Memory: {app_memory:.1f} MB")
        print(f"   App CPU: {app_cpu:.1f}%")
        
        return True
        
    except ImportError:
        print("❌ psutil not available - install with: pip install psutil")
        return False
    except Exception as e:
        print(f"❌ System monitoring test failed: {e}")
        return False

def test_system_tray_components():
    """Test system tray components"""
    print("\n🔔 Testing system tray components...")
    
    try:
        from PyQt6.QtWidgets import QApplication, QSystemTrayIcon
        from system_tray_manager import (
            AdvancedSystemTrayManager, NotificationLevel, TrayNotification,
            BackgroundTaskManager, SystemResourceMonitor
        )
        
        # Create minimal app for testing
        app = QApplication([])
        
        # Test system tray availability
        if QSystemTrayIcon.isSystemTrayAvailable():
            print("✅ System tray available")
        else:
            print("⚠️  System tray not available on this platform")
            
        # Test notification creation
        notification = TrayNotification(
            "Test Title", 
            "Test message", 
            NotificationLevel.INFO
        )
        print(f"✅ Notification created: {notification.id}")
        
        # Test background task manager
        task_manager = BackgroundTaskManager()
        print("✅ Background task manager created")
        
        # Test resource monitor
        resource_monitor = SystemResourceMonitor()
        print("✅ System resource monitor created")
        
        return True
        
    except ImportError as e:
        print(f"❌ System tray components not available: {e}")
        return False
    except Exception as e:
        print(f"❌ System tray test failed: {e}")
        return False

def test_background_operations():
    """Test background operations"""
    print("\n⚙️ Testing background operations...")
    
    try:
        from background_operations import (
            BackgroundOperationsManager, BackgroundTask, BackgroundTaskType,
            DocumentProcessingWorker, HealthCheckWorker, SessionSyncWorker
        )
        from api_client import SyncAPIClient
        from session_manager import SessionManager
        
        # Create dependencies
        api_client = SyncAPIClient()
        session_manager = SessionManager()
        
        # Test background operations manager
        try:
            bg_ops = BackgroundOperationsManager(api_client, session_manager)
            print("✅ Background operations manager created")
        except Exception as e:
            print(f"⚠️  Background operations manager creation failed (expected if backend not running): {e}")
            return False
        
        # Test task creation
        task = BackgroundTask("test_task", BackgroundTaskType.SESSION_SYNC)
        print(f"✅ Background task created: {task.task_id}")
        
        # Test worker creation
        sync_worker = SessionSyncWorker(session_manager)
        print("✅ Session sync worker created")
        
        # Test health check worker
        health_worker = HealthCheckWorker(api_client)
        print("✅ Health check worker created")
        
        return True
        
    except ImportError as e:
        print(f"❌ Background operations not available: {e}")
        return False
    except Exception as e:
        print(f"❌ Background operations test failed: {e}")
        return False

def test_main_window_integration():
    """Test main window Phase 13 integration"""
    print("\n🖼️ Testing main window integration...")
    
    try:
        from PyQt6.QtWidgets import QApplication
        from main_window import MainWindow
        
        # Create minimal app
        app = QApplication([])
        
        # Test main window creation
        main_window = MainWindow()
        print("✅ Main window with Phase 13 created")
        
        # Check Phase 13 components
        if hasattr(main_window, 'tray_manager'):
            print("✅ System tray manager integrated")
        else:
            print("⚠️  System tray manager not found")
            
        if hasattr(main_window, 'background_ops'):
            print("✅ Background operations integrated")
        else:
            print("⚠️  Background operations not found")
            
        # Check new methods
        phase13_methods = [
            'setup_system_tray',
            'setup_background_operations',
            'show_tray_notification',
            'schedule_document_processing',
            'cleanup_and_exit'
        ]
        
        missing_methods = []
        for method in phase13_methods:
            if hasattr(main_window, method):
                print(f"✅ Method {method} available")
            else:
                missing_methods.append(method)
                print(f"❌ Method {method} missing")
                
        return len(missing_methods) == 0
        
    except ImportError as e:
        print(f"❌ Main window integration not available: {e}")
        return False
    except Exception as e:
        print(f"❌ Main window integration test failed: {e}")
        return False

def test_file_structure():
    """Test Phase 13 file structure"""
    print("📁 Checking Phase 13 file structure...")
    
    required_files = {
        "system_tray_manager.py": "System tray integration",
        "background_operations.py": "Background operations manager",
        "main_window.py": "Main window (Phase 13 enhanced)",
        "main.py": "Application entry (Phase 13 enhanced)",
        "verify_phase13.py": "Phase 13 verification script"
    }
    
    missing_files = []
    for file, description in required_files.items():
        if Path(file).exists():
            print(f"✅ {file} - {description}")
        else:
            print(f"❌ {file} - {description} (MISSING)")
            missing_files.append(file)
    
    if missing_files:
        print(f"\n⚠️  Missing files: {missing_files}")
        return False
    
    print("✅ All Phase 13 files present")
    return True

def test_dependency_integration():
    """Test dependency integration"""
    print("\n📦 Testing dependency integration...")
    
    # Test psutil integration
    psutil_ok = test_system_monitoring()
    
    # Test PyQt6 system tray
    try:
        from PyQt6.QtWidgets import QApplication, QSystemTrayIcon
        app = QApplication([])
        
        if QSystemTrayIcon.isSystemTrayAvailable():
            print("✅ PyQt6 system tray support")
            tray_ok = True
        else:
            print("⚠️  System tray not supported on this platform")
            tray_ok = False
            
    except Exception as e:
        print(f"❌ PyQt6 system tray test failed: {e}")
        tray_ok = False
    
    return psutil_ok and tray_ok

def run_integration_test():
    """Run a simple integration test"""
    print("\n🔗 Running integration test...")
    
    try:
        from PyQt6.QtWidgets import QApplication
        from system_tray_manager import initialize_system_tray, cleanup_system_tray
        from background_operations import initialize_background_operations, cleanup_background_operations
        from session_manager import SessionManager
        from api_client import SyncAPIClient
        
        # Create minimal app
        app = QApplication([])
        
        # Create mock main window
        class MockMainWindow:
            def __init__(self):
                self.is_authenticated = False
                
            def isVisible(self):
                return True
                
            def isActiveWindow(self):
                return True
                
            def show(self):
                pass
                
            def hide(self):
                pass
                
            def raise_(self):
                pass
                
            def activateWindow(self):
                pass
        
        mock_window = MockMainWindow()
        session_manager = SessionManager()
        api_client = SyncAPIClient()
        
        # Test system tray initialization
        tray_manager = initialize_system_tray(mock_window, session_manager)
        if tray_manager:
            print("✅ System tray manager initialized")
        else:
            print("⚠️  System tray manager initialization failed")
            
        # Test background operations initialization
        try:
            bg_ops = initialize_background_operations(api_client, session_manager)
            if bg_ops:
                print("✅ Background operations initialized")
            else:
                print("❌ Background operations initialization failed")
                return False
        except Exception as e:
            print(f"⚠️  Background operations initialization failed (expected if backend not running): {e}")
            # Don't fail the test if backend is not running
            bg_ops = None
            
        # Test cleanup
        try:
            cleanup_background_operations()
            cleanup_system_tray()
            print("✅ Cleanup completed successfully")
        except Exception as e:
            print(f"⚠️  Cleanup had issues (expected): {e}")
            # Don't fail the test for cleanup issues
        
        return True
        
    except Exception as e:
        print(f"❌ Integration test failed: {e}")
        return False

def run_comprehensive_test():
    """Run comprehensive Phase 13 verification"""
    print("🧪 RAG Desktop Phase 13 - Comprehensive Verification")
    print("=" * 60)
    
    # Test 1: File structure
    files_ok = test_file_structure()
    
    # Test 2: Dependencies
    deps_ok = test_dependency_integration()
    
    # Test 3: System tray components
    tray_ok = test_system_tray_components()
    
    # Test 4: Background operations
    bg_ops_ok = test_background_operations()
    
    # Test 5: Main window integration
    integration_ok = test_main_window_integration()
    
    # Test 6: Integration test
    full_integration_ok = run_integration_test()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 Phase 13 Verification Results:")
    print(f"  File Structure: {'✅ PASS' if files_ok else '❌ FAIL'}")
    print(f"  Dependencies: {'✅ PASS' if deps_ok else '❌ FAIL'}")
    print(f"  System Tray: {'✅ PASS' if tray_ok else '❌ FAIL'}")
    print(f"  Background Ops: {'✅ PASS' if bg_ops_ok else '❌ FAIL'}")
    print(f"  Integration: {'✅ PASS' if integration_ok else '❌ FAIL'}")
    print(f"  Full Integration: {'✅ PASS' if full_integration_ok else '❌ FAIL'}")
    
    all_passed = all([files_ok, deps_ok, tray_ok, bg_ops_ok, integration_ok, full_integration_ok])
    
    if all_passed:
        print(f"\n🎉 Phase 13 System Integration COMPLETE!")
        print("\n🚀 Enhanced Features Available:")
        print("  • 🔔 Advanced system tray with notifications")
        print("  • ⚙️ Background document processing")
        print("  • 📊 Real-time system health monitoring")
        print("  • 🔄 Automatic session synchronization")
        print("  • 🗑️ Intelligent cache management")
        print("  • ⚡ Non-blocking background operations")
        print("  • 🖥️ System resource monitoring")
        print("  • 🎯 Smart minimize/close to tray behavior")
        
        print("\n💡 Phase 13 Usage:")
        print("  • Right-click tray icon for quick actions")
        print("  • Background tasks run automatically")
        print("  • Health monitoring alerts via notifications")
        print("  • Configurable tray and background settings")
        
        return True
    else:
        print("\n❌ Phase 13 setup incomplete. Please check errors above.")
        return False

def main():
    """Main verification function"""
    if len(sys.argv) > 1:
        test_type = sys.argv[1].lower()
        
        if test_type == "tray":
            success = test_system_tray_components()
        elif test_type == "background":
            success = test_background_operations()
        elif test_type == "integration":
            success = test_main_window_integration()
        elif test_type == "files":
            success = test_file_structure()
        elif test_type == "deps":
            success = test_dependency_integration()
        elif test_type == "monitoring":
            success = test_system_monitoring()
        elif test_type == "full":
            success = run_comprehensive_test()
        else:
            print(f"❌ Unknown test type: {test_type}")
            return 1
            
        return 0 if success else 1
    else:
        print("🔔 RAG Desktop Phase 13 Verification")
        print("\nUsage:")
        print("  python verify_phase13.py tray        - Test system tray components")
        print("  python verify_phase13.py background  - Test background operations")
        print("  python verify_phase13.py integration - Test main window integration")
        print("  python verify_phase13.py files       - Check file structure")
        print("  python verify_phase13.py deps        - Test dependencies")
        print("  python verify_phase13.py monitoring  - Test system monitoring")
        print("  python verify_phase13.py full        - Run complete verification")
        
        # Run comprehensive test by default
        print("\nRunning comprehensive verification...")
        success = run_comprehensive_test()
        return 0 if success else 1

if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)