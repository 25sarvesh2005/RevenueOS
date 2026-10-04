"""
RevenueOS – Master Backend Engine CLI Wrapper
=============================================
Delegates to the canonical RevenueOS CoreEngine (backend/engine/core.py).
Maintains full backward compatibility for Electron IPC and CLI workflows.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Add backend directory to sys.path if not present
BACKEND_DIR = Path(__file__).resolve().parent.parent
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

try:
    from engine.core import (
        CoreEngine,
        BackendEngine,
        ExcelToPowerBIEngine,
        ColumnMeta,
        TableMeta,
        RelationshipMeta,
        DaxMeasureMeta,
        clean_identifier,
        format_title,
        main,
    )
except ImportError:
    from backend.engine.core import (
        CoreEngine,
        BackendEngine,
        ExcelToPowerBIEngine,
        ColumnMeta,
        TableMeta,
        RelationshipMeta,
        DaxMeasureMeta,
        clean_identifier,
        format_title,
        main,
    )

__all__ = [
    "CoreEngine",
    "BackendEngine",
    "ExcelToPowerBIEngine",
    "ColumnMeta",
    "TableMeta",
    "RelationshipMeta",
    "DaxMeasureMeta",
    "clean_identifier",
    "format_title",
    "main",
]

if __name__ == "__main__":
    main()
