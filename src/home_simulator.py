"""
Smart Home Simulator & Dynamic GUI Dashboard for Project JARVIS (Apex Home Automations).
Features:
- Object-Oriented Virtual Device State Machine
- Top-Tier Cyberpunk Stark-Themed Tkinter GUI Dashboard
- Live CPU / RAM / Latency Telemetry
- Interactive Device Cards & Clickable Controls
- 🎙️ Microphone Toggle (Online / Muted) & 🛑 Emergency HALT / Override Button
- Model Selector Dropdown (qwen3.5:2b, etc.)
- Asynchronous, Zero-Lag Text & Voice Command Execution
"""

import os
import sys
import time
import json
import threading
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime
from typing import Dict, Any, List, Optional, Callable
import psutil


# =============================================================================
# 1. OOP VIRTUAL DEVICE HIERARCHY
# =============================================================================

class SmartDevice:
    """Base class for all simulated smart home virtual devices."""
    def __init__(self, device_id: str, name: str, room: str):
        self.device_id = device_id
        self.name = name
        self.room = room
        self.last_updated = datetime.now()

    def get_state(self) -> Dict[str, Any]:
        raise NotImplementedError


class SmartLight(SmartDevice):
    def __init__(self, device_id: str, name: str, room: str, brightness: int = 0, color: str = "Warm White"):
        super().__init__(device_id, name, room)
        self.is_on = brightness > 0
        self.brightness = brightness
        self.color = color

    def turn_on(self, brightness: int = 100, color: Optional[str] = None):
        self.is_on = True
        self.brightness = max(1, min(100, brightness))
        if color:
            self.color = color
        self.last_updated = datetime.now()

    def turn_off(self):
        self.is_on = False
        self.brightness = 0
        self.last_updated = datetime.now()

    def set_brightness(self, level: int):
        level = max(0, min(100, level))
        self.brightness = level
        self.is_on = level > 0
        self.last_updated = datetime.now()

    def toggle(self):
        if self.is_on:
            self.turn_off()
        else:
            self.turn_on(100)

    def get_state(self) -> Dict[str, Any]:
        return {
            "device_id": self.device_id,
            "name": self.name,
            "room": self.room,
            "is_on": self.is_on,
            "brightness": self.brightness,
            "color": self.color,
            "status_text": f"ON ({self.brightness}%)" if self.is_on else "OFF"
        }


class SmartThermostat(SmartDevice):
    def __init__(self, device_id: str, name: str, room: str, target_temp: float = 22.0, mode: str = "AUTO"):
        super().__init__(device_id, name, room)
        self.target_temp = target_temp
        self.ambient_temp = 21.5
        self.mode = mode

    def set_temperature(self, temp: float):
        self.target_temp = max(16.0, min(32.0, float(temp)))
        if self.target_temp > self.ambient_temp + 1.0:
            self.mode = "HEAT"
        elif self.target_temp < self.ambient_temp - 1.0:
            self.mode = "COOL"
        else:
            self.mode = "AUTO"
        self.last_updated = datetime.now()

    def get_state(self) -> Dict[str, Any]:
        return {
            "device_id": self.device_id,
            "name": self.name,
            "room": self.room,
            "target_temp": self.target_temp,
            "ambient_temp": self.ambient_temp,
            "mode": self.mode,
            "status_text": f"{self.target_temp:.1f}°C"
        }


class SmartLock(SmartDevice):
    def __init__(self, device_id: str, name: str, room: str, is_locked: bool = True):
        super().__init__(device_id, name, room)
        self.is_locked = is_locked

    def lock(self):
        self.is_locked = True
        self.last_updated = datetime.now()

    def unlock(self):
        self.is_locked = False
        self.last_updated = datetime.now()

    def toggle(self):
        self.is_locked = not self.is_locked
        self.last_updated = datetime.now()

    def get_state(self) -> Dict[str, Any]:
        return {
            "device_id": self.device_id,
            "name": self.name,
            "room": self.room,
            "is_locked": self.is_locked,
            "status_text": "LOCKED" if self.is_locked else "UNLOCKED"
        }


