"""
RevenueOS – Silver Transformation Layer
=========================================
Transforms validated Bronze data into standardized Silver tables.

Transformations applied:
  - Type coercion (TEXT → DATE, NUMERIC, etc.)
  - Discount normalization (0–100 range → 0–1 decimal)
  - Derived financial columns (gross_revenue, discount_amount, net_sales)
  - Category/status standardization (UPPER/title-case)
  - ID trimming (whitespace removal)
  - CTR calculation for marketing
  - Margin calculation for products
  - Rejection of records that cannot be safely typed

Every transformation is documented in comments below.
"""

from __future__ import annotations

import sys
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import numpy as np
from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    SCHEMA_BRONZE,
    SCHEMA_SILVER,
    get_engine,
    get_run_id,
    logger,
)


# ---------------------------------------------------------------------------
# Utility helpers
# ---------------------------------------------------------------------------

def _to_date(series: pd.Series, col_name: str) -> pd.Series:
    """Coerce a text column to datetime.date. Unparseable → NaT."""
    parsed = pd.to_datetime(series, errors="coerce", infer_datetime_format=True)
    n_failed = parsed.isna().sum() - series.isna().sum()
    if n_failed > 0:
        logger.warning("  %s: %d values could not be parsed as dates → NaT", col_name, n_failed)
    return parsed.dt.date


def _to_numeric(series: pd.Series, col_name: str) -> pd.Series:
    """Coerce a text column to float. Unparseable → NaN."""
    result = pd.to_numeric(series, errors="coerce")
    n_failed = result.isna().sum() - series.isna().sum()
    if n_failed > 0:
        logger.warning("  %s: %d non-numeric values → NaN", col_name, n_failed)
    return result


def _normalize_discount(series: pd.Series) -> pd.Series:
    """
    Normalize discount to [0, 1] decimal.
    Some sources store discount as 0–100 (percentage), others as 0–1.
    Rule: if median > 1, treat as percentage and divide by 100.
    """
    numeric = pd.to_numeric(series, errors="coerce")
    if numeric.dropna().median() > 1:
        logger.info("  discount: detected percentage format (>1), dividing by 100")
        numeric = numeric / 100.0
    # Clamp to [0, 1]
    numeric = numeric.clip(0, 1)
    return numeric


def _clean_id(series: pd.Series) -> pd.Series:
    """Strip whitespace from ID columns."""
    return series.astype(str).str.strip()


def _standardize_text(series: pd.Series) -> pd.Series:
    """Title-case and strip a text column."""
    return series.astype(str).str.strip().str.title()


def _write_silver(df: pd.DataFrame, table_name: str, engine,
                  run_id: str, truncate: bool = False) -> None:
    """Write a DataFrame to a silver table."""
    df["run_id"]      = run_id
    df["ingested_at"] = datetime.now(timezone.utc).isoformat()

    with engine.begin() as conn:
        if truncate:
            conn.execute(text(f"TRUNCATE TABLE {SCHEMA_SILVER}.{table_name}"))
        df.to_sql(
            name=table_name,
            schema=SCHEMA_SILVER,
            con=conn,
            if_exists="append",
            index=False,
            method="multi",
            chunksize=5000,
        )
    logger.info("  → silver.%s: %d rows written", table_name, len(df))


# ---------------------------------------------------------------------------
# Per-entity transformations
# ---------------------------------------------------------------------------

def transform_orders(engine, run_id: str, truncate: bool = False) -> int:
    """Bronze → Silver: orders."""
    logger.info("[orders] Transforming bronze → silver")
    df = pd.read_sql(f"SELECT * FROM {SCHEMA_BRONZE}.orders", engine)
    logger.info("  Bronze rows loaded: %d", len(df))

    # ID cleaning
    df["order_id"]    = _clean_id(df["order_id"])
    df["customer_id"] = _clean_id(df["customer_id"])
    df["product_id"]  = _clean_id(df["product_id"])

    # Date parsing
    df["order_date"] = _to_date(df["order_date"], "order_date")

    # Numeric coercion
    df["quantity"]   = _to_numeric(df["quantity"],   "quantity")
    df["unit_price"] = _to_numeric(df["unit_price"], "unit_price")
    df["discount"]   = _normalize_discount(df.get("discount", pd.Series(dtype=float)))

    # Standardize categoricals
    df["channel"]  = _standardize_text(df.get("channel",  pd.Series(dtype=str)))
    df["location"] = _standardize_text(df.get("location", pd.Series(dtype=str)))
    df["status"]   = df.get("status", pd.Series(dtype=str)).astype(str).str.strip().str.upper()

    # Derived financial metrics
    df["gross_revenue"]   = df["quantity"] * df["unit_price"]
    df["discount_amount"] = df["gross_revenue"] * df["discount"].fillna(0)
    df["net_sales"]       = df["gross_revenue"] - df["discount_amount"]

    # Drop rows that are unusable (no order_id, no quantity, no unit_price)
    before = len(df)
    df = df.dropna(subset=["order_id", "quantity", "unit_price", "order_date"])
    rejected = before - len(df)
    if rejected:
        logger.warning("  %d rows rejected (missing critical fields)", rejected)

    # Select silver columns
    silver_cols = ["order_id", "customer_id", "product_id", "order_date",
                   "quantity", "unit_price", "discount_pct", "channel", "location",
                   "status", "gross_revenue", "discount_amount", "net_sales",
                   "source_file", "run_id", "ingested_at"]
    df = df.rename(columns={"discount": "discount_pct"})
    df = df[[c for c in silver_cols if c in df.columns or c in ("run_id", "ingested_at")]]

    _write_silver(df, "orders", engine, run_id, truncate)
    return len(df)


