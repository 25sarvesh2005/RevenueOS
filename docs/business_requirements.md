# RevenueOS – Business Requirements Document (BRD)

## 1. Executive Context & Business Scenario

### Company Profile
The business is a mid-sized omnichannel consumer retail enterprise generating between ₹50 Cr and ₹250 Cr in annualized gross merchandise value (GMV). Operations span multiple consumer touchpoints:
- **Direct-to-Consumer (D2C)**: Web storefront and mobile application.
- **Marketplaces**: Third-party channel partners (Amazon Marketplace, Flipkart).
- **Physical Retail**: Company-owned flagship and regional partner experience stores.
- **Wholesale / B2B**: Institutional supply orders.

### The Business Challenge
While gross sales indicate sustained quarter-on-quarter growth, commercial operating margin is compressing. Multiple disconnected operational systems prevent executive leadership from diagnosing where capital is being lost:
1. **ERP / Order Management**: Logs gross transactions but does not track post-order return costs or payment processing failures.
2. **Payment Gateways**: Track checkout authorizations and drops, isolated from customer lifetime value data.
3. **Warehouse / WMS**: Records stockouts and safety buffers, but lacks financial modeling on lost sales opportunity.
4. **Ad Platforms**: Report platform-attributed ROAS without factoring in return rates or heavy promotional discounting.

RevenueOS serves as the single source of financial and decision intelligence unifying these operational silos.

---

## 2. Core Business Objectives

RevenueOS must definitively answer five core questions:

| # | Core Question | Primary Operational Owner | RevenueOS System Component |
|---|:---|:---|:---|
| **1** | **Where is revenue being generated?** | VP Commercial / CCO | `gold_daily_financials`, Page 01 & 02 |
| **2** | **Where is profit being created or destroyed?** | VP Finance / CFO | `gold_product_profitability`, Page 05 |
| **3** | **Where is revenue leaking?** | Head of Commercial Ops | `gold_revenue_leakage`, Page 03 |
| **4** | **Which customers, products, and inventory situations require immediate intervention?** | Merchandising & CRM Directors | `gold_customer_health`, `gold_inventory_risk`, Page 04 & 06 |
| **5** | **What specific issue should an analyst investigate next?** | Lead Analytics Engineer / Commercial Analyst | `gold_investigation_queue`, `Investigation Copilot`, Page 08 |

---

## 3. Financial Waterfall Reconciliation Standards

To maintain absolute financial integrity and auditability, all calculations in SQL, Python, and Power BI must conform strictly to the following mathematical waterfall:

$$\begin{aligned}
\text{Gross Revenue} &= \sum (\text{Quantity} \times \text{Unit Price}) \\
\text{Total Discounts} &= \sum (\text{Quantity} \times \text{Unit Price} \times \text{Discount Rate}) \\
\text{Net Sales} &= \text{Gross Revenue} - \text{Total Discounts} \\
\text{Total Returns} &= \sum (\text{Quantity Returned} \times \text{Unit Price}) \\
\text{Net Revenue} &= \text{Net Sales} - \text{Total Returns} \\
\text{Cost of Goods Sold (COGS)} &= \sum (\text{Quantity} \times \text{Product Standard Cost}) \\
\text{Gross Profit} &= \text{Net Sales} - \text{COGS} \\
\text{Gross Margin \%} &= \frac{\text{Gross Profit}}{\text{Net Sales}} \\
\text{Net Contribution After Marketing} &= \text{Gross Profit} - \text{Total Marketing Ad Spend}
\end{aligned}$$

> **Important Accounting Principle**:
> Operating expenses (returns, discounts, cancellations) must never be hidden or silently blended into net numbers. The reconciliation ledger must make every reduction visible and traceable to individual order IDs.

---

## 4. Stakeholder Personas & Acceptance Criteria

### 1. Chief Financial Officer / VP Finance
- **Needs**: High-level visibility into true realized margin, gross-to-net waterfall, and reconciliation against bank payouts.
- **Acceptance Criteria**: Discrepancies between payment captures and net sales must be flagged if variance exceeds 2.0%.

### 2. VP of Commercial & Retail
- **Needs**: Channel and regional performance comparison, promotional discount impact, and pricing elasticity.
- **Acceptance Criteria**: High-volume, low-margin products ("Revenue Traps") must be automatically surfaced within 24 hours of margin deterioration.

### 3. Supply Chain & Inventory Director
- **Needs**: Days-of-Inventory (DOI) tracking, warehouse stockout incidence, and estimated revenue impact of unfulfilled demand.
- **Acceptance Criteria**: Stockout financial impact must be estimated based on trailing 30-day average daily sales velocity.

### 4. Head of Growth & Marketing
- **Needs**: True blended ROAS and Customer Acquisition Cost (CAC) calculated against actual realized margin rather than top-line gross GMV.
- **Acceptance Criteria**: Marketing efficiency reports must report Contribution After Marketing (CAM) and account for customer return rates by campaign.

### 5. Lead Commercial Analyst
- **Needs**: A ranked queue of data anomalies and margin erosions with root-cause drivers already extracted so investigative effort is focused on actionable remedies.
- **Acceptance Criteria**: Investigation Queue must compute objective priority scores ($Impact \times Severity \times Confidence$) and link directly to source transaction IDs.

---

## 5. Non-Functional & SLA Requirements

- **Data Refresh SLA**: The batch pipeline must complete execution within 15 minutes of source data arrival.
- **Data Integrity Threshold**: Duplicate order records in Bronze must be de-duplicated with 100% precision in Silver.
- **Auditability**: 100% of rows in Gold star schema must be traceable to Bronze `source_file` and `ingestion_timestamp`.
- **System Portability**: The entire data platform must run locally via Docker Compose without requiring external cloud accounts or vendor lock-in.
