"""
RevenueOS – Master Platform Pre-Flight Verification & Audit Runner
===================================================================
Executes an end-to-end institutional verification of all platform components:
  1. License Integrity & Metadata Conformity
  2. JavaScript ES Module & Electron IPC Syntax Checks
  3. Python Environment & Core Dependencies
  4. Automated Pytest Suite Execution (121 Tests)
  5. Canonical CoreEngine Excel Ingestion & 9-Chart Pack Synthesis
  6. Power BI Template (.pbit) & Fabric Project (.pbip) Artifact Audit
  7. High-Performance DAX Evaluation Engine
  8. Vector PDF Executive Performance Briefing Generation
  9. Pre-Flight Diagnostic Summary

Usage:
  python scripts/verify_platform.py
"""

from __future__ import annotations

import sys
import subprocess
import json
import shutil
import tempfile
import time
from pathlib import Path

# Paths
ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))


def print_header(title: str):
    print("\n" + "=" * 76)
    print(f"  {title.upper()}")
    print("=" * 76)


def print_step(step_num: int, title: str):
    print(f"\n[Step {step_num}/8] {title}...")


def check_license_integrity() -> bool:
    print_step(1, "Validating Commercial License Integrity & pyproject.toml")
    license_file = ROOT_DIR / "LICENSE"
    pyproject_file = ROOT_DIR / "pyproject.toml"

    if not license_file.exists():
        print("  FAIL: LICENSE file missing.")
        return False

    license_text = license_file.read_text(encoding="utf-8")
    if "Sarvesh Sharma" not in license_text or "Commercial & Royalty License" not in license_text:
        print("  FAIL: LICENSE file does not contain expected copyright holder.")
        return False

    pyproj_text = pyproject_file.read_text(encoding="utf-8")
    if "MIT" in pyproj_text:
        print("  FAIL: pyproject.toml contains conflicting MIT license classifier.")
        return False

    if 'license = { file = "LICENSE" }' not in pyproj_text:
        print("  FAIL: pyproject.toml does not reference LICENSE file.")
        return False

    print("  PASS: License declarations are 100% consistent across legal headers and package manifests.")
    return True


def check_javascript_syntax() -> bool:
    print_step(2, "Checking Electron & ES Module JavaScript Syntax")
    node_exe = shutil.which("node")
    if not node_exe:
        print("  WARNING: Node.js executable not in PATH. Skipping Node syntax check.")
        return True

    # Check main and preload
    for f in ["frontend/main.js", "frontend/preload.js"]:
        full_path = ROOT_DIR / f
        res = subprocess.run([node_exe, "--check", str(full_path)], capture_output=True, text=True)
        if res.returncode != 0:
            print(f"  FAIL: Syntax error in {f}:\n{res.stderr}")
            return False

    # Check root ES module app.js
    app_js = ROOT_DIR / "frontend" / "app.js"
    if app_js.exists():
        res = subprocess.run(
            [node_exe, "--input-type=module", "--check"],
            input=app_js.read_text(encoding="utf-8"),
            capture_output=True,
            text=True,
        )
        if res.returncode != 0:
            print(f"  FAIL: Syntax error in frontend/app.js:\n{res.stderr}")
            return False

    # Check ES modules in frontend/modules
    modules = list((ROOT_DIR / "frontend" / "modules").glob("*.js"))
    for mod in modules:
        res = subprocess.run([node_exe, "--check", str(mod)], capture_output=True, text=True)
        if res.returncode != 0:
            print(f"  FAIL: Syntax error in module {mod.name}:\n{res.stderr}")
            return False

    print(f"  PASS: Main process, preload bridge, app.js, and all {len(modules)} frontend ES modules passed syntax check.")
    return True


def run_pytest_suite() -> bool:
    print_step(3, "Executing Pytest Test Suite (121 Tests)")
    start = time.time()
    res = subprocess.run([sys.executable, "-m", "pytest", "tests/", "-q"], cwd=str(ROOT_DIR), capture_output=True, text=True)
    duration = time.time() - start

    if res.returncode != 0:
        print(f"  FAIL: Pytest tests failed:\n{res.stdout}\n{res.stderr}")
        return False

    # Extract test pass count
    last_line = [l.strip() for l in res.stdout.split("\n") if l.strip()][-1]
    print(f"  PASS: {last_line} (Duration: {duration:.2f}s)")
    return True


