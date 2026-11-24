"""The settings gate: the enforcement settings in effect are the ones in arch/settings.json, so weakening a check fails
here as well as in code-owner review. It reads what the tools will use, not the files' text, where the tools say:

  compiler    every workspace target's compiler arguments as cargo passes them, for the dev and the release profile
              (a wrapper records them during `cargo clippy --all-targets`): the workspace lint levels, RUSTFLAGS'
              -D warnings, any cap on lints, cfgs, and the profile's overflow checks, debug assertions, optimization
              and panic strategy. Every target of a kind (library, binary, tests) must have the recorded arguments.
  clippy      the driver each crate is checked with, the config folder Clippy reads (CLIPPY_CONF_DIR) and the
              settings in its clippy.toml
  rustdoc     RUSTDOCFLAGS, which doc tests get
  cargo       cargo's configuration from files (.cargo/config.toml here, in a parent folder or in CARGO_HOME), as
              cargo merges it: a test runner, [env], profile overrides or a compiler wrapper there change what the
              gates check
  deny        the settings in deny.toml, the config check.py gives cargo-deny
  toolchain   the rustc, cargo, Clippy and cargo-deny versions that run
  codeowners  /CODEOWNERS is the only one, every rule names an owner, and it lists every enforcement path

Settings from the environment (RUSTFLAGS, CARGO_PROFILE_*, RUSTC_WRAPPER, CLIPPY_CONF_DIR, ...) never reach the gates:
scripts/tools.py drops them. Changing a setting on purpose means changing arch/settings.json in the same change (both
are code-owned): `python3 scripts/settings.py record` writes it from the settings in effect, for the owner to review.

Usage: python3 scripts/settings.py [record]
"""
from pathlib import Path
import json
import os
import re
import shlex
import subprocess
import sys
import tomllib

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tools import rust_env, tool_path  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / 'arch/settings.json'
WORK = ROOT / '.build/settings'
FIX = ('Restore it. If the change is meant, it needs the owner: they change the setting and arch/settings.json together. '
       'Never weaken a check to make code pass; fix the code, or stop and report.')
# rustc flags that take the next argument as their value.
VALUED = {'-C', '-L', '-l', '-D', '-A', '-W', '-F', '-Z', '-o', '--crate-name', '--crate-type', '--cfg', '--check-cfg',
          '--extern', '--out-dir', '--cap-lints', '--target', '--emit', '--json', '--error-format', '--edition',
          '--force-warn', '--sysroot', '--remap-path-prefix', '--print'}
OWNER = re.compile(r'^@[A-Za-z0-9_-]+(/[A-Za-z0-9._-]+)?$|^[^@\s]+@[^@\s]+\.[^@\s]+$')
LEVELS = {'-D': '--deny', '-A': '--allow', '-W': '--warn', '-F': '--forbid', '--force-warn': '--force-warn'}
# Where output goes, which build it is, how it links and how much debug info it keeps: none of it changes a check.
IGNORED = re.compile(r'^(--crate-name|--crate-type|--error-format|--json|--emit|--out-dir|-L|-l|--extern|--check-cfg|'
                     r'--diagnostic-width|--remap-path-prefix)( |=|$)|^-C (metadata|extra-filename|incremental|linker|'
                     r'debuginfo|split-debuginfo|strip|embed-bitcode)=|^--cfg feature=')


def wrap(argv: list[str]) -> None:
    """Run as cargo's RUSTC_WRAPPER: note a workspace target's arguments and environment, then run the compiler."""
    if os.environ.get('CARGO_PRIMARY_PACKAGE'):
        with open(os.environ['BSTACK_SETTINGS_LOG'], 'a') as log:
            log.write(json.dumps({'argv': argv, 'dir': os.environ.get('CARGO_MANIFEST_DIR', ''),
                                  'profile': os.environ['BSTACK_SETTINGS_PROFILE'],
                                  'clippy_conf_dir': os.environ.get('CLIPPY_CONF_DIR'),
                                  'clippy_args': os.environ.get('CLIPPY_ARGS')}) + '\n')
    os.execvp(argv[0], argv)


