# b-stack: agent instructions

This repo is a toolkit agents use to create new apps with enforcement built in. Its main contents are rules with tests, starter templates, and skills. Prose is kept minimal.

## Layout

- `skills/`: procedures (`SKILL.md`), plus principles for judgment calls in `skills/README.md`
- `rules/<id>/`: `rule.toml` + `<platform>/<case>/` test cases (`ios/`, `rust/`). Format in `rules/README.md`.
- `starters/ios/`, `starters/rust/`: the templates a new project is copied from. Each `README.md` lists what's built.
- `scripts/`: `test_rules.py` (runs every case through its platform's starter `scripts/check.py`), `check_repo.py`, `test_starter_scripts.py` (the starters' helpers outside the gates), `platforms.py` (what differs per platform), `verify_artifacts.py`
- `DECISIONS.md`: the human owner's summary. Update it when a decision is made or a finding changes.
- `research/lauren-tan-video/`: source material. Keep the raw transcript unchanged.

## Before handing back

```sh
python3 scripts/test_rules.py
python3 scripts/check_repo.py
python3 scripts/test_starter_scripts.py
```

Zero FAIL in all three. `test_rules.py` runs the iOS cases, then the Rust ones; `--platform ios` or `--platform rust` runs one. iOS: the first run downloads pinned tools and builds TCA and the Harmonize rules (a few minutes more); later runs take 20 to 30 minutes on a laptop, mostly simulator runs for the verify cases. Needs an iOS Simulator runtime. Rust: about a minute; needs `rustup`, which installs the pinned toolchain into the cache folder. Each checkout has its own work folder; a second run in the same checkout is refused until the first finishes. Anything on this Mac that needs a simulator another run is using (this suite, or `check.py`'s tests and verify gates in any checkout) waits for it and prints who holds it. Run it as shown: how many cases or simulators run at once (`rule_jobs`, `verify_workers` in `~/.config/b-stack/config.toml`) is the owner's per-machine setting, not something to change for a run.

## Rules for changing this repo

- **Every rule claim is tested.** A new rule needs a fail case naming the gate that rejects it and the exact `diagnostic`, for each platform it claims. The enforcement itself goes in that platform's starter: `starters/ios/template/` (compiler setting, Harmonize rule, SwiftLint rule) or `starters/rust/template/` (workspace lints, `clippy.toml`, `deny.toml`, `arch/`). Never edit a case just to make it pass. If the toolchain disagrees with the rule, the rule or `DECISIONS.md` is what changes.
- **Record the toolchain version** for any compiler finding.
- **Starters only list what exists.** Don't describe planned pieces as built.
- **No new prose docs** beyond skills, `rules/README.md`, starter READMEs and `DECISIONS.md`.
- When citing the talk, check `research/lauren-tan-video/ANALYSIS.md`; don't attribute our ideas to her.

## Large files

Build output, package checkouts and downloaded tools go to the cache folder set by `$BSTACK_CACHE_DIR` or `cache_dir` in `~/.config/b-stack/config.toml` (logic in `starters/ios/template/scripts/paths.py`). On the owner's machine that's an external drive. If the folder is unavailable, scripts stop; never work around that by building on the internal drive. Say the drive isn't mounted.

## Research media

Video and images live in the folder set by `$BSTACK_MEDIA_DIR` or `media_dir` in `~/.config/b-stack/config.toml` (logic in `scripts/media.py`); `artifacts/` links there, or is the folder when nothing is set. Never copy them into Git. `scripts/verify_artifacts.py` checks them. `research/lauren-tan-video/build_report.py` rewrites files in that folder; inspect before running.

## Scope

Don't deploy, publish, install global tools, or start automated workflows without asking. Tools come from `starters/ios/template/tools.toml` (pinned, checksum-verified, local).
