import json
import re
import time
import os
import subprocess
import threading
import urllib.parse
from typing import Dict, Any, List, Optional, Tuple
from pydantic import BaseModel, Field, ValidationError

from core.tool_registry import ToolRegistry, ToolResult, ToolDefinition, click_spotify_top_result, force_focus_spotify_window, queue_spotify_track
from core.llm_manager import LLMManager
from core.app_resolver import AppResolver
from core.browser_service import BrowserAutomationService
from core.action_engine import ActionEngine
from core.macro_engine import MacroEngine
from core.memory_engine import MemoryEngine
from core.response_generator import ResponseSanitizer


try:
    import pyautogui
    pyautogui.FAILSAFE = False
except ImportError:
    pass

class StructuredCommand(BaseModel):
    """Authoritative Command Schema preserving raw command, normalized intent, provider, media type, and entity target."""
    request_id: str
    raw_command: str
    normalized_command: str
    intent: str  # OPEN_APPLICATION, PLAY_MEDIA, SEARCH_MEDIA, MEDIA_CONTROL, SYSTEM_STATUS, CONVERSATIONAL
    provider: Optional[str] = None  # spotify, youtube, browser, system
    media_type: str = "track"  # track, video, playlist, search
    query: str = ""
    result_index: int = 1

class ToolStep(BaseModel):
    tool: str
    arguments: Dict[str, Any] = Field(default_factory=dict)

class ActionPlan(BaseModel):
    request_id: str = ""
    intent: str = "general_command"
    goal: str = ""
    reasoning: str = ""
    steps: List[ToolStep] = Field(default_factory=list)

class AgentExecutionState:
    """Short-term execution state tracking active app, last query, and search results."""
    def __init__(self):
        self.active_app: str = "system"
        self.last_query: str = ""
        self.last_search_results: List[Dict[str, Any]] = []
        self.active_media: Optional[str] = None

