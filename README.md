# b-stack

Clone this, and an agent can set up a new app where quality is **enforced, not requested**: architecture encoded in the compiler, checks that block workarounds, and rules that are tested to prove they fire.

It started from Lauren Tan's talk [*All Code Is Slop (Except Mine)*](https://www.youtube.com/watch?v=O_zcc6Xl12g) and is built around an **enforcement pyramid**: make the wrong thing impossible to write; failing that, block it from merging; failing that, catch it in verification. Prose comes last.

**Status: early.** Three starters. The iOS one uses TCA for state flow and enforces 13 tested rules through the compiler, unit tests, [Tuist](https://tuist.dev), [SwiftLint](https://github.com/realm/SwiftLint), [Harmonize](https://github.com/perrystreetsoftware/Harmonize), and verification: XCUITest journeys from a feature map, run against a test-mode build of the app, with screenshot evidence. The Rust one enforces 12 tested rules through the compiler, [Clippy](https://doc.rust-lang.org/clippy/), [cargo-deny](https://github.com/EmbarkStudios/cargo-deny), an architecture checker built on [syn](https://github.com/dtolnay/syn), and journeys that run the built binary. The TypeScript one is an Electron app laid out like [T3 Code](https://github.com/pingdotgg/t3code) (pnpm, Effect, React, vite-plus) and enforces 12 tested rules through TypeScript 7 with the Effect language service, type-aware [oxlint](https://oxc.rs) with rules of our own, a dependency and architecture check, and journeys that drive the built app through Playwright. CI and a new-feature command are not built yet.

## Using it

Ask your agent (Claude Code, Codex, …) from this repo:

> Start a new iOS app called *X* using the new-project skill.

or a Rust one ("Start a new Rust project called *X* …"), or a TypeScript desktop app ("Start a new Electron app called *X* …").

| Folder | What it is |
|---|---|
| [skills/](skills/) | Procedures for agents: new project, correction loop |
| [rules/](rules/) | Rules as data, each with fail/pass test cases per platform, run through that starter's gates |
| [starters/ios/](starters/ios/) | The iOS template a new project is created from |
| [starters/rust/](starters/rust/) | The Rust template |
| [starters/typescript/](starters/typescript/) | The TypeScript (Electron) template |
| [scripts/](scripts/) | `test_rules.py`, `check_repo.py`, `verify_artifacts.py` |
| [DECISIONS.md](DECISIONS.md) | Why things are the way they are (for humans) |
| [research/](research/lauren-tan-video/) | The source talk: transcript and slide analysis |

## Checks

```sh
python3 scripts/test_rules.py   # every rule case through its starter's gates (iOS ~15 min, Rust ~1 min, TypeScript ~2 min; first run downloads tools)
python3 scripts/check_repo.py   # rule/case/skill format, catalog, links
```

Requires Python 3.11+. iOS: macOS with Xcode (tested with 27.2 / Swift 6.4.2) and an iOS Simulator runtime. Rust: `rustup` (tested on macOS, Apple silicon). TypeScript: macOS on Apple silicon, with a display for the journeys. Tuist, SwiftLint, cargo-deny, the Rust toolchain, Node.js, pnpm and Electron are downloaded, pinned and verified; nothing is installed globally. To keep build output and tools off your main drive, set `cache_dir = "/path"` in `~/.config/b-stack/config.toml`. The research video and images aren't in Git: `verify_artifacts.py` looks in `artifacts/`, or in `media_dir = "/path"` from the same file.
