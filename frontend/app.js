/**
 * RevenueOS Studio – Modern Application Orchestrator
 * ====================================================
 * High-performance, clean controller coordinating:
 * - Reactive state store (modules/state.js)
 * - Executive dashboard & Chart.js visualizations (modules/charts.js)
 * - Data Marts grid explorer (modules/dataView.js)
 * - Kimball Star Schema topology (modules/modelView.js)
 * - DAX Semantic Layer & Evaluator (modules/daxEngine.js)
 * - Slicers & Dynamic Cross-Filtering (modules/slicers.js)
 * - Automated Excel ingestion pipeline (modules/pipeline.js)
 * - Native Power BI export & toasts (modules/modals.js, modules/toast.js)
 */

import { state } from "./modules/state.js";
import { showToast } from "./modules/toast.js";
import {
  renderCharts,
  renderStatisticalGallery,
  selectVisual,
} from "./modules/charts.js";
import {
  renderDataView,
  filterDataGrid,
  exportCurrentTableCSV,
} from "./modules/dataView.js";
import {
  renderModelView,
  drawModelRelationships,
} from "./modules/modelView.js";
import {
  populateDAXMeasures,
  updateDAXFormula,
  evaluateDAX,
  saveDAX,
  copyAllDAX,
  renderDaxCatalog,
} from "./modules/daxEngine.js";
import {
  setCategoryFilter,
  setChannelFilter,
  resetFilters,
  applySlicerFilters,
  populateSlicers,
} from "./modules/slicers.js";
import {
  refreshData,
  selectAndRunExcel,
  runSamplePipeline,
  runPipelineForPath,
  updateProgress,
  appendLog,
} from "./modules/pipeline.js";
import {
  launchNativePowerBI,
  exportCSVMarts,
} from "./modules/modals.js";

// Theme Manager
export function toggleTheme() {
  const currentTheme = document.body.dataset.theme || "dark";
  const newTheme = currentTheme === "dark" ? "light" : "dark";
  document.body.dataset.theme = newTheme;
  document.body.className = `revenueos-${newTheme}`;
  const icon = document.getElementById("themeToggleIcon");
  if (icon) icon.textContent = newTheme === "dark" ? "🌙" : "☀️";
  try {
    localStorage.setItem("revenueos_theme", newTheme);
  } catch (e) {}
  renderCharts(state);
}

export function loadSavedTheme() {
  try {
    const saved = localStorage.getItem("revenueos_theme") || "dark";
    document.body.dataset.theme = saved;
    document.body.className = `revenueos-${saved}`;
    const icon = document.getElementById("themeToggleIcon");
    if (icon) icon.textContent = saved === "dark" ? "🌙" : "☀️";
  } catch (e) {}
}

// Switch between the 4 primary views
export function switchView(viewName) {
  state.activeView = viewName;

  document.querySelectorAll(".nav-tab-btn").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.view === viewName);
  });

  document.querySelectorAll(".app-view").forEach((v) => {
    v.classList.remove("active");
  });

  const activeViewEl = document.getElementById(`view_${viewName}`);
  if (activeViewEl) {
    activeViewEl.classList.add("active");
  }

  // Trigger view-specific rendering
  if (viewName === "dashboard") {
    renderCharts(state);
  } else if (viewName === "data") {
    renderDataView(state);
  } else if (viewName === "model") {
    renderModelView(state);
    setTimeout(() => drawModelRelationships(state), 120);
  } else if (viewName === "dax") {
    renderDaxCatalog(state);
    populateDAXMeasures(state);
  }
}

// Update live metric summary chip in header / filter bar
export function updateSummaryChip(state) {
  const chip = document.getElementById("dashboardFilterSummary");
  if (!chip) return;

  const data = state.getFilteredData();
  const rev = Math.round(data.kpis?.totalRevenue || 0);
  const orders = data.kpis?.totalOrders || 0;
  const cur = data.kpis?.currency || "$";

  let statusText = `⚡ ${orders.toLocaleString()} Orders · ${cur}${rev.toLocaleString()}`;
  if (state.activeCategoryFilter !== "ALL" || state.activeChannelFilter !== "ALL") {
    statusText = `Filtered: ${orders.toLocaleString()} Orders · ${cur}${rev.toLocaleString()}`;
  }
  chip.innerHTML = `<span>${statusText}</span>`;
}

export let dashboardSubMode = "interactive";

