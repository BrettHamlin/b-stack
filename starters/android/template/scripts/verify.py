"""The verify gate: every feature is in the feature map, and every journey it names passes in the running app.

Map check (feature-map/*.toml):
  - every feature folder (features/<name>) is in exactly one feature's `modules`, and every module named is one
  - each feature has a journey that turns the device (Screen.rotate), so its state must survive recreation, and one
    that has the app's process end in the background (Screen.returnAfterProcessDeath), so it must survive that too
  - each journey has a `name` and a `proves`, and no journey is named twice (in one feature or across features)
  - the journeys in verify/journeys (top-level `fun Journey.<name>()`) are exactly the mapped ones
  - verify/runner holds only Driver.kt and the generated adapters (Journeys.kt), which match what `adapters` writes
Run: app-verify and the runner are built, then the journeys run on the emulator (scripts/emulator.py, holding its
lock): the runner drives app-verify through UiAutomator, one JUnit test per journey.
  - every mapped journey runs once and passes, and saves at least one screenshot (Screen.checkpoint)
Smoke: the shipped app (app, a debug build: its own manifest and composition root, which journeys never run) is
installed with no data and launched from its launcher entry; it must still be running and showing its window a few
seconds later, with nothing in the crash log. Its screenshot is evidence too (shipped-app/launched.png).
Evidence (screenshots per journey, and evidence.md listing them) goes to .build/evidence/latest/.

Release (the release gate): the same journeys against app-verify built as release (R8 shrinking and obfuscation, as
the shipped app is built), then the smoke launch of the shipped app's release build (signed with a throwaway key).
Evidence goes to .build/evidence/release/.

Usage: python3 scripts/verify.py [map|run|release]     (default: run, which does the map check first)
       python3 scripts/verify.py adapters      write verify/runner's adapters for the journeys in verify/journeys
"""
from contextlib import contextmanager, nullcontext
from pathlib import Path
from typing import Iterator
import fcntl
import json
import re
import shutil
import subprocess
import sys
import time
import tomllib

sys.path.insert(0, str(Path(__file__).resolve().parent))
from emulator import adb, boot, in_use  # noqa: E402
from tools import android_env, gradle_command  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / '.build/evidence/latest'
RELEASE_EVIDENCE = ROOT / '.build/evidence/release'
JOURNEYS = ROOT / 'verify/journeys/src/commonMain/kotlin'
RUNNER = ROOT / 'verify/runner/src/main/kotlin/runner'
ADAPTERS = RUNNER / 'Journeys.kt'
JOURNEY = re.compile(r'^fun\s+Journey\s*\.\s*(\w+)\s*\(\s*\)', re.MULTILINE)
TOP_LEVEL = re.compile(r'^[^\s{}/]', re.MULTILINE)
ANY_JOURNEY = re.compile(r'^[ \t]*(?!private\b)(?:[\w@]+[ \t]+)*fun\s+Journey\s*\.\s*(\w+)', re.MULTILINE)  # however it's declared; private helpers aren't journeys


def load_map() -> tuple[list[dict], list[str]]:
    features, errors = [], []
    for path in sorted((ROOT / 'feature-map').glob('*.toml')):
        try:
            entry = tomllib.loads(path.read_text())
        except tomllib.TOMLDecodeError as error:
            errors.append(f'[verified-features] feature-map/{path.name}: invalid TOML: {error}')
            continue
        entry['file'] = f'feature-map/{path.name}'
        features.append(entry)
    return features, errors


def journey_bodies() -> dict[str, str]:
    """Each journey's body text, from its `fun Journey.<name>()` to the next top-level declaration (a journey, a
    private helper, anything that starts a line at column 0 other than its braces)."""
    bodies = {}
    for path in sorted(JOURNEYS.rglob('*.kt')):
        text = path.read_text()
        for m in JOURNEY.finditer(text):
            end = TOP_LEVEL.search(text, m.end())
            bodies[m.group(1)] = text[m.end():end.start() if end else len(text)]
    return bodies


