# RevenueOS Studio — UI/UX Comprehensive Audit

> **Phase 1 Deliverable according to AGENTS.md**  
> *Author: Principal Design Engineer*  
> *Target: RevenueOS Desktop (Electron + Python)*  
> *Date: 2026-10-05*

---

## 1. Project Context & Inventory

| Attribute | Specification |
|---|---|
| **What the app does** | Automated Excel-to-Power BI Decision Engine and Studio that profiles transactional workbooks, in-memory decomposes Kimball Star Schemas, synthesizes DAX calculations, and compiles production `.pbit` templates. |
| **Primary users** | Financial Analysts, Revenue Operations (RevOps) Managers, BI Developers, and Executive Decision Makers. |
| **The user's #1 job** | Ingest any transactional workbook (`.xlsx`, `.csv`) and instantly explore verified data marts, star schema relationships, dynamic financial KPIs, and export ready-to-use Power BI artifacts. |
| **Platform** | Windows (primary / tested), macOS, Linux. |
| **Renderer Stack** | Vanilla HTML5 / ES6 Modules / Vanilla CSS custom property tokens / Chart.js engine. |
| **Python Backend** | Python 3.10+ engine (`backend/engine/core.py`, `backend/engine/master.py`), FastAPI REST fallback (`backend/api/app.py`), Pandas, NumPy, OpenPyXL. |
| **IPC Architecture** | Secure Electron IPC bridge (`contextBridge`, `ipcRenderer.invoke`, `ipcMain.handle`) with zero Node integration in renderer + HTTP localhost fallback. |
| **Brand Assets** | RevenueOS Geometric Matrix logo (`#6366F1`, `#F59E0B`, `#10B981`, `#06B6D4`). |
| **Visual Direction** | High-density analytical studio, sleek dark mode default with light mode system toggle, crisp contrast, zero decorative fluff. |
| **Hard Constraints** | Offline-capable, strict CSP (no unsafe remote CDNs), min window size 1100x740, <100ms UI response time. |

---

## 2. Screen & Flow Inventory

The application is structured into four dedicated primary views and one operational modal:

### View 1: Executive Dashboard (`#view_dashboard`)
- **Purpose**: High-level financial and operational health assessment.
- **Entry Point**: Default view upon launch; accessible via tab `[ 📊 Executive Dashboard ]`.
- **Primary Elements**:
  - Global slicer bar (Period date range, Category pills, Channel selector, Reset button, active filter chip).
  - 5 Dynamic KPI Cards (Gross Revenue, Gross Profit, Gross Margin %, Total Orders, Units Sold & Returns).
  - 2x2 Responsive Analytical Grid:
    - Monthly Revenue, Cost & Margin % Trajectory (Dual-Axis Combo).
    - Revenue Contribution by Category (Donut with click-to-filter).
    - Revenue by Sales Channel (Bar with click-to-filter).
    - Top 10 Product SKUs by Gross Volume (Horizontal Bar Leaderboard).

### View 2: Data Marts Grid (`#view_data`)
- **Purpose**: In-depth tabular inspection of in-memory Kimball dimensional tables.
- **Entry Point**: Nav tab `[ 📑 Data Marts Grid ]`.
- **Primary Elements**:
  - Table switcher pills (`orders` [FACT], `customers` [DIM], `products` [DIM], `dim_date` [DIM], `payments`, `returns`, etc.).
  - Search input for live sub-string row filtering.
  - Export CSV button (`#btnExportCurrentTableCSV`).
  - Active table metadata strip (row count, column count, table type).
  - Virtualized/scrollable data table with sticky header and sortable columns.

