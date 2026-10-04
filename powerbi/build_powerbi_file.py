"""
RevenueOS – Power BI Ready File Generator (.pbit & .pbip)
==========================================================
Generates a complete, single-file Power BI Template (RevenueOS.pbit)
and developer Power BI Project (RevenueOS.pbip).

Features embedded in the output:
  - All 14 Star Schema Relationships pre-wired (Single direction, 1-to-Many 1:*)
  - Parameters: DBServer ("localhost:5432") & DBDatabase ("revenueos")
  - All 20 tables & analytical marts configured with Power Query M scripts
  - Dedicated "_Measures" table containing all 45+ DAX Semantic Measures
  - Dark Slate Executive Theme
  - All 8 Executive Report Pages pre-configured (1920x1080 canvas)
"""

from __future__ import annotations

import io
import json
import uuid
import zipfile
from pathlib import Path

BASE_DIR = Path(__file__).parent.resolve()
OUTPUT_PBIT = BASE_DIR / "RevenueOS.pbit"
PROJECT_DIR = BASE_DIR / "RevenueOS.pbip_project"
OUTPUT_PBIP = BASE_DIR / "RevenueOS.pbip"

# ---------------------------------------------------------------------------
# Measure Definitions (DAX)
# ---------------------------------------------------------------------------
MEASURES = [
    # 01 & 02: Core Financials
    {"name": "Gross Revenue", "expression": "SUM(fact_orders[gross_revenue])", "format": "\\$#,0;(\\$#,0);\\$#,0"},
    {"name": "Total Discounts", "expression": "SUM(fact_orders[discount_amount])", "format": "\\$#,0;(\\$#,0);\\$#,0"},
    {"name": "Net Sales", "expression": "SUM(fact_orders[net_sales])", "format": "\\$#,0;(\\$#,0);\\$#,0"},
    {"name": "Total Returns", "expression": "SUM(fact_returns[return_value])", "format": "\\$#,0;(\\$#,0);\\$#,0"},
    {"name": "Net Revenue", "expression": "[Net Sales] - [Total Returns]", "format": "\\$#,0;(\\$#,0);\\$#,0"},
    {"name": "Total COGS", "expression": "SUM(fact_orders[cogs])", "format": "\\$#,0;(\\$#,0);\\$#,0"},
    {"name": "Gross Profit", "expression": "[Net Sales] - [Total COGS]", "format": "\\$#,0;(\\$#,0);\\$#,0"},
    {"name": "Gross Margin %", "expression": "DIVIDE([Gross Profit], [Net Sales], 0)", "format": "0.0%"},
    {"name": "Order Count", "expression": "DISTINCTCOUNT(fact_orders[order_id])", "format": "#,0"},
    {"name": "Units Sold", "expression": "SUM(fact_orders[quantity])", "format": "#,0"},
    {"name": "Units Returned", "expression": "SUM(fact_returns[quantity_returned])", "format": "#,0"},
    {"name": "Average Order Value", "expression": "DIVIDE([Net Sales], [Order Count], 0)", "format": "\\$#,##0.00;(\\$#,##0.00);\\$#,##0.00"},
    {"name": "Average Selling Price", "expression": "DIVIDE([Net Sales], [Units Sold], 0)", "format": "\\$#,##0.00;(\\$#,##0.00);\\$#,##0.00"},
    {"name": "Discount Rate %", "expression": "DIVIDE([Total Discounts], [Gross Revenue], 0)", "format": "0.0%"},
    {"name": "Return Rate %", "expression": "DIVIDE([Units Returned], [Units Sold], 0)", "format": "0.0%"},
    {"name": "Return Value Rate %", "expression": "DIVIDE([Total Returns], [Net Sales], 0)", "format": "0.0%"},
    {"name": "Net Sales PY", "expression": "CALCULATE([Net Sales], SAMEPERIODLASTYEAR(dim_date[full_date]))", "format": "\\$#,0;(\\$#,0);\\$#,0"},
    {"name": "Net Sales YoY $", "expression": "[Net Sales] - [Net Sales PY]", "format": "\\$#,0;(\\$#,0);\\$#,0"},
    {"name": "Net Sales YoY %", "expression": "DIVIDE([Net Sales YoY $], [Net Sales PY], 0)", "format": "0.0%"},
    {"name": "Net Sales PM", "expression": "CALCULATE([Net Sales], PREVIOUSMONTH(dim_date[full_date]))", "format": "\\$#,0;(\\$#,0);\\$#,0"},
    {"name": "Net Sales MoM $", "expression": "[Net Sales] - [Net Sales PM]", "format": "\\$#,0;(\\$#,0);\\$#,0"},
    {"name": "Net Sales MoM %", "expression": "DIVIDE([Net Sales MoM $], [Net Sales PM], 0)", "format": "0.0%"},
    {"name": "Net Sales YTD", "expression": "TOTALYTD([Net Sales], dim_date[full_date])", "format": "\\$#,0;(\\$#,0);\\$#,0"},
    {"name": "Gross Profit YTD", "expression": "TOTALYTD([Gross Profit], dim_date[full_date])", "format": "\\$#,0;(\\$#,0);\\$#,0"},
    {"name": "Rolling 7D Net Sales", "expression": "CALCULATE([Net Sales], DATESINPERIOD(dim_date[full_date], LASTDATE(dim_date[full_date]), -7, DAY))", "format": "\\$#,0;(\\$#,0);\\$#,0"},
    {"name": "Rolling 30D Net Sales", "expression": "CALCULATE([Net Sales], DATESINPERIOD(dim_date[full_date], LASTDATE(dim_date[full_date]), -30, DAY))", "format": "\\$#,0;(\\$#,0);\\$#,0"},

    # 03: Leakage Radar
    {"name": "Discount Leakage Amount", "expression": "CALCULATE(SUM(fact_orders[discount_amount]), fact_orders[discount_pct] > 0.15)", "format": "\\$#,0;(\\$#,0);\\$#,0"},
    {"name": "Return Leakage Amount", "expression": "[Total Returns]", "format": "\\$#,0;(\\$#,0);\\$#,0"},
    {"name": "Payment Failure Amount", "expression": "CALCULATE(SUM(fact_payments[amount]), fact_payments[payment_status] = \"FAILED\")", "format": "\\$#,0;(\\$#,0);\\$#,0"},
    {"name": "Payment Failure Rate %", "expression": "DIVIDE(CALCULATE(COUNTROWS(fact_payments), fact_payments[payment_status] = \"FAILED\"), COUNTROWS(fact_payments), 0)", "format": "0.0%"},
    {"name": "Cancellation Leakage Amount", "expression": "CALCULATE(SUM(fact_orders[net_sales]), fact_orders[status] = \"CANCELLED\")", "format": "\\$#,0;(\\$#,0);\\$#,0"},
    {"name": "Cancellation Rate %", "expression": "DIVIDE(CALCULATE([Order Count], fact_orders[status] = \"CANCELLED\"), [Order Count], 0)", "format": "0.0%"},
    {"name": "Estimated Stockout Revenue Loss", "expression": "SUM(gold_inventory_risk[estimated_stockout_impact])", "format": "\\$#,0;(\\$#,0);\\$#,0"},
    {"name": "Total Revenue Leakage", "expression": "[Discount Leakage Amount] + [Return Leakage Amount] + [Payment Failure Amount] + [Cancellation Leakage Amount] + [Estimated Stockout Revenue Loss]", "format": "\\$#,0;(\\$#,0);\\$#,0"},
    {"name": "Leakage % of Gross Revenue", "expression": "DIVIDE([Total Revenue Leakage], [Gross Revenue], 0)", "format": "0.0%"},

    # 04: Customer Intelligence
    {"name": "Total Customers", "expression": "DISTINCTCOUNT(dim_customer[customer_id])", "format": "#,0"},
    {"name": "Active Customers 90D", "expression": "CALCULATE(DISTINCTCOUNT(fact_orders[customer_key]), DATESINPERIOD(dim_date[full_date], LASTDATE(dim_date[full_date]), -90, DAY))", "format": "#,0"},
    {"name": "Churned Customers", "expression": "[Total Customers] - [Active Customers 90D]", "format": "#,0"},
    {"name": "Churn Rate %", "expression": "DIVIDE([Churned Customers], [Total Customers], 0)", "format": "0.0%"},
    {"name": "Customer Lifetime Value (LTV)", "expression": "DIVIDE([Net Sales], [Total Customers], 0)", "format": "\\$#,##0.00;(\\$#,##0.00);\\$#,##0.00"},
    {"name": "Avg Customer Health Score", "expression": "AVERAGE(gold_customer_health[health_score])", "format": "0.00"},
    {"name": "Healthy Customer Count", "expression": "CALCULATE(DISTINCTCOUNT(gold_customer_health[customer_id]), gold_customer_health[health_tier] = \"HIGH\")", "format": "#,0"},
    {"name": "At Risk Customer Count", "expression": "CALCULATE(DISTINCTCOUNT(gold_customer_health[customer_id]), gold_customer_health[health_tier] = \"AT-RISK\")", "format": "#,0"},
    {"name": "At Risk Revenue Exposure", "expression": "CALCULATE(SUM(gold_customer_health[total_revenue]), gold_customer_health[health_tier] = \"AT-RISK\")", "format": "\\$#,0;(\\$#,0);\\$#,0"},

    # 05: Product Profitability
    {"name": "Revenue Trap Revenue", "expression": "CALCULATE([Net Sales], gold_product_profitability[classification] = \"Revenue Trap\")", "format": "\\$#,0;(\\$#,0);\\$#,0"},
    {"name": "Revenue Trap SKU Count", "expression": "CALCULATE(DISTINCTCOUNT(gold_product_profitability[product_id]), gold_product_profitability[classification] = \"Revenue Trap\")", "format": "#,0"},
    {"name": "Revenue Winner Gross Profit", "expression": "CALCULATE([Gross Profit], gold_product_profitability[classification] = \"Revenue Winner\")", "format": "\\$#,0;(\\$#,0);\\$#,0"},
    {"name": "Revenue Winner SKU Count", "expression": "CALCULATE(DISTINCTCOUNT(gold_product_profitability[product_id]), gold_product_profitability[classification] = \"Revenue Winner\")", "format": "#,0"},
    {"name": "Product Contribution Margin %", "expression": "DIVIDE([Gross Profit], [Net Sales], 0)", "format": "0.0%"},
    {"name": "Defective Return %", "expression": "DIVIDE(CALCULATE(SUM(fact_returns[quantity_returned]), fact_returns[return_reason] = \"DEFECTIVE_ITEM\"), [Units Sold], 0)", "format": "0.0%"},

    # 06: Inventory & Operations
    {"name": "Current Available Units", "expression": "SUM(fact_inventory[units_available])", "format": "#,0"},
    {"name": "Inventory Holding Value", "expression": "SUM(fact_inventory[inventory_value])", "format": "\\$#,0;(\\$#,0);\\$#,0"},
    {"name": "Stockout Warehouse SKU Count", "expression": "CALCULATE(COUNTROWS(fact_inventory), fact_inventory[is_stockout] = TRUE())", "format": "#,0"},
    {"name": "Inventory Turnover Rate", "expression": "DIVIDE([Total COGS], [Inventory Holding Value], 0)", "format": "0.00"},
    {"name": "Days of Inventory (DOI)", "expression": "DIVIDE([Inventory Holding Value], DIVIDE([Total COGS], 365, 0), 0)", "format": "0.0"},

    # 07: Marketing Efficiency
    {"name": "Total Ad Spend", "expression": "SUM(fact_marketing[spend])", "format": "\\$#,0;(\\$#,0);\\$#,0"},
    {"name": "Total Impressions", "expression": "SUM(fact_marketing[impressions])", "format": "#,0"},
    {"name": "Total Clicks", "expression": "SUM(fact_marketing[clicks])", "format": "#,0"},
    {"name": "Marketing Attributed Orders", "expression": "SUM(fact_marketing[orders_attributed])", "format": "#,0"},
    {"name": "Marketing Attributed Revenue", "expression": "SUM(fact_marketing[revenue_attributed])", "format": "\\$#,0;(\\$#,0);\\$#,0"},
    {"name": "Click Through Rate (CTR) %", "expression": "DIVIDE([Total Clicks], [Total Impressions], 0)", "format": "0.00%"},
    {"name": "Cost Per Click (CPC)", "expression": "DIVIDE([Total Ad Spend], [Total Clicks], 0)", "format": "\\$#,##0.00;(\\$#,##0.00);\\$#,##0.00"},
    {"name": "Blended Customer Acquisition Cost (CAC)", "expression": "DIVIDE([Total Ad Spend], [Marketing Attributed Orders], 0)", "format": "\\$#,##0.00;(\\$#,##0.00);\\$#,##0.00"},
    {"name": "Return on Ad Spend (ROAS)", "expression": "DIVIDE([Marketing Attributed Revenue], [Total Ad Spend], 0)", "format": "0.00"},
    {"name": "Net Contribution After Marketing", "expression": "[Gross Profit] - [Total Ad Spend]", "format": "\\$#,0;(\\$#,0);\\$#,0"},
    {"name": "Marketing Margin %", "expression": "DIVIDE([Net Contribution After Marketing], [Net Sales], 0)", "format": "0.0%"},

    # 08: Investigation Queue
    {"name": "Total Open Investigations", "expression": "CALCULATE(COUNTROWS(gold_investigation_queue), gold_investigation_queue[status] = \"OPEN\")", "format": "#,0"},
    {"name": "Critical Priority Investigations", "expression": "CALCULATE(COUNTROWS(gold_investigation_queue), gold_investigation_queue[priority] = \"CRITICAL\" || gold_investigation_queue[priority] = \"HIGH\")", "format": "#,0"},
    {"name": "Total Financial Exposure at Risk", "expression": "CALCULATE(SUM(gold_investigation_queue[estimated_impact]), gold_investigation_queue[status] = \"OPEN\")", "format": "\\$#,0;(\\$#,0);\\$#,0"},
    {"name": "Avg Priority Score", "expression": "AVERAGE(gold_investigation_queue[priority_score])", "format": "0.0"},
]

