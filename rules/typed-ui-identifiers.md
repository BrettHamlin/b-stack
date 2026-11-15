# typed-ui-identifiers

**Status:** Draft
**Layer:** 1

## Problem
The verification driver finds UI elements by identifier. When identifiers are loose strings, a typo or rename breaks verification silently, and agents invent new names instead of reusing existing ones.

## Layer
Layer 1. Identifiers are constants that the app and the driver/tests both reference, so a mismatch fails to compile.

## Enforcement
- One shared module or file of identifiers (e.g. an enum per screen), used by both the app and the UI tests/driver
- Layer 2: ban string literals passed to the accessibility-identifier API in product code
- Identifiers are stable; renaming one is a deliberate change

## Error message
> Use a constant from `UIID` instead of a string literal for accessibility identifiers. Add a new case if none fits.

## Escape hatches
- String literals → layer-2 ban
- Matching elements by visible text in tests → driver convention prefers identifiers; review

## Origin
Our discussion of what verification needs from the architecture. Lauren's driver example clicks by accessible name.
