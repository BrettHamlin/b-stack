"""Package the desktop app for macOS (Apple silicon) with electron-builder, then run every journey against the
packaged app, so what ships is what was verified.

  1. build the app (scripts/build.py) and stage it alone: its bundled code and a package.json, no node_modules
  2. electron-builder --mac dir, from the Electron the lockfile installed (nothing downloaded), unsigned
  3. zip the .app with ditto, which keeps the bundle's symlinks and permissions
  4. the journeys, launching the packaged app ($BSTACK_PACKAGED_APP); screenshots in .build/evidence/latest/

Output: .build/package/<name>-mac-arm64.zip and the .app beside it. Signing and notarizing need the owner's Apple
Developer ID and aren't done here.

Usage: python3 scripts/package.py [--no-journeys]
"""
from pathlib import Path
import json
import os
import shutil
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from build import DIST, build  # noqa: E402
from tools import install, node_env  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / '.build/package'


def run(cmd: list[str], env: dict, cwd: Path = ROOT) -> None:
    proc = subprocess.run(cmd, cwd=cwd, env=env, capture_output=True, text=True)
    if proc.returncode != 0:
        sys.exit(f'`{" ".join(cmd[:3])} ...` failed:\n{(proc.stdout + proc.stderr).strip()[-4000:]}')


def package(env: dict) -> Path:
    failed = build(env)
    if failed:
        sys.exit(failed)
    name = json.loads((ROOT / 'package.json').read_text())['name']
    electron = ROOT / 'apps/desktop/node_modules/electron'
    version = json.loads((electron / 'package.json').read_text())['version']
    shutil.rmtree(OUT, ignore_errors=True)
    stage = OUT / 'stage'
    shutil.copytree(DIST, stage / 'dist')
    (stage / 'package.json').write_text(json.dumps({'name': name, 'productName': name, 'version': '0.0.0',
                                                    'main': 'dist/main.cjs', 'private': True}, indent=2))
    config = {
        'appId': f'dev.bstack.{name}', 'productName': name, 'electronVersion': version,
        'electronDist': str(electron / 'dist'), 'npmRebuild': False, 'files': ['dist/**/*', 'package.json'],
        'directories': {'output': str(OUT / 'out')}, 'mac': {'target': ['dir'], 'identity': None},
    }
    (OUT / 'electron-builder.json').write_text(json.dumps(config, indent=2))
    builder = ROOT / 'apps/desktop/node_modules/.bin/electron-builder'
    run([str(builder), '--mac', '--arm64', '--projectDir', str(stage), '--config', str(OUT / 'electron-builder.json')],
        {**env, 'CSC_IDENTITY_AUTO_DISCOVERY': 'false'})
    app = OUT / 'out/mac-arm64' / f'{name}.app'
    if not (app / 'Contents/Resources/app.asar').is_file():
        sys.exit(f'electron-builder left no {app}/Contents/Resources/app.asar')
    run(['ditto', '-c', '-k', '--norsrc', '--keepParent', str(app), str(OUT / f'{name}-mac-arm64.zip')], env)
    return app


if __name__ == '__main__':
    env = node_env()
    install(env)
    app = package(env)
    print(f'packaged {app}\nzipped {OUT / (app.stem + "-mac-arm64.zip")}')
    if '--no-journeys' not in sys.argv[1:]:
        shutil.rmtree(ROOT / '.build/evidence/latest', ignore_errors=True)
        binary = app / 'Contents/MacOS' / app.stem
        proc = subprocess.run(['vp', 'test', 'run', '--project', 'journeys'], cwd=ROOT,
                              env={**env, 'BSTACK_PACKAGED_APP': str(binary)}, capture_output=True, text=True)
        print((proc.stdout + proc.stderr).strip()[-3000:])
        if proc.returncode != 0:
            sys.exit('The packaged app failed its journeys.')
        print('every journey passed against the packaged app')
