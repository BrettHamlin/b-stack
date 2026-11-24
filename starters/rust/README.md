# Rust starter

Copied into a new repo by the [new-project skill](../../skills/new-project/SKILL.md). Only what's listed as built exists.

## What's built

| Piece | Path | Status |
|---|---|---|
| Cargo workspace: core, one example feature, one platform crate, the app binary | `template/Cargo.toml`, `template/crates/` | ✅ Builds with Rust 1.99.0 and the strict settings below |
| Module shape: crate roles by folder, the links each may use, which are `no_std`, which third-party crates each may use | `template/arch/shape.toml` | ✅ Agents add crates in the shape's folders without editing protected files |
| Example feature: a tally of named items (record, show, failed save keeps the old tally), with example tests and a property test | `template/crates/features/tally/`, `template/crates/platform/files/`, `template/crates/app/` | ✅ |
| Property test for the example feature: 200 seeded random sequences of records, failed loads and failed saves, checked step by step against a model; stops at the first divergence and prints the seed and steps | `template/crates/features/tally/tests/property.rs` | ✅ Under a second. No library: a seeded generator in the file |
| Gate command: compiler, clippy, deny, arch, settings, tests, verify | `template/scripts/check.py` | ✅ Every gate passes; rule suite 66/66 (2026-11-24, Rust 1.99.0, cargo-deny 0.20.2) |
| Architecture checks: the crate graph and manifests against the shape (`cargo metadata`), then every source file through a `syn` parser | `template/scripts/arch.py`, `template/arch/checker/` | ✅ Module boundaries, third-party crates per role, inherited lints, no build scripts or proc macros, no lint attributes, no global state, no std in `no_std` crates, no skipped tests, no `macro_rules!`/`include!`/`#[path]` |
| Verification: feature map, journeys that run the built app binary, evidence | `template/scripts/verify.py`, `template/crates/app/tests/journeys.rs`, `template/feature-map/` | ✅ Three tally journeys; each journey's output goes to `.build/evidence/latest/evidence.md` |
| Pinned tools, checksum-verified, no global install | `template/rust-toolchain.toml`, `template/tools.toml`, `template/scripts/tools.py` | ✅ Rust 1.99.0 (installed by rustup into the tools folder, not `~/.rustup`), cargo-deny 0.20.2 for Apple silicon Macs and x64 Linux. Inherited settings that change a check (`RUSTFLAGS`, `CARGO_PROFILE_*`, `RUSTC_WRAPPER`, `CLIPPY_CONF_DIR`, ...) are dropped, and every crate gets the root `clippy.toml` |
| New-feature command: a feature crate in the shape's folder, its feature-map entry, a journey stub and the app's dependency on it; every edit checked before any file is written | `template/scripts/new_feature.py` | ✅ The new crate passes compiler, clippy, deny, arch and settings; its test and journey fail the tests and verify gates with "Write this ..." until written |
| Settings gate: the compiler arguments each target gets (lint levels, `-D warnings`, profile settings) as cargo passes them, Clippy's config, cargo's merged config, deny.toml, the toolchain versions, CODEOWNERS coverage; `record` for the owner | `template/scripts/settings.py`, `template/arch/settings.json` | ✅ A lowered lint level, a profile without overflow checks, a `.cargo/config.toml` test runner, a weakened deny.toml or clippy.toml, or a CODEOWNERS gap fails it |
| CI workflow: every gate on pull requests and `main`, on Linux | `template/.github/workflows/check.yml` | ✅ The same commands as b-stack's own CI runs on the starter (a test checks they match) |
| Build output, toolchain and downloaded crates in a configurable cache folder | `template/scripts/paths.py`, `template/scripts/tools.py` | ✅ `.build/` becomes a link into it; stops if the folder is missing |
| Agent instructions, CODEOWNERS | `template/AGENTS.template.md`, `template/CODEOWNERS` | ✅ Draft; placeholders to fill in |

Needs `rustup` on the machine; `scripts/tools.py` installs the pinned toolchain with it. The cargo-deny pins are the
`aarch64-apple-darwin` and `x86_64-unknown-linux-musl` builds.

## Module shape

| Crate folder | Role | May depend on | std |
|---|---|---|---|
| `crates/core` | core: domain types shared by every feature | nothing | `no_std` |
| `crates/features/<name>` | feature: logic, plus the traits for what it needs from outside | core | `no_std` |
| `crates/platform/<name>` | platform: real I/O, implementing feature traits | core, features | std |
| `crates/app` | app: the composition root and only binary | everything | std |

This table is `template/arch/shape.toml` (protected). The root `Cargo.toml`'s members are the same folders, so a new
crate in one of them is built and checked without editing a protected file. A crate's own `Cargo.toml` declares its
dependencies; the arch gate checks each one against the shape. Each of those folders needs at least one crate: Cargo
1.99.0 fails to load the workspace when a member glob matches nothing, so an app with no platform crate needs the owner
to remove `crates/platform/*` from the root `Cargo.toml`. No third-party crates are allowed to start; each role's
`external` list is where the owner adds them. Journeys are the tests in `crates/app/tests/journeys.rs`.

## Strict settings

| Setting | Where | Effect |
|---|---|---|
| `unsafe_code = "forbid"` | `Cargo.toml` workspace lints | No unsafe code, and no attribute can lower it; thread safety can't be bypassed |
| `deprecated = "deny"`, `RUSTFLAGS=-D warnings` | `Cargo.toml`, `scripts/tools.py` | Retired APIs and every other warning fail the build |
| Clippy: `unwrap_used`, `expect_used`, `panic`, `todo`, `unimplemented`, `indexing_slicing`, `as_conversions`, `wildcard_enum_match_arm`, `allow_attributes`, `disallowed_methods`, `dbg_macro`, `exit`, `mem_forget` | `Cargo.toml` workspace lints | Denied outside tests (`clippy.toml` allows unwrap, expect, panic and indexing in tests) |
| `disallowed-methods` | `clippy.toml` | `std::thread::sleep` banned, with the reason |
| `CLIPPY_CONF_DIR` = the project root | `scripts/tools.py` | Every crate gets the root `clippy.toml`; a crate's own can't drop the bans |
| `[sources]`, `[licenses]` | `deny.toml` | crates.io only; permissive licenses only |
| `#![no_std]` | core and feature crates | std can't be named there |

## Not built yet (in order)

1. **Release builds:** the optimized binary, checked and launched once, named by version.
2. **Journeys against the release build** (a `release` gate).
3. **Check record:** the iOS starter's observe-mode hand-back record (`handback.py`, hooks) isn't ported.
4. **Verify skill** for agents in the new app (the iOS starter has one).
5. **Fuzzing** for code that reads untrusted input (file formats, network messages).

Branch protection (the `check` job as a required status check, code-owner review) is set on GitHub after the first
push; the new-project skill says how.
