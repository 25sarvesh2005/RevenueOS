# RevenueOS — Business Requirements Document (BRD)
## Institutional Specification, Operational Architecture & Commercial Royalty Framework

**Document ID:** `BRD-REVOS-2026.1`  
**Author & Copyright Holder:** Sarvesh Sharma  
**Version:** 1.0 (Production Release)  
**Status:** Approved for Commercial Architecture & Deployment  
**Governing License:** RevenueOS Source-Available Commercial & Royalty License (Version 1.0)  

---

## 1. Executive Summary & Strategic Purpose

Omnichannel retail, direct-to-consumer (D2C), and mid-market distribution enterprises routinely generate operational and transactional records across fragmented spreadsheets, disparate ERP exports, and siloed point-of-sale systems. In standard enterprise practice, transforming these raw workbooks into auditable business intelligence requires weeks of manual data engineering: resolving entity keys, normalizing denormalized tables into dimensional models, authoring hundreds of DAX calculations, and building Power BI reports.

**RevenueOS** is an autonomous revenue intelligence and decision platform that bridges raw transactional spreadsheets to executive financial intelligence. Through an integrated two-pillar architecture—combining a native **Electron Desktop Studio** and a high-performance **Python Analytics & DAX Engine**—RevenueOS automatically profiles any Excel workbook, decomposes flat sheets into a Kimball Star Schema, writes standardized DAX measures, compiles native Power BI template artifacts (`.pbit` & `.pbip`), synthesizes AI diagnostic memos, and enforces corporate revenue leakage triage with zero hallucination.

This document formalizes the complete business requirements, persona matrices, functional and non-functional specifications, operational governance, and commercial royalty licensing covenants governing RevenueOS.

---

## 2. Core Business Problems Solved

| Problem Domain | Industry Reality | RevenueOS Solution |
| :--- | :--- | :--- |
| **Manual Data Modeling Delays** | BI engineers spend 40–80 hours per project manually building star schemas, date tables, and foreign key relationships. | **Autonomous Schema Inference**: Detects facts, dimensions, bridges, calendar dimensions, and foreign keys in under 5 seconds. |
| **Formula Divergence & Vibe Metrics** | Different teams calculate Gross Margin, ROAS, and CAC with inconsistent mathematical baselines. | **Standardized DAX Synthesis**: Generates 180+ GAAP/IFRS-compliant DAX expressions with format strings, time-intelligence, and documentation. |
| **Unquantified Revenue Leakage** | Return spikes, promotional discount stacking, and inventory stockouts silently erode 2–5% of gross margin. | **Automated Leakage Radar**: Quantifies dollar-impact across 6 commercial mechanisms with deterministic severity tiers. |
| **Power BI Authoring Overhead** | Analysts rebuild identical charts, slicers, and themes across disparate client workspaces. | **Native Power BI Artifact Generation**: Compiles production-ready `.pbit` templates and `.pbip` developer projects natively. |
| **LLM Hallucinations in Financial BI** | Generic AI copilots invent revenue metrics or hallucinate non-existent database columns. | **Deterministic Investigation Copilot**: Root-cause briefs and action playbooks verified directly against physical star schema marts. |
| **Commercial Exploitation Without Royalties** | Open-source enterprise tools are frequently rebranded and monetized by intermediaries without creator compensation. | **Strict Commercial Royalty License**: Legally binding royalty covenants and liquidated damages protecting creator IP. |

---

## 3. Stakeholder Persona Matrix

### 3.1 Chief Financial Officer (CFO)
- **Primary Need**: Complete gross-to-net waterfall visibility, margin protection, discount governance, and executive reporting.
- **RevenueOS Touchpoint**: Executive Performance Briefing (HTML, Markdown, and 3-page Vector PDF), Gross-to-Net Waterfall chart, and Leakage Radar.
- **Success Metric**: Reduction of unmonitored promotional variance by $>15\%$; instant monthly reporting turnaround.

### 3.2 VP of Revenue Operations / FP&A Director
- **Primary Need**: Real-time cross-channel attribution, anomaly triage, root-cause diagnostics, and actionable remediation checklists.
- **RevenueOS Touchpoint**: AI Investigation Copilot modal, collaborative visual annotations, and recurring automated pipeline schedules.
- **Success Metric**: Mean-time-to-detection (MTTD) for margin compression reduced from weeks to seconds.

### 3.3 Head of Business Intelligence / Analytics Engineer
- **Primary Need**: Clean Kimball star schema marts, auditable CSV tables, TMSL data modeling, and Fabric project source control.
- **RevenueOS Touchpoint**: Power BI Desktop replica Studio, dynamic SVG Model View, live DAX formula bar, `.pbit` & `.pbip` compiler.
- **Success Metric**: Time-to-first-report for new transactional datasets reduced from 5 days to $<60$ seconds.

---

