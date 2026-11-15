# Decisions

For the human owner: what we decided and why. Agents work from `skills/`, `rules/` and `starters/`, not this file.

## Purpose

b-stack lets anyone clone it and have an agent set up a new app where quality is **enforced, not requested**. It started from Lauren Tan's talk *All Code Is Slop (Except Mine)* (`research/`) and goes beyond it.

## Core beliefs

- **Agents repeat the same mistakes** across runs, so a check pays off every time it fires. Correcting in chat fixes one instance.
- **Every agent session is a new hire on day one.** Onboarding aids (paved paths, obvious structure) are needed permanently.
- **Code is the agents' memory.** They copy existing patterns, so the first patterns in a repo become the template. Enforcement must exist from the first commit.
- **Architecture first, enforced right away.** A rule needs a correct path to point to; architecture is a decision, a rule makes it executable.
- **Verification is now cheap** (property tests, models, journey checks), so use it.
- **Don't automate a bad loop.** One reliable agent loop comes before triggers and fleets.

## The enforcement pyramid

Sorted by how hard each layer is to get around (Lauren's sorts by kind of thing):

| Layer | Meaning | Enforced by |
|---|---|---|
| 1. Can't be written | The wrong thing won't compile | Types, modules, compiler settings |
| 2. Can't be merged | A check blocks it before `main` | Parsed-code checker in protected CI |
| 3. Can't pass verification | The running product behaves wrong | Journey, property, formal tests |
| 4. Guided | Steers judgment; enforces nothing | Prose (minimal) |
| 5. Judged | Is the intent right? | Human review of evidence |
| Foundation | Nobody weakens the checks unnoticed | CODEOWNERS, branch protection, settings checks |

Rule: push every constraint as high as it goes.

## Decisions

| Date | Decision | Why |
|---|---|---|
| 2026-11-15 | The repo is for **agents first**: rules with tests, starters, skills. Prose is minimal; this file is the human summary. | Prose is the weakest layer. A repo about enforcement should be enforced itself. |
| 2026-11-15 | Rules are data plus **fail/pass test cases** run against the real compiler. | A rule that has never fired is unproven. |
| 2026-11-15 | Skills are plain `SKILL.md` folders. | Works in Claude Code and Codex. |
| 2026-11-15 | iOS is the first platform. | Owner's current focus. |
| 2026-11-15 | Starter templates are extracted from a real app, not designed up front. | Make one loop dependable before scaling. |
| 2026-11-15 | Every project gets a "stop and report" escalation rule. | Agents work around rules when the only options are comply or fail. |

## Verified findings (Swift 6.4.2, Xcode 27.2)

Most are tested on every run of `scripts/test_rules.py`; `~Copyable` was checked by hand. Notable results:

- **Compiler enforces:** distinct ID types, exhaustive switches, `~Copyable` single use, unavailable APIs (with a custom message), warnings as errors, main-actor isolation.
- **Strict settings reject an unneeded `public import`.**
- **Module boundaries are only partly a compiler guarantee.** An undeclared sibling import fails on a clean build only; once the sibling is built, incremental builds accept it. Indirect imports and system frameworks (e.g. `SwiftUI` in Domain) always compile. The checker must cover all three.
- **The compiler accepts every escape hatch** (`@unchecked Sendable`, `nonisolated(unsafe)`, `!`), so the checker must ban them.

## Open questions

- **Verification design** (next discussion): feature map format, driver (own CLI on XCUITest vs existing harness), evidence storage, CI cost.
- **Checker:** SwiftSyntax from day one, or SwiftLint as a stopgap?
- **Project generation:** Tuist vs XcodeGen vs a hand-kept project with a settings check.
- **Comment policy** we'd actually enforce.
- **Which changes may merge on evidence alone**, and when to add the outer loop.
