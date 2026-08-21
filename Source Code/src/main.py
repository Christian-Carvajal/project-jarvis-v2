"""
Main Application Coordinator for Project JARVIS.
Features:
- Two-Turn Alternating Conversational State Machine (STANDBY_WAKE_WORD <-> ACTIVE_COMMAND)
- 100% Pure Agentic AI Reasoning Engine (Local Ollama qwen3.5:2b) with Zero Hardcoded Triggers
- Dynamic Cross-PC Desktop Automation & Apex Smart Home Simulator
- Modern Stark Dark Cyberpunk GUI Dashboard with Mic & HALT Controls
- Structured ISO Logging and Sub-2.0s Performance
"""

import os
import sys
import warnings

# Suppress HuggingFace Hub unauthenticated / symlink warnings on Windows
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"
os.environ["HF_HUB_DISABLE_IMPLICIT_TOKEN"] = "1"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
warnings.filterwarnings("ignore", category=UserWarning, module="huggingface_hub")
warnings.filterwarnings("ignore", message=".*unauthenticated requests.*")
warnings.filterwarnings("ignore", message=".*cache-system uses symlinks.*")

if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass

import time
import json
import logging
import threading
from enum import Enum
from datetime import datetime
from typing import Optional, Dict, Any, List

from src.ai_engine import AIEngine, AssistantIntentResponse, DeviceAction, PCAutomationEngine, DEFAULT_MODEL
from src.home_simulator import SmartHomeStateMachine, ModernHomeDashboard
from src.voice_pipeline import VoicePipeline

# Project and Directory paths
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
SEARCH_DIRS = [
    CURRENT_DIR,
    os.path.abspath(os.path.join(CURRENT_DIR, "..")),
    os.path.abspath(os.path.join(CURRENT_DIR, "..", "..")),
]
for d in SEARCH_DIRS:
    if d not in sys.path:
        sys.path.insert(0, d)

PROJECT_ROOT = CURRENT_DIR
for d in SEARCH_DIRS:
    if os.path.exists(os.path.join(d, "Execution Log")) or os.path.exists(os.path.join(d, "Source Code")):
        PROJECT_ROOT = d
        break

EXEC_LOG_DIR = os.path.join(PROJECT_ROOT, "Execution Log")
os.makedirs(EXEC_LOG_DIR, exist_ok=True)
LOG_FILE = os.path.join(EXEC_LOG_DIR, "assistant_execution.log")

# Setup structured logger
logging.basicConfig(
    filename=LOG_FILE,
    level=logging.INFO,
    format="%(message)s",
    encoding="utf-8"
)
logger = logging.getLogger("JarvisLogger")


class AssistantState(Enum):
    """Two-Turn Alternating Conversational State Machine."""
    STANDBY_WAKE_WORD = 1
    ACTIVE_COMMAND = 2


