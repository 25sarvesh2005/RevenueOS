"""
RevenueOS – Main Pipeline Orchestrator
========================================
Executes the full Bronze → Silver → Gold pipeline in sequence.

Usage
-----
    python pipeline.py                     # full run
    python pipeline.py --phase bronze      # only bronze ingestion
    python pipeline.py --phase quality     # only quality checks
    python pipeline.py --phase silver      # only silver transformation
    python pipeline.py --phase gold        # only gold build
    python pipeline.py --truncate          # truncate silver/gold before loading
"""

from __future__ import annotations

import argparse
import sys
import time
from datetime import datetime, timezone

from config import get_run_id, logger


def run_phase(name: str, fn, *args, **kwargs):
    logger.info("\n" + "─" * 60)
    logger.info("▶ PHASE: %s", name.upper())
    logger.info("─" * 60)
    t0 = time.time()
    try:
        result = fn(*args, **kwargs)
        elapsed = time.time() - t0
        logger.info("✓ %s completed in %.1fs", name, elapsed)
        return result
    except Exception as exc:
        logger.error("✗ %s FAILED: %s", name, exc)
        raise


def main():
    parser = argparse.ArgumentParser(
        description="RevenueOS – End-to-End Analytics Pipeline"
    )
    parser.add_argument(
        "--phase",
        choices=["bronze", "quality", "silver", "gold", "anomalies", "forecast", "report", "all"],
        default="all",
        help="Which pipeline phase to run.",
    )
    parser.add_argument(
        "--truncate",
        action="store_true",
        help="Truncate target tables before loading (idempotent reruns).",
    )
    args = parser.parse_args()

    run_id    = get_run_id()
    started   = datetime.now(timezone.utc)

    logger.info("=" * 60)
    logger.info("REVENUEOS PIPELINE")
    logger.info("Run ID  : %s", run_id)
    logger.info("Phase   : %s", args.phase)
    logger.info("Truncate: %s", args.truncate)
    logger.info("Started : %s UTC", started.strftime("%Y-%m-%d %H:%M:%S"))
    logger.info("=" * 60)

    # ----------------------------------------------------------------
    # Bronze ingestion
    # ----------------------------------------------------------------
    if args.phase in ("bronze", "all"):
        from ingestion.ingest_bronze import ingest_all
        run_phase("Bronze Ingestion", ingest_all, truncate=args.truncate)

    # ----------------------------------------------------------------
    # Data quality checks
    # ----------------------------------------------------------------
    if args.phase in ("quality", "all"):
        from quality.run_checks import run_quality_checks
        report = run_phase("Data Quality Checks", run_quality_checks, run_id=run_id)
        if report:
            report.print()
            if report.overall_status() == "CRITICAL":
                logger.error("Pipeline halted: CRITICAL quality failure.")
                sys.exit(2)

    # ----------------------------------------------------------------
    # Silver transformation
    # ----------------------------------------------------------------
    if args.phase in ("silver", "all"):
        from transformation.transform_silver import transform_all
        run_phase("Silver Transformation", transform_all, truncate=args.truncate)

    # ----------------------------------------------------------------
    # Gold layer
    # ----------------------------------------------------------------
    if args.phase in ("gold", "all"):
        from transformation.build_gold import build_gold
        run_phase("Gold Layer Build", build_gold)

    # ----------------------------------------------------------------
    # Statistical & ML Anomaly Detection
    # ----------------------------------------------------------------
    if args.phase in ("anomalies", "all"):
        try:
            from config import get_engine, SCHEMA_SILVER
            from python.anomaly_detection.detector import run_anomaly_pipeline
            import pandas as pd
            engine = get_engine()
            orders_df = pd.read_sql(f"SELECT * FROM {SCHEMA_SILVER}.orders", engine)
            products_df = pd.read_sql(f"SELECT * FROM {SCHEMA_SILVER}.products", engine)
            run_phase("Anomaly Engine", run_anomaly_pipeline, orders_df=orders_df, products_df=products_df)
        except Exception as exc:
            logger.warning("Anomaly engine skipped or encountered non-fatal error: %s", exc)

    # ----------------------------------------------------------------
    # Forward-Looking Revenue Forecasting
    # ----------------------------------------------------------------
    if args.phase in ("forecast", "all"):
        try:
            from config import get_engine, SCHEMA_GOLD
            from python.forecasting.forecast_engine import generate_revenue_forecast
            import pandas as pd
            engine = get_engine()
            daily_df = pd.read_sql(f"SELECT * FROM {SCHEMA_GOLD}.gold_daily_financials", engine)
            if not daily_df.empty:
                run_phase("Revenue Forecasting", generate_revenue_forecast, daily_financials_df=daily_df, horizon_days=30)
        except Exception as exc:
            logger.warning("Forecast engine skipped or encountered non-fatal error: %s", exc)

    # ----------------------------------------------------------------
    # Executive Briefing & Decision Report
    # ----------------------------------------------------------------
    if args.phase in ("report", "all"):
        try:
            from config import get_engine
            from python.reporting.executive_report import fetch_gold_summary, generate_executive_briefing
            from pathlib import Path
            engine = get_engine()
            def _gen_report():
                data = fetch_gold_summary(engine)
                md = generate_executive_briefing(data)
                out = Path("docs/executive_briefing.md")
                out.parent.mkdir(parents=True, exist_ok=True)
                out.write_text(md, encoding="utf-8")
                logger.info("Saved executive report to %s", out)
            run_phase("Executive Briefing Generation", _gen_report)
        except Exception as exc:
            logger.warning("Report generation skipped or encountered non-fatal error: %s", exc)

    # ----------------------------------------------------------------
    # Summary
    # ----------------------------------------------------------------
    elapsed = (datetime.now(timezone.utc) - started).total_seconds()
    logger.info("=" * 60)
    logger.info("✓ Pipeline complete in %.1fs", elapsed)
    logger.info("=" * 60)


if __name__ == "__main__":
    main()
