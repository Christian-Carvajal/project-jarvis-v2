import os
import sys
import re
from typing import Union, List

class SecurityEngine:
    """Centralized Security Engine validating shell commands, execution targets, and file paths to prevent destructive OS operations."""

    BLOCKED_DIRS = [
        "system32",
        "syswow64",
        "c:\\windows",
        "c:/windows",
        "/etc",
        "/usr",
        "/var"
    ]

    DESTRUCTIVE_PATTERNS = [
        r"\bdel\b",
        r"\brmdir\b",
        r"\bremove\b",
        r"\bunlink\b",
        r"\berase\b",
        r"\bformat\b",
        r"\bos\.remove\b",
        r"\bshutil\.rmtree\b",
        r"\bremove-item\b",
        r"\bclear-disk\b",
        r"\bdiskpart\b",
        r"\bdrop\b"
    ]

    @classmethod
    def canonicalize_path(cls, path_str: str) -> str:
        """Resolves environment variables and absolute paths for strict inspection."""
        try:
            expanded = os.path.expandvars(os.path.expanduser(path_str))
            return os.path.normpath(os.path.abspath(expanded)).lower()
        except Exception:
            return path_str.lower().strip()

    @classmethod
    def is_safe_target(cls, target: str) -> bool:
        """Validates shell targets, paths, and commands against safety policies."""
        if not target or not isinstance(target, str):
            return False

        clean_target = target.lower().strip()
        canonical = cls.canonicalize_path(clean_target)

        # 1. Block access to protected system directories
        for sys_dir in cls.BLOCKED_DIRS:
            if sys_dir in clean_target or sys_dir in canonical:
                print(f"[SecurityEngine Blocked]: Protected directory match in target '{target}'")
                return False

        # 2. Block destructive command patterns
        for pattern in cls.DESTRUCTIVE_PATTERNS:
            if re.search(pattern, clean_target, flags=re.IGNORECASE):
                print(f"[SecurityEngine Blocked]: Destructive pattern match '{pattern}' in target '{target}'")
                return False

        return True
