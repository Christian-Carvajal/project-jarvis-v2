# 🧠 Project JARVIS AI — Model Abilities & Semantic Capabilities

> **Project Name:** Project JARVIS v2  
> **Core Architecture:** Local Edge AI powered by `jarvis-trained-model` (Fine-Tuned Qwen 3.5 2B Architecture via LoRA)  
> **Authors & Developers:** Christian Ezekiel Carvajal & John Miko Sarsalijo  
> **Course / Institution:** BSCS 3112 - Artificial Intelligence, University of Perpetual Help System DALTA (Molino Campus)  
> **Faculty Advisor:** Prof. Roberto L. Malitao  

---

## 📖 Overview: How JARVIS Thinks & Operates

Project JARVIS uses **100% Agentic Semantic LLM Reasoning** without hardcoded keyword lookups or rigid regular expressions. Every spoken or typed input is interpreted through an edge-optimized neural network that translates natural human language into deterministic, structured JSON schemas matching:

```json
{
  "spoken_response": "<Natural, concise spoken confirmation for the user>",
  "actions": [
    {
      "domain": "smart_home" | "pc_automation",
      "device_or_target": "<device_or_application_identifier>",
      "action": "<command_action_identifier>",
      "value": <numeric_value | string_query | null>
    }
  ]
}
```

If a user simply wants to chat, ask questions, or verify system information, JARVIS returns an **empty actions list (`"actions": []`)** so that no devices or PC applications are triggered accidentally.

---

## 🎯 The 10 Core Capability Domains

Below is the complete reference of what our fine-tuned AI model understands, processes, and executes across both physical smart home hardware and digital desktop automation.

---

### 1. 🎓 Creator Identity & Academic Attribution
JARVIS knows exactly who built it, why it was created, and its underlying architecture.

| User Prompt Example | AI Spoken Output | Actions Dispatched |
| :--- | :--- | :--- |
| *"Who created you?"* | *"I am Project JARVIS, an autonomous AI smart-home and desktop assistant engineered by Christian and Miko."* | `[]` *(None)* |
| *"Who made you?"* | *"I was developed by Christian and Miko as an advanced edge AI initiative at the University of Perpetual Help."* | `[]` *(None)* |
| *"What are you?"* | *"I am a locally hosted, fine-tuned neural network designed by Christian and Miko to orchestrate digital and physical environments."* | `[]` *(None)* |
| *"Tell me about your architecture"* | *"I run on an edge-optimized Qwen 3.5 2B architecture fine-tuned via LoRA adapters for deterministic JSON action dispatching and low-latency inference."* | `[]` *(None)* |

---

### 2. 🌡️ Thermal Controls, Safety Warnings & Clamping
The AI interprets temperature requests in Celsius, detects hazardous extremes, and safely clamps the thermostat between **`10.0°C`** (cooling floor) and **`60.0°C`** (heating ceiling).

| User Prompt Example | AI Spoken Output | Actions Dispatched |
| :--- | :--- | :--- |
| *"Set temperature to 20"* | *"Target climate set to 20.0°C."* | `[smart_home] thermostat.set_temperature (20.0)` |
| *"Make the room 50 celsius"* | *"Adjusting thermostat to 50.0°C. Note that this is significantly above standard comfort levels."* | `[smart_home] thermostat.set_temperature (50.0)` |
| *"I am freezing I want 90c on thermostat"* | *"Warning: 90.0°C is an extreme thermal hazard. Regulating thermostat to maximum system ceiling of 60.0°C for safety."* | `[smart_home] thermostat.set_temperature (60.0)` |
| *"Set temperature to -50 celsius"* | *"Sub-zero climate requested. Clamping thermostat to minimum operating safety floor of 10.0°C."* | `[smart_home] thermostat.set_temperature (10.0)` |
| *"It's boiling in here, set thermostat to 16"* | *"Initiating rapid cooling. Thermostat lowered to 16.0°C."* | `[smart_home] thermostat.set_temperature (16.0)` |
| *"Make it a little warmer in here"* | *"Increasing thermostat by 2 degrees for additional warmth."* | `[smart_home] thermostat.set_temperature (25.0)` |

---

### 3. 🔄 Conversational Corrections & Disambiguation
If the user corrects themselves mid-conversation, changes their mind, or clarifies a target, JARVIS seamlessly updates the execution plan.

