"""
RevenueOS – Core Engine
=======================
Canonical, production-grade universal engine that ingests ANY Excel file,
infers Kimball Star Schema, generates clean CSV marts, writes tailored DAX measures,
compiles native Power BI Template (.pbit) and Project (.pbip), generates high-resolution
analytical charts, and produces complete structured manifests for the RevenueOS platform.
"""

from __future__ import annotations

import argparse
import io
import json
import os
import re
import sys
import uuid
import zipfile
from dataclasses import asdict, dataclass, field
from datetime import datetime, date, timedelta
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import pandas as pd
import numpy as np

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker


def clean_identifier(name: str) -> str:
    """Sanitize strings into clean SQL/Power BI table and column names."""
    s = str(name).strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s-]+", "_", s)
    s = re.sub(r"_+", "_", s)
    s = s.lower().strip("_")
    return s or "unnamed"


def format_title(identifier: str) -> str:
    """Convert snake_case identifier to Clean Title Case."""
    words = identifier.replace("_", " ").split()
    return " ".join(w.capitalize() for w in words)


@dataclass
class ColumnMeta:
    name: str
    original_name: str
    dtype: str  # 'string', 'int64', 'double', 'datetime', 'boolean'
    is_key: bool = False
    is_foreign_key: bool = False
    is_metric: bool = False
    is_date: bool = False
    is_category: bool = False
    sample_values: List[Any] = field(default_factory=list)
    null_count: int = 0
    unique_count: int = 0


@dataclass
class TableMeta:
    name: str
    original_sheet: str
    table_type: str  # 'fact', 'dimension', 'calendar', 'bridge'
    row_count: int
    columns: List[ColumnMeta]
    primary_key: Optional[str] = None
    composite_keys: List[str] = field(default_factory=list)
    date_column: Optional[str] = None
    csv_filename: str = ""
    preview_rows: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class RelationshipMeta:
    from_table: str
    from_column: str
    to_table: str
    to_column: str
    cardinality: str = "OneToMany"  # 1 : *
    cross_filtering: str = "OneDirection"


@dataclass
class DaxMeasureMeta:
    name: str
    expression: str
    category: str
    description: str
    format_string: str = "#,0"
    table_name: str = "_Measures"


