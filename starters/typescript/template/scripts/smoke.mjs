// Prove a packaged app runs on the system it was built for, where the journeys can't run (Windows, Linux; CI runs it
// there): open it on an empty data folder, check what it shows, take the steps, check again, then open it again and
// check the result was kept. The checks and steps are the app's own, in apps/desktop/journeys/smoke.json.
// Usage: node scripts/smoke.mjs <executable> <folder with node_modules/playwright-core> <evidence folder>
import * as NodeFs from "node:fs/promises";
import * as NodeModule from "node:module";
import * as NodeOs from "node:os";
import * as NodePath from "node:path";

const [executable, tools, evidence] = process.argv.slice(2);
if (!executable || !tools || !evidence) {
  throw new Error("usage: node scripts/smoke.mjs <executable> <folder with node_modules/playwright-core> <evidence folder>");
}
const plan = JSON.parse(await NodeFs.readFile(new URL("../apps/desktop/journeys/smoke.json", import.meta.url), "utf8"));
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
const shows = async (page, { id, lines }) => {
  const element = page.getByTestId(id);
  await element.getByText(lines.at(-1), { exact: true }).first().waitFor({ timeout: 30_000 });
  const actual = await element.locator(":scope > *").allInnerTexts();
  if (JSON.stringify(actual) !== JSON.stringify(lines)) {
    throw new Error(`${id}: expected ${JSON.stringify(lines)}, saw ${JSON.stringify(actual)}`);
  }
};

const first = await open();
await shows(first.page, plan.start);
for (const step of plan.steps) {
  if ("fill" in step) await first.page.getByTestId(step.fill).fill(step.text);
  else await first.page.getByTestId(step.click).click();
}
await shows(first.page, plan.after);
await first.page.screenshot({ path: NodePath.join(evidence, "01-after-steps.png") });
await first.app.close();

const again = await open();
await shows(again.page, plan.after);
await again.page.screenshot({ path: NodePath.join(evidence, "02-after-relaunch.png") });
await again.app.close();
process.stdout.write(`smoke passed on ${process.platform}-${process.arch}: ${executable}\n`);