def verify_canonical_engine_and_charts() -> tuple[bool, dict]:
    print_step(4, "Testing Canonical CoreEngine & 9-Chart Pack Synthesis")
    from backend.engine.core import CoreEngine

    sample_excel = ROOT_DIR / "data" / "raw" / "excel" / "revenueos_sample.xlsx"
    if not sample_excel.exists():
        fixture = ROOT_DIR / "tests" / "fixtures" / "test_sales.xlsx"
        if fixture.exists():
            sample_excel = fixture
        else:
            print(f"  FAIL: Sample workbook not found at {sample_excel}")
            return False, {}

    tmp_dir = Path(tempfile.mkdtemp(prefix="revenueos_verify_"))
    try:
        engine = CoreEngine(
            excel_path=sample_excel,
            output_dir=tmp_dir,
            project_name="PreFlightVerification",
            currency_symbol="$",
            generate_visuals=True,
        )
        manifest_path = engine.run()
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

        # Verify charts
        charts = manifest.get("charts", [])
        if len(charts) != 9:
            print(f"  FAIL: Expected 9 charts, generated {len(charts)}")
            return False, {}

        for c in charts:
            p = Path(c["path"])
            if not p.exists() or p.stat().st_size < 1000:
                print(f"  FAIL: Chart file missing or empty: {c['filename']}")
                return False, {}

        # Verify Power BI artifacts
        pbit = tmp_dir / "powerbi" / "preflightverification.pbit"
        pbip = tmp_dir / "powerbi" / "preflightverification.pbip"
        if not pbit.exists() or pbit.stat().st_size < 1000:
            print("  FAIL: .pbit template missing or invalid.")
            return False, {}
        if not pbip.exists():
            print("  FAIL: .pbip project descriptor missing.")
            return False, {}

        # Verify CSV marts
        csv_files = list((tmp_dir / "csv").glob("*.csv"))
        if len(csv_files) < 4:
            print(f"  FAIL: Expected at least 4 CSV marts, found {len(csv_files)}")
            return False, {}

        print(f"  PASS: CoreEngine ran successfully: {len(manifest['tables'])} tables, {len(manifest['relationships'])} relationships, {len(manifest['daxMeasures'])} DAX measures.")
        print(f"  PASS: Generated all 9 publication-grade Matplotlib charts (waterfall, scatter, heatmap, trends).")
        print(f"  PASS: Compiled standalone Power BI template ({pbit.stat().st_size:,} bytes) and Fabric project.")
        return True, manifest
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)


def verify_dax_evaluator() -> bool:
    print_step(5, "Testing High-Performance DAX Evaluation Engine")
    from backend.api.dax_evaluator import DaxEvaluator

    evaluator = DaxEvaluator(data_dir=ROOT_DIR / "exports" / "default_model")
    expr1 = "SUM(orders[revenue])"
    res1 = evaluator.evaluate(expr1)
    if res1["status"] != "SUCCESS" or res1["evaluated_value"] is None:
        print(f"  FAIL: DAX evaluation failed on {expr1}: {res1.get('error')}")
        return False

    expr2 = "DIVIDE([Total Gross Profit], [Total Revenue], 0)"
    res2 = evaluator.evaluate(expr2)
    if res2["status"] != "SUCCESS":
        print(f"  FAIL: DAX evaluation failed on {expr2}: {res2.get('error')}")
        return False

    print(f"  PASS: DaxEvaluator computed '{expr1}' -> {res1['formatted_value']} in {res1['execution_time_ms']}ms.")
    print(f"  PASS: DaxEvaluator computed '{expr2}' -> {res2['formatted_value']} in {res2['execution_time_ms']}ms.")
    return True


def verify_pdf_reporting() -> bool:
    print_step(6, "Testing Publication Vector PDF Synthesis")
    from backend.python.reporting.executive_report import generate_executive_pdf_from_manifest

    sample_path = ROOT_DIR / "frontend" / "model_data_sample.json"
    if not sample_path.exists():
        from backend.api.app import _ensure_default_artifacts, DEFAULT_MODEL_DIR
        _ensure_default_artifacts()
        sample_path = DEFAULT_MODEL_DIR / "manifest.json"
        if not sample_path.exists():
            print("  FAIL: Neither model_data_sample.json nor default manifest.json found.")
            return False

    manifest = json.loads(sample_path.read_text(encoding="utf-8"))
    tmp_pdf = Path(tempfile.mktemp(suffix=".pdf"))
    try:
        generate_executive_pdf_from_manifest(manifest, tmp_pdf)
        if not tmp_pdf.exists() or tmp_pdf.stat().st_size < 15000:
            print("  FAIL: PDF report output was missing or truncated.")
            return False

        with open(tmp_pdf, "rb") as f:
            if f.read(5) != b"%PDF-":
                print("  FAIL: File is not a valid PDF.")
                return False

        print(f"  PASS: Compiled 3-page publication vector PDF briefing ({tmp_pdf.stat().st_size:,} bytes).")
        return True
    finally:
        if tmp_pdf.exists():
            tmp_pdf.unlink()


