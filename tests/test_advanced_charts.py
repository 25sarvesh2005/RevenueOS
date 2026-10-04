"""
RevenueOS – Tests for Advanced Matplotlib Chart Visualizations (Phase 6)
========================================================================
Validates 9-chart analytical pack generation:
  1. Monthly Revenue & Margin Trend (Dual Axis)
  2. Category Revenue Distribution
  3. Channel Revenue Breakdown
  4. Top Products Ranking
  5. Executive 4-Quadrant Summary Dashboard
  6. Marketing Spend vs ROAS
  7. Gross-to-Net Revenue Waterfall
  8. Price Elasticity & Volume Scatter
  9. Cross-Metric Correlation Heatmap
"""

from pathlib import Path
import json
import pytest
from backend.engine.core import CoreEngine


class TestAdvancedCharts:
    @pytest.fixture(scope="class")
    def run_output(self, tmp_path_factory):
        tmp_dir = tmp_path_factory.mktemp("adv_charts")
        engine = CoreEngine(
            excel_path="data/raw/excel/revenueos_sample.xlsx",
            output_dir=tmp_dir,
            project_name="ChartTestOS",
            currency_symbol="$",
            generate_visuals=True,
        )
        manifest_path = engine.run()
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        return {
            "output_dir": tmp_dir,
            "manifest": manifest,
            "engine": engine,
        }

    def test_all_nine_charts_registered_in_manifest(self, run_output):
        manifest = run_output["manifest"]
        charts = manifest.get("charts", [])
        assert len(charts) == 9, f"Expected 9 charts, found {len(charts)}"

        expected_ids = [
            "chart_monthly_trend",
            "chart_category_share",
            "chart_channel_breakdown",
            "chart_top_products",
            "chart_executive_dashboard",
            "chart_marketing_roas",
            "chart_gross_to_net_waterfall",
            "chart_price_elasticity",
            "chart_correlation_matrix",
        ]
        actual_ids = [c["id"] for c in charts]
        for eid in expected_ids:
            assert eid in actual_ids, f"Missing expected chart ID: {eid}"

    def test_all_chart_files_exist_on_disk(self, run_output):
        manifest = run_output["manifest"]
        output_dir = run_output["output_dir"]
        charts_dir = output_dir / "charts"
        assert charts_dir.exists()

        for c in manifest["charts"]:
            chart_file = charts_dir / c["filename"]
            assert chart_file.exists(), f"Chart file does not exist: {c['filename']}"
            assert chart_file.stat().st_size > 2000, f"Chart file is too small/empty: {c['filename']}"

    def test_png_headers_are_valid(self, run_output):
        output_dir = run_output["output_dir"]
        charts_dir = output_dir / "charts"
        png_magic = b"\x89PNG\r\n\x1a\n"

        for chart_path in charts_dir.glob("*.png"):
            with open(chart_path, "rb") as f:
                header = f.read(8)
                assert header == png_magic, f"File {chart_path.name} is not a valid PNG image"

    def test_waterfall_chart_generation(self, run_output):
        manifest = run_output["manifest"]
        c7 = next((c for c in manifest["charts"] if c["id"] == "chart_gross_to_net_waterfall"), None)
        assert c7 is not None
        assert "waterfall" in c7["filename"].lower()
        assert c7["title"] == "Gross-to-Net Revenue Waterfall"

    def test_price_elasticity_scatter_generation(self, run_output):
        manifest = run_output["manifest"]
        c8 = next((c for c in manifest["charts"] if c["id"] == "chart_price_elasticity"), None)
        assert c8 is not None
        assert "elasticity" in c8["filename"].lower()
        assert c8["title"] == "Price Elasticity & Demand Scatter"

    def test_correlation_heatmap_generation(self, run_output):
        manifest = run_output["manifest"]
        c9 = next((c for c in manifest["charts"] if c["id"] == "chart_correlation_matrix"), None)
        assert c9 is not None
        assert "correlation" in c9["filename"].lower()
        assert c9["title"] == "Cross-Metric Correlation Heatmap"

    def test_charts_disabled_flag(self, tmp_path):
        engine = CoreEngine(
            excel_path="data/raw/excel/revenueos_sample.xlsx",
            output_dir=tmp_path,
            generate_visuals=False,
        )
        manifest_path = engine.run()
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert len(manifest.get("charts", [])) == 0

    def test_custom_currency_symbol_propagation(self, tmp_path):
        engine = CoreEngine(
            excel_path="data/raw/excel/revenueos_sample.xlsx",
            output_dir=tmp_path,
            currency_symbol="₹",
            generate_visuals=True,
        )
        manifest_path = engine.run()
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert manifest["dashboard"]["kpis"]["currency"] == "₹"
        assert len(manifest["charts"]) == 9
