---
name: verify
description: Run this Rust app and prove a feature works the way a user sees it, with its output as evidence. Use before handing back any behaviour change, when adding a feature, or to explore the running app.
---

# Verify

`python3 scripts/verify.py` is the one driver for the running app. Journeys run the built binary the way a user does: arguments in, output and saved data out. Don't prove a feature by calling its crate from a test instead.

## Prove a change: the gates

```sh
python3 scripts/verify.py          # same as check.py's verify gate: every journey against the debug build
python3 scripts/verify.py release  # same as the release gate: every journey against the release build
python3 scripts/package.py         # the release binary, checked and launched once (crates/app/smoke.toml)
```

`verify` checks the feature map, then runs each journey in `crates/app/tests/journeys.rs` on its own and writes `.build/evidence/latest/evidence.md` with every command a journey ran and what the app printed (release: `.build/evidence/release/evidence.md`). Read it. A passing journey whose output shows the wrong thing is a bad journey: fix it. Code that works only in debug builds fails the release gate: `debug_assert!` doesn't run there, so never put work inside one.

## Explore the running app

```sh
python3 scripts/check.py --only compiler            # builds the app (and everything else) into .build/target
mkdir -p .build/look && .build/target/debug/app --data .build/look show
```

Run the binary the gates built; don't run cargo by hand (scripts/tools.py sets where the toolchain, downloads and build output go). Use a data folder under `.build/` (never your own files), and start it empty to see a new user's state. Exploring is for looking and judging; it's not proof. Once a behaviour works, write the journey that proves it.

## Add a feature

1. Run `python3 scripts/new_feature.py <name>`: it creates `crates/features/<name>/` (a `no_std` crate and a test to write), `feature-map/<name>.toml`, a journey stub `<name>_works` at the end of `crates/app/tests/journeys.rs`, and the app's dependency on the crate. The test and the journey fail until you write them.
2. Write the feature's logic in its crate, with a trait for each thing it needs from outside (a store, a clock), implemented in a `crates/platform/<name>/` crate. Wire it into `crates/app/src/main.rs` (code-owned: if you can't, stop and report what the app needs).
3. Write the journey: a new data folder with `data_folder("<journey>")`, then `app(&data, &[...])` for each step, asserting the whole of `stdout`, `stderr` and `ok`. Run it again on the same folder to check what was saved.
4. In `feature-map/<id>.toml`, name the feature's crates in `modules` and each journey with what it `proves`. A journey belongs to one feature only. A feature whose code lives in a crate another feature already has gets its own entry naming that crate: `python3 scripts/new_feature.py <id> --in <module>` creates the entry, journey stub and test stub.
5. If the app's main path changes, keep `crates/app/smoke.toml` (code-owned) about it: package.py launches the release binary with it.

## Rules

- Drive the real user path through the real binary: journeys run `CARGO_BIN_EXE_app`, the same composition root that ships.
- Carry each journey through the user's action and check the resulting output and state: never stop at a prompt or usage message without running the command it offers.
- Check durable effects, not just the output: run the app again on the same data folder and check again; make saving fail (a read-only folder) where a failure must leave things as they were.
- Assert whole values (`assert_eq!(run.stdout, "apple 2\npear 1\n")`), not parts.
- If a journey fails, fix the app. **Never weaken a journey to make it pass.** If you can't make it pass within the rules, stop and report.
