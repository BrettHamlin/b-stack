"""Build the app for release, and prove the release build runs.

  1. `cargo build --release --locked --package app`: the release profile (optimized, overflow checks kept, debug
     assertions off), with the pinned toolchain and the lockfile as it is (a build that would change it fails).
  2. The binary is copied out and checked: it is an executable file, and its SHA-256 matches what cargo built.
  3. The copy is launched once, the smoke run in crates/app/smoke.toml (its arguments, a new, empty data folder, the
     output it must print and exit 0), with a 60-second limit.
Outputs in .build/package/out/, named by the app's version (crates/app/Cargo.toml) and this machine's target:
app-<version>-<target> and app-<version>-<target>.sha256. They are staged in a folder of their own and moved there
only once every check passes. The release gate (check.py) runs every journey against the same profile.

Usage: python3 scripts/package.py
"""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import tomllib

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tools import rust_env  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / '.build/package/out'
SMOKE = ROOT / 'crates/app/smoke.toml'


def smoke(binary: Path, scratch: Path) -> list[str]:
    spec = tomllib.loads(SMOKE.read_text())
    data = scratch / 'smoke-data'
    data.mkdir()
    args = [a.replace('{data}', str(data)) for a in spec['args']]
    try:
        proc = subprocess.run([str(binary), *args], cwd=scratch, capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired:
        return [f'[release] the release build didn\'t finish its smoke run ({SMOKE.relative_to(ROOT)}) in 60 s.']
    if proc.returncode != 0 or proc.stdout != spec['stdout']:
        return [f'[release] the release build\'s smoke run ({SMOKE.relative_to(ROOT)}) exited {proc.returncode} '
                f'printing {proc.stdout!r} (expected 0 and {spec["stdout"]!r}).\n{proc.stderr.strip()[-2000:]}']
    return []


def main() -> int:
    if sys.argv[1:]:
        sys.exit(__doc__)
    env = rust_env()
    build = subprocess.run(['cargo', 'build', '--release', '--locked', '--package', 'app'], cwd=ROOT, env=env,
                           capture_output=True, text=True)
    if build.returncode != 0:
        print(build.stderr[-4000:])
        return 1
    meta = json.loads(subprocess.run(['cargo', 'metadata', '--format-version', '1', '--no-deps'], cwd=ROOT, env=env,
                                     capture_output=True, text=True, check=True).stdout)
    version = next(p['version'] for p in meta['packages'] if p['name'] == 'app')
    host = next(line.split(': ', 1)[1] for line in subprocess.run(['rustc', '-vV'], cwd=ROOT, env=env,
                capture_output=True, text=True, check=True).stdout.splitlines() if line.startswith('host: '))
    built = Path(env['CARGO_TARGET_DIR']) / 'release/app'
    name = f'app-{version}-{host}'
    (ROOT / '.build').mkdir(exist_ok=True)  # rust_env() linked it into the cache folder, if one is configured
    staging = Path(tempfile.mkdtemp(dir=ROOT / '.build', prefix='package-'))
    try:
        staged = staging / name
        shutil.copy2(built, staged)
        digest = hashlib.sha256(staged.read_bytes()).hexdigest()
        problems = []
        if not os.access(staged, os.X_OK):
            problems.append(f'[release] {name} isn\'t executable.')
        if digest != hashlib.sha256(built.read_bytes()).hexdigest():
            problems.append(f'[release] {name} differs from the binary cargo built (changed while being copied?).')
        problems = problems or smoke(staged, staging)
        if problems:
            print('\n'.join(problems))
            return 1
        (staging / f'{name}.sha256').write_text(f'{digest}  {name}\n')
        OUT.mkdir(parents=True, exist_ok=True)
        for item in (staged, staging / f'{name}.sha256'):
            shutil.move(item, OUT / item.name)
    finally:
        shutil.rmtree(staging, ignore_errors=True)
    print(f'package: app {version} for {host}, release build; its smoke run passed. Outputs: {OUT}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
