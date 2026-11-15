# Rules catalog

Reusable rules, collected across projects. Each one turns a recurring agent mistake into enforcement placed as high on the [pyramid](../guide/01-pyramid.md) as it will go. New projects start by picking rules from here; the [correction loop](../playbook/correction-loop.md) adds to it.

## Entry format

One file per rule, named `<rule-id>.md`. Every entry must have these sections, and `scripts/check_guide.py` enforces it:

```markdown
# <rule-id>

**Status:** Draft | Proven in <project>
**Layer:** 1 | 2 | 3 | Foundation

## Problem
The failure class, and why agents fall into it.

## Layer
Where it's enforced, and why it can't go higher.

## Enforcement
How, in general terms. Platform specifics go in platforms/<platform>.md.

## Error message
The message the agent sees: what's wrong, what to use instead, what to do if blocked.

## Escape hatches
The ways around it, and how each is blocked.

## Origin
Where this rule came from.
```

Every rule must also appear in each platform file under `platforms/`, even if only to say "not applicable" or "to do."

## Rules

| Rule | Layer | Summary |
|---|---|---|
| [module-boundaries](module-boundaries.md) | 1 + 2 | Modules may only depend in the allowed direction |
| [typed-identifiers](typed-identifiers.md) | 1 | IDs and units are distinct types, not raw primitives |
| [exhaustive-states](exhaustive-states.md) | 1 | States are sum types matched without a catch-all default |
| [retired-apis](retired-apis.md) | 1 | Retired or banned APIs fail to compile, naming the replacement |
| [explicit-dependencies](explicit-dependencies.md) | 1 | Dependencies are passed in; no singletons or globals |
| [no-concurrency-escapes](no-concurrency-escapes.md) | 1 + 2 | Strict concurrency on; its escape hatches are banned |
| [no-suppressions](no-suppressions.md) | 2 | No lint or compiler suppression comments outside an allowlist |
| [protected-enforcement](protected-enforcement.md) | Foundation | The enforcement surface can't change without a human |
| [typed-ui-identifiers](typed-ui-identifiers.md) | 1 | UI test identifiers are compiler-checked constants |
