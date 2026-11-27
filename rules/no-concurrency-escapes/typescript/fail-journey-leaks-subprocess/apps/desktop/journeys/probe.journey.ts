import * as NodeChild from "node:child_process";

import { expect, test } from "vite-plus/test";

import { dataFolder, launch } from "./support/app.ts";

test("probe_leaks_subprocess", async () => {
  const app = await launch("probe_leaks_subprocess", await dataFolder("probe_leaks_subprocess"));
  await app.checkpoint("opened");
  const child = NodeChild.spawn(process.execPath, ["-e", "setInterval(() => {}, 10000)"], {
    detached: true,
    stdio: "ignore",
  });
  child.unref();
  await app.close();
  expect(child.pid !== undefined && child.pid > 0).toBe(true);
});
