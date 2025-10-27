# ============================================================
#  Pearl Pixel Salon - PowerShell Launcher
# ============================================================

$ErrorActionPreference = "SilentlyContinue"
$BaseDir = Split-Path -Parent $MyInvocation.MyCommand.Path

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Pearl Pixel Salon" -ForegroundColor Magenta
Write-Host "  One-Click Launcher" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Check setup
if (-not (Test-Path "$BaseDir\backend\venv\Scripts\python.exe")) {
    Write-Host "[!] Backend not set up yet!" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please run SETUP_WINDOWS_SIMPLE.bat first." -ForegroundColor Yellow
    Write-Host ""
    Read-Host "Press Enter to exit"
    exit 1
}

Write-Host "Stopping any existing services..." -ForegroundColor Gray
Stop-Process -Name python -Force -ErrorAction SilentlyContinue
Start-Sleep -Seconds 2

Write-Host ""
Write-Host "[1/4] Starting Stable Diffusion..." -ForegroundColor Green

$sdPath = Join-Path (Split-Path $BaseDir) "stable-diffusion-webui"
$pythonPath = Join-Path $BaseDir "backend\venv\Scripts\python.exe"
$env:PYTHON = $null
if (Test-Path $pythonPath) {
    Write-Host "       Using backend virtualenv Python: $pythonPath" -ForegroundColor Gray
    $env:PYTHON = $pythonPath
}

$sdProcess = Start-Process powershell -ArgumentList @(
    '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command',
    "Set-Location '$sdPath'; `$env:COMMANDLINE_ARGS='--api --listen --port 7860'; .\webui-user.bat"
) -PassThru -WindowStyle Minimized

Write-Host "       Waiting for Stable Diffusion health check..." -ForegroundColor Gray
$maxWait = 120
$elapsed = 0
while ($elapsed -lt $maxWait) {
    try {
        Invoke-WebRequest -Uri 'http://127.0.0.1:7860/sdapi/v1/sd-models' -UseBasicParsing -TimeoutSec 10 | Out-Null
        Write-Host "       Stable Diffusion is responsive" -ForegroundColor Green
        break
    }
    catch {
        Start-Sleep -Seconds 5
        $elapsed += 5
    }
}

if ($elapsed -ge $maxWait) {
    Write-Host "[ERROR] Stable Diffusion did not respond in time." -ForegroundColor Red
    Write-Host "Check the SD console window for details." -ForegroundColor Yellow
    exit 1
}

Write-Host ""
Write-Host "[2/4] Starting Backend API..." -ForegroundColor Green

$backendProcess = Start-Process powershell -ArgumentList @(
    '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command',
    "Set-Location '$BaseDir\backend'; .\venv\Scripts\Activate.ps1; python api.py"
) -PassThru -WindowStyle Minimized

Start-Sleep -Seconds 5

Write-Host ""
Write-Host "[3/4] Starting Frontend server..." -ForegroundColor Green
$frontendProcess = Start-Process powershell -ArgumentList @(
    '-NoProfile', '-ExecutionPolicy', 'Bypass', '-Command',
    "Set-Location '$BaseDir\frontend'; py -3.10 -m http.server 8010"
) -PassThru -WindowStyle Minimized

Start-Sleep -Seconds 3

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  Pearl Pixel Salon is Ready!" -ForegroundColor Magenta
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Web Interface:  " -NoNewline
Write-Host "http://127.0.0.1:8010/" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Opening in browser..." -ForegroundColor Gray
Start-Sleep -Seconds 2
Start-Process "http://127.0.0.1:8010/"

Write-Host ""
Write-Host "  Services running (minimized windows):" -ForegroundColor Gray
Write-Host "  - Stable Diffusion API" -ForegroundColor DarkGray
Write-Host "  - Backend API" -ForegroundColor DarkGray
Write-Host "  - Frontend Viewer" -ForegroundColor DarkGray
Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Press Ctrl+C to stop all services" -ForegroundColor Yellow
Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

# Keep running until Ctrl+C
try {
    while ($true) {
        Start-Sleep -Seconds 5
        
        # Check if services are still running
        if (-not (Get-Process -Id $backendProcess.Id -ErrorAction SilentlyContinue)) {
            Write-Host "[!] Backend stopped unexpectedly!" -ForegroundColor Red
            break
        }
        if (-not (Get-Process -Id $frontendProcess.Id -ErrorAction SilentlyContinue)) {
            Write-Host "[!] Frontend server stopped unexpectedly!" -ForegroundColor Red
            break
        }
    }
}
finally {
    Write-Host ""
    Write-Host "Stopping Pearl Pixel Salon..." -ForegroundColor Yellow
    Stop-Process -Name python -Force -ErrorAction SilentlyContinue
    if ($sdProcess) { Stop-Process -Id $sdProcess.Id -Force -ErrorAction SilentlyContinue }
    if ($frontendProcess) { Stop-Process -Id $frontendProcess.Id -Force -ErrorAction SilentlyContinue }
    Write-Host "All services stopped." -ForegroundColor Green
    Write-Host ""
}


