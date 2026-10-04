"""
RevenueOS – Universal Excel to Power BI Pipeline Engine (Deprecated Shim)
========================================================================
This module is retained for backward compatibility with existing tests and scripts.
Please import and use `backend.engine.core.CoreEngine` directly.
"""

from __future__ import annotations

import sys
import warnings
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

warnings.warn(
    "excel_to_powerbi.py is deprecated and will be consolidated in a future release. "
    "Please import from backend.engine.core instead.",
    DeprecationWarning,
    stacklevel=2,
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
