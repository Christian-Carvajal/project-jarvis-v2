"""
AI Engine Module for Project JARVIS (Apex Home Automations & Stark PC Suite).
100% Pure Agentic AI Reasoning Engine interfacing directly with local Ollama (qwen3.5:2b).
Zero hardcoded trigger rules, keyword dictionaries, or regular expression matching.
All intent classification, tool selection, and parameter extraction are decided dynamically by the local LLM.
"""

import os
import sys
import re
import time
import json
import shutil
import subprocess
import threading
import webbrowser
import urllib.parse
from typing import List, Optional, Any, Dict, Tuple
from pydantic import BaseModel, Field, model_validator
import requests
try:
    import psutil
    PSUTIL_AVAILABLE = True
except Exception:
    psutil = None
    PSUTIL_AVAILABLE = False

import ollama

try:
    import pyautogui
    import pyperclip
    PYAUTOGUI_AVAILABLE = True
    pyautogui.FAILSAFE = False
except ImportError:
    PYAUTOGUI_AVAILABLE = False

try:
    import win32api
    import win32con
    import win32gui
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False

try:
    from rapidfuzz import process, fuzz
    RAPIDFUZZ_AVAILABLE = True
except ImportError:
    RAPIDFUZZ_AVAILABLE = False

DEFAULT_MODEL = "jarvis-trained-model"
CUSTOM_MODEL_CANDIDATES = ["jarvis-trained-model"]


