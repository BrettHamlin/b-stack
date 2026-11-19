# Decisions

For the human owner: what we decided and why. Agents work from `skills/`, `rules/` and `starters/`, not this file.

## Purpose

b-stack lets anyone clone it and have an agent set up a new app where quality is **enforced, not requested**. It started from Lauren Tan's talk *All Code Is Slop (Except Mine)* (`research/`) and goes beyond it.

## Core beliefs

- **Agents repeat the same mistakes** across runs, so a check pays off every time it fires. Correcting in chat fixes one instance.
- **Every agent session is a new hire on day one.** Onboarding aids (paved paths, obvious structure) are needed permanently.
- **Code is the agents' memory.** They copy existing patterns, so the first patterns in a repo become the template. Enforcement must exist from the first commit.
- **Architecture first, enforced right away.** A rule needs a correct path to point to; architecture is a decision, a rule makes it executable.
- **Verification is now cheap** (property tests, models, journey checks), so use it.
- **Don't automate a bad loop.** One reliable agent loop comes before triggers and fleets.

## The enforcement pyramid

Sorted by how hard each layer is to get around (Lauren's sorts by kind of thing):

| Layer | Meaning | Enforced by |
|---|---|---|
| 1. Can't be written | The wrong thing won't compile | Types, modules, compiler settings |
| 2. Can't be merged | A check blocks it before `main` | Parsed-code checker in protected CI |
| 3. Can't pass verification | The running product behaves wrong | Journey, property, formal tests |
| 4. Guided | Steers judgment; enforces nothing | Prose (minimal) |
| 5. Judged | Is the intent right? | Human review of evidence |
| Foundation | Nobody weakens the checks unnoticed | CODEOWNERS, branch protection, settings checks |

Rule: push every constraint as high as it goes.

## Decisions

| Date | Decision | Why |
|---|---|---|
| 2026-11-15 | The repo is for **agents first**: rules with tests, starters, skills. Prose is minimal; this file is the human summary. | Prose is the weakest layer. A repo about enforcement should be enforced itself. |
| 2026-11-15 | Rules are data plus **fail/pass test cases** run against the real compiler. | A rule that has never fired is unproven. |
| 2026-11-15 | Skills are plain `SKILL.md` folders. | Works in Claude Code and Codex. |
| 2026-11-15 | iOS is the first platform. | Owner's current focus. |
| 2026-11-15 | Starter templates are extracted from a real app, not designed up front. | Make one loop dependable before scaling. |
| 2026-11-15 | Every project gets a "stop and report" escalation rule. | Agents work around rules when the only options are comply or fail. |
| 2026-11-15 | **Adopt existing tools instead of writing our own checker:** Tuist (project generation + import graph), Harmonize (architecture rules as unit tests), SwiftLint (syntax-level bans). Rules tests prove each tool enforces what we need. | They already exist, are maintained, and our rule cases showed they catch what the compiler misses. Writing our own SwiftSyntax checker was the alternative. |
| 2026-11-15 | **One gate command per app** (`scripts/check.py`: compiler, Tuist, SwiftLint, Harmonize). b-stack's rule tests run through that same command. | The rule tests then prove the app's real gate works, not a separate test setup. |
| 2026-11-15 | **Tools are pinned and checksum-verified** in `tools.toml`, downloaded into the project, never installed globally. | Reproducible across machines and CI; a tampered download is refused. |
| 2026-11-16 | **State flow: The Composable Architecture (TCA) 1.26.2.** Each feature is `<Feature>Interface` (types, client protocols), `<Feature>Logic` (a `@Reducer`, no I/O), `<Feature>` (SwiftUI view that only sends actions), `<Feature>Tests` (exhaustive `TestStore`). TCA and its libraries are linked as shared frameworks via Tuist `productTypes`. Dependencies are passed in through initializers. | Trial (same spec, fresh agent each, 8 deliberate mistakes): TCA caught 7/8, Mobius 1/8 with 3 mistakes making its tests hang. TCA's exhaustive TestStore caught untested changes and deleted assertions; its view binding made writing state from the view a compile error. Costs: ~15 min first clean build; Tuist's default static linking copied TCA into every module and split its dependency system. |
| 2026-11-16 | **Large regenerable files go to a configured cache folder** (`$BSTACK_CACHE_DIR` or `~/.config/b-stack/config.toml`); project `.build/` folders become links into it. If it's missing, scripts stop instead of falling back. Default for a fresh clone: inside the project. | The owner's internal drive has ~20 GB free and one trial build produced 5.5 GB; large files belong on MicroBay. A silent fallback would refill the internal drive. |
| 2026-11-17 | **Verification: a scripted gate, with agents exploring.** XCUITest journeys, named in a feature map (`feature-map/<id>.toml`: entry points, journeys, what each proves, gotchas), run by `scripts/verify.py` as check.py's `verify` gate; every feature module needs an entry and every journey must be mapped. Evidence (screenshots per checkpoint, result bundle, `evidence.md`) is generated per run in the cache folder. Agents explore with agent-device via `verify.py launch/doctor/cleanup`, then write the journey. | A gate must give the same answer every time; an agent's judgement can't. Agents are better at judging new behaviour, so they explore and then encode what they proved. Swift Testing can't drive UI (Xcode 27.2), so journeys use XCUITest. Launch/doctor/drive/evidence/cleanup and the feature-map content follow pstack's `create-verification-skill`; making it a gate is ours. |
| 2026-11-17 | **Test mode is a separate app target (`AppVerify`) composed with a `Fixtures` module**, selected by `BSTACK_FIXTURE` / `BSTACK_RESET` launch environment. The shipped `App` can't import Fixtures (Harmonize) or declare it unused (Tuist `--only redundant`). | A flag inside the shipped app relies on `#if DEBUG` discipline and can ship test mode to users. Here the release build can't contain it. |
| 2026-11-17 | **Journeys use a typed layer (JourneyKit); raw XCUITest lookups are banned by name elsewhere.** `UIID` (Core) is a distinct type, constants live in `<Feature>Interface`, and journeys find elements only via `screen.find(_ id: UIID)`. | Four review rounds kept finding new ways to write a string lookup that static analysis missed (comments, parentheses, shadowing, predicate syntax) and new false failures on dictionaries. The compiler now rejects a String where an identifier goes, and the remaining rule bans a closed list of API names instead of guessing which subscripts are queries. |
| 2026-11-17 | **App and AppVerify compose features the same way:** both call the same view initializer (e.g. `NotificationSettingsView(preferences:)`), which loads the saved value itself; only the services passed in differ. Journeys record the fixture they launched, and verify checks it against the map. | Otherwise App's own wiring is never run: a shipped app that skipped loading the saved value would pass every gate. The one App-only line, which services it passes, is left to review. |
| 2026-11-19 | **Gates run side by side where they can; the rule suite stays serial by default.** `check.py` runs SwiftLint, Harmonize and Tuist alongside the Xcode builds, and verify reuses the compiler gate's AppVerify build. `test_rules.py` gives each project checkout its own work folder and a lock, and reports time per case and worker. Parallel rule cases (`--jobs`) and split journeys (`verify.py --workers`) are opt-in. | Measured on a 10-core, 16 GB laptop with the cache and simulators on one external drive (Xcode 27.2, iOS 27.2): 2 workers took 24 min against about 20 serially, each case ran about 1.6 times slower, and journeys timed out. Cloning a simulator to split the starter's 2 journeys took them from under a minute to about 5 each. Before the lock, two checkouts' suites shared one work folder and broke each other's runs. |
| 2026-11-15 | **iOS architecture, judged by how much the compiler can enforce:** (1) feature modules split Interface/Implementation (TMA-style) plus Core, Platform and App, with the project generated by Tuist; (2) one actor isolation domain per kind of shared state; (3) a pure core per feature, side effects only in the shell. | Each gives compiler walls, verified with Swift 6.4.2: `internal` blocks cross-module access, actors block cross-domain access within a module, a module without imports can't do I/O. `package` access is not a wall within one package, so avoid it. |

## Verified findings (Swift 6.4.2, Xcode 27.2, Tuist 4.216.7, SwiftLint 0.65.1, Harmonize 1.3.0)

Most are tested on every run of `scripts/test_rules.py`; `~Copyable`, the `package`/`internal`/actor walls and the import-only purity check were tested by hand. Notable results:

- **Compiler enforces:** distinct ID types, exhaustive switches, `~Copyable` single use, unavailable APIs (with a custom message), warnings as errors, main-actor isolation.
- **Strict settings reject an unneeded `public import`.**
- **Module boundaries are only partly a compiler guarantee.** An undeclared sibling import fails on a clean build only; once the sibling is built, incremental builds accept it. Indirect imports and system frameworks (e.g. `SwiftUI` in Domain) always compile. The checker must cover all three.
- **The compiler accepts every escape hatch** (`@unchecked Sendable`, `nonisolated(unsafe)`, `!`), so other tools must ban them.
- **Tuist `inspect dependencies --only implicit`** catches undeclared sibling and indirect imports (and `--only redundant` catches unused ones), but **not system frameworks**. It only works on Tuist-managed projects.
- **Harmonize** catches disallowed imports including system frameworks, `static let shared`, `@unchecked Sendable`, `nonisolated(unsafe)`. Gaps in 1.3.0: its type-name list drops `@unchecked` (read the syntax node instead), it can't see calls inside computed properties like a SwiftUI `body` (both halves of the UI-identifier rule parse with SwiftSyntax instead: views must pass a UIID's `.rawValue` to `.accessibilityIdentifier` (or a UIKit `accessibilityIdentifier` assignment), and journey files may not use XCUITest's lookup API by name, a closed list, after earlier regex and scope-tracking versions kept missing forms such as optional chaining, shadowed names and predicate argument positions), and it has no `switch` view (catch-all-default rule uses SwiftSyntax directly, a heuristic without type information).
- **SwiftLint `--strict`** catches force unwrap/try/cast and, with a comment-matching custom rule, **every** suppression comment, including `disable all` and a comment that disables the ban itself. Its baseline tolerates existing violations and fails new ones.
- **State-flow trial (TCA 1.26.2 vs Mobius 0.8.0):** neither stops I/O inside reducers/update functions (now rule `no-io-in-logic`). TCA's macros need `-skipMacroValidation` for command-line builds. With Tuist, every TCA runtime library must be a shared framework, except `CasePathsMacrosSupport`, which macros use and must stay static. Mobius tests built on async streams hang rather than fail when logic breaks.
- **Simulators:** device-specific runtimes (e.g. `iOS-27-2-iPhone19-4`) can fail to prepare for tests; the tests gate picks devices from the standard iOS runtime.
- **Verification (XCUITest, Xcode 27.2):**
  - Swift Testing can't drive UI; journeys are `XCTestCase`s.
  - `xcodebuild test` puts the build folder first on the runner's and app's `DYLD_FRAMEWORK_PATH`. TCA's dependency swift-sharing builds `Sharing.framework`, the name of a private iOS framework, so the runner loaded it in place of Apple's and crashed before any test ran (`DEDSupport` category, "missing from an installed root"). Our `Settings` module also shares a name with a private iOS framework. `verify.py` runs from a copy of the `.xctestrun` without the build folder on those paths. The app and test bundle embed their own frameworks, so they run as the shipped app would.
  - A SwiftUI `Text` row in a `Form` is exposed as a cell, not static text; a `Toggle` is a switch inside a switch, and only the inner one toggles.
  - The two Settings journeys take about 80 s, including the build for testing.
  - agent-device's runner can take the foreground after a launch; `agent-device open <bundle id>` brings the app back without relaunching it.
  - Tuist `--only redundant`, newly added to the gate, found an unused `SettingsTests → Core` dependency.
  - Harmonize 1.3.0's `productionCode()` skips files under a folder whose name ends in `Tests` or `Fixtures`, matched against the path relative to the scope's base (`testCode()` is only those). `module-boundaries` scopes each module with `.on("Targets/<module>")`, which makes the module folder the base, so `Targets/Fixtures` *is* checked (case `fail-fixtures-imports-swiftui`). Rules that scan all of `productionCode()` (no-concurrency-escapes, explicit-dependencies) do skip it, mitigated by CODEOWNERS until the enforcement-gaps follow-up.
  - `package` *is* a wall between modules that don't share a package name. Only Core and the `*Interface` targets get `SWIFT_PACKAGE_NAME = StarterIdentifiers` (Project.swift), so `UIID`'s `package init` can't be reached from the journeys, the apps or the views, in any safe spelling: `UIID(...)`, `.init(...)`, `UIID.init`, a factory in an extension, an `ExpressibleByStringLiteral` conformance, or `@testable import` (they are built with `ENABLE_TESTABILITY = NO`; Debug otherwise enables it) (Swift 6.4.2, Xcode 27.2; tested by compiler cases). Outside the package the initializer isn't even a candidate: a call reports "no exact matches in call to initializer", not an access error. Within one package it is not a wall, as the 2026-11-15 decision notes.
  - Redeclaring `XCUIElementQuery.subscript(_: String)` in the UI-test module: `@available(*, unavailable)` does not override the SDK's subscript (`app.buttons["x"]` still compiles), but `@available(*, deprecated)` does, and is an error under warnings-as-errors (Swift 6.4.2, Xcode 27.2). Module selectors (`XCUIAutomation::`) and `AnyObject` casts get around such a shadow, so PR #1 uses JourneyKit plus a by-name ban; a sealed JourneyKit module is the follow-up.
  - A public struct's stored properties need their modules imported `public` even when the property and the initializer using it are internal: without library evolution, clients need the stored types' metadata to lay the struct out. With `internal import SettingsLogic`/`ComposableArchitecture` in Settings, App failed to link (undefined `nominal type descriptor` for `NotificationSettings.State` and `Store`). Keep those imports `public`; `init(store:)` is internal, so apps must use `init(preferences:)`.
- **Harmonize 1.3.0 tests hang when run in parallel** (seen with 10 rules: every test passes alone in about 1 s, and the full parallel run never finished in 2 hours). The gate runs them with `--no-parallel`; the full set takes about 1 s.
- **Parallel builds and simulators compete, they don't add up** on a 10-core, 16 GB laptop. Each Xcode build already uses every core, and booted simulators' disk images and the build folders share one external drive: with 2 rule-suite workers each worker's busy time rose about 1.6 times, and with 3 simulators the load average passed 300 and journeys failed with `kAXErrorServerNotFound` and runner timeouts. A freshly cloned simulator runs its first-boot services for minutes. Re-measure on a faster machine before turning parallelism on by default.
- **Tool details that bite:** Python's `zipfile` breaks macOS framework symlinks (use `ditto`); a placeholder type named like its module (`enum Core` in `Core`) breaks module-qualified lookup.

## Open questions

- **Fast computer-use models for exploration (Jev).** A fast typed decision model (Jev, TypeSafe AI) choosing taps from the accessibility tree, with a large model planning, could make agent exploration and UI property testing (random action sequences checking invariants; Bombadil is web-only) cheap enough to run widely. Research (Nov 2026, `~/Code/b-stack-trials/jev/FINDINGS.md`): the API works (one typed-decision endpoint; a test call took 0.35 s and cost about $0.00002; early access); Jev-Mobile has no released code and was tested only on Android; jev-use is desktop-only; OpenAI computer use, UI-TARS and AgentCPM-GUI have no iOS Simulator path. Most UI property testing needs no model (random walks over the accessibility tree with deterministic checks); Jev would pick goal-directed moves through a small adapter over agent-device. A trial on the Settings screen is the next decision. Never the gate: models aren't deterministic.
- **Verification in CI:** macOS runners are costly; journeys per PR or nightly, and where evidence is published.
- **Harmonize 2.0** (beta) generates an agent skill from the rules: would replace a hand-written rule index. Re-evaluate when stable.
- **Comment policy** we'd actually enforce.
- **Which changes may merge on evidence alone**, and when to add the outer loop.
