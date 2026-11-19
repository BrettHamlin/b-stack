"""Verify the running app: launch it in test mode, drive every feature-map journey, and keep the evidence.

Commands:
  run        check the feature map, run every journey on a simulator, write evidence (the `verify` gate)
             option: --workers N, the most simulators to split journeys across (see Parallel journeys)
  map        only check the feature map (no simulator)
  launch     build AppVerify, boot a simulator, install and start it, for exploring with agent-device
             options: --fixture NAME (default standard), --reset (restore the fixture's starting data)
  doctor     read-only: is the simulator booted, AppVerify installed and running? Run it whenever anything looks off.
  cleanup    stop AppVerify and shut down a simulator this script booted, and delete simulator clones a crashed run
             left behind. Evidence is kept.

Test mode: AppVerify is the app composed with Targets/Fixtures instead of real services. It reads BSTACK_FIXTURE
(a Fixture case, e.g. standard or save-fails) and BSTACK_RESET=1. The shipped App can't import Fixtures.

Feature map: feature-map/*.toml, one file per feature. Every feature module (each Targets/<Feature>Interface) needs an
entry, and each entry's module must be a feature. Each journey is named by exactly one entry, with a fixture that
exists. Every journey that runs must be in the map, and every journey in the map must run and pass, using the fixture
the map names.

Parallel journeys: off by default. With --workers N (or $BSTACK_VERIFY_WORKERS, or verify_workers in the b-stack
config) above 1 and a shut-down simulator, `run` clones it and splits the journeys across it and its clones,
one xcodebuild per simulator, then merges the result bundles and checks the merged results exactly as a single run's.
The first simulator runs every journey not given to another (-skip-testing), so a journey the source scan can't see
still runs. Clones are deleted afterwards. A fresh clone boots like a new device and starts every first-boot service:
on a 10-core, 16 GB Mac (Xcode 27.2, iOS 27.2) cloning for the starter's 2 journeys took them from under a minute to
about 5 minutes each, so cloning only pays off for many journeys. A simulator that's already booted belongs to someone else: it's borrowed, alone, and never cloned.

Evidence: .build/evidence/<time>-<commit>/ (in the cache folder if one is configured): evidence.md, screenshots,
the .xcresult bundle and the logs. It is written on every run that gets past the map check, including failed generation, boots, builds
and timeouts. .build/evidence/latest points at the newest such run, and is removed when the map check fails.
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
import threading
import time
import tomllib

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import link_build_dirs, machine_setting  # noqa: E402
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


def known_fixtures() -> set[str]:
    """Fixture names AppVerify accepts: the raw values of the `Fixture` enum's cases in Targets/Fixtures."""
    names: set[str] = set()
    for source in (ROOT / 'Targets/Fixtures').glob('**/*.swift'):
        # Comments become a space and each string literal a numbered placeholder, so neither the enum search nor the
        # case regex can match inside them, and braces in strings don't move the depth.
        text, strings = source.read_text(), []
        masked, i = [], 0
        while i < len(text):
            after = skip_literal(text, i)
            if after == i:
                masked.append(text[i])
                i += 1
                continue
            if text[i] in '"#':
                strings.append(string_value(text[i:after]))
                masked.append(f'\x00{len(strings) - 1}\x00')
            else:
                masked.append(' ')
            i = after
        masked = ''.join(masked)
        start = re.search(r'\benum\s+Fixture\b[^{]*\{', masked)
        if not start:
            continue
        depth, body = 1, []                                         # the enum's own body, nested bodies dropped
        for ch in masked[start.end():]:
            depth += {'{': 1, '}': -1}.get(ch, 0)
            if not depth:
                break
            if depth == 1 and ch not in '{}':
                body.append(ch)
        item = r'(\w+)\s*(?:=\s*\x00(\d+)\x00)?'
        for declaration in re.finditer(r'\bcase\s+(' + item + r'(?:\s*,\s*' + item + r')*)', ''.join(body)):
            for match in re.finditer(item, declaration.group(1)):     # case a, b = "b-raw", across lines too
                names.add(strings[int(match.group(2))] if match.group(2) is not None else match.group(1))
    return names


