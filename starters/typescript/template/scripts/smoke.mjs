// Prove a packaged app runs on a system where the journeys can't run (Windows and Linux, where CI runs it, and the Intel
// macOS build under Rosetta): open it on an empty data folder, check what it shows, take the steps, check again, then open it again and
// check the result was kept. The checks and steps are the app's own, in apps/desktop/journeys/smoke.json.
// With an expected version, it also waits for the app to download that update, then reopens the app until it runs that
// version (the update installs when the app quits) and checks the result was kept.
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

// The app's stdout, collected from launch on: it reports its version and update steps there.
const said = (app) => {
  const output = { text: "" };
  app.process().stdout.on("data", (chunk) => {
    output.text += String(chunk);
  });
  return output;
};
const until = async (output, pattern, ms) => {
  const deadline = Date.now() + ms;
  while (Date.now() < deadline) {
    const found = pattern.exec(output.text);
    if (found) return found;
    await new Promise((resolve) => setTimeout(resolve, 200));
  }
  return null;
};

const open = async () => {
  // A first launch can be slow: Rosetta translates an Intel build on a Mac the first time it runs.
  const app = await _electron.launch({ executablePath: NodePath.resolve(executable), args, timeout: 180_000 });
  const output = said(app);
  const page = await app.firstWindow();
  await page.waitForLoadState("domcontentloaded");
  return { app, page, output };
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
await shows(first.page, plan.start);
for (const step of plan.steps) {
  if ("fill" in step) await first.page.getByTestId(step.fill).fill(step.text);
  else await first.page.getByTestId(step.click).click();
}
await shows(first.page, plan.after);
await first.page.screenshot({ path: NodePath.join(evidence, "01-after-steps.png") });
if (update) {
  if (!(await until(first.output, new RegExp(`update downloaded: ${update.replaceAll(".", "\\.")}`), 180_000))) {
    throw new Error(`no update to ${update} within 3 minutes; the app said:\n${first.output.text}`);
  }
  process.stdout.write(first.output.text);
}
await first.app.close();

// The update installs after the app quits (on Windows the installer runs on, on macOS Squirrel stages it): reopen
// until the new version runs, for up to 3 minutes.
const deadline = Date.now() + 180_000;
let again = await open();
if (update) {
  // Asked of the main process itself.
  const version = (opened) => opened.app.evaluate(({ app }) => app.getVersion());
  for (let running = await version(again); running !== update; running = await version(again)) {
    await again.app.close();
    if (Date.now() > deadline) throw new Error(`the app still runs ${running || "an unknown version"}, not ${update}`);
    await new Promise((resolve) => setTimeout(resolve, 5_000));
    again = await open();
  }
  process.stdout.write(`relaunched on ${update}\n`);
}
await shows(again.page, plan.after);
await again.page.screenshot({ path: NodePath.join(evidence, "02-after-relaunch.png") });
await again.app.close();
process.stdout.write(`smoke passed: ${executable}\n`);
