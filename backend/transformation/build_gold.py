"""
RevenueOS – Gold Layer Builder
=================================
Populates the star schema (dimensions + facts) and gold analytical tables
from silver data.

Execution order:
  1. Dim Date
  2. Dim Customer, Product, Channel, Location, Supplier, Campaign, Payment Method
  3. Fact Orders, Payments, Returns, Inventory, Marketing
  4. Gold: Daily Financials, Customer Health, Product Profitability,
           Revenue Leakage, Inventory Risk, Marketing Efficiency,
           Business Anomalies, Investigation Queue

Usage
-----
    python transformation/build_gold.py            # full build
    python transformation/build_gold.py --step dims  # dimensions only
"""

from __future__ import annotations

import sys
import json
from datetime import datetime, timezone, date, timedelta
from pathlib import Path

import numpy as np
import pandas as pd
from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    SCHEMA_SILVER,
    SCHEMA_GOLD,
    get_engine,
    get_run_id,
    logger,
    DISCOUNT_LEAKAGE_THRESHOLD,
    MARGIN_LEAKAGE_THRESHOLD,
    HIGH_RETURN_RATE_THRESHOLD,
    IQR_MULTIPLIER,
    ZSCORE_THRESHOLD,
    ISO_FOREST_CONTAMINATION,
)


# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def _upsert(df: pd.DataFrame, table: str, engine, schema: str = SCHEMA_GOLD,
            truncate: bool = True) -> None:
    """Write a DataFrame to a gold table (truncate+append pattern)."""
    if df.empty:
        logger.warning("  %s.%s: empty DataFrame, skipping write.", schema, table)
        return
    with engine.begin() as conn:
        if truncate:
            conn.execute(text(f"TRUNCATE TABLE {schema}.{table} CASCADE"))
        df.to_sql(table, con=conn, schema=schema, if_exists="append",
                  index=False, method="multi", chunksize=5000)
    logger.info("  → %s.%s: %d rows", schema, table, len(df))


def _read_silver(engine, table: str) -> pd.DataFrame:
    return pd.read_sql(f"SELECT * FROM {SCHEMA_SILVER}.{table}", engine)


def _read_gold_key_map(engine, table: str, natural_col: str,
                       key_col: str) -> pd.Series:
    """Return a natural-key to surrogate-key mapping from a gold dimension."""
    df = pd.read_sql(
        f"SELECT {natural_col}, {key_col} FROM {SCHEMA_GOLD}.{table}",
        engine,
    )
    return df.dropna(subset=[natural_col]).drop_duplicates(natural_col).set_index(natural_col)[key_col]


def _nullable_int(series: pd.Series) -> pd.Series:
    """Convert mapped surrogate keys to nullable integers for SQL loading."""
    return pd.to_numeric(series, errors="coerce").astype("Int64")


# ---------------------------------------------------------------------------
# Step 1 – Dimension: Date
# ---------------------------------------------------------------------------

def build_dim_date(engine, start: date = date(2020, 1, 1),
                   end: date = date(2027, 12, 31)) -> None:
    logger.info("[dim_date] Building date dimension %s → %s", start, end)
    dates = pd.date_range(start, end, freq="D")
    df = pd.DataFrame({"full_date": dates})
    df["date_key"]      = df["full_date"].dt.strftime("%Y%m%d").astype(int)
    df["year"]          = df["full_date"].dt.year.astype("int16")
    df["quarter"]       = df["full_date"].dt.quarter.astype("int16")
    df["month"]         = df["full_date"].dt.month.astype("int16")
    df["month_name"]    = df["full_date"].dt.strftime("%B")
    df["week"]          = df["full_date"].dt.isocalendar().week.astype("int16")
    df["day_of_week"]   = df["full_date"].dt.dayofweek.astype("int16")
    df["day_name"]      = df["full_date"].dt.strftime("%A")
    df["is_weekend"]    = df["day_of_week"] >= 5
    df["fiscal_year"]   = df["year"]
    df["fiscal_quarter"]= df["quarter"].astype("int16")
    df["full_date"]     = df["full_date"].dt.date

    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE gold.dim_date CASCADE"))
        df.to_sql("dim_date", con=conn, schema=SCHEMA_GOLD,
                  if_exists="append", index=False, method="multi", chunksize=5000)
    logger.info("  dim_date: %d rows", len(df))


# ---------------------------------------------------------------------------
# Step 2 – Other Dimensions
# ---------------------------------------------------------------------------

def build_dim_customer(engine) -> pd.DataFrame:
    logger.info("[dim_customer] Building")
    df = _read_silver(engine, "customers")
    dim = df[["customer_id","name","email","city","region","signup_date","segment"]].copy()
    dim = dim.drop_duplicates("customer_id")
    _upsert(dim, "dim_customer", engine)
    return dim


def build_dim_product(engine) -> pd.DataFrame:
    logger.info("[dim_product] Building")
    df = _read_silver(engine, "products")
    dim = df[["product_id","product_name","category","subcategory",
              "supplier","cost","selling_price","margin_pct"]].copy()
    dim = dim.drop_duplicates("product_id")
    _upsert(dim, "dim_product", engine)
    return dim


