# RevenueOS – Data Dictionary

Every important column in every layer is documented here.
Format: Column | Description | Type | Source | Nullable | Business Meaning

---

## Bronze Layer

### bronze.orders

| Column | Description | Type | Source | Nullable | Business Meaning |
|--------|-------------|------|--------|----------|-----------------|
| run_id | Pipeline execution identifier | TEXT | Pipeline | No | Trace which run loaded this row |
| source_file | Original CSV filename | TEXT | Pipeline | No | Traceability to source |
| ingestion_timestamp | When the row was loaded | TIMESTAMPTZ | Pipeline | No | Ingestion audit |
| order_id | Raw order identifier | TEXT | Orders system | Yes | Links to all order activity |
| customer_id | Raw customer identifier | TEXT | Orders system | Yes | Links to customer master |
| product_id | Raw product identifier | TEXT | Orders system | Yes | Links to product master |
| order_date | Order date (unparsed) | TEXT | Orders system | Yes | When order was placed |
| quantity | Units ordered (unparsed) | TEXT | Orders system | Yes | Volume sold |
| unit_price | Price per unit (unparsed) | TEXT | Orders system | Yes | Revenue per unit |
| discount | Discount applied (unparsed) | TEXT | Orders system | Yes | May be % (0–100) or decimal (0–1) |
| channel | Sales channel | TEXT | Orders system | Yes | Online/Offline/Mobile etc. |
| location | Order location | TEXT | Orders system | Yes | City or warehouse |
| status | Order status | TEXT | Orders system | Yes | COMPLETED/CANCELLED/PENDING |
| _raw_row | Row number in source CSV | INTEGER | Pipeline | No | Debugging |

### bronze.quality_log

| Column | Description | Type | Source | Nullable | Business Meaning |
|--------|-------------|------|--------|----------|-----------------|
| log_id | Auto-increment PK | SERIAL | Pipeline | No | Unique log entry |
| run_id | Pipeline run identifier | TEXT | Pipeline | No | Links to pipeline run |
| logged_at | Timestamp of check | TIMESTAMPTZ | Pipeline | No | Audit trail |
| source_table | Table checked | TEXT | Pipeline | No | e.g. "orders" |
| check_type | Type of quality check | TEXT | Pipeline | No | NULL_CHECK, DUPLICATE_CHECK, etc. |
| severity | Severity level | TEXT | Pipeline | No | INFO / WARNING / ERROR / CRITICAL |
| message | Human-readable description | TEXT | Pipeline | No | What was found |
| affected_count | Number of affected records | INTEGER | Pipeline | Yes | Scale of the issue |
| sample_values | Example values triggering the check | TEXT | Pipeline | Yes | Debugging |

---

## Silver Layer

### silver.orders

| Column | Description | Type | Source | Nullable | Business Meaning |
|--------|-------------|------|--------|----------|-----------------|
| order_id | Cleaned order identifier | TEXT | bronze.orders | No | Primary grain key |
| customer_id | Cleaned customer identifier | TEXT | bronze.orders | Yes | FK to customers |
| product_id | Cleaned product identifier | TEXT | bronze.orders | Yes | FK to products |
| order_date | Parsed order date | DATE | bronze.orders | Yes | Parsed from text; NULL if unparseable |
| quantity | Units ordered | NUMERIC | bronze.orders | Yes | Non-negative after cleaning |
| unit_price | Price per unit | NUMERIC | bronze.orders | Yes | Non-negative after cleaning |
| discount_pct | Discount as decimal 0–1 | NUMERIC | bronze.orders | Yes | Normalized from source (see A3) |
| channel | Standardized channel | TEXT | bronze.orders | Yes | Title-cased |
| location | Standardized location | TEXT | bronze.orders | Yes | Title-cased |
| status | Uppercased order status | TEXT | bronze.orders | Yes | COMPLETED / CANCELLED / PENDING |
| gross_revenue | quantity × unit_price | NUMERIC | Derived | Yes | Revenue before any deduction |
| discount_amount | gross_revenue × discount_pct | NUMERIC | Derived | Yes | Value of discount applied |
| net_sales | gross_revenue − discount_amount | NUMERIC | Derived | Yes | Revenue after discount, before returns |

### silver.products

| Column | Description | Type | Source | Nullable | Business Meaning |
|--------|-------------|------|--------|----------|-----------------|
| product_id | Cleaned product ID | TEXT | bronze.products | No | Primary grain key |
| product_name | Product name | TEXT | bronze.products | Yes | |
| category | Standardized category | TEXT | bronze.products | Yes | Title-cased |
| subcategory | Standardized subcategory | TEXT | bronze.products | Yes | Title-cased |
| supplier | Standardized supplier name | TEXT | bronze.products | Yes | Title-cased |
| cost | Unit cost (COGS proxy) | NUMERIC | bronze.products | Yes | See assumption A1 |
| selling_price | List selling price | NUMERIC | bronze.products | Yes | |
| margin_pct | (selling_price − cost) / selling_price | NUMERIC | Derived | Yes | Catalogue margin before discounts |

---

## Gold Layer – Dimensions

### gold.dim_date

| Column | Description | Type | Business Meaning |
|--------|-------------|------|-----------------|
| date_key | YYYYMMDD integer PK | INTEGER | FK from all fact tables |
| full_date | Calendar date | DATE | |
| year, quarter, month | Calendar breakdowns | SMALLINT | Used for time filters |
| week, day_of_week | Week-level breakdowns | SMALLINT | |
| is_weekend | Saturday or Sunday | BOOLEAN | Weekend demand patterns |
| fiscal_year, fiscal_quarter | Fiscal calendar (same as calendar in v1) | SMALLINT | |