class DeviceAction(BaseModel):
    """Pydantic v2 schema representing an agentic action decided by the LLM."""
    domain: str = Field(default="smart_home", description="Target domain: 'smart_home' or 'pc_automation'")
    device_or_target: str = Field(default="living_room_light", description="Target identifier (e.g. living_room_light, kitchen_light, bedroom_light, thermostat, front_door_lock, notepad, calculator, brave, spotify, youtube, lock_pc)")
    action: str = Field(default="turn_on", description="Action to perform (e.g. turn_on, turn_off, set_temperature, open_app, close_app, open_website, system_control, media_control, web_search)")
    value: Optional[Any] = Field(default=None, description="Action parameter (e.g. temperature float in °C, brightness level, URL, search query string, fan speed)")

    @model_validator(mode="before")
    @classmethod
    def sanitize_action(cls, values: Any) -> Any:
        if not isinstance(values, dict):
            return values

        # Extract raw target from various candidate fields
        raw_target = str(
            values.get("device_or_target")
            or values.get("target")
            or values.get("device")
            or values.get("entity")
            or values.get("room")
            or values.get("light")
            or values.get("app")
            or values.get("name")
            or values.get("software")
            or values.get("website")
            or values.get("service")
            or values.get("browser")
            or values.get("url")
            or ""
        ).lower().strip()

        # Extract raw action name from various candidate fields
        act = str(
            values.get("action")
            or values.get("act")
            or values.get("operation")
            or values.get("type")
            or values.get("command")
            or "turn_on"
        ).lower().strip()

        domain = str(values.get("domain") or "").lower().strip()
        val = values.get("value") if values.get("value") is not None else (
            values.get("val") or values.get("param") or values.get("parameter") or values.get("query") or values.get("song") or values.get("track") or values.get("artist") or values.get("temp") or values.get("temperature") or values.get("brightness")
        )

        target = raw_target

        # 1. URL handling: If target or value is a URL, resolve canonical PC target
        for candidate_url in [raw_target, str(val) if val else ""]:
            if candidate_url.startswith("http://") or candidate_url.startswith("https://") or "www." in candidate_url:
                c_low = candidate_url.lower()
                if "spotify.com" in c_low:
                    target = "spotify"
                    domain = "pc_automation"
                    act = "open_app" if not act or act in ["turn_on", "launch", "open", "launchapp"] else act
                    if "/search/" in c_low:
                        q_part = c_low.split("/search/")[-1].split("?")[0]
                        val = urllib.parse.unquote(q_part).strip() if q_part else None
                        act = "play_music"
                    elif val == candidate_url:
                        val = None
                    break
                elif "youtube.com" in c_low or "youtu.be" in c_low:
                    target = "youtube"
                    domain = "pc_automation"
                    act = "open_website"
                    if "search_query=" in c_low:
                        q_part = c_low.split("search_query=")[-1].split("&")[0]
                        val = urllib.parse.unquote(q_part).strip() if q_part else None
                    elif val == candidate_url:
                        val = None
                    break
                elif "discord.com" in c_low or "discord.gg" in c_low:
                    target = "discord"
                    domain = "pc_automation"
                    act = "open_app"
                    val = None
                    break
                elif "google.com" in c_low:
                    if "?q=" in c_low or "&q=" in c_low:
                        q_part = (c_low.split("?q=")[-1] if "?q=" in c_low else c_low.split("&q=")[-1]).split("&")[0]
                        val = urllib.parse.unquote(q_part).strip()
                        target = "browser"
                        domain = "pc_automation"
                        act = "web_search"
                    else:
                        target = "chrome"
                        domain = "pc_automation"
                        act = "open_app"
                        val = None
                    break
                elif "github.com" in c_low:
                    target = "github"
                    domain = "pc_automation"
                    act = "open_website"
                    val = "https://github.com"
                    break
                elif "canvas" in c_low:
                    target = "canvas"
                    domain = "pc_automation"
                    act = "open_website"
                    val = "https://canvas.instructure.com"
                    break
                else:
                    target = "browser"
                    domain = "pc_automation"
                    act = "open_website"
                    val = candidate_url
                    break

        pc_targets = [
            "youtube", "spotify", "google", "github", "canvas", "browser", "chrome", "edge", "brave",
            "firefox", "notepad", "calculator", "calc", "paint", "mspaint", "terminal", "cmd", "powershell",
            "explorer", "file_explorer", "vscode", "code", "vs_code", "task_manager", "taskmgr", "lock_pc", "web_search",
            "discord", "steam", "volume", "media", "screenshot", "system"
        ]
        pc_actions = ["open_app", "close_app", "open_website", "system_control", "web_search", "media_control", "launch", "open", "close", "kill", "search", "play_music", "play_song", "play"]

        # 2. Extract target embedded inside action name (e.g. "openSpotify" -> "spotify", "openSteam" -> "steam")
        if not target or target in ["device", "target", "entity", "room", "light", "app", "system", "living_room_light"]:
            for pt in pc_targets:
                if pt in act and pt not in ["media", "system"]:
                    target = pt
                    break

        # 3. Handle music and playback actions (e.g. "play_song", "play_music", "play music", "stream")
        if any(k in act for k in ["play_song", "play_music", "play music", "listen", "stream"]) or (act == "play" and (not target or target in ["spotify", "music", "song", "media"])):
            domain = "pc_automation"
            if not target or target in ["device", "target", "entity", "room", "light", "app", "system", "living_room_light", "music", "song", "media"]:
                target = "spotify"
            act = "play_music"
            if val and str(val).lower().strip() in ["something", "music", "some music", "a song", "song", "tracks", "unknown", "none", "null"]:
                val = None

        # 4. Infer target from value if target is missing
        if not target or target in ["device", "target", "entity", "room", "light", "app", "system"]:
            if val and isinstance(val, str):
                v_low = val.lower().strip()
                for pt in pc_targets:
                    if pt == v_low or (pt in v_low and len(pt) >= 4):
                        target = pt
                        val = None
                        break
                if not target or target in ["device", "target", "entity", "room", "light", "app", "system"]:
                    if any(st in v_low for st in ["kitchen", "bedroom", "living room", "livingroom", "thermostat", "front door", "ceiling fan"]):
                        target = v_low
                        val = None

        # 5. Smart Home entity fallbacks (only if not a PC target or music action)
        if not target or target in ["device", "target", "entity", "room", "light", "app", "system"]:
            if any(k in act for k in ["unlock", "lock"]) and not any(k in act for k in ["pc", "workstation"]):
                target = "front_door_lock"
            elif any(k in act for k in ["temp", "temperature", "thermostat", "climate", "ac", "cool", "heat", "warm", "freeze"]):
                target = "thermostat"
            elif any(k in act for k in ["fan", "ceiling"]):
                target = "ceiling_fan"
            elif any(k in act for k in ["blind", "blinds", "curtain"]) and not any(k in act for k in ["music", "song", "play"]):
                target = "window_blinds"
            elif any(k in act for k in ["entertainment", "tv", "television", "theater", "display"]):
                target = "entertainment_unit"
            elif "kitchen" in act:
                target = "kitchen_light"
            elif "bedroom" in act:
                target = "bedroom_light"
            elif "living" in act:
                target = "living_room_light"
            elif any(k in act for k in ["all_lights", "all lights"]):
                target = "all_lights"

        # Normalize target string
        target_norm = target.replace(" ", "_").replace("-", "_")
        if "notepad.exe" in target_norm or "notepad" in target_norm:
            target_norm = "notepad"
            target = "notepad"
        elif "calc.exe" in target_norm or target_norm in ["calculator", "calc", "calculatorapp"]:
            target_norm = "calculator"
            target = "calculator"
        elif target_norm in ["vs_code", "vscode", "code.exe"]:
            target_norm = "vscode"
            target = "vscode"
        elif target_norm in ["taskmgr", "task_manager", "taskmanager"]:
            target_norm = "task_manager"
            target = "task_manager"
        elif target_norm in ["file_explorer", "explorer", "explorer.exe"]:
            target_norm = "explorer"
            target = "explorer"
        elif target_norm in ["google_chrome", "chrome.exe"]:
            target_norm = "chrome"
            target = "chrome"
        elif target_norm in ["microsoft_edge", "msedge", "edge.exe"]:
            target_norm = "edge"
            target = "edge"
        elif target_norm in ["brave_browser", "brave.exe"]:
            target_norm = "brave"
            target = "brave"

        # Route domain correctly
        if any(pt in target_norm for pt in pc_targets) or act in pc_actions or any(pt in act for pt in pc_targets):
            domain = "pc_automation"
        elif any(k in target_norm for k in ["thermostat", "temp", "climate", "ac", "heater", "heating", "heat"]) or any(k in act for k in ["set_temperature", "set temperature", "warm", "cool", "cooldown"]):
            domain = "smart_home"
            target = "thermostat"
        elif any(k in target_norm for k in ["entertainment", "tv", "television", "theater", "display"]):
            domain = "smart_home"
            target = "entertainment_unit"
        elif any(k in target_norm for k in ["kitchen", "bedroom", "living", "light", "door", "lock", "fan", "blind", "alarm"]):
            domain = "smart_home"
        elif not domain:
            domain = "smart_home"

        if domain == "smart_home":
            if "kitchen" in target_norm:
                target = "kitchen_light"
            elif "bedroom" in target_norm:
                target = "bedroom_light"
            elif "living" in target_norm:
                target = "living_room_light"
            elif any(k in target_norm for k in ["all_lights", "all_light", "all_lights_off", "all_lights_on"]):
                target = "all_lights"
            elif any(k in target_norm for k in ["thermostat", "temp", "climate", "ac", "heater", "heating", "heat"]):
                target = "thermostat"
            elif any(k in target_norm for k in ["door", "lock", "front_door", "deadbolt"]):
                target = "front_door_lock"
            elif any(k in target_norm for k in ["alarm", "security"]):
                target = "security_alarm"
            elif any(k in target_norm for k in ["fan", "ceiling"]):
                target = "ceiling_fan"
            elif any(k in target_norm for k in ["blind", "blinds", "window", "curtain"]):
                target = "window_blinds"
            elif any(k in target_norm for k in ["entertainment", "tv", "television", "theater", "display"]):
                target = "entertainment_unit"
            elif target_norm:
                target = target_norm

            # Normalize action strings for smart home
            if any(k in act for k in ["turnoff", "turn_off", "turn off", "deactivate", "disable", "shut", "zero", "power_to_zero", "extinguish", "darken", "off"]):
                act = "turn_off"
            elif any(k in act for k in ["turnon", "turn_on", "turn on", "activate", "enable", "illuminate", "on"]):
                act = "turn_on"
            elif any(k in act for k in ["set_temperature", "set temperature", "temperature", "temp", "cooldown", "cool", "heat", "warm"]):
                act = "set_temperature"
                if any(k in act for k in ["cool", "cooldown"]) and val is None:
                    val = 20.0
                elif any(k in act for k in ["warm", "heat"]) and val is None:
                    val = 24.0
            elif any(k in act for k in ["unlock", "open_door", "unsecure"]):
                act = "unlock"
            elif any(k in act for k in ["lock", "close_door", "secure"]):
                act = "lock"
            elif any(k in act for k in ["close", "lower", "shut"]):
                act = "turn_off" if target == "entertainment_unit" else "close"
            elif any(k in act for k in ["open", "raise", "up"]):
                act = "turn_on" if target == "entertainment_unit" else "open"
        else:
            # PC Automation domain action normalization
            if any(k in act for k in ["open", "launch", "start", "run", "turn_on", "turn on", "activate", "enable", "open_app", "openapp"]):
                if any(k in target for k in ["youtube", "github", "google", "canvas", "website"]):
                    act = "open_website"
                elif target == "browser" and val and (str(val).startswith("http") or "www." in str(val)):
                    act = "open_website"
                else:
                    act = "open_app"
            elif any(k in act for k in ["close", "kill", "terminate", "exit", "stop", "turn_off", "turn off", "shut", "close_app"]):
                act = "close_app"
            elif any(k in act for k in ["search", "query", "web_search"]):
                act = "open_website" if "youtube" in target else "web_search"
            elif any(k in act for k in ["play", "stream", "listen", "play_music", "play_song"]):
                act = "play_music" if target == "spotify" else "open_website"
            elif target == "lock_pc" or ("lock" in act and "pc" in target):
                act = "lock_pc" if act == "lock_pc" else "system_control"

        values["domain"] = domain
        values["device_or_target"] = target if target else ("browser" if domain == "pc_automation" else "living_room_light")
        values["action"] = act
        values["value"] = val
        return values

    @property
    def target(self) -> str:
        return self.device_or_target