## 4. Functional Requirements (FR-01 to FR-12)

### FR-01: Universal Excel Ingestion & Profiling
- The system **MUST** ingest arbitrary Microsoft Excel workbooks (`.xlsx`, `.xlsm`, `.xls`) regardless of sheet count or column naming schemes.
- The system **MUST** profile every column for physical data type, null ratio, uniqueness cardinality, metric status, and date presence.
- The system **MUST** execute headless via CLI or interactively through the Electron Studio drag-and-drop zone.

### FR-02: Autonomous Entity Resolution & Single-Sheet Decomposition
- When presented with a single denormalized spreadsheet (e.g. flat transactional export), the system **MUST** automatically isolate distinct dimensional entities (e.g., `customers`, `products`, `locations`) from the central `orders` fact.
- Extracted dimensions **MUST** be deduplicated, assigned surrogate/natural primary keys, and linked back to the referencing fact table.

### FR-03: Kimball Star Schema Construction
- The engine **MUST** classify tables into **Facts**, **Dimensions**, **Junction Bridges**, and **Calendar Dimensions**.
- The system **MUST** auto-generate a comprehensive Kimball Calendar Dimension (`dim_date`) spanning the earliest to latest transaction date, including attributes: `full_date`, `year`, `quarter`, `month`, `month_name`, `month_year`, `day_of_week`, and `is_weekend`.
- Junction tables with $\ge 2$ dimension foreign keys and low metric density **MUST** be classified as `bridge` tables with bidirectional relationship semantics.

### FR-04: Enterprise DAX Metric Synthesis
- The system **MUST** synthesize standard semantic measures for all numeric metrics:
  - Aggregations: `SUM`, `AVERAGE`, `MIN`, `MAX`, `COUNTROWS`, `DISTINCTCOUNT`.
  - Financial Ratios: `Gross Profit`, `Gross Margin %`, `Discount Rate %`, `ROAS`, `CAC`, `AOV`.
  - Time-Intelligence: `YTD`, `Prior Month`, `MoM %`, `Prior Year`, `YoY %`.
- All measures **MUST** be encapsulated in a dedicated `_Measures` table and formatted with currency and percentage masks.

### FR-05: Native Power BI Artifact Compilation
- The engine **MUST** assemble binary `.pbit` (Power BI Template) archives natively using Python `zipfile`, embedding TMSL schemas, layout diagrams, and Power Query M ingestion scripts.
- The engine **MUST** compile Microsoft Fabric `.pbip` Developer Projects with decoupled `.SemanticModel/model.bim` and `.Report/definition.pbir` structures.

### FR-06: High-Resolution 9-Chart Visual Intelligence Pack
The engine **MUST** render 9 publication-grade, dark-mode 300 DPI Matplotlib analytical charts:
1. `01_monthly_revenue_and_margin_trend.png` (Dual-axis monthly trajectory)
2. `02_category_revenue_distribution.png` (Categorical Pareto revenue contribution)
3. `03_channel_revenue_breakdown.png` (Acquisition channel volume distribution)
4. `04_top_products_ranking.png` (Top 10 revenue-generating SKUs)
5. `05_executive_summary_dashboard.png` (Executive 4-quadrant overview with KPI banners)
6. `06_marketing_roas_analysis.png` (Marketing channel spend vs. ROAS multiplier)
7. `07_gross_to_net_waterfall.png` (Gross-to-net bridge: Gross $\rightarrow$ Discounts $\rightarrow$ Returns $\rightarrow$ Net $\rightarrow$ COGS $\rightarrow$ Gross Profit)
8. `08_price_elasticity_scatter.png` (Unit selling price vs. units sold, bubble-scaled by revenue)
9. `09_metric_correlation_matrix.png` (Pearson correlation heatmap across all numerical metrics)

### FR-07: Low-Latency DAX Evaluation Runtime
- The backend **MUST** expose a Pandas-powered DAX evaluator capable of executing `SUM`, `AVERAGE`, `MIN`, `MAX`, `COUNTROWS`, `DISTINCTCOUNT`, `DIVIDE`, and compound measure references in $<2$ milliseconds.
- The formula bar in the Electron Studio **MUST** evaluate expressions in real time, supporting both naked expressions and assignment syntax (`[Measure Name] = ...`).

### FR-08: AI Investigation Copilot with Root-Cause Diagnostics
- The system **MUST** provide a diagnostic Copilot synthesizing statistical anomaly signals into structured memos:
  - Situation Analysis (benchmark comparison)
  - Root-Cause Drivers (discount stacking, return transit defects, supplier cost variance)
  - Immediate Remediation Action Checklist
- All statements **MUST** be derived from ingested star schema marts with zero generative hallucination.

