import asyncio
from typing import Optional, Callable, Tuple
from core.llm_manager import LLMManager
from core.tts_engine import TTSEngine
from core.stt_engine import STTEngine
from core.action_engine import ActionEngine
from core.memory_engine import MemoryEngine
from core.agent_planner import AgentPlanner, ActionPlan

class VoicePipeline:
    """Unified Orchestration Pipeline connecting STT, LLM Agent Planner, Tool System, TTS, and Memory engines with Single Response Path and Request ID Tracking."""

    def __init__(
        self,
        llm_manager: Optional[LLMManager] = None,
        tts_engine: Optional[TTSEngine] = None,
        stt_engine: Optional[STTEngine] = None,
        action_engine: Optional[ActionEngine] = None,
    ):
        self.llm = llm_manager or LLMManager(model_name="qwen2.5:1.5b")
        self.tts = tts_engine or TTSEngine()
        self.stt = stt_engine or STTEngine()
        self.action_engine = action_engine or ActionEngine()
        self.memory_engine = getattr(self.action_engine, 'memory_engine', MemoryEngine())
        self.planner = AgentPlanner(self.llm, self.memory_engine)
        self.is_running = False

    async def acknowledge(self, text: str = "At your service, sir."):
        """Play acknowledgment feedback when wake word is triggered."""
        print(f"\n[JARVIS]: {text}")
        await self.tts.speak_text(text)

    async def process_user_input(
        self,
        user_text: str,
        chunk_callback: Optional[Callable[[str, str], None]] = None,
        speak_audio: bool = True
    ) -> str:
        """Processes user command through AgentPlanner with single response path enforcement."""
        if not user_text.strip():
            return ""

        # Dispatch via Agent Planner
        def _hud_notify(stage: str, msg: str):
            if chunk_callback:
                chunk_callback(stage, msg)

        success, reply, plan = self.planner.plan_and_execute(user_text, hud_callback=_hud_notify)

        req_id = plan.request_id or "REQ-000000"
        print(f"[{req_id}][RESPONSE]\n{reply}\n")

        self.memory_engine.store_turn("user", user_text)
        self.memory_engine.store_turn("assistant", reply)

        # Single Authoritative Response Path: Only speak audio if requested (for CLI mode)
        if speak_audio:
            await self.tts.speak_text(reply)

        return reply

    async def run_voice_cycle(self) -> bool:
        """Run a single 2-stage wake word & command execution cycle."""
        print("\n[SYSTEM]: Listening for wake word ('Jarvis' / 'Hey Jarvis')...")
        wake_detected = await self.stt.detect_wake_word(timeout=4.0)

        if wake_detected:
            print("[SYSTEM]: Wake word detected!")
            await self.acknowledge("At your service, sir.")

            print("[SYSTEM]: Listening for command...")
            command = await self.stt.listen_command(timeout=6.0, phrase_time_limit=10.0)

            if command:
                await self.process_user_input(command, speak_audio=True)
            else:
                await self.tts.speak_text("I didn't catch that, sir.")
            return True
        return False

    async def run_pipeline_loop(self):
        """Continuous pipeline loop for wake word detection and command execution."""
        self.is_running = True
        print("=" * 60)
        print("  JARVIS VOICE PIPELINE — ACTIVE & LISTENING")
        print("=" * 60)

        while self.is_running:
            try:
                await self.run_voice_cycle()
                await asyncio.sleep(0.1)
            except asyncio.CancelledError:
                self.is_running = False
                break
            except Exception as e:
                print(f"\n[Pipeline Error: {e}]")
                await asyncio.sleep(1.0)
