"""
RevenueOS – Anomaly Detection Engine
======================================
Implements statistical and machine learning anomaly detection routines:
  1. Interquartile Range (IQR) – Robust to non-normal distributions (discounts, order value)
  2. Z-Score – Standard normal deviation detection
  3. Isolation Forest – Unsupervised multivariate anomaly isolation via scikit-learn

All findings are scored for:
  - Deviation % vs baseline
  - Estimated financial impact (INR / currency)
  - Severity (LOW, MEDIUM, HIGH, CRITICAL)
  - Traceable evidence explanation

Produces records ready for `gold.gold_business_anomalies` and `gold.gold_investigation_queue`.
"""

from __future__ import annotations

import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import List, Dict, Any, Optional

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

sys.path.insert(0, str(Path(__file__).parent.parent.parent))
from config import (
    IQR_MULTIPLIER,
    ZSCORE_THRESHOLD,
    ISO_FOREST_CONTAMINATION,
    SCHEMA_GOLD,
    get_engine,
    logger,
)


class AnomalyDetector:
    """Multi-method anomaly detection suite for revenue, margin, discount, and order patterns."""

    def __init__(
        self,
        iqr_multiplier: float = IQR_MULTIPLIER,
        z_threshold: float = ZSCORE_THRESHOLD,
        contamination: float = ISO_FOREST_CONTAMINATION,
    ):
        self.iqr_multiplier = iqr_multiplier
        self.z_threshold = z_threshold
        self.contamination = contamination

    # ---------------------------------------------------------------------------
    # Method 1: IQR (Interquartile Range)
    # ---------------------------------------------------------------------------
    def detect_iqr(
        self,
        df: pd.DataFrame,
        entity_col: str,
        metric_col: str,
        entity_type: str = "Order",
        min_samples: int = 10,
    ) -> pd.DataFrame:
        """Detect outliers using robust IQR fences."""
        if df.empty or metric_col not in df.columns or len(df) < min_samples:
            return pd.DataFrame()

        clean_series = pd.to_numeric(df[metric_col], errors="coerce").dropna()
        if len(clean_series) < min_samples:
            return pd.DataFrame()

        q25 = clean_series.quantile(0.25)
        q75 = clean_series.quantile(0.75)
        iqr = q75 - q25
        median_val = clean_series.median()

        if iqr == 0:
            return pd.DataFrame()

        lower_bound = q25 - (self.iqr_multiplier * iqr)
        upper_bound = q75 + (self.iqr_multiplier * iqr)

        outliers = df[(df[metric_col] < lower_bound) | (df[metric_col] > upper_bound)].copy()
        if outliers.empty:
            return pd.DataFrame()

        records = []
        now_ts = datetime.now(timezone.utc).isoformat()

        for _, row in outliers.iterrows():
            obs = float(row[metric_col])
            base = float(median_val)
            dev_pct = round((obs - base) / base, 4) if base != 0 else 0.0

            # Estimate financial impact
            impact = abs(obs - base)
            if "quantity" in row:
                impact *= float(row["quantity"])

            severity = self._classify_severity(impact, abs(dev_pct))

            records.append({
                "anomaly_id": f"ANOM-IQR-{uuid.uuid4().hex[:8].upper()}",
                "detected_at": now_ts,
                "entity_type": entity_type,
                "entity_id": str(row[entity_col]),
                "metric": metric_col,
                "observed_value": obs,
                "baseline_value": base,
                "deviation_pct": dev_pct,
                "severity": severity,
                "estimated_financial_impact": round(impact, 2),
                "detection_method": "IQR_FENCE",
                "status": "OPEN",
            })

        return pd.DataFrame(records)

    # ---------------------------------------------------------------------------
    # Method 2: Z-Score
    # ---------------------------------------------------------------------------
    def detect_zscore(
        self,
        df: pd.DataFrame,
        entity_col: str,
        metric_col: str,
        entity_type: str = "Product",
        min_samples: int = 15,
    ) -> pd.DataFrame:
        """Detect outliers using parametric Z-scores."""
        if df.empty or metric_col not in df.columns or len(df) < min_samples:
            return pd.DataFrame()

        clean_series = pd.to_numeric(df[metric_col], errors="coerce").dropna()
        std_val = clean_series.std()
        mean_val = clean_series.mean()

        if std_val == 0 or np.isnan(std_val):
            return pd.DataFrame()

        z_scores = (clean_series - mean_val) / std_val
        outlier_idx = z_scores[z_scores.abs() > self.z_threshold].index

        if len(outlier_idx) == 0:
            return pd.DataFrame()

        records = []
        now_ts = datetime.now(timezone.utc).isoformat()

        for idx in outlier_idx:
            row = df.loc[idx]
            obs = float(row[metric_col])
            base = float(mean_val)
            dev_pct = round((obs - base) / base, 4) if base != 0 else 0.0
            impact = abs(obs - base)
            severity = self._classify_severity(impact, abs(dev_pct))

            records.append({
                "anomaly_id": f"ANOM-Z-{uuid.uuid4().hex[:8].upper()}",
                "detected_at": now_ts,
                "entity_type": entity_type,
                "entity_id": str(row[entity_col]),
                "metric": metric_col,
                "observed_value": obs,
                "baseline_value": base,
                "deviation_pct": dev_pct,
                "severity": severity,
                "estimated_financial_impact": round(impact, 2),
                "detection_method": "Z_SCORE",
                "status": "OPEN",
            })

        return pd.DataFrame(records)

    # ---------------------------------------------------------------------------
    # Method 3: Isolation Forest
    # ---------------------------------------------------------------------------
    def detect_isolation_forest(
        self,
        df: pd.DataFrame,
        entity_col: str,
        feature_cols: List[str],
        entity_type: str = "Customer",
        min_samples: int = 30,
    ) -> pd.DataFrame:
        """Detect multivariate anomalies using tree isolation."""
        if df.empty or len(df) < min_samples:
            return pd.DataFrame()

        features_df = df[feature_cols].apply(pd.to_numeric, errors="coerce").fillna(0)

        model = IsolationForest(
            contamination=self.contamination,
            random_state=42,
            n_estimators=100,
        )
        preds = model.fit_predict(features_df)
        scores = model.decision_function(features_df)

        anomaly_indices = np.where(preds == -1)[0]
        if len(anomaly_indices) == 0:
            return pd.DataFrame()

        records = []
        now_ts = datetime.now(timezone.utc).isoformat()
        primary_metric = feature_cols[0]
        baseline_val = float(df[primary_metric].median())

        for idx in anomaly_indices:
            row = df.iloc[idx]
            obs = float(row[primary_metric])
            dev_pct = round((obs - baseline_val) / baseline_val, 4) if baseline_val != 0 else 0.0
            impact = abs(obs - baseline_val)
            severity = self._classify_severity(impact, abs(dev_pct))

            records.append({
                "anomaly_id": f"ANOM-IF-{uuid.uuid4().hex[:8].upper()}",
                "detected_at": now_ts,
                "entity_type": entity_type,
                "entity_id": str(row[entity_col]),
                "metric": f"Multivariate ({', '.join(feature_cols)})",
                "observed_value": obs,
                "baseline_value": baseline_val,
                "deviation_pct": dev_pct,
                "severity": severity,
                "estimated_financial_impact": round(impact, 2),
                "detection_method": "ISOLATION_FOREST",
                "status": "OPEN",
            })

        return pd.DataFrame(records)

    # ---------------------------------------------------------------------------
    # Severity Matrix
    # ---------------------------------------------------------------------------
    @staticmethod
    def _classify_severity(impact: float, abs_dev_pct: float) -> str:
        if impact > 50000 or abs_dev_pct > 1.5:
            return "CRITICAL"
        if impact > 15000 or abs_dev_pct > 0.8:
            return "HIGH"
        if impact > 5000 or abs_dev_pct > 0.3:
            return "MEDIUM"
        return "LOW"