def takes(step: str, body: str) -> bool:
    """Whether a journey body takes a Screen step (`rotate`), directly or through a helper in verify/journeys that does."""
    call = re.compile(rf'\b{step}\s*\(\s*\)')
    helpers = set()
    for path in sorted(JOURNEYS.rglob('*.kt')):
        text = path.read_text()
        starts = list(re.finditer(r'^(?:[\w@]+[ \t]+)*fun\s+(?:[\w.<>]+\.)?(\w+)\s*\(', text, re.MULTILINE))
        for i, m in enumerate(starts):
            end = starts[i + 1].start() if i + 1 < len(starts) else len(text)
            if call.search(text[m.end():end]):
                helpers.add(m.group(1))
    return bool(call.search(body)) or any(re.search(rf'\b{h}\s*\(', body) for h in helpers)


def journeys_in_code() -> list[str]:
    return [m.group(1) for path in sorted(JOURNEYS.rglob('*.kt')) for m in JOURNEY.finditer(path.read_text())]


def adapters_text(names: list[str]) -> str:
    imports = ''.join(f'import journeys.{n}\n' for n in sorted(set(names)))
    tests = ''.join(f'\n    @Test\n    fun {n}() = Driver("{n}").{n}()\n' for n in names)
    return ('// Generated by scripts/verify.py adapters from the journeys in verify/journeys. Don\'t edit: the verify\n'
            '// gate fails if this file differs from what it generates.\npackage runner\n\n'
            'import androidx.test.ext.junit.runners.AndroidJUnit4\n' + imports +
            'import org.junit.Test\nimport org.junit.runner.RunWith\n\n'
            '@RunWith(AndroidJUnit4::class)\nclass Journeys {' + tests + '}\n')


def map_errors(features: list[dict]) -> list[str]:
    errors = []
    folders = sorted(p.name for p in (ROOT / 'features').iterdir() if p.is_dir()) if (ROOT / 'features').is_dir() else []
    claimed: dict[str, str] = {}
    for feature in features:
        where = feature['file']
        for key in ('id', 'summary', 'modules', 'journeys'):
            if key not in feature:
                errors.append(f'[verified-features] {where}: missing `{key}`')
        for module in feature.get('modules', []):
            if module not in folders:
                errors.append(f'[verified-features] {where}: module `{module}` isn\'t a feature (features/{module}). '
                              'Name the feature folders this feature is made of.')
            elif module in claimed:
                errors.append(f'[verified-features] {where}: module `{module}` is already in {claimed[module]}')
            else:
                claimed[module] = where
        if not feature.get('journeys'):
            errors.append(f'[verified-features] {where}: no journeys. Each feature needs at least one journey that '
                          'runs the app and shows the feature working.')
        for journey in feature.get('journeys', []):
            if not journey.get('name') or not journey.get('proves'):
                errors.append(f'[verified-features] {where}: each journey needs a `name` and what it `proves`')
    for folder in folders:
        if folder not in claimed:
            errors.append(f'[verified-features] features/{folder} isn\'t in the feature map. Add feature-map/<id>.toml '
                          'naming it in `modules`, with journeys in verify/journeys that prove it works in the app.')
    seen: dict[str, str] = {}
    for feature in features:
        for journey in feature.get('journeys', []):
            name = journey.get('name')
            if name in seen:
                errors.append(f'[verified-features] {feature["file"]}: journey `{name}` is already named in {seen[name]}')
            elif name:
                seen[name] = feature['file']
    code = journeys_in_code()
    bodies = journey_bodies()
    for feature in features:
        names = [j.get('name') for j in feature.get('journeys', [])]
        if names and all(n in bodies for n in names) and not any(takes('rotate', bodies[n]) for n in names):
            errors.append(f'[verified-features] {feature["file"]}: none of its journeys turns the device (screen.rotate()). '
                          'Each feature has one that does, checking its state and half-done input survive the screen '
                          'being recreated.')
        if names and all(n in bodies for n in names) and not any(takes('returnAfterProcessDeath', bodies[n]) for n in names):
            errors.append(f'[verified-features] {feature["file"]}: none of its journeys has the app\'s process end in the '
                          'background (screen.returnAfterProcessDeath()). Each feature has one that does, checking its '
                          'state and half-done input come back in a new process (keep input in the model\'s Saved).')
    errors += [f'[verified-features] journey `{n}` is still the stub new_feature.py wrote. Write it: use the feature as '
               'a user would, check what they\'d see, and that it survives the device turning and the process ending.'
               for n, body in bodies.items() if 'Write this journey' in body]
    other = sorted({m.group(1) for path in sorted(JOURNEYS.rglob('*.kt')) for m in ANY_JOURNEY.finditer(path.read_text())} - set(code))
    errors += [f'[verified-features] journey `{n}` in verify/journeys isn\'t declared as a plain top-level '
               f'`fun Journey.{n}()`, so it never runs (a helper for journeys: make it private).' for n in other]
    errors += [f'[verified-features] journey `{n}` is defined {code.count(n)} times in verify/journeys. Each journey '
               'has one name, as in the feature map.' for n in sorted(set(code)) if code.count(n) > 1]
    errors += [f'[verified-features] journey `{n}` in verify/journeys isn\'t in the feature map. Add it to the feature '
               'it proves.' for n in dict.fromkeys(code) if n not in seen]
    errors += [f'[verified-features] {seen[n]}: journey `{n}` isn\'t in verify/journeys (as `fun Journey.{n}()`), so it '
               'never runs.' for n in seen if n not in code]
    allowed = {RUNNER / 'Driver.kt', ADAPTERS}
    extra = sorted(str(p.relative_to(ROOT)) for p in (ROOT / 'verify/runner').rglob('*') if p.is_file() and p not in allowed)
    if extra:
        errors.append(f'[verified-features] verify/runner holds only the driver (Driver.kt) and the generated adapters '
                      f'(Journeys.kt); found {", ".join(extra)}. Journey bodies go in verify/journeys.')
    if not ADAPTERS.is_file() or ADAPTERS.read_text() != adapters_text(code):
        errors.append('[verified-features] verify/runner/src/main/kotlin/runner/Journeys.kt isn\'t the generated adapters '
                      'for the journeys in verify/journeys. Run `python3 scripts/verify.py adapters`; never edit it by hand.')
    return errors