### gold.dim_product

| Column | Description | Type | Business Meaning |
|--------|-------------|------|-----------------|
| product_key | Surrogate PK | SERIAL | FK from fact tables |
| product_id | Natural key | TEXT | Source system ID |
| cost | Unit cost at time of dimension load | NUMERIC | Used for COGS calculation |
| selling_price | List price at dimension load | NUMERIC | |
| margin_pct | Catalogue gross margin | NUMERIC | |

---

## Gold Layer – Facts

### gold.fact_orders

**Grain**: One row = one product line in one order.

| Column | Description | Type | Formula | Business Meaning |
|--------|-------------|------|---------|-----------------|
| order_line_key | Surrogate PK | SERIAL | | |
| order_id | Source order ID | TEXT | | Links orders together |
| date_key | FK to dim_date | INTEGER | | Order date |
| customer_key | FK to dim_customer | INTEGER | | |
| product_key | FK to dim_product | INTEGER | | |
| quantity | Units sold | NUMERIC | | |
| unit_price | Price at transaction | NUMERIC | | Transaction price (may differ from list price) |
| discount_pct | Discount applied | NUMERIC | | 0–1 decimal |
| gross_revenue | Revenue before deductions | NUMERIC | qty × unit_price | |
| discount_amount | Discount value | NUMERIC | gross_revenue × discount_pct | |
| net_sales | Revenue after discount | NUMERIC | gross_revenue − discount_amount | Net sales before returns |
| cogs | Cost of goods | NUMERIC | qty × product.cost | See assumption A1 |
| gross_profit | Profit contribution | NUMERIC | net_sales − cogs | |
| gross_margin_pct | Margin ratio | NUMERIC | gross_profit / net_sales | NULL if net_sales = 0 |

### gold.fact_returns

**Grain**: One row = one returned product line.

| Column | Description | Type | Formula |
|--------|-------------|------|---------|
| return_id | Source return ID | TEXT | |
| order_id | Originating order | TEXT | |
| date_key | Return date | INTEGER | |
| quantity_returned | Units returned | NUMERIC | |
| return_value | Value of return | NUMERIC | quantity_returned × unit_price at order time (see A2) |

---

## Gold Layer – Intelligence Tables

### gold.gold_customer_health

| Column | Description | Type | Range | Business Meaning |
|--------|-------------|------|-------|-----------------|
| health_score | Composite score | NUMERIC | 0–1 | Higher = healthier customer |
| health_tier | Categorization | TEXT | HIGH/MEDIUM/LOW/AT-RISK | Analyst priority tier |
| recency_score | Days since last order score | NUMERIC | 0–1 | 1 = ordered very recently |
| frequency_score | Order count score | NUMERIC | 0–1 | 1 = highest order count in population |
| monetary_score | Revenue score | NUMERIC | 0–1 | 1 = highest revenue in population |
| profitability_score | Margin score | NUMERIC | 0–1 | 1 = highest margin in population |
| trend_score | Revenue trend score | NUMERIC | 0–1 | 1 = strongest positive trend |
| behavior_score | Return rate score | NUMERIC | 0–1 | 1 = lowest return rate |
| revenue_trend_pct | 30d vs prior 30d | NUMERIC | -∞ to +∞ | Positive = growing |

### gold.gold_product_profitability

| Column | Description | Type | Business Meaning |
|--------|-------------|------|-----------------|
| classification | Product quadrant | TEXT | Revenue Winner / Revenue Trap / Hidden Winner / Dead Stock Candidate / Low Priority |
| realised_margin_pct | Actual margin after discounts & returns | NUMERIC | May differ from catalogue margin_pct |
| stockout_days | Days with zero inventory | INTEGER | Estimate of missed selling days |

### gold.gold_investigation_queue

| Column | Description | Type | Business Meaning |
|--------|-------------|------|-----------------|
| priority | Investigation urgency | TEXT | HIGH / MEDIUM / LOW |
| priority_score | Numeric ranking score | NUMERIC | `abs(impact) × severity × confidence` |
| issue | Human-readable problem statement | TEXT | |
| estimated_impact | Estimated financial magnitude | NUMERIC | Always an estimate — see assumptions.md |
| possible_drivers | JSON list of potential causes | TEXT | For analyst context |
| recommended_investigation | Suggested next step | TEXT | Analyst guidance, not directive |
| confidence | Confidence in the signal | TEXT | HIGH / MEDIUM / LOW |
| status | Workflow status | TEXT | OPEN / INVESTIGATING / CLOSED |

---

## Calculation Cross-Reference

All metrics below must be consistent across SQL, Python, and Power BI:

| Metric | SQL source | Python source | Power BI measure |
|--------|-----------|---------------|-----------------|
| Net Revenue | `fact_orders.net_sales − fact_returns.return_value` | `build_gold.py` | `[Net Revenue]` |
| Gross Profit | `fact_orders.gross_profit` | `build_gold.py` | `[Gross Profit]` |
| Gross Margin % | `fact_orders.gross_margin_pct` | `build_gold.py` | `[Gross Margin %]` |
| ROAS | `fact_marketing.roas` | `build_gold.py` | `[ROAS]` |
| Customer Health Score | `gold_customer_health.health_score` | `build_gold.py` | `[Health Score]` |

---

*Last updated: 2026-10-04. Update this file whenever source systems or transformations change.*
