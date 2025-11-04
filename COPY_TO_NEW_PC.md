# Copying Project to Another PC

## ❌ **Short Answer: NO, you can't just copy-paste everything**

The project has large model files and virtual environments that won't transfer well. Here's the right way to do it:

---

## ✅ **Correct Way to Set Up on New PC**

### **What to Copy:**
✅ Copy these folders/files:
- `backend/` (Python code)
- `frontend/` (HTML/CSS/JS)
- `scripts/` (Setup scripts)
- `comfyui/` (Workflows)
- `*.md` (Documentation)
- `*.sh` (Shell scripts)
- `*.bat` (Windows scripts)
- `package.json`, `requirements.txt`, `config.yaml`

❌ **DO NOT Copy:**
- `backend/venv/` (Virtual environment - recreate on new PC)
- `stable-diffusion-webui/` (Too large, reinstall fresh)
- `stable-diffusion-webui/models/` (Model files - 2GB+, download separately)
- `output/`, `temp/`, `cache/` (Generated files)
- `__pycache__/`, `*.pyc` (Python cache)
- `.git/` (Optional, or use git clone instead)

---

## 🚀 **Step-by-Step Setup on New PC**

### **Method 1: Using Git (Recommended)**

#### **On Your Current Mac:**
```bash
cd /Users/himanshumacpro24/Development/pixel-sprite-generator

# Make sure all important changes are committed
git add .
git commit -m "Ready for deployment"
git push origin Pixel-Main
```

#### **On New PC:**
```bash
# Clone the repository
git clone <your-repo-url>
cd pixel-sprite-generator
```

---

### **Method 2: Manual Copy**

#### **On Your Current Mac - Create Clean Copy:**
```bash
cd /Users/himanshumacpro24/Development

# Create a clean copy excluding large files
rsync -av --progress \
  --exclude='backend/venv' \
  --exclude='stable-diffusion-webui' \
  --exclude='output' \
  --exclude='temp' \
  --exclude='cache' \
  --exclude='__pycache__' \
  --exclude='*.pyc' \
  --exclude='.git' \
  pixel-sprite-generator/ pixel-sprite-generator-clean/

# Zip it
tar -czf pixel-sprite-generator-clean.tar.gz pixel-sprite-generator-clean/
```

Then transfer `pixel-sprite-generator-clean.tar.gz` to the new PC.

---

## 🔧 **Setup on New PC (macOS)**

### **1. Install Prerequisites**
```bash
# Install Homebrew (if not installed)
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"

# Install Python 3.10 (CRITICAL - must be 3.10, not 3.11/3.12)
brew install python@3.10

# Install Rust (needed for Stable Diffusion)
brew install rust

# Install Git
brew install git
```

### **2. Extract Project (if using manual copy)**
```bash
cd ~/Development
tar -xzf pixel-sprite-generator-clean.tar.gz
cd pixel-sprite-generator-clean
```

### **3. Set Up Python Virtual Environment**
```bash
cd backend
python3.10 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### **4. Install Stable Diffusion WebUI**
```bash
cd /path/to/pixel-sprite-generator
git clone https://github.com/AUTOMATIC1111/stable-diffusion-webui.git
```

### **5. Download Models** (REQUIRED!)

**Option A: Download from CivitAI (Manual)**
1. Download `allInOnePixelModel_v1.ckpt` (2.0GB) from:
   - https://civitai.com/models/34/all-in-one-pixel-model
   - Place in: `stable-diffusion-webui/models/Stable-diffusion/`

2. Download `pixel-art-xl-v1.1.safetensors` (163MB) from:
   - https://civitai.com/models/120096/pixel-art-xl
   - Place in: `stable-diffusion-webui/models/Lora/`

**Option B: Copy from Original Mac (if available)**
```bash
# On original Mac, copy models to external drive or network
cp stable-diffusion-webui/models/Stable-diffusion/allInOnePixelModel_v1.ckpt /path/to/transfer/
cp stable-diffusion-webui/models/Lora/pixel-art-xl-v1.1.safetensors /path/to/transfer/

