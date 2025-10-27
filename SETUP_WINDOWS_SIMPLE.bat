@echo off
REM ============================================================
REM  Simple Windows Setup for Pixel Sprite Generator
REM ============================================================

cd /d "%~dp0"

echo.
echo ============================================================
echo   Pixel Sprite Generator - Windows Setup
echo ============================================================
echo.

REM Check Python 3.10
py -3.10 --version >nul 2>&1
if errorlevel 1 (
    echo [!] Python 3.10 not found
    echo.
    echo Please install Python 3.10 from:
    echo https://www.python.org/downloads/release/python-31011/
    echo.
    pause
    exit /b 1
)

echo [OK] Python 3.10 detected
echo.

REM Create backend venv
echo [1/3] Creating backend virtual environment...
if exist "backend\venv" (
    echo    Virtual environment already exists, skipping...
) else (
    py -3.10 -m venv backend\venv
    if errorlevel 1 (
        echo [ERROR] Failed to create venv
        pause
        exit /b 1
    )
    echo    [OK] Created venv
)

echo.
echo [2/4] Installing backend dependencies...
backend\venv\Scripts\python.exe -m pip install --upgrade pip --quiet
backend\venv\Scripts\python.exe -m pip install -r backend\requirements.txt
if errorlevel 1 (
    echo [ERROR] Failed to install backend dependencies
    pause
    exit /b 1
)

echo    [OK] Backend ready
echo.

REM Bootstrap Stable Diffusion web UI environment and assets
echo [3/4] Preparing Stable Diffusion runtime (first launch may take a while)...
backend\venv\Scripts\python.exe scripts\bootstrap.py setup
if errorlevel 1 (
    echo [ERROR] Failed to bootstrap Stable Diffusion environment
    pause
    exit /b 1
)

echo    [OK] Stable Diffusion prepared
echo.

REM Create directories
echo [4/4] Creating output directories...
if not exist "output" mkdir output
if not exist "temp" mkdir temp  
if not exist "cache" mkdir cache
echo    [OK] Directories ready
echo.

echo ============================================================
echo   Setup Complete!
echo ============================================================
echo.
echo Next steps:
echo.
echo 1. Launch everything with START_WINDOWS.bat
echo.
echo 2. Or run components manually:
echo    - Stable Diffusion: 1_START_SD.bat
echo    - Backend API: backend\venv\Scripts\python.exe backend\api.py
echo    - Frontend:      py -3.10 -m http.server 8010 --directory frontend
echo.
pause


