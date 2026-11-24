# Rules

Each rule turns a recurring agent mistake into enforcement, with test cases that prove it fires. A rule is enforced per platform (iOS, Rust, TypeScript, Android), each with its own cases. `python3 scripts/test_rules.py` runs every case through its platform's starter gate command (`scripts/check.py`), one platform after another; `--platform ios`, `--platform rust`, `--platform typescript` or `--platform android` runs one. `python3 scripts/check_repo.py` validates the format. What each platform's cases may change is in `scripts/platforms.py`.

## Layout

```
rules/<rule-id>/
  rule.toml                   the rule
  ios/<case-name>/
    case.toml                 what must happen
    Targets/<Target>/*.swift  code overlaid onto the starter's Targets/
    feature-map/*.toml        overlaid onto feature-map/
    Tuist/ProjectDescriptionHelpers/Features.swift   replaces the feature declaration (starter-only cases)
  rust/<case-name>/
    case.toml                 what must happen
    crates/**                 overlaid onto the starter's crates/ (usually a new crate, e.g. crates/features/probe/)
    feature-map/*.toml        overlaid onto feature-map/
  typescript/<case-name>/
    case.toml                 what must happen
    packages/**, apps/**      overlaid onto the starter's (usually a new package, e.g. packages/features/probe/)
    feature-map/*.toml        overlaid onto feature-map/
  android/<case-name>/
    case.toml                 what must happen
    features/**, platform/**, core/**, app/**, verify/**, ...   overlaid onto the starter's module folders (usually a
                              feature of the case's own, features/probe/{api,logic,ui}, or platform/probe/)
    feature-map/*.toml        overlaid onto feature-map/
rules/case-feature/ios/       Meter: a small iOS feature any case can bring (case_feature = true)
  feature.toml                its declaration, added to the project's Features.swift
  Targets/<Target>/*.swift    its modules, plus the files App, AppVerify, Platform and journeys need to use them
```

### rule.toml

| Key | Meaning |
|---|---|
| `id` | Same as the folder name |
| `layer` | `1` compiler, `2` lint/architecture checks, `1+2` both, `3` verification, `foundation` repo protection |
| `summary`, `problem` | One line each |
| `message` | What the agent sees: what's wrong, what to use instead, stop and report if blocked |
| `escape_hatches` | Ways around the rule, and what blocks each |
| `origin` | Where the rule came from |
| `[ios]`, `[rust]`, `[typescript]`, `[android]` | One table per platform the rule is enforced on, at least one. One key per enforcing tool saying how (iOS: `compiler`, `tuist`, `swiftlint`, `harmonize`, `tests`, `verify`, `repo`; Rust: `compiler`, `clippy`, `deny`, `arch`, `tests`, `verify`, `repo`; TypeScript: `compiler`, `lint`, `deps`, `arch`, `settings`, `tests`, `verify`, `repo`; Android: `compiler`, `detekt`, `konsist`, `arch`, `deps`, `tests`, `verify`, `repo`). `tests_pending` if no cases exist yet, with the reason. Optional `layer` and `message` when they differ on that platform. |

### case.toml

| Key | Meaning |
|---|---|
| `expect` | `fail` (must be rejected) or `pass` (must be accepted by every gate except `verify`, which runs on the untouched project: on iOS it drives a simulator, and a case's code isn't a mapped feature) |
| `enforced_by` | The gate that must reject a fail case. iOS: `compiler`, `tuist`, `swiftlint`, `harmonize`, `tests` or `verify`. Rust: `compiler`, `clippy`, `deny`, `arch`, `tests` or `verify`. TypeScript: `compiler`, `lint`, `deps`, `arch`, `settings`, `tests` or `verify`. Android: `compiler`, `detekt`, `konsist`, `arch`, `deps`, `tests` or `verify` |
| `diagnostic` | Fail cases: text the gate's output must contain |
| `uses_example` | `false` if the case applies to any app, or a short reason it uses the starter's example (iOS: Settings; Rust, TypeScript and Android: tally; its modules, identifiers, journeys, fixtures or feature map). Required. Example cases run only on the starter; `test_rules.py --project <app>` lists them as OUT with the reason. `check_repo.py` fails a `false` case whose files mention the example, or (iOS) that replaces Features.swift, which would drop the app's own features |
| `adds_targets` | Optional: targets (iOS) or folders directly under `crates/` (Rust), `packages/` (TypeScript) or `features/` (Android) the case adds that the project doesn't have (otherwise a missing one is a SKIP) |
| `case_feature` | Optional, iOS: `true` adds the case feature (`rules/case-feature/ios`: modules `MeterInterface`, `MeterLogic`, `Meter`, `MeterTests`, identifiers `MeterUIID`) before the case's own files, so the case can put code in a feature's modules on any app |
| `features` | Optional, iOS: Swift declarations (`'Feature("CaseProfile", links: [...])'`) added to the front of the project's `features` list, keeping the app's own. A project that already has a feature with a declared name (the case feature's too) SKIPs the case |
| `shared_links` | Optional, iOS: `SharedLink` cases (`"appUsesPlatform"`) added to the project's `sharedLinks` |
| `generate_adapters` | Optional, iOS: `true` runs `scripts/verify.py adapters` after the overlay, as an agent does after adding a journey body |
| `needs_fixtures` | Optional, iOS: fixtures the case's feature map names that must already exist (e.g. `["standard"]`, the starter's default); a project without one SKIPs the case |
| `edits` | Optional: `[[edits]]` tables (`file`, `find`, `replace`) applied to a protected project file (iOS: `Project.swift`; Rust: the root `Cargo.toml` or `Cargo.lock`; TypeScript: the root `package.json`, `pnpm-lock.yaml`, `pnpm-workspace.yaml`, `tsconfig.base.json`, `tsconfig.effect.json`, `vite.config.ts` or `CODEOWNERS`; Android: `gradle/libs.versions.toml`, `settings.gradle.kts`, `gradle.properties` or `CODEOWNERS`), for cases about hand edits. `find` must occur exactly once, or the case FAILs |