class CoreEngine:
    """
    Consolidated Canonical Pipeline & Analytics Engine.
    Converts arbitrary Excel workbooks into Power BI Star Schema marts,
    generates DAX measures, .pbit/.pbip artifacts, and dashboard aggregations.
    """

    def __init__(
        self,
        excel_path: str | Path,
        output_dir: Optional[str | Path] = None,
        project_name: Optional[str] = None,
        currency_symbol: str = "$",
        emit_manifest: bool = True,
        generate_visuals: bool = True,
        log_callback: Optional[Callable[[str, Optional[int], Optional[str]], None]] = None,
    ):
        self.excel_path = Path(excel_path).resolve()
        if not self.excel_path.exists():
            raise FileNotFoundError(f"Source Excel file not found: {self.excel_path}")

        stem = clean_identifier(self.excel_path.stem)
        self.project_name = project_name or format_title(stem)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        if output_dir:
            self.output_dir = Path(output_dir).resolve()
        else:
            self.output_dir = (self.excel_path.parent / f"powerbi_export_{stem}_{timestamp}").resolve()

        self.csv_dir = self.output_dir / "csv"
        self.powerbi_dir = self.output_dir / "powerbi"
        self.charts_dir = self.output_dir / "charts"
        self.currency_symbol = currency_symbol
        self.emit_manifest = emit_manifest
        self.generate_visuals = generate_visuals
        self.log_callback = log_callback

        # Internal state
        self.raw_frames: Dict[str, pd.DataFrame] = {}
        self.processed_frames: Dict[str, pd.DataFrame] = {}
        self.tables: List[TableMeta] = []
        self.relationships: List[RelationshipMeta] = []
        self.dax_measures: List[DaxMeasureMeta] = []
        self.charts: List[Dict[str, Any]] = []
        self.min_date: Optional[datetime] = None
        self.max_date: Optional[datetime] = None
        self.logs: List[str] = []

    def _log(self, message: str, progress: Optional[int] = None, stage: Optional[str] = None) -> None:
        """Record and optionally stream progress event to stdout as JSON."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        entry = f"[{timestamp}] {message}"
        self.logs.append(entry)

        if self.log_callback:
            try:
                self.log_callback(message, progress, stage)
            except Exception:
                pass

        if self.emit_manifest:
            payload = {"message": message}
            if progress is not None:
                payload["progress"] = progress
            if stage is not None:
                payload["stage"] = stage
            print(f"EVENT_JSON:{json.dumps(payload)}", flush=True)

    def load_and_profile_sheets(self) -> None:
        """Step 1: Read all sheets and profile columns, keys, and metrics."""
        self._log(f"Reading workbook: {self.excel_path.name}", progress=10, stage="Loading Excel")
        excel_file = pd.ExcelFile(self.excel_path)
        sheet_names = excel_file.sheet_names
        self._log(f"Found {len(sheet_names)} sheet(s): {', '.join(sheet_names)}", progress=15)

        for sheet in sheet_names:
            df = excel_file.parse(sheet)
            if df.empty or len(df.columns) == 0:
                continue

            clean_cols = {}
            for col in df.columns:
                c = clean_identifier(str(col))
                base_c = c
                idx = 1
                while c in clean_cols.values():
                    c = f"{base_c}_{idx}"
                    idx += 1
                clean_cols[col] = c

            df = df.rename(columns=clean_cols)
            df = df.dropna(how="all").dropna(axis=1, how="all")
            table_name = clean_identifier(sheet)
            self.raw_frames[table_name] = df
            self._log(f"Loaded '{table_name}': {len(df)} rows, {len(df.columns)} columns")

        if not self.raw_frames:
            raise ValueError("The provided Excel file contains no valid tabular data.")

    def _make_safe_previews(self, df: pd.DataFrame, n: int = 50) -> List[Dict[str, Any]]:
        """Extract JSON-safe preview records for Electron Data View."""
        sample = df.head(n).copy()
        for col in sample.columns:
            if pd.api.types.is_datetime64_any_dtype(sample[col]):
                sample[col] = sample[col].dt.strftime("%Y-%m-%d").fillna("")
            elif pd.api.types.is_float_dtype(sample[col]):
                sample[col] = sample[col].apply(lambda x: round(float(x), 2) if pd.notnull(x) else "")
            elif pd.api.types.is_integer_dtype(sample[col]):
                sample[col] = sample[col].apply(lambda x: int(x) if pd.notnull(x) else "")
            else:
                sample[col] = sample[col].fillna("").astype(str)
        return sample.to_dict(orient="records")

    def _infer_column_meta(self, df: pd.DataFrame, col: str) -> ColumnMeta:
        """Infer type, metric, key, and date status of a column."""
        series = df[col]
        null_count = int(series.isna().sum())
        non_null = series.dropna()
        unique_count = int(series.nunique())
        total_rows = len(df)

        col_lower = col.lower()
        is_date = False
        is_metric = False
        is_key = False
        is_category = False
        dtype = "string"

        if pd.api.types.is_datetime64_any_dtype(series):
            is_date = True
            dtype = "datetime"
        elif any(k in col_lower for k in ["date", "timestamp", "created_at", "updated_at", "time", "day"]):
            try:
                converted = pd.to_datetime(non_null.head(100), errors="coerce", format="mixed")
                if converted.notna().sum() > len(converted) * 0.7:
                    is_date = True
                    dtype = "datetime"
            except Exception:
                pass

        if not is_date:
            if pd.api.types.is_numeric_dtype(series):
                is_int = pd.api.types.is_integer_dtype(series) or (non_null % 1 == 0).all() if len(non_null) > 0 else False
                dtype = "int64" if is_int else "double"
                if any(k in col_lower for k in ["id", "key", "code", "zip", "postal", "phone", "year", "quarter"]):
                    is_key = True
                else:
                    is_metric = True
            elif pd.api.types.is_bool_dtype(series):
                dtype = "boolean"
            else:
                dtype = "string"
                if any(k in col_lower for k in ["id", "key", "code", "num", "no"]):
                    is_key = True
                else:
                    is_category = True

        if unique_count == total_rows and total_rows > 0:
            if is_key or any(k in col_lower for k in ["id", "key", "code"]):
                is_key = True

        sample_vals = [str(v) for v in non_null.head(3).tolist()]

        return ColumnMeta(
            name=col,
            original_name=col,
            dtype=dtype,
            is_key=is_key,
            is_metric=is_metric,
            is_date=is_date,
            is_category=is_category,
            sample_values=sample_vals,
            null_count=null_count,
            unique_count=unique_count
        )

    def analyze_and_build_model(self) -> None:
        """Step 2: Infer Star Schema, Facts, Dimensions, Dates, and Relationships."""
        self._log("Analyzing dimensional model & relationships...", progress=30, stage="Modeling Star Schema")

        intermediate_tables: Dict[str, TableMeta] = {}
        temp_data: Dict[str, Dict[str, Any]] = {}

        for tbl_name, df in self.raw_frames.items():
            cols_meta = [self._infer_column_meta(df, c) for c in df.columns]
            pk = None
            date_col = None

            for c in cols_meta:
                if (c.is_key or "id" in c.name.lower() or "key" in c.name.lower()) and c.unique_count == len(df) and pk is None:
                    pk = c.name
                if c.is_date and date_col is None:
                    date_col = c.name
                    try:
                        dates = pd.to_datetime(df[c.name].dropna(), errors="coerce", format="mixed")
                        valid_dates = dates[dates.notna()]
                        if not valid_dates.empty:
                            s_min = valid_dates.min().to_pydatetime()
                            s_max = valid_dates.max().to_pydatetime()
                            if self.min_date is None or s_min < self.min_date:
                                self.min_date = s_min
                            if self.max_date is None or s_max > self.max_date:
                                self.max_date = s_max
                    except Exception:
                        pass

            # Infer composite candidate keys if no single primary key
            composite_keys = []
            if pk is None and len(df) > 1:
                key_cands = [c.name for c in cols_meta if c.is_key or any(k in c.name.lower() for k in ["id", "key", "code", "line", "seq", "num"])]
                if len(key_cands) >= 2:
                    import itertools
                    for combo in itertools.combinations(key_cands, 2):
                        if df.drop_duplicates(subset=list(combo)).shape[0] == len(df):
                            composite_keys = list(combo)
                            break

            temp_data[tbl_name] = {
                "df": df,
                "cols_meta": cols_meta,
                "pk": pk,
                "composite_keys": composite_keys,
                "date_col": date_col,
                "has_metric": any(c.is_metric for c in cols_meta)
            }

        # Classify Dimensions vs Facts
        dim_names_hints = ["customer", "product", "client", "user", "store", "supplier", "vendor", "channel", "category", "employee", "item", "dim"]
        fact_names_hints = ["order", "sale", "trans", "payment", "return", "inventory", "marketing", "event", "fact", "line", "detail"]

        for tbl_name, info in temp_data.items():
            t_lower = tbl_name.lower()
            is_referenced = False
            if info["pk"]:
                pk_name = info["pk"].lower()
                for other_name, other_info in temp_data.items():
                    if other_name != tbl_name:
                        for col in other_info["cols_meta"]:
                            if col.name.lower() == pk_name:
                                is_referenced = True
                                break

            if any(hint in t_lower for hint in dim_names_hints) or (info["pk"] is not None and is_referenced):
                table_type = "dimension"
            elif any(hint in t_lower for hint in fact_names_hints):
                table_type = "fact"
            elif info["has_metric"] or info["date_col"] is not None:
                table_type = "fact"
            elif info["pk"] is not None:
                table_type = "dimension"
            else:
                table_type = "fact"

            df = info["df"]
            previews = self._make_safe_previews(df, 50)

            table_meta = TableMeta(
                name=tbl_name,
                original_sheet=tbl_name,
                table_type=table_type,
                row_count=len(df),
                columns=info["cols_meta"],
                primary_key=info["pk"],
                composite_keys=info.get("composite_keys", []),
                date_column=info["date_col"],
                csv_filename=f"{tbl_name}.csv",
                preview_rows=previews
            )
            intermediate_tables[tbl_name] = table_meta
            self.processed_frames[tbl_name] = df

        # Single Sheet Auto-Decomposition if only 1 sheet uploaded
        if len(self.raw_frames) == 1:
            self._decompose_single_sheet(list(self.raw_frames.keys())[0], intermediate_tables)

        # Build dim_date Calendar Dimension
        if self.min_date and self.max_date:
            self._log(f"Detected date range: {self.min_date.strftime('%Y-%m-%d')} to {self.max_date.strftime('%Y-%m-%d')}")
            dim_date_df = self._generate_calendar_dimension(self.min_date, self.max_date)
            date_cols_meta = [self._infer_column_meta(dim_date_df, c) for c in dim_date_df.columns]
            dim_date_meta = TableMeta(
                name="dim_date",
                original_sheet="[Generated Calendar]",
                table_type="dimension",
                row_count=len(dim_date_df),
                columns=date_cols_meta,
                primary_key="date",
                date_column="date",
                csv_filename="dim_date.csv",
                preview_rows=self._make_safe_previews(dim_date_df, 50)
            )
            intermediate_tables["dim_date"] = dim_date_meta
            self.processed_frames["dim_date"] = dim_date_df

        self.tables = list(intermediate_tables.values())
        self._detect_relationships()

    def _decompose_single_sheet(self, sheet_name: str, intermediate_tables: Dict[str, TableMeta]) -> None:
        """If user uploaded a single denormalized table, extract logical dimensions."""
        df = self.raw_frames[sheet_name]
        cols = df.columns
        extracted_dims = {}

        cust_cols = [c for c in cols if any(k in c.lower() for k in ["customer", "client", "buyer"])]
        cust_id = next((c for c in cust_cols if any(k in c.lower() for k in ["id", "code", "key", "number"])), None)
        if cust_id and len(cust_cols) > 1:
            dim_cust_df = df[cust_cols].drop_duplicates(subset=[cust_id]).dropna(subset=[cust_id])
            if len(dim_cust_df) < len(df) * 0.95:
                extracted_dims["dim_customer"] = (dim_cust_df, cust_id)

        prod_cols = [c for c in cols if any(k in c.lower() for k in ["product", "item", "sku", "article"])]
        prod_id = next((c for c in prod_cols if any(k in c.lower() for k in ["id", "code", "key", "sku"])), None)
        if prod_id and len(prod_cols) > 1:
            dim_prod_df = df[prod_cols].drop_duplicates(subset=[prod_id]).dropna(subset=[prod_id])
            if len(dim_prod_df) < len(df) * 0.95:
                extracted_dims["dim_product"] = (dim_prod_df, prod_id)

        if extracted_dims:
            fact_name = f"fact_{sheet_name}" if not sheet_name.startswith("fact_") else sheet_name
            intermediate_tables.pop(sheet_name, None)

            for dim_name, (dim_df, pk) in extracted_dims.items():
                dim_meta = TableMeta(
                    name=dim_name,
                    original_sheet=f"{sheet_name} (Decomposed)",
                    table_type="dimension",
                    row_count=len(dim_df),
                    columns=[self._infer_column_meta(dim_df, c) for c in dim_df.columns],
                    primary_key=pk,
                    csv_filename=f"{dim_name}.csv",
                    preview_rows=self._make_safe_previews(dim_df, 50)
                )
                intermediate_tables[dim_name] = dim_meta
                self.processed_frames[dim_name] = dim_df

            fact_meta = TableMeta(
                name=fact_name,
                original_sheet=sheet_name,
                table_type="fact",
                row_count=len(df),
                columns=[self._infer_column_meta(df, c) for c in df.columns],
                primary_key=next((c for c in df.columns if "order_id" in c or "transaction_id" in c or c == "id"), None),
                date_column=next((c for c in df.columns if any(k in c for k in ["date", "time"])), None),
                csv_filename=f"{fact_name}.csv",
                preview_rows=self._make_safe_previews(df, 50)
            )
            intermediate_tables[fact_name] = fact_meta
            self.processed_frames[fact_name] = df

    def _generate_calendar_dimension(self, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """Create a complete Kimball Date Dimension dataframe."""
        start = datetime(start_date.year, 1, 1)
        end = datetime(end_date.year, 12, 31)
        dates = pd.date_range(start=start, end=end, freq="D")

        dim_date = pd.DataFrame({"date": dates.strftime("%Y-%m-%d")})
        dim_date["full_date"] = dates.strftime("%Y-%m-%d")
        dim_date["year"] = dates.year
        dim_date["quarter"] = "Q" + dates.quarter.astype(str)
        dim_date["quarter_number"] = dates.quarter
        dim_date["month"] = dates.month
        dim_date["month_name"] = dates.strftime("%B")
        dim_date["month_year"] = dates.strftime("%b %Y")
        dim_date["month_year_sort"] = dates.year * 100 + dates.month
        dim_date["day_of_month"] = dates.day
        dim_date["day_of_week"] = dates.dayofweek + 1
        dim_date["day_name"] = dates.strftime("%A")
        dim_date["week_number"] = dates.isocalendar().week.astype(int)
        dim_date["is_weekend"] = dates.dayofweek.isin([5, 6])
        return dim_date

    def _detect_relationships(self) -> None:
        """Match unique Primary Keys across tables to Foreign Keys in referencing tables."""
        KEY_ALIASES = {
            "customer": ["customer_id", "client_id", "user_id", "account_id", "cust_id"],
            "product": ["product_id", "item_id", "sku", "sku_id", "article_id", "prod_id"],
            "order": ["order_id", "transaction_id", "invoice_id", "sale_id"],
            "store": ["store_id", "branch_id", "location_id", "shop_id"],
            "employee": ["employee_id", "rep_id", "agent_id", "salesperson_id"],
        }

        for target in self.tables:
            if not target.primary_key or target.name == "dim_date":
                continue
            pk = target.primary_key
            pk_clean = pk.lower()

            # Find if pk belongs to an alias cluster
            alias_cluster = set()
            for cluster_keys in KEY_ALIASES.values():
                if pk_clean in cluster_keys:
                    alias_cluster = set(cluster_keys)
                    break

            for source in self.tables:
                if source.name == target.name or source.name == "dim_date":
                    continue

                matched_col = None
                for col_meta in source.columns:
                    c_clean = col_meta.name.lower()
                    if c_clean == pk_clean or c_clean == f"{target.name}_{pk_clean}" or (alias_cluster and c_clean in alias_cluster):
                        matched_col = col_meta.name
                        col_meta.is_foreign_key = True
                        break

                if matched_col:
                    exists = any(
                        r.from_table == source.name and r.from_column == matched_col and r.to_table == target.name
                        for r in self.relationships
                    )
                    if not exists:
                        rel = RelationshipMeta(
                            from_table=source.name,
                            from_column=matched_col,
                            to_table=target.name,
                            to_column=pk,
                            cardinality="OneToMany",
                            cross_filtering="OneDirection"
                        )
                        self.relationships.append(rel)
                        self._log(f"  [Link] {target.name}.{pk} (1) ────< (*) {source.name}.{matched_col}")

        # Many-to-Many bridge table identification
        for tbl in self.tables:
            if tbl.name == "dim_date" or tbl.table_type == "dimension":
                continue
            dim_links = [
                r for r in self.relationships
                if r.from_table == tbl.name and any(t.name == r.to_table and t.table_type == "dimension" for t in self.tables)
            ]
            metric_cols = [c for c in tbl.columns if c.is_metric]
            if len(dim_links) >= 2 and len(metric_cols) <= 2:
                tbl.table_type = "bridge"
                for r in dim_links:
                    r.cardinality = "ManyToMany"
                    r.cross_filtering = "BothDirections"
                self._log(f"  [Bridge Table Identified] {tbl.name} tagged as bridge with bidirectional filtering")

        # Date dimension relationships
        dim_date = next((t for t in self.tables if t.name == "dim_date"), None)
        if dim_date:
            for tbl in self.tables:
                if tbl.name != "dim_date" and tbl.date_column:
                    rel = RelationshipMeta(
                        from_table=tbl.name,
                        from_column=tbl.date_column,
                        to_table="dim_date",
                        to_column="date",
                        cardinality="OneToMany",
                        cross_filtering="OneDirection"
                    )
                    self.relationships.append(rel)
                    self._log(f"  [Calendar Link] dim_date.date (1) ────< (*) {tbl.name}.{tbl.date_column}")

    def export_csv_marts(self) -> None:
        """Step 3: Save all tables to clean UTF-8 CSV files."""
        self._log("Exporting clean CSV marts...", progress=50, stage="Exporting CSVs")
        self.csv_dir.mkdir(parents=True, exist_ok=True)

        for tbl_meta in self.tables:
            df = self.processed_frames[tbl_meta.name]
            csv_path = self.csv_dir / tbl_meta.csv_filename
            df.to_csv(csv_path, index=False, encoding="utf-8")
            self._log(f"  [OK] Exported {tbl_meta.name}: {len(df)} rows -> {csv_path.name}")

    def synthesize_dax_measures(self) -> None:
        """Step 4: Dynamically construct comprehensive DAX measures."""
        self._log("Synthesizing dynamic DAX measures...", progress=65, stage="Generating DAX")
        measures: List[DaxMeasureMeta] = []

        has_date_dim = any(t.name == "dim_date" for t in self.tables)
        date_expr = "dim_date[date]" if has_date_dim else None

        for fact in [t for t in self.tables if t.table_type == "fact"]:
            table_name = fact.name
            metrics = [c for c in fact.columns if c.is_metric]

            pk = fact.primary_key
            if pk:
                measures.append(DaxMeasureMeta(
                    name=f"{format_title(fact.name)} Count",
                    expression=f"DISTINCTCOUNT({table_name}[{pk}])",
                    category="01 Volume & Counts",
                    description=f"Distinct count of {pk} in {table_name}",
                    format_string="#,0"
                ))
            else:
                measures.append(DaxMeasureMeta(
                    name=f"Total {format_title(fact.name)} Rows",
                    expression=f"COUNTROWS({table_name})",
                    category="01 Volume & Counts",
                    description=f"Total rows in {table_name}",
                    format_string="#,0"
                ))

            rev_col = next((c.name for c in metrics if any(k in c.name.lower() for k in ["revenue", "sales", "amount", "total"])), None)
            cost_col = next((c.name for c in metrics if any(k in c.name.lower() for k in ["cost", "cogs", "expense"])), None)
            disc_col = next((c.name for c in metrics if any(k in c.name.lower() for k in ["discount"])), None)

            for m in metrics:
                col_name = m.name
                title = format_title(col_name)
                is_curr = any(k in col_name.lower() for k in ["revenue", "sales", "amount", "cost", "price", "profit", "spend", "value"])
                fmt = f"\\{self.currency_symbol}#,0;(\\{self.currency_symbol}#,0);\\{self.currency_symbol}#,0" if is_curr else "#,0"

                m_total_name = f"Total {title}"
                measures.append(DaxMeasureMeta(
                    name=m_total_name,
                    expression=f"SUM({table_name}[{col_name}])",
                    category="02 Core Metrics",
                    description=f"Aggregated sum of {col_name} in {table_name}",
                    format_string=fmt
                ))

                measures.append(DaxMeasureMeta(
                    name=f"Average {title}",
                    expression=f"AVERAGE({table_name}[{col_name}])",
                    category="02 Core Metrics",
                    description=f"Arithmetic average of {col_name} in {table_name}",
                    format_string=f"\\{self.currency_symbol}#,##0.00" if is_curr else "#,##0.00"
                ))

                if has_date_dim and date_expr:
                    measures.append(DaxMeasureMeta(
                        name=f"{title} YTD",
                        expression=f"TOTALYTD([{m_total_name}], {date_expr})",
                        category="04 Time Intelligence",
                        description=f"Year-to-date calculation for {m_total_name}",
                        format_string=fmt
                    ))
                    measures.append(DaxMeasureMeta(
                        name=f"{title} Prior Month",
                        expression=f"CALCULATE([{m_total_name}], PREVIOUSMONTH({date_expr}))",
                        category="04 Time Intelligence",
                        description=f"Previous month value for {m_total_name}",
                        format_string=fmt
                    ))
                    measures.append(DaxMeasureMeta(
                        name=f"{title} MoM %",
                        expression=f"DIVIDE([{m_total_name}] - [{title} Prior Month], [{title} Prior Month], 0)",
                        category="04 Time Intelligence",
                        description=f"Month-over-month growth percentage for {m_total_name}",
                        format_string="0.0%"
                    ))
                    measures.append(DaxMeasureMeta(
                        name=f"{title} Prior Year",
                        expression=f"CALCULATE([{m_total_name}], SAMEPERIODLASTYEAR({date_expr}))",
                        category="04 Time Intelligence",
                        description=f"Same period last year for {m_total_name}",
                        format_string=fmt
                    ))
                    measures.append(DaxMeasureMeta(
                        name=f"{title} YoY %",
                        expression=f"DIVIDE([{m_total_name}] - [{title} Prior Year], [{title} Prior Year], 0)",
                        category="04 Time Intelligence",
                        description=f"Year-over-year growth percentage for {m_total_name}",
                        format_string="0.0%"
                    ))

            if rev_col and cost_col:
                rev_m = f"Total {format_title(rev_col)}"
                cost_m = f"Total {format_title(cost_col)}"
                curr_fmt = f"\\{self.currency_symbol}#,0;(\\{self.currency_symbol}#,0);\\{self.currency_symbol}#,0"

                measures.append(DaxMeasureMeta(
                    name="Gross Profit",
                    expression=f"[{rev_m}] - [{cost_m}]",
                    category="03 Margins & Profitability",
                    description="Gross Profit calculated as Net Sales/Revenue minus Total Cost/COGS",
                    format_string=curr_fmt
                ))
                measures.append(DaxMeasureMeta(
                    name="Gross Margin %",
                    expression=f"DIVIDE([Gross Profit], [{rev_m}], 0)",
                    category="03 Margins & Profitability",
                    description="Gross Profit Margin percentage",
                    format_string="0.0%"
                ))

            if rev_col and disc_col:
                disc_m = f"Total {format_title(disc_col)}"
                rev_m = f"Total {format_title(rev_col)}"
                measures.append(DaxMeasureMeta(
                    name="Discount Rate %",
                    expression=f"DIVIDE([{disc_m}], [{rev_m}], 0)",
                    category="03 Margins & Profitability",
                    description="Effective aggregate discount percentage",
                    format_string="0.0%"
                ))

        for dim in [t for t in self.tables if t.table_type == "dimension" and t.name != "dim_date"]:
            if dim.primary_key:
                measures.append(DaxMeasureMeta(
                    name=f"Total {format_title(dim.name.replace('dim_', ''))}s",
                    expression=f"DISTINCTCOUNT({dim.name}[{dim.primary_key}])",
                    category="05 Entity Intelligence",
                    description=f"Total unique count of {dim.name}",
                    format_string="#,0"
                ))

        self.dax_measures = measures
        self.powerbi_dir.mkdir(parents=True, exist_ok=True)
        dax_file = self.powerbi_dir / "measures.dax"
        lines = [
            f"// ===================================================================",
            f"// {self.project_name} – DAX Semantic Measures Library",
            f"// Auto-generated by RevenueOS Canonical Engine",
            f"// ===================================================================",
            ""
        ]

        curr_cat = None
        for m in sorted(self.dax_measures, key=lambda x: (x.category, x.name)):
            if m.category != curr_cat:
                curr_cat = m.category
                lines.append(f"\n// -------------------------------------------------------------------")
                lines.append(f"// Category: {curr_cat}")
                lines.append(f"// -------------------------------------------------------------------")
            lines.append(f"// {m.description}")
            lines.append(f"// Format: {m.format_string}")
            lines.append(f"{m.name} = \n{m.expression}\n")

        dax_file.write_text("\n".join(lines), encoding="utf-8")
        self._log(f"  [OK] Saved DAX measures to: {dax_file.name}")

    def generate_power_query_m(self) -> None:
        """Step 5: Write Power Query M scripts to load CSV files."""
        self._log("Generating Power Query M scripts...", progress=75, stage="Generating M Code")
        m_queries = []
        csv_folder_abs = str(self.csv_dir.resolve()).replace("\\", "/")

        for tbl in self.tables:
            csv_path = f"{csv_folder_abs}/{tbl.csv_filename}"
            col_types = []
            for c in tbl.columns:
                if c.dtype == "int64":
                    t = "Int64.Type"
                elif c.dtype == "double":
                    t = "type number"
                elif c.dtype == "datetime":
                    t = "type datetime"
                elif c.dtype == "boolean":
                    t = "type logical"
                else:
                    t = "type text"
                col_types.append(f'{{"{c.name}", {t}}}')

            col_transforms = ", ".join(col_types)
            m_code = f"""// Table: {tbl.name}
