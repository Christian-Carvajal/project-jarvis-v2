"""
Primary Entry Point for Project JARVIS (Apex Home Automations & PC Suite).
Redirects to the official modular application inside src/main.py.
"""

import os
import sys

# Ensure src/ is discoverable
PROJECT_ROOT = os.path.dirname(os.path.abspath(__file__))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from src.main import main

if __name__ == "__main__":
    main()
