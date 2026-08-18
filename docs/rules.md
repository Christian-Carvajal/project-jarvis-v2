# Antigravity Rules & Professor Execution Directives

> **CRITICAL DIRECTIVE:** Read and adhere strictly to these rules before executing any code changes.

1. **Zero Hardcoded Triggers / Commands:**
   - The system is **100% Agentic**.
   - NEVER add rigid regex patterns (`re.match`), hardcoded keyword dictionaries, or rule-based string matching to execute commands.
   - All natural language understanding, intent extraction, parameter resolution, and cross-domain action generation MUST be decided dynamically by local **Qwen 2.5:1.5B (Ollama)** in strict JSON schema format (`format="json"`) validated against Pydantic v2 schemas (`DeviceAction`, `AssistantIntentResponse`).

2. **Two-Turn Alternating Conversational State Machine:**
   - Maintain the strict separation of states:
     - `STATE_STANDBY_WAKE_WORD`: Microphone listens strictly for `"Hey Jarvis"` / `"Jarvis"`. Non-wake utterances are discarded. On wake word detection, JARVIS speaks: *"At your service, sir. What can I do for you?"* and transitions to `STATE_ACTIVE_COMMAND`.
     - `STATE_ACTIVE_COMMAND`: Microphone listens directly for raw speech **WITHOUT** requiring a wake word. Dispatches actions, speaks confirmation, and automatically resets to `STATE_STANDBY_WAKE_WORD`.
     - **6-Second Timeout:** If no speech is heard for 6 seconds in `STATE_ACTIVE_COMMAND`, JARVIS speaks *"Returning to standby, sir."* and resets to `STATE_STANDBY_WAKE_WORD`.

3. **Universal Cross-PC Portability (Zero Machine-Specific Paths):**
   - NEVER use absolute hardcoded paths (e.g. `C:\Users\...`).
   - Dynamic application resolution must use `shutil.which`, `os.path.expandvars`, Start Menu program scanning, and standard system command aliases.

4. **Strict Deliverables & Rubrics Preserved:**
   - Do NOT alter or remove the mandatory deliverable files:
     - `main.py`
     - `src/voice_pipeline.py`
     - `src/ai_engine.py`
     - `src/home_simulator.py`
     - `assistant_execution.log`
     - `Prelim_Project_Report.pdf`
     - `test_system_e2e.py`

5. **Structured Audit Logging:**
   - Every single command interaction MUST be persisted to `assistant_execution.log` with an ISO 8601 timestamp, raw voice transcription, validated JSON payload, state transitions, and execution latency.

6. **Virtual Environment Enforcement:**
   - Always run commands inside the local `.venv` environment (`.\.venv\Scripts\activate`).
