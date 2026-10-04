# RevenueOS – Pipeline Runbook

Step-by-step instructions for running, maintaining, and debugging the pipeline.

---

## Prerequisites

| Requirement | Version | Notes |
|-------------|---------|-------|
| Python | 3.10+ | |
| PostgreSQL | 15+ | via Docker or local |
| Docker Desktop | any | for `docker compose` |
| Power BI Desktop | any | for BI layer |

---

## First-Time Setup

```bash
# 1. Clone repo
git clone <your-repo>
cd revenueos

# 2. Create virtual environment
python -m venv .venv
.venv\Scripts\activate         # Windows
# source .venv/bin/activate    # Mac/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
# Edit .env with your PostgreSQL credentials

# 5. Start PostgreSQL
docker compose up -d

# 6. Verify connection
python -c "from config import get_engine; e = get_engine(); print('DB OK')"
```

---

## Daily Pipeline Run

```bash
# Full run (all phases)
python pipeline.py

# Idempotent rerun (truncate + reload)
python pipeline.py --truncate
```

---

## Phase-by-Phase Run

```bash
# Phase 0: Import Excel sheets → canonical raw CSVs
python pipeline.py --phase excel

# Phase 1: Ingest canonical CSVs → Bronze
python pipeline.py --phase bronze

# Phase 2: Run quality checks
python pipeline.py --phase quality

# Phase 3: Transform Bronze → Silver
python pipeline.py --phase silver

# Phase 4: Build Gold layer
python pipeline.py --phase gold
```

---

## Continuous Automation Pipeline Engine

The engine (`engine/pipeline_engine.py`) provides hands-off automation for enterprise data platforms:

```bash
# 1. Pre-flight Health & Diagnostic Checks
# Validates database connectivity, Bronze/Silver/Gold schemas, and raw data readiness
python pipeline.py --health

# 2. Continuous File Watcher
# Actively monitors data/raw/ and data/raw/excel/ for new or modified files.
# Features a 3-second debounce window to ensure file transfer completes before ingestion.
python pipeline.py --watch

# 3. Headless Scheduled Daemon
# Runs recurring batch ingestion on a background interval (default: 3600 seconds / 1 hour).
# Handles SIGINT and SIGTERM gracefully to complete in-flight transactions.
python pipeline.py --daemon --interval 3600

# 4. Gold Mart Artifact Export
# Exports all Kimball star schema tables and 8 analytical marts to data/processed/gold/*.csv
# Automatically compiles powerbi/RevenueOS.pbit and powerbi/RevenueOS.pbip
python pipeline.py --export
```

### Execution Telemetry & Audit Logs
- In PostgreSQL: `SELECT * FROM bronze.pipeline_runs ORDER BY started_at DESC LIMIT 10;`
- Local JSON audit trail: `data/pipeline_runs.json` (persisted even when PostgreSQL connection is offline).


---

## Adding New Data Files

### Excel workbooks

1. Place `.xlsx` or `.xlsm` workbooks into `data/raw/excel/`.
2. Use one sheet per entity: `orders`, `customers`, `products`, `payments`, `returns`, `inventory`, and `marketing`.
3. Run `python pipeline.py --phase excel` to generate canonical CSVs into `data/raw/<entity>/`.
4. Run `python pipeline.py --truncate` to preprocess and rebuild the Power BI-ready Gold layer.

### Canonical CSVs

1. Place new CSVs into `data/raw/<entity>/`.
2. Run the pipeline or just the Bronze phase.
3. New files are automatically discovered — no code changes needed.
4. If the CSV has extra columns, they will be logged as "unexpected" and dropped before Bronze loading.

---

## Checking Data Quality

```bash
# Run all quality checks and print report
python quality/run_checks.py

# Check one entity
python quality/run_checks.py --entity orders

# View quality log in PostgreSQL
psql -U revenueos -d revenueos -c "SELECT * FROM bronze.quality_log ORDER BY logged_at DESC LIMIT 20;"
```

---

## Debugging Failed Runs

### Problem: Bronze table empty after ingestion

1. Check `data/raw/<entity>/` for CSV files.
2. Run: `python quality/run_checks.py --entity <entity>`
3. Check for FILE_READ errors in output.

### Problem: Silver rows fewer than Bronze rows

This is expected if:
- Records failed date parsing (null order_date).
- Records had missing required IDs.
- See `bronze.quality_log` for rejection counts.

### Problem: Gold table empty

Check that Silver tables have data first:
```sql
SELECT COUNT(*) FROM silver.orders;
SELECT COUNT(*) FROM silver.products;
```

### Problem: Referential integrity warnings in quality log

Orders referencing unknown customers/products will produce orphan warnings.
This does not halt the pipeline. Check your source data for consistency.

---

## Running Tests

```bash
# All tests
pytest tests/ -v

# With coverage
pytest tests/ --cov=. --cov-report=term-missing

# Single test class
pytest tests/test_core.py::TestFinancialCalculations -v
```

---

## Resetting the Database

```bash
# Full reset (drops all data!)
docker compose down -v
docker compose up -d

# Or truncate all gold tables:
python pipeline.py --truncate --phase gold
```

---

## Environment Variables Reference

| Variable | Default | Description |
|----------|---------|-------------|
| `DB_HOST` | `localhost` | PostgreSQL host |
| `DB_PORT` | `5432` | PostgreSQL port |
| `DB_NAME` | `revenueos` | Database name |
| `DB_USER` | `revenueos` | DB user |
| `DB_PASSWORD` | `revenueos` | DB password |
| `SCHEMA_BRONZE` | `bronze` | Bronze schema name |
| `SCHEMA_SILVER` | `silver` | Silver schema name |
| `SCHEMA_GOLD` | `gold` | Gold schema name |
| `DISCOUNT_LEAKAGE_THRESHOLD` | `0.25` | Discount % threshold for leakage flag |
| `MARGIN_LEAKAGE_THRESHOLD` | `0.15` | Margin % threshold for leakage flag |
| `HIGH_RETURN_RATE_THRESHOLD` | `0.15` | Return rate flag threshold |
| `IQR_MULTIPLIER` | `1.5` | IQR multiplier for anomaly detection |
| `ZSCORE_THRESHOLD` | `3.0` | Z-score threshold |
| `ISOLATION_FOREST_CONTAMINATION` | `0.05` | Contamination rate for Isolation Forest |

---

## Key Tables Reference

| Table | Schema | Description |
|-------|--------|-------------|
| `bronze.orders` | bronze | Raw order data |
| `bronze.quality_log` | bronze | All quality check results |
| `silver.orders` | silver | Standardized orders |
| `gold.fact_orders` | gold | Order fact table (star schema) |
| `gold.dim_customer` | gold | Customer dimension |
| `gold.gold_daily_financials` | gold | Daily revenue/profit aggregates |
| `gold.gold_customer_health` | gold | Customer health scores |
| `gold.gold_product_profitability` | gold | Product P&L and classification |
| `gold.gold_revenue_leakage` | gold | Revenue leakage estimates |
| `gold.gold_business_anomalies` | gold | Detected anomalies |
| `gold.gold_investigation_queue` | gold | Prioritized analyst work queue |
