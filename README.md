# b-stack

Clone this, and an agent can set up a new app where quality is **enforced, not requested**: architecture encoded in the compiler, checks that block workarounds, and rules that are tested to prove they fire.

It started from Lauren Tan's talk [*All Code Is Slop (Except Mine)*](https://www.youtube.com/watch?v=O_zcc6Xl12g) and is built around an **enforcement pyramid**: make the wrong thing impossible to write; failing that, block it from merging; failing that, catch it in verification. Prose comes last.

**Status: early.** iOS only. The starter uses TCA for state flow and enforces 13 tested rules through the compiler, unit tests, [Tuist](https://tuist.dev), [SwiftLint](https://github.com/realm/SwiftLint), [Harmonize](https://github.com/perrystreetsoftware/Harmonize), and verification: XCUITest journeys from a feature map, run against a test-mode build of the app, with screenshot evidence. CI and a new-feature command are not built yet.

## Using it

Ask your agent (Claude Code, Codex, …) from this repo:

> Start a new iOS app called *X* using the new-project skill.

| Folder | What it is |
|---|---|
| [skills/](skills/) | Procedures for agents: new project, correction loop |
| [rules/](rules/) | Rules as data, each with fail/pass Swift test cases run through the starter's gates |
| [starters/ios/](starters/ios/) | The iOS template a new project is created from |
| [scripts/](scripts/) | `test_rules.py`, `check_repo.py`, `verify_artifacts.py` |
| [DECISIONS.md](DECISIONS.md) | Why things are the way they are (for humans) |
| [research/](research/lauren-tan-video/) | The source talk: transcript and slide analysis |

## Checks

```sh
python3 scripts/test_rules.py   # every rule case through the starter's gates (~15 min; first run downloads tools)
python3 scripts/check_repo.py   # rule/case/skill format, catalog, links
```

Requires macOS with Xcode (tested with 27.2 / Swift 6.4.2), an iOS Simulator runtime, and Python 3.11+. Tuist and SwiftLint are downloaded, pinned and checksum-verified; nothing is installed globally. To keep build output and tools off your main drive, set `cache_dir = "/path"` in `~/.config/b-stack/config.toml`. The research video and images aren't in Git: `verify_artifacts.py` looks in `artifacts/`, or in `media_dir = "/path"` from the same file.
