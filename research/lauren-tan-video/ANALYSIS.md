# Full-video analysis: All Code Is Slop (Except Mine)

Lauren Tan (poteto), AI Engineer Code Summit. Source: https://www.youtube.com/watch?v=O_zcc6Xl12g

Reviewed the complete 135-segment automatic transcript, 105 frames sampled across the full 17:31 video, and 71 detected visual transitions. Selected 42 readable captures covering the substantive slides and significant builds. Repeated pyramid highlights and UI-demo frames are grouped where they communicate the same point. Intro/outro logos and camera cuts add no setup details. Capture times below are reading positions, not exact slide-start timestamps. The downloaded MP4 is a video-only stream; the speech source used here is the complete automatic transcript, with technical names checked against slide text.

The core mechanism is a reinforcing loop: the codebase teaches agents patterns; framework APIs and machine checks constrain new work; runtime and formal verification provide feedback; human review focuses on evidence and unresolved judgment; repeated mistakes improve the environment. External triggers scale that established loop.

The talk gives enough detail to reconstruct the architecture of the process, but does not expose the complete internal configuration. Distinguish observed slide content, Lauren's reported experience, and our proposed application. In particular, model/proof validity remains scoped to its assumptions and connection to implementation.

Related source: https://github.com/cursor/plugins/tree/main/pstack

Implementation details and platform adaptations: [IMPLEMENTATION-GUIDE.md](IMPLEMENTATION-GUIDE.md).

## 01. Title — 0:25

[Video at capture](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=25s) · [Full-resolution capture](/Volumes/MicroBay/Downloads/video-research/O_zcc6Xl12g/slides/01-0025.jpg)

**Observed / reported:** Title identifies poteto, also Lauren Tan, working on Grok Bot. The title's 'except mine' joke sets up skepticism about how we judge other people's code.

**How it works:** She proposes earning trust through the engineering environment. Branding and agent preference do not establish quality.

**Application and limits:** Judge our generated changes by observable behavior, constraints, and maintenance cost.

## 02. Our craft and their slop — 0:36

[Video at capture](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=36s) · [Full-resolution capture](/Volumes/MicroBay/Downloads/video-research/O_zcc6Xl12g/slides/02-0036.jpg)

**Observed / reported:** 'Our blessed craft / their barbarous slop' labels equivalent agents, prompting, iteration, and 4,000-line PRs differently.

**How it works:** This exposes inconsistent standards. A familiar author or preferred model can make the same engineering practice seem acceptable.

**Application and limits:** Use the same acceptance criteria for human and agent changes. A large PR needs evidence regardless of author.

## 03. Personal PR volume — 0:45

[Video at capture](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=45s) · [Full-resolution capture](/Volumes/MicroBay/Downloads/video-research/O_zcc6Xl12g/slides/03-0045.jpg)

**Observed / reported:** Her personal chart shows March–October PR counts: 68, 254, 352, 685, 1,113, 2,401, 2,932, 3,127; total 10,932.

**How it works:** She attributes scaling to roughly six months improving the environment. The count is an output measure; the chart does not reveal PR size, task value, or cost.

**Application and limits:** Treat this as motivation for reducing repeated supervision. Track useful completed work and escaped defects alongside throughput.

## 04. Quality and quantity — 1:00

[Video at capture](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=60s) · [Full-resolution capture](/Volumes/MicroBay/Downloads/video-research/O_zcc6Xl12g/slides/04-0060.jpg)

**Observed / reported:** 'Quality & quantity' and 'everyone can be a coding machine.' Her thesis is increasing output while maintaining or improving quality.

**How it works:** Agents lower the cost of producing code; engineering effort shifts toward making that output reliable.

**Application and limits:** Define what quality means for each product before increasing autonomous work: correctness, responsiveness, accessibility, recovery, and operability.

## 05. Trust enables scale — 1:25

[Video at capture](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=85s) · [Full-resolution capture](/Volumes/MicroBay/Downloads/video-research/O_zcc6Xl12g/slides/05-0085.jpg)

**Observed / reported:** A conceptual curve plots trust against the number of agents, from one through thousands. It is an illustration, without measured trust units.

**How it works:** More parallel work is manageable only when each change requires less scarce human attention.

