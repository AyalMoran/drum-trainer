#!/usr/bin/env python3
"""
Development startup script for Drum Trainer
Starts both the backend and frontend servers
"""

import subprocess
import sys
import time
import os
from pathlib import Path

def check_dependencies():
    """Check if required dependencies are installed"""
    try:
        import fastapi
        import uvicorn
        print("✓ Python dependencies found")
    except ImportError:
        print("✗ Python dependencies not found. Please run: pip install -r requirements.txt")
        return False
    
    # Check if Node.js is available
    try:
        subprocess.run(["node", "--version"], check=True, capture_output=True)
        print("✓ Node.js found")
    except (subprocess.CalledProcessError, FileNotFoundError):
        print("✗ Node.js not found. Please install Node.js 16+")
        return False
    
    # Check if npm is available (Windows-friendly)
    npm_found = False
    npm_commands = ["npm", "npm.cmd"]
    
    for npm_cmd in npm_commands:
        try:
            # Use shell=True on Windows for better PATH resolution
            if os.name == 'nt':  # Windows
                result = subprocess.run(f"{npm_cmd} --version", shell=True, check=True, capture_output=True, text=True)
            else:
                result = subprocess.run([npm_cmd, "--version"], check=True, capture_output=True, text=True)
            
            if result.returncode == 0:
                print(f"✓ npm found (version: {result.stdout.strip()})")
                npm_found = True
                break
        except (subprocess.CalledProcessError, FileNotFoundError):
            continue
    
    if not npm_found:
        print("✗ npm not found. Please install npm")
        return False
    
    return True

def install_frontend_deps():
    """Install frontend dependencies if needed"""
    frontend_dir = Path("frontend")
    if not frontend_dir.exists():
        print("✗ Frontend directory not found")
        return False
    
    node_modules = frontend_dir / "node_modules"
    if not node_modules.exists():
        print("Installing frontend dependencies...")
        try:
            # Use shell=True on Windows for better PATH resolution
            if os.name == 'nt':  # Windows
                subprocess.run("npm install", cwd=frontend_dir, shell=True, check=True)
            else:
                subprocess.run(["npm", "install"], cwd=frontend_dir, check=True)
            print("✓ Frontend dependencies installed")
        except subprocess.CalledProcessError:
            print("✗ Failed to install frontend dependencies")
            return False
    else:
        print("✓ Frontend dependencies already installed")
    
    return True

def start_backend():
    """Start the backend server"""
    print("Starting backend server...")
    try:
        # Start the server from the root directory
        backend_process = subprocess.Popen([
            sys.executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"
        ])
        
        print("✓ Backend server started (PID: {})".format(backend_process.pid))
        return backend_process
    except Exception as e:
        print(f"✗ Failed to start backend: {e}")
        return None

def start_frontend():
    """Start the frontend development server"""
    print("Starting frontend server...")
    try:
        # Use shell=True on Windows for better PATH resolution
        if os.name == 'nt':  # Windows
            frontend_process = subprocess.Popen(
                "npm run dev", 
                cwd="frontend", 
                shell=True
            )
        else:
            frontend_process = subprocess.Popen([
                "npm", "run", "dev"
            ], cwd="frontend")
        
        print("✓ Frontend server started (PID: {})".format(frontend_process.pid))
        return frontend_process
    except Exception as e:
        print(f"✗ Failed to start frontend: {e}")
        return None

def main():
    """Main startup function"""
    print("🚀 Starting Drum Trainer Development Environment")
    print("=" * 50)
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Install frontend dependencies if needed
    if not install_frontend_deps():
        sys.exit(1)
    
    print("\nStarting servers...")
    print("-" * 30)
    
    # Start backend
    backend_process = start_backend()
    if not backend_process:
        sys.exit(1)
    
    # Wait a moment for backend to start
    time.sleep(2)
    
    # Start frontend
    frontend_process = start_frontend()
    if not frontend_process:
        print("Stopping backend...")
        backend_process.terminate()
        sys.exit(1)
    
    print("\n" + "=" * 50)
    print("🎯 Drum Trainer is starting up!")
    print("Backend: http://localhost:8000")
    print("Frontend: http://localhost:3000")
    print("API Docs: http://localhost:8000/docs")
    print("\nPress Ctrl+C to stop all servers")
    print("=" * 50)
    
    try:
        # Wait for processes to complete
        backend_process.wait()
        frontend_process.wait()
    except KeyboardInterrupt:
        print("\n\n🛑 Stopping servers...")
        backend_process.terminate()
        frontend_process.terminate()
        print("✓ Servers stopped")
    except Exception as e:
        print(f"\nError: {e}")
        backend_process.terminate()
        frontend_process.terminate()

if __name__ == "__main__":
    main()
