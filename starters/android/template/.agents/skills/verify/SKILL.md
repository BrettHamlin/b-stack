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
3. Write the journey in `verify/journeys` as `fun Journey.<name>()`: `launch(fixture)`, then `find(id)` (a list item: `find(<Feature>Ui.<element>.at(row))`) and `tap`, `type`, `shows`, `describes`, `isSelected` (a selected tab, ship or option), `isGone` (a dismissed dialog, a removed piece), `isDisabled`, `relaunch()`, `rotate()`, `returnAfterProcessDeath()`, and `checkpoint("what it shows")` for the evidence. Each feature needs one journey that calls `rotate()` and one that calls `returnAfterProcessDeath()` (what the app keeps comes back from its store; the screen's session that isn't stored anywhere else, such as a selection, half-typed input or a turn in progress, comes back from the model's `Saved`, which `rememberModel` passes in; never copy stored data into `Saved`). app-verify runs with StrictMode: disk or network work on the main thread kills it, so the journey fails. Journey bodies are common code: they can't reach UiAutomator, Android or the JVM. Then run `python3 scripts/verify.py adapters`, which writes the runner's test for each journey. If the Screen lacks something, stop and report (journeykit and the runner are code-owned).
4. Start from known data with a `fixtures.Fixture` (app-verify reads `bstack.fixture`), never by adding a test mode to the shipped app.
5. In `feature-map/<id>.toml`, name the feature's folder in `modules` and each journey with what it `proves`. A journey belongs to one feature only. A feature whose code goes in a module another feature has gets its own entry naming that module: `python3 scripts/new_feature.py <id> --in <module>` makes it, with a journey stub and a test stub.
6. Every `UiId` an api declares must be named by a journey (`<Feature>Ui.<element>`, or `.at(...)` for list items); the map check fails on one that isn't. An element no journey checks is unproven: check it, or remove the identifier.

## Time and animation

- The emulator runs with animations off (`emulator.py` sets the window, transition and animator scales to 0 after boot). Compose's animations honour the animator scale, so each one jumps to its end: journeys and screenshots see end states. Assert the state a step ends in; never wait for an animation or sleep in a journey.
- Animation lives in the ui module only, derived from state (`animateFloatAsState`, `AnimatedVisibility`, `updateTransition`), never timed by hand with `delay` or `withFrameNanos` (Konsist fails those in ui). The model never waits for an animation to finish: it moves to the next state at once, and the view animates towards it. Users who turn on Remove animations get the same jump, with no code of yours.
- Art goes in the ui module's `src/main/res` (drawables, images), drawn from state like everything else.

## Prove an effect the screen doesn't show (a sound)

The effect goes through a client (`python3 scripts/new_client.py <feature> <name>`, then change the interface to what it does), which platform implements for real. In app-verify, the fixture's client records each call, and app-verify shows the record under a `UiId` from the feature's api, which journeys check like any other element:

```kotlin
// api: the client, and the element app-verify shows the record in
enum class Cue { Fire, Hit }
interface BattleSound { fun play(cue: Cue) }
object BattleUi { /* ... */ val soundsPlayed = UiId("battle.soundsPlayed") }

// fixtures: records instead of playing
class RecordedSound : BattleSound {
    private val played = MutableStateFlow(emptyList<Cue>())
    val record: StateFlow<List<Cue>> = played.asStateFlow()
    override fun play(cue: Cue) = played.update { it + cue }
}

// app-verify: below the feature's entry point
val played by app.sound.record.collectAsState()
Text(played.joinToString("\n"), Modifier.uiId(BattleUi.soundsPlayed))

// journey
screen.find(BattleUi.fire).tap()
screen.find(BattleUi.soundsPlayed).shows("Fire\nHit")
```

A setting that changes the effect (mute) is the model's state, kept through a store; the journey turns it on, relaunches, and checks the record stays empty.

## Rules

- Drive the real user path through the real app: app-verify calls the same feature entry points as the shipped app; only the services passed in differ.
- Check what the screen draws, not what code says: `shows` reads the text drawn. A mark that isn't text (a highlight, an icon, a Canvas stroke) gets a `contentDescription` in the view saying what it means (`"Open space, can move here"`), and the journey checks it with `describes(...)`; screen-reader users hear the same words.
- Check durable effects, not just the screen: `relaunch()` and check again; `rotate()` where state must survive a configuration change; `returnAfterProcessDeath()` where it must survive the system ending the app in the background.
- `shows` compares the whole text of an element and everything in it, one text per line.
- If a journey fails, fix the app. **Never weaken a journey to make it pass.** If you can't make it pass within the rules, stop and report.