**Application and limits:** Increase concurrency after measuring reliable unattended completion. Do not interpret the curve as evidence that running more agents creates trust.

## 06. Low trust loop — 1:35

[Video at capture](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=95s) · [Full-resolution capture](/Volumes/MicroBay/Downloads/video-research/O_zcc6Xl12g/slides/06-0095.jpg)

**Observed / reported:** The low-trust loop is 'agent writes slop code → human verifies it → issues found.' The human remains the bottleneck.

**How it works:** Repeated verbal corrections solve individual instances while leaving the next instance equally likely.

**Application and limits:** Record recurring review findings and convert suitable ones into APIs, type constraints, lint rules, or behavioral tests.

## 07. High trust loop — 1:50

[Video at capture](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=110s) · [Full-resolution capture](/Volumes/MicroBay/Downloads/video-research/O_zcc6Xl12g/slides/07-0110.jpg)

**Observed / reported:** The high-trust build adds 'agent writes good code → agent verifies it → issues found.' It still contains feedback and failure detection.

**How it works:** Verification becomes part of the agent's normal task, with tools capable of revealing mistakes before handoff.

**Application and limits:** Require the agent to run the relevant checks and exercise the real user journey, then deliver the evidence with the change.

## 08. The poteto pyramid — 2:05

[Video at capture](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=125s) · [Full-resolution capture](/Volumes/MicroBay/Downloads/video-research/O_zcc6Xl12g/slides/08-0125.jpg)

**Observed / reported:** The inverted poteto pyramid lists codebase; static analysis; verification; prose; human review. A downward arrow is labeled cost. The slide groups tests and CI under 'static analysis,' although many tests execute code.

**How it works:** Spend heavily on reusable constraints and preserve expensive judgment for what those layers cannot settle. She highlights each layer in successive builds.

**Application and limits:** Prioritize clear APIs and architecture, machine-enforced checks, runtime/formal verification, concise judgment guidance, then targeted human review. The drawing is a prioritization model, not quantified cost accounting.

## 09. Code is memory — 3:05

[Video at capture](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=185s) · [Full-resolution capture](/Volumes/MicroBay/Downloads/video-research/O_zcc6Xl12g/slides/09-0185.jpg)

**Observed / reported:** 'Code is memory' overlays the pyramid. She says the codebase is one of an agent's largest inputs.

**How it works:** Repository patterns teach future implementations. An enforced improvement persists across tasks more reliably than an isolated correction in chat.

**Application and limits:** Replace deprecated examples and make the preferred implementation easy to discover. Repository cleanup improves the context supplied to the next agent.

## 10. Codebase as a garden — 3:35

[Video at capture](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=215s) · [Full-resolution capture](/Volumes/MicroBay/Downloads/video-research/O_zcc6Xl12g/slides/10-0215.jpg)

**Observed / reported:** A building covered in vegetation illustrates code arriving as a continuous, almost organic stream.

**How it works:** The building's structure shapes where growth can occur. Architecture plays that role for rapidly generated code.

**Application and limits:** Create explicit boundaries and reusable primitives before scaling generation. Folder naming alone is insufficient without checks.

## 11. Organic architecture — 4:05

[Video at capture](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=245s) · [Full-resolution capture](/Volumes/MicroBay/Downloads/video-research/O_zcc6Xl12g/slides/11-0245.jpg)

**Observed / reported:** The same building gains the label 'Organic Architecture.' She describes constraints as foundations around which new code grows.

**How it works:** Architecture is maintained continuously as patterns appear, rather than treated as a one-time diagram.

**Application and limits:** Use recurring agent mistakes as feedback about the shape of our abstractions and module boundaries.

## 12. Copying workarounds — 4:30

[Video at capture](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=270s) · [Full-resolution capture](/Volumes/MicroBay/Downloads/video-research/O_zcc6Xl12g/slides/12-0270.jpg)

**Observed / reported:** 'Each copy makes the next copy more likely' shows one workaround propagating through connected weeds into 'the pattern.'

**How it works:** Agents may infer that repeated code is the accepted local convention. Duplication gives a bad technique apparent legitimacy.

**Application and limits:** Prevent new instances first, then migrate existing ones so agents cannot keep learning from them. Link the replacement API in the diagnostic.

