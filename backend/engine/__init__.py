"""
RevenueOS Engine Package
========================
Provides unified master engine, Kimball star schema decomposition,
DAX measure synthesis, TMSL/PBIP generation, and pipeline engines.
"""

from backend.engine.master import BackendEngine, clean_identifier, format_title
from backend.engine.pipeline_engine import PipelineEngine, PipelineRunResult, PhaseResult
from backend.engine.excel_to_powerbi import ExcelToPowerBIEngine

__all__ = [
    "BackendEngine",
    "PipelineEngine",
    "PipelineRunResult",
    "PhaseResult",
    "ExcelToPowerBIEngine",
    "clean_identifier",
    "format_title"
]