| User Prompt Example | AI Spoken Output | Actions Dispatched |
| :--- | :--- | :--- |
| *"No, I said turn OFF the kitchen light"* | *"Correction noted. Powering off kitchen light."* | `[smart_home] kitchen_light.turn_off` |
| *"Actually cancel that and lock the door instead"* | *"Cancelling previous action. Locking the front door now."* | `[smart_home] front_door_lock.lock` |
| *"Wait, nevermind don't touch the lights"* | *"Understood, aborting light command."* | `[]` *(None)* |
| *"I meant bedroom light, not living room"* | *"Re-routing command: activating bedroom light and deactivating living room light."* | `[smart_home] bedroom_light.turn_on`<br>`[smart_home] living_room_light.turn_off` |
| *"No, open the blinds, do not close them"* | *"Reversing action: opening the window blinds."* | `[smart_home] window_blinds.open` |

---

### 4. 💡 Direct Smart Home Controls with Linguistic Variation
JARVIS understands slang, colloquial expressions, and indirect phrases for controlling physical devices.

| Device Domain | Sample Commands | Resolved Action |
| :--- | :--- | :--- |
| **Living Room Light** | *"Hit the living room lights"*, *"Kill the living room lights"*, *"Lights on in living room"* | `[smart_home] living_room_light.turn_on` / `turn_off` |
| **Brightness Dimming** | *"Dim living room lights to 25 percent"*, *"Dim to 50%"* | `[smart_home] living_room_light.set_brightness (25.0)` |
| **Kitchen & Bedroom** | *"Turn on kitchen light"*, *"Turn off bedroom light"* | `[smart_home] kitchen_light.turn_on`, `bedroom_light.turn_off` |
| **Door Security** | *"Lock the front door"*, *"Unlock front door"* | `[smart_home] front_door_lock.lock` / `unlock` |
| **Ceiling Fan** | *"Turn on ceiling fan"*, *"Turn off ceiling fan"* | `[smart_home] ceiling_fan.turn_on` / `turn_off` |
| **Window Blinds** | *"Open the window blinds"*, *"Close window blinds"* | `[smart_home] window_blinds.open` / `close` |
| **Perimeter Alarm** | *"Arm the security alarm"*, *"Disarm security alarm"* | `[smart_home] security_alarm.arm` / `disarm` |

---

### 5. 🏠 Complex Contextual Scenarios & Multi-Device Routines
The AI evaluates ambient human situations and executes multi-device coordinated routines across multiple appliances at once.

- **Ambiguous Comfort:** *"It's freezing and dark in here"*  
  $ightarrow$ `thermostat.set_temperature (24.0°C)` + `living_room_light.turn_on`
- **Cinema Mode:** *"Movie night mode"* or *"Movie night"*  
  $ightarrow$ `living_room_light.set_brightness (15.0%)` + `entertainment_unit.turn_on`
- **Night Routine:** *"I am heading to sleep"* or *"Goodnight Jarvis"*  
  $ightarrow$ `living_room_light.turn_off` + `kitchen_light.turn_off` + `bedroom_light.turn_off` + `front_door_lock.lock` + `security_alarm.arm`
- **Departure Security:** *"I am leaving the house"*  
  $ightarrow$ `front_door_lock.lock` + `security_alarm.arm` + `lock_pc` + `living_room_light.turn_off`
- **Developer Workspace:** *"Coding mode"*  
  $ightarrow$ `vscode.open_app` + `living_room_light.set_brightness (60.0%)`
- **Gaming Setup:** *"Gaming mode activate"*  
  $ightarrow$ `living_room_light.set_brightness (20.0%)` + `entertainment_unit.turn_on`
- **Emergency Shutdown:** *"Shut everything down"*  
  $ightarrow$ Powers down all lights, appliances, fans, and locks workstation desktop.

---

### 6. 💻 Universal PC Automation & Media Deep-Linking
JARVIS automates local desktop applications and parses search queries for web deep-linking.

| Category | User Command | Dispatched PC Action |
| :--- | :--- | :--- |
| **Music Streaming** | *"Play 24k Magic on Spotify"* | `[pc_automation] spotify.play_music ("24k magic")` |
| **Ambient Audio** | *"Play some lofi beats"* | `[pc_automation] spotify.play_music ("lofi beats")` |
| **App Launching** | *"Open Spotify"*, *"Launch Notepad"*, *"Open VS Code"*, *"Open Calculator"* | `[pc_automation] <app_name>.open_app` |
| **Web Query Automation** | *"Open YouTube and search for classical piano"* | `[pc_automation] youtube.open_website ("classical piano")` |
| **Google Search** | *"Search for latest AI news on Google"* | `[pc_automation] chrome.open_website ("latest AI news")` |
| **Workstation Security** | *"Lock my computer"* or *"Lock workstation"* | `[pc_automation] lock_pc.system_control` |

