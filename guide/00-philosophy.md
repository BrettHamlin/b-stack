# 00 · Philosophy

**Status:** Draft. Discussed and agreed.

## The goal

Build apps that AI agents can work on quickly **without** the quality dropping. Trust in agents doesn't come from the model being good. It comes from the environment: code, checks and verification that make the right change easy and the wrong change hard to land.

This guide started from Lauren Tan's talk *All Code Is Slop (Except Mine)* ([research](../research/lauren-tan-video/)). We kept her core ideas and reorganized them around one question: **how hard is each rule to get around?**

## Core beliefs

1. **Agents make the same mistakes over and over.** Human mistakes vary from person to person. The same model makes the same mistake in a thousand parallel runs. So a check that blocks one mistake pays off every time it fires, and correcting the agent in chat fixes only one of many repeats.

2. **Every agent session is a new hire on day one.** Agents don't remember corrections between sessions. Everything we used to do for onboarding (paved paths, obvious names, self-explanatory structure, one way to do each thing) is now needed permanently.

3. **The code is the agents' memory.** Agents copy whatever patterns they see. A workaround that's copied once looks like the convention and spreads. The **first** patterns in a new repo become the template for everything after, so the starting code and its enforcement matter more than they used to.

4. **Architecture first, enforced right away.** A rule needs a correct path to point to ("don't do X, use Y"), so the architecture comes first. But its enforcement has to exist from the first file, not get added after a cleanup.

5. **Push every rule as high up the pyramid as it can go.** Make it impossible to write, rather than catching it in review. See [01 · Pyramid](01-pyramid.md).

6. **When rules pile up in one place, the architecture is wrong.** A cluster of rules about the same problem means the abstraction underneath doesn't fit. Fix the design, not the symptoms.

7. **Checking is now cheap.** Property tests, formal models and full user-journey checks used to be too expensive to write. Agents make them affordable, so use them.

8. **Give agents a legitimate way to say "I'm blocked."** Agents work around rules mostly because they've been told to finish. If the only options are "comply" or "fail," they invent a third. A sanctioned escalation path is part of enforcement.

9. **Don't automate a bad loop.** Make one agent's write → verify → fix cycle reliable before adding triggers, schedules or fleets of agents.

## Which old human practices change

| Practice | Built for | With agents |
|---|---|---|
| Saving keystrokes (DRY, clever abstractions, metaprogramming) | Typing is slow | **Relax.** Prefer boring and explicit. Duplication still matters, but because copies spread, not because they cost typing. |
| Minimal testing | Tests were expensive to write | **Reverse it.** Verification is cheap now. |
| Comments as memory aids | Humans forget context | **Mostly drop them.** Comments go stale, can't be enforced, and let agents justify shortcuts. Keep only what code can't express. |
| Onboarding docs and paved paths | New hires | **Needed permanently.** Every session is a new hire. |
| Style guides and conventions | Humans absorb norms | **Turn them into checks.** Agents don't absorb anything. |
| Small PRs and code review for knowledge sharing | Reviewer attention, team learning | **Shift to evidence.** Humans review intent and proof, not every line. |
| Tolerating some mess and refactoring later | Mess spreads slowly | **Mess spreads fast.** Prevent it from day one. |

## What doesn't change

Humans still own **intent**: what the product should do, which trade-offs are acceptable, and whether the evidence shows the right thing. The pyramid exists so human attention goes to those questions and nothing else.
