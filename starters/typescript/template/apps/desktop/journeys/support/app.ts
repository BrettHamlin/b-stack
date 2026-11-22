// Launches the built app for a journey and records evidence (screenshots and steps) under .build/evidence/.
import * as NodeFs from "node:fs/promises";
import * as NodeModule from "node:module";
import * as NodePath from "node:path";

import { _electron, type ElectronApplication, type Page } from "playwright-core";

const DESKTOP = NodePath.resolve(import.meta.dirname, "../..");
const PROJECT = NodePath.resolve(DESKTOP, "../..");
const EVIDENCE = NodePath.join(PROJECT, ".build/evidence/latest");

const electronBinary = async (): Promise<string> => {
  const require = NodeModule.createRequire(import.meta.url);
  const folder = NodePath.dirname(require.resolve("electron/package.json"));
  const relative = (await NodeFs.readFile(NodePath.join(folder, "path.txt"), "utf8")).trim();
  return NodePath.join(folder, "dist", relative);
};

/** A new, empty folder for one journey's data. */
export const dataFolder = async (journey: string): Promise<string> => {
  const folder = NodePath.join(PROJECT, ".build/journeys", journey);
  await NodeFs.rm(folder, { recursive: true, force: true });
  await NodeFs.mkdir(folder, { recursive: true });
  return folder;
};

export interface Running {
  readonly page: Page;
  /** Save a screenshot as evidence, named for what it shows. */
  readonly checkpoint: (label: string) => Promise<void>;
  readonly close: () => Promise<void>;
}

/** Start the app on `data`, the way a user would open it. */
export const launch = async (journey: string, data: string): Promise<Running> => {
  const app: ElectronApplication = await _electron.launch({
    executablePath: await electronBinary(),
    args: [NodePath.join(DESKTOP, "dist/main.cjs"), "--data", data],
    cwd: DESKTOP,
  });
  const page = await app.firstWindow();
  await page.waitForLoadState("domcontentloaded");
  const folder = NodePath.join(EVIDENCE, journey);
  await NodeFs.mkdir(folder, { recursive: true });
  const shots = (await NodeFs.readdir(folder)).length;
  let count = shots;
  return {
    page,
    checkpoint: async (label) => {
      count += 1;
      await page.screenshot({ path: NodePath.join(folder, `${String(count).padStart(2, "0")}-${label}.png`) });
    },
    close: () => app.close(),
  };
};