## 13. Read the code sometimes — 4:55

[Video at capture](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=295s) · [Full-resolution capture](/Volumes/MicroBay/Downloads/video-research/O_zcc6Xl12g/slides/13-0295.jpg)

**Observed / reported:** 'Yes, you should read the code sometimes' appears beside a human asking the agent to walk through it.

**How it works:** The talk retains an explicit role for understanding implementation, despite later claims about reduced deep review of routine product code.

**Application and limits:** Read framework changes, critical invariants, and unfamiliar algorithms. Use walkthroughs to expose assumptions, then encode what can be checked.

## 14. Dune framework — 5:10

[Video at capture](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=310s) · [Full-resolution capture](/Volumes/MicroBay/Downloads/video-research/O_zcc6Xl12g/slides/14-0310.jpg)

**Observed / reported:** Dune combines an app framework for navigation, rendering, and IPC with one folder per feature, strict import bans, and no comments in code. She describes it as roughly Next.js for Electron.

**How it works:** A narrow paved path packages expertise into framework behavior and lint constraints. Product work uses that path repeatedly.

**Application and limits:** Build a thin product foundation around our chosen platform. Dune's internal implementation is not supplied by this talk; pstack is a separate public skill collection.

## 15. Nuance and API design — 5:45

[Video at capture](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=345s) · [Full-resolution capture](/Volumes/MicroBay/Downloads/video-research/O_zcc6Xl12g/slides/15-0345.jpg)

**Observed / reported:** 'Nuance tends to lead to slop — just design better APIs.' She says useEffect is banned in product code and allowed only in selected Dune internals.

**How it works:** Move difficult lifecycle decisions into a small framework layer instead of expecting every agent to use a subtle primitive correctly.

**Application and limits:** Provide approved APIs for subscriptions, data loading, timers, and cleanup before restricting direct primitives. Scope restrictions to the layer where an alternative exists.

## 16. Directory structure as context — 6:35

[Video at capture](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=395s) · [Full-resolution capture](/Volumes/MicroBay/Downloads/video-research/O_zcc6Xl12g/slides/16-0395.jpg)

**Observed / reported:** electron-renderer contains features, client, primitives; electron-main contains startup, notifications, update. Direct imports are crossed out with 'not even types'; both depend on shared types in shared/. A side-project file src/sim/tick.hot.ts signals 'runs every tick' and 'no allocations.'

**How it works:** Names convey execution context, and dependency analysis/linting enforces it. Shared contracts avoid importing implementation across process boundaries.

**Application and limits:** Use equivalent UI/domain/platform boundaries on mobile and desktop. For Electron, preserve typed IPC through an appropriate bridge. Do not interpret the import ban as a ban on legitimate process communication.

## 17. Unsolicited markdown — 7:05

[Video at capture](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=425s) · [Full-resolution capture](/Volumes/MicroBay/Downloads/video-research/O_zcc6Xl12g/slides/17-0425.jpg)

**Observed / reported:** 'Stop agents from writing unsolicited markdown.' The illustration says 'Source?' and 'I made it up.' She describes agents turning corrections into excessive hard rules or documenting excuses.

**How it works:** Unreviewed prose can create fictional requirements and rationalize architectural shortcuts.

**Application and limits:** Keep maintained specifications and feature maps with owners; prevent incidental task notes from silently becoming policy. This requested analysis is intentional documentation, not the behavior she criticizes.

## 18. Quick fixes and timers — 7:40

[Video at capture](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=460s) · [Full-resolution capture](/Volumes/MicroBay/Downloads/video-research/O_zcc6Xl12g/slides/18-0460.jpg)

**Observed / reported:** The timer example progresses Sep 9 → Oct 3 → Oct 17: setTimeout(() => release(id), 0), justified as fixing flicker, is copied into a shared module and becomes '183 timers.'

**How it works:** She connects timer proliferation to a mismatch between VS Code's imperative architecture and React's declarative model, plus allocation/GC overhead. A zero-delay timer postpones work; it does not establish correct ownership or ordering.

**Application and limits:** Repair lifecycle, cancellation, and resource ownership. Ban unsupported scheduling shortcuts in product layers and provide a supported primitive. The slide's 'it would be a larger change' excuse is not a correctness argument.

