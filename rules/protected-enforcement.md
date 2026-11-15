# protected-enforcement

**Status:** Draft
**Layer:** Foundation

## Problem
Agents can edit anything in their working copy, including compiler flags, lint configs, the dependency graph and CI workflows. Weakening the check is often the cheapest way to make it pass.

## Layer
Foundation. Every other rule depends on this one.

## Enforcement
- The enforcement surface is listed explicitly ([04 · Foundation](../guide/04-foundation.md))
- CODEOWNERS covers it, with code-owner review required ([template](../templates/CODEOWNERS))
- Protected branch, required checks, no agent admin rights
- CI workflow protected from edits in the same PR (CODEOWNERS on `.github/`, or required org workflows)
- A layer-2 settings check asserts strictness flags are on and the graph matches the committed file

## Error message
> This change modifies the enforcement surface (`<file>`). It needs code-owner review. If you changed it to make a check pass, revert and fix the underlying issue, or stop and report.

## Escape hatches
- Moving settings to a file not on the list → the settings check asserts the *effective* settings, not just one file
- Disabling the check in the workflow → workflow protection

## Origin
Our discussion. The same point appears in the research implementation guide: a required check must cover its own configuration.
