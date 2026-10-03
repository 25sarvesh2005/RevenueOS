# RevenueOS – Metric Definitions

All metrics defined here must remain consistent across SQL, Python, and Power BI.

---

## Revenue Metrics

| Metric | Definition | Formula | Layer |
|--------|-----------|---------|-------|
| Gross Revenue | Revenue before any deductions | `quantity × unit_price` | Silver, Gold |
| Discount Amount | Value of discount applied | `gross_revenue × discount_pct` | Silver, Gold |
| Net Sales | Revenue after discount, before returns | `gross_revenue − discount_amount` | Silver, Gold |
| Return Value | Value of returned goods | `quantity_returned × unit_price` | Gold |
| Net Revenue | Actual revenue after discounts and returns | `net_sales − return_value` | Gold |

---

## Profitability Metrics

| Metric | Definition | Formula | Layer |
|--------|-----------|---------|-------|
| COGS | Cost of goods sold | `quantity × product.cost` | Gold |
| Gross Profit | Profit after COGS | `net_revenue − COGS` | Gold |
| Gross Margin % | Profitability ratio | `gross_profit ÷ net_revenue` | Gold |

---

## Customer Metrics

| Metric | Definition | Formula |
|--------|-----------|---------|
| Return Rate | Proportion of units returned | `returned_units ÷ sold_units` |
| Discount Dependency | Share of revenue from discounted orders | `discount_amount ÷ total_revenue` |
| Payment Fail Rate | Payment failure proportion | `failed_payments ÷ total_payments` |
| Revenue Trend % | 30-day revenue change | `(last_30d − prev_30d) ÷ prev_30d` |
| Customer Health Score | Composite prioritization score | See below |

### Customer Health Score Weights

| Component | Weight |
|-----------|--------|
| Recency Score | 20% |
| Frequency Score | 15% |
| Monetary Score | 25% |
| Profitability Score | 20% |
| Trend Score | 10% |
| Behavior Score | 10% |
| **Total** | **100%** |

### Health Tier Thresholds

| Tier | Score Range |
|------|------------|
| HIGH | ≥ 0.70 |
| MEDIUM | 0.45 – 0.69 |
| LOW | 0.25 – 0.44 |
| AT-RISK | < 0.25 |

---

## Marketing Metrics

| Metric | Definition | Formula |
|--------|-----------|---------|
| CTR | Click-through rate | `clicks ÷ impressions` |
| Conversion Rate | Order rate from clicks | `orders_attributed ÷ clicks` |
| CAC | Customer acquisition cost | `spend ÷ orders_attributed` |
| ROAS | Return on ad spend | `revenue_attributed ÷ spend` |
| Contribution After Marketing | Profit after marketing cost | `gross_profit − spend` |

---

## Inventory Metrics

| Metric | Definition | Formula |
|--------|-----------|---------|
| Inventory Value | Value of stock on hand | `units_available × product.cost` |
| Days of Inventory | Estimated stock coverage | `units_available ÷ daily_avg_demand` |
| Stockout Days | Days with zero inventory | Count of snapshots where units_available = 0 |
| Sell-through Rate | Proportion of stock sold | `units_sold ÷ (units_available + units_sold)` |

---

## Revenue Leakage Mechanisms

| Mechanism | Description | Metric | Language |
|-----------|------------|--------|---------|
| Returns | Products returned by customers | Return Value | Estimated impact |
| Discounts | High discounts with low margin | Discount Amount | Estimated margin impact |
| Payment Failure | Orders with failed payment | Failed Amount | Potentially affected order value |
| Low Margin | Orders below margin threshold | Gross Profit | Below-threshold contribution |
| Stockout | Lost demand due to zero stock | Demand × Price | Estimated sales opportunity |

> **Note**: All leakage values are estimates or potential impacts — not confirmed losses.

---

## Anomaly Detection Methods

| Method | Used For | Threshold |
|--------|---------|-----------|
| IQR | Order value, quantity, discount | 1.5× IQR (configurable) |
| Z-Score | Normally distributed metrics | ±3σ (configurable) |
| Isolation Forest | Multi-dimensional patterns | 5% contamination (configurable) |

> Anomalies are investigation candidates, not confirmed fraud or errors.