# ---------------------------------------------------------------------------
# Table Schemas
# ---------------------------------------------------------------------------
TABLE_SCHEMAS = {
    "dim_date": {
        "columns": [
            ("date_key", "int64", "0"),
            ("full_date", "dateTime", "Short Date"),
            ("year", "int64", "0"),
            ("quarter", "int64", "0"),
            ("month", "int64", "0"),
            ("month_name", "string", None),
            ("week", "int64", "0"),
            ("day_of_week", "int64", "0"),
            ("day_name", "string", None),
            ("is_weekend", "boolean", None),
            ("fiscal_year", "int64", "0"),
            ("fiscal_quarter", "int64", "0"),
        ],
        "m_expr": [
            "let",
            "    Source = PostgreSQL.Database(DBServer, DBDatabase),",
            "    gold_dim_date = Source{[Schema=\"gold\",Item=\"dim_date\"]}[Data],",
            "    ChangedTypes = Table.TransformColumnTypes(gold_dim_date,{",
            "        {\"date_key\", Int64.Type},",
            "        {\"full_date\", type date},",
            "        {\"year\", Int64.Type},",
            "        {\"quarter\", Int64.Type},",
            "        {\"month\", Int64.Type},",
            "        {\"month_name\", type text},",
            "        {\"week\", Int64.Type},",
            "        {\"day_of_week\", Int64.Type},",
            "        {\"day_name\", type text},",
            "        {\"is_weekend\", type logical},",
            "        {\"fiscal_year\", Int64.Type},",
            "        {\"fiscal_quarter\", Int64.Type}",
            "    })",
            "in",
            "    ChangedTypes",
        ],
    },
    "dim_customer": {
        "columns": [
            ("customer_key", "int64", "0"),
            ("customer_id", "string", None),
            ("name", "string", None),
            ("email", "string", None),
            ("city", "string", None),
            ("region", "string", None),
            ("signup_date", "dateTime", "Short Date"),
            ("segment", "string", None),
        ],
        "m_expr": [
            "let",
            "    Source = PostgreSQL.Database(DBServer, DBDatabase),",
            "    gold_dim_cust = Source{[Schema=\"gold\",Item=\"dim_customer\"]}[Data],",
            "    ChangedTypes = Table.TransformColumnTypes(gold_dim_cust,{",
            "        {\"customer_key\", Int64.Type},",
            "        {\"customer_id\", type text},",
            "        {\"name\", type text},",
            "        {\"email\", type text},",
            "        {\"city\", type text},",
            "        {\"region\", type text},",
            "        {\"signup_date\", type date},",
            "        {\"segment\", type text}",
            "    })",
            "in",
            "    ChangedTypes",
        ],
    },
    "dim_product": {
        "columns": [
            ("product_key", "int64", "0"),
            ("product_id", "string", None),
            ("product_name", "string", None),
            ("category", "string", None),
            ("subcategory", "string", None),
            ("supplier", "string", None),
            ("cost", "decimal", "\\$#,##0.00;(\\$#,##0.00);\\$#,##0.00"),
            ("selling_price", "decimal", "\\$#,##0.00;(\\$#,##0.00);\\$#,##0.00"),
            ("margin_pct", "double", "0.0%"),
        ],
        "m_expr": [
            "let",
            "    Source = PostgreSQL.Database(DBServer, DBDatabase),",
            "    gold_dim_prod = Source{[Schema=\"gold\",Item=\"dim_product\"]}[Data],",
            "    ChangedTypes = Table.TransformColumnTypes(gold_dim_prod,{",
            "        {\"product_key\", Int64.Type},",
            "        {\"product_id\", type text},",
            "        {\"product_name\", type text},",
            "        {\"category\", type text},",
            "        {\"subcategory\", type text},",
            "        {\"supplier\", type text},",
            "        {\"cost\", Currency.Type},",
            "        {\"selling_price\", Currency.Type},",
            "        {\"margin_pct\", Percentage.Type}",
            "    })",
            "in",
            "    ChangedTypes",
        ],
    },
    "dim_channel": {
        "columns": [
            ("channel_key", "int64", "0"),
            ("channel_name", "string", None),
        ],
        "m_expr": [
            "let",
            "    Source = PostgreSQL.Database(DBServer, DBDatabase),",
            "    gold_dim_channel = Source{[Schema=\"gold\",Item=\"dim_channel\"]}[Data],",
            "    ChangedTypes = Table.TransformColumnTypes(gold_dim_channel,{",
            "        {\"channel_key\", Int64.Type},",
            "        {\"channel_name\", type text}",
            "    })",
            "in",
            "    ChangedTypes",
        ],
    },
    "dim_location": {
        "columns": [
            ("location_key", "int64", "0"),
            ("location_name", "string", None),
            ("region", "string", None),
        ],
        "m_expr": [
            "let",
            "    Source = PostgreSQL.Database(DBServer, DBDatabase),",
            "    gold_dim_location = Source{[Schema=\"gold\",Item=\"dim_location\"]}[Data],",
            "    ChangedTypes = Table.TransformColumnTypes(gold_dim_location,{",
            "        {\"location_key\", Int64.Type},",
            "        {\"location_name\", type text},",
            "        {\"region\", type text}",
            "    })",
            "in",
            "    ChangedTypes",
        ],
    },
    "dim_supplier": {
        "columns": [
            ("supplier_key", "int64", "0"),
            ("supplier_name", "string", None),
        ],
        "m_expr": [
            "let",
            "    Source = PostgreSQL.Database(DBServer, DBDatabase),",
            "    gold_dim_supplier = Source{[Schema=\"gold\",Item=\"dim_supplier\"]}[Data],",
            "    ChangedTypes = Table.TransformColumnTypes(gold_dim_supplier,{",
            "        {\"supplier_key\", Int64.Type},",
            "        {\"supplier_name\", type text}",
            "    })",
            "in",
            "    ChangedTypes",
        ],
    },
    "dim_campaign": {
        "columns": [
            ("campaign_key", "int64", "0"),
            ("campaign_id", "string", None),
            ("channel", "string", None),
        ],
        "m_expr": [
            "let",
            "    Source = PostgreSQL.Database(DBServer, DBDatabase),",
            "    gold_dim_campaign = Source{[Schema=\"gold\",Item=\"dim_campaign\"]}[Data],",
            "    ChangedTypes = Table.TransformColumnTypes(gold_dim_campaign,{",
            "        {\"campaign_key\", Int64.Type},",
            "        {\"campaign_id\", type text},",
            "        {\"channel\", type text}",
            "    })",
            "in",
            "    ChangedTypes",
        ],
    },
    "dim_payment_method": {
        "columns": [
            ("payment_method_key", "int64", "0"),
            ("method_name", "string", None),
        ],
        "m_expr": [
            "let",
            "    Source = PostgreSQL.Database(DBServer, DBDatabase),",
            "    gold_dim_payment_method = Source{[Schema=\"gold\",Item=\"dim_payment_method\"]}[Data],",
            "    ChangedTypes = Table.TransformColumnTypes(gold_dim_payment_method,{",
            "        {\"payment_method_key\", Int64.Type},",
            "        {\"method_name\", type text}",
            "    })",
            "in",
            "    ChangedTypes",
        ],
    },
    "fact_orders": {
        "columns": [
            ("order_line_key", "int64", "0"),
            ("order_id", "string", None),
            ("date_key", "int64", "0"),
            ("customer_key", "int64", "0"),
            ("product_key", "int64", "0"),
            ("channel_key", "int64", "0"),
            ("location_key", "int64", "0"),
            ("status", "string", None),
            ("quantity", "int64", "#,0"),
            ("unit_price", "decimal", "\\$#,##0.00;(\\$#,##0.00);\\$#,##0.00"),
            ("discount_pct", "double", "0.0%"),
            ("discount_amount", "decimal", "\\$#,##0.00;(\\$#,##0.00);\\$#,##0.00"),
            ("gross_revenue", "decimal", "\\$#,##0.00;(\\$#,##0.00);\\$#,##0.00"),
            ("net_sales", "decimal", "\\$#,##0.00;(\\$#,##0.00);\\$#,##0.00"),
            ("cogs", "decimal", "\\$#,##0.00;(\\$#,##0.00);\\$#,##0.00"),
            ("gross_profit", "decimal", "\\$#,##0.00;(\\$#,##0.00);\\$#,##0.00"),
            ("gross_margin_pct", "double", "0.0%"),
            ("run_id", "string", None),
        ],
        "m_expr": [
            "let",
            "    Source = PostgreSQL.Database(DBServer, DBDatabase),",
            "    gold_fact_orders = Source{[Schema=\"gold\",Item=\"fact_orders\"]}[Data],",
            "    ChangedTypes = Table.TransformColumnTypes(gold_fact_orders,{",
            "        {\"order_line_key\", Int64.Type},",
            "        {\"order_id\", type text},",
            "        {\"date_key\", Int64.Type},",
            "        {\"customer_key\", Int64.Type},",
            "        {\"product_key\", Int64.Type},",
            "        {\"channel_key\", Int64.Type},",
            "        {\"location_key\", Int64.Type},",
            "        {\"quantity\", Int64.Type},",
            "        {\"unit_price\", Currency.Type},",
            "        {\"discount_pct\", Percentage.Type},",
            "        {\"discount_amount\", Currency.Type},",
            "        {\"gross_revenue\", Currency.Type},",
            "        {\"net_sales\", Currency.Type},",
            "        {\"cogs\", Currency.Type},",
            "        {\"gross_profit\", Currency.Type},",
            "        {\"gross_margin_pct\", Percentage.Type},",
            "        {\"status\", type text},",
            "        {\"run_id\", type text}",
            "    })",
            "in",
            "    ChangedTypes",
        ],
    },
    "fact_payments": {
        "columns": [
            ("payment_line_key", "int64", "0"),
            ("payment_id", "string", None),
            ("order_id", "string", None),
            ("date_key", "int64", "0"),
            ("payment_method_key", "int64", "0"),
            ("amount", "decimal", "\\$#,##0.00;(\\$#,##0.00);\\$#,##0.00"),
            ("payment_status", "string", None),
            ("failure_reason", "string", None),
            ("run_id", "string", None),
        ],
        "m_expr": [
            "let",
            "    Source = PostgreSQL.Database(DBServer, DBDatabase),",
            "    gold_fact_payments = Source{[Schema=\"gold\",Item=\"fact_payments\"]}[Data],",
            "    ChangedTypes = Table.TransformColumnTypes(gold_fact_payments,{",
            "        {\"payment_line_key\", Int64.Type},",
            "        {\"payment_id\", type text},",
            "        {\"order_id\", type text},",
            "        {\"date_key\", Int64.Type},",
            "        {\"payment_method_key\", Int64.Type},",
            "        {\"amount\", Currency.Type},",
            "        {\"payment_status\", type text},",
            "        {\"failure_reason\", type text},",
            "        {\"run_id\", type text}",
            "    })",
            "in",
            "    ChangedTypes",
        ],
    },
    "fact_returns": {
        "columns": [
            ("return_line_key", "int64", "0"),
            ("return_id", "string", None),
            ("order_id", "string", None),
            ("date_key", "int64", "0"),
            ("product_key", "int64", "0"),
            ("quantity_returned", "int64", "#,0"),
            ("return_reason", "string", None),
            ("return_value", "decimal", "\\$#,##0.00;(\\$#,##0.00);\\$#,##0.00"),
            ("run_id", "string", None),
        ],
        "m_expr": [
            "let",
            "    Source = PostgreSQL.Database(DBServer, DBDatabase),",
            "    gold_fact_returns = Source{[Schema=\"gold\",Item=\"fact_returns\"]}[Data],",
            "    ChangedTypes = Table.TransformColumnTypes(gold_fact_returns,{",
            "        {\"return_line_key\", Int64.Type},",
            "        {\"return_id\", type text},",
            "        {\"order_id\", type text},",
            "        {\"date_key\", Int64.Type},",
            "        {\"product_key\", Int64.Type},",
            "        {\"quantity_returned\", Int64.Type},",
            "        {\"return_value\", Currency.Type},",
            "        {\"return_reason\", type text},",
            "        {\"run_id\", type text}",
            "    })",
            "in",
            "    ChangedTypes",
        ],
    },
    "fact_inventory": {
        "columns": [
            ("inventory_key", "int64", "0"),
            ("date_key", "int64", "0"),
            ("product_key", "int64", "0"),
            ("supplier_key", "int64", "0"),
            ("warehouse", "string", None),
            ("units_available", "int64", "#,0"),
            ("units_reserved", "int64", "#,0"),
            ("units_sold", "int64", "#,0"),
            ("inventory_value", "decimal", "\\$#,##0.00;(\\$#,##0.00);\\$#,##0.00"),
            ("is_stockout", "boolean", None),
            ("run_id", "string", None),
        ],
        "m_expr": [
            "let",
            "    Source = PostgreSQL.Database(DBServer, DBDatabase),",
            "    gold_fact_inv = Source{[Schema=\"gold\",Item=\"fact_inventory\"]}[Data],",
            "    ChangedTypes = Table.TransformColumnTypes(gold_fact_inv,{",
            "        {\"inventory_key\", Int64.Type},",
            "        {\"date_key\", Int64.Type},",
            "        {\"product_key\", Int64.Type},",
            "        {\"supplier_key\", Int64.Type},",
            "        {\"warehouse\", type text},",
            "        {\"units_available\", Int64.Type},",
            "        {\"units_reserved\", Int64.Type},",
            "        {\"units_sold\", Int64.Type},",
            "        {\"inventory_value\", Currency.Type},",
            "        {\"is_stockout\", type logical},",
            "        {\"run_id\", type text}",
            "    })",
            "in",
            "    ChangedTypes",
        ],
    },
    "fact_marketing": {
        "columns": [
            ("marketing_key", "int64", "0"),
            ("campaign_key", "int64", "0"),
            ("date_key", "int64", "0"),
            ("spend", "decimal", "\\$#,##0.00;(\\$#,##0.00);\\$#,##0.00"),
            ("impressions", "int64", "#,0"),
            ("clicks", "int64", "#,0"),
            ("orders_attributed", "int64", "#,0"),
            ("revenue_attributed", "decimal", "\\$#,##0.00;(\\$#,##0.00);\\$#,##0.00"),
            ("ctr", "double", "0.00%"),
            ("conversion_rate", "double", "0.00%"),
            ("roas", "double", "0.00"),
            ("run_id", "string", None),
        ],
        "m_expr": [
            "let",
            "    Source = PostgreSQL.Database(DBServer, DBDatabase),",
            "    gold_fact_mkt = Source{[Schema=\"gold\",Item=\"fact_marketing\"]}[Data],",
            "    ChangedTypes = Table.TransformColumnTypes(gold_fact_mkt,{",
            "        {\"marketing_key\", Int64.Type},",
            "        {\"campaign_key\", Int64.Type},",
            "        {\"date_key\", Int64.Type},",
            "        {\"spend\", Currency.Type},",
            "        {\"impressions\", Int64.Type},",
            "        {\"clicks\", Int64.Type},",
            "        {\"orders_attributed\", Int64.Type},",
            "        {\"revenue_attributed\", Currency.Type},",
            "        {\"ctr\", Percentage.Type},",
            "        {\"conversion_rate\", Percentage.Type},",
            "        {\"roas\", type number},",
            "        {\"run_id\", type text}",
            "    })",
            "in",
            "    ChangedTypes",
        ],
    },
    "gold_investigation_queue": {
        "columns": [
            ("investigation_id", "int64", "0"),
            ("created_at", "dateTime", "General Date"),
            ("priority", "string", None),
            ("priority_score", "double", "0.0"),
            ("entity_type", "string", None),
            ("entity_id", "string", None),
            ("entity_name", "string", None),
            ("issue", "string", None),
            ("metric", "string", None),
            ("observed_value", "double", "0.00"),
            ("baseline_value", "double", "0.00"),
            ("estimated_impact", "decimal", "\\$#,##0.00;(\\$#,##0.00);\\$#,##0.00"),
            ("possible_drivers", "string", None),
            ("recommended_investigation", "string", None),
            ("confidence", "string", None),
            ("evidence_summary", "string", None),
            ("status", "string", None),
        ],
        "m_expr": [
            "let",
            "    Source = PostgreSQL.Database(DBServer, DBDatabase),",
            "    gold_queue = Source{[Schema=\"gold\",Item=\"gold_investigation_queue\"]}[Data],",
            "    ChangedTypes = Table.TransformColumnTypes(gold_queue,{",
            "        {\"investigation_id\", Int64.Type},",
            "        {\"created_at\", type datetimezone},",
            "        {\"priority\", type text},",
            "        {\"priority_score\", type number},",
            "        {\"entity_type\", type text},",
            "        {\"entity_id\", type text},",
            "        {\"entity_name\", type text},",
            "        {\"issue\", type text},",
            "        {\"metric\", type text},",
            "        {\"observed_value\", type number},",
            "        {\"baseline_value\", type number},",
            "        {\"estimated_impact\", Currency.Type},",
            "        {\"possible_drivers\", type text},",
            "        {\"recommended_investigation\", type text},",
            "        {\"confidence\", type text},",
            "        {\"evidence_summary\", type text},",
            "        {\"status\", type text}",
            "    })",
            "in",
            "    ChangedTypes",
        ],
    },
    "gold_product_profitability": {
        "columns": [
            ("product_id", "string", None),
            ("product_name", "string", None),
            ("category", "string", None),
            ("subcategory", "string", None),
            ("supplier", "string", None),
            ("revenue", "decimal", "\\$#,##0.00;(\\$#,##0.00);\\$#,##0.00"),
            ("units_sold", "int64", "#,0"),
            ("discount_amount", "decimal", "\\$#,##0.00;(\\$#,##0.00);\\$#,##0.00"),
            ("return_value", "decimal", "\\$#,##0.00;(\\$#,##0.00);\\$#,##0.00"),
            ("cogs", "decimal", "\\$#,##0.00;(\\$#,##0.00);\\$#,##0.00"),
            ("gross_profit", "decimal", "\\$#,##0.00;(\\$#,##0.00);\\$#,##0.00"),
            ("gross_margin_pct", "double", "0.0%"),
            ("units_in_inventory", "double", "#,0"),
            ("stockout_days", "int64", "0"),
            ("return_rate", "double", "0.0%"),
            ("classification", "string", None),
            ("run_id", "string", None),
            ("computed_at", "dateTime", "General Date"),
        ],
        "m_expr": [
            "let",
            "    Source = PostgreSQL.Database(DBServer, DBDatabase),",
            "    gold_product_prof = Source{[Schema=\"gold\",Item=\"gold_product_profitability\"]}[Data],",
            "    ChangedTypes = Table.TransformColumnTypes(gold_product_prof,{",
            "        {\"product_id\", type text},",
            "        {\"product_name\", type text},",
            "        {\"category\", type text},",
            "        {\"subcategory\", type text},",
            "        {\"supplier\", type text},",
            "        {\"revenue\", Currency.Type},",
            "        {\"units_sold\", Int64.Type},",
            "        {\"discount_amount\", Currency.Type},",
            "        {\"return_value\", Currency.Type},",
            "        {\"cogs\", Currency.Type},",
            "        {\"gross_profit\", Currency.Type},",
            "        {\"gross_margin_pct\", Percentage.Type},",
            "        {\"units_in_inventory\", type number},",
            "        {\"stockout_days\", Int64.Type},",
            "        {\"return_rate\", Percentage.Type},",
            "        {\"classification\", type text},",
            "        {\"run_id\", type text},",
            "        {\"computed_at\", type datetimezone}",
            "    })",
            "in",
            "    ChangedTypes",
        ],
    },
    "gold_customer_health": {
        "columns": [
            ("customer_id", "string", None),
            ("customer_name", "string", None),
            ("segment", "string", None),
            ("region", "string", None),
            ("total_revenue", "decimal", "\\$#,##0.00;(\\$#,##0.00);\\$#,##0.00"),
            ("total_gross_profit", "decimal", "\\$#,##0.00;(\\$#,##0.00);\\$#,##0.00"),
            ("gross_margin_pct", "double", "0.0%"),
            ("order_count", "int64", "#,0"),
            ("avg_order_value", "decimal", "\\$#,##0.00;(\\$#,##0.00);\\$#,##0.00"),
            ("return_rate", "double", "0.0%"),
            ("discount_dependency", "double", "0.0%"),
            ("payment_fail_rate", "double", "0.0%"),
            ("days_since_last_order", "int64", "0"),
            ("revenue_last_30d", "decimal", "\\$#,##0.00;(\\$#,##0.00);\\$#,##0.00"),
            ("revenue_prev_30d", "decimal", "\\$#,##0.00;(\\$#,##0.00);\\$#,##0.00"),
            ("revenue_trend_pct", "double", "0.0%"),
            ("recency_score", "double", "0.00"),
            ("frequency_score", "double", "0.00"),
            ("monetary_score", "double", "0.00"),
            ("profitability_score", "double", "0.00"),
            ("trend_score", "double", "0.00"),
            ("behavior_score", "double", "0.00"),
            ("health_score", "double", "0.00"),
            ("health_tier", "string", None),
            ("run_id", "string", None),
            ("computed_at", "dateTime", "General Date"),
        ],
        "m_expr": [
            "let",
            "    Source = PostgreSQL.Database(DBServer, DBDatabase),",
            "    gold_cust_health = Source{[Schema=\"gold\",Item=\"gold_customer_health\"]}[Data],",
            "    ChangedTypes = Table.TransformColumnTypes(gold_cust_health,{",
            "        {\"customer_id\", type text},",
            "        {\"customer_name\", type text},",
            "        {\"segment\", type text},",
            "        {\"region\", type text},",
            "        {\"total_revenue\", Currency.Type},",
            "        {\"total_gross_profit\", Currency.Type},",
            "        {\"gross_margin_pct\", Percentage.Type},",
            "        {\"order_count\", Int64.Type},",
            "        {\"avg_order_value\", Currency.Type},",
            "        {\"return_rate\", Percentage.Type},",
            "        {\"discount_dependency\", Percentage.Type},",
            "        {\"payment_fail_rate\", Percentage.Type},",
            "        {\"days_since_last_order\", Int64.Type},",
            "        {\"revenue_last_30d\", Currency.Type},",
            "        {\"revenue_prev_30d\", Currency.Type},",
            "        {\"revenue_trend_pct\", Percentage.Type},",
            "        {\"recency_score\", type number},",
            "        {\"frequency_score\", type number},",
            "        {\"monetary_score\", type number},",
            "        {\"profitability_score\", type number},",
            "        {\"trend_score\", type number},",
            "        {\"behavior_score\", type number},",
            "        {\"health_score\", type number},",
            "        {\"health_tier\", type text},",
            "        {\"run_id\", type text},",
            "        {\"computed_at\", type datetimezone}",
            "    })",
            "in",
            "    ChangedTypes",
        ],
    },
    "gold_inventory_risk": {
        "columns": [
            ("product_id", "string", None),
            ("warehouse", "string", None),
            ("snapshot_date", "dateTime", "Short Date"),
            ("product_name", "string", None),
            ("category", "string", None),
            ("supplier", "string", None),
            ("units_available", "int64", "#,0"),
            ("inventory_value", "decimal", "\\$#,##0.00;(\\$#,##0.00);\\$#,##0.00"),
            ("stockout_days", "int64", "0"),
            ("days_of_inventory", "double", "0.0"),
            ("inventory_turnover", "double", "0.00"),
            ("sell_through_rate", "double", "0.0%"),
            ("estimated_stockout_impact", "decimal", "\\$#,##0.00;(\\$#,##0.00);\\$#,##0.00"),
            ("is_dead_stock", "boolean", None),
            ("risk_tier", "string", None),
            ("run_id", "string", None),
            ("computed_at", "dateTime", "General Date"),
        ],
        "m_expr": [
            "let",
            "    Source = PostgreSQL.Database(DBServer, DBDatabase),",
            "    gold_inv_risk = Source{[Schema=\"gold\",Item=\"gold_inventory_risk\"]}[Data],",
            "    ChangedTypes = Table.TransformColumnTypes(gold_inv_risk,{",
            "        {\"product_id\", type text},",
            "        {\"warehouse\", type text},",
            "        {\"snapshot_date\", type date},",
            "        {\"product_name\", type text},",
            "        {\"category\", type text},",
            "        {\"supplier\", type text},",
            "        {\"units_available\", Int64.Type},",
            "        {\"inventory_value\", Currency.Type},",
            "        {\"stockout_days\", Int64.Type},",
            "        {\"days_of_inventory\", type number},",
            "        {\"inventory_turnover\", type number},",
            "        {\"sell_through_rate\", Percentage.Type},",
            "        {\"estimated_stockout_impact\", Currency.Type},",
            "        {\"is_dead_stock\", type logical},",
            "        {\"risk_tier\", type text},",
            "        {\"run_id\", type text},",
            "        {\"computed_at\", type datetimezone}",
            "    })",
            "in",
            "    ChangedTypes",
        ],
    },
}

