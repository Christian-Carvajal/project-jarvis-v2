# Academic Defense & Live Demonstration Guide

> **Course:** BSCS 3112 - Artificial Intelligence  
> **Faculty Advisor / Evaluator:** Prof. Roberto L. Malitao  
> **Presenters:** Christian Ezekiel L. Carvajal & John Miko Sarsalijo  

---

## 🎬 Live Demonstration Script (Step-by-Step)

### 1. Introduction & State Machine Explanation (30 seconds)
- **Presenter:** *"Good day, Prof. Malitao and panel. We present Project JARVIS v2, an offline, local-first artificial intelligence assistant engineered with a Two-Turn Conversational State Machine and 100% Pure Agentic AI Reasoning using Qwen 2.5:1.5B via Ollama."*
- **Key Point:** Point out that all hardcoded regex and keyword triggers have been completely eliminated.

---

### 2. Demonstration 1: Strict Two-Stage Wake Word Gating & Non-Wake Rejection
- **Action:** Speak ordinary conversational words into the microphone:
  - Say: *"Hello"* or *"Good morning"*
  - **Expected:** The status remains `Standby (Waiting for 'Jarvis')` (`#00E5FF`), console prints `[Passive Acoustic Gate]: Discarded non-wake audio`, and JARVIS does not trigger.
- **Action:** Say: *"Hey Jarvis"*
  - **Expected:** Status changes to Green (`#00E676`), JARVIS speaks: *"At your service, sir. What can I do for you?"*, status transitions to Yellow (`#FFD700`) `Listening for Command...`.

---

### 3. Demonstration 2: Turn 2 Direct Command Execution (No Wake Word)
- **Action:** While in active mode (Yellow status), say directly without saying "Hey Jarvis":
  - Say: *"Turn on the living room light and set the temperature to 24 degrees"*
  - **Expected:**
    1. Whisper STT captures raw command with Silero VAD auto-slicing.
    2. Local Qwen 2.5:1.5B dynamically outputs JSON payload with 2 actions (`living_room_light.turn_on`, `thermostat.set_temperature`).
    3. GUI device cards update in real-time.
    4. JARVIS speaks spoken confirmation and resets back to `Standby` (`#00E5FF`).

---

### 4. Demonstration 3: Compound Dual-Domain Action (Smart Home + Dynamic PC Desktop Automation)
- **Action:** Say *"Hey Jarvis"*, wait for acknowledgment, then say:
  - Say: *"Open Notepad and turn on the kitchen light"*
  - **Expected:**
    1. Dynamic PC Automation Engine resolves Notepad without hardcoded paths and launches `notepad.exe`.
    2. Smart Home Simulator turns on Kitchen Light.
    3. Spoken confirmation: *"Opening Notepad and turning on the kitchen light, sir."*

---

### 5. Demonstration 4: Ambiguous Natural Language Reasoning
- **Action:** Say *"Hey Jarvis"*, wait for acknowledgment, then say:
  - Say: *"It is freezing and dark in here"*
  - **Expected:** Qwen 2.5 reasons dynamically that the user is cold and in the dark $\rightarrow$ turns on living room lights and adjusts thermostat $\rightarrow$ confirms verbally.

---

### 6. Demonstration 5: Emergency HALT & Microphone Controls
- **Action:** Issue a long spoken command, then click **🛑 HALT**.
  - **Expected:** TTS speech stops immediately, execution queue is cleared, and assistant resets cleanly to Standby.
- **Action:** Click **🎙️ Mic Toggle**.
  - **Expected:** Mic toggles between Muted and Online.

---

## 🎯 Anticipated Technical Q&A with Prof. Malitao

**Q1: How do you guarantee the AI is 100% agentic and not using hardcoded regex keywords?**  
**Answer:** *"All raw speech transcriptions are passed directly into `AIEngine.parse_command(prompt)`. We utilize Ollama's structured JSON format with a strict Pydantic v2 schema (`AssistantIntentResponse`). The local Qwen 2.5:1.5B LLM autonomously classifies the intent, maps the target entity, extracts parameters, and selects tools across both Smart Home and PC Automation domains."*

**Q2: How does the Two-Turn Conversational State Machine work?**  
**Answer:** *"We implemented an explicit state machine (`AssistantState.STANDBY_WAKE_WORD` and `AssistantState.ACTIVE_COMMAND`). In Turn 1, the microphone acts as an acoustic gate listening strictly for 'Hey Jarvis'. Once detected, JARVIS acknowledges and enters Turn 2, where it captures the user's raw command without requiring the wake word again. It automatically resets to standby after execution, or after a 6-second timeout if no speech is detected."*

**Q3: How does the Dynamic PC Automation work without hardcoded paths?**  
**Answer:** *"We use `shutil.which`, `os.path.expandvars`, and Windows Start Menu program discovery to resolve executables dynamically at runtime. This makes the automation engine 100% portable across any Windows PC regardless of user profile directories."*