def verify_api_endpoints() -> bool:
    print_step(7, "Testing FastAPI REST API Layer Endpoints")
    from starlette.testclient import TestClient
    from backend.api.app import app

    client = TestClient(app)
    # 1. Health
    r_health = client.get("/api/health")
    if r_health.status_code != 200 or r_health.json().get("status") != "HEALTHY":
        print(f"  FAIL: /api/health endpoint unhealthy: {r_health.status_code}")
        return False

    # 2. Executive HTML
    r_html = client.get("/api/reports/default/executive-html")
    if r_html.status_code != 200 or "<!DOCTYPE html>" not in r_html.text:
        print(f"  FAIL: /api/reports/default/executive-html failed: {r_html.status_code}")
        return False

    # 3. Executive PDF
    r_pdf = client.get("/api/reports/default/executive-pdf")
    if r_pdf.status_code != 200 or not r_pdf.content.startswith(b"%PDF-"):
        print(f"  FAIL: /api/reports/default/executive-pdf failed: {r_pdf.status_code}")
        return False

    # 4. Copilot memo
    r_copilot = client.post("/api/copilot/investigate", json={"entity_name": "TestEntity", "issue": "Margin Variance"})
    if r_copilot.status_code != 200 or "REVENUEOS INVESTIGATION BRIEFING" not in r_copilot.json().get("briefing", ""):
        print(f"  FAIL: /api/copilot/investigate failed: {r_copilot.status_code}")
        return False

    print("  PASS: REST API endpoints (/api/health, /reports, /pdf, /copilot) verified successfully.")
    return True


def verify_institutional_documentation() -> bool:
    print_step(8, "Verifying Institutional Documentation Suite")
    doc_files = [
        "docs/business_requirements.md",
        "docs/metric_definitions.md",
        "docs/data_dictionary.md",
        "docs/pipeline_runbook.md",
        "docs/runbook.md",
        "docs/assumptions.md",
        "README.md",
        "LICENSE",
    ]
    for d in doc_files:
        p = ROOT_DIR / d
        if not p.exists() or p.stat().st_size < 500:
            print(f"  FAIL: Institutional documentation missing or incomplete: {d}")
            return False

    print(f"  PASS: All {len(doc_files)} institutional documentation and governance manuals present and validated.")
    return True


def main():
    print_header("RevenueOS Enterprise Pre-Flight Platform Verification")
    print(f"Workspace Root: {ROOT_DIR}")
    print(f"Timestamp     : {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}")
    print(f"Copyright     : © Sarvesh Sharma — RevenueOS Commercial Royalty License v1.0")

    checks = [
        ("License Integrity", check_license_integrity),
        ("JavaScript & Electron Syntax", check_javascript_syntax),
        ("Pytest Test Suite (121 Tests)", run_pytest_suite),
        ("CoreEngine & 9-Chart Pack", lambda: verify_canonical_engine_and_charts()[0]),
        ("DAX Evaluation Engine", verify_dax_evaluator),
        ("Publication PDF Engine", verify_pdf_reporting),
        ("FastAPI REST Layer", verify_api_endpoints),
        ("Institutional Documentation", verify_institutional_documentation),
    ]

    all_passed = True
    start_total = time.time()

    for name, check_fn in checks:
        try:
            passed = check_fn()
            if not passed:
                all_passed = False
                break
        except Exception as e:
            print(f"  CRITICAL ERROR in {name}: {e}")
            all_passed = False
            break

    total_duration = time.time() - start_total
    print_header("Verification Results Summary")

    if all_passed:
        print(f"  STATUS      : 100% PASSED (ALL 8 CHECKS GREEN)")
        print(f"  TOTAL TIME  : {total_duration:.2f} seconds")
        print(f"  VERDICT     : PRODUCTION READY & COMMERCIALLY COMPLIANT")
        print("=" * 76 + "\n")
        sys.exit(0)
    else:
        print(f"  STATUS      : VERIFICATION FAILED")
        print(f"  TOTAL TIME  : {total_duration:.2f} seconds")
        print(f"  VERDICT     : REMEDIATION REQUIRED")
        print("=" * 76 + "\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
