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

    Write-Host "[2/3] Bootstrapping and upgrading pip package installer..." -ForegroundColor Cyan
    & $venvPython -m ensurepip --default-pip | Out-Null
    & $venvPython -m pip install --upgrade pip | Out-Null

    Write-Host "[3/3] Installing all required AI, GUI, and Audio packages from requirements.txt..." -ForegroundColor Cyan
    Write-Host "      (This may take 1-2 minutes on first run. Please wait...)" -ForegroundColor Yellow
    Write-Host ""
    & $venvPython -m pip install -r requirements.txt
    Write-Host "[SUCCESS]: Environment provisioned successfully!" -ForegroundColor Green
    Write-Host ""
}

# 3. Verify core runtime dependencies inside .venv
& $venvPython -m pip --version | Out-Null
if ($LASTEXITCODE -ne 0) {
    Write-Host "[NOTICE]: Bootstrapping missing pip installer inside .venv..." -ForegroundColor Yellow
    & $venvPython -m ensurepip --default-pip | Out-Null
}

$depCheck = & $venvPython -c "import pydantic, requests, PyQt6" 2>&1
if ($LASTEXITCODE -ne 0) {
    Write-Host "[NOTICE]: Installing missing dependencies..." -ForegroundColor Yellow
    & $venvPython -m pip install -r requirements.txt
}

# 4. Check Ollama AI daemon & model registration
$ollamaCheck = Get-Command ollama -ErrorAction SilentlyContinue
if ($ollamaCheck) {
    try {
        $tags = Invoke-RestMethod -Uri "http://127.0.0.1:11434/api/tags" -TimeoutSec 2 -ErrorAction Stop
        Write-Host "[OLLAMA CHECK]: Ollama AI service online on http://127.0.0.1:11434." -ForegroundColor Green
    } catch {
        Write-Host "[OLLAMA CHECK]: Starting background Ollama AI service..." -ForegroundColor Yellow
        Start-Process -FilePath "ollama" -ArgumentList "serve" -WindowStyle Hidden
        Start-Sleep -Seconds 2
    }

    $installedModels = & ollama list 2>&1
    if ($installedModels -notmatch "jarvis-trained-model") {
        if (Test-Path ".\models\jarvis-trained-model.gguf") {
            Write-Host "[OLLAMA SETUP]: Registering jarvis-trained-model from local GGUF..." -ForegroundColor Cyan
            & ollama create jarvis-trained-model -f Modelfile
        } else {
            Write-Host "[OLLAMA SETUP]: Local GGUF not bundled. Auto-pulling base model qwen2.5:1.5b..." -ForegroundColor Cyan
            & ollama pull qwen2.5:1.5b
            $autoModelfile = @"
FROM qwen2.5:1.5b
PARAMETER temperature 0.2
PARAMETER top_p 0.95
PARAMETER num_predict 512
PARAMETER stop "<|im_end|>"
PARAMETER stop "<|endoftext|>"
PARAMETER stop "###"
TEMPLATE """Below is an instruction that describes a task, paired with an input that provides further context. Write a response that appropriately completes the request.

### Instruction:
You are JARVIS, an autonomous AI smart home and desktop assistant. Parse the user request into structured JSON actions.

### Input:
{{ .Prompt }}

### Response:
"""
"@
            $autoModelfile | Out-File -FilePath "Modelfile.auto" -Encoding utf8
            & ollama create jarvis-trained-model -f Modelfile.auto
            Remove-Item "Modelfile.auto" -Force -ErrorAction SilentlyContinue
        }
    }
} else {
    Write-Host "[OLLAMA NOTICE]: Ollama CLI not detected. Local GUI automation active." -ForegroundColor Yellow
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
