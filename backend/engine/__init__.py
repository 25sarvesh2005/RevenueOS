"""
RevenueOS Engine Package
========================
Provides unified canonical engine (CoreEngine), Kimball star schema decomposition,
DAX measure synthesis, TMSL/PBIP generation, and pipeline engines.
"""

from backend.engine.core import (
    CoreEngine,
    BackendEngine,
    ExcelToPowerBIEngine,
    ColumnMeta,
    TableMeta,
    RelationshipMeta,
    DaxMeasureMeta,
    clean_identifier,
    format_title,
)
from backend.engine.pipeline_engine import PipelineEngine, PipelineRunResult, PhaseResult

__all__ = [
    "CoreEngine",
    "BackendEngine",
    "ExcelToPowerBIEngine",
    "PipelineEngine",
    "PipelineRunResult",
    "PhaseResult",
    "ColumnMeta",
    "TableMeta",
    "RelationshipMeta",
    "DaxMeasureMeta",
    "clean_identifier",
    "format_title",
]
