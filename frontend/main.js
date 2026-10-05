/**
 * RevenueOS Studio – Electron Main Process
 * ========================================
 * High-performance desktop bridge launching the Power BI Replica Studio,
 * orchestrating the Python Kimball Star Schema pipeline, and managing native dialogs.
 */

const { app, BrowserWindow, ipcMain, dialog, shell, clipboard } = require("electron");
const path = require("path");
const { spawn } = require("child_process");
const fs = require("fs");

let mainWindow = null;
let currentPipelineProcess = null;

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1440,
    height: 940,
    minWidth: 1100,
    minHeight: 740,
    backgroundColor: "#0B0E14",
    title: "RevenueOS Studio – Automated Excel-to-Power BI Decision Engine",
    webPreferences: {
      preload: path.join(__dirname, "preload.js"),
      nodeIntegration: false,
      contextIsolation: true,
      sandbox: false,
    },
  });

  mainWindow.loadFile(path.join(__dirname, "index.html"));

  mainWindow.webContents.on("console-message", (event, level, message, line, sourceId) => {
    console.log(`[RENDERER_LOG level=${level}] ${message} (${sourceId}:${line})`);
  });

  mainWindow.on("closed", () => {
    mainWindow = null;
  });
}

app.whenReady().then(() => {
  createWindow();

  app.on("activate", () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on("window-all-closed", () => {
  if (process.platform !== "darwin") {
    app.quit();
  }
});

// ---------------------------------------------------------------------------
// IPC Handlers
// ---------------------------------------------------------------------------

// 1. File Selection Dialog (Excel)
ipcMain.handle("dialog:select-excel", async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    title: "Select Business Data Workbook (Excel or CSV)",
    properties: ["openFile"],
    filters: [
      { name: "Business Data Files", extensions: ["xlsx", "xls", "xlsm", "csv"] },
      { name: "Excel Workbooks", extensions: ["xlsx", "xls", "xlsm"] },
      { name: "CSV Files", extensions: ["csv"] },
      { name: "All Files", extensions: ["*"] },
    ],
  });

  if (result.canceled || result.filePaths.length === 0) {
    return null;
  }
  return result.filePaths[0];
});

// 2. Folder Selection Dialog
ipcMain.handle("dialog:select-folder", async () => {
  const result = await dialog.showOpenDialog(mainWindow, {
    title: "Select Output Destination Folder",
    properties: ["openDirectory", "createDirectory"],
  });

  if (result.canceled || result.filePaths.length === 0) {
    return null;
  }
  return result.filePaths[0];
});

// Security: Directory allowlist for shell navigation
const projectRoot = path.resolve(__dirname, "..");
const allowedDirectories = new Set([projectRoot]);

function isSafePath(targetPath) {
  if (!targetPath || typeof targetPath !== "string") return false;
  try {
    const resolved = path.resolve(targetPath);
    for (const allowed of allowedDirectories) {
      if (resolved.startsWith(allowed)) {
        return fs.existsSync(resolved);
      }
    }
    return false;
  } catch {
    return false;
  }
}

// Helper to normalize manifest paths portably across environments
function normalizeManifestPaths(manifest) {
  if (!manifest) return manifest;
  try {
    if (manifest.outputDirectory && !path.isAbsolute(manifest.outputDirectory)) {
      manifest.outputDirectory = path.resolve(projectRoot, manifest.outputDirectory);
    }
    if (manifest.sourceExcel && !path.isAbsolute(manifest.sourceExcel)) {
      manifest.sourceExcel = path.resolve(projectRoot, manifest.sourceExcel);
    }
    if (manifest.paths) {
      for (const [key, val] of Object.entries(manifest.paths)) {
        if (typeof val === "string") {
          manifest.paths[key] = path.isAbsolute(val) ? val : path.resolve(projectRoot, val);
        }
      }
      if (manifest.paths.outputDir) {
        allowedDirectories.add(path.resolve(manifest.paths.outputDir));
      }
    }
    if (Array.isArray(manifest.charts)) {
      manifest.charts.forEach((chart) => {
        if (chart.path && !path.isAbsolute(chart.path)) {
          chart.path = path.resolve(projectRoot, chart.path);
        }
      });
    }
  } catch (err) {
    console.warn("Failed to normalize manifest paths:", err);
  }
  return manifest;
}

