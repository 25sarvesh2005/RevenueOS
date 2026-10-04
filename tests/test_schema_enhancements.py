"""
RevenueOS – Tests for Kimball Schema Enhancements (Phase 6)
===========================================================
Validates:
  - Composite primary key inference
  - Many-to-Many bridge table identification
  - Bidirectional cross-filtering in Power BI TMSL
  - Semantic key alias resolution (customer_id <-> client_id, etc.)
  - Calendar dimension completeness
"""

from pathlib import Path
import json
import pandas as pd
import pytest
from backend.engine.core import CoreEngine, clean_identifier, format_title, TableMeta, ColumnMeta


class TestSchemaEnhancements:
    def test_composite_key_detection_on_line_items(self, tmp_path):
        # Create Excel with an order_items table having composite (order_id, line_no)
        excel_path = tmp_path / "composite_test.xlsx"
        df_items = pd.DataFrame({
            "order_id": ["ORD-1", "ORD-1", "ORD-2", "ORD-2"],
            "line_no": [1, 2, 1, 2],
            "product_id": ["P1", "P2", "P1", "P3"],
            "qty": [1, 5, 2, 1],
            "price": [10.0, 20.0, 10.0, 50.0],
        })
        with pd.ExcelWriter(excel_path) as writer:
            df_items.to_excel(writer, sheet_name="order_items", index=False)

        engine = CoreEngine(excel_path=excel_path, output_dir=tmp_path / "out", generate_visuals=False)
        engine.load_and_profile_sheets()
        engine.analyze_and_build_model()

        tbl = next((t for t in engine.tables if t.name == "order_items"), None)
        assert tbl is not None
        assert tbl.primary_key is None  # Neither order_id nor line_no is uniquely 1:1 on its own
        assert len(tbl.composite_keys) == 2
        assert "order_id" in tbl.composite_keys
        assert "line_no" in tbl.composite_keys

    def test_bridge_table_detection_and_bidirectional_filtering(self, tmp_path):
        engine = CoreEngine(
            excel_path="data/raw/excel/revenueos_sample.xlsx",
            output_dir=tmp_path,
            generate_visuals=False,
        )
        engine.load_and_profile_sheets()
        engine.analyze_and_build_model()

        returns_tbl = next((t for t in engine.tables if t.name == "returns"), None)
        assert returns_tbl is not None
        assert returns_tbl.table_type == "bridge"

        # Check entity relationships attached to returns have BothDirections
        bridge_rels = [r for r in engine.relationships if r.from_table == "returns" and r.to_table != "dim_date"]
        assert len(bridge_rels) >= 2
        for r in bridge_rels:
            assert r.cross_filtering == "BothDirections"
            assert r.cardinality == "ManyToMany"

        # Calendar link should remain OneDirection
        cal_rel = next((r for r in engine.relationships if r.from_table == "returns" and r.to_table == "dim_date"), None)
        if cal_rel:
            assert cal_rel.cross_filtering == "OneDirection"

    def test_tmsl_both_directions_serialization(self, tmp_path):
        engine = CoreEngine(
            excel_path="data/raw/excel/revenueos_sample.xlsx",
            output_dir=tmp_path,
            generate_visuals=False,
        )
        engine.run()

        # Check model.bim in PBIP semantic model directory
        safe_name = clean_identifier(engine.project_name)
        model_bim_path = tmp_path / "powerbi" / f"{safe_name}.SemanticModel" / "model.bim"
        assert model_bim_path.exists()

        tmsl = json.loads(model_bim_path.read_text(encoding="utf-8"))
        rels = tmsl["model"]["relationships"]
        bidirectional_rels = [r for r in rels if r.get("crossFilteringBehavior") == "bothDirections"]
        assert len(bidirectional_rels) >= 1

    def test_key_alias_resolution(self, tmp_path):
        excel_path = tmp_path / "alias_test.xlsx"
        df_clients = pd.DataFrame({
            "client_id": ["C1", "C2", "C3"],
            "client_name": ["Alice", "Bob", "Charlie"],
            "country": ["US", "UK", "CA"],
        })
        df_sales = pd.DataFrame({
            "sale_id": ["S1", "S2", "S3"],
            "customer_id": ["C1", "C2", "C1"],
            "revenue": [100.0, 250.0, 300.0],
        })
        with pd.ExcelWriter(excel_path) as writer:
            df_clients.to_excel(writer, sheet_name="clients", index=False)
            df_sales.to_excel(writer, sheet_name="sales", index=False)

        engine = CoreEngine(excel_path=excel_path, output_dir=tmp_path / "out", generate_visuals=False)
        engine.load_and_profile_sheets()
        engine.analyze_and_build_model()

        # Check that sales.customer_id is linked to clients.client_id
        linked = any(
            r.from_table == "sales" and r.from_column == "customer_id" and r.to_table == "clients" and r.to_column == "client_id"
            for r in engine.relationships
        )
        assert linked, "Expected sales.customer_id to link with clients.client_id via KEY_ALIASES"

    def test_calendar_dimension_completeness(self, tmp_path):
        engine = CoreEngine(
            excel_path="data/raw/excel/revenueos_sample.xlsx",
            output_dir=tmp_path,
            generate_visuals=False,
        )
        engine.load_and_profile_sheets()
        engine.analyze_and_build_model()

        dim_date = next((t for t in engine.tables if t.name == "dim_date"), None)
        assert dim_date is not None
        assert dim_date.table_type == "dimension"
        col_names = [c.name for c in dim_date.columns]
        expected_cols = ["date", "full_date", "year", "quarter", "month", "month_name", "month_year", "day_of_week", "is_weekend"]
        for ec in expected_cols:
            assert ec in col_names

    def test_clean_identifier_utility(self):
        assert clean_identifier("Product SKU # (Units)") == "product_sku_units"
        assert clean_identifier("Total-Revenue$$$") == "total_revenue"
        assert clean_identifier("  spaced   name  ") == "spaced_name"
        assert clean_identifier("") == "unnamed"

    def test_format_title_utility(self):
        assert format_title("gross_margin_pct") == "Gross Margin Pct"
        assert format_title("customer_lifetime_value") == "Customer Lifetime Value"
        assert format_title("dim_products") == "Dim Products"

    def test_calendar_dimension_single_year_boundary(self, tmp_path):
        from datetime import datetime
        engine = CoreEngine(
            excel_path="data/raw/excel/revenueos_sample.xlsx",
            output_dir=tmp_path,
            generate_visuals=False,
        )
        df_cal = engine._generate_calendar_dimension(datetime(2024, 3, 1), datetime(2024, 7, 15))
        assert len(df_cal) == 366  # 2024 is a leap year (full Jan 1 - Dec 31)
        assert df_cal["year"].unique().tolist() == [2024]
        assert "2024-01-01" in df_cal["date"].values
        assert "2024-12-31" in df_cal["date"].values

    def test_clean_identifier_handles_numbers_and_underscores(self):
        assert clean_identifier("123_Order_Summary_456") == "123_order_summary_456"
        assert clean_identifier("___redundant___underscores___") == "redundant_underscores"
        assert clean_identifier("Special & Characters * Here") == "special_characters_here"

    def test_table_meta_preview_rows_structure(self, tmp_path):
        engine = CoreEngine(
            excel_path="data/raw/excel/revenueos_sample.xlsx",
            output_dir=tmp_path,
            generate_visuals=False,
        )
        engine.load_and_profile_sheets()
        engine.analyze_and_build_model()

        orders_tbl = next((t for t in engine.tables if t.name == "orders"), None)
        assert orders_tbl is not None
        assert len(orders_tbl.preview_rows) > 0
        assert isinstance(orders_tbl.preview_rows[0], dict)
        assert "order_id" in orders_tbl.preview_rows[0]

