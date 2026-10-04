"""
RevenueOS – Tests for Excel Importer
====================================
Validates:
  - Sheet entity detection across synonyms and aliases
  - Column name normalization and alias resolution
  - Default value backfilling for missing optional columns
  - Multi-sheet Excel workbook ingestion into canonical raw CSV files
"""

from __future__ import annotations

from pathlib import Path
import pandas as pd
import pytest

from ingestion.import_excel import (
    detect_entity,
    normalize_name,
    standardize_frame,
    import_excel_file,
    import_excel_paths,
)


class TestExcelImporter:
    """Unit and integration tests for the Excel ingestion module."""

    def test_normalize_name(self):
        assert normalize_name("Order ID") == "order_id"
        assert normalize_name("Sales Orders-2024!") == "sales_orders_2024"
        assert normalize_name("  unit_price   ") == "unit_price"
        assert normalize_name("Discount%") == "discount"

    def test_detect_entity_exact_and_aliases(self):
        assert detect_entity("orders") == "orders"
        assert detect_entity("Sales_Orders") == "orders"
        assert detect_entity("Transactions") == "orders"
        assert detect_entity("Clients") == "customers"
        assert detect_entity("SKUs") == "products"
        assert detect_entity("Refunds") == "returns"
        assert detect_entity("Warehouse_Stock") == "inventory"
        assert detect_entity("Campaigns") == "marketing"
        assert detect_entity("Unknown_Sheet") is None

    def test_standardize_frame_column_aliases(self):
        raw_df = pd.DataFrame({
            "Order Number": ["ORD-101", "ORD-102"],
            "Customer ID": ["CUST-1", "CUST-2"],
            "SKU": ["PROD-1", "PROD-2"],
            "OrderDate": ["2024-01-01", "2024-01-02"],
            "Qty": [2, 5],
            "UnitPrice": [100.0, 250.0],
            "Discount Rate": [0.10, 0.05],
            "Channel Name": ["Direct", "Amazon"],
            "Order Status": ["COMPLETED", "SHIPPED"],
        })

        cleaned = standardize_frame(raw_df, "orders")

        assert "order_id" in cleaned.columns
        assert "customer_id" in cleaned.columns
        assert "product_id" in cleaned.columns
        assert "order_date" in cleaned.columns
        assert "quantity" in cleaned.columns
        assert "unit_price" in cleaned.columns
        assert "discount" in cleaned.columns
        assert "channel" in cleaned.columns
        assert "status" in cleaned.columns
        assert cleaned["order_id"].tolist() == ["ORD-101", "ORD-102"]

    def test_standardize_frame_default_values(self):
        raw_inv = pd.DataFrame({
            "product_id": ["P1", "P2"],
            "warehouse": ["WH-North", "WH-South"],
            "snapshot_date": ["2024-01-01", "2024-01-01"],
            "units_available": [50, 0],
        })
        cleaned = standardize_frame(raw_inv, "inventory")
        assert "units_reserved" in cleaned.columns
        assert "units_sold" in cleaned.columns
        assert cleaned["units_reserved"].tolist() == [0, 0]
        assert cleaned["units_sold"].tolist() == [0, 0]

    def test_import_excel_workbook(self, tmp_path: Path):
        workbook_path = tmp_path / "test_retail_data.xlsx"
        out_dir = tmp_path / "raw_out"

        orders_data = pd.DataFrame({
            "order_id": ["O1", "O2"],
            "customer_id": ["C1", "C2"],
            "product_id": ["P1", "P2"],
            "order_date": ["2024-01-01", "2024-01-02"],
            "quantity": [1, 2],
            "unit_price": [50.0, 100.0],
            "discount": [0.0, 0.1],
            "channel": ["Online", "Store"],
        })
        customers_data = pd.DataFrame({
            "customer_id": ["C1", "C2"],
            "name": ["Alice", "Bob"],
            "email": ["alice@example.com", "bob@example.com"],
            "city": ["Mumbai", "Delhi"],
            "region": ["West", "North"],
            "signup_date": ["2023-05-01", "2023-06-15"],
            "segment": ["VIP", "Regular"],
        })

        with pd.ExcelWriter(workbook_path, engine="openpyxl") as writer:
            orders_data.to_excel(writer, sheet_name="Sales_Orders", index=False)
            customers_data.to_excel(writer, sheet_name="Clients", index=False)
            pd.DataFrame({"notes": ["random metadata"]}).to_excel(writer, sheet_name="Notes", index=False)

        summary = import_excel_file(workbook_path, out_dir=out_dir, overwrite=True)

        assert "orders" in summary
        assert "customers" in summary
        assert "marketing" not in summary

        orders_csv = summary["orders"][0]
        assert orders_csv.exists()
        df_read_orders = pd.read_csv(orders_csv)
        assert len(df_read_orders) == 2
        assert "order_id" in df_read_orders.columns

        customers_csv = summary["customers"][0]
        assert customers_csv.exists()
        df_read_cust = pd.read_csv(customers_csv)
        assert len(df_read_cust) == 2
        assert "customer_id" in df_read_cust.columns
