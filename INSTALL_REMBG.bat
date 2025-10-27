@echo off
echo Installing rembg for AI-based background removal...
echo.
echo This will take a few minutes (downloads AI models ~100MB)
echo.
pause

cd /d "%~dp0backend"
call venv\Scripts\activate.bat
pip install rembg==2.0.56

echo.
echo ========================================
echo Installation complete!
echo ========================================
echo.
echo Rembg uses AI to detect subjects and remove backgrounds
echo - Much cleaner than chromakey/magenta approach
echo - No color bleeding or artifacts
echo - Works with any background color
echo.
echo Your config.yaml is already updated to use rembg.
echo Just restart the backend and try generating!
echo.
pause


