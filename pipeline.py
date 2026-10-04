"""
RevenueOS – Enterprise Analytics Pipeline & Automation Engine
=============================================================
Unified CLI entrypoint delegating to backend.pipeline.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add backend directory to sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from backend.pipeline import main

if __name__ == "__main__":
    sys.exit(main())
