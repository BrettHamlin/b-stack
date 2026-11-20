# Rules

Each rule turns a recurring agent mistake into enforcement, with test cases that prove it fires. `python3 scripts/test_rules.py` runs every case through the starter's own gate command (`scripts/check.py`); `python3 scripts/check_repo.py` validates the format.

## Layout

```
rules/<rule-id>/
  rule.toml                   the rule
  ios/<case-name>/
    case.toml                 what must happen
    Targets/<Target>/*.swift  code overlaid onto the starter's Targets/
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
| `[ios]` | One key per enforcing tool (`compiler`, `tuist`, `swiftlint`, `harmonize`, `tests`, `verify`, `repo`) saying how. `tests_pending` if no cases exist yet, with the reason. |

### case.toml

| Key | Meaning |
|---|---|
| `expect` | `fail` (must be rejected) or `pass` (must be accepted by every gate except `verify`, which drives a simulator and runs on the untouched project) |
| `enforced_by` | The gate that must reject a fail case: `compiler`, `tuist`, `swiftlint`, `harmonize`, `tests` or `verify` |
| `diagnostic` | Fail cases: text the gate's output must contain |
| `adds_targets` | Optional: targets the case adds that the project doesn't have (otherwise a missing target is a SKIP) |

Every rule needs at least one `fail` case, unless `tests_pending` explains why.

## Catalog

| Rule | Layer | Enforced by | Summary |
|---|---|---|---|
| [module-boundaries](module-boundaries/rule.toml) | 1+2 | compiler, Tuist, Harmonize | Modules depend and import only in the allowed directions |
| [typed-identifiers](typed-identifiers/rule.toml) | 1 | compiler | IDs and units are distinct types, not raw primitives |
| [exhaustive-states](exhaustive-states/rule.toml) | 1+2 | compiler, Harmonize | Enum switches handle every case; no catch-all default |
| [retired-apis](retired-apis/rule.toml) | 1 | compiler | Retired APIs fail to compile, naming the replacement |
| [explicit-dependencies](explicit-dependencies/rule.toml) | 1+2 | Harmonize | Dependencies are passed in; no singletons |
| [no-concurrency-escapes](no-concurrency-escapes/rule.toml) | 1+2 | compiler, Harmonize | Strict concurrency on; its escape hatches banned |
| [no-force-operations](no-force-operations/rule.toml) | 2 | SwiftLint | No force unwrap, force try or force cast |
| [no-suppressions](no-suppressions/rule.toml) | 2 | SwiftLint | No lint suppression comments |
| [typed-ui-identifiers](typed-ui-identifiers/rule.toml) | 1+2 | compiler, Harmonize, verify | Typed journey bodies cannot import XCUITest; only generated adapters use XCTestCase |
| [no-io-in-logic](no-io-in-logic/rule.toml) | 2 | Harmonize | Feature logic does no I/O; effects call injected clients |
| [exhaustive-tests](exhaustive-tests/rule.toml) | 2 | Harmonize | TCA tests stay exhaustive (no exhaustivity off or skips) |
| [tests-always-run](tests-always-run/rule.toml) | 2 | tests | Every test target runs in the tests gate |
| [no-fixtures-in-release](no-fixtures-in-release/rule.toml) | 2 | Harmonize, Tuist | Only the test-mode app (AppVerify) can use fixtures |
| [verified-features](verified-features/rule.toml) | 3 | verify | Every feature is in the feature map and its journeys pass in the running app |
| [protected-enforcement](protected-enforcement/rule.toml) | foundation | (not tested yet) | Enforcement files need a human code owner to change |
