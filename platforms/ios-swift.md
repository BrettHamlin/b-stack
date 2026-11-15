# Platform: iOS / Swift

**Status:** Draft. Layer 1 settings verified with Swift 6.4.2 / Xcode 27.2 (Nov 15, 2026). Layer 2 tooling and verification not yet built.

## Recommended shape

- A thin Xcode app target, plus **local Swift packages** holding almost all the code, one target per architectural module. SwiftPM makes module boundaries and compiler settings explicit and reviewable.
- Generate the Xcode project from a manifest (Tuist or XcodeGen; not chosen yet) so `project.pbxproj` is never hand-edited and can't hide setting changes.

## Layer 1: compiler settings

Verified to build with Swift 6.4.2:

```swift
// swift-tools-version: 6.2
import PackageDescription

let strict: [SwiftSetting] = [
    .enableUpcomingFeature("InternalImportsByDefault"),  // imports aren't re-exported unless marked public
    .enableUpcomingFeature("MemberImportVisibility"),    // no members leaking through indirect imports
    .enableUpcomingFeature("ExistentialAny"),            // `any Protocol` must be written explicitly
    .treatAllWarnings(as: .error),
]

let package = Package(
    name: "AppModules",
    platforms: [.iOS(.v18)],
    targets: [
        .target(name: "Domain", swiftSettings: strict),
        .target(name: "Data", dependencies: ["Domain"], swiftSettings: strict),
        .target(name: "Features", dependencies: ["Domain"],
                swiftSettings: strict + [.defaultIsolation(MainActor.self)]),  // UI code is main-actor by default
    ],
    swiftLanguageModes: [.v6]  // strict concurrency: data races are errors
)
```

The module list is illustrative. Each project defines its own in its boundaries file.

## What the compiler actually enforces

Tested on Nov 15, 2026 with a scratch package:

| Attempt | Result |
|---|---|
| Pass `String` where `UserID` is expected | ✅ `cannot convert value of type 'String' to expected argument type 'UserID'` |
| Add an enum case without updating a `switch` | ✅ `switch must be exhaustive` |
| Use a `~Copyable` value twice | ✅ `'k' consumed more than once` |
| Call an `@available(*, unavailable, message:)` API | ✅ error shows the custom message naming the replacement |
| Unused value, with warnings as errors | ✅ error |
| Detached task mutating main-actor state | ✅ `main actor-isolated property 'n' can not be mutated from a nonisolated context` |
| Import a sibling module not declared as a dependency | ✅ `unable to resolve module dependency` |
| **Import a module reachable only indirectly** (App → Features → Domain; App imports Domain) | ❌ **compiles**, even with `--explicit-target-dependency-import-check error` |
| **`import SwiftUI` in Domain** | ❌ **compiles**; system frameworks are always importable |
| `@unchecked Sendable`, `nonisolated(unsafe)`, `!` force unwrap | ❌ compile, as expected for escape hatches |

**So module boundaries are only partly a compiler guarantee in Swift.** The ❌ rows must be covered by the layer-2 import check.

## Layer 2: checks (to build)

A SwiftSyntax-based checker, run as one command locally and in CI. First rules:

- **Import check:** every `import` in a module must be allowed by the boundaries file, including system frameworks (e.g. Domain may import `Foundation` only)
- **Escape hatches**, outside an allowlist: `@unchecked Sendable`, `nonisolated(unsafe)`, `@preconcurrency import`, `Task.detached` in feature code, `DispatchQueue` and `asyncAfter` in feature code, `try!`, `as!`, force unwrap `!`, `unsafeBitCast`, `Unsafe*Pointer`
- **Suppressions:** `swiftlint:disable` and similar comments
- **Catch-all `default:`** on project-owned enums
- **Globals:** `static let shared` / global `var` outside the composition root
- **Accessibility IDs:** string literals passed to `.accessibilityIdentifier(_:)`
- **Settings:** `Package.swift` still uses Swift 6 language mode and the `strict` settings on every target; the dependency graph from `swift package describe --type json` matches the boundaries file

SwiftLint (`--baseline` supported) may cover some of these quickly. The parsed-code checker is the long-term home.

## Foundation

CODEOWNERS on `Package.swift`, the project manifest, the boundaries file, checker source and config, allowlists and baselines, `.github/`, `AGENTS.md`, `.claude/`. CI on a macOS runner runs `xcodebuild` plus the checker as required checks.

## Layer 3: verification (to discuss)

- Driver built on **XCUITest**, with a launch argument that starts the app in a fixture mode (isolated storage, seeded account, local or fake backend)
- Identifiers from a shared `UIID` enum used by both the app and the tests
- Simulator evidence covers the simulator only. Push delivery, background suspension, power use and distribution need device or release checks.

## Rule mapping

| Rule | iOS / Swift enforcement |
|---|---|
| [module-boundaries](../rules/module-boundaries.md) | SwiftPM targets + `InternalImportsByDefault` (layer 1); import check against the boundaries file for indirect imports and system frameworks (layer 2) |
| [typed-identifiers](../rules/typed-identifiers.md) | `struct UserID: Hashable, Sendable`; validated types with private `init` and a failable `parse` |
| [exhaustive-states](../rules/exhaustive-states.md) | Enums with associated values; checker bans `default:` on project enums |
| [retired-apis](../rules/retired-apis.md) | `@available(*, unavailable, message:)` for owned APIs; checker bans platform APIs in feature modules |
| [explicit-dependencies](../rules/explicit-dependencies.md) | Initializer injection, protocols in the consuming module, one composition root; checker bans `static let shared` |
| [no-concurrency-escapes](../rules/no-concurrency-escapes.md) | Swift 6 mode + `defaultIsolation(MainActor.self)` for UI; checker bans `@unchecked Sendable`, `nonisolated(unsafe)`, `@preconcurrency`, `Task.detached`, `DispatchQueue` in features |
| [no-suppressions](../rules/no-suppressions.md) | Checker bans `swiftlint:disable` etc.; allowlist file |
| [protected-enforcement](../rules/protected-enforcement.md) | CODEOWNERS + branch protection; settings check on `Package.swift` and the graph |
| [typed-ui-identifiers](../rules/typed-ui-identifiers.md) | Shared `UIID` enum; checker bans string literals in `.accessibilityIdentifier` |
