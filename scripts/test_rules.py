"""Prove every rule fires, by running each case through the project's own gate command (scripts/check.py).

For each case, Targets/ and feature-map/ are reset to the project's, and the case's own copies are overlaid:
  fail case   `check.py --only <enforced_by>` must fail, and its output must contain the case's diagnostic
  pass case   `check.py` must pass every gate except verify, so correct code never trips any rule
The untouched project must pass every gate, including verify (journeys in the running app); if it doesn't, no case
counts and the run fails. Pass cases skip verify because it drives a simulator for minutes per run; verify's own fail
cases still run it. A case may add a target the project doesn't have by listing it in `adds_targets`; otherwise a
missing target is a SKIP.

Cases run in parallel, each worker in its own copy of the project with its own build folder, so no case sees
another's files and the order doesn't matter. Cases that need a simulator (pass cases, and tests and verify fail cases)
run only on workers that have one: one per --simulator, each used by one worker at a time. Results print in case
order, whichever finishes first. Workers' folders are kept per project checkout: a worker's first run builds
everything (TCA, Harmonize) in its folder, later runs are incremental.

Default project: starters/ios/template. Pass --project <new-app> to prove a new app's setup enforces the rules.
Work and tool downloads go to the cache folder if one is configured (see starters/ios/template/scripts/paths.py),
otherwise to .build/rule-tests/ and .tools/ (gitignored).
"""
from dataclasses import dataclass
from pathlib import Path
import argparse
import fcntl
import hashlib
import json
import os
import shutil
import subprocess
import sys
import threading
import time
import tomllib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'starters/ios/template/scripts'))
from paths import cache_root  # noqa: E402
from simulator import simulator, state  # noqa: E402
SKIP = {'.build', '.tools', 'Derived'}
ALL_BUT_VERIFY = ('compiler', 'tuist', 'swiftlint', 'harmonize', 'tests')
OVERLAYS = ('Targets', 'feature-map')  # project folders a case may add files to or replace files in
# Rough minutes per case by what it runs, so the longest start first and no worker is left with a long one at the end.
COST = {'untouched': 6, 'verify': 2, 'pass': 2, 'compiler': 1, 'tests': 1, 'tuist': 0.2, 'harmonize': 0.2, 'swiftlint': 0.1}


