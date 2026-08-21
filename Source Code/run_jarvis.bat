@echo off
title STARK INDUSTRIES - JARVIS AI Workstation Launcher
cd /d "%~dp0"

echo =======================================================
echo          INITIALIZING STARK JARVIS AI SYSTEM           
echo =======================================================
echo Target Directory: %CD%
echo.

:: 1. Auto-detect Python installation (python or py launcher)
set PYTHON_CMD=
python --version >nul 2>&1
if not errorlevel 1 (
    set PYTHON_CMD=python
    goto PYTHON_FOUND
)

py -3 --version >nul 2>&1
if not errorlevel 1 (
    set PYTHON_CMD=py -3
    goto PYTHON_FOUND
)

py --version >nul 2>&1
if not errorlevel 1 (
    set PYTHON_CMD=py
    goto PYTHON_FOUND
)

goto NO_PYTHON

:PYTHON_FOUND
echo [SYSTEM CHECK]: Found Python runtime (%PYTHON_CMD%).

:: 2. Check if .venv exists
if exist ".\.venv\Scripts\python.exe" goto VERIFY_DEPS

echo.
echo =======================================================
echo  FIRST-RUN INITIALIZATION: Provisioning Virtualenv
echo =======================================================
echo [1/3] Creating local virtual environment (.venv)...
%PYTHON_CMD% -m venv .venv
if errorlevel 1 goto VENV_FAIL

echo [2/3] Bootstrapping and upgrading pip package installer...
.\.venv\Scripts\python.exe -m ensurepip --default-pip >nul 2>&1
.\.venv\Scripts\python.exe -m pip install --upgrade pip >nul 2>&1

echo [3/3] Installing all required AI, GUI, and Audio packages...
echo       (This may take 1-2 minutes on first run. Please wait...)
echo.
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
if errorlevel 1 goto DEPS_WARN

echo.
echo [SUCCESS]: Environment provisioned successfully!
echo.

:VERIFY_DEPS
:: 3. Verify core runtime dependencies inside .venv
.\.venv\Scripts\python.exe -m pip --version >nul 2>&1
if errorlevel 1 (
    echo [NOTICE]: Bootstrapping missing pip installer inside .venv...
    .\.venv\Scripts\python.exe -m ensurepip --default-pip >nul 2>&1
)

.\.venv\Scripts\python.exe -c "import pydantic, requests, PyQt6" >nul 2>&1
if errorlevel 1 (
    echo [NOTICE]: Installing missing dependencies inside .venv...
    .\.venv\Scripts\python.exe -m pip install -r requirements.txt
)

:: 4. Check Ollama background service status & auto-launch
ollama --version >nul 2>&1
if not errorlevel 1 (
    curl -s --connect-timeout 1 http://127.0.0.1:11434/api/tags >nul 2>&1
    if errorlevel 1 (
        echo [OLLAMA CHECK]: Starting background Ollama AI service...
        start /b "" ollama serve >nul 2>&1
        timeout /t 2 >nul 2>&1
    ) else (
        echo [OLLAMA CHECK]: Ollama AI service online on http://127.0.0.1:11434.
    )

    :: Ensure jarvis-trained-model exists in Ollama
    ollama list | findstr /i "jarvis-trained-model" >nul 2>&1
    if errorlevel 1 (
        if exist ".\models\jarvis-trained-model.gguf" (
            echo [OLLAMA SETUP]: Registering jarvis-trained-model from local GGUF...
            ollama create jarvis-trained-model -f Modelfile
        ) else (
            echo [OLLAMA SETUP]: Local GGUF not bundled. Auto-pulling base model qwen2.5:1.5b...
            ollama pull qwen2.5:1.5b
            (
                echo FROM qwen2.5:1.5b
                echo PARAMETER temperature 0.2
                echo PARAMETER top_p 0.95
                echo PARAMETER num_predict 512
                echo PARAMETER stop "<|im_end|>"
                echo PARAMETER stop "<|endoftext|>"
                echo PARAMETER stop "###"
                echo TEMPLATE """Below is an instruction that describes a task, paired with an input that provides further context. Write a response that appropriately completes the request.
                echo.
                echo ### Instruction:
                echo You are JARVIS, an autonomous AI smart home and desktop assistant. Parse the user request into structured JSON actions.
                echo.
                echo ### Input:
                echo {{ .Prompt }}
                echo.
                echo ### Response:
                echo """
            ) > "Modelfile.auto"
            ollama create jarvis-trained-model -f Modelfile.auto
            del /f /q Modelfile.auto >nul 2>&1
        )
    )
) else (
    echo [OLLAMA NOTICE]: Ollama CLI not detected. Local GUI automation active.
)

:: 5. Launch JARVIS AI Workstation directly via .venv python
echo.
echo [LAUNCH]: Starting JARVIS AI Workstation...
echo =======================================================
echo.
.\.venv\Scripts\python.exe main.py

if errorlevel 1 goto RUN_ERROR

pause
exit /b 0

:DEPS_WARN
echo [WARNING]: Package installation completed with warnings. Attempting launch...
goto VERIFY_DEPS

:RUN_ERROR
echo.
echo [JARVIS System Notice]: Process exited with code %ERRORLEVEL%.
pause
exit /b %ERRORLEVEL%

:NO_PYTHON
echo.
echo [ERROR]: Python is not installed or not added to system PATH!
echo Please install Python 3.10, 3.11, or 3.12 from https://www.python.org/
echo IMPORTANT: Make sure to check "Add Python.exe to PATH" during setup.
echo.
pause
exit /b 1

:VENV_FAIL
echo.
echo [ERROR]: Failed to create virtual environment (.venv)!
echo Please check folder permissions and try again.
echo.
pause
exit /b 1
