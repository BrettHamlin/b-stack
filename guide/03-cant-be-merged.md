# 03 · Layer 2: Can't be merged

**Status:** Draft. Discussed and agreed.

Layer 2 catches what the compiler can't: escape hatches, imports the compiler allows, and config changes. Agents can edit anything in their working copy, so **a layer-2 check only counts if it runs somewhere the agent can't change**. That's protected CI; see [04 · Foundation](04-foundation.md).

## What layer 2 checks

1. **Escape hatches.** Ban the language's ways around the compiler outside an explicit allowlist: force unwraps, unchecked concurrency markers, unsafe casts, `any`, ignore comments.
2. **Suppression comments.** Agents *will* write `// lint:disable` or a language's ignore pragma. Forbid them, or allow them only in allowlisted files with a reference to a ticket.
3. **Import and dependency graph.** Keep a committed file listing which module may depend on which, and which system frameworks each module may import. Compare the real graph and the real imports against it. This covers what the compiler misses: indirect imports, platform frameworks, and new dependencies added to the build manifest.
4. **Build settings.** Assert the language mode, strictness flags and warnings-as-errors are still on. Prefer **generating** project files from a small manifest, so hand edits to large generated files can't hide setting changes.
5. **Project-specific bans.** APIs that are legal but wrong here, such as raw timers in feature code or direct database access from UI. Each one needs a supported replacement first.

## Check the parsed code, not the text

Regex-based lint is fooled by formatting, aliases and comments. Use a tool that parses the code: a SwiftSyntax checker, an ESLint or Clippy rule, a Python `ast` walker, or a dependency analyzer. Start with regex if it unblocks you, then move rules to a parser-based tool as they prove valuable.

## The ratchet

Some exceptions are legitimate, such as wrapping a C library. Record existing ones in a **baseline** committed to the repo:

- New violations fail the build.
- Removing a violation is always allowed, and the baseline shrinks.
- The baseline itself is a protected file.

The count can only go down. That's how you adopt a rule in an existing codebase without stopping all work.

## Where checks run

| Where | Purpose | Can be bypassed? |
|---|---|---|
| Agent hooks / editor | Instant feedback | Yes; it's for convenience |
| Pre-commit | Fast local feedback | Yes (`--no-verify`) |
| **Required CI check on a protected branch** | **The actual gate** | **No, as long as the [foundation](04-foundation.md) holds** |

Run the same command in all three places, so passing locally predicts passing in CI.

## Good layer-2 diagnostics

Each failure message should state:
- what was found and where
- why it's banned (one line)
- **what to use instead**, and where it lives
- what to do if the replacement doesn't fit: *stop and report*, never suppress

## Don't over-rule

Each rule should eliminate a meaningful class of failure. Personal style preferences belong in a formatter, not the rules catalog. A rule with no supported replacement creates pressure for worse workarounds.