def default_jobs() -> int:
    """One worker per 3 cores and 5 GB of memory (3 on a 10-core, 16 GB laptop): each builds with Xcode and may run a
    simulator, and memory pressure kills test runners, which looks like a real failure."""
    memory = int(subprocess.run(['sysctl', '-n', 'hw.memsize'], capture_output=True, text=True).stdout.strip() or 0)
    return max(1, min((os.cpu_count() or 1) // 3, memory // (5 << 30)))


parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument('--project', type=Path, default=ROOT / 'starters/ios/template', help='project root containing scripts/check.py')
parser.add_argument('--rule', action='append', help='only run this rule id (repeatable)')
parser.add_argument('--jobs', type=int, help='cases to run at once (default: one per 3 cores and 5 GB of memory)')
parser.add_argument('--simulator', action='append', metavar='UDID',
                    help='a simulator cases may use (repeatable; one worker each). Default: $BSTACK_SIMULATOR_ID, '
                         'else the first available iPhone')
args = parser.parse_args()

project = args.project.resolve()
if not (project / 'scripts/check.py').is_file():
    sys.exit(f'No scripts/check.py in {project}')

cache = cache_root()
# One folder per project checkout, so runs from two checkouts never share files; a lock stops two runs of one.
work_root = (cache / 'rule-tests' if cache else ROOT / '.build/rule-tests') / \
    f'{project.name}-{hashlib.sha256(str(project).encode()).hexdigest()[:8]}'
work_root.mkdir(parents=True, exist_ok=True)
lock_file = (work_root / 'run.lock').open('w')
try:
    fcntl.flock(lock_file, fcntl.LOCK_EX | fcntl.LOCK_NB)
except BlockingIOError:
    sys.exit(f'Another test_rules.py run is using {work_root}. Wait for it to finish.')
base_env = dict(os.environ) if cache else {**os.environ, 'BSTACK_TOOLS_DIR': str(ROOT / '.tools')}
simulators = list(dict.fromkeys(args.simulator or [simulator()]))


@dataclass
class Worker:
    work: Path
    simulator: str | None

    def env(self) -> dict:
        # One simulator per worker, and verify inside a case runs on that one only (no clones).
        env = {**base_env, 'BSTACK_VERIFY_WORKERS': '1'}
        if self.simulator:
            env['BSTACK_SIMULATOR_ID'] = self.simulator
        return env

    def prepare(self) -> None:
        self.work.mkdir(parents=True, exist_ok=True)
        for item in self.work.iterdir():
            if item.name not in SKIP:
                shutil.rmtree(item) if item.is_dir() else item.unlink()
        for item in project.iterdir():
            if item.name not in SKIP and not item.name.endswith(('.xcodeproj', '.xcworkspace')):
                (shutil.copytree if item.is_dir() else shutil.copy2)(item, self.work / item.name)

    def check(self, *gates: str) -> tuple[bool, str]:
        cmd = [sys.executable, 'scripts/check.py'] + [a for g in gates for a in ('--only', g)]
        proc = subprocess.run(cmd, cwd=self.work, env=self.env(), capture_output=True, text=True)
        return proc.returncode == 0, proc.stdout + proc.stderr

    def reset_targets(self, case_dir: Path | None = None) -> None:
        for folder in OVERLAYS:
            if (self.work / folder).exists():
                shutil.rmtree(self.work / folder)
            if (project / folder).exists():
                shutil.copytree(project / folder, self.work / folder)
            if case_dir and (case_dir / folder).is_dir():
                shutil.copytree(case_dir / folder, self.work / folder, dirs_exist_ok=True)


def tail(output: str) -> str:
    lines = [l for l in output.splitlines() if l.strip()][-8:]
    return '\n'.join(f'      {l[:220]}' for l in lines)


@dataclass
class Task:
    index: int  # print order
    label: str
    case_dir: Path | None = None  # None: the untouched project
    case: dict | None = None
    cost: float = 0
    needs_simulator: bool = False
    result: tuple[str, str] | None = None  # (status, detail)


def run_case(worker: Worker, task: Task) -> tuple[str, str]:
    worker.reset_targets(task.case_dir)
    if task.case is None:
        ok, output = worker.check()
        return ('PASS', '') if ok else ('FAIL', tail(output))
    case = task.case
    if case['expect'] == 'pass':
        ok, output = worker.check(*ALL_BUT_VERIFY)
        return ('PASS', '') if ok else ('FAIL', 'correct code tripped a gate\n' + tail(output))
    ok, output = worker.check(case['enforced_by'])
    if ok:
        return 'FAIL', f'{case["enforced_by"]} let it through\n' + tail(output)
    if case['diagnostic'] not in output:
        return 'FAIL', f'{case["enforced_by"]} failed, but without "{case["diagnostic"]}"\n' + tail(output)
    return 'PASS', ''


tasks = [Task(0, '(untouched project passes every gate)', cost=COST['untouched'], needs_simulator=True)]
for case_file in sorted(ROOT.glob('rules/*/ios/*/case.toml')):
    rule, name = case_file.parents[2].name, case_file.parent.name
    if args.rule and rule not in args.rule:
        continue
    case = tomllib.loads(case_file.read_text())
    task = Task(len(tasks), f'{rule} / {name}  [{case["enforced_by"]}]', case_file.parent, case)
    adds = set(case.get('adds_targets', []))
    case_targets = case_file.parent / 'Targets'
    missing = [m.name for m in (case_targets.iterdir() if case_targets.is_dir() else [])
               if not (project / 'Targets' / m.name).is_dir() and m.name not in adds]
    if missing:
        task.result = ('SKIP', f'project has no target {", ".join(missing)}')
    else:
        kind = 'pass' if case['expect'] == 'pass' else case['enforced_by']
        task.cost = COST[kind]
        task.needs_simulator = kind in ('pass', 'tests', 'verify')
    tasks.append(task)

pending = sorted((t for t in tasks if t.result is None), key=lambda t: -t.cost)
jobs = max(1, min(args.jobs or default_jobs(), len(pending)))
workers = [Worker(work_root / f'w{i}',
                  simulators[i] if i < len(simulators) else None) for i in range(jobs)]
if not any(t.needs_simulator for t in pending):
    workers = [Worker(w.work, None) for w in workers]
lock = threading.Lock()
timings: list[tuple[str, str, bool, float]] = []  # label, worker, on a simulator worker, seconds
printed = 0
aborted = False


def take(worker: Worker) -> Task | None:
    """The costliest waiting task this worker can run. Workers with a simulator take simulator tasks first, if others
    can do the rest."""
    with lock:
        if aborted:
            return None
        runnable = [t for t in pending if worker.simulator or not t.needs_simulator]
        if worker.simulator and any(w.simulator is None for w in workers):
            runnable.sort(key=lambda t: not t.needs_simulator)  # stable: still costliest first within each kind
        if not runnable:
            return None
        pending.remove(runnable[0])
        return runnable[0]


def flush() -> None:
    """Print finished results in case order (call with the lock held)."""
    global printed
    while printed < len(tasks) and tasks[printed].result is not None and not (aborted and printed):
        task = tasks[printed]
        status, detail = task.result
        if task.case is None:
            print(f'{status}     {task.label}', flush=True)
            if detail:
                print(detail, flush=True)
        else:
            print(f'{status:8} {task.label}' + (f'  ({detail})' if detail and '\n' not in detail else ''), flush=True)
            if '\n' in detail:
                print('      ' + detail, flush=True)
        printed += 1


def work(worker: Worker) -> None:
    global aborted
    worker.prepare()
    while task := take(worker):
        task_started = time.monotonic()
        try:
            result = run_case(worker, task)
        except Exception as error:  # noqa: BLE001 - a crash in the harness is a FAIL for that case, never a pass
            result = ('FAIL', f'test harness error: {error!r}')
        with lock:
            timings.append((task.label, worker.work.name, worker.simulator is not None, time.monotonic() - task_started))
            task.result = result
            if task.case is None and result[0] != 'PASS':
                aborted = True  # nothing else counts if the untouched project fails
            flush()
    worker.reset_targets()


# Tools download once here, so parallel workers never fetch the same one at the same time.
for tool in ('tuist', 'swiftlint'):
    if (project / 'scripts/tools.py').is_file():
        subprocess.run([sys.executable, str(project / 'scripts/tools.py'), tool], env=base_env, capture_output=True)
# Simulators this run boots are shut down at the end; one already booted is borrowed and left as it was.
used = {w.simulator for w in workers if w.simulator}
booted_here = [udid for udid in used if state(udid).get('state') == 'Shutdown']
for udid in booted_here:
    subprocess.run(['xcrun', 'simctl', 'boot', udid], capture_output=True)
started = time.monotonic()
try:
    threads = [threading.Thread(target=work, args=(w,)) for w in workers]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()
finally:
    for udid in booted_here:
        subprocess.run(['xcrun', 'simctl', 'shutdown', udid], capture_output=True)

if tasks[0].result is None or tasks[0].result[0] != 'PASS':
    with lock:
        if tasks[0].result is None:
            print('FAIL     (untouched project passes every gate)\n      the run stopped before it finished')
    sys.exit(1)
counts = {'PASS': 0, 'SKIP': 0, 'FAIL': 0}
for task in tasks[1:]:
    if task.result is None:
        task.result = ('FAIL', 'never ran (no worker could take it)')
        with lock:
            flush()
    counts[task.result[0]] += 1
print('\n' + ', '.join(f'{n} {s.lower()}' for s, n in counts.items()) + f'  (project: {project})')
print(f'{len(workers)} workers, {len(used)} simulators, {time.monotonic() - started:.0f}s', flush=True)
busy = {w.work.name: sum(t for _, name, _, t in timings if name == w.work.name) for w in workers}
print('Busy time per worker: ' + ', '.join(f'{name} {seconds:.0f}s' for name, seconds in busy.items()), flush=True)
(work_root / 'timings.json').write_text(json.dumps(
    [{'case': label, 'worker': name, 'simulator': sim, 'seconds': round(t, 1)} for label, name, sim, t in timings], indent=1))
sys.exit(1 if counts['FAIL'] else 0)
