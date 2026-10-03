# RevenueOS – Power BI Dashboard Specification (8 Pages)

This document provides the complete structural and visual blueprint for building the 8-page **RevenueOS Power BI report** in Power BI Desktop.

---

## Star Schema Relationship Model

Before assembling visuals, ensure the following star schema relationships are active (Single Cross-Filter Direction, 1-to-Many `1:*`):

```
       ┌───────────────┐
       │   dim_date    │
       └───────┬───────┘
               │ 1:date_key
               ├───────────────────────┬──────────────────────┬──────────────────────┐
               │ *:order_date_key      │ *:payment_date_key   │ *:return_date_key    │ *:snapshot_date_key
       ┌───────▼───────┐       ┌───────▼───────┐      ┌───────▼───────┐      ┌───────▼───────┐
       │  fact_orders  │       │ fact_payments │      │ fact_returns  │      │fact_inventory │
       └───────┬───────┘       └───────────────┘      └───────┬───────┘      └───────┬───────┘
               │ *:customer_key                               │ *:product_key        │ *:product_key
       ┌───────▼───────┐                                      │                      │
       │ dim_customer  │                              ┌───────▼──────────────────────▼───────┐
       └───────────────┘                              │             dim_product              │
               │ *:product_key                        └──────────────────────────────────────┘
       ┌───────▼───────┐
       │  dim_channel  │ (1:channel_key to fact_orders)
       └───────────────┘
       ┌───────────────┐
       │ dim_location  │ (1:location_key to fact_orders)
       └───────────────┘
```

---

## Global Design Standards
- **Canvas Size**: 16:9 (1920 × 1080 px or 1280 × 720 px)
- **Theme**: Import `revenueos_theme.json`
- **Global Header**: Logo / Title ("RevenueOS"), Run/Refresh Timestamp, Global Date Slicer (`dim_date[full_date]`), Region Slicer (`dim_location[region]`), Channel Slicer (`dim_channel[channel_name]`).

---

## Page 01 — Executive Command Center

### Purpose
Executive cockpit answering: *"Are we making money, losing money, and where is the leak?"*

### Layout & Visuals
1. **Top KPI Ribbon (Cards)**:
   - Card 1: `[Gross Revenue]` (Subtitle: YoY % variance via `[Net Sales YoY %]`)
   - Card 2: `[Net Sales]` (Subtitle: vs Target / PY)
   - Card 3: `[Gross Profit]` (Subtitle: Margin via `[Gross Margin %]`)
   - Card 4: `[Total Revenue Leakage]` (Accent: Rose `#F43F5E`, Subtitle: `% of Gross` via `[Leakage % of Gross Revenue]`)
   - Card 5: `[Total Open Investigations]` (Accent: Amber `#F59E0B`, Subtitle: `[Critical Priority Count]` Critical)
2. **Visual 1: Gross-to-Net Revenue Waterfall**:
   - Visual Type: Waterfall Chart
   - Category: Breakdown Categories (`Gross Revenue` → `Discounts` → `Returns` → `COGS` → `Gross Profit`)
   - Values: Measures corresponding to steps
3. **Visual 2: 30-Day Revenue & Margin Trajectory**:
   - Visual Type: Line & Clustered Column Chart
   - X-Axis: `dim_date[full_date]`
   - Column Values: `[Net Sales]`
   - Line Values: `[Gross Margin %]` (Secondary Y-Axis)
4. **Visual 3: Leakage Breakdown Bar Chart**:
   - Visual Type: Clustered Bar Chart
   - Y-Axis: Leakage Category (`Discount Overrides`, `Returns`, `Payment Failures`, `Cancellations`, `Stockout Loss`)
   - X-Axis: Amount
5. **Visual 4: Urgent Action Callouts (Table)**:
   - Visual Type: Table
   - Columns: `gold_investigation_queue[priority]`, `[entity_name]`, `[issue]`, `[estimated_impact]`
   - Filter: `status = "OPEN"` and `priority IN ("CRITICAL", "HIGH")`

---

## Page 02 — Revenue Intelligence

### Purpose
Deep dive into volume, price, mix, channels, and geography.

### Layout & Visuals
1. **KPI Cards**:
   - `[Average Order Value]`, `[Average Selling Price]`, `[Units Sold]`, `[Discount Rate %]`
