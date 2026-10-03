"""
RevenueOS – Time Series Forecasting Engine
============================================
Provides reliable, grounded forecasting for:
  1. Net Revenue / Sales
  2. Order Volume
  3. Product Demand (Units Sold)

Forecasting Methodologies:
  - Simple & Exponential Smoothing (SES / Holt's Linear Trend)
  - Rolling Window Moving Averages (7-day, 14-day, 30-day)
  - Linear Trend with 80% & 95% Confidence / Prediction Intervals

Outputs are formatted for direct Power BI consumption and executive planning.
"""

from __future__ import annotations

import sys
from datetime import date, datetime, timedelta
from pathlib import Path
from typing import Literal, Optional, Tuple, Dict, Any

import numpy as np
import pandas as pd
from scipy import stats

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config import logger


class ForecastEngine:
    """Statistical time series forecasting for business metrics."""

    def __init__(self, horizon_days: int = 30):
        self.horizon_days = horizon_days

    # ---------------------------------------------------------------------------
    # Method 1: Holt's Linear Exponential Smoothing (Level + Trend)
    # ---------------------------------------------------------------------------
    def holt_linear_smoothing(
        self,
        series: pd.Series,
        alpha: float = 0.3,
        beta: float = 0.1,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Double exponential smoothing (Holt's method).
        Returns: (forecasts, lower_bounds_95, upper_bounds_95)
        """
        y = series.values.astype(float)
        n = len(y)
        if n < 3:
            # Fallback for ultra-short series
            mean_val = np.mean(y) if n > 0 else 0.0
            return (
                np.full(self.horizon_days, mean_val),
                np.full(self.horizon_days, mean_val * 0.8),
                np.full(self.horizon_days, mean_val * 1.2),
            )

        level = y[0]
        trend = y[1] - y[0]
        fitted = np.zeros(n)
        fitted[0] = level

        for t in range(1, n):
            last_level = level
            level = alpha * y[t] + (1 - alpha) * (last_level + trend)
            trend = beta * (level - last_level) + (1 - beta) * trend
            fitted[t] = level + trend

        # Residual standard error
        residuals = y[1:] - fitted[:-1]
        residual_std = np.std(residuals) if len(residuals) > 1 else (y.std() or 1.0)

        forecasts = np.zeros(self.horizon_days)
        lower_95 = np.zeros(self.horizon_days)
        upper_95 = np.zeros(self.horizon_days)

        for h in range(1, self.horizon_days + 1):
            fc = level + h * trend
            # Variance expands with forecast horizon sqrt(h)
            margin = 1.96 * residual_std * np.sqrt(h)
            forecasts[h - 1] = max(0.0, fc)
            lower_95[h - 1] = max(0.0, fc - margin)
            upper_95[h - 1] = max(0.0, fc + margin)

        return forecasts, lower_95, upper_95

    # ---------------------------------------------------------------------------
    # Method 2: Linear Trend Regression with Prediction Intervals
    # ---------------------------------------------------------------------------
    def linear_trend_regression(
        self,
        series: pd.Series,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Ordinary Least Squares regression over time index.
        Returns: (forecasts, lower_bounds_95, upper_bounds_95)
        """
        y = series.values.astype(float)
        n = len(y)
        if n < 3:
            return self.holt_linear_smoothing(series)

        x = np.arange(n)
        slope, intercept, r_val, p_val, std_err = stats.linregress(x, y)

        fitted = intercept + slope * x
        residuals = y - fitted
        se = np.sqrt(np.sum(residuals**2) / (n - 2)) if n > 2 else np.std(residuals)

        x_future = np.arange(n, n + self.horizon_days)
        forecasts = intercept + slope * x_future

        # Prediction interval formula: se * sqrt(1 + 1/n + (x0 - x_bar)^2 / sum(xi - x_bar)^2)
        x_bar = np.mean(x)
        ss_x = np.sum((x - x_bar) ** 2) if np.sum((x - x_bar) ** 2) > 0 else 1.0

        lower_95 = np.zeros(self.horizon_days)
        upper_95 = np.zeros(self.horizon_days)

        t_crit = stats.t.ppf(0.975, df=max(1, n - 2))

        for i, x0 in enumerate(x_future):
            pi_margin = t_crit * se * np.sqrt(1 + 1 / n + (x0 - x_bar) ** 2 / ss_x)
            lower_95[i] = max(0.0, forecasts[i] - pi_margin)
            upper_95[i] = max(0.0, forecasts[i] + pi_margin)
            forecasts[i] = max(0.0, forecasts[i])

        return forecasts, lower_95, upper_95


def generate_revenue_forecast(
    daily_financials_df: pd.DataFrame,
    horizon_days: int = 30,
    method: Literal["holt", "regression"] = "holt",
) -> pd.DataFrame:
    """
    Produce daily net sales forecast table for the next `horizon_days`.
    Combines historical actuals with future projections.
    """
    if daily_financials_df.empty or "report_date" not in daily_financials_df.columns:
        logger.warning("generate_revenue_forecast: empty or invalid daily_financials dataframe.")
        return pd.DataFrame()

    df = daily_financials_df.copy()
    df["report_date"] = pd.to_datetime(df["report_date"])
    # Aggregate daily net revenue across all slices if multiple
    daily_agg = df.groupby("report_date")["net_sales"].sum().sort_index()

    engine = ForecastEngine(horizon_days=horizon_days)

    if method == "holt":
        fc, low95, high95 = engine.holt_linear_smoothing(daily_agg)
    else:
        fc, low95, high95 = engine.linear_trend_regression(daily_agg)

    last_date = daily_agg.index.max().date()
    future_dates = [last_date + timedelta(days=i) for i in range(1, horizon_days + 1)]

    # Historical rows
    hist_records = []
    for dt, val in daily_agg.items():
        hist_records.append({
            "forecast_date": dt.date().isoformat(),
            "series_type": "ACTUAL",
            "metric": "net_sales",
            "value": round(float(val), 2),
            "lower_bound_95": None,
            "upper_bound_95": None,
            "method": "RECORDED",
        })

    # Future forecast rows
    for dt, val, low, high in zip(future_dates, fc, low95, high95):
        hist_records.append({
            "forecast_date": dt.isoformat(),
            "series_type": "FORECAST",
            "metric": "net_sales",
            "value": round(float(val), 2),
            "lower_bound_95": round(float(low), 2),
            "upper_bound_95": round(float(high), 2),
            "method": method.upper(),
        })

    result_df = pd.DataFrame(hist_records)
    logger.info("✓ Generated %d-day revenue forecast using %s method.", horizon_days, method)
    return result_df


if __name__ == "__main__":
    # Test harness
    print("Testing Forecast Engine standalone...")
    dates = pd.date_range("2024-01-01", "2024-06-30", freq="D")
    trend = np.linspace(50000, 85000, len(dates))
    noise = np.random.normal(0, 4000, len(dates))
    mock_df = pd.DataFrame({"report_date": dates, "net_sales": trend + noise})

    fc_df = generate_revenue_forecast(mock_df, horizon_days=30, method="holt")
    print(fc_df.tail(15).to_string())
