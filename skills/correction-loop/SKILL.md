---
name: correction-loop
description: Turn a correction or repeated review comment into a tested, enforced rule instead of a one-off fix. Use when the user corrects you, or the same issue is flagged twice.
---

# Correction loop

A correction in chat fixes one instance. A rule fixes every future instance.

## 1. Fix the instance, then name the class

Fix what was asked. Then describe the *kind* of mistake ("feature code uses raw timers to paper over ordering"), not the single instance. If it's a one-off preference rather than a recurring failure, stop here.

## 2. Check the catalog

Search `rules/*/rule.toml` in b-stack. If a rule already covers it, the project isn't enforcing it: apply that rule and go to step 6.

## 3. Push it as high as it goes

Stop at the first that works:
1. **Impossible to write:** change types, module boundaries or the API (layer 1, enforced by the compiler)
2. **Blocked by a check:** a checker rule in protected CI (layer 2)
3. **Caught by verification:** a journey, property or model test (layer 3)
4. **Prose:** only if nothing above works; record why

## 4. Make sure a correct path exists

A ban without a replacement produces worse workarounds. If no supported way exists, propose one to the user before banning anything.

## 5. Write the rule with tests

Add `rules/<rule-id>/` following `rules/README.md`:
- `rule.toml`: problem, message (names the fix), escape hatches
- at least one **fail** case: code that must be rejected
- a **pass** case: the correct alternative, which must compile

## 6. Prove it fires

```sh
python3 scripts/test_rules.py --rule <rule-id>
```

Then run `python3 scripts/check_repo.py`. A rule that has never fired is unproven.

## 7. Existing violations

New violations fail immediately. Record existing ones in a baseline that may only shrink, then migrate them so agents stop copying them.

## 8. Report clusters

If several rules accumulate around one area, tell the user: the architecture there probably doesn't fit, and fixing the abstraction beats adding more rules.
