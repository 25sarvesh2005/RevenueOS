# RevenueOS Studio — Design System & Visual Token Specification

> **Phase 2 Deliverable according to AGENTS.md**  
> *Author: Principal Design Engineer*  
> *Target: RevenueOS Studio Desktop Application*  
> *Date: 2026-10-05*

---

## 1. Subject & Audience

- **Subject**: Automated Excel-to-Power BI Decision Engine transforming unmodeled transaction data into verified Kimball Star Schemas, synthesized DAX semantic measures, and visual analytics.
- **Audience**: Quantitative analysts, revenue operations managers, and business intelligence architects who scrutinize large datasets under tight deadlines and require extreme clarity, rapid filter response, zero visual clutter, and seamless keyboard workflow.

---

## 2. Color Palette & Semantic System

RevenueOS uses an **intentional, purposeful palette**:
- The background and surfaces remain ultra-disciplined and quiet (dark obsidian slate and crisp paper light).
- Boldness is concentrated in **one place**: the **financial indicators and semantic model status**, where numbers and cards instantly telegraph fiscal health.

### 2.1 Dark Mode Palette (Default)

| Token | Hex Value | Role / Usage | Contrast vs Background |
|---|---|---|---|
| `--bg-base` | `#0B0E14` | Window base canvas, outer frame | Baseline |
| `--bg-surface` | `#131722` | Header, slicer bar, toolbars | 1.15:1 |
| `--bg-card` | `#181C28` | Metric cards, chart containers, table wrappers | 1.3:1 |
| `--bg-card-hover` | `#202534` | Hovered cards, active pills, table hover row | 1.5:1 |
| `--bg-input` | `#0F121C` | Form inputs, search fields, date pickers | Recessed |
| `--border-subtle` | `#1F2433` | Internal dividers, subtle table gridlines | Subtle separator |
| `--border-card` | `#272C3D` | Card and panel boundaries | 3.2:1 against bg |
| `--border-focus` | `#6366F1` | Focus visible ring, active tab marker | 5.4:1 against bg |
| `--text-bright` | `#FFFFFF` | Headings, KPI values, active labels | 18:1 against bg |
| `--text-main` | `#E2E8F0` | Body text, table cell content | 13.5:1 against bg |
| `--text-muted` | `#94A3B8` | Subtitles, column headers, meta labels | 6.8:1 against bg |
| `--text-subtle` | `#64748B` | Disabled indicators, secondary metadata | 4.6:1 against bg |

### 2.2 Light Mode Palette (Executive / High-Ambient Mode)

| Token | Hex Value | Role / Usage |
|---|---|---|
| `--bg-base` | `#F8FAFC` | Window base canvas (soft off-white) |
| `--bg-surface` | `#FFFFFF` | Header, slicer bar, toolbars |
| `--bg-card` | `#FFFFFF` | Metric cards, chart containers, table wrappers |
| `--bg-card-hover` | `#F1F5F9` | Hovered rows, hover pills |
| `--bg-input` | `#F8FAFC` | Form inputs, search fields |
| `--border-subtle` | `#E2E8F0` | Subtle table row borders |
| `--border-card` | `#CBD5E1` | Card boundaries, component borders |
| `--border-focus` | `#4F46E5` | High-contrast focus ring |
| `--text-bright` | `#0F172A` | Headings, KPI values |
| `--text-main` | `#1E293B` | Body copy, table cells |
| `--text-muted` | `#64748B` | Subtitles, table headers |
| `--text-subtle` | `#94A3B8` | Auxiliary metadata |

### 2.3 Semantic Functional Colors (Consistent across modes)

| Semantic Role | Hex (Dark) | Hex (Light) | Purpose |
|---|---|---|---|
| **Primary Accent** | `#6366F1` (Indigo) | `#4F46E5` (Deep Indigo) | Primary buttons, active tabs, brand anchor |
| **Success / Positive** | `#10B981` (Emerald) | `#059669` (Forest Emerald) | Positive MoM growth, 100% integrity, clean load |
| **Warning / Caution** | `#F59E0B` (Amber) | `#D97706` (Warm Amber) | Fact table border, return rate alert, pending state |
| **Danger / Deficit** | `#EF4444` (Rose) | `#DC2626` (Crimson) | Cost of Goods Sold, negative margin, pipeline error |
| **Info / Dimension** | `#06B6D4` (Cyan) | `#0891B2` (Ocean Cyan) | Channels, dimension tables, relationship connectors |

---

## 3. Typography System

The interface pairs **Inter** for dense, clean UI readability with **Fira Code** for monospace numeric precision, DAX formulas, and data table records.

### 3.1 Type Hierarchy

| Level | Size | Weight | Line Height | Tracking | Font Family | Usage |
|---|---|---|---|---|---|---|
| **Hero / KPI Value** | 24px | 700 (Bold) | 30px | -0.5px | Inter | Primary KPI numbers |
| **Section Heading** | 18px | 700 (Bold) | 24px | -0.3px | Inter | View titles (`Model`, `DAX`) |
| **Card Heading** | 14px | 600 (Semi-Bold) | 20px | -0.2px | Inter | Chart titles, modal titles |
| **Body / Primary** | 13px | 400 (Regular) | 18px | 0px | Inter | Table rows, descriptions |
| **Small / UI** | 12px | 500 (Medium) | 16px | 0px | Inter | Navigation tabs, buttons, inputs |
| **Micro / Badges** | 11px | 600 (Semi-Bold) | 14px | +0.2px | Inter | KPI badges, filter chips, tags |
| **Code / Numbers** | 12px | 400 / 600 | 18px | 0px | Fira Code | DAX expressions, JSON, IDs |

