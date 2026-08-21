# Completed Task Execution Log

> **Project:** Project JARVIS v2  
> **Course:** BSCS 3112 - Artificial Intelligence  
> **Faculty Advisor:** Prof. Roberto L. Malitao  
> **Status:** 100% Completed, Verified & Submission Packaged  

---

## 📅 Architectural Refactor & Milestone Log

### Phase 1: Elimination of Hardcoded Trigger Rules & Regex Matching
- Removed all static regex matching (`re.match`), hardcoded keyword dictionaries, and rule-based command dispatchers.
- Upgraded `src/ai_engine.py` to use pure agentic LLM reasoning via local **Qwen 3.5 (2B Parameter Base / LoRA Fine-Tuned)** in strict JSON format (`format="json"`).
- Implemented robust Pydantic v2 schemas (`DeviceAction` and `AssistantIntentResponse`).

### Phase 2: Implementation of Two-Turn Conversational State Machine
- Created `AssistantState` enum (`STANDBY_WAKE_WORD = 1`, `ACTIVE_COMMAND = 2`) in `src/main.py`.
- **Turn 1 (`STATE_STANDBY_WAKE_WORD`):** Listens strictly for `"Hey Jarvis"` / `"Jarvis"`, filters non-wake background speech, speaks acknowledgment: *"At your service, sir. What can I do for you?"*, and transitions to `STATE_ACTIVE_COMMAND`.
- **Turn 2 (`STATE_ACTIVE_COMMAND`):** Listens directly for raw user commands without requiring wake word repetition, executes agentic action plans across Smart Home and PC Automation engines, speaks confirmation, and resets to `STATE_STANDBY_WAKE_WORD`.
- Implemented a 6-second timeout fallback that speaks *"Returning to standby, sir."* and resets if no command is heard.

### Phase 3: Hardware Microphone & Audio Pipeline Stabilization
- Replaced PyAudio dependency with native `sounddevice` float32 streaming converted to int16 PCM `sr.AudioData`.
- Integrated Silero VAD frame-by-frame auto-slicing (stops recording after ~350ms of trailing silence).
- Added audio gain normalization to eliminate quiet mic / mumbling dropouts.
- Built automatic hardware microphone discovery to bypass disconnected virtual webcams.
- Integrated persistent British TTS background worker thread with `queue.Queue` and emergency HALT override.

### Phase 4: Dynamic Cross-PC Desktop Automation Engine
- Implemented `PCAutomationEngine` with zero hardcoded user paths (`C:\Users\...`).
- Added dynamic application discovery via `shutil.which` and Start Menu registry scanning.
- Built dynamic web search (YouTube, Spotify, Google), process termination (`taskkill`), volume/media controls, and workstation lock (`rundll32.exe user32.dll,LockWorkStation`).

### Phase 5: Automated Verification & Packaging
- Built comprehensive E2E verification test suite (`test_system_e2e.py`) verifying 12 acoustic wake/non-wake cases and 6 complex multi-domain agentic commands (18/18 tests passed, 100%).
- Built automated packaging script (`package_submission.py`) generating `AI_PrelimExam_Group_Carvajal_Sarsalijo.zip`.
- Maintained strict ISO 8601 audit logging in `assistant_execution.log`.

### Phase 6: Baseline Pre-Training Model Benchmark Evaluation (`qwen3.5:2b`)
- Developed automated evaluation harness (`benchmark_baseline.py`) with 15 standardized test scenarios across Direct IoT, Ambiguous Comfort, PC Automation, and Chit-Chat.
- Recorded baseline metrics: **100.0% JSON validity**, **100.0% action schema accuracy**, **66.7% chit-chat null-action accuracy**, **93.3% overall score**, **10.11s latency**, and **47.7 tokens/sec**.
- Exported raw JSON results to [`benchmarks/baseline_qwen3.5_2b_results.json`](../benchmarks/baseline_qwen3.5_2b_results.json).
- Documented full benchmark analysis and pre-training baseline results in [`docs/baseline_benchmark_results.md`](baseline_benchmark_results.md) and [`benchmarks/README.md`](../benchmarks/README.md) for comparative evaluation against fine-tuned weights.

### Phase 7: Fine-Tuned Model Integration (`jarvis-trained-model`) & Comparative Evaluation
- Integrated custom LoRA fine-tuned model (`jarvis-trained-model`) into active system configuration across `src/ai_engine.py`, `src/main.py`, `src/home_simulator.py`, `core/llm_manager.py`, `core/voice_pipeline.py`, and `ui/hud_window.py`.
- Developed side-by-side comparative benchmark harness (`benchmark_compare.py`) evaluating `qwen3.5:2b` (Baseline) vs. `jarvis-trained-model` (Fine-Tuned).
- Verified key empirical improvements:
  * **Chit-Chat Null-Action Accuracy:** Improved from **66.7% to 100.0%**, successfully resolving the baseline `[CHAT-02]` action hallucination flaw (*"Thank you for your help"* $\rightarrow$ `actions: []`).
  * **Inference Latency:** Reduced by **38.5%** from 10.11s down to **6.22s** average latency.
  * **Token Generation Throughput:** Increased by **56.8%** from 47.7 tok/s up to **74.8 tokens/sec**.
  * **Overall Benchmark Score:** Achieved **100.0% (15/15)** comprehensive pass rate.
- Exported comparative analysis artifacts to [`benchmarks/model_comparison_results.json`](../benchmarks/model_comparison_results.json) and [`benchmarks/model_comparison_results.md`](../benchmarks/model_comparison_results.md).
- Updated academic report generator (`generate_report.py`) with empirical scorecard, LoRA hyperparameters (Rank 16, Alpha 16, 40 steps, loss converged to ~0.046), and compiled the final 3-page `Prelim_Project_Report.pdf`.

### Phase 8: Custom Model Pruning, HUD Lock & Final 100% Comprehensive Audit
- **Model Standardized Strictly on `jarvis-trained-model`:** Removed all legacy model references (`jarvis-custom`, `qwen3.5:4b`, `qwen3.5:9b`, `deepseek-r1:8b`) across HUD (`ui/hud_window.py`), Smart Home Simulator (`src/home_simulator.py`), `src/ai_engine.py`, and `core/llm_manager.py`.
- **HUD Cyberpunk Interface Fix & Model Selector Lock:** Verified PyQt6 GUI runs flawlessly with Arc Reactor visualizer, audio level callbacks, terminal console, text command bar, mic toggle, and emergency HALT override.
- **Side-by-Side Comparative Benchmark:** Executed `python benchmark_compare.py` $\rightarrow$ Achieved **100.0% (15/15)** pass rate for `jarvis-trained-model`.
- **Academic PDF Report Compilation:** Executed `python generate_report.py` $\rightarrow$ Verified 3-page academic report compiled to `Prelim_Project_Report.pdf`.
- **Full End-to-End System Smoke Test:** Executed `python test_system_e2e.py` $\rightarrow$ Verified **18/18 tests passed (100.0%)** across acoustic gating (12/12) and agentic multi-domain execution (6/6).