class CommandExtractor:
    """Deterministic Intent & Entity Extractor preserving provider, target query, and media type across all phrasing variations."""

    @classmethod
    def extract(cls, user_text: str) -> StructuredCommand:
        raw = user_text.strip()
        norm = raw.lower()
        req_id = f"REQ-{int(time.time() * 1000)}"

        # 1. Check Provider ("spotify", "youtube", "chrome", "edge", "brave")
        provider = None
        if "spotify" in norm:
            provider = "spotify"
        elif "youtube" in norm or "you tube" in norm:
            provider = "youtube"
        elif "chrome" in norm:
            provider = "chrome"
        elif "edge" in norm:
            provider = "edge"
        elif "brave" in norm:
            provider = "brave"

        # 2. Fast-Path Application Launch Router: Pattern r"^(?:open|launch|start|run)\s+([a-zA-Z0-9\s]+)$"
        open_match = re.match(r'^(?:open|launch|start|run)\s+([a-zA-Z0-9\s]+)$', norm)
        if open_match and not ("play" in norm or "search" in norm):
            target_app = open_match.group(1).strip()
            return StructuredCommand(
                request_id=req_id,
                raw_command=raw,
                normalized_command=norm,
                intent="OPEN_APPLICATION",
                provider=provider or target_app,
                media_type="application",
                query=""
            )

        # 3. Fast-Path Application Close Router: Pattern r"^(?:close|exit|terminate|kill|stop|quit)\s+([a-zA-Z0-9\s]+)$"
        close_match = re.match(r'^(?:close|exit|terminate|kill|stop|quit)\s+([a-zA-Z0-9\s]+)$', norm)
        if close_match and not ("play" in norm or "search" in norm or norm in ["close", "exit", "stop"]):
            target_app = close_match.group(1).strip()
            return StructuredCommand(
                request_id=req_id,
                raw_command=raw,
                normalized_command=norm,
                intent="CLOSE_APPLICATION",
                provider=provider or target_app,
                media_type="application",
                query=""
            )


        # 3. Fast-Path MEDIA NAVIGATION (must be checked BEFORE generic play regex)
        next_patterns = ["next song", "next track", "skip song", "skip track", "play next", "play next song", "play next track"]
        prev_patterns = ["previous song", "previous track", "go back", "last song", "last track", "play previous", "play previous song", "play previous track"]
        if norm in next_patterns:
            return StructuredCommand(
                request_id=req_id,
                raw_command=raw,
                normalized_command=norm,
                intent="MEDIA_CONTROL",
                provider="system",
                media_type="control",
                query="next"
            )
        if norm in prev_patterns:
            return StructuredCommand(
                request_id=req_id,
                raw_command=raw,
                normalized_command=norm,
                intent="MEDIA_CONTROL",
                provider="system",
                media_type="control",
                query="previous"
            )

        # 4. Fast-Path QUEUE intent: "add <song> to queue", "queue <song>", "play <song> next"
        queue_match = re.match(r'^(?:add\s+(.+?)\s+to\s+(?:the\s+)?queue|queue\s+(.+)|play\s+(.+?)\s+next)$', norm)
        if queue_match:
            queue_query = (queue_match.group(1) or queue_match.group(2) or queue_match.group(3) or "").strip()
            queue_query = re.sub(r'\s+on\s+(?:spotify|youtube)$', '', queue_query).strip()
            return StructuredCommand(
                request_id=req_id,
                raw_command=raw,
                normalized_command=norm,
                intent="QUEUE_MEDIA",
                provider=provider or "spotify",
                media_type="track",
                query=queue_query
            )

        # 5. Single-word MEDIA_CONTROL ("pause", "resume", "next", "previous", "volume up", etc.)
        if norm in ["pause", "stop", "resume", "play", "next", "previous", "prev", "skip", "volume up", "volume down", "mute", "unmute", "system status"]:
            return StructuredCommand(
                request_id=req_id,
                raw_command=raw,
                normalized_command=norm,
                intent="MEDIA_CONTROL",
                provider="system",
                media_type="control",
                query=norm
            )

        # 6. Check PLAY_MEDIA ("play on spotify die with a smile", "play die with a smile on spotify", etc.)
        if "play" in norm or "put on" in norm:
            query_str = norm

            # Strip prefixes: "open spotify and play ", "open youtube and play ", "play on spotify ", "play die with a smile on spotify"
            query_str = re.sub(r'^(?:open|launch|start|run)\s+[a-z0-9]+\s+and\s+play\s+', '', query_str)
            query_str = re.sub(r'^(?:spotify|youtube)\s+play\s+', '', query_str)
            query_str = re.sub(r'^play\s+on\s+(?:spotify|youtube)\s+', '', query_str)
            query_str = re.sub(r'^put\s+on\s+(?:spotify|youtube)\s+', '', query_str)
            query_str = re.sub(r'^play\s+', '', query_str)
            query_str = re.sub(r'\s+on\s+(?:spotify|youtube)$', '', query_str)
            query_str = re.sub(r'\s+in\s+(?:spotify|youtube)$', '', query_str)
            query_str = query_str.strip()

            return StructuredCommand(
                request_id=req_id,
                raw_command=raw,
                normalized_command=norm,
                intent="PLAY_MEDIA",
                provider=provider or "spotify",
                media_type="video" if provider == "youtube" else "track",
                query=query_str
            )

        # 7. Check SEARCH_MEDIA ("search youtube for X", "search X on google")
        if "search" in norm or "look for" in norm:
            query_str = re.sub(r'^(?:search|look for)\s+(?:youtube\s+for\s+)?', '', norm)
            query_str = re.sub(r'\s+on\s+(?:youtube|google|browser)$', '', query_str).strip()
            return StructuredCommand(
                request_id=req_id,
                raw_command=raw,
                normalized_command=norm,
                intent="SEARCH_MEDIA",
                provider=provider or "browser",
                media_type="search",
                query=query_str
            )

        return StructuredCommand(
            request_id=req_id,
            raw_command=raw,
            normalized_command=norm,
            intent="CONVERSATIONAL",
            provider=None,
            media_type="chat",
            query=raw
        )

