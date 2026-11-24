---
name: verify
description: Run this app in test mode on the iOS Simulator and prove a feature works the way a user sees it, with screenshot evidence. Use before handing back any behaviour change, when adding a feature, or to explore the running app.
---

# Verify

`python3 scripts/verify.py` is the one driver for the running app. Don't improvise simulator scripts.

## Test mode

The `AppVerify` target is the app composed with `Targets/Fixtures` instead of real services. It reads:
- `BSTACK_FIXTURE`: a `Fixture` case (`standard`, ...). Add a case when a journey needs a new starting state.
- `BSTACK_RESET=1`: restore the fixture's starting data. Launch without it to check that something survived a relaunch.

Only `AppVerify` may import `Fixtures`; the shipped `App` can't (rule `no-fixtures-in-release`).

## Prove a change: the gate

```sh
python3 scripts/verify.py          # same as check.py's verify gate
```

It checks the feature map, checks generated XCTestCase adapters and runs every journey body in `Targets/AppVerifyJourneys` on a simulator, and writes evidence to `.build/evidence/latest/evidence.md`, with a screenshot at every checkpoint. Read the screenshots. A passing journey whose screenshots show the wrong thing is a bad journey: fix it.

## Explore the running app

```sh
python3 scripts/verify.py launch --fixture standard --reset   # build, install, start; prints the simulator id
python3 scripts/verify.py doctor                              # read-only: booted, installed, running?
python3 scripts/simulator.py run -- agent-device snapshot --platform ios --udid <udid> -i   # what's on screen
python3 scripts/simulator.py run -- agent-device click ...    # drive it (screenshot, recordings: the same way)
python3 scripts/verify.py cleanup                             # stop what launch started; evidence is kept
```

Other checkouts' gates share the simulator. `simulator.py run` holds it while the command runs, and waits while a gate elsewhere uses it; `launch` and `cleanup` hold it themselves. Between separate commands another checkout's gate may run and leave its app in front: run `doctor` (or `agent-device open <bundle id>`) before driving again, or put the whole sequence in one `simulator.py run -- sh -c '...'`. Never drive it outside these (see AGENTS.md, "Using the simulator by hand"). Run `doctor` before driving and again whenever something looks off. Exploring is for looking and judging; it's not proof. Once a behaviour works, write the journey that proves it.

## Add a feature

1. Give its views identifiers from a `<Feature>UIID` enum in `<Feature>Interface` (`static let x = UIID("feature.x")`, set with `.accessibilityIdentifier(<Feature>UIID.x.rawValue)`). Only Interface modules may create a `UIID`. For a grid or list, set `.accessibilityIdentifier(<Feature>UIID.x.at(row, column).rawValue)` on each item and find it in a journey with `screen.find(<Feature>UIID.x, at: row, column)`; never build identifiers from strings.
2. Write journey bodies in `Targets/AppVerifyJourneys`: `public import JourneyKit`, a `public final class <Feature>Journeys: Journey`, and `public func testXxx()`. Use `expectTrue`, `expectFalse` and `expectEqual` (they forward the source location to XCTest). `launchApp(fixture:reset:readyWhen:)` returns a `Screen`; find with `screen.find(<Feature>UIID.x)` (or `toggle(_:)`, `switchValue(_:)`). Handles are typed `Element`s: use `tapWhenHittable`, `waitUntilGone`, `waitForExistence`, `label`, `exists`, `tap`, `typeText`. Attach screenshots with `capture(screen, "checkpoint")`. Each launch records `fixture-<name>` so verify can check the fixture against the map. Keep one fixture per journey. Importing XCTest or XCUIAutomation here is a compiler error; add typed helpers in the code-owned `Targets/JourneyKit` instead. Reflection and Objective-C dynamic dispatch are banned too. Run `python3 scripts/verify.py adapters` after changing body classes/methods: it generates the XCTestCase entry points with identical Class/testName identities. Never handwrite runner code in AppVerifyUITests; verify rejects modified or extra adapter files.
3. Add `feature-map/<id>.toml`: `module`, `summary`, `entry_points`, `gotchas`, and one `[[journeys]]` per journey with `test`, `fixture` and `proves`. A journey belongs to one feature only.
4. Compose the feature the same way in `App` and `AppVerify`: both call the same view initializer, and only the services passed in differ.

## Rules

- Drive the real user path. Fakes go only where a real service would be (Fixtures), never inside the feature.
- Check durable effects, not just the screen: relaunch, then check again.
- If a journey fails, fix the app or record why under `gotchas`. **Never weaken a journey to make it pass.** If you can't make it pass within the rules, stop and report.
