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
      const fileName = filePath.split(/[\\/]/).pop() || "RevenueOS_Report";
      const projName = fileName.replace(/\.[^.]+$/, "");
      await runPipelineForPath(filePath, projName, state, onPipelineComplete);
    }
  } else {
    // Web / Browser mode: open native HTML file picker
    let fileInput = document.getElementById("universalFileInput");
    if (!fileInput) {
      fileInput = document.createElement("input");
      fileInput.type = "file";
      fileInput.id = "universalFileInput";
      fileInput.accept = ".xlsx,.xls,.xlsm,.csv";
      fileInput.style.display = "none";
      document.body.appendChild(fileInput);
    }
    fileInput.value = "";
    fileInput.onchange = async (e) => {
      const file = e.target.files?.[0];
      if (file) {
        await runPipelineWithFile(file, state, onPipelineComplete);
      }
    };
    fileInput.click();
  }
}

export async function runPipelineWithFile(file, state, onPipelineComplete) {
  const modal = document.getElementById("pipelineModal");
  const terminal = document.getElementById("pipelineLogTerminal");
  if (modal) modal.style.display = "flex";
  if (terminal) terminal.innerHTML = "";

  const projName = file.name.replace(/\.[^.]+$/, "");
  updateProgress(10, `Uploading & analyzing ${file.name}...`);
  appendLog(`[UPLOAD] Starting ingest of '${file.name}' (${(file.size / 1024).toFixed(1)} KB)`);

  const formData = new FormData();
  formData.append("file", file);
  formData.append("project_name", projName);
  formData.append("currency_symbol", "$");
  formData.append("generate_visuals", "true");

  try {
    const apiUrl = window.location.port === "8000" ? "" : "http://127.0.0.1:8000";
    appendLog(`[REST] Submitting file to ${apiUrl}/api/pipeline/run`);
    const resp = await fetch(`${apiUrl}/api/pipeline/run`, {
      method: "POST",
      body: formData,
    });
    if (!resp.ok) {
      const errText = await resp.text();
      throw new Error(`HTTP ${resp.status}: ${errText}`);
    }
    const runData = await resp.json();
    const jobId = runData.job_id;
    appendLog(`[JOB] Pipeline job queued: ${jobId}`);

    // Poll until completed
    let attempts = 0;
    while (attempts < 60) {
      await new Promise((r) => setTimeout(r, 800));
      attempts++;
      const statusResp = await fetch(`${apiUrl}/api/pipeline/status/${jobId}`);
      if (!statusResp.ok) continue;
      const statusData = await statusResp.json();

      updateProgress(statusData.progress || 50, statusData.stage || "Transforming...");
      if (statusData.logs && statusData.logs.length > 0) {
        appendLog(`[STAGE] ${statusData.logs[statusData.logs.length - 1]}`);
      }

      if (statusData.status === "completed") {
        updateProgress(100, "Complete!");
        appendLog("[SUCCESS] Star schema, DAX measures, and artifacts generated!");

        let manifest = statusData.manifest;
        if (!manifest) {
          const manResp = await fetch(`${apiUrl}/api/manifest/${jobId}`);
          if (manResp.ok) manifest = await manResp.json();
        }

        if (manifest) {
          state.setManifest(manifest, jobId);
          const docTitle = document.getElementById("documentTitle");
          if (docTitle) docTitle.textContent = `${file.name} - Power BI Desktop Studio`;

          if (typeof onPipelineComplete === "function") {
            onPipelineComplete(manifest);
          }
        }
        showToast(`Dataset '${file.name}' successfully loaded & modeled!`, "success");
        setTimeout(() => {
          if (modal) modal.style.display = "none";
        }, 800);
        return;
      } else if (statusData.status === "failed") {
        throw new Error(statusData.error || "Transformation pipeline failed");
      }
    }
  } catch (err) {
    appendLog(`[ERROR] ${err.message}`);
    updateProgress(100, "Failed");
    showToast(`Ingestion failed: ${err.message}`, "error");
  }
}

export async function runSamplePipeline(state, onPipelineComplete) {
  // Let user pick their own file
  await selectAndRunExcel(state, onPipelineComplete);
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
