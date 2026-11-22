import { expect, test } from "vite-plus/test";

test("probe_journey", async () => {
  const playwright = await import("playwright-core");
  expect(typeof playwright._electron.launch).toBe("function");
});
