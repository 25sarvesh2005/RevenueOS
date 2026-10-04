"""
RevenueOS – Enterprise Analytics Pipeline & Automation Engine
=============================================================
Unified entrypoint for execution, automated file watching, scheduled
daemons, pre-flight diagnostics, and artifact publishing.

Usage
-----
    # Standard single execution
    python pipeline.py                          # full pipeline run
    python pipeline.py --phase excel            # import Excel sheets to canonical CSVs
    python pipeline.py --phase bronze           # ingest CSVs into Bronze
    python pipeline.py --phase quality          # run data quality checks
    python pipeline.py --phase silver           # transform into Silver
    python pipeline.py --phase gold             # build Gold star schema & marts
    python pipeline.py --truncate               # truncate target tables before loading

    # Automation Engine modes
    python pipeline.py --watch                  # continuous file watcher for data/raw/
    python pipeline.py --daemon --interval 300  # recurring background scheduler
    python pipeline.py --health                 # pre-flight system & schema diagnostics
    python pipeline.py --export                 # dump Gold marts to CSV & update Power BI
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    from backend.config import logger
    from backend.engine.pipeline_engine import PipelineEngine
except ImportError:
    from config import logger
    from engine.pipeline_engine import PipelineEngine


def main() -> int:
    parser = argparse.ArgumentParser(
        description="RevenueOS - Enterprise Analytics Pipeline & Automation Engine"
    )
    parser.add_argument(
        "--phase",
        choices=["excel", "bronze", "quality", "silver", "gold", "anomalies", "forecast", "report", "all"],
        default="all",
        help="Which pipeline phase to run.",
    )
    parser.add_argument(
        "--excel-path",
        default=None,
        help="Excel workbook or folder to import before Bronze. Defaults to data/raw/excel.",
    )
    parser.add_argument(
        "--truncate",
        action="store_true",
        help="Truncate target tables before loading (idempotent reruns).",
    )
    parser.add_argument(
        "--watch",
        action="store_true",
        help="Run in continuous file watcher mode, triggering pipeline on file changes.",
    )
    parser.add_argument(
        "--daemon",
        action="store_true",
        help="Run in recurring background daemon mode.",
    )
    parser.add_argument(
        "--interval",
        type=int,
        default=300,
        help="Execution interval in seconds for daemon mode (default: 300).",
    )
    parser.add_argument(
        "--health",
        action="store_true",
        help="Run pre-flight database and system health diagnostics.",
    )
    parser.add_argument(
        "--export",
        action="store_true",
        help="Export all Gold analytical tables to processed storage and refresh Power BI assets.",
    )

    args = parser.parse_args()
    engine = PipelineEngine()

    # 1. Health check mode
    if args.health:
        report = engine.run_health_check()
        return 0 if report["status"] == "HEALTHY" else 1

    # 2. Export mode only
    if args.export and not (args.watch or args.daemon):
        engine.export_artifacts()
        return 0

    # 3. Continuous File Watcher mode
    if args.watch:
        engine.start_watcher()
        return 0

    # 4. Recurring Daemon mode
    if args.daemon:
        engine.start_daemon(interval_seconds=args.interval)
        return 0

    # 5. Standard Pipeline Run
    res = engine.execute(
        phase=args.phase,
        truncate=args.truncate,
        excel_path=args.excel_path,
        trigger_type="MANUAL",
        auto_export=True,
    )

    if res.status == "CRITICAL_QUALITY_FAILURE":
        return 2
    elif res.status == "FAILED":
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
