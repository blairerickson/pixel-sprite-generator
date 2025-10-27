@echo off
REM ============================================================
REM  PearlOS Pixel Engine - Windows Launcher
REM ============================================================

echo.
echo ============================================================
echo   PearlOS Pixel Engine Launching (Windows)
echo ============================================================
echo.

cd /d "%~dp0"

REM Check if Python 3.10 is available
py -3.10 --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python 3.10 not found
    echo Please install Python 3.10 from https://www.python.org/downloads/
    pause
    exit /b 1
)

REM Run full setup to guarantee dependencies and assets
echo [1] Ensuring environment is prepared...
backend\venv\Scripts\python.exe -V >NUL 2>&1
if errorlevel 1 (
    py -3.10 -m venv backend\venv
)
backend\venv\Scripts\python.exe scripts\bootstrap.py setup --skip-assets --skip-sd-bootstrap >NUL

echo [2] Launching PearlOS Pixel Engine services...
call START_PEARL_SALON.bat