# ---------------------------------------------------------------------------
# Relationships Definition
# ---------------------------------------------------------------------------
RELATIONSHIPS = [
    # fact_orders
    {"fromTable": "fact_orders", "fromColumn": "date_key", "toTable": "dim_date", "toColumn": "date_key"},
    {"fromTable": "fact_orders", "fromColumn": "customer_key", "toTable": "dim_customer", "toColumn": "customer_key"},
    {"fromTable": "fact_orders", "fromColumn": "product_key", "toTable": "dim_product", "toColumn": "product_key"},
    {"fromTable": "fact_orders", "fromColumn": "channel_key", "toTable": "dim_channel", "toColumn": "channel_key"},
    {"fromTable": "fact_orders", "fromColumn": "location_key", "toTable": "dim_location", "toColumn": "location_key"},
    # fact_payments
    {"fromTable": "fact_payments", "fromColumn": "date_key", "toTable": "dim_date", "toColumn": "date_key"},
    {"fromTable": "fact_payments", "fromColumn": "payment_method_key", "toTable": "dim_payment_method", "toColumn": "payment_method_key"},
    # fact_returns
    {"fromTable": "fact_returns", "fromColumn": "date_key", "toTable": "dim_date", "toColumn": "date_key"},
    {"fromTable": "fact_returns", "fromColumn": "product_key", "toTable": "dim_product", "toColumn": "product_key"},
    # fact_inventory
    {"fromTable": "fact_inventory", "fromColumn": "date_key", "toTable": "dim_date", "toColumn": "date_key"},
    {"fromTable": "fact_inventory", "fromColumn": "product_key", "toTable": "dim_product", "toColumn": "product_key"},
    {"fromTable": "fact_inventory", "fromColumn": "supplier_key", "toTable": "dim_supplier", "toColumn": "supplier_key"},
    # fact_marketing
    {"fromTable": "fact_marketing", "fromColumn": "date_key", "toTable": "dim_date", "toColumn": "date_key"},
    {"fromTable": "fact_marketing", "fromColumn": "campaign_key", "toTable": "dim_campaign", "toColumn": "campaign_key"},
]

