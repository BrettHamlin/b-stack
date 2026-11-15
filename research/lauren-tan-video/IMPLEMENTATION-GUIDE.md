# Applying Lauren Tan's setup to our software

Source: [All Code Is Slop (Except Mine)](https://www.youtube.com/watch?v=O_zcc6Xl12g), full 17:31 video. Analysis prepared November 15, 2026. Capture timestamps identify a readable frame, not an exact slide boundary.

The transferable setup is an engineering environment that makes good implementations easy to produce and bad implementations difficult to land. It has a product framework, enforced architectural boundaries, automated checks, a runnable verification harness, a map of user journeys, selected formal models/proofs, reviewable evidence, and an outer loop that supplies work. Her main claim is that investment in the inner loop makes larger-scale automation practical.

## What the talk establishes

Lauren reports roughly six months of investment, 3,127 personal October PRs, and 10,926 team October PRs. Dune is their client framework, described as something like Next.js for Electron. She says their product code bans useEffect, puts features in conventional folders, enforces import boundaries, and drastically restricts comments. She describes runtime verification through a feature map and CLI, TLA+ modeling of cross-device notifications, Lean proofs for a virtualizer, and UI property-based testing with Bombadil.

She says review increasingly examines verification artifacts and that most routine product changes no longer require deep human review. She describes a release-triggered process that explores a build, finds bugs, opens fix PRs, and auto-merges. The displayed release report gives more implementation detail than the narration: packaged Linux artifacts, checksum validation, a previous-version baseline, a local backend, saved feature-gate values, deduplication, and classification of new versus existing issues.

The talk does **not** provide Dune source, a complete CI pipeline, their exact lint configurations, driver implementation, TLA+ specifications, Lean proofs, Bombadil properties, agent prompts, permission model, merge gates, compute bill, or production incident history. The public pstack repository supplies related workflows; installing it is not equivalent to reproducing the internal environment. Exact model choices and parallelism settings are not established by this talk.

The full slide analysis is in `ANALYSIS.md` and the interactive viewer. The raw automatic transcript is preserved separately; it repeatedly mistranscribes Grok Bot, poteto, TLA+, pstack, and other technical names. The analysis normalizes names using the slides and linked sources without rewriting the raw transcript.

## Reconstructing the operating system

There are three connected loops:

1. **Implementation loop:** understand a concrete behavior → use approved APIs → run fast checks → exercise the actual product → inspect evidence → repair → rerun affected verification.
2. **Environment improvement loop:** notice a recurring mistake → identify its cause → improve an API or enforce a rule → migrate old examples → make the next instance harder to create.
3. **Automation loop:** receive an event → determine actionable work → run the implementation loop → evaluate evidence and checks → merge/release according to the project's policy → observe results.

The first two create the reliability the third depends on. A scheduler that launches a coding agent only supplies work. It does not supply an oracle for correctness.

### 1. A small product foundation

Create a thin framework around the existing stack. Put the difficult, repetitive decisions in one maintained layer: data access, subscriptions, task cancellation, persistence, navigation, IPC/native bridges, background work, retry policy, and error handling. Product features should consume those APIs through a narrow interface.

For Electron, a corresponding layout could be:

```text
electron-renderer/
  features/<feature>/
  client/
  primitives/
electron-main/
  startup/
  notifications/
  update/
shared/
  contracts/
```

Use a dependency analyzer and AST-aware lint rules to forbid direct main↔renderer imports, including type imports if adopting her exact convention. Both sides can import shared contracts; a platform bridge performs the permitted IPC. Audit aliases, re-exports, dynamic imports, and generated entry points so the check covers the actual dependency graph.

For other platforms, preserve the architectural idea rather than Electron's names:

| Surface | Useful boundaries | Examples of constraints |
| --- | --- | --- |
| iOS / Swift | UI, domain, data, platform; main actor versus background work | Domain cannot import UI frameworks; UI does not own raw database connections; actor isolation and cancellation have explicit owners |
| Android / Kotlin | UI, domain, repositories, platform; lifecycle scopes | No blocking I/O on UI dispatcher; structured coroutine ownership; dependencies follow module rules |
| React Native | Feature UI, domain, data, native adapters | Native modules accessed through adapters; effects/subscriptions confined to approved lifecycle wrappers |
| Web | Feature UI, domain, transport, server-only code | Browser bundles cannot import server secrets; schemas validate boundaries; supported data-loading APIs |
| Desktop native / Tauri | UI, domain, privileged host services | Privileged actions behind explicit contracts; avoid bypasses from presentation code |
| Backend | API, domain, persistence, integrations, jobs | No cross-tenant queries without a tenant scope; bounded retries; transactional writes where required |
| CLI / library | Parsing, domain operations, I/O adapters | Explicit exit codes; side effects isolated; deterministic algorithm core |

These are proposed adaptations, not a list of technologies Lauren says her team uses. Real threading, actor, and lifecycle semantics require code-level design; an import rule alone cannot prove them.

Her useEffect example illustrates a general technique: restrict a subtle primitive where misuse is common, then supply an API that handles its lifecycle correctly. An indiscriminate ban without a usable replacement creates pressure for worse workarounds. Framework internals remain a higher-leverage review surface because their mistakes propagate through many features.

### 2. Turn corrections into durable controls

Classify the failure before choosing a control:

| Repeated problem | Appropriate durable response | Evidence it works |
| --- | --- | --- |
| Renderer imports privileged implementation | Dependency rule plus shared contracts | Invalid import rejected; intended IPC path still functions |
| Product code invents a timing workaround | Supported scheduling/lifecycle API and scoped AST rule | Original race reproduced; replacement fixes it under relevant ordering |
| Save appears successful but is lost after restart | Persistence journey and failure handling | Fresh process displays saved data; failed write never reports success |
| Retry duplicates a payment/message/job | Idempotent domain API, transaction design, concurrency test/model | Duplicate delivery cannot produce duplicate committed effect within stated assumptions |
| Agent copies deprecated API | Forbid new use, migrate examples, expose replacement | Repository usage converges and new violations fail CI |
| Unclear comment justifies unsafe cleanup | Make ownership explicit and verify release semantics | Resources are released exactly when their owner ends |

A good diagnostic names the forbidden behavior, the reason, the replacement, and where that replacement lives. For example: “Feature code cannot call setTimeout to coordinate view cleanup. Use the owned-task API, which cancels work when the feature unmounts. If ownership is wrong, fix it in the lifecycle layer.” This is a proposed diagnostic, not a verbatim Dune rule.

AST and dependency checks need to understand imports and aliases; a text search for `useEffect` is not equivalent to enforceable architecture. Checks should run locally in the normal agent loop and be required in CI. A required check needs to cover its own configuration, so an agent cannot satisfy it by weakening the rule. Preserve clear ownership of acceptance criteria and changes to the verification infrastructure.

Do not manufacture dozens of rules from personal style preferences. Each rule should eliminate a meaningful failure class and retain a sensible exception path. Useful rationale and interface documentation can remain even if we reduce redundant comments. Lauren's comment policy is a deliberate local choice, not a necessary condition for adopting the rest of the system.

### 3. Give every project a reliable way to run and be driven

The agent needs to start from a clean state, determine that the product is usable, perform real actions, observe results, and stop its own processes. This is the practical prerequisite for runtime verification.

A platform-specific driver can present a consistent command surface. Illustrative commands below are a proposed interface, not an installed tool:

```text
verify-app launch --isolated --fixture standard-account
verify-app doctor
verify-app snapshot
verify-app click --name Settings
verify-app capture --journey notification-preferences
verify-app cleanup
```

The launch result should identify the instance, build, device/profile, ports, data directory, and evidence directory. “Ready” means the mapped feature is usable: migrations finished, fixture loaded, authentication established, and required services available. A listening port alone does not establish readiness.

Reuse existing automation before building another system:

| Platform | Candidate driver | Capture and observations |
| --- | --- | --- |
| Web | Existing Playwright/Cypress harness, browser/CDP | Screenshot, video/trace, accessibility tree, console/network, persisted state |
| Electron | Electron-capable harness plus browser/CDP and host observations | Window actions, renderer traces, main-process logs, IPC and files |
| iOS | XCUITest / XCTest; compatible existing mobile harness | Simulator/device screenshot, action trace, app logs, persistent data, permissions |
| Android | Instrumentation / Espresso / UI Automator; compatible existing mobile harness | Emulator/device recording, logcat, accessibility hierarchy, persisted state |
| Native desktop | OS accessibility/UI automation and existing app tests | Window state, logs, files, process lifecycle |
| API / worker service | HTTP client plus integration environment | Response, durable side effects, queue/job history, timing, traces |
| CLI / TUI | Isolated PTY/expect-style harness | Terminal transcript, exit status, generated files, actual side effects |

Simulator evidence covers the simulator. Real-device behavior, push delivery, OS background suspension, power use, and distribution need appropriate device or release validation. CDP does not automatically cover native mobile interfaces.

Use stable accessibility labels or identifiers. These improve both product accessibility and automation. Keep each run's data, profile, and evidence separate; agents should not accidentally drive the same app instance concurrently. Cleanup removes processes and scratch state owned by that run while retaining proof.

### 4. Maintain a feature map with explicit success conditions

A feature map is a verification specification organized around what the user can do. It is more useful than a list of screens because it includes how to reach them and what observable result means success.

For example, a notification-preference feature record could contain:

```yaml
id: notification-preferences
entry_points:
  - Settings > Notifications
preconditions:
  - signed in as fixture account A
  - second client signed in as the same account
actions:
  - disable a notification category
  - leave Settings and reopen it
  - restart the first client
  - reconnect the second client
expected:
  - category stays disabled after restart
  - second client converges to the agreed preference
  - unrelated categories and other accounts are unchanged
evidence:
  - action trace and relevant screenshots
  - persisted preference and sync observations
failure_cases:
  - write failure
  - offline edit
  - concurrent edit on second client
```

This is our example, not her internal feature file. Conflict resolution, permission behavior, and convergence rules must be decided by the product owner. An agent should not invent them from “make notifications work.” List each meaningful entry point and platform difference. A successful journey through one route does not prove another route works.

Start with three to five important journeys. The public `/create-verification-skill` source specifically recommends a feature index and per-feature files, launch/doctor/drive/evidence/cleanup instructions, and an end-to-end execution of the generated skill before handing it over. It says evidence should include actions, resulting state, and side effects, and survive cleanup. This is corroborating public source material, not extra configuration demonstrated in the video.

### 5. Combine verification methods by failure class

**Runtime journeys** answer whether the built product behaves correctly in exercised scenarios. A screenshot of Settings cannot prove a preference survived restart. Capture the transition, then observe durable state through a fresh process or appropriate backend observation.

**Property-based testing** generates inputs and sequences under constraints. For a chat product, properties might require no duplicate message IDs, no crash on valid navigation, no cross-account message visibility, and recovery after a cancelled operation. Preserve random seed, generator version, build, action trace, and minimized failure where supported. A discovered sequence should become a replayable regression. Bombadil is the tool named in the talk; native apps need a compatible harness and generator.

**TLA+ model checking** suits interacting state machines: retry/cancel, device sync, notification acknowledgement, job leases, offline edits. Define finite abstractions and invariants; run the checker; retain the specification, configuration, bounds, state counts, assumptions, and shortest counterexample when available. A passing bounded run establishes properties of that model/configuration, not every possible state of production software.

**Lean proofs** suit precise algorithmic properties: index/range calculations, ordering, bounds, or scroll-anchor arithmetic. State the theorem and assumptions, identify the implementation correspondence, and avoid unproved placeholders in claimed proofs. A theorem about simplified arithmetic does not by itself establish absence of browser rendering jitter or scheduling errors. Lauren says their formal work is still experimental; her actual theorems are not shown.

**Benchmarks and release observation** cover what logic checks miss: latency, memory, battery/CPU, startup assets, package size, crashes, and behavior under load. Keep workload and hardware/device definitions stable and record distributions. Her chart's mixed results are a useful reminder to examine all budgets.

### 6. Example: build a cancellable offline send feature across platforms

Begin with the user behavior: compose while offline, enqueue once, reconnect, retry safely, and either deliver or show an honest recoverable failure. Specify what cancellation means before and after server acceptance, what happens on restart, and how multiple devices reconcile status.

Use a domain operation for enqueue/send with a stable idempotency key; platform adapters own networking and storage; UI subscribes through approved lifecycle APIs. Do not patch UI timing with arbitrary delays. Make invalid transitions explicit in types where feasible.

Write the feature map for compose, retry, cancel, restart, and second-device display. Run it through the web/desktop/mobile drivers with the same domain expectations and platform-specific permission/lifecycle cases.

Candidate model states include Draft, Queued, Sending, Acknowledged, CancelRequested, Cancelled, and Failed. These names alone are **not a model**. Define transitions and races, including acceptance arriving after local cancellation. Candidate invariants are “one committed server message per idempotency key” and “UI never claims cancellation prevented delivery when the server already accepted.” A liveness property needs assumptions about eventual connectivity and server availability.

Generate sequences of reconnects, duplicate responses, restarts, cancellation, and device switching. Check durable side effects alongside UI state. Review the model's assumptions, replay any counterexample, and check that the runtime implementation agrees. The deliverable is a working change plus a reproducible verification package.

### 7. Make evidence portable and reviewable

Every evidence package should identify:

```text
commit / build / package checksum
platform / OS / device or simulator / profile
fixture and relevant configuration / feature gates
claim being checked and feature-map revision
commands or action trace
expected and observed outcome
screenshots / recording / logs / persisted effects
test or model configuration and results
limitations and uncovered surfaces
```

This binds the claim to what was actually executed. For formal work, keep the checked model or proof, not merely a diagram labeled “verified.” For a runtime bug, keep the failing baseline and passing fix when feasible. A different model reviewing the same prose is useful judgment, but does not replace an executable behavioral check.

### 8. Add the outer loop after the inner loop works

Her release example can be adapted as:

```text
release artifact available
  → verify provenance and capture configuration
  → create isolated verification environment
  → explore mapped and generated user journeys
  → reproduce findings against current and previous builds
  → deduplicate and classify new vs existing issues
  → create a bounded fix task per confirmed issue
  → rerun fast checks, affected journeys, and relevant models
  → apply the project's merge/release policy
  → observe shipped behavior
```

The report on her slide checks package SHA-256s, runs a local backend, records copied production gate values, and separates regressions from old issues. Those details matter: discovering an old issue in a new build does not establish a new regression, and testing a different feature-gate configuration may exercise a different product.

For our implementation, give repeated events stable identities so they do not create duplicate work; preserve baseline/build identity; isolate agent branches and runtime instances; bound resources and retries; and retain a clear failure outcome. These are design recommendations inferred from the workflow, not controls explicitly shown in the talk.

Introduce automatic merge for a well-understood class of changes only after its checks and evidence prove reliable. Framework, verification infrastructure, data migration, authentication, and novel product semantics need policies appropriate to their impact. The video does not establish that her team automatically merges every category of change.

Mobile releases need an additional distribution stage: signed builds, store or internal-channel delivery, phased rollout where available, and observation of adoption/crash behavior. Desktop needs installers and update-path checks. A merged source change is not equivalent to a user running a healthy new version.

## Adoption sequence and completion criteria

1. **Baseline:** a fresh checkout starts; one real feature can be exercised; existing checks and current defects are recorded.
2. **Paved path:** the highest-frequency architectural mistake has a supported replacement and a required check; old examples are migrated.
3. **Runtime verification:** a maintained driver and three to five feature maps can produce evidence from isolated runs; cleanup preserves that evidence.
4. **Deeper coverage:** one costly stateful failure class has an executable model or generated sequence test; counterexamples can be reproduced; performance budgets exist.
5. **Evidence-based review:** changes carry build-linked results and explicit gaps; failures produce root-cause improvements instead of accumulated prose.
6. **Scoped automation:** one trigger can run the proven loop on a representative task; duplicate events, failure, resource usage, and handoff are handled.

Use observed readiness, not a promised calendar deadline, to move between these stages. Useful measures include time to verified completion, recurring review findings, escaped defects, forward-fix/rework, incident impact, latency/resource budgets, flaky checks, autonomous completion rate, and compute cost per accepted result. PR count and reverted-commit percentage remain supporting measures.

## Sources and confidence

- Primary: full YouTube transcript and video frames, with all substantive slides, builds, and the short UI demo inspected.
- Related public source: [pstack](https://github.com/cursor/plugins/tree/main/pstack).
- Read in addition to the video: [create-verification-skill](https://github.com/cursor/plugins/blob/main/pstack/skills/create-verification-skill/SKILL.md). The live repository can evolve independently of the talk.
- Referenced on slides: [create-formal-verification-skill](https://github.com/cursor/plugins/tree/main/pstack/skills/create-formal-verification-skill), [statechart](https://github.com/cursor/plugins/tree/main/pstack/skills/statechart), [no-comments](https://github.com/cursor/plugins/tree/main/pstack/skills/no-comments), [Bombadil](https://github.com/antithesishq/bombadil), [Grok Bot](https://x.ai/bot).

Observed slide text and reported experience are distinguished in the slide notes. Proposed platform choices, control designs, schemas, commands, and adoption criteria in this guide are our engineering translation. None of the private internal tools, CI settings, proof results, or productivity claims has been independently reproduced in this analysis.
