# RevenueOS_Enterprise_Sample – Power BI Deployment & Import Guide

This document provides step-by-step instructions to load your converted Excel dataset into Power BI Desktop.

---

## ⚡ Method 1: Single-Click Instant Template (Recommended)

You do **not** need to manually drag tables or write formulas. The engine has pre-wired everything:

1. Locate the compiled template:
   `powerbi/revenueos_enterprise_sample.pbit`
2. **Double-click** `revenueos_enterprise_sample.pbit`. Power BI Desktop will launch automatically.
3. Power BI will prompt you to verify or confirm parameters:
   - All **8 Tables** are pre-loaded from CSV.
   - All **12 Star Schema Relationships** are pre-joined (`1:*`).
   - All **69 DAX Measures** are pre-calculated inside the `_Measures` table.
4. Click **Load** or **Apply Changes**.

---

## 🛠 Method 2: Manual CSV Import & Model Setup

If you prefer to configure your model manually in Power BI Desktop:

### Step 1: Ingest the Generated CSV Files
1. Open **Power BI Desktop**.
2. On the **Home** tab ribbon, click **Get Data** → **Text/CSV**.
3. Browse to the output CSV folder:
   `C:/Partition/SERIOUS PROJECTS/RevenueOS/data/raw/excel/powerbi_export_revenueos_sample_20261005_223811/csv`
4. Import each generated table:
   - `orders.csv` (500 rows, DIMENSION)
   - `customers.csv` (100 rows, DIMENSION)
   - `products.csv` (31 rows, DIMENSION)
   - `payments.csv` (520 rows, FACT)
   - `returns.csv` (25 rows, BRIDGE)
   - `inventory.csv` (11,284 rows, FACT)
   - `marketing.csv` (4,473 rows, FACT)
   - `dim_date.csv` (1,096 rows, DIMENSION)

5. Click **Load** for each table.

---

### Step 2: Configure the Star Schema Relationships
1. In the left navigation bar of Power BI Desktop, click **Model View** (icon with 3 boxes).
2. Arrange your Fact tables in the center and Dimension tables around them.
3. Drag and connect the following primary/foreign key pairs:

| From (Fact Table) | Column | Cardinality | To (Dimension Table) | Column |
| :--- | :--- | :---: | :--- | :--- |
| **payments** | `order_id` | `* : 1` (One-Way) | **orders** | `order_id` |
| **returns** | `order_id` | `* : 1` (One-Way) | **orders** | `order_id` |
| **orders** | `customer_id` | `* : 1` (One-Way) | **customers** | `customer_id` |
| **orders** | `product_id` | `* : 1` (One-Way) | **products** | `product_id` |
| **returns** | `product_id` | `* : 1` (One-Way) | **products** | `product_id` |
| **inventory** | `product_id` | `* : 1` (One-Way) | **products** | `product_id` |
| **orders** | `order_date` | `* : 1` (One-Way) | **dim_date** | `date` |
| **customers** | `signup_date` | `* : 1` (One-Way) | **dim_date** | `date` |
| **payments** | `payment_date` | `* : 1` (One-Way) | **dim_date** | `date` |
| **returns** | `return_date` | `* : 1` (One-Way) | **dim_date** | `date` |
| **inventory** | `snapshot_date` | `* : 1` (One-Way) | **dim_date** | `date` |
| **marketing** | `date` | `* : 1` (One-Way) | **dim_date** | `date` |

---

### Step 3: Add the DAX Measures
1. On the **Home** tab, click **Enter Data**.
2. Name the table `_Measures` and click **Load**.
3. Select `_Measures` in the Data pane, click **New Measure** on the ribbon.
4. Open `powerbi/measures.dax` and paste the desired measures:

#### Core Measures Preview:
```dax
Payments Count = 
DISTINCTCOUNT(payments[payment_id])
```

```dax
Total Amount = 
SUM(payments[amount])
```

```dax
Average Amount = 
AVERAGE(payments[amount])
```

```dax
Amount YTD = 
TOTALYTD([Total Amount], dim_date[date])
```

```dax
Amount Prior Month = 
CALCULATE([Total Amount], PREVIOUSMONTH(dim_date[date]))
```

```dax
Amount MoM % = 
DIVIDE([Total Amount] - [Amount Prior Month], [Amount Prior Month], 0)
```

```dax
Amount Prior Year = 
CALCULATE([Total Amount], SAMEPERIODLASTYEAR(dim_date[date]))
```

```dax
Amount YoY % = 
DIVIDE([Total Amount] - [Amount Prior Year], [Amount Prior Year], 0)
```


---

## 📜 Intellectual Property & Commercial License

This automated pipeline and its generated assets are governed by the:
**RevenueOS Source-Available Commercial & Royalty License (Version 1.0)**

- **Permitted**: Non-commercial internal testing, evaluation, and research.
- **Strictly Prohibited**: Any monetization, commercial exploitation, hosted SaaS deployment, or resale without prior written agreement and royalty payments to the author (**Sarvesh Sharma**).
