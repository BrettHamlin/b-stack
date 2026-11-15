# typed-identifiers

**Status:** Draft
**Layer:** 1

## Problem
IDs, units and validated values passed as raw `String`/`Int` get mixed up: a message ID passed as a user ID, milliseconds as seconds, unvalidated input treated as valid. The compiler can't help when everything is a `String`.

## Layer
Layer 1. Distinct types make mixing them a compile error.

## Enforcement
- A distinct type per ID or unit (`UserID`, `MessageID`, `Milliseconds`)
- Validated values have a private initializer and a failable parse function, so holding the type proves it's valid
- Optional layer 2: flag public APIs that take raw primitives named `*id`/`*ID`

## Error message
Compiler: `cannot convert value of type 'String' to expected argument type 'UserID'`. The type name itself says what's needed.

## Escape hatches
- Exposing the raw value and re-wrapping freely → keep raw access narrow; constructors that skip validation stay private
- Generic `String` parameters in new APIs → optional layer-2 check plus review

## Origin
Our discussion. Verified in Swift: passing a `String` where `UserID` is expected fails to compile.