class JarvisVirtualAssistant:
    """
    Central Controller for JARVIS.
    Executes the Two-Turn Alternating Conversational State Machine:
    Phase 1: STANDBY_WAKE_WORD (Listens for voice command / wake phrase)
    Phase 2: ACTIVE_COMMAND (Listens directly for the follow-up command without requiring wake word)
    """

    def __init__(self):
        print("================================================================")
        print("  [+] PROJECT JARVIS - 2-TURN AGENTIC AI WORKSTATION (jarvis-trained-model)")
        print("  100% Offline | Pure Agentic Local LLM | British JARVIS Voice")
        print("================================================================")

        self.state = AssistantState.STANDBY_WAKE_WORD
        self.is_processing = False
        self.is_running = True

        # 1. Core Modules
        self.state_machine = SmartHomeStateMachine(log_filepath=LOG_FILE)
        self.ai = AIEngine(model_name="jarvis-trained-model")
        self.ai_engine = self.ai  # Alias for backward compatibility
        self.voice = VoicePipeline()
        self.voice_pipeline = self.voice  # Alias for backward compatibility

        # 2. Modern GUI Dashboard
        self.gui = ModernHomeDashboard(
            state_machine=self.state_machine,
            on_command_submit=self.handle_typed_command,
            on_halt_clicked=self.handle_emergency_halt,
            on_mic_toggle=self.handle_mic_toggle,
            on_model_change=self.handle_model_change,
            on_voice_trigger=self.handle_voice_trigger
        )
        self.simulator = self.gui  # Alias for blueprint compatibility

        self._ensure_log_header()

        # 3. Dedicated Two-Turn State Machine Worker Thread
        self.state_thread = threading.Thread(target=self._state_machine_worker, daemon=True)
        self.state_thread.start()

    def _ensure_log_header(self):
        """Initializes structured logging file inside Execution Log."""
        try:
            os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
            if not os.path.exists(LOG_FILE) or os.path.getsize(LOG_FILE) == 0:
                with open(LOG_FILE, "w", encoding="utf-8") as f:
                    f.write("# APEX HOME AUTOMATIONS & STARK PC SUITE - JARVIS EXECUTION LOG\n")
                    f.write("# Two-Turn Conversational State Machine & Pure Agentic LLM Reasoning\n\n")
        except Exception:
            pass

    def _safe_gui(self, callback):
        """Safely dispatches a UI update to Tkinter without crashing if mainloop is not active."""
        if hasattr(self, 'gui') and self.gui:
            try:
                self.gui.after(0, callback)
            except Exception:
                try:
                    callback()
                except Exception:
                    pass

    def reset_to_standby(self):
        """Resets assistant to Standby listening state."""
        self.state = AssistantState.STANDBY_WAKE_WORD
        self.is_processing = False
        self._safe_gui(lambda: self.gui.update_status("Standby (Waiting for Command)", "#00E5FF"))

    def _state_machine_worker(self):
        """
        Background Loop executing the Dual-Phase State Machine:
        Phase 1: STANDBY (Continuous acoustic listen for wake word or direct wake+command)
        Phase 2: ACTIVE (10-second open mic listening window)
        """
        while self.is_running:
            if not self.voice.is_listening:
                time.sleep(0.1)
                continue

            # =================================================================
            # PHASE 1: STANDBY (Awaiting Voice Command)
            # =================================================================
            if self.state == AssistantState.STANDBY_WAKE_WORD:
                self._safe_gui(lambda: self.gui.update_status("Standby (Waiting for Command)", "#00E5FF"))

                wake_detected, text = self.voice.listen_for_wake_word()

                if wake_detected:
                    self.is_processing = True
                    # If user spoke wake word + command, or natural prompt, send full query to LLM
                    query_prompt = text.strip() if (text and len(text.strip()) >= 2) else "hey jarvis"
                    self._safe_gui(lambda q=query_prompt: self.gui.log_console(f"⚡ VOICE INPUT: \"{q}\""))
                    self._execute_command_pipeline(query_prompt)
                    self.state = AssistantState.STANDBY_WAKE_WORD
                    self.is_processing = False

            # =================================================================
            # PHASE 2: ACTIVE COMMAND (No Wake Word Required)
            # =================================================================
            elif self.state == AssistantState.ACTIVE_COMMAND:
                self._safe_gui(lambda: self.gui.update_status("Listening for Command (10s)...", "#FFD700"))
                self._safe_gui(lambda: self.gui.log_console("[ACTIVE] Listening for your command (waiting up to 10 seconds)..."))

                command_text = self.voice.listen_raw_command(timeout=10.0)

                if command_text and len(command_text.strip()) >= 3:
                    self.is_processing = True
                    self._execute_command_pipeline(command_text.strip())
                else:
                    # 10-Second Timeout Fallback
                    timeout_msg = "Returning to standby, sir."
                    print(f"[ACTIVE TIMEOUT]: {timeout_msg}")
                    self._safe_gui(lambda: self.gui.log_console(f"[TIMEOUT] No command heard within 10 seconds. {timeout_msg}"))
                    self.voice.speak(timeout_msg)

                # Always reset back to standby after command execution or timeout
                self.state = AssistantState.STANDBY_WAKE_WORD
                self.is_processing = False

    def _execute_command_pipeline(self, prompt: str) -> str:
        """
        Unified Agentic Execution Pipeline:
        Prompt -> Pure Qwen 3.5 (2B) LLM -> Pydantic Schema -> (Smart Home + PC Action Dispatch) -> GUI & TTS.
        """
        start_time = time.time()
        self.is_processing = True

        print(f"\n[PIPELINE START]: Processing prompt -> '{prompt}'")
        self._safe_gui(lambda: self.gui.log_console(f"User Command: \"{prompt}\""))
        self._safe_gui(lambda: self.gui.update_status(f"Reasoning ({self.ai.model_name})...", "#E040FB"))

        # 1. Live Hardware Telemetry Injection & Pure LLM Intent Extraction
        live_summary = self.state_machine.get_summary_text()
        intent: AssistantIntentResponse = self.ai.parse_command(prompt, live_state=live_summary)
        latency_ms = (time.time() - start_time) * 1000

        print(f"[INTENT IDENTIFIED]: {intent.interpreted_intent}")
        if intent.reasoning:
            print(f"[CHAIN-OF-THOUGHT REASONING]: {intent.reasoning}")
        print(f"[ACTIONS PLANNED]: {len(intent.actions)} action(s)")

        self._safe_gui(lambda: self.gui.update_latency(latency_ms))
        if intent.reasoning:
            self._safe_gui(lambda r=intent.reasoning: self.gui.log_console(f"💭 REASONING: {r}"))
        self._safe_gui(lambda: self.gui.log_console(f"🧠 ACTION PLAN: {len(intent.actions)} action(s) planned"))

        # 2. Dispatch Actions (Deduplicated Execution)
        state_transitions: List[str] = []
        dispatched_sigs = set()

        for act in intent.actions:
            target = act.device_or_target
            action_name = act.action
            val = act.value

            sig = f"{act.domain}:{target}:{action_name}:{val}"
            if sig in dispatched_sigs:
                continue
            dispatched_sigs.add(sig)

            # Smart Home Domain
            if act.domain == "smart_home":
                msg = self.state_machine.apply_action(target, action_name, val)
                state_transitions.append(msg)
                print(f"  -> [Smart Home]: {target}.{action_name}({val}) | {msg}")
                self._safe_gui(lambda m=msg: self.gui.log_console(f"⚡ {m}"))

            # PC Desktop Automation Domain
            elif act.domain == "pc_automation":
                pc_msg = PCAutomationEngine.execute_pc_action(target, action_name, val)
                state_transitions.append(pc_msg)
                print(f"  -> [PC Automation]: {pc_msg}")
                self._safe_gui(lambda m=pc_msg: self.gui.log_console(f"⚡ {m}"))

        # 3. Refresh GUI state
        self._safe_gui(self.gui.refresh_dashboard)

        # 4. Spoken Response
        spoken = intent.spoken_response
        if spoken:
            spoken_clean = str(spoken).strip()
            for _ in range(5):
                if spoken_clean.startswith("{") and spoken_clean.endswith("}"):
                    try:
                        data = json.loads(spoken_clean)
                        if isinstance(data, dict):
                            if "spoken_response" in data:
                                spoken_clean = str(data["spoken_response"]).strip()
                            elif "response" in data:
                                spoken_clean = str(data["response"]).strip()
                            elif "message" in data:
                                spoken_clean = str(data["message"]).strip()
                    except Exception:
                        break
                else:
                    break

            for _ in range(10):
                found = False
                for token in [
                    '"spoken_response":', "'spoken_response':", 'spoken_response":', "spoken_response':", 'spoken_response:',
                    '"response":', "'response':", 'response":', "response':", 'response:',
                    '"message":', "'message':", 'message":', "message':", 'message:',
                    '"spoken_actions":', "'spoken_actions':", 'spoken_actions":', 'spoken_actions:',
                    '"actions":', "'actions':", 'actions":', 'actions:'
                ]:
                    if token in spoken_clean:
                        idx = spoken_clean.find(token) + len(token)
                        spoken_clean = spoken_clean[idx:].strip(' \t\n\r"\'{},[]')
                        found = True
                    if not found:
                        break

            spoken = spoken_clean.strip('{}[]"\' \t\n\r') if spoken_clean else "Command executed successfully, sir."

        print(f"[PIPELINE COMPLETE in {latency_ms:.1f}ms]: Spoken Response -> \"{spoken}\"")

        self._safe_gui(lambda: self.gui.log_console(f"⏱️ LATENCY: {latency_ms:.1f} ms | Status: PROCESSED"))
        self._safe_gui(lambda: self.gui.log_console(f"Jarvis: \"{spoken}\""))
        self._safe_gui(lambda: self.gui.update_status("Speaking Response...", "#00E676"))

        # Wait for TTS audio playback to completely finish before unmuting mic / returning to standby
        # This prevents the microphone from capturing speaker audio feedback and repeating commands
        event = threading.Event()
        self.voice.speak(spoken, callback=lambda: event.set())
        event.wait(timeout=10.0)
        time.sleep(0.4)

        # 5. Persist ISO Timestamped Audit Log
        self._write_execution_log(
            prompt=prompt,
            plan=intent,
            transitions="; ".join(state_transitions) if state_transitions else "None",
            latency_ms=latency_ms
        )

        self.reset_to_standby()
        return spoken

    def handle_user_command(self, command_text: str) -> str:
        """Alias for backward compatibility."""
        return self._execute_command_pipeline(command_text)

    def handle_typed_command(self, typed_text: str):
        """Asynchronous execution for text commands typed in the GUI."""
        if not typed_text or not typed_text.strip():
            return

        def _worker():
            self._execute_command_pipeline(typed_text.strip())

        threading.Thread(target=_worker, daemon=True).start()

    def handle_voice_trigger(self):
        """Asynchronous single-turn voice capture when user clicks 'SPEAK NOW' in the GUI."""
        if self.is_processing:
            return

        def _voice_worker():
            self.is_processing = True
            self._safe_gui(lambda: self.gui.update_status("Listening for Command (10s)...", "#00FF88"))
            self._safe_gui(lambda: self.gui.log_console("🎙️ [LISTENING]: Microphone active — speak your command (waiting up to 10s)..."))

            command_text = self.voice.listen_raw_command(timeout=10.0)

            if command_text and len(command_text.strip()) >= 3:
                self._safe_gui(lambda: self.gui.log_console(f"🎙️ [VOICE RECOGNIZED]: \"{command_text.strip()}\""))
                self._execute_command_pipeline(command_text.strip())
            else:
                msg = "No command detected, sir."
                self._safe_gui(lambda: self.gui.log_console(f"Jarvis: \"{msg}\""))
                self._safe_gui(lambda: self.gui.update_status("Standby (Waiting for Command)", "#00E5FF"))
                self.voice.speak(msg)
                self.is_processing = False

            self.reset_to_standby()

        threading.Thread(target=_voice_worker, daemon=True).start()

    def handle_emergency_halt(self):
        """Emergency HALT: Stops TTS playback and resets pipeline to Standby."""
        self.voice.halt_speech()
        self.is_processing = False
        self.state = AssistantState.STANDBY_WAKE_WORD
        self._safe_gui(lambda: self.gui.log_console("🛑 [HALT]: Emergency speech and execution override triggered!"))
        self._safe_gui(lambda: self.gui.update_status("🛑 HALTED", "#FF3366"))
        self._safe_gui(lambda: self.gui.after(1000, self.reset_to_standby))

    def handle_mic_toggle(self) -> bool:
        """Toggles hardware microphone state."""
        is_muted = self.voice.toggle_mic()
        if hasattr(self, 'gui') and self.gui:
            status_text = "🔇 Microphone MUTED." if is_muted else "🎙️ Microphone ONLINE."
            self.gui.log_console(f"🎙️ [HARDWARE]: {status_text}")
        return is_muted

    def handle_model_change(self, model_name: str):
        """Dynamically switches the active local LLM model."""
        self.ai.model_name = model_name
        if hasattr(self, 'gui') and self.gui:
            self.gui.log_console(f"🧠 [AI ENGINE]: Active model switched to '{model_name}'.")

    def _write_execution_log(self, prompt: str, plan: AssistantIntentResponse, transitions: str, latency_ms: float):
        """Writes structured execution record to log file."""
        try:
            iso_now = datetime.now().isoformat()
            plan_json = json.dumps(plan.model_dump(), indent=2)
            entry = f"""
======================================================================
TIMESTAMP: {iso_now}
VOICE TRANSCRIPTION: "{prompt}"
PARSED JSON PAYLOAD:
{plan_json}
STATE TRANSITIONS: {transitions}
EXECUTION LATENCY: {latency_ms:.2f} ms ({latency_ms/1000:.2f} s)
======================================================================
"""
            os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
            with open(LOG_FILE, "a", encoding="utf-8") as f:
                f.write(entry)
        except Exception as e:
            print(f"[Logging Error: {e}]")

    def run(self):
        """Starts Tkinter main loop."""
        try:
            self.gui.mainloop()
        except KeyboardInterrupt:
            pass
        finally:
            self.is_running = False
            self.voice.tts.stop()


# Alias for blueprint compatibility
JarvisApp = JarvisVirtualAssistant


def main():
    app = JarvisVirtualAssistant()
    app.run()


if __name__ == "__main__":
    main()