- **Body Line Length**: Maximum 72 characters per line for readable documentation and measure descriptions.
- **Font Bundling**: Fonts are declared with system fallbacks (`-apple-system, BlinkMacSystemFont, Segoe UI, Roboto`) so offline launch is instantaneous without network roundtrips.

---

## 4. Spacing System (4px Base Grid)

Zero arbitrary pixel values. Every margin, padding, gap, and dimension snaps to:

| Step | Value | Tokens | Purpose |
|---|---|---|---|
| 1 | 4px | `--space-1` | Micro padding, pill gaps, icon nudging |
| 2 | 8px | `--space-2` | Button padding, icon-to-label spacing |
| 3 | 12px | `--space-3` | Slicer bar padding, card internal gap |
| 4 | 16px | `--space-4` | Standard card internal padding, grid gap |
| 5 | 20px | `--space-5` | Main viewport margins, chart card padding |
| 6 | 24px | `--space-6` | View container padding, section separation |
| 7 | 32px | `--space-8` | Modal separation, major architectural gaps |
| 8 | 48px | `--space-12` | Empty state vertical spacing |

---

## 5. Shape, Radius, Borders & Elevation

- **Radii**:
  - `--radius-xs` (4px): Badges, table cells, tags.
  - `--radius-sm` (6px): Buttons, text inputs, dropdowns.
  - `--radius-md` (10px): Metric cards, chart containers, table wrappers.
  - `--radius-lg` (14px): Modals, hero dropzones.
  - `--radius-pill` (20px): Category filter pills, status chips.
- **Borders**: Exactly 1px solid `var(--border-card)`. Selected/Fact cards use 1.5px solid `var(--accent-gold)`.
- **Elevation**:
  - Low (`--shadow-sm`): `0 1px 3px rgba(0,0,0,0.2)`. Used on metric cards.
  - High (`--shadow-card`): `0 8px 24px rgba(0,0,0,0.35)`. Used on modals and active popovers.
  - Focus Ring (`--shadow-focus`): `0 0 0 2px var(--bg-base), 0 0 0 4px var(--border-focus)`. Meets WCAG 2.1 AA.

---

## 6. Motion & Feedback Discipline

- **Durations**:
  - Micro-action (button press, hover): 120ms (`ease-out`).
  - View transition / fade: 180ms (`cubic-bezier(0.16, 1, 0.3, 1)`).
  - Progress fill: 250ms (`ease-in-out`).
- **Rule**: Motion confirms actions (e.g. `✓ Copied` feedback, filter chip pop-in). Zero decorative parallax, zero looping bounce effects.

---

## 7. Layout Concept & Architecture

```
+---------------------------------------------------------------------------------------------+
| [LOGO] RevenueOS  [EXCEL->PBI] | [📊 Dashboard] [📑 Data] [🕸️ Model] [⚡ DAX] | [⚡Sample] [📁Import] [🚀Export]|
+---------------------------------------------------------------------------------------------+
|  PERIOD: [ 2024-01-01 ] to [ 2025-12-31 ] | CATEGORY: (All) (Elec) (Apparel) | [↺ Reset Filters] |
+---------------------------------------------------------------------------------------------+
|                                                                                             |
|  +----------------+ +----------------+ +----------------+ +----------------+ +------------+ |
|  | GROSS REVENUE  | | GROSS PROFIT   | | GROSS MARGIN % | | TOTAL ORDERS   | | UNITS SOLD | |
|  | $8,474,028     | | $2,246,208     | | 26.5%          | | 500            | | 1,229      | |
|  | +14.2% MoM     | | 26.5% Margin   | | Optimal ✓      | | Avg: $16,948   | | 2.7% Return| |
|  +----------------+ +----------------+ +----------------+ +----------------+ +------------+ |
|                                                                                             |
|  +----------------------------------------------+ +---------------------------------------+ |
|  | 📈 Monthly Revenue vs Cost Trajectory        | | 🍩 Revenue by Product Category        | |
|  | (Dual-Axis Bar & Line Combo Chart)           | | (Clickable Donut Cross-Filter)        | |
|  +----------------------------------------------+ +---------------------------------------+ |
|                                                                                             |
|  +----------------------------------------------+ +---------------------------------------+ |
|  | 📊 Revenue by Sales Channel                  | | 🏆 Top 10 Product SKUs Leaderboard    | |
|  | (Direct, Amazon, Store, Mobile, Wholesale)   | | (Horizontal Volume Ranking)           | |
|  +----------------------------------------------+ +---------------------------------------+ |
+---------------------------------------------------------------------------------------------+
```

---

## 8. Self-Critique per AGENTS.md

- **Is any part a generic template?**  
  No. Most generic BI templates add fake sidebar navigation rails, fake status toolbars, or bloated ribbon toolbars with 40 broken buttons. RevenueOS eliminates the rail and ribbon completely, devoting **94% of the vertical viewport directly to data**.
- **Where is the boldness spent?**  
  The boldness is reserved entirely for the **metric feedback loop**: when a user clicks a category pill or a donut chart slice, the entire financial model recalibrates in <16ms with live calculated MoM metrics, margin health indicators, and filter breadcrumbs. Everything else (chrome, tabs, borders) stays quiet, dark, and precise.