def transform_customers(engine, run_id: str, truncate: bool = False) -> int:
    logger.info("[customers] Transforming bronze → silver")
    df = pd.read_sql(f"SELECT * FROM {SCHEMA_BRONZE}.customers", engine)

    df["customer_id"]  = _clean_id(df["customer_id"])
    df["email"]        = df["email"].astype(str).str.strip().str.lower()
    df["city"]         = _standardize_text(df.get("city",    pd.Series(dtype=str)))
    df["region"]       = _standardize_text(df.get("region",  pd.Series(dtype=str)))
    df["segment"]      = _standardize_text(df.get("segment", pd.Series(dtype=str)))
    df["signup_date"]  = _to_date(df.get("signup_date", pd.Series(dtype=str)), "signup_date")

    df = df.dropna(subset=["customer_id"])
    df = df.drop_duplicates(subset=["customer_id"], keep="last")

    _write_silver(df[["customer_id","name","email","city","region",
                       "signup_date","segment","source_file"]], "customers", engine, run_id, truncate)
    return len(df)


def transform_products(engine, run_id: str, truncate: bool = False) -> int:
    logger.info("[products] Transforming bronze → silver")
    df = pd.read_sql(f"SELECT * FROM {SCHEMA_BRONZE}.products", engine)

    df["product_id"]    = _clean_id(df["product_id"])
    df["product_name"]  = df["product_name"].astype(str).str.strip()
    df["category"]      = _standardize_text(df.get("category",    pd.Series(dtype=str)))
    df["subcategory"]   = _standardize_text(df.get("subcategory", pd.Series(dtype=str)))
    df["supplier"]      = _standardize_text(df.get("supplier",    pd.Series(dtype=str)))
    df["cost"]          = _to_numeric(df["cost"],          "cost").clip(lower=0)
    df["selling_price"] = _to_numeric(df["selling_price"], "selling_price").clip(lower=0)

    # Derived: margin
    df["margin_pct"] = np.where(
        df["selling_price"] > 0,
        (df["selling_price"] - df["cost"]) / df["selling_price"],
        np.nan,
    )

    df = df.dropna(subset=["product_id"])
    df = df.drop_duplicates(subset=["product_id"], keep="last")

    _write_silver(df[["product_id","product_name","category","subcategory",
                       "supplier","cost","selling_price","margin_pct","source_file"]],
                  "products", engine, run_id, truncate)
    return len(df)


def transform_payments(engine, run_id: str, truncate: bool = False) -> int:
    logger.info("[payments] Transforming bronze → silver")
    df = pd.read_sql(f"SELECT * FROM {SCHEMA_BRONZE}.payments", engine)

    df["payment_id"]     = _clean_id(df["payment_id"])
    df["order_id"]       = _clean_id(df["order_id"])
    df["payment_date"]   = _to_date(df["payment_date"], "payment_date")
    df["payment_method"] = _standardize_text(df.get("payment_method", pd.Series(dtype=str)))
    df["payment_status"] = df.get("payment_status", pd.Series(dtype=str)).astype(str).str.strip().str.upper()
    df["amount"]         = _to_numeric(df["amount"], "amount").clip(lower=0)
    df["failure_reason"] = df.get("failure_reason", pd.Series(dtype=str))

    df = df.dropna(subset=["payment_id", "order_id"])
    df = df.drop_duplicates(subset=["payment_id"], keep="last")

    _write_silver(df[["payment_id","order_id","payment_date","payment_method",
                       "amount","payment_status","failure_reason","source_file"]],
                  "payments", engine, run_id, truncate)
    return len(df)


