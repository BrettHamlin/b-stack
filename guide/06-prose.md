# 06 · Layer 4: Guided (prose)

**Status:** Stub. Not yet discussed in depth.

Prose (AGENTS.md, skills, rule files, docs) **steers judgment but enforces nothing**. It's where things go only after they've failed to fit layers 1–3.

## What we know so far

- **Keep it short.** Every line should be something that can't be checked automatically. When a prose rule *can* become a check, move it up and delete the prose.
- **The escalation rule belongs here.** "Never suppress or weaken a check; if blocked, stop and report." See [04 · Foundation](04-foundation.md).
- **Stop unrequested markdown.** Agents write notes, docs and comments that justify shortcuts or turn one small correction into a permanent hard rule. Prose that wasn't asked for shouldn't quietly become policy.
- **Comments are mostly a liability.** They go stale and can't be enforced. Lauren's team removed about 98%. Keep what code can't express: external contracts, legal text, non-obvious reasons that matter.
- **Prose is versioned and protected** like any other part of the [enforcement surface](04-foundation.md).

Template: [templates/AGENTS.md](../templates/AGENTS.md).

## Open questions

- A comment policy we'd actually enforce, and how
- Skills vs AGENTS.md: what goes where
- How to detect prose that should have become a check