def build_dim_channel(engine, orders_df: pd.DataFrame) -> None:
    logger.info("[dim_channel] Building")
    channels = orders_df["channel"].dropna().unique()
    dim = pd.DataFrame({"channel_name": sorted(channels)})
    _upsert(dim, "dim_channel", engine)


def build_dim_location(engine, orders_df: pd.DataFrame) -> None:
    logger.info("[dim_location] Building")
    locations = orders_df["location"].dropna().unique()
    # Simplified: location_name → extract region by last word
    df_loc = pd.DataFrame({"location_name": sorted(locations)})
    df_loc["region"] = df_loc["location_name"].str.split().str[-1]
    _upsert(df_loc, "dim_location", engine)


def build_dim_supplier(engine, products_df: pd.DataFrame) -> None:
    logger.info("[dim_supplier] Building")
    suppliers = products_df["supplier"].dropna().unique()
    dim = pd.DataFrame({"supplier_name": sorted(suppliers)})
    _upsert(dim, "dim_supplier", engine)


def build_dim_campaign(engine, marketing_df: pd.DataFrame) -> None:
    logger.info("[dim_campaign] Building")
    df = marketing_df[["campaign_id","channel"]].drop_duplicates("campaign_id")
    _upsert(df, "dim_campaign", engine)


def build_dim_payment_method(engine, payments_df: pd.DataFrame) -> None:
    logger.info("[dim_payment_method] Building")
    methods = payments_df["payment_method"].dropna().unique()
    dim = pd.DataFrame({"method_name": sorted(methods)})
    _upsert(dim, "dim_payment_method", engine)


# ---------------------------------------------------------------------------
# Step 3 – Fact Tables
# ---------------------------------------------------------------------------

def _date_key(series: pd.Series) -> pd.Series:
    """Convert a date series to integer date_key (YYYYMMDD)."""
    return pd.to_datetime(series, errors="coerce").dt.strftime("%Y%m%d").astype("Int64")


def build_fact_orders(engine, orders: pd.DataFrame,
                      products: pd.DataFrame) -> pd.DataFrame:
    logger.info("[fact_orders] Building")

    # Join product cost for COGS
    cost_map = products.set_index("product_id")["cost"]
    customer_key_map = _read_gold_key_map(engine, "dim_customer", "customer_id", "customer_key")
    product_key_map = _read_gold_key_map(engine, "dim_product", "product_id", "product_key")
    channel_key_map = _read_gold_key_map(engine, "dim_channel", "channel_name", "channel_key")
    location_key_map = _read_gold_key_map(engine, "dim_location", "location_name", "location_key")

    orders = orders.copy()
    orders["cogs"] = orders["quantity"] * orders["product_id"].map(cost_map)
    orders["gross_profit"] = orders["net_sales"] - orders["cogs"]
    orders["gross_margin_pct"] = np.where(
        orders["net_sales"] > 0,
        orders["gross_profit"] / orders["net_sales"],
        np.nan,
    )
    orders["date_key"] = _date_key(orders["order_date"])
    orders["customer_key"] = _nullable_int(orders["customer_id"].map(customer_key_map))
    orders["product_key"] = _nullable_int(orders["product_id"].map(product_key_map))
    orders["channel_key"] = _nullable_int(orders["channel"].map(channel_key_map)) if "channel" in orders.columns else pd.Series(index=orders.index, dtype="Int64")
    orders["location_key"] = _nullable_int(orders["location"].map(location_key_map)) if "location" in orders.columns else pd.Series(index=orders.index, dtype="Int64")

    fact = orders.rename(columns={"discount": "discount_pct"}).copy()
    fact_cols = ["order_id","date_key","customer_key","product_key",
                 "channel_key","location_key","status","quantity","unit_price","discount_pct",
                 "gross_revenue","discount_amount","net_sales",
                 "cogs","gross_profit","gross_margin_pct","run_id"]
    fact = fact[[c for c in fact_cols if c in fact.columns]]

    _upsert(fact, "fact_orders", engine)
    return fact


def build_fact_payments(engine, payments: pd.DataFrame) -> None:
    logger.info("[fact_payments] Building")
    payment_method_key_map = _read_gold_key_map(
        engine, "dim_payment_method", "method_name", "payment_method_key"
    )
    df = payments.copy()
    df["date_key"] = _date_key(df["payment_date"])
    df["payment_method_key"] = _nullable_int(df["payment_method"].map(payment_method_key_map))
    fact_cols = ["payment_id","order_id","date_key","payment_method_key",
                 "amount","payment_status","failure_reason","run_id"]
    df = df[[c for c in fact_cols if c in df.columns]]
    _upsert(df, "fact_payments", engine)


def build_fact_returns(engine, returns: pd.DataFrame,
                       orders: pd.DataFrame) -> pd.DataFrame:
    logger.info("[fact_returns] Building")
    # Look up unit_price from orders to calculate return_value
    price_map = orders.groupby("order_id")["unit_price"].first()
    product_key_map = _read_gold_key_map(engine, "dim_product", "product_id", "product_key")
    df = returns.copy()
    df["unit_price"]   = df["order_id"].map(price_map)
    df["return_value"] = df["quantity_returned"] * df["unit_price"]
    df["date_key"]     = _date_key(df["return_date"])
    df["product_key"]  = _nullable_int(df["product_id"].map(product_key_map))
    fact_cols = ["return_id","order_id","date_key","product_key",
                 "quantity_returned","return_reason","return_value","run_id"]
    df = df[[c for c in fact_cols if c in df.columns]]
    _upsert(df, "fact_returns", engine)
    return df


