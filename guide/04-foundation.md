# 04 · Foundation: protecting the enforcement

**Status:** Draft. Discussed and agreed.

Every layer is only as strong as the protection on its own configuration. If an agent can loosen a compiler flag, edit a lint config, add a module dependency or change the CI workflow, the cheapest "fix" for any failure is to weaken the check. The foundation makes sure that kind of change **needs a human**.

## The enforcement surface

These are all the files that decide what gets enforced. Every project should list its own, and treat the list itself as protected.

- Compiler and build config: language mode, strictness flags, warnings-as-errors
- Build manifests and dependency declarations (`Package.swift`, `Cargo.toml`, `package.json`, Gradle files, project manifests)
- Lint and checker configs, the checker's own source, allowlists and baselines
- The allowed dependency graph file
- CI workflow definitions
- CODEOWNERS
- Agent instructions and hook configuration (AGENTS.md, `.claude/`)

## Controls

1. **Agents have no admin rights and can't push to `main`.** All changes go through PRs.
2. **Branch protection with required status checks.** The layer-2 command must pass before merging.
3. **CODEOWNERS on the enforcement surface**, plus "require review from code owners." A PR that touches enforcement needs a named human.
4. **Close the CI-workflow hole.** On GitHub, a pull request's workflow runs from the PR's own branch, so a PR can edit the workflow that checks it. Protect `.github/` with CODEOWNERS, or use organization rulesets that require a workflow defined outside the PR.
5. **A settings check that verifies the settings.** Layer 2 asserts that strictness flags are on and that the dependency graph matches the committed file. Any change to those therefore shows up as a deliberate, reviewed edit.
6. **Agent hooks for fast feedback.** Block edits to protected paths and commands like `git commit --no-verify` before they happen. This saves wasted runs, but it's **not** a security boundary; CI is.

## The escalation rule

Protection without an escape valve produces creative workarounds. Every project's agent instructions should say:

> Never suppress, weaken or bypass a check. If the right fix isn't possible within the rules, stop and report what's blocking you and what you'd change.

Treat a well-reported block as a successful outcome. It often shows that a rule or API is missing something, which feeds the [correction loop](../playbook/correction-loop.md).

## What the foundation can't catch

Changes that break the intent while passing every check, such as hand-rolling a lock to avoid an actor or writing a test that asserts nothing. Those are caught by [verification](05-verification.md) and by [review focused on the enforcement layer](07-review.md).
