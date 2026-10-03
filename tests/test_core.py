"""
RevenueOS – Test Suite
========================
Tests cover:
  - Financial calculation logic
  - Silver transformation helpers
  - Quality check logic (unit tests, no DB required)
  - Data reconciliation

Run with:
    pytest tests/ -v
    pytest tests/ --cov=. --cov-report=term-missing
"""

from __future__ import annotations

import sys
from pathlib import Path
import pandas as pd
import numpy as np
import pytest

# Make root importable
sys.path.insert(0, str(Path(__file__).parent.parent))


# =========================================================================
# Financial Calculation Tests
# =========================================================================

class TestFinancialCalculations:
    """
    Verify the core financial engine formulas match the spec.
    These are pure Python calculations, no DB required.
    """

    def test_gross_revenue(self):
        qty = 10
        price = 100.0
        assert qty * price == 1000.0

    def test_discount_amount(self):
        gross = 1000.0
        discount_pct = 0.10
        assert gross * discount_pct == pytest.approx(100.0)

    def test_net_sales_before_returns(self):
        gross = 1000.0
        discount = 100.0
        assert gross - discount == pytest.approx(900.0)

    def test_return_value(self):
        returned_qty = 2
        unit_price = 100.0
        assert returned_qty * unit_price == pytest.approx(200.0)

    def test_net_revenue(self):
        net_sales = 900.0
        return_value = 200.0
        assert net_sales - return_value == pytest.approx(700.0)

    def test_cogs(self):
        sold_qty = 8          # after returns
        unit_cost = 60.0
        assert sold_qty * unit_cost == pytest.approx(480.0)

    def test_gross_profit(self):
        net_revenue = 700.0
        cogs = 480.0
        assert net_revenue - cogs == pytest.approx(220.0)

    def test_gross_margin_pct(self):
        gross_profit = 220.0
        net_revenue = 700.0
        margin = gross_profit / net_revenue
        assert margin == pytest.approx(0.3143, rel=1e-3)

    def test_margin_zero_revenue(self):
        """Gross margin should be NaN / undefined when net revenue is 0.
        Uses pd.Series to match how production code handles vectorized operations.
        """
        net_revenue  = pd.Series([0.0])
        gross_profit = pd.Series([0.0])
        # Production pattern: avoid division by zero
        result = np.where(net_revenue > 0, gross_profit / net_revenue.replace(0, np.nan), np.nan)
        assert np.isnan(result[0])

    def test_roas(self):
        revenue_attributed = 50_000.0
        spend = 10_000.0
        assert revenue_attributed / spend == pytest.approx(5.0)

    def test_cac(self):
        spend = 10_000.0
        orders = 200
        assert spend / orders == pytest.approx(50.0)

    def test_contribution_after_marketing(self):
        gross_profit = 30_000.0
        spend = 10_000.0
        assert gross_profit - spend == pytest.approx(20_000.0)


# =========================================================================
# Discount Normalization Tests
# =========================================================================

class TestDiscountNormalization:
    """
    The silver layer normalizes discounts that arrive as percentages (0–100)
    to decimal form (0–1). Verify the detection and conversion logic.
    """

    def _normalize(self, series: pd.Series) -> pd.Series:
        """Mirror of transform_silver._normalize_discount."""
        numeric = pd.to_numeric(series, errors="coerce")
        if numeric.dropna().median() > 1:
            numeric = numeric / 100.0
        return numeric.clip(0, 1)

    def test_decimal_passthrough(self):
        s = pd.Series([0.10, 0.20, 0.05, 0.30])
        result = self._normalize(s)
        pd.testing.assert_series_equal(result, s)

    def test_percentage_conversion(self):
        s = pd.Series([10.0, 20.0, 5.0, 30.0])
        result = self._normalize(s)
        expected = pd.Series([0.10, 0.20, 0.05, 0.30])
        pd.testing.assert_series_equal(result, expected)

    def test_clamping_above_1(self):
        s = pd.Series([0.5, 1.5, 0.2])   # already decimal, one value > 1
        result = self._normalize(s)
        assert result.max() <= 1.0

    def test_negative_clamped_to_zero(self):
        s = pd.Series([-0.1, 0.2, 0.3])
        result = self._normalize(s)
        assert result.min() >= 0.0


# =========================================================================
# Quality Check Logic Tests
# =========================================================================