def build_fact_inventory(engine, inventory: pd.DataFrame,
                         products: pd.DataFrame) -> None:
    logger.info("[fact_inventory] Building")
    cost_map = products.set_index("product_id")["cost"]
    product_key_map = _read_gold_key_map(engine, "dim_product", "product_id", "product_key")
    supplier_key_map = _read_gold_key_map(engine, "dim_supplier", "supplier_name", "supplier_key")
    supplier_map = products.set_index("product_id")["supplier"] if "supplier" in products.columns else pd.Series(dtype=object)
    df = inventory.copy()
    df["inventory_value"] = df["units_available"] * df["product_id"].map(cost_map)
    df["is_stockout"]     = df["units_available"] == 0
    df["date_key"]        = _date_key(df["snapshot_date"])
    df["product_key"]     = _nullable_int(df["product_id"].map(product_key_map))
    df["supplier_key"]    = _nullable_int(df["product_id"].map(supplier_map).map(supplier_key_map)) if not supplier_map.empty else pd.Series(index=df.index, dtype="Int64")
    fact_cols = ["date_key","product_key","supplier_key","warehouse","units_available",
                 "units_reserved","units_sold","inventory_value","is_stockout","run_id"]
                 "units_reserved","units_sold","inventory_value","is_stockout","run_id"]
    df = df[[c for c in fact_cols if c in df.columns]]
    _upsert(df, "fact_inventory", engine)


def build_fact_marketing(engine, marketing: pd.DataFrame) -> None:
    logger.info("[fact_marketing] Building")
    campaign_key_map = _read_gold_key_map(engine, "dim_campaign", "campaign_id", "campaign_key")
    df = marketing.copy()
    df["conversion_rate"] = np.where(
        df["clicks"] > 0, df["orders_attributed"] / df["clicks"], np.nan
    )
    df["roas"] = np.where(
        df["spend"] > 0, df["revenue_attributed"] / df["spend"], np.nan
    )
    df["date_key"] = _date_key(df["date"])
    df["campaign_key"] = _nullable_int(df["campaign_id"].map(campaign_key_map))
    fact_cols = ["date_key","campaign_key","spend","impressions","clicks",
                 "orders_attributed","revenue_attributed","ctr",
                 "conversion_rate","roas","run_id"]
    df = df[[c for c in fact_cols if c in df.columns]]
    _upsert(df, "fact_marketing", engine)


# ---------------------------------------------------------------------------
# Step 4 – Gold Analytical Tables
# ---------------------------------------------------------------------------

def build_gold_daily_financials(engine, orders: pd.DataFrame,
                                returns: pd.DataFrame, run_id: str) -> None:
    logger.info("[gold_daily_financials] Building")
    df = orders.copy()
    df["order_date"] = pd.to_datetime(df["order_date"], errors="coerce").dt.date

    # Aggregate returns by order → product
    ret = returns.copy()
    ret["return_date"] = pd.to_datetime(ret["return_date"], errors="coerce").dt.date
    ret_agg = ret.groupby("order_id")["return_value"].sum().reset_index()
    df = df.merge(ret_agg, on="order_id", how="left")
    df["return_value"] = df["return_value"].fillna(0)
    df["net_revenue"]  = df["net_sales"] - df["return_value"]
    df["gross_profit"] = df["net_revenue"] - df["cogs"].fillna(0)

    agg = df.groupby(["order_date","channel","location"]).agg(
        gross_revenue=("gross_revenue", "sum"),
        discount_amount=("discount_amount","sum"),
        net_sales=("net_sales","sum"),
        return_value=("return_value","sum"),
        net_revenue=("net_revenue","sum"),
        cogs=("cogs","sum"),
        gross_profit=("gross_profit","sum"),
        order_count=("order_id","nunique"),
        units_sold=("quantity","sum"),
    ).reset_index()

    agg["gross_margin_pct"] = np.where(
        agg["net_revenue"] > 0, agg["gross_profit"] / agg["net_revenue"], np.nan
    )
    agg["avg_order_value"] = np.where(
        agg["order_count"] > 0, agg["net_revenue"] / agg["order_count"], np.nan
    )
    agg = agg.rename(columns={"order_date": "report_date",
                               "location": "region"})
    agg["category"] = "All"
    agg["run_id"]   = run_id

    with engine.begin() as conn:
        conn.execute(text("TRUNCATE TABLE gold.gold_daily_financials"))
        agg.to_sql("gold_daily_financials", con=conn, schema=SCHEMA_GOLD,
                   if_exists="append", index=False, method="multi", chunksize=5000)
    logger.info("  gold_daily_financials: %d rows", len(agg))


