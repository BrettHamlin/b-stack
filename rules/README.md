# Rules

Each rule turns a recurring agent mistake into enforcement, with tests that prove it fires. Run them all with `python3 scripts/test_rules.py`; validate the format with `python3 scripts/check_repo.py`.

## Layout

```
rules/<rule-id>/
  rule.toml                   the rule
  ios/<case-name>/
    case.toml                 what must happen
    Sources/<Module>/*.swift  code overlaid onto the starter package
```

### rule.toml

| Key | Meaning |
|---|---|
| `id` | Same as the folder name |
| `layer` | `1` compiler, `2` checker, `1+2` both, `3` verification, `foundation` repo protection |
| `summary`, `problem` | One line each |
| `message` | What the agent sees: what's wrong, what to use instead, stop and report if blocked |
| `escape_hatches` | Ways around the rule, and what blocks each |
| `origin` | Where the rule came from |
| `[ios]` | `compiler` / `checker` / `repo`: how it's enforced on iOS. `tests_pending` if no cases exist yet, with the reason. |

### case.toml

| Key | Meaning |
|---|---|
| `expect` | `fail` (must be rejected) or `pass` (must be accepted) |
| `enforced_by` | `compiler` (tested now) or `checker` (must compile; PENDING until the checker exists) |
| `diagnostic` | For compiler fail cases: text the compiler error must contain |

Every rule needs at least one `fail` case, unless `tests_pending` explains why.

## Catalog

| Rule | Layer | Summary |
|---|---|---|
| [module-boundaries](module-boundaries/rule.toml) | 1+2 | Modules depend and import only in the allowed directions |
| [typed-identifiers](typed-identifiers/rule.toml) | 1 | IDs and units are distinct types, not raw primitives |
| [exhaustive-states](exhaustive-states/rule.toml) | 1 | State is a sum type matched without a catch-all default |
| [retired-apis](retired-apis/rule.toml) | 1 | Retired APIs fail to compile, naming the replacement |
| [explicit-dependencies](explicit-dependencies/rule.toml) | 1 | Dependencies are passed in; no singletons |
| [no-concurrency-escapes](no-concurrency-escapes/rule.toml) | 1+2 | Strict concurrency on; its escape hatches banned |
| [no-suppressions](no-suppressions/rule.toml) | 2 | No suppression comments outside an allowlist |
| [typed-ui-identifiers](typed-ui-identifiers/rule.toml) | 1 | UI identifiers are constants, not string literals |
| [protected-enforcement](protected-enforcement/rule.toml) | foundation | Enforcement files need a human code owner to change |
