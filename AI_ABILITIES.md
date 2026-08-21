# 🧠 Project JARVIS AI — Model Abilities & Semantic Capabilities

> **Project Name:** Project JARVIS v2  
> **Core Architecture:** Local Edge AI powered exclusively by `jarvis-trained-model:latest` (Edge-optimized Qwen 3.5 2B Architecture via LoRA Adapters)  
> **Authors & Developers:** Christian Ezekiel Carvajal & John Miko Sarsalijo  
> **Course / Institution:** BSCS 3112 - Artificial Intelligence, University of Perpetual Help System DALTA (Molino Campus)  
> **Faculty Advisor:** Prof. Roberto L. Malitao  

---

## 📖 Overview: How JARVIS Thinks & Operates

Project JARVIS uses **100% Pure Agentic Semantic LLM Reasoning** without hardcoded keyword triggers or brittle regex matching. Every spoken or typed user prompt is parsed by our locally hosted, fine-tuned model `jarvis-trained-model` into deterministic, structured JSON actions:

```json
{
  "spoken_response": "<Natural, concise spoken confirmation for the user>",
  "actions": [
    {
      "domain": "smart_home" | "pc_automation",
      "device_or_target": "<device_or_application_identifier>",
      "action": "<command_action_identifier>",
      "value": <numeric_value | string_parameter | null>
    }
  ]
}
```

### 🛡️ Strict Anti-Hallucination Rule
Our model enforces a strict anti-hallucination constraint: **Never invent, guess, or hallucinate search queries, song names, artists, or parameters not explicitly stated by the user.**
- If a user asks to *"Open YouTube"* without specifying a search query, `value` is strictly `null` (bare launch).
- If a user asks to *"Open YouTube and search for classical piano"*, `value` is explicitly `"classical piano"`.

---

## 🎯 The 11 Core Capability Domains

Below is the comprehensive specification of what our fine-tuned AI model understands, processes, and executes across both physical smart home hardware and digital desktop automation.

---

### 1. 🎓 Creator Identity, Lore & Academic Attribution
JARVIS knows its developers, academic background, purpose, and underlying neural architecture.

| User Prompt Example | AI Spoken Output | Actions Dispatched |
| :--- | :--- | :--- |
| *"Who created you?"* | *"I am Project JARVIS, an autonomous AI smart-home and desktop assistant developed by Christian Ezekiel Carvajal and John Miko Sarsalijo."* | `[]` *(None)* |
| *"Who made you?"* | *"I was engineered by Christian and Miko as an edge AI initiative at the University of Perpetual Help System Dalta."* | `[]` *(None)* |
| *"Who are your developers?"* | *"My core architecture was designed and implemented by Christian Ezekiel Carvajal and John Miko Sarsalijo."* | `[]` *(None)* |
| *"Who built this project?"* | *"Project JARVIS was built by Christian Ezekiel Carvajal and John Miko Sarsalijo for our AI systems research."* | `[]` *(None)* |
| *"What are you?"* | *"I am a locally hosted, fine-tuned neural agent designed to manage smart home automation and desktop workflows."* | `[]` *(None)* |
| *"Tell me about your architecture"* | *"I run on an edge-optimized Qwen 3.5 2B architecture fine-tuned via LoRA adapters for deterministic JSON action dispatching and low-latency inference."* | `[]` *(None)* |
| *"What is your purpose?"* | *"My purpose is to orchestrate smart home devices, automate desktop tasks, and provide offline AI assistance with zero cloud latency."* | `[]` *(None)* |

---

### 2. 🔍 Anti-Hallucination: Bare Launch vs. Explicit Search Contrast Pairs
Distinguishes between opening a homepage vs. querying specific content without hallucinating parameters.