def build_gold_product_profitability(engine, orders: pd.DataFrame,
                                     returns: pd.DataFrame,
                                     inventory: pd.DataFrame,
                                     products: pd.DataFrame,
                                     run_id: str) -> pd.DataFrame:
    logger.info("[gold_product_profitability] Building")
    ord_agg = orders.groupby("product_id").agg(
        revenue=("net_sales","sum"),
        units_sold=("quantity","sum"),
        discount_amount=("discount_amount","sum"),
        cogs=("cogs","sum"),
        order_count=("order_id","count"),
    ).reset_index()

    ret_agg = returns.groupby("product_id")["return_value"].sum().reset_index()
    ret_units = returns.groupby("product_id")["quantity_returned"].sum().reset_index()

    inv_agg = inventory.groupby("product_id").agg(
        units_in_inventory=("units_available","mean"),
        stockout_days=("is_stockout","sum") if "is_stockout" in inventory.columns else ("units_available", lambda x: (x == 0).sum()),
    ).reset_index()

    df = ord_agg.merge(ret_agg, on="product_id", how="left")
    df = df.merge(ret_units, on="product_id", how="left")
    df = df.merge(inv_agg, on="product_id", how="left")
    df = df.merge(
        products[["product_id","product_name","category","subcategory","supplier"]],
        on="product_id", how="left",
    )

    df["return_value"] = df["return_value"].fillna(0)
    df["quantity_returned"] = df["quantity_returned"].fillna(0)
    df["gross_profit"] = df["revenue"] - df["cogs"].fillna(0) - df["return_value"]
    df["gross_margin_pct"] = np.where(
        df["revenue"] > 0, df["gross_profit"] / df["revenue"], np.nan
    )
    df["return_rate"] = np.where(
        df["units_sold"] > 0, df["quantity_returned"] / df["units_sold"], np.nan
    )

    # Product classification
    rev_median = df["revenue"].median()
    margin_median = df["gross_margin_pct"].median()

    def classify(row):
        high_rev = row["revenue"] >= rev_median
        high_margin = (row["gross_margin_pct"] or 0) >= margin_median
        low_inv_turnover = (row.get("units_in_inventory", 0) or 0) > 0 and (row["units_sold"] or 0) == 0
        if low_inv_turnover:
            return "Dead Stock Candidate"
        if high_rev and high_margin:
            return "Revenue Winner"
        if high_rev and not high_margin:
            return "Revenue Trap"
        if not high_rev and high_margin:
            return "Hidden Winner"
        return "Low Priority"

    df["classification"] = df.apply(classify, axis=1)
    df["run_id"]         = run_id
    df["computed_at"]    = datetime.now(timezone.utc).isoformat()

    _upsert(df, "gold_product_profitability", engine)
    return df


