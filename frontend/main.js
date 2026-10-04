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
    backgroundColor: "#1B1A19",
    title: "RevenueOS Studio – Power BI Desktop Replica Engine",
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
    title: "Select Source Excel Workbook",
    properties: ["openFile"],
    filters: [
      { name: "Excel Workbooks", extensions: ["xlsx", "xls", "xlsm"] },
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
    let accumulatedError = "";

    proc.stdout.on("data", (data) => {
      const text = data.toString("utf-8");
      const lines = text.split("\n");

      for (const line of lines) {
        const trimmed = line.trim();
        if (!trimmed) continue;

        if (trimmed.startsWith("PIPELINE_PROGRESS:") || trimmed.startsWith("EVENT_JSON:")) {
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
          } catch (e) {}
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
      if (code === 0 && finalManifest) {
        resolve({ success: true, manifest: finalManifest });
      } else {
        reject(
          new Error(
            accumulatedError || `Pipeline failed with exit code ${code}`
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
  const samplePath = path.resolve(
    __dirname,
    "..",
    "data",
    "raw",
    "excel",
    "revenueos_sample.xlsx"
  );
  if (fs.existsSync(samplePath)) {
    return samplePath;
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

// 8. Load Precompiled Initial Model (Portable)
ipcMain.handle("app:load-initial-model", () => {
  const candidates = [
    path.resolve(__dirname, "model_data.json"),
    path.resolve(__dirname, "model_data_sample.json"),
  ];

  for (const modelPath of candidates) {
    if (fs.existsSync(modelPath)) {
      try {
        const raw = fs.readFileSync(modelPath, "utf-8");
        const data = JSON.parse(raw);
        return normalizeManifestPaths(data);
      } catch (e) {
        console.error("Failed to parse initial model from", modelPath, e);
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

