---
name: new-project
description: Set up a new app repository from a b-stack starter, with enforcement built in from the first commit. Use when asked to start, create or scaffold a new app.
---

# New project

Agents copy whatever patterns exist first, so enforcement must exist before the first feature.

## 1. Confirm what's being built

Ask the user for the platform and a one-line description of the app. Available starters: `starters/ios/`. For any other platform, **stop and report** that no starter exists yet.

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

## 5. Report

- what was created
- the gate results and the rule-test summary line
- what's still missing (CI, branch protection)
- the evidence path from the verify gate
- what the user must do by hand (GitHub branch protection, code owners)
