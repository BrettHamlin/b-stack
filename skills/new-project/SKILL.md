---
name: new-project
description: Set up a new app repository from a b-stack starter, with enforcement built in from the first commit. Use when asked to start, create or scaffold a new app.
---

# New project

Agents copy whatever patterns exist first, so enforcement must exist before the first feature.

## 1. Confirm what's being built

Ask the user for the platform and a one-line description of the app. Available starters: `starters/ios/` (an iOS app), `starters/rust/` (a Rust workspace with a binary), `starters/typescript/` (an Electron desktop app laid out like T3 Code) and `starters/android/` (a Kotlin Android app with Compose). For any other platform, **stop and report** that no starter exists yet. The steps below are for iOS; for Rust, see [Rust](#rust); for TypeScript, see [TypeScript](#typescript); for Android, see [Android](#android).

## 2. Agree the module plan with the user

Propose, then confirm with the user. Don't decide alone:
- the first features (each becomes `<Feature>Interface`, `<Feature>Logic`, `<Feature>` and `<Feature>Tests`, plus a `feature-map/<id>.toml` entry and journeys, following the Settings example)
- for each feature, the journeys that prove it works from the user's side, and the fixtures (starting states) they need
- which module owns persistence and networking (default: Platform)
- the one approved way to do subscriptions, timers, cancellation and background work

## 3. Create the repo from the template

Copy `starters/ios/template/` into the new repo with a copy that keeps symlinks (`cp -R`, `rsync -a`): `Rules/Sources/ModuleShape/` links to `Tuist/ProjectDescriptionHelpers/`, so the rules check the same feature list Tuist builds from. Then:
- rename `AGENTS.template.md` → `AGENTS.md` and fill in its placeholders; add `CLAUDE.md` containing `@AGENTS.md`
- replace the example Settings feature with the agreed features: declare them, and the links they use, in `Tuist/ProjectDescriptionHelpers/Features.swift`, and replace the code in `Targets/`, `Targets/Fixtures`, `Targets/AppVerify*` and `feature-map/`. Don't edit `Project.swift`, `ModuleShape.swift` or `Rules/`: targets, dependencies and allowed imports come from the declaration. If a feature needs a link `Features.swift` can't express, it's outside the module shape: stop and report
- replace `@OWNER` in `CODEOWNERS` with the user's GitHub handle
- `git init`, then `git config core.hooksPath .githooks` so every commit gets a `Checked:` trailer

Check `starters/ios/README.md` for what the template doesn't include yet. List each missing piece in your report; don't improvise substitutes.

## 4. Prove the gates work

In the new repo: `python3 scripts/check.py` must PASS every gate, including `verify`. Open `.build/evidence/latest/evidence.md` and check its screenshots show what each journey claims.

Then, from b-stack: `python3 scripts/test_rules.py --project <new-repo>`. It runs every case that applies to any app; cases written against the starter's Settings example are listed as OUT with their reason. Zero FAIL is required. A FAIL means the new repo doesn't enforce that rule: fix the setup, never the test case. A SKIP means the new repo lacks a target a general case uses; report it.

## Rust

Steps 1, 2 and 5 are the same. In step 2, each feature is a `no_std` crate in `crates/features/<name>/` (logic plus traits for what it needs), with real I/O in a `crates/platform/<name>/` crate and wiring in `crates/app`, following the tally example. Then:
- copy `starters/rust/template/` into the new repo; rename `AGENTS.template.md` → `AGENTS.md`, fill in its placeholders, and add `CLAUDE.md` containing `@AGENTS.md`
- replace the tally example (`crates/features/tally`, `crates/platform/files`, the app's commands, `crates/app/tests/journeys.rs`, `feature-map/`) with the agreed features. Don't edit the root `Cargo.toml`, `arch/`, `clippy.toml` or `deny.toml`. A third-party crate needs the owner: list the ones the features need and ask before adding them to `arch/shape.toml`
- add each agreed feature with `python3 scripts/new_feature.py <name>`, then write its logic, test and journey
- replace `@OWNER` in `CODEOWNERS`; `git init`, then `git config core.hooksPath .githooks` so every commit gets a `Checked:` trailer; after the first push, make the `check` job (`.github/workflows/check.yml`) a required status check, with code-owner review; keep `crates/app/smoke.toml` about the app's main path
- check `starters/rust/README.md` for what the template doesn't include yet, and list it in your report

Prove it: `python3 scripts/check.py` must PASS every gate in the new repo, `.build/evidence/latest/evidence.md` must show each journey doing what it claims, and `python3 scripts/package.py` must build the release binary and pass its smoke run. Then, from b-stack, `python3 scripts/test_rules.py --project <new-repo>` (the platform is found from the repo's files) must give zero FAIL.

## TypeScript

Steps 1, 2 and 5 are the same. In step 2, each feature is a package in `packages/features/<name>/` (logic plus the Effect services it needs, with no I/O), with real I/O in a `packages/platform/<name>/` package, wiring in `apps/desktop` (the main process) and `apps/web` (the renderer), and anything both processes share in `packages/contracts`, following the tally example. Then:
- copy `starters/typescript/template/` into the new repo, leaving out `node_modules/`, `dist/` and `.build/`; rename `AGENTS.template.md` → `AGENTS.md`, fill in its placeholders, and add `CLAUDE.md` containing `@AGENTS.md`
- replace the tally example (`packages/features/tally`, `packages/platform/files`, the tally parts of `packages/contracts`, `apps/desktop/src`, `apps/web/src`, `apps/desktop/journeys/tally.journey.ts`, `apps/desktop/journeys/smoke.json`, `feature-map/`) with the agreed features. `smoke.json` is what the Windows and Linux smoke jobs check: a start state, a few steps by test id, and the result, which must survive a relaunch. Don't edit the root `package.json`, `pnpm-workspace.yaml`, `vite.config.ts`, the tsconfig files or `arch/`. A third-party package needs the owner: list the ones the features need and ask before adding them to `arch/shape.json`
- add each agreed feature with `python3 scripts/new_feature.py <name>`, then write its logic, test and journey
- replace `@OWNER` in `CODEOWNERS`; `git init`, then `git config core.hooksPath .githooks` so every commit gets a `Checked:` trailer; after the first push, the owner sets up code-owner review ([GitHub](#github-code-owner-review)), and for signed packages and updates add the signing secrets and the UPDATE_URL variable the workflow names
- check `starters/typescript/README.md` for what the template doesn't include yet, and list it in your report

Prove it: `python3 scripts/check.py` must PASS every gate in the new repo (it installs the packages first), and the screenshots and `.build/evidence/latest/evidence.md` must show each journey doing what it claims, and `python3 scripts/package.py` must build the app and pass every journey against it. Then, from b-stack, `python3 scripts/test_rules.py --project <new-repo>` must give zero FAIL.

## Android

Steps 1, 2 and 5 are the same. In step 2, each feature is three modules in `features/<name>/`: `api` (types, client interfaces, `<Feature>Ui` identifiers), `logic` (common code: the model, with Turbine tests of every state and a property test) and `ui` (Compose screens and the entry point both apps call), with real I/O in `platform/<name>` and wiring in `app` (real services) and `app-verify` (fixtures), following the tally example. Then:
- copy `starters/android/template/` into the new repo, leaving out `.build/`; rename `AGENTS.template.md` → `AGENTS.md`, fill in its placeholders, add `CLAUDE.md` containing `@AGENTS.md`, and set `bstack.applicationId` in `gradle.properties`
- replace the tally example (`features/tally`, `platform/files`, the tally parts of `fixtures`, `app`, `app-verify`, `verify/journeys`, `feature-map/`) with the agreed features: `python3 scripts/new_feature.py <name>` creates each feature's three modules, its map entry and a journey stub, and links them; show its entry point in `app` and `app-verify`, then write its logic, test and journey (run `python3 scripts/verify.py adapters` after adding journeys). Each module declares what it uses in its `module.toml`. Don't edit `arch/`, `build-logic/`, `gradle/`, the root Gradle files or `tools.toml`. A library needs the owner: list the ones the features need and ask before adding them to `gradle/libs.versions.toml` and `arch/shape.json` (and regenerating `gradle/verification-metadata.xml`)
- replace `@OWNER` in `CODEOWNERS`; `git init`, then `git config core.hooksPath .githooks` so every commit gets a `Checked:` trailer; after the first push, the owner sets up code-owner review ([GitHub](#github-code-owner-review)). For signed release builds of `main`, the user adds an upload key as the repository secrets the workflow names; until then `python3 scripts/package.py` signs with a throwaway test key
- check `starters/android/README.md` for what the template doesn't include yet, and list it in your report

Prove it: `python3 scripts/check.py` must PASS every gate in the new repo (the first run downloads the JDK, Gradle, the Android SDK and an emulator image into the cache folder), and `.build/evidence/latest/evidence.md` must show each journey doing what it claims. Then, from b-stack, `python3 scripts/test_rules.py --project <new-repo>` must give zero FAIL.

## GitHub: code-owner review

`CODEOWNERS` protects nothing until GitHub requires code-owner review, and GitHub never counts a pull request author's own approval. So agents act as a separate GitHub user, and the default branch gets a ruleset. The owner does both; agents never change repository settings. The Android and TypeScript workflows' first step (`scripts/branch_rules.py`) fails until the ruleset is in place, so CI on the first push fails until then; re-run it after.

1. **The machine user.** The owner creates a GitHub account for agents (any name; it isn't the code owner), invites it to the repository with the Write role (not Maintain or Admin), and on that account creates a classic personal access token with the `repo` and `workflow` scopes. Agents run with `GH_TOKEN` set to that token (`gh auth setup-git` makes `git push` use it). The owner keeps Admin, and `@OWNER` in `CODEOWNERS` is the owner's handle, so the owner's approval is a second person's.
2. **The ruleset**, run by the owner (`<owner>/<repo>` is the new repository). It requires a pull request on the default branch with code-owner review and no other approvals, so a pull request that touches no code-owned file merges once the checks pass, and one that does waits for the owner; and it requires the CI checks. Nobody bypasses it. Android:

   ```sh
   gh api -X POST repos/<owner>/<repo>/rulesets --input - <<'EOF'
   {"name": "code owners review enforcement changes", "target": "branch", "enforcement": "active",
    "conditions": {"ref_name": {"include": ["~DEFAULT_BRANCH"], "exclude": []}}, "bypass_actors": [],
    "rules": [
     {"type": "pull_request", "parameters": {"required_approving_review_count": 0, "require_code_owner_review": true,
      "dismiss_stale_reviews_on_push": true, "require_last_push_approval": false, "required_review_thread_resolution": false}},
     {"type": "required_status_checks", "parameters": {"strict_required_status_checks_policy": false,
      "required_status_checks": [{"context":"check"}]}}]}
   EOF
   ```

   TypeScript: the same, with `"required_status_checks": [{"context":"check"}, {"context":"installers win-x64"}, {"context":"installers win-arm64"}, {"context":"installers linux-x64"}, {"context":"installers linux-arm64"}]`. iOS and Rust: the same rules with their workflow's job names; their workflows don't check the ruleset yet. A private repository needs a paid GitHub plan for rulesets to apply; on the free plan, `branch_rules.py` finds no rules and CI fails.

Paths every feature edits (the feature map, journeys, fixtures, the composition roots) aren't code-owned, so features don't wait for the owner. Instead, the verify gate fails when a journey or feature the base branch has is gone, unless `arch/retired.toml` (code-owned) lists it.

## 5. Report

- what was created
- the gate results and the rule-test summary line
- what's still missing (CI, the ruleset)
- the evidence path from the verify gate
- what the user must do by hand: the machine user and the ruleset ([GitHub](#github-code-owner-review))
