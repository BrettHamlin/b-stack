"""Run every enforcement gate. Exit non-zero if any gate fails. CI runs this; agents run it before handing back.

Gates:
  compiler  Kotlin 2.4 and the Android Gradle Plugin build every module with warnings as errors, each with its role's
            settings (build-logic/, arch/shape.json); common modules also compile as real common code (no JDK)
  detekt    detekt with type resolution (arch/detekt.yml, plus our rules in arch/detekt-rules): no !!, as, catch-all
            else, throwing lookups, hard-coded dispatchers, GlobalScope or runBlocking
  lint      Android Lint's NewApi on every Android module: no call to an API newer than minSdk 29 without a version
            check (build-logic)
  konsist   the architecture tests in arch/konsist: imports by role, no singletons or service locators, no ad-hoc
            scopes or threads, typed UI identifiers, no I/O in logic, exhaustive tests, no skipped tests
  arch      module folders, source sets and files against the module shape; no suppressions or opt-ins (arch.py)
  deps      every library from Google's or Maven Central's repository, checked against gradle/verification-metadata.xml,
            with an allowed license (deps.py)
  settings  the enforcement settings in effect (Gradle, Kotlin, Android, Lint, detekt, test tasks) are the ones recorded
            in arch/settings.json, and CODEOWNERS covers every enforcement path (settings.py)
  tests     every unit and property test in every module; a module whose tests didn't run, or a skipped test, fails
  verify    the feature map is complete, and every journey passes in app-verify on the emulator (verify.py)
  release   every journey passes against app-verify's release build (R8, as the shipped app is built), and the
            shipped app's release build starts (verify.py release)

Each gate's output is printed when it fails, followed by its result and time; a summary in gate order comes last.
Every run is recorded against the git tree of the files it saw (scripts/handback.py, observe mode: it never blocks).

Usage: python3 scripts/check.py [--only GATE ...]
"""
from pathlib import Path
import argparse
import re
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parent))
from arch import findings as arch_findings, modules  # noqa: E402
from handback import record_check, snapshot  # noqa: E402
from tools import android_env, gradle_command  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
GATES = ['compiler', 'detekt', 'lint', 'konsist', 'arch', 'deps', 'settings', 'tests', 'verify', 'release']
RESULTS = ROOT / '.build/gradle'


def gradle(env: dict, *tasks: str) -> tuple[bool, str]:
    proc = subprocess.run(gradle_command('--continue', *tasks), cwd=ROOT, env=env, capture_output=True, text=True)
    output = proc.stdout + proc.stderr
    # Gradle's own advice after a failure says nothing about the code.
    noise = re.compile(r'^(\* Try:|> Run with --|> Get more help|BUILD FAILED|\d+ actionable tasks|Configuration cache|'
                       r'Reusing configuration|Calculating task graph|\[Incubating\] Problems report|Deprecated Gradle|'
                       r'You can use \'--warning-mode|For more on this|Successfully generated)')
    lines = [l for l in output.splitlines() if l.strip() and not noise.match(l.strip())]
    return proc.returncode == 0, '\n'.join(lines)


def test_results(folder: str) -> list[tuple[str, str, str]]:
    """(test, status, message) for every JUnit XML result under .build/gradle/<module>/test-results."""
    found = []
    for path in sorted((RESULTS / folder).glob('test-results/**/*.xml')):
        suite = ET.parse(path).getroot()
        for case in suite.iter('testcase'):
            failure = case.find('failure') if case.find('failure') is not None else case.find('error')
            status = 'skipped' if case.find('skipped') is not None else 'failed' if failure is not None else 'passed'
            found.append((f'{case.get("classname")}.{case.get("name")}', status,
                          (failure.get('message') or failure.text or '') if failure is not None else ''))
    return found


def clear_results(folder: str) -> None:
    for path in (RESULTS / folder).glob('test-results/**/*.xml'):
        path.unlink()


GRADLE_GATES = {
    'compiler': ('assembleDebug', 'compileCommonMainKotlinMetadata', 'compileTestKotlinJvm', 'compileDebugUnitTestKotlin',
                 'testClasses'),
    'detekt': ('detektMainJvm', 'detektTestJvm', 'detektMain', 'detektTest'),
    'lint': ('lintDebug',),
    'konsist': (':arch:konsist:test',),
    'tests': ('jvmTest', 'testDebugUnitTest'),
}


# Gates whose Gradle run is never shared. Lint and detekt in one Gradle run leave detekt's Kotlin environment alive in
# the daemon (detekt 2.0.0-alpha.6, AGP 9.5.2): a later detekt run in that daemon read a module's jar as it was then, and
# failed on an entry the rebuilt jar no longer had.
ALONE = {'lint'}


def lint_reports() -> list[Path]:
    return sorted(RESULTS.glob('**/reports/lint-results-debug.txt'))


def tested_modules() -> list[str]:
    return [folder for folder, role in modules() if role['kind'] in ('common', 'android-library', 'android-app')
            and ((ROOT / folder / 'src/commonTest').is_dir() or (ROOT / folder / 'src/test').is_dir())]


