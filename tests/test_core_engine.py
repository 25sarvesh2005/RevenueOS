"""
Unit and integration tests for RevenueOS Canonical Core Engine (backend/engine/core.py).
"""

import json
from pathlib import Path
import pandas as pd
import pytest

from engine.core import CoreEngine, clean_identifier, format_title


class TestCoreEngine:
    @pytest.fixture
    def multi_sheet_excel(self, tmp_path):
        """Create a multi-sheet Excel file with marketing and orders for comprehensive engine testing."""
        excel_path = tmp_path / "enterprise_sales.xlsx"

        orders_df = pd.DataFrame({
            "order_id": ["ORD-101", "ORD-102", "ORD-103", "ORD-104", "ORD-105"],
            "customer_id": ["CUST-1", "CUST-2", "CUST-1", "CUST-3", "CUST-2"],
            "product_id": ["PRD-A", "PRD-B", "PRD-A", "PRD-C", "PRD-B"],
            "order_date": ["2024-01-10", "2024-02-15", "2024-03-20", "2024-04-25", "2024-05-30"],
            "quantity": [2, 1, 4, 3, 2],
            "unit_price": [150.0, 300.0, 150.0, 75.0, 300.0],
            "discount": [15.0, 0.0, 30.0, 0.0, 20.0],
            "revenue": [285.0, 300.0, 570.0, 225.0, 580.0],
            "cost": [160.0, 180.0, 320.0, 120.0, 360.0],
            "channel": ["Direct", "Partner", "Organic", "Paid Search", "Direct"]
        })

        customers_df = pd.DataFrame({
            "customer_id": ["CUST-1", "CUST-2", "CUST-3"],
            "customer_name": ["Acme Corp", "Beta LLC", "Gamma Inc"],
            "segment": ["Enterprise", "Mid-Market", "SMB"]
        })

        products_df = pd.DataFrame({
            "product_id": ["PRD-A", "PRD-B", "PRD-C"],
            "product_name": ["Platform Pro", "Analytics Core", "Connector Suite"],
            "category": ["Software", "SaaS", "Integration"]
        })

        marketing_df = pd.DataFrame({
            "channel": ["Direct", "Partner", "Organic", "Paid Search"],
            "spend": [500.0, 1200.0, 200.0, 1500.0],
            "revenue": [2000.0, 4800.0, 1000.0, 4500.0],
            "impressions": [10000, 25000, 5000, 40000],
            "clicks": [500, 1200, 300, 2100]
        })

        with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
            orders_df.to_excel(writer, sheet_name="Orders", index=False)
            customers_df.to_excel(writer, sheet_name="Customers", index=False)
            products_df.to_excel(writer, sheet_name="Products", index=False)
            marketing_df.to_excel(writer, sheet_name="Marketing", index=False)

        return excel_path

    def test_canonical_core_engine_execution(self, multi_sheet_excel, tmp_path):
        out_dir = tmp_path / "canonical_export"
        engine = CoreEngine(
            excel_path=multi_sheet_excel,
            output_dir=out_dir,
            project_name="Enterprise Model",
            currency_symbol="$",
            emit_manifest=False,
            generate_visuals=True
        )
        manifest_path = engine.run()

        assert manifest_path.exists()
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        assert manifest["status"] == "SUCCESS"
        assert manifest["projectName"] == "Enterprise Model"
        assert manifest["summary"]["tablesCount"] >= 4
        assert manifest["summary"]["hasDateDimension"] is True

        # Check charts generated
        assert "charts" in manifest
        assert len(manifest["charts"]) >= 4
        charts_dir = out_dir / "charts"
        assert charts_dir.exists()
        for chart_info in manifest["charts"]:
            chart_file = Path(chart_info["path"])
            assert chart_file.exists()
            assert chart_file.stat().st_size > 0

        # Check dashboard aggregations
        assert "dashboard" in manifest
        kpis = manifest["dashboard"]["kpis"]
        assert kpis["totalOrders"] == 5
        assert kpis["totalRevenue"] > 1000
        assert kpis["grossProfit"] > 0
        assert len(manifest["dashboard"]["timeSeries"]) > 0

        # Check Power BI artifacts
        pbi_dir = out_dir / "powerbi"
        assert (pbi_dir / "enterprise_model.pbit").exists()
        assert (pbi_dir / "enterprise_model.pbip").exists()
        assert (pbi_dir / "measures.dax").exists()

    def test_canonical_core_engine_csv_ingestion(self, tmp_path):
        csv_file = tmp_path / "simple_sales.csv"
        df = pd.DataFrame({
            "order_id": ["O-1", "O-2", "O-3"],
            "customer_id": ["C-1", "C-2", "C-1"],
            "revenue": [500.0, 750.0, 250.0],
            "cost": [250.0, 400.0, 100.0],
            "order_date": ["2025-01-01", "2025-01-02", "2025-01-03"],
        })
        df.to_csv(csv_file, index=False)

        out_dir = tmp_path / "csv_out"
        engine = CoreEngine(
            excel_path=csv_file,
            output_dir=out_dir,
            project_name="Direct CSV Ingestion",
            emit_manifest=False,
            generate_visuals=False,
        )
        manifest_path = engine.run()
        assert manifest_path.exists()

        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        assert manifest["status"] == "SUCCESS"
        assert manifest["projectName"] == "Direct CSV Ingestion"
        assert manifest["summary"]["totalRows"] >= 3
        assert len(manifest["tables"]) >= 1
