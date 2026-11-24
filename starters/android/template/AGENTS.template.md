# <App name>: agent instructions

## Before you change code

- Modules and their links come from the module shape (`arch/shape.json`, the owner's). A module's role is its folder: `core` (shared types), `features/<name>/api` (the feature's types, client interfaces and `<Feature>Ui` identifiers), `features/<name>/logic` (its model: state, actions, effects through injected clients), `features/<name>/ui` (Compose screens that render state and send actions), `platform/<name>` (real I/O implementing feature clients), `fixtures` (test-mode setups), `app` (the shipped app) and `app-verify` (the test-mode app). Modules have no build files: each declares the modules it uses in its `module.toml` (`uses`), and the build fails if its role may not use one. Libraries come with the role (`arch/shape.json`); a module can't add one. A link the shape doesn't allow is outside it: stop and report. Don't edit `arch/`, `build-logic/`, `gradle/`, the root Gradle files or `tools.toml`.
- Run Gradle only through the scripts (`python3 scripts/check.py`, or `python3 scripts/tools.py gradle <tasks>`): they use the pinned JDK, Gradle and Android SDK, and keep everything large in the cache folder.
- Use the existing approved APIs for <persistence, networking, time, background work>. Don't introduce a second way to do the same thing.
- Dependencies are constructor parameters: a feature's api declares what it needs (an interface), a platform module implements it, and the composition roots pass the real or fixture one in, with the coroutine scope and dispatchers: process-wide services live in each app's `Application` class (in `app/` and `app-verify/`), never in an Activity. No singletons, `object` services or CompositionLocal lookups.
- Start a feature with `python3 scripts/new_feature.py <name>`: it creates the three modules, the map entry and a journey stub, and links them. Its test and journey fail until you write them.
- Every feature has the shape `new_feature.py` creates: `api` holds declarations only (data types, enums, client interfaces, `<Feature>Ui`, IDs as `@JvmInline value class`es, never a raw `Int` or `String`), `logic` is common code (no JDK or Android there) with a `<Feature>Model` whose `state` is a `StateFlow` and whose `send(action)` is the only way in, tests in `logic/src/commonTest` that assert every state whole with Turbine (`assertEquals(<state>, awaitItem())`, never a count or a filtered or mapped part of it), a property test (seeded random sequences checked against a model of the spec, written from the spec), a `<Feature>Route(model)` entry point both apps show, a `feature-map/<id>.toml` entry, and journeys in `verify/journeys` that drive app-verify and prove it works by what the screen shows. The apps build the model from their services with `rememberModel`, and the shipped app does nothing but compose. Only platform modules do I/O. Views tag elements with `Modifier.uiId(<Feature>Ui.<element>)` (list and grid items with `<element>.at(row, column)`); journeys find them by the same identifiers and read the text the screen draws (so a view never sets `text` semantics), and each feature has a journey that turns the device (`rotate()`) and one that has its process end in the background (`returnAfterProcessDeath()`); the screen's session that isn't stored anywhere else (a selection, half-typed input, a turn in progress) goes in the model's `Saved`, and what the app keeps goes through a store, loaded again after the process ends, never copied into `Saved`. Opt-ins come from the build per role (`arch/shape.json`), never `@OptIn`.

## Checks

```sh
python3 scripts/check.py        # compiler, detekt, lint, konsist, arch, deps, settings, tests, verify, release: all must PASS
python3 scripts/package.py      # the release app bundle and APK (R8, signed), and the release build's launch
```

Run it before handing back. If it stops because the cache folder is unavailable (e.g. an external drive isn't mounted), report that; don't build elsewhere. A failure names the rule and how to fix it.

Use the `verify` skill (`.agents/skills/verify`) to explore the running app and to write journeys. `verify` runs every feature-map journey on the emulator and writes screenshots and `.build/evidence/latest/evidence.md`. For behaviour changes, look at them and include the path in your report.

## Never weaken enforcement

Never suppress, disable, weaken or bypass a check. That includes `@Suppress`, `@OptIn`, `@SuppressLint`, `tools:ignore`, `!!`, `as` casts, `lateinit`, `@Ignore`, build files in modules, other source sets, and editing `arch/`, `build-logic/`, `gradle/`, `tools.toml`, `scripts/` or CI, and loosening, deleting or renaming a journey or feature-map entry (the verify gate fails when one the base branch has is gone; only the owner can retire one, in `arch/retired.toml`). The settings gate compares the build settings in effect with `arch/settings.json`, so a weakened setting fails wherever it was changed.

**If the right fix isn't possible within the rules, stop and report:** what you were trying to do, which rule blocks it, and what you'd change. A clear report is a successful outcome.

## GitHub

You act as the project's machine user (`GH_TOKEN` is its token), never as the owner, so the owner's review is a real second person's. A pull request that touches a code-owned file (`CODEOWNERS` lists them: the gates, their settings, the module shape, CI, this file) waits for the owner's review; one that touches none merges once CI passes. Keep a change to a code-owned file in its own pull request and say why it's needed. Never change the repository's settings or rules, and never ask for the owner's credentials.

## Don't write unrequested docs

No new markdown files, rule files or explanatory comments unless asked. Comments are for what code can't express.
