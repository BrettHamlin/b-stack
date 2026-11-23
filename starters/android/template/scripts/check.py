"""Run every enforcement gate. Exit non-zero if any gate fails. CI runs this; agents run it before handing back.

Gates:
  compiler  Kotlin 2.4 and the Android Gradle Plugin build every module with warnings as errors, each with its role's
            settings (build-logic/, arch/shape.json); common modules also compile as real common code (no JDK)
  detekt    detekt with type resolution (arch/detekt.yml, plus our rules in arch/detekt-rules): no !!, as, catch-all
            else, throwing lookups, hard-coded dispatchers, GlobalScope or runBlocking
  konsist   the architecture tests in arch/konsist: imports by role, no singletons or service locators, no ad-hoc
            scopes or threads, typed UI identifiers, no I/O in logic, exhaustive tests, no skipped tests
  arch      module folders, source sets and files against the module shape; no suppressions or opt-ins (arch.py)
  deps      every library from Google's or Maven Central's repository, checked against gradle/verification-metadata.xml,
            with an allowed license (deps.py)
  tests     every unit and property test in every module; a module whose tests didn't run, or a skipped test, fails
  verify    the feature map is complete, and every journey passes in app-verify on the emulator (verify.py)

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
GATES = ['compiler', 'detekt', 'konsist', 'arch', 'deps', 'tests', 'verify']
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


def konsist(env: dict) -> tuple[bool, str]:
    clear_results('arch/konsist')
    ok, output = gradle(env, ':arch:konsist:test')
    failures = [message for _, status, message in test_results('arch/konsist') if status != 'passed']
    if failures:
        return False, '\n'.join(failures)
    return ok, output


def tests(env: dict) -> tuple[bool, str]:
    """Every module's tests run and pass. A module with test sources and no results fails, and so does a skipped test,
    however it was skipped (Konsist bans @Ignore; this catches the rest)."""
    with_tests = [(folder, role) for folder, role in modules() if role['kind'] in ('common', 'android-library', 'android-app')
                  and ((ROOT / folder / 'src/commonTest').is_dir() or (ROOT / folder / 'src/test').is_dir())]
    for folder, _ in with_tests:
        clear_results(folder)
    ok, output = gradle(env, 'jvmTest', 'testDebugUnitTest')
    problems = []
    for folder, _ in with_tests:
        results = test_results(folder)
        if not results:
            problems.append(f'[tests-always-run] {folder} has tests, but none ran. Every module\'s tests run in this '
                            'gate (jvmTest, testDebugUnitTest); if they can\'t, stop and report.')
        problems += [f'[tests-always-run] {folder}: {name} was skipped. Every test runs: fix the code or the test, or '
                     'stop and report.' for name, status, _ in results if status == 'skipped']
    if problems:
        return False, '\n'.join([output, *problems])
    return ok, output


def gate(name: str, env: dict) -> tuple[bool, str]:
    if name == 'compiler':
        return gradle(env, 'assembleDebug', 'compileCommonMainKotlinMetadata', 'compileTestKotlinJvm',
                      'compileDebugUnitTestKotlin', 'testClasses')
    if name == 'detekt':
        return gradle(env, 'detektMainJvm', 'detektTestJvm', 'detektMain', 'detektTest')
    if name == 'konsist':
        return konsist(env)
    if name == 'arch':
        found = arch_findings()
        return not found, '\n'.join(found)
    if name == 'deps':
        proc = subprocess.run([sys.executable, str(ROOT / 'scripts/deps.py')], cwd=ROOT, env=env, capture_output=True,
                              text=True)
        return proc.returncode == 0, (proc.stdout + proc.stderr).strip()
    if name == 'tests':
        return tests(env)
    proc = subprocess.run([sys.executable, str(ROOT / 'scripts/verify.py'), 'run'], cwd=ROOT, env=env,
                          capture_output=True, text=True)
    return proc.returncode == 0, (proc.stdout + proc.stderr).strip()


def check(selected: list[str]) -> list[str]:
    env = android_env()
    before = snapshot(ROOT)  # observe mode: a run counts only for files that didn't change while it ran
    results: dict[str, bool] = {}
    for name in selected:
        started = time.monotonic()
        ok, output = gate(name, env)
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