export function switchDashboardSubMode(mode) {
  dashboardSubMode = mode;
  document.querySelectorAll(".mode-pill").forEach((btn) => {
    btn.classList.toggle("active", btn.dataset.mode === mode);
  });

  const interactiveSection = document.getElementById("interactiveChartsSection");
  const statisticalSection = document.getElementById("statisticalGallerySection");
  const modeInfo = document.getElementById("dashboardModeInfo");
  const slicerBar = document.getElementById("canvasSlicerBar");

  if (mode === "interactive") {
    if (interactiveSection) interactiveSection.style.display = "grid";
    if (statisticalSection) statisticalSection.style.display = "none";
    if (slicerBar) slicerBar.style.display = "flex";
    if (modeInfo) modeInfo.textContent = "Interactive cross-filtering with Chart.js";
    renderCharts(state);
  } else {
    if (interactiveSection) interactiveSection.style.display = "none";
    if (statisticalSection) statisticalSection.style.display = "grid";
    if (slicerBar) slicerBar.style.display = "none";
    if (modeInfo) modeInfo.textContent = "High-resolution econometric charts generated by Python engine";
    renderStatisticalGallery(state);
  }
}

// Refresh all views when a new dataset or filter changes
export function refreshAllViews() {
  const emptyState = document.getElementById("canvasEmptyState");
  const mainContent = document.getElementById("canvasMainContent");

  if (emptyState && mainContent) {
    if (!state.currentManifest) {
      emptyState.style.display = "block";
      mainContent.style.display = "none";
    } else {
      emptyState.style.display = "none";
      mainContent.style.display = "block";
    }
  }

  // Update Statistical Pack Badge
  const statBadge = document.getElementById("statisticalBadge");
  if (statBadge) {
    const count = state.currentManifest?.charts?.length || 9;
    statBadge.textContent = `${count} Charts`;
  }

  // Populate dynamic slicers
  populateSlicers(state.currentManifest, state, () => {
    renderCharts(state);
    updateSummaryChip(state);
  });

  // Render active view
  if (!state.activeView || state.activeView === "dashboard") {
    if (dashboardSubMode === "statistical") {
      renderStatisticalGallery(state);
    } else {
      renderCharts(state);
    }
  } else if (state.activeView === "data") {
    renderDataView(state);
  } else if (state.activeView === "model") {
    renderModelView(state);
  } else if (state.activeView === "dax") {
    renderDaxCatalog(state);
  }

  // Populate DAX editor dropdown
  populateDAXMeasures(state);
  updateSummaryChip(state);

  // Update document title if present
  const docTitle = document.getElementById("documentTitle");
  if (docTitle && state.currentManifest?.projectName) {
    docTitle.textContent = `${state.currentManifest.projectName} · Star Schema Studio`;
  }
}

export const app = {
  state,
  init,
  toggleTheme,
  loadSavedTheme,
  refreshAllViews,
  switchView,
  switchDashboardSubMode,
  updateSummaryChip,

  // DAX Semantic Operations
  evaluateDAX: () => evaluateDAX(state),
  saveDAX: () => saveDAX(state),
  copyAllDAX: () => copyAllDAX(state),
  updateDAXFormula: (name) => updateDAXFormula(name, state),

  // Slicer Cross-Filtering
  setCategoryFilter: (cat) =>
    setCategoryFilter(cat, state, () => {
      renderCharts(state);
      updateSummaryChip(state);
    }),
  setChannelFilter: (chan) =>
    setChannelFilter(chan, state, () => {
      renderCharts(state);
      updateSummaryChip(state);
    }),
  resetFilters: () =>
    resetFilters(state, () => {
      renderCharts(state);
      updateSummaryChip(state);
    }),

  // Ingestion Pipeline
  selectAndRunExcel: () => selectAndRunExcel(state, () => refreshAllViews()),
  runSamplePipeline: () => runSamplePipeline(state, () => refreshAllViews()),
  runPipelineForPath: (path, proj) => runPipelineForPath(path, proj, state, () => refreshAllViews()),
  refreshData: () =>
    refreshData(state, () => {
      renderCharts(state);
      renderDataView(state);
      updateSummaryChip(state);
    }),

  // Export Shell Actions
  launchNativePowerBI: () => launchNativePowerBI(state),
  exportCSVMarts: () => exportCSVMarts(state),

  showToast,
};

// Global reference for HTML event triggers
window.app = app;

