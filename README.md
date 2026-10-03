# RevenueOS — Revenue Intelligence & Decision Engine

> *From raw transactions to financial decisions.*

[![CI Pipeline](https://github.com/25sarvesh2005/RevenueOS/actions/workflows/ci.yml/badge.svg)](https://github.com/25sarvesh2005/RevenueOS/actions)
![Python Version](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue.svg)
![Database](https://img.shields.io/badge/PostgreSQL-16-336791.svg?logo=postgresql&logoColor=white)
![Power BI](https://img.shields.io/badge/Power_BI-8_Page_Dashboard-F2C811.svg?logo=powerbi&logoColor=black)
![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)
![Tests](https://img.shields.io/badge/Tests-51%20Passed-brightgreen.svg)

RevenueOS is an end-to-end Data Analytics and Decision Intelligence platform engineered for omnichannel retail enterprises. It transforms messy, multi-source operational data into validated financial metrics, leakage radars, statistical anomaly detections, and an actionable, prioritized business investigation queue.

---

## 🗂 Project Structure

```
revenueos/
│
├── pipeline.py              # Main pipeline orchestrator
├── config.py                # Shared config, DB engine, paths
├── requirements.txt
├── .env.example
├── docker-compose.yml
│
├── data/
│   ├── raw/                 # Drop your CSV files here
│   │   ├── orders/
│   │   ├── customers/
│   │   ├── products/
│   │   ├── payments/
│   │   ├── returns/
│   │   ├── inventory/
│   │   └── marketing/
│   ├── processed/
│   │   ├── bronze/
│   │   ├── silver/
│   │   └── gold/
│   └── sample/
│
├── ingestion/
│   └── ingest_bronze.py     # CSV → Bronze PostgreSQL
│
├── quality/
│   └── run_checks.py        # Data Quality Engine
│
├── transformation/
│   ├── transform_silver.py  # Bronze → Silver
│   └── build_gold.py        # Silver → Gold (star schema + analytics)
│
├── warehouse/
│   └── init.sql             # All DDL: Bronze / Silver / Gold schemas
│
├── analytics/               # SQL analytics scripts
├── python/                  # Advanced Python analytics
│   ├── anomaly_detection/
│   ├── forecasting/
│   └── reporting/
│
├── tests/
│   └── test_core.py         # pytest test suite
│
├── powerbi/                 # Power BI .pbix files
├── docs/                    # Full documentation
└── screenshots/
```

---

## ⚡ Quick Start

### 1. Clone & configure

```bash
git clone <your-repo-url>
cd revenueos
cp .env.example .env
# Edit .env with your DB credentials
```

### 2. Start PostgreSQL

```bash
docker compose up -d
```

### 3. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 4. Drop your CSV files

Place your CSV files into the corresponding `data/raw/<entity>/` folders:

| Entity    | Folder                  | Required Columns                                                                 |
|-----------|-------------------------|----------------------------------------------------------------------------------|
| Orders    | `data/raw/orders/`      | order_id, customer_id, product_id, order_date, quantity, unit_price, discount    |
| Customers | `data/raw/customers/`   | customer_id, name, email, city, region, signup_date, segment                     |
| Products  | `data/raw/products/`    | product_id, product_name, category, subcategory, supplier, cost, selling_price   |
| Payments  | `data/raw/payments/`    | payment_id, order_id, payment_date, payment_method, amount, payment_status       |
| Returns   | `data/raw/returns/`     | return_id, order_id, product_id, return_date, quantity_returned, return_reason   |
| Inventory | `data/raw/inventory/`   | product_id, warehouse, snapshot_date, units_available, units_reserved, units_sold|
| Marketing | `data/raw/marketing/`   | campaign_id, date, channel, spend, impressions, clicks, orders_attributed        |

### 5. Run the full pipeline

```bash
python pipeline.py
```

Or run individual phases:

```bash
python pipeline.py --phase bronze      # ingest CSVs to Bronze
python pipeline.py --phase quality     # run data quality checks
python pipeline.py --phase silver      # transform to Silver
python pipeline.py --phase gold        # build Gold analytics
python pipeline.py --truncate          # idempotent rerun
```

### 6. Run tests

```bash
pytest tests/ -v
```

---

## 📐 Architecture

```
SOURCE SYSTEMS (CSV files)
        ↓
BRONZE LAYER (PostgreSQL)
  Raw data preserved + ingestion metadata
        ↓
DATA QUALITY ENGINE
  Schema · Nulls · Duplicates · Referential Integrity · Reconciliation
        ↓
SILVER LAYER (PostgreSQL)
  Standardized · Typed · Cleaned · Derived fields
        ↓
GOLD LAYER – Star Schema
  dim_date · dim_customer · dim_product · dim_channel · ...
  fact_orders · fact_payments · fact_returns · fact_inventory · fact_marketing
        ↓
GOLD ANALYTICS
  Daily Financials · Customer Health · Product Profitability
  Revenue Leakage · Inventory Risk · Marketing Efficiency
  Business Anomalies · Investigation Queue
        ↓
POWER BI DECISION LAYER
  8 Dashboard Pages + Drill-through
```

---

## 💡 Core Financial Definitions

| Metric | Formula |
|--------|---------|
| Gross Revenue | Quantity × Unit Price |
| Discount Amount | Gross Revenue × Discount % |
| Net Sales | Gross Revenue − Discount Amount |
| Return Value | Returned Qty × Unit Price |
| Net Revenue | Net Sales − Return Value |
| COGS | Sold Qty × Product Unit Cost |
| Gross Profit | Net Revenue − COGS |
| Gross Margin % | Gross Profit ÷ Net Revenue |

---

## 🔍 Revenue Intelligence Features

| Engine | Description |
|--------|-------------|
| **Revenue Leakage Radar** | Identifies estimated impact from Returns, Discounts, Payment Failures, Low-Margin sales |
| **Customer Health Score** | Weighted composite of Recency, Frequency, Monetary, Profitability, Trend, Behavior |
| **Product Profitability** | Classifies products: Revenue Winner / Revenue Trap / Hidden Winner / Dead Stock |
| **Anomaly Detection** | IQR-based detection on order value, quantity, discount |
| **Investigation Queue** | Prioritized list of business signals requiring analyst attention |

---

## 📊 Power BI Pages

| Page | Focus |
|------|-------|
| 01 Executive Command Center | KPIs: Revenue, Profit, Margin, Leakage |
| 02 Revenue Intelligence | Trends, channels, categories, drill-down |
| 03 Revenue Leakage Radar | Waterfall by leakage mechanism |
| 04 Customer Intelligence | Scatter: Revenue × Margin, health tiers |
| 05 Product & Profitability | Quadrant: Revenue vs Margin |
| 06 Inventory & Operations | Stockout days, dead stock, turnover |
| 07 Marketing Efficiency | ROAS, CAC, Contribution After Marketing |
| 08 Investigation Queue | Analyst work queue with evidence |

---

## ⚠️ Data Assumptions

- Product cost is treated as full COGS proxy.
- Returns are valued at the transaction selling price.
- Stockout revenue impact is an **estimate**, not confirmed lost revenue.
- Campaign attribution follows the available `orders_attributed` field.
- Customer Health Score is a **prioritization model**, not a causal model.
- Anomaly detection identifies unusual behavior — **not fraud**.
- Discount leakage flags products/orders exceeding the configured threshold.

---

## 🏗 Implementation Roadmap

- [x] Phase 1: Project scaffold & business definition
- [x] Phase 2: Synthetic data generator & source mapping
- [x] Phase 3: Bronze ingestion pipeline
- [x] Phase 4: Data Quality & Reconciliation Engine
- [x] Phase 5: Silver transformation & deduplication
- [x] Phase 6: Kimball star schema DDL & indexes
- [x] Phase 7: Gold financial waterfall engine
- [x] Phase 8: Intelligence SQL engines (Customer, Product, Leakage, Inventory, Marketing)
- [x] Phase 9: Decision & Investigation Queue
- [x] Phase 10: Power BI suite (DAX measures, Power Query M, dark theme, 8-page spec)
- [x] Phase 11: Python statistical/ML anomalies, forecasting & Investigation Copilot
- [x] Phase 12: Complete documentation & comprehensive test suite (51 tests passing)

---

## 📁 Key Files & Modules

| Module / File | Purpose |
| :--- | :--- |
| [`pipeline.py`](file:///c:/Partition/SERIOUS%20PROJECTS/RevenueOS/pipeline.py) | Main end-to-end pipeline runner with modular phase execution |
| [`config.py`](file:///c:/Partition/SERIOUS%20PROJECTS/RevenueOS/config.py) | Global configuration, connection pools, and leakage thresholds |
| [`data/generate_sample_data.py`](file:///c:/Partition/SERIOUS%20PROJECTS/RevenueOS/data/generate_sample_data.py) | Omnichannel synthetic dataset generator for all 7 raw entities |
| [`ingestion/ingest_bronze.py`](file:///c:/Partition/SERIOUS%20PROJECTS/RevenueOS/ingestion/ingest_bronze.py) | Multi-source CSV ingestion into raw Bronze layer with run tracking |
| [`quality/run_checks.py`](file:///c:/Partition/SERIOUS%20PROJECTS/RevenueOS/quality/run_checks.py) | Data quality rules, foreign key integrity, and reconciliation engine |
| [`transformation/transform_silver.py`](file:///c:/Partition/SERIOUS%20PROJECTS/RevenueOS/transformation/transform_silver.py) | Bronze to Silver normalization, typing, and deduplication |
| [`transformation/build_gold.py`](file:///c:/Partition/SERIOUS%20PROJECTS/RevenueOS/transformation/build_gold.py) | Kimball star schema dimensional modeling & gold table materialization |
| [`warehouse/init.sql`](file:///c:/Partition/SERIOUS%20PROJECTS/RevenueOS/warehouse/init.sql) | Complete DDL for Bronze, Silver, and Gold star schema + indexes |
| [`analytics/*.sql`](file:///c:/Partition/SERIOUS%20PROJECTS/RevenueOS/analytics/) | 7 Gold analytical SQL queries (Financials, Leakage, Health, etc.) |
| [`python/anomaly_detection/detector.py`](file:///c:/Partition/SERIOUS%20PROJECTS/RevenueOS/python/anomaly_detection/detector.py) | IQR, Z-Score, and Isolation Forest anomaly detection engine |
| [`python/forecasting/forecast_engine.py`](file:///c:/Partition/SERIOUS%20PROJECTS/RevenueOS/python/forecasting/forecast_engine.py) | Holt-Winters and linear trend 30-day forward-looking forecasting |
| [`python/reporting/investigation_copilot.py`](file:///c:/Partition/SERIOUS%20PROJECTS/RevenueOS/python/reporting/investigation_copilot.py) | AI / Analytical Copilot synthesizing signals into executive diagnostic briefs |
| [`python/reporting/executive_report.py`](file:///c:/Partition/SERIOUS%20PROJECTS/RevenueOS/python/reporting/executive_report.py) | Automated executive financial briefing and decision memo generator |
| [`powerbi/dax_measures.dax`](file:///c:/Partition/SERIOUS%20PROJECTS/RevenueOS/powerbi/dax_measures.dax) | Full semantic DAX measures library organized across all 8 pages |
| [`powerbi/power_query_m.pq`](file:///c:/Partition/SERIOUS%20PROJECTS/RevenueOS/powerbi/power_query_m.pq) | Copy-paste M scripts to ingest PostgreSQL gold star schema |
| [`powerbi/revenueos_theme.json`](file:///c:/Partition/SERIOUS%20PROJECTS/RevenueOS/powerbi/revenueos_theme.json) | High-contrast Dark Slate executive UI theme |
| [`powerbi/page_specifications.md`](file:///c:/Partition/SERIOUS%20PROJECTS/RevenueOS/powerbi/page_specifications.md) | Visual blueprints and drill-through specs for all 8 dashboard pages |
| [`tests/`](file:///c:/Partition/SERIOUS%20PROJECTS/RevenueOS/tests/) | Comprehensive pytest suite (51 passing unit & integration tests) |
| [`docs/`](file:///c:/Partition/SERIOUS%20PROJECTS/RevenueOS/docs/) | Full documentation: Architecture, BRD, Data Dictionary, Runbook, Assumptions |

---

*RevenueOS is an enterprise-grade analytics platform. All business impact values are estimates and should be validated before use in production decisions.*