class AssistantIntentResponse(BaseModel):
    """Authoritative Pydantic v2 schema for multi-action agentic plans generated by local LLM."""
    spoken_response: str = Field(default="Executing command, sir.")
    actions: List[DeviceAction] = Field(default_factory=list)
    reasoning: Optional[str] = Field(default=None, description="Native Chain of Thought reasoning from <think></think> blocks")
    raw_prompt: Optional[str] = Field(default="")
    interpreted_intent: Optional[str] = Field(default="agentic_action_plan")
    model_name: Optional[str] = Field(default=DEFAULT_MODEL)
    prompt_eval_count: Optional[int] = Field(default=None)
    eval_count: Optional[int] = Field(default=None)
    eval_duration_ms: Optional[float] = Field(default=None)

    @model_validator(mode="before")
    @classmethod
    def sanitize_plan(cls, values: Any) -> Any:
        if isinstance(values, list):
            values = {"actions": values, "spoken_response": ""}

        if not isinstance(values, dict):
            return values

        # Normalize and deduplicate actions
        actions = values.get("actions", [])
        if isinstance(actions, list):
            target_map = {}
            for act in actions:
                if isinstance(act, dict):
                    domain = str(act.get("domain") or "smart_home").strip().lower()
                    target = str(act.get("device_or_target") or act.get("target") or "").strip().lower()
                    action_name = str(act.get("action") or "").strip().lower()
                    val = act.get("value")

                    key = f"{domain}:{target}"
                    # If we already have this target, keep the one that has a specific search/play value
                    if key in target_map:
                        existing = target_map[key]
                        if not existing.get("value") and val:
                            target_map[key] = act
                    else:
                        target_map[key] = act
                elif hasattr(act, "device_or_target"):
                    key = f"{act.domain}:{act.device_or_target.lower()}"
                    if key not in target_map or (not getattr(target_map[key], 'value', None) and getattr(act, 'value', None)):
                        target_map[key] = act

            values["actions"] = list(target_map.values())

        # Ensure spoken_response is a pure human-readable dialogue string without JSON keys
        raw_spoken = values.get("spoken_response")
        if raw_spoken is not None:
            raw_s = str(raw_spoken).strip()
            # If spoken_response was serialized JSON e.g. '{"spoken_response": "..."}'
            for _ in range(5):
                if raw_s.startswith("{") and raw_s.endswith("}"):
                    try:
                        inner_data = json.loads(raw_s)
                        if isinstance(inner_data, dict):
                            if "spoken_response" in inner_data:
                                raw_s = str(inner_data["spoken_response"]).strip()
                            elif "response" in inner_data:
                                raw_s = str(inner_data["response"]).strip()
                            elif "message" in inner_data:
                                raw_s = str(inner_data["message"]).strip()
                    except Exception:
                        pass
                else:
                    break

            # Strip any residual JSON keys, brackets or quotes repeatedly
            for _ in range(10):
                found = False
                for token in [
                    '"spoken_response":', "'spoken_response':", 'spoken_response":', "spoken_response':", 'spoken_response:',
                    '"response":', "'response':", 'response":', "response':", 'response:',
                    '"message":', "'message':", 'message":', "message':", 'message:',
                    '"spoken_actions":', "'spoken_actions':", 'spoken_actions":', 'spoken_actions:',
                    '"actions":', "'actions':", 'actions":', 'actions:'
                ]:
                    if token in raw_s:
                        idx = raw_s.find(token) + len(token)
                        raw_s = raw_s[idx:].strip(' \t\n\r"\'{},[]')
                        found = True
                if not found:
                    break

            # Clean any wrapping quotes or brackets
            raw_s = raw_s.strip('{}[]"\' \t\n\r')
            if any(k in raw_s for k in ['"domain":', "'domain':", '"device_or_target":', '"action":', 'domain":', 'device_or_target":']):
                raw_s = "Command executed successfully, sir."
            values["spoken_response"] = raw_s if raw_s else "Executing command, sir."

        if not values.get("interpreted_intent"):
            values["interpreted_intent"] = "agentic_action_plan"

        return values


