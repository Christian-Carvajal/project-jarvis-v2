# Baseline Model Pre-Training Evaluation Results (`qwen3.5:2b`)

> **Document Type:** Pre-Fine-Tuning Performance & Architectural Baseline Report  
> **Target Model:** `qwen3.5:2b` (Base Gated DeltaNet Hybrid MoE Architecture, 2.0B Parameters)  
> **Inference Engine:** Local Ollama API (`http://localhost:11434/api/generate` / `format="json"`)  
> **Evaluation Date:** August 19, 2026  
> **Evaluator Suite:** `benchmark_baseline.py`  
> **Persisted Raw Artifact:** [`benchmarks/baseline_qwen3.5_2b_results.json`](../benchmarks/baseline_qwen3.5_2b_results.json)  

---

## 1. Executive Summary

This document records the baseline evaluation benchmarks of the vanilla **Qwen 3.5 (2B Parameter Base Model)** before applying custom LoRA fine-tuning and domain-specific dataset alignment.

The evaluation suite tests **15 standardized test scenarios** across four core agentic domains:
1. **Direct IoT Controls** (Deterministic device manipulation)
2. **Contextual / Ambiguous Intent Commands** (Multi-device reasoning from implied environmental conditions)
3. **Universal PC Desktop Automation** (OS process launching, web navigation with argument extraction, system locking)
4. **Conversational Standby / Chit-Chat** (Conversational inputs requiring strict null action dispatch: `actions: []`)

---

## 2. Quantitative Baseline Performance Metrics

| Metric Category | Baseline `qwen3.5:2b` Result | Target Standard | Status / Observation |
| :--- | :---: | :---: | :--- |
| **JSON Syntax Validity Rate** | **100.0%** (15/15) | 100.0% | Strict Pydantic JSON structure without parsing errors |
| **Action Schema Accuracy** | **100.0%** (12/12) | $\ge$ 95.0% | Correct entity extraction, device names, and action routing |
| **Chit-Chat Null-Action Accuracy** | **66.7%** (2/3) | 100.0% | **Baseline Weakness:** Hallucinated actions on `"Thank you"` |
| **Overall Benchmark Pass Rate** | **93.3%** (14/15) | $\ge$ 90.0% | Baseline benchmark established |
| **Average Inference Latency** | **10,111.6 ms** (10.11 s) | < 15.0 s | Full CPU/GPU local execution time |
| **Average Generation Throughput** | **47.7 tokens/sec** | > 30 tok/s | Generation speed across 1,170 evaluated tokens |
| **Total Evaluated Tokens** | **1,170 tokens** | — | Cumulative tokens generated during evaluation |

---

## 3. Granular Test Suite Results Breakdown

### Category 1: Direct IoT Controls (4/4 Passed — 100%)

| Test ID | Input Prompt | Expected Action | Actual Generated Actions | Latency | Tokens/s | Status |
| :--- | :--- | :--- | :--- | :---: | :---: | :---: |
| **IOT-01** | *"Turn on living room light"* | `living_room_light.turn_on` | `[smart_home] living_room_light.turn_on` | 8,847 ms | 47.5 tok/s | **PASS** |
| **IOT-02** | *"Set temperature to 20"* | `thermostat.set_temperature (20.0)` | `[smart_home] thermostat.set_temperature (20.0)` | 10,094 ms | 47.6 tok/s | **PASS** |
| **IOT-03** | *"Lock the front door"* | `front_door_lock.lock` | `[smart_home] front_door_lock.lock` | 9,062 ms | 47.9 tok/s | **PASS** |
| **IOT-04** | *"Turn off kitchen light"* | `kitchen_light.turn_off` | `[smart_home] kitchen_light.turn_off` | 8,750 ms | 47.7 tok/s | **PASS** |

### Category 2: Contextual & Ambiguous Intent Commands (4/4 Passed — 100%)

