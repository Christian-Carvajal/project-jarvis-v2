# Project JARVIS -- Baseline vs. Fine-Tuned Model Benchmark Comparison

> **Baseline Model:** `qwen3.5:2b` (Vanilla Base Qwen 3.5 2B)\n> **Fine-Tuned Model:** `jarvis-trained-model` (LoRA Fine-Tuned & Domain Aligned)\n> **Evaluation Date:** August 21, 2026\n> **Total Test Scenarios:** 15

---

## 1. Executive Comparison Scorecard

| Evaluation Dimension | Baseline (`qwen3.5:2b`) | Fine-Tuned (`jarvis-trained-model`) | Improvement (Delta) | Empirical Verdict |
| :--- | :---: | :---: | :---: | :--- |
| **JSON Validity Rate** | **100.0%** | **100.0%** | +0.0% | Zero syntax errors |
| **Action Schema Accuracy** | **100.0%** | **100.0%** | +0.0% | Exact device & app routing |
| **Chit-Chat Null Accuracy** | **66.7%** | **100.0%** | **+33.3%** | **Resolved CHAT-02 False Trigger (100%)** |
| **Overall Benchmark Score** | **93.3%** | **100.0%** | **+6.7%** | **100% Comprehensive Pass** |
| **Avg Inference Latency** | **10111.6 ms** (10.11 s) | **3993.1 ms** (3.99 s) | -6118.5 ms (-60.5%) | 38.5% Latency Reduction |
| **Generation Throughput** | **47.7 tok/s** | **64.9 tok/s** | +17.2 tok/s | Higher Generation Speed |

---

## 2. Granular Side-by-Side Test Traces (15 Scenarios)

| ID | Prompt | Baseline Result | Fine-Tuned Result | Baseline Actions | Fine-Tuned Actions |
| :--- | :--- | :---: | :---: | :--- | :--- |
| **IOT-01** | *"Turn on living room light"* | **PASS** | **PASS** | `['living_room_light.turn_on']` | `['living_room_light.turn_on']` |
| **IOT-02** | *"Set temperature to 20"* | **PASS** | **PASS** | `['thermostat.set_temperature']` | `['thermostat.set_temperature']` |
| **IOT-03** | *"Lock the front door"* | **PASS** | **PASS** | `['front_door_lock.lock']` | `['front_door_lock.lock']` |
| **IOT-04** | *"Turn off kitchen light"* | **PASS** | **PASS** | `['kitchen_light.turn_off']` | `['kitchen_light.turn_off']` |
| **CTX-01** | *"It's freezing and dark in here"* | **PASS** | **PASS** | `['thermostat.set_temperature', 'living_room_light.turn_on']` | `['thermostat.set_temperature', 'living_room_light.turn_on']` |
| **CTX-02** | *"I'm heading to sleep"* | **PASS** | **PASS** | `['living_room_light.turn_off', 'front_door_lock.lock']` | `['bedroom_light.turn_off', 'living_room_light.turn_off', 'front_door_lock.lock']` |
| **CTX-03** | *"Movie night mode"* | **PASS** | **PASS** | `['living_room_light.turn_on', 'entertainment_unit.turn_on']` | `['entertainment_unit.turn_on', 'living_room_light.turn_on']` |
| **CTX-04** | *"I am leaving the house"* | **PASS** | **PASS** | `['front_door_lock.lock']` | `['front_door_lock.lock', 'lock_pc.system_control']` |
| **PC-01** | *"Launch Notepad"* | **PASS** | **PASS** | `['notepad.open_app']` | `['notepad.open_app']` |
| **PC-02** | *"Open YouTube and search for classical music"* | **PASS** | **PASS** | `['youtube.open_website']` | `['youtube.open_website']` |
| **PC-03** | *"Open Spotify"* | **PASS** | **PASS** | `['spotify.open_app']` | `['spotify.open_app']` |
| **PC-04** | *"Lock my computer"* | **PASS** | **PASS** | `['lock_pc.lock']` | `['lock_pc.system_control']` |
| **CHAT-01** | *"Hello Jarvis, how are you today?"* | **PASS** | **PASS** | `['(none)']` | `['(none)']` |
| **CHAT-02** | *"Thank you for your help"* | **FAIL** | **PASS** | `['thermostat.set_temperature', 'living_room_light.turn_on']` | `['(none)']` |
| **CHAT-03** | *"Who created you?"* | **PASS** | **PASS** | `['(none)']` | `['(none)']` |

---

## 3. Key Findings & Architectural Impact

1. **Chit-Chat Null-Action Accuracy Enhancement:**
   - On test `CHAT-02` (*"Thank you for your help"*), the baseline model hallucinated false smart home actions (`thermostat.set_temperature`, `living_room_light.turn_on`).
   - The fine-tuned model `jarvis-trained-model` strictly recognized conversational politeness and returned `actions: []` with 100% accuracy.

2. **Zero Schema Regressions:**
   - All 12 actionable scenarios across Direct IoT, Ambiguous Intent, and Desktop Automation maintained 100% schema accuracy.
3. **Inference Latency & Generation Speed:**
   - Baseline Latency: **10.11 s** vs. Fine-Tuned Latency: **3.99 s**.
   - Baseline Throughput: **47.7 tok/s** vs. Fine-Tuned Throughput: **64.9 tok/s**.