## 19. Comments are liabilities — 8:30

[Video at capture](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=510s) · [Full-resolution capture](/Volumes/MicroBay/Downloads/video-research/O_zcc6Xl12g/slides/19-0510.jpg)

**Observed / reported:** 'Comments are liabilities' shows 65,824 on July 31 and 1,227 'today,' referencing /no-comments. She says they banned roughly 99% because comments stale and cannot enforce behavior.

**How it works:** A comment can preserve a plausible explanation while the implementation remains wrong. Fewer comments is her team's policy, not an experimentally established cause of fewer bugs.

**Application and limits:** Prefer explicit APIs and executable rules. Preserve necessary rationale, external contracts, legal text, and assumptions that cannot be expressed usefully in code; choose our policy deliberately.

## 20. Corrections become checks — 9:20

[Video at capture](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=560s) · [Full-resolution capture](/Volumes/MicroBay/Downloads/video-research/O_zcc6Xl12g/slides/20-0560.jpg)

**Observed / reported:** 'Whenever you correct your agent' shows an increasing staircase labeled 7, 17, 38, 90, 139, 149, 157, 167. The caption says 'lint against it or categorically eliminate the problem.' The y-axis does not specify a unit.

**How it works:** Corrections accumulate into durable constraints instead of repeated supervision. She explicitly recommends better API design or architecture when a lint is not enough.

**Application and limits:** For each repeated issue, ask whether it is syntactically detectable, expressible in types, behaviorally testable, or requires an architectural change. Avoid inventing a rule for a one-off preference.

## 21. Verification matters — 9:50

[Video at capture](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=590s) · [Full-resolution capture](/Volumes/MicroBay/Downloads/video-research/O_zcc6Xl12g/slides/21-0590.jpg)

**Observed / reported:** 'Verification is the most important step' overlays the pyramid. She says review now focuses on videos, screenshots, diagrams, and formal verification.

**How it works:** A verification artifact lets reviewers inspect a claim about behavior without deriving the entire behavior from a diff.

**Application and limits:** Attach relevant evidence to the exact build or commit. A screenshot is evidence of visible state; persistence, side effects, and timing need additional observations.

## 22. Runtime feature map — 10:20

[Video at capture](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=620s) · [Full-resolution capture](/Volumes/MicroBay/Downloads/video-research/O_zcc6Xl12g/slides/22-0620.jpg)

**Observed / reported:** The feature map has three explicit columns: what features exist, how users reach it, what proves it works. The slide references /create-verification-skill.

**How it works:** It gives users and agents a shared vocabulary and tells the agent both how to exercise a feature and how to recognize success.

**Application and limits:** Map the first few important journeys with prerequisites, visible entry points, actions, expected state, side effects, and evidence. Keep the map synchronized with the product.

## 23. Feature map and CLI — 10:45

[Video at capture](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=645s) · [Full-resolution capture](/Volumes/MicroBay/Downloads/video-research/O_zcc6Xl12g/slides/23-0645.jpg)

**Observed / reported:** A CLI is added: app aria-click --accessible-name "Settings"; app snapshot; app screenshot proof.png. Labels say 'drive the real app' and 'agent checks its own work.'

**How it works:** Reusable, testable commands replace freshly improvised automation scripts and reduce token use. Stable accessibility names form part of the control surface.

**Application and limits:** Expose launch, readiness, interaction, snapshots, screenshots/recording, logs, and cleanup through one maintained driver. These are slide examples; no installed executable named app is established.

## 24. TLA+ and Lean — 11:10

[Video at capture](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=670s) · [Full-resolution capture](/Volumes/MicroBay/Downloads/video-research/O_zcc6Xl12g/slides/24-0670.jpg)

**Observed / reported:** TLA+ is presented for modeling state machines and checking rules; Lean for proofs about algorithms. She cites notification flows across devices and a custom virtualizer's flicker/jitter behavior, and calls the approach promising but experimental.

**How it works:** Model checking explores reachable behavior in a specified model; proof checking validates a formal claim under assumptions. They target different failure classes.