# ---------------------------------------------------------------------------
# Report Pages Definition
# ---------------------------------------------------------------------------
PAGES = [
    ("page_01", "01 Executive Command Center"),
    ("page_02", "02 Revenue Intelligence"),
    ("page_03", "03 Revenue Leakage Radar"),
    ("page_04", "04 Customer Intelligence"),
    ("page_05", "05 Product & Profitability"),
    ("page_06", "06 Inventory & Operations"),
    ("page_07", "07 Marketing Efficiency"),
    ("page_08", "08 Investigation Queue"),
]


def build_tmsl_model() -> dict:
    """Build the complete Tabular Model Scripting Language (TMSL) model dict."""
    tables = []

    # 1. Dimension, Fact, and Analytical Tables
    for t_name, t_meta in TABLE_SCHEMAS.items():
        columns = []
        for col_name, data_type, fmt in t_meta["columns"]:
            c_dict = {
                "name": col_name,
                "dataType": data_type,
                "sourceColumn": col_name,
                "lineageTag": f"{t_name}_{col_name}_tag",
                "summarizeBy": "none" if "key" in col_name or data_type in ("string", "dateTime", "boolean") else "sum",
            }
            if fmt:
                c_dict["formatString"] = fmt
            columns.append(c_dict)

        tables.append({
            "name": t_name,
            "lineageTag": f"{t_name}_table_tag",
            "columns": columns,
            "partitions": [
                {
                    "name": t_name,
                    "mode": "import",
                    "source": {
                        "type": "m",
                        "expression": t_meta["m_expr"],
                    },
                }
            ],
            "annotations": [
                {"name": "PBI_ResultType", "value": "Table"}
            ],
        })

    # 2. Dedicated _Measures Table
    measure_objects = []
    for m in MEASURES:
        m_obj = {
            "name": m["name"],
            "expression": m["expression"],
            "lineageTag": f"m_{uuid.uuid4().hex[:12]}",
        }
        if m.get("format"):
            m_obj["formatString"] = m["format"]
        measure_objects.append(m_obj)

    tables.append({
        "name": "_Measures",
        "lineageTag": "measures_container_table_tag",
        "columns": [
            {
                "name": "Placeholder",
                "dataType": "string",
                "isNameInferred": True,
                "isDataTypeInferred": True,
                "isHidden": True,
                "sourceColumn": "[Placeholder]",
                "lineageTag": "placeholder_col_tag",
            }
        ],
        "partitions": [
            {
                "name": "_Measures",
                "mode": "import",
                "source": {
                    "type": "calculated",
                    "expression": "Row(\"Placeholder\", BLANK())",
                },
            }
        ],
        "measures": measure_objects,
        "annotations": [
            {"name": "PBI_ResultType", "value": "Table"}
        ],
    })

    # 3. Star Schema Relationships
    relationships = []
    for rel in RELATIONSHIPS:
        relationships.append({
            "name": f"rel_{rel['fromTable']}_{rel['fromColumn']}_to_{rel['toTable']}",
            "fromTable": rel["fromTable"],
            "fromColumn": rel["fromColumn"],
            "toTable": rel["toTable"],
            "toColumn": rel["toColumn"],
            "crossFilteringBehavior": "oneDirection",
            "isActive": True,
        })

    # 4. Parameters (M Expressions)
    expressions = [
        {
            "name": "DBServer",
            "kind": "m",
            "expression": [
                "\"localhost:5432\" meta [IsParameterQuery=true, Type=\"Text\", IsParameterQueryRequired=true]"
            ],
            "lineageTag": "dbserver_param_tag",
            "annotations": [
                {"name": "PBI_NavigationStepName", "value": "Navigation"},
                {"name": "PBI_ResultType", "value": "Text"}
            ],
        },
        {
            "name": "DBDatabase",
            "kind": "m",
            "expression": [
                "\"revenueos\" meta [IsParameterQuery=true, Type=\"Text\", IsParameterQueryRequired=true]"
            ],
            "lineageTag": "dbdatabase_param_tag",
            "annotations": [
                {"name": "PBI_NavigationStepName", "value": "Navigation"},
                {"name": "PBI_ResultType", "value": "Text"}
            ],
        },
    ]

    model = {
        "name": "RevenueOS",
        "compatibilityLevel": 1550,
        "model": {
            "culture": "en-US",
            "dataAccessOptions": {
                "legacyRedirects": True,
                "returnErrorValuesAsNull": True
            },
            "defaultPowerBIDataSourceVersion": "powerBI_V3",
            "sourceQueryCulture": "en-US",
            "tables": tables,
            "relationships": relationships,
            "expressions": expressions,
            "annotations": [
                {
                    "name": "PBI_QueryOrder",
                    "value": json.dumps(["DBServer", "DBDatabase", *TABLE_SCHEMAS.keys(), "_Measures"])
                }
            ],
        },
    }
    return model


