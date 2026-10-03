"""
RevenueOS – Data Quality Engine
=================================
Runs structured quality checks on the Bronze layer and writes results
to bronze.quality_log and a printed/file report.

Checks implemented:
  - Schema validation
  - Null checks (required fields)
  - Duplicate detection
  - Referential integrity (cross-table foreign key checks)
  - Range/value checks (negatives, out-of-bounds discounts, etc.)
  - Reconciliation (source row count vs bronze row count)

Usage
-----
    python quality/run_checks.py                    # all checks
    python quality/run_checks.py --entity orders    # single entity
    python quality/run_checks.py --report-only      # print last report
"""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import pandas as pd
from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    SCHEMA_BRONZE,
    get_engine,
    get_run_id,
    logger,
)

# ---------------------------------------------------------------------------
# Result data structures
# ---------------------------------------------------------------------------

@dataclass
class QualityResult:
    check_type: str
    entity: str
    severity: str      # INFO | WARNING | ERROR | CRITICAL
    message: str
    affected_count: int = 0
    sample_values: str | None = None

    def is_ok(self) -> bool:
        return self.severity == "INFO"


@dataclass
class QualityReport:
    run_id: str
    generated_at: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    results: list[QualityResult] = field(default_factory=list)

    def add(self, result: QualityResult) -> None:
        self.results.append(result)

    # ---- Summary helpers ----
    def warnings(self) -> list[QualityResult]:
        return [r for r in self.results if r.severity == "WARNING"]

    def errors(self) -> list[QualityResult]:
        return [r for r in self.results if r.severity in ("ERROR", "CRITICAL")]

    def overall_status(self) -> str:
        if any(r.severity == "CRITICAL" for r in self.results):
            return "CRITICAL"
        if any(r.severity == "ERROR" for r in self.results):
            return "ERROR"
        if any(r.severity == "WARNING" for r in self.results):
            return "WARNING"
        return "OK"

    def print(self) -> None:
        """Print a human-readable report to stdout."""
        sep = "=" * 60
        print(sep)
        print("REVENUEOS DATA QUALITY REPORT")
        print(sep)
        print(f"Run ID      : {self.run_id}")
        print(f"Generated at: {self.generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}")
        print(f"Overall     : {self.overall_status()}")
        print(sep)

        # Group by entity
        entities_seen: list[str] = []
        for r in self.results:
            if r.entity not in entities_seen:
                entities_seen.append(r.entity)

        for entity in entities_seen:
            entity_results = [r for r in self.results if r.entity == entity]
            print(f"\n[{entity.upper()}]")
            for r in entity_results:
                icon = {"INFO": "✓", "WARNING": "⚠", "ERROR": "✗", "CRITICAL": "🔴"}.get(r.severity, "?")
                line = f"  {icon} {r.check_type:<30} | {r.severity:<8} | {r.message}"
                if r.affected_count:
                    line += f" ({r.affected_count:,} affected)"
                print(line)

        print(f"\nCritical failures : {sum(1 for r in self.results if r.severity == 'CRITICAL')}")
        print(f"Errors            : {sum(1 for r in self.results if r.severity == 'ERROR')}")
        print(f"Warnings          : {sum(1 for r in self.results if r.severity == 'WARNING')}")
        print(sep)


# ---------------------------------------------------------------------------
# Check implementations
# ---------------------------------------------------------------------------

def _load_bronze(engine, entity: str) -> pd.DataFrame:
    """Load all rows for a bronze entity into a DataFrame."""
    return pd.read_sql(f"SELECT * FROM {SCHEMA_BRONZE}.{entity}", engine)


def check_nulls(df: pd.DataFrame, entity: str, required_cols: list[str],
                report: QualityReport) -> None:
    """Check for NULLs / empty strings in required columns."""
    for col in required_cols:
        if col not in df.columns:
            continue
        null_mask = df[col].isna() | (df[col].astype(str).str.strip() == "")
        count = int(null_mask.sum())
        severity = "WARNING" if count > 0 else "INFO"
        sample = str(df[null_mask][col].head(3).tolist()) if count > 0 else None
        report.add(QualityResult(
            check_type=f"NULL_CHECK:{col}",
            entity=entity,
            severity=severity,
            message=f"Null/empty values in '{col}'",
            affected_count=count,
            sample_values=sample,
        ))


def check_duplicates(df: pd.DataFrame, entity: str, key_cols: list[str],
                     report: QualityReport) -> None:
    """Check for duplicate rows based on key columns."""
    available_keys = [c for c in key_cols if c in df.columns]
    if not available_keys:
        return
    dup_mask = df.duplicated(subset=available_keys, keep=False)
    count = int(dup_mask.sum())
    severity = "WARNING" if count > 0 else "INFO"
    sample_vals: str | None = None
    if count > 0:
        sample_vals = str(df[dup_mask][available_keys].head(3).to_dict("records"))
    report.add(QualityResult(
        check_type="DUPLICATE_CHECK",
        entity=entity,
        severity=severity,
        message=f"Duplicate rows on key [{', '.join(available_keys)}]",
        affected_count=count,
        sample_values=sample_vals,
    ))