def transform_returns(engine, run_id: str, truncate: bool = False) -> int:
    logger.info("[returns] Transforming bronze → silver")
    df = pd.read_sql(f"SELECT * FROM {SCHEMA_BRONZE}.returns", engine)

    df["return_id"]        = _clean_id(df["return_id"])
    df["order_id"]         = _clean_id(df["order_id"])
    df["product_id"]       = _clean_id(df["product_id"])
    df["return_date"]      = _to_date(df["return_date"], "return_date")
    df["quantity_returned"]= _to_numeric(df["quantity_returned"], "quantity_returned").clip(lower=0)
    df["return_reason"]    = _standardize_text(df.get("return_reason", pd.Series(dtype=str)))

    df = df.dropna(subset=["return_id", "order_id"])
    df = df.drop_duplicates(subset=["return_id"], keep="last")

    _write_silver(df[["return_id","order_id","product_id","return_date",
                       "quantity_returned","return_reason","source_file"]],
                  "returns", engine, run_id, truncate)
    return len(df)


def transform_inventory(engine, run_id: str, truncate: bool = False) -> int:
    logger.info("[inventory] Transforming bronze → silver")
    df = pd.read_sql(f"SELECT * FROM {SCHEMA_BRONZE}.inventory", engine)

    df["product_id"]      = _clean_id(df["product_id"])
    df["warehouse"]       = _standardize_text(df.get("warehouse", pd.Series(dtype=str)))
    df["snapshot_date"]   = _to_date(df["snapshot_date"], "snapshot_date")
    df["units_available"] = _to_numeric(df["units_available"], "units_available").clip(lower=0)
    df["units_reserved"]  = _to_numeric(df.get("units_reserved", pd.Series(dtype=float)), "units_reserved").clip(lower=0)
    df["units_sold"]      = _to_numeric(df.get("units_sold", pd.Series(dtype=float)), "units_sold").clip(lower=0)

    df = df.dropna(subset=["product_id", "warehouse", "snapshot_date"])

    _write_silver(df[["product_id","warehouse","snapshot_date","units_available",
                       "units_reserved","units_sold","source_file"]],
                  "inventory", engine, run_id, truncate)
    return len(df)


def transform_marketing(engine, run_id: str, truncate: bool = False) -> int:
    logger.info("[marketing] Transforming bronze → silver")
    df = pd.read_sql(f"SELECT * FROM {SCHEMA_BRONZE}.marketing", engine)

    df["campaign_id"]       = _clean_id(df["campaign_id"])
    df["date"]              = _to_date(df["date"], "date")
    df["channel"]           = _standardize_text(df.get("channel", pd.Series(dtype=str)))
    df["spend"]             = _to_numeric(df["spend"], "spend").clip(lower=0)
    df["impressions"]       = _to_numeric(df.get("impressions", pd.Series(dtype=float)), "impressions").clip(lower=0)
    df["clicks"]            = _to_numeric(df.get("clicks", pd.Series(dtype=float)), "clicks").clip(lower=0)
    df["orders_attributed"] = _to_numeric(df.get("orders_attributed", pd.Series(dtype=float)), "orders_attributed").clip(lower=0)
    df["revenue_attributed"]= _to_numeric(df.get("revenue_attributed", pd.Series(dtype=float)), "revenue_attributed").clip(lower=0)

    # Derived: CTR
    df["ctr"] = np.where(
        df["impressions"] > 0,
        df["clicks"] / df["impressions"],
        np.nan,
    )

    df = df.dropna(subset=["campaign_id", "date"])

    _write_silver(df[["campaign_id","date","channel","spend","impressions",
                       "clicks","orders_attributed","revenue_attributed","ctr","source_file"]],
                  "marketing", engine, run_id, truncate)
    return len(df)


# ---------------------------------------------------------------------------
# Main runner
# ---------------------------------------------------------------------------

TRANSFORMERS = {
    "orders":    transform_orders,
    "customers": transform_customers,
    "products":  transform_products,
    "payments":  transform_payments,
    "returns":   transform_returns,
    "inventory": transform_inventory,
    "marketing": transform_marketing,
}


def transform_all(truncate: bool = False) -> dict[str, int]:
    """Run all transformations. Returns {entity: row_count}."""
    run_id = get_run_id()
    engine = get_engine()

    logger.info("=" * 60)
    logger.info("RevenueOS Silver Transformation — Run ID: %s", run_id)
    logger.info("=" * 60)

    results: dict[str, int] = {}
    for entity, fn in TRANSFORMERS.items():
        try:
            results[entity] = fn(engine, run_id, truncate)
        except Exception as exc:
            logger.error("Failed to transform '%s': %s", entity, exc)
            results[entity] = -1

    logger.info("Silver transformation complete: %s", results)
    return results


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="RevenueOS – Silver Transformation")
    parser.add_argument("--entity", choices=list(TRANSFORMERS.keys()), default=None)
    parser.add_argument("--truncate", action="store_true")
    args = parser.parse_args()

    run_id = get_run_id()
    engine = get_engine()

    if args.entity:
        TRANSFORMERS[args.entity](engine, run_id, truncate=args.truncate)
    else:
        transform_all(truncate=args.truncate)
