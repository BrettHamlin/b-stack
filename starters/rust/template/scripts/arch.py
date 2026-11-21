"""The arch gate: the crate graph and manifests against the module shape (arch/shape.toml), then every crate's source
through arch/checker (a syn parser). Prints `[rule-id] where: message` per finding; exits 1 if there are any.

Graph and manifests (from `cargo metadata` and each crate's Cargo.toml):
  module-boundaries      every crate folder is a workspace member in a role's folder; each dependency on another
                         crate is one its role may use; only the composition root has a binary
  allowed-dependencies   a third-party crate is on the role's `external` list (deny.toml checks sources and licenses)
  no-suppressions        each crate inherits the workspace lints exactly; no build scripts or proc-macro crates
  tests-always-run       no target turns its tests off (test = false, harness = false, autotests = false,
                         required-features, ...)
  no-io-in-logic         a no_std crate's library root is src/lib.rs, where the checker requires #![no_std]
Source (arch/checker): lint-level attributes, `static` and thread_local!, std in no_std crates, #[ignore], and
macro_rules!/include!/#[path] that hide code from the parse.

Usage: python3 scripts/arch.py
"""
from fnmatch import fnmatch
from pathlib import Path
import json
import os
import subprocess
import sys
import tomllib

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tools import rust_env  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
TEST_SWITCHES = ('autotests', 'autobins', 'autoexamples', 'autobenches', 'autolib')


def in_folder(rel: Path, pattern: str) -> bool:
    parts = pattern.split('/')
    return len(rel.parts) == len(parts) and all(fnmatch(p, q) for p, q in zip(rel.parts, parts))


def role_of(rel: Path, roles: dict) -> str | None:
    return next((name for name, role in roles.items() if in_folder(rel, role['path'])), None)


def crate_folders() -> list[Path]:
    """Every folder under crates/ with a Cargo.toml, member or not."""
    found = []
    for manifest in (ROOT / 'crates').rglob('Cargo.toml'):
        rel = manifest.parent.relative_to(ROOT)
        if not any(part in ('target', '.build') or part.startswith('.') for part in rel.parts):
            found.append(rel)
    return sorted(found)


def graph_findings(env: dict, roles: dict) -> tuple[list[str], dict[Path, str]]:
    out: list[str] = []
    proc = subprocess.run(['cargo', 'metadata', '--format-version', '1', '--no-deps'], cwd=ROOT, env=env,
                          capture_output=True, text=True)
    if proc.returncode != 0:
        return [f'[arch] cargo metadata failed:\n{proc.stderr.strip()}'], {}
    metadata = json.loads(proc.stdout)
    members = {Path(p['manifest_path']).parent.resolve(): p for p in metadata['packages']}
    member_roles: dict[Path, str] = {}

    for rel in crate_folders():
        if (ROOT / rel).resolve() not in members:
            out.append(f'[module-boundaries] {rel}: not a workspace member, so no gate builds or checks it. Crates go in '
                       'the module shape\'s folders (arch/shape.toml), which the root Cargo.toml includes; never edit those.')
    for folder, package in sorted(members.items()):
        rel = folder.relative_to(ROOT.resolve()) if folder.is_relative_to(ROOT.resolve()) else folder
        role = role_of(Path(rel), roles)
        if role is None:
            out.append(f'[module-boundaries] {rel}: not in any role\'s folder in arch/shape.toml '
                       f'({", ".join(r["path"] for r in roles.values())}). Move the crate into one; if none fits, stop and report.')
            continue
        member_roles[folder] = role

    for folder, role in member_roles.items():
        package, shape = members[folder], roles[role]
        rel = folder.relative_to(ROOT.resolve())
        manifest = tomllib.loads((folder / 'Cargo.toml').read_text())
        if manifest.get('lints') != {'workspace': True}:
            out.append(f'[no-suppressions] {rel}/Cargo.toml: [lints] must be exactly `workspace = true`, so the crate '
                       'gets every workspace lint at its level. Fix the code the lint objects to; never change lint levels.')
        for target in package['targets']:
            kinds = set(target['kind'])
            if kinds & {'custom-build', 'proc-macro'}:
                what = 'a build script' if 'custom-build' in kinds else 'a proc-macro crate'
                out.append(f'[no-suppressions] {rel}: {what} runs code at build time that no gate sees. Write the code '
                           'in the crate itself; if that\'s impossible, stop and report.')
            if 'bin' in kinds and not shape.get('binary'):
                out.append(f'[module-boundaries] {rel}: binary `{target["name"]}` in a {role} crate. Only the composition '
                           'root (the app crate) has a binary; it wires real services into the features.')
            if kinds & {'lib', 'rlib', 'bin', 'test'} and not target.get('test', True):
                out.append(f'[tests-always-run] {rel}: `test = false` on {target["name"]} leaves its tests out of the '
                           'tests gate. Remove it; every test runs.')
            if 'lib' in kinds and not target.get('doctest', True):
                out.append(f'[tests-always-run] {rel}: `doctest = false` leaves the doc tests out of the tests gate.')
            if 'lib' in kinds and shape.get('no_std') and Path(target['src_path']).resolve() != folder / 'src/lib.rs':
                out.append(f'[no-io-in-logic] {rel}/Cargo.toml: the library\'s root is {os.path.relpath(target["src_path"], folder)}, but a no_std '
                           'crate\'s root must be src/lib.rs, where `#![no_std]` is checked. Remove the [lib] `path`.')
        tables = [manifest.get('lib', {}), *[t for kind in ('bin', 'test', 'bench', 'example') for t in manifest.get(kind, [])]]
        for table in tables:
            if table.get('harness') is False:
                out.append(f'[tests-always-run] {rel}/Cargo.toml: `harness = false` on {table.get("name", "a target")} '
                           'replaces the test runner, so its tests may never run. Use #[test] functions.')
            if 'required-features' in table:
                out.append(f'[tests-always-run] {rel}/Cargo.toml: `required-features` on {table.get("name", "a target")} '
                           'skips it unless those features are on, and the gates build with default features, so its '
                           'tests may never run. Remove it.')
        for switch in TEST_SWITCHES:
            if manifest.get('package', {}).get(switch) is False:
                out.append(f'[tests-always-run] {rel}/Cargo.toml: `{switch} = false` stops Cargo finding targets, so '
                           'their tests never run. Remove it.')
        for dep in package['dependencies']:
            name = dep.get('rename') or dep['name']
            if dep.get('path'):
                target_dir = Path(dep['path']).resolve()
                target_role = member_roles.get(target_dir)
                if target_dir not in members:
                    out.append(f'[module-boundaries] {rel}: depends on `{name}` at {dep["path"]}, which isn\'t a crate in '
                               'this workspace. Code lives in the workspace\'s crates.')
                elif target_role is not None and target_role not in shape['may_use']:
                    allowed = ', '.join(shape['may_use']) or 'no other crates'
                    out.append(f'[module-boundaries] {rel}: a {role} crate may not depend on `{name}` (a {target_role} '
                               f'crate). {role} may use: {allowed}. Pass what you need in through a trait defined in a '
                               'crate this one may use; never edit arch/shape.toml. If that can\'t work, stop and report.')
            elif dep['name'] not in shape.get('external', []):
                out.append(f'[allowed-dependencies] {rel}: third-party crate `{dep["name"]}` isn\'t allowed in a {role} '
                           'crate. Adding one needs the owner (arch/shape.toml): write it without the '
                           'crate, or stop and report which crate you need and why.')
    return out, member_roles


