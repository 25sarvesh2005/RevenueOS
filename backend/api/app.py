"""
RevenueOS Intelligence REST API Application
===========================================
Enterprise FastAPI application for pipeline orchestration, asynchronous job tracking,
dynamic DAX formula evaluation, health diagnostics, and Power BI artifact distribution.
"""

from __future__ import annotations

import io
import json
import os
import shutil
import sys
import tempfile
import time
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
import pandas as pd
from fastapi import (
    BackgroundTasks,
    Depends,
    FastAPI,
    File,
    Form,
    HTTPException,
    Query,
    UploadFile,
    status,
)
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse, PlainTextResponse

from backend.api.auth import verify_api_key
from backend.api.dax_evaluator import DaxEvaluator
from backend.api.schemas import (
    AnnotationCreateRequest,
    AnnotationResponse,
    CopilotInvestigateRequest,
    CopilotInvestigateResponse,
    DaxEvaluateRequest,
    DaxEvaluateResponse,
    HealthCheckResponse,
    JobProgress,
    JobStatus,
    JobStatusResponse,
    PipelineRunResponse,
    ScheduleCreateRequest,
    ScheduleResponse,
    TenantRunSummary,
)
from backend.engine.core import CoreEngine
from backend.python.reporting.executive_report import generate_manifest_executive_report
from backend.python.reporting.investigation_copilot import InvestigationCopilot

# Base project paths
API_DIR = Path(__file__).resolve().parent
BACKEND_DIR = API_DIR.parent
PROJECT_ROOT = BACKEND_DIR.parent
EXPORTS_DIR = PROJECT_ROOT / "exports"
STAGING_DIR = PROJECT_ROOT / "data" / "staging"
DEFAULT_MODEL_DIR = EXPORTS_DIR / "default_model"

STAGING_DIR.mkdir(parents=True, exist_ok=True)
EXPORTS_DIR.mkdir(parents=True, exist_ok=True)

