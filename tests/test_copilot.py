"""
RevenueOS – Tests for Investigation Copilot
=============================================
Validates:
  - Synthesis of structured signals into executive briefings
  - Evidence preservation (zero fabrication)
  - Dossier generation across multiple priority items
"""

import json
import pandas as pd
import pytest

from python.reporting.investigation_copilot import InvestigationCopilot


class TestInvestigationCopilot:

    @pytest.fixture
    def sample_queue_item(self):
        return {
            "entity_type": "Product",
            "entity_id": "PRD-E109",
            "entity_name": "Flagship Smartphone X12",
            "issue": "Revenue Trap: Negative Gross Margin",
            "priority": "HIGH",
            "metric": "gross_margin_pct",
            "observed_value": -0.052,
            "baseline_value": 0.22,
            "estimated_impact": 650000.0,
            "possible_drivers": json.dumps([
                "Excessive voucher stacking (>25%)",
                "Spike in transit damage returns",
            ]),
            "recommended_investigation": "Audit coupon policy and inspect packaging supplier.",
            "confidence": "HIGH",
            "evidence_summary": "Net Sales: ₹1,500,000 | COGS: ₹1,578,000 | Returns: ₹120,000",
        }

    def test_synthesize_investigation(self, sample_queue_item):
        copilot = InvestigationCopilot(currency_symbol="₹")
        memo = copilot.synthesize_investigation(sample_queue_item)

        assert "REVENUEOS INVESTIGATION BRIEFING" in memo
        assert "Flagship Smartphone X12" in memo
        assert "₹650,000.00" in memo
        assert "Excessive voucher stacking" in memo
        assert "HIGH" in memo

    def test_generate_dossier(self, sample_queue_item):
        copilot = InvestigationCopilot()
        queue_df = pd.DataFrame([
            sample_queue_item,
            {
                "entity_type": "Customer",
                "entity_id": "CUST-00042",
                "entity_name": "Enterprise Client Alpha",
                "issue": "Churn Risk on High-Value Account",
                "priority": "CRITICAL",
                "metric": "days_since_last_order",
                "observed_value": 115,
                "baseline_value": 30,
                "estimated_impact": 1200000.0,
                "possible_drivers": ["Payment failures on renewal", "Account executive departure"],
                "recommended_investigation": "Direct executive outreach within 24 hours.",
                "confidence": "HIGH",
                "evidence_summary": "LTV: ₹4,500,000 | Recency: 115 days vs 30 avg",
                "priority_score": 1200000.0,
            }
        ])

        dossier = copilot.generate_dossier(queue_df, max_items=5)
        assert "# REVENUEOS DECISION INTELLIGENCE DOSSIER" in dossier
        assert "Enterprise Client Alpha" in dossier
        assert "Flagship Smartphone X12" in dossier
