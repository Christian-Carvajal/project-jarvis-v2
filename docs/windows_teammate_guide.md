# Windows Teammate & Troubleshooting Guide

> **Target Audience:** Windows Users & Teammates (John Miko Sarsalijo)  
> **Project:** Project JARVIS v2  

---

## 🛠️ Common Windows Setup Steps & Solutions

### 1. PowerShell Script Execution Policy
If PowerShell blocks virtual environment activation (`.\.venv\Scripts\activate`), run:
```powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned -Force
```

---

### 2. Ollama Daemon Setup & Verification
Ensure Ollama is running and the `qwen2.5:1.5b` model is downloaded:
```powershell
# 1. Check if Ollama is running
curl -s http://localhost:11434/api/tags

# 2. Pull Qwen 2.5:1.5B
ollama pull qwen2.5:1.5b

# 3. Test simple query
ollama run qwen2.5:1.5b "Hello"
```

---

### 3. Microphone Device Selection & PyAudio Fix
Project JARVIS v2 uses native `sounddevice` to capture audio, which completely bypasses the legacy PyAudio compilation requirement on Windows.

If your system has multiple microphones (e.g. built-in mic, headset, webcam):
1. `src/voice_pipeline.py` automatically picks the physical microphone array with the highest priority.
2. You can check the selected microphone in the startup console:
   ```text
   [STT Mic Selection]: Selected hardware microphone 'Microphone Array (Intel® Smart Sound Technology)' (Index 2).
   ```
3. To mute or unmute the microphone at any time, click the **🎙️ Mic Toggle** button in the dashboard.

---

### 4. Running Verification
Always run `test_system_e2e.py` before presenting or committing changes:
```powershell
.\.venv\Scripts\activate
python test_system_e2e.py
```
All 18 tests should pass with `100%`.
