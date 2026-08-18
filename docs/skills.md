# Technology Stack & Skills Matrix

> **Project:** Project JARVIS v2  
> **Course:** BSCS 3112 - Artificial Intelligence  

---

## 🛠️ Core Technology Components

| Component | Library / Tool | Purpose |
| :--- | :--- | :--- |
| **Local LLM Engine** | Ollama (`qwen2.5:1.5b`) | 100% agentic natural language reasoning, intent extraction, tool selection |
| **Schema Validation** | Pydantic v2 | Strict JSON schema constraints for multi-action execution plans |
| **Speech-to-Text (STT)** | OpenAI Faster-Whisper (`tiny` / `base`) | Local offline voice transcription with initial prompt conditioning |
| **Voice Activity Detection** | Silero VAD | Frame-by-frame speech segmentation and 350ms trailing silence auto-slicing |
| **Audio Capture** | SoundDevice + NumPy | Native float32 audio capture and int16 PCM conversion (no PyAudio errors) |
| **Text-to-Speech (TTS)** | Edge-TTS / Pyttsx3 (SAPI5) | British JARVIS voice synthesis in dedicated background worker with emergency HALT |
| **GUI Dashboard** | Tkinter / CustomTkinter | Dark Cyberpunk HUD, device telemetry, mic toggle, emergency halt, live console |
| **Desktop Automation** | `subprocess`, `webbrowser`, `shutil`, `psutil`, `pyautogui`, `win32api` | Dynamic cross-PC application launching/killing, web search, volume/media control, workstation locking |
| **State Machine** | Python `Enum` + `threading` | Two-Turn Alternating Conversational State Machine (`STANDBY` <-> `ACTIVE`) |
| **Verification Suite** | `test_system_e2e.py` | Automated 18/18 end-to-end verification tests |
| **Audit Logging** | Python `logging` | ISO 8601 structured logs in `assistant_execution.log` |
