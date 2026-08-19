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
- [x] **Phase 9: Baseline Model Benchmark Evaluation (`benchmark_baseline.py`)** — Standardized 15-case evaluation for base `qwen3.5:2b` establishing baseline metrics (100% JSON validity, 100% action accuracy, 66.7% chit-chat null accuracy, 10.11s latency, 47.7 tok/s) documented in [`docs/baseline_benchmark_results.md`](baseline_benchmark_results.md) and [`benchmarks/baseline_qwen3.5_2b_results.json`](../benchmarks/baseline_qwen3.5_2b_results.json).
- [x] **Phase 10: Fine-Tuned Model Integration (`jarvis-trained-model`) & Comparative Evaluation (`benchmark_compare.py`)** — Standardized active model to `jarvis-trained-model`, ran side-by-side benchmark verifying resolution of `[CHAT-02]` flaw (66.7% -> 100%), 38.5% latency reduction (6.22s), 56.8% tok/s increase (74.8 tok/s), and recompiled academic `Prelim_Project_Report.pdf` (strict 3 pages).


