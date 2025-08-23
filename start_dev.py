#!/usr/bin/env python3
"""
Development startup script for Drum Trainer
Starts both the backend and frontend servers
"""

import subprocess
import sys
import time
import os
import requests
import webbrowser
from pathlib import Path

def check_dependencies(): 
    """Check if required dependencies are installed"""
    # Check if we're in a virtual environment or if dependencies are available
    try:
        import fastapi
        import uvicorn  
        print("✓ Python dependencies found")
        return True
    except ImportError:
        # Try to activate virtual environment if it exists
        venv_path = Path("venv")
        if venv_path.exists():
            print("⚠️  Dependencies not found in current environment")
            print("   Found virtual environment at 'venv/'")
            print("   Please activate it first: source venv/bin/activate")
            print("   Or run: venv/bin/pip install -r requirements.txt")
        else:
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
            #  Use shell  = True on Windows for better PATH resolution
            if os.name   == 'nt':  # Windows
               result     = subprocess.run(f"{npm_cmd} --version", shell=True, check=True, capture_output=True, text=True)
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

def install_backend_deps():
    """Install backend dependencies if needed"""
    venv_path = Path("venv")
    if not venv_path.exists():
        print("✗ Virtual environment not found")
        return False
    
    # Check if key dependencies are already installed
    try:
        import fastapi
        import uvicorn
        print("✓ Backend dependencies already installed")
        return True
    except ImportError:
        print("Installing backend dependencies...")
        try:
            if os.name == 'nt':  # Windows
                subprocess.run("venv\\Scripts\\pip install -r requirements.txt", shell=True, check=True)
            else:
                subprocess.run(["venv/bin/pip", "install", "-r", "requirements.txt"], check=True)
            print("✓ Backend dependencies installed")
            return True
        except subprocess.CalledProcessError:
            print("✗ Failed to install backend dependencies")
            return False

def start_backend():
    """Start the backend server"""
    print("Starting backend server...")
    try: 
        # Check if we have a virtual environment and use it
        venv_path = Path("venv")
        python_executable = sys.executable
        
        if venv_path.exists():
            # Use the virtual environment's Python
            if os.name == 'nt':  # Windows
                venv_python = venv_path / "Scripts" / "python.exe"
            else:  # Unix/Linux
                venv_python = venv_path / "bin" / "python"
            
            if venv_python.exists():
                python_executable = str(venv_python)
                print(f"   Using virtual environment: {venv_python}")
            else:
                print(f"   Virtual environment found but Python not at expected path: {venv_python}")
        
        # Start the server from the root directory
        backend_process = subprocess.Popen([
            python_executable, "-m", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"
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

def wait_for_backend(max_attempts=30, delay=1):
    """Wait for backend to be ready by polling the health endpoint"""
    print("Waiting for backend to be ready...")
    
    for attempt in range(max_attempts):
        try:
            response = requests.get("http://localhost:8000/health", timeout=2)
            if response.status_code == 200:
                print("✓ Backend is ready!")
                return True
        except (requests.RequestException, requests.Timeout):
            pass
        
        if attempt < max_attempts - 1:
            print(f"  Attempt {attempt + 1}/{max_attempts} - Backend not ready yet...")
            time.sleep(delay)
    
    print("✗ Backend failed to start within expected time")
    return False

def wait_for_frontend(max_attempts=30, delay=1):
    """Wait for frontend to be ready by polling the dev server"""
    print("Waiting for frontend to be ready...")
    
    for attempt in range(max_attempts):
        try:
            response = requests.get("http://localhost:3000", timeout=2)
            if response.status_code == 200:
                print("✓ Frontend is ready!")
                return True
        except (requests.RequestException, requests.Timeout):
            pass
        
        if attempt < max_attempts - 1:
            print(f"  Attempt {attempt + 1}/{max_attempts} - Frontend not ready yet...")
            time.sleep(delay)
    
    print("⚠️  Frontend may not be ready yet, but continuing...")
    return False

def open_browser():
    """Open the Drum Trainer application in the default browser"""
    try:
        print("🌐 Opening Drum Trainer in your default browser...")
        webbrowser.open("http://localhost:3000")
        print("✓ Browser opened successfully!")
    except Exception as e:
        print(f"⚠️  Could not open browser automatically: {e}")
        print("   Please manually open: http://localhost:3000")

def main():
    """Main startup function"""
    print("🚀 Starting Drum Trainer Development Environment")
    print("=" * 50)
    
    # Check dependencies
    if not check_dependencies():
        # Try to install backend dependencies automatically
        if not install_backend_deps():
            print("Please install dependencies manually:")
            print("  source venv/bin/activate  # or venv\\Scripts\\activate on Windows")
            print("  pip install -r requirements.txt")
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
    
    # Wait for backend to be ready
    if not wait_for_backend():
        print("Stopping backend...")
        backend_process.terminate()
        sys.exit(1)
    
    # Start frontend
    frontend_process = start_frontend()
    if not frontend_process:
        print("Stopping backend...")
        backend_process.terminate()
        sys.exit(1)
    
    # Wait for frontend to be ready
    if wait_for_frontend():
        # Small delay to ensure frontend is fully loaded
        print("⏳ Waiting a moment for frontend to fully load...")
        time.sleep(3)
        # Open browser automatically
        open_browser()
    else:
        print("💡 You can manually open: http://localhost:3000")
    
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
