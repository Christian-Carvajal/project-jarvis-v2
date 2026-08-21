# APEX HOME AUTOMATIONS — ON-PREMISE AI VIRTUAL ASSISTANT (PROJECT JARVIS)

| **Project Metadata** | **Details** |
| :--- | :--- |
| **Course & Lesson** | Artificial Intelligence - Lab \| Lesson 3 – Prelim Mini-Project |
| **Exam Title** | **PRELIM MINI PROJECT EXAM: AI-Powered Home Virtual Assistant** |
| **Faculty Lead / Instructor** | **Prof. Rob Malitao** |
| **Due Date** | **August 21, 2026** |
| **Execution Environment** | **100% Software-Simulated Desktop Execution (Zero-Hardware)** |
| **Student Engineers** | **JOHN MIKO SARSALIJO** (Lead GUI & Simulator Architect)<br>**CHRISTIAN EZEKIEL CARVAJAL** (Lead AI & Systems Architect) |

---

## 📌 1. Project Overview & Business Scenario

**Apex Home Automations**, a consumer technology enterprise, is developing next-generation smart home hub software. Addressing consumer privacy concerns regarding always-on cloud listening devices (such as Amazon Alexa or Google Home), this prototype demonstrates an **on-premise, privacy-focused home virtual assistant (PROJECT JARVIS)** that operates **100% offline** on a desktop workstation.

### Core Architecture Highlights
1. **100% Pure Local AI Reasoning (Zero Hardcoded Rules / Regex)**:
   All natural language queries are parsed exclusively by the local fine-tuned Ollama model (`jarvis-trained-model` / Qwen 2.5/3.5:2B). The AI dynamically generates native `<think>...</think>` Chain-of-Thought reasoning and emits structured Pydantic v2 JSON action plans. Zero regular expressions or keyword dictionaries dictate system decisions.
2. **Two-Turn Alternating Conversational State Machine**:
   - **Phase 1 (Standby Mode)**: Listens passively for the wake phrase (`"Jarvis"`, `"Hey Jarvis"`) or direct wake-and-command phrases.
   - **Phase 2 (Active Command Mode)**: Open-mic command capture window with automatic silence detection and timeout fallback.
3. **Simulated Smart Home Dashboard & OS Desktop Automation**:
   - **Smart Home Virtual State Machine**: Interactive visualization of multi-room lighting, climate thermostat with ambient physics, security deadbolts, motorized blinds, ceiling fans, entertainment units, and alarm systems.
   - **Universal PC Desktop Automation**: Dynamically launches desktop applications, performs deep browser searches (YouTube, Google, Spotify), manages running processes, adjusts system volume, and locks the Windows workstation.
4. **Offline Voice Processing Pipeline**:
   High-speed Voice Activity Detection (VAD) audio buffering coupled with offline Text-to-Speech (TTS) synthesis and an emergency **HALT** button override.

---

## 📁 2. File and Directory Structure

```text
AI_PrelimExam_Group_Carvajal_Sarsalijo / Project-Jarvis-main/
│
├── Execution Log/
│   └── assistant_execution.log        # Auto-generated ISO 8601 audit record (transcriptions, JSON, latency)
│
├── Project Documentation/
│   └── Prelim_Project_Report_Final.pdf # Mandated 3-page academic report with architecture diagrams & metrics
│
├── Source Code/                       # Mandated /src and project implementation codebase
│   ├── benchmarks/                    # LLM performance benchmarks and comparison logs
│   ├── config/                        # Configuration settings and personality profiles
│   ├── core/                          # Low-level system adapters and helper engines
│   │   ├── action_engine.py           # PC automation driver execution
│   │   ├── app_resolver.py            # Windows Start Menu & system process resolution
│   │   ├── macro_engine.py            # Multi-action desktop macro scheduler
│   │   ├── stt_engine.py              # Audio capture and speech-to-text adapter
│   │   └── tts_engine.py              # Speech synthesis queue management
│   ├── datasets/                      # Fine-tuning dataset JSONL records for local LLM
│   ├── reports/                       # Generated report assets and build artifacts
│   ├── scripts/                       # Automated submission packaging and PDF report generation
│   │   ├── generate_report.py         # Automated ReportLab PDF generator
│   │   └── package_submission.py      # Final zip deliverable packager
│   ├── src/                           # Primary application modules
│   │   ├── __init__.py                # Package initializer
│   │   ├── ai_engine.py               # Pure Ollama LLM Reasoning Engine & Pydantic Schema Validator
│   │   ├── home_simulator.py          # Virtual Smart Home Device State Machine & Modern HUD
│   │   ├── main.py                    # Dual-Phase State Machine Controller & Event Coordinator
│   │   └── voice_pipeline.py          # Acoustic Wake-Word Gating, VAD & Audio Stream Controller
│   ├── tests/                         # Automated test verification suites
│   │   ├── test_pc_navigation.py      # PC desktop automation test suite (14/14 tests)
│   │   └── test_system_e2e.py         # End-to-end system verification suite (18/18 tests)
│   ├── ui/                            # Cyberpunk Stark HUD window components
│   ├── Modelfile                      # Ollama model definition and system instructions
│   ├── jarvis_memory.db               # Local SQLite database for persistent memory
│   ├── main.py                        # Root launcher redirecting to src/main.py
│   └── requirements.txt               # Complete Python runtime package dependencies
│
├── requirements.sh                    # Shell setup and environment provisioning script
├── run_jarvis.bat                     # Windows batch one-click auto-setup & launch script
├── run_jarvis.ps1                     # PowerShell one-click setup & execution script
├── run_jarvis.vbs                     # Silent windowless background launcher
└── README.md                          # Root academic specification and user guide
```

