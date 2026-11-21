---
name: verify
description: Run this app's built binary and prove a feature works the way a user sees it, with the output as evidence. Use before handing back any behaviour change, when adding a feature, or to explore the running app.
---

# Verify

`python3 scripts/verify.py` is the one driver for the running app. Don't improvise `cargo run` commands: the scripts set up the pinned toolchain and the build folder.

## Prove a change: the gate

```sh
python3 scripts/verify.py          # same as check.py's verify gate
```

It checks the feature map, then runs every journey in `crates/app/tests/journeys.rs` on its own against the built app binary, and writes each journey's commands and output to `.build/evidence/latest/evidence.md`. Read it. A passing journey whose output shows the wrong thing is a bad journey: fix it.

## Explore the running app

```sh
python3 scripts/verify.py launch -- <args>    # build the app, run it once with <args>, print its output and exit code
```

Give the app a scratch data folder that exists, never real data. Exploring is for looking and judging; it's not proof. Once a behaviour works, write the journey that proves it.

## Add a feature

1. `python3 scripts/new_feature.py <name>` creates `crates/features/<name>/` (`no_std`), `feature-map/<name>.toml` and a `<name>_works` journey stub. The tests and verify gates fail until the stub and the map entry are written.
2. Write the logic in the feature crate, with a trait for each thing it needs from outside. Implement the traits in a crate in `crates/platform/`, and wire the feature into `crates/app`: real services are created there only.
3. Replace the stub with journeys that run the app the way a user would: the `app(...)` helper runs the built binary with arguments, and `data_folder(...)` gives each journey a new, empty folder. Check durable effects, not only output: run the app again and check what it remembers. Check failures too (the tally example makes its data folder read-only to make a save fail).
4. Fill in `feature-map/<name>.toml`: `summary`, and one `[[journeys]]` per journey with `name` (the test function) and what it `proves`. A journey belongs to one feature only.

## Rules

- Drive the real user path: the built binary, its arguments and its files. Fakes go only where a real service would be, never inside the feature.
- If a journey fails, fix the app or record why in the feature's map entry. **Never weaken a journey to make it pass.** If you can't make it pass within the rules, stop and report.
- Journeys live in `crates/app/tests/journeys.rs` only; the verify gate rejects a `[[test]]` that moves them.
