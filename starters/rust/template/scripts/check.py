"""Run every enforcement gate. Exit non-zero if any gate fails. CI runs this; agents run it before handing back.

Gates:
  compiler  build every crate and target with the pinned toolchain: unsafe forbidden, deprecated APIs and every
            other warning are errors (Cargo.toml's workspace lints, RUSTFLAGS=-D warnings)
  clippy    no unwrap/expect/panic, indexing, `as` casts, catch-all matches on enums, banned APIs (clippy.toml)
  deny      every crate in the dependency tree comes from crates.io and has an allowed license (deny.toml)
  arch      the crate graph against the module shape (arch/shape.toml), and the source checks in arch/checker
  tests     every test: unit, integration, property and doc tests
  verify    the feature map is complete, and every journey passes against the built app (scripts/verify.py)

The gates run one after another (compiler, clippy and tests share one build folder). Each gate's output is printed
when it fails, followed by its result and time; a summary in gate order comes last. Before a gate that compiles
(compiler, clippy, tests, verify), a workspace crate with a build script or proc macro fails that gate without being
built, since building it would run that code before any gate had looked at it.

Each run is recorded against the files it saw (scripts/handback.py, observe mode), so a hand-back or commit can say
whether its files passed every gate.

Usage: python3 scripts/check.py [--only GATE ...]
"""
from pathlib import Path
import argparse
import subprocess
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parent))
from arch import build_time_code, findings as arch_findings  # noqa: E402
from handback import record_check, snapshot  # noqa: E402
from tools import rust_env, tool_path  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
GATES = ['compiler', 'clippy', 'deny', 'arch', 'tests', 'verify']
COMPILES = {'compiler', 'clippy', 'tests', 'verify'}
NOISE = ('Compiling ', 'Checking ', 'Finished ', 'Running ', 'Doc-tests ', 'Blocking ', 'Locking ', 'Adding ',
         'Downloaded ', 'Downloading ', 'Updating ')


def run(cmd: list[str], env: dict) -> tuple[bool, str]:
    proc = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True)
    lines = [l for l in (proc.stdout + proc.stderr).splitlines() if not l.strip().startswith(NOISE)]
    return proc.returncode == 0, '\n'.join(lines).strip()


def gate(name: str, env: dict) -> tuple[bool, str]:
    if name == 'compiler':
        return run(['cargo', 'build', '--workspace', '--all-targets'], env)
    if name == 'clippy':
        return run(['cargo', 'clippy', '--workspace', '--all-targets'], env)
    if name == 'deny':
        return run([str(tool_path('cargo-deny')), '--manifest-path', 'Cargo.toml', 'check', '--hide-inclusion-graph',
                    'bans', 'licenses', 'sources'], env)
    if name == 'arch':
        found = arch_findings()
        return not found, '\n'.join(found)
    if name == 'tests':
        ok, output = run(['cargo', 'test', '--workspace', '--all-targets', '--no-fail-fast'], env)
        if not ok:
            return ok, output
        return run(['cargo', 'test', '--workspace', '--doc', '--no-fail-fast'], env)
    return run([sys.executable, str(ROOT / 'scripts/verify.py'), 'run'], env)


def check(selected: list[str], env: dict) -> list[str]:
    unsafe_to_build = build_time_code(env) if COMPILES & set(selected) else []
    results: dict[str, bool] = {}
    for name in selected:
        started = time.monotonic()
        ok, output = (False, '\n'.join(unsafe_to_build)) if name in COMPILES and unsafe_to_build else gate(name, env)
        results[name] = ok
        if not ok and output:
            print(output)
        print(f'{"PASS" if ok else "FAIL"} {name}  ({time.monotonic() - started:.0f}s)', flush=True)
    if len(selected) > 1:
        print('Summary: ' + ', '.join(f'{n} {"PASS" if results[n] else "FAIL"}' for n in selected), flush=True)
    return [n for n in selected if not results[n]]


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--only', action='append', choices=GATES)
    chosen = parser.parse_args().only or GATES
    env = rust_env()  # links .build into the cache folder first, so the snapshot never sees build output
    before = snapshot(ROOT)  # observe mode: a run counts only for files that didn't change while it ran
    try:
        selected = [g for g in GATES if g in chosen]
        failed = check(selected, env)
    except KeyboardInterrupt:
        sys.exit('\nStopped.')  # an interrupted run isn't a check, so it isn't recorded
    record_check(ROOT, selected, failed, before)  # observe mode: lets scripts/handback.py tell whether hand-backs were checked
    sys.exit(1 if failed else 0)