### FR-09: Publication-Grade Multi-Page Vector PDF Briefing
- The system **MUST** compile a 3-page vector PDF executive briefing:
  - **Page 1**: Executive scoreboards, KPI cards, and primary waterfall/trend visualization.
  - **Page 2**: Multi-dimensional diagnostics, top product rankings, and elasticity scatter.
  - **Page 3**: Complete star schema table catalog, top DAX measures, and mandatory commercial royalty licensing notice.

### FR-10: Collaborative Visual Annotation Layer
- Users **MUST** be able to attach timestamped, author-attributed annotations to specific visual components.
- Annotations **MUST** be categorized (`note`, `risk`, `opportunity`, `leakage`) and retrievable via API.

### FR-11: Multi-Tenant Run Tracking & Scheduled Ingestion
- The platform **MUST** track pipeline runs chronologically, supporting multi-tenant isolation via `tenant_id`.
- The system **MUST** allow registration of recurring cron schedules for automated ingestion.

### FR-12: External Webhook Triggering
- The system **MUST** provide an external webhook endpoint (`POST /api/webhook/pipeline-trigger`) to enable triggering pipeline execution from third-party systems (ERP, Zapier, Shopify, Stripe).

---

## 5. Non-Functional Requirements (NFR-01 to NFR-08)

| Code | Category | Requirement Specification |
| :--- | :--- | :--- |
| **NFR-01** | **Performance & Latency** | Sub-millisecond ($<2$ms) DAX formula evaluation; pipeline completion under 10 seconds for workbooks $\le 50,000$ rows. |
| **NFR-02** | **Zero Hallucination** | 100% of financial figures, totals, and percentages must match standard GAAP/IFRS accounting definitions exactly. |
| **NFR-03** | **Desktop Portability** | The Electron Studio must operate fully offline with bundled Python scripts without external cloud dependencies. |
| **NFR-04** | **Security & Isolation** | Strict Content Security Policy (`default-src 'self'`), context bridge isolation, and path traversal guards on all file operations. |
| **NFR-05** | **Test Coverage** | Full test suite must maintain $\ge 120$ automated tests with a 100% pass rate across Python 3.10 through 3.13. |
| **NFR-06** | **Cross-Platform Compatibility** | Universal compatibility across Windows 10/11, macOS (Apple Silicon & Intel), and Ubuntu Linux. |
| **NFR-07** | **Observability** | Structured audit logging with execution IDs, duration milliseconds, phase breakdowns, and records processed. |
| **NFR-08** | **Extensibility** | Clean ES module architecture in frontend ($<300$ lines per module); modular analytics engine in backend. |

---

## 6. Commercial Royalty Licensing Model & IP Governance

RevenueOS is released under a **Source-Available Commercial & Royalty License (Version 1.0)** authored by **Sarvesh Sharma**:

### 6.1 Permitted Evaluation Scope
- Individuals, academic researchers, and enterprise evaluators may inspect, test, compile, and benchmark RevenueOS in non-production environments free of charge.

### 6.2 Strict Commercial Use Prohibition
- **No third party, corporation, consultancy, or individual has the right to profit from, monetize, or commercially deploy RevenueOS without an executed commercial license and mandatory royalty remittances.**
- Prohibited activities include:
  1. Operating RevenueOS as a commercial SaaS, cloud API, or managed analytics service.
  2. Utilizing RevenueOS to deliver paid consulting, advisory, or fee-based implementations.
  3. Bundling or reselling RevenueOS within proprietary commercial software suites.
  4. Deriving direct commercial revenue or arbitrage from RevenueOS outputs without licensing.

### 6.3 Mandatory Remittance & Royalty Structure
- Commercial deployment requires an executed **RevenueOS Commercial Enterprise Agreement** with **Sarvesh Sharma**.
- Agreements stipulate mandatory recurring license fees and/or percentage-based revenue royalties.
- Violations are subject to contractual liquidated damages, statutory copyright damages, and immediate injunctive relief.

---

## 7. Accounting & Regulatory Conformity

All automated computations adhere to international financial reporting standards:
- **ASC 606 / IFRS 15**: Revenue recognized only upon transfer of control; promotional discounts and return provisions deducted directly from gross inflow.
- **Gross-to-Net Bridge**:
  $$\text{Gross Revenue} = \sum (\text{Quantity} \times \text{Unit Selling Price})$$
  $$\text{Net Sales} = \text{Gross Revenue} - \text{Promotional Discounts}$$
  $$\text{Net Revenue} = \text{Net Sales} - \text{Return Adjustments}$$
  $$\text{Gross Profit} = \text{Net Revenue} - \text{Cost of Goods Sold (COGS)}$$
  $$\text{Gross Margin \%} = \frac{\text{Gross Profit}}{\text{Net Revenue}} \times 100$$
- **Clamp Guarantees**: Discount percentages $>1.0$ normalized; negative quantities quarantined to return allowances.

---

*Document finalized by Antigravity under architectural instruction of Sarvesh Sharma — Author & Copyright Holder of RevenueOS.*