def build_gold_customer_health(engine, orders: pd.DataFrame,
                               returns: pd.DataFrame,
                               payments: pd.DataFrame,
                               customers: pd.DataFrame,
                               run_id: str) -> None:
    logger.info("[gold_customer_health] Building")
    today = pd.Timestamp.now().normalize()

    # Base order metrics
    ord_agg = orders.groupby("customer_id").agg(
        total_revenue=("net_sales","sum"),
        total_cogs=("cogs","sum"),
        order_count=("order_id","nunique"),
        total_discount=("discount_amount","sum"),
        last_order_date=("order_date","max"),
        units_sold=("quantity","sum"),
    ).reset_index()

    # Return metrics per customer via order → customer join
    ret_merged = returns.merge(
        orders[["order_id","customer_id"]].drop_duplicates(), on="order_id", how="left"
    )
    ret_agg = ret_merged.groupby("customer_id").agg(
        total_return_value=("return_value","sum"),
        quantity_returned=("quantity_returned","sum"),
    ).reset_index()

    # Payment failure rate
    pay_merged = payments.merge(
        orders[["order_id","customer_id"]].drop_duplicates(), on="order_id", how="left"
    )
    pay_agg = pay_merged.groupby("customer_id").agg(
        total_payments=("payment_id","count"),
        failed_payments=("payment_status", lambda x: (x == "FAILED").sum()),
    ).reset_index()
    pay_agg["payment_fail_rate"] = pay_agg["failed_payments"] / pay_agg["total_payments"].replace(0, np.nan)

    # Recent trend (last 30d vs prev 30d)
    orders["order_date"] = pd.to_datetime(orders["order_date"], errors="coerce")
    last_30 = today - pd.Timedelta(days=30)
    prev_30 = today - pd.Timedelta(days=60)
    rev_last = orders[orders["order_date"] >= last_30].groupby("customer_id")["net_sales"].sum()
    rev_prev = orders[(orders["order_date"] >= prev_30) & (orders["order_date"] < last_30)].groupby("customer_id")["net_sales"].sum()

    # Combine
    df = ord_agg.merge(ret_agg, on="customer_id", how="left")
    df = df.merge(pay_agg[["customer_id","payment_fail_rate"]], on="customer_id", how="left")
    df = df.merge(customers[["customer_id","name","segment","region"]], on="customer_id", how="left")

    df["total_return_value"] = df["total_return_value"].fillna(0)
    df["quantity_returned"]  = df["quantity_returned"].fillna(0)
    df["total_gross_profit"] = df["total_revenue"] - df["total_cogs"].fillna(0) - df["total_return_value"]
    df["gross_margin_pct"]   = np.where(df["total_revenue"] > 0,
                                         df["total_gross_profit"] / df["total_revenue"], np.nan)
    df["return_rate"]        = np.where(df["units_sold"] > 0,
                                         df["quantity_returned"] / df["units_sold"], np.nan)
    df["discount_dependency"]= np.where(df["total_revenue"] > 0,
                                         df["total_discount"] / df["total_revenue"], np.nan)
    df["avg_order_value"]    = df["total_revenue"] / df["order_count"].replace(0, np.nan)

    df["last_order_date"]    = pd.to_datetime(df["last_order_date"], errors="coerce")
    df["days_since_last_order"] = (today - df["last_order_date"]).dt.days

    df["revenue_last_30d"]   = df["customer_id"].map(rev_last).fillna(0)
    df["revenue_prev_30d"]   = df["customer_id"].map(rev_prev).fillna(0)
    df["revenue_trend_pct"]  = np.where(
        df["revenue_prev_30d"] > 0,
        (df["revenue_last_30d"] - df["revenue_prev_30d"]) / df["revenue_prev_30d"],
        np.nan,
    )

    # Scoring (0–1 normalized)
    def _norm(s: pd.Series) -> pd.Series:
        rng = s.max() - s.min()
        return (s - s.min()) / rng if rng > 0 else pd.Series(0.5, index=s.index)

    df["recency_score"]       = 1 - _norm(df["days_since_last_order"].fillna(365))
    df["frequency_score"]     = _norm(df["order_count"])
    df["monetary_score"]      = _norm(df["total_revenue"])
    df["profitability_score"] = _norm(df["gross_margin_pct"].fillna(0))
    df["trend_score"]         = _norm(df["revenue_trend_pct"].fillna(0))
    df["behavior_score"]      = 1 - _norm(df["return_rate"].fillna(0))

    df["health_score"] = (
        0.20 * df["recency_score"] +
        0.15 * df["frequency_score"] +
        0.25 * df["monetary_score"] +
        0.20 * df["profitability_score"] +
        0.10 * df["trend_score"] +
        0.10 * df["behavior_score"]
    )

    def tier(score):
        if score >= 0.70: return "HIGH"
        if score >= 0.45: return "MEDIUM"
        if score >= 0.25: return "LOW"
        return "AT-RISK"

    df["health_tier"]    = df["health_score"].apply(tier)
    df["run_id"]         = run_id
    df["computed_at"]    = datetime.now(timezone.utc).isoformat()

    df = df.rename(columns={"name": "customer_name"})
    cols = ["customer_id","customer_name","segment","region","total_revenue",
            "total_gross_profit","gross_margin_pct","order_count","avg_order_value",
            "return_rate","discount_dependency","payment_fail_rate",
            "days_since_last_order","revenue_last_30d","revenue_prev_30d",
            "revenue_trend_pct","recency_score","frequency_score","monetary_score",
            "profitability_score","trend_score","behavior_score","health_score",
            "health_tier","run_id","computed_at"]
    df = df[[c for c in cols if c in df.columns]]

    _upsert(df, "gold_customer_health", engine)


def build_gold_revenue_leakage(engine, orders: pd.DataFrame,
                               returns: pd.DataFrame,
                               payments: pd.DataFrame,
                               run_id: str) -> None:
    logger.info("[gold_revenue_leakage] Building")
    rows = []

    # 1. Discount leakage
    disc = orders[orders["discount_pct"] > DISCOUNT_LEAKAGE_THRESHOLD].copy()
    if not disc.empty:
        disc["margin_pct"] = np.where(disc["net_sales"] > 0,
                                       (disc["net_sales"] - disc.get("cogs", 0)) / disc["net_sales"],
                                       np.nan)
        leaky = disc[disc["margin_pct"] < MARGIN_LEAKAGE_THRESHOLD]
        rows.append({
            "run_id": run_id, "leakage_type": "Discounts",
            "entity_type": "Product", "entity_id": None, "entity_name": "Multiple",
            "estimated_impact": float(leaky["discount_amount"].sum()),
            "leakage_rate": float(disc["discount_pct"].mean()),
            "supporting_metric": "avg_discount_pct",
            "supporting_value": float(disc["discount_pct"].mean()),
            "threshold_used": DISCOUNT_LEAKAGE_THRESHOLD,
            "is_estimate": True,
        })

    # 2. Return leakage
    if not returns.empty:
        total_return_val = float(returns["return_value"].sum())
        rows.append({
            "run_id": run_id, "leakage_type": "Returns",
            "entity_type": "All", "entity_id": None, "entity_name": "All Products",
            "estimated_impact": total_return_val,
            "leakage_rate": len(returns) / max(len(orders), 1),
            "supporting_metric": "return_value",
            "supporting_value": total_return_val,
            "threshold_used": HIGH_RETURN_RATE_THRESHOLD,
            "is_estimate": True,
        })

    # 3. Payment failure leakage
    if not payments.empty:
        failed = payments[payments["payment_status"] == "FAILED"]
        rows.append({
            "run_id": run_id, "leakage_type": "Payment Failure",
            "entity_type": "Payment", "entity_id": None, "entity_name": "Failed Payments",
            "estimated_impact": float(failed["amount"].sum()),
            "leakage_rate": len(failed) / max(len(payments), 1),
            "supporting_metric": "failed_payment_amount",
            "supporting_value": float(failed["amount"].sum()),
            "threshold_used": None,
            "is_estimate": True,
        })

    # 4. Low margin leakage
    low_margin = orders[orders.get("gross_margin_pct", pd.Series()) < MARGIN_LEAKAGE_THRESHOLD]
    if not low_margin.empty:
        rows.append({
            "run_id": run_id, "leakage_type": "Low Margin",
            "entity_type": "Order", "entity_id": None, "entity_name": "Low-Margin Orders",
            "estimated_impact": float(low_margin["gross_profit"].sum()) if "gross_profit" in low_margin else 0,
            "leakage_rate": len(low_margin) / max(len(orders), 1),
            "supporting_metric": "orders_below_margin_threshold",
            "supporting_value": len(low_margin),
            "threshold_used": MARGIN_LEAKAGE_THRESHOLD,
            "is_estimate": True,
        })

    if rows:
        df = pd.DataFrame(rows)
        df["computed_at"] = datetime.now(timezone.utc).isoformat()
        _upsert(df, "gold_revenue_leakage", engine)


