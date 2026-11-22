"""The deps gate: every package in the dependency tree comes from the npm registry with an integrity hash, and has an
allowed license. Which third-party packages each role may use is the arch gate's job (arch/shape.json).

  sources    every package in pnpm-lock.yaml resolves to the registry with an integrity hash: no git, tarball URL or
             local folder dependencies (workspace packages are linked, not resolved)
  licenses   every installed package's own license field: shipped dependencies (each package's `dependencies`, all
             the way down) have a permissive license;
             build and test tools (devDependencies) may also be MPL-2.0, which never ships in the app

Usage: python3 scripts/deps.py
"""
from pathlib import Path
import json
import re
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tools import install, node_env  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
PERMISSIVE = {'MIT', 'Apache-2.0', 'BSD-2-Clause', 'BSD-3-Clause', 'ISC', '0BSD', 'BlueOak-1.0.0', 'CC0-1.0',
              'Unlicense', 'Zlib'}
TOOLS_ALSO = {'MPL-2.0'}


def source_findings() -> list[str]:
    """Every `resolution` in the lockfile must be exactly a registry integrity hash, as pnpm writes it. Fails closed: a
    resolution written any other way (a tarball URL, git, a folder, a block mapping, a quoted key) is a finding."""
    out = []
    lines = (ROOT / 'pnpm-lock.yaml').read_text().splitlines()
    for number, line in enumerate(lines, 1):
        if not re.search(r'''['"]?resolution['"]?\s*:''', line):
            continue
        if not re.fullmatch(r'    resolution: \{integrity: sha512-[A-Za-z0-9+/=]+\}', line):
            name = lines[number - 2].strip().rstrip(':') if number > 1 else '?'
            out.append(f'[allowed-dependencies] pnpm-lock.yaml:{number}: {name} {line.strip()}. Packages come only from '
                       'the npm registry with an integrity hash: no git, URL or folder dependencies.')
    if not any('resolution: {integrity:' in line for line in lines):
        out.append('[allowed-dependencies] pnpm-lock.yaml: no registry packages found; is the lockfile valid?')
    return out


def licenses(env: dict, prod: bool) -> dict[str, set[tuple[str, str]]]:
    """License -> installed packages (name, path), read from each installed package's package.json (`pnpm list`). Workspace packages are
    the app's own and are left out; everything else is in, registry or not."""
    proc = subprocess.run(['pnpm', 'list', '--recursive', '--json', '--depth', 'Infinity', *(['--prod'] if prod else [])],
                          cwd=ROOT, env=env, capture_output=True, text=True)
    if proc.returncode != 0:
        sys.exit(f'pnpm list failed:\n{(proc.stdout + proc.stderr).strip()[-2000:]}')
    found: dict[str, set[tuple[str, str]]] = {}
    seen: set[str] = set()

    def walk(node: dict) -> None:
        sections = ('dependencies', 'optionalDependencies') + (() if prod else ('devDependencies',))
        children = [item for section in sections for item in (node.get(section) or {}).items()]
        for name, dependency in children:
            path = dependency.get('path', '')
            if path in seen or str(dependency.get('version', '')).startswith('link:'):
                continue
            if not (Path(path) / 'package.json').is_file():
                continue  # an optional package for another platform, not installed here
            seen.add(path)
            manifest = json.loads((Path(path) / 'package.json').read_text()) if path else {}
            license = manifest.get('license')
            if not isinstance(license, str):
                legacy = manifest.get('licenses')
                license = ' OR '.join(l.get('type', '?') for l in legacy) if isinstance(legacy, list) else 'none'
            found.setdefault(license, set()).add((name, path))
            walk(dependency)

    for importer in json.loads(proc.stdout or '[]'):
        walk(importer)
    return found


def license_findings(env: dict) -> list[str]:
    out = []
    shipped = licenses(env, prod=True)
    for license, packages in sorted(shipped.items()):
        if license not in PERMISSIVE:
            names = sorted({name for name, _ in packages})
            out.append(f'[allowed-dependencies] {", ".join(names)}: license {license} isn\'t allowed in shipped '
                       f'dependencies (allowed: {", ".join(sorted(PERMISSIVE))}). Stop and report: the owner decides.')
    # Each installed copy by itself: a tool's version of a package isn't covered by a shipped version's license.
    shipped_paths = {path for packages in shipped.values() for _, path in packages}
    for license, packages in sorted(licenses(env, prod=False).items()):
        tools = sorted({name for name, path in packages if path not in shipped_paths})
        if tools and license not in PERMISSIVE | TOOLS_ALSO:
            out.append(f'[allowed-dependencies] {", ".join(tools)}: license {license} isn\'t allowed, even for build '
                       f'and test tools (allowed: {", ".join(sorted(PERMISSIVE | TOOLS_ALSO))}). Stop and report.')
    return out


if __name__ == '__main__':
    env = node_env()
    install(env)
    found = source_findings() + license_findings(env)
    print('\n'.join(found) if found else 'deps: every package is from the registry with an allowed license')
    sys.exit(1 if found else 0)
