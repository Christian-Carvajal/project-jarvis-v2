# Project Handover & AI Teammate Continuity Guide

> **Target Audience:** John Miko Sarsalijo & his Antigravity AI Assistant  
> **Project Name:** Project JARVIS v2 (Apex Smart Home & Universal PC Automation Workstation)  
> **Course:** BSCS 3112 - Artificial Intelligence (UPHSD Molino Campus)  
> **Faculty Advisor / Professor:** Prof. Roberto L. Malitao  
> **Current Status:** 100% Implemented, 18/18 E2E Automated Tests Passed, Submission Ready  

---

## 🎯 Executive Context for Incoming AI / Antigravity Instance

If you are an Antigravity AI assistant taking over this codebase for John Miko Sarsalijo, **read this section first**:

This codebase represents the completed, fully refactored **Project JARVIS v2**. It satisfies all academic deliverables and guidelines set by **Prof. Roberto L. Malitao**.

### ⚠️ Critical Professor Directives (Must NEVER be violated):
1. **NO Hardcoded Triggers or Static Command Dictionaries:**
   - The system is **100% Agentic**.
   - Do NOT add rigid regex patterns (`re.match`), keyword dictionaries, or rule-based string matching to parse user intent.
   - All intent understanding, device targeting, parameter extraction, and cross-domain action generation are performed dynamically by local **Qwen 3.5 (2B Parameter Base / LoRA Fine-Tuned)** in structured JSON format (`format="json"`) validated against Pydantic v2 schemas (`DeviceAction`, `AssistantIntentResponse`).
2. **Two-Turn Alternating Conversational State Machine:**
   - **Turn 1 (`STATE_STANDBY_WAKE_WORD`):** Passive acoustic gate listening strictly for `"Hey Jarvis"` / `"Jarvis"`. All non-wake words (like `"hello"`, `"good morning"`) are discarded. When wake word is detected, JARVIS speaks: *"At your service, sir. What can I do for you?"* and immediately transitions to `STATE_ACTIVE_COMMAND`.
   - **Turn 2 (`STATE_ACTIVE_COMMAND`):** Listens directly for the raw user command **WITHOUT requiring the wake word**. Sends prompt to Qwen 3.5 (2B), dispatches actions to Smart Home + Dynamic PC engines, speaks confirmation, and automatically resets to `STATE_STANDBY_WAKE_WORD`.
   - **Timeout Protection:** If the user stays silent for 6 seconds while in `STATE_ACTIVE_COMMAND`, JARVIS speaks *"Returning to standby, sir."* and resets to `STATE_STANDBY_WAKE_WORD`.
3. **Preserve Mandatory Deliverables:**
   - `main.py`: Root entry point invoking `src.main.main()`.
   - `src/main.py`: Two-Turn State Machine Coordinator.
   - `src/voice_pipeline.py`: SoundDevice capture + Silero VAD + Faster-Whisper + British TTS Worker with Emergency HALT.
   - `src/ai_engine.py`: 100% Pure Agentic AI Engine (Ollama Qwen 3.5:2b) + Dynamic PC Desktop Automation Engine.
   - `src/home_simulator.py`: Apex Smart Home State Machine & Dark Cyberpunk GUI Dashboard.
   - `assistant_execution.log`: Structured ISO 8601 execution logs.
   - `test_system_e2e.py`: Automated 18/18 E2E verification suite.
   - `package_submission.py`: Automated zip packager.

---

## 📁 Repository Directory Structure

```
project-jarvis-v2/
├── src/
│   ├── __init__.py
│   ├── main.py              # Central Two-Turn State Machine Coordinator & Worker
│   ├── ai_engine.py         # Pure Agentic Qwen 2.5 LLM Engine & Dynamic PC Automation
│   ├── voice_pipeline.py    # SoundDevice STT + Silero VAD + Whisper + Edge-TTS/Pyttsx3 Worker
│   └── home_simulator.py    # Apex Smart Home State Machine & Modern Cyberpunk GUI Dashboard
├── docs/
│   ├── README.md            # Documentation Directory Index
│   ├── handover.md          # This Handover Document
│   ├── rules.md             # Strict Antigravity AI Directives
│   ├── setup.md             # Environment & Ollama Setup Guide
│   ├── project_plan_and_status.md # Milestones & Verification Status
│   ├── completed_task.md    # Complete Task Execution Log
│   ├── demo_guide.md        # Academic Defense Presentation Script & Q&A
│   ├── skills.md            # Tech Stack Matrix
│   ├── changelog.md         # Release Notes ([2.0.0])
│   └── windows_teammate_guide.md # Windows & PowerShell Troubleshooting Guide
├── assistant_execution.log  # Structured ISO 8601 Execution & Performance Log
├── test_system_e2e.py       # Automated 18/18 E2E Verification Test Suite
├── package_submission.py    # Automated Final Submission Packager
├── Prelim_Project_Report.pdf# Academic Defense Report & System Architecture
├── requirements.txt         # Production Dependencies
└── README.md                # Root Project Overview
```

