/**
 * RevenueOS Studio – Power BI Desktop Replica Orchestrator
 * ========================================================
 * Modular Application Root coordinating:
 * - State management (modules/state.js)
 * - Toast notification feedback (modules/toast.js)
 * - Visualizations & Chart.js lifecycles (modules/charts.js)
 * - Tabular Data Grid & Matrix (modules/dataView.js)
 * - Kimball Star Schema Diagram & SVG Wire Connectors (modules/modelView.js)
 * - DAX Semantic Formula Engine & Measure Catalog (modules/daxEngine.js)
 * - Slicers & Dynamic Cross-Filtering (modules/slicers.js)
 * - Python Pipeline Engine & Ingestion Streaming (modules/pipeline.js)
 * - Modals, Shell Integrations & Focus Mode (modules/modals.js)
 * - Ribbon Navigation & Fields Hierarchy (modules/ribbon.js)
 */

import { state } from "./modules/state.js";
import { showToast } from "./modules/toast.js";
import {
  renderCharts,
  selectVisual,
  transformSelectedVisual,
} from "./modules/charts.js";
import {
  renderDataView,
  renderFinancialTable,
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
} from "./modules/daxEngine.js";
import {
  setCategoryFilter,
  setChannelFilter,
  resetFilters,
  applySlicerFilters,
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
  openPowerQueryModal,
  openNewMeasureModal,
  confirmCreateMeasure,
  openMatplotlibModal,
  openChartsFolder,
  launchNativePowerBI,
  exportCSVMarts,
  toggleFocus,
  closeFocusMode,
  openCopilotModal,
  runCopilotInvestigation,
  openExecutiveReportModal,
  exportExecutiveReportPdf,
  openAnnotationModal,
  saveAnnotation,
} from "./modules/modals.js";
import {
  setupRibbonTabs,
  switchView,
  switchPage,
  addNewPage,
  renderFieldsTree,
} from "./modules/ribbon.js";

function refreshAllViews() {
  populateDAXMeasures(state);
  renderFieldsTree(state, (name) => updateDAXFormula(name, state));
  renderCharts(state);
  renderDataView(state);
  renderModelView(state);
  renderFinancialTable(state);
}

export const app = {
  state,
  init,
  refreshAllViews,

  // Ribbon & Viewport Navigation
  switchView: (viewName) =>
    switchView(viewName, state, (v) => {
      if (v === "report") renderCharts(state);
      else if (v === "data") renderDataView(state);
      else if (v === "model") renderModelView(state);
    }),
  switchPage: (pageId) => switchPage(pageId, state),
  addNewPage: () => addNewPage(state),
  selectVisual: (id) => selectVisual(id, state),
  transformSelectedVisual: (type) => transformSelectedVisual(type, state),

  // DAX Semantic Operations
  evaluateDAX: () => evaluateDAX(state),
  saveDAX: () => saveDAX(state),
  copyAllDAX: () => copyAllDAX(state),
  updateDAXFormula: (name) => updateDAXFormula(name, state),

  // Slicer Cross-Filtering
  setCategoryFilter: (cat) =>
    setCategoryFilter(cat, state, () => renderCharts(state)),
  setChannelFilter: (chan) =>
    setChannelFilter(chan, state, () => renderCharts(state)),
  resetFilters: () => resetFilters(state, () => renderCharts(state)),

  // Pipeline Engine
  refreshData: () =>
    refreshData(state, () => {
      renderCharts(state);
      renderDataView(state);
    }),
  selectAndRunExcel: () =>
    selectAndRunExcel(state, () => refreshAllViews()),
  runSamplePipeline: () =>
    runSamplePipeline(state, () => refreshAllViews()),
  runPipelineForPath: (path, proj) =>
    runPipelineForPath(path, proj, state, () => refreshAllViews()),
  updateProgress,
  appendLog,

  // Modals & Native Shell
  openPowerQueryModal: () => openPowerQueryModal(state),
  openNewMeasureModal: () => openNewMeasureModal(),
  confirmCreateMeasure: () =>
    confirmCreateMeasure(state, () => {
      populateDAXMeasures(state);
      renderFieldsTree(state, (name) => updateDAXFormula(name, state));
    }),
  openMatplotlibModal: () => openMatplotlibModal(state),
  openChartsFolder: () => openChartsFolder(state),
  launchNativePowerBI: () => launchNativePowerBI(state),
  exportCSVMarts: () => exportCSVMarts(state),
  toggleFocus: (id) => toggleFocus(id, state),
  closeFocusMode: () => closeFocusMode(state),
  openCopilotModal: (entity, issue) => openCopilotModal(entity, issue, state),
  runCopilotInvestigation: () => runCopilotInvestigation(state),
  openExecutiveReportModal: () => openExecutiveReportModal(state),
  exportExecutiveReportPdf: () => exportExecutiveReportPdf(state),
  openAnnotationModal: () => openAnnotationModal(state),
  saveAnnotation: () => saveAnnotation(state),
  showToast,
};

