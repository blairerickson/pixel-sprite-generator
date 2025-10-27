@echo off
REM Test if all services are responding

cd /d "%~dp0"

echo.
echo ============================================================
echo   Testing Connections
echo ============================================================
echo.

echo [1] Testing Stable Diffusion API (port 7860)...
curl -s http://127.0.0.1:7860/docs >nul 2>&1
if errorlevel 1 (
    echo    [FAIL] Cannot reach http://127.0.0.1:7860
    echo    Make sure Stable Diffusion is running with --api flag
) else (
    echo    [OK] Stable Diffusion API responding
)

echo.
echo [2] Testing Backend API (port 8000)...
curl -s http://127.0.0.1:8000/health >nul 2>&1
if errorlevel 1 (
    echo    [FAIL] Cannot reach http://127.0.0.1:8000
    echo    Make sure backend is running
) else (
    echo    [OK] Backend API responding
    curl -s http://127.0.0.1:8000/health
)

echo.
echo [3] Testing Frontend (port 8010)...
curl -s http://127.0.0.1:8010/index.html >nul 2>&1
if errorlevel 1 (
    echo    [FAIL] Cannot reach http://127.0.0.1:8010
    echo    Make sure frontend server is running
) else (
    echo    [OK] Frontend responding
)

echo.
echo ============================================================
echo   Test Complete
echo ============================================================
echo.
pause

