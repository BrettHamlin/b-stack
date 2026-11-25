import { GreetingUi } from "@app/contracts";
import { expect, test } from "vite-plus/test";

import { dataFolder, launch } from "./support/app.ts";

test("greeting_works", async () => {
  const app = await launch("greeting_works", await dataFolder("greeting_works"));
  await app.fill(GreetingUi.name, "Ada");
  await app.click(GreetingUi.greet);
  await app.waitForText(GreetingUi.shown, "Hello, Ada!");
  expect(await app.lines(GreetingUi.shown)).toEqual(["Hello, Ada!"]);
  await app.checkpoint("greeted");
  await app.close();
});