**Application and limits:** Model cancellation, retries, sync, and notification acknowledgement; prove selected indexing or layout algorithms when worthwhile. Track how the model/proof corresponds to actual code. The talk does not supply the models, proofs, bounds, or implementation-linkage details.

## 25. UI property based testing — 11:40

[Video at capture](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=700s) · [Full-resolution capture](/Volumes/MicroBay/Downloads/video-research/O_zcc6Xl12g/slides/25-0700.jpg)

**Observed / reported:** An embedded video demonstrates UI property-based testing with github.com/antithesishq/bombadil. It opens menus, settings, bot creation, and other states while entering unusual strings.

**How it works:** Generate many action/input sequences and check invariants, reaching combinations that a scripted happy path misses. She reports finding UI bugs; the clip does not reveal its property definitions or seeds.

**Application and limits:** Define invariants such as no crash, no cross-account state, recoverable navigation, and no duplicate send. Save seed, action trace, build, and failure artifact so findings become reproducible regressions. Native UI needs a compatible driver rather than assuming this browser-oriented library covers every platform.

## 26. Subtle bugs and manual verification — 11:55

[Video at capture](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=715s) · [Full-resolution capture](/Volumes/MicroBay/Downloads/video-research/O_zcc6Xl12g/slides/26-0715.jpg)

**Observed / reported:** A May 15, 2026 Cindy Sridharan post says subtle bugs in AI-generated PRs required several additional days and substantial manual verification.

**How it works:** Code generation speed can hide downstream repair work. Reviewing only initial output time understates total cost.

**Application and limits:** Measure time to verified completion and follow-up fixes, not just initial PR creation.

## 27. Verification token spend — 12:10

[Video at capture](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=730s) · [Full-resolution capture](/Volumes/MicroBay/Downloads/video-research/O_zcc6Xl12g/slides/27-0730.jpg)

**Observed / reported:** A Nov 5, 2026 follow-up says 70% of daily token spend verifies patches and about 20–30% creates them. Lauren says most of her own usage similarly goes to verification.

**How it works:** Lower-cost generation makes extensive checking economical. The quoted percentage is one practitioner's reported allocation, not a controlled optimum.

**Application and limits:** Budget verification explicitly and measure value per check. Allocate depth according to risk rather than imposing a universal 70% quota.

## 28. Testing across the lifecycle — 12:35

[Video at capture](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=755s) · [Full-resolution capture](/Volumes/MicroBay/Downloads/video-research/O_zcc6Xl12g/slides/28-0755.jpg)

**Observed / reported:** A lifecycle chart spans pre-production, deploy, release, post-release: unit/functional/component/fuzz/property/formal/static/mutation/coverage/benchmark/contract/lint/acceptance/regression/smoke/usability/UI/penetration/threat/performance work; integration/tap-compare/load/shadowing/config/soak; canarying/monitoring/traffic-shaping/feature flags/exception tracking; teeing/profiling/logs/chaos/monitoring/A-B/tracing/dynamic exploration/real-user monitoring/auditing/on-call.

**How it works:** Verification continues after code tests pass and after deployment. She argues agents reduce the cost of applying established engineering methods.

**Application and limits:** Choose coverage by failure mode and lifecycle stage. The chart is a menu of techniques, not proof her team runs every technique for every PR.

## 29. Statechart — 13:05

[Video at capture](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=785s) · [Full-resolution capture](/Volumes/MicroBay/Downloads/video-research/O_zcc6Xl12g/slides/29-0785.jpg)

**Observed / reported:** /statechart links to pstack and shows a large user-flow diagram with highlighted problem paths.

**How it works:** A user-oriented state machine makes requirements and counterexample paths reviewable alongside runtime video and screenshots.

**Application and limits:** Review the agreed states and invariants before relying on an agent's implementation. A Mermaid diagram by itself does not establish that a model checker ran or that implementation conforms.

## 30. Results transition — 13:25

[Video at capture](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=805s) · [Full-resolution capture](/Volumes/MicroBay/Downloads/video-research/O_zcc6Xl12g/slides/30-0805.jpg)

**Observed / reported:** 'Ok so what' transitions from methods to results.

**How it works:** The next charts are evidence she offers for the approach. They are a team's observational results, without a controlled comparison.

**Application and limits:** Assess the complete group of metrics rather than treating PR volume as sufficient evidence.