def app_id(module: str, variant: str = 'debug') -> str:
    metadata = ROOT / f'.build/gradle/{module}/outputs/apk/{variant}/output-metadata.json'
    return json.loads(metadata.read_text())['applicationId']


def apk(module: str, variant: str = 'debug') -> Path:
    found = sorted((ROOT / f'.build/gradle/{module}/outputs/apk/{variant}').glob('*.apk'))
    return found[0]


def parse_instrumentation(output: str) -> dict[str, tuple[str, str]]:
    """{test name: (status, stack)} from `am instrument -r` output: status ok, failed, error or skipped."""
    results: dict[str, tuple[str, str]] = {}
    block: dict[str, str] = {}
    key = None
    for line in output.splitlines():
        if line.startswith('INSTRUMENTATION_STATUS: '):
            key, _, value = line.removeprefix('INSTRUMENTATION_STATUS: ').partition('=')
            block[key] = value
        elif line.startswith('INSTRUMENTATION_STATUS_CODE: '):
            code = int(line.split(': ', 1)[1])
            name = block.get('test', '')
            if code != 1 and name:  # 1 is "started"
                status = {0: 'ok', -2: 'failed', -1: 'error', -3: 'skipped', -4: 'skipped'}.get(code, 'error')
                results[name] = (status, block.get('stack', ''))
            block, key = {}, None
        elif key == 'stack':
            block['stack'] += '\n' + line
    return results


def smoke(env: dict, serial: str, variant: str = 'debug', folder: Path = EVIDENCE / 'shipped-app',
          built: tuple[Path, str] | None = None) -> list[str]:
    """Launches the shipped app's build (debug for verify, release for the release gate; package.py passes its own
    copy of the APK and its id as `built`) as a user would on a fresh install: it must start and stay up. The app is
    uninstalled before and after, since its builds are signed with different keys."""
    path, shipped = built or (apk('app', variant), app_id('app', variant))
    adb(env, 'uninstall', shipped, serial=serial)
    out = adb(env, 'install', str(path), serial=serial, timeout=300)
    if 'Success' not in out:
        return [f'[verified-features] installing the shipped app (app, {variant}) failed:\n{out[-2000:]}']
    try:
        return launched(env, serial, shipped, variant, folder)
    finally:
        adb(env, 'uninstall', shipped, serial=serial)