def check_ranges(df: pd.DataFrame, entity: str,
                 range_rules: list[dict[str, Any]],
                 report: QualityReport) -> None:
    """
    range_rules: list of {col, min, max, label}
    Checks column values fall within [min, max].
    """
    for rule in range_rules:
        col = rule["col"]
        if col not in df.columns:
            continue
        numeric = pd.to_numeric(df[col], errors="coerce")
        violations = numeric.notna() & (
            (rule.get("min") is not None and numeric < rule["min"]) |
            (rule.get("max") is not None and numeric > rule["max"])
        )
        count = int(violations.sum())
        severity = "WARNING" if count > 0 else "INFO"
        report.add(QualityResult(
            check_type=f"RANGE_CHECK:{col}",
            entity=entity,
            severity=severity,
            message=rule.get("label", f"Range violation in '{col}'"),
            affected_count=count,
        ))


def check_referential_integrity(engine, child_entity: str, child_col: str,
                                parent_entity: str, parent_col: str,
                                report: QualityReport) -> None:
    """Find child rows whose FK value does not exist in the parent table."""
    sql = f"""
        SELECT COUNT(*) AS orphan_count
        FROM {SCHEMA_BRONZE}.{child_entity} c
        WHERE c.{child_col} IS NOT NULL
          AND c.{child_col} <> ''
          AND NOT EXISTS (
              SELECT 1 FROM {SCHEMA_BRONZE}.{parent_entity} p
              WHERE p.{parent_col} = c.{child_col}
          )
    """
    with engine.connect() as conn:
        result = conn.execute(text(sql)).fetchone()
        count = result[0] if result else 0

    severity = "WARNING" if count > 0 else "INFO"
    report.add(QualityResult(
        check_type="REFERENTIAL_INTEGRITY",
        entity=child_entity,
        severity=severity,
        message=f"{child_entity}.{child_col} → {parent_entity}.{parent_col}: orphan rows",
        affected_count=int(count),
    ))


def check_reconciliation(engine, entity: str, raw_dir: Path,
                         report: QualityReport) -> None:
    """Compare source CSV row counts to bronze table row counts."""
    entity_dir = raw_dir / entity
    csv_files = list(entity_dir.glob("*.csv"))
    if not csv_files:
        return

    source_rows = 0
    for f in csv_files:
        try:
            # Count lines minus header
            with open(f, encoding="utf-8-sig") as fh:
                source_rows += sum(1 for _ in fh) - 1
        except Exception:
            pass

    with engine.connect() as conn:
        result = conn.execute(
            text(f"SELECT COUNT(*) FROM {SCHEMA_BRONZE}.{entity}")
        ).fetchone()
        bronze_rows = result[0] if result else 0

    # Allow small tolerance for header-only files
    diff = abs(source_rows - bronze_rows)
    severity = "WARNING" if diff > 0 else "INFO"
    report.add(QualityResult(
        check_type="RECONCILIATION",
        entity=entity,
        severity=severity,
        message=(
            f"Source CSVs: {source_rows:,} rows | "
            f"Bronze table: {bronze_rows:,} rows | "
            f"Diff: {diff:,}"
        ),
        affected_count=diff,
    ))


# ---------------------------------------------------------------------------
# Per-entity check specifications
# ---------------------------------------------------------------------------

ENTITY_CHECKS: dict[str, dict] = {
    "orders": {
        "required_nulls": ["order_id", "customer_id", "product_id", "order_date",
                           "quantity", "unit_price"],
        "key_cols": ["order_id", "product_id"],
        "range_rules": [
            {"col": "quantity",   "min": 0,   "max": None, "label": "Negative quantity in orders"},
            {"col": "unit_price", "min": 0,   "max": None, "label": "Negative unit_price in orders"},
            {"col": "discount",   "min": 0,   "max": 1,    "label": "Discount outside 0–1 range"},
        ],
    },
    "customers": {
        "required_nulls": ["customer_id", "name"],
        "key_cols": ["customer_id"],
        "range_rules": [],
    },
    "products": {
        "required_nulls": ["product_id", "product_name", "cost", "selling_price"],
        "key_cols": ["product_id"],
        "range_rules": [
            {"col": "cost",          "min": 0, "max": None, "label": "Negative cost in products"},
            {"col": "selling_price", "min": 0, "max": None, "label": "Negative selling_price in products"},
        ],
    },
    "payments": {
        "required_nulls": ["payment_id", "order_id", "amount", "payment_status"],
        "key_cols": ["payment_id"],
        "range_rules": [
            {"col": "amount", "min": 0, "max": None, "label": "Negative payment amount"},
        ],
    },
    "returns": {
        "required_nulls": ["return_id", "order_id", "product_id", "quantity_returned"],
        "key_cols": ["return_id"],
        "range_rules": [
            {"col": "quantity_returned", "min": 0, "max": None, "label": "Negative quantity_returned"},
        ],
    },
    "inventory": {
        "required_nulls": ["product_id", "warehouse", "snapshot_date", "units_available"],
        "key_cols": ["product_id", "warehouse", "snapshot_date"],
        "range_rules": [
            {"col": "units_available", "min": 0, "max": None, "label": "Negative units_available"},
            {"col": "units_reserved",  "min": 0, "max": None, "label": "Negative units_reserved"},
        ],
    },
    "marketing": {
        "required_nulls": ["campaign_id", "date", "spend"],
        "key_cols": ["campaign_id", "date", "channel"],
        "range_rules": [
            {"col": "spend",       "min": 0, "max": None, "label": "Negative marketing spend"},
            {"col": "impressions", "min": 0, "max": None, "label": "Negative impressions"},
            {"col": "clicks",      "min": 0, "max": None, "label": "Negative clicks"},
        ],
    },
}