def string_value(literal: str) -> str:
    """The contents of a plain or raw ("...", #"..."#, \"\"\"...\"\"\") string literal, escapes left as written."""
    hashes = len(literal) - len(literal.lstrip('#'))
    inner = literal[hashes:len(literal) - hashes]
    quote = '\"\"\"' if inner.startswith('\"\"\"') else '"'
    return inner[len(quote):-len(quote)]


def journeys_in_code() -> set[str]:
    """Class/test pairs XCTest would run: classes that inherit from XCTestCase directly or through a base class,
    with their own and inherited `test...()` methods. A fast first check only: anything it can't see (a test in an
    extension, a base class behind a typealias) is still caught from the run's results."""
    classes: dict[str, tuple[list[str], set[str]]] = {}
    for source in (ROOT / 'Targets').glob('*UITests/**/*.swift'):
        text = without_literals(source.read_text())
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


def without_literals(text: str) -> str:
    """The text with comments and string literals replaced by a space, so declarations inside them aren't seen."""
    kept, i = [], 0
    while i < len(text):
        after = skip_literal(text, i)
        if after != i:
            kept.append(' ')
            i = after
        else:
            kept.append(text[i])
            i += 1
    return ''.join(kept)


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
    feature_modules = set(features())
    mapped = {e.get('module') for e in entries}
    for feature in sorted(feature_modules):
        if feature not in mapped:
            errors.append(f'feature {feature} has no feature-map entry. Add feature-map/<id>.toml with module = "{feature}" '
                          'and at least one journey that proves it works.')
    fixtures = known_fixtures()
    owners: dict[str, str] = {}
    for entry in entries:
        if 'module' in entry and entry['module'] not in feature_modules:
            errors.append(f'feature-map/{entry["file"]}: module "{entry["module"]}" is not a feature '
                          f'(no Targets/{entry["module"]}Interface).')
        if not entry.get('journeys'):
            errors.append(f'feature-map/{entry["file"]}: no journeys. Every feature needs at least one.')
        for journey in entry.get('journeys', []):
            test, fixture = journey.get('test', ''), journey.get('fixture')
            if not re.fullmatch(r'\w+/test\w+', test):
                errors.append(f'feature-map/{entry["file"]}: journey "{test}" is not Class/testName.')
            if test in owners:
                errors.append(f'journey {test} is named by both feature-map/{owners[test]} and feature-map/{entry["file"]}. '
                              'A journey proves one feature.')
            owners.setdefault(test, entry['file'])
            if fixture is not None and fixture not in fixtures:
                errors.append(f'journey {test} (feature-map/{entry["file"]}): fixture "{fixture}" does not exist. '
                              f'Known fixtures: {", ".join(sorted(fixtures))}.')
    for test in sorted(journeys_in_code() - set(owners)):
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


def isolated_xctestrun(built: Path | None = None) -> Path | None:
    """Copy of the built .xctestrun without the build folder on the runner's and app's DYLD_* search paths.

    Xcode puts the build folder first on DYLD_FRAMEWORK_PATH. A framework there named like an Apple one (TCA's
    dependency swift-sharing builds Sharing.framework; iOS has a private Sharing.framework) then replaces Apple's in
    the test runner, which crashes before any test runs. The app and the test bundle embed their own frameworks, so
    they run without it, the way the shipped app does.
    """
    if built is None:
        found = sorted((DERIVED / 'Build/Products').glob(f'{SCHEME}_*.xctestrun'), key=lambda p: p.stat().st_mtime)
        if not found:
            return None
        built = found[-1]
    plan = plistlib.loads(built.read_bytes())
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
    isolated = built.with_name(f'{SCHEME}-isolated.xctestrun')
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


def fixtures_used(shots: list[tuple[str, str]]) -> set[str]:
    """Fixtures a journey launched with, from the `fixture-<name>` text attachments its launch helper adds. A
    screenshot that happens to be named `fixture-...` is evidence, not a launch, so images don't count."""
    return {name.removeprefix('fixture-') for name, file in shots if name.startswith('fixture-') and not is_image(file)}


def is_image(file: str) -> bool:
    return file.lower().endswith(('.png', '.jpg', '.jpeg'))