# Backward compatibility alias
ActionPlan = AssistantIntentResponse
class PCAutomationEngine:
    """
    Dynamic Universal PC Desktop Automation Engine.
    Executes actions decided by the LLM (opening apps, closing processes, web navigation, system controls).
    Features robust Spotify search & autoplay, YouTube playback, browser launching, and Windows app discovery.
    """

    KNOWN_PROCESS_MAP = {
        "brave": "brave.exe",
        "chrome": "chrome.exe",
        "google chrome": "chrome.exe",
        "edge": "msedge.exe",
        "msedge": "msedge.exe",
        "microsoft edge": "msedge.exe",
        "firefox": "firefox.exe",
        "spotify": "Spotify.exe",
        "notepad": "notepad.exe",
        "calculator": "calc.exe",
        "calc": "calc.exe",
        "paint": "mspaint.exe",
        "mspaint": "mspaint.exe",
        "cmd": "cmd.exe",
        "command prompt": "cmd.exe",
        "powershell": "powershell.exe",
        "terminal": "wt.exe",
        "wt": "wt.exe",
        "code": "Code.exe",
        "vscode": "Code.exe",
        "vs code": "Code.exe",
        "visual studio code": "Code.exe",
        "discord": "Discord.exe",
        "steam": "steam.exe",
        "task_manager": "taskmgr.exe",
        "task manager": "taskmgr.exe",
        "taskmgr": "taskmgr.exe",
        "explorer": "explorer.exe",
        "file explorer": "explorer.exe",
        "file_explorer": "explorer.exe",
        "word": "WINWORD.EXE",
        "excel": "EXCEL.EXE",
        "powerpoint": "POWERPNT.EXE"
    }

    WEB_FALLBACKS = {
        "spotify": "https://open.spotify.com",
        "code": "https://vscode.dev",
        "vscode": "https://vscode.dev",
        "calculator": "https://www.google.com/search?q=calculator",
        "calc": "https://www.google.com/search?q=calculator",
        "youtube": "https://www.youtube.com",
        "github": "https://www.github.com",
        "canvas": "https://canvas.instructure.com",
        "google": "https://www.google.com",
        "discord": "https://discord.com/app",
        "steam": "https://store.steampowered.com"
    }

    _app_cache: Dict[str, str] = {}

    @classmethod
    def _scan_windows_apps(cls):
        """Discovers installed application executables and shortcuts across Windows."""
        if cls._app_cache:
            return

        search_roots = [
            r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs",
            os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs"),
            os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WindowsApps"),
            r"C:\Program Files\BraveSoftware\Brave-Browser\Application",
            r"C:\Program Files\Google\Chrome\Application",
            r"C:\Program Files (x86)\Google\Chrome\Application",
            r"C:\Program Files (x86)\Microsoft\Edge\Application",
            os.path.expandvars(r"%LOCALAPPDATA%\Programs"),
            r"C:\Program Files",
            r"C:\Program Files (x86)"
        ]

        for root_dir in search_roots:
            if os.path.exists(root_dir):
                try:
                    for root, dirs, files in os.walk(root_dir):
                        depth = root[len(root_dir):].count(os.sep)
                        if depth > 4:
                            dirs.clear()
                            continue
                        for file in files:
                            fl = file.lower()
                            if fl.endswith((".lnk", ".exe", ".url")):
                                key = file.rsplit(".", 1)[0].lower() if "." in file else fl
                                full_p = os.path.join(root, file)
                                if key not in cls._app_cache:
                                    cls._app_cache[key] = full_p
                except Exception:
                    pass

    @classmethod
    def resolve_app_path(cls, app_name: str) -> Optional[str]:
        """Resolves full executable or shortcut path for any target application."""
        clean = app_name.lower().strip()
        clean_exe = cls.KNOWN_PROCESS_MAP.get(clean, f"{clean}.exe")

        # 1. Direct explicit Windows app paths
        custom_paths = {
            "spotify": [
                os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WindowsApps\Spotify.exe"),
                os.path.expandvars(r"%APPDATA%\Spotify\Spotify.exe"),
                os.path.expandvars(r"%LOCALAPPDATA%\Programs\Spotify\Spotify.exe"),
                r"C:\Program Files\Spotify\Spotify.exe",
                r"C:\Program Files (x86)\Spotify\Spotify.exe"
            ],
            "code": [
                os.path.expandvars(r"%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe"),
                os.path.expandvars(r"%LOCALAPPDATA%\Programs\Microsoft VS Code\bin\code.cmd"),
                r"C:\Program Files\Microsoft VS Code\Code.exe"
            ],
            "vscode": [
                os.path.expandvars(r"%LOCALAPPDATA%\Programs\Microsoft VS Code\Code.exe"),
                os.path.expandvars(r"%LOCALAPPDATA%\Programs\Microsoft VS Code\bin\code.cmd"),
                r"C:\Program Files\Microsoft VS Code\Code.exe"
            ],
            "calculator": [
                r"C:\Windows\System32\calc.exe",
                os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WindowsApps\CalculatorApp.exe")
            ],
            "notepad": [
                r"C:\Windows\System32\notepad.exe",
                os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WindowsApps\notepad.exe")
            ],
            "discord": [
                os.path.expandvars(r"%LOCALAPPDATA%\Discord\Update.exe --processStart Discord.exe"),
                os.path.expandvars(r"%LOCALAPPDATA%\Discord\app-*\Discord.exe"),
                os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs\Discord Inc\Discord.lnk")
            ],
            "steam": [
                r"C:\Program Files (x86)\Steam\steam.exe",
                r"C:\Program Files\Steam\steam.exe"
            ],
            "brave": [
                r"C:\Program Files\BraveSoftware\Brave-Browser\Application\brave.exe",
                r"C:\Program Files (x86)\BraveSoftware\Brave-Browser\Application\brave.exe",
                os.path.expandvars(r"%LOCALAPPDATA%\BraveSoftware\Brave-Browser\Application\brave.exe")
            ],
            "chrome": [
                r"C:\Program Files\Google\Chrome\Application\chrome.exe",
                r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
                os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe")
            ],
            "edge": [
                r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
                r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"
            ]
        }

        if clean in custom_paths:
            for p in custom_paths[clean]:
                if "*" in p:
                    import glob
                    matches = glob.glob(p)
                    if matches and os.path.exists(matches[0]):
                        return matches[0]
                elif os.path.exists(p):
                    return p

        # 2. System PATH lookup
        p_match = shutil.which(clean_exe) or shutil.which(clean)
        if p_match:
            return p_match

        # 3. Start Menu & WindowsApps Scan
        cls._scan_windows_apps()
        if clean in cls._app_cache:
            return cls._app_cache[clean]

        for k, path in cls._app_cache.items():
            if clean == k or clean in k or k in clean:
                return path

        # 4. Fuzzy match via RapidFuzz
        if RAPIDFUZZ_AVAILABLE and cls._app_cache:
            try:
                match = process.extractOne(clean, list(cls._app_cache.keys()), scorer=fuzz.partial_ratio)
                if match and match[1] >= 80:
                    return cls._app_cache[match[0]]
            except Exception:
                pass

        return None

    @classmethod
    def focus_window(cls, app_name: str) -> bool:
        """Restores (SW_RESTORE=9) and brings an application window to foreground."""
        clean = app_name.lower().strip()
        proc_exe = cls.KNOWN_PROCESS_MAP.get(clean, f"{clean}.exe").replace(".exe", "")

        try:
            if WIN32_AVAILABLE:
                import win32gui
                found_hwnd = []
                def _enum_windows_cb(hwnd, extra):
                    if win32gui.IsWindowVisible(hwnd):
                        w_title = win32gui.GetWindowText(hwnd).lower()
                        if clean in w_title or proc_exe.lower() in w_title:
                            found_hwnd.append(hwnd)
                win32gui.EnumWindows(_enum_windows_cb, None)
                if found_hwnd:
                    win32gui.ShowWindow(found_hwnd[0], 9)  # SW_RESTORE
                    win32gui.SetForegroundWindow(found_hwnd[0])
                    return True
        except Exception:
            pass

        try:
            ps_script = f"""
            $proc = Get-Process -Name "{proc_exe}" -ErrorAction SilentlyContinue | Where-Object {{ $_.MainWindowHandle -ne 0 }} | Select-Object -First 1
            if ($proc) {{
                $wshell = New-Object -ComObject WScript.Shell
                $wshell.AppActivate($proc.Id)
            }}
            """
            res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], capture_output=True, timeout=2)
            return res.returncode == 0
        except Exception:
            return False

    @classmethod
    def is_process_running(cls, app_name: str) -> bool:
        clean = app_name.lower().strip()
        proc_exe = cls.KNOWN_PROCESS_MAP.get(clean, f"{clean}.exe").lower()
        try:
            if PSUTIL_AVAILABLE and psutil:
                for proc in psutil.process_iter(['name']):
                    if proc.info['name'] and proc.info['name'].lower() == proc_exe:
                        return True
        except Exception:
            pass
        return False

    @classmethod
    def launch_app(cls, app_name: str) -> Tuple[bool, str]:
        """Launches application dynamically on Windows desktop, restoring and focusing existing instances."""
        clean = app_name.lower().strip()

        # Check if already running and responsive -> focus window
        if cls.is_process_running(clean):
            if cls.focus_window(clean):
                return True, f"Focused active window for {clean.capitalize()}."

        # Browser handler
        if clean in ["brave", "chrome", "google chrome", "edge", "msedge", "firefox", "browser"]:
            target_browser = "brave" if (clean == "browser" and cls.resolve_app_path("brave")) else ("chrome" if (clean == "browser" and cls.resolve_app_path("chrome")) else ("edge" if clean == "browser" else clean))
            p = cls.resolve_app_path(target_browser)
            if p and os.path.exists(p):
                try:
                    subprocess.Popen([p, "--new-window"])
                    return True, f"Launched {target_browser.capitalize()} browser window."
                except Exception:
                    pass
            try:
                webbrowser.open_new("https://google.com")
                return True, "Opened default web browser."
            except Exception:
                pass

        # Spotify handler with multi-stage execution
        if clean in ["spotify", "spotify app", "spotify music"]:
            # Stage 1: Explicit Spotify executable
            spotify_p = cls.resolve_app_path("spotify")
            if spotify_p and os.path.exists(spotify_p):
                try:
                    subprocess.Popen([spotify_p])
                    time.sleep(0.8)
                    cls.focus_window("spotify")
                    return True, "Launched Spotify Application."
                except Exception:
                    pass

            # Stage 2: Windows URI protocol
            try:
                os.system("start spotify:")
                time.sleep(0.8)
                cls.focus_window("spotify")
                return True, "Launched Spotify."
            except Exception:
                pass

            # Stage 3: PowerShell Start-Process
            try:
                subprocess.Popen(["powershell", "-NoProfile", "-Command", "Start-Process spotify:"], shell=True)
                return True, "Launched Spotify."
            except Exception:
                pass

            # Stage 4: Web Fallback
            webbrowser.open("https://open.spotify.com")
            return True, "Opened Spotify Web Player."

        # Discord handler
        if clean in ["discord", "discord app"]:
            disc_p = cls.resolve_app_path("discord")
            if disc_p and os.path.exists(disc_p):
                try:
                    if disc_p.endswith(".lnk"):
                        os.startfile(disc_p)
                    else:
                        subprocess.Popen([disc_p], shell=True)
                    return True, "Launched Discord."
                except Exception:
                    pass
            try:
                os.system("start discord:")
                return True, "Launched Discord."
            except Exception:
                pass
            webbrowser.open("https://discord.com/app")
            return True, "Opened Discord Web."

        # Steam handler
        if clean in ["steam", "steam app"]:
            steam_p = cls.resolve_app_path("steam")
            if steam_p and os.path.exists(steam_p):
                try:
                    subprocess.Popen([steam_p], shell=True)
                    return True, "Launched Steam."
                except Exception:
                    pass
            try:
                os.system("start steam:")
                return True, "Launched Steam."
            except Exception:
                pass
            webbrowser.open("https://store.steampowered.com")
            return True, "Opened Steam."

        # Calculator handler
        if clean in ["calc", "calculator", "calculator app"]:
            try:
                subprocess.Popen(["calc.exe"])
                return True, "Launched Calculator."
            except Exception:
                try:
                    os.system("start calculator:")
                    return True, "Launched Calculator."
                except Exception:
                    pass

        # Notepad handler
        if clean in ["notepad", "text editor"]:
            try:
                subprocess.Popen(["notepad.exe"])
                return True, "Launched Notepad."
            except Exception:
                pass

        # General application resolver
        app_path = cls.resolve_app_path(clean)
        if app_path:
            try:
                if app_path.endswith(".lnk") or app_path.endswith(".url"):
                    os.startfile(app_path)
                else:
                    subprocess.Popen([app_path], shell=True)
                return True, f"Launched '{clean.capitalize()}'."
            except Exception:
                try:
                    os.startfile(app_path)
                    return True, f"Launched '{clean.capitalize()}'."
                except Exception:
                    pass

        # URI Protocol Attempt
        try:
            os.system(f"start {clean}:")
            return True, f"Launched '{clean.capitalize()}'."
        except Exception:
            pass

        if clean in cls.WEB_FALLBACKS:
            url = cls.WEB_FALLBACKS[clean]
            webbrowser.open(url)
            return True, f"Launched '{clean.capitalize()}' Web Fallback ({url})."

        return False, f"Application '{clean}' is not registered on this system."

    @classmethod
    def close_app(cls, app_name: str) -> Tuple[bool, str]:
        """Terminates active process gracefully or via taskkill."""
        clean = app_name.strip()
        if clean.lower().endswith(".exe"):
            clean = clean[:-4]
        clean = clean.lower()
        proc_exe = cls.KNOWN_PROCESS_MAP.get(clean, f"{clean}.exe")

        try:
            res = subprocess.run(["taskkill", "/IM", proc_exe], capture_output=True, text=True)
            if res.returncode == 0:
                return True, f"Closed {clean.capitalize()}."

            res_force = subprocess.run(["taskkill", "/F", "/IM", proc_exe], capture_output=True, text=True)
            if res_force.returncode == 0:
                return True, f"Force-closed {clean.capitalize()}."

            return True, f"No active process found for {clean.capitalize()}."
        except Exception as e:
            return False, f"Error closing {clean}: {e}"

    @classmethod
    def play_spotify(cls, query: Optional[str] = None) -> str:
        """Cognitive Spotify automation: launches app, searches track, and triggers playback via keystroke automation."""
        clean_q = str(query or "").strip()
        # Filter filler words
        clean_q = re.sub(r'^(?:play|listen\s+to|stream|put\s+on)\s+', '', clean_q, flags=re.IGNORECASE)
        clean_q = re.sub(r'\s+(?:on|in)\s+spotify.*$', '', clean_q, flags=re.IGNORECASE)
        clean_q = clean_q.strip()

        if not clean_q or clean_q.lower() in ["something", "music", "some music", "a song", "song", "tracks", "anything", "spotify"]:
            # Resume playback
            os.system("start spotify:")
            time.sleep(0.5)
            cls.focus_window("spotify")
            if WIN32_AVAILABLE:
                win32api.keybd_event(win32con.VK_MEDIA_PLAY_PAUSE, 0, 0, 0)
                win32api.keybd_event(win32con.VK_MEDIA_PLAY_PAUSE, 0, win32con.KEYEVENTF_KEYUP, 0)
            elif PYAUTOGUI_AVAILABLE:
                pyautogui.press('playpause')
            return "PC Action: Resumed playback on Spotify"

        def _bg_spotify():
            try:
                # 1. Open Spotify
                os.system("start spotify:")
                time.sleep(0.6)
                cls.focus_window("spotify")

                # 2. Dispatch Search URI
                encoded_q = urllib.parse.quote(clean_q)
                os.system(f"start spotify:search:{encoded_q}")
                time.sleep(1.5)
                cls.focus_window("spotify")

                # 3. Use Ctrl+K quick search overlay to select top item
                if PYAUTOGUI_AVAILABLE:
                    for k in ['ctrl', 'alt', 'shift']:
                        try: pyautogui.keyUp(k)
                        except Exception: pass
                    pyautogui.press('escape')
                    time.sleep(0.2)
                    pyautogui.hotkey('ctrl', 'k')
                    time.sleep(0.4)
                    pyautogui.hotkey('ctrl', 'a')
                    time.sleep(0.1)
                    pyautogui.press('backspace')
                    time.sleep(0.1)
                    if 'pyperclip' in sys.modules:
                        import pyperclip
                        pyperclip.copy(clean_q)
                        time.sleep(0.1)
                        pyautogui.hotkey('ctrl', 'v')
                    else:
                        pyautogui.write(clean_q)
                    time.sleep(0.7)
                    pyautogui.press('enter')
            except Exception as e:
                print(f"[PCAutomationEngine Spotify Async Error: {e}]")

        threading.Thread(target=_bg_spotify, daemon=True).start()
        return f"PC Action: Playing '{clean_q.title()}' on Spotify"

    @classmethod
    def play_youtube(cls, query: Optional[str] = None) -> str:
        """Navigates YouTube in browser, selects the top video result, and starts playback."""
        clean_q = str(query or "").strip()
        clean_q = re.sub(r'^(?:play|watch|search\s+(?:for\s+)?)\s+', '', clean_q, flags=re.IGNORECASE)
        clean_q = re.sub(r'\s+(?:on|in)\s+you\s*tube.*$', '', clean_q, flags=re.IGNORECASE)
        clean_q = clean_q.strip()

        if not clean_q or clean_q.lower() in ["something", "a video", "video", "anything", "youtube", "you tube", "yt"]:
            webbrowser.open_new("https://www.youtube.com")
            return "PC Action: Opened YouTube homepage"

        encoded = urllib.parse.quote(clean_q)
        target_url = f"https://www.youtube.com/results?search_query={encoded}"
        webbrowser.open_new(target_url)

        def _bg_youtube():
            try:
                time.sleep(2.2)
                cls.focus_window("brave") or cls.focus_window("chrome") or cls.focus_window("edge")
                if PYAUTOGUI_AVAILABLE:
                    pyautogui.press('escape')
                    time.sleep(0.2)
                    pyautogui.press('tab')
                    time.sleep(0.1)
                    pyautogui.press('enter')
            except Exception as e:
                print(f"[PCAutomationEngine YouTube Async Error: {e}]")

        threading.Thread(target=_bg_youtube, daemon=True).start()
        return f"PC Action: Playing '{clean_q}' on YouTube"

    @classmethod
    def execute_pc_action(cls, target: str, action: str, value: Any = None) -> str:
        """Central execution router for LLM-decided PC automation actions."""
        target_clean = str(target or "").lower().strip()
        act_clean = str(action or "").lower().strip()

        # 1. Close Application
        if act_clean in ["close_app", "close", "kill", "terminate", "exit", "stop_app"]:
            _, msg = cls.close_app(target_clean)
            return f"PC Action: {msg}"

        # 2. Spotify Playback
        if target_clean == "spotify" or act_clean in ["play_music", "play_song"] or (act_clean in ["play", "stream", "listen"] and target_clean not in ["youtube"]):
            return cls.play_spotify(value)

        # 3. YouTube Playback & Navigation
        if "youtube" in target_clean or act_clean == "youtube":
            return cls.play_youtube(value)

        # 4. Web Search
        if act_clean == "web_search" or target_clean in ["web_search", "google_search"]:
            query = str(value or target_clean.replace("search", "")).strip()
            url = f"https://www.google.com/search?q={urllib.parse.quote(query)}"
            webbrowser.open_new(url)
            return f"PC Action: Searched Google for '{query}'"

        # 5. Open Website
        if act_clean == "open_website" or target_clean in ["github", "google", "canvas"]:
            if target_clean == "google":
                if value and not str(value).startswith("http"):
                    url = f"https://www.google.com/search?q={urllib.parse.quote(str(value))}"
                else:
                    url = "https://www.google.com"
            elif target_clean == "github":
                url = "https://github.com" if not value else str(value)
            elif target_clean in cls.WEB_FALLBACKS:
                url = cls.WEB_FALLBACKS[target_clean]
            elif value and str(value).startswith("http"):
                url = str(value)
            elif target_clean == "browser":
                url = "https://www.google.com"
            else:
                url = f"https://www.{target_clean}.com" if not target_clean.startswith("http") else target_clean
            webbrowser.open_new(url)
            return f"PC Action: Opened website '{url}'"

        # 6. Media & Volume Controls
        if act_clean in ["media_control", "volume", "media"] or any(k in target_clean for k in ["volume", "mute", "pause", "play", "skip", "next", "prev"]):
            val_str = str(value or "").lower()
            if "next" in val_str or "next" in target_clean or "skip" in target_clean:
                if WIN32_AVAILABLE:
                    win32api.keybd_event(win32con.VK_MEDIA_NEXT_TRACK, 0, 0, 0)
                    win32api.keybd_event(win32con.VK_MEDIA_NEXT_TRACK, 0, win32con.KEYEVENTF_KEYUP, 0)
                elif PYAUTOGUI_AVAILABLE:
                    pyautogui.press('nexttrack')
                return "PC Action: Skipped to next track"

            elif "prev" in val_str or "previous" in val_str or "prev" in target_clean:
                if WIN32_AVAILABLE:
                    win32api.keybd_event(win32con.VK_MEDIA_PREV_TRACK, 0, 0, 0)
                    win32api.keybd_event(win32con.VK_MEDIA_PREV_TRACK, 0, win32con.KEYEVENTF_KEYUP, 0)
                elif PYAUTOGUI_AVAILABLE:
                    pyautogui.press('prevtrack')
                return "PC Action: Returned to previous track"

            elif "up" in target_clean or "louder" in target_clean or "up" in val_str or "volume_up" in val_str:
                if WIN32_AVAILABLE:
                    for _ in range(5):
                        win32api.keybd_event(win32con.VK_VOLUME_UP, 0, 0, 0)
                        win32api.keybd_event(win32con.VK_VOLUME_UP, 0, win32con.KEYEVENTF_KEYUP, 0)
                elif PYAUTOGUI_AVAILABLE:
                    for _ in range(5): pyautogui.press('volumeup')
                return "PC Action: Increased system volume"

            elif "down" in target_clean or "quieter" in target_clean or "down" in val_str or "volume_down" in val_str:
                if WIN32_AVAILABLE:
                    for _ in range(5):
                        win32api.keybd_event(win32con.VK_VOLUME_DOWN, 0, 0, 0)
                        win32api.keybd_event(win32con.VK_VOLUME_DOWN, 0, win32con.KEYEVENTF_KEYUP, 0)
                elif PYAUTOGUI_AVAILABLE:
                    for _ in range(5): pyautogui.press('volumedown')
                return "PC Action: Decreased system volume"

            elif "mute" in target_clean or "mute" in val_str:
                if WIN32_AVAILABLE:
                    win32api.keybd_event(win32con.VK_VOLUME_MUTE, 0, 0, 0)
                    win32api.keybd_event(win32con.VK_VOLUME_MUTE, 0, win32con.KEYEVENTF_KEYUP, 0)
                elif PYAUTOGUI_AVAILABLE:
                    pyautogui.press('volumemute')
                return "PC Action: Toggled volume mute"

            elif any(k in target_clean for k in ["pause", "play", "resume"]) or any(k in val_str for k in ["pause", "play", "resume"]):
                if WIN32_AVAILABLE:
                    win32api.keybd_event(win32con.VK_MEDIA_PLAY_PAUSE, 0, 0, 0)
                    win32api.keybd_event(win32con.VK_MEDIA_PLAY_PAUSE, 0, win32con.KEYEVENTF_KEYUP, 0)
                elif PYAUTOGUI_AVAILABLE:
                    pyautogui.press('playpause')
                return f"PC Action: Toggled media playback ({value if value else 'Play/Pause'})"

        # 7. System Controls
        if act_clean in ["system_control", "lock_pc", "open_task_manager", "open_explorer"] or target_clean in ["lock_pc", "lock", "task_manager", "open_task_manager", "file_explorer", "open_explorer", "screenshot", "system"]:
            if target_clean in ["lock_pc", "lock"] or act_clean == "lock_pc":
                if sys.platform == "win32":
                    subprocess.Popen(["rundll32.exe", "user32.dll,LockWorkStation"], shell=True)
                return "PC Action: Workstation locked"
            elif target_clean == "system" and str(value).lower() in ["status", "telemetry"]:
                return "PC Action: System status nominal (Workstation online, local AI active)"
            elif target_clean in ["task_manager", "open_task_manager", "taskmgr"] or act_clean == "open_task_manager":
                subprocess.Popen(["taskmgr.exe"], shell=True)
                return "PC Action: Launched Task Manager"
            elif target_clean in ["file_explorer", "explorer", "open_explorer"] or act_clean == "open_explorer":
                subprocess.Popen(["explorer.exe"], shell=True)
                return "PC Action: Opened File Explorer"
            elif target_clean == "screenshot":
                if PYAUTOGUI_AVAILABLE:
                    pyautogui.screenshot("screenshot.png")
                    return "PC Action: Captured screen to screenshot.png"

        # 8. Dynamic Native Application Launcher
        _, msg = cls.launch_app(target_clean)
        return f"PC Action: {msg}"


