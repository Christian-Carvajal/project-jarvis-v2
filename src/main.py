"""
Main Application Coordinator for Project JARVIS.
Features:
- Two-Turn Alternating Conversational State Machine (STANDBY_WAKE_WORD <-> ACTIVE_COMMAND)
- 100% Pure Agentic AI Reasoning Engine (Local Ollama qwen2.5:1.5b) with Zero Hardcoded Triggers
- Dynamic Cross-PC Desktop Automation & Apex Smart Home Simulator
- Modern Stark Dark Cyberpunk GUI Dashboard with Mic & HALT Controls
- Structured ISO Logging and Sub-2.0s Performance
"""

import os
import sys
import time
import json
import logging
import threading
from enum import Enum
from datetime import datetime
from typing import Optional, Dict, Any, List

from src.ai_engine import AIEngine, AssistantIntentResponse, DeviceAction, PCAutomationEngine
from src.home_simulator import SmartHomeStateMachine, ModernHomeDashboard
from src.voice_pipeline import VoicePipeline

# Setup structured logger
LOG_FILE = "assistant_execution.log"
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
    Phase 1: STANDBY_WAKE_WORD (Listens for 'Hey Jarvis')
    Phase 2: ACTIVE_COMMAND (Listens directly for the follow-up command without requiring wake word)
    """

    def __init__(self):
        print("================================================================")
        print("  ⚡ PROJECT JARVIS — 2-TURN AGENTIC AI WORKSTATION")
        print("  100% Offline | Pure Agentic Local LLM | British JARVIS Voice")
        print("================================================================")

        self.state = AssistantState.STANDBY_WAKE_WORD
        self.is_processing = False
        self.is_running = True

        # 1. Core Modules
        self.state_machine = SmartHomeStateMachine(log_filepath=LOG_FILE)
        self.ai = AIEngine(model_name="qwen2.5:1.5b")
        self.ai_engine = self.ai  # Alias for backward compatibility
        self.voice = VoicePipeline()
        self.voice_pipeline = self.voice  # Alias for backward compatibility

        # 2. Modern GUI Dashboard
        self.gui = ModernHomeDashboard(
            state_machine=self.state_machine,
            on_command_submit=self.handle_typed_command,
            on_halt_clicked=self.handle_emergency_halt,
            on_mic_toggle=self.handle_mic_toggle,
            on_model_change=self.handle_model_change
        )
        self.simulator = self.gui  # Alias for blueprint compatibility

        self._ensure_log_header()

        # 3. Dedicated Two-Turn State Machine Worker Thread
        self.state_thread = threading.Thread(target=self._state_machine_worker, daemon=True)
        self.state_thread.start()

    def _ensure_log_header(self):
        """Initializes structured logging file."""
        if not os.path.exists(LOG_FILE) or os.path.getsize(LOG_FILE) == 0:
            with open(LOG_FILE, "w", encoding="utf-8") as f:
                f.write("# APEX HOME AUTOMATIONS & STARK PC SUITE - JARVIS EXECUTION LOG\n")
                f.write("# Two-Turn Conversational State Machine & Pure Agentic LLM Reasoning\n\n")

    def _reset_to_standby(self):
        """Resets assistant to Standby listening state."""
        self.is_processing = False
        self.state = AssistantState.STANDBY_WAKE_WORD
        if hasattr(self, 'gui') and self.gui:
            self.gui.after(0, lambda: self.gui.update_status("Standby (Waiting for 'Jarvis')", "#00E5FF"))

    def _state_machine_worker(self):
        """
        Two-Turn State Machine Loop:
        - PHASE 1: STANDBY_WAKE_WORD -> Listens for 'Hey Jarvis'
        - PHASE 2: ACTIVE_COMMAND -> Listens for command WITHOUT wake word
        """
        time.sleep(0.5)

        while self.is_running:
            if self.is_processing or self.voice.is_mic_muted:
                time.sleep(0.1)
                continue

            # =================================================================
            # PHASE 1: STANDBY (Awaiting Wake Word)
            # =================================================================
            if self.state == AssistantState.STANDBY_WAKE_WORD:
                if hasattr(self, 'gui') and self.gui:
                    self.gui.after(0, lambda: self.gui.update_status("Standby (Waiting for 'Jarvis')", "#00E5FF"))

                wake_detected, text = self.voice.listen_for_wake_word()

                if wake_detected:
                    self.is_processing = True

                    # Check if user spoke wake word + command all in one breath
                    if text and len(text.strip()) >= 3:
                        self.gui.after(0, lambda: self.gui.log_console(f"⚡ WAKE + COMMAND: \"{text.strip()}\""))
                        self._execute_command_pipeline(text.strip())
                        self.state = AssistantState.STANDBY_WAKE_WORD
                        self.is_processing = False
                    else:
                        # User only said "Hey Jarvis" -> Speak ack & transition to ACTIVE_COMMAND
                        ack_msg = "At your service, sir. What can I do for you?"
                        print(f"[JARVIS Acknowledgment]: \"{ack_msg}\"")
                        if hasattr(self, 'gui') and self.gui:
                            self.gui.after(0, lambda: self.gui.log_console(f"Jarvis: \"{ack_msg}\""))
                            self.gui.after(0, lambda: self.gui.update_status("Speaking Acknowledgment...", "#00E676"))

                        def on_ack_done():
                            self.state = AssistantState.ACTIVE_COMMAND
                            self.is_processing = False

                        self.voice.speak(ack_msg, callback=on_ack_done)
                        # Small buffer to ensure TTS completes before active recording
                        time.sleep(1.8)

            # =================================================================
            # PHASE 2: ACTIVE COMMAND (No Wake Word Required)
            # =================================================================
            elif self.state == AssistantState.ACTIVE_COMMAND:
                if hasattr(self, 'gui') and self.gui:
                    self.gui.after(0, lambda: self.gui.update_status("Listening for Command...", "#FFD700"))
                    self.gui.after(0, lambda: self.gui.log_console("[ACTIVE] Listening for your command (no wake word needed)..."))

                command_text = self.voice.listen_raw_command(timeout=6.0)

                if command_text and len(command_text.strip()) >= 3:
                    self.is_processing = True
                    self._execute_command_pipeline(command_text.strip())
                else:
                    # 6-Second Timeout Fallback
                    timeout_msg = "Returning to standby, sir."
                    print(f"[ACTIVE TIMEOUT]: {timeout_msg}")
                    if hasattr(self, 'gui') and self.gui:
                        self.gui.after(0, lambda: self.gui.log_console(f"[TIMEOUT] No command heard. {timeout_msg}"))
                    self.voice.speak(timeout_msg)

                # Always reset back to standby after command execution or timeout
                self.state = AssistantState.STANDBY_WAKE_WORD
                self.is_processing = False

    def _execute_command_pipeline(self, prompt: str) -> str:
        """
        Unified Agentic Execution Pipeline:
        Prompt -> Pure Qwen 2.5 LLM -> Pydantic Schema -> (Smart Home + PC Action Dispatch) -> GUI & TTS.
        """
        start_time = time.time()
        self.is_processing = True

        print(f"\n[PIPELINE START]: Processing prompt -> '{prompt}'")
        if hasattr(self, 'gui') and self.gui:
            self.gui.after(0, lambda: self.gui.log_console(f"User Command: \"{prompt}\""))
            self.gui.after(0, lambda: self.gui.update_status("Reasoning (Qwen 2.5)...", "#E040FB"))

        # 1. Pure LLM Intent Extraction (Zero hardcoded regex)
        intent: AssistantIntentResponse = self.ai.parse_command(prompt)
        latency_ms = (time.time() - start_time) * 1000

        print(f"[INTENT IDENTIFIED]: {intent.interpreted_intent}")
        print(f"[ACTIONS PLANNED]: {len(intent.actions)} action(s)")

        if hasattr(self, 'gui') and self.gui:
            self.gui.after(0, lambda: self.gui.update_latency(latency_ms))
            self.gui.after(0, lambda: self.gui.log_console(f"🧠 ACTION PLAN: {len(intent.actions)} action(s) planned"))

        # 2. Dispatch Actions
        state_transitions: List[str] = []

        for act in intent.actions:
            target = act.device_or_target
            action_name = act.action
            val = act.value

            # Smart Home Domain
            if act.domain == "smart_home":
                msg = self.state_machine.apply_action(target, action_name, val)
                state_transitions.append(msg)
                print(f"  -> [Smart Home]: {target}.{action_name}({val}) | {msg}")
                if hasattr(self, 'gui') and self.gui:
                    self.gui.after(0, lambda m=msg: self.gui.log_console(f"⚡ {m}"))

            # PC Desktop Automation Domain
            elif act.domain == "pc_automation":
                pc_msg = PCAutomationEngine.execute_pc_action(target, action_name, val)
                state_transitions.append(pc_msg)
                print(f"  -> [PC Automation]: {pc_msg}")
                if hasattr(self, 'gui') and self.gui:
                    self.gui.after(0, lambda m=pc_msg: self.gui.log_console(f"⚡ {m}"))

        # 3. Refresh GUI state
        if hasattr(self, 'gui') and self.gui:
            self.gui.after(0, self.gui.refresh_dashboard)

        # 4. Spoken Response
        spoken = intent.spoken_response
        print(f"[PIPELINE COMPLETE in {latency_ms:.1f}ms]: Spoken Response -> \"{spoken}\"")

        if hasattr(self, 'gui') and self.gui:
            self.gui.after(0, lambda: self.gui.log_console(f"⏱️ LATENCY: {latency_ms:.1f} ms | Status: PROCESSED"))
            self.gui.after(0, lambda: self.gui.log_console(f"Jarvis: \"{spoken}\""))
            self.gui.after(0, lambda: self.gui.update_status("Speaking Response...", "#00E676"))

        event = threading.Event()
        self.voice.speak(spoken, callback=lambda: event.set())

        # 5. Persist ISO Timestamped Audit Log
        self._write_execution_log(
            prompt=prompt,
            plan=intent,
            transitions="; ".join(state_transitions) if state_transitions else "None",
            latency_ms=latency_ms
        )

        self._reset_to_standby()
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

    def handle_emergency_halt(self):
        """Emergency HALT: Stops TTS playback and resets pipeline to Standby."""
        self.voice.halt_speech()
        self.is_processing = False
        self.state = AssistantState.STANDBY_WAKE_WORD
        if hasattr(self, 'gui') and self.gui:
            self.gui.log_console("🛑 [HALT]: Emergency speech and execution override triggered!")
            self.gui.update_status("🛑 HALTED", "#FF3366")
            self.gui.after(1000, self._reset_to_standby)

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
