import os
import sys
import re
import shutil
import subprocess
import time
import asyncio
import json
import random
import urllib.parse

import webbrowser
import psutil
import requests
from typing import Tuple, Dict, Any, Optional, List

try:
    import pyautogui
    import pyperclip
    from PIL import Image, ImageGrab
    PYAUTOGUI_AVAILABLE = True
    pyautogui.FAILSAFE = False
except ImportError:
    PYAUTOGUI_AVAILABLE = False


try:
    import win32api
    import win32con
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False

from core.macro_engine import MacroEngine
from core.memory_engine import MemoryEngine
from core.security_engine import SecurityEngine


class HomeAssistantClient:
    """Home Assistant REST API wrapper with simulation fallback."""

    def __init__(self, host: str = "http://localhost:8123", token: Optional[str] = None):
        self.host = host.rstrip("/")
        self.token = token
        self.headers = {
            "Authorization": f"Bearer {token}" if token else "",
            "Content-Type": "application/json",
        }
        self.simulation_mode = True if not token else False

    def toggle_device(self, domain: str, service: str, entity_id: str) -> Tuple[bool, str]:
        """Turn on/off or toggle smart home entities."""
        if self.simulation_mode:
            state = "ON" if service == "turn_on" else "OFF"
            return True, f"[SIMULATED HA]: Entity '{entity_id}' set to {state}."

        url = f"{self.host}/api/services/{domain}/{service}"
        payload = {"entity_id": entity_id}
        try:
            resp = requests.post(url, headers=self.headers, json=payload, timeout=3)
            if resp.status_code == 200:
                return True, f"Successfully executed {service} on {entity_id}."
            return False, f"Home Assistant error: HTTP {resp.status_code}"
        except Exception as e:
            return False, f"Failed to connect to Home Assistant: {str(e)}"

    def get_entity_state(self, entity_id: str) -> Tuple[bool, str]:
        """Fetch status of a specific Home Assistant entity."""
        if self.simulation_mode:
            return True, f"[SIMULATED HA]: Entity '{entity_id}' state is active."

        url = f"{self.host}/api/states/{entity_id}"
        try:
            resp = requests.get(url, headers=self.headers, timeout=3)
            if resp.status_code == 200:
                data = resp.json()
                state = data.get("state", "unknown")
                return True, f"Entity '{entity_id}' state is {state}."
            return False, f"HTTP {resp.status_code}"
        except Exception as e:
            return False, str(e)


