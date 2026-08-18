import os
import sys
import time
import asyncio
import subprocess
import json
from typing import Tuple, Dict, Any, Optional, List


from core.security_engine import SecurityEngine


class MacroEngine:
    """Executes multi-step macro routines from macros.json asynchronously."""

    def __init__(self, macros_file: str = "config/macros.json"):
        self.macros_file = macros_file
        self.macros: Dict[str, Any] = {}
        self.load_macros()

    def load_macros(self):
        """Loads macro definitions from JSON configuration file."""
        if os.path.exists(self.macros_file):
            try:
                with open(self.macros_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.macros = data.get("macros", {})
            except Exception as e:
                print(f"[MacroEngine Error loading macros: {e}]")

    def get_macro(self, macro_key: str) -> Optional[Dict[str, Any]]:
        """Retrieves a specific macro by key with fuzzy matching fallback."""
        clean_key = macro_key.lower().strip().replace(" ", "_")
        if clean_key in self.macros:
            return self.macros[clean_key]

        matching = [k for k in self.macros.keys() if k in clean_key or clean_key in k]
        if matching:
            return self.macros[matching[0]]

        return None

    async def execute_macro_async(self, macro_name: str, action_engine=None) -> Tuple[bool, str]:
        """Executes a JSON macro routine asynchronously with non-blocking delays."""
        macro_data = self.get_macro(macro_name)
        if not macro_data:
            return False, f"Macro '{macro_name}' not recognized."

        steps = macro_data.get("actions") or macro_data.get("steps", [])
        macro_desc = macro_data.get("name") or macro_data.get("description", macro_name)
        feedbacks = []

        for step in steps:
            action_type = step.get("action") or step.get("type")
            target = step.get("target", "")

            if not SecurityEngine.is_safe_target(target):
                feedbacks.append(f"Blocked unsafe target '{target}'")
                continue

            if action_type in ["open_app", "launch"]:
                if action_engine:
                    success, msg = action_engine.launch_app_dynamically(target)
                    if success: feedbacks.append(msg)
                else:
                    subprocess.Popen(target, shell=True)
                    feedbacks.append(f"Launched {target}")
            elif action_type == "play_spotify":
                if action_engine:
                    success, msg = action_engine.play_on_spotify(target)
                    if success: feedbacks.append(msg)
            elif action_type == "play_youtube":
                if action_engine:
                    success, msg = action_engine.play_on_youtube(target)
                    if success: feedbacks.append(msg)
            elif action_type == "media_control":
                if action_engine:
                    success, msg = action_engine.handle_media_control(target)
                    if success: feedbacks.append(msg)
            elif action_type == "smart_home":
                if action_engine:
                    domain = "scene" if "scene" in target else "light"
                    success, msg = action_engine.ha_client.toggle_device(domain, "turn_on", target)
                    if success: feedbacks.append(msg)
            elif action_type == "delay":
                await asyncio.sleep(float(target))

            await asyncio.sleep(0.4)

        return True, f"Executed '{macro_desc}' routine: {', '.join(feedbacks) if feedbacks else 'Complete'}."

    def execute_macro(self, macro_name: str, action_engine=None) -> Tuple[bool, str]:
        """Synchronous fallback wrapper for macro execution."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                asyncio.create_task(self.execute_macro_async(macro_name, action_engine))
                return True, f"Initiated '{macro_name}' macro routine."
            else:
                return loop.run_until_complete(self.execute_macro_async(macro_name, action_engine))
        except Exception as e:
            return False, f"Macro execution error: {str(e)}"
