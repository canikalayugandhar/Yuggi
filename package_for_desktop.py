#!/usr/bin/env python3
"""
Create a desktop package of Trinity Wealth Scanner
"""
import shutil
import os
from pathlib import Path
import zipfile

def create_desktop_package():
    """Create a complete desktop package"""
    
    print("📦 Creating Trinity Wealth Scanner Desktop Package...")
    
    # Create desktop directory
    desktop_dir = Path("trinity_scanner_desktop")
    if desktop_dir.exists():
        shutil.rmtree(desktop_dir)
    
    desktop_dir.mkdir()
    
    # Copy backend files
    backend_src = Path("backend")
    backend_dst = desktop_dir / "backend"
    
    if backend_src.exists():
        shutil.copytree(backend_src, backend_dst)
        print("✅ Backend files copied")
    
    # Copy frontend files  
    frontend_src = Path("frontend")
    frontend_dst = desktop_dir / "frontend"
    
    if frontend_src.exists():
        shutil.copytree(frontend_src, frontend_dst)
        print("✅ Frontend files copied")
    
    # Copy startup scripts
    startup_files = [
        "start_desktop.bat",
        "start_desktop.sh", 
        "check_setup.py",
        "DESKTOP_SETUP.md"
    ]
    
    for file_name in startup_files:
        src_file = Path(file_name)
        if src_file.exists():
            shutil.copy2(src_file, desktop_dir / file_name)
            print(f"✅ {file_name} copied")
    
    # Create desktop environment files
    env_dir = desktop_dir / ".env_desktop"
    env_dir.mkdir()
    
    # Backend .env for desktop
    backend_env = backend_dst / ".env"
    with open(backend_env, "w") as f:
        f.write("""# Trinity Wealth Scanner - Desktop Environment
MONGO_URL=mongodb://localhost:27017/trinity_scanner
DEBUG=True
HOST=0.0.0.0
PORT=8001
""")
    
    # Frontend .env for desktop
    frontend_env = frontend_dst / ".env"
    with open(frontend_env, "w") as f:
        f.write("""# Trinity Wealth Scanner - Desktop Frontend
REACT_APP_BACKEND_URL=http://localhost:8001
BROWSER=none
""")
    
    print("✅ Environment files created")
    
    # Make shell script executable
    start_script = desktop_dir / "start_desktop.sh"
    if start_script.exists():
        os.chmod(start_script, 0o755)
    
    setup_script = desktop_dir / "check_setup.py"
    if setup_script.exists():
        os.chmod(setup_script, 0o755)
    
    # Create README for desktop
    readme_content = """# Trinity Wealth Scanner - Desktop Edition

## Quick Start
1. Run setup checker: `python check_setup.py`
2. Start the scanner: `./start_desktop.bat` (Windows) or `./start_desktop.sh` (Mac/Linux)
3. Open: http://localhost:3000

## Requirements
- Python 3.8+
- Node.js 16+  
- MongoDB Community Edition

## First Time Setup
1. Install MongoDB and start the service
2. Install Python dependencies: `cd backend && pip install -r requirements.txt`
3. Install Node.js dependencies: `cd frontend && npm install`
4. Run the setup checker: `python check_setup.py`

## Features
- ✅ Real-time signal generation
- ✅ Live options data (ATM contracts)  
- ✅ Win/Loss outcome monitoring
- ✅ P&L calculations
- ✅ Configuration persistence
- ✅ Complete privacy (runs locally)

## Support
See DESKTOP_SETUP.md for detailed instructions and troubleshooting.
"""
    
    with open(desktop_dir / "README.md", "w") as f:
        f.write(readme_content)
    
    print("✅ Desktop README created")
    
    # Create zip package
    zip_path = Path("trinity_scanner_desktop.zip")
    if zip_path.exists():
        zip_path.unlink()
    
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(desktop_dir):
            for file in files:
                file_path = Path(root) / file
                arcname = file_path.relative_to(desktop_dir.parent)
                zipf.write(file_path, arcname)
    
    print(f"✅ Desktop package created: {zip_path}")
    print(f"📊 Package size: {zip_path.stat().st_size / 1024 / 1024:.1f} MB")
    
    return zip_path

def main():
    print("🖥️ Trinity Wealth Scanner - Desktop Packager")
    print("=" * 50)
    
    try:
        zip_file = create_desktop_package()
        
        print("\n🎉 Desktop package ready!")
        print(f"📦 Package: {zip_file}")
        print("\n📋 Next steps for users:")
        print("1. Download and extract the zip file")
        print("2. Run: python check_setup.py")  
        print("3. Follow the setup instructions")
        print("4. Start with: ./start_desktop.bat or ./start_desktop.sh")
        
    except Exception as e:
        print(f"❌ Error creating package: {e}")
        return False
    
    return True

if __name__ == "__main__":
    main()