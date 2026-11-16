"""Verify the running app: launch it in test mode, drive every feature-map journey, and keep the evidence.

Commands:
  run        check the feature map, run every journey on a simulator, write evidence (the `verify` gate)
  map        only check the feature map (no simulator)
  launch     build AppVerify, boot a simulator, install and start it, for exploring with agent-device
             options: --fixture NAME (default standard), --reset (restore the fixture's starting data)
  doctor     read-only: is the simulator booted, AppVerify installed and running? Run it whenever anything looks off.
  cleanup    stop AppVerify and shut down a simulator this script booted. Evidence is kept.

Test mode: AppVerify is the app composed with Targets/Fixtures instead of real services. It reads BSTACK_FIXTURE
(a Fixture case, e.g. standard or save-fails) and BSTACK_RESET=1. The shipped App can't import Fixtures.

Feature map: feature-map/*.toml, one file per feature. Every feature module (each Targets/<Feature>Interface) needs an
entry; every journey an entry names must exist in Targets/*UITests, and every journey there must be named by an entry.

Evidence: .build/evidence/<time>-<commit>/ (in the cache folder if one is configured): evidence.md, screenshots,
the .xcresult bundle and the xcodebuild log. .build/evidence/latest points at the newest run.
"""
from datetime import datetime, timezone
from pathlib import Path
import argparse
import json
import os
import plistlib
import re
import shutil
import subprocess
import sys
import tomllib

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import link_build_dirs  # noqa: E402
from simulator import simulator, state  # noqa: E402
from tools import tool_path  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
BUNDLE_ID = 'dev.bstack.starter.verify'
SCHEME = 'AppVerify'
DERIVED = ROOT / '.build/DerivedData'
SESSION = ROOT / '.build/verify-session.json'
JOURNEY_TIMEOUT = 1200


def fail(message: str) -> None:
    print(f'[verify] {message}', flush=True)


# ---------------------------------------------------------------- feature map

def features() -> list[str]:
    return sorted(p.name.removesuffix('Interface') for p in (ROOT / 'Targets').glob('*Interface') if p.is_dir())


def journeys_in_code() -> set[str]:
    """Class/test pairs XCTest would run: classes that inherit from XCTestCase directly or through a base class,
    with their own and inherited `test...()` methods. Results the run reports are also checked against the map."""
    classes: dict[str, tuple[list[str], set[str]]] = {}
    for source in (ROOT / 'Targets').glob('*UITests/**/*.swift'):
        text = source.read_text()
        for cls in re.finditer(r'\bclass\s+(\w+)\s*:\s*([^{]+)\{', text):
            bases = [b.strip() for b in cls.group(2).split(',')]
            classes[cls.group(1)] = (bases, set(re.findall(r'func\s+(test\w+)\s*\(\s*\)', top_level(text, cls.end()))))

    def is_test_class(name: str, seen: frozenset = frozenset()) -> bool:
        bases = classes.get(name, ([], set()))[0]
        return 'XCTestCase' in bases or any(b in classes and b not in seen and is_test_class(b, seen | {name}) for b in bases)

    def tests(name: str, seen: frozenset = frozenset()) -> set[str]:
        bases, own = classes.get(name, ([], set()))
        return own.union(*(tests(b, seen | {name}) for b in bases if b in classes and b not in seen))

    return {f'{name}/{test}' for name in classes if is_test_class(name) for test in tests(name)}


def skip_literal(text: str, i: int) -> int:
    """If a comment or string literal starts at i, return the index just after it; otherwise return i.

    Handles // and nested /* */ comments, and "...", \"\"\"...\"\"\" and raw #"..."# strings with escapes.
    Interpolated expressions are skipped with the string; their braces never reach the brace counter.
    """
    if text.startswith('//', i):
        newline = text.find('\n', i)
        return len(text) if newline == -1 else newline
    if text.startswith('/*', i):
        depth, j = 1, i + 2
        while j < len(text) and depth:
            if text.startswith('/*', j):
                depth, j = depth + 1, j + 2
            elif text.startswith('*/', j):
                depth, j = depth - 1, j + 2
            else:
                j += 1
        return j
    j = i
    while j < len(text) and text[j] == '#':
        j += 1
    hashes = j - i
    if j >= len(text) or text[j] != '"':
        return i
    quote = '\"\"\"' if text.startswith('\"\"\"', j) else '"'
    closing = quote + '#' * hashes
    escape = '\\' + '#' * hashes
    j += len(quote)
    while j < len(text):
        if text.startswith(escape + '(', j):
            j = skip_parens(text, j + len(escape) + 1)
        elif text.startswith(escape, j):
            j += len(escape) + 1
        elif text.startswith(closing, j):
            return j + len(closing)
        else:
            j += 1
    return len(text)