def write_evidence(directory: Path, entries: list[dict], results: dict[str, dict], device: dict, sha: str) -> None:
    shots = attachments(directory)
    lines = [
        f'# Evidence: {sha}', '',
        '| | |', '|---|---|',
        f'| Commit | `{sha}` |',
        f'| Run | {datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")} |',
        f'| Simulator | {device.get("name", "?")} ({device.get("runtime", "?")}), `{device.get("udid", "?")}`'
        + (f', with journeys split across it and {device["clones"]} clone(s) of it' if device.get('clones') else '') + ' |',
        f'| App | AppVerify (`{BUNDLE_ID}`), test mode with fixtures |', '',
    ]
    for entry in entries:
        lines += [f'## {entry["id"]}', '', entry['summary'], '']
        for journey in entry['journeys']:
            result = results.get(journey['test'], {'result': 'Not run', 'messages': []})
            used = ', '.join(f'`{f}`' for f in sorted(fixtures_used(shots.get(journey['test'], [])))) or 'none recorded'
            lines += [f'### {journey["test"]}: {result["result"]}', '',
                      f'Fixture recorded by the journey: {used} (map: `{journey["fixture"]}`). Proves: {journey["proves"]}', '']
            lines += [f'- Failure: {m}' for m in result['messages']]
            for name, file in sorted(shots.get(journey['test'], [])):
                if is_image(file):
                    lines.append(f'- ![{name}](attachments/{file})')
            lines.append('')
    lines += ['## Not covered', '',
              '- Real services: journeys run against fixtures, not production backends.',
              '- One simulator model and OS version; no physical device.',
              '- The shipped App\'s choice of services (Targets/App): it composes features through the same view '
              'initializers as AppVerify, but only AppVerify runs here.', '']
    (directory / 'evidence.md').write_text('\n'.join(lines))


def write_failure(directory: Path, sha: str, device: dict, reason: str) -> None:
    """evidence.md for a run that stopped before any journey finished, so `latest` always has one to read."""
    (directory / 'evidence.md').write_text('\n'.join([
        f'# Evidence: {sha}', '',
        f'**Run failed before any journey finished:** {reason}', '',
        f'Simulator: {device.get("name", "?")} ({device.get("runtime", "?")}). Logs are in this folder.', '']))
    fail(reason)


def default_workers() -> int:
    """How many simulators journeys may run on at once: $BSTACK_VERIFY_WORKERS, else `verify_workers` in
    ~/.config/b-stack/config.toml, else 1. A machine setting: a fresh clone's first boot costs minutes (see Parallel
    journeys), more than splitting a few journeys saves, so set it only after timing verify on that machine."""
    if os.environ.get('BSTACK_VERIFY_WORKERS'):
        return max(1, int(os.environ['BSTACK_VERIFY_WORKERS']))
    return machine_setting('verify_workers', 1)


def shards(entries: list[dict], count: int) -> list[list[str]]:
    """Split the mapped journeys the source scan can see into up to `count` groups, one per simulator.

    Group 0 runs everything except the other groups' journeys (-skip-testing), so a journey the scan can't see, or one
    missing from the map, still runs and is still caught. The others run only their own journeys (-only-testing).
    """
    named = sorted({j['test'] for e in entries for j in e['journeys']} & journeys_in_code())
    count = max(1, min(count, len(named)))
    return [named[k::count] for k in range(count)]


def test_target(xctestrun: Path) -> str | None:
    """The one UI test target in the .xctestrun (journey IDs for -only-testing are Target/Class/test), else None."""
    plan = plistlib.loads(xctestrun.read_bytes())
    targets = [t for config in plan.get('TestConfigurations', []) for t in config.get('TestTargets', [])]
    targets += [v for k, v in plan.items() if isinstance(v, dict) and 'TestBundlePath' in v]
    names = {t.get('BlueprintName') for t in targets}
    return names.pop() if len(names) == 1 and None not in names else None


CLONES = ROOT / '.build/verify-clones.json'