### View 3: Star Schema Model (`#view_model`)
- **Purpose**: Visual validation of dimensional integrity, referential constraints, and cardinality.
- **Entry Point**: Nav tab `[ 🕸️ Star Schema Model ]`.
- **Primary Elements**:
  - Model summary badge (count of Fact tables, Dimension tables, active relationships).
  - Schema diagram canvas containing interactive table cards.
  - Table card indicators for Primary Keys (`PK`) and Foreign Keys (`FK`).
  - Live SVG connector wires showing `1 : *` relationships with interactive tooltip inspector.

### View 4: DAX Measures Catalog (`#view_dax`)
- **Purpose**: Exploration, synthesis, clipboard copying, and live testing of synthesized business logic.
- **Entry Point**: Nav tab `[ ⚡ DAX Measures ]`.
- **Primary Elements**:
  - DAX formula tester bar (fx badge, measure picker, syntax editor, `▶ Run DAX` button, live result badge).
  - Category selector pills (`Volume & Counts`, `Core Metrics`, `Time Intelligence`, etc.).
  - Search input for filtering measures by name or formula text.
  - Measures card grid with Fira Code syntax block, one-click copy button, description, and table destination tag.

### Modal: Pipeline Ingestion Progress (`#pipelineModal`)
- **Purpose**: Real-time feedback during Excel parsing, dimensional decomposition, and file compilation.
- **Entry Point**: Triggered by `[ Sample Data ]`, `[ Import Excel / CSV ]`, or drag-and-drop.
- **Primary Elements**: Animated progress bar (0–100%), stage descriptions, and real-time streaming terminal log.

---

## 3. Core User Flow Maps

### Flow 1: Ingest & Evaluate Transactional Excel (Primary User Task)
1. **Launch App**: App displays dashboard shell instantly (<1s). Preloaded baseline or empty state shows clear primary action: `[ Sample Data ]` or `[ Import Excel / CSV ]`.
2. **Select Workbook**: Native file dialog opens (or user drags file into window).
3. **Pipeline Execution**: Progress modal appears showing real-time stages (10% Profiling, 35% Kimball Schema, 65% DAX Synthesis, 100% Complete).
4. **Instant Dashboard Reveal**: Modal closes; KPI cards and 4 charts populate dynamically with the newly ingested data.
5. **Cross-Filtering**: User clicks a category pill or doughnut chart slice; all metrics recalculate within 16ms without layout shift.

### Flow 2: Inspect & Export Clean Data Marts
1. **Navigate to Data View**: User clicks `[ 📑 Data Marts Grid ]` in header.
2. **Select Mart**: User selects `products` or `orders` pill.
3. **Filter Records**: User types into the search bar (e.g. `Smart`); rows filter instantly.
4. **Sort Columns**: User clicks a column header; rows sort ascending/descending.
5. **Export Mart**: User clicks `[ Export CSV ]`; native save dialog exports the mart to disk.

### Flow 3: Verify Star Schema & Export Native Power BI
1. **Navigate to Model View**: User clicks `[ 🕸️ Star Schema Model ]`.
2. **Review Topology**: Central Fact card (`orders`) is highlighted with amber border; Dimension cards surround it.
3. **Verify Constraints**: User inspects relationship wires (`1 : *`); clicks connector to confirm zero orphan keys.
4. **Compile Template**: User clicks `[ 🚀 Export .PBIT ]` in header; native Power BI template is compiled and launched.

### Flow 4: DAX Business Logic Audit & Clipboard Copy
1. **Navigate to DAX Catalog**: User clicks `[ ⚡ DAX Measures ]`.
2. **Search Formula**: User types `Growth` or selects `Time Intelligence` pill.
3. **Copy Expression**: User clicks `[ Copy ]` on `[Revenue Growth MoM %]`; button shows `✓ Copied` feedback.
4. **Ad-Hoc DAX Test**: User clicks `Test in Editor ▶`, edits formula, clicks `▶ Run DAX`; evaluated value appears instantly.

---

## 4. Problem Inventory & Gap Analysis