## 31. Team PR volume — 13:40

[Video at capture](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=820s) · [Full-resolution capture](/Volumes/MicroBay/Downloads/video-research/O_zcc6Xl12g/slides/31-0820.jpg)

**Observed / reported:** Team merged PRs June–October: 809, 1,984, 4,203, 5,648, 10,926; total 23,570. The spoken '11,000' is rounded.

**How it works:** A rising number of contributors and changes accompanies the tooling investment. The chart does not isolate effects of staffing, PR sizing, model changes, or task mix.

**Application and limits:** Track throughput, change size, rework, quality, compute cost, and delivered outcomes together. Do not make raw PR count a target.

## 32. Desktop releases — 13:50

[Video at capture](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=830s) · [Full-resolution capture](/Volumes/MicroBay/Downloads/video-research/O_zcc6Xl12g/slides/32-0830.jpg)

**Observed / reported:** Desktop releases: August since launch 7, September 19, October 15; total 41. Median time between releases: 44, 25, 28 hours.

**How it works:** She describes this as roughly daily stable releases. A 28-hour median interval is not equivalent to releasing on every calendar day.

**Application and limits:** Distinguish merge, deploy, staged rollout, stable release, and actual adoption. Mobile store review and binary distribution impose different release constraints.

## 33. Contributor distribution — 14:00

[Video at capture](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=840s) · [Full-resolution capture](/Volumes/MicroBay/Downloads/video-research/O_zcc6Xl12g/slides/33-0840.jpg)

**Observed / reported:** Contributors June–October: 15, 48, 95, 163, 227. October bins: 49 with one PR, 78 with 2–9, 77 with 10–99, 22 with 100–999, one with 1,000+.

**How it works:** The environment supports both core contributors and low-context drive-by work. Growth in people also contributes to growth in total PRs.

**Application and limits:** Test whether a fresh contributor or agent can launch, find a feature, make a constrained change, and verify it without tribal knowledge.

## 34. Revert rate — 14:20

[Video at capture](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=860s) · [Full-resolution capture](/Volumes/MicroBay/Downloads/video-research/O_zcc6Xl12g/slides/34-0860.jpg)

**Observed / reported:** Revert rate is labeled '% of commits reverted': June 0.98%, July 0.61%, August 0.47%, September 0.48%, October 0.47%.

**How it works:** The relative revert measure falls while volume grows. It excludes defects corrected forward, undetected problems, and other outcomes unless they lead to counted reverts.

**Application and limits:** Preserve the denominator. Pair it with incidents, escaped defects, forward-fix/rework, customer impact, and recovery time. Avoid calling 0.47% the overall bug rate.

## 35. Performance measurements — 14:50

[Video at capture](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=890s) · [Full-resolution capture](/Volumes/MicroBay/Downloads/video-research/O_zcc6Xl12g/slides/35-0890.jpg)

**Observed / reported:** May→now: cold launch 2,304→1,395ms; relaunch 1,348→829ms; first paint 2,268→1,379ms; short-chat median typing 3.8→2.8ms; long-chat median 8.4→2.9ms and p90 9.7→3.4ms; settings 112→92ms; long-chat cold open 153→165ms, warm 138→86ms; switch to short chat 88→49ms, back to long 105→63ms; resize 3.0→6.9ms; idle memory 488→545MiB; idle CPU 0.40→0.80%; startup JS+CSS 2.0→7.7MB.

**How it works:** Most shown interaction latencies improve, but five measurements regress: cold long-chat open, resize, memory, idle CPU, and startup assets. Hardware, workload, repetitions, and benchmark method are not given.

**Application and limits:** Keep performance budgets across responsiveness, resource use, startup, and package size. The slide supports mixed improvement, not universal improvement. Rust is mentioned only as a possible rewrite idea.

## 36. Foundations revisited — 15:20

[Video at capture](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=920s) · [Full-resolution capture](/Volumes/MicroBay/Downloads/video-research/O_zcc6Xl12g/slides/36-0920.jpg)

**Observed / reported:** The full pyramid returns at the conclusion.

**How it works:** Architecture, automated checks, verification, concise prose, and judgment are prerequisites to scaling automation.

