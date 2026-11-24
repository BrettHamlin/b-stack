---
name: verify
description: Run this Android app and prove a feature works the way a user sees it, with screenshot evidence. Use before handing back any behaviour change, when adding a feature, or to explore the running app.
---

# Verify

`python3 scripts/verify.py` is the one driver for the running app, and `python3 scripts/emulator.py` the one way to the emulator. Don't start emulators, install APKs or drive the screen any other way.

## Prove a change: the gate

```sh
python3 scripts/verify.py          # same as check.py's verify gate
```

It checks the feature map, builds app-verify and the journey runner, boots the emulator if needed (holding this Mac's lock on it, so other checkouts wait), runs every journey in `verify/journeys`, and writes `.build/evidence/latest/evidence.md` with a screenshot at every checkpoint. Read the screenshots. A passing journey whose screenshots show the wrong thing is a bad journey: fix it.

## Explore the running app

```sh
python3 scripts/emulator.py run -- adb shell am start -W -n <app-verify id>/appverify.VerifyActivity --es bstack.fixture Saved --ez bstack.reset true
python3 scripts/emulator.py run -- sh -c 'adb exec-out screencap -p > .build/look.png'
python3 scripts/emulator.py run -- sh -c 'adb shell uiautomator dump /sdcard/ui.xml && adb shell cat /sdcard/ui.xml'
```

`run` holds the emulator's lock and sets `$ANDROID_SERIAL`. app-verify's id is in `.build/gradle/app-verify/outputs/apk/debug/output-metadata.json` after a build (one per checkout). Elements tagged with `Modifier.uiId` show their identifier as the `resource-id` in the dump. Exploring is for looking and judging; it's not proof. Once a behaviour works, write the journey that proves it.

## Add a feature

1. Run `python3 scripts/new_feature.py <name>`: it creates `features/<name>/api`, `logic` and `ui` with their `module.toml`s, `feature-map/<name>.toml`, a journey stub (which turns the device and has the process end) and the adapters, and links the feature into `verify/journeys`, `app` and `app-verify`. Then show its entry point in both apps.
2. Give the feature's elements identifiers in its api module: an `object <Feature>Ui { val thing = UiId("feature.thing") }`. Only api modules can make a `UiId`. Views tag with `Modifier.uiId(<Feature>Ui.thing)`; nothing else counts.
3. Write the journey in `verify/journeys` as `fun Journey.<name>()`: `launch(fixture)`, then `find(id)` (a list item: `find(TallyUi.item.at(row))`) and `tap`, `type`, `shows`, `isDisabled`, `relaunch()`, `rotate()`, `returnAfterProcessDeath()`, and `checkpoint("what it shows")` for the evidence. Each feature needs one journey that calls `rotate()` and one that calls `returnAfterProcessDeath()` (keep half-done input in the model's `Saved`, which `rememberModel` passes in). app-verify runs with StrictMode: disk or network work on the main thread kills it, so the journey fails. Journey bodies are common code: they can't reach UiAutomator, Android or the JVM. Then run `python3 scripts/verify.py adapters`, which writes the runner's test for each journey. If the Screen lacks something, stop and report (journeykit and the runner are code-owned).
4. Start from known data with a `fixtures.Fixture` (app-verify reads `bstack.fixture`), never by adding a test mode to the shipped app.
5. In `feature-map/<id>.toml`, name the feature's folder in `modules` and each journey with what it `proves`. A journey belongs to one feature only.

## Rules

- Drive the real user path through the real app: app-verify calls the same feature entry points as the shipped app; only the services passed in differ.
- Check durable effects, not just the screen: `relaunch()` and check again; `rotate()` where state must survive a configuration change; `returnAfterProcessDeath()` where it must survive the system ending the app in the background.
- `shows` compares the whole text of an element and everything in it, one text per line.
- If a journey fails, fix the app. **Never weaken a journey to make it pass.** If you can't make it pass within the rules, stop and report.
