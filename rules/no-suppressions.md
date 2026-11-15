# no-suppressions

**Status:** Draft
**Layer:** 2

## Problem
The quickest way past any lint rule is a suppression comment (`// swiftlint:disable`, `// eslint-disable`, `# type: ignore`, `#[allow(...)]`). Agents use them freely under pressure to finish.

## Layer
Layer 2. The compiler doesn't care about comments, so this must be a check in protected CI.

## Enforcement
- Ban every suppression syntax for the tools in use
- Allow exceptions only in an allowlist file (protected), each with a reason and a ticket reference
- Count existing ones in a baseline that can only shrink

## Error message
> Suppression comments aren't allowed. Fix the underlying issue. If the rule is wrong for this case, stop and report; exceptions are added to the allowlist by a human.

## Escape hatches
- Editing the lint config to disable the rule → config is [protected](protected-enforcement.md)
- Moving code into an allowlisted file → allowlist changes need a code owner

## Origin
Our discussion of how agents get around linters.
