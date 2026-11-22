"""Package the desktop app with electron-builder for each platform, then prove each package runs.

  1. build the app (scripts/build.py) and stage it alone: its bundled code and a package.json, no node_modules
  2. electron-builder `dir` for each target, from the locked Electron (another platform's binary is downloaded and
     checked against the locked package's checksums.json, scripts/tools.py)
  3. archive each: a zip made by ditto for macOS (keeps the bundle's symlinks), a zip for Windows, a tar.gz for Linux
  4. the verify gate's journeys and checks against the Apple silicon package ($BSTACK_PACKAGED_APP); evidence in
     .build/evidence/mac-arm64/. The Intel macOS package gets scripts/smoke.mjs here, under Rosetta (whose first
     launch translates Electron and is too slow for a journey's time limit); the Windows and Linux packages get it on
     those systems (CI runs it).

Targets: mac-arm64 (default), mac-x64, win-x64, linux-x64; --all for every one.

Signing (macOS): with $CSC_LINK (a .p12 Developer ID Application certificate, or its base64) and $CSC_KEY_PASSWORD
set, electron-builder signs the app with the hardened runtime; with $APPLE_ID, $APPLE_APP_SPECIFIC_PASSWORD and
$APPLE_TEAM_ID also set, it notarizes it. Without them the app is unsigned. Windows and Linux packages are unsigned.

Output: .build/package/<name>-<target>.(zip|tar.gz), and each unpacked app under .build/package/out/.

Usage: python3 scripts/package.py [--all | TARGET ...] [--no-journeys]
"""
from pathlib import Path
import json
import os
import shutil
import subprocess
import sys
import tarfile
import zipfile

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build import DIST, build  # noqa: E402
from tools import electron_dist, install, node_env  # noqa: E402
import verify  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / '.build/package'
# target: (electron-builder platform flag, arch flag, Electron release name, unpacked folder, executable in it)
TARGETS = {
    'mac-arm64': ('--mac', '--arm64', None, 'mac-arm64', '{name}.app/Contents/MacOS/{name}'),
    'mac-x64': ('--mac', '--x64', 'darwin-x64', 'mac', '{name}.app/Contents/MacOS/{name}'),
    'win-x64': ('--win', '--x64', 'win32-x64', 'win-unpacked', '{name}.exe'),
    'linux-x64': ('--linux', '--x64', 'linux-x64', 'linux-unpacked', '{name}'),
}
SIGNING = ('CSC_LINK', 'CSC_KEY_PASSWORD')
NOTARIZING = ('APPLE_ID', 'APPLE_APP_SPECIFIC_PASSWORD', 'APPLE_TEAM_ID')


def run(cmd: list[str], env: dict, cwd: Path = ROOT) -> str:
    proc = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True)
    if proc.returncode != 0:
        sys.exit(f'`{" ".join(cmd[:3])} ...` failed:\n{(proc.stdout + proc.stderr).strip()[-4000:]}')
    return proc.stdout + proc.stderr


def stage(name: str) -> Path:
    shutil.rmtree(OUT, ignore_errors=True)
    folder = OUT / 'stage'
    shutil.copytree(DIST, folder / 'dist')
    (folder / 'package.json').write_text(json.dumps({'name': name, 'productName': name, 'version': '0.0.0',
                                                     'main': 'dist/main.cjs', 'private': True}, indent=2))
    return folder


def config(name: str, target: str) -> dict:
    electron = ROOT / 'apps/desktop/node_modules/electron'
    release = TARGETS[target][2]
    signed = all(os.environ.get(key) for key in SIGNING)
    mac: dict = {'target': ['dir']}
    if signed:
        mac |= {'hardenedRuntime': True, 'notarize': all(os.environ.get(key) for key in NOTARIZING)}
    else:
        mac['identity'] = None
    return {
        'appId': f'dev.bstack.{name}', 'productName': name, 'executableName': name,
        'electronVersion': json.loads((electron / 'package.json').read_text())['version'],
        'electronDist': str(electron_dist(release) if release else electron / 'dist'),
        'npmRebuild': False, 'files': ['dist/**/*', 'package.json'], 'directories': {'output': str(OUT / 'out')},
        'mac': mac,
        # No signing tool for Windows on a Mac: leave the executable as electron-builder copies it.
        'win': {'target': ['dir'], 'signAndEditExecutable': False},
        'linux': {'target': ['dir']},
    }


