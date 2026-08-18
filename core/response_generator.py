import re

class ResponseSanitizer:
    """Sanitizes technical logs, exception traces, and verification failure strings into polite, natural language responses."""

    @classmethod
    def sanitize(cls, text: str, query: str = "") -> str:
        if not text:
            return ""

        raw = text.strip()

        # Check if text contains raw verification failure string
        if "[VERIFICATION] FAILED:" in raw or "OS Media mismatch:" in raw:
            title_query = query.title().strip() if query else "the track"
            return f"I searched for '{title_query}' on Spotify, but the player couldn't start the new track."

        # Strip technical prefix tags like [VERIFICATION], [FAIL], [ERROR]
        clean = re.sub(r'\[(?:VERIFICATION|FAIL|ERROR|WARNING)\]\s*', '', raw)
        clean = re.sub(r'FAILED:\s*', '', clean)
        clean = clean.strip()

        return clean if clean else raw
