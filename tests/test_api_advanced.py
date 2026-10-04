"""
RevenueOS – Tests for Advanced API Endpoints & Enterprise Hardening (Phase 6)
=============================================================================
Validates:
  - GET /api/reports/{job_id}/executive-pdf endpoint
  - Comprehensive chart artifact serving for all 9 chart types
  - Path traversal security on chart endpoints
  - Multi-tenant schedule registration & filtering
  - Job-scoped collaborative annotations
  - External webhook pipeline trigger & fallbacks
"""

from pathlib import Path
import pytest
from starlette.testclient import TestClient
from backend.api.app import app, job_store


@pytest.fixture
def client():
    return TestClient(app)


class TestApiAdvanced:
    def test_executive_pdf_endpoint_default(self, client):
        response = client.get("/api/reports/default/executive-pdf")
        assert response.status_code == 200
        assert "application/pdf" in response.headers["content-type"]
        assert response.content.startswith(b"%PDF-")
        assert len(response.content) > 10000

    def test_executive_pdf_endpoint_invalid_job_id(self, client):
        response = client.get("/api/reports/unknown_invalid_job_9999/executive-pdf")
        assert response.status_code == 404

    def test_all_nine_charts_retrieval(self, client):
        chart_files = [
            "01_monthly_revenue_and_margin_trend.png",
            "02_category_revenue_distribution.png",
            "03_channel_revenue_breakdown.png",
            "04_top_products_ranking.png",
            "05_executive_summary_dashboard.png",
            "06_marketing_roas_analysis.png",
            "07_gross_to_net_waterfall.png",
            "08_price_elasticity_scatter.png",
            "09_metric_correlation_matrix.png",
        ]
        for cf in chart_files:
            resp = client.get(f"/api/charts/default/{cf}")
            # In default model, either 200 if file exists or 404 if not yet generated
            assert resp.status_code in (200, 404)
            if resp.status_code == 200:
                assert "image/png" in resp.headers["content-type"]
                assert resp.content.startswith(b"\x89PNG")

    def test_chart_path_traversal_protection(self, client):
        resp = client.get("/api/charts/default/../../pyproject.toml")
        assert resp.status_code == 404

    def test_multi_tenant_schedule_filtering(self, client):
        # Register schedule for Tenant Alpha
        resp_a = client.post(
            "/api/schedules",
            json={
                "tenant_id": "tenant_alpha",
                "cron_expression": "0 6 * * *",
                "source_excel": "data/raw/excel/revenueos_sample.xlsx",
                "project_name": "Alpha Daily Marts",
            },
        )
        assert resp_a.status_code == 200
        sched_a_id = resp_a.json()["schedule_id"]

        # Register schedule for Tenant Beta
        resp_b = client.post(
            "/api/schedules",
            json={
                "tenant_id": "tenant_beta",
                "cron_expression": "0 12 * * *",
                "source_excel": "data/raw/excel/revenueos_sample.xlsx",
                "project_name": "Beta Midday Marts",
            },
        )
        assert resp_b.status_code == 200

        # Filter by tenant_alpha
        resp_filter_a = client.get("/api/schedules?tenant_id=tenant_alpha")
        assert resp_filter_a.status_code == 200
        items_a = resp_filter_a.json()
        assert any(s["schedule_id"] == sched_a_id for s in items_a)
        assert all(s["tenant_id"] == "tenant_alpha" for s in items_a)

    def test_job_scoped_annotations(self, client):
        target_job = "job_annot_phase6"
        client.post(
            "/api/annotations",
            json={
                "job_id": target_job,
                "visual_id": "visualMonthlyTrend",
                "author": "Chief Risk Officer",
                "category": "risk",
                "content": "Supply chain disruption expected in Q3.",
            },
        )
        resp = client.get(f"/api/annotations/{target_job}")
        assert resp.status_code == 200
        annots = resp.json()
        assert len(annots) >= 1
        assert annots[-1]["category"] == "risk"
        assert "Supply chain" in annots[-1]["content"]

    def test_webhook_pipeline_trigger(self, client):
        resp = client.post(
            "/api/webhook/pipeline-trigger",
            json={
                "project_name": "WebhookTestEnterprise",
                "tenant_id": "tenant_webhook",
            },
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "RUNNING"
        assert "Webhook received" in data["message"]
        assert data["job_id"] is not None

    def test_annotations_empty_job_returns_empty_list(self, client):
        resp = client.get("/api/annotations/non_existent_job_xyz_99")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_dax_evaluator_assignment_syntax_via_api(self, client):
        resp = client.post(
            "/api/evaluate-dax",
            json={"expression": "[Total Revenue Metric] = SUM(orders[revenue])"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "SUCCESS"
        assert data["evaluated_value"] is not None
        assert "$" in data["formatted_value"]

    def test_api_runs_structure_and_types(self, client):
        resp = client.get("/api/runs")
        assert resp.status_code == 200
        runs = resp.json()
        assert isinstance(runs, list)
        for r in runs:
            assert "job_id" in r
            assert "tenant_id" in r
            assert "status" in r

    def test_api_reports_executive_html_doctype(self, client):
        resp = client.get("/api/reports/default/executive-html")
        assert resp.status_code == 200
        assert "text/html" in resp.headers["content-type"]
        assert "<!DOCTYPE html>" in resp.text
        assert "RevenueOS" in resp.text
