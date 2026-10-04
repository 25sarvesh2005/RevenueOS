/**
 * RevenueOS Studio – Dialogs, Modals & Native Shell Integrations
 * ===============================================================
 * Handles Power Query M viewer, Custom Measure creator, Matplotlib gallery,
 * Focus Mode viewer, and Power BI / File Explorer shell launchers.
 */

import { showToast } from "./toast.js";

export function openPowerQueryModal(state) {
  const modal = document.getElementById("powerQueryModal");
  const block = document.getElementById("pqCodeBlock");
  if (!modal || !block) return;

  const tables = state.currentManifest?.tables || [];
  let code = "// RevenueOS Generated Power Query M Script\n// Kimball Star Schema Marts\n\n";

  tables.forEach((tbl) => {
    code += `shared ${tbl.name} = let\n`;
    code += `    Source = Csv.Document(File.Contents("csv/${tbl.csv_filename || tbl.name + '.csv'}"), [Delimiter=",", Encoding=65001]),\n`;
    code += `    #"Promoted Headers" = Table.PromoteHeaders(Source, [PromoteAllScalars=true])\n`;
    code += `in\n    #"Promoted Headers";\n\n`;
  });

  block.textContent = code;
  modal.style.display = "flex";
}

export function openNewMeasureModal() {
  const modal = document.getElementById("newMeasureModal");
  if (modal) modal.style.display = "flex";
}

export function confirmCreateMeasure(state, onMeasureCreated) {
  const nameInput = document.getElementById("newMeasureNameInput");
  const exprInput = document.getElementById("newMeasureExprInput");
  if (!nameInput || !exprInput) return;

  const name = nameInput.value.trim();
  const expr = exprInput.value.trim();
  if (!name || !expr) {
    showToast("Please provide both a Measure Name and DAX Expression.", "warning");
    return;
  }

  if (!state.currentManifest) state.currentManifest = { measures: [] };
  if (!state.currentManifest.measures) state.currentManifest.measures = [];

  state.currentManifest.measures.unshift({
    name: name,
    expression: expr,
    category: "User Custom",
    description: "Custom measure added in RevenueOS Studio",
  });

  if (typeof onMeasureCreated === "function") {
    onMeasureCreated(name);
  }

  const modal = document.getElementById("newMeasureModal");
  if (modal) modal.style.display = "none";
  showToast(`Measure [${name}] created!`, "success");
}

export function openMatplotlibModal(state) {
  const modal = document.getElementById("matplotlibModal");
  const grid = document.getElementById("matplotlibGalleryGrid");
  if (!modal || !grid) return;

  const charts = state.currentManifest?.charts || [];
  grid.innerHTML = "";

  if (charts.length === 0) {
    grid.innerHTML = `<div style="grid-column: 1/-1; text-align: center; color: var(--pbi-text-muted); padding: 40px 0; font-size: 13px;">No Matplotlib charts compiled yet. Import or run an Excel workbook to automatically generate 300 DPI publication charts.</div>`;
  } else {
    charts.forEach((c) => {
      const card = document.createElement("div");
      card.style.background = "var(--pbi-surface-alt)";
      card.style.border = "1px solid var(--pbi-border)";
      card.style.borderRadius = "4px";
      card.style.padding = "10px";
      card.style.display = "flex";
      card.style.flexDirection = "column";
      card.style.gap = "8px";
      card.style.cursor = "pointer";
      card.style.transition = "transform 0.15s ease, border-color 0.15s ease";
      card.onmouseover = () => {
        card.style.borderColor = "var(--pbi-accent-blue)";
        card.style.transform = "translateY(-2px)";
      };
      card.onmouseout = () => {
        card.style.borderColor = "var(--pbi-border)";
        card.style.transform = "none";
      };

      const imgUri = (c.path || "").replace(/\\/g, "/");
      card.innerHTML = `
        <div style="font-weight: 600; font-size: 12px; color: var(--pbi-text-bright);">${c.title}</div>
        <div style="overflow: hidden; border-radius: 4px; background: #121212; height: 180px; display: flex; align-items: center; justify-content: center;">
          <img src="file:///${imgUri}" alt="${c.title}" style="max-width: 100%; max-height: 100%; object-fit: contain;" />
        </div>
        <div style="font-size: 10px; color: var(--pbi-text-muted);">${c.filename} • Click to open high-res</div>
      `;
      card.addEventListener("click", () => {
        if (window.api?.launchFile) {
          window.api.launchFile(c.path);
        } else {
          window.open(`file:///${imgUri}`, "_blank");
        }
      });
      grid.appendChild(card);
    });
  }

  modal.style.display = "flex";
}

export async function openChartsFolder(state) {
  const chartsDir = state.currentManifest?.paths?.chartsDir;
  if (chartsDir && window.api?.openFolder) {
    await window.api.openFolder(chartsDir);
  } else {
    showToast("Charts folder location is in the project output directory.", "info");
  }
}

export async function launchNativePowerBI(state) {
  const pbitPath = state.currentManifest?.paths?.pbitPath;
  if (pbitPath && window.api?.launchFile) {
    await window.api.launchFile(pbitPath);
    showToast("Launching Power BI Desktop Template (.pbit)...", "success");
  } else {
    showToast("Power BI template (.pbit) compiled in output directory.", "info");
  }
}

export async function exportCSVMarts(state) {
  const csvDir = state.currentManifest?.paths?.csvDir;
  if (csvDir && window.api?.openFolder) {
    await window.api.openFolder(csvDir);
    showToast("Opened CSV Marts directory", "info");
  } else {
    showToast("CSV data marts ready in output directory.", "info");
  }
}

export async function copyAllDAX(state) {
  const measures = state.currentManifest?.measures || [];
  let text = "// RevenueOS Studio Synthesized DAX Measures\n\n";
  measures.forEach((m) => {
    text += `[${m.name}] =\n${m.expression}\n\n`;
  });
  if (window.api?.copyToClipboard) {
    await window.api.copyToClipboard(text);
    showToast("All DAX measures copied to clipboard!", "success");
  } else {
    navigator.clipboard?.writeText(text);
    showToast("All DAX measures copied to clipboard!", "success");
  }
}

export function toggleFocus(containerId, state) {
  const target = document.getElementById(containerId);
  if (!target) return;

  const modal = document.getElementById("focusModeModal");
  const focusTitle = document.getElementById("focusModalTitle");
  const titleText = target.querySelector(".visual-title")?.textContent || "Visual Focus";
  if (focusTitle) focusTitle.textContent = `Focus Mode: ${titleText}`;

  if (modal) modal.style.display = "flex";

  setTimeout(() => {
    const ctx = document.getElementById("chartFocusCanvas")?.getContext("2d");
    if (ctx && window.Chart) {
      if (state.charts.focus) state.charts.focus.destroy();
      const data = state.getFilteredData();
      state.charts.focus = new window.Chart(ctx, {
        type: "bar",
        data: {
          labels: data.timeSeries.map((t) => t.period),
          datasets: [
            { label: "Revenue", data: data.timeSeries.map((t) => t.revenue), backgroundColor: "#118DFF" },
            { label: "COGS", data: data.timeSeries.map((t) => t.cost), backgroundColor: "#E66C37" },
          ],
        },
        options: { responsive: true, maintainAspectRatio: false },
      });
    }
  }, 50);
}

export function closeFocusMode(state) {
  const modal = document.getElementById("focusModeModal");
  if (modal) modal.style.display = "none";
  if (state.charts.focus) state.charts.focus.destroy();
}
