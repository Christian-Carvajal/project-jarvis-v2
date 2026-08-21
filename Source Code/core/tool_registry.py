import time
import json
from typing import Dict, Any, Callable, List, Optional, Tuple
from pydantic import BaseModel, Field

try:
    import win32gui
    WIN32GUI_AVAILABLE = True
except ImportError:
    WIN32GUI_AVAILABLE = False

class ToolResult(BaseModel):
    """Structured result returned by every tool execution."""
    success: bool
    tool_name: str
    message: str
    data: Dict[str, Any] = Field(default_factory=dict)
    execution_time_ms: float = 0.0

class ToolDefinition(BaseModel):
    """Predictable schema defining an automation capability."""
    name: str
    description: str
    input_schema: Dict[str, Any]
    safety_classification: str = "safe"  # safe, confirmation_required, restricted
    requires_confirmation: bool = False
    verifiable: bool = True

class ToolRegistry:
    """Authoritative Tool Registry managing automation tool definitions, execution dispatch, and safety validation."""

    _instance: Optional['ToolRegistry'] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ToolRegistry, cls).__new__(cls)
            cls._instance.tools: Dict[str, ToolDefinition] = {}
            cls._instance.executors: Dict[str, Callable[..., ToolResult]] = {}
        return cls._instance

    def register(self, tool_def: ToolDefinition, executor: Callable[..., ToolResult]):
        """Registers a new automation tool and its execution handler."""
        self.tools[tool_def.name] = tool_def
        self.executors[tool_def.name] = executor

    def get_tool(self, name: str) -> Optional[ToolDefinition]:
        """Retrieves tool definition by name."""
        return self.tools.get(name)

    def list_tools(self) -> List[ToolDefinition]:
        """Returns list of registered tools."""
        return list(self.tools.values())

    def get_tool_prompt_descriptions(self) -> str:
        """Formats tool schemas into prompt context for LLM planner."""
        descriptions = []
        for name, tool in self.tools.items():
            descriptions.append(f"- **{name}**: {tool.description} | Schema: {json.dumps(tool.input_schema)}")
        return "\n".join(descriptions)

    def execute_tool(self, tool_name: str, arguments: Dict[str, Any]) -> ToolResult:
        """Executes targeted tool safely with execution timing and error handling."""
        start_t = time.time()
        executor = self.executors.get(tool_name)
        if not executor:
            return ToolResult(
                success=False,
                tool_name=tool_name,
                message=f"Tool '{tool_name}' is not registered.",
                data={},
                execution_time_ms=0.0
            )

        try:
            result = executor(**arguments)
            result.execution_time_ms = round((time.time() - start_t) * 1000, 2)
            return result
        except Exception as e:
            return ToolResult(
                success=False,
                tool_name=tool_name,
                message=f"Execution error in tool '{tool_name}': {str(e)}",
                data={},
                execution_time_ms=round((time.time() - start_t) * 1000, 2)
            )


def force_focus_spotify_window() -> bool:
    """Forces the Spotify Desktop window into OS foreground focus via win32gui."""
    if not WIN32GUI_AVAILABLE:
        return False
    try:
        hwnds = []
        def _enum_cb(hwnd, results):
            if win32gui.IsWindowVisible(hwnd):
                title = win32gui.GetWindowText(hwnd)
                if 'Spotify' in title:
                    results.append(hwnd)
        win32gui.EnumWindows(_enum_cb, hwnds)
        if hwnds:
            hwnd = hwnds[0]
            win32gui.ShowWindow(hwnd, 9)  # SW_RESTORE
            win32gui.SetForegroundWindow(hwnd)
            return True
    except Exception as e:
        print(f"[win32gui Focus Notice]: {e}")
    return False


def _normalize_for_match(text: str) -> set:
    """Extracts lowercase keyword set from a string for fuzzy matching."""
    stop_words = {"the", "a", "an", "of", "on", "in", "by", "and", "or", "to", "for", "with", "from"}
    words = set(text.lower().split())
    return words - stop_words


def _element_matches_query(element, query: str) -> bool:
    """Checks if a UI Automation element's Name or parent Name contains keywords from the query.
    Uses both keyword intersection AND substring matching for maximum flexibility."""
    query_lower = query.lower().strip()
    query_keywords = _normalize_for_match(query)
    if not query_keywords:
        return True  # No query to validate against

    def _text_matches(text: str) -> bool:
        """Returns True if text matches query via keyword intersection OR substring containment."""
        if not text:
            return False
        text_lower = text.lower()
        # Substring match: "Circles" in "Circles - Post Malone" or vice versa
        if query_lower in text_lower or text_lower in query_lower:
            return True
        # Keyword intersection match
        text_keywords = _normalize_for_match(text)
        if query_keywords & text_keywords:
            return True
        return False

    try:
        # Check the element's own Name
        el_name = element.Name or ""
        if _text_matches(el_name):
            return True

        # Check parent element's Name (e.g., Top Result card wrapping the Play button)
        try:
            parent = element.GetParentControl()
            if parent:
                if _text_matches(parent.Name or ""):
                    return True
                # Check grandparent for deeper nesting
                try:
                    grandparent = parent.GetParentControl()
                    if grandparent and _text_matches(grandparent.Name or ""):
                        return True
                except Exception:
                    pass
        except Exception:
            pass
    except Exception:
        pass

    return False


