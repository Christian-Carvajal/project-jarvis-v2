import os
import sys
import time
import urllib.parse
import webbrowser
from typing import Tuple, Optional, Dict, Any

try:
    from playwright.sync_api import sync_playwright
    HAS_PLAYWRIGHT = True
except ImportError:
    HAS_PLAYWRIGHT = False

try:
    import pyautogui
    import pyperclip
    pyautogui.FAILSAFE = False
    HAS_PYAUTOGUI = True
except ImportError:
    HAS_PYAUTOGUI = False

from core.app_resolver import AppResolver

class BrowserAutomationService:
    """Dedicated Browser Automation Layer supporting DOM selectors, YouTube video selection, web search, and title verification."""

    def __init__(self):
        self.app_resolver = AppResolver()
        self.active_browser_type = "brave" if self.app_resolver.resolve_app_path("brave") else "chrome"

    def open_url(self, url: str) -> Tuple[bool, str]:
        """Opens URL in system default browser or active browser process."""
        try:
            webbrowser.open_new(url)
            time.sleep(1.0)
            self.app_resolver.focus_window("brave") or self.app_resolver.focus_window("chrome") or self.app_resolver.focus_window("edge")
            return True, f"Navigated to {url}."
        except Exception as e:
            return False, f"Failed to open URL: {str(e)}"

    def search_web(self, query: str) -> Tuple[bool, str, Dict[str, Any]]:
        """Searches Google for sanitized target query."""
        clean_q = query.strip()
        encoded = urllib.parse.quote(clean_q)
        target_url = f"https://www.google.com/search?q={encoded}"

        success, msg = self.open_url(target_url)
        return success, f"Searched Google for '{clean_q}'.", {"query": clean_q, "url": target_url}

    def search_youtube(self, query: str, auto_play: bool = True, result_index: int = 1) -> Tuple[bool, str, Dict[str, Any]]:
        """Searches YouTube for exact query using Playwright DOM selectors or browser keyboard navigation, selecting the specified video result index."""
        clean_q = query.strip()
        encoded = urllib.parse.quote(clean_q)
        target_url = f"https://www.youtube.com/results?search_query={encoded}"

        # 1. Attempt Playwright deterministic DOM automation if available
        if HAS_PLAYWRIGHT:
            try:
                with sync_playwright() as p:
                    # Launch persistent or headful browser instance
                    browser = p.chromium.launch(headless=False)
                    page = browser.new_page()
                    page.goto(target_url)
                    page.wait_for_selector("ytd-video-renderer", timeout=5000)

                    # Query all video renderer elements
                    video_elements = page.query_selector_all("ytd-video-renderer a#video-title")
                    if video_elements and len(video_elements) >= result_index:
                        target_elem = video_elements[result_index - 1]
                        raw_title = target_elem.inner_text() or clean_q
                        video_title = raw_title.encode("ascii", "ignore").decode("ascii").strip() or clean_q

                        if auto_play:
                            target_elem.click()
                            page.wait_for_timeout(2000)

                        current_url = page.url
                        browser.close()
                        return True, f"Playing '{video_title}' on YouTube.", {"title": video_title, "url": current_url, "index": result_index}
            except Exception as pe:
                clean_err = str(pe).encode("ascii", "ignore").decode("ascii")
                print(f"[Browser Automation Notice: Playwright engine fallback ({clean_err})]")

        # 2. Fallback: Native Browser Launch & Key-Nav Target Selection
        self.open_url(target_url)

        if HAS_PYAUTOGUI:
            time.sleep(2.5)
            self.app_resolver.focus_window("brave") or self.app_resolver.focus_window("chrome") or self.app_resolver.focus_window("edge")

            # Reset focus to page body
            pyautogui.press('escape')
            time.sleep(0.2)

            # Tab to top video result
            for _ in range(result_index):
                pyautogui.press('tab')
                time.sleep(0.1)

            if auto_play:
                pyautogui.press('enter')

        return True, f"Selected result #{result_index} for '{clean_q}' on YouTube.", {"query": clean_q, "index": result_index}