def build_gold_inventory_risk(engine, inventory: pd.DataFrame, products: pd.DataFrame,
                              orders: pd.DataFrame, run_id: str) -> None:
    logger.info("[gold_inventory_risk] Building")
    if inventory.empty:
        return

    inv = inventory.copy()
    inv["snapshot_date"] = pd.to_datetime(inv["snapshot_date"]).dt.date
    # Get latest snapshot per product and warehouse
    latest_idx = inv.groupby(["product_id", "warehouse"])["snapshot_date"].idxmax()
    latest = inv.loc[latest_idx].copy()

    # Join product metadata
    prod_meta = products.set_index("product_id")[["product_name", "category", "supplier", "cost", "selling_price"]]
    latest = latest.join(prod_meta, on="product_id")

    # Inventory value
    latest["inventory_value"] = latest["units_available"] * latest["cost"].fillna(0)

    # Historical stats per product-warehouse
    hist = inv.groupby(["product_id", "warehouse"]).agg(
        stockout_days=("is_stockout", "sum"),
        total_units_sold=("units_sold", "sum"),
    ).reset_index()

    df = pd.merge(latest, hist, on=["product_id", "warehouse"], how="left")

    # Sales velocity from orders
    if not orders.empty:
        comp_orders = orders[orders["status"] != "CANCELLED"]
        sales_vel = comp_orders.groupby("product_id").agg(
            total_qty=("quantity", "sum"),
            distinct_days=("order_date", "nunique"),
        ).reset_index()
        sales_vel["avg_daily_demand"] = sales_vel["total_qty"] / sales_vel["distinct_days"].replace(0, np.nan)
        df = pd.merge(df, sales_vel[["product_id", "avg_daily_demand"]], on="product_id", how="left")
    else:
        df["avg_daily_demand"] = 0

    df["avg_daily_demand"] = df["avg_daily_demand"].fillna(0)
    df["stockout_days"] = df["stockout_days"].fillna(0).astype(int)

    # Days of inventory
    df["days_of_inventory"] = np.where(df["avg_daily_demand"] > 0,
                                       (df["units_available"] / df["avg_daily_demand"]).round(1), np.nan)

    # Inventory turnover (annualized)
    df["inventory_turnover"] = np.where(df["units_available"] > 0,
                                        ((df["avg_daily_demand"] * 365) / df["units_available"]).round(2), np.nan)

    # Sell-through rate
    total_avail_sold = df["units_available"] + df["total_units_sold"].fillna(0)
    df["sell_through_rate"] = np.where(total_avail_sold > 0,
                                       (df["total_units_sold"].fillna(0) / total_avail_sold).round(4), np.nan)

    # Estimated stockout impact: stockout_days * avg_daily_demand * selling_price
    df["estimated_stockout_impact"] = (df["stockout_days"] * df["avg_daily_demand"] * df["selling_price"].fillna(0)).round(2)

    # Dead stock
    df["is_dead_stock"] = (df["units_available"] > 0) & (df["total_units_sold"].fillna(0) == 0)

    # Risk tier
    def _risk_tier(row):
        if row["units_available"] == 0:
            return "HIGH - Stockout"
        doi = row["days_of_inventory"]
        if pd.notna(doi) and doi < 7:
            return "HIGH - Low Stock"
        if row["is_dead_stock"]:
            return "MEDIUM - Dead Stock"
        if pd.notna(doi) and doi <= 30:
            return "MEDIUM - Watch"
        return "LOW"

    df["risk_tier"] = df.apply(_risk_tier, axis=1)
    df["run_id"] = run_id
    df["computed_at"] = datetime.now(timezone.utc).isoformat()

    cols = [
        "product_id", "warehouse", "snapshot_date", "product_name", "category", "supplier",
        "units_available", "inventory_value", "stockout_days", "days_of_inventory",
        "inventory_turnover", "sell_through_rate", "estimated_stockout_impact",
        "is_dead_stock", "risk_tier", "run_id", "computed_at"
    ]
    _upsert(df[cols], "gold_inventory_risk", engine)


