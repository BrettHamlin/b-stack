import { expect, test } from "vite-plus/test";

import { dataFolder, launch } from "./support/app.ts";

test("probe_journey", async () => {
  const app = await launch("probe_journey", await dataFolder("probe_journey"));
  await app.checkpoint("opened");
  await app.close();
  expect(1).toBe(1);
});
