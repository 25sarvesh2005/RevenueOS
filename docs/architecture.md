# RevenueOS – End-to-End System Architecture

## 1. High-Level Architecture Overview

RevenueOS is an end-to-end Data Analytics and Decision Intelligence platform engineered for omnichannel retail. It ingests disconnected transactional data across seven operational sources, rigorously cleanses and validates it through a Medallion Lakehouse/Warehouse architecture, models it into a Kimball star schema, and applies statistical and machine-learning intelligence to surface prioritized business investigations.

```
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                               OPERATIONAL DATA SOURCES                                 │
│  Orders CSV/API │ Customers │ Products │ Payments │ Returns │ Inventory │ Marketing   │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              BRONZE LAYER (PostgreSQL)                                 │
│  • Raw text types preserved (no silent data loss)                                      │
│  • Audit lineage: run_id, source_file, ingestion_timestamp, _raw_row                   │
│  • Tables: bronze.orders, bronze.customers, bronze.products, etc.                      │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                           DATA QUALITY & RECONCILIATION ENGINE                         │
│  • Schema & Required Column Validation                                                 │
│  • Null Rate & Cardinality Thresholds                                                  │
│  • Primary Key & Foreign Key Referential Integrity                                     │
│  • Numeric Range & Business Logic Reconciliation Checks                                │
│  • Result logged to: bronze.quality_log (CRITICAL failures halt pipeline)              │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                              SILVER LAYER (PostgreSQL)                                 │
│  • Conformed data types: ISO-8601 dates, numeric currencies, trimmed text               │
│  • Deduplication via business keys & latest timestamps                                 │
│  • Status standardizations (e.g. COMPLETED, CANCELLED, PENDING)                        │
│  • Calculated fields: discount_rate, net_sales                                         │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                            GOLD LAYER — STAR SCHEMA (Kimball)                          │
│                                                                                        │
│  DIMENSIONS:                   FACT TABLES:                                            │
│  • dim_date (Surrogate Key)    • fact_orders (Grain: 1 line item per order)            │
│  • dim_customer                • fact_payments (Grain: 1 payment attempt)              │
│  • dim_product                 • fact_returns (Grain: 1 return record)                 │
│  • dim_channel                 • fact_inventory (Grain: 1 SKU per warehouse per week)  │
│  • dim_location                • fact_marketing (Grain: 1 campaign per channel per day)│
│  • dim_supplier                                                                        │
│  • dim_campaign                                                                        │
│  • dim_payment_method                                                                  │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │
                     ┌──────────────────────┴──────────────────────┐
                     ▼                                             ▼
┌──────────────────────────────────────────┐  ┌──────────────────────────────────────────┐
│      SQL ANALYTICAL MARTS (Phase 8)      │  │  PYTHON STATISTICAL & ML ENGINE (Ph 11)  │
│  • gold_daily_financials                 │  │  • Statistical IQR outlier detection     │
│  • gold_customer_health                  │  │  • Parametric Z-score margin screening   │
│  • gold_product_profitability            │  │  • Scikit-learn Isolation Forest         │
│  • gold_revenue_leakage                  │  │  • Holt-Winters & OLS Revenue Forecast   │
│  • gold_inventory_risk                   │  │  • gold_business_anomalies               │
│  • gold_marketing_efficiency             │  │                                          │
└────────────────────┬─────────────────────┘  └────────────────────┬─────────────────────┘
                     └──────────────────────┬──────────────────────┘
                                            │
                                            ▼
┌────────────────────────────────────────────────────────────────────────────────────────┐
│                             DECISION & INVESTIGATION ENGINE                            │
│  • Aggregates anomalies, revenue traps, leakage vectors, and customer churn signals    │
│  • Priority Score = ABS(estimated_impact) × Severity Weight × Confidence Weight        │
│  • Table: gold.gold_investigation_queue                                                │
│  • Traceable evidence summary & recommended cross-functional remediation               │
└───────────────────────────────────────────┬────────────────────────────────────────────┘
                                            │
                     ┌──────────────────────┴──────────────────────┐
                     ▼                                             ▼
┌──────────────────────────────────────────┐  ┌──────────────────────────────────────────┐
│      POWER BI 8-PAGE EXECUTIVE SUITE     │  │      AI & ANALYTICAL INVESTIGATION       │
│  01. Executive Command Center            │  │                 COPILOT                  │
│  02. Revenue Intelligence                │  │  • Evidence-grounded executive summaries │
│  03. Revenue Leakage Radar               │  │  • Commercial & Operations playbooks     │
│  04. Customer Intelligence               │  │  • Root cause diagnostic briefs          │
│  05. Product & Profitability             │  │  • Zero evidence fabrication             │
│  06. Inventory & Operations              │  │                                          │
│  07. Marketing Efficiency                │  │                                          │
│  08. Investigation Queue                 │  │                                          │
└──────────────────────────────────────────┘  └──────────────────────────────────────────┘
```