| Screen / Area | Problem Found | Severity | Category | Remediation |
|---|---|---|---|---|
| **Global Shell** | Missing light theme mode (only dark mode available). Analysts in bright office environments need light mode option. | Major | Theme / A11y | Add system-aware theme token set (`data-theme="light"` / `"dark"`) with manual toggle. |
| **Global Shell** | Keyboard shortcuts for rapid view switching and actions (Ctrl+1..4, Ctrl+O, Ctrl+E, Esc) are not documented or wired. | Major | Keyboard / A11y | Implement global keyboard handler (`Ctrl+1..4` view navigation, `Ctrl+O` import, `Esc` dismiss modal, `/` focus search). Document in UI. |
| **Slicer Bar** | Preset quick date buttons (e.g. "Last 30 Days", "YTD", "Full Range") are missing; user has to click native date inputs. | Minor | UX / Speed | Add quick date range chips (`YTD`, `2024`, `2025`, `All Time`) next to date inputs. |
| **Data View** | Large tables (10,000+ rows) can cause DOM bloat if rendered all at once without pagination or row limit. | Major | Performance | Add client-side windowing/pagination controls (e.g. 50 / 100 / 250 rows per page with page stepper). |
| **Model View** | Relationship lines currently calculate midpoint offsets; if cards wrap on smaller screens, wires can cross awkwardly. | Minor | Layout / Visual | Use orthogonal or clean cubic bezier anchor ports (right edge to left edge) with card dragging/positioning logic. |
| **DAX Measures** | New measure creation button is not directly accessible on the DAX view (must be done in sandbox). | Minor | UX / Workflow | Add `[ + New Measure ]` action button next to `[ Copy All DAX ]`. |
| **Accessibility** | Focus visible rings on pills and cards need higher contrast outline for keyboard tab navigation. | Major | A11y | Add high-contrast `:focus-visible` styling (`outline: 2px solid var(--border-focus); outline-offset: 2px`). |

---

## 5. What Currently Works and Must Be Kept

1. **Reactive Dynamic State Engine (`frontend/modules/state.js`)**:
   - `getFilteredData()` dynamic calculation engine calculates revenue, profit, margin %, orders, units, AOV, MoM growth, and return rates on-the-fly. Must be preserved intact.
2. **Four Clean Views Architecture**:
   - The 4-tab top navigation (`Executive Dashboard`, `Data Marts Grid`, `Star Schema Model`, `DAX Measures`) is clean, intuitive, and frees up all vertical space.
3. **Fast Python Compilation Pipeline**:
   - Subprocess execution (`backend/engine/core.py`) completes full parsing, schema decomposition, 69 DAX measures, and 9 charts in 5 seconds.
4. **All 123 Automated Tests**:
   - Full test suite passes 100% across API, pipeline, core calculations, forecasting, and schema decomposition.

---

## 6. Technical Constraints

- **Electron Security**: Must retain `contextIsolation: true`, `nodeIntegration: false`, `sandbox: false` with typed `contextBridge` methods.
- **CSP**: No external fonts or scripts from remote origins should block offline startup.
- **Chart.js Lifecycle**: Must destroy previous chart instances before rebuilding to prevent memory leaks and canvas flickering.
- **Localhost Binding**: Python API binds strictly to `127.0.0.1`.

---

## 7. Phase 1 Audit Conclusion

The application's core engine is robust, fast, and feature-complete. The recent simplification removed the bloated, fake Power BI ribbon and replaced it with a modern, high-aesthetic layout. 

To reach production excellence per `AGENTS.md`:
1. Formalize the compact token design system with light and dark mode variants (`docs/design-system.md`).
2. Implement system light/dark theme toggle and high-contrast `:focus-visible` states.
3. Add full keyboard navigation (`Ctrl+1..4`, `Ctrl+O`, `Esc`, `/`).
4. Add pagination to the Data Marts table explorer for performance on massive workbooks.
5. Add quick date preset pills (`All Time`, `2024`, `2025`, `YTD`).
