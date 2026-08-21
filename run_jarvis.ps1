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
$venvPython = ""
if (Test-Path ".\Source Code\.venv\Scripts\python.exe") {
    $venvPython = ".\Source Code\.venv\Scripts\python.exe"
} elseif (Test-Path ".\.venv\Scripts\python.exe") {
    $venvPython = ".\.venv\Scripts\python.exe"
}

if (-not $venvPython) {
    Write-Host ""
    Write-Host "=======================================================" -ForegroundColor Yellow
    Write-Host "  FIRST-RUN INITIALIZATION: Provisioning Virtualenv" -ForegroundColor Yellow
    Write-Host "=======================================================" -ForegroundColor Yellow
    Write-Host "[1/3] Creating local virtual environment (.venv)..." -ForegroundColor Cyan
    if (Test-Path ".\Source Code") {
        & $pythonCheck.Name -m venv ".\Source Code\.venv"
        $venvPython = ".\Source Code\.venv\Scripts\python.exe"
        & $venvPython -m pip install --upgrade pip | Out-Null
        Write-Host "[3/3] Installing packages from Source Code/requirements.txt..." -ForegroundColor Cyan
        & $venvPython -m pip install -r ".\Source Code\requirements.txt"
    } else {
        & $pythonCheck.Name -m venv ".\.venv"
        $venvPython = ".\.venv\Scripts\python.exe"
        & $venvPython -m pip install --upgrade pip | Out-Null
        Write-Host "[3/3] Installing packages from requirements.txt..." -ForegroundColor Cyan
        & $venvPython -m pip install -r requirements.txt
    }
    Write-Host "[SUCCESS]: Environment provisioned successfully!" -ForegroundColor Green
    Write-Host ""
}

# 3. Verify runtime dependencies
$depCheck = & $venvPython -c "import pydantic, requests" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[NOTICE]: Installing missing dependencies..." -ForegroundColor Yellow
    if (Test-Path ".\Source Code\requirements.txt") {
        & $venvPython -m pip install -r ".\Source Code\requirements.txt"
    } else {
        & $venvPython -m pip install -r requirements.txt
    }
}

# 4. Launch JARVIS AI Workstation
Write-Host "[LAUNCH]: Starting JARVIS AI Workstation..." -ForegroundColor Green
Write-Host "=======================================================" -ForegroundColor Cyan
Write-Host ""
if (Test-Path ".\Source Code\main.py") {
    Push-Location ".\Source Code"
    & ".\.venv\Scripts\python.exe" main.py
    Pop-Location
} else {
    & $venvPython main.py
}

if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "[JARVIS System Notice]: Process exited with code $LASTEXITCODE." -ForegroundColor Red
    Read-Host "Press Enter to exit..."
}
