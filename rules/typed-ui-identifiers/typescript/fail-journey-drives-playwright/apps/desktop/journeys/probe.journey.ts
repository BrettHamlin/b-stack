import { _electron } from "playwright-core";
import { expect, test } from "vite-plus/test";

test("probe_journey", async () => {
  const app = await _electron.launch({ args: ["."] });
  const page = await app.firstWindow();
  expect(await page.getByText("Add").count()).toBe(1);
  await app.close();
});