Every rule needs at least one `fail` case, unless `tests_pending` explains why.

## Catalog

| Rule | Layer | iOS | Rust | TypeScript | Android | Summary |
|---|---|---|---|---|---|---|
| [module-boundaries](module-boundaries/rule.toml) | 1+2 | compiler, Tuist, Harmonize | compiler, arch | compiler, oxlint, arch | compiler, Konsist, arch | Modules depend and import only in the allowed directions |
| [typed-identifiers](typed-identifiers/rule.toml) | 1 | compiler | compiler | compiler | compiler, Konsist | IDs and units are distinct types, not raw primitives |
| [exhaustive-states](exhaustive-states/rule.toml) | 1+2 | compiler, Harmonize | compiler, Clippy | oxlint | compiler, detekt | Enum switches handle every case; no catch-all default |
| [retired-apis](retired-apis/rule.toml) | 1 | compiler | compiler, Clippy | oxlint | compiler, detekt | Retired APIs fail to compile, naming the replacement |
| [explicit-dependencies](explicit-dependencies/rule.toml) | 1+2 | Harmonize | arch | compiler, oxlint | Konsist | Dependencies are passed in; no singletons or global state |
| [no-concurrency-escapes](no-concurrency-escapes/rule.toml) | 1+2 | compiler, Harmonize | compiler | oxlint | compiler, detekt, Konsist | Strict concurrency on; its escape hatches banned (Rust: unsafe forbidden; TypeScript: every promise awaited, no raw timers) |
| [no-force-operations](no-force-operations/rule.toml) | 2 | SwiftLint | Clippy | oxlint | detekt | No force unwrap, force try or force cast (Rust: unwrap, expect, panic, indexing, `as`; TypeScript: `!`, `as`, `any`) |
| [no-suppressions](no-suppressions/rule.toml) | 2 | SwiftLint | arch | arch | arch | No lint suppressions (Rust: also no lint-level changes, build scripts, or macros that hide code) |
| [typed-ui-identifiers](typed-ui-identifiers/rule.toml) | 1+2 | compiler, Harmonize, verify |  | compiler, oxlint | compiler, Konsist, verify | Typed journey bodies cannot import XCUITest; only generated adapters use XCTestCase (TypeScript: journeys use a typed Screen) |
| [no-io-in-logic](no-io-in-logic/rule.toml) | 2 | Harmonize | compiler, arch | compiler, oxlint, arch | compiler, Konsist, arch | Feature logic does no I/O; effects call injected clients (Rust: `no_std`; TypeScript: no Node.js or DOM types) |
| [io-only-in-platform](io-only-in-platform/rule.toml) | 2 | Harmonize |  |  | compiler, Konsist | Only Platform (and test mode's Fixtures) does network, disk, preferences, keychain or environment I/O |
| [thin-app](thin-app/rule.toml) | 2 | Harmonize |  |  | Konsist | The shipped App only composes screens and services; no decisions, functions or tasks |
| [views-hold-no-clients](views-hold-no-clients/rule.toml) | 1+2 | compiler, Harmonize |  |  | compiler, Konsist | A feature's view gets only its store; clients go into the reducer |
| [exhaustive-tests](exhaustive-tests/rule.toml) | 2 | Harmonize |  | oxlint | Konsist | TCA tests stay exhaustive (no exhaustivity off or skips; TypeScript: whole-value assertions) |
| [tests-always-run](tests-always-run/rule.toml) | 2 | tests | tests, arch | tests, oxlint, arch | tests, Konsist, arch | Every test target runs in the tests gate |
| [no-fixtures-in-release](no-fixtures-in-release/rule.toml) | 2 | Harmonize, Tuist |  | arch, oxlint | compiler | Only the test-mode app (AppVerify) can use fixtures (TypeScript: only journeys and tests) |
| [allowed-dependencies](allowed-dependencies/rule.toml) | 2 |  | arch, cargo-deny | arch, deps | compiler, deps | Third-party packages only from each role's list, the registry, allowed licenses |
| [verified-features](verified-features/rule.toml) | 3 | verify | verify | verify (Playwright) | verify (UiAutomator) | Every feature is in the feature map and its journeys pass in the running app |
| [protected-enforcement](protected-enforcement/rule.toml) | foundation | (not tested yet) | (not tested yet) | settings | (not tested yet) | Enforcement files need a human code owner to change |
