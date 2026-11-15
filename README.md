# b-stack

Clone this, and an agent can set up a new app where quality is **enforced, not requested**: architecture encoded in the compiler, checks that block workarounds, and rules that are tested to prove they fire.

It started from Lauren Tan's talk [*All Code Is Slop (Except Mine)*](https://www.youtube.com/watch?v=O_zcc6Xl12g) and is built around an **enforcement pyramid**: make the wrong thing impossible to write; failing that, block it from merging; failing that, catch it in verification. Prose comes last.

**Status: early.** iOS only. Rules and compiler enforcement work; the checker, CI and verification parts of the starter are not built yet.

## Using it

Ask your agent (Claude Code, Codex, …) from this repo:

> Start a new iOS app called *X* using the new-project skill.

| Folder | What it is |
|---|---|
| [skills/](skills/) | Procedures for agents: new project, correction loop |
| [rules/](rules/) | Rules as data, each with fail/pass Swift test cases |
| [starters/ios/](starters/ios/) | The iOS template a new project is created from |
| [scripts/](scripts/) | `test_rules.py`, `check_repo.py`, `verify_artifacts.py` |
| [DECISIONS.md](DECISIONS.md) | Why things are the way they are (for humans) |
| [research/](research/lauren-tan-video/) | The source talk: transcript and slide analysis |

## Checks

```sh
python3 scripts/test_rules.py   # every rule case against the real Swift compiler (~1 min)
python3 scripts/check_repo.py   # rule/case/skill format, catalog, links
```

Requires Python 3.11+ and Swift 6.2+ (tested with 6.4.2).
