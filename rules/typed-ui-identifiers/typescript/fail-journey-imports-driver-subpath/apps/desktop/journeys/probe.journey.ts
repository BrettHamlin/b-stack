import { expect, test } from "vite-plus/test";

import * as driver from "../node_modules/playwright-core/index.js";

test("probe_journey", () => {
  expect(typeof driver).toBe("object");
});