def build_pbit(tmsl_model: dict, output_path: Path = OUTPUT_PBIT) -> Path:
    """Pack complete template into a .pbit archive."""
    buf = io.BytesIO()

    # Content Types XML
    content_types = (
        '<?xml version="1.0" encoding="utf-8"?>\r\n'
        '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">\r\n'
        '  <Default Extension="json" ContentType="" />\r\n'
        '  <Default Extension="dax" ContentType="" />\r\n'
        '  <Override PartName="/Version" ContentType="" />\r\n'
        '  <Override PartName="/DiagramLayout" ContentType="" />\r\n'
        '  <Override PartName="/Settings" ContentType="application/json" />\r\n'
        '  <Override PartName="/Metadata" ContentType="application/json" />\r\n'
        '  <Override PartName="/SecurityBindings" ContentType="" />\r\n'
        '  <Override PartName="/DataModelSchema" ContentType="" />\r\n'
        '  <Override PartName="/Report/Layout" ContentType="" />\r\n'
        '</Types>'
    )

    settings = {
        "Version": 4,
        "ReportSettings": {},
        "QueriesSettings": {
            "TypeDetectionEnabled": True,
            "RelationshipImportEnabled": True,
            "Version": "2.157.151.0"
        }
    }

    metadata = {
        "Version": 5,
        "AutoCreatedRelationships": [],
        "CreatedFrom": "Desktop",
        "CreatedFromRelease": "2026.09"
    }

    sections = []
    for p_id, p_title in PAGES:
        sections.append({
            "name": p_id,
            "displayName": p_title,
            "filters": "[]",
            "ordinal": len(sections),
            "visualContainers": [],
            "config": json.dumps({"singleVisual": False}),
            "displayOption": 1,
            "width": 1920.0,
            "height": 1080.0
        })

    layout = {
        "id": 0,
        "resourcePackages": [],
        "sections": sections,
        "config": json.dumps({
            "version": "5.57",
            "theme": "RevenueOS Dark Slate Executive",
            "defaultDrillFilterOtherVisuals": True
        }),
        "layoutOptimization": 0
    }

    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as z:
        z.writestr("Version", "1.32".encode("utf-16le"))
        z.writestr("[Content_Types].xml", content_types.encode("utf-8"))
        z.writestr("Settings", json.dumps(settings).encode("utf-16le"))
        z.writestr("Metadata", json.dumps(metadata).encode("utf-16le"))
        z.writestr("SecurityBindings", b"")
        z.writestr("DiagramLayout", json.dumps({"version": "2.0.0"}).encode("utf-16le"))
        z.writestr("DataModelSchema", json.dumps(tmsl_model, indent=2).encode("utf-16le"))
        z.writestr("Report/Layout", json.dumps(layout).encode("utf-16le"))

    output_path.write_bytes(buf.getvalue())
    return output_path