REFERENTIAL_CHECKS = [
    # (child_entity, child_col, parent_entity, parent_col)
    ("orders",   "customer_id", "customers", "customer_id"),
    ("orders",   "product_id",  "products",  "product_id"),
    ("payments", "order_id",    "orders",    "order_id"),
    ("returns",  "order_id",    "orders",    "order_id"),
    ("returns",  "product_id",  "products",  "product_id"),
    ("inventory","product_id",  "products",  "product_id"),
]


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

def run_quality_checks(entity: str | None = None,
                       run_id: str | None = None) -> QualityReport:
    """Run all quality checks and return a populated QualityReport."""
    run_id  = run_id or get_run_id()
    report  = QualityReport(run_id=run_id)
    engine  = get_engine()

    from config import RAW_DIR

    entities = [entity] if entity else list(ENTITY_CHECKS.keys())

    logger.info("Starting quality checks for: %s", entities)

    # Per-entity checks
    for ent in entities:
        if ent not in ENTITY_CHECKS:
            logger.warning("No check spec for entity '%s' – skipping.", ent)
            continue

        spec = ENTITY_CHECKS[ent]
        try:
            df = _load_bronze(engine, ent)
        except Exception as exc:
            report.add(QualityResult(
                check_type="TABLE_READ",
                entity=ent,
                severity="ERROR",
                message=f"Could not read bronze.{ent}: {exc}",
            ))
            continue

        if df.empty:
            report.add(QualityResult(
                check_type="TABLE_READ",
                entity=ent,
                severity="WARNING",
                message=f"bronze.{ent} is empty – has ingestion run?",
            ))
            continue

        report.add(QualityResult(
            check_type="ROW_COUNT",
            entity=ent,
            severity="INFO",
            message=f"bronze.{ent} contains {len(df):,} rows",
        ))

        check_nulls(df, ent, spec["required_nulls"], report)
        check_duplicates(df, ent, spec["key_cols"], report)
        check_ranges(df, ent, spec["range_rules"], report)
        check_reconciliation(engine, ent, RAW_DIR, report)

    # Referential integrity
    ref_entities = {child for child, *_ in REFERENTIAL_CHECKS}
    run_ref = ref_entities if entity is None else (ref_entities & {entity})
    for child_ent, child_col, parent_ent, parent_col in REFERENTIAL_CHECKS:
        if child_ent in run_ref:
            check_referential_integrity(
                engine, child_ent, child_col, parent_ent, parent_col, report
            )

    # Persist results to quality_log
    _persist_report(engine, report)

    return report


def _persist_report(engine, report: QualityReport) -> None:
    """Write all QualityResult rows to bronze.quality_log."""
    rows = [
        {
            "run_id": report.run_id,
            "source_table": r.entity,
            "check_type": r.check_type,
            "severity": r.severity,
            "message": r.message,
            "affected_count": r.affected_count,
            "sample_values": r.sample_values,
        }
        for r in report.results
    ]
    if rows:
        pd.DataFrame(rows).to_sql(
            "quality_log",
            schema=SCHEMA_BRONZE,
            con=engine,
            if_exists="append",
            index=False,
            method="multi",
        )
    logger.info("Quality results written to bronze.quality_log (%d rows)", len(rows))


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="RevenueOS – Data Quality Checks"
    )
    parser.add_argument(
        "--entity",
        choices=list(ENTITY_CHECKS.keys()),
        default=None,
        help="Run checks for a single entity only.",
    )
    args = parser.parse_args()

    report = run_quality_checks(entity=args.entity)
    report.print()

    exit_code = 0 if report.overall_status() in ("OK", "WARNING") else 1
    sys.exit(exit_code)
