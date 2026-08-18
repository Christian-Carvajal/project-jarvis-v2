# Project Setup & Installation Guide

> **Project:** Project JARVIS v2  
> **Supported OS:** Windows 10 / 11 (64-bit)  
> **Python Version:** Python 3.10 – 3.14  

---

## 🛠️ Step-by-Step Environment Setup

### 1. Prerequisites Installation
1. **Python 3.10 – 3.14** from [python.org](https://www.python.org/downloads/)  
   ⚠️ **CRITICAL:** Check the box **"Add Python to PATH"** during installation!
2. **Ollama AI Runtime** from [ollama.com/download](https://ollama.com/download)  
   After installation, open a terminal and pull the Qwen 2.5:1.5B model:
   ```powershell
   ollama pull qwen2.5:1.5b
   ```

---

### 2. Virtual Environment & Dependencies Setup

Open PowerShell in the project root directory:

```powershell
# 1. Create isolated Python virtual environment
python -m venv .venv

# 2. Activate virtual environment
.\.venv\Scripts\activate

# 3. Upgrade pip and install all production dependencies
python -m pip install --upgrade pip
pip install -r requirements.txt
```

---

### 3. Verify System Installation

Run the automated 18/18 E2E verification test suite to ensure all subsystems (Acoustic Gating, Ollama Qwen 2.5, Smart Home State Machine, Dynamic PC Automation) are operating at 100%:

```powershell
python test_system_e2e.py
```

Expected output:
```text
===========================================================================
  OVERALL VERIFICATION RESULTS: 18/18 TESTS PASSED (100%)
  AVERAGE OFFLINE NLP LATENCY:  ~6.6 s
  LOGGING RECORD PERSISTED TO:  assistant_execution.log
===========================================================================
```

---

### 4. Running Project JARVIS

```powershell
python main.py
```

---

## 🔧 Hardware Microphone Troubleshooting

If running on a laptop with multiple microphones or virtual webcams (Iriun/Camo):
- JARVIS automatically scans physical audio devices and binds to the active hardware microphone array.
- You can toggle the microphone on/off at runtime using the **🎙️ Mic Toggle** button in the GUI dashboard.
