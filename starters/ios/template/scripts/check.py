"""Run every enforcement gate. Exit non-zero if any gate fails. CI runs this; agents run it before handing back.

Gates:
  compiler   generate the Xcode project with Tuist, then build every target with strict Swift settings
  tuist      every import of a project module is a declared dependency, and every declared one is used
  swiftlint  no force unwraps, force try/cast, or suppression comments
  harmonize  architecture rules in Rules/ (module shape and allowed imports, no singletons, concurrency escapes, ...)
  tests      unit tests on an iOS Simulator (TCA TestStore tests are exhaustive)
  verify     the feature map is complete, and every journey passes in the running app (scripts/verify.py)

Gates that don't depend on each other run at the same time: swiftlint, harmonize and tuist alongside the Xcode gates.
compiler, tests and verify share one build folder and simulator, so they run one after another, and verify runs the
AppVerify build the compiler gate just made instead of building it again. Each gate's output is printed whole when it
finishes, followed by its result and time; a summary in gate order comes last.

Usage: python3 scripts/check.py [--only GATE ...]
"""
from concurrent.futures import Future, ThreadPoolExecutor
from pathlib import Path
import argparse
import os
import subprocess
import sys
import threading
import time
from xml.etree import ElementTree

sys.path.insert(0, str(Path(__file__).resolve().parent))
from handback import record_check, snapshot  # noqa: E402
from paths import link_build_dirs  # noqa: E402
from simulator import simulator  # noqa: E402
from tools import tool_path  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
GATES = ['compiler', 'tuist', 'swiftlint', 'harmonize', 'tests', 'verify']
XCODE = ('compiler', 'tests', 'verify')  # share .build/DerivedData and the simulator: one at a time
ENV = {**os.environ, 'TUIST_STATS_OPT_OUT': '1', 'TUIST_DISABLE_ANALYTICS': '1'}
DERIVED = ROOT / '.build/DerivedData'
PRINT = threading.Lock()
STOP = threading.Event()  # set on Ctrl-C: gates not yet started are skipped


class Step:
    """One command's result: whether it passed, and the lines to show for it (empty when it passed)."""

    def __init__(self, ok: bool, report: str = ''):
        self.ok, self.report = ok, report


def run(cmd: list[str]) -> Step:
    proc = subprocess.run(cmd, cwd=ROOT, env=ENV, capture_output=True, text=True)
    if proc.returncode == 0:
        return Step(True)
    output = proc.stdout + proc.stderr
    errors = [l.strip() for l in output.splitlines() if 'error:' in l and len(l) < 1000]
    return Step(False, '\n'.join(list(dict.fromkeys(errors))[:50]) if errors else output.strip()[-4000:])


def chain(*steps) -> Step:
    """Run steps (each a Step or a function returning one) in order, stopping at the first that fails."""
    for step in steps:
        result = step() if callable(step) else step
        if not result.ok:
            return result
    return Step(True)


def xcodebuild(scheme: str, destination: str, action: str) -> list[str]:
    return ['xcodebuild', '-workspace', 'Starter.xcworkspace', '-scheme', scheme, '-destination', destination,
            '-derivedDataPath', '.build/DerivedData', '-quiet', '-skipMacroValidation', action, 'CODE_SIGNING_ALLOWED=NO']


def unrun_tests() -> Step:
    """Every Targets/*Tests folder must be a test target that a scheme runs, or its tests would never run and the gate
    would still pass. Unit-test targets are in the UnitTests scheme automatically (Project.swift); UI tests run in verify."""
    run_by: set[str] = set()
    for scheme in (ROOT / 'Starter.xcodeproj/xcshareddata/xcschemes').glob('*.xcscheme'):
        for testable in ElementTree.parse(scheme).getroot().iterfind('TestAction/Testables/TestableReference'):
            if testable.get('skipped') != 'YES':
                run_by |= {ref.get('BlueprintName') for ref in testable.iter('BuildableReference')}
    unrun = sorted(d.name for d in (ROOT / 'Targets').iterdir() if d.is_dir() and d.name.endswith('Tests')
                   and d.name not in run_by)
    if unrun:
        return Step(False, f'[tests] no scheme runs the tests in {", ".join("Targets/" + n for n in unrun)}. Declare its feature '
                           'in Tuist/ProjectDescriptionHelpers/Features.swift; the UnitTests scheme runs every unit-test target.')
    return Step(True)


def dump_project(tuist: str) -> Step:
    """Write the project Tuist builds from Project.swift to .build/tuist-project.json, for the harmonize gate's check
    that its targets and dependencies are the ones the module shape gives Features.swift."""
    out = ROOT / '.build/tuist-project.json'
    out.unlink(missing_ok=True)
    proc = subprocess.run([tuist, 'dump', 'project'], cwd=ROOT, env=ENV, capture_output=True, text=True)
    if proc.returncode != 0:
        return Step(False, (proc.stdout + proc.stderr).strip()[-4000:])
    out.write_text(proc.stdout)
    return Step(True)


def built_xctestrun(since: float) -> Path | None:
    """The AppVerify .xctestrun written by a build-for-testing that started at `since`, if there is one."""
    fresh = [p for p in (DERIVED / 'Build/Products').glob('AppVerify_*.xctestrun') if p.stat().st_mtime >= since]
    return max(fresh, key=lambda p: p.stat().st_mtime) if fresh else None


