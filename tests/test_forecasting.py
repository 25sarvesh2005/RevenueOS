"""
RevenueOS – Tests for Forecasting Engine
==========================================
Validates:
  - Holt's linear smoothing
  - Linear trend regression
  - Confidence interval bounds consistency
  - Horizon lengths and formatting
"""

import numpy as np
import pandas as pd
import pytest

from python.forecasting.forecast_engine import ForecastEngine, generate_revenue_forecast


class TestForecasting:

    @pytest.fixture
    def historical_revenue_series(self):
        np.random.seed(42)
        n = 90
        trend = np.linspace(10000, 25000, n)
        noise = np.random.normal(0, 1000, n)
        return pd.Series(trend + noise)

    def test_holt_linear_smoothing(self, historical_revenue_series):
        engine = ForecastEngine(horizon_days=14)
        fc, low95, high95 = engine.holt_linear_smoothing(historical_revenue_series)

        assert len(fc) == 14
        assert len(low95) == 14
        assert len(high95) == 14

        # Bounds check: lower <= forecast <= upper
        for i in range(14):
            assert low95[i] <= fc[i] <= high95[i]

    def test_linear_trend_regression(self, historical_revenue_series):
        engine = ForecastEngine(horizon_days=21)
        fc, low95, high95 = engine.linear_trend_regression(historical_revenue_series)

        assert len(fc) == 21
        assert len(low95) == 21
        assert len(high95) == 21

        # Bounds check
        for i in range(21):
            assert low95[i] <= fc[i] <= high95[i]

    def test_generate_revenue_forecast_wrapper(self):
        dates = pd.date_range("2024-01-01", periods=60, freq="D")
        sales = np.linspace(5000, 12000, 60)
        df = pd.DataFrame({"report_date": dates, "net_sales": sales})

        forecast_df = generate_revenue_forecast(df, horizon_days=10, method="holt")
        assert not forecast_df.empty
        # Total rows should be 60 historical + 10 forecast = 70
        assert len(forecast_df) == 70

        future_rows = forecast_df[forecast_df["series_type"] == "FORECAST"]
        assert len(future_rows) == 10
        assert all(future_rows["lower_bound_95"] <= future_rows["value"])
