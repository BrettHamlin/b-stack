# <App name>: agent instructions

## Before you change code

- Crates and their dependencies come from the module shape (`arch/shape.toml`, the owner's). A crate's role is its folder: `crates/core`, `crates/features/<name>`, `crates/platform/<name>`, `crates/app`. To add a feature, create `crates/features/<name>/` with `[lints] workspace = true` in its `Cargo.toml`, and declare the dependencies its role allows. Don't edit the root `Cargo.toml`, `arch/`, `clippy.toml` or `deny.toml`: the gates fail if a crate is outside the shape. A link the shape doesn't allow is outside it: stop and report.
- Use the existing approved APIs for <persistence, networking, time, background work>. Don't introduce a second way to do the same thing.
- Pass dependencies in as parameters and traits. Real services are created in one place only: the app crate.
- Add a feature with `python3 scripts/new_feature.py <name>`: it creates the crate, its feature-map entry and a journey to write. Its test and journey fail until you write them.
- Each feature is a crate in `crates/features/<name>`: `no_std` logic, a trait for each thing it needs from outside (implemented in a platform crate), example tests and a property test (random sequences checked against a model of the spec, written from the spec) in its `tests/` folder, a `feature-map/<id>.toml` entry, and journeys in `crates/app/tests/journeys.rs` that run the built app and prove it works.

## Checks

```sh
python3 scripts/check.py        # compiler, clippy, deny, arch, settings, tests, verify, release: all must PASS
python3 scripts/package.py      # the release binary, checked and launched once
```

Run it before handing back. If it stops because the cache folder is unavailable (e.g. an external drive isn't mounted), report that; don't build elsewhere. A failure names the rule and how to fix it.

`verify` runs every feature-map journey against the built app and writes each one's output to `.build/evidence/latest/evidence.md`; `release` runs them against the release build. For behaviour changes, read it and include its path in your report. The verify skill (`.agents/skills/verify/SKILL.md`) says how to prove and explore a feature.

## Never weaken enforcement

Never suppress, disable, weaken or bypass a check. That includes lint attributes (`#[allow]`, `#[expect]`), `unsafe`, `#[ignore]`, and editing `Cargo.toml` (root), `arch/`, `clippy.toml`, `deny.toml`, `rust-toolchain.toml`, `tools.toml`, `.cargo/`, `scripts/`, or CI. The settings gate compares the settings in effect with `arch/settings.json`; never change both to get a change through.

**If the right fix isn't possible within the rules, stop and report:** what you were trying to do, which rule blocks it, and what you'd change. A clear report is a successful outcome.

## Don't write unrequested docs

No new markdown files, rule files or explanatory comments unless asked. Comments are for what code can't express.
