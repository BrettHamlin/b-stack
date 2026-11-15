# 01 · The enforcement pyramid

**Status:** Draft. Discussed and agreed. Layer 3 will be refined after the verification discussion.

Lauren Tan's pyramid sorts layers by *kind of thing*: codebase, static analysis, verification, prose, human review. Ours sorts them by **how hard each layer is to get around**.

```
 ┌──────────────────────────────────────────────────────┐
 │ 1. CAN'T BE WRITTEN                                  │  strongest, cheapest per use
 │    design + compiler: the wrong thing won't compile  │
 ├──────────────────────────────────────────────────────┤
 │ 2. CAN'T BE MERGED                                   │
 │    structural checks in protected CI                 │
 ├──────────────────────────────────────────────────────┤
 │ 3. CAN'T PASS VERIFICATION                           │
 │    runtime, property, formal: behaviour is wrong     │
 ├──────────────────────────────────────────────────────┤
 │ 4. GUIDED                                            │
 │    prose: steers judgment, enforces nothing          │
 ├──────────────────────────────────────────────────────┤
 │ 5. JUDGED                                            │  weakest, most expensive
 │    human review of intent                            │
 └──────────────────────────────────────────────────────┘
   FOUNDATION: the enforcement itself is protected
   (CODEOWNERS, protected CI, config checks)
```

| Layer | Question it answers | Detail |
|---|---|---|
| 1. Can't be written | Is the wrong thing impossible to express? | [02](02-cant-be-written.md) |
| 2. Can't be merged | Does a check block it before `main`? | [03](03-cant-be-merged.md) |
| Foundation | Can anyone weaken the checks without a human noticing? | [04](04-foundation.md) |
| 3. Can't pass verification | Does the running product actually behave correctly? | [05](05-verification.md) |
| 4. Guided | What judgment can't be checked? | [06](06-prose.md) |
| 5. Judged | Is the intent right? | [07](07-review.md) |

## The one rule: push it up

When you correct an agent, or spot a recurring problem, ask in order:

1. **Can I make it impossible to write?** Change the types, the module structure or the API.
2. **If not, can a check block it from merging?** A structural rule in protected CI.
3. **If not, can verification catch it?** A journey test, property test or model.
4. **Only then** write prose about it.
5. **Only then** rely on a human to catch it.

Each answer becomes an entry in the [rules catalog](../rules/). The step-by-step version is in [playbook/correction-loop.md](../playbook/correction-loop.md).

## How it maps to Lauren's pyramid

| Hers | Ours |
|---|---|
| Codebase (APIs, architecture, refactoring) | Layer 1 |
| Static analysis: compilers and types | Layer 1. The type system is part of design, not a check run afterwards. |
| Static analysis: lints, tests, CI | Layer 2 |
| Verification (runtime, formal) | Layer 3 |
| Prose (rules, skills, AGENTS.md) | Layer 4 |
| Human review | Layer 5 |
| *(not in her pyramid)* | **Foundation:** protecting the enforcement itself |

## Properties of a healthy pyramid

- **Each layer covers the gaps of the one above.** Lint bans the compiler's escape hatches. Verification checks the behaviour lint can't see.
- **The lower layers shrink over time.** If prose or review keeps growing, rules aren't being pushed up.
- **Every layer has a sanctioned "I'm blocked" path.** Otherwise agents invent workarounds.
- **The weaker the language's compiler, the more the lower layers and the foundation matter.** In Rust or Swift 6 a lot fits in layer 1. In Python or JavaScript, "the compiler" is a type checker run in CI, which is really layer 2 strength.
- **Test every compiler claim against the real compiler.** For example, Swift module boundaries turned out to be weaker than expected; see [platforms/ios-swift.md](../platforms/ios-swift.md).
