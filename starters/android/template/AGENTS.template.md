# <App name>: agent instructions

## Before you change code

- Modules and their links come from the module shape (`arch/shape.json`, the owner's). A module's role is its folder (below). Modules have no build files: each declares the modules it uses in its `module.toml` (`uses`), and the build fails if its role may not use one. Libraries come with the role (`arch/shape.json`); a module can't add one. A link the shape doesn't allow is outside it: stop and report. Don't edit `arch/`, `build-logic/`, `gradle/`, the root Gradle files or `tools.toml`.
- Run Gradle only through the scripts (`python3 scripts/check.py`, or `python3 scripts/tools.py gradle <tasks>`): they use the pinned JDK, Gradle and Android SDK, and keep everything large in the cache folder.
- Persisted data is JSON through kotlinx.serialization: its types are `@Serializable` in the feature's api, and a platform module reads and writes them. Never a hand-made string format. Use the existing approved APIs for <networking, time, background work>. Don't introduce a second way to do the same thing.
- Dependencies are constructor parameters: a feature's api declares what it needs (an interface), a platform module implements it, and the composition roots pass the real or fixture one in, with the coroutine scope and dispatchers: process-wide services live in each app's `Application` class (in `app/` and `app-verify/`), never in an Activity. No singletons, `object` services or CompositionLocal lookups.
- Start each piece with its command; what it creates passes every gate, and its stubs fail until you write them:
  - a feature with modules of its own: `python3 scripts/new_feature.py <name>` (the three modules, the map entry, a journey stub and a test stub, linked into both apps and the journeys)
  - a feature whose code goes in a module another feature has (a new rule on the same screen): `python3 scripts/new_feature.py <id> --in <module>` (its map entry, journey stub and test stub)
  - a client that keeps data (a store) or reaches the outside world: `python3 scripts/new_client.py <feature> <name>` (the interface and result type in the api, `platform/<name>` with a test, a fake for the model's tests, fixtures for failing and unreadable data, and the wiring in both `Application` classes)

## Where code goes

Every feature has the shape these commands create. By module role:

- **api** (`features/<name>/api`): declarations only: data types, enums, client interfaces and their result types, and `<Feature>Ui`, the UI identifiers. IDs are `@JvmInline value class`es, never a raw `Int` or `String`. Persisted types are `@Serializable` here.
- **logic** (`features/<name>/logic`): common code (no JDK or Android). A `<Feature>Model` whose `state` is a `StateFlow` and whose `send(action)` is the only way in. State is data: the model works out what the screen needs (what's allowed, reachable, done) and puts it in the state, as values or properties without parameters, never a function the view calls. The model never waits for an animation. The session that isn't stored anywhere else (a selection, half-typed input, a turn in progress) goes in the model's `Saved`; what the app keeps goes through a store and is loaded again after the process ends, never copied into `Saved`.
- **logic tests** (`logic/src/commonTest`): Turbine: subscribe first (`model.state.test { }`), then after each `send` assert the state it makes whole (`assertEquals(<state>, awaitItem())`), never a count or a filtered or mapped part of it. A property test: seeded random sequences checked against a model of the spec, written from the spec; it branches on an enum with a `when` naming every case, never `if`/`else`.
- **ui** (`features/<name>/ui`): Compose screens that render state and send actions, and the `<Feature>Route(model)` entry point both apps show. From its logic it imports only the model and its state and action types. It tags elements with `Modifier.uiId(<Feature>Ui.<element>)` (list and grid items with `<element>.at(row, column)`) and never sets `text` semantics; a mark that isn't text gets a `contentDescription` saying what it means. Animation lives here only, derived from state with Compose's animation APIs (`animate*AsState`, `AnimatedVisibility`, `updateTransition`), never timed by hand (`delay`, `withFrameNanos`); Compose honours the system's animation scale, so reduce-motion (Remove animations) needs no code of its own. Art (drawables, images) goes in this module's `src/main/res`.
- **platform** (`platform/<name>`): the only I/O. Implements a feature's client interfaces, with a test in `src/test`.
- **fixtures**: test-mode setups (`Fixture`, which journeys launch with) and each client's fixture versions (failing, unreadable, recording). Only app-verify uses it.
- **app**: the shipped app, which only composes: its `Application` builds process-wide services once, and its Activity shows each feature's entry point with a model built by `rememberModel`.
- **app-verify**: the same entry points on the fixture's services. An effect the screen doesn't show (a sound) goes through a client whose fixture records each call, and app-verify shows that record under a `UiId` journeys check (the `verify` skill has the pattern).
- **feature-map and journeys** (`feature-map/<id>.toml`, `verify/journeys`): each feature's entry, and journeys that drive app-verify and prove it works by what the screen shows (`shows`, `describes`, `isSelected`, `isGone`, `isDisabled`), asserting end states. Every `UiId` an api declares is checked by a journey. Each feature has a journey that turns the device (`rotate()`) and one that has its process end in the background (`returnAfterProcessDeath()`).

Opt-ins come from the build per role (`arch/shape.json`), never `@OptIn`.

## Review

Review every change for conformance to this architecture, not only for whether the feature works, and brief every reviewer you start (sol-loop included) the same way. Check it against:

- the rules the gates enforce: allowed-dependencies, animations-from-state, exhaustive-states, exhaustive-tests, explicit-dependencies, io-only-in-platform, listed-permissions, minimum-os-apis, module-boundaries, no-concurrency-escapes, no-fixtures-in-release, no-force-operations, no-io-in-logic, no-suppressions, protected-enforcement, retired-apis, tests-always-run, thin-api, thin-app, typed-identifiers, typed-ui-identifiers, verified-features, views-hold-no-clients (a failure message starts with the rule's id)
- the module roles above: each piece of code is where its role says
- the `verify` skill: journeys check what the screen draws, every element, end states and durable effects

Severity: **blocker**: breaks one of those rules or weakens a check, whether or not a gate failed. **should**: works against a convention or a tool here (a second way to do something, a hand-made format, code a command would have laid out differently). **nit**: the rest. Fix blockers and shoulds. Then, for each departure, ask: was it caught by a gate? If not, stop and report it: what departed, which rule or convention, and that no gate caught it.

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
