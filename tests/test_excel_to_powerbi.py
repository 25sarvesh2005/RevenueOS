"""
Unit and integration tests for RevenueOS Universal Excel-to-Power BI Pipeline Engine.
"""

import json
from pathlib import Path
import pandas as pd
import pytest

from engine.excel_to_powerbi import ExcelToPowerBIEngine, clean_identifier, format_title


class TestExcelToPowerBIEngine:
    @pytest.fixture
    def sample_excel(self, tmp_path):
        """Create a temporary multi-sheet Excel file for testing."""
        excel_path = tmp_path / "test_store.xlsx"

        orders_df = pd.DataFrame({
            "order_id": ["ORD-1", "ORD-2", "ORD-3", "ORD-4"],
            "customer_id": ["CUST-101", "CUST-102", "CUST-101", "CUST-103"],
            "product_id": ["PRD-50", "PRD-51", "PRD-50", "PRD-52"],
            "order_date": ["2024-01-15", "2024-02-20", "2024-03-10", "2024-04-05"],
            "quantity": [2, 1, 3, 5],
            "unit_price": [100.0, 250.0, 100.0, 50.0],
            "discount": [10.0, 0.0, 20.0, 0.0],
            "revenue": [190.0, 250.0, 280.0, 250.0],
            "cost": [120.0, 150.0, 180.0, 150.0]
        })

        customers_df = pd.DataFrame({
            "customer_id": ["CUST-101", "CUST-102", "CUST-103"],
            "customer_name": ["Alice Corp", "Bob Ltd", "Charlie Inc"],
            "city": ["New York", "London", "Tokyo"],
            "segment": ["Enterprise", "Mid-Market", "SMB"]
        })

        products_df = pd.DataFrame({
            "product_id": ["PRD-50", "PRD-51", "PRD-52"],
            "product_name": ["Cloud Server", "Analytics Suite", "API Gateway"],
            "category": ["Infrastructure", "Software", "Platform"]
        })

        with pd.ExcelWriter(excel_path, engine="openpyxl") as writer:
            orders_df.to_excel(writer, sheet_name="Orders", index=False)
            customers_df.to_excel(writer, sheet_name="Customers", index=False)
            products_df.to_excel(writer, sheet_name="Products", index=False)

        return excel_path

    def test_clean_identifier(self):
        assert clean_identifier("  Total Sales (USD)  ") == "total_sales_usd"
        assert clean_identifier("Order-ID#") == "order-id" or clean_identifier("Order-ID#") == "order_id"
        assert clean_identifier("Customer Name") == "customer_name"

    def test_format_title(self):
        assert format_title("gross_revenue_amount") == "Gross Revenue Amount"
        assert format_title("customer_id") == "Customer Id"

    def test_pipeline_execution_end_to_end(self, sample_excel, tmp_path):
        out_dir = tmp_path / "output_pbi"
        engine = ExcelToPowerBIEngine(
            excel_path=sample_excel,
            output_dir=out_dir,
            project_name="Test Store Model",
            currency_symbol="$"
        )
        manifest_path = engine.run()

        # 1. Manifest file created and valid
        assert manifest_path.exists()
        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        assert manifest["status"] == "SUCCESS"
        assert manifest["projectName"] == "Test Store Model"
        assert manifest["summary"]["tablesCount"] >= 3
        assert manifest["summary"]["measuresCount"] > 0
        assert manifest["summary"]["hasDateDimension"] is True

        # 2. CSV files exported
        csv_dir = out_dir / "csv"
        assert csv_dir.exists()
        assert (csv_dir / "orders.csv").exists()
        assert (csv_dir / "customers.csv").exists()
        assert (csv_dir / "products.csv").exists()
        assert (csv_dir / "dim_date.csv").exists()

        # 3. Relationships properly formed
        rels = manifest["relationships"]
        assert len(rels) >= 2
        # Check customer link
        has_cust_rel = any(
            r["from_table"] == "orders" and r["from_column"] == "customer_id" and r["to_table"] == "customers"
            for r in rels
        )
        assert has_cust_rel is True

        # Check product link
        has_prod_rel = any(
            r["from_table"] == "orders" and r["from_column"] == "product_id" and r["to_table"] == "products"
            for r in rels
        )
        assert has_prod_rel is True

        # 4. DAX measures generated
        pbi_dir = out_dir / "powerbi"
        dax_file = pbi_dir / "measures.dax"
        assert dax_file.exists()
        dax_content = dax_file.read_text(encoding="utf-8")
        assert "Gross Profit" in dax_content
        assert "Gross Margin %" in dax_content
        assert "TOTALYTD" in dax_content

        # 5. Native Power BI template (.pbit) and project (.pbip) generated
        pbit_file = pbi_dir / "test_store_model.pbit"
        pbip_file = pbi_dir / "test_store_model.pbip"
        assert pbit_file.exists()
        assert pbit_file.stat().st_size > 1000
        assert pbip_file.exists()

        # 6. Deployment guide generated
        guide_file = out_dir / "POWERBI_DEPLOYMENT_GUIDE.md"
        assert guide_file.exists()
        guide_text = guide_file.read_text(encoding="utf-8")
        assert "Method 1: Single-Click Instant Template" in guide_text
        assert "Method 2: Manual CSV Import" in guide_text
        assert "RevenueOS Source-Available Commercial & Royalty License" in guide_text