# On new Mac, copy to correct locations
cp /path/to/transfer/allInOnePixelModel_v1.ckpt stable-diffusion-webui/models/Stable-diffusion/
cp /path/to/transfer/pixel-art-xl-v1.1.safetensors stable-diffusion-webui/models/Lora/
```

### **6. Update Paths in config.yaml**
Edit `backend/config.yaml` and update any absolute paths if needed.

### **7. Make Scripts Executable**
```bash
chmod +x start_webui.sh start_backend.sh
```

### **8. Run the Project**
```bash
# Terminal 1
./start_webui.sh

# Terminal 2
./start_backend.sh
```

### **9. Open Browser**
Go to: http://127.0.0.1:8010

---

## 🪟 **Setup on New PC (Windows)**

### **1. Install Prerequisites**
- Download and install Python 3.10.6 from: https://www.python.org/downloads/release/python-3106/
  - ✅ Check "Add Python to PATH"
  - ✅ Check "Install for all users"

- Download and install Git from: https://git-scm.com/download/win

- Install Visual Studio Build Tools:
  - https://visualstudio.microsoft.com/downloads/
  - Select "Desktop development with C++"

### **2. Extract Project**
Extract the zip file to `C:\Development\pixel-sprite-generator\`

### **3. Set Up Python Virtual Environment**
```cmd
cd C:\Development\pixel-sprite-generator\backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements-windows.txt
```

### **4. Install Stable Diffusion WebUI**
```cmd
cd C:\Development\pixel-sprite-generator
git clone https://github.com/AUTOMATIC1111/stable-diffusion-webui.git
```

### **5. Download Models** (Same as macOS above)
Place models in:
- `stable-diffusion-webui\models\Stable-diffusion\allInOnePixelModel_v1.ckpt`
- `stable-diffusion-webui\models\Lora\pixel-art-xl-v1.1.safetensors`

### **6. Run the Project**

**Option A: Using Batch Files (Easiest)**
```cmd
REM Terminal 1 - Start Stable Diffusion WebUI
1_START_SD.bat

REM Terminal 2 - Start Backend API
2_START_BACKEND.bat
```

**Option B: Manual Commands**
```cmd
REM Terminal 1
cd stable-diffusion-webui
webui.bat --api --listen --port 7860

