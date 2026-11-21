# <App name>: agent instructions

## Before you change code

- Modules and their dependencies come from the module shape (`Tuist/ProjectDescriptionHelpers/ModuleShape.swift`, the owner's) and the feature list in `Tuist/ProjectDescriptionHelpers/Features.swift` (yours). To add a feature, create its folders and add it to `Features.swift`; to use a link the shape allows (e.g. Platform implementing a feature's client, App using Platform), add that link there. Don't edit `Project.swift` or `Rules/`: the gates fail if the project differs from the declaration. A link `Features.swift` can't express is outside the shape: stop and report.
- Use the existing approved APIs for <lifecycle, background work, persistence, navigation>. Don't introduce a second way to do the same thing.
- Pass dependencies in through initializers. They're wired together in two places only: `App` (real services) and `AppVerify` (test mode, the only place that may use `Fixtures`). Both compose each feature through the same view initializer.
- Features use TCA, shaped like `Targets/Settings*`: types and client protocols in `<Feature>Interface`, a `@Reducer` in `<Feature>Logic` (no I/O; effects call injected clients), a view in `<Feature>` that only sends actions, exhaustive `TestStore` tests in `<Feature>Tests` (examples, plus a property test that checks random action sequences against a model of the spec, like `NotificationSettingsPropertyTests`), plus a `feature-map/<id>.toml` entry and journey bodies in `Targets/AppVerifyJourneys` (generated XCTestCase adapters in `Targets/AppVerifyUITests`) that prove it works.

## Checks

```sh
python3 scripts/check.py        # compiler, tuist, swiftlint, harmonize, tests, verify: all must PASS
```

Run it before handing back. If it stops because the cache folder is unavailable (e.g. an external drive isn't mounted), report that; don't build elsewhere. A failure names the rule and how to fix it.

`verify` runs every feature-map journey in the running app (test mode) and writes evidence to `.build/evidence/latest/evidence.md`. For behaviour changes, read its screenshots and include the evidence path in your report. How to run, explore and add journeys: the `verify` skill (`.agents/skills/verify/SKILL.md`).

## Using the simulator by hand

Other checkouts of this app on the Mac use the same simulators. Run every command that touches a simulator by hand (`agent-device`, `xcrun simctl`, screen recordings for PR evidence) through:

```sh
python3 scripts/simulator.py run -- <command>                  # waits while a gate elsewhere uses the simulator, then holds it
python3 scripts/simulator.py run --for 20 -- xcrun simctl io booted recordVideo --force demo.mov   # 20 s recording
```

The command gets `$BSTACK_SIMULATOR_ID`. `check.py` and `verify.py` already take the same lock. Nothing stops a tool run outside it from breaking another checkout's journeys, so don't. Installs don't clash: AppVerify and its UI-test runner get a bundle ID of their own in each checkout (`python3 scripts/verify.py doctor` prints it).

## Never weaken enforcement

Never suppress, disable, weaken or bypass a check. That includes suppression comments, editing `Project.swift`, `ModuleShape.swift`, `.swiftlint.yml`, `Rules/`, `tools.toml`, `scripts/`, or CI.

**If the right fix isn't possible within the rules, stop and report:** what you were trying to do, which rule blocks it, and what you'd change. A clear report is a successful outcome.

## Don't write unrequested docs

No new markdown files, rule files or explanatory comments unless asked. Comments are for what code can't express.
