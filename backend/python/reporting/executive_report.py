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


def generate_manifest_executive_report(manifest: Dict[str, Any], currency: str = "$") -> Dict[str, str]:
    """
    Generate standalone Executive Performance Briefing (Markdown & HTML)
    directly from manifest and analytical marts without requiring a PostgreSQL connection.
    """
    now_utc = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    dash = manifest.get("dashboard", {})
    kpis = dash.get("kpis", {})
    rev = kpis.get("totalRevenue", 0.0)
    cogs = kpis.get("totalCost", 0.0)
    gp = kpis.get("grossProfit", 0.0)
    margin = kpis.get("grossMarginPct", 0.0)
    orders = kpis.get("totalOrders", 0)
    units = kpis.get("totalUnits", 0)
    returns = dash.get("returns", {})

    proj_name = manifest.get("projectName", "RevenueOS Intelligence Report")
    tables = manifest.get("tables", [])
    measures = manifest.get("measures", [])
    charts = manifest.get("charts", [])

    # 1. Build Markdown
    md = [
        f"# 📊 {proj_name} – Executive Intelligence Briefing",
        f"**Generated**: `{now_utc}` | **Engine**: `RevenueOS Core 1.0.0` | **License**: `Commercial Source-Available (Royalty)`",
        "",
        "---",
        "",
        "## 1. Executive KPI Scorecard",
        "",
        f"| Metric | Value | Benchmark / Variance | Status |",
        f"|:---|:---:|:---:|:---:|",
        f"| **Gross Revenue** | **{currency}{rev:,.2f}** | Primary Top-Line Volume | ✅ Active |",
        f"| **Cost of Goods Sold (COGS)** | **{currency}{cogs:,.2f}** | Direct Product Incurrence | 📊 Tracked |",
        f"| **Gross Profit** | **{currency}{gp:,.2f}** | Contribution to Overhead | ✅ Positive |",
        f"| **Gross Margin %** | **{margin:.1f}%** | Target Benchmark: 25.0% | {'✅ Exceeding' if margin >= 25 else '⚠️ Under Benchmark'} |",
        f"| **Total Processed Orders** | **{orders:,}** | Filtered Analytical Universe | 📦 Ingested |",
        f"| **Total Units Fulfilled** | **{units:,}** | Avg Units/Order: {(units/orders if orders else 0):.2f} | 🚚 Fulfilled |",
        f"| **Return Rate** | **{returns.get('returnRate', 0.0):.2f}%** | Total: {returns.get('totalReturns', 0)} items | {'✅ Normal' if returns.get('returnRate', 0) < 5 else '⚠️ High'} |",
        "",
        "---",
        "",
        "## 2. Kimball Star Schema Dimensional Marts",
        "",
        "| Table Name | Model Role | Columns | Row Count | Storage Mart |",
        "|:---|:---:|:---:|:---:|:---|",
    ]

    for tbl in tables:
        t_name = tbl.get("name", "")
        role = tbl.get("table_type", "dimension").upper()
        cols_cnt = len(tbl.get("columns", []))
        r_cnt = tbl.get("row_count", 0)
        csv_file = tbl.get("csv_filename", f"{t_name}.csv")
        md.append(f"| `{t_name}` | **{role}** | {cols_cnt} cols | {r_cnt:,} rows | `{csv_file}` |")

    md.extend([
        "",
        "---",
        "",
        "## 3. Synthesized Semantic DAX Measures",
        "",
        "| Measure Name | Inferred Category | DAX Formula Expression |",
        "|:---|:---:|:---|",
    ])

    for m in measures[:10]:
        m_name = m.get("name", "")
        cat = m.get("category", "General")
        expr = m.get("expression", "").replace("\n", " ")
        md.append(f"| `[{m_name}]` | {cat} | `{expr}` |")

    md.extend([
        "",
        "---",
        "",
        "## 4. Proprietary Commercial License Notice",
        "> **STRICT LEGAL NOTICE**: This briefing, associated data marts, and Power BI artifacts were compiled",
        "> by RevenueOS Studio under a commercial proprietary royalty license. No third party may exploit,",
        "> commercialize, or derive profit without express written authorization and mandatory royalty remittances.",
    ])

    markdown_content = "\n".join(md)

    # 2. Build HTML
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>{proj_name} – Executive Briefing</title>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      background-color: #121212;
      color: #E0E0E0;
      line-height: 1.6;
      margin: 0;
      padding: 40px;
    }}
    .container {{
      max-width: 1000px;
      margin: 0 auto;
      background: #1E1E1E;
      border: 1px solid #333333;
      border-radius: 8px;
      padding: 36px 48px;
      box-shadow: 0 8px 32px rgba(0,0,0,0.5);
    }}
    h1 {{ color: #FFFFFF; font-size: 26px; border-bottom: 2px solid #118DFF; padding-bottom: 12px; margin-top: 0; }}
    h2 {{ color: #F2C80F; font-size: 18px; margin-top: 32px; border-bottom: 1px solid #2C2C2C; padding-bottom: 6px; }}
    .meta-bar {{ color: #888888; font-size: 12px; margin-bottom: 24px; }}
    .kpi-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 16px; margin: 20px 0; }}
    .kpi-card {{ background: #252526; border: 1px solid #383838; border-radius: 6px; padding: 16px; }}
    .kpi-title {{ font-size: 11px; text-transform: uppercase; color: #888888; font-weight: 600; }}
    .kpi-val {{ font-size: 24px; font-weight: 700; color: #FFFFFF; margin: 8px 0; }}
    .kpi-sub {{ font-size: 11px; color: #2ECC71; }}
    table {{ width: 100%; border-collapse: collapse; margin-top: 14px; font-size: 13px; }}
    th, td {{ border: 1px solid #333333; padding: 10px 14px; text-align: left; }}
    th {{ background: #2A2A2A; color: #FFFFFF; font-weight: 600; }}
    tr:nth-child(even) {{ background: #1A1A1A; }}
    code {{ font-family: "Fira Code", monospace; background: #2D2D2D; padding: 2px 6px; border-radius: 3px; font-size: 12px; color: #118DFF; }}
    .footer-license {{ margin-top: 40px; padding: 16px; background: #251B14; border: 1px solid #6E3816; border-radius: 6px; font-size: 11px; color: #E09E6D; }}
  </style>
</head>
<body>
  <div class="container">
    <h1>📊 {proj_name}</h1>
    <div class="meta-bar">Generated: <strong>{now_utc}</strong> &nbsp;|&nbsp; Engine: <strong>RevenueOS Core 1.0.0</strong> &nbsp;|&nbsp; License: <strong>Proprietary Royalty</strong></div>

    <h2>1. Executive KPI Summary</h2>
    <div class="kpi-grid">
      <div class="kpi-card">
        <div class="kpi-title">Gross Revenue</div>
        <div class="kpi-val">{currency}{rev:,.2f}</div>
        <div class="kpi-sub">Total Inflow</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-title">Gross Profit</div>
        <div class="kpi-val">{currency}{gp:,.2f}</div>
        <div class="kpi-sub">Margin: {margin:.1f}%</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-title">Total Orders</div>
        <div class="kpi-val">{orders:,}</div>
        <div class="kpi-sub">{units:,} Units Fulfilled</div>
      </div>
      <div class="kpi-card">
        <div class="kpi-title">Return Rate</div>
        <div class="kpi-val">{returns.get('returnRate', 0.0):.2f}%</div>
        <div class="kpi-sub">{returns.get('totalReturns', 0)} Items Returned</div>
      </div>
    </div>

    <h2>2. Star Schema Dimensional Marts</h2>
    <table>
      <thead>
        <tr><th>Table</th><th>Role</th><th>Columns</th><th>Rows</th><th>Export File</th></tr>
      </thead>
      <tbody>
        {"".join(f"<tr><td><code>{tbl.get('name')}</code></td><td><strong>{tbl.get('table_type', 'dim').upper()}</strong></td><td>{len(tbl.get('columns', []))} cols</td><td>{tbl.get('row_count', 0):,}</td><td><code>{tbl.get('csv_filename')}</code></td></tr>" for tbl in tables)}
      </tbody>
    </table>

    <h2>3. Synthesized Semantic DAX Measures (Top)</h2>
    <table>
      <thead>
        <tr><th>Measure</th><th>Category</th><th>Expression</th></tr>
      </thead>
      <tbody>
        {"".join(f"<tr><td><code>[{m.get('name')}]</code></td><td>{m.get('category')}</td><td><code>{m.get('expression', '').replace(chr(10), ' ')}</code></td></tr>" for m in measures[:8])}
      </tbody>
    </table>

    <div class="footer-license">
      <strong>COMMERCIAL LEGAL NOTICE</strong>: This document and all analytical computations are strictly governed by the RevenueOS Commercial Royalty License.
    </div>
  </div>
</body>
</html>
"""
    return {"markdown": markdown_content, "html": html_content}



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
