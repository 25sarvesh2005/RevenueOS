/**
 * RevenueOS Studio – Electron Preload Script
 * ==========================================
 * Exposes secure context bridge to Electron renderer.
 */

const { contextBridge, ipcRenderer } = require("electron");

contextBridge.exposeInMainWorld("api", {
  // Dialogs
  selectExcelFile: () => ipcRenderer.invoke("dialog:select-excel"),
  selectOutputFolder: () => ipcRenderer.invoke("dialog:select-folder"),
  getSamplePath: () => ipcRenderer.invoke("app:get-sample-path"),

  // Pipeline Execution
  runPipeline: (params) => ipcRenderer.invoke("pipeline:run", params),

  // Events & Streams
  onPipelineProgress: (callback) => {
    const handler = (event, data) => callback(data);
    ipcRenderer.on("pipeline:progress", handler);
    return () => ipcRenderer.removeListener("pipeline:progress", handler);
  },
  onPipelineLog: (callback) => {
    const handler = (event, msg) => callback(msg);
    ipcRenderer.on("pipeline:log", handler);
    return () => ipcRenderer.removeListener("pipeline:log", handler);
  },

  // Shell Actions
  openFolder: (folderPath) => ipcRenderer.invoke("shell:open-folder", folderPath),
  launchFile: (filePath) => ipcRenderer.invoke("shell:launch-file", filePath),
  copyToClipboard: (text) => ipcRenderer.invoke("clipboard:write", text),

  // Preloaded Data & Storage
  loadInitialModel: () => ipcRenderer.invoke("app:load-initial-model"),
  saveCSV: (params) => ipcRenderer.invoke("dialog:save-csv", params),

  // DAX Semantic Engine Evaluation
  evaluateDax: (expression, jobId) => ipcRenderer.invoke("dax:evaluate", { expression, jobId }),

  // PDF Export
  exportPdf: (params) => ipcRenderer.invoke("report:export-pdf", params),
});
