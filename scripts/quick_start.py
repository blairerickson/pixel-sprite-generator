"""
Quick start script for Pixel Sprite Generator
Automates setup and testing
"""
import os
import sys
import subprocess
import platform
from pathlib import Path

def print_header(text):
    print("\n" + "="*60)
    print(f"  {text}")
    print("="*60 + "\n")

def print_step(num, text):
    print(f"\n[{num}] {text}")

def run_command(cmd, cwd=None):
    """Run command and return success status"""
    try:
        subprocess.run(cmd, shell=True, check=True, cwd=cwd)
        return True
    except subprocess.CalledProcessError:
        return False

def check_python():
    """Check Python version"""
    version = sys.version_info
    if version.major < 3 or (version.major == 3 and version.minor < 10):
        print("❌ Python 3.10+ required")
        return False
    print(f"✅ Python {version.major}.{version.minor}.{version.micro}")
    return True

def check_git():
    """Check if git is installed"""
    if run_command("git --version"):
        print("✅ Git installed")
        return True
    print("❌ Git not found")
    return False

def setup_venv():
    """Create and activate virtual environment"""
    print_step(1, "Creating virtual environment...")
    
    backend_dir = Path(__file__).parent.parent / "backend"
    venv_dir = backend_dir / "venv"
    
    if venv_dir.exists():
        print("  ℹ️  Virtual environment already exists")
    else:
        if not run_command(f"{sys.executable} -m venv venv", cwd=backend_dir):
            print("  ❌ Failed to create venv")
            return False
        print("  ✅ Virtual environment created")
    
    # Determine activation script
    if platform.system() == "Windows":
        activate_script = venv_dir / "Scripts" / "activate.bat"
        pip_exe = venv_dir / "Scripts" / "pip.exe"
    else:
        activate_script = venv_dir / "bin" / "activate"
        pip_exe = venv_dir / "bin" / "pip"
    
    return True, pip_exe

def install_requirements(pip_exe):
    """Install Python requirements"""
    print_step(2, "Installing requirements...")
    
    backend_dir = Path(__file__).parent.parent / "backend"
    requirements = backend_dir / "requirements.txt"
    
    cmd = f'"{pip_exe}" install -r "{requirements}"'
    if run_command(cmd):
        print("  ✅ Requirements installed")
        return True
    else:
        print("  ❌ Failed to install requirements")
        return False

def create_directories():
    """Create necessary directories"""
    print_step(3, "Creating directories...")
    
    base_dir = Path(__file__).parent.parent
    dirs = ["output", "temp", "cache"]
    
    for dir_name in dirs:
        dir_path = base_dir / dir_name
        dir_path.mkdir(exist_ok=True)
        print(f"  ✅ {dir_name}/")
    
    return True

def check_sd_backend():
    """Check if SD backend is accessible"""
    print_step(4, "Checking Stable Diffusion backend...")
    
    try:
        import requests
        
        # Try A1111
        try:
            response = requests.get("http://127.0.0.1:7860/sdapi/v1/sd-models", timeout=2)
            if response.status_code == 200:
                print("  ✅ Automatic1111 detected on port 7860")
                return True, "automatic1111"
        except:
            pass
        
        # Try ComfyUI
        try:
            response = requests.get("http://127.0.0.1:8188/system_stats", timeout=2)
            if response.status_code == 200:
                print("  ✅ ComfyUI detected on port 8188")
                return True, "comfyui"
        except:
            pass
        
        print("  ⚠️  No SD backend detected")
        print("     Please install and start Automatic1111 or ComfyUI")
        print("     See docs/SETUP.md for instructions")
        return False, None
        
    except ImportError:
        print("  ⚠️  'requests' not installed, skipping check")
        return False, None

def update_config(backend_type):
    """Update config.yaml with detected backend"""
    if not backend_type:
        return
    
    print_step(5, "Updating configuration...")
    
    config_path = Path(__file__).parent.parent / "backend" / "config.yaml"
    
    try:
        with open(config_path, 'r') as f:
            content = f.read()
        
        # Update backend type
        if backend_type == "automatic1111":
            content = content.replace('backend: "comfyui"', 'backend: "automatic1111"')
            content = content.replace('api_url: "http://127.0.0.1:8188"', 'api_url: "http://127.0.0.1:7860"')
        else:
            content = content.replace('backend: "automatic1111"', 'backend: "comfyui"')
            content = content.replace('api_url: "http://127.0.0.1:7860"', 'api_url: "http://127.0.0.1:8188"')
        
        with open(config_path, 'w') as f:
            f.write(content)
        
        print(f"  ✅ Config updated for {backend_type}")
    except Exception as e:
        print(f"  ⚠️  Could not update config: {e}")

def print_next_steps(has_backend):
    """Print instructions for next steps"""
    print_header("Setup Complete!")
    
    if not has_backend:
        print("⚠️  IMPORTANT: Install Stable Diffusion backend first")
        print("\nOption A - Automatic1111 (Recommended):")
        print("  1. git clone https://github.com/AUTOMATIC1111/stable-diffusion-webui.git")
        print("  2. cd stable-diffusion-webui")
        print("  3. Run: webui-user.bat (Windows) or ./webui.sh (Linux/Mac)")
        print("  4. Add --api flag in webui-user settings")
        print("\nOption B - ComfyUI:")
        print("  1. git clone https://github.com/comfyanonymous/ComfyUI")
        print("  2. cd ComfyUI")
        print("  3. pip install -r requirements.txt")
        print("  4. python main.py")
        print("\nThen download models - see docs/MODELS.md")
        print("\n" + "-"*60 + "\n")
    
    backend_dir = Path(__file__).parent.parent / "backend"
    frontend_dir = Path(__file__).parent.parent / "frontend"
    
    print("🚀 To start the backend:")
    if platform.system() == "Windows":
        print(f"  cd {backend_dir}")
        print("  venv\\Scripts\\activate")
        print("  python api.py")
    else:
        print(f"  cd {backend_dir}")
        print("  source venv/bin/activate")
        print("  python api.py")
    
    print("\n🌐 To start the frontend:")
    print(f"  cd {frontend_dir}")
    print("  python -m http.server 8080")
    print("  Open: http://localhost:8080")
    
    print("\n📚 Documentation:")
    print("  Setup Guide:  README.md")
    
    print("\n✨ Example usage:")
    print("  curl -X POST http://localhost:8000/generate \\")
    print('    -H "Content-Type: application/json" \\')
    print('    -d \'{"prompt": "pixel art knight", "preset": "character_sprite"}\'')

def main():
    print_header("Pixel Sprite Generator - Quick Start")
    
    print("Checking prerequisites...")
    
    if not check_python():
        sys.exit(1)
    
    if not check_git():
        print("⚠️  Git recommended but not required")
    
    print("\n" + "-"*60)
    
    # Setup
    result = setup_venv()
    if not result:
        sys.exit(1)
    
    success, pip_exe = result
    
    if not install_requirements(pip_exe):
        sys.exit(1)
    
    if not create_directories():
        sys.exit(1)
    
    has_backend, backend_type = check_sd_backend()
    
    if backend_type:
        update_config(backend_type)
    
    # Done
    print_next_steps(has_backend)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Setup cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

