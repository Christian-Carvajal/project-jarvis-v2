@echo off
TITLE JARVIS — Environment & Dependency Installer
echo ======================================================
echo   PROJECT JARVIS — ENVIRONMENT & DEPENDENCY SETUP
echo ======================================================

IF NOT EXIST ".venv" (
    echo [INFO] Creating Python virtual environment (.venv)...
    python -m venv .venv
)

echo [INFO] Activating virtual environment...
call .venv\Scripts\activate.bat

echo [INFO] Bootstrapping pip if needed...
python -m ensurepip --default-pip >nul 2>&1

echo [INFO] Upgrading pip and setuptools...
python -m pip install --upgrade pip setuptools

echo [INFO] Installing requirements from requirements.txt...
python -m pip install -r requirements.txt

echo.
echo ======================================================
echo   DEPENDENCIES INSTALLED SUCCESSFULLY!
echo   Launch JARVIS using: run_jarvis.bat
echo ======================================================
pause
