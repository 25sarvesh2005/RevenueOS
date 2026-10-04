# RevenueOS — Project Overview

> **Automated Excel-to-Power BI Decision Engine & Desktop Studio**  
> *Author: Sarvesh Sharma*

---

## What is RevenueOS?

**RevenueOS** is a production-grade analytics platform and desktop application designed to bridge the gap between messy transactional Excel spreadsheets and enterprise-ready Power BI reporting.

Instead of manual data wrangling, schema modeling, and formula drafting, RevenueOS autonomously:
1. **Profiles & Ingests**: Ingests multi-sheet or single-sheet transactional Excel workbooks (`.xlsx`, `.xls`, `.xlsm`).
2. **Decomposes Star Schema**: Inferences Kimball dimensional star schemas, extracting Facts (orders, transactions, marketing) and Dimensions (customers, products, calendar date dimension).
3. **Synthesizes DAX Measures**: Automatically writes production-ready DAX calculations (Gross Sales, Net Revenue, COGS, Gross Margin %, Time Intelligence YTD/MoM/YoY, and Entity Intelligence).
4. **Compiles Power BI Templates**: Directly builds ready-to-open Power BI Templates (`.pbit`) and Developer Projects (`.pbip`) using native TMSL semantic models.
5. **Interactive In-App Power BI Replica Studio**: Provides a built-in desktop replica featuring:
   - **Report View**: Interactive KPI cards, monthly financial trends, category share donuts, channel breakdowns, and real-time slicers (Date range, Category pills, Channel filters).
   - **Data View**: In-memory tabular grid explorer with data type indicators and search filtering.
   - **Model View**: Interactive Star Schema topology diagram with Fact/Dimension cards and relationship lines (`1 : *`).
   - **DAX Formula Bar**: Power BI formula bar with measure selector, syntax viewer, and instant clipboard copy.

---

## Architecture Overview

```
RevenueOS/
├── frontend/        # Electron Power BI Desktop Studio (HTML, Fluent CSS, Chart.js)
├── backend/         # Master Python Kimball Engine, DAX Synthesis & ML Marts
├── data/            # Source Excel workbooks (e.g. data/raw/excel/revenueos_sample.xlsx)
├── exports/         # Generated .pbit templates, .pbip models, and clean CSV data marts
├── tests/           # 66 automated unit & integration test suites
├── start.bat        # Single-click Windows launcher
└── package.json     # Application entrypoint
```

---

## How to Run

### Windows (Single-Click)
Double-click `start.bat` (or `run.bat`) in the root directory.

### Command Line
```bash
npm start
```

---

## Commercial & Royalty License

This software and its underlying architecture are protected under the **RevenueOS Source-Available Commercial & Royalty License (Version 1.0)**.

- **Non-Commercial Use**: Free for personal evaluation, academic review, and local portfolio demonstrations.
- **Commercial Restriction**: Any commercial monetization, revenue generation, SaaS hosting, enterprise redistribution, or consulting use strictly requires prior written agreement and royalty payments to **Sarvesh Sharma**.
