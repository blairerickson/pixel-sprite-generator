@echo off
echo Starting Web Interface...
cd /d "%~dp0frontend"
py -3.10 -m http.server 8080

