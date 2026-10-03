"""
RevenueOS – Bronze Ingestion Layer
===================================
Loads CSV files from data/raw/<entity>/ into the corresponding
bronze.<entity> table in PostgreSQL.

Usage
-----
    python ingestion/ingest_bronze.py                    # all entities
    python ingestion/ingest_bronze.py --entity orders    # single entity

The ingestion is *additive* (append-only) by default.
Use --truncate to clear the target table before loading (for reruns).
"""

from __future__ import annotations

import argparse
import csv
import logging
import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
from sqlalchemy import text

# Make root importable when running the script directly
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    SCHEMA_BRONZE,
    RAW_DIR,
    get_engine,
    get_run_id,
    logger,
)

# ---------------------------------------------------------------------------
# Entity definitions
# Each entry maps an entity name to:
#   - raw subdirectory under data/raw/
#   - target bronze table name
#   - expected columns (used to catch schema drift early)
# ---------------------------------------------------------------------------
ENTITIES: dict[str, dict] = {
    "orders": {
        "raw_subdir": "orders",
        "table": f"{SCHEMA_BRONZE}.orders",
        "expected_columns": {
            "order_id", "customer_id", "product_id", "order_date",
            "quantity", "unit_price", "discount", "channel",
        },
    },
    "customers": {
        "raw_subdir": "customers",
        "table": f"{SCHEMA_BRONZE}.customers",
        "expected_columns": {
            "customer_id", "name", "email", "city", "region",
            "signup_date", "segment",
        },
    },
    "products": {
        "raw_subdir": "products",
        "table": f"{SCHEMA_BRONZE}.products",
        "expected_columns": {
            "product_id", "product_name", "category", "subcategory",
            "supplier", "cost", "selling_price",
        },
    },
    "payments": {
        "raw_subdir": "payments",
        "table": f"{SCHEMA_BRONZE}.payments",
        "expected_columns": {
            "payment_id", "order_id", "payment_date", "payment_method",
            "amount", "payment_status",
        },
    },
    "returns": {
        "raw_subdir": "returns",
        "table": f"{SCHEMA_BRONZE}.returns",
        "expected_columns": {
            "return_id", "order_id", "product_id", "return_date",
            "quantity_returned", "return_reason",
        },
    },
    "inventory": {
        "raw_subdir": "inventory",
        "table": f"{SCHEMA_BRONZE}.inventory",
        "expected_columns": {
            "product_id", "warehouse", "snapshot_date",
            "units_available", "units_reserved", "units_sold",
        },
    },
    "marketing": {
        "raw_subdir": "marketing",
        "table": f"{SCHEMA_BRONZE}.marketing",
        "expected_columns": {
            "campaign_id", "date", "channel", "spend", "impressions",
            "clicks", "orders_attributed", "revenue_attributed",
        },
    },
}


# ---------------------------------------------------------------------------
# Core ingestion logic
# ---------------------------------------------------------------------------

def _log_quality(engine, run_id: str, source_table: str, check_type: str,
                 severity: str, message: str, affected: int = 0,
                 sample: str | None = None) -> None:
    """Insert a record into bronze.quality_log."""
    sql = text("""
        INSERT INTO bronze.quality_log
            (run_id, source_table, check_type, severity, message,
             affected_count, sample_values)
        VALUES
            (:run_id, :source_table, :check_type, :severity, :message,
             :affected, :sample)
    """)
    with engine.begin() as conn:
        conn.execute(sql, {
            "run_id": run_id, "source_table": source_table,
            "check_type": check_type, "severity": severity,
            "message": message, "affected": affected, "sample": sample,
        })


def _check_schema(df: pd.DataFrame, expected: set[str], entity: str,
                  filepath: Path, engine, run_id: str) -> None:
    """Warn if source columns are missing or unexpected."""
    actual = set(df.columns.str.lower())
    missing = expected - actual
    unexpected = actual - expected - {"location", "status", "failure_reason",
                                       "return_reason"}  # known optional cols

    if missing:
        msg = f"Missing expected columns in {filepath.name}: {sorted(missing)}"
        logger.warning(msg)
        _log_quality(engine, run_id, entity, "SCHEMA_CHECK", "WARNING", msg,
                     affected=len(missing))

    if unexpected:
        msg = f"Unexpected columns in {filepath.name}: {sorted(unexpected)}"
        logger.info(msg)
        _log_quality(engine, run_id, entity, "SCHEMA_CHECK", "INFO", msg,
                     affected=len(unexpected))