// Global reference for backward-compatibility with inline HTML event triggers
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

  // B. Ribbon Tabs
  setupRibbonTabs();

  // C. Left Navigation Rail (Report / Data / Model)
  document.querySelectorAll(".rail-btn").forEach((btn) => {
    btn.addEventListener("click", () => app.switchView(btn.dataset.view));
  });

  // D. Page Switcher Tabs
  document.querySelectorAll(".page-tab").forEach((tab) => {
    if (tab.dataset.page) {
      tab.addEventListener("click", () => app.switchPage(tab.dataset.page));
    }
  });

  // E. Add Page Button (+)
  document.getElementById("btnAddPage")?.addEventListener("click", () => app.addNewPage());

  // F. DAX Measure Selector Dropdown
  document.getElementById("daxMeasureDropdown")?.addEventListener("change", (e) => {
    app.updateDAXFormula(e.target.value);
  });

  // G. DAX Formula Bar Buttons
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
      showToast("DAX formula copied to clipboard!", "info");
    }
  });

  // H. Category Slicer Pills
  document.querySelectorAll(".slicer-pills .slicer-pill").forEach((pill) => {
    pill.addEventListener("click", () => {
      document.querySelectorAll(".slicer-pills .slicer-pill").forEach((p) => p.classList.remove("active"));
      pill.classList.add("active");
      app.setCategoryFilter(pill.dataset.category);
    });
  });

  // I. Channel Slicer
  document.getElementById("channelSlicerSelect")?.addEventListener("change", (e) => {
    app.setChannelFilter(e.target.value);
  });

  // J. Date Slicers
  document.getElementById("slicerStartDate")?.addEventListener("change", (e) => {
    state.dateRange.start = e.target.value;
    applySlicerFilters(state, () => renderCharts(state));
  });
  document.getElementById("slicerEndDate")?.addEventListener("change", (e) => {
    state.dateRange.end = e.target.value;
    applySlicerFilters(state, () => renderCharts(state));
  });

  // K. Reset Slicers
  document.getElementById("btnResetSlicers")?.addEventListener("click", () => app.resetFilters());

  // L. Ribbon Tools
  document.getElementById("btnLoadSample")?.addEventListener("click", () => app.runSamplePipeline());
  document.getElementById("btnSelectExcel")?.addEventListener("click", () => app.selectAndRunExcel());
  document.getElementById("btnGetData")?.addEventListener("click", () => app.selectAndRunExcel());
  document.getElementById("btnRefreshData")?.addEventListener("click", () => app.refreshData());
  document.getElementById("btnTransformData")?.addEventListener("click", () => app.openPowerQueryModal());
  document.getElementById("btnNewMeasure")?.addEventListener("click", () => app.openNewMeasureModal());
  document.getElementById("btnManageRelationships")?.addEventListener("click", () => app.switchView("model"));
  document.getElementById("btnStarSchemaViewer")?.addEventListener("click", () => app.switchView("model"));
  document.getElementById("btnLaunchPowerBI")?.addEventListener("click", () => app.launchNativePowerBI());
  document.getElementById("btnExportCSVMarts")?.addEventListener("click", () => app.exportCSVMarts());
  document.getElementById("btnMatplotlibPack")?.addEventListener("click", () => app.openMatplotlibModal());
  document.getElementById("btnOpenChartsFolder")?.addEventListener("click", () => app.openChartsFolder());
  document.getElementById("btnCopyAllDAX")?.addEventListener("click", () => app.copyAllDAX());
  document.getElementById("btnInvestigateCopilot")?.addEventListener("click", () => app.openCopilotModal());
  document.getElementById("btnExecutiveBriefing")?.addEventListener("click", () => app.openExecutiveReportModal());
  document.getElementById("btnExportExecutivePdf")?.addEventListener("click", () => app.exportExecutiveReportPdf());
  document.getElementById("btnAddAnnotation")?.addEventListener("click", () => app.openAnnotationModal());
  document.getElementById("btnRunCopilot")?.addEventListener("click", () => app.runCopilotInvestigation());
  document.getElementById("btnSaveAnnotation")?.addEventListener("click", () => app.saveAnnotation());

  // M. Theme Switcher
  document.getElementById("themeSelect")?.addEventListener("change", (e) => {
    document.body.className = e.target.value;
    renderCharts(state);
  });

  // N. Data View Table Switcher
  document.querySelectorAll(".dv-table-item").forEach((item) => {
    item.addEventListener("click", () => {
      document.querySelectorAll(".dv-table-item").forEach((i) => i.classList.remove("active"));
      item.classList.add("active");
      state.activeTable = item.dataset.table;
      renderDataView(state);
    });
  });

  // O. Data Grid Search & Export
  document.getElementById("dgSearchInput")?.addEventListener("input", (e) => {
    filterDataGrid(e.target.value, state);
  });
  document.getElementById("btnExportCurrentTableCSV")?.addEventListener("click", () => {
    exportCurrentTableCSV(state);
  });

  // P. Visualizations Gallery (Transform active chart)
  document.querySelectorAll(".visuals-gallery .vis-icon-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      document.querySelectorAll(".visuals-gallery .vis-icon-btn").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
      if (btn.dataset.chartType) {
        app.transformSelectedVisual(btn.dataset.chartType);
      }
    });
  });

  // Q. Canvas Visual Containers (Click to select)
  document.querySelectorAll(".pbi-visual-container").forEach((container) => {
    container.addEventListener("click", (e) => {
      if (!e.target.closest(".vtool-btn")) {
        app.selectVisual(container.id);
      }
    });
  });

  // R. Power Query & Measure Modals
  document.getElementById("btnCopyPqCode")?.addEventListener("click", () => {
    const code = document.getElementById("pqCodeBlock")?.textContent;
    if (code) {
      if (window.api?.copyToClipboard) {
        window.api.copyToClipboard(code);
      } else {
        navigator.clipboard?.writeText(code);
      }
      showToast("Power Query M code copied to clipboard!", "info");
    }
  });
  document.getElementById("btnConfirmCreateMeasure")?.addEventListener("click", () => {
    app.confirmCreateMeasure();
  });

  // S. Global Error Boundary / Window Error Listener
  window.addEventListener("error", (event) => {
    console.error("[RevenueOS Studio Unhandled Error]", event.error);
    showToast(`Runtime exception: ${event.message}`, "error", 5000);
  });
  window.addEventListener("unhandledrejection", (event) => {
    console.error("[RevenueOS Studio Unhandled Promise]", event.reason);
    showToast(`Async exception: ${event.reason?.message || event.reason}`, "error", 5000);
  });
}

async function init() {
  setupEventListeners();

  // Load initial dataset from model_data.json or model_data_sample.json
  try {
    if (window.api?.loadInitialModel) {
      const preloaded = await window.api.loadInitialModel();
      if (preloaded) state.setManifest(preloaded);
    }
    if (!state.currentManifest) {
      const resp = await fetch("model_data.json");
      if (resp.ok) {
        state.setManifest(await resp.json());
      } else {
        const sampleResp = await fetch("model_data_sample.json");
        if (sampleResp.ok) {
          state.setManifest(await sampleResp.json());
        }
      }
    }
  } catch (e) {
    console.warn("Could not load initial model_data.json:", e);
  }

  refreshAllViews();
  selectVisual("visualMonthlyTrend", state);
}

document.addEventListener("DOMContentLoaded", () => {
  app.init();
});