def normalized(args: list[str]) -> tuple[list[str], str, str, bool]:
    """(the arguments that change a check, in order; the source file; the crate type; compiled as tests)."""
    kept, source, crate_type, test = [], '', 'lib', False
    i = 0
    while i < len(args):
        arg = args[i]
        if arg in VALUED and i + 1 < len(args):
            value, i = args[i + 1], i + 2
            if arg in LEVELS:
                kept.append(f'{LEVELS[arg]}={value}')
                continue
            if arg == '--crate-type':
                crate_type = value
            joined = f'{arg} {value}' if arg.startswith('-C') or arg in ('-Z', '--cfg') else f'{arg}={value}'
            if not IGNORED.search(joined):
                kept.append(joined)
            continue
        i += 1
        if arg == '--test':
            test = True
            kept.append(arg)
        elif not arg.startswith('-'):
            source = arg
        elif not IGNORED.search(arg):
            kept.append(arg)
    return kept, source, crate_type, test


def target_key(manifest: str, target: dict) -> str:
    """A target by package, name, kind and source: two targets may share any one of these."""
    return f'{relative(str(Path(manifest).parent))} {target["name"]} {",".join(target["kind"])} {relative(target["src_path"])}'


def compiled() -> tuple[list[dict], dict[str, str], dict[str, set[str]]]:
    """Every workspace target's compile, dev and release, as cargo runs it under check.py's environment; every target
    cargo metadata lists (build scripts aside); and, per profile, the targets cargo reported building."""
    env = rust_env()
    WORK.mkdir(parents=True, exist_ok=True)
    wrapper, log = WORK / 'rustc-wrapper', WORK / 'compiles.jsonl'
    wrapper.write_text(f'#!/bin/sh\nexec {shlex.quote(sys.executable)} {shlex.quote(str(Path(__file__).resolve()))} '
                       '--wrap "$@"\n')
    wrapper.chmod(0o755)
    log.unlink(missing_ok=True)
    env = {**env, 'CARGO_TARGET_DIR': str(WORK / 'target'), 'RUSTC_WRAPPER': str(wrapper), 'BSTACK_SETTINGS_LOG': str(log)}
    meta = subprocess.run(['cargo', 'metadata', '--format-version', '1', '--no-deps'], cwd=ROOT, env=env,
                          capture_output=True, text=True)
    if meta.returncode != 0:
        sys.exit(f'[protected-enforcement] cargo metadata failed:\n{meta.stderr.strip()[-3000:]}')
    packages = json.loads(meta.stdout)['packages']
    members = [a for p in packages for a in ('-p', p['name'])]
    listed = {target_key(p['manifest_path'], t): f'{relative(t["src_path"])} (target `{t["name"]}`)'
              for p in packages for t in p['targets'] if 'custom-build' not in t['kind']}
    built: dict[str, set[str]] = {}
    for profile, flag in (('dev', []), ('release', ['--release'])):
        # Clean the workspace's own crates, so cargo compiles each one again and the wrapper sees it.
        subprocess.run(['cargo', 'clean', '--quiet', *flag, *members], cwd=ROOT, env=env, capture_output=True)
        proc = subprocess.run(['cargo', 'clippy', '--quiet', '--message-format', 'json', '--workspace', '--all-targets',
                               *flag], cwd=ROOT, env={**env, 'BSTACK_SETTINGS_PROFILE': profile}, capture_output=True,
                              text=True)
        messages = [json.loads(line) for line in proc.stdout.splitlines() if line.startswith('{')]
        built[profile] = {target_key(m['manifest_path'], m['target']) for m in messages
                          if m.get('reason') == 'compiler-artifact'}
        if proc.returncode != 0:
            sys.exit(f'[protected-enforcement] Couldn\'t read the compiler settings ({profile} profile): the workspace '
                     f'doesn\'t check. Run the clippy gate.\n{proc.stderr.strip()[-3000:]}')
    return ([json.loads(line) for line in log.read_text().splitlines()] if log.is_file() else []), listed, built


def relative(path: str | None) -> str | None:
    if path is None:
        return None
    resolved = Path(path).resolve()
    return str(resolved.relative_to(ROOT.resolve())) if resolved.is_relative_to(ROOT.resolve()) else str(resolved)


def first_line(cmd: list[str], env: dict) -> str:
    proc = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True)
    return proc.stdout.strip().splitlines()[0] if proc.returncode == 0 and proc.stdout.strip() else f'(failed: {cmd[0]})'