---

## ⚡ 3. Detailed Component & Function Breakdown

### A. `Source Code/src/ai_engine.py` (AI Intent Extraction & JSON Parsing)
- **`AIEngine.parse_command(prompt)`**:
  Constructs the inference payload and sends the user query to the local Ollama API (`http://127.0.0.1:11434/api/chat`) running `jarvis-trained-model`.
- **`AIEngine._extract_reasoning_and_json(raw_content, thinking_content)`**:
  Extracts the raw `<think>...</think>` Chain-of-Thought reasoning tokens and cleanly isolates the JSON payload without regex interception.
- **`AssistantIntentResponse` (Pydantic v2 Model)**:
  Validates the returned JSON against strict schema definitions:
  - `spoken_response`: Human-readable dialogue spoken by JARVIS.
  - `actions`: List of `DeviceAction` objects with `domain`, `device_or_target`, `action`, and `value`.
  - `reasoning`: Chain-of-Thought explanation generated by the model.
  - `interpreted_intent`: High-level intent category (`agentic_action_plan`, `conversational_dialogue`, `device_status_query`).
- **`PCAutomationEngine`**:
  Executes OS-level automation including `open_app`, `close_app`, `open_website`, `play_music` (Spotify/YouTube), `media_control`, `volume_control`, and `lock_pc`.

### B. `Source Code/src/home_simulator.py` (Simulated Smart Home Dashboard)
- **`SmartHomeStateMachine`**:
  Maintains the authoritative state of 9 simulated smart devices:
  1. `living_room_light` (SmartLight - On/Off, Brightness 0-100%)
  2. `kitchen_light` (SmartLight - On/Off, Brightness 0-100%)
  3. `bedroom_light` (SmartLight - On/Off, Brightness 0-100%)
  4. `thermostat` (SmartThermostat - Target Temp 16-30°C, Ambient Simulation)
  5. `front_door_lock` (SmartLock - Locked/Unlocked)
  6. `ceiling_fan` (SmartFan - Off/Low/Medium/High)
  7. `window_blinds` (SmartBlinds - Open/Closed)
  8. `entertainment_unit` (EntertainmentUnit - Off/Active/Streaming)
  9. `security_alarm` (SecurityAlarm - Disarmed/Armed/Triggered)
- **`ModernHomeDashboard` (GUI)**:
  Dark Cyberpunk visual interface displaying live device status cards, interactive toggle buttons, console stream, latency gauge, model selector, microphone mute toggle, and emergency **HALT** button.

### C. `Source Code/src/voice_pipeline.py` (Voice & Speech Processing Pipeline)
- **`VoicePipeline.listen_for_wake_word()`**:
  Continuous acoustic listening stream using hardware microphone indexing and energy thresholding to detect wake words (`"Jarvis"`, `"Hey Jarvis"`) and compound commands.
- **`VoicePipeline.listen_raw_command(timeout=10.0)`**:
  Captures follow-up speech commands in active mode with Silero VAD silence truncation.
- **`VoicePipeline.speak(text, callback)`**:
  Asynchronous offline speech synthesis using `pyttsx3` with queue management and immediate interrupt support.

