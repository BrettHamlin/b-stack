# no-concurrency-escapes

**Status:** Draft
**Layer:** 1 + 2

## Problem
Concurrency bugs (races, UI updates from background threads, state without a clear owner) are subtle, and agents fix them with quick dispatches or delays. When the compiler objects, agents reach for the escape hatches that silence it.

## Layer
Layer 1: the language's strict concurrency checking. Layer 2: ban the escape hatches, because the compiler accepts them.

## Enforcement
- Strictest concurrency mode on (e.g. Swift 6 language mode; UI modules isolated to the main actor by default)
- Layer-2 ban outside an allowlist: unchecked-sendable markers, unsafe nonisolated state, compatibility imports that silence checking, detached tasks in feature code, ad-hoc dispatch or delay calls in feature code
- Provide approved primitives for background work and cancellation

## Error message
> `@unchecked Sendable` isn't allowed here. Make the type an actor, or confine it to the main actor. If neither fits, stop and report what you're trying to share.

## Escape hatches
- Every marker listed above → layer-2 AST check with allowlist and baseline
- Hand-rolled locks around shared mutable state → review; prefer actors

## Origin
Lauren Tan talk (timer and scheduling workarounds). Verified in Swift 6: a detached task mutating main-actor state fails to compile, while `@unchecked Sendable` and `nonisolated(unsafe)` compile fine, hence the layer-2 ban.
