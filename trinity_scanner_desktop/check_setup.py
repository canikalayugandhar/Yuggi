#!/usr/bin/env python3
"""
Trinity Wealth Scanner - Desktop Setup Checker
Verifies all requirements are met for desktop deployment
"""
import sys
import subprocess
import socket
import os
from pathlib import Path

def check_python():
    """Check Python version"""
    version = sys.version_info
    print(f"🐍 Python Version: {version.major}.{version.minor}.{version.micro}")
    
    if version.major >= 3 and version.minor >= 8:
        print("   ✅ Python version is compatible")
        return True
    else:
        print("   ❌ Python 3.8+ required")
        return False

def check_node():
    """Check Node.js version"""
    try:
        result = subprocess.run(['node', '--version'], capture_output=True, text=True)
        version = result.stdout.strip()
        print(f"📦 Node.js Version: {version}")
        
        # Extract major version number
        major_version = int(version.replace('v', '').split('.')[0])
        if major_version >= 16:
            print("   ✅ Node.js version is compatible")
            return True
        else:
            print("   ❌ Node.js 16+ required")
            return False
            
    except FileNotFoundError:
        print("📦 Node.js: ❌ Not installed")
        print("   Install from: https://nodejs.org/")
        return False

def check_mongodb():
    """Check if MongoDB is available"""
    try:
        result = subprocess.run(['mongod', '--version'], capture_output=True, text=True)
        if result.returncode == 0:
            version_line = result.stdout.split('\n')[0]
            print(f"🍃 MongoDB: {version_line}")
            print("   ✅ MongoDB is installed")
            
            # Check if MongoDB is running
            return check_mongodb_connection()
        else:
            print("🍃 MongoDB: ❌ Not installed")
            return False
            
    except FileNotFoundError:
        print("🍃 MongoDB: ❌ Not found")
        print("   Install from: https://www.mongodb.com/try/download/community")
        return False

def check_mongodb_connection():
    """Check if MongoDB is running on default port"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex(('localhost', 27017))
        sock.close()
        
        if result == 0:
            print("   ✅ MongoDB is running on port 27017")
            return True
        else:
            print("   ⚠️ MongoDB installed but not running")
            print("   Start with: mongod or brew services start mongodb-community")
            return False
            
    except Exception:
        print("   ❌ Cannot connect to MongoDB")
        return False

def check_ports():
    """Check if required ports are available"""
    ports_to_check = [3000, 8001]
    available_ports = []
    
    for port in ports_to_check:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(1)
        result = sock.connect_ex(('localhost', port))
        sock.close()
        
        if result != 0:
            print(f"🔌 Port {port}: ✅ Available")
            available_ports.append(port)
        else:
            print(f"🔌 Port {port}: ⚠️ In use")
    
    return len(available_ports) == len(ports_to_check)

def check_dependencies():
    """Check Python dependencies"""
    try:
        import fastapi, uvicorn, motor, pymongo, pandas, requests
        print("📚 Python Dependencies: ✅ Core packages available")
        return True
    except ImportError as e:
        print(f"📚 Python Dependencies: ❌ Missing {e.name}")
        print("   Run: pip install -r requirements.txt")
        return False

def check_directory_structure():
    """Check if project structure is correct"""
    required_dirs = ['backend', 'frontend']
    required_files = [
        'backend/server.py',
        'backend/requirements.txt', 
        'frontend/package.json',
        'frontend/src/App.js'
    ]
    
    missing_items = []
    
    for directory in required_dirs:
        if not Path(directory).exists():
            missing_items.append(f"Directory: {directory}")
    
    for file_path in required_files:
        if not Path(file_path).exists():
            missing_items.append(f"File: {file_path}")
    
    if not missing_items:
        print("📁 Project Structure: ✅ All required files present")
        return True
    else:
        print("📁 Project Structure: ❌ Missing items:")
        for item in missing_items:
            print(f"   - {item}")
        return False

def main():
    print("=" * 50)
    print("   Trinity Wealth Scanner - Setup Checker")
    print("=" * 50)
    print()
    
    checks = [
        ("Python 3.8+", check_python),
        ("Node.js 16+", check_node),
        ("MongoDB", check_mongodb),
        ("Available Ports", check_ports),
        ("Python Dependencies", check_dependencies),
        ("Project Structure", check_directory_structure)
    ]
    
    results = []
    
    for name, check_func in checks:
        try:
            result = check_func()
            results.append(result)
        except Exception as e:
            print(f"❌ Error checking {name}: {e}")
            results.append(False)
        print()
    
    # Summary
    passed = sum(results)
    total = len(results)
    
    print("=" * 50)
    print(f"   Setup Check Results: {passed}/{total} passed")
    print("=" * 50)
    
    if passed == total:
        print("🎉 All checks passed! You're ready to run Trinity Wealth Scanner.")
        print()
        print("Next steps:")
        print("1. Run: ./start_desktop.bat (Windows) or ./start_desktop.sh (Mac/Linux)")
        print("2. Open: http://localhost:3000")
        print("3. Configure your Kite API credentials in Settings")
    else:
        print("⚠️ Some requirements are missing. Please install the missing components.")
        print()
        print("Quick fixes:")
        if not results[0]:  # Python
            print("- Install Python 3.8+: https://www.python.org/downloads/")
        if not results[1]:  # Node.js
            print("- Install Node.js 16+: https://nodejs.org/")
        if not results[2]:  # MongoDB
            print("- Install MongoDB: https://www.mongodb.com/try/download/community")
        if not results[4]:  # Dependencies
            print("- Run: pip install -r backend/requirements.txt")
            print("- Run: cd frontend && npm install")

if __name__ == "__main__":
    main()