// Prove a packaged app runs on a system where the journeys can't run (Windows and Linux, where CI runs it, and the Intel
// macOS build under Rosetta): open it on an empty data folder, check what it shows, take the steps, check again, then open it again and
// check the result was kept. The checks and steps are the app's own, in apps/desktop/journeys/smoke.json.
// With an expected version, it also waits for the app to download that update (the app reports it on stdout).
// Usage: node scripts/smoke.mjs <executable> <folder with node_modules/playwright-core> <evidence folder> [<version>]
import * as NodeFs from "node:fs/promises";
import * as NodeModule from "node:module";
import * as NodeOs from "node:os";
import * as NodePath from "node:path";

const [executable, tools, evidence, update] = process.argv.slice(2);
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
  // A first launch can be slow: Rosetta translates an Intel build on a Mac the first time it runs.
  const app = await _electron.launch({ executablePath: NodePath.resolve(executable), args, timeout: 180_000 });
  const page = await app.firstWindow();
  await page.waitForLoadState("domcontentloaded");
  return { app, page };
};
// The element's children read exactly `lines` (an empty list too), within 30 seconds.
const shows = async (page, { id, lines }) => {
  const element = page.getByTestId(id);
  await element.waitFor({ timeout: 30_000 });
  const deadline = Date.now() + 30_000;
  let actual = [];
  while (Date.now() < deadline) {
    actual = await element.locator(":scope > *").allInnerTexts();
    if (JSON.stringify(actual) === JSON.stringify(lines)) return;
    await page.waitForTimeout(200);
  }
  throw new Error(`${id}: expected ${JSON.stringify(lines)}, saw ${JSON.stringify(actual)}`);
};

const first = await open();
const updated = update
  ? new Promise((resolve, reject) => {
      let said = "";
      const timer = setTimeout(() => reject(new Error(`no update to ${update} within 3 minutes; the app said:\n${said}`)), 180_000);
      first.app.process().stdout.on("data", (chunk) => {
        said += String(chunk);
        if (said.includes(`update downloaded: ${update}`)) {
          clearTimeout(timer);
          resolve(said);
        }
      });
    })
  : Promise.resolve("");
await shows(first.page, plan.start);
for (const step of plan.steps) {
  if ("fill" in step) await first.page.getByTestId(step.fill).fill(step.text);
  else await first.page.getByTestId(step.click).click();
}
await shows(first.page, plan.after);
await first.page.screenshot({ path: NodePath.join(evidence, "01-after-steps.png") });
if (update) process.stdout.write(`${(await updated).trim()}\n`);
await first.app.close();

const again = await open();
await shows(again.page, plan.after);
await again.page.screenshot({ path: NodePath.join(evidence, "02-after-relaunch.png") });
await again.app.close();
process.stdout.write(`smoke passed: ${executable}\n`);