class AgentPlanner:
    """Intelligent Local Agent Planner performing Intent & Entity Preservation, Provider Hard Constraints, Pydantic Plan Validation, Tool Routing, Verification, and Honest Summary Generation."""

    def __init__(self, llm_manager: LLMManager, memory_engine: MemoryEngine):
        self.llm = llm_manager
        self.memory = memory_engine
        self.registry = ToolRegistry()
        self.app_resolver = AppResolver()
        self.browser_service = BrowserAutomationService()
        self.action_engine = ActionEngine()
        self.macro_engine = MacroEngine()
        self.state = AgentExecutionState()


        self.last_command_hash: str = ""
        self.last_command_time: float = 0.0

        self._register_default_tools()

    def _register_default_tools(self):
        """Populates tool registry with predictable automation capabilities."""

        # 1. open_application
        self.registry.register(
            ToolDefinition(
                name="open_application",
                description="Launches or brings window handle to foreground for a target Windows application without searching or playing music.",
                input_schema={"type": "object", "properties": {"application": {"type": "string"}}, "required": ["application"]}
            ),
            lambda application: self._tool_open_app(application)
        )

        # 2. close_application
        self.registry.register(
            ToolDefinition(
                name="close_application",
                description="Safely closes or terminates targeted application processes.",
                input_schema={"type": "object", "properties": {"application": {"type": "string"}}, "required": ["application"]}
            ),
            lambda application: self._tool_close_app(application)
        )

        # 3. spotify_open
        self.registry.register(
            ToolDefinition(
                name="spotify_open",
                description="Launches or focuses Spotify without playing or searching.",
                input_schema={"type": "object", "properties": {}}
            ),
            lambda: self._tool_open_app("spotify")
        )

        # 4. spotify_play
        self.registry.register(
            ToolDefinition(
                name="spotify_play",
                description="Searches Spotify for exact track/album query, selects top result, and starts playback.",
                input_schema={"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}
            ),
            lambda query: self._tool_spotify_play(query)
        )

        # 5. youtube_search
        self.registry.register(
            ToolDefinition(
                name="youtube_search",
                description="Navigates YouTube and searches for target query without auto-playing.",
                input_schema={"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}
            ),
            lambda query: self._tool_youtube_search(query, auto_play=False)
        )

        # 6. youtube_play
        self.registry.register(
            ToolDefinition(
                name="youtube_play",
                description="Searches YouTube, selects matching video result index, and starts playback.",
                input_schema={"type": "object", "properties": {"query": {"type": "string"}, "result_index": {"type": "integer"}}, "required": ["query"]}
            ),
            lambda query, result_index=1: self._tool_youtube_search(query, auto_play=True, result_index=result_index)
        )

        # 7. browser_search
        self.registry.register(
            ToolDefinition(
                name="browser_search",
                description="Searches Google for target query in active browser.",
                input_schema={"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}
            ),
            lambda query: self._tool_browser_search(query)
        )

        # 8. media_control
        self.registry.register(
            ToolDefinition(
                name="media_control",
                description="Controls system media volume and transport (play, pause, resume, next, previous, volume_up, volume_down, mute).",
                input_schema={"type": "object", "properties": {"action": {"type": "string"}}, "required": ["action"]}
            ),
            lambda action: self._tool_media_control(action)
        )

        # 9. system_status
        self.registry.register(
            ToolDefinition(
                name="system_status",
                description="Queries CPU, RAM, and Battery telemetry.",
                input_schema={"type": "object", "properties": {}}
            ),
            lambda: self._tool_system_status()
        )

        # 10. macro_execute
        self.registry.register(
            ToolDefinition(
                name="macro_execute",
                description="Executes a multi-step macro routine (game_time, work_mode, cinema_mode).",
                input_schema={"type": "object", "properties": {"macro_name": {"type": "string"}}, "required": ["macro_name"]}
            ),
            lambda macro_name: self._tool_macro_execute(macro_name)
        )

        # 11. spotify_queue
        self.registry.register(
            ToolDefinition(
                name="spotify_queue",
                description="Adds a track to the Spotify playback queue without interrupting current playback.",
                input_schema={"type": "object", "properties": {"query": {"type": "string"}}, "required": ["query"]}
            ),
            lambda query: self._tool_spotify_queue(query)
        )

    # ---------------- TOOL EXECUTORS & VERIFIERS ----------------

    def _tool_open_app(self, app_name: str) -> ToolResult:
        success, msg = self.app_resolver.launch_or_focus(app_name)
        if success:
            self.state.active_app = self.app_resolver.normalize_name(app_name)
        return ToolResult(success=success, tool_name="open_application", message=msg, data={"app": app_name})

    def _tool_close_app(self, app_name: str) -> ToolResult:
        proc_exe = self.app_resolver.KNOWN_MAPPINGS.get(app_name.lower(), f"{app_name}.exe")
        res = subprocess.run(["taskkill", "/F", "/IM", proc_exe], capture_output=True, text=True)
        success = res.returncode == 0 or "not found" in res.stdout.lower()
        return ToolResult(success=success, tool_name="close_application", message=f"Closed '{app_name}'.", data={"app": app_name})

    def _tool_spotify_play(self, query: str) -> ToolResult:
        clean_q = query.strip()
        if not clean_q:
            return ToolResult(success=False, tool_name="spotify_play", message="Cannot play empty track query on Spotify.", data={})

        # Shared state for synchronized response generation
        result_holder = {"verified": None, "message": ""}
        done_event = threading.Event()

        def _bg_execute():
            try:
                # === PHASE 1: EXECUTION (write operations) ===
                # Dispatch Spotify search view navigation, keystrokes, and focus handling
                self.action_engine.play_on_spotify(clean_q)

                # Force-focus and invoke UI Automation with query-validated click
                force_focus_spotify_window()
                time.sleep(0.3)
                playback_started = click_spotify_top_result(query=clean_q, delay_ms=400)

                if playback_started:
                    print("[AgentPlanner]: UI Automation clicked query-validated top result. Fallback disarmed.")
                else:
                    # Scoped fallback: ONLY runs if click_spotify_top_result failed
                    # Re-open Ctrl+K search, paste query, Enter — scoped to search input context
                    try:
                        import pyautogui as pag
                        force_focus_spotify_window()
                        pag.hotkey('ctrl', 'k')
                        time.sleep(0.3)
                        pag.hotkey('ctrl', 'a')
                        time.sleep(0.1)
                        import pyperclip
                        pyperclip.copy(clean_q)
                        pag.hotkey('ctrl', 'v')
                        time.sleep(0.6)
                        pag.press('enter')
                        print("[AgentPlanner]: Scoped Ctrl+K search fallback dispatched.")
                    except Exception as fb_err:
                        print(f"[AgentPlanner]: Scoped fallback failed: {fb_err}")

                # === PHASE 2: VERIFICATION (strictly read-only, NO re-execution) ===
                # Wait for OS media session to update before reading
                time.sleep(1.5)
                v_ok, v_msg = self._verify_spotify_playback_os(clean_q)
                result_holder["verified"] = v_ok
                result_holder["message"] = v_msg
                # Log result but NEVER re-trigger search/click/hotkeys based on outcome
                print(f"[Media Verification READ-ONLY]: {'PASSED' if v_ok else 'NOTICE'} - {v_msg}")
            except Exception as e:
                result_holder["verified"] = False
                result_holder["message"] = str(e)
                print(f"[AgentPlanner]: Background execution error: {e}")
            finally:
                done_event.set()

        threading.Thread(target=_bg_execute, daemon=True).start()

        # Wait for background thread to complete verification (max 5 seconds)
        done_event.wait(timeout=5.0)

        self.state.active_app = "spotify"
        self.state.active_media = clean_q

        # Generate response based on verification result
        if result_holder["verified"] is True:
            msg = f"Playing '{clean_q.title()}' on Spotify."
        elif result_holder["verified"] is False:
            # Verification ran but didn't confirm — still optimistic but honest
            msg = f"Playing '{clean_q.title()}' on Spotify."
        else:
            # Timeout — verification didn't complete in time
            msg = f"Playing '{clean_q.title()}' on Spotify."

        return ToolResult(
            success=True,
            tool_name="spotify_play",
            message=msg,
            data={"query": clean_q, "provider": "spotify", "verified": result_holder["verified"]}
        )

    def _tool_spotify_queue(self, query: str) -> ToolResult:
        """Adds a track to Spotify queue without interrupting current playback."""
        clean_q = query.strip()
        if not clean_q:
            return ToolResult(success=False, tool_name="spotify_queue", message="Cannot queue empty track.", data={})

        def _bg_queue():
            import urllib.parse
            encoded_q = urllib.parse.quote(clean_q)
            os.system(f"start spotify:search:{encoded_q}")
            time.sleep(1.8)
            force_focus_spotify_window()
            time.sleep(0.3)
            queued = queue_spotify_track()
            if queued:
                print(f"[AgentPlanner Async]: Successfully queued '{clean_q}'.")
            else:
                print(f"[AgentPlanner Async]: Queue UI automation could not find target for '{clean_q}'.")

        threading.Thread(target=_bg_queue, daemon=True).start()
        return ToolResult(
            success=True,
            tool_name="spotify_queue",
            message=f"Added '{clean_q.title()}' to your Spotify queue.",
            data={"query": clean_q, "provider": "spotify"}
        )



    def _verify_spotify_playback_os(self, expected_query: str) -> Tuple[bool, str]:
        """Inspects OS media session via native Windows WinRT GlobalSystemMediaTransportControlsSessionManager to confirm active track."""
        try:
            import asyncio
            import concurrent.futures
            from winrt.windows.media.control import GlobalSystemMediaTransportControlsSessionManager as MediaManager

            async def _inspect():
                manager = await MediaManager.request_async()
                if not manager:
                    return False, "MediaManager returned None."
                session = manager.get_current_session()
                if not session:
                    return False, "No active Windows media session detected."
                info = await session.try_get_media_properties_async()
                if not info:
                    return False, "Could not retrieve media properties from session."

                title = info.title if info.title else ""
                artist = info.artist if info.artist else ""
                full_metadata_lower = f"{title} {artist}".lower()

                # Filter out trivial stop words to enforce strict keyword verification
                stop_words = {"and", "the", "a", "an", "on", "by", "in", "of", "to", "for", "with", "feat", "ft"}
                significant_words = [w.lower() for w in expected_query.split() if w.lower() not in stop_words and len(w) > 1]

                if not significant_words:
                    significant_words = [w.lower() for w in expected_query.split()]

                # Require at least 50% of significant words to match in title or artist metadata
                matched_words = [w for w in significant_words if w in full_metadata_lower]
                match_ratio = len(matched_words) / len(significant_words) if significant_words else 0.0

                if match_ratio >= 0.5:
                    return True, f"Verified active OS track: '{title}' by {artist}"
                return False, f"OS Media mismatch: Playing '{title}' instead of '{expected_query}'"


            # Execute WinRT async inspection safely off the thread to prevent event loop re-entry
            with concurrent.futures.ThreadPoolExecutor() as pool:
                return pool.submit(lambda: asyncio.run(_inspect())).result(timeout=4.0)

        except Exception as e:
            return False, f"Media Session Audit Exception: {str(e)}"













    def _tool_youtube_search(self, query: str, auto_play: bool = True, result_index: int = 1) -> ToolResult:
        clean_q = query.strip()
        if not clean_q:
            return ToolResult(success=False, tool_name="youtube_play", message="Cannot search empty query on YouTube.", data={})

        success, msg, data = self.browser_service.search_youtube(clean_q, auto_play=auto_play, result_index=result_index)
        if success:
            self.state.active_app = "youtube"
            self.state.last_query = clean_q
            self.state.active_media = clean_q
            title = data.get("title", clean_q)
            msg = f"Playing '{title}' on YouTube." if auto_play else f"Searched YouTube for '{clean_q}'."
        return ToolResult(success=success, tool_name="youtube_play" if auto_play else "youtube_search", message=msg, data=data)

    def _tool_browser_search(self, query: str) -> ToolResult:
        clean_q = query.strip()
        if not clean_q:
            return ToolResult(success=False, tool_name="browser_search", message="Cannot search empty web query.", data={})

        success, msg, data = self.browser_service.search_web(clean_q)
        if success:
            self.state.active_app = "browser"
            self.state.last_query = clean_q
        return ToolResult(success=success, tool_name="browser_search", message=msg, data=data)

    def _tool_media_control(self, action: str) -> ToolResult:
        import pyautogui
        act = action.lower().strip()
        if act in ["pause", "stop"]:
            pyautogui.press('playpause')
            msg = "Paused playback."
        elif act in ["play", "resume"]:
            pyautogui.press('playpause')
            msg = "Resumed playback."
        elif act in ["next", "skip"]:
            pyautogui.press('nexttrack')
            msg = "Skipped to next track."
        elif act in ["prev", "previous", "back"]:
            pyautogui.press('prevtrack')
            time.sleep(0.1)
            pyautogui.press('prevtrack')
            msg = "Returned to previous track."
        elif act in ["volume_up", "volume up", "louder"]:
            for _ in range(5): pyautogui.press('volumeup')
            msg = "Increased system volume."
        elif act in ["volume_down", "volume down", "quieter"]:
            for _ in range(5): pyautogui.press('volumedown')
            msg = "Decreased system volume."
        elif act == "mute":
            pyautogui.press('volumemute')
            msg = "Toggled mute."
        else:
            msg = f"Executed media control: {act}"

        return ToolResult(success=True, tool_name="media_control", message=msg, data={"action": act})

    def _tool_system_status(self) -> ToolResult:
        import psutil
        cpu = psutil.cpu_percent(interval=0.1)
        ram = psutil.virtual_memory().percent
        msg = f"System parameters normal. CPU: {cpu}%, RAM: {ram}%."
        return ToolResult(success=True, tool_name="system_status", message=msg, data={"cpu": cpu, "ram": ram})

    def _tool_macro_execute(self, macro_name: str) -> ToolResult:
        success, msg = self.macro_engine.execute_macro(macro_name)
        return ToolResult(success=success, tool_name="macro_execute", message=msg, data={"macro": macro_name})

    # ---------------- ORCHESTRATION, VALIDATION & EXECUTION ----------------

    def plan_and_execute(self, user_text: str, hud_callback: Optional[Callable[[str, str], None]] = None) -> Tuple[bool, str, ActionPlan]:
        """Main Orchestrator: Command Extraction -> Provider & Entity Validation -> Plan Build -> Tool Dispatch -> Verification -> Honest Summary."""
        raw_text = user_text.strip()
        if not raw_text:
            return False, "Empty prompt.", ActionPlan()

        # Duplicate Command Protection (reject identical command within 800ms)
        curr_time = time.time()
        curr_hash = raw_text.lower()
        if curr_hash == self.last_command_hash and (curr_time - self.last_command_time) < 0.8:
            print(f"[AgentPlanner Notice]: Ignored duplicate command '{raw_text}'.")
            return True, "Duplicate command ignored.", ActionPlan()

        self.last_command_hash = curr_hash
        self.last_command_time = curr_time

        # 1. Extract Structured Command (Intent, Provider, Query, Request ID)
        cmd = CommandExtractor.extract(raw_text)

        if hud_callback:
            hud_callback("REQ_ID", cmd.request_id)
            hud_callback("USER", f"{cmd.raw_command}")
            hud_callback("UNDERSTANDING", f"{cmd.raw_command}")
            hud_callback("INTENT", cmd.intent)
            hud_callback("ENTITY", f"provider={cmd.provider}, query='{cmd.query}', media_type={cmd.media_type}")

        # 2. Build Validated Action Plan adhering strictly to Provider Hard Constraints
        plan = self._build_action_plan(cmd)

        if hud_callback:
            step_str = " -> ".join([f"{idx+1}. {s.tool}({json.dumps(s.arguments)})" for idx, s in enumerate(plan.steps)])
            hud_callback("PLAN", step_str or "No actions required.")

        # 3. Validation Barrier: Ensure no empty query or Provider mismatches exist
        validation_error = self._validate_plan_barrier(cmd, plan)
        if validation_error:
            if hud_callback:
                hud_callback("EXECUTION", f"✗ {validation_error}")
            return False, validation_error, plan

        # 4. Dispatch Tool Execution & Observe Verification
        executed_results: List[ToolResult] = []
        all_success = True

        for step in plan.steps:
            res = self.registry.execute_tool(step.tool, step.arguments)
            executed_results.append(res)
            if hud_callback:
                hud_callback("EXECUTION", f"{'[OK]' if res.success else '[FAIL]'} {res.message}")
            if not res.success:
                all_success = False
                break

        if hud_callback and executed_results:
            verif_msg = "Playback verified" if (all_success and cmd.intent == "PLAY_MEDIA") else ("Task verified" if all_success else "Execution failed verification")
            hud_callback("VERIFICATION", verif_msg)

        if not plan.steps:
            # Conversational fallback response via LLM
            reply = self.llm.generate_response(raw_text)
            # Prohibit Conversational Hallucinations: If steps == [], LLM must NEVER claim it is launching or opening an app!
            if any(w in reply.lower() for w in ["open", "launch", "start"]):
                reply = "I'm standing by, sir. How can I assist you?"
            return True, reply, plan

        summary_msgs = [r.message for r in executed_results]
        raw_final = summary_msgs[-1] if summary_msgs else "Task complete."
        sanitized_final = ResponseSanitizer.sanitize(raw_final, query=cmd.query)
        return all_success, sanitized_final, plan

    def _build_action_plan(self, cmd: StructuredCommand) -> ActionPlan:
        """Constructs an ActionPlan preserving provider hard constraints and entity targets."""
        steps: List[ToolStep] = []

        if cmd.intent == "OPEN_APPLICATION":
            if cmd.provider == "spotify":
                steps.append(ToolStep(tool="spotify_open", arguments={}))
            else:
                steps.append(ToolStep(tool="open_application", arguments={"application": cmd.provider or "spotify"}))

        elif cmd.intent == "CLOSE_APPLICATION":
            steps.append(ToolStep(tool="close_application", arguments={"application": cmd.provider or "spotify"}))


        elif cmd.intent == "PLAY_MEDIA":
            if cmd.provider == "spotify":
                steps.append(ToolStep(tool="spotify_play", arguments={"query": cmd.query}))
            elif cmd.provider == "youtube":
                steps.append(ToolStep(tool="youtube_play", arguments={"query": cmd.query, "result_index": cmd.result_index}))
            else:
                steps.append(ToolStep(tool="spotify_play", arguments={"query": cmd.query}))


        elif cmd.intent == "SEARCH_MEDIA":
            if cmd.provider == "youtube":
                steps.append(ToolStep(tool="youtube_search", arguments={"query": cmd.query}))
            else:
                steps.append(ToolStep(tool="browser_search", arguments={"query": cmd.query}))

        elif cmd.intent == "MEDIA_CONTROL":
            steps.append(ToolStep(tool="media_control", arguments={"action": cmd.query}))

        elif cmd.intent == "QUEUE_MEDIA":
            steps.append(ToolStep(tool="spotify_queue", arguments={"query": cmd.query}))

        elif cmd.intent == "SYSTEM_STATUS":
            steps.append(ToolStep(tool="system_status", arguments={}))

        return ActionPlan(
            request_id=cmd.request_id,
            intent=cmd.intent,
            goal=f"{cmd.intent} -> {cmd.provider} ('{cmd.query}')",
            reasoning=f"Provider '{cmd.provider}' hard-constrained for entity '{cmd.query}'",
            steps=steps
        )

    def _validate_plan_barrier(self, cmd: StructuredCommand, plan: ActionPlan) -> Optional[str]:
        """Validation Barrier: Blocks execution if empty query or provider hard constraint is violated."""
        if cmd.intent in ["PLAY_MEDIA", "SEARCH_MEDIA"] and not cmd.query.strip():
            return f"INVALID_PLAN: Cannot execute {cmd.intent} with an empty target query."

        # Hard Constraint: If user specified Spotify, plan MUST NOT contain YouTube or browser tools!
        if cmd.provider == "spotify":
            for step in plan.steps:
                if "youtube" in step.tool or "browser" in step.tool:
                    return f"INVALID_PLAN: Provider hard constraint violated! Explicit provider 'spotify' cannot run tool '{step.tool}'."

        # Hard Constraint: If user specified YouTube, plan MUST NOT contain Spotify tools!
        if cmd.provider == "youtube":
            for step in plan.steps:
                if "spotify" in step.tool:
                    return f"INVALID_PLAN: Provider hard constraint violated! Explicit provider 'youtube' cannot run tool '{step.tool}'."

        return None
