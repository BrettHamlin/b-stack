---
name: new-project
description: Set up a new app repository from a b-stack starter, with enforcement built in from the first commit. Use when asked to start, create or scaffold a new app.
---

# New project

Agents copy whatever patterns exist first, so enforcement must exist before the first feature.

## 1. Confirm what's being built

Ask the user for the platform and a one-line description of the app. Available starters: `starters/ios/`. For any other platform, **stop and report** that no starter exists yet.

## 2. Agree the boundaries with the user

Propose, then confirm with the user. Don't decide these alone:
- modules and the allowed dependency direction between them
- what runs on the UI thread vs background, and who owns shared state
- which module owns persistence and networking
- the one approved way to do subscriptions, timers, cancellation and background work

Write the result into the new repo's `boundaries.yaml` (format: `starters/ios/template/boundaries.yaml`).

## 3. Create the repo from the template

Copy `starters/ios/template/` into the new repo:
- rename `AGENTS.template.md` → `AGENTS.md` and fill in its placeholders
- adjust `Modules/Package.swift` targets to match `boundaries.yaml`, keeping the `strict` settings on every target
- replace `@OWNER` in `CODEOWNERS` with the user's GitHub handle

Check `starters/ios/README.md` for what the template doesn't include yet. List each missing piece in your report; don't improvise substitutes.

## 4. Prove the rules fire

From the b-stack repo, run:

```sh
python3 scripts/test_rules.py --package <new-repo>/Modules
```

Every case must be PASS or PENDING (needs the checker). A FAIL means the setup doesn't enforce that rule: fix the setup, never the test case. A SKIP means the project lacks a module the case uses; report it.

## 5. Report

- what was created
- the rule-test summary line
- what's still pending or missing (checker, CI, branch protection, verification)
- anything the user must do by hand (e.g. GitHub branch protection)