function setupEventListeners() {
  // A. Pipeline Real-time Progress & Log Streams
  if (window.api?.onPipelineProgress) {
    window.api.onPipelineProgress((data) => {
      if (data.progress !== undefined) {
        updateProgress(data.progress, data.stage || "Processing...");
      }
    });
  }
  if (window.api?.onPipelineLog) {
    window.api.onPipelineLog((msg) => {
      appendLog(msg);
    });
  }

  // B. Top Navigation Tabs (Dashboard, Data, Model, DAX)
  document.querySelectorAll(".nav-tab-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      if (btn.dataset.view) {
        app.switchView(btn.dataset.view);
      }
    });
  });

  // C. Header Action Buttons
  document.getElementById("btnLoadSample")?.addEventListener("click", () => app.runSamplePipeline());
  document.getElementById("btnImportExcel")?.addEventListener("click", () => app.selectAndRunExcel());
  document.getElementById("btnLaunchPowerBI")?.addEventListener("click", () => app.launchNativePowerBI());
  document.getElementById("btnExportCSVMarts")?.addEventListener("click", () => app.exportCSVMarts());

  // D. Dashboard Slicers
  document.querySelectorAll("#categorySlicerPills .slicer-pill").forEach((pill) => {
    pill.addEventListener("click", () => {
      document.querySelectorAll("#categorySlicerPills .slicer-pill").forEach((p) => p.classList.remove("active"));
      pill.classList.add("active");
      app.setCategoryFilter(pill.dataset.category);
    });
  });

  document.getElementById("channelSlicerSelect")?.addEventListener("change", (e) => {
    app.setChannelFilter(e.target.value);
  });

  document.getElementById("slicerStartDate")?.addEventListener("change", (e) => {
    state.dateRange.start = e.target.value;
    applySlicerFilters(state, () => {
      renderCharts(state);
      updateSummaryChip(state);
    });
  });

  document.getElementById("slicerEndDate")?.addEventListener("change", (e) => {
    state.dateRange.end = e.target.value;
    applySlicerFilters(state, () => {
      renderCharts(state);
      updateSummaryChip(state);
    });
  });

  document.getElementById("btnResetSlicers")?.addEventListener("click", () => app.resetFilters());

  // D2. Dashboard Sub-Mode Toggle (Interactive vs Statistical)
  document.getElementById("btnModeInteractive")?.addEventListener("click", () => {
    switchDashboardSubMode("interactive");
  });
  document.getElementById("btnModeStatistical")?.addEventListener("click", () => {
    switchDashboardSubMode("statistical");
  });

  // E. Theme Toggle
  document.getElementById("btnThemeToggle")?.addEventListener("click", () => {
    app.toggleTheme();
  });

  // F. New Measure Modal
  document.getElementById("btnOpenNewMeasureModal")?.addEventListener("click", () => {
    const modal = document.getElementById("newMeasureModal");
    if (modal) modal.style.display = "flex";
    document.getElementById("newMeasureNameInput")?.focus();
  });

  document.getElementById("btnConfirmCreateMeasure")?.addEventListener("click", () => {
    const nameInput = document.getElementById("newMeasureNameInput");
    const exprInput = document.getElementById("newMeasureExprInput");
    const name = nameInput?.value?.trim();
    const expr = exprInput?.value?.trim();
    if (!name || !expr) {
      showToast("Please provide both a measure name and DAX expression.", "warning");
      return;
    }
    if (!state.currentManifest) state.currentManifest = { measures: [] };
    if (!state.currentManifest.measures) state.currentManifest.measures = [];

    state.currentManifest.measures.unshift({
      name,
      expression: expr,
      category: "User Custom",
      description: "Custom measure added in RevenueOS Studio",
      table_name: "_Measures",
    });

    populateDAXMeasures(state);
    renderDaxCatalog(state);
    const modal = document.getElementById("newMeasureModal");
    if (modal) modal.style.display = "none";
    if (nameInput) nameInput.value = "";
    if (exprInput) exprInput.value = "";
    showToast(`Measure [${name}] created!`, "success");
  });

  // G. Global Keyboard Shortcuts (Ctrl+1..4, Ctrl+O, Ctrl+E, Esc, /)
  window.addEventListener("keydown", (e) => {
    const isTyping = ["INPUT", "TEXTAREA", "SELECT"].includes(document.activeElement?.tagName);

    if (e.key === "Escape") {
      const pm = document.getElementById("pipelineModal");
      const nm = document.getElementById("newMeasureModal");
      if (pm) pm.style.display = "none";
      if (nm) nm.style.display = "none";
      return;
    }

    if (e.ctrlKey || e.metaKey) {
      if (e.key === "1") {
        e.preventDefault();
        app.switchView("dashboard");
      } else if (e.key === "2") {
        e.preventDefault();
        app.switchView("data");
      } else if (e.key === "3") {
        e.preventDefault();
        app.switchView("model");
      } else if (e.key === "4") {
        e.preventDefault();
        app.switchView("dax");
      } else if (e.key.toLowerCase() === "o") {
        e.preventDefault();
        app.selectAndRunExcel();
      } else if (e.key.toLowerCase() === "e") {
        e.preventDefault();
        app.launchNativePowerBI();
      } else if (e.shiftKey && e.key.toLowerCase() === "s") {
        e.preventDefault();
        app.runSamplePipeline();
      }
    } else if (!isTyping && e.key === "/") {
      e.preventDefault();
      if (state.activeView === "data") {
        document.getElementById("dgSearchInput")?.focus();
      } else if (state.activeView === "dax") {
        document.getElementById("daxSearchInput")?.focus();
      }
    }
  });

  // E. Data View Search & Export
  document.getElementById("dgSearchInput")?.addEventListener("input", (e) => {
    filterDataGrid(e.target.value, state);
  });

  document.getElementById("btnExportCurrentTableCSV")?.addEventListener("click", () => {
    exportCurrentTableCSV(state);
  });

  // F. DAX Measures Formula Bar & Search
  document.getElementById("daxMeasureDropdown")?.addEventListener("change", (e) => {
    app.updateDAXFormula(e.target.value);
  });

  document.getElementById("btnEvaluateDax")?.addEventListener("click", () => app.evaluateDAX());
  document.getElementById("btnSaveDax")?.addEventListener("click", () => app.saveDAX());
  document.getElementById("btnCopyDax")?.addEventListener("click", () => {
    const formula = document.getElementById("daxFormulaInput")?.value;
    if (formula) {
      if (window.api?.copyToClipboard) {
        window.api.copyToClipboard(formula);
      } else {
        navigator.clipboard?.writeText(formula);
      }
      showToast("DAX formula copied to clipboard!", "success");
    }
  });

  document.getElementById("btnCopyAllDax")?.addEventListener("click", () => app.copyAllDAX());

  document.getElementById("daxSearchInput")?.addEventListener("input", (e) => {
    const activeCat = document.querySelector(".dax-cat-pill.active")?.dataset.cat || "ALL";
    renderDaxCatalog(state, e.target.value, activeCat);
  });

  // G. Drag & Drop File Ingestion
  window.addEventListener("dragover", (e) => {
    e.preventDefault();
    e.stopPropagation();
    document.body.classList.add("drag-active");
  });

  window.addEventListener("dragleave", (e) => {
    e.preventDefault();
    e.stopPropagation();
    document.body.classList.remove("drag-active");
  });

  window.addEventListener("drop", async (e) => {
    e.preventDefault();
    e.stopPropagation();
    document.body.classList.remove("drag-active");
    const files = e.dataTransfer?.files;
    if (files && files.length > 0) {
      const file = files[0];
      if (file.name.match(/\.(xlsx|xls|xlsm|csv)$/i)) {
        if (window.api?.runPipeline && file.path) {
          const projName = file.name.replace(/\.[^.]+$/, "");
          await runPipelineForPath(file.path, projName);
        } else {
          const { runPipelineWithFile } = await import("./modules/pipeline.js");
          await runPipelineWithFile(file, state, () => refreshAllViews());
        }
      } else {
        showToast("Please drop an Excel workbook (.xlsx, .xls, .xlsm) or CSV file.", "warning");
      }
    }
  });

  // Window resize: re-render charts & re-draw SVG lines
  window.addEventListener("resize", () => {
    if (state.activeView === "dashboard") {
      Object.values(state.charts).forEach((c) => c?.resize?.());
    } else if (state.activeView === "model") {
      drawModelRelationships(state);
    }
  });
}

async function init() {
  loadSavedTheme();
  setupEventListeners();

  // Load preloaded initial model if available from Electron main or static manifest
  try {
    if (window.api?.loadInitialModel) {
      const preloaded = await window.api.loadInitialModel();
      if (preloaded) {
        state.setManifest(preloaded);
      }
    } else {
      const resp = await fetch("../exports/default_model/manifest.json");
      if (resp.ok) {
        const preloaded = await resp.json();
        state.setManifest(preloaded);
      }
    }
  } catch (e) {
    console.debug("No preloaded model available:", e);
  }

  refreshAllViews();
}

document.addEventListener("DOMContentLoaded", () => {
  init();
});
