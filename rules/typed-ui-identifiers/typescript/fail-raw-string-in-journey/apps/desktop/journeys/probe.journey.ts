import { test } from "vite-plus/test";

import { dataFolder, launch } from "./support/app.ts";

test("probe_journey", async () => {
  const app = await launch("probe_journey", await dataFolder("probe_journey"));
  await app.click("probe-add");
  await app.close();
});
