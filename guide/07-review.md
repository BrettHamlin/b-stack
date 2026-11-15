# 07 · Layer 5: Judged (human review)

**Status:** Stub. Not yet discussed in depth.

Human attention is the scarcest resource, so the layers above exist to protect it. What's left for humans is **intent**: is this the right behaviour, and does the evidence actually show it?

## What we know so far

- **Review evidence, not diffs.** Recordings, screenshots, saved-data checks, statecharts, model results. Readable evidence matters more than readable code.
- **Always review changes to the enforcement surface.** Any PR touching the files listed in [04 · Foundation](04-foundation.md) gets a human, enforced by CODEOWNERS.
- **Look for workarounds that pass every check.** Hand-rolled locks to avoid actors, detached tasks to escape isolation, banned APIs re-created under a new name, tests that assert nothing. An LLM reviewer prompted with "did this change get around a constraint?" is a useful first pass.
- **Still read some code.** Framework and core API changes, critical invariants, unfamiliar algorithms. Mistakes there spread to every feature.
- **Every review finding should feed the [correction loop](../playbook/correction-loop.md).** If you had to say it once, ask whether a check could say it next time.

## Open questions

- What evidence format makes review fast
- Which kinds of change can merge on evidence alone, and when
