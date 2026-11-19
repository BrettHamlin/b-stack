# <App name>: agent instructions

## Before you change code

- Module dependencies are declared in `Project.swift`. Allowed system imports per module are in `Rules/Tests/ArchitectureRules/ModuleBoundaries.swift`.
- Use the existing approved APIs for <lifecycle, background work, persistence, navigation>. Don't introduce a second way to do the same thing.
- Pass dependencies in through initializers. They're wired together in two places only: `App` (real services) and `AppVerify` (test mode, the only place that may use `Fixtures`). Both compose each feature through the same view initializer.
- Features use TCA, shaped like `Targets/Settings*`: types and client protocols in `<Feature>Interface`, a `@Reducer` in `<Feature>Logic` (no I/O; effects call injected clients), a view in `<Feature>` that only sends actions, exhaustive `TestStore` tests in `<Feature>Tests` (examples, plus a property test that checks random action sequences against a model of the spec, like `NotificationSettingsPropertyTests`), plus a `feature-map/<id>.toml` entry and journey bodies in `Targets/AppVerifyJourneys` (generated XCTestCase adapters in `Targets/AppVerifyUITests`) that prove it works.

## Checks

```sh
python3 scripts/check.py        # compiler, tuist, swiftlint, harmonize, tests, verify: all must PASS
```

Run it before handing back. If it stops because the cache folder is unavailable (e.g. an external drive isn't mounted), report that; don't build elsewhere. A failure names the rule and how to fix it.

`verify` runs every feature-map journey in the running app (test mode) and writes evidence to `.build/evidence/latest/evidence.md`. For behaviour changes, read its screenshots and include the evidence path in your report. How to run, explore and add journeys: the `verify` skill (`.agents/skills/verify/SKILL.md`).

## Never weaken enforcement

Never suppress, disable, weaken or bypass a check. That includes suppression comments, editing `Project.swift` settings or dependencies, `.swiftlint.yml`, `Rules/`, `tools.toml`, `scripts/`, or CI.

**If the right fix isn't possible within the rules, stop and report:** what you were trying to do, which rule blocks it, and what you'd change. A clear report is a successful outcome.

## Don't write unrequested docs

No new markdown files, rule files or explanatory comments unless asked. Comments are for what code can't express.