2. **Visual 1: Channel Performance Matrix**:
   - Visual Type: Matrix
   - Rows: `dim_channel[channel_name]`
   - Values: `[Gross Revenue]`, `[Total Discounts]`, `[Net Sales]`, `[Gross Profit]`, `[Gross Margin %]`, `[Order Count]`
3. **Visual 2: Regional Revenue & Margin Map / Bar**:
   - Visual Type: Filled Map or Horizontal Bar Chart
   - Category: `dim_location[region]`
   - Values: `[Net Sales]`, Tooltip: `[Gross Margin %]`, `[Return Rate %]`
4. **Visual 3: Product Category Growth (MoM / YoY)**:
   - Visual Type: Clustered Column Chart
   - X-Axis: `dim_product[category]`
   - Values: `[Net Sales]`, `[Net Sales PY]`
5. **Visual 4: Price vs Volume Elasticity Scatter**:
   - Visual Type: Scatter Chart
   - X-Axis: `[Average Selling Price]`
   - Y-Axis: `[Units Sold]`
   - Details: `dim_product[product_name]`
   - Size: `[Net Sales]`

---

## Page 03 — Revenue Leakage Radar

### Purpose
Quantify, isolate, and trace the 6 commercial leakage vectors down to the transaction.

### Layout & Visuals
1. **KPI Cards**:
   - `[Total Revenue Leakage]`, `[Discount Leakage Amount]`, `[Return Leakage Amount]`, `[Payment Failure Amount]`, `[Cancellation Leakage Amount]`
2. **Visual 1: Leakage Composition Tree Map**:
   - Category: Leakage Type
   - Values: Loss Amount
3. **Visual 2: Payment Gateway Failure Heatmap**:
   - Visual Type: Matrix
   - Rows: `fact_payments[payment_method]`
   - Columns: `fact_payments[failure_reason]`
   - Values: `[Payment Failure Amount]`, `[Payment Failure Rate %]` (Conditional color formatting: red highlight on high timeout/decline)
4. **Visual 3: Discount Abuse Outlier Scatter**:
   - Visual Type: Scatter Chart
   - X-Axis: `fact_orders[discount_rate]`
   - Y-Axis: `fact_orders[gross_revenue]`
   - Details: `fact_orders[order_id]`
   - Play/Color Axis: `dim_channel[channel_name]`
5. **Visual 4: Return Reasons Breakdown**:
   - Visual Type: Donut Chart
   - Legend: `fact_returns[return_reason]`
   - Values: `[Total Returns]`

---

## Page 04 — Customer Intelligence

### Purpose
Monitor customer lifetime value, health scoring, cohort retention, and churn risk.

### Layout & Visuals
1. **KPI Cards**:
   - `[Total Customers]`, `[Active Customers 90D]`, `[Avg Customer Health Score]`, `[At Risk Revenue Exposure]`
2. **Visual 1: Customer Health Score Distribution**:
   - Visual Type: Histogram / Column Chart
   - X-Axis: Health Score Bins (0-20, 21-40, 41-60, 61-80, 81-100)
   - Values: Customer Count
   - Legend: `gold_customer_health[health_status]` (Healthy: Green, At Risk: Amber, Churned: Rose)
3. **Visual 2: Customer Spend vs Health Matrix**:
   - Visual Type: Scatter Chart
   - X-Axis: `total_spend`
   - Y-Axis: `health_score`
   - Details: `customer_name`
   - Size: `order_count`
4. **Visual 3: High-Value At-Risk Customers (Investigation Table)**:
   - Visual Type: Table
   - Columns: `customer_id`, `name`, `segment`, `city`, `total_spend`, `health_score`, `days_since_last_order`, `return_rate`
   - Filter: `health_status = 'At Risk'` sorted by `total_spend` DESC

---

## Page 05 — Product & Profitability

### Purpose
Classify product catalog into commercial quadrants and identify **Revenue Traps**.

### Layout & Visuals
1. **KPI Cards**:
   - `[Profit Driver SKU Count]`, `[Revenue Trap SKU Count]`, `[Revenue Trap Revenue]`, `[Profit Driver Gross Profit]`
