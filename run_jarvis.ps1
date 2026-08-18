# STARK INDUSTRIES — JARVIS AI Workstation PowerShell Launcher
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Definition
Set-Location $ScriptDir

Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host "         INITIALIZING STARK JARVIS AI SYSTEM           " -ForegroundColor Cyan
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host "Target Directory: $ScriptDir" -ForegroundColor Yellow
Write-Host ""

# 1. Auto-detect Python installation
$pythonCheck = Get-Command python -ErrorAction SilentlyContinue
if (-not $pythonCheck) {
    $pythonCheck = Get-Command py -ErrorAction SilentlyContinue
}

if (-not $pythonCheck) {
    Write-Host "[ERROR]: Python is not installed or not added to system PATH!" -ForegroundColor Red
    Write-Host "Please install Python 3.10+ from https://www.python.org/ and enable 'Add Python to PATH'." -ForegroundColor Yellow
    Read-Host "Press Enter to exit..."
    exit 1
}

Write-Host "[SYSTEM CHECK]: Found Python runtime ($($pythonCheck.Name))." -ForegroundColor Green

# 2. Check if .venv exists
$venvPython = ".\.venv\Scripts\python.exe"
if (-not (Test-Path $venvPython)) {
    Write-Host ""
    Write-Host "=======================================================" -ForegroundColor Yellow
    Write-Host "  FIRST-RUN INITIALIZATION: Provisioning Virtualenv" -ForegroundColor Yellow
    Write-Host "=======================================================" -ForegroundColor Yellow
    Write-Host "[1/3] Creating local virtual environment (.venv)..." -ForegroundColor Cyan
    python -m venv .venv

    Write-Host "[2/3] Upgrading pip package installer..." -ForegroundColor Cyan
    & $venvPython -m pip install --upgrade pip | Out-Null

    Write-Host "[3/3] Installing all required AI, GUI, and Audio packages from requirements.txt..." -ForegroundColor Cyan
    Write-Host "      (This may take 1-2 minutes on first run. Please wait...)" -ForegroundColor Yellow
    Write-Host ""
    & $venvPython -m pip install -r requirements.txt
    Write-Host "[SUCCESS]: Environment provisioned successfully!" -ForegroundColor Green
    Write-Host ""
}

# 3. Verify PyQt6 installation
$pyqtCheck = & $venvPython -c "import PyQt6" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[NOTICE]: Installing missing dependencies..." -ForegroundColor Yellow
    & $venvPython -m pip install -r requirements.txt
}

# 4. Launch JARVIS AI Workstation
Write-Host "[LAUNCH]: Starting JARVIS AI Workstation..." -ForegroundColor Green
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host ""
& $venvPython main.py

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "[JARVIS System Notice]: Process exited with code $LASTEXITCODE." -ForegroundColor Red
    Read-Host "Press Enter to exit..."
}
