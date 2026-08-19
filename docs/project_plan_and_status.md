# Project Plan & Status

> **Overall Project Status:** `COMPLETED / 18 OF 18 TESTS PASSED (100%) / DEFENSE READY`  
> **Course:** BSCS 3112 - Artificial Intelligence  
> **Instructor:** Prof. Roberto L. Malitao  

---

## 🏗️ System Architecture Pipeline

```
[User Microphone Input]
           |
[Native SoundDevice + Silero VAD Frame Streaming (350ms silence auto-slice)]
           |
[Faster-Whisper STT (Domain-Prompt Conditioned)]
           |
[Two-Turn State Machine (STANDBY_WAKE_WORD <-> ACTIVE_COMMAND)]
           |
[100% Agentic Local AI Engine (Ollama Qwen 3.5:2b JSON Mode)]
           |
[Pydantic v2 Schema Validation: AssistantIntentResponse]
          /                                       \
[Smart Home State Machine]           [Universal PC Automation Engine]
(Lighting, Climate, Locks, Blinds)    (App Launch/Kill, Web Search, System Controls)
          \                                       /
           +-------------------+-----------------+
                               |
            [Dedicated British TTS Worker Thread (Edge-TTS / Pyttsx3)]
                               |
            [Modern Cyberpunk GUI Dashboard & Live Telemetry]
                               |
            [ISO 8601 Audit Logging: assistant_execution.log]
```

---

## 📋 Milestone & Phase Verification Tracker

- [x] **Phase 1: Project Scaffolding & Rubric Alignment** — Architecture, `src/` modular structure, and isolated virtual environment.
- [x] **Phase 2: High-Precision Voice Pipeline (`src/voice_pipeline.py`)** — Native `sounddevice` capture, hardware microphone indexing, Silero VAD auto-slicing, Whisper STT, and dedicated British TTS worker with Emergency HALT.
- [x] **Phase 3: 100% Agentic AI Engine (`src/ai_engine.py`)** — Local Qwen 3.5 (2B) inference via Ollama JSON format, strict Pydantic v2 validation (`DeviceAction`, `AssistantIntentResponse`), zero hardcoded regex/rules.
- [x] **Phase 4: Dynamic PC Desktop Automation (`src/ai_engine.py`)** — Cross-PC application launcher/terminator, deep web navigation (YouTube, Spotify, Google), volume/media control, workstation locking.
- [x] **Phase 5: Apex Smart Home Simulator & Dark Cyberpunk GUI (`src/home_simulator.py`)** — Multi-device state machine, live device cards, microphone toggle, emergency HALT button, real-time latency tracker, and console stream.
- [x] **Phase 6: Two-Turn Conversational State Machine (`src/main.py`)** — Standby wake-word phase $\leftrightarrow$ Active raw command phase with 6-second timeout fallback.
- [x] **Phase 7: End-to-End Automated Verification (`test_system_e2e.py`)** — 18/18 tests passed (100% success rate).
- [x] **Phase 8: Packaging & Academic Deliverables** — `package_submission.py` zip generation, `assistant_execution.log`, and `Prelim_Project_Report.pdf`.
