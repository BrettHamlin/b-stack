import { expect, test } from "vite-plus/test";

import { dataFolder, launch } from "./support/app.ts";

test("probe_journey", async () => {
  const app = await launch("probe_journey", await dataFolder("probe_journey"));
  const title = await app.page.title();
  await app.close();
  expect(title.length).toBeGreaterThan(0);
});