def skip_parens(text: str, j: int) -> int:
    """Index just after the ')' closing a string interpolation whose '(' is just before j."""
    depth = 1
    while j < len(text) and depth:
        after = skip_literal(text, j)
        if after != j:
            j = after
            continue
        depth += {'(': 1, ')': -1}.get(text[j], 0)
        j += 1
    return j


def top_level(text: str, start: int) -> str:
    """The text of a type body that opens just before `start`, without nested bodies (helper types, closures,
    function bodies), comments or string literals, so only the type's own declarations remain."""
    depth, kept, i = 1, [], start
    while i < len(text) and depth:
        after = skip_literal(text, i)
        if after != i:
            i = after
            continue
        if text[i] == '{':
            depth += 1
        elif text[i] == '}':
            depth -= 1
        elif depth == 1:
            kept.append(text[i])
        i += 1
    return ''.join(kept)


def load_map() -> tuple[list[dict], list[str]]:
    entries, errors = [], []
    for path in sorted((ROOT / 'feature-map').glob('*.toml')):
        try:
            entry = tomllib.loads(path.read_text())
        except tomllib.TOMLDecodeError as error:
            errors.append(f'feature-map/{path.name}: invalid TOML: {error}')
            continue
        for key in ('id', 'module', 'summary', 'entry_points', 'journeys'):
            if key not in entry:
                errors.append(f'feature-map/{path.name}: missing "{key}"')
        for journey in entry.get('journeys', []):
            for key in ('test', 'fixture', 'proves'):
                if key not in journey:
                    errors.append(f'feature-map/{path.name}: a journey is missing "{key}"')
        entry['file'] = path.name
        entries.append(entry)
    return entries, errors


def check_map() -> tuple[list[dict], list[str]]:
    entries, errors = load_map()
    mapped = {e.get('module') for e in entries}
    for feature in features():
        if feature not in mapped:
            errors.append(f'feature {feature} has no feature-map entry. Add feature-map/<id>.toml with module = "{feature}" '
                          'and at least one journey that proves it works.')
    in_code = journeys_in_code()
    named = {j.get('test') for e in entries for j in e.get('journeys', [])}
    for entry in entries:
        if not entry.get('journeys'):
            errors.append(f'feature-map/{entry["file"]}: no journeys. Every feature needs at least one.')
        for journey in entry.get('journeys', []):
            if journey.get('test') not in in_code:
                errors.append(f'journey {journey.get("test")} (feature-map/{entry["file"]}) does not exist in Targets/*UITests.')
    for test in sorted(in_code - named):
        errors.append(f'journey {test} is not in the feature map. Name it under the feature it proves.')
    return entries, errors


# ---------------------------------------------------------------- simulator helpers

def sh(cmd: list[str], timeout: int | None = None, log: Path | None = None) -> subprocess.CompletedProcess:
    # Output goes to a file, not a pipe: simulator helper processes can inherit and hold a pipe open.
    if log is None:
        return subprocess.run(cmd, cwd=ROOT, capture_output=True, text=True, timeout=timeout)
    with log.open('w') as out:
        return subprocess.run(cmd, cwd=ROOT, stdout=out, stderr=subprocess.STDOUT, text=True, timeout=timeout)


def boot(udid: str) -> bool:
    """Start booting the simulator if it isn't booted. Returns True if this call booted it (and so owns it)."""
    if state(udid).get('state') != 'Shutdown':
        return False  # booted or booting by someone else: borrow it, never shut it down
    return sh(['xcrun', 'simctl', 'boot', udid]).returncode == 0


def wait_booted(udid: str) -> bool:
    try:
        return sh(['xcrun', 'simctl', 'bootstatus', udid, '-b'], timeout=300).returncode == 0
    except subprocess.TimeoutExpired:
        return False


def shutdown(udid: str) -> None:
    sh(['xcrun', 'simctl', 'shutdown', udid], timeout=120)


def generate() -> bool:
    tuist = str(tool_path('tuist'))
    for cmd in ([tuist, 'install'], [tuist, 'generate', '--no-open']):
        proc = sh(cmd)
        if proc.returncode != 0:
            print((proc.stdout + proc.stderr).strip()[-3000:])
            return False
    return True