def check(selected: list[str]) -> list[str]:
    """Run the selected gates and return the ones that failed."""
    tuist = str(tool_path('tuist'))  # resolved (and downloaded if needed) once, before any thread uses it
    swiftlint = str(tool_path('swiftlint')) if 'swiftlint' in selected else ''
    results: dict[str, bool] = {}
    times: dict[str, float] = {}

    def report(name: str, step: Step, started: float) -> bool:
        results[name], times[name] = step.ok, time.monotonic() - started
        with PRINT:
            if step.report:
                print(step.report)
            print(f'{"PASS" if step.ok else "FAIL"} {name}  ({times[name]:.0f}s)', flush=True)
        return step.ok

    # Before any other Tuist command starts, so two never write its manifest cache at once (takes about a second).
    dumped = dump_project(tuist) if 'harmonize' in selected else Step(True)

    with ThreadPoolExecutor(max_workers=8) as pool:
        # Every Tuist command needs the packages installed; install once, so two installs never race.
        # verify alone generates for itself, after its feature-map check, so a map error fails before any Tuist work.
        install: Future | None = None
        if any(g in selected for g in ('compiler', 'tests', 'tuist')):
            install = pool.submit(run, [tuist, 'install'])
        generated: Future | None = None
        if any(g in selected for g in ('compiler', 'tests')):
            generated = pool.submit(lambda: chain(install.result(), lambda: run([tuist, 'generate', '--no-open'])))

        tuist_done = threading.Event()  # verify without compiler/tests runs Tuist itself: only after this gate
        if 'tuist' not in selected:
            tuist_done.set()

        def tuist_gate(started: float) -> None:
            # After generate, so two Tuist commands never write its manifest cache at once. It doesn't touch the
            # generated project (checked with Tuist 4.216.7), so it runs alongside the Xcode builds.
            try:
                if generated:
                    generated.result()
                report('tuist', chain(install.result(),
                                      lambda: run([tuist, 'inspect', 'dependencies', '--only', 'implicit', '--only', 'redundant'])),
                       started)
            finally:
                tuist_done.set()

        def xcode_lane(started: float) -> None:
            xctestrun: Path | None = None
            if 'compiler' in selected:
                build_started = time.time() - 1
                ok = report('compiler', chain(
                    generated.result(),
                    lambda: run(xcodebuild('App', 'generic/platform=iOS Simulator', 'build')),
                    lambda: run(xcodebuild('AppVerify', 'generic/platform=iOS Simulator', 'build-for-testing'))),
                    started)
                xctestrun = built_xctestrun(build_started) if ok else None
                started = time.monotonic()
            if 'tests' in selected and not STOP.is_set():
                report('tests', chain(
                    generated.result(),
                    unrun_tests,
                    lambda: run(xcodebuild('UnitTests', f'platform=iOS Simulator,id={simulator()}', 'test'))),
                    started)
                started = time.monotonic()
            if 'verify' in selected and not STOP.is_set():
                if not generated:
                    tuist_done.wait()  # verify.py installs and generates with Tuist itself
                with PRINT:
                    print('verify: running the journeys (output when they finish; evidence in .build/evidence/latest)',
                          flush=True)
                cmd = [sys.executable, str(ROOT / 'scripts/verify.py'), 'run']
                if generated and generated.result().ok:
                    cmd.append('--generated')
                if xctestrun:
                    cmd += ['--xctestrun', str(xctestrun)]  # the build the compiler gate just made, from these sources
                proc = subprocess.run(cmd, cwd=ROOT, env=ENV, capture_output=True, text=True)
                report('verify', Step(proc.returncode == 0, (proc.stdout + proc.stderr).strip()), started)

        jobs = []
        start = time.monotonic()
        if 'swiftlint' in selected:
            jobs.append(pool.submit(lambda: report('swiftlint', run([swiftlint, 'lint', '--strict', '--quiet']), start)))
        if 'harmonize' in selected:
            # Serial: run in parallel, Harmonize 1.3.0 rules can deadlock on its shared source cache and hang forever.
            jobs.append(pool.submit(lambda: report('harmonize', chain(dumped, lambda: run(
                ['swift', 'test', '--no-parallel', '--package-path', 'Rules', '--scratch-path', '.build/rules'])), start)))
        if 'tuist' in selected:
            jobs.append(pool.submit(tuist_gate, start))
        if any(g in XCODE for g in selected):
            jobs.append(pool.submit(xcode_lane, start))
        try:
            for job in jobs:
                job.result()  # re-raises a crash in a gate's thread instead of reporting it as a pass
        except KeyboardInterrupt:
            STOP.set()  # the running commands got Ctrl-C too; don't start the next gate in the Xcode lane
            raise

    if len(selected) > 1:
        print('Summary: ' + ', '.join(f'{name} {"PASS" if results[name] else "FAIL"}' for name in GATES if name in selected),
              flush=True)
    return [name for name in GATES if name in selected and not results[name]]


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--only', action='append', choices=GATES)
    chosen = parser.parse_args().only or GATES
    link_build_dirs(ROOT)
    before = snapshot(ROOT)  # observe mode: a run counts only for files that didn't change while it ran
    try:
        selected = [g for g in GATES if g in chosen]
        failed = check(selected)
    except KeyboardInterrupt:
        sys.exit('\nStopped.')  # an interrupted run isn't a check, so it isn't recorded
    record_check(ROOT, selected, failed, before)  # observe mode: lets scripts/handback.py tell whether hand-backs were checked
    sys.exit(1 if failed else 0)