class ActionEngine:
    """Core Action Engine managing OS commands, GUI automation, Computer Vision screen navigation, PID window focus, state-aware Spotify playback, Two-Stage Asynchronous Execution, and Macro Engine integration."""

    def __init__(self, ha_token: Optional[str] = None):
        self.ha_client = HomeAssistantClient(token=ha_token)
        self.macro_engine = MacroEngine()
        self.memory_engine = MemoryEngine()

        self.PROCESS_MAP = {
            "brave": "brave.exe",
            "spotify": "spotify.exe",
            "chrome": "chrome.exe",
            "msedge": "msedge.exe",
            "edge": "msedge.exe",
            "notepad": "notepad.exe",
            "discord": "Discord.exe",
            "calculator": "CalculatorApp.exe",
            "cmd": "cmd.exe",
            "powershell": "powershell.exe",
            "steam": "steam.exe"
        }

        # Conversational filler phrases to ignore in queries
        self.VAGUE_FILLER_PATTERNS = [
            r"\ba video\b", r"\bany video\b", r"\bany kind will do\b", r"\banything\b",
            r"\bwhatever\b", r"\bsomething\b", r"\bjust play\b", r"\bplay a video\b"
        ]

        self.personality_file = "config/personality.json"
        self.personality_data = self._load_personality()

    def _load_personality(self) -> Dict[str, Any]:
        if os.path.exists(self.personality_file):
            try:
                with open(self.personality_file, "r", encoding="utf-8") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def get_stage1_ack(self, intent_type: str) -> str:
        """Returns a dynamic Stage-1 voice acknowledgment from personality template."""
        acks = self.personality_data.get("acknowledgments", {}).get(intent_type, [])
        if not acks:
            acks = self.personality_data.get("acknowledgments", {}).get("general", ["Processing your request."])
        return random.choice(acks)

    def get_stage2_wrapup(self, intent_type: str) -> str:
        """Returns a dynamic Stage-2 context-aware completion wrap-up from personality template."""
        wrapups = self.personality_data.get("completion_wrapups", {}).get(intent_type, [])
        if not wrapups:
            wrapups = self.personality_data.get("completion_wrapups", {}).get("general", ["Task complete."])
        return random.choice(wrapups)

    def _is_safe_operation(self, command_or_path: str) -> bool:
        """Strict safety guard blocking file deletions and system directory modifications via SecurityEngine."""
        return SecurityEngine.is_safe_target(command_or_path)

    def sanitize_query(self, query: str) -> str:
        """Strips conversational fluff and vague filler words from raw search queries."""
        clean = query.strip()
        for pattern in self.VAGUE_FILLER_PATTERNS:
            clean = re.sub(pattern, "", clean, flags=re.IGNORECASE).strip()

        clean = re.sub(r'^(?:on|about|for|to|a|of)\s+', '', clean, flags=re.IGNORECASE).strip()
        return clean

    def is_process_running(self, process_name: str) -> bool:
        """Checks if a targeted application process is currently active."""
        try:
            clean_name = process_name.replace(".exe", "")
            ps_script = f'Get-Process -Name "{clean_name}" -ErrorAction SilentlyContinue'
            res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], capture_output=True, text=True)
            return bool(res.stdout.strip())
        except Exception:
            return False

    def focus_process_window(self, process_name: str) -> bool:
        """Brings an application window to the foreground by Process ID (PID)."""
        try:
            clean_pname = process_name.replace(".exe", "")
            ps_script = f"""
            $proc = Get-Process -Name "{clean_pname}" -ErrorAction SilentlyContinue | Where-Object {{ $_.MainWindowHandle -ne 0 }} | Select-Object -First 1
            if ($proc) {{
                $wshell = New-Object -ComObject WScript.Shell
                $wshell.AppActivate($proc.Id)
            }}
            """
            res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], capture_output=True, timeout=2)
            return res.returncode == 0
        except Exception:
            return False

    def wait_and_focus_process(self, process_name: str, timeout: float = 7.0) -> bool:
        """Polls until an application process window handle exists and brings it to the foreground."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            if self.focus_process_window(process_name):
                return True
            time.sleep(0.5)
        return False

    def release_modifier_keys(self) -> None:
        """Forces OS release of all stuck modifier keys."""
        if PYAUTOGUI_AVAILABLE:
            for k in ['ctrl', 'alt', 'shift']:
                pyautogui.keyUp(k)

    def type_via_clipboard(self, text: str) -> None:
        """Pastes text directly via OS clipboard to prevent stuck Ctrl modifier key conflicts."""
        if not PYAUTOGUI_AVAILABLE:
            return

        self.release_modifier_keys()
        pyperclip.copy(text)
        time.sleep(0.1)
        pyautogui.hotkey('ctrl', 'v')
        self.release_modifier_keys()

    def focus_window(self, app_title: str) -> bool:
        """Brings the targeted application window directly into OS foreground focus."""
        return self.focus_process_window(app_title)

    def capture_screen(self, save_path: str = "temp_screen.png") -> Tuple[bool, str]:
        """Captures a full screenshot of the active monitor for vision processing."""
        if PYAUTOGUI_AVAILABLE:
            try:
                screenshot = ImageGrab.grab()
                screenshot.save(save_path)
                return True, save_path
            except Exception as e:
                return False, f"Failed to capture screen: {str(e)}"
        return False, "Pillow/PyAutoGUI unavailable."

    def click_coordinate(self, x: int, y: int) -> Tuple[bool, str]:
        """Performs a visual click at exact screen pixel coordinates."""
        if PYAUTOGUI_AVAILABLE:
            pyautogui.click(x, y)
            return True, f"Clicked coordinate ({x}, {y})."
        return False, "PyAutoGUI unavailable."

    def locate_and_click(self, template_image_path: str, confidence: float = 0.8) -> Tuple[bool, str]:
        """Locates an image target on screen using visual template matching and clicks it."""
        if PYAUTOGUI_AVAILABLE:
            try:
                location = pyautogui.locateCenterOnScreen(template_image_path, confidence=confidence)
                if location:
                    pyautogui.click(location)
                    return True, f"Visually identified and clicked target at {location}."
                return False, "Visual target not found on active screen."
            except Exception as e:
                return False, f"Vision engine error: {str(e)}"
        return False, "PyAutoGUI unavailable."

    def close_app(self, app_name: str) -> Tuple[bool, str]:
        """Safely and gracefully terminate targeted application processes."""
        clean_name = re.sub(r'\.exe$', '', app_name.strip(), flags=re.IGNORECASE).lower()
        proc_exe = self.PROCESS_MAP.get(clean_name, f"{clean_name}.exe")

        try:
            soft_result = subprocess.run(["taskkill", "/IM", proc_exe], capture_output=True, text=True)
            if soft_result.returncode == 0:
                return True, f"Closed {clean_name} gracefully."

            force_result = subprocess.run(["taskkill", "/F", "/IM", proc_exe], capture_output=True, text=True)
            if force_result.returncode == 0:
                return True, f"Force closed {clean_name}."
            else:
                return True, f"Could not find an active process for {clean_name}."
        except Exception as e:
            return False, f"Error closing {clean_name}: {str(e)}"

    def _resolve_spotify_query(self, raw_query: str) -> str:
        """Resolves target song query into full track + artist entity target via iTunes API."""
        if not raw_query.strip():
            return ""
        url = f"https://itunes.apple.com/search?term={urllib.parse.quote(raw_query)}&entity=song&limit=1"
        try:
            r = requests.get(url, timeout=3.0)
            data = r.json()
            if data.get("resultCount", 0) > 0:
                track = data["results"][0]
                t = track.get("trackName", "")
                a = track.get("artistName", "")
                return f"{t} {a}".strip()
        except Exception:
            pass
        return raw_query.strip()

    def play_on_spotify(self, query: str = "") -> Tuple[bool, str]:
        """Cognitive & self-aware Spotify automation: dismisses open modals, uses URI search, and guarantees playback across warm/cold states."""
        clean_query = self.sanitize_query(query)
        was_running = self.is_process_running("spotify")


        # 1. Force Spotify GUI window unminimize / restore
        os.system("start spotify:")
        time.sleep(0.5)
        self.wait_and_focus_process("spotify", timeout=5.0)

        if not clean_query:
            if PYAUTOGUI_AVAILABLE:
                pyautogui.sleep(1.0 if was_running else 2.5)
                self.release_modifier_keys()
                pyautogui.press('playpause')
            return True, "Resuming Spotify playback."

        # Resolve full title + artist target entity
        resolved_q = self._resolve_spotify_query(clean_query)
        encoded_q = urllib.parse.quote(resolved_q)

        # 2. Dispatch Spotify search URI
        os.system(f"start spotify:search:{encoded_q}")

        # 3. Wait for Spotify search DOM render
        render_delay = 1.8 if was_running else 2.5
        time.sleep(render_delay)

        # 4. Force-focus Spotify window via win32gui for deterministic foreground ownership
        try:
            import win32gui
            def _enum_cb(hwnd, results):
                if win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd)
                    if 'Spotify' in title:
                        results.append(hwnd)
            hwnds = []
            win32gui.EnumWindows(_enum_cb, hwnds)
            if hwnds:
                hwnd = hwnds[0]
                win32gui.ShowWindow(hwnd, 9)  # SW_RESTORE
                win32gui.SetForegroundWindow(hwnd)
        except Exception:
            self.focus_process_window("spotify")
        time.sleep(0.3)

        if PYAUTOGUI_AVAILABLE:
            self.release_modifier_keys()

            # Dismiss open modals
            pyautogui.press('escape')
            pyautogui.sleep(0.2)
            self.release_modifier_keys()

            # Open Ctrl+K Quick Search Overlay
            pyautogui.hotkey('ctrl', 'k')
            self.release_modifier_keys()
            pyautogui.sleep(0.5)

            # Clear existing text (Ctrl+A -> Backspace)
            pyautogui.hotkey('ctrl', 'a')
            self.release_modifier_keys()
            pyautogui.sleep(0.1)
            pyautogui.press('backspace')
            self.release_modifier_keys()
            pyautogui.sleep(0.1)

            # Paste target query cleanly via clipboard
            self.type_via_clipboard(clean_query)
            self.release_modifier_keys()
            pyautogui.sleep(0.8) # Wait for Quick Search dropdown list to render

            # Select primary top match directly (starts playback automatically)
            pyautogui.press('enter')
            self.release_modifier_keys()

        return True, f"Playing '{clean_query}' on Spotify."















    def play_on_youtube(self, query: str = "") -> Tuple[bool, str]:
        """Navigates YouTube, focuses browser process window, and plays top video match."""
        clean_query = self.sanitize_query(query) or "trending music videos"
        encoded_query = urllib.parse.quote(clean_query)

        url = f"https://www.youtube.com/results?search_query={encoded_query}"
        webbrowser.open_new(url)

        if PYAUTOGUI_AVAILABLE:
            pyautogui.sleep(2.5)
            self.focus_process_window("brave") or self.focus_process_window("chrome") or self.focus_process_window("msedge")
            pyautogui.press('tab')
            pyautogui.press('enter')

        return True, f"Playing '{clean_query}' on YouTube."

    def search_web(self, query: str) -> Tuple[bool, str]:
        """Searches Google for sanitized target queries."""
        clean_query = self.sanitize_query(query) or "trending news"

        encoded_query = urllib.parse.quote(clean_query)
        url = f"https://www.google.com/search?q={encoded_query}"
        webbrowser.open_new(url)
        return True, f"Searching Google for '{clean_query}'."

    def click_and_type(self, text: str, press_enter: bool = True) -> Tuple[bool, str]:
        """Types input text directly into the active UI element or text box via clipboard."""
        if PYAUTOGUI_AVAILABLE:
            self.type_via_clipboard(text)
            if press_enter:
                pyautogui.press('enter')
            return True, f"Entered '{text}'."
        return False, "PyAutoGUI unavailable."

    def press_shortcut(self, key_combination: str) -> Tuple[bool, str]:
        """Executes hardware key combinations (e.g. 'ctrl+t', 'alt+tab', 'space')."""
        if PYAUTOGUI_AVAILABLE:
            keys = [k.strip().lower() for k in key_combination.split('+')]
            if len(keys) == 1:
                pyautogui.press(keys[0])
            else:
                pyautogui.hotkey(*keys)
                self.release_modifier_keys()
            return True, f"Executed shortcut '{key_combination}'."
        return False, "PyAutoGUI unavailable."

    def _send_native_media_key(self, vk_code: int) -> bool:
        """Sends native OS virtual hardware key event directly to Windows system transport controls."""
        if WIN32_AVAILABLE:
            try:
                win32api.keybd_event(vk_code, 0, 0, 0)
                win32api.keybd_event(vk_code, 0, win32con.KEYEVENTF_KEYUP, 0)
                return True
            except Exception:
                pass
        return False

    def handle_media_control(self, action: str) -> Tuple[bool, str]:
        """Controls system volume and media playback via native OS transport keys."""
        act = action.lower()

        if any(k in act for k in ["pause", "play", "resume"]):
            if WIN32_AVAILABLE:
                self._send_native_media_key(win32con.VK_MEDIA_PLAY_PAUSE)
            elif PYAUTOGUI_AVAILABLE:
                pyautogui.press('playpause')
            return True, "Toggled media playback."

        elif any(k in act for k in ["next", "skip"]):
            if WIN32_AVAILABLE:
                self._send_native_media_key(win32con.VK_MEDIA_NEXT_TRACK)
            elif PYAUTOGUI_AVAILABLE:
                pyautogui.press('nexttrack')
            return True, "Skipped track."

        elif any(k in act for k in ["prev", "back"]):
            if WIN32_AVAILABLE:
                self._send_native_media_key(win32con.VK_MEDIA_PREV_TRACK)
            elif PYAUTOGUI_AVAILABLE:
                pyautogui.press('prevtrack')
            return True, "Previous track."

        elif "volume up" in act or "louder" in act:
            if WIN32_AVAILABLE:
                for _ in range(5):
                    self._send_native_media_key(win32con.VK_VOLUME_UP)
            elif PYAUTOGUI_AVAILABLE:
                for _ in range(5):
                    pyautogui.press('volumeup')
            return True, "Increased system volume."

        elif "volume down" in act or "quieter" in act:
            if WIN32_AVAILABLE:
                for _ in range(5):
                    self._send_native_media_key(win32con.VK_VOLUME_DOWN)
            elif PYAUTOGUI_AVAILABLE:
                for _ in range(5):
                    pyautogui.press('volumedown')
            return True, "Decreased system volume."

        elif "mute" in act:
            if WIN32_AVAILABLE:
                self._send_native_media_key(win32con.VK_VOLUME_MUTE)
            elif PYAUTOGUI_AVAILABLE:
                pyautogui.press('volumemute')
            return True, "Toggled mute."

        return False, ""

    def launch_app_dynamically(self, app_name: str) -> Tuple[bool, str]:
        """Launches applications dynamically with non-destructive multi-window support."""
        clean_name = re.sub(r'\.exe$', '', app_name.strip(), flags=re.IGNORECASE).lower()

        if not self._is_safe_operation(clean_name):
            return True, "Security protocol active: Command blocked."

        if clean_name in ["brave", "chrome", "edge", "msedge"]:
            browser_path = shutil.which(clean_name) or shutil.which(f"{clean_name}.exe")
            if browser_path and self._is_safe_operation(browser_path):
                subprocess.Popen([browser_path, "--new-window", "--no-crash-restore-bubble"])
                return True, f"Opening new {clean_name} window."
            else:
                webbrowser.open_new("https://google.com")
                return True, f"Opening browser window."

        path_match = shutil.which(clean_name) or shutil.which(f"{clean_name}.exe")
        if path_match and self._is_safe_operation(path_match):
            os.startfile(path_match)
            return True, f"Launching {clean_name}."

        start_menu_paths = [
            r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs",
            os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs")
        ]

        for search_root in start_menu_paths:
            if os.path.exists(search_root):
                for root, _, files in os.walk(search_root):
                    for file in files:
                        if clean_name in file.lower() and file.endswith((".lnk", ".exe")):
                            full_path = os.path.join(root, file)
                            if self._is_safe_operation(full_path):
                                os.startfile(full_path)
                                return True, f"Opening {clean_name}."

        return False, ""

    def parse_and_execute(self, command: str) -> Tuple[bool, str]:
        """Hybrid parser routing user intents to appropriate GUI/Vision handlers."""
        cmd_lower = command.lower().strip()

        # Log turn into memory
        self.memory_engine.store_turn("user", command)

        # 0. Check Macros
        for macro_key in self.macro_engine.macros:
            if macro_key.replace("_", " ") in cmd_lower or macro_key in cmd_lower:
                try:
                    loop = asyncio.get_event_loop()
                    if loop.is_running():
                        loop.create_task(self.macro_engine.execute_macro_async(macro_key, self))
                    else:
                        self.macro_engine.execute_macro(macro_key, self)
                except Exception:
                    self.macro_engine.execute_macro(macro_key, self)
                return True, self.get_stage1_ack("macro_routine")


        # 1. YouTube Intents
        if "youtube" in cmd_lower and any(kw in cmd_lower for kw in ["play", "plaly", "plaay", "watch", "search", "open", "go to"]):
            raw_target = re.sub(r'.*?(?:play|plaly|plaay|watch|search|open|go to)\s*', '', cmd_lower, flags=re.IGNORECASE)
            raw_target = re.sub(r'\s*on\s+youtube.*$', '', raw_target, flags=re.IGNORECASE).strip()
            return self.play_on_youtube(raw_target)

        # 2. Spotify Intents
        if "spotify" in cmd_lower and any(kw in cmd_lower for kw in ["play", "plaly", "plaay", "playy", "plai", "listen", "search", "serch", "open"]):
            raw_target = re.sub(r'.*?(?:play|plaly|plaay|playy|plai|listen|search|serch|open)\s*', '', cmd_lower, flags=re.IGNORECASE)
            raw_target = re.sub(r'\s*on\s+spotify.*$', '', raw_target, flags=re.IGNORECASE).strip()
            if raw_target.lower() in ["a music", "music", "some music", "a song", "song", "tracks", "anything"]:
                raw_target = ""
            return self.play_on_spotify(raw_target)

        # 3. Web Search
        if cmd_lower.startswith("search ") or "google " in cmd_lower:
            raw_target = re.sub(r'^(?:search|google)\s*', '', cmd_lower).replace('on google', '').strip()
            return self.search_web(raw_target)

        # 4. Shortcut / Key Press Automation
        if cmd_lower.startswith("press ") or cmd_lower.startswith("shortcut "):
            keys = re.sub(r'^(?:press|shortcut)\s*', '', cmd_lower).strip()
            return self.press_shortcut(keys)

        # 5. Typing Automation
        if cmd_lower.startswith("type "):
            return self.click_and_type(command[5:].strip())

        # 6. Media Controls
        if any(kw in cmd_lower for kw in ["volume up", "volume down", "mute", "pause music", "pause song", "skip song", "next track", "previous track"]):
            return self.handle_media_control(cmd_lower)

        # 7. System Telemetry & Metrics Query
        if "system status" in cmd_lower or "cpu usage" in cmd_lower or "battery" in cmd_lower or "system telemetry" in cmd_lower:
            cpu = psutil.cpu_percent(interval=0.1)
            ram = psutil.virtual_memory().percent
            battery_str = ""
            if hasattr(psutil, "sensors_battery"):
                battery = psutil.sensors_battery()
                if battery:
                    battery_str = f" Battery level is at {int(battery.percent)} percent."
            return True, f"System operating within normal parameters. CPU usage at {cpu} percent, RAM usage at {ram} percent.{battery_str}"

        # 8. Smart Home Automations (Home Assistant)
        if "turn on" in cmd_lower and ("light" in cmd_lower or "lamp" in cmd_lower):
            entity = "light.living_room"
            success, msg = self.ha_client.toggle_device("light", "turn_on", entity)
            return True, "Illuminating living room lights."

        if "turn off" in cmd_lower and ("light" in cmd_lower or "lamp" in cmd_lower):
            entity = "light.living_room"
            success, msg = self.ha_client.toggle_device("light", "turn_off", entity)
            return True, "Extinguishing living room lights."

        # 9. Multi-Process Compound Launch/Close
        launch_verbs = r'\b(?:open|launch|run|start|execute)\b'
        close_verbs = r'\b(?:close|exit|kill|terminate|stop|quit|end)\b'

        has_launch = bool(re.search(launch_verbs, cmd_lower))
        has_close = bool(re.search(close_verbs, cmd_lower))

        if not (has_launch or has_close):
            return False, ""

        segments = re.split(r'\s*(?:and|then|,|;|&)\s*', cmd_lower)
        feedbacks = []
        executed_any = False
        current_verb = "launch" if has_launch else "close"

        for segment in segments:
            seg_clean = segment.strip()
            if not seg_clean:
                continue

            close_match = re.search(r'^(?:close|exit|kill|terminate|stop|quit|end)\s+(.+)$', seg_clean)
            if close_match:
                current_verb = "close"
                target = close_match.group(1).strip()
                success, msg = self.close_app(target)
                if success:
                    feedbacks.append(msg)
                    executed_any = True
                continue

            launch_match = re.search(r'^(?:open|launch|run|start|execute)\s+(.+)$', seg_clean)
            if launch_match:
                current_verb = "launch"
                target = launch_match.group(1).strip()
                success, msg = self.launch_app_dynamically(target)
                if success:
                    feedbacks.append(msg)
                    executed_any = True
                continue

            clean_target = re.sub(r'^(?:open|launch|run|start|execute|close|exit|kill|terminate|stop|quit|end)\s+', '', seg_clean).strip()
            if clean_target:
                if current_verb == "launch":
                    success, msg = self.launch_app_dynamically(clean_target)
                else:
                    success, msg = self.close_app(clean_target)

                if success:
                    feedbacks.append(msg)
                    executed_any = True

        if executed_any:
            return True, " ".join(feedbacks)

        return False, ""