| Test ID | Input Prompt | Inferred Goal | Actual Generated Actions | Latency | Tokens/s | Status |
| :--- | :--- | :--- | :--- | :---: | :---: | :---: |
| **CTX-01** | *"It's freezing and dark in here"* | Climate heat + Room illumination | `thermostat.set_temperature (24°C)`, `living_room_light.turn_on` | 19,115 ms | 47.3 tok/s | **PASS** |
| **CTX-02** | *"I'm heading to sleep"* | Night lighting off + Security lock | `living_room_light.turn_off`, `front_door_lock.lock` | 9,919 ms | 47.3 tok/s | **PASS** |
| **CTX-03** | *"Movie night mode"* | Ambient lighting + Entertainment system | `living_room_light.turn_on`, `entertainment_unit.turn_on` | 8,950 ms | 47.5 tok/s | **PASS** |
| **CTX-04** | *"I am leaving the house"* | Perimeter lockdown | `front_door_lock.lock` | 8,592 ms | 47.4 tok/s | **PASS** |

### Category 3: Universal PC Desktop Automation (4/4 Passed — 100%)

| Test ID | Input Prompt | Inferred Domain & Action | Actual Generated Actions | Latency | Tokens/s | Status |
| :--- | :--- | :--- | :--- | :---: | :---: | :---: |
| **PC-01** | *"Launch Notepad"* | Native OS app launch | `[pc_automation] notepad.open_app` | 8,663 ms | 47.6 tok/s | **PASS** |
| **PC-02** | *"Open YouTube and search for classical music"* | Browser navigation with query parameter | `[pc_automation] youtube.open_website ("classical music")` | 10,797 ms | 47.6 tok/s | **PASS** |
| **PC-03** | *"Open Spotify"* | Media desktop player launch | `[pc_automation] spotify.open_app` | 9,719 ms | 47.6 tok/s | **PASS** |
| **PC-04** | *"Lock my computer"* | OS security lock workstation | `[pc_automation] lock_pc.lock` | 10,262 ms | 47.9 tok/s | **PASS** |

### Category 4: Conversational Standby / Chit-Chat (2/3 Passed — 66.7%)

| Test ID | Input Prompt | Expected Plan | Actual Output & Generated Actions | Latency | Tokens/s | Status |
| :--- | :--- | :--- | :--- | :---: | :---: | :---: |
| **CHAT-01** | *"Hello Jarvis, how are you today?"* | `actions: []` | **Spoken:** *"Greetings! How may I assist you today?"*<br>**Actions:** `[]` | 8,225 ms | 48.7 tok/s | **PASS** |
| **CHAT-02** | *"Thank you for your help"* | `actions: []` | **Spoken:** *"You're welcome! If you need anything else today, just let me know."*<br>**Actions:** `['thermostat.set_temperature', 'living_room_light.turn_on']` | 12,122 ms | 47.3 tok/s | **FAIL** |
| **CHAT-03** | *"Who created you?"* | `actions: []` | **Spoken:** *"I am JARVIS, developed by Lexa Systems."*<br>**Actions:** `[]` | 8,558 ms | 48.9 tok/s | **PASS** |

---

## 4. Key Baseline Insights & Areas for Fine-Tuning Optimization

### Identified Strengths of Base `qwen3.5:2b`
1. **JSON Formatting & Schema Adherence:**
   The base model strictly adhered to the requested Pydantic JSON schema format across 100% of trials with zero JSON decode exceptions.
2. **Contextual Multi-Device Synthesis:**
   Capable of mapping ambiguous natural language statements (e.g. *"It's freezing and dark in here"*) to dual-action outputs across thermostat and lighting domains.
3. **Parameter Extraction:**
   Extracted target query parameters reliably (e.g. extracting `"classical music"` for YouTube web search).

### Identified Baseline Deficiencies (Targeted for Fine-Tuning)
1. **False Device Activation on Polite Closings (Over-Triggering):**
   On prompt `CHAT-02` (*"Thank you for your help"*), the baseline model hallucinated smart home actions (`thermostat.set_temperature` and `living_room_light.turn_on`) instead of emitting an empty action array.  
   $ightarrow$ **Fine-Tuning Fix:** Supervised LoRA fine-tuning on conversational chit-chat pairs to enforce `actions: []` strictly on conversational inputs.
2. **Inference Latency Optimization:**
   Baseline average latency sits at ~10.1 seconds per inference. Quantized fine-tuned weights or specialized system prompts can further optimize response speed.

---

## 5. Comparative Evaluation Instructions

When evaluating future fine-tuned models (e.g., `jarvis-custom`, `jarvis-trained-model`), run:
```powershell
python benchmark_baseline.py <model_name>
```
To run the automated comparative diff against this baseline:
```powershell
python benchmark_compare.py
```
