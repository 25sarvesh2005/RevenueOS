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

// 3. Run Pipeline Engine (Python Process)
ipcMain.handle("pipeline:run", async (event, params) => {
  const { excelPath, outputDir, projectName, currency } = params;

  return new Promise((resolve, reject) => {
    const pythonExe = process.platform === "win32" ? "python" : "python3";
    const scriptPath = path.resolve(__dirname, "..", "backend", "engine", "master.py");

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

        if (trimmed.startsWith("PIPELINE_PROGRESS:")) {
          try {
            const progressData = JSON.parse(trimmed.substring(18));
            mainWindow?.webContents.send("pipeline:progress", progressData);
          } catch (e) {}
        } else if (trimmed.startsWith("PIPELINE_COMPLETE:")) {
          try {
            finalManifest = JSON.parse(trimmed.substring(18));
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

// 5. Shell: Open Directory
ipcMain.handle("shell:open-folder", async (event, folderPath) => {
  if (folderPath && fs.existsSync(folderPath)) {
    await shell.openPath(folderPath);
    return true;
  }
  return false;
});

// 6. Shell: Launch / Open File (e.g., .pbit in Power BI Desktop)
ipcMain.handle("shell:launch-file", async (event, filePath) => {
  if (filePath && fs.existsSync(filePath)) {
    await shell.openPath(filePath);
    return true;
  }
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
