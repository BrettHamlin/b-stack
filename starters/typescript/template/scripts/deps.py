"""The deps gate: every package in the dependency tree comes from the npm registry with an integrity hash, and has an
allowed license. Which third-party packages each role may use is the arch gate's job (arch/shape.json).

  sources    every package in pnpm-lock.yaml resolves to the registry with an integrity hash: no git, tarball URL or
             local folder dependencies (workspace packages are linked, not resolved)
  licenses   `pnpm licenses list`: shipped dependencies (each package's `dependencies`) have a permissive license;
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
    out = []
    text = (ROOT / 'pnpm-lock.yaml').read_text()
    for match in re.finditer(r"^  '?([^\s:']+)'?:\n    resolution: \{([^}]*)\}", text, re.M):
        name, resolution = match.group(1), match.group(2)
        if not re.fullmatch(r'integrity: sha512-[A-Za-z0-9+/=]+', resolution.strip()):
            out.append(f'[allowed-dependencies] pnpm-lock.yaml: {name} resolves to {{{resolution.strip()}}}. Packages '
                       'come only from the npm registry with an integrity hash: no git, URL or folder dependencies.')
    if not re.search(r'^    resolution: \{integrity:', text, re.M):
        out.append('[allowed-dependencies] pnpm-lock.yaml: no registry packages found; is the lockfile valid?')
    return out


def licenses(env: dict, prod: bool) -> dict[str, list[str]]:
    proc = subprocess.run(['pnpm', 'licenses', 'list', '--json', *(['--prod'] if prod else [])], cwd=ROOT, env=env,
                          capture_output=True, text=True)
    if proc.returncode != 0:
        sys.exit(f'pnpm licenses list failed:\n{(proc.stdout + proc.stderr).strip()[-2000:]}')
    return {license: sorted({p['name'] for p in found}) for license, found in json.loads(proc.stdout or '{}').items()}


def license_findings(env: dict) -> list[str]:
    out = []
    shipped = licenses(env, prod=True)
    for license, names in sorted(shipped.items()):
        if license not in PERMISSIVE:
            out.append(f'[allowed-dependencies] {", ".join(names)}: license {license} isn\'t allowed in shipped '
                       f'dependencies (allowed: {", ".join(sorted(PERMISSIVE))}). Stop and report: the owner decides.')
    shipped_names = {n for names in shipped.values() for n in names}
    for license, names in sorted(licenses(env, prod=False).items()):
        tools = [n for n in names if n not in shipped_names]
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