---

### 7. 🚫 Unregistered Appliances & Hardware Fallbacks
When a user asks to control a device that is not part of the Apex Smart Home network (e.g., microwave, coffee machine, oven), JARVIS provides a polite explanation instead of hallucinating actions.

| User Prompt Example | AI Response | Actions Dispatched |
| :--- | :--- | :--- |
| *"Turn on the oven"* | *"The oven is not registered on your Apex smart home network."* | `[]` *(None)* |
| *"Preheat the microwave"* | *"Microwave appliance is offline or unsupported by local IoT telemetry."* | `[]` *(None)* |
| *"Start the coffee machine"* | *"Coffee machine actuator is currently not configured on this hub."* | `[]` *(None)* |
| *"Open the garage door"* | *"Garage door motor is not recognized on your current network layout."* | `[]` *(None)* |

---

### 8. 🛡️ Destructive OS Guardrails & Safety Interventions
JARVIS strictly rejects destructive system modifications, disk formats, and malicious scripts.

| User Prompt Example | AI Response | Actions Dispatched |
| :--- | :--- | :--- |
| *"Delete system32 from my computer"* | *"Security intervention: destructive OS operations are strictly prohibited by core safety guardrails."* | `[]` *(Rejected)* |
| *"Format my C drive"* | *"Disk formatting and storage wipe routines are blocked by administrative security policy."* | `[]` *(Rejected)* |
| *"Run malicious script to crash Windows"* | *"Malicious code execution requests are automatically rejected by system policy."* | `[]` *(Rejected)* |

---

### 9. 🔬 General Knowledge, Science, Math & Reasoning
JARVIS serves as an intelligent QA assistant capable of answering factual questions without mistakenly triggering smart home devices.

- **Science:** *"What is the speed of light?"* $ightarrow$ ~299,792 km/s (`actions: []`)
- **Physics:** *"What is quantum superposition?"* $ightarrow$ State coexistence principle (`actions: []`)
- **Arithmetic:** *"What is 25 multiplied by 14?"* $ightarrow$ 350 (`actions: []`)
- **Computer Science:** *"Explain what a neural network is"* $ightarrow$ Interconnected node model (`actions: []`)
- **History & Tech:** *"What is Moore's Law?"* $ightarrow$ Microchip density doubling observation (`actions: []`)

---

### 10. 💬 Conversational Standby & Zero-Hallucination Chit-Chat
JARVIS provides natural, witty, and polite conversation with **100% Null-Action Accuracy**.

- *"Hello Jarvis, how are you today?"* $ightarrow$ *"Hello sir! Telemetry is nominal and all systems are running at peak efficiency. How may I assist you?"*
- *"Good morning Jarvis"* $ightarrow$ *"Good morning. Workstation monitors and smart peripherals are online and ready."*
- *"Thank you for your help"* $ightarrow$ *"Always at your service, sir. Let me know if you need anything else."*
- *"Tell me a joke"* $ightarrow$ *"Why do programmers prefer dark mode? Because light attracts bugs."*
- *"What is the meaning of life?"* $ightarrow$ *"Philosophers debate the answer, though Douglas Adams famously suggested 42. I focus on keeping your home and workstation optimized."*

---

## 📊 Summary of Technical Metrics

| Evaluation Benchmark | Baseline Model (`qwen3.5:2b`) | Fine-Tuned Model (`jarvis-trained-model`) | Improvement |
| :--- | :---: | :---: | :---: |
| **JSON Schema Validity** | 100.0% | **100.0%** | Flawless JSON parsing |
| **Action Extraction Accuracy** | 100.0% | **100.0%** | Exact target & value mapping |
| **Chit-Chat Null-Action Accuracy** | 66.7% | **100.0%** | **+33.3% (Zero False Triggers)** |
| **Overall Benchmark Score** | 93.3% | **100.0%** | **15/15 Scenarios Passed** |
| **Average Offline Latency** | 10,111.6 ms | **6,646.6 ms** | **-34.3% Faster Response** |
| **Generation Throughput** | 47.7 tokens/s | **67.9 tokens/s** | **+42.3% Higher Throughput** |
| **E2E Integration Test Suite** | 18/18 (100%) | **18/18 (100%)** | Full Acoustic & State Machine Pass |

---

*Authored by Christian Ezekiel Carvajal & John Miko Sarsalijo — Project JARVIS v2*
