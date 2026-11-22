// The main process: the composition root for real services. Usage: electron . [--data <folder>]
import { encodeTally, decodeTally, TallyChannel } from "@app/contracts";
import { fileTallyStore } from "@app/files";
import { current, TallyStore } from "@app/tally";
import * as NodeServices from "@effect/platform-node/NodeServices";
import * as Effect from "effect/Effect";
import * as Layer from "effect/Layer";
import { app, BrowserWindow, ipcMain } from "electron";
import { autoUpdater } from "electron-updater";

const dataFolder = (argv: ReadonlyArray<string>): string => {
  const flag = argv.indexOf("--data");
  return (flag === -1 ? undefined : argv[flag + 1]) ?? app.getPath("userData");
};

const store = fileTallyStore(dataFolder(process.argv)).pipe(Layer.provide(NodeServices.layer));

ipcMain.handle(TallyChannel.load, () =>
  Effect.runPromise(
    current.pipe(
      Effect.map(encodeTally),
      Effect.orElseSucceed(() => null),
      Effect.provide(store),
    ),
  ),
);

ipcMain.handle(TallyChannel.save, (_event, data: unknown) =>
  Effect.runPromise(
    Effect.gen(function* () {
      const tally = yield* decodeTally(data);
      const saved = yield* TallyStore;
      yield* saved.save(tally);
      return true;
    }).pipe(
      Effect.orElseSucceed(() => false),
      Effect.provide(store),
    ),
  ),
);

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
// line on stdout, which the update test reads.
const checkForUpdates = async (): Promise<void> => {
  if (!app.isPackaged) return;
  autoUpdater.on("update-available", (info) => process.stdout.write(`update available: ${info.version}\n`));
  autoUpdater.on("update-not-available", () => process.stdout.write("update not available\n"));
  autoUpdater.on("update-downloaded", (info) => process.stdout.write(`update downloaded: ${info.version}\n`));
  autoUpdater.on("error", (error) => process.stdout.write(`update error: ${error.message}\n`));
  await autoUpdater.checkForUpdates();
};

app.on("window-all-closed", () => app.quit());
open().catch(() => app.exit(1));
checkForUpdates().catch((error: unknown) => {
  process.stdout.write(`update error: ${error instanceof Error ? error.message : "unknown"}\n`);
});
