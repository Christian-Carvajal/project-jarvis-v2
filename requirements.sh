#!/usr/bin/env bash
# ==============================================================================
# APEX HOME AUTOMATIONS ? PROJECT JARVIS
# Automated Dependency & Environment Provisioning Script
# ==============================================================================

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "======================================================="
echo "       PROJECT JARVIS ? ENVIRONMENT SETUP SCRIPT       "
echo "======================================================="
echo "Working Directory: $SCRIPT_DIR"

# 1. Detect Python 3 runtime
PYTHON_BIN=""
for cmd in python3 python py; do
    if command -v $cmd >/dev/null 2>&1; then
        PYTHON_BIN="$cmd"
        break
    fi
done

if [ -z "$PYTHON_BIN" ]; then
    echo "[ERROR]: Python 3 runtime not found in PATH."
    echo "Please install Python 3.10+ from https://www.python.org/"
    exit 1
fi

echo "[SYSTEM CHECK]: Found Python runtime ($($PYTHON_BIN --version))."

# 2. Determine VENV location
VENV_DIR=""
REQ_FILE=""

if [ -d "$SCRIPT_DIR/Source Code" ]; then
    VENV_DIR="$SCRIPT_DIR/Source Code/.venv"
    REQ_FILE="$SCRIPT_DIR/Source Code/requirements.txt"
else
    VENV_DIR="$SCRIPT_DIR/.venv"
    REQ_FILE="$SCRIPT_DIR/requirements.txt"
fi

# 3. Create Virtual Environment if not present
if [ ! -d "$VENV_DIR" ]; then
    echo "[1/3] Creating virtual environment at $VENV_DIR..."
    "$PYTHON_BIN" -m venv "$VENV_DIR"
else
    echo "[1/3] Existing virtual environment detected."
fi

# Determine Python in VENV (Windows vs Unix)
if [ -f "$VENV_DIR/Scripts/python.exe" ]; then
    VENV_PY="$VENV_DIR/Scripts/python.exe"
elif [ -f "$VENV_DIR/bin/python" ]; then
    VENV_PY="$VENV_DIR/bin/python"
else
    VENV_PY="$PYTHON_BIN"
fi

# 4. Upgrade pip and install requirements
echo "[2/3] Upgrading pip..."
"$VENV_PY" -m pip install --upgrade pip --quiet 2>/dev/null || true

if [ -f "$REQ_FILE" ]; then
    echo "[3/3] Installing dependencies from $REQ_FILE..."
    "$VENV_PY" -m pip install -r "$REQ_FILE"
else
    echo "[WARNING]: requirements.txt not found at $REQ_FILE."
fi

# 5. Check Ollama daemon
echo ""
echo "[OLLAMA CHECK]: Verifying local Ollama service..."
if command -v ollama >/dev/null 2>&1; then
    if curl -s --connect-timeout 2 http://127.0.0.1:11434/api/tags >/dev/null 2>&1; then
        echo "[OLLAMA]: Local Ollama daemon is active and responsive on http://127.0.0.1:11434."
    else
        echo "[OLLAMA NOTICE]: Ollama service not running. Starting background daemon..."
        ollama serve >/dev/null 2>&1 &
        sleep 2
    fi
else
    echo "[OLLAMA NOTICE]: Ollama CLI not detected in PATH. Ensure Ollama is installed."
fi

echo ""
echo "======================================================="
echo "  [SUCCESS] All dependencies provisioned smoothly!"
echo "  Launch with: ./run_jarvis.bat or ./run_jarvis.ps1"
echo "======================================================="
