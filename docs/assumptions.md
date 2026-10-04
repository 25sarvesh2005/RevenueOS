# RevenueOS — Modeling & Analytical Assumptions
**Baseline Financial, Structural, and Algorithmic Assumptions**  
*Document Version: 1.0.0 · Author: Sarvesh Sharma · License: RevenueOS Commercial Royalty License*

---

## 1. Accounting & Revenue Recognition Assumptions

1. **Accrual Basis at Invoiced Execution**:
   - Gross Revenue is recognized at the moment of order invoice placement (`order_date`), regardless of payment settlement latency.
2. **Discount Rate Normalization**:
   - Discounts specified as whole numbers $> 1.0$ (e.g. $20$ representing $20\%$) are normalized to decimals ($0.20$).
   - Discounts are strictly clamped to the interval $[0.0, 1.0]$. Negative discounts are treated as zero.
3. **Negative Quantity Handling**:
   - Line items with $\text{Quantity} < 0$ are classified as return transactions or credit adjustments and segregated from forward sales volume.
4. **COGS Consistency**:
   - Direct unit procurement cost is assumed constant across order line items unless explicitly differentiated in transaction tables.
   - If `unit_cost` is missing from the transaction row, it is imputed from the standard cost in `dim_products`.

---

## 2. Schema Inference & Topology Assumptions

1. **Transaction Fact Identification**:
   - The primary transactional fact table is identified by inspecting sheets or tables containing at least one order identifier column and date column.
2. **Referential Integrity**:
   - All foreign keys in the fact table (`customer_id`, `product_id`, `date`) are expected to reference unique dimension keys. Missing dimension keys generate synthetic placeholder records (`CUST-UNKNOWN`, `SKU-UNKNOWN`) to preserve referential integrity without dropping fact transactions.
3. **Calendar Date Dimension Generation**:
   - The master calendar `dim_date` is dynamically constructed spanning from the minimum order date to the maximum order date $+ 90\text{ days}$ buffer to support forward forecasting and run-rate projections.

---

## 3. Anomaly & Outlier Detection Assumptions

1. **Interquartile Range (IQR)**:
   - Outliers are identified beyond $1.5 \times \text{IQR}$ bounds ($\text{Q1} - 1.5 \times \text{IQR}$ and $\text{Q3} + 1.5 \times \text{IQR}$).
2. **Z-Score Normalization**:
   - Values with $|z| \ge 3.0$ standard deviations from the rolling mean are flagged as statistical anomalies.
3. **Multivariate Isolation Forest**:
   - Default contamination factor is set to $0.05$ ($5\%$ expected anomalous rate in enterprise commercial transactions).

---

## 4. Benchmark Assumptions

* **Default Target Gross Margin**: $30.0\%$
* **Normal Operating Gross Margin Benchmark**: $25.0\%$
* **Normal Return Rate Benchmark**: $< 3.0\%$
* **Normal Payment Failure Benchmark**: $< 1.5\%$

---

## 5. Commercial Royalty License Notice

All analytical models, heuristic thresholds, and decision logic documented herein are governed by the **RevenueOS Commercial Royalty License**.