REM Terminal 2
cd backend
venv\Scripts\activate
python api.py
```

### **7. Open Browser**
Go to: http://127.0.0.1:8010

---

## 📋 **Quick Checklist for New PC**

- [ ] Python 3.10 installed (NOT 3.11 or 3.12)
- [ ] Git installed
- [ ] Project files copied/cloned
- [ ] Virtual environment created
- [ ] Dependencies installed (`pip install -r requirements.txt`)
- [ ] Stable Diffusion WebUI cloned
- [ ] Model files downloaded (2GB+ total)
- [ ] Models placed in correct directories
- [ ] Scripts made executable (macOS/Linux)
- [ ] Tested: WebUI starts without errors
- [ ] Tested: Backend starts without errors
- [ ] Tested: Frontend loads in browser

---

## ⚠️ **Common Issues on New PC**

### **Issue 1: "Python 3.10 not found"**
- Make sure you installed Python 3.10 specifically
- On Mac: `brew install python@3.10`
- On Windows: Download Python 3.10.6 installer from python.org
- **Windows**: Make sure you checked "Add Python to PATH" during installation
- **Test**: Open Command Prompt and type `python --version`

### **Issue 2: "Module not found" errors**

**macOS:**
```bash
# Activate venv and reinstall
source backend/venv/bin/activate
pip install -r requirements.txt
```

**Windows:**
```cmd
cd backend
venv\Scripts\activate
pip install -r requirements-windows.txt
```

### **Issue 3: "Models not loading"**
- Check model file names match config.yaml (should be `allInOnePixelModel_v1.ckpt`)
- Check files are in correct directories:
  - `stable-diffusion-webui/models/Stable-diffusion/allInOnePixelModel_v1.ckpt`
  - `stable-diffusion-webui/models/Lora/pixel-art-xl-v1.1.safetensors`
- Check file permissions (especially on Windows)
- Check that files aren't blocked (Windows: Right-click → Properties → Unblock)

### **Issue 4: "Port already in use"**

**macOS:**
```bash
lsof -i :8010
kill -9 <PID>
```

**Windows:**
```cmd
netstat -ano | findstr :8010
taskkill /PID <PID> /F
```

### **Issue 5: "venv/Scripts/activate not found" (Windows)**
```cmd
# Recreate virtual environment
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements-windows.txt
```

### **Issue 6: "tokenizers compilation error" (Windows)**
- This happens if you use Python 3.11 or 3.12
- **Solution**: Uninstall and install Python 3.10.6 specifically
- Python 3.10 is REQUIRED for compatibility

### **Issue 7: "Stable Diffusion WebUI won't start" (Windows)**
```cmd
cd stable-diffusion-webui
# Delete any existing venv
rmdir /s venv
# Run webui.bat - it will create new venv
webui.bat --api --listen --port 7860
```

### **Issue 8: "Frontend shows blank page" (Windows)**
- Make sure both WebUI and Backend are running
- Check browser console (F12) for errors
- Try clearing browser cache (Ctrl+Shift+Delete)
- Try different browser (Chrome, Firefox, Edge)

### **Issue 9: "Can't download from CivitAI" (Windows)**
- Create free account on CivitAI
- Make sure files aren't blocked by antivirus
- Try downloading with browser instead of download manager
- Check that files are fully downloaded (2GB and 163MB sizes)

---

## 💾 **Model Files Are The Key**

The **most important files** to transfer are the model files:
- `allInOnePixelModel_v1.ckpt` (2.0GB)
- `pixel-art-xl-v1.1.safetensors` (163MB)

Without these, the system won't work. Everything else can be reinstalled quickly.

---

## 🎯 **Recommended Transfer Method**

**Best approach:**
1. ✅ Use Git to transfer code
2. ✅ Download models on new PC (or copy via external drive)
3. ✅ Recreate virtual environments
4. ✅ Run fresh Stable Diffusion WebUI install

**Why?** 
- Smaller transfer size
- Clean installation
- No compatibility issues
- Proper dependencies for new system

---

## 🪟 **Windows-Specific Quick Start Guide**

### **TL;DR - Complete Windows Setup (New PC)**

1. **Install Python 3.10.6** (NOT 3.11 or 3.12!)
   - Download: https://www.python.org/downloads/release/python-3106/
   - ✅ Check "Add Python to PATH"
   - ✅ Check "Install for all users"

2. **Install Git**
   - Download: https://git-scm.com/download/win
   - Use default settings

3. **Get the Project**
   ```cmd
   cd C:\Development
   git clone <your-repo-url>
   cd pixel-sprite-generator
   ```

4. **Set Up Backend**
   ```cmd
   cd backend
   python -m venv venv
   venv\Scripts\activate
   pip install -r requirements-windows.txt
   cd ..
   ```

5. **Install Stable Diffusion WebUI**
   ```cmd
   git clone https://github.com/AUTOMATIC1111/stable-diffusion-webui.git
   ```

6. **Download Models** (CRITICAL!)
   - Download `allInOnePixelModel_v1.ckpt` (2.0GB) from: https://civitai.com/models/34/all-in-one-pixel-model
   - Download `pixel-art-xl-v1.1.safetensors` (163MB) from: https://civitai.com/models/120096/pixel-art-xl
   
   Place them in:
   - `stable-diffusion-webui\models\Stable-diffusion\allInOnePixelModel_v1.ckpt`
   - `stable-diffusion-webui\models\Lora\pixel-art-xl-v1.1.safetensors`

7. **Run the Project**
   - Double-click `1_START_SD.bat` (wait for it to load)
   - Double-click `2_START_BACKEND.bat`
   - Open browser: http://127.0.0.1:8010

---

## ✅ **Verification Checklist for Windows**

Before you say "it's not working", check these:

- [ ] Python 3.10.6 installed (type `python --version` in cmd)
- [ ] Git installed
- [ ] Project cloned or extracted to `C:\Development\pixel-sprite-generator\`
- [ ] Backend venv created: `backend\venv\Scripts\activate.bat` exists
- [ ] Requirements installed: `pip list` shows fastapi, uvicorn, etc.
- [ ] Stable Diffusion WebUI cloned: `stable-diffusion-webui\` folder exists
- [ ] Model files downloaded (total ~2.2GB)
- [ ] Models in correct folders (check paths above)
- [ ] Files unblocked (right-click .ckpt file → Properties → Unblock if present)
- [ ] Both batch files run without errors
- [ ] WebUI shows "Running on local URL: http://127.0.0.1:7860"
- [ ] Backend shows "Uvicorn running on http://0.0.0.0:8010"
- [ ] Browser shows the UI with Icon/Character/Alive buttons
- [ ] Can generate a test sprite

---

## 📁 **Critical Files for Windows Transfer**

If using manual copy, make sure these are included:

**Must Have:**
- ✅ `backend/` folder (all Python files)
- ✅ `frontend/` folder (HTML/CSS/JS)
- ✅ `backend/config.yaml` (configuration)
- ✅ `backend/requirements-windows.txt` (dependencies)
- ✅ `1_START_SD.bat` (WebUI launcher)
- ✅ `2_START_BACKEND.bat` (Backend launcher)
- ✅ `start_webui.sh` and `start_backend.sh` (for reference)
- ✅ All `.md` documentation files

**Don't Copy:**
- ❌ `backend/venv/` (recreate on Windows)
- ❌ `stable-diffusion-webui/` except `models/` if you want to save download time
- ❌ `output/`, `temp/`, `cache/`
- ❌ `__pycache__/`, `*.pyc`

---

## 🎯 **Windows Performance Tips**

1. **GPU Acceleration**: If your Windows PC has NVIDIA GPU:
   - WebUI will automatically use it
   - Much faster than Mac CPU
   - 512x512 image in ~10-30 seconds

2. **Firewall**: Windows may ask to allow Python/WebUI through firewall
   - Click "Allow access" for both Private and Public networks

3. **Antivirus**: Some antivirus may flag model files
   - Add folder to exclusions: `stable-diffusion-webui\models\`
   - This is safe - models are just data files

4. **Windows Defender**: May slow down first run
   - Be patient during first WebUI startup
   - It's scanning new Python environment

---

## 🚨 **Critical Windows Gotchas**

### **1. Python Version**
- ❌ Python 3.11 or 3.12 → Will NOT work
- ❌ Python from Microsoft Store → May cause issues
- ✅ Python 3.10.6 from python.org → Works perfectly

### **2. File Paths**
- Use `\` for paths in Windows, not `/`
- No spaces in folder names (use `C:\Development\` not `C:\My Projects\`)
- Install in short path (not `C:\Users\YourName\Desktop\...`)

### **3. Model Files**
- Must be **exactly** these sizes:
  - `allInOnePixelModel_v1.ckpt` → 2.0 GB (2,032,666,368 bytes)
  - `pixel-art-xl-v1.1.safetensors` → 163 MB (170,663,936 bytes)
- If different, re-download (file is corrupted)

### **4. Batch Files**
- Don't close the Command Prompt windows
- Keep both running (WebUI and Backend)
- They should show continuous logs

### **5. First Run Takes Longer**
- WebUI first run: 10-15 minutes (downloading dependencies)
- Be patient, it's normal
- Subsequent runs: 2-3 minutes

---

## 💡 **Windows-Specific Commands Reference**

```cmd
REM Check Python version
python --version

REM Check if pip works
pip --version

REM Check installed packages
pip list

REM Check running processes
tasklist | findstr python

REM Check ports in use
netstat -ano | findstr :8010
netstat -ano | findstr :7860

REM Kill process by PID
taskkill /PID <number> /F

REM Test backend health
curl http://127.0.0.1:8010/health

REM Test WebUI
curl http://127.0.0.1:7860
```

---

## ✨ **You're Ready!**

If you followed this guide, your Windows PC should now have a fully working Pixel Sprite Generator with:
- ✅ Icon mode (new feature!)
- ✅ Character sprites
- ✅ Pixel art generation
- ✅ All features from Mac version

**Need help?** Check the Common Issues section above or the documentation files in the project folder.