---

## 2. Medallion Layer Specifications

### Bronze Layer (`bronze.*`)
- **Philosophy**: Pure append, zero loss. Data is ingested as raw text/VARCHAR strings directly from incoming CSV files or REST endpoints.
- **Audit Columns**: Every table contains:
  - `run_id`: UUID identifying the pipeline execution run.
  - `source_file`: Name of source CSV file for full provenance.
  - `ingestion_timestamp`: UTC timestamp when the record entered the database.
  - `_raw_row`: Source CSV line index to troubleshoot malformed rows.
- **Tables**: `orders`, `customers`, `products`, `payments`, `returns`, `inventory`, `marketing`, `quality_log`.

### Silver Layer (`silver.*`)
- **Philosophy**: Conformed, cleaned, type-safe truth.
- **Transformations**:
  - String stripping and whitespace normalization.
  - Type parsing: dates to `DATE`/`TIMESTAMP`, numbers to `NUMERIC(14,2)` or `INTEGER`.
  - Discount normalization: handles both percentages (e.g., `15.0`) and decimal factors (e.g., `0.15`) safely into a `0.0 – 1.0` range.
  - Deduplication: Deduplicates orders and customers on business primary keys (`order_id`, `customer_id`).
  - Derived fields: `net_sales = quantity * unit_price * (1 - discount_rate)`.

### Gold Layer (`gold.*`)
- **Philosophy**: Kimball dimensional star schema and pre-computed analytical views.
- **Dimensional Modeling**:
  - Integer surrogate keys (e.g. `customer_key`, `product_key`, `date_key = YYYYMMDD`).
  - Single-point-of-truth Conformed Dimensions shared across multiple fact tables.
- **Fact Table Granularity**:
  - `fact_orders`: 1 row per order line item.
  - `fact_payments`: 1 row per payment transaction attempt.
  - `fact_returns`: 1 row per customer return record.
  - `fact_inventory`: 1 row per product SKU per warehouse per snapshot date.
  - `fact_marketing`: 1 row per campaign per channel per calendar day.

---

## 3. Decision & Intelligence Architecture

### Revenue Leakage Radar (6 Vectors)
Revenue leakage represents commercial surplus lost between gross demand and collected profit:
1. **Discount Overrides**: Discretionary or stacked discounts exceeding policy threshold (>15%).
2. **Customer Returns**: Value refunded plus return processing costs.
3. **Payment Failures**: Revenue lost at checkout due to payment gateway timeouts, technical errors, and card declines.
4. **Order Cancellations**: Customer or merchant cancelled orders prior to fulfillment.
5. **Stockout Opportunity Cost**: Estimated lost sales when inventory is 0 on high-demand SKUs.
6. **Margin Degradation**: Products sold below target contribution margin threshold.

### Prioritization Algorithm
The Decision Engine computes an objective priority score for every signal:
$$\text{Priority Score} = |\text{Estimated Financial Impact}| \times W_{\text{severity}} \times W_{\text{confidence}}$$

Where:
- $W_{\text{severity}}$: `CRITICAL` = 2.0, `HIGH` = 1.5, `MEDIUM` = 1.0, `LOW` = 0.5.
- $W_{\text{confidence}}$: `HIGH` = 1.0, `MEDIUM` = 0.8, `LOW` = 0.5.

Items are ranked in `gold.gold_investigation_queue` to ensure analysts prioritize the top 5% of commercial emergencies that represent 80% of value at risk.

---

## 4. Operational SLAs & Idempotency

- **Idempotency**: All Silver and Gold ETL transformations support atomic execution (`TRUNCATE` + load or transaction-managed `MERGE`/`UPSERT`). Re-running a pipeline batch produces identical, repeatable warehouse states.
- **End-to-End Pipeline Latency**: Full batch processing of 50,000+ transactional rows runs in under 45 seconds on standard multi-core hardware.
- **Zero Silent Failure**: If a pipeline step encounters a data quality rule violation categorized as `CRITICAL`, the orchestrator halts immediately and logs detailed diagnostic context to `bronze.quality_log`.
