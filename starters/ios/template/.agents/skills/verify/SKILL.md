---
name: verify
description: Run this app in test mode on the iOS Simulator and prove a feature works the way a user sees it, with screenshot evidence. Use before handing back any behaviour change, when adding a feature, or to explore the running app.
---

# Verify

`python3 scripts/verify.py` is the one driver for the running app. Don't improvise simulator scripts.

## Test mode

The `AppVerify` target is the app composed with `Targets/Fixtures` instead of real services. It reads:
- `BSTACK_FIXTURE`: a `Fixture` case (`standard`, `save-fails`, ...). Add a case when a journey needs a new starting state.
- `BSTACK_RESET=1`: restore the fixture's starting data. Launch without it to check that something survived a relaunch.

Only `AppVerify` may import `Fixtures`; the shipped `App` can't (rule `no-fixtures-in-release`).

## Prove a change: the gate

```sh
python3 scripts/verify.py          # same as check.py's verify gate
```

It checks the feature map, runs every journey in `Targets/AppVerifyUITests` on a simulator, and writes evidence to `.build/evidence/latest/evidence.md`, with a screenshot at every checkpoint. Read the screenshots. A passing journey whose screenshots show the wrong thing is a bad journey: fix it.

## Explore the running app

```sh
python3 scripts/verify.py launch --fixture standard --reset   # build, install, start; prints the simulator id
python3 scripts/verify.py doctor                              # read-only: booted, installed, running?
agent-device snapshot --platform ios --udid <udid> -i         # what's on screen
agent-device click ... / agent-device screenshot ...          # drive it
python3 scripts/verify.py cleanup                             # stop what launch started; evidence is kept
```

Run `doctor` before driving and again whenever something looks off. Exploring is for looking and judging; it's not proof. Once a behaviour works, write the journey that proves it.

## Add a feature

1. Give its views identifiers from a `<Feature>UIID` enum in `<Feature>Interface`. Journeys find elements by those constants, never string literals.
2. Write journeys in `Targets/AppVerifyUITests` (`XCTestCase`, `testXxx()`). Each launches with a fixture, acts like a user, asserts what the user would see, and attaches screenshots (`XCTAttachment`, `.keepAlways`).
3. Add `feature-map/<id>.toml`: `module`, `summary`, `entry_points`, `gotchas`, and one `[[journeys]]` per journey with `test`, `fixture` and `proves`.

## Rules

- Drive the real user path. Fakes go only where a real service would be (Fixtures), never inside the feature.
- Check durable effects, not just the screen: relaunch, then check again.
- If a journey fails, fix the app or record why under `gotchas`. **Never weaken a journey to make it pass.** If you can't make it pass within the rules, stop and report.