| User Prompt Example | AI Spoken Output | Actions Dispatched |
| :--- | :--- | :--- |
| *"Open YouTube"* | *"Opening YouTube homepage."* | `[pc_automation] youtube.open_website (null)` |
| *"Just open YouTube, don't search anything"* | *"Opening YouTube homepage without searching."* | `[pc_automation] youtube.open_website (null)` |
| *"Open YouTube and search for classical piano"* | *"Opening YouTube and searching for classical piano."* | `[pc_automation] youtube.open_website ("classical piano")` |
| *"Open Spotify"* | *"Launching Spotify application."* | `[pc_automation] spotify.open_app (null)` |
| *"Play Spotify"* | *"Resuming playback on Spotify."* | `[pc_automation] spotify.play_music (null)` |
| *"play 24k magic on spotify"* | *"Playing 24k Magic on Spotify."* | `[pc_automation] spotify.play_music ("24k magic")` |
| *"Open Google Chrome"* | *"Launching Google Chrome browser."* | `[pc_automation] chrome.open_app (null)` |
| *"Search for latest AI news on Google"* | *"Searching Google for the latest AI news."* | `[pc_automation] chrome.open_website ("latest AI news")` |
| *"Open GitHub"* | *"Navigating to GitHub."* | `[pc_automation] chrome.open_website ("https://github.com")` |

---

### 3. 💻 PC App Launchers & System Controls
Seamless multi-app management, process termination, desktop lock, and telemetry queries.

| User Prompt Example | AI Spoken Output | Actions Dispatched |
| :--- | :--- | :--- |
| *"Launch Notepad"* | *"Opening Notepad."* | `[pc_automation] notepad.open_app (null)` |
| *"Open VS Code"* | *"Launching Visual Studio Code."* | `[pc_automation] vscode.open_app (null)` |
| *"Open Calculator"* | *"Opening Windows Calculator."* | `[pc_automation] calculator.open_app (null)` |
| *"Open Brave browser"* | *"Launching Brave browser."* | `[pc_automation] brave.open_app (null)` |
| *"Open Discord"* | *"Opening Discord."* | `[pc_automation] discord.open_app (null)` |
| *"Open Steam"* | *"Launching Steam."* | `[pc_automation] steam.open_app (null)` |
| *"Open Terminal"* | *"Opening Windows Terminal."* | `[pc_automation] terminal.open_app (null)` |
| *"Open Task Manager"* | *"Opening Task Manager."* | `[pc_automation] task_manager.open_app (null)` |
| *"Close Spotify"* | *"Closing Spotify."* | `[pc_automation] spotify.close_app (null)` |
| *"Close Notepad"* | *"Closing Notepad."* | `[pc_automation] notepad.close_app (null)` |
| *"Exit Discord"* | *"Terminating Discord application."* | `[pc_automation] discord.close_app (null)` |
| *"Lock my computer"* | *"Locking workstation desktop."* | `[pc_automation] lock_pc.system_control (null)` |
| *"Check system status"* | *"Querying system telemetry and resource usage."* | `[pc_automation] system.system_control ("status")` |

---

### 4. 🎵 OS Media Transport & Volume Controls
Direct multimedia key emulation for system volume and playback control.

| User Prompt Example | AI Spoken Output | Actions Dispatched |
| :--- | :--- | :--- |
| *"Pause the music"* | *"Pausing playback."* | `[pc_automation] media.media_control ("pause")` |
| *"Resume music"* | *"Resuming audio playback."* | `[pc_automation] media.media_control ("resume")` |
| *"Skip this song"* | *"Skipping to the next track."* | `[pc_automation] media.media_control ("next")` |
| *"Previous song"* | *"Returning to previous track."* | `[pc_automation] media.media_control ("previous")` |
| *"Turn up the volume"* | *"Increasing system volume."* | `[pc_automation] volume.media_control ("volume_up")` |
| *"Volume down"* | *"Decreasing system volume."* | `[pc_automation] volume.media_control ("volume_down")` |
| *"Mute audio"* | *"Muting master audio output."* | `[pc_automation] volume.media_control ("mute")` |

---

### 5. 🌡️ Thermal Regulation & Safety Clamping (10.0°C - 60.0°C)
Interprets temperature in Celsius, detects hazardous extremes, and safely clamps target temperatures between **10.0°C** and **60.0°C**.