def commit() -> str:
    proc = sh(['git', 'rev-parse', '--short', 'HEAD'])
    sha = proc.stdout.strip() if proc.returncode == 0 else 'nogit'
    dirty = sh(['git', 'status', '--porcelain', '--', '.']).stdout.strip()
    return f'{sha}-dirty' if dirty else sha


# ---------------------------------------------------------------- run

DYLD_KEYS = ('DYLD_FRAMEWORK_PATH', 'DYLD_LIBRARY_PATH', '__XPC_DYLD_FRAMEWORK_PATH', '__XPC_DYLD_LIBRARY_PATH')


def isolated_xctestrun() -> Path | None:
    """Copy of the built .xctestrun without the build folder on the runner's and app's DYLD_* search paths.

    Xcode puts the build folder first on DYLD_FRAMEWORK_PATH. A framework there named like an Apple one (TCA's
    dependency swift-sharing builds Sharing.framework; iOS has a private Sharing.framework) then replaces Apple's in
    the test runner, which crashes before any test runs. The app and the test bundle embed their own frameworks, so
    they run without it, the way the shipped app does.
    """
    built = sorted((DERIVED / 'Build/Products').glob(f'{SCHEME}_*.xctestrun'), key=lambda p: p.stat().st_mtime)
    if not built:
        return None
    plan = plistlib.loads(built[-1].read_bytes())
    targets = [t for config in plan.get('TestConfigurations', []) for t in config.get('TestTargets', [])]
    targets += [v for k, v in plan.items() if isinstance(v, dict) and 'TestBundlePath' in v]
    for target in targets:
        for group in ('EnvironmentVariables', 'TestingEnvironmentVariables', 'UITargetAppEnvironmentVariables'):
            env = target.get(group, {})
            for key in DYLD_KEYS:
                if key in env:
                    kept = [p for p in env[key].split(':') if p and not p.startswith('__TESTROOT__')]
                    if kept:
                        env[key] = ':'.join(kept)
                    else:
                        del env[key]
    isolated = built[-1].with_name(f'{SCHEME}-isolated.xctestrun')
    isolated.write_bytes(plistlib.dumps(plan))
    return isolated


def collect_tests(node: dict, path: list[str], out: list[dict]) -> None:
    if node.get('nodeType') == 'Test Case':
        messages = [c.get('name', '') for c in node.get('children', []) if c.get('nodeType') == 'Failure Message']
        suite = next((p for p in reversed(path) if p), '')
        out.append({'test': f'{suite}/{node.get("name", "").removesuffix("()")}', 'result': node.get('result'),
                    'messages': messages})
        return
    name = node.get('name', '') if node.get('nodeType') == 'Test Suite' else ''
    for child in node.get('children', []):
        collect_tests(child, path + [name], out)


def attachments(directory: Path) -> dict[str, list[tuple[str, str]]]:
    """Exported attachments per journey, as (name, file) pairs whose file exists."""
    manifest = directory / 'attachments/manifest.json'
    found: dict[str, list[tuple[str, str]]] = {}
    if manifest.is_file():
        for test in json.loads(manifest.read_text()):
            key = test.get('testIdentifier', '').removesuffix('()')
            for item in test.get('attachments', []):
                # Xcode appends "_<n>_<UUID>.<ext>" to the name given in the journey.
                name = re.sub(r'_\d+_[0-9A-Fa-f-]{36}(\.\w+)?$', '', item.get('suggestedHumanReadableName', ''))
                file = item.get('exportedFileName', '')
                if file and (directory / 'attachments' / file).is_file():
                    found.setdefault(key, []).append((name, file))
    return found


def is_image(file: str) -> bool:
    return file.lower().endswith(('.png', '.jpg', '.jpeg'))


def write_evidence(directory: Path, entries: list[dict], results: dict[str, dict], device: dict, sha: str) -> None:
    shots = attachments(directory)
    lines = [
        f'# Evidence: {sha}', '',
        '| | |', '|---|---|',
        f'| Commit | `{sha}` |',
        f'| Run | {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")} |',
        f'| Simulator | {device.get("name", "?")} ({device.get("runtime", "?")}), `{device.get("udid", "?")}` |',
        f'| App | AppVerify (`{BUNDLE_ID}`), test mode with fixtures |', '',
    ]
    for entry in entries:
        lines += [f'## {entry["id"]}', '', entry['summary'], '']
        for journey in entry['journeys']:
            result = results.get(journey['test'], {'result': 'Not run', 'messages': []})
            lines += [f'### {journey["test"]}: {result["result"]}', '',
                      f'Fixture `{journey["fixture"]}`. Proves: {journey["proves"]}', '']
            lines += [f'- Failure: {m}' for m in result['messages']]
            for name, file in sorted(shots.get(journey['test'], [])):
                lines.append(f'- {"!" if is_image(file) else ""}[{name}](attachments/{file})')
            lines.append('')
    lines += ['## Not covered', '',
              '- Real services: journeys run against fixtures, not production backends.',
              '- One simulator model and OS version; no physical device.', '']
    (directory / 'evidence.md').write_text('\n'.join(lines))