def run_anomaly_pipeline(orders_df: pd.DataFrame, products_df: Optional[pd.DataFrame] = None) -> pd.DataFrame:
    """Run full statistical and ML anomaly suite across order, discount, and margin metrics."""
    detector = AnomalyDetector()
    all_findings = []

    logger.info("▶ Running Anomaly Engine (IQR, Z-Score, Isolation Forest)...")

    # 1. Order Net Sales IQR Outliers
    if "net_sales" in orders_df.columns:
        anom_sales = detector.detect_iqr(
            orders_df, entity_col="order_id", metric_col="net_sales", entity_type="Order"
        )
        if not anom_sales.empty:
            all_findings.append(anom_sales)
            logger.info("  ✓ Found %d order value outliers via IQR", len(anom_sales))

    # 2. Discount Rate IQR Outliers
    if "discount" in orders_df.columns:
        anom_disc = detector.detect_iqr(
            orders_df, entity_col="order_id", metric_col="discount", entity_type="Order"
        )
        if not anom_disc.empty:
            all_findings.append(anom_disc)
            logger.info("  ✓ Found %d discount outliers via IQR", len(anom_disc))

    # 3. Product Margin Z-Score Outliers
    if products_df is not None and not products_df.empty and "margin_pct" in products_df.columns:
        anom_prod = detector.detect_zscore(
            products_df, entity_col="product_id", metric_col="margin_pct", entity_type="Product"
        )
        if not anom_prod.empty:
            all_findings.append(anom_prod)
            logger.info("  ✓ Found %d product margin anomalies via Z-Score", len(anom_prod))

    # 4. Multivariate Order Pattern via Isolation Forest
    candidate_features = [c for c in ["net_sales", "discount", "quantity"] if c in orders_df.columns]
    if len(candidate_features) >= 2 and len(orders_df) >= 30:
        anom_if = detector.detect_isolation_forest(
            orders_df, entity_col="order_id", feature_cols=candidate_features, entity_type="Order"
        )
        if not anom_if.empty:
            all_findings.append(anom_if)
            logger.info("  ✓ Found %d multivariate anomalies via Isolation Forest", len(anom_if))

    if not all_findings:
        logger.info("  No anomalies detected across specified metrics.")
        return pd.DataFrame()

    combined = pd.concat(all_findings, ignore_index=True)
    logger.info("✓ Total anomalies isolated: %d", len(combined))
    return combined


if __name__ == "__main__":
    # Test harness
    print("Testing Anomaly Detector standalone...")
    dummy_orders = pd.DataFrame({
        "order_id": [f"ORD-{i}" for i in range(100)],
        "net_sales": [1000 + np.random.normal(0, 100) for _ in range(95)] + [15000, 18000, 12, 19000, 22000],
        "discount": [0.05] * 90 + [0.55, 0.60, 0.70, 0.80, 0.45] + [0.0] * 5,
        "quantity": [1] * 95 + [20, 25, 30, 40, 50],
    })
    res = run_anomaly_pipeline(dummy_orders)
    print(res.head(10).to_string())