// 3. Run Pipeline Engine (Python Process)
ipcMain.handle("pipeline:run", async (event, params) => {
  const { excelPath, outputDir, projectName, currency } = params;

  return new Promise((resolve, reject) => {
    const pythonExe = process.platform === "win32" ? "python" : "python3";
    let scriptPath = path.resolve(__dirname, "..", "backend", "engine", "core.py");
    if (!fs.existsSync(scriptPath)) {
      scriptPath = path.resolve(__dirname, "..", "backend", "engine", "master.py");
    }

    if (outputDir) {
      allowedDirectories.add(path.resolve(outputDir));
    }

    const args = [scriptPath, excelPath];
    if (outputDir) args.push("--output-dir", outputDir);
    if (projectName) args.push("--project-name", projectName);
    if (currency) args.push("--currency", currency);

    const proc = spawn(pythonExe, args, {
      cwd: path.resolve(__dirname, ".."),
      env: { ...process.env, PYTHONUNBUFFERED: "1" },
    });

    currentPipelineProcess = proc;
    let finalManifest = null;
    let manifestFilePath = null;
    let accumulatedError = "";
    let stdoutBuffer = "";

    proc.stdout.on("data", (data) => {
      stdoutBuffer += data.toString("utf-8");
      const lines = stdoutBuffer.split("\n");
      // Retain the trailing incomplete line chunk in the buffer
      stdoutBuffer = lines.pop();

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed) continue;

        if (trimmed.startsWith("PIPELINE_COMPLETE_PATH:")) {
          manifestFilePath = trimmed.substring(23).trim();
          console.log("[MAIN] Discovered manifest path from engine:", manifestFilePath);
        } else if (trimmed.startsWith("PIPELINE_PROGRESS:") || trimmed.startsWith("EVENT_JSON:")) {
          try {
            const prefixLen = trimmed.startsWith("PIPELINE_PROGRESS:") ? 18 : 11;
            const progressData = JSON.parse(trimmed.substring(prefixLen));
            mainWindow?.webContents.send("pipeline:progress", progressData);
            if (progressData.message) {
              mainWindow?.webContents.send("pipeline:log", progressData.message);
            }
          } catch (e) {}
        } else if (trimmed.startsWith("PIPELINE_COMPLETE:")) {
          try {
            finalManifest = JSON.parse(trimmed.substring(18));
            normalizeManifestPaths(finalManifest);
          } catch (e) {
            console.warn("[MAIN] Direct stdout JSON parse deferred to disk fallback:", e.message);
          }
        } else {
          mainWindow?.webContents.send("pipeline:log", trimmed);
        }
      }
    });

    proc.stderr.on("data", (data) => {
      const errText = data.toString("utf-8");
      accumulatedError += errText;
      mainWindow?.webContents.send("pipeline:log", `[STDERR] ${errText.trim()}`);
    });

    proc.on("close", (code) => {
      currentPipelineProcess = null;

      // Check leftover buffer in case stream ended without newline
      if (stdoutBuffer && stdoutBuffer.trim()) {
        const trimmed = stdoutBuffer.trim();
        if (trimmed.startsWith("PIPELINE_COMPLETE_PATH:")) {
          manifestFilePath = trimmed.substring(23).trim();
        } else if (trimmed.startsWith("PIPELINE_COMPLETE:")) {
          try {
            finalManifest = JSON.parse(trimmed.substring(18));
            normalizeManifestPaths(finalManifest);
          } catch (e) {}
        }
      }

      // Robust fallback 1: Load from emitted manifestFilePath
      if (!finalManifest && manifestFilePath && fs.existsSync(manifestFilePath)) {
        try {
          const raw = fs.readFileSync(manifestFilePath, "utf-8");
          finalManifest = JSON.parse(raw);
          normalizeManifestPaths(finalManifest);
          console.log("[MAIN] Successfully read manifest from manifestFilePath:", manifestFilePath);
        } catch (e) {
          console.error("[MAIN] Error reading manifest file:", e);
        }
      }

      // Robust fallback 2: Check designated outputDir if provided
      if (!finalManifest && outputDir) {
        const outManifest = path.join(path.resolve(outputDir), "manifest.json");
        if (fs.existsSync(outManifest)) {
          try {
            finalManifest = JSON.parse(fs.readFileSync(outManifest, "utf-8"));
            normalizeManifestPaths(finalManifest);
            console.log("[MAIN] Successfully read manifest from outputDir:", outManifest);
          } catch (e) {}
        }
      }

      if (code === 0 && finalManifest) {
        resolve({ success: true, manifest: finalManifest });
      } else {
        reject(
          new Error(
            accumulatedError || (!finalManifest ? "Pipeline completed but manifest could not be read." : `Pipeline failed with exit code ${code}`)
          )
        );
      }
    });

    proc.on("error", (err) => {
      currentPipelineProcess = null;
      reject(err);
    });
  });
});

