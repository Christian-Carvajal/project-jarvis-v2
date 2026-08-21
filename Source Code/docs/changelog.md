# Changelog & Version History

All notable changes to **Project JARVIS** are documented in this file.

---

## [2.0.0] - 2026-08-18 (Project JARVIS v2 - Production & Defense Release)

### 🚀 Major Architectural Refactoring
- **100% Pure Agentic AI Reasoning Engine:**
  - Removed all hardcoded regex matchers (`re.match`), keyword dictionaries, and rule-based dispatchers.
  - Implemented dynamic reasoning via local **Qwen 3.5 (2B Parameter Base / LoRA Fine-Tuned)** in strict JSON schema format (`format="json"`).
  - Built strict Pydantic v2 schemas (`DeviceAction` and `AssistantIntentResponse`).
- **Two-Turn Alternating Conversational State Machine:**
  - Introduced `AssistantState` enum (`STANDBY_WAKE_WORD = 1` and `ACTIVE_COMMAND = 2`).
  - **Turn 1:** Passive acoustic gate listening strictly for `"Hey Jarvis"` / `"Jarvis"`. Non-wake words are discarded. Speaks acknowledgment: *"At your service, sir. What can I do for you?"* and transitions to active mode.
  - **Turn 2:** Captures raw follow-up commands directly without requiring the wake word, executes actions, speaks confirmation, and automatically resets to standby.
  - Added 6-second timeout fallback (*"Returning to standby, sir."*).
- **Dynamic Cross-PC Desktop Automation Engine:**
  - Zero hardcoded user file paths. Dynamic executable discovery via `shutil.which` and Start Menu registry scanning.
  - Cross-PC support for launching apps, closing processes, web search (YouTube, Spotify, Google), volume/media controls, and workstation locking.
- **Robust Audio Capture & Device Discovery:**
  - Replaced PyAudio with native `sounddevice` float32 streaming and int16 PCM conversion.
  - Integrated Silero VAD frame-by-frame auto-slicing (stops recording after ~350ms trailing silence).
  - Added audio gain normalization and hardware microphone auto-discovery.
- **Dedicated British TTS Worker & Emergency HALT:**
  - Dedicated background thread with `queue.Queue` for thread-safe speech synthesis.
  - Instant speech cancellation via GUI **🛑 HALT** button override.
- **Verification Suite & Deliverables:**
  - 18/18 automated E2E tests passed (`test_system_e2e.py`).
  - Automated submission packaging script (`package_submission.py`).
  - Structured ISO 8601 logging in `assistant_execution.log`.

---

## [1.0.0] - 2026-08-10 (Legacy Prototype)
- Initial prototype with PyQt6 Arc Reactor UI, rule-based matching, and basic Whisper STT.
