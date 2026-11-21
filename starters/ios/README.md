# iOS starter

Copied into a new repo by the [new-project skill](../../skills/new-project/SKILL.md). It's built up in stages. Only what's listed as built exists.

## What's built

| Piece | Path | Status |
|---|---|---|
| Tuist project: Core, SettingsInterface, SettingsLogic, Settings, SettingsTests, Platform, Fixtures, App, AppVerify, JourneyKit, AppVerifyJourneys, AppVerifyUITests | `template/Project.swift`, `template/Targets/` | ✅ Generates and builds for the iOS Simulator with strict Swift 6 settings |
| Feature declaration: targets, dependencies and allowed imports derived from the module shape and a feature list | `template/Tuist/ProjectDescriptionHelpers/` | ✅ Agents add features and links inside the shape without editing protected files; hand edits to `Project.swift` fail the harmonize gate |
| TCA 1.26.2, linked once as shared frameworks | `template/Tuist/Package.swift` | ✅ |
| Example feature: notification toggle (save, failure revert, cancellation) with exhaustive TestStore tests | `Targets/Settings*` | ✅ Built by an agent in the state-flow trial |
| Property test for the example feature: 200 seeded random sequences of toggles, waits and closes, checked step by step against a model of the spec; stops at the first divergence and prints its steps | `Targets/SettingsTests/NotificationSettingsPropertyTests.swift` | ✅ About 5 s. No library: a seeded generator in the file |
| Gate command: compiler, Tuist, SwiftLint, Harmonize, tests, verify | `template/scripts/check.py` | ✅ Every gate passes; full rule suite 103/103 (2026-11-21, Xcode 27.2, iOS 27.2 Simulator) |
| Verification: test-mode app (`AppVerify` + `Fixtures`), XCUITest journeys, feature map, evidence with screenshots | `template/scripts/verify.py`, `template/Targets/AppVerify*`, `template/Targets/Fixtures`, `template/feature-map/` | ✅ Two Settings journeys (saved across relaunch; failed save reverts), run on the simulator by the rule suite |
| Verify skill for agents in the new app: run, explore with agent-device, add journeys | `template/.agents/skills/verify/` | ✅ |
| Pinned tools, checksum-verified, no global install | `template/tools.toml`, `template/scripts/tools.py` | ✅ Tuist 4.216.7, SwiftLint 0.65.1 |
| Build output and tools in a configurable cache folder | `template/scripts/paths.py` | ✅ `.build/` becomes a link into it; stops if the folder is missing |
| Architecture rules | `template/Rules/` (Harmonize 1.3.0) | ✅ Allowed imports, singletons, concurrency escapes, catch-all defaults, UI identifiers (views and journeys), no I/O in Logic, exhaustive tests, no fixtures outside AppVerify |
| Lint rules | `template/.swiftlint.yml` | ✅ Force operations, suppression comments |
| Check record, observe mode: check.py records the git tree each run saw. `audit` says whether any commit's tree was checked (squash merges included; a check after the commit counts); each Claude Code hand-back is logged for every checkout the session worked in (Stop hook, headless too); each commit gets a `Checked:` trailer. Never blocks | `template/scripts/handback.py`, `template/.claude/settings.json`, `template/.githooks/`, `template/.gitignore` | ✅ `python3 scripts/handback.py audit main~5..main`, `summary`. Records are in the clone's git folder, local to that machine. Codex has no hand-back hook here; its commits are stamped and audited |
| Agent instructions, CODEOWNERS | `template/AGENTS.template.md`, `template/CODEOWNERS` | ✅ Draft; placeholders to fill in |

Journeys live in `Targets/AppVerifyJourneys`, inheriting JourneyKit's `Journey` helpers. `Screen.find(_ id: UIID)`
returns an `Element` wrapper; no SDK app, element, query or screenshot is public. `python3 scripts/verify.py adapters`
generates the XCTestCase entry points in `Targets/AppVerifyUITests`; the map/verify gate rejects handwritten adapters
or extra runner files. Reflection and Objective-C dynamic access remain a Harmonize ban. The SDK's XCTest
module re-exports XCUIAutomation, so putting journey bodies in the XCTestCase target would reopen raw lookups.

The Settings feature is a small, complete example of the feature shape, including its feature-map entry and journeys. New features copy its pattern; replace it once real features exist.

## Module shape

| Target | May depend on | Allowed system imports |
|---|---|---|
| Core | nothing | Foundation |
| `<Feature>Interface` | Core | Foundation (also holds the feature's `UIID` constants) |
| `<Feature>Logic` | its Interface, Core, TCA | Foundation, ComposableArchitecture (no I/O APIs) |
| `<Feature>` | its Logic and Interface, Core, TCA | Foundation, SwiftUI, Observation, ComposableArchitecture |
| `<Feature>Tests` | its Logic and Interface, Core, TCA | (test code) |
| Platform | Core, Interfaces it implements | Foundation |
| Fixtures (test-mode setups) | Platform, Interfaces, Core | Foundation |
| App (composition root, shipped) | features, Interfaces, Platform | Foundation, SwiftUI |
| AppVerify (composition root, test mode) | features, Interfaces, Fixtures | Foundation, SwiftUI |
| JourneyKit (typed UI driver) | Core | XCTest (internal import; library evolution enabled) |
| AppVerifyJourneys (journey bodies) | JourneyKit, Interfaces | Foundation; no testing search paths |
| AppVerifyUITests (generated adapters) | AppVerify, AppVerifyJourneys | XCTest |

This table is `template/Tuist/ProjectDescriptionHelpers/ModuleShape.swift` (protected). Features, and the links each uses from the table, are declared in `Features.swift` next to it; that file is the only one agents edit to add a feature or a link, and it can only name links in the table. `Project.swift` builds every target from the two; Tuist checks imports against the declared dependencies, and Harmonize (`ModuleBoundaries.swift`, which compiles the same two files) checks system imports, that the generated project matches the declaration, and that every declared module has its folder. "Interfaces it implements" and App → Platform are optional links (`.platformImplementsInterface`, `.appUsesPlatform`), as are a feature's Logic, view or tests using Core, Fixtures using Core, Platform or an Interface, and App or AppVerify using an Interface.

## Strict settings (Project.swift)

| Setting | Effect |
|---|---|
| `SWIFT_VERSION = 6.0` | Strict concurrency: data races are errors |
| `SWIFT_DEFAULT_ACTOR_ISOLATION = MainActor` on feature and App targets | UI code is main-actor by default |
| `InternalImportsByDefault`, `MemberImportVisibility`, `ExistentialAny` | Imports aren't re-exported; no member leakage; explicit `any` |
| `SWIFT_TREAT_WARNINGS_AS_ERRORS` | Warnings block the build |
| `-enable-library-evolution` on JourneyKit; distribution build on Core | Internal XCTest types stay out of journey clients |
| `ENABLE_TESTING_SEARCH_PATHS = NO` on AppVerifyJourneys | XCTest/XCUIAutomation imports fail in journey bodies |

## Not built yet (in order)

1. **New-feature command:** creates a feature's four module folders, feature-map entry and journey stub (targets and allowed imports already come from `Features.swift`).
2. **CI workflow:** runs `scripts/check.py` and the rule tests as required checks; branch protection; evidence attached to PRs.
3. **Settings assertion:** a gate that fails if strict settings in `Project.swift` are weakened (protected-enforcement).
4. **Exploration at scale:** UI property testing (random action sequences checking invariants) with a fast computer-use model; see Jev in `DECISIONS.md`.
