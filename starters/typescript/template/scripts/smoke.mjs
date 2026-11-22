// Prove a packaged app runs on the system it was built for: open it on an empty data folder, add an item, close it,
// open it again and check the item was kept. For the packages this Mac can't run (Windows, Linux); CI runs it there.
// The test ids are the example's (TallyUi in packages/contracts): change the steps when the example is replaced.
// Usage: node scripts/smoke.mjs <executable> <folder with node_modules/playwright-core> <evidence folder>
import * as NodeFs from "node:fs/promises";
import * as NodeModule from "node:module";
import * as NodeOs from "node:os";
import * as NodePath from "node:path";

const [executable, tools, evidence] = process.argv.slice(2);
if (!executable || !tools || !evidence) {
  throw new Error("usage: node scripts/smoke.mjs <executable> <folder with node_modules/playwright-core> <evidence folder>");
}
const { _electron } = NodeModule.createRequire(NodePath.join(NodePath.resolve(tools), "noop.js"))("playwright-core");
const data = await NodeFs.mkdtemp(NodePath.join(NodeOs.tmpdir(), "smoke-"));
await NodeFs.mkdir(evidence, { recursive: true });
// CI's Linux runners can't give Chromium's sandbox the setuid helper it needs.
const args = ["--data", data, ...(process.platform === "linux" ? ["--no-sandbox"] : [])];

const open = async () => {
  const app = await _electron.launch({ executablePath: NodePath.resolve(executable), args });
  const page = await app.firstWindow();
  await page.waitForLoadState("domcontentloaded");
  return { app, page };
};
const lines = async (page, line) => {
  const items = page.getByTestId("tally-items");
  await items.getByText(line, { exact: true }).waitFor({ timeout: 30_000 });
  return items.locator(":scope > *").allInnerTexts();
};
const expect = (actual, expected) => {
  if (JSON.stringify(actual) !== JSON.stringify(expected)) {
    throw new Error(`expected ${JSON.stringify(expected)}, saw ${JSON.stringify(actual)}`);
  }
};

const first = await open();
expect(await lines(first.page, "(empty)"), ["(empty)"]);
await first.page.getByTestId("tally-name").fill("apple");
await first.page.getByTestId("tally-add").click();
expect(await lines(first.page, "apple 1"), ["apple 1"]);
await first.page.screenshot({ path: NodePath.join(evidence, "01-added.png") });
await first.app.close();

const again = await open();
expect(await lines(again.page, "apple 1"), ["apple 1"]);
await again.page.screenshot({ path: NodePath.join(evidence, "02-after-relaunch.png") });
await again.app.close();
process.stdout.write(`smoke passed on ${process.platform}-${process.arch}: ${executable}\n`);
