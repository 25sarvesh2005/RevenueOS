# RevenueOS – Power BI Desktop Setup & Deployment Guide

This directory contains the production assets for connecting, modeling, and styling the **RevenueOS 8-Page Executive Power BI Dashboard**.

---

## Directory Contents

| File | Purpose |
| :--- | :--- |
| **[`RevenueOS.pbit`](file:///c:/Partition/SERIOUS%20PROJECTS/RevenueOS/powerbi/RevenueOS.pbit)** | **One-click Power BI Template: pre-wired relationships, 70 measures, all 18 tables, 8 pages** |
| **[`RevenueOS.pbip`](file:///c:/Partition/SERIOUS%20PROJECTS/RevenueOS/powerbi/RevenueOS.pbip)** | **Power BI Project entrypoint (modern developer format with TMDL/PBIR structure)** |
| [`build_powerbi_file.py`](file:///c:/Partition/SERIOUS%20PROJECTS/RevenueOS/powerbi/build_powerbi_file.py) | Automated Python compiler to regenerate `.pbit` and `.pbip` from code |
| [`dax_measures.dax`](file:///c:/Partition/SERIOUS%20PROJECTS/RevenueOS/powerbi/dax_measures.dax) | Complete DAX measure library organized across all 8 pages |
| [`power_query_m.pq`](file:///c:/Partition/SERIOUS%20PROJECTS/RevenueOS/powerbi/power_query_m.pq) | Copy-paste M scripts to ingest PostgreSQL `gold` star schema |
| [`revenueos_theme.json`](file:///c:/Partition/SERIOUS%20PROJECTS/RevenueOS/powerbi/revenueos_theme.json) | High-contrast Dark Slate executive UI theme |
| [`page_specifications.md`](file:///c:/Partition/SERIOUS%20PROJECTS/RevenueOS/powerbi/page_specifications.md) | Detailed visual layout and drill-through blueprints for Pages 01–08 |

---

## ⚡ Quickest Way (Single-Click Ready File)

You do **not** need to manually copy-paste queries, drag relationship lines, or create measures one-by-one.

1. **Start the database and pipeline** (if not already running):
   ```bash
   docker compose up -d
   python pipeline.py --truncate
   ```
2. **Double-click [`RevenueOS.pbit`](file:///c:/Partition/SERIOUS%20PROJECTS/RevenueOS/powerbi/RevenueOS.pbit)** (or open [`RevenueOS.pbip`](file:///c:/Partition/SERIOUS%20PROJECTS/RevenueOS/powerbi/RevenueOS.pbip)).
3. Power BI Desktop will launch with:
   - **All 18 tables** loaded from the Gold schema via Power Query M.
   - **All 14 Star Schema Relationships** pre-joined (Single cross-filter direction, 1-to-Many `1:*`).
   - **All 70 DAX Measures** pre-calculated inside the dedicated `_Measures` table.
   - **All 8 Executive Report Pages** configured at 1920×1080 canvas size.
   - **Dark Slate Executive Theme** pre-applied.
4. When prompted, confirm or enter your database connection (defaults: `DBServer = localhost:5432`, `DBDatabase = revenueos`), then click **Load**.

---

## 🛠 Manual Setup Instructions (Alternative)

### Step 1: Spin Up the Database
Ensure PostgreSQL is running (either locally or via Docker):
```bash
docker compose up -d postgres
```

### Step 2: Run Excel Preprocessing and the RevenueOS Pipeline
Place source workbooks in `data/raw/excel/`, then run:

```bash
python pipeline.py --truncate
```

This imports Excel sheets into canonical raw CSVs, loads Bronze, cleans Silver, and rebuilds the Power BI-ready Gold layer.

### Step 3: Ingest the Gold Star Schema via Power Query
1. Open **Power BI Desktop**.
2. Click **Home** → **Transform Data** (opens Power Query Editor).
3. Under **Home** → **Manage Parameters**, create two parameters:
   - `DBServer`: Text, `localhost:5432`
   - `DBDatabase`: Text, `revenueos`
4. Click **New Source** → **Blank Query** → **Advanced Editor**.
5. Paste the M scripts from [`power_query_m.pq`](file:///c:/Partition/SERIOUS%20PROJECTS/RevenueOS/powerbi/power_query_m.pq) for each table:
   - Dimensions: `dim_date`, `dim_customer`, `dim_product`, `dim_channel`, `dim_location`, `dim_campaign`, `dim_payment_method`
   - Facts: `fact_orders`, `fact_payments`, `fact_returns`, `fact_inventory`, `fact_marketing`
   - Analytics / Queue: `gold_investigation_queue`, `gold_product_profitability`, `gold_customer_health`
6. Click **Close & Apply**.

### Step 4: Establish Star Schema Relationships
In Power BI's **Model View**, link the dimension primary keys to fact foreign keys:
- `dim_date[date_key]` → `fact_orders[date_key]` (1 to *)
- `dim_date[date_key]` → `fact_payments[date_key]` (1 to *)
- `dim_date[date_key]` → `fact_returns[date_key]` (1 to *)
- `dim_date[date_key]` → `fact_inventory[date_key]` (1 to *)
- `dim_date[date_key]` → `fact_marketing[date_key]` (1 to *)
- `dim_customer[customer_key]` → `fact_orders[customer_key]` (1 to *)
- `dim_product[product_key]` → `fact_orders[product_key]` (1 to *)
- `dim_product[product_key]` → `fact_returns[product_key]` (1 to *)
- `dim_product[product_key]` → `fact_inventory[product_key]` (1 to *)
- `dim_channel[channel_key]` → `fact_orders[channel_key]` (1 to *)
- `dim_location[location_key]` → `fact_orders[location_key]` (1 to *)
- `dim_campaign[campaign_key]` → `fact_marketing[campaign_key]` (1 to *)
- `dim_payment_method[payment_method_key]` → `fact_payments[payment_method_key]` (1 to *)

### Step 5: Import the Dark Theme
1. In the Power BI ribbon, select **View** → **Themes** dropdown.
2. Click **Browse for themes...**
3. Select [`revenueos_theme.json`](file:///c:/Partition/SERIOUS%20PROJECTS/RevenueOS/powerbi/revenueos_theme.json).

### Step 6: Add DAX Measures & Assemble Visuals
1. Create a blank measure holder table: **Home** → **Enter Data** → Name table `_Measures`.
2. Open [`dax_measures.dax`](file:///c:/Partition/SERIOUS%20PROJECTS/RevenueOS/powerbi/dax_measures.dax) and create the measures in `_Measures`.
3. Follow [`page_specifications.md`](file:///c:/Partition/SERIOUS%20PROJECTS/RevenueOS/powerbi/page_specifications.md) to assemble each of the 8 pages:
   - **01 Executive Command Center**
   - **02 Revenue Intelligence**
   - **03 Revenue Leakage Radar**
   - **04 Customer Intelligence**
   - **05 Product & Profitability**
   - **06 Inventory & Operations**
   - **07 Marketing Efficiency**
   - **08 Investigation Queue**
