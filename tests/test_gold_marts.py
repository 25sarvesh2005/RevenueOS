"""
RevenueOS – Tests for Gold Mart Logic (Inventory Risk & Marketing Efficiency)
=============================================================================
Validates:
  - Days of Inventory (DOI) calculation
  - Sell-through rate formula
  - Estimated stockout opportunity loss formula
  - Dead stock detection
  - Risk tier classification
  - ROAS, CAC, CTR, conversion rate, and contribution after marketing
"""

import numpy as np
import pandas as pd
import pytest


class TestInventoryRiskLogic:
    """Validates inventory risk metrics without database dependencies."""

    def test_days_of_inventory(self):
        units_avail = 100
        avg_daily_demand = 5.0
        doi = units_avail / avg_daily_demand
        assert doi == 20.0

    def test_inventory_turnover(self):
        avg_daily_demand = 10.0
        units_avail = 200
        turnover = (avg_daily_demand * 365) / units_avail
        assert turnover == pytest.approx(18.25)

    def test_sell_through_rate(self):
        units_sold = 80
        units_available = 20
        total = units_sold + units_available
        sell_through = units_sold / total
        assert sell_through == 0.80

    def test_stockout_financial_impact(self):
        stockout_days = 12
        avg_daily_demand = 4.5
        unit_price = 1500.0
        # Estimated stockout opportunity loss
        impact = stockout_days * avg_daily_demand * unit_price
        assert impact == pytest.approx(81000.0)

    def test_dead_stock_flag(self):
        units_available = 50
        units_sold = 0
        is_dead_stock = (units_available > 0) and (units_sold == 0)
        assert is_dead_stock is True

        units_sold_active = 5
        is_dead_stock_active = (units_available > 0) and (units_sold_active == 0)
        assert is_dead_stock_active is False

    def test_risk_tiering(self):
        def _get_tier(units_avail, doi, is_dead):
            if units_avail == 0:
                return "HIGH - Stockout"
            if doi < 7:
                return "HIGH - Low Stock"
            if is_dead:
                return "MEDIUM - Dead Stock"
            if doi <= 30:
                return "MEDIUM - Watch"
            return "LOW"

        assert _get_tier(0, 0, False) == "HIGH - Stockout"
        assert _get_tier(10, 4.0, False) == "HIGH - Low Stock"
        assert _get_tier(50, 45.0, True) == "MEDIUM - Dead Stock"
        assert _get_tier(50, 20.0, False) == "MEDIUM - Watch"
        assert _get_tier(500, 90.0, False) == "LOW"


class TestMarketingEfficiencyLogic:
    """Validates marketing efficiency formulas."""

    def test_roas_and_cac(self):
        spend = 15000.0
        revenue_attributed = 60000.0
        orders_attributed = 150

        roas = revenue_attributed / spend
        cac = spend / orders_attributed

        assert roas == 4.0
        assert cac == 100.0

    def test_ctr_and_conversion_rate(self):
        impressions = 100000
        clicks = 2500
        conversions = 125

        ctr = clicks / impressions
        conv_rate = conversions / clicks

        assert ctr == pytest.approx(0.025)
        assert conv_rate == pytest.approx(0.05)

    def test_contribution_after_marketing(self):
        gross_profit = 35000.0
        spend = 12000.0
        cam = gross_profit - spend
        assert cam == 23000.0

    def test_marketing_efficiency_tiers(self):
        def _tier(roas):
            if roas >= 4.0:
                return "Strong"
            if roas >= 2.5:
                return "Average"
            if roas >= 1.0:
                return "Weak"
            return "Loss-Making"

        assert _tier(4.5) == "Strong"
        assert _tier(3.2) == "Average"
        assert _tier(1.8) == "Weak"
        assert _tier(0.6) == "Loss-Making"