// 4. Sample Excel Path Provider
ipcMain.handle("app:get-sample-path", () => {
  const candidatePaths = [
    path.resolve(__dirname, "..", "data", "raw", "excel", "revenueos_sample.xlsx"),
    path.resolve(__dirname, "..", "tests", "fixtures", "test_sales.xlsx"),
  ];
  for (const p of candidatePaths) {
    if (fs.existsSync(p)) {
      return p;
    }
  }
  return null;
});

// 5. Shell: Open Directory (Security Hardened)
ipcMain.handle("shell:open-folder", async (event, folderPath) => {
  if (folderPath && isSafePath(folderPath)) {
    await shell.openPath(path.resolve(folderPath));
    return true;
  }
  console.warn(`[SECURITY] Blocked shell:open-folder for untrusted path: ${folderPath}`);
  return false;
});

// 6. Shell: Launch / Open File (Security Hardened)
ipcMain.handle("shell:launch-file", async (event, filePath) => {
  if (filePath && isSafePath(filePath)) {
    await shell.openPath(path.resolve(filePath));
    return true;
  }
  console.warn(`[SECURITY] Blocked shell:launch-file for untrusted path: ${filePath}`);
  return false;
});

// 7. Clipboard: Copy Text
ipcMain.handle("clipboard:write", (event, text) => {
  if (text) {
    clipboard.writeText(text);
    return true;
  }
  return false;
});

// 7b. Image Reader for High-Res Visuals
ipcMain.handle("image:read", async (event, imgPath) => {
  if (imgPath && isSafePath(imgPath) && fs.existsSync(imgPath)) {
    const ext = path.extname(imgPath).toLowerCase().replace(".", "") || "png";
    const data = fs.readFileSync(imgPath).toString("base64");
    return `data:image/${ext};base64,${data}`;
  }
  return null;
});

// 8. Load Precompiled Initial Model (Portable)
ipcMain.handle("app:load-initial-model", () => {
  const candidates = [
    path.resolve(__dirname, "..", "exports", "default_model", "manifest.json"),
    path.resolve(__dirname, "model_data.json"),
    path.resolve(__dirname, "model_data_sample.json"),
  ];
  for (const candidate of candidates) {
    if (fs.existsSync(candidate)) {
      try {
        const raw = fs.readFileSync(candidate, "utf-8");
        const parsed = JSON.parse(raw);
        return normalizeManifestPaths(parsed);
      } catch (err) {
        console.warn("Failed reading candidate manifest:", candidate, err);
      }
    }
  }
  return null;
});

// 9. Save CSV Table to Disk Dialog
ipcMain.handle("dialog:save-csv", async (event, { defaultName, content }) => {
  const result = await dialog.showSaveDialog(mainWindow, {
    title: "Export Table CSV",
    defaultPath: defaultName || "export.csv",
    filters: [{ name: "CSV Files", extensions: ["csv"] }],
  });
  if (!result.canceled && result.filePath) {
    fs.writeFileSync(result.filePath, content, "utf-8");
    return result.filePath;
  }
  return null;
});

