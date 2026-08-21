import os
import sys
import re
import shutil
import subprocess
import time
import psutil
from typing import Optional, Dict, Tuple, List
from rapidfuzz import process, fuzz
from core.security_engine import SecurityEngine

class AppResolver:
    """Portable Windows Application Resolver & Window Handle Focus Engine with Win32 ShowWindow restore and IsHungAppWindow process crash recovery."""

    _instance: Optional['AppResolver'] = None

    KNOWN_MAPPINGS = {
        "spotify": "spotify.exe",
        "brave": "brave.exe",
        "chrome": "chrome.exe",
        "google chrome": "chrome.exe",
        "edge": "msedge.exe",
        "microsoft edge": "msedge.exe",
        "discord": "Discord.exe",
        "steam": "steam.exe",
        "notepad": "notepad.exe",
        "calculator": "CalculatorApp.exe",
        "cmd": "cmd.exe",
        "command prompt": "cmd.exe",
        "powershell": "powershell.exe",
        "terminal": "wt.exe",
        "task manager": "taskmgr.exe",
        "code": "Code.exe",
        "vs code": "Code.exe",
        "vscode": "Code.exe"
    }

    ALIASES = {
        "spotty": "spotify",
        "spot if i": "spotify",
        "spotifi": "spotify",
        "you tube": "youtube",
        "mr beast": "mrbeast",
        "google chrome": "chrome",
        "microsoft edge": "edge"
    }

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(AppResolver, cls).__new__(cls)
            cls._instance._init_cache()
        return cls._instance

    def _init_cache(self):
        self.app_cache: Dict[str, str] = {}
        self._scan_start_menu()

    def normalize_name(self, raw_name: str) -> str:
        """Normalizes user speech text to canonical application key."""
        clean = raw_name.lower().strip()
        for alias, canonical in self.ALIASES.items():
            if clean == alias:
                return canonical
        return clean

    def _scan_start_menu(self):
        """Scans Windows Start Menu shortcut trees and WindowsApps directory to discover installed application executables."""
        search_roots = [
            r"C:\ProgramData\Microsoft\Windows\Start Menu\Programs",
            os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs"),
            os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WindowsApps")
        ]
        for root_dir in search_roots:
            if os.path.exists(root_dir):
                for root, _, files in os.walk(root_dir):
                    for file in files:
                        if file.endswith((".lnk", ".exe")):
                            name_key = file.rsplit(".", 1)[0].lower()
                            full_path = os.path.join(root, file)
                            if SecurityEngine.is_safe_target(full_path):
                                self.app_cache[name_key] = full_path

    def is_running(self, app_name: str) -> Tuple[bool, Optional[int]]:
        """Checks if an application process is active and returns its primary PID."""
        clean_name = self.normalize_name(app_name)
        proc_exe = self.KNOWN_MAPPINGS.get(clean_name, f"{clean_name}.exe").lower()

        try:
            for proc in psutil.process_iter(['pid', 'name']):
                if proc.info['name'] and proc.info['name'].lower() == proc_exe:
                    return True, proc.info['pid']
        except Exception:
            pass

        return False, None

    def check_responsiveness(self, app_name: str) -> str:
        """Determines process state using ctypes IsHungAppWindow and PowerShell Get-Process: NOT_RUNNING, RESPONSIVE, NOT_RESPONSIVE."""
        clean_name = self.normalize_name(app_name)
        proc_exe = self.KNOWN_MAPPINGS.get(clean_name, f"{clean_name}.exe").replace(".exe", "")

        # 1. Win32 IsHungAppWindow Check via ctypes
        if sys.platform == "win32":
            try:
                import ctypes
                user32 = ctypes.windll.user32
                ps_script = f'(Get-Process -Name "{proc_exe}" -ErrorAction SilentlyContinue | Where-Object {{ $_.MainWindowHandle -ne 0 }} | Select-Object -First 1).MainWindowHandle'
                res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], capture_output=True, text=True, timeout=2)
                hwnd_str = res.stdout.strip()
                if hwnd_str and hwnd_str.isdigit():
                    hwnd = int(hwnd_str)
                    if hwnd != 0 and user32.IsHungAppWindow(hwnd):
                        return "NOT_RESPONSIVE"
            except Exception:
                pass

        # 2. PowerShell .Responding Property Fallback
        try:
            ps_cmd = f'(Get-Process -Name "{proc_exe}" -ErrorAction SilentlyContinue | Select-Object -First 1).Responding'
            res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_cmd], capture_output=True, text=True, timeout=2)
            out = res.stdout.strip().lower()
            if "true" in out:
                return "RESPONSIVE"
            elif "false" in out:
                return "NOT_RESPONSIVE"
        except Exception:
            pass

        running, _ = self.is_running(clean_name)
        return "RESPONSIVE" if running else "NOT_RUNNING"

    def focus_window(self, app_name: str) -> bool:
        """Restores (SW_RESTORE=9) and brings an application window to the foreground by PID / Process Name."""
        clean_name = self.normalize_name(app_name)
        proc_exe = self.KNOWN_MAPPINGS.get(clean_name, f"{clean_name}.exe").replace(".exe", "")

        try:
            ps_script = f"""
            $proc = Get-Process -Name "{proc_exe}" -ErrorAction SilentlyContinue | Where-Object {{ $_.MainWindowHandle -ne 0 }} | Select-Object -First 1
            if ($proc) {{
                $hwnd = $proc.MainWindowHandle
                if (-not ("Win32Helper" -as [type])) {{
                    Add-Type -TypeDefinition @"
                    using System;
                    using System.Runtime.InteropServices;
                    public class Win32Helper {{
                        [DllImport("user32.dll")] public static extern bool ShowWindow(IntPtr hWnd, int nCmdShow);
                        [DllImport("user32.dll")] public static extern bool SetForegroundWindow(IntPtr hWnd);
                    }}
"@
                }}
                [Win32Helper]::ShowWindow($hwnd, 9)
                [Win32Helper]::SetForegroundWindow($hwnd)
                exit 0
            }} else {{
                exit 1
            }}
            """
            res = subprocess.run(["powershell", "-NoProfile", "-Command", ps_script], capture_output=True, timeout=2)
            return res.returncode == 0
        except Exception:
            return False

    def resolve_app_path(self, app_name: str) -> Optional[str]:
        """Resolves target application executable path via known mappings, Start Menu/WindowsApps cache, or system PATH."""
        clean_name = self.normalize_name(app_name)

        # Explicit Windows app location fallbacks
        custom_paths = {
            "spotify": [
                os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\WindowsApps\Spotify.exe"),
                os.path.expandvars(r"%APPDATA%\Spotify\Spotify.exe"),
                r"C:\Program Files\Spotify\Spotify.exe",
                r"C:\Program Files (x86)\Spotify\Spotify.exe"
            ]
        }

        if clean_name in custom_paths:
            for p in custom_paths[clean_name]:
                if os.path.exists(p) and SecurityEngine.is_safe_target(p):
                    return p

        if clean_name in self.KNOWN_MAPPINGS:
            exe_name = self.KNOWN_MAPPINGS[clean_name]
            path_match = shutil.which(exe_name)
            if path_match and SecurityEngine.is_safe_target(path_match):
                return path_match

        if clean_name in self.app_cache:
            return self.app_cache[clean_name]

        # Fuzzy match against Start Menu / WindowsApps cache
        if self.app_cache:
            match = process.extractOne(clean_name, list(self.app_cache.keys()), scorer=fuzz.partial_ratio)
            if match and match[1] >= 80:
                return self.app_cache[match[0]]

        # System PATH lookup fallback
        system_match = shutil.which(clean_name) or shutil.which(f"{clean_name}.exe")
        if system_match and SecurityEngine.is_safe_target(system_match):
            return system_match

        return None

    def launch_or_focus(self, app_name: str) -> Tuple[bool, str]:
        """Launches or focuses application, restoring minimized windows and force-killing frozen processes."""
        clean_name = self.normalize_name(app_name)
        proc_exe = self.KNOWN_MAPPINGS.get(clean_name, f"{clean_name}.exe")

        # 1. Check process responsiveness via IsHungAppWindow
        state = self.check_responsiveness(clean_name)

        if state == "NOT_RESPONSIVE":
            # Force-kill frozen process tree
            print(f"[AppResolver Notice]: Process '{clean_name}' is unresponsive (IsHungAppWindow=True). Executing force-kill...")
            subprocess.run(["taskkill", "/F", "/T", "/IM", proc_exe], capture_output=True, text=True)
            time.sleep(1.0)
            state = "NOT_RUNNING"

        # 2. Try focusing existing window handle first
        if state == "RESPONSIVE":
            if self.focus_window(clean_name):
                return True, f"Focused active window for '{clean_name.capitalize()}'."

        # 3. If window handle missing (running in background) or NOT_RUNNING, launch fresh instance
        app_path = self.resolve_app_path(clean_name)
        if app_path and SecurityEngine.is_safe_target(app_path):
            try:
                os.startfile(app_path)
            except Exception:
                os.system(f"start {clean_name}:")
        else:
            if clean_name in ["spotify", "steam", "discord"]:
                os.system(f"start {clean_name}:")

        # 4. Bounded wait for startup responsiveness & window focus
        start_t = time.time()
        while time.time() - start_t < 2.5:
            if self.focus_window(clean_name):
                return True, f"Launched '{clean_name.capitalize()}'."
            time.sleep(0.4)

        return True, f"Launched '{clean_name.capitalize()}'."
