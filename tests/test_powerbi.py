"""
RevenueOS – Tests for Power BI Ready File (.pbit & .pbip)
=========================================================
Validates:
  - Generation of single-file template (RevenueOS.pbit)
  - Integrity of Tabular Model Schema (TMSL) and DataModelSchema
  - Auto-wiring of all 14 star schema relationships
  - Assembly of 70 DAX semantic measures in _Measures
  - Configuration of all 8 executive pages in Report/Layout
  - PBIP project structure and model.bim integrity
"""

from __future__ import annotations

import json
import zipfile
from pathlib import Path

from powerbi.build_powerbi_file import (
    build_tmsl_model,
    build_pbit,
    build_pbip,
    RELATIONSHIPS,
    MEASURES,
    PAGES,
    TABLE_SCHEMAS,
)


class TestPowerBIReadyFiles:
    """Test suite validating Power BI template and project generation."""

    def test_tmsl_model_structure(self):
        model = build_tmsl_model()
        assert model["name"] == "RevenueOS"
        inner_model = model["model"]

        # Check tables
        table_names = {t["name"] for t in inner_model["tables"]}
        for expected in TABLE_SCHEMAS.keys():
            assert expected in table_names
        assert "_Measures" in table_names

        # Check measures in _Measures table
        measures_table = next(t for t in inner_model["tables"] if t["name"] == "_Measures")
        assert len(measures_table["measures"]) == len(MEASURES)

        # Check relationships
        assert len(inner_model["relationships"]) == len(RELATIONSHIPS)
        for rel in inner_model["relationships"]:
            assert rel["crossFilteringBehavior"] == "oneDirection"
            assert rel["isActive"] is True

        # Check parameters
        expr_names = {e["name"] for e in inner_model["expressions"]}
        assert "DBServer" in expr_names
        assert "DBDatabase" in expr_names

    def test_pbit_generation(self, tmp_path: Path):
        tmsl = build_tmsl_model()
        out_pbit = tmp_path / "RevenueOS_Test.pbit"
        build_pbit(tmsl, output_path=out_pbit)

        assert out_pbit.exists()
        assert out_pbit.stat().st_size > 5000

        with zipfile.ZipFile(out_pbit, "r") as z:
            names = set(z.namelist())
            assert "DataModelSchema" in names
            assert "Report/Layout" in names
            assert "[Content_Types].xml" in names
            assert "Settings" in names
            assert "Metadata" in names
            assert "Version" in names

            # Validate DataModelSchema JSON
            schema_data = json.loads(z.read("DataModelSchema").decode("utf-16le"))
            assert schema_data["name"] == "RevenueOS"
            assert len(schema_data["model"]["tables"]) >= 18

            # Validate Report/Layout pages
            layout_data = json.loads(z.read("Report/Layout").decode("utf-16le"))
            section_titles = [s["displayName"] for s in layout_data["sections"]]
            assert len(section_titles) == 8
            assert "01 Executive Command Center" in section_titles
            assert "08 Investigation Queue" in section_titles

    def test_pbip_generation(self, tmp_path: Path):
        tmsl = build_tmsl_model()
        pbip_file = build_pbip(tmsl, target_root=tmp_path)

        assert pbip_file.exists()
        assert (tmp_path / "RevenueOS.Report" / "definition.pbir").exists()
        assert (tmp_path / "RevenueOS.Report" / "definition" / "report.json").exists()
        assert (tmp_path / "RevenueOS.SemanticModel" / "model.bim").exists()

        model_bim = json.loads((tmp_path / "RevenueOS.SemanticModel" / "model.bim").read_text(encoding="utf-8"))
        assert model_bim["name"] == "RevenueOS"
        assert len(model_bim["model"]["tables"]) >= 18
