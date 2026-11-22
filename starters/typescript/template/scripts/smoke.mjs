// Prove a packaged app runs on a system where the journeys can't run (Windows and Linux, where CI runs it, and the Intel
// macOS build under Rosetta): open it on an empty data folder, check what it shows, take the steps, check again, then open it again and
// check the result was kept. The checks and steps are the app's own, in apps/desktop/journeys/smoke.json.
// With an expected version, it also waits for the app to download that update, then reopens the app until it runs that
// version (the update installs when the app quits) and checks the result was kept.
// Usage: node scripts/smoke.mjs <executable> <folder with node_modules/playwright-core> <evidence folder> [<version>]
import * as NodeChild from "node:child_process";
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
const log = (line) => process.stdout.write(`[${new Date().toISOString()}] ${line}\n`);
// Every wait has a limit, so a hang fails with what it was waiting for instead of running into the job's timeout.
const within = (promise, ms, what) =>
  Promise.race([promise, new Promise((_, reject) => setTimeout(() => reject(new Error(`${what}: no answer in ${ms / 1000}s`)), ms))]);
// Windows: the update's installer (named <app>-<version>-win-<arch>.exe) runs on after the app quits.
const installing = (version) =>
  process.platform === "win32" &&
  NodeChild.execFileSync("tasklist", ["/FO", "CSV", "/NH"], { encoding: "utf8" }).includes(`-${version}-win-`);
// Windows: every process of the app and its installer, with its parent and command line, for a failure report.
const processes = () =>
  process.platform !== "win32"
    ? ""
    : NodeChild.execFileSync(
        "powershell",
        ["-NoProfile", "-Command",
          "Get-CimInstance Win32_Process | Where-Object { $_.Name -like 'starter*' -or $_.CommandLine -like '*starter*' } | " +
          "Format-List ProcessId,ParentProcessId,Name,CommandLine | Out-String -Width 400"],
        { encoding: "utf8" },
      );
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
  if (!(await until(first.output, new RegExp(`update ready: ${update.replaceAll(".", "\\.")}`), 180_000))) {
    throw new Error(`no update to ${update} within 3 minutes; the app said:\n${first.output.text}`);
  }
  process.stdout.write(first.output.text);
}
log("closing the app");
// The app may already be gone (the update's installer can end it): don't wait on it for long.
await within(first.app.close(), 60_000, "closing the app").catch((error) => log(String(error)));
log(`closed\n${processes()}`);

// The update installs after the app quits (on Windows the installer runs on, on macOS Squirrel stages it): reopen
// until the new version runs, for up to 3 minutes.
const deadline = Date.now() + 180_000;
// Asked of the main process itself. A launch can fail while an installer is replacing the app: try again until the
// deadline.
const version = (opened) => within(opened.app.evaluate(({ app }) => app.getVersion()), 30_000, "asking the version");
let again;
for (let running = "", failure = ""; ; failure = "") {
  if (update && installing(update)) {
    failure = "its installer is still running";
  } else {
    try {
      again = await within(open(), 200_000, "opening the app");
      running = update ? await version(again) : "";
      log(`running ${running || "(no update expected)"}`);
      if (!update || running === update) break;
      await within(again.app.close(), 60_000, "closing the app").catch((error) => log(String(error)));
    } catch (error) {
      failure = String(error);
    }
  }
  log(`not yet: ${failure || `runs ${running}`}`);
  if (Date.now() > deadline) {
    throw new Error(`the app still runs ${running || "an unknown version"}, not ${update}: ${failure}\n${processes()}`);
  }
  await new Promise((resolve) => setTimeout(resolve, 5_000));
}
if (update) process.stdout.write(`relaunched on ${update}\n`);
await shows(again.page, plan.after);
await again.page.screenshot({ path: NodePath.join(evidence, "02-after-relaunch.png") });
await again.app.close();
process.stdout.write(`smoke passed: ${executable}\n`);
