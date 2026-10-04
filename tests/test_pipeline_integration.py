"""
End-to-end Integration Tests for RevenueOS Canonical Pipeline Engine.
Verifies full artifact generation, schema profiling, CSV mart persistence,
and metric consistency against enterprise Excel datasets.
"""

import json
from pathlib import Path
import pandas as pd
import pytest

from backend.engine.core import CoreEngine


class TestPipelineIntegration:
    """Tests the canonical pipeline execution against real tabular workbooks."""

    @pytest.fixture
    def sample_excel_path(self):
        root = Path(__file__).resolve().parent.parent
        p = root / "data" / "raw" / "excel" / "revenueos_sample.xlsx"
        if not p.exists():
            fixture = root / "tests" / "fixtures" / "test_sales.xlsx"
            if fixture.exists():
                return fixture
            pytest.skip(f"Baseline sample workbook not found at {p}")
        return p

    def test_full_pipeline_execution_produces_valid_manifest(self, sample_excel_path, tmp_path):
        out_dir = tmp_path / "integration_export"
        engine = CoreEngine(
            excel_path=sample_excel_path,
            output_dir=out_dir,
            project_name="Integration Test Enterprise Model",
            currency_symbol="$",
            emit_manifest=False,
            generate_visuals=True,
        )
        manifest_path = engine.run()

        # 1. Manifest file existence and schema validation
        assert manifest_path.exists()
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))

        assert manifest["status"] == "SUCCESS"
        assert manifest["projectName"] == "Integration Test Enterprise Model"
        assert manifest["summary"]["tablesCount"] >= 4
        assert manifest["summary"]["totalRows"] > 0
        assert manifest["summary"]["measuresCount"] > 0
        assert manifest["summary"]["hasDateDimension"] is True

        # 2. Financial KPIs sanity
        kpis = manifest["dashboard"]["kpis"]
        assert kpis["totalRevenue"] > 0
        assert kpis["totalOrders"] > 0
        assert kpis["grossProfit"] > 0
        assert kpis["grossMarginPct"] > 0

        # 3. CSV Mart validation & Row Count Consistency
        csv_dir = out_dir / "csv"
        assert csv_dir.exists()

        for tbl in manifest["tables"]:
            csv_path = csv_dir / tbl["csv_filename"]
            assert csv_path.exists(), f"CSV file missing on disk: {tbl['csv_filename']}"
            df = pd.read_csv(csv_path, low_memory=False)
            assert len(df) == tbl["row_count"], f"Row count mismatch in {tbl['name']}: CSV={len(df)}, Meta={tbl['row_count']}"

        # 4. Power BI Native Artifacts
        pbi_dir = out_dir / "powerbi"
        assert pbi_dir.exists()

        pbit_file = pbi_dir / "integration_test_enterprise_model.pbit"
        assert pbit_file.exists()
        assert pbit_file.stat().st_size > 1000

        pbip_file = pbi_dir / "integration_test_enterprise_model.pbip"
        assert pbip_file.exists()

        dax_file = pbi_dir / "measures.dax"
        assert dax_file.exists()
        dax_text = dax_file.read_text(encoding="utf-8")
        assert "Total Revenue Attributed" in dax_text
        assert "TOTALYTD" in dax_text
        assert "Total Spend" in dax_text

        # 5. High-Resolution Matplotlib Visuals
        charts_dir = out_dir / "charts"
        assert charts_dir.exists()
        assert len(manifest["charts"]) >= 4

        for chart_info in manifest["charts"]:
            chart_file = Path(chart_info["path"])
            assert chart_file.exists(), f"Chart file not found: {chart_file}"
            assert chart_file.stat().st_size > 5_000, f"Chart file appears corrupt or empty: {chart_file}"

        # 6. Step-by-Step Deployment Guide
        guide_file = out_dir / "POWERBI_DEPLOYMENT_GUIDE.md"
        assert guide_file.exists()
        assert "RevenueOS Source-Available Commercial & Royalty License" in guide_file.read_text(encoding="utf-8")

    def test_direct_revenue_and_cost_margin_dax(self, tmp_path):
        excel_path = tmp_path / "sales_data.xlsx"
        df = pd.DataFrame({
            "order_id": ["O-1", "O-2", "O-3"],
            "order_date": ["2024-01-01", "2024-02-01", "2024-03-01"],
            "revenue": [500.0, 1000.0, 1500.0],
            "cost": [300.0, 600.0, 900.0]
        })
        with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
            df.to_excel(writer, sheet_name="Orders", index=False)

        out_dir = tmp_path / "margin_export"
        engine = CoreEngine(excel_path=excel_path, output_dir=out_dir, emit_manifest=False, generate_visuals=False)
        engine.run()

        dax_file = out_dir / "powerbi" / "measures.dax"
        assert dax_file.exists()
        dax_content = dax_file.read_text(encoding="utf-8")
        assert "Gross Profit =" in dax_content
        assert "Gross Margin % =" in dax_content
