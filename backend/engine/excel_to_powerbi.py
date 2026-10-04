"""
RevenueOS – Universal Excel to Power BI Pipeline Engine
======================================================
Analyzes ANY Excel workbook (.xlsx/.xls/.xlsm), dynamically profiles
tables and entities, builds an optimized Kimball Star Schema, generates
clean CSV marts, synthesizes tailored DAX measures, generates Power Query M,
compiles native Power BI Template (.pbit) and Project (.pbip), and provides
a comprehensive step-by-step deployment guide.
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


def clean_identifier(name: str) -> str:
    """Sanitize strings into clean SQL/Power BI table and column names."""
    s = str(name).strip()
    s = re.sub(r"[^\w\s-]", "", s)
    s = re.sub(r"[\s-]+", "_", s)
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
    table_type: str  # 'fact', 'dimension', 'calendar'
    row_count: int
    columns: List[ColumnMeta]
    primary_key: Optional[str] = None
    date_column: Optional[str] = None
    csv_filename: str = ""
    preview_rows: List[Dict[str, Any]] = field(default_factory=list)


@dataclass
class RelationshipMeta:
    from_table: str
    from_column: str
    to_table: str
    to_column: str
    cardinality: str = "OneToMany"  # Power BI OneToMany (to_table is 1, from_table is *)
    cross_filtering: str = "OneDirection"


@dataclass
class DaxMeasureMeta:
    name: str
    expression: str
    category: str
    description: str
    format_string: str = "#,0"
    table_name: str = "_Measures"


class ExcelToPowerBIEngine:
    """
    Universal Automated Engine converting arbitrary Excel files into
    ready-to-use Power BI dimensional models, CSVs, DAX, and templates.
    """

    def __init__(
        self,
        excel_path: str | Path,
        output_dir: Optional[str | Path] = None,
        project_name: Optional[str] = None,
        currency_symbol: str = "$",
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
        self.currency_symbol = currency_symbol

        # State storage
        self.raw_frames: Dict[str, pd.DataFrame] = {}
        self.processed_frames: Dict[str, pd.DataFrame] = {}
        self.tables: List[TableMeta] = []
        self.relationships: List[RelationshipMeta] = []
        self.dax_measures: List[DaxMeasureMeta] = []
        self.date_range: Tuple[Optional[datetime], Optional[datetime]] = (None, None)
        self.logs: List[str] = []

    def _log(self, message: str, progress: Optional[int] = None, stage: Optional[str] = None):
        """Record and stream progress event."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        entry = f"[{timestamp}] {message}"
        self.logs.append(entry)

        payload = {"message": message}
        if progress is not None:
            payload["progress"] = progress
        if stage is not None:
            payload["stage"] = stage

        # Stream structured JSON line to stdout for Electron IPC capture
        print(f"EVENT_JSON:{json.dumps(payload)}", flush=True)

    def load_and_profile_sheets(self) -> None:
        """Step 1: Read all sheets and profile columns, keys, and metrics."""
        self._log(f"Reading workbook: {self.excel_path.name}", progress=10, stage="Loading Excel")
        
        # Load all sheets
        excel_file = pd.ExcelFile(self.excel_path)
        sheet_names = excel_file.sheet_names
        self._log(f"Found {len(sheet_names)} sheet(s): {', '.join(sheet_names)}", progress=15)

        for sheet in sheet_names:
            df = excel_file.parse(sheet)
            # Skip empty sheets
            if df.empty or len(df.columns) == 0:
                self._log(f"Skipping empty sheet '{sheet}'")
                continue

            # Clean column names
            clean_cols = {}
            for col in df.columns:
                c = clean_identifier(str(col))
                # avoid collision
                base_c = c
                idx = 1
                while c in clean_cols.values():
                    c = f"{base_c}_{idx}"
                    idx += 1
                clean_cols[col] = c

            df = df.rename(columns=clean_cols)
            # Drop completely empty rows and columns
            df = df.dropna(how="all").dropna(axis=1, how="all")
            table_name = clean_identifier(sheet)
            self.raw_frames[table_name] = df
            self._log(f"Loaded '{table_name}': {len(df)} rows, {len(df.columns)} columns")

        if not self.raw_frames:
            raise ValueError("The provided Excel file contains no valid tabular data.")

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

        # Check date
        if pd.api.types.is_datetime64_any_dtype(series):
            is_date = True
            dtype = "datetime"
        elif any(k in col_lower for k in ["date", "timestamp", "created_at", "updated_at", "time", "day", "month"]):
            try:
                converted = pd.to_datetime(non_null.head(100), errors="coerce")
                if converted.notna().sum() > len(converted) * 0.7:
                    is_date = True
                    dtype = "datetime"
            except Exception:
                pass

        # Check numeric
        if not is_date:
            if pd.api.types.is_numeric_dtype(series):
                is_int = pd.api.types.is_integer_dtype(series) or (non_null % 1 == 0).all() if len(non_null) > 0 else False
                dtype = "int64" if is_int else "double"
                
                # Distinguish IDs/Keys from numerical metrics
                if any(k in col_lower for k in ["id", "key", "code", "zip", "postal", "phone", "year", "quarter"]):
                    is_key = True
                else:
                    is_metric = True
            elif pd.api.types.is_bool_dtype(series):
                dtype = "boolean"
            else:
                # String or categorical
                dtype = "string"
                if any(k in col_lower for k in ["id", "key", "code", "num", "no"]):
                    is_key = True
                else:
                    is_category = True

        # Candidate primary key check
        if unique_count == total_rows and total_rows > 0:
            if is_key or any(k in col_lower for k in ["id", "key", "code"]):
                is_key = True

        # Samples
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

        # Collect all dates for calendar generation
        min_date = None
        max_date = None

        intermediate_tables: Dict[str, TableMeta] = {}

        # Pass 1: Collect candidates and PKs
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
                        dates = pd.to_datetime(df[c.name].dropna(), errors="coerce")
                        valid_dates = dates[dates.notna()]
                        if not valid_dates.empty:
                            sheet_min = valid_dates.min().to_pydatetime()
                            sheet_max = valid_dates.max().to_pydatetime()
                            if min_date is None or sheet_min < min_date:
                                min_date = sheet_min
                            if max_date is None or sheet_max > max_date:
                                max_date = sheet_max
                    except Exception:
                        pass

            temp_data[tbl_name] = {
                "df": df,
                "cols_meta": cols_meta,
                "pk": pk,
                "date_col": date_col,
                "has_metric": any(c.is_metric for c in cols_meta)
            }

        # Pass 2: Determine Dimension vs Fact
        # Dimension signals: PK is referenced by other tables, or name matches known dimension entities
        dim_names_hints = ["customer", "product", "client", "user", "store", "supplier", "vendor", "channel", "category", "employee", "item", "dim"]
        fact_names_hints = ["order", "sale", "trans", "payment", "return", "inventory", "marketing", "event", "fact", "line", "detail"]

        for tbl_name, info in temp_data.items():
            t_lower = tbl_name.lower()
            is_referenced_by_others = False
            if info["pk"]:
                pk_name = info["pk"].lower()
                for other_name, other_info in temp_data.items():
                    if other_name != tbl_name:
                        for col in other_info["cols_meta"]:
                            if col.name.lower() == pk_name:
                                is_referenced_by_others = True
                                break

            # Decision
            if any(hint in t_lower for hint in dim_names_hints) or (info["pk"] is not None and is_referenced_by_others):
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
            previews = df.head(10).fillna("").to_dict(orient="records")

            table_meta = TableMeta(
                name=tbl_name,
                original_sheet=tbl_name,
                table_type=table_type,
                row_count=len(df),
                columns=info["cols_meta"],
                primary_key=info["pk"],
                date_column=info["date_col"],
                csv_filename=f"{tbl_name}.csv",
                preview_rows=previews
            )
            intermediate_tables[tbl_name] = table_meta
            self.processed_frames[tbl_name] = df

        # Special Case: Single Sheet Workbook Decomposition
        if len(self.raw_frames) == 1:
            self._decompose_single_sheet(list(self.raw_frames.keys())[0], intermediate_tables)

        # Build dim_date Calendar Dimension
        if min_date and max_date:
            self._log(f"Detected date range: {min_date.strftime('%Y-%m-%d')} to {max_date.strftime('%Y-%m-%d')}")
            dim_date_df = self._generate_calendar_dimension(min_date, max_date)
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
                preview_rows=dim_date_df.head(10).to_dict(orient="records")
            )
            intermediate_tables["dim_date"] = dim_date_meta
            self.processed_frames["dim_date"] = dim_date_df

        # Discover Relationships (Foreign Key matching)
        self.tables = list(intermediate_tables.values())
        self._detect_relationships()

    def _decompose_single_sheet(self, sheet_name: str, intermediate_tables: Dict[str, TableMeta]) -> None:
        """If user uploaded a single denormalized table, extract logical dimensions."""
        df = self.raw_frames[sheet_name]
        self._log(f"Single-table dataset detected ('{sheet_name}'). Inspecting for dimension decomposition...")

        cols = df.columns
        extracted_dims = {}

        # Look for customer dimension
        cust_cols = [c for c in cols if any(k in c.lower() for k in ["customer", "client", "buyer"])]
        cust_id = next((c for c in cust_cols if any(k in c.lower() for k in ["id", "code", "key", "number"])), None)
        if cust_id and len(cust_cols) > 1:
            dim_cust_df = df[cust_cols].drop_duplicates(subset=[cust_id]).dropna(subset=[cust_id])
            if len(dim_cust_df) < len(df) * 0.95:
                extracted_dims["dim_customer"] = (dim_cust_df, cust_id)
                self._log(f"  -> Extracted 'dim_customer' ({len(dim_cust_df)} unique records)")

        # Look for product dimension
        prod_cols = [c for c in cols if any(k in c.lower() for k in ["product", "item", "sku", "article"])]
        prod_id = next((c for c in prod_cols if any(k in c.lower() for k in ["id", "code", "key", "sku"])), None)
        if prod_id and len(prod_cols) > 1:
            dim_prod_df = df[prod_cols].drop_duplicates(subset=[prod_id]).dropna(subset=[prod_id])
            if len(dim_prod_df) < len(df) * 0.95:
                extracted_dims["dim_product"] = (dim_prod_df, prod_id)
                self._log(f"  -> Extracted 'dim_product' ({len(dim_prod_df)} unique records)")

        # If dimensions extracted, create them and streamline fact table
        if extracted_dims:
            fact_name = f"fact_{sheet_name}" if not sheet_name.startswith("fact_") else sheet_name
            intermediate_tables.pop(sheet_name, None)
            
            # Save extracted dimensions
            for dim_name, (dim_df, pk) in extracted_dims.items():
                dim_meta = TableMeta(
                    name=dim_name,
                    original_sheet=f"{sheet_name} (Decomposed)",
                    table_type="dimension",
                    row_count=len(dim_df),
                    columns=[self._infer_column_meta(dim_df, c) for c in dim_df.columns],
                    primary_key=pk,
                    csv_filename=f"{dim_name}.csv",
                    preview_rows=dim_df.head(10).to_dict(orient="records")
                )
                intermediate_tables[dim_name] = dim_meta
                self.processed_frames[dim_name] = dim_df

            # Update Fact table
            fact_meta = TableMeta(
                name=fact_name,
                original_sheet=sheet_name,
                table_type="fact",
                row_count=len(df),
                columns=[self._infer_column_meta(df, c) for c in df.columns],
                primary_key=next((c for c in df.columns if "order_id" in c or "transaction_id" in c or "id" == c), None),
                date_column=next((c for c in df.columns if any(k in c for k in ["date", "time"])), None),
                csv_filename=f"{fact_name}.csv",
                preview_rows=df.head(10).to_dict(orient="records")
            )
            intermediate_tables[fact_name] = fact_meta
            self.processed_frames[fact_name] = df

    def _generate_calendar_dimension(self, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """Create a complete Kimball Date Dimension dataframe."""
        # Buffer dates to start and end of years
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
        for target in self.tables:
            if not target.primary_key or target.name == "dim_date":
                continue
            pk = target.primary_key
            pk_clean = pk.lower()

            for source in self.tables:
                if source.name == target.name or source.name == "dim_date":
                    continue

                matched_col = None
                for col_meta in source.columns:
                    c_clean = col_meta.name.lower()
                    if c_clean == pk_clean or c_clean == f"{target.name}_{pk_clean}":
                        matched_col = col_meta.name
                        col_meta.is_foreign_key = True
                        break

                if matched_col:
                    # Target has the unique PK (1), Source has the FK (*)
                    # Avoid duplicate inverse relationships
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

        # Inspect Fact tables for metrics
        for fact in [t for t in self.tables if t.table_type == "fact"]:
            table_name = fact.name
            metrics = [c for c in fact.columns if c.is_metric]

            # 1. Row & Volume counts
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

            # Revenue / Sales / Monetary metrics
            rev_col = next((c.name for c in metrics if any(k in c.name.lower() for k in ["revenue", "sales", "amount", "total"])), None)
            cost_col = next((c.name for c in metrics if any(k in c.name.lower() for k in ["cost", "cogs", "expense"])), None)
            qty_col = next((c.name for c in metrics if any(k in c.name.lower() for k in ["quantity", "qty", "units"])), None)
            disc_col = next((c.name for c in metrics if any(k in c.name.lower() for k in ["discount"])), None)

            # Generate primary metrics
            for m in metrics:
                col_name = m.name
                title = format_title(col_name)
                is_curr = any(k in col_name.lower() for k in ["revenue", "sales", "amount", "cost", "price", "profit", "spend", "value"])
                fmt = f"\\{self.currency_symbol}#,0;(\\{self.currency_symbol}#,0);\\{self.currency_symbol}#,0" if is_curr else "#,0"
                
                # Total
                m_total_name = f"Total {title}"
                measures.append(DaxMeasureMeta(
                    name=m_total_name,
                    expression=f"SUM({table_name}[{col_name}])",
                    category="02 Core Metrics",
                    description=f"Aggregated sum of {col_name} in {table_name}",
                    format_string=fmt
                ))

                # Average
                m_avg_name = f"Average {title}"
                avg_fmt = f"\\{self.currency_symbol}#,##0.00" if is_curr else "#,##0.00"
                measures.append(DaxMeasureMeta(
                    name=m_avg_name,
                    expression=f"AVERAGE({table_name}[{col_name}])",
                    category="02 Core Metrics",
                    description=f"Arithmetic average of {col_name} in {table_name}",
                    format_string=avg_fmt
                ))

                # Time Intelligence if dim_date exists
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

            # Profitability & Margins (if revenue & cost exist)
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

            # Discounts & Leakage
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

        # Distinct counts on Dimensions
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
        self._log(f"Synthesized {len(measures)} production DAX measures across 5 categories.")

        # Save to measures.dax
        self.powerbi_dir.mkdir(parents=True, exist_ok=True)
        dax_file = self.powerbi_dir / "measures.dax"
        lines = [
            f"// ===================================================================",
            f"// {self.project_name} – DAX Semantic Measures Library",
            f"// Auto-generated by RevenueOS Pipeline Engine",
            f"// Generated At: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
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
        
        # Build TMSL DataModelSchema
        tmsl_tables = []

        # 1. Business Data Tables
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

        # 2. _Measures Table
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

        # 3. Relationships
        tmsl_rels = []
        for r in self.relationships:
            tmsl_rels.append({
                "name": f"{r.from_table}_{r.from_column}_to_{r.to_table}_{r.to_column}",
                "fromTable": r.from_table,
                "fromColumn": r.from_column,
                "toTable": r.to_table,
                "toColumn": r.to_column,
                "crossFilteringBehavior": "oneDirection",
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

        # Build .pbit (ZIP format)
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

        # Semantic model and report dirs
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

    def create_manifest(self) -> Path:
        """Step 8: Output complete structured JSON manifest for Electron UI."""
        self._log("Assembling pipeline manifest...", progress=98, stage="Finalizing")

        pbit_name = f"{clean_identifier(self.project_name)}.pbit"
        pbip_name = f"{clean_identifier(self.project_name)}.pbip"

        manifest_data = {
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
            "paths": {
                "outputDir": str(self.output_dir),
                "csvDir": str(self.csv_dir),
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
                "summary": "Free for non-commercial evaluation. Unauthorized commercial monetization, SaaS deployment, or resale is strictly prohibited without written agreement and royalty payments."
            }
        }

        manifest_path = self.output_dir / "manifest.json"
        manifest_path.write_text(json.dumps(manifest_data, indent=2), encoding="utf-8")
        self._log(f"Manifest written to: {manifest_path.name}", progress=100, stage="Complete")

        # Also print complete JSON payload marker for Electron process stdout
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
        manifest_path = self.create_manifest()
        return manifest_path


def main():
    parser = argparse.ArgumentParser(
        description="RevenueOS Universal Excel to Power BI Pipeline Engine"
    )
    parser.add_argument("excel_path", help="Path to source Excel workbook (.xlsx/.xls/.xlsm)")
    parser.add_argument("--output-dir", default=None, help="Directory to save generated artifacts")
    parser.add_argument("--project-name", default=None, help="Display name for the project")
    parser.add_argument("--currency", default="$", help="Currency symbol for DAX formatting (default: $)")

    args = parser.parse_args()

    try:
        engine = ExcelToPowerBIEngine(
            excel_path=args.excel_path,
            output_dir=args.output_dir,
            project_name=args.project_name,
            currency_symbol=args.currency
        )
        engine.run()
    except Exception as e:
        err = {"status": "ERROR", "error": str(e)}
        print(f"PIPELINE_ERROR:{json.dumps(err)}", file=sys.stderr, flush=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
