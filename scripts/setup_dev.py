#!/usr/bin/env python3
import subprocess
import sys
import os
from pathlib import Path

def run_command(command, cwd=None):
    """Run shell command and return result"""
    try:
        result = subprocess.run(command, shell=True, cwd=cwd, check=True, 
                              capture_output=True, text=True)
        print(f"✓ {command}")
        return result.stdout
    except subprocess.CalledProcessError as e:
        print(f"✗ {command}")
        print(f"Error: {e.stderr}")
        return None

def setup_environment():
    """Setup development environment"""
    print("Setting up RAG Desktop App development environment...")
    
    # Check if .env exists
    if not Path(".env").exists():
        if Path(".env.example").exists():
            run_command("cp .env.example .env")
            print("✓ Created .env from .env.example")
        else:
            print("✗ No .env.example found!")
            return False
    
    # Install Python dependencies
    print("\nInstalling Python dependencies...")
    if run_command("pip install -r requirements.txt"):
        print("✓ Python dependencies installed")
    else:
        print("✗ Failed to install Python dependencies")
        return False
    
    # Start Docker services
    print("\nStarting Docker services...")
    if run_command("docker-compose up -d"):
        print("✓ Docker services started")
    else:
        print("✗ Failed to start Docker services")
        return False
    
    # Wait for services
    print("\nWaiting for services to be ready...")
    import time
    time.sleep(10)
    
    print("\n🎉 Development environment setup complete!")
    print("\nServices running:")
    print("- PostgreSQL: localhost:5432")
    print("- Qdrant: localhost:6333") 
    print("- Ollama: localhost:11434")
    
    return True

if __name__ == "__main__":
    success = setup_environment()
    sys.exit(0 if success else 1)