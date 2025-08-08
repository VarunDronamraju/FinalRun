#!/usr/bin/env python3
"""
Test Google OAuth configuration
"""

import sys
import os
sys.path.append('backend')

from config import settings

def test_oauth_config():
    """Test OAuth configuration"""
    print("Testing OAuth Configuration...")
    print(f"Google Client ID: {settings.google_client_id}")
    print(f"Google Client Secret: {'*' * len(settings.google_client_secret) if settings.google_client_secret else 'Not set'}")
    print(f"Google Redirect URI: {settings.google_redirect_uri}")
    
    if not settings.google_client_id:
        print("ERROR: Google Client ID is not set")
        return False
    
    if not settings.google_client_secret:
        print("ERROR: Google Client Secret is not set")
        return False
        
    if "your_google_client_id_here" in settings.google_client_id:
        print("ERROR: Google Client ID still has placeholder value")
        return False
        
    print("SUCCESS: OAuth configuration looks good!")
    return True

if __name__ == "__main__":
    test_oauth_config()