let
    Source = Csv.Document(File.Contents("{csv_path}"),[Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.None]),
    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true]),
    #"Changed Type" = Table.TransformColumnTypes(#"Promoted Headers", {{{col_transforms}}})
in
    #"Changed Type"
"""
            m_queries.append(m_code)

        pq_file = self.powerbi_dir / "power_query_m.pq"
        pq_file.write_text("\n\n".join(m_queries), encoding="utf-8")
        self._log(f"  [OK] Saved Power Query M code to: {pq_file.name}")

    def compile_powerbi_artifacts(self) -> Tuple[Path, Path]:
        """Step 6: Build single-click .pbit and .pbip project files."""
        self._log("Compiling Power BI Template (.pbit) and Project (.pbip)...", progress=85, stage="Compiling Power BI")
        
        tmsl_tables = []
        for tbl in self.tables:
            cols = []
            for c in tbl.columns:
                if c.dtype == "int64":
                    dt = "int64"
                elif c.dtype == "double":
                    dt = "double"
                elif c.dtype == "datetime":
                    dt = "dateTime"
                elif c.dtype == "boolean":
                    dt = "boolean"
                else:
                    dt = "string"

                col_obj = {
                    "name": c.name,
                    "dataType": dt,
                    "sourceColumn": c.name,
                    "summarizeBy": "sum" if c.is_metric else "none"
                }
                cols.append(col_obj)

            tmsl_tables.append({
                "name": tbl.name,
                "columns": cols,
                "partitions": [
                    {
                        "name": f"{tbl.name}-Partition",
                        "mode": "import",
                        "source": {
                            "type": "m",
                            "expression": [
                                f'let Source = Csv.Document(File.Contents("{str(self.csv_dir.resolve()).replace(chr(92), "/")}/{tbl.csv_filename}"),[Delimiter=",", Encoding=65001, QuoteStyle=QuoteStyle.None]), #"Promoted" = Table.PromoteHeaders(Source, [PromoteAllScalars=true]) in #"Promoted"'
                            ]
                        }
                    }
                ]
            })

        measures_obj = []
        for m in self.dax_measures:
            measures_obj.append({
                "name": m.name,
                "expression": m.expression,
                "formatString": m.format_string,
                "description": m.description,
                "displayFolder": m.category
            })

        tmsl_tables.append({
            "name": "_Measures",
            "columns": [{"name": "Measure_Placeholder", "dataType": "string", "sourceColumn": "Measure_Placeholder", "isHidden": True}],
            "measures": measures_obj,
            "partitions": [{
                "name": "_Measures-Partition",
                "mode": "import",
                "source": {"type": "m", "expression": ['let Source = #table({"Measure_Placeholder"}, {{""}}) in Source']}
            }]
        })

        tmsl_rels = []
        for r in self.relationships:
            tmsl_rels.append({
                "name": f"{r.from_table}_{r.from_column}_to_{r.to_table}_{r.to_column}",
                "fromTable": r.from_table,
                "fromColumn": r.from_column,
                "toTable": r.to_table,
                "toColumn": r.to_column,
                "crossFilteringBehavior": "bothDirections" if r.cross_filtering == "BothDirections" else "oneDirection",
                "securityFilteringBehavior": "oneDirection"
            })

        tmsl_model = {
            "name": self.project_name,
            "compatibilityLevel": 1550,
            "model": {
                "culture": "en-US",
                "tables": tmsl_tables,
                "relationships": tmsl_rels
            }
        }

        safe_name = clean_identifier(self.project_name)
        pbit_path = self.powerbi_dir / f"{safe_name}.pbit"

        buf = io.BytesIO()
        content_types = """<?xml version="1.0" encoding="utf-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
  <Default Extension="json" ContentType="" />
  <Override PartName="/Version" ContentType="" />
  <Override PartName="/Settings" ContentType="" />
  <Override PartName="/Metadata" ContentType="" />
  <Override PartName="/SecurityBindings" ContentType="" />
  <Override PartName="/DiagramLayout" ContentType="" />
  <Override PartName="/DataModelSchema" ContentType="" />
  <Override PartName="/Report/Layout" ContentType="" />
