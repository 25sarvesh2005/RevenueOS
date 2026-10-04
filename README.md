# RevenueOS — Revenue Intelligence & Automated Decision Engine

> *From raw transactions to auditable financial intelligence and automated operational decisions.*

[![CI Pipeline](https://github.com/25sarvesh2005/RevenueOS/actions/workflows/ci.yml/badge.svg)](https://github.com/25sarvesh2005/RevenueOS/actions)
![Electron](https://img.shields.io/badge/Desktop_App-Electron_v44-47848F.svg?logo=electron&logoColor=white)
![Python Version](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12%20%7C%203.13-blue.svg)
![Database](https://img.shields.io/badge/PostgreSQL-16-336791.svg?logo=postgresql&logoColor=white)
![Power BI](https://img.shields.io/badge/Power_BI-8_Page_Semantic_App-F2C811.svg?logo=powerbi&logoColor=black)
[![License: Commercial Royalty](https://img.shields.io/badge/License-Commercial%20Royalty-crimson.svg)](LICENSE)
![Tests](https://img.shields.io/badge/Tests-66%20Passed-brightgreen.svg)

RevenueOS is an enterprise-grade Data Analytics, Analytics Engineering, and Automated Decision Intelligence platform engineered for omnichannel retail enterprises. It features **RevenueOS Studio**—an autonomous Electron desktop application that accepts ANY Excel workbook, auto-decomposes entities into a Kimball Star Schema, generates clean CSV marts, writes tailored DAX measures, compiles native Power BI Templates (`.pbit` & `.pbip`), and guides analysts through deployment.

---

## 🗂 Clean Two-Pillar Architecture

RevenueOS is organized into a clean, modern separation of concerns:

```
revenueos/
│
├── frontend/                # Power BI Desktop Replica Studio (Electron)
│   ├── main.js              # Native Electron process & Python pipeline IPC
│   ├── preload.js           # Secure context bridge API
│   ├── index.html           # Power BI Ribbon, Canvas, Data View & Model View
│   ├── styles.css           # Microsoft Fluent Dark/Light Power BI theme
│   └── app.js               # Interactive Chart.js charts, slicers, DAX formula bar
│
├── backend/                 # Master Python Data & Intelligence Engine
│   ├── engine/              # Universal Kimball Star Schema & DAX Synthesis Engine
│   │   ├── master.py        # Master pipeline: Excel profiling, DAX, PBIT/PBIP compilation
│   │   ├── excel_to_powerbi.py # CLI pipeline wrapper
│   │   └── pipeline_engine.py  # Continuous watcher, background daemon, health diagnostics
│   ├── ingestion/           # Excel parsing & Bronze schema ingestion
│   ├── transformation/      # Silver cleansing & Gold dimensional marts
│   ├── quality/             # Great Expectations data quality assertions
│   ├── warehouse/           # PostgreSQL Kimball Star Schema DDL
│   ├── analytics/           # Gold SQL marts (financials, customer health, marketing)
│   ├── python/              # ML Anomaly Detection, Forecasting & Investigation Copilot
│   ├── powerbi/             # Native Power BI template (.pbit/.pbip) builders
│   ├── config.py            # Global connection pools & settings
│   └── pipeline.py          # Unified CLI entry point
│
├── data/                    # Raw & processed datasets
│   └── raw/excel/           # Source Excel workbooks (e.g., revenueos_sample.xlsx)
│
├── tests/                   # 66 comprehensive passing unit & integration tests
├── docs/                    # Architecture, BRD, and Power BI deployment guides
├── exports/                 # Generated CSV marts, .pbit templates, DAX formulas
├── package.json             # Desktop app configuration (Electron v44 + Chart.js)
├── requirements.txt         # Python dependencies
└── LICENSE                  # Source-Available Commercial & Royalty License
```

---

---

## ⚡ Quick Start

### 🚀 Option 1: RevenueOS Studio (Electron Desktop App)

Launch the visual desktop application to drag & drop any Excel file and generate Power BI models, CSVs, and DAX measures automatically:

```bash
# 1. Install Node & Python dependencies
npm install
pip install -r requirements.txt

# 2. Launch the desktop application
npm start
```

Or run the universal engine headlessly via CLI:

```bash
# Analyze any Excel file and output Power BI template, CSVs, and DAX
python backend/engine/master.py data/raw/excel/revenueos_sample.xlsx --output-dir exports/my_model
```

---

### ⚙️ Option 2: Full Warehouse Data Pipeline (PostgreSQL Batch Engine)

#### 1. Clone & configure

```bash
git clone <your-repo-url>
cd revenueos
cp .env.example .env
# Edit .env with your DB credentials
```

#### 2. Start PostgreSQL

```bash
docker compose up -d
```

#### 3. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 4. Import Excel or drop CSV files

Preferred Excel workflow:

```bash
# Put workbooks in data/raw/excel/ and convert sheets to canonical raw CSVs
python pipeline.py --phase excel

# Or import one workbook explicitly
python pipeline.py --phase excel --excel-path data/raw/excel/revenueos_source.xlsx
```

The Excel importer expects one sheet per entity. Sheet names can be simple names such as `orders`, `customers`, `products`, `payments`, `returns`, `inventory`, and `marketing`. It normalizes friendly column names, trims text, fills safe optional defaults, and writes clean CSVs to `data/raw/<entity>/`.

If you already have canonical CSVs, place them directly into the corresponding `data/raw/<entity>/` folders:

| Entity    | Folder                  | Required Columns                                                                 |
|-----------|-------------------------|----------------------------------------------------------------------------------|
| Orders    | `data/raw/orders/`      | order_id, customer_id, product_id, order_date, quantity, unit_price, discount    |
| Customers | `data/raw/customers/`   | customer_id, name, email, city, region, signup_date, segment                     |
| Products  | `data/raw/products/`    | product_id, product_name, category, subcategory, supplier, cost, selling_price   |
| Payments  | `data/raw/payments/`    | payment_id, order_id, payment_date, payment_method, amount, payment_status       |
| Returns   | `data/raw/returns/`     | return_id, order_id, product_id, return_date, quantity_returned, return_reason   |
| Inventory | `data/raw/inventory/`   | product_id, warehouse, snapshot_date, units_available, units_reserved, units_sold|
| Marketing | `data/raw/marketing/`   | campaign_id, date, channel, spend, impressions, clicks, orders_attributed, revenue_attributed |

### 5. Run the pipeline

```bash
# Full end-to-end batch execution
python pipeline.py

# Idempotent clean rerun (truncate + reload)
python pipeline.py --truncate

# Or run individual phases:
python pipeline.py --phase excel       # convert Excel sheets to canonical raw CSVs
python pipeline.py --phase bronze      # ingest CSVs to raw Bronze schema
python pipeline.py --phase quality     # execute data quality & reconciliation gates
python pipeline.py --phase silver      # transform Bronze to normalized Silver
python pipeline.py --phase gold        # materialize Kimball star schema & analytical marts
```

### 6. Continuous Automation Engine

RevenueOS incorporates an autonomous execution engine for zero-touch continuous operation, real-time file drop watching, scheduled daemon execution, pre-flight diagnostics, and gold mart export:

```bash
# Pre-flight infrastructure & schema health diagnostics
python pipeline.py --health

# Continuous debounced file watcher (watches data/raw/ and data/raw/excel/)
python pipeline.py --watch

# Headless scheduled background daemon (runs hourly, graceful SIGINT/SIGTERM handling)
python pipeline.py --daemon --interval 3600

# Export Gold marts to CSV & compile Power BI templates (.pbit and .pbip)
python pipeline.py --export
```

### 7. Run test suite

```bash
pytest tests/ -v
```

---

## 📐 Architecture

```
SOURCE SYSTEMS (Excel workbooks / drop-directory CSV files)
        │
        ├──► CONTINUOUS FILE WATCHER (engine/pipeline_engine.py)
        │      Debounced SHA256/mtime change detection
        │
        ▼
EXCEL IMPORTER (ingestion/import_excel.py)
  Sheet mapping + column normalization + canonical raw CSV generation
        ↓
BRONZE LAYER (PostgreSQL bronze schema)
  Raw data preserved + ingestion metadata + pipeline_runs telemetry
        ↓
DATA QUALITY ENGINE (quality/run_checks.py)
  Schema · Nulls · Duplicates · Referential Integrity · Cross-Layer Reconciliation
        ↓
SILVER LAYER (PostgreSQL silver schema)
  Standardized · Strongly Typed · Cleansed · Deduped · Derived fields
        ↓
GOLD LAYER – Kimball Star Schema (PostgreSQL gold schema)
  dim_date · dim_customer · dim_product · dim_channel · dim_campaign
  fact_orders · fact_payments · fact_returns · fact_inventory · fact_marketing
        ↓
GOLD ANALYTICS & DECISION MARTS
  Daily Financials · Customer Health · Product Profitability
  Revenue Leakage · Inventory Risk · Marketing Efficiency
  Statistical Anomaly Detection · Prioritized Investigation Queue
        ↓
POWER BI SEMANTIC LAYER & ARTIFACT EXPORT
  8 Executive Pages · PBIT / PBIP Templates · Investigation Copilot Briefs
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

## 🔍 Revenue Intelligence & Automation Features

| Engine | Description |
|--------|-------------|
| **Automation Pipeline Engine** | Event-driven watcher, background daemon scheduler, pre-flight diagnostics, and mart exporter |
| **Revenue Leakage Radar** | Identifies quantified impact from Returns, Discounts, Payment Failures, and Low-Margin erosion |
| **Customer Health Score** | Weighted composite of Recency, Frequency, Monetary, Profitability, Trend, and Behavior |
| **Product Profitability** | Classifies products: Revenue Winner / Revenue Trap / Hidden Winner / Dead Stock |
| **Statistical Anomaly Detection** | IQR, Z-Score, and multivariate Isolation Forest anomaly interceptors |
| **Investigation Queue & Copilot**| Prioritized work queue with automated AI executive diagnostic memos |

---

## 📊 Power BI Semantic Suite

| Page | Focus |
|------|-------|
| 01 Executive Command Center | Strategic KPIs: Revenue, Gross Profit, Margin %, Leakage Impact |
| 02 Revenue Intelligence | Channel, category, and regional performance with drill-down |
| 03 Revenue Leakage Radar | Waterfall attribution across return, discount, and margin leakages |
| 04 Customer Intelligence | Customer health tiers, CLV, churn risk, and profitability scatter |
| 05 Product & Profitability | Quadrant analysis: Margin % vs Net Revenue, SKU classifications |
| 06 Inventory & Operations | Stockout estimates, dead stock risk, and inventory turnover |
| 07 Marketing Efficiency | ROAS, CAC, contribution after marketing, and channel ROI |
| 08 Investigation Queue | Operational triage queue with prioritized evidence dossiers |

---

## ⚠️ Data Assumptions & Operating Boundaries

- Product cost is treated as the full unit COGS proxy.
- Returns are valued at the original transaction selling price.
- Stockout revenue impact is an **estimate**, calculated from velocity during stockout windows.
- Campaign attribution follows the available `orders_attributed` model.
- Customer Health Score is a **prioritization model**, not a causal churn predictor.
- Anomaly detection identifies statistical deviations — **not fraudulent intent**.
- Discount leakage flags products/orders exceeding configured business thresholds.

---

## 🏗 Implementation Roadmap

- [x] Phase 1: Project scaffold & business definition
- [x] Phase 2: Omnichannel synthetic dataset generator & source mapping
- [x] Phase 3: Bronze ingestion pipeline with audit run tracking
- [x] Phase 4: Enterprise Data Quality & Reconciliation Engine
- [x] Phase 5: Silver transformation, normalization & deduplication
- [x] Phase 6: Kimball star schema DDL, indexes & integrity constraints
- [x] Phase 7: Gold financial waterfall & reconciled P&L engine
- [x] Phase 8: Intelligence SQL engines (Customer, Product, Leakage, Inventory, Marketing)
- [x] Phase 9: Prioritized Decision & Investigation Queue
- [x] Phase 10: Power BI semantic suite (DAX measures, M scripts, dark theme, 8-page spec)
- [x] Phase 11: Python statistical/ML anomalies, forecasting & Investigation Copilot
- [x] Phase 12: Complete documentation & comprehensive test suite (66 tests passing)
- [x] Phase 13: Continuous Automation Pipeline Engine (watcher, daemon, health, export) & Commercial Royalty Licensing
- [x] Phase 14: RevenueOS Studio Desktop Application (Electron + Universal Excel-to-Power BI Engine)

---

## 📁 Key Files & Modules

| Module / File | Purpose |
| :--- | :--- |
| [`electron/main.js`](electron/main.js) | RevenueOS Studio: Electron main process, IPC bridges, and native shell launchers |
| [`electron/renderer/`](electron/renderer/) | RevenueOS Studio: Modern Dark Slate UI, star schema visualizer, DAX library & table preview |
| [`engine/excel_to_powerbi.py`](engine/excel_to_powerbi.py) | Universal Excel-to-Power BI engine: schema decomposition, CSV generation, DAX synthesis, PBIT compiler |
| [`engine/pipeline_engine.py`](engine/pipeline_engine.py) | Automation Engine: continuous file watcher, daemon scheduler, pre-flight diagnostics, export |
| [`pipeline.py`](pipeline.py) | Main end-to-end pipeline runner with modular phase execution & CLI |
| [`config.py`](config.py) | Global configuration, connection pools, and leakage thresholds |
| [`data/generate_sample_data.py`](data/generate_sample_data.py) | Omnichannel synthetic dataset generator for all 7 raw entities |
| [`ingestion/import_excel.py`](ingestion/import_excel.py) | Excel workbook importer that creates canonical raw CSVs for preprocessing |
| [`ingestion/ingest_bronze.py`](ingestion/ingest_bronze.py) | Multi-source CSV ingestion into raw Bronze layer with run tracking |
| [`quality/run_checks.py`](quality/run_checks.py) | Data quality rules, foreign key integrity, and reconciliation engine |
| [`transformation/transform_silver.py`](transformation/transform_silver.py) | Bronze to Silver normalization, typing, and deduplication |
| [`transformation/build_gold.py`](transformation/build_gold.py) | Kimball star schema dimensional modeling & gold table materialization |
| [`warehouse/init.sql`](warehouse/init.sql) | Complete DDL for Bronze, Silver, and Gold star schema + pipeline_runs table |
| [`analytics/*.sql`](analytics/) | 7 Gold analytical SQL queries (Financials, Leakage, Health, etc.) |
| [`python/anomaly_detection/detector.py`](python/anomaly_detection/detector.py) | IQR, Z-Score, and Isolation Forest anomaly detection engine |
| [`python/forecasting/forecast_engine.py`](python/forecasting/forecast_engine.py) | Holt-Winters and linear trend 30-day forward-looking forecasting |
| [`python/reporting/investigation_copilot.py`](python/reporting/investigation_copilot.py) | AI / Analytical Copilot synthesizing signals into executive diagnostic briefs |
| [`python/reporting/executive_report.py`](python/reporting/executive_report.py) | Automated executive financial briefing and decision memo generator |
| [`powerbi/dax_measures.dax`](powerbi/dax_measures.dax) | Full semantic DAX measures library organized across all 8 pages |
| [`powerbi/power_query_m.pq`](powerbi/power_query_m.pq) | Copy-paste M scripts to ingest PostgreSQL gold star schema |
| [`powerbi/revenueos_theme.json`](powerbi/revenueos_theme.json) | High-contrast Dark Slate executive UI theme |
| [`powerbi/page_specifications.md`](powerbi/page_specifications.md) | Visual blueprints and drill-through specs for all 8 dashboard pages |
| [`powerbi/RevenueOS.pbit`](powerbi/RevenueOS.pbit) | Compiled Power BI Template with embedded Dark Theme & DAX schema |
| [`powerbi/RevenueOS.pbip`](powerbi/RevenueOS.pbip) | Power BI Developer Project definition for CI/CD version control |
| [`tests/`](tests/) | Comprehensive pytest suite (66 passing unit & integration tests) |
| [`docs/`](docs/) | Full documentation: Architecture, BRD, Data Dictionary, Runbooks, Assumptions |

---

## 📜 Commercial Source-Available & Royalty License

RevenueOS is licensed under the **RevenueOS Source-Available Commercial & Royalty License (Version 1.0)**.

- **Non-Commercial Use**: You are free to view, evaluate, test, and conduct academic/educational research using this repository.
- **Commercial Exploitation Strictly Prohibited**: No individual, company, or organization has the right to profit, commercialize, resell, sub-license, host as SaaS, or monetize RevenueOS or any derivative works without an executed commercial license agreement and royalty payments to the author (**Sarvesh Sharma**).
- **Inquiries & Commercial Licensing**: For commercial licensing inquiries or royalty agreements, please open an issue or contact the copyright holder via GitHub (`@25sarvesh2005`).

---

*RevenueOS is an enterprise-grade analytics platform. All business impact values are estimates and should be validated before use in production decisions.*