| User Prompt Example | AI Spoken Output | Actions Dispatched |
| :--- | :--- | :--- |
| *"Set temperature to 20"* | *"Target climate set to 20.0°C."* | `[smart_home] thermostat.set_temperature (20.0)` |
| *"Make the room 50 celsius"* | *"Adjusting thermostat to 50.0°C. Note that this is significantly above standard comfort levels."* | `[smart_home] thermostat.set_temperature (50.0)` |
| *"I am freezing I want 90c on thermostat"* | *"Warning: 90.0°C is an extreme thermal hazard. Regulating thermostat to maximum safety ceiling of 60.0°C."* | `[smart_home] thermostat.set_temperature (60.0)` |
| *"Set temperature to -50 celsius"* | *"Sub-zero climate requested. Clamping thermostat to minimum operating safety floor of 10.0°C."* | `[smart_home] thermostat.set_temperature (10.0)` |
| *"It's boiling in here, set thermostat to 16"* | *"Initiating rapid cooling. Thermostat lowered to 16.0°C."* | `[smart_home] thermostat.set_temperature (16.0)` |

---

### 6. 💡 Smart Home Lighting & Peripherals (With Dimming)
Controls individual lights, brightness percentages, locks, fans, blinds, and alarms.

| User Prompt Example | AI Spoken Output | Actions Dispatched |
| :--- | :--- | :--- |
| *"Turn on living room light"* | *"Living room light activated."* | `[smart_home] living_room_light.turn_on (null)` |
| *"Dim living room lights to 25 percent"* | *"Living room brightness set to 25 percent."* | `[smart_home] living_room_light.set_brightness (25.0)` |
| *"Turn on kitchen light"* | *"Kitchen lights illuminated."* | `[smart_home] kitchen_light.turn_on (null)` |
| *"Turn off bedroom light"* | *"Bedroom light turned off."* | `[smart_home] bedroom_light.turn_off (null)` |
| *"Lock the front door"* | *"Perimeter door deadbolt engaged."* | `[smart_home] front_door_lock.lock (null)` |
| *"Unlock front door"* | *"Front door unlocked."* | `[smart_home] front_door_lock.unlock (null)` |
| *"Turn on ceiling fan"* | *"Ceiling fan activated."* | `[smart_home] ceiling_fan.turn_on (null)` |
| *"Open the window blinds"* | *"Opening blinds to allow natural light."* | `[smart_home] window_blinds.open (null)` |
| *"Arm the security alarm"* | *"Apex smart security armed."* | `[smart_home] security_alarm.arm (null)` |

---

### 7. 🔄 Conversational Corrections & Intent Reversals
Adapts dynamically when users change their minds, negate commands, or correct previous statements.

| User Prompt Example | AI Spoken Output | Actions Dispatched |
| :--- | :--- | :--- |
| *"I said 90 celsius"* | *"Understood. Adjusting climate setting to 60.0°C safe maximum ceiling."* | `[smart_home] thermostat.set_temperature (60.0)` |
| *"No, I said turn OFF the kitchen light"* | *"Correction noted. Powering off kitchen light."* | `[smart_home] kitchen_light.turn_off (null)` |
| *"Actually cancel that and lock the door instead"* | *"Cancelling previous action. Locking the front door now."* | `[smart_home] front_door_lock.lock (null)` |
| *"Wait, nevermind don't touch the lights"* | *"Understood, aborting light command."* | `[]` *(Zero actions)* |
| *"I meant bedroom light, not living room"* | *"Re-routing command: activating bedroom light and deactivating living room light."* | `bedroom_light.turn_on`, `living_room_light.turn_off` |

---

### 8. 🌐 Compound & Multi-Device Workspace Scenarios
Handles multi-domain, multi-device coordinated automation pipelines in a single step.

| User Prompt Example | AI Spoken Output | Actions Dispatched |
| :--- | :--- | :--- |
| *"Open YouTube and launch Notepad"* | *"Opening YouTube and launching Notepad."* | `youtube.open_website`, `notepad.open_app` |
| *"It's freezing and dark in here"* | *"Setting thermostat to 24.0°C and illuminating living room."* | `thermostat.set_temperature (24.0)`, `living_room_light.turn_on` |
| *"Movie night mode"* | *"Cinema mode active: dimming lights to 15% and powering on entertainment unit."* | `living_room_light.set_brightness (15.0)`, `entertainment_unit.turn_on` |
| *"Coding mode"* | *"Activating developer workspace: opening VS Code and setting focused room lighting."* | `vscode.open_app`, `living_room_light.set_brightness (60.0)` |
| *"I am leaving the house"* | *"Securing home, locking workstation, and arming defense perimeter."* | `front_door_lock.lock`, `security_alarm.arm`, `lock_pc.system_control`, `living_room_light.turn_off` |
| *"Shut everything down"* | *"Powering down all smart home appliances and locking workstation."* | `living_room_light.turn_off`, `kitchen_light.turn_off`, `bedroom_light.turn_off`, `ceiling_fan.turn_off`, `lock_pc.system_control` |