</Types>"""

        layout = {
            "id": 0,
            "resourcePackages": [],
            "sections": [
                {
                    "id": 0,
                    "name": "ReportSection1",
                    "displayName": "Executive Summary",
                    "ordinal": 0,
                    "visualContainers": [],
                    "config": json.dumps({"singleVisual": False}),
                    "displayOption": 1,
                    "width": 1920.0,
                    "height": 1080.0
                }
            ],
            "config": json.dumps({
                "version": "5.57",
                "theme": "RevenueOS Dark Slate Executive",
                "defaultDrillFilterOtherVisuals": True
            }),
            "layoutOptimization": 0
        }

        with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as z:
            z.writestr("Version", "1.32".encode("utf-16le"))
            z.writestr("[Content_Types].xml", content_types.encode("utf-8"))
            z.writestr("Settings", json.dumps({"AutoRecover": True}).encode("utf-16le"))
            z.writestr("Metadata", json.dumps({"version": "2.0"}).encode("utf-16le"))
            z.writestr("SecurityBindings", b"")
            z.writestr("DiagramLayout", json.dumps({"version": "2.0.0"}).encode("utf-16le"))
            z.writestr("DataModelSchema", json.dumps(tmsl_model, indent=2).encode("utf-16le"))
            z.writestr("Report/Layout", json.dumps(layout).encode("utf-16le"))

        pbit_path.write_bytes(buf.getvalue())
        self._log(f"  [OK] Saved Power BI Template: {pbit_path.name} ({pbit_path.stat().st_size:,} bytes)")

        # Build .pbip project directory
        pbip_path = self.powerbi_dir / f"{safe_name}.pbip"
        pbip_content = {
            "version": "1.0",
            "artifacts": [{"report": {"path": f"{safe_name}.Report"}}],
            "settings": {"enableAutoRecovery": True}
        }
        pbip_path.write_text(json.dumps(pbip_content, indent=2), encoding="utf-8")

        model_dir = self.powerbi_dir / f"{safe_name}.SemanticModel"
        report_dir = self.powerbi_dir / f"{safe_name}.Report"
        model_dir.mkdir(parents=True, exist_ok=True)
        report_dir.mkdir(parents=True, exist_ok=True)

        (model_dir / "definition.pbism").write_text(json.dumps({"version": "4.0"}, indent=2), encoding="utf-8")
        (model_dir / "model.bim").write_text(json.dumps(tmsl_model, indent=2), encoding="utf-8")
        (report_dir / "definition.pbir").write_text(
            json.dumps({"version": "4.0", "datasetReference": {"byPath": {"path": f"../{safe_name}.SemanticModel"}}}, indent=2),
            encoding="utf-8"
        )
        self._log(f"  [OK] Saved Power BI Developer Project: {pbip_path.name}")
        return pbit_path, pbip_path

    def compute_dashboard_aggregations(self) -> Dict[str, Any]:
        """Compute multi-dimensional aggregations to render live replica charts in the Electron App."""
        self._log("Computing multi-dimensional dashboard aggregations...", progress=90, stage="Pre-computing Dashboard")

        orders_fact = next((t for t in self.tables if t.name in ["orders", "fact_orders", "sales", "transactions"]), None)
        if not orders_fact:
            orders_fact = next((t for t in self.tables if t.table_type == "fact"), None)

        if not orders_fact:
            return {}

        df = self.processed_frames[orders_fact.name].copy()

        # Identify key columns
        date_col = orders_fact.date_column or next((c.name for c in orders_fact.columns if c.is_date), None)
        if not date_col:
            date_col = next((c for c in df.columns if any(k in c.lower() for k in ["date", "time", "created"])), None)

        rev_col = next((c for c in df.columns if any(k in c.lower() for k in ["revenue", "sales", "amount", "total_price", "grand_total"])), None)
        cost_col = next((c for c in df.columns if any(k in c.lower() for k in ["cost", "cogs", "total_cost"])), None)
        qty_col = next((c for c in df.columns if any(k in c.lower() for k in ["quantity", "qty", "units"])), None)
        disc_col = next((c for c in df.columns if "discount" in c.lower()), None)
        price_col = next((c for c in df.columns if any(k in c.lower() for k in ["unit_price", "price", "selling_price", "rate"])), None)

        # Merge with dimensions if available for richer breakdown
        prod_dim = next((t for t in self.tables if t.name in ["products", "dim_product"]), None)
        if prod_dim and "product_id" in df.columns:
            prod_df = self.processed_frames[prod_dim.name]
            if "product_id" in prod_df.columns:
                df = df.merge(prod_df, on="product_id", how="left", suffixes=("", "_prod"))

        cust_dim = next((t for t in self.tables if t.name in ["customers", "dim_customer"]), None)
        if cust_dim and "customer_id" in df.columns:
            cust_df = self.processed_frames[cust_dim.name]
            if "customer_id" in cust_df.columns:
                df = df.merge(cust_df, on="customer_id", how="left", suffixes=("", "_cust"))

        # Derive Net Revenue if not explicitly present
        if not rev_col and price_col and qty_col:
            q = pd.to_numeric(df[qty_col], errors="coerce").fillna(1.0)
            p = pd.to_numeric(df[price_col], errors="coerce").fillna(0.0)
            gross = q * p
            if disc_col:
                d = pd.to_numeric(df[disc_col], errors="coerce").fillna(0.0)
                if d.max() <= 1.0:
                    df["_calc_revenue"] = gross * (1.0 - d.clip(0, 1))
                else:
                    df["_calc_revenue"] = (gross - d).clip(lower=0)
            else:
                df["_calc_revenue"] = gross
            rev_col = "_calc_revenue"

        # Derive Total Cost / COGS if not explicitly present
        if not cost_col:
            cost_source_col = next((c for c in df.columns if any(k in c.lower() for k in ["cost", "unit_cost", "cogs"])), None)
            if cost_source_col and qty_col:
                q = pd.to_numeric(df[qty_col], errors="coerce").fillna(1.0)
                c = pd.to_numeric(df[cost_source_col], errors="coerce").fillna(0.0)
                df["_calc_cost"] = q * c
                cost_col = "_calc_cost"

        # Time series aggregation
        time_series = []
        if date_col and rev_col and date_col in df.columns:
            df["_dt"] = pd.to_datetime(df[date_col], errors="coerce", format="mixed")
            df["_month"] = df["_dt"].dt.strftime("%Y-%m")
            agg_dict = {rev_col: "sum"}
            if cost_col and cost_col in df.columns:
                agg_dict[cost_col] = "sum"
            if qty_col and qty_col in df.columns:
                agg_dict[qty_col] = "sum"

            monthly = df.dropna(subset=["_month"]).groupby("_month").agg(agg_dict).reset_index()

            for _, row in monthly.sort_values("_month").iterrows():
                rev = float(row[rev_col]) if rev_col else 0.0
                cost = float(row[cost_col]) if cost_col and cost_col in df.columns else 0.0
                time_series.append({
                    "period": row["_month"],
                    "revenue": round(rev, 2),
                    "cost": round(cost, 2),
                    "profit": round(rev - cost, 2),
                    "marginPct": round(((rev - cost) / rev * 100), 1) if rev > 0 else 0.0,
                    "units": int(row[qty_col]) if qty_col and qty_col in df.columns else 0
                })

        # Category Breakdown
        by_category = []
        cat_col = next((c for c in df.columns if any(k in c.lower() for k in ["category", "dept", "department", "type"])), None)
        if cat_col and rev_col:
            cat_grouped = df.groupby(cat_col)[rev_col].sum().reset_index().sort_values(rev_col, ascending=False).head(8)
            for _, row in cat_grouped.iterrows():
                by_category.append({
                    "category": str(row[cat_col]),
                    "revenue": round(float(row[rev_col]), 2)
                })

        # Channel Breakdown
        by_channel = []
        chan_col = next((c for c in df.columns if any(k in c.lower() for k in ["channel", "region", "city", "segment"])), None)
        if chan_col and rev_col:
            chan_grouped = df.groupby(chan_col)[rev_col].sum().reset_index().sort_values(rev_col, ascending=False).head(6)
            for _, row in chan_grouped.iterrows():
                by_channel.append({
                    "channel": str(row[chan_col]),
                    "revenue": round(float(row[rev_col]), 2)
                })

        # Top Products
        top_products = []
        name_col = next((c for c in df.columns if any(k in c.lower() for k in ["product_name", "item_name", "title", "sku"])), None)
        if name_col and rev_col:
            prod_grouped = df.groupby(name_col)[rev_col].sum().reset_index().sort_values(rev_col, ascending=False).head(10)
            for _, row in prod_grouped.iterrows():
                top_products.append({
                    "product": str(row[name_col]),
                    "revenue": round(float(row[rev_col]), 2)
                })

        # Total KPI metrics
        total_rev = float(df[rev_col].sum()) if rev_col and rev_col in df.columns else 0.0
        total_cost = float(df[cost_col].sum()) if cost_col and cost_col in df.columns else 0.0
        total_orders = int(len(df))
        total_units = int(df[qty_col].sum()) if qty_col and qty_col in df.columns else total_orders
        total_disc = float(df[disc_col].sum()) if disc_col and disc_col in df.columns else 0.0

        # Slicer options
        filter_categories = [str(x) for x in df[cat_col].dropna().unique().tolist()[:20]] if cat_col else []
        filter_channels = [str(x) for x in df[chan_col].dropna().unique().tolist()[:20]] if chan_col else []

        # Customer Segments Breakdown
        by_segment = []
        seg_col = next((c for c in df.columns if "segment" in c.lower()), None)
        if seg_col and rev_col:
            seg_grouped = df.groupby(seg_col)[rev_col].sum().reset_index().sort_values(rev_col, ascending=False)
            for _, row in seg_grouped.iterrows():
                by_segment.append({
                    "segment": str(row[seg_col]),
                    "revenue": round(float(row[rev_col]), 2)
                })

        # Marketing metrics if marketing table exists
        marketing_metrics = []
        mkt_table = next((t for t in self.tables if "marketing" in t.name.lower() or "campaign" in t.name.lower()), None)
        if mkt_table and mkt_table.name in self.processed_frames:
            mdf = self.processed_frames[mkt_table.name]
            mchan = next((c for c in mdf.columns if "channel" in c.lower()), None)
            mspd = next((c for c in mdf.columns if "spend" in c.lower() or "cost" in c.lower()), None)
            mattr = next((c for c in mdf.columns if "revenue" in c.lower() or "sales" in c.lower()), None)
            mimpr = next((c for c in mdf.columns if "impression" in c.lower()), None)
            mclk = next((c for c in mdf.columns if "click" in c.lower()), None)
            if mchan and mspd:
                agg_m = {mspd: "sum"}
                if mattr: agg_m[mattr] = "sum"
                if mimpr: agg_m[mimpr] = "sum"
                if mclk: agg_m[mclk] = "sum"
                mgrouped = mdf.groupby(mchan).agg(agg_m).reset_index()
                for _, row in mgrouped.iterrows():
                    s = float(row[mspd]) if mspd else 0.0
                    r = float(row[mattr]) if mattr else 0.0
                    marketing_metrics.append({
                        "channel": str(row[mchan]),
                        "spend": round(s, 2),
                        "revenue": round(r, 2),
                        "roas": round(r / s, 2) if s > 0 else 0.0,
                        "impressions": int(row[mimpr]) if mimpr else 0,
                        "clicks": int(row[mclk]) if mclk else 0
                    })

        # Returns metrics if returns table exists
        returns_metrics = {"totalReturns": 0, "returnRate": 0.0, "reasons": []}
        ret_table = next((t for t in self.tables if "return" in t.name.lower()), None)
        if ret_table and ret_table.name in self.processed_frames:
            rdf = self.processed_frames[ret_table.name]
            rqty = next((c for c in rdf.columns if "quantity" in c.lower() or "qty" in c.lower()), None)
            rreas = next((c for c in rdf.columns if "reason" in c.lower()), None)
            tot_ret = int(rdf[rqty].sum()) if rqty else len(rdf)
            returns_metrics["totalReturns"] = tot_ret
            returns_metrics["returnRate"] = round((tot_ret / total_units * 100), 2) if total_units > 0 else 0.0
            if rreas:
                rg = rdf.groupby(rreas).size().reset_index(name="count").sort_values("count", ascending=False)
                for _, row in rg.iterrows():
                    returns_metrics["reasons"].append({
                        "reason": str(row[rreas]),
                        "count": int(row["count"])
                    })

        min_date_str = str(self.min_date.strftime("%Y-%m-%d")) if self.min_date else ""
        max_date_str = str(self.max_date.strftime("%Y-%m-%d")) if self.max_date else ""

        return {
            "kpis": {
                "totalRevenue": round(total_rev, 2),
                "totalCost": round(total_cost, 2),
                "grossProfit": round(total_rev - total_cost, 2),
                "grossMarginPct": round(((total_rev - total_cost) / total_rev * 100), 1) if total_rev > 0 else 0.0,
                "totalOrders": total_orders,
                "totalUnits": total_units,
                "avgOrderValue": round(total_rev / total_orders, 2) if total_orders > 0 else 0.0,
                "totalDiscounts": round(total_disc, 2),
                "currency": self.currency_symbol
            },
            "timeSeries": time_series,
            "byCategory": by_category,
            "byChannel": by_channel,
            "topProducts": top_products,
            "bySegment": by_segment,
            "marketing": marketing_metrics,
            "returns": returns_metrics,
            "filterOptions": {
                "categories": filter_categories,
                "channels": filter_channels,
                "minDate": min_date_str,
                "maxDate": max_date_str
            }
        }

    def generate_step_by_step_guide(self) -> Path:
        """Step 7: Generate human-friendly, comprehensive deployment guide."""
        self._log("Writing step-by-step deployment guide...", progress=92, stage="Generating Guide")

        csv_folder = str(self.csv_dir.resolve()).replace("\\", "/")
        pbit_name = f"{clean_identifier(self.project_name)}.pbit"
        pbip_name = f"{clean_identifier(self.project_name)}.pbip"

        guide_content = f"""# {self.project_name} – Power BI Deployment & Import Guide

