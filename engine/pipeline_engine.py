"""
RevenueOS – Enterprise Automation Pipeline Engine
==================================================
Production-grade orchestration, continuous file watching, daemon scheduling,
automated artifact publishing, audit logging, and system health diagnostics.

Execution Modes:
  1. Single Run:    Executes requested phases in sequence.
  2. Watch Mode:    Continuously monitors data/raw/ for newly dropped/modified files.
  3. Daemon Mode:   Scheduled background runner firing on recurring intervals.
  4. Health Check:  Pre-flight system, database, and staging verification.
  5. Export Mode:   Exports Gold analytical marts to processed storage and updates Power BI assets.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import signal
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import pandas as pd
from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    DATA_DIR,
    PROCESSED_DIR,
    RAW_DIR,
    ROOT_DIR,
    SCHEMA_BRONZE,
    SCHEMA_GOLD,
    SCHEMA_SILVER,
    get_engine,
    get_run_id,
    logger,
)


@dataclass
class PhaseResult:
    name: str
    status: str  # SUCCESS | FAILED | SKIPPED
    duration_seconds: float
    error_message: str | None = None
    records_affected: int = 0


@dataclass
class PipelineRunResult:
    run_id: str
    trigger_type: str
    started_at: str
    completed_at: str | None = None
    duration_seconds: float = 0.0
    status: str = "RUNNING"  # SUCCESS | FAILED | CRITICAL_QUALITY_FAILURE
    phase: str = "all"
    phases: list[PhaseResult] = field(default_factory=list)
    records_processed: int = 0
    metrics_summary: dict[str, Any] = field(default_factory=dict)
    error_message: str | None = None


class PipelineEngine:
    """Enterprise-grade orchestrator and automation engine for RevenueOS."""

    RUNS_LOG_PATH = DATA_DIR / "pipeline_runs.json"

    def __init__(self, engine=None):
        self._db_engine = engine

    def get_db(self):
        if self._db_engine is None:
            self._db_engine = get_engine()
        return self._db_engine

    # -----------------------------------------------------------------------
    # Core Pipeline Execution
    # -----------------------------------------------------------------------
    def execute(
        self,
        phase: str = "all",
        truncate: bool = False,
        excel_path: str | Path | None = None,
        trigger_type: str = "MANUAL",
        auto_export: bool = True,
    ) -> PipelineRunResult:
        """Executes pipeline phases and persists execution metadata."""
        run_id = get_run_id()
        started_utc = datetime.now(timezone.utc)
        result = PipelineRunResult(
            run_id=run_id,
            trigger_type=trigger_type,
            started_at=started_utc.isoformat(),
            phase=phase,
        )

        logger.info("=" * 65)
        logger.info("REVENUEOS ENTERPRISE AUTOMATION ENGINE")
        logger.info("Run ID       : %s", run_id)
        logger.info("Trigger Type : %s", trigger_type)
        logger.info("Phase Scope  : %s", phase)
        logger.info("Truncate     : %s", truncate)
        logger.info("Started UTC  : %s", started_utc.strftime("%Y-%m-%d %H:%M:%S"))
        logger.info("=" * 65)

        self._record_run_start(result)

        try:
            # ---------------------------------------------------------------
            # Phase 0: Excel Ingestion / Preprocessing
            # ---------------------------------------------------------------
            if phase in ("excel", "all"):
                from ingestion.import_excel import import_excel_paths
                src = [Path(excel_path)] if excel_path else [RAW_DIR / "excel"]
                p_res = self._run_phase_safe(
                    "Excel Preprocessing",
                    import_excel_paths,
                    src,
                    out_dir=RAW_DIR,
                    overwrite=True,
                )
                result.phases.append(p_res)

            # ---------------------------------------------------------------
            # Phase 1: Bronze Landing Layer
            # ---------------------------------------------------------------
            if phase in ("bronze", "all"):
                from ingestion.ingest_bronze import ingest_all
                p_res = self._run_phase_safe(
                    "Bronze Ingestion",
                    ingest_all,
                    truncate=truncate,
                )
                result.phases.append(p_res)

            # ---------------------------------------------------------------
            # Phase 2: Data Quality Gatekeeper
            # ---------------------------------------------------------------
            if phase in ("quality", "all"):
                from quality.run_checks import run_quality_checks
                t0 = time.time()
                report = run_quality_checks(run_id=run_id)
                dur = time.time() - t0
                if report:
                    report.print()
                    status = report.overall_status()
                    result.metrics_summary["quality_status"] = status
                    result.metrics_summary["quality_summary"] = {
                        "info": report.info_count(),
                        "warning": report.warning_count(),
                        "error": report.error_count(),
                        "critical": report.critical_count(),
                    }
                    if status == "CRITICAL":
                        err = "Pipeline halted: CRITICAL data quality violations detected."
                        logger.error(err)
                        result.phases.append(
                            PhaseResult("Data Quality Gate", "FAILED", dur, error_message=err)
                        )
                        result.status = "CRITICAL_QUALITY_FAILURE"
                        result.error_message = err
                        self._record_run_end(result)
                        return result

                result.phases.append(PhaseResult("Data Quality Gate", "SUCCESS", dur))

            # ---------------------------------------------------------------
            # Phase 3: Silver Transformation
            # ---------------------------------------------------------------
            if phase in ("silver", "all"):
                from transformation.transform_silver import transform_all
                p_res = self._run_phase_safe(
                    "Silver Transformation",
                    transform_all,
                    truncate=truncate,
                )
                result.phases.append(p_res)

            # ---------------------------------------------------------------
            # Phase 4: Gold Star Schema & Marts
            # ---------------------------------------------------------------
            if phase in ("gold", "all"):
                from transformation.build_gold import build_gold
                p_res = self._run_phase_safe("Gold Star Schema", build_gold)
                result.phases.append(p_res)

            # ---------------------------------------------------------------
            # Phase 5: Statistical & ML Anomaly Engine
            # ---------------------------------------------------------------
            if phase in ("anomalies", "all"):
                def _run_anomalies():
                    from python.anomaly_detection.detector import run_anomaly_pipeline
                    db = self.get_db()
                    orders_df = pd.read_sql(f"SELECT * FROM {SCHEMA_SILVER}.orders", db)
                    products_df = pd.read_sql(f"SELECT * FROM {SCHEMA_SILVER}.products", db)
                    return run_anomaly_pipeline(orders_df=orders_df, products_df=products_df)

                p_res = self._run_phase_safe("Anomaly Detection", _run_anomalies)
                result.phases.append(p_res)

            # ---------------------------------------------------------------
            # Phase 6: Revenue Forecasting
            # ---------------------------------------------------------------
            if phase in ("forecast", "all"):
                def _run_forecast():
                    from python.forecasting.forecast_engine import generate_revenue_forecast
                    db = self.get_db()
                    daily_df = pd.read_sql(f"SELECT * FROM {SCHEMA_GOLD}.gold_daily_financials", db)
                    if not daily_df.empty:
                        return generate_revenue_forecast(daily_financials_df=daily_df, horizon_days=30)
                    return None

                p_res = self._run_phase_safe("Revenue Forecasting", _run_forecast)
                result.phases.append(p_res)

            # ---------------------------------------------------------------
            # Phase 7: Executive Briefing Report
            # ---------------------------------------------------------------
            if phase in ("report", "all"):
                def _run_report():
                    from python.reporting.executive_report import (
                        fetch_gold_summary,
                        generate_executive_briefing,
                    )
                    db = self.get_db()
                    summary = fetch_gold_summary(db)
                    briefing_md = generate_executive_briefing(summary)
                    out_path = ROOT_DIR / "docs" / "executive_briefing.md"
                    out_path.parent.mkdir(parents=True, exist_ok=True)
                    out_path.write_text(briefing_md, encoding="utf-8")
                    logger.info("Saved executive decision report to %s", out_path)
                    return str(out_path)

                p_res = self._run_phase_safe("Executive Briefing", _run_report)
                result.phases.append(p_res)

            # ---------------------------------------------------------------
            # Phase 8: Automated Artifact Publishing & Power BI Sync
            # ---------------------------------------------------------------
            if auto_export and phase in ("gold", "all"):
                p_res = self._run_phase_safe("Artifact Publishing", self.export_artifacts)
                result.phases.append(p_res)

            result.status = "SUCCESS"

        except Exception as exc:
            logger.error("Pipeline run failed with unhandled exception: %s", exc, exc_info=True)
            result.status = "FAILED"
            result.error_message = str(exc)
        finally:
            ended_utc = datetime.now(timezone.utc)
            result.completed_at = ended_utc.isoformat()
            result.duration_seconds = round((ended_utc - started_utc).total_seconds(), 2)
            self._record_run_end(result)

        logger.info("=" * 65)
        logger.info("PIPELINE COMPLETED [%s] in %.2fs", result.status, result.duration_seconds)
        logger.info("=" * 65)
        return result

    def _run_phase_safe(self, name: str, fn: Callable, *args, **kwargs) -> PhaseResult:
        logger.info("\n" + "-" * 60)
        logger.info("-> PHASE: %s", name.upper())
        logger.info("-" * 60)
        t0 = time.time()
        try:
            res = fn(*args, **kwargs)
            elapsed = round(time.time() - t0, 2)
            logger.info("[OK] %s completed in %.2fs", name, elapsed)
            records = len(res) if isinstance(res, (list, pd.DataFrame)) else 0
            return PhaseResult(name=name, status="SUCCESS", duration_seconds=elapsed, records_affected=records)
        except Exception as exc:
            elapsed = round(time.time() - t0, 2)
            logger.error("[FAIL] %s FAILED in %.2fs: %s", name, elapsed, exc)
            raise

    # -----------------------------------------------------------------------
    # Continuous File Watcher Engine
    # -----------------------------------------------------------------------
    def start_watcher(self, debounce_seconds: float = 3.0, poll_interval: float = 1.0) -> None:
        """Continuously watches raw staging folders and triggers automated pipeline execution."""
        logger.info("Starting RevenueOS Automated File Watcher...")
        logger.info("Watching directory: %s", RAW_DIR.resolve())
        logger.info("Press Ctrl+C to stop.")

        snapshot = self._scan_raw_files()
        logger.info("Initial baseline scanned: %d files monitored.", len(snapshot))

        last_trigger_time = 0.0
        pending_changes = False

        def _sig_handler(sig, frame):
            logger.info("\nStopping file watcher gracefully...")
            sys.exit(0)

        signal.signal(signal.SIGINT, _sig_handler)

        while True:
            try:
                time.sleep(poll_interval)
                current = self._scan_raw_files()
                added_or_modified = {
                    p: h for p, h in current.items() if p not in snapshot or snapshot[p] != h
                }

                if added_or_modified:
                    logger.info("Detected changes in %d file(s):", len(added_or_modified))
                    for f in added_or_modified.keys():
                        logger.info("  -> %s", Path(f).name)
                    pending_changes = True
                    last_trigger_time = time.time()
                    snapshot = current

                if pending_changes and (time.time() - last_trigger_time >= debounce_seconds):
                    pending_changes = False
                    logger.info("\n[TRIGGER] Debounce window elapsed. Executing automated pipeline...")
                    self.execute(phase="all", truncate=True, trigger_type="WATCHER")
                    snapshot = self._scan_raw_files()

            except SystemExit:
                break
            except Exception as exc:
                logger.error("Watcher encountered error: %s (resuming loop)", exc)
                time.sleep(2.0)

    def _scan_raw_files(self) -> dict[str, str]:
        """Returns map of relative path -> mtime:size hash for change detection."""
        state = {}
        if not RAW_DIR.exists():
            return state

        for child in RAW_DIR.rglob("*"):
            if child.is_file() and child.suffix.lower() in {".csv", ".xlsx", ".xlsm", ".xls"}:
                if not child.name.startswith("~$") and child.name != ".gitkeep":
                    stat = child.stat()
                    signature = f"{stat.st_mtime}:{stat.st_size}"
                    state[str(child.resolve())] = signature
        return state

    # -----------------------------------------------------------------------
    # Scheduled Daemon Runner
    # -----------------------------------------------------------------------
    def start_daemon(self, interval_seconds: int = 300) -> None:
        """Runs the pipeline on a scheduled recurrence."""
        logger.info("Starting RevenueOS Daemon Runner (Interval: %ds)...", interval_seconds)
        logger.info("Press Ctrl+C to terminate.")

        def _sig_handler(sig, frame):
            logger.info("\nTerminating daemon runner gracefully...")
            sys.exit(0)

        signal.signal(signal.SIGINT, _sig_handler)

        while True:
            try:
                logger.info("\n[SCHEDULED] Triggering scheduled pipeline run at %s UTC", datetime.now(timezone.utc).isoformat())
                self.execute(phase="all", truncate=True, trigger_type="SCHEDULED")
                logger.info("Sleeping for %d seconds until next scheduled run...", interval_seconds)
                time.sleep(interval_seconds)
            except SystemExit:
                break
            except Exception as exc:
                logger.error("Daemon cycle error: %s", exc)
                time.sleep(10.0)

    # -----------------------------------------------------------------------
    # Artifact Exporter & Power BI Synchronizer
    # -----------------------------------------------------------------------
    def export_artifacts(self) -> dict[str, Any]:
        """Dumps all Gold analytical datasets to disk and compiles updated Power BI templates."""
        out_gold_dir = PROCESSED_DIR / "gold"
        out_gold_dir.mkdir(parents=True, exist_ok=True)
        db = self.get_db()

        gold_tables = [
            "dim_date", "dim_customer", "dim_product", "dim_channel",
            "dim_location", "dim_supplier", "dim_campaign", "dim_payment_method",
            "fact_orders", "fact_payments", "fact_returns", "fact_inventory", "fact_marketing",
            "gold_daily_financials", "gold_customer_health", "gold_product_profitability",
            "gold_revenue_leakage", "gold_inventory_risk", "gold_marketing_efficiency",
            "gold_investigation_queue"
        ]

        exported = {}
        for table in gold_tables:
            try:
                df = pd.read_sql(f"SELECT * FROM {SCHEMA_GOLD}.{table}", db)
                csv_path = out_gold_dir / f"{table}.csv"
                df.to_csv(csv_path, index=False)
                exported[table] = len(df)
            except Exception as exc:
                logger.warning("Could not export %s: %s", table, exc)

        # Regenerate Power BI .pbit and .pbip
        try:
            from powerbi.build_powerbi_file import build_tmsl_model, build_pbit, build_pbip
            tmsl = build_tmsl_model()
            build_pbit(tmsl)
            build_pbip(tmsl)
            logger.info("Refreshed Power BI assets (RevenueOS.pbit & RevenueOS.pbip).")
        except Exception as exc:
            logger.warning("Power BI asset refresh skipped: %s", exc)

        logger.info("Exported %d Gold tables to %s", len(exported), out_gold_dir)
        return exported

    # -----------------------------------------------------------------------
    # Pre-Flight System Health & Diagnostics
    # -----------------------------------------------------------------------
    def run_health_check(self) -> dict[str, Any]:
        """Runs pre-flight operational checks across database, storage, and schemas."""
        report = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "status": "HEALTHY",
            "database_connected": False,
            "schemas": {},
            "raw_staging": {},
            "issues": [],
        }

        # 1. DB Connectivity
        try:
            db = self.get_db()
            with db.connect() as conn:
                conn.execute(text("SELECT 1"))
            report["database_connected"] = True
        except Exception as exc:
            report["status"] = "UNHEALTHY"
            report["issues"].append(f"Database connection failed: {exc}")

        # 2. Schema verification
        if report["database_connected"]:
            for sch in (SCHEMA_BRONZE, SCHEMA_SILVER, SCHEMA_GOLD):
                try:
                    with db.connect() as conn:
                        res = conn.execute(
                            text("SELECT table_name FROM information_schema.tables WHERE table_schema = :s"),
                            {"s": sch},
                        ).fetchall()
                        tables = [r[0] for r in res]
                        report["schemas"][sch] = {"table_count": len(tables), "tables": tables}
                except Exception as exc:
                    report["issues"].append(f"Failed to inspect schema {sch}: {exc}")

        # 3. Raw Data Staging
        report["raw_staging"]["raw_dir_exists"] = RAW_DIR.exists()
        entity_counts = {}
        for entity in ["orders", "customers", "products", "payments", "returns", "inventory", "marketing", "excel"]:
            p = RAW_DIR / entity
            entity_counts[entity] = len(list(p.glob("*"))) if p.exists() else 0
        report["raw_staging"]["files"] = entity_counts

        print("=" * 65)
        print("REVENUEOS PRE-FLIGHT SYSTEM HEALTH REPORT")
        print("=" * 65)
        print(f"Status           : {report['status']}")
        print(f"Database Online  : {report['database_connected']}")
        if report["database_connected"]:
            for s, meta in report["schemas"].items():
                print(f"  Schema '{s}': {meta['table_count']} tables")
        print("Raw Data Files   :")
        for entity, count in report["raw_staging"]["files"].items():
            print(f"  {entity:<14}: {count} file(s)")
        if report["issues"]:
            print("\nIssues Identified:")
            for issue in report["issues"]:
                print(f"  [!] {issue}")
        print("=" * 65)

        return report

    # -----------------------------------------------------------------------
    # Run Audit Logging
    # -----------------------------------------------------------------------
    def _record_run_start(self, res: PipelineRunResult) -> None:
        self._append_run_file(res)

    def _record_run_end(self, res: PipelineRunResult) -> None:
        self._append_run_file(res)
        # Attempt DB persistence
        try:
            db = self.get_db()
            with db.begin() as conn:
                conn.execute(
                    text(f"""
                        INSERT INTO {SCHEMA_BRONZE}.pipeline_runs
                            (run_id, started_at, completed_at, duration_seconds,
                             trigger_type, phase, status, records_processed,
                             metrics_summary, error_message)
                        VALUES
                            (:rid, :sat, :cat, :dur, :trig, :ph, :stat, :rec, :met, :err)
                        ON CONFLICT (run_id) DO UPDATE SET
                            completed_at = EXCLUDED.completed_at,
                            duration_seconds = EXCLUDED.duration_seconds,
                            status = EXCLUDED.status,
                            records_processed = EXCLUDED.records_processed,
                            metrics_summary = EXCLUDED.metrics_summary,
                            error_message = EXCLUDED.error_message
                    """),
                    {
                        "rid": res.run_id,
                        "sat": res.started_at,
                        "cat": res.completed_at,
                        "dur": res.duration_seconds,
                        "trig": res.trigger_type,
                        "ph": res.phase,
                        "stat": res.status,
                        "rec": res.records_processed,
                        "met": json.dumps(res.metrics_summary),
                        "err": res.error_message,
                    },
                )
        except Exception:
            pass  # file-based audit log acts as resilient fallback

    def _append_run_file(self, res: PipelineRunResult) -> None:
        try:
            self.RUNS_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
            history = []
            if self.RUNS_LOG_PATH.exists():
                try:
                    history = json.loads(self.RUNS_LOG_PATH.read_text(encoding="utf-8"))
                except Exception:
                    history = []

            # Upsert current run by run_id
            updated = False
            for idx, r in enumerate(history):
                if r.get("run_id") == res.run_id:
                    history[idx] = asdict(res)
                    updated = True
                    break
            if not updated:
                history.insert(0, asdict(res))

            # Keep last 100 runs
            history = history[:100]
            self.RUNS_LOG_PATH.write_text(json.dumps(history, indent=2), encoding="utf-8")
        except Exception as exc:
            logger.warning("Could not write file audit log: %s", exc)
