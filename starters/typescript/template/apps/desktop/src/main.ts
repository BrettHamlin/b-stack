// The main process: the composition root for real services. Usage: electron . [--data <folder>]
import { encodeTally, decodeTally, TallyChannel } from "@app/contracts";
import { fileTallyStore } from "@app/files";
import { current, TallyStore } from "@app/tally";
import * as NodeServices from "@effect/platform-node/NodeServices";
import * as Effect from "effect/Effect";
import * as Layer from "effect/Layer";
import { app, BrowserWindow, ipcMain } from "electron";

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

app.on("window-all-closed", () => app.quit());
open().catch(() => app.exit(1));
