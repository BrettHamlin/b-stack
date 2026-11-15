# retired-apis

**Status:** Draft
**Layer:** 1

## Problem
Agents copy old APIs because old code still uses them, and they reach for subtle primitives that need expertise to use correctly. Lauren's examples: `useEffect`, and `setTimeout` used as a quick fix, which spread to 183 timers.

## Layer
Layer 1 for APIs we own: mark them unavailable so they don't compile. Layer 2 for platform APIs we can't mark: a project ban with a replacement.

## Enforcement
1. Provide the supported replacement first
2. Mark the old API unavailable, with a message naming the replacement
3. Migrate existing callers so agents stop copying them

## Error message
> `'legacyTimer()' is unavailable: Use TaskScope.run, which cancels when the feature ends`

## Escape hatches
- Re-creating the API under another name → review; the correction loop adds a check
- Calling the underlying platform API directly → layer-2 ban in product modules, allowed only in the framework layer

## Origin
Lauren Tan talk (Dune bans `useEffect` in product code; timer workarounds). Verified in Swift: `@available(*, unavailable, message:)` fails with the custom message.
