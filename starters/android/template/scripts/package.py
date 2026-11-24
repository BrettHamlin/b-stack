"""Build the shipped app for release, and prove the release build runs.

  1. :app:bundleRelease and :app:assembleRelease: R8 shrinks and obfuscates the code and drops unused resources
     (build-logic), and both are signed with the upload key named by the environment:
       BSTACK_UPLOAD_KEYSTORE (a .jks or .p12 file), BSTACK_UPLOAD_KEYSTORE_PASSWORD, BSTACK_UPLOAD_KEY_ALIAS,
       BSTACK_UPLOAD_KEY_PASSWORD.
     Without them, a throwaway key in .build/package/ signs the build so it can be installed and tested; its outputs
     are named `-test-signed` and must never be uploaded.
  2. The signatures are checked (apksigner for the APK, jarsigner for the bundle); a build that comes out unsigned
     fails.
  3. The release APK is installed on the emulator with no data and launched from its icon's intent (verify.py's smoke
     launch): code R8 broke usually crashes here, and nowhere else before users see it.
Outputs in .build/package/out/, named starter-<versionName>-<versionCode>: .aab (for Play), .apk, -mapping.txt (to
read obfuscated crash reports; keep it with each upload). Evidence: .build/evidence/release/launched.png.

Usage: python3 scripts/package.py [--version-name 0.2.0 --version-code 2]
"""
from pathlib import Path
import argparse
import json
import os
import shutil
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from emulator import boot, in_use  # noqa: E402
from tools import android_env, gradle_command, sdk_packages  # noqa: E402
from verify import EVIDENCE, app_id, smoke  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / '.build/package/out'
KEYS = ('BSTACK_UPLOAD_KEYSTORE', 'BSTACK_UPLOAD_KEYSTORE_PASSWORD', 'BSTACK_UPLOAD_KEY_ALIAS', 'BSTACK_UPLOAD_KEY_PASSWORD')


def throwaway_key(env: dict) -> dict:
    """A key for test builds only, made once per checkout."""
    store = ROOT / '.build/package/test-upload.jks'
    if not store.is_file():
        store.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run([str(Path(env['JAVA_HOME']) / 'bin/keytool'), '-genkeypair', '-keystore', str(store),
                        '-storepass', 'test-only', '-keypass', 'test-only', '-alias', 'test', '-keyalg', 'RSA',
                        '-keysize', '2048', '-validity', '3650', '-dname', 'CN=Test build not for upload', '-noprompt'],
                       check=True, capture_output=True)
    return dict(zip(KEYS, (str(store), 'test-only', 'test', 'test-only')))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--version-name')
    parser.add_argument('--version-code', type=int)
    args = parser.parse_args()
    env = android_env()
    given = [k for k in KEYS if os.environ.get(k)]
    if given and len(given) != len(KEYS):
        sys.exit(f'Signing needs all of {", ".join(KEYS)}; only {", ".join(given)} set.')
    test_signed = not given
    signing = throwaway_key(env) if test_signed else {k: os.environ[k] for k in KEYS}
    # A path from where package.py was run, not from app/ (where Gradle would resolve a relative one).
    signing['BSTACK_UPLOAD_KEYSTORE'] = str(Path(signing['BSTACK_UPLOAD_KEYSTORE']).resolve())
    props = ([f'-Pbstack.versionName={args.version_name}'] if args.version_name else []) + \
            ([f'-Pbstack.versionCode={args.version_code}'] if args.version_code else [])
    # Only Gradle sees the key's passwords; the emulator package.py may boot doesn't.
    build = subprocess.run(gradle_command('-q', *props, ':app:bundleRelease', ':app:assembleRelease'), cwd=ROOT,
                           env={**env, **signing}, capture_output=True, text=True)
    if build.returncode != 0:
        print((build.stdout + build.stderr)[-4000:])
        return 1
    outputs = ROOT / '.build/gradle/app/outputs'
    apk, aab = outputs / 'apk/release/app-release.apk', outputs / 'bundle/release/app-release.aab'
    build_tools = next(p.split(';')[1] for p in sdk_packages() if p.startswith('build-tools;'))
    apksigner = Path(env['ANDROID_HOME']) / 'build-tools' / build_tools / 'apksigner'
    problems = []
    if not apk.is_file() or subprocess.run([str(apksigner), 'verify', str(apk)], env=env, capture_output=True).returncode:
        problems.append(f'{apk.name} isn\'t signed (apksigner verify failed).')
    jarsigner = subprocess.run([str(Path(env['JAVA_HOME']) / 'bin/jarsigner'), '-verify', str(aab)], env=env,
                               capture_output=True, text=True)
    if not aab.is_file() or 'jar verified' not in jarsigner.stdout:
        problems.append(f'{aab.name} isn\'t signed (jarsigner -verify: {jarsigner.stdout.strip()[-300:]}).')
    if problems:
        print('\n'.join(problems))
        return 1
    folder = EVIDENCE.parent / 'release'
    shutil.rmtree(folder, ignore_errors=True)
    with in_use(f'package.py in {ROOT}'):
        failed = smoke(env, boot(env), 'release', folder)
    if failed:
        print('\n'.join(failed).replace('[verified-features] ', '[release] '))
        return 1
    built = json.loads((outputs / 'apk/release/output-metadata.json').read_text())['elements'][0]
    version = f'{built["versionName"]}-{built["versionCode"]}'
    name = f'starter-{version}' + ('-test-signed' if test_signed else '')
    OUT.mkdir(parents=True, exist_ok=True)
    shutil.copy(aab, OUT / f'{name}.aab')
    shutil.copy(apk, OUT / f'{name}.apk')
    shutil.copy(outputs / 'mapping/release/mapping.txt', OUT / f'{name}-mapping.txt')
    print(f'package: {app_id("app", "release")} {version}, signed{" with a throwaway test key (not for upload)" if test_signed else ""}; '
          f'the release build started and stayed up on the emulator. Outputs: {OUT}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