def build_gold_marketing_efficiency(engine, marketing: pd.DataFrame, orders: pd.DataFrame,
                                    run_id: str) -> None:
    logger.info("[gold_marketing_efficiency] Building")
    if marketing.empty:
        return

    mkt = marketing.copy()
    mkt["date"] = pd.to_datetime(mkt["date"]).dt.date

    agg = mkt.groupby(["campaign_id", "channel"]).agg(
        period_start=("date", "min"),
        period_end=("date", "max"),
        spend=("spend", "sum"),
        impressions=("impressions", "sum"),
        clicks=("clicks", "sum"),
        orders_attributed=("orders_attributed", "sum"),
        revenue_attributed=("revenue_attributed", "sum"),
    ).reset_index()

    # Channel profit margin estimation from orders
    if not orders.empty and "gross_profit" in orders.columns and "net_sales" in orders.columns:
        tot_net = orders["net_sales"].sum()
        overall_margin = (orders["gross_profit"].sum() / tot_net) if tot_net > 0 else 0.25
    else:
        overall_margin = 0.25

    agg["gross_profit"] = (agg["revenue_attributed"] * overall_margin).round(2)
    agg["ctr"] = np.where(agg["impressions"] > 0, (agg["clicks"] / agg["impressions"]).round(6), np.nan)
    agg["conversion_rate"] = np.where(agg["clicks"] > 0, (agg["orders_attributed"] / agg["clicks"]).round(6), np.nan)
    agg["cac"] = np.where(agg["orders_attributed"] > 0, (agg["spend"] / agg["orders_attributed"]).round(2), np.nan)
    agg["roas"] = np.where(agg["spend"] > 0, (agg["revenue_attributed"] / agg["spend"]).round(2), np.nan)
    agg["contribution_after_marketing"] = (agg["gross_profit"] - agg["spend"]).round(2)

    def _tier(roas):
        if pd.isna(roas):
            return "Unknown"
        if roas >= 4.0:
            return "Strong"
        if roas >= 2.5:
            return "Average"
        if roas >= 1.0:
            return "Weak"
        return "Loss-Making"

    agg["efficiency_tier"] = agg["roas"].apply(_tier)
    agg["run_id"] = run_id
    agg["computed_at"] = datetime.now(timezone.utc).isoformat()

    cols = [
        "campaign_id", "period_start", "period_end", "channel", "spend", "impressions",
        "clicks", "orders_attributed", "revenue_attributed", "gross_profit", "ctr",
        "conversion_rate", "cac", "roas", "contribution_after_marketing",
        "efficiency_tier", "run_id", "computed_at"
    ]
    _upsert(agg[cols], "gold_marketing_efficiency", engine)


def build_gold_anomalies(engine, orders: pd.DataFrame, run_id: str) -> pd.DataFrame:
    """IQR-based anomaly detection on key order metrics."""
    logger.info("[gold_business_anomalies] Detecting anomalies")
    try:
        from scipy import stats as scipy_stats
    except ImportError:
        scipy_stats = None

    anomalies = []
    now_ts = datetime.now(timezone.utc).isoformat()

    for metric in ["gross_revenue", "discount_pct", "quantity"]:
        if metric not in orders.columns:
            continue
        series = pd.to_numeric(orders[metric], errors="coerce").dropna()
        if series.empty:
            continue

        q1, q3 = series.quantile(0.25), series.quantile(0.75)
        iqr = q3 - q1
        lower = q1 - IQR_MULTIPLIER * iqr
        upper = q3 + IQR_MULTIPLIER * iqr
        outliers = orders[(pd.to_numeric(orders[metric], errors="coerce") < lower) |
                           (pd.to_numeric(orders[metric], errors="coerce") > upper)]

        for _, row in outliers.head(50).iterrows():
            anomalies.append({
                "detected_at": now_ts,
                "run_id": run_id,
                "entity_type": "Order",
                "entity_id": row.get("order_id"),
                "metric": metric,
                "observed_value": row.get(metric),
                "baseline_value": float(series.median()),
                "deviation_pct": (row.get(metric, 0) - series.median()) / max(abs(series.median()), 1),
                "severity": "HIGH" if abs(row.get(metric, 0) - series.median()) > 3 * iqr else "MEDIUM",
                "estimated_financial_impact": abs(row.get("gross_revenue", 0) - series.median()) if metric == "gross_revenue" else None,
                "detection_method": "IQR",
                "status": "OPEN",
            })

    if anomalies:
        df = pd.DataFrame(anomalies)
        _upsert(df, "gold_business_anomalies", engine)
        return df
    return pd.DataFrame()


