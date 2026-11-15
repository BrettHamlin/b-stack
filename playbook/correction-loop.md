# Playbook: the correction loop

**Status:** Draft. Discussed and agreed.

Run this whenever you correct an agent, or the same review comment comes up twice. It turns one-off corrections into permanent constraints.

## 1. Name the failure class

Describe the *kind* of mistake, not this one instance. Example: "feature code uses raw timers to paper over ordering problems," not "the timer on line 40 is wrong."

Is it really recurring, or a one-off preference? One-offs don't get rules.

## 2. Push it up the pyramid

Ask in order and stop at the first "yes":

1. **Can it be impossible to write?** Change the types, the module structure or the API. → [layer 1](../guide/02-cant-be-written.md)
2. **Can a check block it from merging?** → [layer 2](../guide/03-cant-be-merged.md)
3. **Can verification catch it?** → [layer 3](../guide/05-verification.md)
4. Only then **prose**, and record why it couldn't go higher. → [layer 4](../guide/06-prose.md)

## 3. Make sure a correct path exists

A ban without a replacement creates worse workarounds. If no supported way to do the right thing exists, build it first.

## 4. Prevent new cases, then clean up old ones

1. Turn on the rule with a **baseline** of existing violations. New ones fail; the count can only go down.
2. Migrate the existing violations so agents stop copying them.
3. Delete the baseline entries as they're fixed.

## 5. Prove the rule fires

Deliberately write the bad pattern. Confirm it fails with a message that names the fix. A rule that has never fired is unproven.

## 6. Record it

Add or update an entry in the [rules catalog](../rules/) so the next project starts with it.

## 7. Watch for clusters

If several rules accumulate around the same area, the problem is the architecture, not the individual mistakes. Lauren's example: a pile of timer workarounds came from a clash between an imperative framework and a declarative UI library. Fix the abstraction.