This document provides step-by-step instructions to load your converted Excel dataset into Power BI Desktop.

---

## ⚡ Method 1: Single-Click Instant Template (Recommended)

You do **not** need to manually drag tables or write formulas. The engine has pre-wired everything:

1. Locate the compiled template:
   `powerbi/{pbit_name}`
2. **Double-click** `{pbit_name}`. Power BI Desktop will launch automatically.
3. Power BI will prompt you to verify or confirm parameters:
   - All **{len(self.tables)} Tables** are pre-loaded from CSV.
   - All **{len(self.relationships)} Star Schema Relationships** are pre-joined (`1:*`).
   - All **{len(self.dax_measures)} DAX Measures** are pre-calculated inside the `_Measures` table.
4. Click **Load** or **Apply Changes**.

---

## 🛠 Method 2: Manual CSV Import & Model Setup

If you prefer to configure your model manually in Power BI Desktop:

### Step 1: Ingest the Generated CSV Files
1. Open **Power BI Desktop**.
2. On the **Home** tab ribbon, click **Get Data** → **Text/CSV**.
3. Browse to the output CSV folder:
   `{csv_folder}`
4. Import each generated table:
"""
        for tbl in self.tables:
            guide_content += f"   - `{tbl.csv_filename}` ({tbl.row_count:,} rows, {tbl.table_type.upper()})\n"

        guide_content += f"""
5. Click **Load** for each table.

---

### Step 2: Configure the Star Schema Relationships
1. In the left navigation bar of Power BI Desktop, click **Model View** (icon with 3 boxes).
2. Arrange your Fact tables in the center and Dimension tables around them.
3. Drag and connect the following primary/foreign key pairs:

| From (Fact Table) | Column | Cardinality | To (Dimension Table) | Column |
| :--- | :--- | :---: | :--- | :--- |
"""
        for r in self.relationships:
            guide_content += f"| **{r.from_table}** | `{r.from_column}` | `* : 1` (One-Way) | **{r.to_table}** | `{r.to_column}` |\n"

        guide_content += f"""
---

### Step 3: Add the DAX Measures
1. On the **Home** tab, click **Enter Data**.
2. Name the table `_Measures` and click **Load**.
3. Select `_Measures` in the Data pane, click **New Measure** on the ribbon.
4. Open `powerbi/measures.dax` and paste the desired measures:

#### Core Measures Preview:
"""
        for m in self.dax_measures[:8]:
            guide_content += f"```dax\n{m.name} = \n{m.expression}\n```\n\n"

        guide_content += f"""
---

## 📜 Intellectual Property & Commercial License

This automated pipeline and its generated assets are governed by the:
**RevenueOS Source-Available Commercial & Royalty License (Version 1.0)**

