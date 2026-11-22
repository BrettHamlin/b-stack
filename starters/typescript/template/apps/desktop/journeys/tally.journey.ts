// Journeys: each runs the built app the way a user would and checks what they'd see. feature-map/ names which
// journeys prove which feature; the verify gate runs them and fails on any journey the map doesn't name.
import * as NodeFs from "node:fs/promises";

import { TallyUi } from "@app/contracts";
import type { Page } from "playwright-core";
import { expect, test } from "vite-plus/test";

import { dataFolder, launch } from "./support/app.ts";

const shown = async (page: Page, line: string): Promise<ReadonlyArray<string>> => {
  const items = page.getByTestId(TallyUi.items);
  await items.getByText(line, { exact: true }).waitFor();
  return items.locator("li").allInnerTexts();
};

const add = async (page: Page, name: string): Promise<void> => {
  await page.getByTestId(TallyUi.name).fill(name);
  await page.getByTestId(TallyUi.add).click();
};

test("tally_is_saved_across_runs", async () => {
  const data = await dataFolder("tally_is_saved_across_runs");
  const first = await launch("tally_is_saved_across_runs", data);
  expect(await shown(first.page, "(empty)")).toEqual(["(empty)"]);
  await add(first.page, "apple");
  await shown(first.page, "apple 1");
  await add(first.page, "apple");
  await add(first.page, "pear");
  expect(await shown(first.page, "pear 1")).toEqual(["apple 2", "pear 1"]);
  await first.checkpoint("added");
  await first.close();

  const again = await launch("tally_is_saved_across_runs", data);
  expect(await shown(again.page, "apple 2")).toEqual(["apple 2", "pear 1"]);
  await again.checkpoint("after-relaunch");
  await again.close();
});

test("failed_save_keeps_the_old_tally", async () => {
  const data = await dataFolder("failed_save_keeps_the_old_tally");
  const first = await launch("failed_save_keeps_the_old_tally", data);
  await add(first.page, "apple");
  await shown(first.page, "apple 1");
  await NodeFs.chmod(data, 0o555);
  try {
    await add(first.page, "apple");
    const error = first.page.getByTestId(TallyUi.error);
    await error.getByText("the tally couldn't be read or saved", { exact: true }).waitFor();
    expect(await shown(first.page, "apple 1")).toEqual(["apple 1"]);
    await first.checkpoint("save-failed");
  } finally {
    await NodeFs.chmod(data, 0o755);
  }
  await first.close();

  const again = await launch("failed_save_keeps_the_old_tally", data);
  expect(await shown(again.page, "apple 1")).toEqual(["apple 1"]);
  await again.checkpoint("after-relaunch");
  await again.close();
});

test("bad_name_is_refused", async () => {
  const data = await dataFolder("bad_name_is_refused");
  const first = await launch("bad_name_is_refused", data);
  await add(first.page, "two words");
  const error = first.page.getByTestId(TallyUi.error);
  await error.getByText("names are 1 to 32 letters, digits, '-' or '_'", { exact: true }).waitFor();
  expect(await shown(first.page, "(empty)")).toEqual(["(empty)"]);
  await first.checkpoint("refused");
  await first.close();

  const again = await launch("bad_name_is_refused", data);
  expect(await shown(again.page, "(empty)")).toEqual(["(empty)"]);
  await again.close();
});
