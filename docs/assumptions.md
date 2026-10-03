# RevenueOS – Assumptions Register

This document records all analytical assumptions made in the project.
Every assumption here must be referenced in the corresponding code comment.

---

## Data Assumptions

| # | Assumption | Impact | Documented In |
|---|-----------|--------|--------------|
| A1 | Product `cost` field is used as a full COGS proxy. No additional cost allocation (shipping, handling) is included. | COGS may be understated | `build_gold.py` |
| A2 | Returns are valued at the **original transaction unit_price**, not the cost. | Return value may differ from actual refund processed | `build_gold.py` |
| A3 | Discount normalization: if the median discount value in the source is > 1, it is treated as a percentage (0–100) and divided by 100. | Incorrect auto-detection possible if data is mixed | `transform_silver.py` |
| A4 | Customers with duplicate `customer_id` values: the **last-seen** record is kept after deduplication. | Customer attributes may vary across records | `transform_silver.py` |
| A5 | Products with duplicate `product_id` values: the **last-seen** record is kept. | Cost/price may be inconsistent if product records differ | `transform_silver.py` |
| A6 | `signup_date` for customers that cannot be parsed is set to NULL rather than rejected. | Some customer tenure calculations will be incomplete | `transform_silver.py` |

---

## Financial Assumptions

| # | Assumption | Impact | Documented In |
|---|-----------|--------|--------------|
| F1 | Net Revenue = Net Sales − Return Value. Returns are not separated by period (the return is subtracted in the same aggregate as the order). | Period-end reconciliation may differ from accounting | `build_gold.py` |
| F2 | Gross Margin % is calculated as `gross_profit ÷ net_revenue`. Where net_revenue is 0, margin is set to NULL. | Zero-revenue products show no margin | `build_gold.py` |
| F3 | COGS is only computed where a matching `product_id` exists in the products table. Orders with unmatched products have COGS = NULL. | Some gross profit values will be NULL | `build_gold.py` |

---

## Leakage Assumptions

| # | Assumption | Impact | Documented In |
|---|-----------|--------|--------------|
| L1 | Discount leakage flag is triggered when `discount_pct > 25%` AND `gross_margin_pct < 15%`. These thresholds are configurable via `.env`. | Threshold-sensitive — different thresholds produce different signals | `config.py` |
| L2 | Payment failure value represents **potentially affected order value**, not confirmed lost revenue (customers may retry). | Overstates actual revenue impact | `build_gold.py` |
| L3 | Stockout revenue opportunity is estimated as `avg_daily_demand × stockout_days × avg_price`. This is a rough estimate. | Demand may differ from historical average; substitution effects ignored | `build_gold.py` |
| L4 | All leakage values are labeled `is_estimate = TRUE` in the database. | Prevents misinterpretation as confirmed losses | `build_gold.py` |

---

## Analytics Assumptions

| # | Assumption | Impact | Documented In |
|---|-----------|--------|--------------|
| AN1 | Customer Health Score is a **weighted prioritization model**, not a causal or predictive model. | Score should guide analyst attention, not drive automatic decisions | `build_gold.py` |
| AN2 | Anomaly detection uses IQR by default. This is sensitive to heavily skewed distributions. | Extreme outliers in revenue data may cause higher IQR boundaries | `build_gold.py` |
| AN3 | Anomalies are flagged as "requiring investigation" — **not fraud, not errors**. | Prevents misleading downstream communications | `build_gold.py` |
| AN4 | Product classification thresholds (Revenue Winner, Trap, etc.) use the **median** of the population as the boundary. | Classification is relative to the current dataset | `build_gold.py` |
| AN5 | Investigation priority score = `abs(estimated_financial_impact)`. Higher impact = higher priority. | Equal-impact items with different confidence are ranked identically | `build_gold.py` |

---

## Data Quality Assumptions

| # | Assumption | Impact | Documented In |
|---|-----------|--------|--------------|
| Q1 | Rejected records (those that fail type coercion) are logged but **not inserted** into Silver. They remain in Bronze for traceability. | Silver row counts may be lower than Bronze | `transform_silver.py` |
| Q2 | Schema drift warnings are logged but do **not** halt the pipeline unless a critical required column is missing. | Pipeline is tolerant of schema evolution | `quality/run_checks.py` |
| Q3 | Referential integrity violations are flagged as **warnings**, not errors. Orphan records are retained in Bronze. | Silver/Gold joins may produce NULLs for unmatched IDs | `quality/run_checks.py` |

---

*Last updated: 2026-10-04*
*Review this file whenever thresholds, formulas, or source systems change.*