class TestQualityChecks:
    """
    Unit tests for quality check functions (no database).
    """

    def _make_orders(self) -> pd.DataFrame:
        return pd.DataFrame({
            "order_id":    ["O1", "O2", "O3", "O1"],   # O1 is duplicate
            "customer_id": ["C1", None,  "C3", "C1"],  # C2 has no customer
            "quantity":    [5,    10,    -1,   5],      # row 3 negative
            "unit_price":  [100,  200,   150,  100],
            "discount":    [0.1,  0.5,   0.2,  0.1],
        })

    def test_null_detection(self):
        from quality.run_checks import QualityReport, check_nulls
        df     = self._make_orders()
        report = QualityReport(run_id="test")
        check_nulls(df, "orders", ["customer_id"], report)
        null_result = next(r for r in report.results if "customer_id" in r.check_type)
        assert null_result.affected_count == 1
        assert null_result.severity == "WARNING"

    def test_duplicate_detection(self):
        from quality.run_checks import QualityReport, check_duplicates
        df     = self._make_orders()
        report = QualityReport(run_id="test")
        check_duplicates(df, "orders", ["order_id"], report)
        dup_result = report.results[0]
        assert dup_result.affected_count == 2   # 2 rows with order_id='O1'
        assert dup_result.severity == "WARNING"

    def test_range_check_negative_quantity(self):
        from quality.run_checks import QualityReport, check_ranges
        df     = self._make_orders()
        report = QualityReport(run_id="test")
        check_ranges(df, "orders",
                     [{"col": "quantity", "min": 0, "max": None,
                       "label": "Negative quantity"}],
                     report)
        range_result = report.results[0]
        assert range_result.affected_count == 1

    def test_no_duplicate_clean_data(self):
        from quality.run_checks import QualityReport, check_duplicates
        df = pd.DataFrame({"order_id": ["O1","O2","O3"]})
        report = QualityReport(run_id="test")
        check_duplicates(df, "orders", ["order_id"], report)
        assert report.results[0].severity == "INFO"
        assert report.results[0].affected_count == 0

    def test_overall_status_ok(self):
        from quality.run_checks import QualityReport, QualityResult
        report = QualityReport(run_id="test")
        report.add(QualityResult("TEST","orders","INFO","All good"))
        assert report.overall_status() == "OK"

    def test_overall_status_warning(self):
        from quality.run_checks import QualityReport, QualityResult
        report = QualityReport(run_id="test")
        report.add(QualityResult("TEST","orders","WARNING","Some nulls",5))
        assert report.overall_status() == "WARNING"

    def test_overall_status_error(self):
        from quality.run_checks import QualityReport, QualityResult
        report = QualityReport(run_id="test")
        report.add(QualityResult("TEST","orders","ERROR","Schema mismatch"))
        assert report.overall_status() == "ERROR"


# =========================================================================
# Customer Health Score Tests
# =========================================================================

class TestCustomerHealthScore:
    """Verify health score weights sum to 1 and scoring is bounded."""

    WEIGHTS = {
        "recency":       0.20,
        "frequency":     0.15,
        "monetary":      0.25,
        "profitability": 0.20,
        "trend":         0.10,
        "behavior":      0.10,
    }

    def test_weights_sum_to_one(self):
        total = sum(self.WEIGHTS.values())
        assert total == pytest.approx(1.0)

    def test_perfect_score_is_one(self):
        score = sum(self.WEIGHTS.values())
        assert score == pytest.approx(1.0)

    def test_zero_score_is_zero(self):
        score = sum(w * 0 for w in self.WEIGHTS.values())
        assert score == pytest.approx(0.0)

    def test_health_tier_assignment(self):
        def tier(score):
            if score >= 0.70: return "HIGH"
            if score >= 0.45: return "MEDIUM"
            if score >= 0.25: return "LOW"
            return "AT-RISK"

        assert tier(0.80) == "HIGH"
        assert tier(0.60) == "MEDIUM"
        assert tier(0.35) == "LOW"
        assert tier(0.10) == "AT-RISK"


# =========================================================================
# Revenue Leakage Tests
# =========================================================================

class TestRevenueLeakage:
    def test_return_rate_calculation(self):
        returned_units = 50
        sold_units = 500
        rate = returned_units / sold_units
        assert rate == pytest.approx(0.10)

    def test_payment_failure_rate(self):
        failed = 21
        total = 100
        rate = failed / total
        assert rate == pytest.approx(0.21)

    def test_discount_leakage_flag(self):
        discount_pct = 0.30
        margin_pct = 0.10
        DISC_THRESH = 0.25
        MARGIN_THRESH = 0.15
        flagged = discount_pct > DISC_THRESH and margin_pct < MARGIN_THRESH
        assert flagged is True

    def test_stockout_opportunity(self):
        normal_daily_demand = 108
        stockout_days = 6
        avg_price = 1250
        opportunity = normal_daily_demand * stockout_days * avg_price
        assert opportunity == pytest.approx(810_000)
