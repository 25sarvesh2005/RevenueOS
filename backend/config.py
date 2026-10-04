"""
RevenueOS – Shared configuration and database utilities.
All modules import from here to avoid duplicating connection logic.
"""

from __future__ import annotations

import os
import logging
import uuid
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv
from sqlalchemy import create_engine, text
from sqlalchemy.engine import Engine

# ---------------------------------------------------------------------------
# Load .env (Checks Workspace Root and Backend directory)
# ---------------------------------------------------------------------------
root_env = Path(__file__).resolve().parent.parent / ".env"
backend_env = Path(__file__).resolve().parent / ".env"
if root_env.exists():
    load_dotenv(root_env)
elif backend_env.exists():
    load_dotenv(backend_env)
else:
    load_dotenv()

# Environment mode & security
REVENUEOS_ENV = os.getenv("REVENUEOS_ENV", "development").lower()
REVENUEOS_API_KEY = os.getenv("REVENUEOS_API_KEY", "")
DEFAULT_CURRENCY = os.getenv("DEFAULT_CURRENCY", "$")

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    level=getattr(logging, LOG_LEVEL, logging.INFO),
    format="%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("revenueos")


# ---------------------------------------------------------------------------
# Run ID
# ---------------------------------------------------------------------------
def get_run_id() -> str:
    """Return a unique run identifier for this pipeline execution."""
    cfg = os.getenv("PIPELINE_RUN_ID", "auto")
    if cfg == "auto":
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d-%H%M%S")
        return f"{ts}-{uuid.uuid4().hex[:6]}"
    return cfg


# ---------------------------------------------------------------------------
# Database engine
# ---------------------------------------------------------------------------
def get_engine(schema: str | None = None) -> Engine:
    """Create a SQLAlchemy engine from environment variables.

    Args:
        schema: If provided, sets the default search_path for the connection.
    """
    host = os.getenv("DB_HOST", "localhost")
    port = os.getenv("DB_PORT", "5432")
    db   = os.getenv("DB_NAME", "revenueos")
    user = os.getenv("DB_USER", "revenueos")
    pwd  = os.getenv("DB_PASSWORD", "revenueos")

    url = f"postgresql+psycopg://{user}:{pwd}@{host}:{port}/{db}"

    connect_args: dict = {}
    if schema:
        connect_args["options"] = f"-csearch_path={schema}"

    engine = create_engine(url, connect_args=connect_args, pool_pre_ping=True)
    return engine


# ---------------------------------------------------------------------------
# Schema helpers
# ---------------------------------------------------------------------------
SCHEMA_BRONZE = os.getenv("SCHEMA_BRONZE", "bronze")
SCHEMA_SILVER = os.getenv("SCHEMA_SILVER", "silver")
SCHEMA_GOLD   = os.getenv("SCHEMA_GOLD",   "gold")

# Source data paths
ROOT_DIR      = Path(__file__).parent
DATA_DIR      = ROOT_DIR / "data"
RAW_DIR       = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
BRONZE_DIR    = PROCESSED_DIR / "bronze"
SILVER_DIR    = PROCESSED_DIR / "silver"
GOLD_DIR      = PROCESSED_DIR / "gold"

# Leakage / anomaly thresholds from environment
DISCOUNT_LEAKAGE_THRESHOLD  = float(os.getenv("DISCOUNT_LEAKAGE_THRESHOLD",  "0.25"))
MARGIN_LEAKAGE_THRESHOLD    = float(os.getenv("MARGIN_LEAKAGE_THRESHOLD",    "0.15"))
HIGH_RETURN_RATE_THRESHOLD  = float(os.getenv("HIGH_RETURN_RATE_THRESHOLD",  "0.15"))
IQR_MULTIPLIER              = float(os.getenv("IQR_MULTIPLIER",              "1.5"))
ZSCORE_THRESHOLD            = float(os.getenv("ZSCORE_THRESHOLD",            "3.0"))
ISO_FOREST_CONTAMINATION    = float(os.getenv("ISOLATION_FOREST_CONTAMINATION", "0.05"))