class EntertainmentUnit(SmartDevice):
    def __init__(self, device_id: str, name: str, room: str):
        super().__init__(device_id, name, room)
        self.is_active = False
        self.app = "None"

    def turn_on(self, app: str = "Cinema Mode"):
        self.is_active = True
        self.app = app
        self.last_updated = datetime.now()

    def turn_off(self):
        self.is_active = False
        self.app = "None"
        self.last_updated = datetime.now()

    def toggle(self):
        if self.is_active:
            self.turn_off()
        else:
            self.turn_on("Cinema Mode")

    def get_state(self) -> Dict[str, Any]:
        return {
            "device_id": self.device_id,
            "name": self.name,
            "room": self.room,
            "is_active": self.is_active,
            "app": self.app,
            "status_text": "ACTIVE" if self.is_active else "OFF"
        }


class SecurityAlarm(SmartDevice):
    def __init__(self, device_id: str, name: str, room: str):
        super().__init__(device_id, name, room)
        self.mode = "DISARMED"

    def arm(self, mode: str = "ARMED_AWAY"):
        self.mode = mode
        self.last_updated = datetime.now()

    def disarm(self):
        self.mode = "DISARMED"
        self.last_updated = datetime.now()

    def toggle(self):
        if self.mode == "DISARMED":
            self.arm("ARMED_AWAY")
        else:
            self.disarm()

    def get_state(self) -> Dict[str, Any]:
        return {
            "device_id": self.device_id,
            "name": self.name,
            "room": self.room,
            "mode": self.mode,
            "status_text": self.mode
        }


class SmartFan(SmartDevice):
    def __init__(self, device_id: str, name: str, room: str):
        super().__init__(device_id, name, room)
        self.speed = "OFF"

    def set_speed(self, speed: str):
        self.speed = speed.upper()
        self.last_updated = datetime.now()

    def turn_off(self):
        self.speed = "OFF"
        self.last_updated = datetime.now()

    def toggle(self):
        self.speed = "HIGH" if self.speed == "OFF" else "OFF"
        self.last_updated = datetime.now()

    def get_state(self) -> Dict[str, Any]:
        return {
            "device_id": self.device_id,
            "name": self.name,
            "room": self.room,
            "speed": self.speed,
            "status_text": self.speed
        }


class SmartBlinds(SmartDevice):
    def __init__(self, device_id: str, name: str, room: str):
        super().__init__(device_id, name, room)
        self.position = 100

    def open(self):
        self.position = 100
        self.last_updated = datetime.now()

    def close(self):
        self.position = 0
        self.last_updated = datetime.now()

    def set_position(self, pos: int):
        self.position = max(0, min(100, pos))
        self.last_updated = datetime.now()

    def toggle(self):
        self.position = 0 if self.position > 50 else 100
        self.last_updated = datetime.now()

    def get_state(self) -> Dict[str, Any]:
        return {
            "device_id": self.device_id,
            "name": self.name,
            "room": self.room,
            "position": self.position,
            "status_text": f"OPEN ({self.position}%)" if self.position > 0 else "CLOSED"
        }


# =============================================================================
# 2. STATE MACHINE
# =============================================================================

