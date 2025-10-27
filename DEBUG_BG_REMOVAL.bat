@echo off
REM Quick script to test background removal on last generated image

cd /d "%~dp0backend"

echo.
echo ============================================================
echo   Background Removal Debug Tool
echo ============================================================
echo.

REM Find most recent output folder
for /f "delims=" %%i in ('dir /b /ad /o-d ..\output') do (
    set LATEST=%%i
    goto :found
)

:found
if not defined LATEST (
    echo No output folders found!
    echo Generate something first.
    pause
    exit /b 1
)

echo Latest generation: %LATEST%
echo.

REM Test on original
set IMAGE=..\output\%LATEST%\original_0.png

if not exist "%IMAGE%" (
    echo Image not found: %IMAGE%
    pause
    exit /b 1
)

echo Testing background removal on:
echo %IMAGE%
echo.
echo ============================================================
echo.

call venv\Scripts\python.exe test_bg_removal.py "%IMAGE%"

echo.
echo ============================================================
echo.
echo Check the output folder for results!
echo.
pause


