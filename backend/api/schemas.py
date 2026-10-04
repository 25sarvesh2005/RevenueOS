"""
RevenueOS API Data Schemas & Pydantic Models
============================================
Defines typed request and response contracts for all REST endpoints.
"""

from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field


class JobStatus(str, Enum):
    PENDING = "PENDING"
    RUNNING = "RUNNING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"


class JobProgress(BaseModel):
    progress: int = Field(0, ge=0, le=100, description="Completion percentage")
    stage: Optional[str] = Field(None, description="Current stage description")
    message: Optional[str] = Field(None, description="Status update message")



class PipelineRunResponse(BaseModel):
    job_id: str = Field(..., description="Unique job execution identifier")
    status: JobStatus = Field(JobStatus.PENDING, description="Initial execution state")
    message: str = Field(..., description="Status description")
    created_at: str = Field(..., description="ISO 8601 creation timestamp")


class JobStatusResponse(BaseModel):
    job_id: str = Field(..., description="Unique job execution identifier")
    status: JobStatus = Field(..., description="Current job status")
    progress: int = Field(0, ge=0, le=100, description="Completion percentage (0-100)")
    stage: Optional[str] = Field(None, description="Current execution stage description")
    message: Optional[str] = Field(None, description="Latest status message or log line")
    created_at: str = Field(..., description="ISO 8601 creation timestamp")
    completed_at: Optional[str] = Field(None, description="ISO 8601 completion timestamp")
    duration_seconds: Optional[float] = Field(None, description="Execution duration in seconds")
    error: Optional[str] = Field(None, description="Error message if failed")
    manifest_summary: Optional[Dict[str, Any]] = Field(None, description="Summary metrics if completed")


class DaxEvaluateRequest(BaseModel):
    expression: str = Field(..., description="DAX formula (e.g., SUM(orders[revenue]), Gross Profit)")
    job_id: Optional[str] = Field(None, description="Optional job ID to evaluate against a completed dataset")
    table: Optional[str] = Field(None, description="Optional target table name override")


class DaxEvaluateResponse(BaseModel):
    expression: str = Field(..., description="Original formula expression")
    status: str = Field(..., description="'SUCCESS' or 'ERROR'")
    evaluated_value: Optional[Any] = Field(None, description="Raw numeric or text value")
    formatted_value: Optional[str] = Field(None, description="Human-formatted representation (currency, %, etc.)")
    data_type: str = Field("string", description="Inferred return type")
    execution_time_ms: float = Field(0.0, description="Computation latency in milliseconds")
    error: Optional[str] = Field(None, description="Error details if evaluation failed")


class HealthCheckResponse(BaseModel):
    status: str = Field(..., description="Operational status: 'HEALTHY' or 'DEGRADED'")
    timestamp: str = Field(..., description="ISO 8601 check timestamp")
    version: str = Field("1.0.0", description="RevenueOS version")
    python_version: str = Field(..., description="Active Python interpreter version")
    workspace_root: str = Field(..., description="Server project root path")
    dependencies: Dict[str, str] = Field(default_factory=dict, description="Core package versions")
    active_jobs_count: int = Field(0, description="Number of tracked jobs in memory")
    database_connected: bool = Field(False, description="PostgreSQL database connectivity status")


class CopilotInvestigateRequest(BaseModel):
    job_id: Optional[str] = Field(None, description="Optional job ID to pull analytical context from")
    entity_type: Optional[str] = Field("Product", description="Entity category: Product, Customer, Channel, Campaign")
    entity_name: Optional[str] = Field(None, description="Entity name or SKU identifier")
    issue: Optional[str] = Field(None, description="Identified anomaly or risk description")
    metric: Optional[str] = Field("gross_margin_pct", description="Impacted financial or operational metric")
    observed_value: Optional[float] = Field(None, description="Actual observed metric value")
    baseline_value: Optional[float] = Field(None, description="Expected benchmark or historical baseline")
    estimated_impact: Optional[float] = Field(0.0, description="Estimated financial impact / leakage amount")
    priority: Optional[str] = Field("HIGH", description="Priority level: LOW, MEDIUM, HIGH, CRITICAL")
    drivers: Optional[List[str]] = Field(default_factory=list, description="Candidate root-cause drivers")
    evidence: Optional[str] = Field(None, description="Observable analytical evidence summary")


class CopilotInvestigateResponse(BaseModel):
    briefing: str = Field(..., description="Evidence-backed executive briefing memo")
    priority: str = Field("HIGH", description="Assigned investigation priority")
    entity_name: str = Field(..., description="Target entity analyzed")
    estimated_impact: float = Field(0.0, description="Total quantified revenue/profit leakage")
    root_causes: List[str] = Field(default_factory=list, description="Derived causal mechanisms")
    action_plan: List[str] = Field(default_factory=list, description="Immediate remediation actions")


class AnnotationCreateRequest(BaseModel):
    job_id: str = Field(..., description="Target pipeline run or job identifier")
    visual_id: str = Field(..., description="Canvas visual or card element ID")
    author: str = Field("Analyst", description="Name or role of person creating note")
    content: str = Field(..., description="Annotation insight or finding content")
    category: str = Field("note", description="Category: note, risk, opportunity, leakage")


class AnnotationResponse(BaseModel):
    id: str = Field(..., description="Unique annotation ID")
    job_id: str = Field(..., description="Job identifier")
    visual_id: str = Field(..., description="Target visual element")
    author: str = Field(..., description="Author")
    content: str = Field(..., description="Content")
    category: str = Field(..., description="Category")
    created_at: str = Field(..., description="Creation timestamp")


class ScheduleCreateRequest(BaseModel):
    cron_expression: str = Field(..., description="Standard 5-part cron syntax or interval descriptor")
    source_excel: str = Field(..., description="Path to source Excel workbook")
    project_name: Optional[str] = Field("RevenueOS_Scheduled", description="Project name")
    currency: Optional[str] = Field("$", description="Currency symbol")
    tenant_id: Optional[str] = Field("default", description="Tenant identifier")


class ScheduleResponse(BaseModel):
    schedule_id: str = Field(..., description="Unique schedule identifier")
    cron_expression: str = Field(..., description="Cron frequency")
    source_excel: str = Field(..., description="Source path")
    project_name: str = Field(..., description="Project name")
    tenant_id: str = Field("default", description="Tenant identifier")
    is_active: bool = Field(True, description="Active status")
    created_at: str = Field(..., description="Creation timestamp")


class TenantRunSummary(BaseModel):
    tenant_id: str = Field(..., description="Tenant identifier")
    job_id: str = Field(..., description="Job execution identifier")
    project_name: str = Field(..., description="Report or project title")
    status: str = Field(..., description="Job execution status")
    created_at: str = Field(..., description="Execution start timestamp")
    completed_at: Optional[str] = Field(None, description="Completion timestamp")
    total_revenue: Optional[float] = Field(None, description="Total Gross Revenue")
    gross_margin_pct: Optional[float] = Field(None, description="Gross Margin %")

