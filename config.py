"""
RevenueOS – Shared configuration and database utilities.
Re-exports canonical configuration from backend.config to guarantee single source of truth.
"""

from __future__ import annotations

import sys
from pathlib import Path

# Ensure backend package is discoverable
BACKEND_DIR = Path(__file__).resolve().parent / "backend"
if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from backend.config import (  # noqa: F401
    REVENUEOS_ENV,
    REVENUEOS_API_KEY,
    DEFAULT_CURRENCY,
    LOG_LEVEL,
    logger,
    get_run_id,
    get_engine,
    SCHEMA_BRONZE,
    SCHEMA_SILVER,
    SCHEMA_GOLD,
    ROOT_DIR,
    DATA_DIR,
    RAW_DIR,
    PROCESSED_DIR,
    BRONZE_DIR,
    SILVER_DIR,
    GOLD_DIR,
    DISCOUNT_LEAKAGE_THRESHOLD,
    MARGIN_LEAKAGE_THRESHOLD,
    HIGH_RETURN_RATE_THRESHOLD,
    IQR_MULTIPLIER,
    ZSCORE_THRESHOLD,
    ISO_FOREST_CONTAMINATION,
)
