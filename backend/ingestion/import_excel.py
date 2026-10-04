"""
RevenueOS Excel Importer
========================
Converts Excel workbooks into canonical raw CSV files for the Bronze pipeline.

Expected workbook pattern
-------------------------
One sheet per entity, with sheet names such as:
orders, customers, products, payments, returns, inventory, marketing.

Usage
-----
    python ingestion/import_excel.py data/raw/excel/revenueos_source.xlsx
    python ingestion/import_excel.py data/raw/excel --overwrite
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

import pandas as pd

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import RAW_DIR, logger
from ingestion.ingest_bronze import ENTITIES, OPTIONAL_SOURCE_COLUMNS


ENTITY_ALIASES: dict[str, set[str]] = {
    "orders": {"orders", "order", "sales", "sales_orders", "transactions"},
    "customers": {"customers", "customer", "clients", "accounts"},
    "products": {"products", "product", "items", "skus", "catalog"},
    "payments": {"payments", "payment", "transactions_payments"},
    "returns": {"returns", "return", "refunds", "rma"},
    "inventory": {"inventory", "stock", "warehouse", "warehouse_stock"},
    "marketing": {"marketing", "campaigns", "campaign", "ad_spend", "media"},
}

COLUMN_ALIASES: dict[str, dict[str, str]] = {
    "*": {
        "id": "id",
        "date": "date",
        "orderdate": "order_date",
        "order_date": "order_date",
        "customerid": "customer_id",
        "customer_id": "customer_id",
        "productid": "product_id",
        "product_id": "product_id",
        "sku": "product_id",
        "qty": "quantity",
        "unitprice": "unit_price",
        "unit_price": "unit_price",
        "discount_percent": "discount",
        "discount_pct": "discount",
        "discount_rate": "discount",
        "channel_name": "channel",
        "order_status": "status",
    },
    "orders": {
        "sales_order_id": "order_id",
        "order_number": "order_id",
        "orderid": "order_id",
    },
    "customers": {
        "customer_name": "name",
        "client_name": "name",
        "signup": "signup_date",
        "signupdate": "signup_date",
    },
    "products": {
        "item_id": "product_id",
        "item_name": "product_name",
        "sku_name": "product_name",
        "name": "product_name",
        "price": "selling_price",
        "msrp": "selling_price",
        "unit_cost": "cost",
    },
    "payments": {
        "paymentid": "payment_id",
        "payment_status": "payment_status",
        "status": "payment_status",
        "method": "payment_method",
        "reason": "failure_reason",
    },
    "returns": {
        "returnid": "return_id",
        "returned_quantity": "quantity_returned",
        "returned_qty": "quantity_returned",
        "reason": "return_reason",
    },
    "inventory": {
        "stock_date": "snapshot_date",
        "available": "units_available",
        "on_hand": "units_available",
        "reserved": "units_reserved",
        "sold": "units_sold",
    },
    "marketing": {
        "campaign": "campaign_id",
        "campaign_name": "campaign_id",
        "media_channel": "channel",
        "cost": "spend",
        "conversions": "orders_attributed",
        "orders": "orders_attributed",
        "attributed_orders": "orders_attributed",
        "revenue": "revenue_attributed",
        "attributed_revenue": "revenue_attributed",
    },
}

DEFAULT_VALUES: dict[str, dict[str, object]] = {
    "inventory": {"units_reserved": 0, "units_sold": 0},
    "marketing": {"orders_attributed": 0, "revenue_attributed": 0},
}


def normalize_name(value: object) -> str:
    """Normalize sheet and column names to snake_case-like identifiers."""
    text = str(value).strip().lower()
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return re.sub(r"_+", "_", text).strip("_")


def detect_entity(sheet_name: str) -> str | None:
    """Infer the RevenueOS entity represented by a workbook sheet."""
    normalized = normalize_name(sheet_name)
    for entity, aliases in ENTITY_ALIASES.items():
        if normalized == entity or normalized in aliases:
            return entity
    return None


def _column_aliases_for(entity: str) -> dict[str, str]:
    aliases = dict(COLUMN_ALIASES["*"])
    aliases.update(COLUMN_ALIASES.get(entity, {}))
    return aliases


def standardize_frame(df: pd.DataFrame, entity: str) -> pd.DataFrame:
    """Clean a workbook sheet into the canonical raw schema for one entity."""
    df = df.dropna(how="all").dropna(axis=1, how="all").copy()
    df.columns = [normalize_name(c) for c in df.columns]
    df = df.rename(columns=_column_aliases_for(entity))
    df = df.loc[:, ~df.columns.duplicated()]

    for col in df.select_dtypes(include=["object"]).columns:
        df[col] = df[col].map(lambda value: value.strip() if isinstance(value, str) else value)

    expected_cols = ENTITIES[entity]["expected_columns"]
    for col, default in DEFAULT_VALUES.get(entity, {}).items():
        if col not in df.columns:
            df[col] = default

    for col in expected_cols:
        if col not in df.columns:
            df[col] = ""
            logger.warning("Excel sheet for %s is missing '%s'; added empty column.", entity, col)

    allowed_cols = expected_cols | OPTIONAL_SOURCE_COLUMNS.get(entity, set())
    return df[[col for col in df.columns if col in allowed_cols]]


def _safe_output_name(workbook: Path, sheet_name: str) -> str:
    stem = normalize_name(workbook.stem) or "workbook"
    sheet = normalize_name(sheet_name) or "sheet"
    return f"{stem}__{sheet}.csv"


def import_excel_file(path: Path, out_dir: Path = RAW_DIR,
                      overwrite: bool = True) -> dict[str, list[Path]]:
    """Convert one workbook into raw CSV files grouped by entity."""
    path = path.resolve()
    outputs: dict[str, list[Path]] = {entity: [] for entity in ENTITIES}
    workbook = pd.ExcelFile(path)

    for sheet_name in workbook.sheet_names:
        entity = detect_entity(sheet_name)
        if entity is None:
            logger.info("Skipping sheet '%s' in %s; no entity match.", sheet_name, path.name)
            continue

        df = pd.read_excel(workbook, sheet_name=sheet_name)
        cleaned = standardize_frame(df, entity)
        entity_dir = out_dir / entity
        entity_dir.mkdir(parents=True, exist_ok=True)
        out_path = entity_dir / _safe_output_name(path, sheet_name)

        if out_path.exists() and not overwrite:
            logger.warning("Skipping existing CSV: %s", out_path)
            continue

        cleaned.to_csv(out_path, index=False)
        outputs[entity].append(out_path)
        logger.info("Imported %s:%s -> %s (%d rows)", path.name, sheet_name, out_path, len(cleaned))

    return {entity: files for entity, files in outputs.items() if files}


def _iter_excel_files(paths: list[Path]) -> list[Path]:
    files: list[Path] = []
    for path in paths:
        if path.is_dir():
            files.extend(
                child for child in sorted(path.iterdir())
                if child.suffix.lower() in {".xlsx", ".xlsm", ".xls"} and not child.name.startswith("~$")
            )
        elif path.suffix.lower() in {".xlsx", ".xlsm", ".xls"}:
            files.append(path)
    return files


def import_excel_paths(paths: list[Path] | None = None,
                       out_dir: Path = RAW_DIR,
                       overwrite: bool = True) -> dict[str, list[Path]]:
    """Import every workbook from the provided paths."""
    source_paths = paths or [RAW_DIR / "excel"]
    files = _iter_excel_files(source_paths)
    if not files:
        logger.warning("No Excel workbooks found in: %s", ", ".join(str(p) for p in source_paths))
        return {}

    summary: dict[str, list[Path]] = {}
    for file_path in files:
        imported = import_excel_file(file_path, out_dir=out_dir, overwrite=overwrite)
        for entity, output_files in imported.items():
            summary.setdefault(entity, []).extend(output_files)
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description="Import Excel workbooks into RevenueOS raw CSV folders.")
    parser.add_argument(
        "paths",
        nargs="*",
        type=Path,
        default=[RAW_DIR / "excel"],
        help="Excel workbook file(s) or folder(s). Defaults to data/raw/excel.",
    )
    parser.add_argument("--out-dir", type=Path, default=RAW_DIR, help="Raw output directory.")
    parser.add_argument("--overwrite", action="store_true", help="Overwrite generated CSV files.")
    args = parser.parse_args()

    summary = import_excel_paths(args.paths, out_dir=args.out_dir, overwrite=args.overwrite)
    total_files = sum(len(files) for files in summary.values())
    print(f"Imported {total_files} CSV file(s) from Excel.")
    for entity, files in summary.items():
        print(f"  {entity}: {len(files)} file(s)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
