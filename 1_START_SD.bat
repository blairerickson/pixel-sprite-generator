@echo off
echo Starting Stable Diffusion API...
cd /d "%~dp0..\stable-diffusion-webui"
set BOOTSTRAP_ENV=%~dp0..\backend\venv\Scripts\python.exe
if exist "%BOOTSTRAP_ENV%" (
    echo    Using backend virtualenv Python: %BOOTSTRAP_ENV%
    set PYTHON=%BOOTSTRAP_ENV%
) else (
    echo    Backend Python not found, falling back to system python
    set PYTHON=
)

set COMMANDLINE_ARGS=--api --listen --port 7860
call webui-user.bat

