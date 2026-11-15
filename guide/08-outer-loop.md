# 08 · The outer loop (automation)

**Status:** Stub. Deliberately last; not yet discussed.

The "software factory" means triggers (a ticket, a release, an alert, a schedule) that start agents automatically. It **supplies work**; it doesn't make the work correct. Automating an unreliable loop just produces more unreliable output, faster.

## Prerequisites

Don't start until:
- [ ] Layers 1, 2 and the foundation are in place and protected
- [ ] At least one feature can be verified end to end with evidence
- [ ] A single agent reliably completes representative tasks: reproduce → fix → verify
- [ ] The correction loop is running, and review findings are turning into checks

## Ideas from Lauren's talk, to discuss later

- Release-triggered fuzzing: explore the actual packaged build, compare against the previous version, deduplicate findings, open a fix task per confirmed bug
- Separate deciding *whether* to start work from doing it
- Automatic merging only for well-understood kinds of change, once their checks have proven reliable
- Duplicate events, resource limits, retries and failure handling need explicit design