---

## ⚙️ Module Responsibilities & Key Classes

### 1. `src/ai_engine.py`
- `DeviceAction(domain, device_or_target, action, value)`: Pydantic v2 schema representing an agentic action.
- `AssistantIntentResponse(spoken_response, actions, raw_prompt, interpreted_intent)`: Pydantic v2 schema for multi-action agentic plans.
- `PCAutomationEngine`:
  - `launch_app(app_name)`: Discovers executables via `shutil.which` and Start Menu registry scanning without hardcoded machine paths.
  - `close_app(app_name)`: Gracefully terminates processes.
  - `execute_pc_action(target, action, value)`: Dispatches web searches (YouTube, Spotify, Google), system volume/mute controls, media play/pause, workstation lock (`rundll32.exe user32.dll,LockWorkStation`), and application launches.
- `AIEngine`:
  - `parse_command(prompt: str) -> AssistantIntentResponse`: Direct HTTP REST request to local Ollama (`qwen3.5:2b`) with strict JSON schema formatting.

### 2. `src/voice_pipeline.py`
- `TTSEngine`: Dedicated background worker thread with `queue.Queue` for non-blocking British TTS synthesis (Edge-TTS / Pyttsx3 SAPI5 fallback) and emergency `halt()` support.
- `VoicePipeline`:
  - `find_best_hardware_microphone()`: Automatically discovers active physical hardware microphone arrays (skipping disconnected virtual webcams).
  - `record_audio_with_vad()`: SoundDevice recording with Silero VAD frame-by-frame streaming (auto-slices after ~350ms trailing silence) and audio gain normalization.
  - `listen_for_wake_word() -> Tuple[bool, str]`: Standby mode wake word gating.
  - `listen_raw_command(timeout: float = 6.0) -> str`: Active mode raw command capture without wake word filter.

### 3. `src/home_simulator.py`
- `SmartHomeStateMachine`: State machine tracking 8+ smart devices (living room, kitchen, bedroom lights, thermostat, door lock, security alarm, fan, window blinds, entertainment unit).
- `ModernHomeDashboard`: Tkinter-based Dark Cyberpunk GUI Dashboard with live device status cards, microphone toggle button, emergency HALT button, latency telemetry, model selector, and real-time console log.

### 4. `src/main.py`
- `AssistantState(Enum)`: `STANDBY_WAKE_WORD = 1`, `ACTIVE_COMMAND = 2`.
- `JarvisVirtualAssistant`: Central coordinator running the background state machine thread, connecting voice pipeline, agentic AI engine, smart home state machine, dynamic PC automation engine, and GUI dashboard.

---

## 🧪 Verification & Launch Instructions

### 1. Run the Assistant
```powershell
.\.venv\Scripts\activate
python main.py
```

### 2. Run the E2E Verification Suite (18/18 Tests)
```powershell
python test_system_e2e.py
```

### 3. Build Final Submission Zip
```powershell
python package_submission.py Carvajal Sarsalijo
```

---

## 👥 Division of Responsibilities

* **Christian Ezekiel L. Carvajal (AI Engine & Automation Lead):**
  - Architecture and implementation of `AIEngine` (100% Agentic Qwen 3.5 (2B) via Ollama JSON format).
  - Two-Turn Alternating Conversational State Machine in `src/main.py`.
  - Dynamic Universal PC Desktop Automation Engine (`PCAutomationEngine`).
  - Automated 18/18 E2E verification test suite (`test_system_e2e.py`).

* **John Miko Sarsalijo (Voice Pipeline & UI/UX Lead):**
  - High-precision voice capture pipeline (`sounddevice` + Silero VAD + Faster-Whisper + Gain Normalization).
  - Dedicated background British TTS Worker with Emergency HALT override.
  - Dark Cyberpunk GUI Dashboard (`ModernHomeDashboard`).
  - Presentation preparation and academic defense coordination.