2. **Visual 1: Product Quadrant BCG Matrix (Scatter)**:
   - Visual Type: Scatter Chart
   - X-Axis: `[Net Sales]` (Log or Linear scale)
   - Y-Axis: `[Gross Margin %]`
   - Details: `dim_product[product_name]`
   - Color / Legend: `gold_product_profitability[classification]`
   - Reference Lines: Median Revenue (Vertical), 20% Gross Margin (Horizontal)
3. **Visual 2: Top Revenue Traps (Table)**:
   - Columns: `product_name`, `category`, `revenue`, `cogs`, `gross_profit`, `gross_margin_pct`, `return_rate_pct`
   - Conditional formatting: Negative/low gross profit colored Red.
4. **Visual 3: Category Profitability Waterfall**:
   - Category: `dim_product[category]`
   - Values: `[Gross Profit]`

---

## Page 06 — Inventory & Operations

### Purpose
Link inventory availability to financial performance; isolate stockouts and holding costs.

### Layout & Visuals
1. **KPI Cards**:
   - `[Inventory Holding Value]`, `[Stockout Warehouse SKU Count]`, `[Estimated Stockout Revenue Loss]`, `[Days of Inventory (DOI)]`
2. **Visual 1: Warehouse Stockout Timeline**:
   - Visual Type: Clustered Column Chart
   - X-Axis: `snapshot_date`
   - Values: `[Stockout Warehouse SKU Count]`
   - Legend: `warehouse`
3. **Visual 2: High Stockout Revenue Risk SKUs (Table)**:
   - Columns: `product_name`, `warehouse`, `days_stocked_out`, `avg_daily_demand`, `estimated_lost_revenue`
4. **Visual 3: Inventory Turnover vs Margin by Category**:
   - Scatter or Bubble Chart comparing inventory speed to profitability.

---

## Page 07 — Marketing Efficiency

### Purpose
Evaluate campaign spend, attribution, ROAS, and CAC against actual net margin.

### Layout & Visuals
1. **KPI Cards**:
   - `[Total Ad Spend]`, `[ROAS (Return on Ad Spend)]`, `[Blended Customer Acquisition Cost (CAC)]`, `[Net Contribution After Marketing]`
2. **Visual 1: Channel ROAS vs Spend**:
   - Visual Type: Line and Clustered Column Chart
   - X-Axis: `fact_marketing[channel]`
   - Column: `[Total Ad Spend]`
   - Line: `[ROAS]` (Target Benchmark Reference Line at 3.0x)
3. **Visual 2: Daily Spend vs Attributed Revenue**:
   - Visual Type: Area Chart
   - X-Axis: `dim_date[full_date]`
   - Values: `[Total Ad Spend]`, `[Net Sales]`
4. **Visual 3: Campaign Performance Matrix**:
   - Columns: `campaign_name`, `channel`, `spend`, `impressions`, `clicks`, `conversions`, `cpc`, `roas`

---

## Page 08 — Investigation Queue & Decision Engine

### Purpose
The operational bridge from analytics to action. Displays ranked investigations with drill-through to root causes.

### Layout & Visuals
1. **KPI Cards**:
   - `[Total Open Investigations]`, `[Critical Priority Count]`, `[Total Financial Exposure at Risk]`, `[Avg Priority Score]`
2. **Visual 1: Prioritized Investigation Grid (Table / Matrix)**:
   - Columns:
     - `priority` (Conditional color: CRITICAL=Red, HIGH=Orange, MEDIUM=Yellow, LOW=Green)
     - `entity_type` (Order / Product / Customer / Warehouse)
     - `entity_name`
     - `issue`
     - `metric`
     - `observed_value`
     - `baseline_value`
     - `estimated_impact` (Formatted Currency)
     - `status`
   - Drill-through: Configured to drill through to Page 03 (Orders), Page 04 (Customers), or Page 05 (Products).
3. **Visual 2: Impact by Entity Type (Donut)**:
   - Legend: `entity_type`
   - Values: `SUM(estimated_impact)`
4. **Visual 3: Investigation Detail Pane (Multi-row Card or Text Visual)**:
   - Shows: `possible_drivers`, `evidence_summary`, `recommended_investigation` for selected queue item.
