# RevenueOS_Sample – Power BI Deployment & Import Guide

This document provides step-by-step instructions to load your converted Excel dataset into Power BI Desktop.

---

## ⚡ Method 1: Single-Click Instant Template (Recommended)

1. Locate the compiled template:
   `powerbi/revenueos_sample.pbit`
2. **Double-click** `revenueos_sample.pbit`. Power BI Desktop will launch automatically with all tables, relationships, and DAX measures pre-loaded!
3. Click **Load** or **Apply Changes**.

---

## 🛠 Method 2: Manual CSV Import & Model Setup

1. Open **Power BI Desktop**.
2. Click **Get Data** → **Text/CSV**.
3. Browse to `C:/Partition/SERIOUS PROJECTS/RevenueOS/data/raw/excel/powerbi_export_revenueos_sample_20261004_113020/csv` and load all tables:
   - `orders.csv` (500 rows, DIMENSION)
   - `customers.csv` (100 rows, DIMENSION)
   - `products.csv` (31 rows, DIMENSION)
   - `payments.csv` (520 rows, FACT)
   - `returns.csv` (25 rows, FACT)
   - `inventory.csv` (11,284 rows, FACT)
   - `marketing.csv` (4,473 rows, FACT)
   - `dim_date.csv` (1,096 rows, DIMENSION)

4. Navigate to **Model View** and wire the Star Schema relationships:
- Connect `payments.order_id` (Many) to `orders.order_id` (One).
- Connect `returns.order_id` (Many) to `orders.order_id` (One).
- Connect `orders.customer_id` (Many) to `customers.customer_id` (One).
- Connect `orders.product_id` (Many) to `products.product_id` (One).
- Connect `returns.product_id` (Many) to `products.product_id` (One).
- Connect `inventory.product_id` (Many) to `products.product_id` (One).
- Connect `orders.order_date` (Many) to `dim_date.date` (One).
- Connect `customers.signup_date` (Many) to `dim_date.date` (One).
- Connect `payments.payment_date` (Many) to `dim_date.date` (One).
- Connect `returns.return_date` (Many) to `dim_date.date` (One).
- Connect `inventory.snapshot_date` (Many) to `dim_date.date` (One).
- Connect `marketing.date` (Many) to `dim_date.date` (One).

5. Create `_Measures` table and copy-paste the formulas from `powerbi/measures.dax`.
