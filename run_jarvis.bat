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

echo [2/3] Upgrading pip package installer...
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
:: 3. Verify PyQt6 inside .venv
.\.venv\Scripts\python.exe -c "import PyQt6" >nul 2>&1
if errorlevel 1 (
    echo [NOTICE]: Installing missing dependencies inside .venv...
    .\.venv\Scripts\python.exe -m pip install -r requirements.txt
)

:: 4. Check Ollama background service status & auto-launch
ollama --version >nul 2>&1
if not errorlevel 1 (
    curl -s --connect-timeout 1 http://localhost:11434/api/tags >nul 2>&1
    if errorlevel 1 (
        echo [OLLAMA CHECK]: Starting background Ollama AI service...
        start /b "" ollama serve >nul 2>&1
    ) else (
        echo [OLLAMA CHECK]: Ollama AI service online on http://localhost:11434.
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