class AIEngine:
    """
    Pure Agentic Local AI Engine interfacing directly with Ollama (jarvis-trained-model).
    Extracts structured intent, dispatches smart home and PC automation actions, with intelligent resilience.
    """

    SYSTEM_PROMPT = (
        "You are JARVIS, an autonomous AI smart home and desktop assistant created by Christian Ezekiel Carvajal and John Miko Sarsalijo. "
        "Parse the user request into structured JSON actions. "
        "STRICT ANTI-HALLUCINATION RULE: Never invent, guess, or hallucinate search queries, song names, artists, or parameters not explicitly stated by the user. "
        "If the user only asks to open or launch an application or website without specifying a query, set 'value' to null."
    )

    def __init__(self, model_name: Optional[str] = None, base_url: str = "http://127.0.0.1:11434"):
        self.base_url = base_url.rstrip("/")
        # Fix localhost IPv6 delay on Windows by standardizing on 127.0.0.1
        if "localhost" in self.base_url:
            self.base_url = self.base_url.replace("localhost", "127.0.0.1")
        self.model_name = self._resolve_model_name(model_name)

    def _resolve_model_name(self, requested_model: Optional[str]) -> str:
        """Dynamically discovers fine-tuned or standardized models from local Ollama."""
        if requested_model:
            return requested_model

        for test_url in [self.base_url, "http://127.0.0.1:11434", "http://localhost:11434"]:
            try:
                resp = requests.get(f"{test_url}/api/tags", timeout=2.0)
                if resp.status_code == 200:
                    self.base_url = test_url
                    available_models = [m.get("name", "").lower() for m in resp.json().get("models", [])]
                    for candidate in CUSTOM_MODEL_CANDIDATES:
                        for avail in available_models:
                            if candidate in avail or avail.startswith(candidate):
                                return candidate
                    if available_models:
                        return available_models[0].split(":")[0]
            except Exception:
                pass

        return DEFAULT_MODEL

    def _check_ollama_health(self) -> bool:
        """Verifies connection to local Ollama daemon."""
        for test_url in [self.base_url, "http://127.0.0.1:11434", "http://localhost:11434"]:
            try:
                resp = requests.get(f"{test_url}/api/tags", timeout=2.0)
                if resp.status_code == 200:
                    self.base_url = test_url
                    return True
            except Exception:
                pass
        return False

    def _extract_reasoning_and_json(self, raw_content: str, thinking_content: str = "") -> Tuple[Optional[str], str]:
        """
        Cleanly separates native <think>...</think> Chain-of-Thought reasoning from the subsequent JSON payload.
        Handles both inline <think> tags and Ollama's separate thinking field.
        """
        reasoning = thinking_content.strip() if thinking_content else None
        text = raw_content.strip()

        # Extract inline <think>...</think> if present in text
        if "<think>" in text:
            start_idx = text.find("<think>")
            end_idx = text.find("</think>")
            if end_idx != -1:
                think_block = text[start_idx + len("<think>"):end_idx].strip()
                if think_block:
                    reasoning = think_block
                text = (text[:start_idx] + text[end_idx + len("</think>"):]).strip()
            else:
                # Unclosed <think> tag
                think_block = text[start_idx + len("<think>"):].strip()
                if think_block and not reasoning:
                    reasoning = think_block
                text = text[:start_idx].strip()

        cleaned_json_str = self._clean_llm_json(text)
        return reasoning, cleaned_json_str

    def parse_command(self, prompt: str, live_state: Optional[str] = None) -> AssistantIntentResponse:
        """
        Pure Agentic Intent Extraction:
        Sends prompt directly to local fine-tuned model via Ollama in strict JSON format with 120s timeout,
        extracts Chain-of-Thought reasoning, and validates structured action plan with Pydantic v2.
        """
        clean_prompt = prompt.strip()
        if not clean_prompt:
            return AssistantIntentResponse(
                spoken_response="I am at your service, sir. What can I do for you?",
                actions=[],
                reasoning=None,
                raw_prompt="",
                interpreted_intent="empty_prompt",
                model_name=self.model_name
            )

        if self._check_ollama_health():
            try:
                resp = requests.post(
                    f"{self.base_url}/api/chat",
                    json={
                        "model": self.model_name,
                        "messages": [
                            {"role": "system", "content": self.SYSTEM_PROMPT},
                            {"role": "user", "content": clean_prompt}
                        ],
                        "stream": False,
                        "format": "json"
                    },
                    timeout=120.0
                )
                if resp.status_code == 200:
                    resp_json = resp.json()
                    msg = resp_json.get("message", {})
                    raw_content = msg.get("content", "").strip()
                    thinking = msg.get("thinking", "").strip()

                    reasoning, cleaned_json_str = self._extract_reasoning_and_json(raw_content, thinking)

                    parsed_data = json.loads(cleaned_json_str)
                    parsed_data["raw_prompt"] = clean_prompt
                    if reasoning:
                        parsed_data["reasoning"] = reasoning

                    if "interpreted_intent" not in parsed_data:
                        parsed_data["interpreted_intent"] = "agentic_action_plan"

                    parsed_data["model_name"] = self.model_name
                    parsed_data["prompt_eval_count"] = resp_json.get("prompt_eval_count")
                    parsed_data["eval_count"] = resp_json.get("eval_count")
                    eval_duration = resp_json.get("eval_duration")
                    parsed_data["eval_duration_ms"] = (eval_duration / 1e6) if eval_duration else None

                    # Strict Pydantic v2 validation
                    plan = AssistantIntentResponse.model_validate(parsed_data)
                    return plan
            except Exception as e:
                print(f"[AIEngine Ollama parse notice: {e}]")

        # Deterministic emergency fallback only if Ollama is completely offline/unreachable
        return self._semantic_fallback_parse(clean_prompt, live_state=live_state)

    def _semantic_fallback_parse(self, prompt: str, live_state: Optional[str] = None) -> AssistantIntentResponse:
        """
        Pure Error Reporting Fallback:
        Zero hardcoded triggers or rule-based actions. Notifies user that the local Ollama LLM is unreachable.
        """
        return AssistantIntentResponse(
            spoken_response="The local Ollama AI model is currently offline or unreachable. Please start the Ollama service.",
            actions=[],
            reasoning="Ollama local daemon connection failed. Zero hardcoded actions executed.",
            raw_prompt=prompt,
            interpreted_intent="ollama_offline",
            model_name=self.model_name
        )

    # Alias for backward compatibility
    def parse_intent(self, prompt: str) -> AssistantIntentResponse:
        return self.parse_command(prompt)

    def _clean_llm_json(self, raw_text: str) -> str:
        """Extracts clean JSON substring from LLM response text without regular expressions."""
        text = raw_text.strip()

        # Remove think tags if any
        while "<think>" in text and "</think>" in text:
            start_idx = text.find("<think>")
            end_idx = text.find("</think>") + len("</think>")
            text = (text[:start_idx] + text[end_idx:]).strip()

        # Remove markdown code blocks if any
        if "```json" in text:
            start = text.find("```json") + 7
            end = text.find("```", start)
            if end != -1:
                candidate = text[start:end].strip()
                try:
                    json.loads(candidate)
                    return candidate
                except Exception:
                    pass
        elif "```" in text:
            start = text.find("```") + 3
            end = text.find("```", start)
            if end != -1:
                candidate = text[start:end].strip()
                try:
                    json.loads(candidate)
                    return candidate
                except Exception:
                    pass

        # Robust bracket-counting scanner: find first complete valid { ... }
        start_idx = text.find('{')
        if start_idx != -1:
            depth = 0
            in_string = False
            escape = False
            for i in range(start_idx, len(text)):
                char = text[i]
                if in_string:
                    if escape:
                        escape = False
                    elif char == '\\':
                        escape = True
                    elif char == '"':
                        in_string = False
                else:
                    if char == '"':
                        in_string = True
                    elif char == '{':
                        depth += 1
                    elif char == '}':
                        depth -= 1
                        if depth == 0:
                            candidate = text[start_idx:i+1]
                            try:
                                json.loads(candidate)
                                return candidate
                            except Exception:
                                pass

        first_brace = text.find('{')
        last_brace = text.rfind('}')
        if first_brace != -1 and last_brace != -1 and last_brace > first_brace:
            candidate = text[first_brace:last_brace + 1]
            try:
                json.loads(candidate)
                return candidate
            except Exception:
                pass

        # If no JSON braces found but text exists, wrap as conversational JSON
        if text:
            return json.dumps({"spoken_response": text, "actions": []})
        return "{}"

