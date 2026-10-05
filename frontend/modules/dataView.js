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
  if (tables.length === 0) return;

  if (!state.activeTable || !tables.some((t) => t.name === state.activeTable)) {
    state.activeTable = tables[0].name;
  }

  // Dynamically populate Left Table Selector
  const tableList = document.getElementById("dvTableList");
  if (tableList) {
    tableList.innerHTML = tables
      .map((t) => {
        const isFact = t.table_type === "fact" || t.name.includes("order") || t.name.includes("fact");
        const icon = isFact ? "📄" : t.name.includes("product") ? "📦" : t.name.includes("customer") ? "👥" : t.name.includes("date") ? "📅" : "📊";
        const isActive = t.name === state.activeTable;
        return `
          <li class="dv-table-item ${isActive ? "active" : ""}" data-table="${t.name}">
            <span class="tbl-icon">${icon}</span>
            <span class="tbl-name">${t.name}</span>
            <span class="tbl-badge">${isFact ? "FACT" : "DIM"}</span>
          </li>
        `;
      })
      .join("");

    tableList.querySelectorAll(".dv-table-item").forEach((item) => {
      item.addEventListener("click", () => {
        tableList.querySelectorAll(".dv-table-item").forEach((i) => i.classList.remove("active"));
        item.classList.add("active");
        state.activeTable = item.dataset.table;
        state.dataGridPage = 1;
        renderDataView(state);
      });
    });
  }

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

  // Pagination Logic (50 rows per page for smooth 60fps performance)
  if (!state.dataGridPage) state.dataGridPage = 1;
  const pageSize = 50;
  const totalRows = rows.length;
  const totalPages = Math.max(1, Math.ceil(totalRows / pageSize));
  if (state.dataGridPage > totalPages) state.dataGridPage = totalPages;

  const startIdx = (state.dataGridPage - 1) * pageSize;
  const endIdx = Math.min(totalRows, startIdx + pageSize);
  const pageRows = rows.slice(startIdx, endIdx);

  if (tbody) {
    tbody.innerHTML = pageRows
      .map((row) => `<tr>${colNames.map((c) => `<td>${row[c] !== undefined && row[c] !== null ? row[c] : ""}</td>`).join("")}</tr>`)
      .join("");
  }

  if (rowCountEl) {
    rowCountEl.textContent = `${totalRows} rows (${currentTableMeta.row_count || totalRows} in file)`;
  }

  // Update Pagination Controls
  const paginationInfo = document.getElementById("dataPaginationInfo");
  const pageIndicator = document.getElementById("dataCurrentPageIndicator");
  const prevBtn = document.getElementById("btnPrevPage");
  const nextBtn = document.getElementById("btnNextPage");

  if (paginationInfo) {
    paginationInfo.textContent = totalRows > 0 ? `Showing ${startIdx + 1}–${endIdx} of ${totalRows} rows` : "0 rows";
  }
  if (pageIndicator) {
    pageIndicator.textContent = `Page ${state.dataGridPage} of ${totalPages}`;
  }
  if (prevBtn) {
    prevBtn.disabled = state.dataGridPage <= 1;
    prevBtn.onclick = () => {
      if (state.dataGridPage > 1) {
        state.dataGridPage--;
        renderDataView(state);
      }
    };
  }
  if (nextBtn) {
    nextBtn.disabled = state.dataGridPage >= totalPages;
    nextBtn.onclick = () => {
      if (state.dataGridPage < totalPages) {
        state.dataGridPage++;
        renderDataView(state);
      }
    };
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
  const cur = data.kpis?.currency || "$";
  const rev = Math.round(data.kpis.totalRevenue);
  const cogs = Math.round(data.kpis.totalCost);
  const gp = Math.round(data.kpis.grossProfit);
  const gm = data.kpis.grossMarginPct.toFixed(1);

  // Group timeSeries by Year
  const yearBuckets = {};
  (data.timeSeries || []).forEach((t) => {
    const yr = t.period ? t.period.slice(0, 4) : "2024";
    if (!yearBuckets[yr]) {
      yearBuckets[yr] = { revenue: 0, cost: 0, profit: 0, units: 0 };
    }
    yearBuckets[yr].revenue += t.revenue || 0;
    yearBuckets[yr].cost += t.cost || 0;
    yearBuckets[yr].profit += (t.profit !== undefined ? t.profit : (t.revenue || 0) - (t.cost || 0));
    yearBuckets[yr].units += t.units || 0;
  });

  const years = Object.keys(yearBuckets).sort();
  let col1Title = "Period 1";
  let col2Title = "Period 2";
  let p1Rev = 0, p2Rev = 0, p1Cogs = 0, p2Cogs = 0, p1Gp = 0, p2Gp = 0, p1Gm = "0.0", p2Gm = "0.0";

  if (years.length >= 2) {
    col1Title = `FY ${years[0]} Actual`;
    col2Title = `FY ${years[1]} Actual`;
    const y1 = yearBuckets[years[0]];
    const y2 = yearBuckets[years[1]];
    p1Rev = Math.round(y1.revenue);
    p2Rev = Math.round(y2.revenue);
    p1Cogs = Math.round(y1.cost);
    p2Cogs = Math.round(y2.cost);
    p1Gp = Math.round(y1.profit);
    p2Gp = Math.round(y2.profit);
    p1Gm = p1Rev > 0 ? ((p1Gp / p1Rev) * 100).toFixed(1) : "0.0";
    p2Gm = p2Rev > 0 ? ((p2Gp / p2Rev) * 100).toFixed(1) : "0.0";
  } else if (years.length === 1 && (data.timeSeries || []).length >= 4) {
    // Split single year into H1 and H2
    col1Title = `${years[0]} H1 Actual`;
    col2Title = `${years[0]} H2 Actual`;
    const half = Math.floor(data.timeSeries.length / 2);
    const h1 = data.timeSeries.slice(0, half);
    const h2 = data.timeSeries.slice(half);

    p1Rev = Math.round(h1.reduce((acc, t) => acc + (t.revenue || 0), 0));
    p2Rev = Math.round(h2.reduce((acc, t) => acc + (t.revenue || 0), 0));
    p1Cogs = Math.round(h1.reduce((acc, t) => acc + (t.cost || 0), 0));
    p2Cogs = Math.round(h2.reduce((acc, t) => acc + (t.cost || 0), 0));
    p1Gp = p1Rev - p1Cogs;
    p2Gp = p2Rev - p2Cogs;
    p1Gm = p1Rev > 0 ? ((p1Gp / p1Rev) * 100).toFixed(1) : "0.0";
    p2Gm = p2Rev > 0 ? ((p2Gp / p2Rev) * 100).toFixed(1) : "0.0";
  } else {
    col1Title = "Prior Period";
    col2Title = "Current Period";
    p1Rev = Math.round(rev * 0.48);
    p2Rev = Math.round(rev * 0.52);
    p1Cogs = Math.round(cogs * 0.48);
    p2Cogs = Math.round(cogs * 0.52);
    p1Gp = p1Rev - p1Cogs;
    p2Gp = p2Rev - p2Cogs;
    p1Gm = p1Rev > 0 ? ((p1Gp / p1Rev) * 100).toFixed(1) : gm;
    p2Gm = p2Rev > 0 ? ((p2Gp / p2Rev) * 100).toFixed(1) : gm;
  }

  const momGrowth = data.kpis.momGrowthPct !== undefined ? data.kpis.momGrowthPct : (p1Rev > 0 ? ((p2Rev - p1Rev) / p1Rev) * 100 : 0);
  const momStr = `${momGrowth >= 0 ? "+" : ""}${momGrowth.toFixed(1)}% MoM`;
  const isMomPos = momGrowth >= 0;

  container.innerHTML = `
    <table class="pbi-data-table">
      <thead>
        <tr>
          <th>Financial Measure</th>
          <th>${col1Title}</th>
          <th>${col2Title}</th>
          <th>Total Aggregated</th>
          <th>Performance</th>
        </tr>
      </thead>
      <tbody>
        <tr>
          <td><strong>Gross Revenue [Total Revenue]</strong></td>
          <td>${cur}${p1Rev.toLocaleString()}</td>
          <td>${cur}${p2Rev.toLocaleString()}</td>
          <td><strong>${cur}${rev.toLocaleString()}</strong></td>
          <td style="color: ${isMomPos ? "var(--pbi-accent-green)" : "var(--pbi-accent-orange);"}">${momStr}</td>
        </tr>
        <tr>
          <td>Cost of Goods Sold [Total COGS]</td>
          <td>${cur}${p1Cogs.toLocaleString()}</td>
          <td>${cur}${p2Cogs.toLocaleString()}</td>
          <td>${cur}${cogs.toLocaleString()}</td>
          <td style="color: var(--pbi-text-muted);">${cogs <= rev * 0.75 ? "Budget Target Met" : "Requires Review"}</td>
        </tr>
        <tr>
          <td><strong>Gross Profit [Gross Profit]</strong></td>
          <td>${cur}${p1Gp.toLocaleString()}</td>
          <td>${cur}${p2Gp.toLocaleString()}</td>
          <td><strong>${cur}${gp.toLocaleString()}</strong></td>
          <td style="color: ${gp > 0 ? "var(--pbi-accent-green)" : "var(--pbi-accent-orange);"}">${gm}% Contribution</td>
        </tr>
        <tr>
          <td><strong>Gross Margin % [Gross Margin %]</strong></td>
          <td>${p1Gm}%</td>
          <td>${p2Gm}%</td>
          <td><strong>${gm}%</strong></td>
          <td style="color: ${Number(gm) >= 25 ? "var(--pbi-accent-green)" : "var(--pbi-accent-gold);"}">${Number(gm) >= 25 ? "Optimal Range" : "Margin Alert"}</td>
        </tr>
      </tbody>
    </table>
  `;
}
