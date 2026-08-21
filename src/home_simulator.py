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
import math
import re
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
        t_val = float(temp)
        # If model outputs Fahrenheit comfort values (65°F to 89°F), convert to integer Celsius (18°C to 30°C)
        if 65.0 <= t_val <= 89.0:
            c_conv = (t_val - 32.0) * 5.0 / 9.0
            t_val = round(c_conv)
            if 70.0 <= float(temp) <= 75.0 and t_val <= int(self.ambient_temp):
                t_val = int(self.ambient_temp) + 2  # Boost to comfortable heating (e.g. 24°C)
        else:
            t_val = round(t_val)

        # Support extended temperature safety range (10°C to 60°C) with pure whole integer display (no decimals)
        self.target_temp = float(max(10, min(60, int(t_val))))
        if self.target_temp > self.ambient_temp + 0.5:
            self.mode = "HEAT"
        elif self.target_temp < self.ambient_temp - 0.5:
            self.mode = "COOL"
        else:
            self.mode = "AUTO"
        self.last_updated = datetime.now()

    def toggle(self):
        """Allows manual UI click to cycle temperature targets."""
        if self.target_temp >= 28.0:
            self.set_temperature(18.0)
        else:
            self.set_temperature(self.target_temp + 2.0)

    def get_state(self) -> Dict[str, Any]:
        return {
            "device_id": self.device_id,
            "name": self.name,
            "room": self.room,
            "target_temp": int(round(self.target_temp)),
            "ambient_temp": int(round(self.ambient_temp)),
            "mode": self.mode,
            "status_text": f"{int(round(self.target_temp))}°C"
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

    def open(self, position: int = 100):
        self.position = max(0, min(100, position))
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
        self.last_queried_device: str = "bedroom_light"
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

    def get_summary_text(self) -> str:
        """Returns a concise text summary of all device states for LLM context and status queries."""
        items = []
        for d_id, dev in self.devices.items():
            state = dev.get_state()
            items.append(f"{dev.name}: {state.get('status_text', 'UNKNOWN')}")
        return ", ".join(items)

    def query_device_status(self, query: str) -> Optional[str]:
        """
        Directly queries and returns natural spoken status of a requested smart home device.
        Handles queries like 'is the bedroom light on', 'is the front door locked', etc.
        """
        q = query.lower().strip()
        is_query_intent = any(k in q for k in [
            "is the", "is it", "are the", "are any", "status", "check", "tell me if",
            "what is", "how is", "open or", "on or", "locked or", "closed or", "open on", "?"
        ]) or q.startswith("is ") or q.startswith("are ") or q.startswith("what ")

        if not is_query_intent and not any(k in q for k in ["status", "telemetry", "state"]):
            return None

        # 1. Specific Room Lights
        if "bedroom" in q:
            self.last_queried_device = "bedroom_light"
            dev = self.devices["bedroom_light"]
            return f"The bedroom light is currently {'on at ' + str(dev.brightness) + '% brightness' if dev.is_on else 'powered off'}, sir."

        if "kitchen" in q:
            self.last_queried_device = "kitchen_light"
            dev = self.devices["kitchen_light"]
            return f"The kitchen light is currently {'on at ' + str(dev.brightness) + '% brightness' if dev.is_on else 'powered off'}, sir."

        if "living room" in q or "livingroom" in q:
            self.last_queried_device = "living_room_light"
            dev = self.devices["living_room_light"]
            return f"The living room light is currently {'on at ' + str(dev.brightness) + '% brightness' if dev.is_on else 'powered off'}, sir."

        # 2. General / All Lights
        if "light" in q or "lights" in q:
            on_lights = [d.name for d in self.devices.values() if isinstance(d, SmartLight) and d.is_on]
            if on_lights:
                return f"Currently, {', '.join(on_lights)} {'is' if len(on_lights)==1 else 'are'} on, sir."
            return "All smart lights in the house are currently powered off, sir."

        # 3. Thermostat / Temperature / Climate
        if any(w in q for w in ["thermostat", "temp", "temperature", "climate", "ac", "degrees"]):
            self.last_queried_device = "thermostat"
            dev = self.devices["thermostat"]
            return f"The thermostat is currently set to {dev.target_temp:.1f}°C in {dev.mode} mode, with an ambient temperature of {dev.ambient_temp:.1f}°C."

        # 4. Front Door Lock
        if any(w in q for w in ["door", "front door", "deadbolt", "lock"]):
            self.last_queried_device = "front_door_lock"
            dev = self.devices["front_door_lock"]
            return f"The front door is currently {'locked and secured' if dev.is_locked else 'unlocked'}, sir."

        # 5. Security Alarm
        if any(w in q for w in ["alarm", "security", "perimeter", "defense"]):
            self.last_queried_device = "security_alarm"
            dev = self.devices["security_alarm"]
            return f"The security alarm system is currently {dev.mode.lower()}, sir."

        # 6. Ceiling Fan
        if any(w in q for w in ["fan", "ceiling fan"]):
            self.last_queried_device = "ceiling_fan"
            dev = self.devices["ceiling_fan"]
            return f"The ceiling fan is currently {dev.speed.lower()}, sir."

        # 7. Window Blinds
        if any(w in q for w in ["blind", "blinds", "window", "curtain"]):
            self.last_queried_device = "window_blinds"
            dev = self.devices["window_blinds"]
            return f"The window blinds are currently {'open at ' + str(dev.position) + '%' if dev.position > 0 else 'closed'}, sir."

        # 8. Entertainment Unit
        if any(w in q for w in ["entertainment", "tv", "display", "theater"]):
            self.last_queried_device = "entertainment_unit"
            dev = self.devices["entertainment_unit"]
            return f"The entertainment unit is currently {'active' if dev.is_active else 'powered off'}, sir."

        # 9. Contextual pronoun follow-up ('is it open', 'is it on or off', 'is it open or not')
        if any(w in q for w in ["is it", "it is", "open or not", "on or off", "locked or"]):
            dev = self.devices.get(self.last_queried_device, self.devices["bedroom_light"])
            if isinstance(dev, SmartLight):
                return f"The {dev.name.lower()} is currently {'on at ' + str(dev.brightness) + '% brightness' if dev.is_on else 'powered off'}, sir."
            elif isinstance(dev, SmartLock):
                return f"The {dev.name.lower()} is currently {'locked and secured' if dev.is_locked else 'unlocked'}, sir."
            elif isinstance(dev, SmartBlinds):
                return f"The {dev.name.lower()} are currently {'open at ' + str(dev.position) + '%' if dev.position > 0 else 'closed'}, sir."
            elif isinstance(dev, SmartThermostat):
                return f"The thermostat is currently set to {dev.target_temp:.1f}°C in {dev.mode} mode, with an ambient temperature of {dev.ambient_temp:.1f}°C."

        # 10. General House Overview / Status
        if any(w in q for w in ["house status", "home status", "telemetry", "everything", "overview", "what is on"]):
            return f"Smart home status overview: {self.get_summary_text()}."

        return None

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

        t_clean = raw_target.replace(" ", "_").replace("-", "_")

        targets_to_modify = []
        if t_clean in ["all_lights", "lights", "house_lights", "all", "all_light"]:
            targets_to_modify = [d for d in self.devices.values() if isinstance(d, SmartLight)]
        elif t_clean in self.devices:
            targets_to_modify = [self.devices[t_clean]]
        elif "kitchen" in t_clean:
            targets_to_modify = [self.devices["kitchen_light"]]
        elif "bedroom" in t_clean:
            targets_to_modify = [self.devices["bedroom_light"]]
        elif "living" in t_clean:
            targets_to_modify = [self.devices["living_room_light"]]
        elif any(k in t_clean for k in ["thermostat", "temp", "climate", "ac", "degrees"]):
            targets_to_modify = [self.devices["thermostat"]]
        elif any(k in t_clean for k in ["door", "lock", "front_door", "deadbolt"]):
            targets_to_modify = [self.devices["front_door_lock"]]
        elif any(k in t_clean for k in ["alarm", "security", "perimeter"]):
            targets_to_modify = [self.devices["security_alarm"]]
        elif any(k in t_clean for k in ["fan", "ceiling"]):
            targets_to_modify = [self.devices["ceiling_fan"]]
        elif any(k in t_clean for k in ["blind", "blinds", "window", "curtain"]):
            targets_to_modify = [self.devices["window_blinds"]]
        elif any(k in t_clean for k in ["entertainment", "tv", "display", "theater"]):
            targets_to_modify = [self.devices["entertainment_unit"]]
        else:
            for d_id, dev in self.devices.items():
                if d_id in t_clean or t_clean in d_id:
                    targets_to_modify.append(dev)

        if not targets_to_modify:
            if "light" in t_clean:
                targets_to_modify = [self.devices["living_room_light"]]
            elif "temp" in t_clean or "thermostat" in t_clean:
                targets_to_modify = [self.devices["thermostat"]]
            elif "door" in t_clean or "lock" in t_clean:
                targets_to_modify = [self.devices["front_door_lock"]]
            elif "alarm" in t_clean or "security" in t_clean:
                targets_to_modify = [self.devices["security_alarm"]]

        transitions = []
        for dev in targets_to_modify:
            if isinstance(dev, SmartLight):
                old = f"ON ({dev.brightness}%)" if dev.is_on else "OFF"
                is_turn_off = (
                    any(k in act for k in ["off", "deactivate", "disable", "shut", "zero", "power_to_zero", "extinguish", "darken"])
                    or (val is not None and (val == 0 or str(val) == "0" or str(val).lower() in ["off", "0%"]))
                )
                is_turn_on = any(k in act for k in ["on", "activate", "enable", "illuminate", "light"])
                is_brightness = any(k in act for k in ["brightness", "dim", "brighten", "level", "set"])

                if is_turn_off:
                    dev.turn_off()
                elif is_turn_on:
                    b_val = 100
                    if val is not None and str(val).isdigit():
                        b_val = int(val)
                    dev.turn_on(brightness=b_val)
                elif is_brightness and val is not None:
                    try:
                        b_int = int(val)
                        if b_int <= 0:
                            dev.turn_off()
                        else:
                            dev.set_brightness(b_int)
                    except Exception:
                        dev.turn_on(100)
                else:
                    if "toggle" in act:
                        dev.toggle()
                    else:
                        dev.turn_on(100)
                transitions.append(f"{dev.name}: {old} -> {'ON (' + str(dev.brightness) + '%)' if dev.is_on else 'OFF'}")

            elif isinstance(dev, SmartThermostat):
                old = f"{int(round(dev.target_temp))}°C ({dev.mode})"
                v_str = str(val).lower() if val is not None else ""

                if any(k in v_str for k in ["increase", "raise", "warm", "heat", "up", "warmer"]) or any(k in act for k in ["warm", "heat", "increase", "raise", "up"]):
                    dev.set_temperature(dev.target_temp + 2.0)
                elif any(k in v_str for k in ["decrease", "lower", "cool", "drop", "down", "cooler", "cold"]) or any(k in act for k in ["cool", "decrease", "lower", "drop", "down", "cooldown"]):
                    dev.set_temperature(dev.target_temp - 2.0)
                elif val is not None:
                    m = re.search(r'[-+]?\d*\.?\d+', str(val))
                    if m:
                        dev.set_temperature(float(m.group(0)))
                    else:
                        dev.set_temperature(20.0)
                else:
                    if any(k in act for k in ["cool", "cooler", "cooldown"]):
                        dev.set_temperature(20.0)
                    elif any(k in act for k in ["warm", "heat", "warmer"]):
                        dev.set_temperature(24.0)
                    else:
                        dev.set_temperature(22.0)
                transitions.append(f"{dev.name}: {old} -> {int(round(dev.target_temp))}°C ({dev.mode})")

            elif isinstance(dev, SmartLock):
                old = "LOCKED" if dev.is_locked else "UNLOCKED"
                if any(k in act for k in ["unlock", "open", "unsecure", "disengage"]) or (val is not None and str(val).lower() in ["unlock", "open", "unsecured"]):
                    dev.unlock()
                elif any(k in act for k in ["lock", "secure", "close", "engage"]) or (val is not None and str(val).lower() in ["lock", "close", "secured"]):
                    dev.lock()
                else:
                    dev.lock()
                transitions.append(f"{dev.name}: {old} -> {'LOCKED' if dev.is_locked else 'UNLOCKED'}")

            elif isinstance(dev, EntertainmentUnit):
                old = "ACTIVE" if dev.is_active else "OFF"
                if any(k in act for k in ["off", "stop", "deactivate", "standby", "close", "shut"]):
                    dev.turn_off()
                elif any(k in act for k in ["on", "start", "activate", "play", "open", "launch"]):
                    dev.turn_on(app=str(val) if val else "YouTube")
                else:
                    dev.turn_on()
                transitions.append(f"{dev.name}: {old} -> {'ACTIVE' if dev.is_active else 'OFF'}")

            elif isinstance(dev, SecurityAlarm):
                old = dev.mode
                if any(k in act for k in ["disarm", "off", "deactivate", "disable", "stop"]):
                    dev.disarm()
                elif any(k in act for k in ["arm", "on", "activate", "enable"]):
                    dev.arm(str(val) if val else "ARMED_AWAY")
                else:
                    dev.arm("ARMED_AWAY")
                transitions.append(f"{dev.name}: {old} -> {dev.mode}")

            elif isinstance(dev, SmartFan):
                old = dev.speed
                is_fan_off = (
                    any(k in act for k in ["off", "stop", "deactivate", "disable", "shut"])
                    or val in [0, "0", "0%", "off", "OFF", 0.0]
                    or (str(val).isdigit() and int(val) == 0)
                )
                if is_fan_off:
                    dev.turn_off()
                elif any(k in act for k in ["on", "start", "activate", "speed", "set"]):
                    spd = str(val).upper() if val and str(val).upper() in ["LOW", "MEDIUM", "HIGH"] else "HIGH"
                    dev.set_speed(spd)
                else:
                    dev.set_speed("HIGH")
                transitions.append(f"{dev.name}: {old} -> {dev.speed}")

            elif isinstance(dev, SmartBlinds):
                old = f"{dev.position}%"
                if any(k in act for k in ["close", "shut", "down", "lower", "off", "turn_off", "deactivate"]) or val == 0:
                    dev.close()
                elif any(k in act for k in ["open", "up", "raise", "on", "turn_on", "activate"]):
                    pos = int(val) if val and str(val).isdigit() else 100
                    dev.open(position=pos)
                elif val is not None:
                    try:
                        dev.set_position(int(val))
                    except Exception:
                        dev.open()
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
# 3. MODERN TOP-TIER TKINTER GUI DASHBOARD (STARK CYBERPUNK WORKSTATION)
# =============================================================================

class ModernHomeDashboard(tk.Tk):
    """
    Stark Industries Cyberpunk Dark-Themed GUI Dashboard.
    Features:
    - ⚡ Top Navigation & Telemetry Bar: Brand, Status badge, Model Selector, Latency, CPU/RAM, Mic toggle, HALT override, Clear Chat
    - 🎛️ Left Sidebar Hub: Quick Scenario Presets (Movie Night, Goodnight, Leaving, Comfort, Spotify, YouTube, Lock PC) & Grouped Device Controls
    - 💬 Center/Right Viewport: Pulsing Arc Reactor Visualizer & Much Bigger, Highly Readable Chat / Execution Log
    - ⌨️ Bottom Command Bar: Full-width input with Execute and Voice triggers
    """

    THEME = {
        "bg_dark": "#050B14",
        "header_bg": "#091424",
        "sidebar_bg": "#081220",
        "card_bg": "#0C1B2F",
        "card_border": "#163458",
        "card_active": "#10325A",
        "accent_cyan": "#00F0FF",
        "accent_green": "#00FF88",
        "accent_amber": "#FFB300",
        "accent_red": "#FF3366",
        "accent_purple": "#BD00FF",
        "text_primary": "#FFFFFF",
        "text_secondary": "#7D98B6",
        "entry_bg": "#071222",
        "console_bg": "#040912"
    }

    def __init__(
        self,
        state_machine: SmartHomeStateMachine,
        on_command_submit: Optional[Callable[[str], str]] = None,
        on_halt_clicked: Optional[Callable[[], None]] = None,
        on_mic_toggle: Optional[Callable[[], bool]] = None,
        on_model_change: Optional[Callable[[str], None]] = None,
        on_voice_trigger: Optional[Callable[[], None]] = None
    ):
        super().__init__()
        self.state_machine = state_machine
        self.on_command_submit = on_command_submit
        self.on_halt_clicked = on_halt_clicked
        self.on_mic_toggle = on_mic_toggle
        self.on_model_change = on_model_change
        self.on_voice_trigger = on_voice_trigger

        self.title("⚡ STARK INDUSTRIES — PROJECT JARVIS v2.0 (APEX SMART HOME & PC SUITE)")
        self.geometry("1300x840")
        self.minsize(1050, 720)
        self.configure(bg=self.THEME["bg_dark"])

        self.device_widgets = {}
        self.is_mic_muted = False
        self._reactor_angle = 0
        self._current_status_state = "STANDBY"
        self._pulse_val = 0.0
        self._pulse_dir = 1

        self._build_ui()
        self.refresh_dashboard()

        # Start Telemetry Loop & Robot AI Avatar Animation
        self._start_telemetry_loop()
        self._animate_robot_avatar()

    def _build_ui(self):
        # ---------------- 1. TOP HEADER & TELEMETRY BAR ----------------
        top_bar = tk.Frame(self, bg=self.THEME["header_bg"], padx=16, pady=10, relief=tk.FLAT, bd=0)
        top_bar.pack(fill=tk.X, side=tk.TOP)

        # Brand / Title
        brand_frame = tk.Frame(top_bar, bg=self.THEME["header_bg"])
        brand_frame.pack(side=tk.LEFT)

        title_lbl = tk.Label(
            brand_frame,
            text="⚡ STARK INDUSTRIES",
            font=("Segoe UI", 13, "bold"),
            fg=self.THEME["accent_cyan"],
            bg=self.THEME["header_bg"]
        )
        title_lbl.pack(side=tk.LEFT)

        sub_lbl = tk.Label(
            brand_frame,
            text="JARVIS WORKSTATION v2.0",
            font=("Segoe UI", 9, "bold"),
            fg=self.THEME["text_secondary"],
            bg=self.THEME["header_bg"]
        )
        sub_lbl.pack(side=tk.LEFT, padx=(6, 14))

        # Model Selector
        mod_lbl = tk.Label(
            top_bar,
            text="AI ENGINE:",
            font=("Consolas", 9, "bold"),
            fg=self.THEME["accent_cyan"],
            bg=self.THEME["header_bg"]
        )
        mod_lbl.pack(side=tk.LEFT, padx=(4, 4))

        self.model_combo = ttk.Combobox(
            top_bar,
            values=["jarvis-trained-model", "qwen2.5:1.5b"],
            state="readonly",
            width=20,
            font=("Consolas", 9)
        )
        self.model_combo.set("jarvis-trained-model")
        self.model_combo.bind("<<ComboboxSelected>>", self._handle_model_selected)
        self.model_combo.pack(side=tk.LEFT, padx=(0, 14))

        # Action Buttons on Right
        self.halt_btn = tk.Button(
            top_bar,
            text="🛑 HALT / OVERRIDE",
            font=("Segoe UI", 9, "bold"),
            fg=self.THEME["accent_red"],
            bg="#2B0A14",
            activebackground=self.THEME["accent_red"],
            activeforeground="#FFFFFF",
            relief=tk.FLAT,
            bd=1,
            padx=12,
            pady=4,
            cursor="hand2",
            command=self._handle_halt_click
        )
        self.halt_btn.pack(side=tk.RIGHT, padx=4)

        self.mic_btn = tk.Button(
            top_bar,
            text="🎙️ MIC: ONLINE",
            font=("Segoe UI", 9, "bold"),
            fg=self.THEME["accent_green"],
            bg="#082516",
            activebackground=self.THEME["accent_green"],
            activeforeground="#000000",
            relief=tk.FLAT,
            bd=1,
            padx=10,
            pady=4,
            cursor="hand2",
            command=self._handle_mic_toggle_click
        )
        self.mic_btn.pack(side=tk.RIGHT, padx=4)

        self.clear_btn = tk.Button(
            top_bar,
            text="🧹 CLEAR",
            font=("Segoe UI", 9, "bold"),
            fg=self.THEME["text_secondary"],
            bg="#0B1A2E",
            activebackground=self.THEME["card_active"],
            activeforeground="#FFFFFF",
            relief=tk.FLAT,
            bd=1,
            padx=10,
            pady=4,
            cursor="hand2",
            command=self._clear_console
        )
        self.clear_btn.pack(side=tk.RIGHT, padx=4)

        # Telemetry CPU/RAM Badge
        self.telemetry_label = tk.Label(
            top_bar,
            text="CPU: 0% | RAM: 0 MB",
            font=("Consolas", 9, "bold"),
            fg=self.THEME["accent_cyan"],
            bg=self.THEME["card_bg"],
            padx=8,
            pady=4
        )
        self.telemetry_label.pack(side=tk.RIGHT, padx=6)

        # Latency Display
        self.latency_label = tk.Label(
            top_bar,
            text="⏱️ LATENCY: 0 ms",
            font=("Consolas", 9, "bold"),
            fg=self.THEME["accent_amber"],
            bg=self.THEME["header_bg"],
            padx=6
        )
        self.latency_label.pack(side=tk.RIGHT, padx=4)

        # Assistant Status Badge
        self.status_badge = tk.Label(
            top_bar,
            text="● STANDBY (Say 'Hey Jarvis')",
            font=("Segoe UI", 10, "bold"),
            fg=self.THEME["accent_cyan"],
            bg=self.THEME["card_bg"],
            padx=12,
            pady=4
        )
        self.status_badge.pack(side=tk.RIGHT, padx=6)

        # Separator line under header
        sep = tk.Frame(self, bg=self.THEME["card_border"], height=1)
        sep.pack(fill=tk.X, side=tk.TOP)

        # ---------------- 2. BOTTOM COMMAND BAR ----------------
        bottom_frame = tk.Frame(self, bg=self.THEME["entry_bg"], padx=14, pady=10)
        bottom_frame.pack(fill=tk.X, side=tk.BOTTOM, padx=12, pady=(4, 10))

        cmd_label = tk.Label(
            bottom_frame,
            text="⚡ COMMAND:",
            font=("Segoe UI", 10, "bold"),
            fg=self.THEME["accent_cyan"],
            bg=self.THEME["entry_bg"]
        )
        cmd_label.pack(side=tk.LEFT, padx=(4, 10))

        self.cmd_entry = tk.Entry(
            bottom_frame,
            font=("Consolas", 11),
            bg=self.THEME["bg_dark"],
            fg=self.THEME["text_primary"],
            insertbackground=self.THEME["accent_cyan"],
            relief=tk.FLAT,
            bd=6
        )
        self.cmd_entry.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))
        self.cmd_entry.bind("<Return>", lambda e: self._submit_typed_command())

        self.exec_btn = tk.Button(
            bottom_frame,
            text="🚀 EXECUTE",
            font=("Segoe UI", 9, "bold"),
            bg=self.THEME["accent_cyan"],
            fg="#000000",
            activebackground=self.THEME["accent_green"],
            activeforeground="#000000",
            relief=tk.FLAT,
            padx=16,
            pady=5,
            cursor="hand2",
            command=self._submit_typed_command
        )
        self.exec_btn.pack(side=tk.RIGHT, padx=(0, 4))

        self.voice_trigger_btn = tk.Button(
            bottom_frame,
            text="🎙️ SPEAK NOW",
            font=("Segoe UI", 9, "bold"),
            bg="#082A1A",
            fg=self.THEME["accent_green"],
            activebackground=self.THEME["accent_green"],
            activeforeground="#000000",
            relief=tk.FLAT,
            padx=12,
            pady=5,
            cursor="hand2",
            command=lambda: self._submit_preset_voice_prompt()
        )
        self.voice_trigger_btn.pack(side=tk.RIGHT, padx=6)

        # ---------------- 3. MAIN WORKSPACE SPLIT (LEFT SIDEBAR & CENTER CHAT) ----------------
        main_workspace = tk.Frame(self, bg=self.THEME["bg_dark"], padx=10, pady=6)
        main_workspace.pack(fill=tk.BOTH, expand=True, side=tk.TOP)

        # Left Sidebar (Features, Presets & Device Hub)
        sidebar = tk.Frame(main_workspace, bg=self.THEME["sidebar_bg"], padx=12, pady=10, width=380)
        sidebar.pack(side=tk.LEFT, fill=tk.BOTH, expand=False, padx=(0, 8))
        sidebar.pack_propagate(False)

        # Right / Center Main Viewport (Arc Reactor Visualizer + Bigger Chat Box)
        center_panel = tk.Frame(main_workspace, bg=self.THEME["bg_dark"])
        center_panel.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        self._build_sidebar(sidebar)
        self._build_center_chat(center_panel)

    def _build_sidebar(self, parent):
        # Header for Presets
        lbl_presets = tk.Label(
            parent,
            text="⚡ QUICK SCENARIOS & APPS",
            font=("Segoe UI", 10, "bold"),
            fg=self.THEME["accent_cyan"],
            bg=self.THEME["sidebar_bg"]
        )
        lbl_presets.pack(anchor="w", pady=(2, 6))

        # Presets 2x4 Grid
        presets_frame = tk.Frame(parent, bg=self.THEME["sidebar_bg"])
        presets_frame.pack(fill=tk.X, pady=(0, 10))

        preset_items = [
            ("🎬 Movie Night", "movie night mode"),
            ("🌙 Goodnight", "goodnight jarvis"),
            ("🚶 Leaving Home", "heading out lock my pc and lock the door"),
            ("❄️ Comfort Mode", "it is freezing and dark in here"),
            ("🎵 Open Spotify", "open spotify app"),
            ("📺 Open YouTube", "open youtube and search for lofi beats"),
            ("🔒 Lock Workstation", "lock my pc"),
            ("🌐 Open Browser", "open chrome")
        ]

        p_row, p_col = 0, 0
        for label, cmd in preset_items:
            btn = tk.Button(
                presets_frame,
                text=label,
                font=("Segoe UI", 8, "bold"),
                bg=self.THEME["card_bg"],
                fg=self.THEME["text_primary"],
                activebackground=self.THEME["card_active"],
                activeforeground=self.THEME["accent_cyan"],
                relief=tk.FLAT,
                bd=1,
                padx=6,
                pady=4,
                cursor="hand2",
                command=lambda c=cmd: self._trigger_preset(c)
            )
            btn.grid(row=p_row, column=p_col, sticky="ew", padx=3, pady=3)
            presets_frame.grid_columnconfigure(p_col, weight=1)
            p_col += 1
            if p_col > 1:
                p_col = 0
                p_row += 1

        # Header for Devices
        lbl_devices = tk.Label(
            parent,
            text="🎛️ SMART HOME & SYSTEM HUB",
            font=("Segoe UI", 10, "bold"),
            fg=self.THEME["accent_cyan"],
            bg=self.THEME["sidebar_bg"]
        )
        lbl_devices.pack(anchor="w", pady=(8, 6))

        # Scrollable container for Device Cards
        devices_container = tk.Frame(parent, bg=self.THEME["sidebar_bg"])
        devices_container.pack(fill=tk.BOTH, expand=True)

        devices_canvas = tk.Canvas(devices_container, bg=self.THEME["sidebar_bg"], highlightthickness=0)
        devices_scrollbar = ttk.Scrollbar(devices_container, orient="vertical", command=devices_canvas.yview)
        scrollable_device_frame = tk.Frame(devices_canvas, bg=self.THEME["sidebar_bg"])

        scrollable_device_frame.bind(
            "<Configure>",
            lambda e: devices_canvas.configure(scrollregion=devices_canvas.bbox("all"))
        )
        canvas_window = devices_canvas.create_window((0, 0), window=scrollable_device_frame, anchor="nw", width=345)
        devices_canvas.configure(yscrollcommand=devices_scrollbar.set)

        def _on_canvas_resize(event):
            if event.width > 20:
                devices_canvas.itemconfig(canvas_window, width=event.width - 4)

        devices_canvas.bind("<Configure>", _on_canvas_resize)

        devices_canvas.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        devices_scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self._populate_device_cards(scrollable_device_frame)
        self._bind_mousewheel_to_all(devices_container, devices_canvas)
        self._bind_mousewheel_to_all(scrollable_device_frame, devices_canvas)
        self._bind_mousewheel_to_all(parent, devices_canvas)

    def _bind_mousewheel_to_all(self, widget, canvas):
        """Recursively binds mouse wheel event to widget and all descendants for smooth scrolling."""
        def _on_mousewheel(event):
            try:
                canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")
            except Exception:
                pass
        try:
            widget.bind("<MouseWheel>", _on_mousewheel, add="+")
            for child in widget.winfo_children():
                self._bind_mousewheel_to_all(child, canvas)
        except Exception:
            pass

    def _populate_device_cards(self, parent):
        cards_info = [
            ("living_room_light", "💡 Living Room Light", "smart_home"),
            ("kitchen_light", "💡 Kitchen Light", "smart_home"),
            ("bedroom_light", "💡 Bedroom Light", "smart_home"),
            ("thermostat", "🌡️ Climate Thermostat", "smart_home"),
            ("front_door_lock", "🔒 Front Door Lock", "smart_home"),
            ("entertainment_unit", "📺 Entertainment Unit", "smart_home"),
            ("security_alarm", "🛡️ Security Alarm", "smart_home"),
            ("ceiling_fan", "🌀 Ceiling Fan", "smart_home"),
            ("window_blinds", "🪟 Window Blinds", "smart_home")
        ]

        for dev_id, title, domain in cards_info:
            card = tk.Frame(parent, bg=self.THEME["card_bg"], padx=10, pady=8, relief=tk.FLAT, bd=1, cursor="hand2")
            card.pack(fill=tk.X, pady=4)
            card.bind("<Button-1>", lambda e, d=dev_id: self._toggle_device_click(d))

            top_row = tk.Frame(card, bg=self.THEME["card_bg"])
            top_row.pack(fill=tk.X)
            top_row.bind("<Button-1>", lambda e, d=dev_id: self._toggle_device_click(d))

            title_lbl = tk.Label(top_row, text=title, font=("Segoe UI", 9, "bold"), fg=self.THEME["text_primary"], bg=self.THEME["card_bg"])
            title_lbl.pack(side=tk.LEFT)
            title_lbl.bind("<Button-1>", lambda e, d=dev_id: self._toggle_device_click(d))

            status_lbl = tk.Label(top_row, text="OFF", font=("Consolas", 10, "bold"), fg=self.THEME["text_secondary"], bg=self.THEME["card_bg"])
            status_lbl.pack(side=tk.RIGHT)
            status_lbl.bind("<Button-1>", lambda e, d=dev_id: self._toggle_device_click(d))

            detail_lbl = tk.Label(card, text="State: Standby", font=("Segoe UI", 8), fg=self.THEME["text_secondary"], bg=self.THEME["card_bg"])
            detail_lbl.pack(anchor="w", pady=(2, 0))
            detail_lbl.bind("<Button-1>", lambda e, d=dev_id: self._toggle_device_click(d))

            self.device_widgets[dev_id] = {
                "card": card,
                "status_lbl": status_lbl,
                "detail_lbl": detail_lbl
            }

    def _build_center_chat(self, parent):
        # 1. Animated Robotic AI Avatar Canvas (Speaking & Emotion Visualizer)
        visualizer_frame = tk.Frame(parent, bg=self.THEME["bg_dark"], height=175)
        visualizer_frame.pack(fill=tk.X, side=tk.TOP, pady=(0, 6))
        visualizer_frame.pack_propagate(False)

        self.reactor_canvas = tk.Canvas(
            visualizer_frame,
            bg=self.THEME["header_bg"],
            height=170,
            highlightthickness=1,
            highlightbackground=self.THEME["card_border"]
        )
        self.reactor_canvas.pack(fill=tk.BOTH, expand=True)

        # 2. Enlarged Chat / Telemetry Console Box (DOMINANT VIEWPORT)
        chat_frame = tk.Frame(parent, bg=self.THEME["console_bg"], bd=1, relief=tk.FLAT)
        chat_frame.pack(fill=tk.BOTH, expand=True, side=tk.TOP)

        chat_header = tk.Frame(chat_frame, bg=self.THEME["card_bg"], padx=10, pady=4)
        chat_header.pack(fill=tk.X)

        chat_title = tk.Label(
            chat_header,
            text="💬 LIVE CONVERSATION & AGENTIC ACTION DISPATCH",
            font=("Segoe UI", 9, "bold"),
            fg=self.THEME["accent_cyan"],
            bg=self.THEME["card_bg"]
        )
        chat_title.pack(side=tk.LEFT)

        self.chat_count_lbl = tk.Label(
            chat_header,
            text="0 Interactions",
            font=("Consolas", 8),
            fg=self.THEME["text_secondary"],
            bg=self.THEME["card_bg"]
        )
        self.chat_count_lbl.pack(side=tk.RIGHT)

        # Chat Text Box with Scrollbar
        self.log_text = tk.Text(
            chat_frame,
            bg=self.THEME["console_bg"],
            fg=self.THEME["text_primary"],
            font=("Consolas", 10),
            relief=tk.FLAT,
            bd=8,
            wrap=tk.WORD,
            padx=10,
            pady=10
        )
        chat_scroll = ttk.Scrollbar(chat_frame, orient="vertical", command=self.log_text.yview)
        self.log_text.configure(yscrollcommand=chat_scroll.set)

        chat_scroll.pack(side=tk.RIGHT, fill=tk.Y)
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # Configure custom colored tags
        self.log_text.tag_config("tag_time", foreground="#5E7896", font=("Consolas", 9))
        self.log_text.tag_config("tag_user", foreground="#00FF88", font=("Consolas", 10, "bold"))
        self.log_text.tag_config("tag_jarvis", foreground="#00F0FF", font=("Consolas", 10, "bold"))
        self.log_text.tag_config("tag_action", foreground="#BD00FF", font=("Consolas", 10))
        self.log_text.tag_config("tag_perf", foreground="#FFB300", font=("Consolas", 9, "bold"))
        self.log_text.tag_config("tag_system", foreground="#7D98B6", font=("Consolas", 9, "italic"))
        self.log_text.tag_config("tag_alert", foreground="#FF3366", font=("Consolas", 10, "bold"))

        self._msg_count = 0
        self._robot_frame = 0
        self._blink_counter = 0
        self._is_blinking = False
        self._speech_phase = 0.0

        self.log_console("⚡ STARK JARVIS AI Hub Online. Robotic Avatar Visualizer Active.")
        self.log_console("🧠 Ollama Engine (jarvis-trained-model / Qwen 2.5): READY")
        self.log_console("🔊 British Jarvis Speech Output (Edge-TTS en-GB-RyanNeural): ONLINE")
        self.log_console("🎙️ Hardware Acoustic Gate: LISTENING FOR 'HEY JARVIS'...")

    def _animate_robot_avatar(self):
        """
        Draws high-tech, futuristic animated Robot AI Avatar on canvas.
        Features:
        - Animated cybernetic head, cheek armor, and ear acoustic nodes with bouncing equalizer bars.
        - Expressive glowing optic eyes with natural blinking, scanning laser, and reasoning reticles.
        - Articulating speaking mouth with realistic jaw opening & multi-bar vocal equalizer matrix!
        - Dynamic state transitions (STANDBY, LISTENING, REASONING, SPEAKING, HALTED).
        """
        try:
            self.reactor_canvas.delete("all")
            w = self.reactor_canvas.winfo_width()
            h = self.reactor_canvas.winfo_height()
            if w < 50 or h < 50:
                w, h = 850, 170

            cx, cy = w // 2, (h // 2) - 4
            self._robot_frame += 1

            # State Color Palette
            state_palettes = {
                "STANDBY": {
                    "primary": "#00F0FF",
                    "secondary": "#0080FF",
                    "plate_bg": "#09172B",
                    "plate_border": "#163B66",
                    "eye_glow": "#00F0FF",
                    "mouth_glow": "#00F0FF",
                    "label": "STANDBY // READY"
                },
                "LISTENING": {
                    "primary": "#00FF88",
                    "secondary": "#00AA55",
                    "plate_bg": "#082218",
                    "plate_border": "#145638",
                    "eye_glow": "#00FF88",
                    "mouth_glow": "#00FF88",
                    "label": "LISTENING TO VOICE..."
                },
                "REASONING": {
                    "primary": "#BD00FF",
                    "secondary": "#8000AA",
                    "plate_bg": "#1C0A28",
                    "plate_border": "#4F196B",
                    "eye_glow": "#BD00FF",
                    "mouth_glow": "#BD00FF",
                    "label": "REASONING // QWEN LLM"
                },
                "SPEAKING": {
                    "primary": "#00F0FF",
                    "secondary": "#00FF88",
                    "plate_bg": "#0B2038",
                    "plate_border": "#215890",
                    "eye_glow": "#FFFFFF",
                    "mouth_glow": "#00FF88",
                    "label": "SPEAKING RESPONSE..."
                },
                "HALTED": {
                    "primary": "#FF3366",
                    "secondary": "#AA1133",
                    "plate_bg": "#280A14",
                    "plate_border": "#6B192A",
                    "eye_glow": "#FF3366",
                    "mouth_glow": "#FF3366",
                    "label": "EMERGENCY HALTED"
                }
            }

            p = state_palettes.get(self._current_status_state, state_palettes["STANDBY"])
            primary_c = p["primary"]
            secondary_c = p["secondary"]
            plate_bg = p["plate_bg"]
            plate_border = p["plate_border"]
            eye_c = p["eye_glow"]
            mouth_c = p["mouth_glow"]

            # Subtle breathing vertical bob
            breathe_y = math.sin(self._robot_frame * 0.08) * 1.5
            cy += breathe_y

            # ---------------- 1. BACKGROUND HUD GRID & AMBIENT WAVES ----------------
            # Tech grid lines radiating from sides
            self.reactor_canvas.create_line(30, cy - 25, cx - 110, cy - 25, fill="#102540", width=1)
            self.reactor_canvas.create_line(cx + 110, cy - 25, w - 30, cy - 25, fill="#102540", width=1)
            self.reactor_canvas.create_line(40, cy + 25, cx - 105, cy + 25, fill="#102540", width=1)
            self.reactor_canvas.create_line(cx + 105, cy + 25, w - 40, cy + 25, fill="#102540", width=1)

            # Circular holographic halo behind head
            halo_r = int(72 + math.sin(self._robot_frame * 0.1) * 3)
            self.reactor_canvas.create_oval(cx - halo_r, cy - halo_r + 4, cx + halo_r, cy + halo_r + 4, outline="#112B4C", width=1)
            self.reactor_canvas.create_arc(cx - halo_r - 6, cy - halo_r - 2, cx + halo_r + 6, cy + halo_r + 10, start=(self._robot_frame * 2) % 360, extent=45, outline=secondary_c, width=1, style=tk.ARC)
            self.reactor_canvas.create_arc(cx - halo_r - 6, cy - halo_r - 2, cx + halo_r + 6, cy + halo_r + 10, start=(self._robot_frame * 2 + 180) % 360, extent=45, outline=secondary_c, width=1, style=tk.ARC)

            # ---------------- 2. ROBOTIC EAR ACOUSTIC NODES (LEFT & RIGHT) ----------------
            # Left Ear Node
            self.reactor_canvas.create_polygon(
                [cx - 96, cy - 20, cx - 84, cy - 28, cx - 84, cy + 24, cx - 96, cy + 16],
                fill=plate_bg, outline=primary_c, width=2
            )
            # Right Ear Node
            self.reactor_canvas.create_polygon(
                [cx + 84, cy - 28, cx + 96, cy - 20, cx + 96, cy + 16, cx + 84, cy + 24],
                fill=plate_bg, outline=primary_c, width=2
            )

            # Ear Equalizer LEDs
            for i in range(3):
                eq_val = abs(math.sin(self._robot_frame * 0.22 + i * 1.1)) * (14 if self._current_status_state == "SPEAKING" else 7)
                # Left ear LEDs
                self.reactor_canvas.create_line(cx - 93 + i * 3, cy - eq_val / 2, cx - 93 + i * 3, cy + eq_val / 2, fill=primary_c, width=2)
                # Right ear LEDs
                self.reactor_canvas.create_line(cx + 87 + i * 3, cy - eq_val / 2, cx + 87 + i * 3, cy + eq_val / 2, fill=primary_c, width=2)

            # ---------------- 3. ROBOTIC HEAD / CHASSIS SKULL ----------------
            head_pts = [
                cx - 50, cy - 54,  # top flat left
                cx + 50, cy - 54,  # top flat right
                cx + 78, cy - 30,  # upper temple right
                cx + 82, cy + 6,   # cheek right
                cx + 58, cy + 46,  # jaw right
                cx + 26, cy + 58,  # chin right
                cx - 26, cy + 58,  # chin left
                cx - 58, cy + 46,  # jaw left
                cx - 82, cy + 6,   # cheek left
                cx - 78, cy - 30   # upper temple left
            ]
            self.reactor_canvas.create_polygon(head_pts, fill=plate_bg, outline=plate_border, width=2)

            # Cheek Armor Plates
            self.reactor_canvas.create_polygon(
                [cx - 75, cy - 10, cx - 50, cy - 6, cx - 44, cy + 34, cx - 68, cy + 30],
                fill="#071220", outline=plate_border, width=1
            )
            self.reactor_canvas.create_polygon(
                [cx + 50, cy - 6, cx + 75, cy - 10, cx + 68, cy + 30, cx + 44, cy + 34],
                fill="#071220", outline=plate_border, width=1
            )

            # ---------------- 4. FOREHEAD STARK AI CORE & SENSORS ----------------
            # Forehead Arc Gem
            self.reactor_canvas.create_polygon(
                [cx - 16, cy - 50, cx + 16, cy - 50, cx + 10, cy - 38, cx - 10, cy - 38],
                fill="#050E1A", outline=primary_c, width=1
            )
            core_pulse = 3 + math.sin(self._robot_frame * 0.15) * 1.5
            self.reactor_canvas.create_oval(cx - core_pulse, cy - 44 - core_pulse, cx + core_pulse, cy - 44 + core_pulse, fill=primary_c, outline="#FFFFFF")

            # Forehead tech markings
            self.reactor_canvas.create_line(cx - 40, cy - 46, cx - 22, cy - 46, fill=primary_c, width=1)
            self.reactor_canvas.create_line(cx + 22, cy - 46, cx + 40, cy - 46, fill=primary_c, width=1)

            # ---------------- 5. CYBER-OPTIC ROBOT EYES & VISOR ----------------
            # Blinking logic: Periodic robotic blink every ~100 frames
            self._blink_counter += 1
            if self._blink_counter > 110:
                self._is_blinking = True
            if self._blink_counter > 116:
                self._is_blinking = False
                self._blink_counter = 0

            eye_y = cy - 12
            eye_w = 26
            eye_h = 13 if not self._is_blinking else 2

            # Left Eye Socket & Lens
            left_eye_cx = cx - 35
            self.reactor_canvas.create_polygon(
                [left_eye_cx - 18, eye_y, left_eye_cx - 10, eye_y - eye_h, left_eye_cx + 14, eye_y - eye_h, left_eye_cx + 18, eye_y, left_eye_cx + 12, eye_y + eye_h, left_eye_cx - 12, eye_y + eye_h],
                fill="#030810", outline=primary_c, width=2
            )

            # Right Eye Socket & Lens
            right_eye_cx = cx + 35
            self.reactor_canvas.create_polygon(
                [right_eye_cx - 18, eye_y, right_eye_cx - 12, eye_y - eye_h, right_eye_cx + 10, eye_y - eye_h, right_eye_cx + 18, eye_y, right_eye_cx + 14, eye_y + eye_h, right_eye_cx - 10, eye_y + eye_h],
                fill="#030810", outline=primary_c, width=2
            )

            if not self._is_blinking:
                # Glowing Optic Pupils
                pupil_r = 5 if self._current_status_state != "REASONING" else 4
                self.reactor_canvas.create_oval(left_eye_cx - pupil_r, eye_y - pupil_r, left_eye_cx + pupil_r, eye_y + pupil_r, fill=eye_c, outline=primary_c)
                self.reactor_canvas.create_oval(right_eye_cx - pupil_r, eye_y - pupil_r, right_eye_cx + pupil_r, eye_y + pupil_r, fill=eye_c, outline=primary_c)

                # Listening Scanline Animation
                if self._current_status_state == "LISTENING":
                    scan_x = math.sin(self._robot_frame * 0.25) * 12
                    self.reactor_canvas.create_line(left_eye_cx + scan_x - 4, eye_y - 8, left_eye_cx + scan_x + 4, eye_y + 8, fill="#00FF88", width=2)
                    self.reactor_canvas.create_line(right_eye_cx + scan_x - 4, eye_y - 8, right_eye_cx + scan_x + 4, eye_y + 8, fill="#00FF88", width=2)

                # Reasoning Targeting Reticles
                elif self._current_status_state == "REASONING":
                    r_angle = (self._robot_frame * 12) % 360
                    self.reactor_canvas.create_arc(left_eye_cx - 8, eye_y - 8, left_eye_cx + 8, eye_y + 8, start=r_angle, extent=120, outline=primary_c, width=1, style=tk.ARC)
                    self.reactor_canvas.create_arc(right_eye_cx - 8, eye_y - 8, right_eye_cx + 8, eye_y + 8, start=(r_angle + 180) % 360, extent=120, outline=primary_c, width=1, style=tk.ARC)

            # ---------------- 6. ANIMATED ROBOTIC SPEAKING MOUTH & VOCALIZER MATRIX ----------------
            mouth_y = cy + 28

            if self._current_status_state == "SPEAKING":
                # Advance Speech Phase for organic phoneme cadence
                self._speech_phase += 0.32

                # Articulated Jaw Opening (Smooth phonetic opening and closing)
                open_factor = (abs(math.sin(self._speech_phase * 2.2)) * 0.7 + abs(math.cos(self._speech_phase * 3.6)) * 0.3)
                jaw_drop = int(5 + 14 * open_factor)

                # Upper Cyber-Lip Bar
                self.reactor_canvas.create_line(cx - 28, mouth_y - 2, cx + 28, mouth_y - 2, fill=primary_c, width=2)

                # Open Metallic Mouth Cavity
                self.reactor_canvas.create_polygon(
                    [cx - 26, mouth_y, cx + 26, mouth_y, cx + 20, mouth_y + jaw_drop, cx - 20, mouth_y + jaw_drop],
                    fill="#02060C", outline=plate_border, width=1
                )

                # Lower Articulated Jaw Plate
                self.reactor_canvas.create_line(cx - 22, mouth_y + jaw_drop, cx + 22, mouth_y + jaw_drop, fill=primary_c, width=3)

                # 7-Segment Animated Robotic Vocalizer Equalizer Bars inside Mouth!
                num_bars = 7
                for i in range(num_bars):
                    bx = cx - 18 + i * 6
                    bar_energy = abs(math.sin(self._speech_phase * 2.8 + i * 0.9)) * 0.8 + 0.2
                    bar_h = max(2, int((jaw_drop - 2) * bar_energy))
                    self.reactor_canvas.create_line(bx, mouth_y + 2, bx, mouth_y + 2 + bar_h, fill=mouth_c, width=2)

                # Lateral Acoustic Vocal Ripple Waves (Radiating from Mouth Corners)
                ripple_1 = int(abs(math.sin(self._speech_phase * 2.0)) * 16)
                ripple_2 = int(abs(math.sin(self._speech_phase * 2.0 + 1.2)) * 24)
                self.reactor_canvas.create_arc(cx - 40 - ripple_1, mouth_y - 10, cx - 26 - ripple_1, mouth_y + 14, start=120, extent=120, outline=primary_c, width=2, style=tk.ARC)
                self.reactor_canvas.create_arc(cx + 26 + ripple_1, mouth_y - 10, cx + 40 + ripple_1, mouth_y + 14, start=300, extent=120, outline=primary_c, width=2, style=tk.ARC)
                if ripple_2 > 8:
                    self.reactor_canvas.create_arc(cx - 48 - ripple_2, mouth_y - 14, cx - 30 - ripple_2, mouth_y + 18, start=120, extent=120, outline=secondary_c, width=1, style=tk.ARC)
                    self.reactor_canvas.create_arc(cx + 30 + ripple_2, mouth_y - 14, cx + 48 + ripple_2, mouth_y + 18, start=300, extent=120, outline=secondary_c, width=1, style=tk.ARC)

            else:
                # Closed Standby / Listening / Reasoning Vocal Slit with Glowing Micro-LEDs
                self.reactor_canvas.create_line(cx - 26, mouth_y, cx + 26, mouth_y, fill=primary_c, width=2)
                for i in range(5):
                    lx = cx - 18 + i * 9
                    self.reactor_canvas.create_oval(lx - 1.5, mouth_y - 1.5, lx + 1.5, mouth_y + 1.5, fill=mouth_c, outline="")

            # ---------------- 7. HUD TELEMETRY & LABELS ----------------
            # Top-Left Telemetry
            self.reactor_canvas.create_text(25, 18, text="SYS // JARVIS AI CORE", fill="#4E6D91", font=("Consolas", 8, "bold"), anchor="w")
            self.reactor_canvas.create_text(25, 32, text="VOCAL DUPLEX SYNTHESIZER: ACTIVE", fill="#395270", font=("Consolas", 7), anchor="w")

            # Top-Right Telemetry
            self.reactor_canvas.create_text(w - 25, 18, text="SILERO VAD // MONITORING", fill="#4E6D91", font=("Consolas", 8, "bold"), anchor="e")
            self.reactor_canvas.create_text(w - 25, 32, text="OPTIC SENSORS: 60 FPS SYNC", fill="#395270", font=("Consolas", 7), anchor="e")

            # Center Bottom Avatar State Label
            self.reactor_canvas.create_text(cx, cy + 74, text=f"ROBOT AVATAR: {p['label']}", fill=primary_c, font=("Consolas", 9, "bold"))

        except Exception:
            pass

        self.after(40, self._animate_robot_avatar)

    # Alias for backward compatibility
    _animate_arc_reactor = _animate_robot_avatar

    def log_console(self, text: str):
        """Appends formatted timestamped message to chat log with custom styling tags."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        self._msg_count += 1
        self.chat_count_lbl.config(text=f"{self._msg_count} Events")

        self.log_text.insert(tk.END, f"[{timestamp}] ", "tag_time")

        if "User Command:" in text or "USER" in text or "WAKE + COMMAND:" in text:
            self.log_text.insert(tk.END, f"{text}\n", "tag_user")
        elif "Jarvis:" in text:
            self.log_text.insert(tk.END, f"{text}\n", "tag_jarvis")
        elif "ACTION PLAN:" in text or "⚡" in text or "PC Action:" in text or "Smart Home:" in text:
            self.log_text.insert(tk.END, f"{text}\n", "tag_action")
        elif "LATENCY:" in text or "⏱️" in text:
            self.log_text.insert(tk.END, f"{text}\n", "tag_perf")
        elif "HALT" in text or "🛑" in text:
            self.log_text.insert(tk.END, f"{text}\n", "tag_alert")
        else:
            self.log_text.insert(tk.END, f"{text}\n", "tag_system")

        self.log_text.see(tk.END)

    def log_event(self, text: str):
        """Alias for log_console."""
        self.log_console(text)

    def _clear_console(self):
        """Clears the console log."""
        self.log_text.delete("1.0", tk.END)
        self._msg_count = 0
        self.chat_count_lbl.config(text="0 Events")
        self.log_console("🧹 Chat and Telemetry Console Cleared.")

    def update_status(self, text: str, color: Optional[str] = None):
        """Directly updates the assistant status badge and reactor animation state."""
        c = color or self.THEME["accent_cyan"]
        self.status_badge.config(text=f"● {text}", fg=c)

        # Update reactor state category
        t_upper = text.upper()
        if "LISTENING" in t_upper:
            self._current_status_state = "LISTENING"
        elif "REASONING" in t_upper or "PARSING" in t_upper:
            self._current_status_state = "REASONING"
        elif "SPEAKING" in t_upper:
            self._current_status_state = "SPEAKING"
        elif "HALT" in t_upper:
            self._current_status_state = "HALTED"
        else:
            self._current_status_state = "STANDBY"

    def set_assistant_status(self, status: str, detail: str = ""):
        color_map = {
            "STANDBY": (self.THEME["accent_cyan"], "STANDBY (Say 'Hey Jarvis')"),
            "WAKE_DETECTED": (self.THEME["accent_green"], "WAKE WORD DETECTED!"),
            "LISTENING_CMD": (self.THEME["accent_green"], "LISTENING FOR COMMAND..."),
            "PROCESSING": (self.THEME["accent_amber"], "OLLAMA PARSING INTENT..."),
            "SPEAKING": (self.THEME["accent_cyan"], "SPEAKING CONFIRMATION...")
        }
        color, default_text = color_map.get(status, (self.THEME["accent_cyan"], status))
        text = f"{default_text} {detail}" if detail else default_text
        self.update_status(text, color)
        if detail:
            self.log_console(f"[{status}] {detail}")

    def update_latency_display(self, latency_ms: float):
        color = self.THEME["accent_green"] if latency_ms < 2500 else self.THEME["accent_amber"]
        self.latency_label.config(text=f"⏱️ LATENCY: {latency_ms:.0f} ms", fg=color)

    def update_latency(self, latency_ms: float):
        """Alias for update_latency_display."""
        self.update_latency_display(latency_ms)

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
        self.log_console("🛑 EMERGENCY OVERRIDE: Speech and execution HALTED by user.")
        self.update_status("STANDBY (Emergency Override)", self.THEME["accent_red"])
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
                self.mic_btn.config(text="🎙️ MIC: ONLINE", fg=self.THEME["accent_green"], bg="#082516")
                self.log_console("🎙️ Microphone Hardware: ONLINE")

    def _handle_model_selected(self, event=None):
        selected_model = self.model_combo.get()
        self.log_console(f"🧠 AI Model switched to: '{selected_model}'")
        if self.on_model_change:
            self.on_model_change(selected_model)

    def _trigger_preset(self, command_text: str):
        """Triggers a quick scenario preset command."""
        self.cmd_entry.delete(0, tk.END)
        self.cmd_entry.insert(0, command_text)
        self._submit_typed_command()

    def _submit_preset_voice_prompt(self):
        """Triggers immediate single-turn voice command capture."""
        self.update_status("LISTENING (Speak now...)", self.THEME["accent_green"])
        self.log_console("🎙️ [VOICE]: Microphone active. Speak your command clearly (e.g. 'open spotify', 'turn on light')...")
        if self.on_voice_trigger:
            threading.Thread(target=self.on_voice_trigger, daemon=True).start()

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
        self.update_status("REASONING (Ollama LLM)...", self.THEME["accent_amber"])

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
                widgets["status_lbl"].config(text=f"{int(round(dev.target_temp))}°C", fg=temp_color)
                widgets["detail_lbl"].config(text=f"Ambient: {int(round(dev.ambient_temp))}°C | Mode: {dev.mode}")
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

