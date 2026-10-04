/**
 * RevenueOS Studio – Data View & Table Explorer Module
 * ====================================================
 * Renders sortable/filterable data grids, financial actuals matrix,
 * and handles CSV table exports.
 */

import { showToast } from "./toast.js";

export function renderDataView(state) {
  const tableInfo = document.getElementById("dgTableInfo");
  const thead = document.getElementById("dataGridHead");
  const tbody = document.getElementById("dataGridBody");
  const rowCountEl = document.getElementById("dataGridRowCount");

  const tables = state.currentManifest?.tables || [];
  const currentTableMeta = tables.find((t) => t.name === state.activeTable) || tables[0];
  if (!currentTableMeta) return;

  if (tableInfo) {
    tableInfo.innerHTML = `Table: <strong>${currentTableMeta.name}</strong> (${currentTableMeta.table_type?.toUpperCase() || "TABLE"}) · ${currentTableMeta.row_count || 0} rows`;
  }

  const cols = currentTableMeta.columns || [];
  const colNames = cols.map((c) => (typeof c === "string" ? c : c.name));

  // Sortable Headers
  if (thead) {
    thead.innerHTML = `<tr>${colNames
      .map((c) => {
        let sortIcon = "";
        if (state.sortConfig.col === c) sortIcon = state.sortConfig.desc ? " ▼" : " ▲";
        return `<th style="cursor:pointer;" data-column="${c}">${c}${sortIcon}</th>`;
      })
      .join("")}</tr>`;

    thead.querySelectorAll("th").forEach((th) => {
      th.addEventListener("click", () => sortTable(th.dataset.column, state));
    });
  }

  let rows = [...(currentTableMeta.preview_rows || [])];

  // Apply Sorting
  if (state.sortConfig.col) {
    const col = state.sortConfig.col;
    const isDesc = state.sortConfig.desc;
    rows.sort((a, b) => {
      const valA = a[col] !== undefined ? a[col] : "";
      const valB = b[col] !== undefined ? b[col] : "";
      if (typeof valA === "number" && typeof valB === "number") {
        return isDesc ? valB - valA : valA - valB;
      }
      return isDesc ? String(valB).localeCompare(String(valA)) : String(valA).localeCompare(String(valB));
    });
  }

  if (tbody) {
    tbody.innerHTML = rows
      .map((row) => `<tr>${colNames.map((c) => `<td>${row[c] !== undefined && row[c] !== null ? row[c] : ""}</td>`).join("")}</tr>`)
      .join("");
  }

  if (rowCountEl) {
    rowCountEl.textContent = `Displaying ${rows.length} records in memory`;
  }
}

export function sortTable(colName, state) {
  if (state.sortConfig.col === colName) {
    state.sortConfig.desc = !state.sortConfig.desc;
  } else {
    state.sortConfig.col = colName;
    state.sortConfig.desc = false;
  }
  renderDataView(state);
}

export function filterDataGrid(query) {
  const q = query.toLowerCase();
  const rows = document.querySelectorAll("#dataGridBody tr");
  rows.forEach((r) => {
    r.style.display = r.textContent.toLowerCase().includes(q) ? "" : "none";
  });
}

export async function exportCurrentTableCSV(state) {
  const tables = state.currentManifest?.tables || [];
  const currentTable = tables.find((t) => t.name === state.activeTable) || tables[0];
  if (!currentTable) return;

  const cols = currentTable.columns.map((c) => (typeof c === "string" ? c : c.name));
  const rows = currentTable.preview_rows || [];

  let csv = cols.join(",") + "\n";
  rows.forEach((r) => {
    csv += cols.map((c) => `"${(r[c] !== undefined ? String(r[c]) : "").replace(/"/g, '""')}"`).join(",") + "\n";
  });

  if (window.api?.saveCSV) {
    const savedPath = await window.api.saveCSV({ defaultName: `${currentTable.name}.csv`, content: csv });
    if (savedPath) showToast(`Exported to ${savedPath}`, "success");
  } else {
    const blob = new Blob([csv], { type: "text/csv" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `${currentTable.name}.csv`;
    a.click();
    showToast(`Downloaded ${currentTable.name}.csv`, "success");
  }
}

export function renderFinancialTable(state) {
  const container = document.getElementById("financialSummaryTable");
  if (!container) return;

  const data = state.getFilteredData();
  const rev = Math.round(data.kpis.totalRevenue);
  const cogs = Math.round(data.kpis.totalCost);
  const gp = Math.round(data.kpis.grossProfit);
  const gm = data.kpis.grossMarginPct.toFixed(1);

  container.innerHTML = `
    <table class="pbi-data-table">
      <thead>
        <tr>
          <th>Financial Measure</th>
          <th>FY 2024 Actual</th>
          <th>FY 2025 Actual</th>
          <th>Total Aggregated</th>
          <th>Performance</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td><strong>Gross Revenue [Total Revenue]</strong></td>
          <td>$4,785,124</td>
          <td>$3,688,904</td>
          <td><strong>$${rev.toLocaleString()}</strong></td>
          <td style="color: var(--pbi-accent-green);">+14.2% MoM</td>
        </tr>
        <tr>
          <td>Cost of Goods Sold [Total COGS]</td>
          <td>$3,514,200</td>
          <td>$2,713,620</td>
          <td>$${cogs.toLocaleString()}</td>
          <td style="color: var(--pbi-text-muted);">Budget Target Met</td>
        </tr>
        <tr>
          <td><strong>Gross Profit [Gross Profit]</strong></td>
          <td>$1,270,924</td>
          <td>$975,284</td>
          <td><strong>$${gp.toLocaleString()}</strong></td>
          <td style="color: var(--pbi-accent-green);">+18.7% Margin Contrib</td>
        </tr>
        <tr>
          <td><strong>Gross Margin % [Gross Margin %]</strong></td>
          <td>26.6%</td>
          <td>26.4%</td>
          <td><strong>${gm}%</strong></td>
          <td style="color: var(--pbi-accent-gold);">Optimal Range</td>
        </tr>
      </tbody>
    </table>
  `;
}
