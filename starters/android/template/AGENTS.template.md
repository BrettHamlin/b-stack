# <App name>: agent instructions

## Before you change code

- Modules and their links come from the module shape (`arch/shape.json`, the owner's). A module's role is its folder: `core` (shared types), `features/<name>/api` (the feature's types, client interfaces and `<Feature>Ui` identifiers), `features/<name>/logic` (its model: state, actions, effects through injected clients), `features/<name>/ui` (Compose screens that render state and send actions), `platform/<name>` (real I/O implementing feature clients), `fixtures` (test-mode setups), `app` (the shipped app) and `app-verify` (the test-mode app). Modules have no build files: each declares the modules it uses in its `module.toml` (`uses`), and the build fails if its role may not use one. Libraries come with the role (`arch/shape.json`); a module can't add one. A link the shape doesn't allow is outside it: stop and report. Don't edit `arch/`, `build-logic/`, `gradle/`, the root Gradle files or `tools.toml`.
- Run Gradle only through the scripts (`python3 scripts/check.py`, or `python3 scripts/tools.py gradle <tasks>`): they use the pinned JDK, Gradle and Android SDK, and keep everything large in the cache folder.
- Use the existing approved APIs for <persistence, networking, time, background work>. Don't introduce a second way to do the same thing.
- Dependencies are constructor parameters: a feature's api declares what it needs (an interface), a platform module implements it, and the composition roots pass the real or fixture one in, with the coroutine scope and dispatchers: process-wide services live in each app's `Application` class (`StarterApp`, `VerifyApp`), never in an Activity. No singletons, `object` services or CompositionLocal lookups.
- Features are shaped like `features/tally`: logic in common code (no JDK or Android there), a model whose `state` is a `StateFlow` and whose `send(action)` is the only way in, tests in `logic/src/commonTest` that assert every state with Turbine (`assertEquals(<state>, awaitItem())`), a property test (random sequences checked against a model of the spec, like `TallyPropertyTest`), a feature entry point both apps call (`TallyRoute(store)`), a `feature-map/<id>.toml` entry, and journeys in `verify/journeys` that drive app-verify and prove it works. A feature's entry point takes only its model (`TallyRoute(model)`); the apps build the model from their services with `rememberModel`, and the shipped app does nothing but compose. Only platform modules do I/O. Views tag elements with `Modifier.uiId(<Feature>Ui.<element>)` (list and grid items with `<element>.at(row, column)`); journeys find them by the same identifiers, and each feature has one journey that turns the device (`rotate()`). Opt-ins come from the build per role (`arch/shape.json`), never `@OptIn`.

## Checks

```sh
python3 scripts/check.py        # compiler, detekt, lint, konsist, arch, deps, tests, verify: all must PASS
```

Run it before handing back. If it stops because the cache folder is unavailable (e.g. an external drive isn't mounted), report that; don't build elsewhere. A failure names the rule and how to fix it.

Use the `verify` skill (`.agents/skills/verify`) to explore the running app and to write journeys. `verify` runs every feature-map journey on the emulator and writes screenshots and `.build/evidence/latest/evidence.md`. For behaviour changes, look at them and include the path in your report.

## Never weaken enforcement

Never suppress, disable, weaken or bypass a check. That includes `@Suppress`, `@OptIn`, `@SuppressLint`, `tools:ignore`, `!!`, `as` casts, `lateinit`, `@Ignore`, build files in modules, other source sets, and editing `arch/`, `build-logic/`, `gradle/`, `tools.toml`, `scripts/`, the journeys, or CI.

**If the right fix isn't possible within the rules, stop and report:** what you were trying to do, which rule blocks it, and what you'd change. A clear report is a successful outcome.

## Don't write unrequested docs

No new markdown files, rule files or explanatory comments unless asked. Comments are for what code can't express.
