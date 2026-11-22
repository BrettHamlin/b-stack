# TypeScript starter

An Electron desktop app laid out like [T3 Code](https://github.com/pingdotgg/t3code): a main process and a React renderer, shared contracts, Effect services, pnpm, and vite-plus (oxlint, Vitest). Copied into a new repo by the [new-project skill](../../skills/new-project/SKILL.md). Only what's listed as built exists.

## What's built

| Piece | Path | Status |
|---|---|---|
| pnpm workspace: contracts, one example feature, one platform package, the Electron main process and preload, the React renderer | `template/package.json`, `template/pnpm-workspace.yaml`, `template/packages/`, `template/apps/` | ✅ Builds with the settings below |
| Module shape: package roles by folder, the roles each may use, the third-party packages each may use, the effect modules logic may import | `template/arch/shape.json` | ✅ Agents add packages in the shape's folders without editing protected files |
| Compiler settings per role: no DOM or Node.js in contracts and features; Node.js in platform and desktop; DOM and React in the renderer | `template/tsconfig.base.json`, `template/tsconfig.effect.json`, `template/arch/tsconfig/` | ✅ Packages only extend their role's config (arch gate) |
| Example feature: a tally of named items (record, show, a failed save keeps the old tally), with example tests and a property test | `template/packages/features/tally/`, `template/packages/platform/files/`, `template/apps/` | ✅ |
| Property test for the example feature: 200 seeded random sequences of records and failed saves, checked step by step against a model | `template/packages/features/tally/tests/property.test.ts` | ✅ Under a second. No library: a seeded generator in the file |
| Gate command: compiler, lint, deps, arch, settings, tests, verify | `template/scripts/check.py` | ✅ Every gate passes in about 15 s; rule suite 124/124 (2026-11-22) |
| Lint rules of our own (oxlint JS plugin): imports inside the shape and declared, no ambient declarations, no module state, no skipped tests, typed UI identifiers | `template/arch/lint/index.ts` | ✅ |
| Typed UI identifiers: views set `data-testid` from `UiId`s in contracts; journeys see the app only as a `Screen` that takes `UiId`s | `template/packages/contracts/src/ui.ts`, `template/apps/desktop/journeys/support/app.ts` | ✅ A raw string doesn't compile; journeys can't import Playwright |
| Whole-value test assertions: no partial matchers, no test without an assertion | `template/vite.config.ts` | ✅ |
| Fixtures: test setup that only journeys and tests can use (a devDependency the shipped app can't import) | `template/packages/fixtures/` | ✅ One journey starts from a saved tally |
| Architecture checks: packages and manifests against the shape, per-package tsconfig, config files, suppression comments | `template/scripts/arch.py` | ✅ |
| Dependency checks: every installed package from the npm registry, licenses (from pnpm's own report) | `template/scripts/deps.py` | ✅ |
| Verification: feature map, journeys that launch the built Electron app through Playwright, screenshots as evidence | `template/scripts/verify.py`, `template/apps/desktop/journeys/`, `template/feature-map/` | ✅ Four tally journeys, about 5 s on an idle Mac mini |
| Pinned tools, checksum-verified, no global install | `template/tools.toml`, `template/scripts/tools.py`, `template/pnpm-lock.yaml` | ✅ Node.js 26.13.1, pnpm 12.14.0; Electron's binary checked against its package's checksums |
| Installed packages, Electron and build output in a configurable cache folder | `template/scripts/paths.py`, `template/scripts/tools.py` | ✅ `.build/` becomes a link into it; stops if the folder is missing |
| New-feature command: a feature package, its feature-map entry and a journey; the test and journey fail until written | `template/scripts/new_feature.py` | ✅ |
| Packaging: macOS (Apple silicon and Intel), Windows (x64) and Linux (x64) with electron-builder 26.16.1, from the locked Electron (other platforms' binaries checked against its checksums.json); every journey runs against the Apple silicon package, and `scripts/smoke.mjs` (the app's own steps, in `apps/desktop/journeys/smoke.json`) proves the Intel macOS package under Rosetta and the Windows and Linux packages on those systems. macOS signing with the hardened runtime and notarizing when the Apple credentials are set | `template/scripts/package.py`, `template/scripts/build.py`, `template/scripts/smoke.mjs` | ✅ Unsigned without credentials; CI proves signing with a throwaway certificate. Notarizing is configured but not run here (needs an Apple Developer account) |
| CI: `check.py` and `package.py --all` on a macOS runner, with pnpm refusing to change the lockfile, then the smoke test on Windows and Linux runners; signing from repository secrets; evidence and packages uploaded | `template/.github/workflows/check.yml` | ✅ Make `check` and both `smoke` jobs required status checks; b-stack's own CI runs the same commands on the starter |
| Settings gate: the compiler options each package gets, the Effect diagnostics, the lint and test settings in effect, pnpm's hoisting and install scripts, and CODEOWNERS coverage must match `arch/settings.json` | `template/scripts/settings.py`, `template/arch/settings.json` | ✅ Weakening one means changing the baseline in the same reviewed change |
| Check record, observe mode: check.py records the git tree each run saw; `audit` says whether a commit's tree was checked; each Claude Code hand-back is logged; each commit gets a `Checked:` trailer. Never blocks | `template/scripts/handback.py`, `template/.claude/settings.json`, `template/.githooks/` | ✅ The iOS starter's, with this starter's gates. `git config core.hooksPath .githooks` turns on the trailer |
| Verify skill for agents: the gate, exploring with `verify.py look`, adding a feature | `template/.agents/skills/verify/` (linked from `.claude/skills`) | ✅ |
| Agent instructions, CODEOWNERS | `template/AGENTS.template.md`, `template/CODEOWNERS` | ✅ Draft; placeholders to fill in |

The pins are T3 Code's (2026-11-21): Node.js 26.13.1, pnpm 12.14.0, vite-plus 1.4.0 (oxlint 1.89.0, oxlint-tsgolint 7.0.2004, Vitest 5.0.5), @effect/tsgo 0.67.1 (TypeScript 7.0.2), Effect 4.1.5, Electron 44.10.1, React 19.3.0, playwright-core 1.64.1, electron-builder 26.16.1. `tsconfig.effect.json` is T3 Code's, unchanged (MIT). The Node.js and pnpm pins are the `darwin-arm64` builds.

## Module shape

| Package folder | Role | May depend on | Compiles with |
|---|---|---|---|
| `packages/contracts` | contracts: types, schemas and the IPC bridge shared by every process | nothing | ES2024 only |
| `packages/features/<name>` | feature: logic, plus the Effect services it needs from outside | contracts | ES2024 only |
| `packages/platform/<name>` | platform: real I/O, implementing feature services | contracts, features | Node.js |
| `packages/fixtures` | fixtures: test setup; only a devDependency of the desktop app, for its journeys | contracts, features, platform | Node.js |
| `apps/desktop` | desktop: Electron's main process (a composition root) and preload | contracts, features, platform | Node.js, Electron |
| `apps/web` | web: the renderer (a composition root), reaching the main process only through the preload's bridge | contracts, features | DOM, React |

This table is `template/arch/shape.json` (protected). `pnpm-workspace.yaml` lists the same folders, so a new package in one of them is installed and checked without editing a protected file. A package's own `package.json` declares its dependencies; the arch gate checks each one against the shape, and pnpm makes only declared packages visible to it (`hoist: false`). No third-party packages beyond the starter's are allowed; each role's `external` list is where the owner adds them.

## Strict settings

| Setting | Where | Effect |
|---|---|---|
| `strict`, `noUncheckedIndexedAccess`, `exactOptionalPropertyTypes`, `noPropertyAccessFromIndexSignature`, `noImplicitReturns`, `verbatimModuleSyntax`, `erasableSyntaxOnly` | `tsconfig.base.json` | T3 Code's settings plus a few more |
| `lib: ["ES2024"]`, `types: []`, `rootDir: ${configDir}` | `tsconfig.base.json`, `arch/tsconfig/` | Logic has no I/O to call; no package can import another's files by path |
| About 90 Effect diagnostics as errors | `tsconfig.effect.json` | Services must be provided; no global Date, timers, fetch or console in Effect code; Node built-ins through Effect's services |
| Type-aware oxlint: `no-explicit-any`, `no-non-null-assertion`, `consistent-type-assertions` (never), `no-unsafe-*`, `switch-exhaustiveness-check`, `no-floating-promises`, `no-misused-promises`, `no-deprecated`, raw timers banned | `vite.config.ts` | Errors, with `--deny-warnings` |
| `hoist: false`, `publicHoistPattern: []` | `pnpm-workspace.yaml` | An undeclared package can't be imported |
| `retry: 0`, `allowOnly: false`, fake timers | `vite.config.ts` | Flaky tests are fixed, not retried (T3 Code's settings) |
| Sandboxed renderer: `contextIsolation`, `sandbox`, no `nodeIntegration` | `apps/desktop/src/main.ts` | The page can't reach Node.js |

## Not built yet (in order)

1. **Windows signing:** needs a Windows code-signing certificate (usually held in a hardware module or a signing service), and signing from a Mac needs a tool electron-builder doesn't bring.
2. **Notarizing, run for real:** configured in `package.py`, but never run here (needs an Apple Developer account).
3. **Installers:** packages are plain archives (`.zip`, `.tar.gz`); no `.dmg`, NSIS installer, AppImage or auto-update.
4. **Arm64 Windows and Linux packages.**