def click_spotify_top_result(query: str = "", delay_ms: int = 300) -> bool:
    """Locates the Spotify window and clicks the top search result Play button.
    
    If `query` is provided, validates that the target element's label matches
    the query before clicking to prevent stale-view race conditions.
    Polls up to 800ms for the UI tree to update if initial elements don't match.
    """
    try:
        import uiautomation as auto

        # Force-focus Spotify window before UI tree lookup
        force_focus_spotify_window()
        time.sleep(delay_ms / 1000.0)

        spotify_window = auto.WindowControl(ClassName="Chrome_WidgetWin_1", Name="Spotify")
        if not spotify_window.Exists(maxSearchSeconds=2):
            spotify_window = auto.WindowControl(SubName="Spotify")
            if not spotify_window.Exists(maxSearchSeconds=1):
                return False

        # Poll up to 800ms for UI tree to contain elements matching the query
        max_poll_attempts = 4 if query else 1
        poll_interval = 0.2  # 200ms between polls

        for attempt in range(max_poll_attempts):
            # 1. Target primary Play button inside the Top Result card
            try:
                play_button = spotify_window.ButtonControl(Name="Play", foundIndex=1)
                if play_button.Exists(maxSearchSeconds=0.5):
                    if not query or _element_matches_query(play_button, query):
                        play_button.Click()
                        print(f"[UI Automation]: Clicked Play button (attempt {attempt+1}, query-validated={bool(query)})")
                        return True
            except Exception as e:
                print(f"[UI Automation COM]: Play button lookup error: {e}")
            
            # 2. Target custom card container for Top Result
            try:
                top_result = spotify_window.CustomControl(Name="Top result", foundIndex=1)
                if top_result.Exists(maxSearchSeconds=0.5):
                    if not query or _element_matches_query(top_result, query):
                        top_result.Click()
                        print(f"[UI Automation]: Clicked Top Result card (attempt {attempt+1})")
                        return True
            except Exception as e:
                print(f"[UI Automation COM]: Top Result lookup error: {e}")

            # 3. Target any list item or data row containing track entries
            try:
                data_item = spotify_window.DataItemControl(foundIndex=1)
                if data_item.Exists(maxSearchSeconds=0.5):
                    if not query or _element_matches_query(data_item, query):
                        data_item.Click()
                        print(f"[UI Automation]: Clicked DataItem row (attempt {attempt+1})")
                        return True
            except Exception as e:
                print(f"[UI Automation COM]: DataItem lookup error: {e}")

            # 4. Fallback button search
            try:
                play_button_gen = spotify_window.ButtonControl(Name="Play")
                if play_button_gen.Exists(maxSearchSeconds=0.5):
                    if not query or _element_matches_query(play_button_gen, query):
                        play_button_gen.Click()
                        print(f"[UI Automation]: Clicked generic Play button (attempt {attempt+1})")
                        return True
            except Exception as e:
                print(f"[UI Automation COM]: Generic Play lookup error: {e}")

            # If query validation failed, wait for DOM to update before retrying
            if attempt < max_poll_attempts - 1:
                print(f"[UI Automation]: Stale DOM detected (attempt {attempt+1}), waiting {poll_interval}s for re-render...")
                time.sleep(poll_interval)

        print(f"[UI Automation]: All {max_poll_attempts} polling attempts exhausted, no matching element found for '{query}'.")
    except Exception as e:
        print(f"[UI Automation Notice: {e}]")

    return False


def queue_spotify_track() -> bool:
    """Locates the Spotify top search result and adds it to the playback queue via context menu."""
    try:
        import uiautomation as auto

        force_focus_spotify_window()
        time.sleep(0.3)

        spotify_window = auto.WindowControl(ClassName="Chrome_WidgetWin_1", Name="Spotify")
        if not spotify_window.Exists(maxSearchSeconds=2):
            spotify_window = auto.WindowControl(SubName="Spotify")
            if not spotify_window.Exists(maxSearchSeconds=1):
                return False

        # Find target element using same 4-tier fallback
        target = None
        play_button = spotify_window.ButtonControl(Name="Play", foundIndex=1)
        if play_button.Exists(maxSearchSeconds=1):
            target = play_button
        if not target:
            top_result = spotify_window.CustomControl(Name="Top result", foundIndex=1)
            if top_result.Exists(maxSearchSeconds=1):
                target = top_result
        if not target:
            data_item = spotify_window.DataItemControl(foundIndex=1)
            if data_item.Exists(maxSearchSeconds=1):
                target = data_item

        if not target:
            return False

        # Right-click to open context menu
        target.RightClick()
        time.sleep(0.5)

        # Find and click "Add to queue" menu item
        menu_item = auto.MenuItemControl(SubName="queue")
        if not menu_item.Exists(maxSearchSeconds=2):
            menu_item = auto.MenuItemControl(SubName="Queue")
        if menu_item.Exists(maxSearchSeconds=1):
            menu_item.Click()
            return True

        # Dismiss context menu if queue item not found
        import pyautogui
        pyautogui.press('escape')
    except Exception as e:
        print(f"[Queue UI Automation Notice: {e}]")

    return False