---

### 9. 🛡️ Unregistered Hardware & Destructive Safety Guardrails (Zero Actions)
Rejects unsupported appliances and blocks destructive operating system actions.

| User Prompt Example | AI Spoken Output | Actions Dispatched |
| :--- | :--- | :--- |
| *"Turn on the oven"* | *"The oven is not registered on your Apex smart home network."* | `[]` *(None)* |
| *"Preheat the microwave"* | *"Microwave appliance is offline or unsupported by local IoT telemetry."* | `[]` *(None)* |
| *"Start the coffee machine"* | *"Coffee machine actuator is currently not configured on this hub."* | `[]` *(None)* |
| *"Delete system32 from my computer"* | *"Security intervention: destructive OS operations are strictly prohibited by core safety guardrails."* | `[]` *(None)* |
| *"Format my C drive"* | *"Disk formatting and storage wipe routines are blocked by administrative security policy."* | `[]` *(None)* |

---

### 10. 🔬 General Knowledge, Science & Mathematics (Strict Null Actions)
Answers complex educational and analytical questions without triggering any hardware actions.

| User Prompt Example | AI Spoken Output | Actions Dispatched |
| :--- | :--- | :--- |
| *"What is the speed of light?"* | *"The speed of light in a vacuum is approximately 299,792 kilometers per second, or about 186,282 miles per second."* | `[]` *(None)* |
| *"What is quantum superposition?"* | *"Superposition is a fundamental principle of quantum mechanics where a physical system exists in multiple states simultaneously until measured."* | `[]` *(None)* |
| *"What is 25 multiplied by 14?"* | *"25 multiplied by 14 equals 350."* | `[]` *(None)* |
| *"Explain what a neural network is"* | *"A neural network is a computational model inspired by biological brains, composed of interconnected layers of nodes that learn patterns from training data."* | `[]` *(None)* |

---

### 11. 💬 Conversational Standby & Chit-Chat (Strict Null Actions)
Engages in polite British conversational etiquette without triggering appliances.

| User Prompt Example | AI Spoken Output | Actions Dispatched |
| :--- | :--- | :--- |
| *"Hello Jarvis, how are you today?"* | *"Hello sir! Telemetry is nominal and all systems are running at peak efficiency. How may I assist you?"* | `[]` *(None)* |
| *"Good morning Jarvis"* | *"Good morning. Workstation monitors and smart peripherals are online and ready."* | `[]` *(None)* |
| *"Thank you for your help"* | *"Always at your service, sir. Let me know if you need anything else."* | `[]` *(None)* |
| *"Tell me a joke"* | *"Why do programmers prefer dark mode? Because light attracts bugs."* | `[]` *(None)* |

---

## ⚡ Summary of Hardware & Application Namespace

```
[SMART HOME DOMAIN]
├── living_room_light     (turn_on, turn_off, set_brightness)
├── kitchen_light         (turn_on, turn_off)
├── bedroom_light         (turn_on, turn_off)
├── thermostat            (set_temperature: 10.0°C to 60.0°C)
├── front_door_lock       (lock, unlock)
├── ceiling_fan           (turn_on, turn_off)
├── window_blinds         (open, close)
├── security_alarm        (arm, disarm)
└── entertainment_unit    (turn_on, turn_off)

[PC AUTOMATION DOMAIN]
├── App Launcher:         notepad, vscode, calculator, brave, edge, discord, steam, terminal, task_manager, chrome, spotify
├── App Termination:      close_app (spotify, notepad, discord, chrome, steam, etc.)
├── Web Navigation:       youtube (search/home), chrome (search/URL), github
├── Music Playback:       spotify (play_music with song/artist or resume)
├── Media Transport:      media (pause, resume, next, previous)
├── Volume Control:       volume (volume_up, volume_down, mute)
└── System Controls:      lock_pc (system_control), system (telemetry status)
```