def ingest_entity(entity: str, truncate: bool = False,
                  run_id: str | None = None) -> int:
    """
    Ingest all CSV files for a given entity into the bronze layer.

    Returns
    -------
    int
        Total number of rows loaded.
    """
    if entity not in ENTITIES:
        raise ValueError(f"Unknown entity '{entity}'. Choose from: {list(ENTITIES)}")

    cfg = ENTITIES[entity]
    raw_dir = RAW_DIR / cfg["raw_subdir"]
    table   = cfg["table"]
    run_id  = run_id or get_run_id()

    csv_files = sorted(raw_dir.glob("*.csv"))
    if not csv_files:
        logger.warning("No CSV files found in %s – skipping.", raw_dir)
        return 0

    engine = get_engine()

    if truncate:
        with engine.begin() as conn:
            conn.execute(text(f"TRUNCATE TABLE {table}"))
        logger.info("Truncated %s", table)

    total_rows = 0
    ingestion_ts = datetime.now(timezone.utc).isoformat()

    for filepath in csv_files:
        logger.info("Ingesting %s → %s", filepath.name, table)

        try:
            df = pd.read_csv(filepath, dtype=str, keep_default_na=False)
        except Exception as exc:
            msg = f"Failed to read {filepath.name}: {exc}"
            logger.error(msg)
            _log_quality(engine, run_id, entity, "FILE_READ", "ERROR", msg)
            continue

        # Normalize column names
        df.columns = df.columns.str.strip().str.lower().str.replace(" ", "_")

        # Schema drift check
        _check_schema(df, cfg["expected_columns"], entity, filepath, engine, run_id)

        # Add pipeline metadata
        df["run_id"]              = run_id
        df["source_file"]         = filepath.name
        df["ingestion_timestamp"] = ingestion_ts
        df["_raw_row"]            = range(1, len(df) + 1)

        # Remove columns that don't exist in the bronze table
        # (bronze tables accept all expected + optional + metadata cols)
        with engine.begin() as conn:
            df.to_sql(
                name=table.split(".")[-1],
                schema=SCHEMA_BRONZE,
                con=conn,
                if_exists="append",
                index=False,
                method="multi",
                chunksize=5000,
            )

        logger.info("  Loaded %d rows from %s", len(df), filepath.name)

        _log_quality(
            engine, run_id, entity, "INGESTION", "INFO",
            f"Loaded {len(df)} rows from {filepath.name}",
            affected=len(df),
        )
        total_rows += len(df)

    logger.info("Entity '%s' — total rows ingested: %d", entity, total_rows)
    return total_rows


def ingest_all(truncate: bool = False) -> dict[str, int]:
    """Ingest all entities. Returns dict {entity: row_count}."""
    run_id = get_run_id()
    logger.info("=" * 60)
    logger.info("RevenueOS Bronze Ingestion — Run ID: %s", run_id)
    logger.info("=" * 60)

    results: dict[str, int] = {}
    for entity in ENTITIES:
        try:
            results[entity] = ingest_entity(entity, truncate=truncate, run_id=run_id)
        except Exception as exc:
            logger.error("Failed to ingest '%s': %s", entity, exc)
            results[entity] = -1

    logger.info("=" * 60)
    logger.info("Ingestion summary:")
    for entity, count in results.items():
        status = f"{count:,} rows" if count >= 0 else "FAILED"
        logger.info("  %-15s %s", entity, status)
    logger.info("=" * 60)
    return results


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="RevenueOS – Bronze Layer Ingestion"
    )
    parser.add_argument(
        "--entity",
        choices=list(ENTITIES.keys()),
        default=None,
        help="Ingest a single entity. Omit to ingest all.",
    )
    parser.add_argument(
        "--truncate",
        action="store_true",
        help="Truncate the target table before loading (idempotent reruns).",
    )
    args = parser.parse_args()

    if args.entity:
        ingest_entity(args.entity, truncate=args.truncate)
    else:
        ingest_all(truncate=args.truncate)
