# iOS starter

Copied into a new repo by the [new-project skill](../../skills/new-project/SKILL.md). It's built up in stages. Only what's listed as built exists; the rest is planned.

## What's built

| Piece | Path | Status |
|---|---|---|
| Strict Swift package: Domain, Data, Features | `template/Modules/` | ✅ Builds with Swift 6.4.2; every rule test runs against it |
| Allowed module graph | `template/boundaries.yaml` | ✅ Draft; nothing reads it until the checker exists |
| Agent instructions | `template/AGENTS.template.md` | ✅ Draft; has placeholders for unbuilt commands |
| Enforcement-surface owners | `template/CODEOWNERS` | ✅ Draft; owner must be filled in |
| Feature map example, evidence template | `template/feature-map/`, `template/evidence.template.md` | Draft; format pending the verification discussion |

## Not built yet (in order)

1. **Checker:** a SwiftSyntax tool that turns every PENDING rule case into PASS. First the import check against `boundaries.yaml` (it covers the compiler's gaps), then escape hatches and suppressions.
2. **App target:** an Xcode project generated from a manifest, with a composition root and a fixture launch mode.
3. **CI:** a workflow running the build, the checker and `test_rules.py --package Modules` as required checks.
4. **Verification:** shared `UIID` identifiers, an XCUITest-based driver, one feature-map entry with evidence.
5. **Extract:** after the first real app, update this template from what worked.

## Strict settings in `Modules/Package.swift`

| Setting | Effect |
|---|---|
| `swiftLanguageModes: [.v6]` | Strict concurrency: data races are errors |
| `.defaultIsolation(MainActor.self)` on Features | UI code is main-actor by default |
| `InternalImportsByDefault` | Imports aren't re-exported unless marked `public` |
| `MemberImportVisibility` | Members don't leak through indirect imports |
| `ExistentialAny` | `any Protocol` must be written explicitly |
| `.treatAllWarnings(as: .error)` | Warnings block the build |
