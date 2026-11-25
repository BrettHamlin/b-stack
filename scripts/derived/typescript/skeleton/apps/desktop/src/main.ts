// The main process: the composition root for real services. Usage: electron . [--data <folder>]
import { app, autoUpdater as nativeUpdater, BrowserWindow } from "electron";
import { autoUpdater } from "electron-updater";

const open = async (): Promise<void> => {
  await app.whenReady();
  const window = new BrowserWindow({
    width: 480,
    height: 640,
    webPreferences: {
      preload: `${import.meta.dirname}/preload.cjs`,
      contextIsolation: true,
      sandbox: true,
      nodeIntegration: false,
    },
  });
  await window.loadFile(`${import.meta.dirname}/renderer/index.html`);
};

// Updates: a packaged app built with an update feed (scripts/package.py, $BSTACK_UPDATE_URL) checks it at start,
// downloads a newer version (electron-updater checks its SHA-512) and installs it when the app quits. Each step is a
// line on stdout, which the update test reads; `update ready` means quitting now installs it.
const checkForUpdates = async (): Promise<void> => {
  if (!app.isPackaged) return;
  autoUpdater.on("update-available", (info) => process.stdout.write(`update available: ${info.version}\n`));
  autoUpdater.on("update-not-available", () => process.stdout.write("update not available\n"));
  autoUpdater.on("update-downloaded", (info) => {
    process.stdout.write(`update downloaded: ${info.version}\n`);
    // On macOS, Squirrel still has to fetch and stage the update before quitting installs it.
    if (process.platform === "darwin") {
      nativeUpdater.once("update-downloaded", () => process.stdout.write(`update ready: ${info.version}\n`));
    } else {
      process.stdout.write(`update ready: ${info.version}\n`);
    }
  });
  autoUpdater.on("error", (error) => process.stdout.write(`update error: ${error.message}\n`));
  const result = await autoUpdater.checkForUpdates();
  // The download runs on after the check returns; awaiting it keeps a failed download inside the catch below.
  await result?.downloadPromise;
};

app.on("window-all-closed", () => app.quit());
open().catch(() => app.exit(1));
checkForUpdates().catch((error: unknown) => {
  process.stdout.write(`update error: ${error instanceof Error ? error.message : "unknown"}\n`);
});
