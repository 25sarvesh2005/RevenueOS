# RevenueOS – Operational Runbook & Deployment Guide

This runbook provides step-by-step instructions for deploying, operating, maintaining, and troubleshooting the RevenueOS data platform in production or local environments.

---

## 1. Environment Architecture

```
[ Host Machine / CI-CD ]
         │
         ▼
┌────────────────────────────────────────────────────────┐
│                   Docker Compose Stack                 │
│                                                        │
│  ┌───────────────────┐        ┌─────────────────────┐  │
│  │    PostgreSQL 16  │◄───────┤  Pipeline Runner    │  │
│  │   (Port 5432)     │        │  (Python 3.11-slim) │  │
│  │   DB: revenueos   │        └─────────────────────┘  │
│  └─────────┬─────────┘                                 │
│            │                                           │
│            ▼                                           │
│  ┌───────────────────┐                                 │
│  │    pgAdmin 4      │                                 │
│  │   (Port 5050)     │                                 │
│  └───────────────────┘                                 │
└────────────────────────────────────────────────────────┘
```

---

## 2. Quickstart Deployment

### Option A: Docker Compose (Recommended)
Spin up the entire stack with a single command:
```bash
# 1. Start PostgreSQL 16 and pgAdmin 4
docker compose up -d postgres pgadmin

# 2. Run the end-to-end data pipeline
docker compose run --rm pipeline
```

pgAdmin 4 will be accessible at:
- **URL**: `http://localhost:5050`
- **Email**: `admin@revenueos.internal`
- **Password**: `admin123`
*(RevenueOS database connection is pre-registered automatically)*

### Option B: Local Python Environment
```bash
# 1. Set up virtual environment
python -m venv .venv
.venv\Scripts\activate      # Windows
# source .venv/bin/activate # Linux/Mac

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment variables
cp .env.example .env

# 4. Generate realistic test data (optional if providing own datasets)
python data/generate_sample_data.py --rows 15000

# 5. Run full pipeline
python pipeline.py --truncate
```

---

## 3. Pipeline Execution Controls

The orchestrator [`pipeline.py`](file:///c:/Partition/SERIOUS%20PROJECTS/RevenueOS/pipeline.py) supports modular execution:

```bash
# Convert Excel workbook sheets into canonical raw CSVs
python pipeline.py --phase excel

# Run only Bronze ingestion (loads canonical raw CSVs into bronze schema)
python pipeline.py --phase bronze

# Run only Data Quality validation (Logs checks to bronze.quality_log)
python pipeline.py --phase quality

# Run only Silver transformation (Cleanses, types, and deduplicates)
python pipeline.py --phase silver

# Run only Gold dimensional build (Populates star schema & analytical marts)
python pipeline.py --phase gold

# Run statistical & ML anomaly detection engine
python -c "from python.anomaly_detection.detector import run_anomaly_pipeline; print('Anomaly Detector Ready')"

# Generate Executive Decision Briefing (Markdown report)
python python/reporting/executive_report.py --output docs/executive_briefing.md
```

### Automation & Daemon Controls

```bash
# Run pre-flight health & infrastructure diagnostics
python pipeline.py --health

# Run continuous debounced file watcher (watches data/raw/ and data/raw/excel/)
python pipeline.py --watch

# Run background scheduled daemon (hourly recurring pipeline execution)
python pipeline.py --daemon --interval 3600

# Export Gold marts to CSV & compile Power BI templates (.pbit & .pbip)
python pipeline.py --export
```

---

## 4. Incident Response & Troubleshooting

### Quality Check Failure: `CRITICAL`
If the data quality engine encounters severe referential integrity or schema violations, the pipeline halts immediately with exit code `2`.

**Remediation Steps**:
1. Inspect the latest quality run log in PostgreSQL:
   ```sql
   SELECT entity, check_name, status, observed_value, threshold, message
   FROM bronze.quality_log
   WHERE run_id = (SELECT run_id FROM bronze.quality_log ORDER BY logged_at DESC LIMIT 1)
     AND status = 'CRITICAL';
   ```
2. Correct the offending raw CSV file in `data/raw/<entity>/`.
3. Re-run the pipeline with the `--truncate` flag for a clean idempotent reload:
   ```bash
   python pipeline.py --truncate
   ```

### Database Connection Refused
- Verify PostgreSQL container health: `docker compose ps`
- Confirm port 5432 is not occupied by another local service: `netstat -ano | findstr 5432`
- Check PostgreSQL container logs: `docker compose logs postgres`

### Schema Reset & Full Refresh
To reset the warehouse to an empty initialized state:
```bash
# Drop all tables and re-apply init.sql
docker compose down -v
docker compose up -d postgres
```

---

## 5. Power BI Production Refresh

1. Open `powerbi/RevenueOS.pbix` in **Power BI Desktop**.
2. If refreshing from a remote server, update parameters:
   - `DBServer` → Host IP / FQDN:Port
   - `DBDatabase` → Database name
3. In Power BI Desktop, click **Refresh** in the Home ribbon.
4. For automated scheduled refresh in Power BI Service:
   - Install **Power BI On-Premises Data Gateway (Standard Mode)** on the database host.
   - Configure gateway data source with PostgreSQL Native connector using credentials from `.env`.
   - Set refresh cadence to **Daily at 06:00 UTC** (after overnight batch execution).