**Application and limits:** Start with our recurring failure classes and cheapest durable prevention. Tool installation alone will not create the environment she describes.

## 37. Should I build a factory — 15:35

[Video at capture](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=935s) · [Full-resolution capture](/Volumes/MicroBay/Downloads/video-research/O_zcc6Xl12g/slides/37-0935.jpg)

**Observed / reported:** 'Should I build a software factory?' clarifies that this means automating writing, shipping, and deploying code.

**How it works:** The factory is a layer built on a reliable development loop.

**Application and limits:** Identify which parts of our loop already produce verifiable outcomes before introducing scheduled or event-triggered work.

## 38. Improve the inner loop — 15:55

[Video at capture](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=955s) · [Full-resolution capture](/Volumes/MicroBay/Downloads/video-research/O_zcc6Xl12g/slides/38-0955.jpg)

**Observed / reported:** 'Don't automate a bad loop' compares low and high trust with the caption 'improve your loop before automating.'

**How it works:** Automating a failure-prone process increases the rate and cost of producing defects and repair work.

**Application and limits:** Make a single agent's reproduce→fix→verify cycle dependable first. Add external triggers once that cycle works on representative tasks.

## 39. Automated triggers — 16:05

[Video at capture](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=965s) · [Full-resolution capture](/Volumes/MicroBay/Downloads/video-research/O_zcc6Xl12g/slides/39-0965.jpg)

**Observed / reported:** The animation adds a third loop labeled factory with an automated trigger. It still contains writing, verification, and feedback.

**How it works:** Automation supplies work and repeats a proven loop; it does not replace checking.

**Application and limits:** Give automated jobs explicit scope, completion evidence, resource limits, and failure handling. These implementation controls are our proposed design, not configuration shown in the talk.

## 40. Grok Bot outer loop — 16:15

[Video at capture](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=975s) · [Full-resolution capture](/Volumes/MicroBay/Downloads/video-research/O_zcc6Xl12g/slides/40-0975.jpg)

**Observed / reported:** Grok Bot outer-loop inputs include feedback on X, a Linear ticket, a new Slack message, cron/schedule, and Datadog/Sentry alerts. A shared team bot feeds an inner coding/verification loop. Link: x.ai/bot.

**How it works:** Connectors and routines initiate coding agents and projects. The outer loop decides when work starts; the inner loop produces and checks changes.

**Application and limits:** Separate trigger ingestion/triage from execution, verification, and merge policy. Use our available orchestrator; the concept does not depend on Grok Bot or Cursor.

## 41. Release fuzzing report — 16:35

[Video at capture](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=995s) · [Full-resolution capture](/Volumes/MicroBay/Downloads/video-research/O_zcc6Xl12g/slides/41-0995.jpg)

**Observed / reported:** The displayed Linux x64 .deb fuzz report compares a stable build with 0.79.4 and checks published SHA-256 values. It uses a local backend from main and a saved copy of production gate values. After merging two duplicate pairs: 50 distinct bugs, three new (0 high/two medium/one low), 47 existing (one high/nine medium/37 low); the high issue also exists in 0.79.4. Findings are separate replies, new first then severity.

**How it works:** This is artifact-level, baseline-aware exploration with environment disclosure and deduplication. The narration says releases trigger fuzzing, fix PRs, and auto-merge; the screenshot itself is a findings report and does not show those fixes passing or merging.

**Application and limits:** Verify the actual packaged build, record provenance and flags, compare against a baseline, preserve replayable evidence, deduplicate, then create fixes that rerun checks. Implement platform-specific release validation and choose merge gates according to risk.

## 42. Closing — 17:05

[Video at capture](https://www.youtube.com/watch?v=O_zcc6Xl12g&t=1025s) · [Full-resolution capture](/Volumes/MicroBay/Downloads/video-research/O_zcc6Xl12g/slides/42-1025.jpg)

**Observed / reported:** The closing title changes to 'all code is slop (except yours).' She returns to high velocity with quality through foundations.

**How it works:** Trust is supported by the surrounding system rather than an assertion that generated code is inherently reliable.

**Application and limits:** Our reusable asset should be a maintained engineering environment: product framework, constraints, feature map, driver, verification, evidence, and feedback.

