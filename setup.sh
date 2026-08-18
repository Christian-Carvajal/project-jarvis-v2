#!/usr/bin/env bash
# PROJECT JARVIS — Setup & Dependency Installer Script

echo "======================================================"
echo "  PROJECT JARVIS — ENVIRONMENT & DEPENDENCY SETUP     "
echo "======================================================"

# 1. Create virtual environment if missing
if [ ! -d ".venv" ]; then
    echo "[INFO] Creating Python virtual environment (.venv)..."
    python3 -m venv .venv || python -m venv .venv
fi

# 2. Activate virtual environment
if [ -f ".venv/bin/activate" ]; then
    source .venv/bin/activate
elif [ -f ".venv/Scripts/activate" ]; then
    source .venv/Scripts/activate
fi

# 3. Upgrade pip & setuptools
echo "[INFO] Upgrading pip and setuptools..."
pip install --upgrade pip setuptools

# 4. Install all requirements (including pywin32, onnxruntime, silero-vad, faster-whisper)
echo "[INFO] Installing requirements from requirements.txt..."
pip install -r requirements.txt

echo ""
echo "======================================================"
echo "  DEPENDENCIES INSTALLED SUCCESSFULLY!                "
echo "  To launch JARVIS:                                  "
echo "    python main.py                                   "
echo "======================================================"