def run() -> bool:
    entries, errors = check_map()
    for error in errors:
        fail(error)
    if errors:
        return False
    if not generate():
        fail('project generation failed')
        return False

    sha = commit()
    directory = ROOT / '.build/evidence' / f'{datetime.now().strftime("%Y%m%d-%H%M%S")}-{sha}'
    directory.mkdir(parents=True)
    latest = ROOT / '.build/evidence/latest'
    latest.unlink(missing_ok=True)
    latest.symlink_to(directory.name)

    udid = simulator()
    device: dict = {}
    result_bundle = directory / 'Journeys.xcresult'
    booted_here = boot(udid)
    try:
        if not wait_booted(udid):
            fail(f'simulator {udid} did not finish booting')
            return False
        device = state(udid)
        built = sh(['xcodebuild', '-workspace', 'Starter.xcworkspace', '-scheme', SCHEME,
                    '-destination', f'platform=iOS Simulator,id={udid}', '-derivedDataPath', str(DERIVED),
                    '-skipMacroValidation', 'build-for-testing', 'CODE_SIGNING_ALLOWED=NO'],
                   timeout=JOURNEY_TIMEOUT, log=directory / 'build.log')
        xctestrun = isolated_xctestrun() if built.returncode == 0 else None
        if xctestrun is None:
            errors = [l.strip() for l in (directory / 'build.log').read_text(errors='replace').splitlines() if 'error:' in l]
            fail('build for testing failed: ' + ('; '.join(dict.fromkeys(errors[:10])) or f'see {directory / "build.log"}'))
            return False
        proc = sh(['xcodebuild', 'test-without-building', '-xctestrun', str(xctestrun),
                   '-destination', f'platform=iOS Simulator,id={udid}', '-resultBundlePath', str(result_bundle)],
                  timeout=JOURNEY_TIMEOUT, log=directory / 'xcodebuild.log')
        status = proc.returncode
    except subprocess.TimeoutExpired:
        fail(f'journeys timed out after {JOURNEY_TIMEOUT}s. Log: {directory / "xcodebuild.log"}'
             + ('' if booted_here else '. The simulator was already booted, so it was left running; it may need a restart.'))
        return False
    finally:
        if booted_here:
            shutdown(udid)

    results: dict[str, dict] = {}
    exported = False
    if result_bundle.exists():
        exported = sh(['xcrun', 'xcresulttool', 'export', 'attachments', '--path', str(result_bundle),
                       '--output-path', str(directory / 'attachments')]).returncode == 0
        tree = sh(['xcrun', 'xcresulttool', 'get', 'test-results', 'tests', '--path', str(result_bundle)])
        if tree.returncode == 0:
            found: list[dict] = []
            for node in json.loads(tree.stdout).get('testNodes', []):
                collect_tests(node, [], found)
            results = {t['test']: t for t in found}
    write_evidence(directory, entries, results, device, sha)

    ok = status == 0
    shots = attachments(directory)
    named = {j['test'] for e in entries for j in e['journeys']}
    for entry in entries:
        for journey in entry['journeys']:
            result = results.get(journey['test'])
            if result is None:
                ok = False
                fail(f'journey {journey["test"]} did not run')
            elif result['result'] != 'Passed':
                ok = False
                fail(f'journey failed: {journey["test"]}: {"; ".join(result["messages"]) or result["result"]}')
            elif not any(is_image(file) for _, file in shots.get(journey['test'], [])):
                ok = False
                fail(f'journey {journey["test"]} attached no screenshots. Attach one at each checkpoint '
                     '(XCTAttachment(screenshot:), lifetime .keepAlways): they are the evidence.')
    for test in sorted(set(results) - named):
        ok = False
        fail(f'journey {test} ran but is not in the feature map. Name it under the feature it proves.')
    if result_bundle.exists() and not exported:
        ok = False
        fail(f'could not export screenshots from {result_bundle}')
    if status != 0 and not any(r['result'] != 'Passed' for r in results.values()):
        log = (directory / 'xcodebuild.log').read_text(errors='replace')
        reasons = log.split('Testing failed:', 1)[1].strip().splitlines()[:5] if 'Testing failed:' in log else []
        fail('the test run failed before any journey finished: ' + ('; '.join(l.strip() for l in reasons) or f'see {directory / "xcodebuild.log"}'))
    print(f'[verify] evidence: {directory / "evidence.md"}', flush=True)
    return ok


