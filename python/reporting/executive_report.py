"""
RevenueOS – Automated Executive Financial & Decision Briefing Generator
========================================================================
Compiles comprehensive executive reports in Markdown and clean HTML from
Gold star schema tables:
  1. Executive Financial Summary (Full Gross-to-Net Waterfall & Margins)
  2. Revenue Leakage Radar (Quantified losses across 6 commercial mechanisms)
  3. Product Profitability Quadrants & Revenue Traps
  4. Customer Health & Retention Trajectory
  5. Top Prioritized Investigation Queue Action Items

Usage:
  python python/reporting/executive_report.py [--output reports/executive_briefing.md]
"""

from __future__ import annotations

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, Dict, Any

import pandas as pd
from sqlalchemy import text

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config import SCHEMA_GOLD, get_engine, logger
from python.reporting.investigation_copilot import InvestigationCopilot


def fetch_gold_summary(engine) -> Dict[str, pd.DataFrame]:
    """Fetch high-level summaries from Gold analytical tables."""
    data = {}
    with engine.connect() as conn:
        try:
            data["financials"] = pd.read_sql(
                text(f"SELECT * FROM {SCHEMA_GOLD}.gold_daily_financials ORDER BY report_date DESC"),
                conn,
            )
        except Exception:
            data["financials"] = pd.DataFrame()

        try:
            data["leakage"] = pd.read_sql(
                text(f"SELECT * FROM {SCHEMA_GOLD}.gold_revenue_leakage"),
                conn,
            )
        except Exception:
            data["leakage"] = pd.DataFrame()

        try:
            data["products"] = pd.read_sql(
                text(f"SELECT * FROM {SCHEMA_GOLD}.gold_product_profitability"),
                conn,
            )
        except Exception:
            data["products"] = pd.DataFrame()

        try:
            data["customers"] = pd.read_sql(
                text(f"SELECT * FROM {SCHEMA_GOLD}.gold_customer_health"),
                conn,
            )
        except Exception:
            data["customers"] = pd.DataFrame()

        try:
            data["queue"] = pd.read_sql(
                text(f"SELECT * FROM {SCHEMA_GOLD}.gold_investigation_queue ORDER BY priority_score DESC"),
                conn,
            )
        except Exception:
            data["queue"] = pd.DataFrame()

    return data