def effective() -> dict:
    """The settings in effect, in arch/settings.json's shape; compiler arguments are per target, not yet by kind."""
    env = rust_env()
    targets, clippy = [], []
    runs, listed, built = compiled()
    for run in runs:
        args, source, crate_type, test = normalized(run['argv'][2:] if Path(run['argv'][0]).name == 'clippy-driver'
                                                    else run['argv'][1:])
        where = relative(str(ROOT / source)) if source else relative(run['dir'])  # cargo runs rustc in the root
        targets.append({'where': where, 'profile': run['profile'], 'kind': 'tests' if test else crate_type, 'args': args})
        clippy.append({'driver': Path(run['argv'][0]).name, 'conf_dir': relative(run['clippy_conf_dir']),
                       'args': run['clippy_args']})
    conf_dirs = {c['conf_dir'] for c in clippy if c['conf_dir'] is not None}
    clippy_config = {}
    for conf in sorted(conf_dirs):
        for name in ('clippy.toml', '.clippy.toml'):
            if (ROOT / conf / name).is_file():
                clippy_config[str(Path(conf) / name)] = tomllib.loads((ROOT / conf / name).read_text())
    config = subprocess.run(['cargo', '-Zunstable-options', 'config', 'get', '--format', 'json'], cwd=ROOT,
                            env={**env, 'RUSTC_BOOTSTRAP': '1'}, capture_output=True, text=True)
    if config.returncode != 0:
        sys.exit(f'[protected-enforcement] Couldn\'t read cargo\'s configuration:\n{config.stderr.strip()[-3000:]}')
    rustc = dict(line.split(': ', 1) for line in subprocess.run(['rustc', '-vV'], cwd=ROOT, env=env, capture_output=True,
                                                                  text=True).stdout.splitlines() if ': ' in line)
    return {
        'targets': targets,
        'listed': listed,
        'built': built,
        'clippy': {'checks': [json.loads(c) for c in sorted({json.dumps(c, sort_keys=True) for c in clippy})],
                   'config': clippy_config},
        'rustdoc': {'RUSTDOCFLAGS': env.get('RUSTDOCFLAGS')},
        'cargo': json.loads(config.stdout or '{}'),
        'deny': tomllib.loads((ROOT / 'deny.toml').read_text()),
        'toolchain': {'rustc': f'{rustc.get("release")} ({rustc.get("commit-hash")})',
                      'cargo': first_line(['cargo', '-V'], env), 'clippy': first_line(['cargo', 'clippy', '-V'], env),
                      'cargo-deny': first_line([str(tool_path('cargo-deny')), '--version'], env)},
    }


def by_kind(targets: list[dict]) -> tuple[dict, list[str]]:
    """Each profile's and kind's arguments, from its targets (which must agree), and the targets that don't."""
    kinds: dict[str, dict[str, list[str]]] = {}
    differ = []
    for target in targets:
        recorded = kinds.setdefault(target['profile'], {}).setdefault(target['kind'], target['args'])
        if recorded != target['args']:
            differ.append(f'{target["where"]} ({target["kind"]}, {target["profile"]} profile)')
    return kinds, differ


def differences(expected, actual, where: str) -> list[str]:
    """Each setting that differs, as `where.key: expected X, found Y`."""
    if isinstance(expected, dict) and isinstance(actual, dict):
        out = []
        for key in sorted(set(expected) | set(actual)):
            out += differences(expected.get(key), actual.get(key), f'{where}.{key}' if where else key)
        return out
    return [] if expected == actual else [f'{where}: arch/settings.json records {json.dumps(expected)}, in effect '
                                          f'{json.dumps(actual)}']


def compiler_findings(expected: dict, targets: list[dict]) -> list[str]:
    """One finding per difference, naming every target it applies to."""
    grouped: dict[tuple, list[str]] = {}
    for target in targets:
        recorded = expected.get(target['profile'], {}).get(target['kind'])
        if recorded is None:
            what = f'arch/settings.json records no compiler arguments for {target["kind"]} targets'
        elif recorded == target['args']:
            continue
        else:
            added = [a for a in target['args'] if a not in recorded]
            missing = [a for a in recorded if a not in target['args']]
            parts = ([f'in effect also {" ".join(added)}'] if added else []) + \
                    ([f'missing {" ".join(missing)}'] if missing else [])
            what = '; '.join(parts) or 'the same arguments in another order (a later lint level wins)'
        grouped.setdefault((target['profile'], target['kind'], what), []).append(target['where'])
    return [f'[protected-enforcement] compiler arguments ({kind}, {profile} profile): {what}. Targets: '
            f'{", ".join(sorted(set(where)))}. {FIX}' for (profile, kind, what), where in grouped.items()]


