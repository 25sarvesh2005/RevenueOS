# RevenueOS — Enterprise Data Dictionary & Schema Catalog
**Kimball Dimensional Architecture & Field Specifications**  
*Document Version: 1.0.0 · Author: Sarvesh Sharma · License: RevenueOS Commercial Royalty License*

---

## 1. Schema Topology (Star Schema)

RevenueOS structures all ingested business spreadsheets into a high-performance **Kimball Dimensional Star Schema** with single-direction ($1 : *$) referential integrity.

```
       ┌────────────────────────┐
       │     dim_customers      │
       │────────────────────────│
       │ PK: customer_id        │
       └───────────┬────────────┘
                   │ 1
                   │
                   │ *
┌──────────────────┴─────┐         ┌────────────────────────┐
│      fact_orders       │ *     1 │      dim_products      │
│────────────────────────├─────────┤────────────────────────│
│ PK: order_id           │         │ PK: product_id         │
│ FK: customer_id        │         └────────────────────────┘
│ FK: product_id         │
│ FK: date_id (FK: date) │         ┌────────────────────────┐
│ FK: channel_id         │ *     1 │        dim_date        │
└──────────────────┬─────┴─────────┤────────────────────────│
                   │               │ PK: date               │
                   │ *             └────────────────────────┘
                   │
                   │ 1
       ┌───────────┴────────────┐
       │      dim_channels      │
       │────────────────────────│
       │ PK: channel_id         │
       └────────────────────────┘
```

---

## 2. Fact Tables

### 2.1 `orders` (Core Sales Transactions Fact)
* **Grain**: One record per line-item / commercial order transaction.
* **Storage Mart**: `csv/orders.csv`

| Column Name | Logical Type | Physical Type | Nullable | Key Role | Business Description | Sample Value |
| :--- | :--- | :--- | :---: | :---: | :--- | :--- |
| `order_id` | String | `VARCHAR(64)` | No | PK / Degenerate | Unique transaction invoice number | `ORD-2024-001` |
| `order_date` | Date | `DATE` | No | FK (`dim_date.date`) | Calendar execution date of order | `2024-01-15` |
| `customer_id` | String | `VARCHAR(64)` | No | FK (`dim_customers`) | Client or purchaser identifier | `CUST-8812` |
| `product_id` | String | `VARCHAR(64)` | No | FK (`dim_products`) | Inventory SKU or item code | `SKU-PRO-40` |
| `quantity` | Integer | `INT4 / INT64` | No | Measure | Number of physical units sold | `3` |
| `unit_price` | Currency | `FLOAT8` | No | Measure | Invoiced price per single unit | `149.99` |
| `unit_cost` | Currency | `FLOAT8` | Yes | Measure | Wholesale / direct production cost | `92.50` |
| `discount` | Percentage | `FLOAT8` | No | Measure | Applied promotional discount rate ($0.0 - 1.0$) | `0.10` |
| `channel` | String | `VARCHAR(32)` | Yes | Attribute / FK | Go-to-market channel (`Online`, `Direct`) | `Online` |
| `status` | String | `VARCHAR(32)` | No | Attribute | Order lifecycle status (`Delivered`, `Shipped`) | `Delivered` |

---

## 3. Dimension Tables

### 3.1 `dim_customers` (Customer Master Dimension)
* **Grain**: One record per unique commercial account or individual client.
* **Storage Mart**: `csv/customers.csv`

| Column Name | Logical Type | Physical Type | Nullable | Key Role | Business Description | Sample Value |
| :--- | :--- | :--- | :---: | :---: | :--- | :--- |
| `customer_id` | String | `VARCHAR(64)` | No | PK | Primary business customer key | `CUST-8812` |
| `customer_name` | String | `VARCHAR(128)` | Yes | Attribute | Account name or trading identity | `Global Logistics Inc` |
| `segment` | String | `VARCHAR(32)` | Yes | Attribute | Market classification (`Enterprise`, `SMB`) | `Enterprise` |
| `region` | String | `VARCHAR(64)` | Yes | Attribute | Geographic operating region | `North America` |
| `signup_date` | Date | `DATE` | Yes | Attribute | Initial onboarding / registration date | `2023-04-12` |

---

### 3.2 `dim_products` (Product & Catalog Dimension)
* **Grain**: One record per distinct product SKU or catalog service item.
* **Storage Mart**: `csv/products.csv`

| Column Name | Logical Type | Physical Type | Nullable | Key Role | Business Description | Sample Value |
| :--- | :--- | :--- | :---: | :---: | :--- | :--- |
| `product_id` | String | `VARCHAR(64)` | No | PK | Inventory stock keeping unit (SKU) | `SKU-PRO-40` |
| `product_name` | String | `VARCHAR(128)` | No | Attribute | Formal product catalog title | `Industrial Sensor V3` |
| `category` | String | `VARCHAR(64)` | Yes | Attribute | Parent merchandise category | `Electronics` |
| `sub_category` | String | `VARCHAR(64)` | Yes | Attribute | Granular product taxonomy | `Hardware Sensors` |
| `standard_cost` | Currency | `FLOAT8` | Yes | Attribute | Standard inventory valuation cost | `85.00` |
| `list_price` | Currency | `FLOAT8` | Yes | Attribute | Manufacturer suggested retail price (MSRP) | `149.99` |

---

### 3.3 `dim_date` (Master Calendar Date Dimension)
* **Grain**: One record per calendar day across entire reporting horizon.
* **Storage Mart**: `csv/dim_date.csv`

| Column Name | Logical Type | Physical Type | Nullable | Key Role | Business Description | Sample Value |
| :--- | :--- | :--- | :---: | :---: | :--- | :--- |
| `date` | Date | `DATE` | No | PK | Standard calendar date (`YYYY-MM-DD`) | `2024-01-15` |
| `year` | Integer | `INT4` | No | Attribute | Four-digit calendar year | `2024` |
| `quarter` | String | `VARCHAR(8)` | No | Attribute | Calendar quarter designation | `Q1` |
| `month` | Integer | `INT4` | No | Attribute | Month number ($1 - 12$) | `1` |
| `month_name` | String | `VARCHAR(16)` | No | Attribute | Full English month name | `January` |
| `week_number` | Integer | `INT4` | No | Attribute | ISO calendar week number ($1 - 53$) | `3` |
| `day_of_week` | String | `VARCHAR(16)` | No | Attribute | Weekday name (`Monday`, `Tuesday`) | `Monday` |
| `is_weekend` | Boolean | `BOOLEAN` | No | Attribute | Saturday or Sunday flag | `False` |

---

## 4. Analytical Mart Tables (`gold` Layer)

| Analytical Mart | Description | Key Metric Columns |
| :--- | :--- | :--- |
| `gold_daily_financials` | Daily rollup of top-line, margin, and order volume | `gross_revenue`, `cogs`, `gross_profit`, `margin_pct` |
| `gold_revenue_leakage` | Quantified revenue leakage across 6 mechanisms | `leakage_amount`, `mechanism`, `severity` |
| `gold_product_profitability`| 4-Quadrant BCG-style profitability classification | `classification` (Profit Driver, Revenue Trap) |
| `gold_customer_health` | RFM customer retention and health scoring | `health_score`, `health_tier`, `churn_risk` |
| `gold_investigation_queue` | Prioritized anomaly detection signals for Copilot | `priority_score`, `issue`, `estimated_impact` |

---

## 5. Proprietary License Notice

This schema architecture, field definitions, and entity mappings are proprietary intellectual property governed by the **RevenueOS Commercial Royalty License**.