def archive(name: str, target: str) -> Path:
    unpacked = OUT / 'out' / TARGETS[target][3]
    if target.startswith('mac'):
        path = OUT / f'{name}-{target}.zip'
        run(['ditto', '-c', '-k', '--norsrc', '--keepParent', str(unpacked / f'{name}.app'), str(path)], os.environ.copy())
    elif target.startswith('win'):
        path = OUT / f'{name}-{target}.zip'
        with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as zipped:
            for file in sorted(unpacked.rglob('*')):
                zipped.write(file, Path(name) / file.relative_to(unpacked))
    else:
        path = OUT / f'{name}-{target}.tar.gz'
        with tarfile.open(path, 'w:gz') as tar:  # keeps the executable's permissions
            tar.add(unpacked, arcname=name)
    return path


def package(env: dict, targets: list[str]) -> dict[str, Path]:
    failed = build(env)
    if failed:
        sys.exit(failed)
    name = json.loads((ROOT / 'package.json').read_text())['name']
    folder = stage(name)
    builder = ROOT / 'apps/desktop/node_modules/.bin/electron-builder'
    signed = all(env.get(key) for key in SIGNING)
    executables = {}
    for target in targets:
        platform, arch, _, unpacked, executable = TARGETS[target]
        settings = OUT / f'electron-builder-{target}.json'
        settings.write_text(json.dumps(config(name, target), indent=2))
        output = run([str(builder), platform, arch, '--projectDir', str(folder), '--config', str(settings)],
                     {**env, 'CSC_IDENTITY_AUTO_DISCOVERY': 'true' if signed and target.startswith('mac') else 'false'})
        skips = ('skipped macOS application code signing', 'code signing will be skipped')
        if signed and target.startswith('mac') and any(skip in output for skip in skips):
            # electron-builder skips an identity macOS doesn't trust and still succeeds: a signed build was asked for.
            reason = next(line.strip() for line in output.splitlines() if any(skip in line for skip in skips))
            sys.exit(f'{target}: $CSC_LINK is set but the app wasn\'t signed:\n{reason}')
        path = OUT / 'out' / unpacked / executable.format(name=name)
        if not path.is_file():
            sys.exit(f'electron-builder left no {path}')
        if target.startswith('mac') and signed:
            app = OUT / 'out' / unpacked / f'{name}.app'
            proc = subprocess.run(['codesign', '--verify', '--deep', '--strict', str(app)], capture_output=True, text=True)
            if proc.returncode != 0:
                said = [line.strip() for line in output.splitlines() if any(w in line.lower() for w in ('sign', 'identity', 'keychain'))]
                sys.exit(f'{target}: the app isn\'t validly signed: {proc.stderr.strip()}\nelectron-builder said:\n' + '\n'.join(said))
        print(f'packaged {target}: {archive(name, target)}', flush=True)
        executables[target] = path
    return executables


def journeys(env: dict, target: str, executable: Path) -> list[str]:
    """The verify gate's checks (map, every mapped journey ran once and passed, screenshots) on a packaged app."""
    verify.EVIDENCE = ROOT / '.build/evidence' / target
    shutil.rmtree(verify.EVIDENCE, ignore_errors=True)
    features, errors = verify.verified_map()
    if errors:
        return errors
    verify.EVIDENCE.mkdir(parents=True)
    return verify.run({**env, 'BSTACK_PACKAGED_APP': str(executable), 'BSTACK_EVIDENCE': str(verify.EVIDENCE)},
                      features, build_first=False)


if __name__ == '__main__':
    args = [a for a in sys.argv[1:] if a != '--no-journeys']
    chosen = list(TARGETS) if '--all' in args else [a for a in args if a != '--all'] or ['mac-arm64']
    unknown = [t for t in chosen if t not in TARGETS]
    if unknown:
        sys.exit(f'unknown target {", ".join(unknown)}; targets: {", ".join(TARGETS)}\n\n{__doc__}')
    env = node_env()
    install(env)
    executables = package(env, chosen)
    if '--no-journeys' not in sys.argv[1:]:
        for target, executable in executables.items():
            if target == 'mac-x64':
                shutil.rmtree(ROOT / '.build/evidence/mac-x64', ignore_errors=True)  # only this run's screenshots
                proc = subprocess.run(['node', 'scripts/smoke.mjs', str(executable), str(ROOT / 'apps/desktop'),
                                       str(ROOT / '.build/evidence/mac-x64')], cwd=ROOT, env=env, capture_output=True, text=True)
                if proc.returncode != 0:
                    sys.exit(f'The mac-x64 package failed its smoke test:\n{(proc.stdout + proc.stderr).strip()[-3000:]}')
                print(f'mac-x64 (Rosetta): {proc.stdout.strip()}')
                continue
            if not target.startswith('mac'):
                print(f'{target}: prove it on that system with scripts/smoke.mjs (CI does)')
                continue
            errors = journeys(env, target, executable)
            if errors:
                sys.exit('\n'.join(errors + [f'The {target} package failed its journeys.']))
            print(f'{target}: every journey passed against the package. Evidence: {verify.EVIDENCE / "evidence.md"}')