def make_clones(udid: str, count: int) -> list[str]:
    """Clone a shut-down simulator `count` times. Clones are recorded in CLONES until deleted, so `cleanup` can remove
    any a crashed run left behind."""
    name = state(udid).get('name', 'iPhone')
    made: list[str] = []
    for k in range(1, count + 1):
        proc = sh(['xcrun', 'simctl', 'clone', udid, f'b-stack verify clone {k} ({name})'])  # never matches devices()'s filter
        if proc.returncode != 0 or not proc.stdout.strip():
            fail(f'could not clone simulator {udid} ({proc.stderr.strip()}); running on fewer simulators')
            break
        made.append(proc.stdout.strip())
        CLONES.write_text(json.dumps(sorted(set(made) | set(recorded_clones()))))
    return made


def recorded_clones() -> list[str]:
    return json.loads(CLONES.read_text()) if CLONES.is_file() else []


def delete_clones(clones: list[str]) -> None:
    for clone in clones:
        sh(['xcrun', 'simctl', 'shutdown', clone], timeout=120)
        sh(['xcrun', 'simctl', 'delete', clone], timeout=120)
    left = [c for c in recorded_clones() if c not in clones]
    if left:
        CLONES.write_text(json.dumps(left))
    else:
        CLONES.unlink(missing_ok=True)


def in_parallel(work: list) -> list:
    """Run functions on threads and return their results in order; an exception is returned, not raised."""
    results: list = [None] * len(work)

    def call(i: int) -> None:
        try:
            results[i] = work[i]()
        except BaseException as error:  # noqa: BLE001 - handed back to the caller
            results[i] = error

    threads = [threading.Thread(target=call, args=(i,)) for i in range(len(work))]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
    return results


