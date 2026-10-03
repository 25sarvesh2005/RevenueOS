"""
RevenueOS – Tests for Anomaly Detection Engine
================================================
Validates:
  - IQR fencing and outlier extraction
  - Parametric Z-score boundaries
  - Multivariate Isolation Forest execution
  - Financial impact estimation and severity categorization
"""

import numpy as np
import pandas as pd
import pytest

from python.anomaly_detection.detector import AnomalyDetector, run_anomaly_pipeline


class TestAnomalyDetection:

    @pytest.fixture
    def sample_orders_df(self):
        # 100 rows with normal distribution + 4 intentional outliers
        np.random.seed(42)
        normal_sales = np.random.normal(loc=1200, scale=150, size=96).tolist()
        outlier_sales = [15000.0, 22000.0, 18500.0, 35000.0]
        sales = normal_sales + outlier_sales

        normal_disc = [0.05] * 96
        outlier_disc = [0.45, 0.60, 0.75, 0.50]
        disc = normal_disc + outlier_disc

        return pd.DataFrame({
            "order_id": [f"ORD-{i:04d}" for i in range(100)],
            "net_sales": sales,
            "discount": disc,
            "quantity": [1] * 96 + [10, 15, 20, 25],
        })

    def test_iqr_detection(self, sample_orders_df):
        detector = AnomalyDetector(iqr_multiplier=1.5)
        anomalies = detector.detect_iqr(
            sample_orders_df, entity_col="order_id", metric_col="net_sales"
        )
        assert not anomalies.empty
        assert len(anomalies) >= 4
        # Verify columns match gold_business_anomalies schema
        expected_cols = [
            "anomaly_id", "detected_at", "entity_type", "entity_id",
            "metric", "observed_value", "baseline_value", "deviation_pct",
            "severity", "estimated_financial_impact", "detection_method", "status"
        ]
        for col in expected_cols:
            assert col in anomalies.columns

    def test_zscore_detection(self):
        detector = AnomalyDetector(z_threshold=3.0)
        df = pd.DataFrame({
            "product_id": [f"PRD-{i}" for i in range(50)],
            "margin_pct": [0.35 + np.random.normal(0, 0.02) for _ in range(48)] + [-0.25, 0.95],
        })
        anomalies = detector.detect_zscore(df, entity_col="product_id", metric_col="margin_pct")
        assert not anomalies.empty
        assert len(anomalies) >= 1
        assert "Z_SCORE" in anomalies["detection_method"].values

    def test_isolation_forest_multivariate(self, sample_orders_df):
        detector = AnomalyDetector(contamination=0.05)
        anomalies = detector.detect_isolation_forest(
            sample_orders_df,
            entity_col="order_id",
            feature_cols=["net_sales", "discount", "quantity"],
        )
        assert not anomalies.empty
        assert "ISOLATION_FOREST" in anomalies["detection_method"].values

    def test_severity_classification(self):
        detector = AnomalyDetector()
        assert detector._classify_severity(impact=60000, abs_dev_pct=0.2) == "CRITICAL"
        assert detector._classify_severity(impact=20000, abs_dev_pct=0.4) == "HIGH"
        assert detector._classify_severity(impact=8000, abs_dev_pct=0.35) == "MEDIUM"
        assert detector._classify_severity(impact=1000, abs_dev_pct=0.1) == "LOW"

    def test_pipeline_integration(self, sample_orders_df):
        findings = run_anomaly_pipeline(sample_orders_df)
        assert not findings.empty
        assert len(findings) > 0
