# Playbook: starting a new project

**Status:** Draft. Stages 0–2 are discussed; stages 3+ will be refined after the verification discussion.

Move to the next stage when the exit check passes, not by calendar date. Expect each project to adapt the details; the order is what matters.

## Stage 0 · Choose the stack with enforcement in mind

- [ ] Prefer a language with a strong compiler (strict types, sum types, concurrency checking). It gives agents a stronger [layer 1](../guide/02-cant-be-written.md).
- [ ] If the language is weak here (Python, JavaScript), plan for strict type checking in CI from day one, and a stronger [foundation](../guide/04-foundation.md).
- [ ] Read the platform notes, e.g. [platforms/ios-swift.md](../platforms/ios-swift.md).

**Exit:** language, platform and build tool chosen.

## Stage 1 · Decide the starting boundaries

Write these down in a short file in the new repo, before writing feature code.

- [ ] **Modules** and the allowed dependency direction between them (see [templates/boundaries.yaml](../templates/boundaries.yaml))
- [ ] **Concurrency model:** what runs on the UI thread, what runs in the background, who owns shared state
- [ ] **Data ownership:** which module owns persistence and network; what the UI is allowed to touch
- [ ] **Lifecycle and side effects:** the one approved way to do subscriptions, timers, cancellation and background work
- [ ] **Lessons from previous projects** to adopt as starting rules: browse the [rules catalog](../rules/)

**Exit:** a boundaries file and a list of starting rules exist.

## Stage 2 · Encode it on day one

Do this *before* the first feature, because agents copy whatever exists first.

- [ ] Strictest compiler settings, warnings as errors
- [ ] Module structure matching the boundaries file
- [ ] Layer-2 command: escape-hatch bans, suppression ban, import/dependency check, settings check. One command, runnable locally.
- [ ] CI runs the build and the layer-2 command as **required checks** on a protected branch
- [ ] CODEOWNERS covering the [enforcement surface](../guide/04-foundation.md)
- [ ] Agent instructions with the escalation rule ([templates/AGENTS.md](../templates/AGENTS.md))
- [ ] Optional: agent hooks blocking edits to protected paths

**Exit test:** deliberately break each starting rule in a throwaway branch. Every violation must fail the build or CI with a message that names the fix. A rule that doesn't fail isn't enforced.

## Stage 3 · First feature, verified end to end

- [ ] Launch in a known state: fixture account, isolated storage, local or fake backend
- [ ] A minimal driver: launch, wait until ready, act, capture, clean up
- [ ] A feature-map entry for one real journey ([templates/feature-map.yaml](../templates/feature-map.yaml))
- [ ] An agent builds the feature and hands back evidence ([templates/evidence.md](../templates/evidence.md))

**Exit:** a fresh agent can build, verify and hand back evidence for a feature without your help.

## Stage 4 · Run the correction loop

- [ ] Every correction goes through [correction-loop](correction-loop.md)
- [ ] Review time is spent on evidence and intent, not repeated mistakes

**Exit:** the same correction stops recurring. Review findings trend toward intent questions.

## Stage 5+ · Deepen, then automate

- [ ] Property tests or formal models for the riskiest stateful flows
- [ ] Performance budgets
- [ ] Only then: the [outer loop](../guide/08-outer-loop.md)
