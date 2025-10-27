@echo off
REM ============================================================
REM  Pearl Pixel Salon - One-Click Launcher
REM ============================================================

cd /d "%~dp0"

echo.
echo ============================================================
echo   PearlOS Pixel Engine Launching
echo ============================================================
echo.

REM Check if setup was run
if not exist "backend\venv\Scripts\python.exe" (
    echo [!] Backend not set up yet!
    echo.
    echo Please run SETUP_WINDOWS_SIMPLE.bat first.
    echo.
    pause
    exit /b 1
)

echo Starting services...
echo.

REM Kill any existing instances
taskkill /FI "WINDOWTITLE eq PearlOS Pixel Engine - SD*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq PearlOS Pixel Engine - Backend*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq PearlOS Pixel Engine - Frontend*" /F >nul 2>&1
timeout /t 2 /nobreak >nul

echo [1/4] Launching engine core...
start "PearlOS Pixel Engine - SD" /MIN cmd /c "%~dp01_START_SD.bat"

echo [2/4] Waiting for engine core health check...
call :WaitForHealth "http://127.0.0.1:7860/sdapi/v1/sd-models" 120
if errorlevel 1 (
    echo [ERROR] Stable Diffusion API did not respond in time.
    echo See log window "PearlOS Pixel Engine - SD" for details.
    goto END
)

echo [3/4] Launching services...
start "PearlOS Pixel Engine - Backend" /MIN cmd /c "%~dp02_START_BACKEND.bat"
timeout /t 5 /nobreak >nul
start "PearlOS Pixel Engine - Frontend" /MIN cmd /c "%~dp03_START_FRONTEND.bat"
timeout /t 3 /nobreak >nul

echo [4/4] Services launched successfully.

echo.
echo ============================================================
echo   PearlOS Pixel Engine is Ready!
echo ============================================================
echo.
echo   Opening in your browser...
echo.

REM Open browser
timeout /t 2 /nobreak >nul
start http://127.0.0.1:8010/

echo   Services running in background windows:
echo   - Engine Core (minimized)
echo   - Backend Services (minimized)
echo   - Live Frontend (minimized)
echo.
echo   View the console windows by clicking them in taskbar.
echo.
echo ============================================================
echo.
echo   TO STOP: Press any key or run STOP_PEARL_SALON.bat
echo.
echo ============================================================
pause

REM Stop all services when user presses key
echo.
echo Stopping PearlOS Pixel Engine...
taskkill /FI "WINDOWTITLE eq PearlOS Pixel Engine - SD*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq PearlOS Pixel Engine - Backend*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq PearlOS Pixel Engine - Frontend*" /F >nul 2>&1

echo All services stopped.
echo.
timeout /t 2 /nobreak >nul

goto :EOF

:WaitForHealth
setlocal
set "url=%~1"
set "timeout=%~2"
if "%timeout%"=="" set "timeout=60"
set "interval=5"
set "elapsed=0"

:HEALTH_LOOP
powershell -NoLogo -NoProfile -Command "try { Invoke-WebRequest -Uri '%url%' -UseBasicParsing -TimeoutSec 10 | Out-Null; exit 0 } catch { exit 1 }"
if %ERRORLEVEL%==0 (
    endlocal & exit /b 0
)
set /a elapsed+=interval
if %elapsed% GEQ %timeout% (
    endlocal & exit /b 1
)
timeout /t %interval% /nobreak >nul
goto HEALTH_LOOP