def run(generated: bool = False, prebuilt: Path | None = None, workers: int | None = None) -> bool:
    """Run the mapped journeys. check.py passes generated=True when it already generated the project, and prebuilt when
    its compiler gate already built AppVerify for testing, so neither happens twice."""
    latest = ROOT / '.build/evidence/latest'
    latest.unlink(missing_ok=True)  # never leave an older run's evidence looking current
    entries, errors = check_map()
    for error in errors:
        fail(error)
    if errors:
        return False

    sha = commit()
    directory = ROOT / '.build/evidence' / f'{datetime.now().strftime("%Y%m%d-%H%M%S")}-{sha}'
    directory.mkdir(parents=True)
    latest.symlink_to(directory.name)
    device: dict = {}
    if not generated and not generate():
        write_failure(directory, sha, device, 'project generation (tuist install/generate) failed')
        return False
    try:
        udid = simulator()
    except (SystemExit, subprocess.CalledProcessError) as missing:  # no simulator, or simctl itself failed
        write_failure(directory, sha, device, f'could not pick a simulator: {missing}')
        return False

    result_bundle = directory / 'Journeys.xcresult'
    groups = shards(entries, default_workers() if workers is None else workers)
    clones: list[str] = []
    # Clones need a shut-down simulator. One that's already booted is someone else's: borrow it, alone.
    if len(groups) > 1 and state(udid).get('state') == 'Shutdown':
        clones = make_clones(udid, len(groups) - 1)
    booted_here = boot(udid)
    devices = [udid]
    status = 0
    step = 'booting the simulator'
    try:
        for clone in clones:
            boot(clone)
        ready = in_parallel([lambda d=d: wait_booted(d) for d in [udid] + clones])
        if ready[0] is not True:
            write_failure(directory, sha, device, f'simulator {udid} did not finish booting')
            return False
        devices = [d for d, ok in zip([udid] + clones, ready) if ok is True]
        device = state(udid)
        step = 'build for testing'
        if prebuilt is not None:
            (directory / 'build.log').write_text(f'Not built here: running {prebuilt}, built by check.py\'s compiler gate.\n')
            xctestrun = isolated_xctestrun(prebuilt)
        else:
            built = sh(['xcodebuild', '-workspace', 'Starter.xcworkspace', '-scheme', SCHEME,
                        '-destination', f'platform=iOS Simulator,id={udid}', '-derivedDataPath', str(DERIVED),
                        '-skipMacroValidation', 'build-for-testing', 'CODE_SIGNING_ALLOWED=NO'],
                       timeout=JOURNEY_TIMEOUT, log=directory / 'build.log')
            xctestrun = isolated_xctestrun() if built.returncode == 0 else None
        if xctestrun is None:
            errors = [l.strip() for l in (directory / 'build.log').read_text(errors='replace').splitlines() if 'error:' in l]
            write_failure(directory, sha, device, 'build for testing failed: '
                          + ('; '.join(dict.fromkeys(errors[:10])) or f'see {directory / "build.log"}'))
            return False
        step = 'the journeys'
        target = test_target(xctestrun)
        if target is None or len(devices) == 1:
            groups = [[]]  # one simulator runs everything
        elif len(devices) < len(groups):
            groups = shards(entries, len(devices))
        others = [f'{target}/{test}' for group in groups[1:] for test in group]
        plans = [(devices[0], [f'-skip-testing:{t}' for t in others])]
        plans += [(devices[k], [f'-only-testing:{target}/{t}' for t in group]) for k, group in enumerate(groups[1:], 1)]
        bundles = [result_bundle] if len(plans) == 1 else [directory / f'Journeys-{k}.xcresult' for k in range(len(plans))]
        logs = [directory / 'xcodebuild.log'] if len(plans) == 1 else [directory / f'xcodebuild-{k}.log' for k in range(len(plans))]
        outcomes = in_parallel([
            lambda d=d, f=f, b=b, l=l: sh(['xcodebuild', 'test-without-building', '-xctestrun', str(xctestrun),
                                           '-destination', f'platform=iOS Simulator,id={d}', '-resultBundlePath', str(b)] + f,
                                          timeout=JOURNEY_TIMEOUT, log=l)
            for (d, f), b, l in zip(plans, bundles, logs)])
        if len(plans) > 1:
            # One log in run order, so failures read the same as from a single run.
            (directory / 'xcodebuild.log').write_text(''.join(
                f'==== simulator {d}: {" ".join(f) or "all journeys"}\n' + l.read_text(errors='replace')
                for (d, f), l in zip(plans, logs) if l.is_file()))
        for outcome in outcomes:
            if isinstance(outcome, subprocess.TimeoutExpired):
                raise outcome
            if isinstance(outcome, BaseException):
                raise outcome
            status = status or outcome.returncode
        present = [b for b in bundles if b.exists()]
        if len(plans) > 1 and present:
            merged = sh(['xcrun', 'xcresulttool', 'merge', '--output-path', str(result_bundle)] + [str(b) for b in present]) \
                if len(present) > 1 else None
            if merged is None:
                present[0].rename(result_bundle)
            elif merged.returncode == 0:
                for bundle in present:
                    shutil.rmtree(bundle)
            else:
                write_failure(directory, sha, device, f'could not merge the result bundles in {directory}: '
                              f'{merged.stderr.strip()}')
                return False
    except subprocess.TimeoutExpired:
        write_failure(directory, sha, device, f'{step} timed out after {JOURNEY_TIMEOUT}s. Logs are in {directory}'
                      + ('' if booted_here else '. The simulator was already booted, so it was left running; it may need a restart.'))
        return False
    finally:
        try:
            delete_clones(clones)
        except subprocess.TimeoutExpired:  # never let cleanup hide the run's own result; `verify.py cleanup` retries
            fail(f'could not delete simulator clones {clones}; run `python3 scripts/verify.py cleanup`')
        if booted_here:
            try:
                shutdown(udid)
            except subprocess.TimeoutExpired:  # never let a slow shutdown hide the run's own result or evidence
                fail(f'simulator {udid} did not shut down within 120 s; shut it down with `xcrun simctl shutdown {udid}`')
    if len(devices) > 1:
        device = {**device, 'clones': len(devices) - 1}

    results: dict[str, dict] = {}
    system: list[dict] = []
    exported = False
    if result_bundle.exists():
        exported = sh(['xcrun', 'xcresulttool', 'export', 'attachments', '--path', str(result_bundle),
                       '--output-path', str(directory / 'attachments')]).returncode == 0
        tree = sh(['xcrun', 'xcresulttool', 'get', 'test-results', 'tests', '--path', str(result_bundle)])
        if tree.returncode == 0:
            found: list[dict] = []
            for node in json.loads(tree.stdout).get('testNodes', []):
                collect_tests(node, [], found)
            # Xcode reports a runner crash as a test under "System Failures"; that's a failed run, not a journey.
            system = [t for t in found if t['test'].startswith('System Failures/')]
            results = {t['test']: t for t in found if t not in system}
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
            elif (used := fixtures_used(shots.get(journey['test'], []))) != {journey['fixture']}:
                ok = False
                fail(f'journey {journey["test"]} launched with {sorted(used) or "no recorded fixture"}, but the map says '
                     f'only "{journey["fixture"]}". Launch through the journey helper, which records each fixture; '
                     'a journey that needs two starting states is two journeys.')
    for test in sorted(set(results) - named):
        ok = False
        fail(f'journey {test} ran but is not in the feature map. Name it under the feature it proves.')
    if result_bundle.exists() and not exported:
        ok = False
        fail(f'could not export screenshots from {result_bundle}')
    for crash in system:
        ok = False
        fail(f'the test runner failed: {crash["test"].removeprefix("System Failures/")}: {"; ".join(crash["messages"])}')
    if status != 0 and not any(r['result'] != 'Passed' for r in results.values()):
        log = (directory / 'xcodebuild.log').read_text(errors='replace')
        reasons = log.split('Testing failed:', 1)[1].strip().splitlines()[:5] if 'Testing failed:' in log else []
        fail('the test run failed before any journey finished: ' + ('; '.join(l.strip() for l in reasons) or f'see {directory / "xcodebuild.log"}'))
    print(f'[verify] evidence: {directory / "evidence.md"}', flush=True)
    return ok