def clear(name: str) -> None:
    """Remove the gate's results from an earlier run, so it reads only this run's."""
    if name == 'lint':
        for report in lint_reports():
            report.unlink()
    elif name == 'konsist':
        clear_results('arch/konsist')
    elif name == 'tests':
        for folder in tested_modules():
            clear_results(folder)


def judge(name: str, ok: bool, output: str) -> tuple[bool, str]:
    """The gate's result from its Gradle run's and the results it left."""
    if name == 'konsist':
        results = test_results('arch/konsist')
        if not results:
            return False, '\n'.join([output, '[konsist] the architecture tests in arch/konsist didn\'t run.'])
        failures = [message for _, status, message in results if status != 'passed']
        if failures:
            return False, '\n'.join(failures)
    if name == 'lint':
        if not ok:
            found = [r.read_text().strip() for r in lint_reports()]
            output = '\n'.join([output, *(f for f in found if f and not f.startswith('No issues found'))])
        if not ok and '[NewApi]' in output:
            output += ('\n[minimum-os-apis] A call above minSdk 29 compiles, but crashes on the older devices the app '
                       'supports. Check the version first (if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) { ... } '
                       'with a path for older versions), or use the AndroidX compat helper (ContextCompat and the like). '
                       'Never raise minSdk or silence Lint; if neither works, stop and report.')
    if name == 'tests':
        # Every module's tests run and pass. A module with test sources and no results fails, and so does a skipped
        # test, however it was skipped (Konsist bans @Ignore; this catches the rest).
        problems = []
        for folder in tested_modules():
            results = test_results(folder)
            if not results:
                problems.append(f'[tests-always-run] {folder} has tests, but none ran. Every module\'s tests run in '
                                'this gate (jvmTest, testDebugUnitTest); if they can\'t, stop and report.')
            problems += [f'[tests-always-run] {folder}: {name} was skipped. Every test runs: fix the code or the test, '
                         'or stop and report.' for name, status, _ in results if status == 'skipped']
            problems += [f'{folder}: {name} failed: {message.strip()[:500]}' for name, status, message in results
                         if status == 'failed']
        if problems:
            return False, '\n'.join([output, *problems])
    return ok, output


def together(names: list[str], env: dict) -> dict[str, tuple[bool, str]]:
    """The Gradle gates' results from one Gradle run of all their tasks, when that run passes: the same tasks on the same
    files as one run per gate, without starting and configuring the build once per gate. When it fails, {}: each gate
    then runs on its own, so a failure is reported by the gate it belongs to, as before."""
    for name in names:
        clear(name)
    ok, _ = gradle(env, *dict.fromkeys(t for name in names for t in GRADLE_GATES[name]))
    return {name: judge(name, True, '') for name in names} if ok else {}


def gate(name: str, env: dict) -> tuple[bool, str]:
    if name in GRADLE_GATES:
        clear(name)
        return judge(name, *gradle(env, *GRADLE_GATES[name]))
    if name == 'arch':
        found = arch_findings()
        return not found, '\n'.join(found)
    if name in ('deps', 'settings'):
        proc = subprocess.run([sys.executable, str(ROOT / f'scripts/{name}.py')], cwd=ROOT, env=env, capture_output=True,
                              text=True)
        return proc.returncode == 0, (proc.stdout + proc.stderr).strip()
    proc = subprocess.run([sys.executable, str(ROOT / 'scripts/verify.py'), 'release' if name == 'release' else 'run'],
                          cwd=ROOT, env=env,
                          capture_output=True, text=True)
    return proc.returncode == 0, (proc.stdout + proc.stderr).strip()


def check(selected: list[str]) -> list[str]:
    env = android_env()
    before = snapshot(ROOT)  # observe mode: a run counts only for files that didn't change while it ran
    results: dict[str, bool] = {}
    shared = [n for n in selected if n in GRADLE_GATES and n not in ALONE]
    joint: dict[str, tuple[bool, str]] | None = None if len(shared) > 1 else {}
    for name in selected:
        started = time.monotonic()
        if joint is None and name in shared:
            joint = together(shared, env)
            if joint:
                print(f'One Gradle run for {", ".join(shared)}: passed  ({time.monotonic() - started:.0f}s)', flush=True)
            else:
                print(f'One Gradle run for {", ".join(shared)}: failed; running each gate on its own to report it  '
                      f'({time.monotonic() - started:.0f}s)', flush=True)
                started = time.monotonic()
        ok, output = joint[name] if joint and name in joint else gate(name, env)
        results[name] = ok
        if not ok and output:
            print(output)
        print(f'{"PASS" if ok else "FAIL"} {name}  ({time.monotonic() - started:.0f}s)', flush=True)
    if len(selected) > 1:
        print('Summary: ' + ', '.join(f'{n} {"PASS" if results[n] else "FAIL"}' for n in selected), flush=True)
    failed = [n for n in selected if not results[n]]
    record_check(ROOT, selected, failed, before)  # observe mode: lets scripts/handback.py tell whether hand-backs were checked
    return failed


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--only', action='append', choices=GATES)
    chosen = parser.parse_args().only or GATES
    try:
        failed = check([g for g in GATES if g in chosen])
    except KeyboardInterrupt:
        sys.exit('\nStopped.')  # an interrupted run isn't a check, so it isn't recorded
    sys.exit(1 if failed else 0)