def launched(env: dict, serial: str, shipped: str, variant: str, folder: Path) -> list[str]:
    adb(env, 'logcat', '-b', 'crash', '-c', serial=serial)
    launcher = ['-a', 'android.intent.action.MAIN', '-c', 'android.intent.category.LAUNCHER']  # what the icon sends
    activity = adb(env, 'shell', 'cmd', 'package', 'resolve-activity', '--brief', *launcher, shipped,
                   serial=serial).strip().splitlines()[-1:]
    if not activity or '/' not in activity[0]:
        return [f'[verified-features] the shipped app ({shipped}) has no launcher activity, so users can\'t open it. Its '
                'manifest (app/src/main/AndroidManifest.xml) needs one activity with MAIN and LAUNCHER.']
    started = adb(env, 'shell', 'am', 'start', '-W', *launcher, '-n', activity[0], serial=serial, timeout=60)
    time.sleep(3)  # a crash in the first frames, or in work started at launch
    crash = adb(env, 'logcat', '-b', 'crash', '-d', serial=serial).strip()
    alive = adb(env, 'shell', 'pidof', shipped, serial=serial).strip()
    focus = adb(env, 'shell', 'dumpsys', 'window', 'displays', serial=serial)
    shown = any(f' {shipped}/' in line for line in focus.splitlines() if 'mCurrentFocus' in line)  # has input focus
    folder.mkdir(parents=True, exist_ok=True)
    with (folder / 'launched.png').open('wb') as png:
        subprocess.run([str(Path(env['ANDROID_HOME']) / 'platform-tools/adb'), '-s', serial, 'exec-out', 'screencap', '-p'],
                       env=env, stdout=png, timeout=60)
    if 'Status: ok' in started and alive and shown and not crash:
        return []
    return [f'[verified-features] the shipped app (app {variant}, {shipped}) didn\'t start and stay up on a fresh install: '
            'journeys run app-verify, so this is the only run of app\'s own manifest and composition root '
            '(StarterApp, MainActivity). Fix the app.\n'
            f'{started.strip()[-1500:]}\n{crash[-3000:] or ("not running" if not alive else "its window isn\'t shown")}']


KEYS = ('BSTACK_UPLOAD_KEYSTORE', 'BSTACK_UPLOAD_KEYSTORE_PASSWORD', 'BSTACK_UPLOAD_KEY_ALIAS', 'BSTACK_UPLOAD_KEY_PASSWORD')


def throwaway_key(env: dict) -> dict:
    """A key for test builds only (the release gate, and package.py without an upload key), made once per checkout."""
    store = ROOT / '.build/package/test-upload.jks'
    if not store.is_file():
        store.parent.mkdir(parents=True, exist_ok=True)
        subprocess.run([str(Path(env['JAVA_HOME']) / 'bin/keytool'), '-genkeypair', '-keystore', str(store),
                        '-storepass', 'test-only', '-keypass', 'test-only', '-alias', 'test', '-keyalg', 'RSA',
                        '-keysize', '2048', '-validity', '3650', '-dname', 'CN=Test build not for upload', '-noprompt'],
                       check=True, capture_output=True)
    return dict(zip(KEYS, (str(store), 'test-only', 'test', 'test-only')))


@contextmanager
def release_outputs() -> Iterator[None]:
    """This checkout's release build outputs, held by whoever builds them until it has read them (the release gate,
    package.py), so one never reads the other's build."""
    lock = ROOT / '.build/package/release-build.lock'
    lock.parent.mkdir(parents=True, exist_ok=True)
    with lock.open('w') as handle:
        fcntl.flock(handle, fcntl.LOCK_EX)
        yield


def run(features: list[dict], variant: str = 'debug', evidence: Path = EVIDENCE) -> list[str]:
    """Builds app-verify, the runner and the shipped app as `variant` (release: R8, as shipped), runs every journey
    against app-verify, then smoke-launches the shipped app."""
    with release_outputs() if variant == 'release' else nullcontext():
        return built_and_run(features, variant, evidence)


