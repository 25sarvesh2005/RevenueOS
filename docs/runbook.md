# RevenueOS — System Operations & Production Runbook
**Deployment, Environment Configuration, Health Diagnostics, and Infrastructure Runbook**  
*Document Version: 1.0.0 · Author: Sarvesh Sharma · License: RevenueOS Commercial Royalty License*

---

## 1. System Requirements & Hardware Sizing

### Minimum Host Specifications (Evaluation & Development)
* **Operating System**: Windows 10/11 (64-bit), macOS 12+, or Ubuntu 22.04 LTS
* **CPU**: Dual-core x86_64 or Apple Silicon (ARM64)
* **RAM**: 4 GB physical memory
* **Disk Space**: 1 GB available storage
* **Runtimes**:
  - Python $\ge 3.10$ (3.13 recommended)
  - Node.js $\ge 18.0$ (20+ recommended)

### Recommended Production Specifications (Multi-Tenant & Enterprise Batch)
* **CPU**: 4+ Cores (for parallel NumPy & Pandas aggregations)
* **RAM**: 16 GB physical memory (supports spreadsheets up to 10M rows)
* **Storage**: NVMe SSD with $\ge 20\text{ GB}$ storage for compiled CSV marts and Power BI project zip archives

---

## 2. Environment Configuration (`.env`)

RevenueOS adopts zero-vibe, explicit configuration management. Create a `.env` file in the project root:

```ini
# RevenueOS Operational Configuration
REVENUEOS_ENV=production
REVENUEOS_PORT=8000
REVENUEOS_HOST=127.0.0.1

# Security & Authentication (Required in Production)
REVENUEOS_API_KEY=YOUR_SECURE_ENTERPRISE_TOKEN_HERE

# PostgreSQL Database Layer (Optional - File-mode operates standalone without DB)
DATABASE_HOST=localhost
DATABASE_PORT=5432
DATABASE_USER=postgres
DATABASE_PASSWORD=YOUR_DB_PASSWORD
DATABASE_NAME=revenueos_db
DATABASE_SCHEMA_GOLD=gold

# Logging & Telemetry
LOG_LEVEL=INFO
```

---

## 3. Starting the Platform

### Option 1: Desktop Replica Studio (Electron + Local Engine)
```powershell
# Windows Desktop App launcher
npm start
```

### Option 2: Headless Intelligence REST API Service
```powershell
# Launch FastAPI backend with uvicorn
uvicorn backend.api.app:app --host 127.0.0.1 --port 8000 --reload
```

Interactive API documentation will be available at:
* Swagger UI: `http://127.0.0.1:8000/docs`
* ReDoc UI: `http://127.0.0.1:8000/redoc`

---

## 4. Health Diagnostics & Readiness Checks

RevenueOS includes automated health and environmental diagnostics:

```bash
curl http://127.0.0.1:8000/api/health
```

**Expected JSON Response**:
```json
{
  "status": "HEALTHY",
  "timestamp": "2026-10-04T07:45:00.000000+00:00",
  "version": "1.0.0",
  "python_version": "3.13.2",
  "workspace_root": "C:\\Partition\\SERIOUS PROJECTS\\RevenueOS",
  "dependencies": {
    "fastapi": "0.104+",
    "pandas": "2.2.3",
    "numpy": "2.2.3",
    "scikit-learn": "1.6.1",
    "python": "3.13.2"
  },
  "active_jobs_count": 0,
  "database_connected": false
}
```

---

## 5. Automated Test Suite Execution

Run the complete test suite (87 tests) to verify system integrity:

```powershell
# Run all unit, integration, and API tests
python -m pytest tests/ -v
```

All 87 tests must report `PASSED`.

---

## 6. Commercial Royalty License Enforcement

RevenueOS is licensed under the **RevenueOS Commercial Royalty License**.
* **Strict Non-Commercial Use**: Testing, academic review, and local evaluation are permitted without fee.
* **Commercial Royalty Mandate**: Any commercial deployment, SaaS hosting, fee-bearing analysis, consulting deliverable, or profit-generating use requires express written agreement and royalty remittances. Contact: **Sarvesh Sharma**.
