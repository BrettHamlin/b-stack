# iOS starter

Copied into a new repo by the [new-project skill](../../skills/new-project/SKILL.md). It's built up in stages. Only what's listed as built exists.

## What's built

| Piece | Path | Status |
|---|---|---|
| Tuist project: Core, SettingsInterface, Settings, Platform, App | `template/Project.swift`, `template/Targets/` | ✅ Generates and builds for the iOS Simulator with strict Swift 6 settings |
| Gate command: compiler, Tuist, SwiftLint, Harmonize | `template/scripts/check.py` | ✅ Passes on the template; every rule case runs through it |
| Pinned tools, checksum-verified, no global install | `template/tools.toml`, `template/scripts/tools.py` | ✅ Tuist 4.216.7, SwiftLint 0.65.1 |
| Build output and tools in a configurable cache folder | `template/scripts/paths.py` | ✅ `.build/` becomes a link into it; stops if the folder is missing |
| Architecture rules | `template/Rules/` (Harmonize 1.3.0) | ✅ Allowed imports, singletons, concurrency escapes, catch-all defaults, UI identifiers |
| Lint rules | `template/.swiftlint.yml` | ✅ Force operations, suppression comments |
| Agent instructions, CODEOWNERS | `template/AGENTS.template.md`, `template/CODEOWNERS` | ✅ Draft; placeholders to fill in |
| Feature map example, evidence template | `template/feature-map/`, `template/evidence.template.md` | Draft; format pending the verification discussion |

The Settings feature is an empty example of the module shape (Interface + Implementation). Replace it with real features.

## Module shape

| Target | May depend on | Allowed system imports |
|---|---|---|
| Core | nothing | Foundation |
| `<Feature>Interface` | Core | Foundation |
| `<Feature>` | its Interface, Core, other features' Interfaces | Foundation, SwiftUI, Observation |
| Platform | Core | Foundation |
| App (composition root) | features, Interfaces, Platform | Foundation, SwiftUI |

Module dependencies live in `Project.swift`; Tuist checks code against them. System-framework allowlists live in `Rules/Tests/ArchitectureRules/ModuleBoundaries.swift`; Harmonize checks them.

## Strict settings (Project.swift)

| Setting | Effect |
|---|---|
| `SWIFT_VERSION = 6.0` | Strict concurrency: data races are errors |
| `SWIFT_DEFAULT_ACTOR_ISOLATION = MainActor` on feature and App targets | UI code is main-actor by default |
| `InternalImportsByDefault`, `MemberImportVisibility`, `ExistentialAny` | Imports aren't re-exported; no member leakage; explicit `any` |
| `SWIFT_TREAT_WARNINGS_AS_ERRORS` | Warnings block the build |

## Not built yet (in order)

1. **New-feature command:** creates `<Feature>Interface` + `<Feature>` targets and their allowlist entries, so agents don't hand-write module setup.
2. **CI workflow:** runs `scripts/check.py` and the rule tests as required checks; branch protection.
3. **Settings assertion:** a gate that fails if strict settings in `Project.swift` are weakened (protected-enforcement).
4. **State flow:** decided by the TCA-vs-alternatives trial.
5. **Verification:** fixture launch mode, shared `UIID` identifiers, a driver, one feature-map entry with evidence.