### D. `Source Code/src/main.py` (Dual-Phase State Coordinator)
- **`JarvisVirtualAssistant`**:
  Central controller executing the Two-Turn state machine, coordinating the voice listener thread, passing transcribed text to the AI engine, dispatching action lists to the simulator and desktop engines, updating HUD telemetry, and writing structured ISO 8601 logs to `Execution Log/assistant_execution.log`.

---

## 📋 4. Rubric & Evaluation Standards

| Evaluation Criteria | Weight | Required Standard | Project Implementation |
| :--- | :---: | :--- | :--- |
| **Voice & Speech Processing Pipeline** | **25%** | Audio capture, STT, and TTS function seamlessly with minimal latency (<2s) and clear audio feedback. | Native SoundDevice capture, high-speed speech-to-text, offline British JARVIS TTS synthesis, and 2-stage acoustic wake-word gating. |
| **AI Intent Extraction & JSON Parsing** | **30%** | Local Qwen model accurately extracts intent and parameters from ambiguous commands; valid JSON matching schema. | Pure Ollama LLM reasoning (`jarvis-trained-model`) with native `<think>` CoT extraction, Pydantic v2 validation, and dynamic parameter resolution. |
| **Simulated Smart-Home GUI** | **20%** | Visually dynamic UI (Tkinter/Pygame) clearly reflecting real-time state changes based on AI output. | Modern Cyberpunk HUD with real-time card toggles, animated status indicators, console log feed, latency metrics, and hardware override buttons. |
| **Code Architecture & Documentation** | **15%** | Modular OOP design (`main.py`, `ai_engine.py`, `home_simulator.py`, `voice_pipeline.py`), PEP-8 compliance, robust error handling. | Decoupled, modular architecture adhering to PEP-8 standards with comprehensive docstrings and clean separation of concerns. |
| **Report & Live Demonstration** | **10%** | Complete PDF report with architecture diagram, task division matrix, and live demo execution. | 3-page academic report with architecture diagrams, peak resource benchmarks (CPU/RAM/VRAM), task division matrix, and automated test suite. |

---

## 🚀 5. Quickstart & Verification Guide

### Step 1: Launch the Assistant
- **Windows (Batch)**: Double-click `run_jarvis.bat`.
- **Windows (PowerShell)**: Execute `.\run_jarvis.ps1`.
- **Bash / Git Bash / Linux / WSL**: Run `./requirements.sh`.

The launcher automatically provisions the Python virtual environment, installs dependencies, verifies Ollama, and opens the JARVIS Cyberpunk HUD.

### Step 2: Test via Voice or Text
- **Voice**: Speak *"Hey Jarvis, turn on the living room light and set the temperature to 24 degrees."*
- **Text Command Bar**: Type *"It is freezing and dark in here"* or *"Open YouTube and search for classical music"*.

### Step 3: Run Automated Verification Test Suites
```powershell
# Run the complete System E2E Test Suite
& ".\Source Code\.venv\Scripts\python.exe" "Source Code\tests\test_system_e2e.py"

# Run the PC Navigation Test Suite
& ".\Source Code\.venv\Scripts\python.exe" "Source Code\tests\test_pc_navigation.py"
```

### Step 4: Inspect Execution Audit Logs
Open `Execution Log/assistant_execution.log` to inspect the complete ISO 8601 audit records containing timestamps, transcribed text, LLM JSON payloads, state transitions, and inference latency.

---

## 👥 6. Academic Project Team & Task Division Matrix

```text
+-------------------------------------------------------------------------------+
|                      APEX HOME AUTOMATIONS — PROJECT JARVIS                   |
+-----------------------------------+-------------------------------------------+
| Student Engineer                  | Primary Responsibilities & Modules        |
+-----------------------------------+-------------------------------------------+
| CHRISTIAN EZEKIEL CARVAJAL        | • Pure Agentic AI Engine (ai_engine.py)   |
| (Lead AI & Systems Architect)     | • Ollama LoRA Fine-Tuning & Prompt Tuning |
|                                   | • Universal PC Automation Engine          |
|                                   | • System Architecture & End-to-End Tests  |
+-----------------------------------+-------------------------------------------+
| JOHN MIKO SARSALIJO               | • Modern Cyberpunk HUD (home_simulator.py)|
| (Lead GUI & Simulator Architect)  | • Smart Home Device State Machine         |
|                                   | • Voice Pipeline STT/TTS (voice_pipeline) |
|                                   | • Academic Documentation & UI Assets      |
+-----------------------------------+-------------------------------------------+
| Faculty Lead / Instructor: Prof. Rob Malitao (August 21, 2026)                |
+-------------------------------------------------------------------------------+
```
