/**
 * RevenueOS Studio – Pipeline Execution & Data Ingestion Module
 * ==============================================================
 * Orchestrates Python Star Schema compilation via Electron IPC bridge
 * or FastAPI REST asynchronous job polling with real-time log streaming.
 */

import { showToast } from "./toast.js";

export function updateProgress(pct, stage) {
  const fill = document.getElementById("pipelineProgressFill");
  const pctText = document.getElementById("pipelinePercentText");
  const stageText = document.getElementById("pipelineStageText");
  if (fill) fill.style.width = `${pct}%`;
  if (pctText) pctText.textContent = `${pct}%`;
  if (stageText) stageText.textContent = stage;
}

export function appendLog(msg) {
  const term = document.getElementById("pipelineLogTerminal");
  if (!term) return;
  const l = document.createElement("div");
  l.textContent = msg;
  term.appendChild(l);
  term.scrollTop = term.scrollHeight;
}

export function refreshData(state, onRefresh) {
  if (typeof onRefresh === "function") {
    onRefresh();
  }
  showToast(`Data marts refreshed at ${new Date().toLocaleTimeString()}`, "info");
}

export async function selectAndRunExcel(state, onPipelineComplete) {
  if (window.api?.selectExcelFile) {
    const filePath = await window.api.selectExcelFile();
    if (filePath) {
      await runPipelineForPath(filePath, "RevenueOS_Report", state, onPipelineComplete);
    }
  } else {
    // Web fallback: Inform user or trigger sample pipeline via REST
    showToast("File selection dialog requires Electron desktop runtime. Running sample pipeline via REST...", "warning");
    await runSamplePipeline(state, onPipelineComplete);
  }
}

export async function runSamplePipeline(state, onPipelineComplete) {
  if (window.api?.getSamplePath) {
    const samplePath = await window.api.getSamplePath();
    if (samplePath) {
      await runPipelineForPath(samplePath, "RevenueOS_Sample", state, onPipelineComplete);
      return;
    }
  }

  // REST API Fallback
  await runPipelineViaRest("sample", state, onPipelineComplete);
}

export async function runPipelineForPath(filePath, projectName = "RevenueOS_Report", state, onPipelineComplete) {
  const modal = document.getElementById("pipelineModal");
  const terminal = document.getElementById("pipelineLogTerminal");
  if (modal) modal.style.display = "flex";
  if (terminal) terminal.innerHTML = "";

  updateProgress(10, "Profiling Excel Workbook...");
  appendLog(`[INIT] Target workbook: ${filePath}`);

  try {
    if (window.api?.runPipeline) {
      const result = await window.api.runPipeline({ excelPath: filePath, projectName, currency: "$" });
      if (result && result.manifest) {
        state.setManifest(result.manifest);
        updateProgress(100, "Complete!");
        showToast("Dataset successfully loaded & Star Schema compiled!", "success");

        if (typeof onPipelineComplete === "function") {
          onPipelineComplete(result.manifest);
        }

        setTimeout(() => {
          if (modal) modal.style.display = "none";
        }, 800);
        return;
      }
    }
    throw new Error("Electron pipeline bridge unavailable.");
  } catch (err) {
    appendLog(`[ERROR] ${err.message}`);
    updateProgress(100, "Failed");
    showToast(`Pipeline execution failed: ${err.message}`, "error");
  }
}

async function runPipelineViaRest(mode = "sample", state, onPipelineComplete) {
  const modal = document.getElementById("pipelineModal");
  const terminal = document.getElementById("pipelineLogTerminal");
  if (modal) modal.style.display = "flex";
  if (terminal) terminal.innerHTML = "";

  updateProgress(15, "Connecting to RevenueOS REST Engine...");
  appendLog(`[REST] Dispatching pipeline job to http://127.0.0.1:8000/api/pipeline/run-sample`);

  try {
    const resp = await fetch("http://127.0.0.1:8000/api/pipeline/run-sample", { method: "POST" });
    if (!resp.ok) {
      throw new Error(`HTTP ${resp.status}: ${resp.statusText}`);
    }
    const data = await resp.json();
    const jobId = data.job_id;
    appendLog(`[REST] Job initiated with ID: ${jobId}`);

    // Poll status until completion
    let complete = false;
    let attempts = 0;
    while (!complete && attempts < 60) {
      await new Promise((r) => setTimeout(r, 1000));
      attempts++;
      const statusResp = await fetch(`http://127.0.0.1:8000/api/pipeline/status/${jobId}`);
      if (!statusResp.ok) continue;

      const statusData = await statusResp.json();
      updateProgress(statusData.progress || 50, statusData.stage || "Processing...");
      if (statusData.logs && statusData.logs.length > 0) {
        const lastLog = statusData.logs[statusData.logs.length - 1];
        appendLog(`[STAGE] ${lastLog}`);
      }

      if (statusData.status === "completed") {
        complete = true;
        updateProgress(100, "Complete!");
        appendLog("[REST] Pipeline completed successfully.");
        if (statusData.manifest) {
          state.setManifest(statusData.manifest, jobId);
          if (typeof onPipelineComplete === "function") {
            onPipelineComplete(statusData.manifest);
          }
        }
        showToast("Dataset successfully loaded via REST engine!", "success");
        setTimeout(() => {
          if (modal) modal.style.display = "none";
        }, 800);
        return;
      } else if (statusData.status === "failed") {
        throw new Error(statusData.error || "REST pipeline failed");
      }
    }
  } catch (err) {
    appendLog(`[ERROR] ${err.message}`);
    updateProgress(100, "Failed");
    showToast(`REST pipeline failed: ${err.message}`, "error");
  }
}