def build_time_code(env: dict) -> list[str]:
    """Workspace crates with code Cargo runs while building (build scripts, proc macros). check.py runs this before
    any gate that compiles, so that code never runs: it is reported here, by the arch gate, instead."""
    proc = subprocess.run(['cargo', 'metadata', '--format-version', '1', '--no-deps'], cwd=ROOT, env=env,
                          capture_output=True, text=True)
    if proc.returncode != 0:
        return [f'[arch] cargo metadata failed:\n{proc.stderr.strip()}']
    found = []
    for package in json.loads(proc.stdout)['packages']:
        folder = Path(package['manifest_path']).parent.resolve()
        rel = folder.relative_to(ROOT.resolve()) if folder.is_relative_to(ROOT.resolve()) else folder
        for target in package['targets']:
            if set(target['kind']) & {'custom-build', 'proc-macro'}:
                what = 'a build script' if 'custom-build' in target['kind'] else 'a proc-macro crate'
                found.append(f'[no-suppressions] {rel}: not compiled, because {what} would run at build time. '
                             'The arch gate says how to fix it.')
    return found


def source_findings(env: dict, roles: dict, member_roles: dict[Path, str]) -> list[str]:
    build_env = {**env, 'RUSTFLAGS': '', 'CARGO_TARGET_DIR': str(ROOT / '.build/arch')}
    build = subprocess.run(['cargo', 'build', '--quiet', '--locked', '--manifest-path', 'arch/checker/Cargo.toml'],
                           cwd=ROOT, env=build_env, capture_output=True, text=True)
    if build.returncode != 0:
        return [f'[arch] the checker didn\'t build:\n{build.stderr.strip()}']
    args = [f'{folder.relative_to(ROOT.resolve())}={"no_std" if roles[role].get("no_std") else "std"}'
            for folder, role in sorted(member_roles.items())]
    proc = subprocess.run([str(ROOT / '.build/arch/debug/arch-checker'), *args], cwd=ROOT, capture_output=True, text=True)
    lines = []
    for line in proc.stdout.splitlines():
        where, _, rest = line.partition(': [')
        rule, _, message = rest.partition('] ')
        lines.append(f'[{rule}] {where}: {message}')
    if proc.returncode not in (0, 1) or (proc.returncode == 1 and not lines):
        lines.append(f'[arch] the checker failed: {proc.stderr.strip()}')
    return lines


def findings() -> list[str]:
    env = rust_env()
    roles = tomllib.loads((ROOT / 'arch/shape.toml').read_text())['roles']
    graph, member_roles = graph_findings(env, roles)
    return graph + source_findings(env, roles, member_roles)


if __name__ == '__main__':
    os.chdir(ROOT)
    found = findings()
    print('\n'.join(found) if found else 'arch: no findings')
    sys.exit(1 if found else 0)