- **Permitted**: Non-commercial internal testing, evaluation, and research.
- **Strictly Prohibited**: Any monetization, commercial exploitation, hosted SaaS deployment, or resale without prior written agreement and royalty payments to the author (**Sarvesh Sharma**).
"""
        guide_path = self.output_dir / "POWERBI_DEPLOYMENT_GUIDE.md"
        guide_path.write_text(guide_content, encoding="utf-8")
        self._log(f"  [OK] Saved deployment guide to: {guide_path.name}")
        return guide_path

    def generate_matplotlib_visuals(self, dashboard: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Step 7b: Synthesize high-resolution dark-mode Matplotlib analytical charts."""
        self._log("Generating high-resolution Matplotlib analytical chart pack...", progress=95, stage="Generating Charts")
        self.charts_dir.mkdir(parents=True, exist_ok=True)
        charts_meta: List[Dict[str, Any]] = []

        # Color tokens matching RevenueOS palette
        BG_DARK = "#18181B"
        CARD_DARK = "#202023"
        BORDER_DARK = "#333338"
        TEXT_LIGHT = "#F4F4F5"
        TEXT_MUTED = "#A1A1AA"
        ACCENT_BLUE = "#0078D4"
        ACCENT_GREEN = "#107C41"
        ACCENT_ORANGE = "#D83B01"
        ACCENT_PURPLE = "#8764B8"
        ACCENT_TEAL = "#00B7C3"
        ACCENT_YELLOW = "#FFB900"
        PALETTE = [ACCENT_BLUE, ACCENT_GREEN, ACCENT_ORANGE, ACCENT_PURPLE, ACCENT_TEAL, ACCENT_YELLOW]

        def apply_dark_style(fig, ax):
            fig.patch.set_facecolor(BG_DARK)
            ax.set_facecolor(CARD_DARK)
            ax.tick_params(colors=TEXT_MUTED, labelsize=9)
            ax.xaxis.label.set_color(TEXT_LIGHT)
            ax.yaxis.label.set_color(TEXT_LIGHT)
            for spine in ax.spines.values():
                spine.set_color(BORDER_DARK)
                spine.set_linewidth(1.0)
            ax.grid(True, linestyle="--", alpha=0.15, color=TEXT_MUTED)

        # -------------------------------------------------------------
        # Chart 1: Monthly Revenue & Gross Profit Trend (Dual Axis)
        # -------------------------------------------------------------
        time_series = dashboard.get("timeSeries", [])
        if time_series and len(time_series) > 1:
            try:
                fig, ax1 = plt.subplots(figsize=(11, 5.5), dpi=300)
                apply_dark_style(fig, ax1)

                df_ts = pd.DataFrame(time_series)
                periods = df_ts["period"].astype(str).tolist()
                x_pos = np.arange(len(periods))
                rev = df_ts["revenue"].astype(float).values
                cost = df_ts["cost"].astype(float).values
                margin = df_ts["marginPct"].astype(float).values

                width = 0.38
                ax1.bar(x_pos - width/2, rev, width=width, label="Gross Revenue", color=ACCENT_BLUE, alpha=0.88, zorder=2)
                ax1.bar(x_pos + width/2, cost, width=width, label="COGS / Cost", color=ACCENT_ORANGE, alpha=0.85, zorder=2)
                ax1.set_ylabel(f"Amount ({self.currency_symbol})", color=TEXT_LIGHT, fontsize=10, weight="bold")
                ax1.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, p: f"{self.currency_symbol}{x*1e-3:.0f}K" if x < 1e6 else f"{self.currency_symbol}{x*1e-6:.1f}M"))
                ax1.set_xticks(x_pos)
                ax1.set_xticklabels(periods, rotation=45, ha="right")

                ax2 = ax1.twinx()
                ax2.set_facecolor("none")
                ax2.plot(x_pos, margin, color=ACCENT_GREEN, linewidth=2.5, marker="o", markersize=5, label="Gross Margin %", zorder=3)
                ax2.set_ylabel("Gross Margin %", color=ACCENT_GREEN, fontsize=10, weight="bold")
                ax2.yaxis.set_major_formatter(ticker.PercentFormatter())
                ax2.tick_params(colors=ACCENT_GREEN, labelsize=9)
                ax2.spines["right"].set_color(ACCENT_GREEN)
                ax2.spines["right"].set_linewidth(1.2)
                ax2.grid(False)

                lines1, labels1 = ax1.get_legend_handles_labels()
                lines2, labels2 = ax2.get_legend_handles_labels()
                ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper left", facecolor=CARD_DARK, edgecolor=BORDER_DARK, labelcolor=TEXT_LIGHT, fontsize=9)

                plt.title(f"{self.project_name} – Monthly Revenue vs COGS & Gross Margin %", color=TEXT_LIGHT, fontsize=13, weight="bold", pad=15)
                fig.tight_layout()

                c1_path = self.charts_dir / "01_monthly_revenue_and_margin_trend.png"
                fig.savefig(c1_path, facecolor=fig.get_facecolor(), edgecolor="none")
                plt.close(fig)
                charts_meta.append({
                    "id": "chart_monthly_trend",
                    "title": "Monthly Revenue vs COGS & Margin Trend",
                    "filename": c1_path.name,
                    "path": str(c1_path)
                })
            except Exception as e:
                self._log(f"Warning: Could not generate Chart 1: {e}")

        # -------------------------------------------------------------
        # Chart 2: Revenue by Product Category
        # -------------------------------------------------------------
        by_category = dashboard.get("byCategory", [])
        if by_category:
            try:
                fig, ax = plt.subplots(figsize=(9, 5), dpi=300)
                apply_dark_style(fig, ax)

                df_cat = pd.DataFrame(by_category).sort_values("revenue", ascending=True)
                cats = df_cat["category"].astype(str).tolist()
                revs = df_cat["revenue"].astype(float).values
                total_rev = np.sum(revs) if np.sum(revs) > 0 else 1.0
                pcts = (revs / total_rev) * 100

                bars = ax.barh(cats, revs, color=PALETTE[:len(cats)], height=0.6, zorder=2)
                ax.set_xlabel(f"Revenue ({self.currency_symbol})", color=TEXT_LIGHT, fontsize=10, weight="bold")
                ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, p: f"{self.currency_symbol}{x*1e-3:.0f}K" if x < 1e6 else f"{self.currency_symbol}{x*1e-6:.2f}M"))

                for bar, p in zip(bars, pcts):
                    w = bar.get_width()
                    ax.text(w + (max(revs) * 0.015), bar.get_y() + bar.get_height()/2, f"{p:.1f}% ({self.currency_symbol}{w:,.0f})",
                            va="center", color=TEXT_LIGHT, fontsize=8.5, weight="bold")

                ax.set_xlim(0, max(revs) * 1.3)
                plt.title(f"{self.project_name} – Revenue Contribution by Category", color=TEXT_LIGHT, fontsize=13, weight="bold", pad=15)
                fig.tight_layout()

                c2_path = self.charts_dir / "02_category_revenue_distribution.png"
                fig.savefig(c2_path, facecolor=fig.get_facecolor(), edgecolor="none")
                plt.close(fig)
                charts_meta.append({
                    "id": "chart_category_share",
                    "title": "Revenue Contribution by Category",
                    "filename": c2_path.name,
                    "path": str(c2_path)
                })
            except Exception as e:
                self._log(f"Warning: Could not generate Chart 2: {e}")

        # -------------------------------------------------------------
        # Chart 3: Revenue by Acquisition Channel
        # -------------------------------------------------------------
        by_channel = dashboard.get("byChannel", [])
        if by_channel:
            try:
                fig, ax = plt.subplots(figsize=(9, 5), dpi=300)
                apply_dark_style(fig, ax)

                df_chan = pd.DataFrame(by_channel).sort_values("revenue", ascending=True)
                chans = df_chan["channel"].astype(str).tolist()
                revs = df_chan["revenue"].astype(float).values

                bars = ax.barh(chans, revs, color=ACCENT_BLUE, height=0.55, zorder=2)
                ax.set_xlabel(f"Revenue ({self.currency_symbol})", color=TEXT_LIGHT, fontsize=10, weight="bold")
                ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, p: f"{self.currency_symbol}{x*1e-3:.0f}K" if x < 1e6 else f"{self.currency_symbol}{x*1e-6:.2f}M"))

                for bar in bars:
                    w = bar.get_width()
                    ax.text(w + (max(revs) * 0.015), bar.get_y() + bar.get_height()/2, f"{self.currency_symbol}{w:,.0f}",
                            va="center", color=TEXT_LIGHT, fontsize=8.5, weight="bold")

                ax.set_xlim(0, max(revs) * 1.25)
                plt.title(f"{self.project_name} – Channel Revenue Breakdown", color=TEXT_LIGHT, fontsize=13, weight="bold", pad=15)
                fig.tight_layout()

                c3_path = self.charts_dir / "03_channel_revenue_breakdown.png"
                fig.savefig(c3_path, facecolor=fig.get_facecolor(), edgecolor="none")
                plt.close(fig)
                charts_meta.append({
                    "id": "chart_channel_breakdown",
                    "title": "Channel Revenue Breakdown",
                    "filename": c3_path.name,
                    "path": str(c3_path)
                })
            except Exception as e:
                self._log(f"Warning: Could not generate Chart 3: {e}")

        # -------------------------------------------------------------
        # Chart 4: Top 10 Performing Products
        # -------------------------------------------------------------
        top_prods = dashboard.get("topProducts", [])
        if top_prods:
            try:
                fig, ax = plt.subplots(figsize=(10, 5.5), dpi=300)
                apply_dark_style(fig, ax)

                df_prods = pd.DataFrame(top_prods).sort_values("revenue", ascending=True)
                prods = [p[:28] + ("..." if len(p) > 28 else "") for p in df_prods["product"].astype(str).tolist()]
                revs = df_prods["revenue"].astype(float).values

                bars = ax.barh(prods, revs, color=ACCENT_TEAL, height=0.6, zorder=2)
                ax.set_xlabel(f"Revenue ({self.currency_symbol})", color=TEXT_LIGHT, fontsize=10, weight="bold")
                ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, p: f"{self.currency_symbol}{x*1e-3:.0f}K" if x < 1e6 else f"{self.currency_symbol}{x*1e-6:.2f}M"))

                for bar in bars:
                    w = bar.get_width()
                    ax.text(w + (max(revs) * 0.015), bar.get_y() + bar.get_height()/2, f"{self.currency_symbol}{w:,.0f}",
                            va="center", color=TEXT_LIGHT, fontsize=8.5, weight="bold")

                ax.set_xlim(0, max(revs) * 1.25)
                plt.title(f"{self.project_name} – Top 10 Revenue-Generating Products", color=TEXT_LIGHT, fontsize=13, weight="bold", pad=15)
                fig.tight_layout()

                c4_path = self.charts_dir / "04_top_products_ranking.png"
                fig.savefig(c4_path, facecolor=fig.get_facecolor(), edgecolor="none")
                plt.close(fig)
                charts_meta.append({
                    "id": "chart_top_products",
                    "title": "Top Products Ranking",
                    "filename": c4_path.name,
                    "path": str(c4_path)
                })
            except Exception as e:
                self._log(f"Warning: Could not generate Chart 4: {e}")

        # -------------------------------------------------------------
        # Chart 5: Executive 4-Quadrant Summary Dashboard
        # -------------------------------------------------------------
        try:
            fig = plt.figure(figsize=(14, 9), dpi=300)
            fig.patch.set_facecolor(BG_DARK)

            gs = fig.add_gridspec(2, 2, hspace=0.35, wspace=0.25, top=0.88, bottom=0.08, left=0.08, right=0.95)

            # Subplot (0,0): Revenue Trend
            ax_ts = fig.add_subplot(gs[0, 0])
            apply_dark_style(fig, ax_ts)
            if time_series:
                df_ts = pd.DataFrame(time_series)
                ax_ts.plot(df_ts["period"], df_ts["revenue"], color=ACCENT_BLUE, marker="o", linewidth=2, label="Revenue")
                ax_ts.plot(df_ts["period"], df_ts["cost"], color=ACCENT_ORANGE, marker="s", linewidth=2, label="COGS")
                ax_ts.set_title("Revenue vs COGS Monthly Trajectory", color=TEXT_LIGHT, fontsize=10, weight="bold")
                ax_ts.tick_params(axis="x", rotation=45, labelsize=7.5)
                ax_ts.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, p: f"{self.currency_symbol}{x*1e-3:.0f}K" if x < 1e6 else f"{self.currency_symbol}{x*1e-6:.1f}M"))
                ax_ts.legend(facecolor=CARD_DARK, edgecolor=BORDER_DARK, labelcolor=TEXT_LIGHT, fontsize=8)

            # Subplot (0,1): Margin %
            ax_mg = fig.add_subplot(gs[0, 1])
            apply_dark_style(fig, ax_mg)
            if time_series:
                df_ts = pd.DataFrame(time_series)
                ax_mg.plot(df_ts["period"], df_ts["marginPct"], color=ACCENT_GREEN, marker="^", linewidth=2.2, label="Gross Margin %")
                ax_mg.axhline(0, color=ACCENT_ORANGE, linestyle="--", alpha=0.6)
                ax_mg.set_title("Gross Margin % Trend", color=TEXT_LIGHT, fontsize=10, weight="bold")
                ax_mg.tick_params(axis="x", rotation=45, labelsize=7.5)
                ax_mg.yaxis.set_major_formatter(ticker.PercentFormatter())
                ax_mg.legend(facecolor=CARD_DARK, edgecolor=BORDER_DARK, labelcolor=TEXT_LIGHT, fontsize=8)

            # Subplot (1,0): Category Donut
            ax_cat = fig.add_subplot(gs[1, 0])
            apply_dark_style(fig, ax_cat)
            if by_category:
                df_cat = pd.DataFrame(by_category).head(5)
                wedges, texts, autotexts = ax_cat.pie(
                    df_cat["revenue"],
                    labels=df_cat["category"],
                    autopct="%1.1f%%",
                    colors=PALETTE[:len(df_cat)],
                    startangle=140,
                    wedgeprops=dict(width=0.45, edgecolor=BG_DARK, linewidth=1.5),
                    textprops=dict(color=TEXT_LIGHT, fontsize=8)
                )
                for autotext in autotexts:
                    autotext.set_color(TEXT_LIGHT)
                    autotext.set_weight("bold")
                ax_cat.set_title("Top Categories Revenue Share", color=TEXT_LIGHT, fontsize=10, weight="bold")

            # Subplot (1,1): Channel Bars
            ax_ch = fig.add_subplot(gs[1, 1])
            apply_dark_style(fig, ax_ch)
            if by_channel:
                df_ch = pd.DataFrame(by_channel).sort_values("revenue", ascending=True)
                ax_ch.barh(df_ch["channel"], df_ch["revenue"], color=ACCENT_PURPLE, height=0.55)
                ax_ch.set_title("Sales by Acquisition Channel", color=TEXT_LIGHT, fontsize=10, weight="bold")
                ax_ch.xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, p: f"{self.currency_symbol}{x*1e-3:.0f}K" if x < 1e6 else f"{self.currency_symbol}{x*1e-6:.1f}M"))

            # KPI Header Banner
            kpis = dashboard.get("kpis", {})
            rev_txt = f"{self.currency_symbol}{kpis.get('totalRevenue', 0):,.0f}"
            gp_txt = f"{self.currency_symbol}{kpis.get('grossProfit', 0):,.0f}"
            gm_txt = f"{kpis.get('grossMarginPct', 0):.1f}%"
            ord_txt = f"{kpis.get('totalOrders', 0):,}"

            fig.text(0.5, 0.95, f"{self.project_name} – Executive KPI Analytics Briefing",
                     ha="center", va="center", color=TEXT_LIGHT, fontsize=15, weight="bold")
            fig.text(0.5, 0.91, f"Gross Revenue: {rev_txt}   |   Gross Profit: {gp_txt}   |   Gross Margin: {gm_txt}   |   Total Orders: {ord_txt}",
                     ha="center", va="center", color=ACCENT_TEAL, fontsize=10.5, weight="bold")

            c5_path = self.charts_dir / "05_executive_summary_dashboard.png"
            fig.savefig(c5_path, facecolor=fig.get_facecolor(), edgecolor="none")
            plt.close(fig)
            charts_meta.append({
                "id": "chart_executive_dashboard",
                "title": "Executive Summary 4-Quadrant Dashboard",
                "filename": c5_path.name,
                "path": str(c5_path)
            })
        except Exception as e:
            self._log(f"Warning: Could not generate Chart 5: {e}")

        # -------------------------------------------------------------
        # Chart 6: Marketing ROAS & Spend Analysis (if marketing exists)
        # -------------------------------------------------------------
        marketing = dashboard.get("marketing", [])
        if marketing:
            try:
                fig, ax1 = plt.subplots(figsize=(9, 5), dpi=300)
                apply_dark_style(fig, ax1)

                df_mkt = pd.DataFrame(marketing)
                chans = df_mkt["channel"].astype(str).tolist()
                x_pos = np.arange(len(chans))
                spend = df_mkt["spend"].astype(float).values
                roas = df_mkt["roas"].astype(float).values

                width = 0.4
                ax1.bar(x_pos, spend, width=width, color=ACCENT_ORANGE, alpha=0.85, label="Ad Spend", zorder=2)
                ax1.set_ylabel(f"Ad Spend ({self.currency_symbol})", color=ACCENT_ORANGE, fontsize=10, weight="bold")
                ax1.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, p: f"{self.currency_symbol}{x*1e-3:.0f}K"))
                ax1.set_xticks(x_pos)
                ax1.set_xticklabels(chans, rotation=30, ha="right")

                ax2 = ax1.twinx()
                ax2.set_facecolor("none")
                ax2.plot(x_pos, roas, color=ACCENT_YELLOW, marker="D", linewidth=2.5, label="ROAS (x)", zorder=3)
                ax2.set_ylabel("ROAS Multiplier", color=ACCENT_YELLOW, fontsize=10, weight="bold")
                ax2.tick_params(colors=ACCENT_YELLOW, labelsize=9)
                ax2.spines["right"].set_color(ACCENT_YELLOW)
                ax2.spines["right"].set_linewidth(1.2)
                ax2.grid(False)

                lines1, labels1 = ax1.get_legend_handles_labels()
                lines2, labels2 = ax2.get_legend_handles_labels()
                ax1.legend(lines1 + lines2, labels1 + labels2, loc="upper right", facecolor=CARD_DARK, edgecolor=BORDER_DARK, labelcolor=TEXT_LIGHT, fontsize=9)

                plt.title(f"{self.project_name} – Marketing Channel Spend vs ROAS", color=TEXT_LIGHT, fontsize=13, weight="bold", pad=15)
                fig.tight_layout()

                c6_path = self.charts_dir / "06_marketing_roas_analysis.png"
                fig.savefig(c6_path, facecolor=fig.get_facecolor(), edgecolor="none")
                plt.close(fig)
                charts_meta.append({
                    "id": "chart_marketing_roas",
                    "title": "Marketing Spend vs ROAS",
                    "filename": c6_path.name,
                    "path": str(c6_path)
                })
            except Exception as e:
                self._log(f"Warning: Could not generate Chart 6: {e}")

        # -------------------------------------------------------------
        # Chart 7: Gross-to-Net Revenue Waterfall (Bridge Analysis)
        # -------------------------------------------------------------
        try:
            fig, ax = plt.subplots(figsize=(10.5, 5.5), dpi=300)
            apply_dark_style(fig, ax)

            kpis = dashboard.get("kpis", {})
            total_rev = float(kpis.get("totalRevenue", 0.0))
            total_cost = float(kpis.get("totalCost", 0.0))
            total_disc = float(kpis.get("totalDiscounts", 0.0))
            gross_profit = float(kpis.get("grossProfit", 0.0))
            returns_data = dashboard.get("returns", {})
            return_cnt = float(returns_data.get("totalReturns", 0))
            tot_orders = float(kpis.get("totalOrders", 1))
            avg_val = (total_rev / tot_orders) if tot_orders > 0 else 0.0
            return_val = round(return_cnt * avg_val * 0.8, 2) if return_cnt > 0 else 0.0

            gross_sales = total_rev + total_disc + return_val

            waterfall_steps = [
                ("Gross Sales", gross_sales, 0, ACCENT_BLUE, False),
                ("Discounts", -total_disc, gross_sales - total_disc, ACCENT_ORANGE, True),
                ("Returns", -return_val, gross_sales - total_disc - return_val, ACCENT_YELLOW, True),
                ("Net Revenue", total_rev, 0, ACCENT_TEAL, False),
                ("COGS", -total_cost, total_rev - total_cost, ACCENT_PURPLE, True),
                ("Gross Profit", gross_profit, 0, ACCENT_GREEN, False),
            ]

            x_indices = np.arange(len(waterfall_steps))
            step_names = [s[0] for s in waterfall_steps]

            for i, (name, val, bottom, color, is_delta) in enumerate(waterfall_steps):
                height = abs(val)
                bar_bottom = bottom if is_delta else 0
                ax.bar(i, height, bottom=bar_bottom, color=color, width=0.55, edgecolor=BORDER_DARK, linewidth=1.2, zorder=3)

                if i < len(waterfall_steps) - 1:
                    line_y = bar_bottom if (is_delta and val < 0) else (bar_bottom + height)
                    ax.plot([i + 0.275, i + 0.725], [line_y, line_y], color=TEXT_MUTED, linestyle=":", linewidth=1.2, zorder=2)

                label_y = bar_bottom + (height / 2) if is_delta else (height + (gross_sales * 0.02 if gross_sales > 0 else 1.0))
                sign = "-" if val < 0 else ""
                lbl = f"{sign}{self.currency_symbol}{abs(val)*1e-3:.1f}K" if abs(val) < 1e6 else f"{sign}{self.currency_symbol}{abs(val)*1e-6:.2f}M"
                ax.text(i, label_y, lbl, ha="center", va="center" if is_delta else "bottom",
                        color=TEXT_LIGHT, fontsize=8.5, weight="bold", zorder=4)

            ax.set_xticks(x_indices)
            ax.set_xticklabels(step_names, rotation=20, ha="right", fontsize=9)
            ax.set_ylabel(f"Amount ({self.currency_symbol})", color=TEXT_LIGHT, fontsize=10, weight="bold")
            ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, p: f"{self.currency_symbol}{x*1e-3:.0f}K" if x < 1e6 else f"{self.currency_symbol}{x*1e-6:.1f}M"))
            if gross_sales > 0:
                ax.set_ylim(0, gross_sales * 1.18)

            plt.title(f"{self.project_name} – Gross-to-Net Revenue & Margin Waterfall", color=TEXT_LIGHT, fontsize=13, weight="bold", pad=15)
            fig.tight_layout()

            c7_path = self.charts_dir / "07_gross_to_net_waterfall.png"
            fig.savefig(c7_path, facecolor=fig.get_facecolor(), edgecolor="none")
            plt.close(fig)
            charts_meta.append({
                "id": "chart_gross_to_net_waterfall",
                "title": "Gross-to-Net Revenue Waterfall",
                "filename": c7_path.name,
                "path": str(c7_path)
            })
        except Exception as e:
            self._log(f"Warning: Could not generate Chart 7: {e}")

        # -------------------------------------------------------------
        # Chart 8: Price Elasticity & Volume Distribution (Scatter)
        # -------------------------------------------------------------
        primary_fact = next((t for t in self.tables if t.name in ["orders", "fact_orders", "sales", "transactions"]), None)
        if not primary_fact:
            primary_fact = next((t for t in self.tables if t.table_type == "fact"), None)

        if primary_fact and primary_fact.name in self.processed_frames:
            try:
                df_fact = self.processed_frames[primary_fact.name].copy()
                prod_table = next((t for t in self.tables if "product" in t.name.lower()), None)
                if prod_table and prod_table.name in self.processed_frames and "product_id" in df_fact.columns:
                    pdf = self.processed_frames[prod_table.name]
                    pname = next((c for c in pdf.columns if "name" in c.lower() or "title" in c.lower()), None)
                    if pname and "product_id" in pdf.columns and pname not in df_fact.columns:
                        df_fact = df_fact.merge(pdf[["product_id", pname]].rename(columns={pname: "product_name"}), on="product_id", how="left")

                p_col = next((c for c in df_fact.columns if any(k in c.lower() for k in ["unit_price", "price", "selling_price", "rate"])), None)
                q_col = next((c for c in df_fact.columns if any(k in c.lower() for k in ["quantity", "qty", "units"])), None)
                r_col = next((c for c in df_fact.columns if any(k in c.lower() for k in ["revenue", "sales", "amount", "total"])), None)
                name_col = next((c for c in df_fact.columns if any(k in c.lower() for k in ["product_name", "item_name", "sku", "product"])), None)

                if p_col and q_col:
                    fig, ax = plt.subplots(figsize=(10, 5.5), dpi=300)
                    apply_dark_style(fig, ax)

                    if name_col:
                        agg_map = {p_col: "mean", q_col: "sum"}
                        if r_col:
                            agg_map[r_col] = "sum"
                        grouped = df_fact.groupby(name_col).agg(agg_map).reset_index()
                    else:
                        grouped = df_fact.sample(n=min(len(df_fact), 100), random_state=42)

                    prices = pd.to_numeric(grouped[p_col], errors="coerce").fillna(0.0).values
                    qtys = pd.to_numeric(grouped[q_col], errors="coerce").fillna(0.0).values
                    rev_vals = pd.to_numeric(grouped[r_col], errors="coerce").fillna(prices * qtys).values if r_col else prices * qtys
                    max_rev = max(rev_vals.max(), 1.0)
                    sizes = (rev_vals / max_rev * 350 + 50)

                    scatter = ax.scatter(
                        prices, qtys, s=sizes, c=rev_vals,
                        cmap="plasma", alpha=0.82, edgecolors=BORDER_DARK, linewidth=1.2, zorder=3
                    )
                    cbar = plt.colorbar(scatter, ax=ax, pad=0.02)
                    cbar.set_label(f"Volume Revenue ({self.currency_symbol})", color=TEXT_LIGHT, fontsize=9)
                    cbar.ax.tick_params(colors=TEXT_MUTED, labelsize=8)

                    ax.set_xlabel(f"Unit Selling Price ({self.currency_symbol})", color=TEXT_LIGHT, fontsize=10, weight="bold")
                    ax.set_ylabel("Total Units Sold", color=TEXT_LIGHT, fontsize=10, weight="bold")
                    ax.xaxis.set_major_formatter(ticker.FuncFormatter(lambda x, p: f"{self.currency_symbol}{x:,.0f}"))
                    ax.yaxis.set_major_formatter(ticker.FuncFormatter(lambda x, p: f"{x:,.0f}"))

                    if name_col and r_col:
                        top_pts = grouped.sort_values(r_col, ascending=False).head(3)
                        for _, r in top_pts.iterrows():
                            px = float(r[p_col]) if pd.notna(r[p_col]) else 0.0
                            qy = float(r[q_col]) if pd.notna(r[q_col]) else 0.0
                            ax.annotate(
                                str(r[name_col])[:20],
                                (px, qy),
                                textcoords="offset points", xytext=(8, 8),
                                color=TEXT_LIGHT, fontsize=8, weight="bold",
                                bbox=dict(boxstyle="round,pad=0.2", facecolor=BG_DARK, edgecolor=BORDER_DARK, alpha=0.85)
                            )

                    plt.title(f"{self.project_name} – Price Elasticity & Demand Distribution", color=TEXT_LIGHT, fontsize=13, weight="bold", pad=15)
                    fig.tight_layout()

                    c8_path = self.charts_dir / "08_price_elasticity_scatter.png"
                    fig.savefig(c8_path, facecolor=fig.get_facecolor(), edgecolor="none")
                    plt.close(fig)
                    charts_meta.append({
                        "id": "chart_price_elasticity",
                        "title": "Price Elasticity & Demand Scatter",
                        "filename": c8_path.name,
                        "path": str(c8_path)
                    })
            except Exception as e:
                self._log(f"Warning: Could not generate Chart 8: {e}")

        # -------------------------------------------------------------
        # Chart 9: Cross-Metric Correlation Heatmap
        # -------------------------------------------------------------
        if primary_fact and primary_fact.name in self.processed_frames:
            try:
                df_fact = self.processed_frames[primary_fact.name]
                num_cols = [c for c in df_fact.columns if pd.api.types.is_numeric_dtype(df_fact[c]) and df_fact[c].nunique() > 2]
                filtered_cols = [c for c in num_cols if any(k in c.lower() for k in ["rev", "sales", "qty", "quant", "price", "cost", "disc", "margin", "profit", "amount"])]
                if len(filtered_cols) < 3:
                    filtered_cols = num_cols[:6]

                if len(filtered_cols) >= 2:
                    fig, ax = plt.subplots(figsize=(8.5, 6.5), dpi=300)
                    apply_dark_style(fig, ax)

                    corr = df_fact[filtered_cols].corr()
                    clean_labels = [format_title(c) for c in filtered_cols]

                    cax = ax.matshow(corr, cmap="coolwarm", vmin=-1.0, vmax=1.0)
                    cbar = plt.colorbar(cax, ax=ax, fraction=0.046, pad=0.04)
                    cbar.set_label("Pearson Correlation (r)", color=TEXT_LIGHT, fontsize=9)
                    cbar.ax.tick_params(colors=TEXT_MUTED, labelsize=8)

                    ax.set_xticks(np.arange(len(clean_labels)))
                    ax.set_yticks(np.arange(len(clean_labels)))
                    ax.set_xticklabels(clean_labels, rotation=35, ha="left", color=TEXT_LIGHT, fontsize=8.5)
                    ax.set_yticklabels(clean_labels, color=TEXT_LIGHT, fontsize=8.5)

                    for (i, j), val in np.ndenumerate(corr.values):
                        if not np.isnan(val):
                            txt_color = "#18181B" if abs(val) > 0.55 else TEXT_LIGHT
                            ax.text(j, i, f"{val:+.2f}", ha="center", va="center", color=txt_color, fontsize=9, weight="bold")

                    plt.title(f"{self.project_name} – Cross-Metric Correlation Matrix", color=TEXT_LIGHT, fontsize=12, weight="bold", pad=25)
                    fig.tight_layout()

                    c9_path = self.charts_dir / "09_metric_correlation_matrix.png"
                    fig.savefig(c9_path, facecolor=fig.get_facecolor(), edgecolor="none")
                    plt.close(fig)
                    charts_meta.append({
                        "id": "chart_correlation_matrix",
                        "title": "Cross-Metric Correlation Heatmap",
                        "filename": c9_path.name,
                        "path": str(c9_path)
                    })
            except Exception as e:
                self._log(f"Warning: Could not generate Chart 9: {e}")

        self.charts = charts_meta
        self._log(f"Generated {len(charts_meta)} Matplotlib analytical charts in {self.charts_dir.name}/")
        return charts_meta

    def create_manifest(self, dashboard_data: Optional[Dict[str, Any]] = None) -> Path:
        """Step 8: Output complete structured JSON manifest for Electron UI."""
        self._log("Assembling pipeline manifest...", progress=98, stage="Finalizing")

        pbit_name = f"{clean_identifier(self.project_name)}.pbit"
        pbip_name = f"{clean_identifier(self.project_name)}.pbip"

        manifest_data: Dict[str, Any] = {
            "status": "SUCCESS",
            "projectName": self.project_name,
            "generatedAt": datetime.now().isoformat(),
            "sourceExcel": str(self.excel_path),
            "outputDirectory": str(self.output_dir),
            "summary": {
                "tablesCount": len(self.tables),
                "totalRows": sum(t.row_count for t in self.tables),
                "relationshipsCount": len(self.relationships),
                "measuresCount": len(self.dax_measures),
                "hasDateDimension": any(t.name == "dim_date" for t in self.tables)
            },
            "tables": [asdict(t) for t in self.tables],
            "relationships": [asdict(r) for r in self.relationships],
            "measures": [asdict(m) for m in self.dax_measures],
            "daxMeasures": [asdict(m) for m in self.dax_measures],
            "paths": {
                "outputDir": str(self.output_dir),
                "csvDir": str(self.csv_dir),
                "chartsDir": str(self.charts_dir),
                "powerbiDir": str(self.powerbi_dir),
                "pbitPath": str(self.powerbi_dir / pbit_name),
                "pbipPath": str(self.powerbi_dir / pbip_name),
                "daxPath": str(self.powerbi_dir / "measures.dax"),
                "pqPath": str(self.powerbi_dir / "power_query_m.pq"),
                "guidePath": str(self.output_dir / "POWERBI_DEPLOYMENT_GUIDE.md")
            },
            "license": {
                "name": "RevenueOS Source-Available Commercial & Royalty License (Version 1.0)",
                "author": "Sarvesh Sharma",
                "summary": "Free for non-commercial evaluation. Commercial exploitation, SaaS hosting, or resale strictly prohibited without written agreement and royalty payments."
            }
        }

        if self.charts:
            manifest_data["charts"] = self.charts
        if dashboard_data:
            manifest_data["dashboard"] = dashboard_data

        manifest_path = self.output_dir / "manifest.json"
        manifest_path.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")
        self._log(f"Manifest written to: {manifest_path.name}", progress=100, stage="Complete")

        if self.emit_manifest:
            print(f"PIPELINE_COMPLETE:{json.dumps(manifest_data)}", flush=True)

        return manifest_path

    def run(self) -> Path:
        """Execute full end-to-end transformation."""
        self.load_and_profile_sheets()
        self.analyze_and_build_model()
        self.export_csv_marts()
        self.synthesize_dax_measures()
        self.generate_power_query_m()
        self.compile_powerbi_artifacts()
        self.generate_step_by_step_guide()
        dashboard_data = self.compute_dashboard_aggregations()
        if self.generate_visuals and dashboard_data:
            self.generate_matplotlib_visuals(dashboard_data)
        manifest_path = self.create_manifest(dashboard_data)
        return manifest_path


# Aliases for backward compatibility
BackendEngine = CoreEngine
ExcelToPowerBIEngine = CoreEngine


def main():
    parser = argparse.ArgumentParser(
        description="RevenueOS Canonical Master Pipeline Engine"
    )
    parser.add_argument("excel_path", help="Path to source Excel workbook (.xlsx/.xls/.xlsm)")
    parser.add_argument("--output-dir", default=None, help="Directory to save generated artifacts")
    parser.add_argument("--project-name", default=None, help="Display name for the project")
    parser.add_argument("--currency", default="$", help="Currency symbol for DAX formatting (default: $)")
    parser.add_argument("--no-visuals", action="store_true", help="Skip matplotlib chart rendering")

    args = parser.parse_args()

    try:
        engine = CoreEngine(
            excel_path=args.excel_path,
            output_dir=args.output_dir,
            project_name=args.project_name,
            currency_symbol=args.currency,
            emit_manifest=True,
            generate_visuals=not args.no_visuals
        )
        engine.run()
    except Exception as e:
        err = {"status": "ERROR", "error": str(e)}
        print(f"PIPELINE_ERROR:{json.dumps(err)}", file=sys.stderr, flush=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