def build_gold_investigation_queue(engine, anomalies_df: pd.DataFrame,
                                   product_prof: pd.DataFrame,
                                   run_id: str) -> None:
    logger.info("[gold_investigation_queue] Building")
    rows = []
    now_ts = datetime.now(timezone.utc).isoformat()

    # From anomalies
    for _, a in anomalies_df.iterrows():
        impact = a.get("estimated_financial_impact") or 0
        rows.append({
            "created_at": now_ts,
            "run_id": run_id,
            "priority": a.get("severity", "MEDIUM"),
            "priority_score": abs(impact),
            "entity_type": a.get("entity_type", "Order"),
            "entity_id": a.get("entity_id"),
            "entity_name": str(a.get("entity_id")),
            "issue": f"Anomaly detected in {a.get('metric')}",
            "metric": a.get("metric"),
            "observed_value": a.get("observed_value"),
            "baseline_value": a.get("baseline_value"),
            "estimated_impact": impact,
            "possible_drivers": json.dumps(["Unusual value detected by IQR method"]),
            "recommended_investigation": f"Review {a.get('entity_type')} {a.get('entity_id')} for {a.get('metric')} anomaly",
            "confidence": "MEDIUM",
            "evidence_summary": f"Observed: {a.get('observed_value'):.2f}, Baseline: {a.get('baseline_value'):.2f}, Deviation: {a.get('deviation_pct', 0):.1%}",
            "status": "OPEN",
        })

    # From product profitability – Revenue Traps
    if not product_prof.empty:
        traps = product_prof[product_prof["classification"] == "Revenue Trap"]
        for _, p in traps.iterrows():
            rows.append({
                "created_at": now_ts,
                "run_id": run_id,
                "priority": "HIGH",
                "priority_score": float(p.get("revenue", 0)),
                "entity_type": "Product",
                "entity_id": p.get("product_id"),
                "entity_name": p.get("product_name"),
                "issue": "Revenue Trap: High revenue, low margin",
                "metric": "gross_margin_pct",
                "observed_value": p.get("gross_margin_pct"),
                "baseline_value": product_prof["gross_margin_pct"].median(),
                "estimated_impact": float(p.get("gross_profit", 0)),
                "possible_drivers": json.dumps(["High discounting", "High return rate", "Elevated COGS"]),
                "recommended_investigation": "Review pricing, discount strategy, and return behavior for this product",
                "confidence": "MEDIUM",
                "evidence_summary": f"Revenue: {p.get('revenue', 0):,.0f} | Margin: {p.get('gross_margin_pct', 0):.1%}",
                "status": "OPEN",
            })

    if rows:
        df = pd.DataFrame(rows)
        _upsert(df, "gold_investigation_queue", engine)


# ---------------------------------------------------------------------------
# Main orchestrator
# ---------------------------------------------------------------------------

def build_gold(step: str | None = None) -> None:
    run_id = get_run_id()
    engine = get_engine()

    logger.info("=" * 60)
    logger.info("RevenueOS Gold Build — Run ID: %s", run_id)
    logger.info("=" * 60)

    # Load silver data once
    orders    = _read_silver(engine, "orders")
    customers = _read_silver(engine, "customers")
    products  = _read_silver(engine, "products")
    payments  = _read_silver(engine, "payments")
    returns   = _read_silver(engine, "returns")
    inventory = _read_silver(engine, "inventory")
    marketing = _read_silver(engine, "marketing")

    if step in (None, "dims"):
        build_dim_date(engine)
        build_dim_customer(engine)
        build_dim_product(engine)
        if "channel" in orders.columns:
            build_dim_channel(engine, orders)
        if "location" in orders.columns:
            build_dim_location(engine, orders)
        if "supplier" in products.columns:
            build_dim_supplier(engine, products)
        if not marketing.empty:
            build_dim_campaign(engine, marketing)
        if not payments.empty:
            build_dim_payment_method(engine, payments)

    if step in (None, "facts"):
        fact_orders = build_fact_orders(engine, orders, products)
        build_fact_payments(engine, payments)
        fact_returns = build_fact_returns(engine, returns, orders)
        # Attach is_stockout for inventory
        inventory["is_stockout"] = inventory["units_available"] == 0
        build_fact_inventory(engine, inventory, products)
        build_fact_marketing(engine, marketing)

    if step in (None, "gold"):
        # Re-compute fact_orders for the analytical layer
        cost_map = products.set_index("product_id")["cost"]
        orders["cogs"]          = orders["quantity"] * orders["product_id"].map(cost_map)
        orders["gross_profit"]  = orders["net_sales"] - orders["cogs"].fillna(0)
        orders["gross_margin_pct"] = np.where(orders["net_sales"] > 0,
                                               orders["gross_profit"] / orders["net_sales"], np.nan)
        returns_with_val = returns.copy()
        price_map = orders.groupby("order_id")["unit_price"].first()
        returns_with_val["unit_price"]   = returns_with_val["order_id"].map(price_map)
        returns_with_val["return_value"] = returns_with_val["quantity_returned"] * returns_with_val["unit_price"].fillna(0)

        build_gold_daily_financials(engine, orders, returns_with_val, run_id)
        prod_prof = build_gold_product_profitability(engine, orders, returns_with_val,
                                                      inventory, products, run_id)
        build_gold_customer_health(engine, orders, returns_with_val, payments,
                                   customers, run_id)
        build_gold_revenue_leakage(engine, orders, returns_with_val, payments, run_id)
        build_gold_inventory_risk(engine, inventory, products, orders, run_id)
        build_gold_marketing_efficiency(engine, marketing, orders, run_id)
        anomalies_df = build_gold_anomalies(engine, orders, run_id)
        build_gold_investigation_queue(engine, anomalies_df, prod_prof, run_id)

    logger.info("Gold build complete.")


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="RevenueOS – Gold Layer Builder")
    parser.add_argument("--step", choices=["dims", "facts", "gold"], default=None,
                        help="Run a specific step only. Omit for full build.")
    args = parser.parse_args()
    build_gold(step=args.step)