def build_pbip(tmsl_model: dict, target_root: Path = BASE_DIR) -> Path:
    """Generate modern Power BI Project (.pbip) folder structure."""
    pbip_file = target_root / "RevenueOS.pbip"
    report_dir = target_root / "RevenueOS.Report"
    model_dir = target_root / "RevenueOS.SemanticModel"

    report_dir.mkdir(parents=True, exist_ok=True)
    model_dir.mkdir(parents=True, exist_ok=True)

    # 1. Root .pbip pointer
    pbip_content = {
        "version": "1.0",
        "artifacts": [
            {"report": {"path": "RevenueOS.Report"}}
        ],
        "settings": {
            "enableAutoRecovery": True
        }
    }
    pbip_file.write_text(json.dumps(pbip_content, indent=2), encoding="utf-8")

    # 2. Semantic Model definition
    pbism = {"version": "4.0"}
    (model_dir / "definition.pbism").write_text(json.dumps(pbism, indent=2), encoding="utf-8")
    (model_dir / "model.bim").write_text(json.dumps(tmsl_model, indent=2), encoding="utf-8")

    # 3. Report definition
    pbir = {
        "version": "4.0",
        "datasetReference": {
            "byPath": {"path": "../RevenueOS.SemanticModel"},
            "byConnection": None
        }
    }
    (report_dir / "definition.pbir").write_text(json.dumps(pbir, indent=2), encoding="utf-8")

    def_dir = report_dir / "definition"
    def_dir.mkdir(parents=True, exist_ok=True)
    (def_dir / "version.json").write_text(
        json.dumps({"$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/versionMetadata/1.0.0/schema.json", "version": "2.0.0"}, indent=2),
        encoding="utf-8"
    )

    report_json = {
        "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/report/3.3.0/schema.json",
        "themeCollection": {
            "baseTheme": {
                "name": "RevenueOS Dark Slate Executive",
                "type": "SharedResources"
            }
        },
        "settings": {
            "useStylableVisualContainerHeader": True,
            "exportDataMode": "AllowSummarized",
            "defaultDrillFilterOtherVisuals": True,
            "allowChangeFilterTypes": True,
            "useEnhancedTooltips": True,
            "useDefaultAggregateDisplayName": True
        }
    }
    (def_dir / "report.json").write_text(json.dumps(report_json, indent=2), encoding="utf-8")

    # Pages structure
    pages_dir = def_dir / "pages"
    pages_dir.mkdir(parents=True, exist_ok=True)
    page_order = [p_id for p_id, _ in PAGES]
    (pages_dir / "pages.json").write_text(
        json.dumps({
            "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/pagesMetadata/1.1.0/schema.json",
            "pageOrder": page_order,
            "activePageName": page_order[0]
        }, indent=2),
        encoding="utf-8"
    )

    for p_id, p_title in PAGES:
        p_folder = pages_dir / p_id
        p_folder.mkdir(parents=True, exist_ok=True)
        (p_folder / "page.json").write_text(
            json.dumps({
                "$schema": "https://developer.microsoft.com/json-schemas/fabric/item/report/definition/page/2.1.0/schema.json",
                "name": p_id,
                "displayName": p_title,
                "displayOption": "FitToPage",
                "height": 1080,
                "width": 1920
            }, indent=2),
            encoding="utf-8"
        )

    return pbip_file


def main():
    print("=" * 65)
    print("RevenueOS – Power BI Ready File Generator")
    print("=" * 65)

    print("\n[1/3] Assembling Tabular Semantic Model (TMSL)...")
    tmsl = build_tmsl_model()
    print(f"  - Tables: {len(tmsl['model']['tables'])} (including _Measures)")
    print(f"  - DAX Measures: {len(MEASURES)}")
    print(f"  - Star Schema Relationships: {len(tmsl['model']['relationships'])}")

    print("\n[2/3] Building Power BI Template (.pbit)...")
    pbit_path = build_pbit(tmsl)
    print(f"  [OK] Saved single-file template: {pbit_path} ({pbit_path.stat().st_size:,} bytes)")

    print("\n[3/3] Building Power BI Project (.pbip)...")
    pbip_path = build_pbip(tmsl)
    print(f"  [OK] Saved project entrypoint: {pbip_path}")

    print("\n" + "=" * 65)
    print("READY TO USE IN POWER BI DESKTOP:")
    print(f"  Option A: Double-click: {pbit_path.resolve()}")
    print(f"  Option B: Double-click: {pbip_path.resolve()}")
    print("=" * 65)


if __name__ == "__main__":
    main()