def generate_executive_briefing(data: Dict[str, pd.DataFrame], currency: str = "₹") -> str:
    """Generate Markdown executive briefing."""
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")

    # Financial Waterfall aggregates
    fin_df = data.get("financials", pd.DataFrame())
    if not fin_df.empty:
        gross_rev = fin_df["gross_revenue"].sum()
        discounts = fin_df["discount_amount"].sum()
        net_sales = fin_df["net_sales"].sum()
        cogs = fin_df["cogs"].sum()
        gross_profit = fin_df["gross_profit"].sum()
        margin_pct = (gross_profit / net_sales * 100) if net_sales > 0 else 0.0
        orders_cnt = fin_df["order_count"].sum()
        units_cnt = fin_df["units_sold"].sum()
        aov = (net_sales / orders_cnt) if orders_cnt > 0 else 0.0
    else:
        gross_rev = discounts = net_sales = cogs = gross_profit = margin_pct = orders_cnt = units_cnt = aov = 0.0

    # Leakage aggregates
    leak_df = data.get("leakage", pd.DataFrame())
    leak_by_mech = {}
    total_leakage = 0.0
    if not leak_df.empty and "mechanism" in leak_df.columns:
        mech_grp = leak_df.groupby("mechanism")["leakage_amount"].sum()
        leak_by_mech = mech_grp.to_dict()
        total_leakage = sum(leak_by_mech.values())

    # Products & Quadrants
    prod_df = data.get("products", pd.DataFrame())
    revenue_traps = []
    profit_drivers = []
    if not prod_df.empty and "classification" in prod_df.columns:
        traps_df = prod_df[prod_df["classification"] == "Revenue Trap"].sort_values(
            by="revenue", ascending=False
        )
        revenue_traps = traps_df.head(5).to_dict(orient="records")

        drivers_df = prod_df[prod_df["classification"] == "Profit Driver"].sort_values(
            by="gross_profit", ascending=False
        )
        profit_drivers = drivers_df.head(5).to_dict(orient="records")

    # Customer Health
    cust_df = data.get("customers", pd.DataFrame())
    health_summary = {}
    if not cust_df.empty and "health_status" in cust_df.columns:
        health_summary = cust_df["health_status"].value_counts().to_dict()
        avg_health = cust_df["health_score"].mean()
    else:
        avg_health = 0.0

    # Investigation Queue
    queue_df = data.get("queue", pd.DataFrame())
    copilot = InvestigationCopilot(currency_symbol=currency)

    # -----------------------------------------------------------------------
    # Document Construction
    # -----------------------------------------------------------------------
    md = [
        f"# 📊 RevenueOS Executive Command Briefing",
        f"*Generated: {now_utc} | Target: C-Suite & Commercial Leadership*",
        f"",
        f"---",
        f"",
        f"## 1. Executive Summary & Core Financial Waterfall",
        f"",
        f"| Financial Metric | Amount ({currency}) | % of Gross | Context / Benchmark |",
        f"| :--- | :--- | :--- | :--- |",
        f"| **Gross Revenue** | **{currency}{gross_rev:,.2f}** | 100.0% | Top-line billed volume |",
        f"| Less: Promotional Discounts | -{currency}{discounts:,.2f} | -{(discounts/gross_rev*100) if gross_rev else 0:.1f}% | Total coupon & campaign reductions |",
        f"| **Net Sales** | **{currency}{net_sales:,.2f}** | {(net_sales/gross_rev*100) if gross_rev else 0:.1f}% | Recognized revenue before COGS |",
        f"| Less: Cost of Goods Sold (COGS) | -{currency}{cogs:,.2f} | -{(cogs/gross_rev*100) if gross_rev else 0:.1f}% | Direct product procurement cost |",
        f"| **Gross Profit** | **{currency}{gross_profit:,.2f}** | **{(gross_profit/gross_rev*100) if gross_rev else 0:.1f}%** | True commercial surplus |",
        f"| **Gross Margin %** | **{margin_pct:.2f}%** | — | Target Threshold: ≥ 25.0% |",
        f"| Total Orders / Units | {orders_cnt:,.0f} orders / {units_cnt:,.0f} units | — | Average Order Value: {currency}{aov:,.2f} |",
        f"",
        f"---",
        f"",
        f"## 2. Revenue Leakage Radar",
        f"",
        f"Total identified commercial leakage across operational systems is modeled at **{currency}{total_leakage:,.2f}**.",
        f"",
        f"| Leakage Mechanism | Loss Amount ({currency}) | % Total Leakage | Root Cause & Remediation |",
        f"| :--- | :--- | :--- | :--- |",
    ]

    for mech, amt in sorted(leak_by_mech.items(), key=lambda x: x[1], reverse=True):
        share = (amt / total_leakage * 100) if total_leakage > 0 else 0
        md.append(f"| **{mech}** | {currency}{amt:,.2f} | {share:.1f}% | Review discount guardrails, gateway health & returns |")

    md.extend([
        f"",
        f"---",
        f"",
        f"## 3. Product Profitability & Revenue Traps",
        f"",
        f"Products classified as **Revenue Traps** generate significant volume but deliver negative or razor-thin gross profit margins due to excessive promotions, high return rates, or procurement cost escalations.",
        f"",
        f"### ⚠️ Identified Revenue Traps (Immediate Commercial Audit Required)",
        f"",
        f"| Product ID | Product Name | Net Sales | Gross Profit | Gross Margin % | Remediation Target |",
        f"| :--- | :--- | :--- | :--- | :--- | :--- |",
    ])

    if revenue_traps:
        for t in revenue_traps:
            md.append(
                f"| `{t.get('product_id')}` | {t.get('product_name')} | {currency}{t.get('revenue', 0):,.2f} | {currency}{t.get('gross_profit', 0):,.2f} | {t.get('gross_margin_pct', 0):.1%} | Cap discount ≤12% / inspect defect rate |"
            )
    else:
        md.append("| — | No active revenue traps detected | — | — | — | Portfolio is healthy |")

    md.extend([
        f"",
        f"### 🌟 Top Profit Drivers",
        f"",
        f"| Product ID | Product Name | Net Sales | Gross Profit | Gross Margin % | Strategic Focus |",
        f"| :--- | :--- | :--- | :--- | :--- | :--- |",
    ])

    if profit_drivers:
        for d in profit_drivers:
            md.append(
                f"| `{d.get('product_id')}` | {d.get('product_name')} | {currency}{d.get('revenue', 0):,.2f} | {currency}{d.get('gross_profit', 0):,.2f} | {d.get('gross_margin_pct', 0):.1%} | Scale marketing & protect stock availability |"
            )
    else:
        md.append("| — | No profit driver data available | — | — | — | — |")

    md.extend([
        f"",
        f"---",
        f"",
        f"## 4. Customer Health & Retention Overview",
        f"",
        f"- **Average Customer Health Score**: `{avg_health:.1f} / 100`",
        f"- **Healthy Accounts**: `{health_summary.get('Healthy', 0):,}`",
        f"- **At-Risk Accounts**: `{health_summary.get('At Risk', 0):,}` (Require automated re-engagement)",
        f"- **Churned / Inactive Accounts**: `{health_summary.get('Churned', 0):,}`",
        f"",
        f"---",
        f"",
        f"## 5. Prioritized Investigation Queue (Actionable Diagnostics)",
        f"",
        f"Top items surfaced by the RevenueOS Decision Engine prioritized by `Financial Impact × Severity × Confidence`:",
        f"",
    ])

    if not queue_df.empty:
        top_queue = queue_df.head(3)
        for idx, (_, item) in enumerate(top_queue.iterrows(), 1):
            md.append(f"### Signal #{idx}: {item.get('issue')} ({item.get('entity_name', item.get('entity_id'))})")
            md.append("```text")
            md.append(copilot.synthesize_investigation(item.to_dict()))
            md.append("```")
            md.append("")
    else:
        md.append("✓ No critical investigation signals currently flagged.")

    md.extend([
        f"",
        f"---",
        f"*End of RevenueOS Executive Briefing. All calculations verifiable via star schema in PostgreSQL `gold` layer.*",
    ])

    return "\n".join(md)


def main():
    parser = argparse.ArgumentParser(description="RevenueOS Executive Briefing Generator")
    parser.add_argument("--output", type=str, default="docs/executive_briefing.md", help="Output path for markdown report")
    args = parser.parse_args()

    engine = get_engine()
    logger.info("▶ Compiling RevenueOS Executive Briefing...")

    data = fetch_gold_summary(engine)
    report_md = generate_executive_briefing(data)

    out_path = Path(args.output)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(report_md, encoding="utf-8")

    logger.info("✓ Executive briefing successfully written to: %s", out_path.resolve())
    print("\n" + "=" * 65)
    print(f"REPORT GENERATED: {out_path.resolve()}")
    print("=" * 65)


if __name__ == "__main__":
    main()