class SmartHomeStateMachine:
    """Manages virtual smart home device registry, transitions, and logging."""

    def __init__(self, log_filepath: str = "assistant_execution.log"):
        self.log_filepath = log_filepath
        self.devices: Dict[str, SmartDevice] = {
            "living_room_light": SmartLight("living_room_light", "Living Room Light", "living_room", brightness=0),
            "kitchen_light": SmartLight("kitchen_light", "Kitchen Light", "kitchen", brightness=0),
            "bedroom_light": SmartLight("bedroom_light", "Bedroom Light", "bedroom", brightness=0),
            "thermostat": SmartThermostat("thermostat", "Climate Thermostat", "living_room", target_temp=22.0),
            "front_door_lock": SmartLock("front_door_lock", "Front Door Lock", "front_door", is_locked=True),
            "entertainment_unit": EntertainmentUnit("entertainment_unit", "Entertainment Unit", "living_room"),
            "security_alarm": SecurityAlarm("security_alarm", "Security Alarm", "house"),
            "ceiling_fan": SmartFan("ceiling_fan", "Ceiling Fan", "living_room"),
            "window_blinds": SmartBlinds("window_blinds", "Window Blinds", "living_room")
        }

    def apply_action(self, target_or_dict: Any, action: Optional[str] = None, value: Any = None) -> str:
        """Applies an action to matching devices via dictionary or positional arguments."""
        if isinstance(target_or_dict, dict):
            return self.execute_action(target_or_dict)
        return self.execute_action({
            "target": str(target_or_dict),
            "device_or_target": str(target_or_dict),
            "action": str(action or "turn_on"),
            "value": value
        })

    def execute_action(self, action_dict: Dict[str, Any]) -> str:
        """Applies validated action dictionary to matching smart devices."""
        raw_target = str(action_dict.get("device_or_target") or action_dict.get("target") or "").lower().strip()
        act = str(action_dict.get("action", "")).lower().strip()
        val = action_dict.get("value")

        targets_to_modify = []
        if raw_target in ["all_lights", "lights", "house_lights", "all"]:
            targets_to_modify = [d for d in self.devices.values() if isinstance(d, SmartLight)]
        elif raw_target in self.devices:
            targets_to_modify = [self.devices[raw_target]]
        else:
            for d_id, dev in self.devices.items():
                if d_id in raw_target or raw_target in d_id:
                    targets_to_modify.append(dev)

        if not targets_to_modify:
            if "light" in raw_target:
                targets_to_modify = [self.devices["living_room_light"]]
            elif "temp" in raw_target or "thermostat" in raw_target or "climate" in raw_target:
                targets_to_modify = [self.devices["thermostat"]]
            elif "door" in raw_target or "lock" in raw_target:
                targets_to_modify = [self.devices["front_door_lock"]]
            elif "alarm" in raw_target or "security" in raw_target:
                targets_to_modify = [self.devices["security_alarm"]]

        transitions = []
        for dev in targets_to_modify:
            if isinstance(dev, SmartLight):
                old = f"ON ({dev.brightness}%)" if dev.is_on else "OFF"
                if act in ["turn_on", "on", "activate"]:
                    dev.turn_on(brightness=int(val) if val and str(val).isdigit() else 100)
                elif act in ["turn_off", "off", "deactivate"]:
                    dev.turn_off()
                elif act in ["set_brightness", "dim", "brighten"] and val is not None:
                    try:
                        dev.set_brightness(int(val))
                    except Exception:
                        dev.turn_on(100)
                transitions.append(f"{dev.name}: {old} -> {'ON (' + str(dev.brightness) + '%)' if dev.is_on else 'OFF'}")

            elif isinstance(dev, SmartThermostat):
                old = f"{dev.target_temp:.1f}°C ({dev.mode})"
                if val is not None:
                    try:
                        dev.set_temperature(float(val))
                    except Exception:
                        dev.set_temperature(24.0)
                elif "warm" in act or "heat" in act or "increase" in act:
                    dev.set_temperature(dev.target_temp + 2.0)
                elif "cool" in act or "decrease" in act:
                    dev.set_temperature(dev.target_temp - 2.0)
                transitions.append(f"{dev.name}: {old} -> {dev.target_temp:.1f}°C ({dev.mode})")

            elif isinstance(dev, SmartLock):
                old = "LOCKED" if dev.is_locked else "UNLOCKED"
                if act in ["lock", "close"]:
                    dev.lock()
                else:
                    dev.unlock()
                transitions.append(f"{dev.name}: {old} -> {'LOCKED' if dev.is_locked else 'UNLOCKED'}")

            elif isinstance(dev, EntertainmentUnit):
                old = "ACTIVE" if dev.is_active else "OFF"
                if act in ["turn_on", "play"]:
                    dev.turn_on()
                else:
                    dev.turn_off()
                transitions.append(f"{dev.name}: {old} -> {'ACTIVE' if dev.is_active else 'OFF'}")

            elif isinstance(dev, SecurityAlarm):
                old = dev.mode
                if act == "disarm":
                    dev.disarm()
                else:
                    dev.arm(str(val) if val else "ARMED_NIGHT")
                transitions.append(f"{dev.name}: {old} -> {dev.mode}")

            elif isinstance(dev, SmartFan):
                old = dev.speed
                if act == "turn_off":
                    dev.turn_off()
                else:
                    dev.set_speed(str(val) if val else "HIGH")
                transitions.append(f"{dev.name}: {old} -> {dev.speed}")

            elif isinstance(dev, SmartBlinds):
                old = f"{dev.position}%"
                if act == "close":
                    dev.close()
                elif act == "open":
                    dev.open()
                elif act == "set_position" and val is not None:
                    dev.set_position(int(val))
                transitions.append(f"{dev.name}: {old} -> {dev.position}%")

        return "; ".join(transitions) if transitions else f"No transition for {raw_target}"

    def log_interaction(self, voice_text: str, json_payload: Dict[str, Any], transitions: str, latency_ms: float):
        """Appends structured log entry to assistant_execution.log with ISO timestamp."""
        timestamp = datetime.now().isoformat()
        log_entry = (
            f"\n{'='*70}\n"
            f"TIMESTAMP: {timestamp}\n"
            f"VOICE TRANSCRIPTION: \"{voice_text}\"\n"
            f"PARSED JSON PAYLOAD:\n{json.dumps(json_payload, indent=2)}\n"
            f"STATE TRANSITIONS: {transitions}\n"
            f"EXECUTION LATENCY: {latency_ms:.2f} ms ({latency_ms/1000:.2f} s)\n"
            f"{'='*70}\n"
        )
        try:
            with open(self.log_filepath, "a", encoding="utf-8") as f:
                f.write(log_entry)
        except Exception as e:
            print(f"[Logging Error: {e}]")