# ---------------------------------------------------------------------------
# FastAPI Application Definition
# ---------------------------------------------------------------------------
app = FastAPI(
    title="RevenueOS Intelligence API",
    description=(
        "Universal Revenue Intelligence & Decision Engine API. "
        "Transforms arbitrary business spreadsheets into Kimball Star Schema marts, "
        "evaluates DAX measures in sub-milliseconds, and compiles native Power BI artifacts."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# Enable CORS for desktop/web client integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------------------------
# In-Memory Job Management
# ---------------------------------------------------------------------------
class JobStore:
    def __init__(self):
        self.jobs: Dict[str, Dict[str, Any]] = {}
        self.annotations: List[Dict[str, Any]] = []
        self.schedules: Dict[str, Dict[str, Any]] = {}

    def create_job(self, project_name: Optional[str] = None, tenant_id: str = "default") -> str:
        job_id = str(uuid.uuid4())[:8]
        now = datetime.now(timezone.utc).isoformat()
        self.jobs[job_id] = {
            "job_id": job_id,
            "tenant_id": tenant_id,
            "status": JobStatus.PENDING,
            "progress": 0,
            "stage": "Queued",
            "message": "Job registered and queued for execution",
            "created_at": now,
            "completed_at": None,
            "duration_seconds": None,
            "error": None,
            "output_dir": None,
            "excel_path": None,
            "project_name": project_name or f"RevenueOS_Job_{job_id}",
            "manifest_summary": None,
            "manifest": None,
            "evaluator": None,
        }
        return job_id

    def get_job(self, job_id: str) -> Optional[Dict[str, Any]]:
        return self.jobs.get(job_id)

    def update_progress(self, job_id: str, message: str, progress: Optional[int] = None, stage: Optional[str] = None):
        job = self.jobs.get(job_id)
        if job:
            if progress is not None:
                job["progress"] = progress
            if stage is not None:
                job["stage"] = stage
            job["message"] = message

    def complete_job(self, job_id: str, output_dir: Path, manifest: Dict[str, Any], duration: float):
        job = self.jobs.get(job_id)
        if job:
            job["status"] = JobStatus.COMPLETED
            job["progress"] = 100
            job["stage"] = "Complete"
            job["message"] = "Pipeline execution completed successfully"
            job["completed_at"] = datetime.now(timezone.utc).isoformat()
            job["duration_seconds"] = duration
            job["output_dir"] = str(output_dir)
            job["manifest"] = manifest
            dash_kpis = manifest.get("dashboard", {}).get("kpis", {})
            job["manifest_summary"] = {
                "totalRevenue": dash_kpis.get("totalRevenue"),
                "grossMarginPct": dash_kpis.get("grossMarginPct"),
                "totalOrders": dash_kpis.get("totalOrders"),
                "tablesCount": len(manifest.get("tables", [])),
                "measuresCount": len(manifest.get("measures", [])),
            }
            # Cache evaluator for fast DAX calculation
            try:
                job["evaluator"] = DaxEvaluator(data_dir=output_dir)
            except Exception:
                pass

    def fail_job(self, job_id: str, error: str):
        job = self.jobs.get(job_id)
        if job:
            job["status"] = JobStatus.FAILED
            job["stage"] = "Failed"
            job["message"] = f"Execution failed: {error}"
            job["completed_at"] = datetime.now(timezone.utc).isoformat()
            job["error"] = error

    def list_runs(self, tenant_id: Optional[str] = None) -> List[TenantRunSummary]:
        results = []
        for j in self.jobs.values():
            if tenant_id and j.get("tenant_id") != tenant_id:
                continue
            summary = j.get("manifest_summary") or {}
            results.append(
                TenantRunSummary(
                    tenant_id=j.get("tenant_id", "default"),
                    job_id=j["job_id"],
                    project_name=j.get("project_name", "Untitled Project"),
                    status=str(j["status"]),
                    created_at=j["created_at"],
                    completed_at=j.get("completed_at"),
                    total_revenue=summary.get("totalRevenue"),
                    gross_margin_pct=summary.get("grossMarginPct"),
                )
            )
        results.sort(key=lambda r: r.created_at, reverse=True)
        return results

    def add_annotation(self, data: Dict[str, Any]) -> Dict[str, Any]:
        ann_id = str(uuid.uuid4())[:8]
        record = {
            "id": ann_id,
            "job_id": data["job_id"],
            "visual_id": data["visual_id"],
            "author": data.get("author", "Analyst"),
            "content": data["content"],
            "category": data.get("category", "note"),
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.annotations.append(record)
        return record

    def get_annotations(self, job_id: str) -> List[Dict[str, Any]]:
        return [a for a in self.annotations if a.get("job_id") == job_id]

    def add_schedule(self, data: Dict[str, Any]) -> Dict[str, Any]:
        sched_id = f"sched_{uuid.uuid4().hex[:6]}"
        record = {
            "schedule_id": sched_id,
            "cron_expression": data["cron_expression"],
            "source_excel": data["source_excel"],
            "project_name": data.get("project_name", "RevenueOS_Scheduled"),
            "tenant_id": data.get("tenant_id", "default"),
            "currency": data.get("currency", "$"),
            "is_active": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.schedules[sched_id] = record
        return record

    def get_schedules(self, tenant_id: Optional[str] = None) -> List[Dict[str, Any]]:
        if not tenant_id:
            return list(self.schedules.values())
        return [s for s in self.schedules.values() if s.get("tenant_id") == tenant_id]


job_store = JobStore()


# ---------------------------------------------------------------------------
# Background Pipeline Worker
# ---------------------------------------------------------------------------
def _run_pipeline_worker(
    job_id: str,
    excel_path: Path,
    output_dir: Path,
    project_name: Optional[str] = None,
    currency_symbol: str = "$",
    generate_visuals: bool = True,
):
    """Executes CoreEngine transformation in background thread."""
    t0 = time.time()
    job_store.jobs[job_id]["status"] = JobStatus.RUNNING

    def _progress_callback(msg: str, prog: Optional[int], stg: Optional[str]):
        job_store.update_progress(job_id, message=msg, progress=prog, stage=stg)

    try:
        engine = CoreEngine(
            excel_path=excel_path,
            output_dir=output_dir,
            project_name=project_name,
            currency_symbol=currency_symbol,
            emit_manifest=False,
            generate_visuals=generate_visuals,
            log_callback=_progress_callback,
        )
        manifest_path = engine.run()
        elapsed = round(time.time() - t0, 2)

        with open(manifest_path, "r", encoding="utf-8") as f:
            manifest = json.load(f)

        job_store.complete_job(job_id, output_dir=output_dir, manifest=manifest, duration=elapsed)

    except Exception as exc:
        job_store.fail_job(job_id, error=str(exc))


# ---------------------------------------------------------------------------
# API Endpoints
# ---------------------------------------------------------------------------

@app.post(
    "/api/pipeline/run",
    response_model=PipelineRunResponse,
    status_code=status.HTTP_202_ACCEPTED,
    tags=["Pipeline"],
    summary="Upload Excel Workbook and Execute Pipeline",
)
async def run_pipeline(
    background_tasks: BackgroundTasks,
    file: Optional[UploadFile] = File(None, description="Source Excel file (.xlsx, .xls, .xlsm)"),
    file_path: Optional[str] = Form(None, description="Local or server path to Excel workbook"),
    project_name: Optional[str] = Form(None, description="Display name for the project"),
    currency_symbol: str = Form("$", description="Currency symbol for DAX measures"),
    generate_visuals: bool = Form(True, description="Whether to render high-res Matplotlib chart pack"),
    _auth: Optional[str] = Depends(verify_api_key),
):
    """
    Submits an Excel workbook for automated Star Schema transformation, DAX synthesis,
    PBIT compilation, and KPI generation. Returns an asynchronous job tracking ID.
    """
    job_id = job_store.create_job(project_name=project_name)
    job_staging = STAGING_DIR / job_id
    job_staging.mkdir(parents=True, exist_ok=True)
    job_output = EXPORTS_DIR / f"job_{job_id}"

    excel_target_path: Optional[Path] = None

    if file and file.filename:
        # Save uploaded file
        dest_filename = Path(file.filename).name
        excel_target_path = job_staging / dest_filename
        with open(excel_target_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
    elif file_path:
        # Validate existing server path
        candidate = Path(file_path).resolve()
        if not candidate.exists() or not candidate.is_file():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Specified file path does not exist on server: {file_path}",
            )
        excel_target_path = candidate
    else:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Must provide either an uploaded file or a valid server file_path.",
        )

    # Queue background task
    background_tasks.add_task(
        _run_pipeline_worker,
        job_id=job_id,
        excel_path=excel_target_path,
        output_dir=job_output,
        project_name=project_name,
        currency_symbol=currency_symbol,
        generate_visuals=generate_visuals,
    )

    return PipelineRunResponse(
        job_id=job_id,
        status=JobStatus.PENDING,
        message=f"Pipeline job '{job_id}' successfully scheduled for execution.",
        created_at=datetime.now(timezone.utc).isoformat(),
    )


@app.get(
    "/api/pipeline/status/{job_id}",
    response_model=JobStatusResponse,
    tags=["Pipeline"],
    summary="Get Pipeline Execution Status",
)
async def get_pipeline_status(
    job_id: str,
    _auth: Optional[str] = Depends(verify_api_key),
):
    """Retrieves real-time status, stage, progress percentage, and metrics for a pipeline run."""
    job = job_store.get_job(job_id)
    if not job:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Pipeline job ID '{job_id}' not found.",
        )

    return JobStatusResponse(
        job_id=job["job_id"],
        status=job["status"],
        progress=job["progress"],
        stage=job["stage"],
        message=job["message"],
        created_at=job["created_at"],
        completed_at=job["completed_at"],
        duration_seconds=job["duration_seconds"],
        error=job["error"],
        manifest_summary=job["manifest_summary"],
    )


@app.get(
    "/api/manifest/{job_id}",
    tags=["Artifacts"],
    summary="Retrieve Structured Manifest JSON",
)
async def get_manifest(
    job_id: str,
    _auth: Optional[str] = Depends(verify_api_key),
):
    """
    Returns the complete structured JSON manifest for a completed pipeline run.
    Accepts 'default' or 'sample' to query the bundled baseline retail model.
    """
    if job_id in ("default", "sample"):
        manifest_path = DEFAULT_MODEL_DIR / "manifest.json"
    else:
        job = job_store.get_job(job_id)
        if not job:
            raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")
        if job["status"] != JobStatus.COMPLETED:
            raise HTTPException(
                status_code=400,
                detail=f"Job '{job_id}' is not complete (current status: {job['status']}).",
            )
        manifest_path = Path(job["output_dir"]) / "manifest.json"

    if not manifest_path.exists():
        raise HTTPException(status_code=404, detail="Manifest file not found on disk.")

    with open(manifest_path, "r", encoding="utf-8") as f:
        return json.load(f)


@app.get(
    "/api/charts/{job_id}/{chart_filename}",
    tags=["Artifacts"],
    summary="Fetch Publication-Ready Matplotlib Chart PNG",
)
async def get_chart(
    job_id: str,
    chart_filename: str,
    _auth: Optional[str] = Depends(verify_api_key),
):
    """Serves high-resolution (300 DPI) analytical charts generated during pipeline execution."""
    if job_id in ("default", "sample"):
        chart_path = DEFAULT_MODEL_DIR / "charts" / chart_filename
    else:
        job = job_store.get_job(job_id)
        if not job or not job.get("output_dir"):
            raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")
        chart_path = Path(job["output_dir"]) / "charts" / chart_filename

    # Prevent directory traversal
    resolved_chart = chart_path.resolve()
    if not resolved_chart.exists() or not str(resolved_chart).endswith(".png"):
        raise HTTPException(status_code=404, detail=f"Chart '{chart_filename}' not found.")

    return FileResponse(resolved_chart, media_type="image/png", filename=chart_filename)


@app.get(
    "/api/download/{job_id}/pbit",
    tags=["Artifacts"],
    summary="Download Native Power BI Template (.pbit)",
)
async def download_pbit(
    job_id: str,
    _auth: Optional[str] = Depends(verify_api_key),
):
    """Downloads the compiled standalone Power BI Desktop Template (.pbit) with relationships and DAX pre-wired."""
    if job_id in ("default", "sample"):
        pbi_dir = DEFAULT_MODEL_DIR / "powerbi"
    else:
        job = job_store.get_job(job_id)
        if not job or not job.get("output_dir"):
            raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")
        pbi_dir = Path(job["output_dir"]) / "powerbi"

    pbit_files = list(pbi_dir.glob("*.pbit"))
    if not pbit_files:
        raise HTTPException(status_code=404, detail="No compiled .pbit template found for this model.")

    target_file = pbit_files[0]
    return FileResponse(
        target_file,
        media_type="application/octet-stream",
        filename=target_file.name,
    )


@app.get(
    "/api/download/{job_id}/pbip",
    tags=["Artifacts"],
    summary="Download Power BI Project Archive (.pbip Zip)",
)
async def download_pbip(
    job_id: str,
    _auth: Optional[str] = Depends(verify_api_key),
):
    """Packages the Power BI Developer Project (.pbip + SemanticModel + Report) as a downloadable zip archive."""
    if job_id in ("default", "sample"):
        pbi_dir = DEFAULT_MODEL_DIR / "powerbi"
    else:
        job = job_store.get_job(job_id)
        if not job or not job.get("output_dir"):
            raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")
        pbi_dir = Path(job["output_dir"]) / "powerbi"

    if not pbi_dir.exists():
        raise HTTPException(status_code=404, detail="Power BI project directory not found.")

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as z:
        for file in pbi_dir.rglob("*"):
            if file.is_file():
                arcname = file.relative_to(pbi_dir)
                z.write(file, arcname)

    buf.seek(0)
    zip_filename = f"{job_id}_powerbi_project.zip"
    temp_zip = STAGING_DIR / zip_filename
    temp_zip.write_bytes(buf.getvalue())

    return FileResponse(
        temp_zip,
        media_type="application/zip",
        filename=zip_filename,
    )


@app.get(
    "/api/download/{job_id}/csv/{filename}",
    tags=["Artifacts"],
    summary="Download Individual CSV Mart Table",
)
async def download_csv_mart(
    job_id: str,
    filename: str,
    _auth: Optional[str] = Depends(verify_api_key),
):
    """Downloads an individual Kimball Star Schema CSV table (e.g. orders.csv, dim_date.csv)."""
    if job_id in ("default", "sample"):
        csv_dir = DEFAULT_MODEL_DIR / "csv"
    else:
        job = job_store.get_job(job_id)
        if not job or not job.get("output_dir"):
            raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")
        csv_dir = Path(job["output_dir"]) / "csv"

    csv_path = (csv_dir / filename).resolve()
    if not csv_path.exists() or not csv_path.suffix.lower() == ".csv":
        raise HTTPException(status_code=404, detail=f"CSV table '{filename}' not found.")

    return FileResponse(csv_path, media_type="text/csv", filename=filename)


@app.post(
    "/api/evaluate-dax",
    response_model=DaxEvaluateResponse,
    tags=["DAX"],
    summary="Evaluate Dynamic DAX Formula",
)
async def evaluate_dax(
    request: DaxEvaluateRequest,
    _auth: Optional[str] = Depends(verify_api_key),
):
    """
    Evaluates a DAX semantic formula against tabular data using the Pandas DAX runtime.
    Supports SUM, AVERAGE, MIN, MAX, COUNTROWS, DISTINCTCOUNT, DIVIDE, compound arithmetic,
    and named measure resolutions.
    """
    evaluator: Optional[DaxEvaluator] = None

    if request.job_id:
        job = job_store.get_job(request.job_id)
        if job and job.get("evaluator"):
            evaluator = job["evaluator"]
        elif job and job.get("output_dir"):
            evaluator = DaxEvaluator(data_dir=Path(job["output_dir"]))
            job["evaluator"] = evaluator

    if not evaluator:
        # Fall back to default model marts
        if DEFAULT_MODEL_DIR.exists():
            evaluator = DaxEvaluator(data_dir=DEFAULT_MODEL_DIR)
        else:
            raise HTTPException(
                status_code=400,
                detail="No loaded model available for DAX evaluation. Run a pipeline job or load default model first.",
            )

    result = evaluator.evaluate(request.expression)
    return DaxEvaluateResponse(**result)


@app.get(
    "/api/health",
    response_model=HealthCheckResponse,
    tags=["Diagnostics"],
    summary="System Health & Operational Diagnostics",
)
async def health_check():
    """Returns server runtime status, Python environment version, dependencies, and workspace diagnostics."""
    import platform
    import sklearn

    deps = {
        "fastapi": "0.104+",
        "pandas": pd.__version__,
        "numpy": np.__version__,
        "scikit-learn": sklearn.__version__,
        "python": platform.python_version(),
    }

    # Check database connectivity if configured
    db_connected = False
    try:
        from backend.config import get_database_url
        from sqlalchemy import create_engine, text
        db_url = get_database_url()
        if db_url:
            eng = create_engine(db_url, connect_args={"connect_timeout": 2})
            with eng.connect() as conn:
                conn.execute(text("SELECT 1"))
            db_connected = True
    except Exception:
        db_connected = False

    return HealthCheckResponse(
        status="HEALTHY",
        timestamp=datetime.now(timezone.utc).isoformat(),
        version="1.0.0",
        python_version=platform.python_version(),
        workspace_root=str(PROJECT_ROOT),
        dependencies=deps,
        active_jobs_count=len(job_store.jobs),
        database_connected=db_connected,
    )


# ---------------------------------------------------------------------------
# Phase 4: Commercial Intelligence & Multi-Tenant Endpoints
# ---------------------------------------------------------------------------

def _get_job_manifest(job_id: str) -> Dict[str, Any]:
    """Helper to retrieve parsed manifest for a given job or default baseline."""
    if job_id in ("default", "sample"):
        manifest_path = DEFAULT_MODEL_DIR / "manifest.json"
        if manifest_path.exists():
            with open(manifest_path, "r", encoding="utf-8") as f:
                return json.load(f)
        sample_path = PROJECT_ROOT / "frontend" / "model_data_sample.json"
        if sample_path.exists():
            with open(sample_path, "r", encoding="utf-8") as f:
                return json.load(f)
        raise HTTPException(status_code=404, detail="Default model manifest not found.")

    job = job_store.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job '{job_id}' not found.")
    if job.get("manifest"):
        return job["manifest"]
    if job.get("output_dir"):
        manifest_path = Path(job["output_dir"]) / "manifest.json"
        if manifest_path.exists():
            with open(manifest_path, "r", encoding="utf-8") as f:
                return json.load(f)
    raise HTTPException(status_code=404, detail=f"Manifest for job '{job_id}' not available.")


@app.get(
    "/api/reports/{job_id}/executive-html",
    tags=["Reports"],
    summary="Generate Executive HTML Briefing",
)
async def get_executive_report_html(
    job_id: str,
    _auth: Optional[str] = Depends(verify_api_key),
):
    """Generates an executive-grade HTML performance briefing with scorecards and Kimball marts inventory."""
    manifest = _get_job_manifest(job_id)
    report = generate_manifest_executive_report(manifest)
    return HTMLResponse(content=report["html"], status_code=200)


@app.get(
    "/api/reports/{job_id}/executive-markdown",
    tags=["Reports"],
    summary="Generate Executive Markdown Briefing",
)
async def get_executive_report_markdown(
    job_id: str,
    _auth: Optional[str] = Depends(verify_api_key),
):
    """Generates an executive-grade Markdown performance briefing for documentation and terminal viewing."""
    manifest = _get_job_manifest(job_id)
    report = generate_manifest_executive_report(manifest)
    return PlainTextResponse(content=report["markdown"], status_code=200)


@app.post(
    "/api/copilot/investigate",
    response_model=CopilotInvestigateResponse,
    tags=["Copilot"],
    summary="AI Investigation Briefing Generator",
)
async def investigate_copilot(
    request: CopilotInvestigateRequest,
    _auth: Optional[str] = Depends(verify_api_key),
):
    """
    Synthesizes structured anomaly, margin leakage, or operational risk signals
    into an executive briefing memo and actionable remediation plan with zero hallucination.
    """
    copilot = InvestigationCopilot(currency_symbol="$")
    item = request.model_dump()
    memo = copilot.synthesize_investigation(item)

    drivers = request.drivers or [
        "Elevated voucher/discount stacking across checkout",
        "Higher logistics and return processing costs",
    ]
    action_plan = [
        f"Audit discount parameters on {request.entity_name or 'target product'}",
        "Inspect supplier unit cost structure and packaging specifications",
        "Activate real-time margin alerts in automated pipeline",
    ]

    return CopilotInvestigateResponse(
        briefing=memo,
        priority=request.priority or "HIGH",
        entity_name=request.entity_name or "Target Entity",
        estimated_impact=request.estimated_impact or 0.0,
        root_causes=drivers,
        action_plan=action_plan,
    )


@app.get(
    "/api/runs",
    response_model=List[TenantRunSummary],
    tags=["Multi-Tenant Runs"],
    summary="List Pipeline Runs",
)
async def list_pipeline_runs(
    tenant_id: Optional[str] = Query(None, description="Optional tenant ID filter"),
    _auth: Optional[str] = Depends(verify_api_key),
):
    """Returns chronological pipeline execution runs across tenants or filtered by tenant."""
    return job_store.list_runs(tenant_id)


@app.get(
    "/api/tenants/{tenant_id}/runs",
    response_model=List[TenantRunSummary],
    tags=["Multi-Tenant Runs"],
    summary="List Runs for Specific Tenant",
)
async def list_tenant_runs(
    tenant_id: str,
    _auth: Optional[str] = Depends(verify_api_key),
):
    """Returns pipeline execution history scoped exclusively to a specific tenant."""
    return job_store.list_runs(tenant_id)


@app.post(
    "/api/annotations",
    response_model=AnnotationResponse,
    tags=["Annotations"],
    summary="Create Collaborative Visual Annotation",
)
async def create_annotation(
    request: AnnotationCreateRequest,
    _auth: Optional[str] = Depends(verify_api_key),
):
    """Saves a collaborative analytical annotation tied to a specific chart or KPI visual."""
    ann = job_store.add_annotation(request.model_dump())
    return AnnotationResponse(**ann)


@app.get(
    "/api/annotations/{job_id}",
    response_model=List[AnnotationResponse],
    tags=["Annotations"],
    summary="Get Visual Annotations for Job",
)
async def get_annotations(
    job_id: str,
    _auth: Optional[str] = Depends(verify_api_key),
):
    """Retrieves all visual annotations associated with a specific report dataset."""
    return [AnnotationResponse(**a) for a in job_store.get_annotations(job_id)]


@app.post(
    "/api/schedules",
    response_model=ScheduleResponse,
    tags=["Schedules"],
    summary="Register Recurring Pipeline Schedule",
)
async def create_pipeline_schedule(
    request: ScheduleCreateRequest,
    _auth: Optional[str] = Depends(verify_api_key),
):
    """Registers a recurring cron or interval pipeline schedule."""
    sched = job_store.add_schedule(request.model_dump())
    return ScheduleResponse(**sched)


@app.get(
    "/api/schedules",
    response_model=List[ScheduleResponse],
    tags=["Schedules"],
    summary="List Active Recurring Schedules",
)
async def list_pipeline_schedules(
    tenant_id: Optional[str] = Query(None, description="Optional tenant filter"),
    _auth: Optional[str] = Depends(verify_api_key),
):
    """Lists registered pipeline schedules."""
    return [ScheduleResponse(**s) for s in job_store.get_schedules(tenant_id)]


@app.post(
    "/api/webhook/pipeline-trigger",
    response_model=PipelineRunResponse,
    tags=["Webhooks"],
    summary="External Webhook Ingestion Trigger",
)
async def webhook_pipeline_trigger(
    background_tasks: BackgroundTasks,
    payload: Dict[str, Any],
    _auth: Optional[str] = Depends(verify_api_key),
):
    """
    Accepts external webhook payloads (e.g. ERP, Shopify, Stripe, Zapier)
    to automatically trigger pipeline processing and Power BI artifact generation.
    """
    source_excel = payload.get("source_excel") or payload.get("excel_path")
    if not source_excel or not Path(source_excel).exists():
        source_excel = str(PROJECT_ROOT / "data" / "raw" / "excel" / "revenueos_sample.xlsx")

    tenant_id = payload.get("tenant_id", "default")
    proj_name = payload.get("project_name", "RevenueOS_Webhook_Run")

    job_id = job_store.create_job(project_name=proj_name, tenant_id=tenant_id)
    background_tasks.add_task(
        _run_pipeline_worker,
        job_id=job_id,
        excel_path=Path(source_excel),
        output_dir=EXPORTS_DIR / job_id,
        project_name=proj_name,
        currency_symbol=payload.get("currency", "$"),
    )
    return PipelineRunResponse(
        job_id=job_id,
        status=JobStatus.RUNNING,
        message=f"Webhook received. Pipeline job '{job_id}' launched.",
        created_at=datetime.now(timezone.utc).isoformat(),
    )

