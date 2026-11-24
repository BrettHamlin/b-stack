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
read obfuscated crash reports; keep it with each upload). Evidence: .build/evidence/package/launched.png.

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
from verify import EVIDENCE, KEYS, smoke, throwaway_key  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / '.build/package/out'
def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--version-name')
    parser.add_argument('--version-code', type=int)
    args = parser.parse_args()
    # The key's settings leave this process's environment, so only the release Gradle run gets them: not the emulator,
    # adb or the signature checks.
    supplied = {k: v for k in KEYS if (v := os.environ.pop(k, ''))}
    if supplied and len(supplied) != len(KEYS):
        sys.exit(f'Signing needs all of {", ".join(KEYS)}; only {", ".join(supplied)} set.')
    env = android_env()
    test_signed = not supplied
    signing = throwaway_key(env) if test_signed else supplied
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
    # Copied out at once, so a release gate run in this checkout meanwhile (which rebuilds the same outputs with the
    # throwaway key) can't change what is checked, launched and kept.
    outputs = ROOT / '.build/gradle/app/outputs'
    built = json.loads((outputs / 'apk/release/output-metadata.json').read_text())
    version = f'{built["elements"][0]["versionName"]}-{built["elements"][0]["versionCode"]}'
    name = f'starter-{version}' + ('-test-signed' if test_signed else '')
    OUT.mkdir(parents=True, exist_ok=True)
    apk, aab, mapping = OUT / f'{name}.apk', OUT / f'{name}.aab', OUT / f'{name}-mapping.txt'
    shutil.copy(outputs / 'apk/release/app-release.apk', apk)
    shutil.copy(outputs / 'bundle/release/app-release.aab', aab)
    shutil.copy(outputs / 'mapping/release/mapping.txt', mapping)
    build_tools = next(p.split(';')[1] for p in sdk_packages() if p.startswith('build-tools;'))
    apksigner = Path(env['ANDROID_HOME']) / 'build-tools' / build_tools / 'apksigner'
    problems = []
    if subprocess.run([str(apksigner), 'verify', str(apk)], env=env, capture_output=True).returncode:
        problems.append(f'{apk.name} isn\'t signed (apksigner verify failed).')
    jarsigner = subprocess.run([str(Path(env['JAVA_HOME']) / 'bin/jarsigner'), '-verify', str(aab)], env=env,
                               capture_output=True, text=True)
    if 'jar verified' not in jarsigner.stdout:
        problems.append(f'{aab.name} isn\'t signed (jarsigner -verify: {jarsigner.stdout.strip()[-300:]}).')
    if not problems:
        folder = EVIDENCE.parent / 'package'
        shutil.rmtree(folder, ignore_errors=True)
        with in_use(f'package.py in {ROOT}'):
            problems = [p.replace('[verified-features] ', '[release] ') for p in
                        smoke(env, boot(env), 'release', folder, (apk, built['applicationId']))]
    if problems:
        for path in (apk, aab, mapping):
            path.unlink(missing_ok=True)  # never leave an output that failed a check
        print('\n'.join(problems))
        return 1
    print(f'package: {built["applicationId"]} {version}, signed{" with a throwaway test key (not for upload)" if test_signed else ""}; '
          f'the release build started and stayed up on the emulator. Outputs: {OUT}')
    return 0


if __name__ == '__main__':
    sys.exit(main())
