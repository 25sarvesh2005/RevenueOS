# RevenueOS — Pipeline Operations & Automation Runbook
**Engineering Runbook for Production Batch, Scheduled, and Streaming Ingestion**  
*Document Version: 1.0.0 · Author: Sarvesh Sharma · License: RevenueOS Commercial Royalty License*

---

## 1. System Pipeline Architecture

The RevenueOS ingestion pipeline operates as a deterministic, multi-phase transformation engine converting arbitrary commercial spreadsheets into validated star schemas and native Power BI artifacts.

```
[Raw Excel File] (.xlsx, .xls, .xlsm)
        │
        ▼
 Phase 1: Workbook Profiling & Sheet Discovery
        │
        ▼
 Phase 2: Schema Inference & Entity Normalization
        │
        ▼
 Phase 3: Data Quality Audit & Anomaly Detection
        │
        ▼
 Phase 4: Kimball Star Schema Mart Generation (CSVs)
        │
        ▼
 Phase 5: Semantic DAX Synthesis (180+ Measures)
        │
        ▼
 Phase 6: Power BI Native Template Compilation (.pbit / .pbip)
        │
        ▼
 Phase 7: 300 DPI Publication Charts (Matplotlib)
        │
        ▼
 Phase 8: Manifest Generation & IPC Streaming Emission
```

---

## 2. Ingestion Execution Modes

### Mode A: Desktop Interactive Pipeline (Electron GUI)
* **Trigger**: Click **"Get Data"** or **"Load Sample Dataset"** in RevenueOS Studio.
* **Mechanism**: Electron main process spawns `backend/engine/core.py` as an isolated subprocess with stdout/stderr JSON streaming.
* **Progress Protocol**:
  - `PIPELINE_PROGRESS: {"progress": int, "stage": str, "message": str}`
  - `PIPELINE_COMPLETE: <json_manifest>`

### Mode B: Enterprise REST API (Headless Service)
* **Trigger**: HTTP POST request to FastAPI endpoint.
* **Endpoint**: `POST /api/pipeline/run` (multipart file upload or server file path).
* **Sample Trigger**: `POST /api/pipeline/run-sample`.
* **Status Polling**: `GET /api/pipeline/status/{job_id}`.
* **Authentication**: Include `X-RevenueOS-API-Key: <token>` header if configured.

```bash
# Example cURL: Trigger pipeline via REST
curl -X POST "http://127.0.0.1:8000/api/pipeline/run" \
  -H "X-RevenueOS-API-Key: YOUR_API_KEY" \
  -F "file=@data/raw/excel/revenueos_sample.xlsx" \
  -F "project_name=Quarterly_Q3_Financials" \
  -F "currency_symbol=$"
```

### Mode C: Direct CLI Execution (Batch / Automated Scripts)
```powershell
# Run canonical CoreEngine directly
python backend/engine/core.py data/raw/excel/revenueos_sample.xlsx `
  --output-dir exports/manual_run `
  --project-name "Enterprise_Batch" `
  --currency "$"
```

### Mode D: External Webhook Trigger (ERP / Zapier / Shopify)
* **Endpoint**: `POST /api/webhook/pipeline-trigger`
* **JSON Payload**:
```json
{
  "source_excel": "data/raw/excel/revenueos_sample.xlsx",
  "project_name": "Shopify_Daily_Ingest",
  "tenant_id": "tenant_acme",
  "currency": "$"
}
```

---

## 3. Pipeline Phase Detail & Invariants

| Phase | Engine Method | Primary Output | Invariant / Failure Condition |
| :---: | :--- | :--- | :--- |
| **1** | `_profile_workbook()` | Sheet catalog | At least 1 valid tabular sheet must contain rows. |
| **2** | `_infer_star_schema()` | Entities (Fact/Dims) | Fact table must resolve at least 1 date/key column. |
| **3** | `_audit_data_quality()`| Quality scores & flags | Null primary keys or negative prices rejected/flagged. |
| **4** | `_generate_csv_marts()`| `csv/*.csv` | UTF-8 encoded, comma-delimited clean relational tables. |
| **5** | `_synthesize_dax()` | `manifest.measures` | All synthesized formulas verified against schema. |
| **6** | `_compile_powerbi()` | `.pbit`, `.pbip` | Valid zip container with TMSL semantic model definition. |
| **7** | `_generate_charts()` | `charts/*.png` | 6 publication figures rendered at 300 DPI. |
| **8** | `_emit_manifest()` | `manifest.json` | Comprehensive machine-readable execution manifest. |

---

## 4. Failure Modes, Diagnostic Codes & Recovery

### Code ERR_EXCEL_CORRUPT (Exit Code 21)
* **Symptom**: `openpyxl` fails to parse workbook structure.
* **Root Cause**: Corrupted binary file, password-protected sheet, or unclosed file handle from another application.
* **Resolution**:
  1. Verify file is not locked in Excel: Close file on desktop.
  2. Verify file is uncorrupted: Run `python -c "import openpyxl; openpyxl.load_workbook('<file>')"`
  3. Ensure workbook has at least 1 sheet with numeric transaction headers.

### Code ERR_SCHEMA_AMBIGUOUS (Exit Code 22)
* **Symptom**: Pipeline cannot isolate fact table or primary key.
* **Root Cause**: Spreadsheet lacks order IDs or date columns.
* **Resolution**: Ensure source spreadsheet contains a column with `date`, `order`, or `invoice` in header.

### Code ERR_PERMISSION_DENIED (Exit Code 13)
* **Symptom**: Subprocess cannot write to target `exports/` folder.
* **Resolution**: Ensure user has write permissions in workspace directory.

---

## 5. Commercial Royalty License Notice

This pipeline engine, its orchestration runbook, and data compilation routines are protected intellectual property under the **RevenueOS Commercial Royalty License**.
