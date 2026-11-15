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
- the first features (each becomes `<Feature>Interface` + `<Feature>`)
- which module owns persistence and networking (default: Platform)
- the one approved way to do subscriptions, timers, cancellation and background work

## 3. Create the repo from the template

Copy `starters/ios/template/` into the new repo, then:
- rename `AGENTS.template.md` → `AGENTS.md` and fill in its placeholders; add `CLAUDE.md` containing `@AGENTS.md`
- replace the example Settings feature with the agreed features in `Project.swift`, `Targets/`, and `Rules/Tests/ArchitectureRules/ModuleBoundaries.swift`, keeping the `strict` settings on every target
- replace `@OWNER` in `CODEOWNERS` with the user's GitHub handle

Check `starters/ios/README.md` for what the template doesn't include yet. List each missing piece in your report; don't improvise substitutes.

## 4. Prove the gates work

In the new repo: `python3 scripts/check.py` must PASS every gate.

Then, from b-stack: `python3 scripts/test_rules.py --project <new-repo>`. Every case must PASS. A FAIL means the new repo doesn't enforce that rule: fix the setup, never the test case. A SKIP means the new repo lacks a target the case uses (e.g. you renamed Settings); report it.

## 5. Report

- what was created
- the gate results and the rule-test summary line
- what's still missing (CI, branch protection, verification)
- what the user must do by hand (GitHub branch protection, code owners)
