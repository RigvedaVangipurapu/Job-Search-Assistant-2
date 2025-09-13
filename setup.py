#!/usr/bin/env python3
"""
Setup script for the Amazon Career Monitoring System
Installs dependencies and Playwright browser binaries
"""

import subprocess
import sys
import os

def run_command(command, description):
    """Run a command and handle errors"""
    print(f"Running: {description}")
    try:
        result = subprocess.run(command, shell=True, check=True, capture_output=True, text=True)
        print(f"✓ {description} completed successfully")
        return True
    except subprocess.CalledProcessError as e:
        print(f"✗ {description} failed: {e.stderr}")
        return False

def main():
    """Main setup function"""
    print("Setting up Amazon Career Monitoring System...")
    print("=" * 50)
    
    # Check if we're in a virtual environment
    if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("Warning: It's recommended to run this in a virtual environment")
        print("You can create one with: python -m venv venv")
        print("Then activate it with: source venv/bin/activate (macOS/Linux) or venv\\Scripts\\activate (Windows)")
        print()
    
    # Install Python dependencies
    if not run_command("pip install -r requirements.txt", "Installing Python dependencies"):
        return False
    
    # Install Playwright browser binaries
    if not run_command("playwright install chromium", "Installing Playwright browser binaries"):
        return False
    
    print("\n" + "=" * 50)
    print("Setup completed successfully!")
    print("\nNext steps:")
    print("1. Run: python career_monitor.py")
    print("2. Check the generated screenshot to verify the page loaded correctly")
    
    return True

if __name__ == "__main__":
    success = main()
    if not success:
        sys.exit(1)
