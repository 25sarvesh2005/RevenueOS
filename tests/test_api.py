"""
Unit and Integration Tests for RevenueOS REST API Layer (backend/api/app.py).
Tests authentication, health diagnostics, manifest retrieval, DAX evaluation,
and pipeline job execution using FastAPI TestClient.
"""

import os
from pathlib import Path
import pytest
from fastapi.testclient import TestClient

from backend.api.app import app, job_store


@pytest.fixture
def client():
    return TestClient(app)


class TestApiHealthAndDiagnostics:
    def test_health_check_endpoint(self, client):
        resp = client.get("/api/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "HEALTHY"
        assert data["version"] == "1.0.0"
        assert "pandas" in data["dependencies"]
        assert "python" in data["dependencies"]
        assert "workspace_root" in data


class TestApiArtifacts:
    def test_default_manifest_retrieval(self, client):
        resp = client.get("/api/manifest/default")
        assert resp.status_code == 200
        manifest = resp.json()
        assert manifest["status"] == "SUCCESS"
        assert manifest["summary"]["tablesCount"] > 0
        assert manifest["summary"]["hasDateDimension"] is True

    def test_default_chart_image_serving(self, client):
        resp = client.get("/api/charts/default/01_monthly_revenue_and_margin_trend.png")
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "image/png"
        assert len(resp.content) > 1000

    def test_chart_not_found(self, client):
        resp = client.get("/api/charts/default/non_existent_chart.png")
        assert resp.status_code == 404

    def test_download_pbit_template(self, client):
        resp = client.get("/api/download/default/pbit")
        assert resp.status_code == 200
        assert "octet-stream" in resp.headers["content-type"]
        assert resp.headers["content-disposition"].endswith('.pbit"') or ".pbit" in resp.headers["content-disposition"]
        assert len(resp.content) > 1000

    def test_download_csv_mart_table(self, client):
        resp = client.get("/api/download/default/csv/orders.csv")
        assert resp.status_code == 200
        assert "text/csv" in resp.headers["content-type"]
        assert b"order_id" in resp.content


class TestApiDaxEvaluation:
    def test_dax_sum_evaluation(self, client):
        payload = {"expression": "SUM(orders[revenue])"}
        resp = client.post("/api/evaluate-dax", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "SUCCESS"
        assert data["evaluated_value"] > 0
        assert "$" in data["formatted_value"]

    def test_dax_countrows_evaluation(self, client):
        payload = {"expression": "COUNTROWS(orders)"}
        resp = client.post("/api/evaluate-dax", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "SUCCESS"
        assert data["evaluated_value"] == 500

    def test_dax_divide_safe_evaluation(self, client):
        payload = {"expression": "DIVIDE(SUM(orders[revenue]), COUNTROWS(orders), 0)"}
        resp = client.post("/api/evaluate-dax", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "SUCCESS"
        assert data["evaluated_value"] > 0

    def test_dax_invalid_syntax_graceful_error(self, client):
        payload = {"expression": "INVALID_FUNCTION(unknown)"}
        resp = client.post("/api/evaluate-dax", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ERROR"
        assert data["error"] is not None


class TestApiAuthentication:
    def test_auth_enforced_when_env_key_is_set(self, client, monkeypatch):
        test_key = "secret_revenueos_token_xyz"
        monkeypatch.setenv("REVENUEOS_API_KEY", test_key)

        # 1. Unauthenticated request rejected
        resp = client.get("/api/manifest/default")
        assert resp.status_code == 403
        assert "Invalid or missing API key" in resp.json()["detail"]

        # 2. Invalid key rejected
        resp = client.get("/api/manifest/default", headers={"X-RevenueOS-API-Key": "wrong_key"})
        assert resp.status_code == 403

        # 3. Valid header accepted
        resp = client.get("/api/manifest/default", headers={"X-RevenueOS-API-Key": test_key})
        assert resp.status_code == 200

        # 4. Valid query param accepted
        resp = client.get(f"/api/manifest/default?api_key={test_key}")
        assert resp.status_code == 200


class TestApiPipelineJobExecution:
    def test_submit_pipeline_run_with_server_file(self, client):
        sample_path = "data/raw/excel/revenueos_sample.xlsx"
        resp = client.post(
            "/api/pipeline/run",
            data={
                "file_path": sample_path,
                "project_name": "API Automated Test",
                "currency_symbol": "$",
                "generate_visuals": "false",
            },
        )
        assert resp.status_code == 202
        data = resp.json()
        assert "job_id" in data
        job_id = data["job_id"]

        # Check job status
        status_resp = client.get(f"/api/pipeline/status/{job_id}")
        assert status_resp.status_code == 200
        status_data = status_resp.json()
        assert status_data["job_id"] == job_id
        assert status_data["status"] in ("PENDING", "RUNNING", "COMPLETED")


class TestApiPhase4Features:
    def test_executive_html_and_markdown_reports(self, client):
        # 1. HTML Briefing
        html_resp = client.get("/api/reports/default/executive-html")
        assert html_resp.status_code == 200
        assert "text/html" in html_resp.headers["content-type"]
        assert "Executive Briefing" in html_resp.text
        assert "Gross Revenue" in html_resp.text
        assert "Commercial Royalty License" in html_resp.text

        # 2. Markdown Briefing
        md_resp = client.get("/api/reports/default/executive-markdown")
        assert md_resp.status_code == 200
        assert "text/plain" in md_resp.headers["content-type"]
        assert "Executive Intelligence Briefing" in md_resp.text
        assert "Kimball Star Schema Dimensional Marts" in md_resp.text

    def test_copilot_investigation_briefing(self, client):
        payload = {
            "entity_type": "Product",
            "entity_name": "Premium Industrial Valve V2",
            "issue": "Severe Margin Compression",
            "metric": "gross_margin_pct",
            "observed_value": 0.082,
            "baseline_value": 0.285,
            "estimated_impact": 142000.0,
            "priority": "CRITICAL",
            "drivers": ["Voucher stacking (>20%)", "Packaging material price spike"],
            "evidence": "Net Revenue: $480,000 | COGS: $440,640",
        }
        resp = client.post("/api/copilot/investigate", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert "briefing" in data
        assert "REVENUEOS INVESTIGATION BRIEFING" in data["briefing"]
        assert "Premium Industrial Valve V2" in data["briefing"]
        assert data["priority"] == "CRITICAL"
        assert data["estimated_impact"] == 142000.0
        assert len(data["root_causes"]) >= 2
        assert len(data["action_plan"]) >= 1

    def test_multi_tenant_run_tracking(self, client):
        # Create a run with a specific tenant
        j1 = job_store.create_job(project_name="Acme Corp Analytics", tenant_id="tenant_acme")
        j2 = job_store.create_job(project_name="Beta Retail Marts", tenant_id="tenant_beta")

        # Query all runs
        all_resp = client.get("/api/runs")
        assert all_resp.status_code == 200
        all_runs = all_resp.json()
        assert len(all_runs) >= 2

        # Query specific tenant
        acme_resp = client.get("/api/tenants/tenant_acme/runs")
        assert acme_resp.status_code == 200
        acme_runs = acme_resp.json()
        assert all(r["tenant_id"] == "tenant_acme" for r in acme_runs)
        assert any(r["job_id"] == j1 for r in acme_runs)

    def test_collaborative_annotations(self, client):
        payload = {
            "job_id": "job_test_123",
            "visual_id": "visualMonthlyTrend",
            "author": "Chief Revenue Officer",
            "content": "Gross margin dipped in Q3 due to expedited supplier freight costs.",
            "category": "risk",
        }
        create_resp = client.post("/api/annotations", json=payload)
        assert create_resp.status_code == 200
        created = create_resp.json()
        assert "id" in created
        assert created["job_id"] == "job_test_123"
        assert created["author"] == "Chief Revenue Officer"

        # Retrieve annotations for job
        get_resp = client.get("/api/annotations/job_test_123")
        assert get_resp.status_code == 200
        items = get_resp.json()
        assert len(items) >= 1
        assert items[0]["content"] == payload["content"]

    def test_pipeline_schedules(self, client):
        payload = {
            "cron_expression": "0 6 * * 1-5",
            "source_excel": "data/raw/excel/revenueos_sample.xlsx",
            "project_name": "Daily Enterprise Mart Compilation",
            "tenant_id": "tenant_enterprise",
        }
        create_resp = client.post("/api/schedules", json=payload)
        assert create_resp.status_code == 200
        created = create_resp.json()
        assert "schedule_id" in created
        assert created["cron_expression"] == "0 6 * * 1-5"
        assert created["tenant_id"] == "tenant_enterprise"

        # List schedules
        list_resp = client.get("/api/schedules")
        assert list_resp.status_code == 200
        scheds = list_resp.json()
        assert any(s["schedule_id"] == created["schedule_id"] for s in scheds)

    def test_webhook_pipeline_trigger(self, client):
        payload = {
            "source_excel": "data/raw/excel/revenueos_sample.xlsx",
            "project_name": "Webhook Triggered Run",
            "tenant_id": "tenant_webhook",
            "currency": "$",
        }
        resp = client.post("/api/webhook/pipeline-trigger", json=payload)
        assert resp.status_code == 200
        data = resp.json()
        assert "job_id" in data
        assert data["status"] in ("PENDING", "RUNNING")
        assert "Webhook received" in data["message"]