# ---------------------------------------------------------------- explore

def launch(fixture: str, reset: bool) -> bool:
    if not generate():
        return False
    udid = simulator()
    proc = sh(['xcodebuild', '-workspace', 'Starter.xcworkspace', '-scheme', SCHEME,
               '-destination', f'platform=iOS Simulator,id={udid}', '-derivedDataPath', str(DERIVED),
               '-quiet', '-skipMacroValidation', 'build', 'CODE_SIGNING_ALLOWED=NO'])
    if proc.returncode != 0:
        print((proc.stdout + proc.stderr).strip()[-3000:])
        return False
    session = json.loads(SESSION.read_text()) if SESSION.is_file() else {}
    booted_here = boot(udid) or (session.get('udid') == udid and session.get('booted_here', False))
    # Recorded before anything else can fail, so `cleanup` can always find a simulator this script booted.
    SESSION.write_text(json.dumps({'udid': udid, 'booted_here': booted_here}))
    if not wait_booted(udid):
        fail(f'simulator {udid} did not finish booting; run `python3 scripts/verify.py cleanup`')
        return False
    app = DERIVED / 'Build/Products/Debug-iphonesimulator/AppVerify.app'
    if sh(['xcrun', 'simctl', 'install', udid, str(app)]).returncode != 0:
        fail('install failed')
        return False
    env = {'SIMCTL_CHILD_BSTACK_FIXTURE': fixture, **({'SIMCTL_CHILD_BSTACK_RESET': '1'} if reset else {})}
    started = subprocess.run(['xcrun', 'simctl', 'launch', '--terminate-running-process', udid, BUNDLE_ID],
                             cwd=ROOT, capture_output=True, text=True, env={**os.environ, **env})
    if started.returncode != 0:
        fail(f'launch failed: {started.stderr.strip()}')
        return False
    print(json.dumps({'udid': udid, 'bundle_id': BUNDLE_ID, 'fixture': fixture, 'reset': reset,
                      'drive': f'agent-device snapshot --platform ios --udid {udid}',
                      'cleanup': 'python3 scripts/verify.py cleanup'}, indent=2))
    return True


def doctor() -> bool:
    session = json.loads(SESSION.read_text()) if SESSION.is_file() else {}
    udid = session.get('udid') or simulator()
    device = state(udid)
    booted = device.get('state') == 'Booted'
    installed = booted and sh(['xcrun', 'simctl', 'get_app_container', udid, BUNDLE_ID]).returncode == 0
    running = booted and BUNDLE_ID in sh(['xcrun', 'simctl', 'spawn', udid, 'launchctl', 'list']).stdout
    report = {'udid': udid, 'simulator': device.get('name'), 'runtime': device.get('runtime'), 'booted': booted,
              'app_installed': installed, 'app_running': running}
    print(json.dumps(report, indent=2))
    return booted and installed and running


def cleanup() -> bool:
    if not SESSION.is_file():
        print('[verify] nothing to clean up')
        return True
    session = json.loads(SESSION.read_text())
    udid = session['udid']
    if state(udid).get('state') == 'Booted':
        sh(['xcrun', 'simctl', 'terminate', udid, BUNDLE_ID])
        if session.get('booted_here'):
            shutdown(udid)
    SESSION.unlink()
    print(f'[verify] cleaned up {udid}; evidence kept in {ROOT / ".build/evidence"}')
    return True


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('command', nargs='?', default='run', choices=['run', 'map', 'launch', 'doctor', 'cleanup'])
    parser.add_argument('--fixture', default='standard')
    parser.add_argument('--reset', action='store_true')
    args = parser.parse_args()
    link_build_dirs(ROOT)
    if args.command == 'map':
        _, problems = check_map()
        for problem in problems:
            fail(problem)
        print('[verify] feature map OK' if not problems else '', end='\n' if not problems else '')
        ok = not problems
    elif args.command == 'run':
        ok = run()
    elif args.command == 'launch':
        ok = launch(args.fixture, args.reset)
    elif args.command == 'doctor':
        ok = doctor()
    else:
        ok = cleanup()
    sys.exit(0 if ok else 1)
