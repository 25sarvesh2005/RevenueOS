"""
RevenueOS Dynamic DAX Evaluator Engine
======================================
Parses and evaluates DAX semantic formulas (aggregations, distinct counts,
safe division, compound measure arithmetic) against in-memory Pandas DataFrames
or persisted CSV marts.
"""

from __future__ import annotations

import json
import math
import os
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd


class DaxEvaluator:
    """
    Pandas-backed runtime evaluator for Power BI DAX expressions.
    Supports SUM, AVERAGE, MIN, MAX, COUNTROWS, DISTINCTCOUNT, DIVIDE,
    named measure resolution, and arithmetic operators.
    """

    def __init__(
        self,
        tables: Optional[Dict[str, pd.DataFrame]] = None,
        data_dir: Optional[str | Path] = None,
        currency_symbol: str = "$",
    ):
        self.tables: Dict[str, pd.DataFrame] = tables or {}
        self.data_dir: Optional[Path] = Path(data_dir).resolve() if data_dir else None
        self.currency_symbol: str = currency_symbol
        self.known_measures: Dict[str, str] = {}  # name -> formula

        if self.data_dir and self.data_dir.exists():
            self._load_from_directory(self.data_dir)
        else:
            self._synthesize_canonical_measures()

    def _synthesize_canonical_measures(self) -> None:
        """Synthesize standard baseline measures if tables exist and measures aren't explicit."""
        for t_name, df in self.tables.items():
            if "order" in t_name:
                rev_col = next((c for c in df.columns if any(k in c.lower() for k in ["revenue", "sales", "amount", "total_price"])), None)
                target_col = rev_col if rev_col else "revenue"
                if "total revenue" not in self.known_measures:
                    self.known_measures["total revenue"] = f"SUM({t_name}[{target_col}])"
                if "total gross profit" not in self.known_measures:
                    self.known_measures["total gross profit"] = f"SUM({t_name}[{target_col}]) * 0.35"
                if "total orders" not in self.known_measures:
                    self.known_measures["total orders"] = f"COUNTROWS({t_name})"
                if "average order value" not in self.known_measures:
                    self.known_measures["average order value"] = f"AVERAGE({t_name}[{target_col}])"

    def _load_from_directory(self, base_dir: Path) -> None:
        """Load CSV tables and DAX definitions from an export directory."""
        # 1. Load CSVs from csv/ or directly
        csv_dir = base_dir / "csv" if (base_dir / "csv").exists() else base_dir
        for csv_file in csv_dir.glob("*.csv"):
            table_name = csv_file.stem.lower()
            try:
                self.tables[table_name] = pd.read_csv(csv_file, low_memory=False)
            except Exception:
                pass

        # 2. Load manifest for measures and formatting
        manifest_path = base_dir / "manifest.json"
        if manifest_path.exists():
            try:
                with open(manifest_path, "r", encoding="utf-8") as f:
                    manifest = json.load(f)
                    measures_list = manifest.get("measures") or manifest.get("daxMeasures") or []
                    for m in measures_list:
                        m_name = m.get("name", "").strip()
                        m_expr = m.get("expression", "").strip()
                        if m_name and m_expr:
                            self.known_measures[m_name.lower()] = m_expr
            except Exception:
                pass

        # 3. Baseline synthesized measures
        self._synthesize_canonical_measures()

    def register_dataframe(self, name: str, df: pd.DataFrame) -> None:
        """Register a table DataFrame for evaluation."""
        self.tables[name.lower()] = df
        self._synthesize_canonical_measures()

    def register_measure(self, name: str, expression: str) -> None:
        """Register a named DAX measure expression."""
        self.known_measures[name.lower()] = expression

    def _resolve_table_column(self, table_name: str, col_name: str) -> Tuple[pd.DataFrame, str]:
        """Find matching table and column case-insensitively."""
        t_key = table_name.lower().strip()
        matched_table = self.tables.get(t_key)
        if matched_table is None:
            # Fuzzy match table (e.g. "order" -> "orders" or "fact_orders")
            for k in self.tables:
                if t_key in k or k in t_key:
                    matched_table = self.tables[k]
                    break

        if matched_table is None:
            raise ValueError(f"Table '{table_name}' not found. Available tables: {list(self.tables.keys())}")

        col_key = col_name.lower().strip()
        matched_col = next((c for c in matched_table.columns if c.lower() == col_key), None)
        if matched_col is None:
            # Try fuzzy match column
            matched_col = next((c for c in matched_table.columns if col_key in c.lower()), None)

        if matched_col is None:
            # Handle derived financial metrics if price and quantity are present
            if col_key in ("revenue", "sales", "net_sales", "amount"):
                price_c = next((c for c in matched_table.columns if any(k in c.lower() for k in ["unit_price", "price", "selling_price", "rate"])), None)
                qty_c = next((c for c in matched_table.columns if any(k in c.lower() for k in ["quantity", "qty", "units"])), None)
                if price_c and qty_c:
                    q = pd.to_numeric(matched_table[qty_c], errors="coerce").fillna(1.0)
                    p = pd.to_numeric(matched_table[price_c], errors="coerce").fillna(0.0)
                    gross = q * p
                    disc_c = next((c for c in matched_table.columns if "discount" in c.lower()), None)
                    if disc_c:
                        d = pd.to_numeric(matched_table[disc_c], errors="coerce").fillna(0.0)
                        if d.max() <= 1.0:
                            matched_table["revenue"] = gross * (1.0 - d.clip(0, 1))
                        else:
                            matched_table["revenue"] = (gross - d).clip(lower=0)
                    else:
                        matched_table["revenue"] = gross
                    return matched_table, "revenue"

            raise ValueError(f"Column '{col_name}' not found in table '{table_name}'. Columns: {list(matched_table.columns)}")

        return matched_table, matched_col

    def _eval_atomic(self, token: str) -> float:
        """Evaluate a single atomic expression: function, measure reference, or literal number."""
        token = token.strip()
        if not token:
            return 0.0

        # Literal number
        try:
            return float(token)
        except ValueError:
            pass

        # Check for measure reference: [Measure Name] or bare Measure Name
        measure_clean = token.strip("[]").strip().lower()
        if measure_clean in self.known_measures:
            formula = self.known_measures[measure_clean]
            return self.evaluate_expression(formula)[0]
        for k, formula in self.known_measures.items():
            if measure_clean in k or k in measure_clean:
                return self.evaluate_expression(formula)[0]

        # 1. SUM(table[col])
        m = re.match(r"^SUM\s*\(\s*(\w+)\s*\[\s*(\w+)\s*\]\s*\)$", token, re.IGNORECASE)
        if m:
            t, c = self._resolve_table_column(m.group(1), m.group(2))
            series = pd.to_numeric(t[c], errors="coerce").dropna()
            return float(series.sum())

        # 2. AVERAGE(table[col])
        m = re.match(r"^AVERAGE\s*\(\s*(\w+)\s*\[\s*(\w+)\s*\]\s*\)$", token, re.IGNORECASE)
        if m:
            t, c = self._resolve_table_column(m.group(1), m.group(2))
            series = pd.to_numeric(t[c], errors="coerce").dropna()
            return float(series.mean()) if len(series) > 0 else 0.0

        # 3. MIN(table[col])
        m = re.match(r"^MIN\s*\(\s*(\w+)\s*\[\s*(\w+)\s*\]\s*\)$", token, re.IGNORECASE)
        if m:
            t, c = self._resolve_table_column(m.group(1), m.group(2))
            series = pd.to_numeric(t[c], errors="coerce").dropna()
            return float(series.min()) if len(series) > 0 else 0.0

        # 4. MAX(table[col])
        m = re.match(r"^MAX\s*\(\s*(\w+)\s*\[\s*(\w+)\s*\]\s*\)$", token, re.IGNORECASE)
        if m:
            t, c = self._resolve_table_column(m.group(1), m.group(2))
            series = pd.to_numeric(t[c], errors="coerce").dropna()
            return float(series.max()) if len(series) > 0 else 0.0

        # 5. COUNTROWS(table)
        m = re.match(r"^COUNTROWS\s*\(\s*(\w+)\s*\)$", token, re.IGNORECASE)
        if m:
            t_key = m.group(1).lower().strip()
            tbl = self.tables.get(t_key)
            if tbl is not None:
                return float(len(tbl))
            for k, df in self.tables.items():
                if t_key in k:
                    return float(len(df))
            raise ValueError(f"Table '{m.group(1)}' not found for COUNTROWS")

        # 6. DISTINCTCOUNT(table[col])
        m = re.match(r"^DISTINCTCOUNT\s*\(\s*(\w+)\s*\[\s*(\w+)\s*\]\s*\)$", token, re.IGNORECASE)
        if m:
            t, c = self._resolve_table_column(m.group(1), m.group(2))
            return float(t[c].nunique(dropna=True))

        # 7. DIVIDE(numerator, denominator[, alternate])
        m = re.match(r"^DIVIDE\s*\(\s*(.+?)\s*,\s*(.+?)(?:\s*,\s*(.+?))?\s*\)$", token, re.IGNORECASE)
        if m:
            num_expr = m.group(1).strip()
            den_expr = m.group(2).strip()
            alt_expr = m.group(3).strip() if m.group(3) else "0"

            num_val = self.evaluate_expression(num_expr)[0]
            den_val = self.evaluate_expression(den_expr)[0]
            alt_val = float(alt_expr) if alt_expr.replace(".", "", 1).isdigit() else 0.0

            if den_val == 0.0 or math.isnan(den_val) or math.isinf(den_val):
                return alt_val
            return float(num_val / den_val)

        raise ValueError(f"Unrecognized or unsupported DAX construct: '{token}'")

    def evaluate_expression(self, expression: str) -> Tuple[float, str]:
        """
        Evaluate full DAX expression (including +, -, *, /, DIVIDE, and measure lookups).
        Returns (numeric_result, inferred_format_type).
        """
        expr = expression.strip()
        if not expr:
            return 0.0, "number"

        # Strip leading measure assignment if present: e.g. [Total Revenue] = ... or TotalRevenue = ...
        eq_match = re.match(r"^(\[.*?\]|\w+)\s*=\s*(.+)$", expr)
        if eq_match:
            expr = eq_match.group(2).strip()

        # Check if entire expression is a DIVIDE call
        if expr.upper().startswith("DIVIDE(") and expr.endswith(")"):
            val = self._eval_atomic(expr)
            return val, "percentage" if "margin" in expr.lower() or "%" in expr else "number"

        # Check if wrapped in single atomic function
        for prefix in ["SUM(", "AVERAGE(", "MIN(", "MAX(", "COUNTROWS(", "DISTINCTCOUNT("]:
            if expr.upper().startswith(prefix) and expr.endswith(")"):
                val = self._eval_atomic(expr)
                return val, "currency" if any(k in expr.lower() for k in ["revenue", "sales", "cost", "price", "profit", "spend", "amount"]) else "number"

        # Check for named measure reference [Name]
        if expr.startswith("[") and expr.endswith("]"):
            clean_name = expr[1:-1].strip().lower()
            if clean_name in self.known_measures:
                sub_expr = self.known_measures[clean_name]
                return self.evaluate_expression(sub_expr)
            for k, sub_expr in self.known_measures.items():
                if clean_name in k or k in clean_name:
                    return self.evaluate_expression(sub_expr)

        # Parse binary expression with brackets: e.g. [Total Revenue] - [Total Cost]
        # or SUM(orders[revenue]) - SUM(orders[cost])
        binary_match = re.match(r"^(.+?)\s*([+\-*/])\s*(.+)$", expr)
        if binary_match:
            left_part = binary_match.group(1).strip()
            op = binary_match.group(2).strip()
            right_part = binary_match.group(3).strip()

            left_val = self.evaluate_expression(left_part)[0]
            right_val = self.evaluate_expression(right_part)[0]

            if op == "+":
                res = left_val + right_val
            elif op == "-":
                res = left_val - right_val
            elif op == "*":
                res = left_val * right_val
            elif op == "/":
                res = left_val / right_val if right_val != 0 else 0.0
            else:
                res = 0.0

            fmt_type = "currency" if any(k in expr.lower() for k in ["revenue", "cost", "profit", "sales"]) else "number"
            return res, fmt_type

        # Direct atomic fallback
        val = self._eval_atomic(expr)
        return val, "number"

    def format_result(self, value: float, format_type: str) -> str:
        """Format raw numeric result with appropriate currency, percent, or integer representation."""
        if math.isnan(value) or math.isinf(value):
            return "N/A"

        if format_type == "percentage":
            # If value is already in 0-100 range or 0-1 range
            pct = value * 100 if abs(value) <= 1.0 and value != 0 else value
            return f"{pct:.1f}%"
        elif format_type == "currency":
            if abs(value) >= 1_000_000:
                return f"{self.currency_symbol}{value / 1_000_000:.2f}M"
            elif abs(value) >= 1_000:
                return f"{self.currency_symbol}{value:,.0f}"
            else:
                return f"{self.currency_symbol}{value:,.2f}"
        else:
            if value.is_integer():
                return f"{int(value):,}"
            return f"{value:,.2f}"

    def evaluate(self, expression: str) -> Dict[str, Any]:
        """High-level evaluation method returning typed evaluation summary."""
        t0 = time.time()
        try:
            val, fmt_type = self.evaluate_expression(expression)
            elapsed_ms = round((time.time() - t0) * 1000, 2)
            formatted = self.format_result(val, fmt_type)
            return {
                "expression": expression,
                "status": "SUCCESS",
                "evaluated_value": round(val, 4),
                "formatted_value": formatted,
                "data_type": "double" if isinstance(val, float) else "int64",
                "execution_time_ms": elapsed_ms,
                "error": None,
            }
        except Exception as exc:
            elapsed_ms = round((time.time() - t0) * 1000, 2)
            return {
                "expression": expression,
                "status": "ERROR",
                "evaluated_value": None,
                "formatted_value": None,
                "data_type": "error",
                "execution_time_ms": elapsed_ms,
                "error": str(exc),
            }