def built_and_run(features: list[dict], variant: str, evidence: Path) -> list[str]:
    env = android_env()
    tasks = [f':app-verify:assemble{variant.title()}', ':verify:runner:assembleDebug', f':app:assemble{variant.title()}']
    signing = throwaway_key(env) if variant == 'release' else {}
    build = subprocess.run(gradle_command('-q', *tasks), env={**env, **signing}, capture_output=True, text=True)
    if build.returncode != 0:
        return [f'[verified-features] the app didn\'t build, so it can\'t run:\n{(build.stdout + build.stderr)[-4000:]}']
    target, runner = app_id('app-verify', variant), app_id('verify/runner')
    device_evidence = f'/sdcard/Android/media/{runner}/evidence'
    with in_use(f'verify.py in {ROOT}'):
        serial = boot(env)
        for module, built in (('app-verify', variant), ('verify/runner', 'debug')):
            out = adb(env, 'install', '-r', '-t', str(apk(module, built)), serial=serial, timeout=300)
            if 'Success' not in out:
                return [f'[verified-features] installing {module} failed:\n{out[-2000:]}']
        adb(env, 'shell', 'rm', '-rf', device_evidence, serial=serial)
        output = adb(env, 'shell', 'am', 'instrument', '-w', '-r', '-e', 'bstack.app', target, '-e', 'bstack.evidence',
                     device_evidence, f'{runner}/androidx.test.runner.AndroidJUnitRunner', serial=serial, timeout=1800)
        adb(env, 'pull', device_evidence + '/.', str(evidence), serial=serial, timeout=300)
        smoke_errors = smoke(env, serial, variant, evidence / 'shipped-app')
    (evidence / 'instrumentation.txt').write_text(output)
    results = parse_instrumentation(output)
    errors: list[str] = list(smoke_errors)
    mapped = {j['name']: f['file'] for f in features for j in f.get('journeys', []) if j.get('name')}
    errors += [f'[verified-features] {mapped[n]}: journey `{n}` didn\'t run.' for n in mapped if n not in results]
    lines = [f'# Verify evidence ({variant} build)', '']
    for feature in features:
        lines += [f'## {feature.get("id")}: {feature.get("summary", "")}', '']
        for journey in feature.get('journeys', []):
            name = journey.get('name')
            if name not in results:
                continue
            status, stack = results[name]
            shots = sorted((evidence / name).glob('*.png')) if (evidence / name).is_dir() else []
            if status != 'ok':
                errors.append(f'[verified-features] journey `{name}` {status} in the {variant} build ({feature["file"]}). Fix the app, or if '
                              f'the journey is wrong, say why; never weaken it.\n{stack[-3000:]}')
            elif not shots:
                errors.append(f'[verified-features] journey `{name}` saved no screenshot. Call checkpoint() where it '
                              'shows the feature working: screenshots are the evidence.')
            lines += [f'### {name}: {"PASS" if status == "ok" and shots else "FAIL"}', '', journey.get('proves', ''), '']
            lines += [f'- ![{shot.stem}]({name}/{shot.name})' for shot in shots] + ['']
    (evidence / 'evidence.md').write_text('\n'.join(lines))
    if not results and not errors:
        errors.append(f'[verified-features] the journeys didn\'t run:\n{output[-3000:]}')
    return errors


if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else 'run'
    if mode == 'adapters':
        ADAPTERS.write_text(adapters_text(journeys_in_code()))
        print(f'wrote {ADAPTERS.relative_to(ROOT)}')
        sys.exit(0)
    if mode not in ('map', 'run', 'release'):
        sys.exit(__doc__)
    folder = RELEASE_EVIDENCE if mode == 'release' else EVIDENCE
    if mode != 'map':
        shutil.rmtree(folder, ignore_errors=True)  # never leave an earlier run's evidence as the latest
    features, errors = load_map()
    errors += map_errors(features)
    if mode != 'map' and not errors:
        folder.mkdir(parents=True)
        errors += run(features, 'release' if mode == 'release' else 'debug', folder)
    done = {'run': f'verify: every feature mapped; every journey passed. Evidence: {EVIDENCE / "evidence.md"}',
            'release': 'verify release: every journey passed against app-verify\'s release build (R8), and the shipped '
                       f'app\'s release build started. Evidence: {RELEASE_EVIDENCE / "evidence.md"}',
            'map': 'verify map: every feature mapped (journeys not run)'}[mode]
    print('\n'.join(errors) if errors else done)
    sys.exit(1 if errors else 0)