# =============================================================================
# 3. MODERN TOP-TIER TKINTER GUI DASHBOARD
# =============================================================================

class ModernHomeDashboard(tk.Tk):
    """
    Stark Industries Cyberpunk Dark-Themed GUI Dashboard.
    Equipped with:
    - 🎙️ Live Microphone Toggle (Online / Muted)
    - 🛑 Emergency HALT / Override Button
    - Model Selection Dropdown (qwen3.5:2b, etc.)
    - Real-Time Hardware Telemetry (CPU %, RAM, Latency)
    - Interactive Clickable Device Cards
    - Instant Zero-Lag Command Dispatcher
    """

    THEME = {
        "bg_dark": "#070D18",
        "card_bg": "#0D1B2E",
        "card_border": "#1B3A60",
        "card_active": "#102C4E",
        "accent_cyan": "#00F0FF",
        "accent_green": "#00FF88",
        "accent_amber": "#FFB300",
        "accent_red": "#FF3366",
        "text_primary": "#FFFFFF",
        "text_secondary": "#7A92AD",
        "entry_bg": "#0B1626"
    }

    def __init__(
        self,
        state_machine: SmartHomeStateMachine,
        on_command_submit: Optional[Callable[[str], str]] = None,
        on_halt_clicked: Optional[Callable[[], None]] = None,
        on_mic_toggle: Optional[Callable[[], bool]] = None,
        on_model_change: Optional[Callable[[str], None]] = None
    ):
        super().__init__()
        self.state_machine = state_machine
        self.on_command_submit = on_command_submit
        self.on_halt_clicked = on_halt_clicked
        self.on_mic_toggle = on_mic_toggle
        self.on_model_change = on_model_change

        self.title("⚡ STARK INDUSTRIES — JARVIS AI WORKSTATION (APEX SMART HOME)")
        self.geometry("1180x780")
        self.minsize(980, 680)
        self.configure(bg=self.THEME["bg_dark"])

        self.device_widgets = {}
        self.is_mic_muted = False

        self._build_ui()
        self.refresh_dashboard()

        # Telemetry Polling Timer (CPU/RAM)
        self._start_telemetry_loop()

    def _build_ui(self):
        # ---------------- TOP HEADER / TELEMETRY BAR ----------------
        header_frame = tk.Frame(self, bg=self.THEME["bg_dark"], padx=18, pady=12)
        header_frame.pack(fill=tk.X)

        title_lbl = tk.Label(
            header_frame,
            text="⚡ APEX SMART HOME & PC WORKSTATION",
            font=("Helvetica", 14, "bold"),
            fg=self.THEME["accent_cyan"],
            bg=self.THEME["bg_dark"]
        )
        title_lbl.pack(side=tk.LEFT)

        sub_lbl = tk.Label(
            header_frame,
            text="| 100% OFFLINE AI HUB",
            font=("Helvetica", 9, "bold"),
            fg=self.THEME["text_secondary"],
            bg=self.THEME["bg_dark"]
        )
        sub_lbl.pack(side=tk.LEFT, padx=(6, 12))

        # Model Selector
        mod_lbl = tk.Label(header_frame, text="MODEL:", font=("Helvetica", 9, "bold"), fg=self.THEME["accent_cyan"], bg=self.THEME["bg_dark"])
        mod_lbl.pack(side=tk.LEFT, padx=(10, 4))

        self.model_combo = ttk.Combobox(
            header_frame,
            values=["jarvis-trained-model"],
            state="readonly",
            width=20,
            font=("Helvetica", 9)
        )
        self.model_combo.set("jarvis-trained-model")
        self.model_combo.bind("<<ComboboxSelected>>", self._handle_model_selected)
        self.model_combo.pack(side=tk.LEFT, padx=(0, 10))

        # HALT Emergency Override Button
        self.halt_btn = tk.Button(
            header_frame,
            text="🛑 HALT / OVERRIDE",
            font=("Helvetica", 9, "bold"),
            fg=self.THEME["accent_red"],
            bg="#2A0B14",
            activebackground=self.THEME["accent_red"],
            activeforeground="#FFFFFF",
            relief=tk.FLAT,
            bd=1,
            padx=10,
            pady=3,
            cursor="hand2",
            command=self._handle_halt_click
        )
        self.halt_btn.pack(side=tk.RIGHT, padx=4)

        # Mic Toggle Button
        self.mic_btn = tk.Button(
            header_frame,
            text="🎙️ MIC: ONLINE",
            font=("Helvetica", 9, "bold"),
            fg=self.THEME["accent_green"],
            bg="#0B2A18",
            activebackground=self.THEME["accent_green"],
            activeforeground="#000000",
            relief=tk.FLAT,
            bd=1,
            padx=10,
            pady=3,
            cursor="hand2",
            command=self._handle_mic_toggle_click
        )
        self.mic_btn.pack(side=tk.RIGHT, padx=4)

        # Telemetry CPU/RAM Badge
        self.telemetry_label = tk.Label(
            header_frame,
            text="CPU: 0% | RAM: 0 MB",
            font=("Consolas", 9, "bold"),
            fg=self.THEME["accent_cyan"],
            bg=self.THEME["card_bg"],
            padx=8,
            pady=4
        )
        self.telemetry_label.pack(side=tk.RIGHT, padx=6)

        # Assistant Status Badge
        self.status_badge = tk.Label(
            header_frame,
            text="● STANDBY (Say 'Hey Jarvis')",
            font=("Helvetica", 10, "bold"),
            fg=self.THEME["accent_cyan"],
            bg=self.THEME["card_bg"],
            padx=10,
            pady=4
        )
        self.status_badge.pack(side=tk.RIGHT, padx=6)

        # Latency Display
        self.latency_label = tk.Label(
            header_frame,
            text="⏱️ LATENCY: 0 ms",
            font=("Helvetica", 9, "bold"),
            fg=self.THEME["accent_amber"],
            bg=self.THEME["bg_dark"],
            padx=6
        )
        self.latency_label.pack(side=tk.RIGHT, padx=4)

        # Separator line
        sep = tk.Frame(self, bg=self.THEME["card_border"], height=1)
        sep.pack(fill=tk.X, padx=14, pady=(0, 10))

        # ---------------- MAIN CONTENT SPLIT (CARDS & TELEMETRY) ----------------
        main_content = tk.Frame(self, bg=self.THEME["bg_dark"], padx=14, pady=4)
        main_content.pack(fill=tk.BOTH, expand=True)

        left_grid = tk.Frame(main_content, bg=self.THEME["bg_dark"])
        left_grid.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))

        right_panel = tk.Frame(main_content, bg=self.THEME["card_bg"], padx=14, pady=12)
        right_panel.pack(side=tk.RIGHT, fill=tk.BOTH, expand=False, ipadx=10)
        right_panel.config(width=420)

        self._build_device_grid(left_grid)
        self._build_right_panel(right_panel)

        # ---------------- BOTTOM COMMAND BAR ----------------
        bottom_frame = tk.Frame(self, bg=self.THEME["entry_bg"], padx=14, pady=10)
        bottom_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=14, pady=(6, 12))

        cmd_label = tk.Label(
            bottom_frame,
            text="Voice / Text Command:",
            font=("Helvetica", 10, "bold"),
            fg=self.THEME["accent_cyan"],
            bg=self.THEME["entry_bg"]
        )
        cmd_label.pack(side=tk.LEFT, padx=(0, 10))

        self.cmd_entry = tk.Entry(
            bottom_frame,
            font=("Consolas", 11),
            bg=self.THEME["bg_dark"],
            fg=self.THEME["text_primary"],
            insertbackground=self.THEME["accent_cyan"],
            relief=tk.FLAT,
            bd=5
        )
        self.cmd_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        self.cmd_entry.bind("<Return>", lambda e: self._submit_typed_command())

        self.exec_btn = tk.Button(
            bottom_frame,
            text="EXECUTE COMMAND",
            font=("Helvetica", 9, "bold"),
            bg=self.THEME["accent_cyan"],
            fg="#000000",
            activebackground=self.THEME["accent_green"],
            activeforeground="#000000",
            relief=tk.FLAT,
            padx=14,
            pady=4,
            cursor="hand2",
            command=self._submit_typed_command
        )
        self.exec_btn.pack(side=tk.RIGHT)

    def _build_device_grid(self, parent):
        cards_info = [
            ("living_room_light", "💡 Living Room Light", "living_room"),
            ("kitchen_light", "💡 Kitchen Light", "kitchen"),
            ("bedroom_light", "💡 Bedroom Light", "bedroom"),
            ("thermostat", "🌡️ Climate Thermostat", "living_room"),
            ("front_door_lock", "🔒 Front Door Lock", "front_door"),
            ("entertainment_unit", "📺 Entertainment Unit", "living_room"),
            ("security_alarm", "🛡️ Security Alarm", "house"),
            ("ceiling_fan", "🌀 Ceiling Fan", "living_room"),
            ("window_blinds", "🪟 Window Blinds", "living_room")
        ]

        row, col = 0, 0
        for dev_id, title, room in cards_info:
            card = tk.Frame(parent, bg=self.THEME["card_bg"], padx=14, pady=10, relief=tk.FLAT, cursor="hand2")
            card.grid(row=row, column=col, sticky="nsew", padx=6, pady=6)
            parent.grid_columnconfigure(col, weight=1)
            parent.grid_rowconfigure(row, weight=1)

            # Click card to toggle device manually
            card.bind("<Button-1>", lambda e, d=dev_id: self._toggle_device_click(d))

            title_lbl = tk.Label(card, text=title, font=("Helvetica", 11, "bold"), fg=self.THEME["text_primary"], bg=self.THEME["card_bg"])
            title_lbl.pack(anchor="w")
            title_lbl.bind("<Button-1>", lambda e, d=dev_id: self._toggle_device_click(d))

            status_lbl = tk.Label(card, text="OFF", font=("Helvetica", 13, "bold"), fg=self.THEME["text_secondary"], bg=self.THEME["card_bg"])
            status_lbl.pack(anchor="w", pady=(4, 2))
            status_lbl.bind("<Button-1>", lambda e, d=dev_id: self._toggle_device_click(d))

            detail_lbl = tk.Label(card, text="State: Standby", font=("Helvetica", 9), fg=self.THEME["text_secondary"], bg=self.THEME["card_bg"])
            detail_lbl.pack(anchor="w")
            detail_lbl.bind("<Button-1>", lambda e, d=dev_id: self._toggle_device_click(d))

            self.device_widgets[dev_id] = {
                "card": card,
                "status_lbl": status_lbl,
                "detail_lbl": detail_lbl
            }

            col += 1
            if col > 2:
                col = 0
                row += 1

    def _build_right_panel(self, parent):
        log_title = tk.Label(
            parent,
            text="📋 LIVE EXECUTION TELEMETRY",
            font=("Helvetica", 11, "bold"),
            fg=self.THEME["accent_cyan"],
            bg=self.THEME["card_bg"]
        )
        log_title.pack(anchor="w", pady=(0, 6))

        self.log_text = tk.Text(
            parent,
            bg=self.THEME["bg_dark"],
            fg=self.THEME["accent_green"],
            font=("Consolas", 9),
            relief=tk.FLAT,
            bd=4,
            wrap=tk.WORD,
            height=26,
            width=48
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)

        self.log_console("⚡ STARK JARVIS AI Hub Initialized.")
        self.log_console("🧠 Ollama Qwen 3.5 (2B): ONLINE")
        self.log_console("🔊 British Jarvis (Edge-TTS en-GB-RyanNeural): READY")
        self.log_console("🎙️ Acoustic Gating: LISTENING FOR 'JARVIS'...")

    def log_console(self, text: str):
        """Appends timestamped event into telemetry text box."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {text}\n")
        self.log_text.see(tk.END)

    def log_event(self, text: str):
        """Alias for log_console."""
        self.log_console(text)

    def update_status(self, text: str, color: Optional[str] = None):
        """Directly updates the assistant status badge."""
        c = color or self.THEME["accent_cyan"]
        self.status_badge.config(text=text, fg=c)

    def set_assistant_status(self, status: str, detail: str = ""):
        color_map = {
            "STANDBY": (self.THEME["accent_cyan"], "● STANDBY (Say 'Hey Jarvis')"),
            "WAKE_DETECTED": (self.THEME["accent_green"], "⚡ WAKE WORD DETECTED!"),
            "LISTENING_CMD": (self.THEME["accent_green"], "🎤 LISTENING FOR COMMAND..."),
            "PROCESSING": (self.THEME["accent_amber"], "🧠 OLLAMA PARSING INTENT..."),
            "SPEAKING": (self.THEME["accent_cyan"], "🔊 SPEAKING CONFIRMATION...")
        }
        color, default_text = color_map.get(status, (self.THEME["accent_cyan"], f"● {status}"))
        text = f"{default_text} {detail}" if detail else default_text
        self.status_badge.config(text=text, fg=color)
        if detail:
            self.log_console(f"[{status}] {detail}")

    def update_latency_display(self, latency_ms: float):
        color = self.THEME["accent_green"] if latency_ms < 2000 else self.THEME["accent_amber"]
        self.latency_label.config(text=f"⏱️ LATENCY: {latency_ms:.0f} ms", fg=color)

    def _start_telemetry_loop(self):
        """Periodically polls CPU % and RAM to display live workstation telemetry."""
        def _poll():
            while True:
                try:
                    cpu = psutil.cpu_percent(interval=None)
                    ram_mb = int(psutil.Process().memory_info().rss / (1024 * 1024))
                    self.after(0, lambda: self.telemetry_label.config(text=f"CPU: {cpu:.0f}% | RAM: {ram_mb} MB"))
                except Exception:
                    pass
                time.sleep(2.0)

        t = threading.Thread(target=_poll, daemon=True)
        t.start()

    def _handle_halt_click(self):
        """Emergency HALT button click."""
        self.log_console("🛑 EMERGENCY OVERRIDE: Speech HALTED by user.")
        self.update_status("● STANDBY (Emergency Override)", self.THEME["accent_red"])
        if self.on_halt_clicked:
            self.on_halt_clicked()

    def _handle_mic_toggle_click(self):
        """Mutes or unmutes hardware microphone."""
        if self.on_mic_toggle:
            is_muted = self.on_mic_toggle()
            self.is_mic_muted = is_muted
            if is_muted:
                self.mic_btn.config(text="🔇 MIC: MUTED", fg=self.THEME["accent_red"], bg="#2A0B14")
                self.log_console("🔇 Microphone Hardware: MUTED")
            else:
                self.mic_btn.config(text="🎙️ MIC: ONLINE", fg=self.THEME["accent_green"], bg="#0B2A18")
                self.log_console("🎙️ Microphone Hardware: ONLINE")

    def _handle_model_selected(self, event=None):
        selected_model = self.model_combo.get()
        self.log_console(f"🧠 AI Model switched to: {selected_model}")
        if self.on_model_change:
            self.on_model_change(selected_model)

    def _toggle_device_click(self, dev_id: str):
        """Allows direct GUI interaction to toggle devices manually."""
        if dev_id in self.state_machine.devices:
            dev = self.state_machine.devices[dev_id]
            if hasattr(dev, "toggle"):
                dev.toggle()
                self.refresh_dashboard()
                self.log_console(f"🖐️ MANUAL TOGGLE: {dev.name} -> {dev.get_state().get('status_text')}")

    def _submit_typed_command(self):
        """Asynchronous, zero-lag submission of typed text command."""
        text = self.cmd_entry.get().strip()
        if not text:
            return

        self.cmd_entry.delete(0, tk.END)
        self.log_console(f"⌨️ USER (Typed): \"{text}\"")
        self.update_status("🧠 OLLAMA PARSING INTENT...", self.THEME["accent_amber"])

        # Execute on background worker thread to prevent freezing the GUI!
        if self.on_command_submit:
            def _worker():
                self.on_command_submit(text)

            threading.Thread(target=_worker, daemon=True).start()

    def refresh_dashboard(self):
        """Synchronizes GUI card visuals with device state machine."""
        for dev_id, dev in self.state_machine.devices.items():
            if dev_id not in self.device_widgets:
                continue

            widgets = self.device_widgets[dev_id]

            if isinstance(dev, SmartLight):
                if dev.is_on:
                    widgets["status_lbl"].config(text=f"ON ({dev.brightness}%)", fg=self.THEME["accent_green"])
                    widgets["detail_lbl"].config(text=f"Color: {dev.color} | Level: {dev.brightness}%")
                    widgets["card"].config(bg=self.THEME["card_active"])
                else:
                    widgets["status_lbl"].config(text="OFF", fg=self.THEME["text_secondary"])
                    widgets["detail_lbl"].config(text="Light is powered off")
                    widgets["card"].config(bg=self.THEME["card_bg"])

            elif isinstance(dev, SmartThermostat):
                temp_color = self.THEME["accent_amber"] if dev.mode == "HEAT" else (self.THEME["accent_cyan"] if dev.mode == "COOL" else self.THEME["accent_green"])
                widgets["status_lbl"].config(text=f"{dev.target_temp:.1f}°C", fg=temp_color)
                widgets["detail_lbl"].config(text=f"Ambient: {dev.ambient_temp:.1f}°C | Mode: {dev.mode}")
                widgets["card"].config(bg=self.THEME["card_active"] if dev.mode != "AUTO" else self.THEME["card_bg"])

            elif isinstance(dev, SmartLock):
                if dev.is_locked:
                    widgets["status_lbl"].config(text="LOCKED", fg=self.THEME["accent_green"])
                    widgets["detail_lbl"].config(text="Perimeter door secured")
                    widgets["card"].config(bg=self.THEME["card_bg"])
                else:
                    widgets["status_lbl"].config(text="UNLOCKED", fg=self.THEME["accent_red"])
                    widgets["detail_lbl"].config(text="⚠️ Door unlocked")
                    widgets["card"].config(bg="#2A0F1A")

            elif isinstance(dev, EntertainmentUnit):
                if dev.is_active:
                    widgets["status_lbl"].config(text="ACTIVE", fg=self.THEME["accent_cyan"])
                    widgets["detail_lbl"].config(text=f"App: {dev.app}")
                    widgets["card"].config(bg=self.THEME["card_active"])
                else:
                    widgets["status_lbl"].config(text="OFF", fg=self.THEME["text_secondary"])
                    widgets["detail_lbl"].config(text="Display Standby")
                    widgets["card"].config(bg=self.THEME["card_bg"])

            elif isinstance(dev, SecurityAlarm):
                if dev.mode == "DISARMED":
                    widgets["status_lbl"].config(text="DISARMED", fg=self.THEME["accent_amber"])
                    widgets["detail_lbl"].config(text="System Disarmed")
                    widgets["card"].config(bg=self.THEME["card_bg"])
                else:
                    widgets["status_lbl"].config(text=dev.mode, fg=self.THEME["accent_green"])
                    widgets["detail_lbl"].config(text="Perimeter: Secure")
                    widgets["card"].config(bg=self.THEME["card_active"])

            elif isinstance(dev, SmartFan):
                if dev.speed == "OFF":
                    widgets["status_lbl"].config(text="OFF", fg=self.THEME["text_secondary"])
                    widgets["detail_lbl"].config(text="Fan Speed: OFF")
                    widgets["card"].config(bg=self.THEME["card_bg"])
                else:
                    widgets["status_lbl"].config(text=f"ON ({dev.speed})", fg=self.THEME["accent_cyan"])
                    widgets["detail_lbl"].config(text=f"Speed: {dev.speed}")
                    widgets["card"].config(bg=self.THEME["card_active"])

            elif isinstance(dev, SmartBlinds):
                if dev.position > 0:
                    widgets["status_lbl"].config(text=f"OPEN ({dev.position}%)", fg=self.THEME["accent_cyan"])
                    widgets["detail_lbl"].config(text=f"Position: {dev.position}%")
                    widgets["card"].config(bg=self.THEME["card_active"])
                else:
                    widgets["status_lbl"].config(text="CLOSED", fg=self.THEME["text_secondary"])
                    widgets["detail_lbl"].config(text="Position: 0% (Closed)")
                    widgets["card"].config(bg=self.THEME["card_bg"])