def codeowners_rules() -> list[list[str]]:
    path = ROOT / 'CODEOWNERS'
    # An inline `#` starts a comment, which isn't an owner.
    lines = [re.sub(r'(^|\s)#.*$', '', line).strip() for line in path.read_text().splitlines()] if path.is_file() else []
    return [line.split() for line in lines if line]


def codeowners_paths() -> list[str]:
    return [rule[0] for rule in codeowners_rules() if owned(rule)]


def owned(rule: list[str]) -> bool:
    """GitHub owners are @user, @org/team or an email address; anything else names no one."""
    return any(OWNER.match(owner) for owner in rule[1:])


def codeowners_findings(expected: list[str]) -> list[str]:
    out = [f'[protected-enforcement] {other}: GitHub reads this CODEOWNERS before the root one. Keep code owners only in '
           f'/CODEOWNERS. {FIX}' for other in ('.github/CODEOWNERS', 'docs/CODEOWNERS') if (ROOT / other).exists()]
    # A pattern with no owner removes ownership from what it matches, so every rule must name one (an @ handle or an
    # email address: GitHub ignores any other word).
    out += [f'[protected-enforcement] CODEOWNERS: `{rule[0]}` has no owner, which removes code-owner review from what '
            f'it matches. {FIX}' for rule in codeowners_rules() if not owned(rule)]
    covered = set(codeowners_paths())
    missing = [p for p in expected if p not in covered]
    if missing:
        out.append(f'[protected-enforcement] CODEOWNERS: no code owner for {", ".join(missing)}. Every enforcement '
                   f'path needs one. {FIX}')
    return out


def findings() -> list[str]:
    expected = json.loads(RECORD.read_text())
    found = effective()
    out = compiler_findings(expected['compiler'], found['targets'])
    for profile in sorted(expected['compiler']):
        missing = [shown for target, shown in sorted(found['listed'].items())
                   if target not in found['built'].get(profile, set())]
        if missing:
            out.append(f'[protected-enforcement] compiler arguments ({profile} profile): cargo never compiled '
                       f'{", ".join(missing)} (`required-features`, say), so no gate checks or tests it. Remove what '
                       f'leaves it out. {FIX}')
    for section in ('clippy', 'rustdoc', 'cargo', 'deny', 'toolchain'):
        out += [f'[protected-enforcement] {section} {d}. {FIX}'
                for d in differences(expected[section], found[section], '')]
    return out + codeowners_findings(expected['codeowners'])


def record() -> None:
    found = effective()
    kinds, differ = by_kind(found['targets'])
    if differ:
        sys.exit(f'Not recorded: these targets\' compiler arguments differ from others of their kind: {", ".join(differ)}')
    RECORD.write_text(json.dumps({
        'about': 'The enforcement settings in effect, recorded by `python3 scripts/settings.py record` (protected). The '
                 'settings gate fails when what cargo, rustc, Clippy, rustdoc and cargo-deny will use differs from this, '
                 'or when CODEOWNERS stops covering a path listed here.',
        'compiler': kinds, **{k: found[k] for k in ('clippy', 'rustdoc', 'cargo', 'deny', 'toolchain')},
        'codeowners': codeowners_paths(),
    }, indent=1) + '\n')
    print(f'recorded {RECORD.relative_to(ROOT)}')


if __name__ == '__main__':
    if sys.argv[1:2] == ['--wrap']:
        wrap(sys.argv[2:])
    if sys.argv[1:] == ['record']:
        record()
        sys.exit(0)
    if sys.argv[1:]:
        sys.exit(__doc__)
    problems = findings()
    shown = problems[:30] + ([f'... and {len(problems) - 30} more'] if len(problems) > 30 else [])
    print('\n'.join(shown) if problems else 'settings: every enforcement setting is as recorded')
    sys.exit(1 if problems else 0)
