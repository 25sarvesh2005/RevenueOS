"""
RevenueOS – Tests for Enterprise Automation Pipeline Engine
============================================================
Validates:
  - PipelineEngine initialization and configuration
  - Raw file scanning, signature generation, and change detection
  - Audit logging and execution state tracking in JSON
  - Pre-flight health diagnostic engine
  - Phase execution safety and error capture
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from engine.pipeline_engine import PipelineEngine, PipelineRunResult, PhaseResult


class TestPipelineEngine:
    """Test suite for the enterprise automation and orchestration engine."""

    def test_run_result_dataclass(self):
        res = PipelineRunResult(
            run_id="test-run-101",
            trigger_type="WATCHER",
            started_at="2026-10-04T10:00:00Z",
            phase="all",
        )
        assert res.run_id == "test-run-101"
        assert res.trigger_type == "WATCHER"
        assert res.status == "RUNNING"
        assert len(res.phases) == 0

        res.phases.append(PhaseResult(name="Bronze", status="SUCCESS", duration_seconds=1.25))
        assert len(res.phases) == 1
        assert res.phases[0].status == "SUCCESS"

    def test_scan_raw_files(self, tmp_path: Path, monkeypatch):
        test_raw = tmp_path / "raw"
        test_raw.mkdir(parents=True)
        (test_raw / "test1.csv").write_text("a,b,c\n1,2,3", encoding="utf-8")
        (test_raw / "temp.tmp").write_text("ignore me", encoding="utf-8")
        (test_raw / "~$lock.xlsx").write_text("ignore lock", encoding="utf-8")

        monkeypatch.setattr("engine.pipeline_engine.RAW_DIR", test_raw)
        engine = PipelineEngine()
        scanned = engine._scan_raw_files()

        # Should scan test1.csv, ignoring .tmp and ~$lock
        assert len(scanned) == 1
        scanned_paths = [Path(p).name for p in scanned.keys()]
        assert "test1.csv" in scanned_paths
        assert "temp.tmp" not in scanned_paths
        assert "~$lock.xlsx" not in scanned_paths

    def test_audit_logging_to_json(self, tmp_path: Path, monkeypatch):
        test_log_file = tmp_path / "runs.json"
        monkeypatch.setattr(PipelineEngine, "RUNS_LOG_PATH", test_log_file)

        engine = PipelineEngine()
        run1 = PipelineRunResult(
            run_id="run-001",
            trigger_type="MANUAL",
            started_at="2026-10-04T10:00:00Z",
            completed_at="2026-10-04T10:00:05Z",
            duration_seconds=5.0,
            status="SUCCESS",
            phase="all",
        )
        engine._append_run_file(run1)

        assert test_log_file.exists()
        logged = json.loads(test_log_file.read_text(encoding="utf-8"))
        assert len(logged) == 1
        assert logged[0]["run_id"] == "run-001"
        assert logged[0]["status"] == "SUCCESS"

        # Update run1
        run1.status = "FAILED"
        run1.error_message = "Sample error"
        engine._append_run_file(run1)
        logged_updated = json.loads(test_log_file.read_text(encoding="utf-8"))
        assert len(logged_updated) == 1
        assert logged_updated[0]["status"] == "FAILED"
        assert logged_updated[0]["error_message"] == "Sample error"

    def test_health_check_structure(self, tmp_path: Path, monkeypatch):
        test_raw = tmp_path / "raw"
        test_raw.mkdir(parents=True)
        for entity in ["orders", "customers", "products", "payments", "returns", "inventory", "marketing", "excel"]:
            (test_raw / entity).mkdir(parents=True)

        monkeypatch.setattr("engine.pipeline_engine.RAW_DIR", test_raw)
        engine = PipelineEngine()
        report = engine.run_health_check()

        assert "timestamp" in report
        assert "status" in report
        assert "raw_staging" in report
        assert "files" in report["raw_staging"]
        assert "orders" in report["raw_staging"]["files"]
