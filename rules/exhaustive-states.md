# exhaustive-states

**Status:** Draft
**Layer:** 1

## Problem
State spread across flags and optionals (`isLoading`, `data?`, `error?`) allows impossible combinations. When a new state is added, agents miss places that should handle it.

## Layer
Layer 1. Sum types plus exhaustive matching make every state explicit, and adding a state breaks every place that doesn't handle it.

## Enforcement
- Model state as enums or sealed types with associated data
- Match without a catch-all `default`, so new cases force updates
- Use typestate where operations are only valid in some states

## Error message
Compiler: `switch must be exhaustive`. The agent has to visit each site and decide.

## Escape hatches
- `default:` / `_ ->` catch-alls → layer-2 check bans catch-alls on project-owned enums
- Going back to bool flags → review; prefer an API shape that makes flags awkward

## Origin
Our discussion. Verified in Swift: adding an enum case fails the build at an exhaustive `switch`.