# ---------------------------------------------------------------- explore

def launch(fixture: str, reset: bool) -> bool:
    if fixture not in known_fixtures():
        fail(f'unknown fixture "{fixture}". Known fixtures: {", ".join(sorted(known_fixtures()))}.')
        return False
    udid = simulator()
    session = json.loads(SESSION.read_text()) if SESSION.is_file() else {}
    if session and session.get('udid') != udid:  # relaunching on the session's own simulator is fine
        fail(f'a session is already open on simulator {session.get("udid")}; run `python3 scripts/verify.py cleanup` first')
        return False
    if not generate():
        return False
    proc = sh(['xcodebuild', '-workspace', 'Starter.xcworkspace', '-scheme', SCHEME,
               '-destination', f'platform=iOS Simulator,id={udid}', '-derivedDataPath', str(DERIVED),
               '-quiet', '-skipMacroValidation', 'build', 'CODE_SIGNING_ALLOWED=NO'])
    if proc.returncode != 0:
        print((proc.stdout + proc.stderr).strip()[-3000:])
        return False
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
    time.sleep(2)  # an app that crashes on launch (e.g. a bad fixture) is gone within this
    if BUNDLE_ID not in sh(['xcrun', 'simctl', 'spawn', udid, 'launchctl', 'list']).stdout:
        fail('AppVerify exited right after launch. Check the fixture, then `python3 scripts/verify.py doctor`.')
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
    if recorded_clones():
        left = recorded_clones()
        delete_clones(left)
        print(f'[verify] deleted simulator clones a run left behind: {", ".join(left)}')
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
    parser.add_argument('--workers', type=int, help='run: most simulators to split journeys across '
                        '(default $BSTACK_VERIFY_WORKERS, else verify_workers in the b-stack config, else 1)')
    parser.add_argument('--generated', action='store_true', help=argparse.SUPPRESS)  # check.py already generated
    parser.add_argument('--xctestrun', type=Path, help=argparse.SUPPRESS)  # check.py's compiler gate already built it
    args = parser.parse_args()
    link_build_dirs(ROOT)
    if args.command == 'map':
        _, problems = check_map()
        for problem in problems:
            fail(problem)
        print('[verify] feature map OK' if not problems else '', end='\n' if not problems else '')
        ok = not problems
    elif args.command == 'run':
        ok = run(args.generated, args.xctestrun, args.workers)
    elif args.command == 'launch':
        ok = launch(args.fixture, args.reset)
    elif args.command == 'doctor':
        ok = doctor()
    else:
        ok = cleanup()
    sys.exit(0 if ok else 1)
