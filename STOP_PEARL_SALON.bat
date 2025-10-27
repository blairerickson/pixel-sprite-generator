@echo off
REM ============================================================
REM  Pearl Pixel Salon - Stop All Services
REM ============================================================

echo.
echo Stopping Pearl Pixel Salon...
echo.

taskkill /FI "WINDOWTITLE eq Stable Diffusion API*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq Backend API*" /F >nul 2>&1
taskkill /FI "WINDOWTITLE eq Web Interface*" /F >nul 2>&1

echo All services stopped.
echo.
pause


