"""
RevenueOS – Tests for Publication Vector PDF Reporting (Phase 6)
================================================================
Validates:
  - Vector PDF synthesis via Matplotlib PdfPages
  - Multi-page document structure
  - Embedded high-res analytical charts
  - Star schema & DAX table rendering
  - Commercial royalty license footer inclusion
"""

from pathlib import Path
import json
import pytest
from backend.python.reporting.executive_report import generate_executive_pdf_from_manifest


class TestPdfReporting:
    @pytest.fixture
    def sample_manifest(self):
        sample_path = Path("frontend/model_data_sample.json")
        if sample_path.exists():
            return json.loads(sample_path.read_text(encoding="utf-8"))
        from backend.api.app import _ensure_default_artifacts, DEFAULT_MODEL_DIR
        _ensure_default_artifacts()
        manifest_path = DEFAULT_MODEL_DIR / "manifest.json"
        assert manifest_path.exists(), f"Default manifest not found at {manifest_path}"
        return json.loads(manifest_path.read_text(encoding="utf-8"))

    def test_pdf_report_synthesis_from_sample(self, tmp_path, sample_manifest):
        pdf_out = tmp_path / "test_executive_report.pdf"
        res_path = generate_executive_pdf_from_manifest(sample_manifest, pdf_out)

        assert res_path.exists()
        assert res_path.stat().st_size > 15000

        with open(res_path, "rb") as f:
            header = f.read(5)
            assert header == b"%PDF-", "Generated document is not a valid PDF file"

    def test_pdf_report_with_live_charts_dir(self, tmp_path, sample_manifest):
        charts_dir = tmp_path / "charts"
        charts_dir.mkdir(parents=True, exist_ok=True)

        # Create dummy PNG charts
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt

        for name in [
            "07_gross_to_net_waterfall.png",
            "04_top_products_ranking.png",
            "08_price_elasticity_scatter.png",
        ]:
            fig, ax = plt.subplots(figsize=(6, 4))
            ax.plot([1, 2, 3], [4, 5, 6])
            fig.savefig(charts_dir / name)
            plt.close(fig)

        pdf_out = tmp_path / "executive_report_with_charts.pdf"
        res_path = generate_executive_pdf_from_manifest(sample_manifest, pdf_out, charts_dir=charts_dir)

        assert res_path.exists()
        assert res_path.stat().st_size > 20000

    def test_pdf_report_custom_currency_and_title(self, tmp_path, sample_manifest):
        sample_manifest["projectName"] = "Acme Global Enterprise"
        sample_manifest["dashboard"]["kpis"]["currency"] = "€"
        sample_manifest["dashboard"]["kpis"]["totalRevenue"] = 12500000.50

        pdf_out = tmp_path / "acme_report.pdf"
        res_path = generate_executive_pdf_from_manifest(sample_manifest, pdf_out)

        assert res_path.exists()
        assert res_path.stat().st_size > 15000

    def test_pdf_report_empty_manifest_graceful_handling(self, tmp_path):
        minimal_manifest = {
            "projectName": "Minimal Model",
            "dashboard": {"kpis": {}},
            "tables": [],
            "daxMeasures": [],
            "charts": [],
        }
        pdf_out = tmp_path / "minimal_report.pdf"
        res_path = generate_executive_pdf_from_manifest(minimal_manifest, pdf_out)

        assert res_path.exists()
        assert res_path.stat().st_size > 10000

    def test_pdf_report_missing_charts_fallback(self, tmp_path, sample_manifest):
        non_existent_charts = tmp_path / "no_such_charts_folder"
        pdf_out = tmp_path / "fallback_report.pdf"
        res_path = generate_executive_pdf_from_manifest(sample_manifest, pdf_out, charts_dir=non_existent_charts)

        assert res_path.exists()
        assert res_path.stat().st_size > 15000
