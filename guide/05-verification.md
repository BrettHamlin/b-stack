# 05 · Layer 3: Can't pass verification

**Status:** Partial draft. **Not yet discussed in depth.** This file records what we know so far; the verification discussion will refine it.

Layers 1 and 2 prove the code has the right *structure*. Layer 3 proves the **running product behaves correctly**. Lauren calls verification "the most important step," and her team's review now mostly looks at verification evidence rather than diffs.

## What verification needs from the architecture

These need to exist from the first commit, because they're painful to add later:

- **Stable, typed UI identifiers.** The driver taps elements by ID. Make the IDs compiler-checked (an enum or generated constants), not loose strings. See rule [typed-ui-identifiers](../rules/typed-ui-identifiers.md).
- **Launch in a known state.** A fixture or test mode with isolated storage, a seeded account, and a local or fake backend, so every run starts clean and repeatable.
- **Swappable seams** for time, network, storage and randomness, so tests and the driver can control them. These are the same seams that [explicit dependencies](../rules/explicit-dependencies.md) create.
- **Domain state as explicit types.** States and transitions that a test, a property generator or a formal model can mirror.

## Parts (to be refined)

| Part | What it is | Proves |
|---|---|---|
| **Feature map** | For each feature: what the user can do, how they reach it, what proves it worked | The shared vocabulary and the success conditions |
| **Driver** | One maintained command-line tool that launches the app, waits until it's ready, acts, observes, captures evidence and cleans up | The real app works for a mapped journey |
| **Evidence package** | Build identity, environment, actions, expected vs observed results, screenshots/recording/logs, saved data, gaps | A reviewable claim tied to a specific build |
| **Property-based tests** | Generated sequences of inputs and actions checked against invariants | Edge cases a scripted happy path misses |
| **Formal models** | TLA+ for interacting state machines (sync, retry, cancel); Lean for precise algorithm properties | Properties of the *model*, within stated bounds |
| **Performance budgets** | Fixed workloads, recorded distributions | Latency and resource use stay within budget |

Starting points: [templates/feature-map.yaml](../templates/feature-map.yaml), [templates/evidence.md](../templates/evidence.md).

## Rules already clear

- A screenshot proves what's visible, not that data persisted. Check durable effects through a fresh launch or the backend.
- A passing model run proves things about the model, not the app. Record its assumptions and how it corresponds to the code.
- Keep the failing baseline and the passing fix as evidence when it's practical.

## Open questions for the verification discussion

- How small can the first feature map be while still being useful?
- Driver design: build our own CLI around XCUITest, or adopt an existing harness?
- Where evidence is stored and how it's linked to PRs
- Which states in a typical app are worth a formal model, and which only need property tests
- How verification runs in CI vs locally (simulator cost, flakiness)