// 10. DAX Semantic Engine Evaluation
ipcMain.handle("dax:evaluate", async (event, { expression, jobId }) => {
  return new Promise((resolve) => {
    const pythonExe = process.platform === "win32" ? "python" : "python3";
    const pyScript = `
import sys, json
from pathlib import Path
from backend.api.dax_evaluator import DaxEvaluator

try:
    expr = sys.argv[1]
    job_id = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] != "null" else None
    
    data_dir = None
    if job_id:
        candidate = Path("exports") / job_id
        if candidate.exists():
            data_dir = candidate
    if not data_dir:
        for p in [Path("exports/default_model"), Path("data/raw/csv"), Path("data/processed")]:
            if p.exists() and any(p.glob("**/*.csv")):
                data_dir = p
                break
                
    evaluator = DaxEvaluator(data_dir=data_dir)
    res = evaluator.evaluate(expr)
    print(json.dumps(res))
except Exception as e:
    print(json.dumps({
        "expression": sys.argv[1] if len(sys.argv) > 1 else "",
        "status": "ERROR",
        "evaluated_value": None,
        "formatted_value": None,
        "data_type": "error",
        "execution_time_ms": 0,
        "error": str(e)
    }))
`;
    const proc = spawn(pythonExe, ["-c", pyScript, expression, jobId || "null"], {
      cwd: path.resolve(__dirname, ".."),
      env: { ...process.env, PYTHONUNBUFFERED: "1" },
    });
    let stdoutData = "";
    proc.stdout.on("data", (d) => { stdoutData += d.toString(); });
    proc.on("close", (code) => {
      try {
        const parsed = JSON.parse(stdoutData.trim());
        resolve(parsed);
      } catch (err) {
        resolve({
          expression,
          status: "ERROR",
          evaluated_value: null,
          formatted_value: null,
          data_type: "error",
          execution_time_ms: 0,
          error: "Failed to evaluate DAX expression in Python engine: " + stdoutData,
        });
      }
    });
    proc.on("error", (err) => {
      resolve({
        expression,
        status: "ERROR",
        evaluated_value: null,
        formatted_value: null,
        data_type: "error",
        execution_time_ms: 0,
        error: err.message,
      });
    });
  });
});

// 11. Export Executive PDF
ipcMain.handle("report:export-pdf", async (event, { jobId, title }) => {
  const saveResult = await dialog.showSaveDialog(mainWindow, {
    title: "Export Executive PDF Report",
    defaultPath: title || "RevenueOS_Executive_Briefing.pdf",
    filters: [{ name: "PDF Documents", extensions: ["pdf"] }],
  });

  if (saveResult.canceled || !saveResult.filePath) {
    return { success: false, cancelled: true };
  }

  return new Promise((resolve) => {
    const pythonExe = process.platform === "win32" ? "python" : "python3";
    const pyScript = `
import sys, json
from pathlib import Path
from backend.python.reporting.executive_report import generate_executive_pdf_from_manifest

try:
    job_id = sys.argv[1]
    out_pdf = Path(sys.argv[2])
    
    manifest_path = None
    charts_dir = None
    if job_id and job_id not in ("default", "sample", "null"):
        p = Path("exports") / job_id / "manifest.json"
        if p.exists():
            manifest_path = p
            charts_dir = Path("exports") / job_id / "charts"
            
    if not manifest_path:
        for candidate in [Path("exports/default_model/manifest.json"), Path("frontend/model_data.json"), Path("frontend/model_data_sample.json")]:
            if candidate.exists():
                manifest_path = candidate
                break
                
    if not manifest_path or not manifest_path.exists():
        raise FileNotFoundError("No active manifest found for PDF synthesis.")
        
    data = json.loads(manifest_path.read_text(encoding="utf-8"))
    if not charts_dir or not charts_dir.exists():
        candidate_charts = manifest_path.parent / "charts"
        if candidate_charts.exists():
            charts_dir = candidate_charts
            
    generate_executive_pdf_from_manifest(data, out_pdf, charts_dir=charts_dir)
    print(json.dumps({"success": True, "filePath": str(out_pdf)}))
except Exception as e:
    print(json.dumps({"success": False, "error": str(e)}))
`;
    const proc = spawn(pythonExe, ["-c", pyScript, jobId || "null", saveResult.filePath], {
      cwd: path.resolve(__dirname, ".."),
      env: { ...process.env, PYTHONUNBUFFERED: "1" },
    });

    let stdoutData = "";
    proc.stdout.on("data", (d) => { stdoutData += d.toString(); });
    proc.on("close", (code) => {
      try {
        const parsed = JSON.parse(stdoutData.trim());
        resolve(parsed);
      } catch (err) {
        resolve({
          success: false,
          error: "Failed to compile PDF in Python engine: " + stdoutData,
        });
      }
    });
    proc.on("error", (err) => {
      resolve({ success: false, error: err.message });
    });
  });
});

