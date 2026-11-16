"""Prove every rule fires, by running each case through the project's own gate command (scripts/check.py).

For each case, Targets/ is reset to the project's and the case's Targets/ is overlaid:
  fail case   `check.py --only <enforced_by>` must fail, and its output must contain the case's diagnostic
  pass case   `check.py` (every gate) must pass, so correct code never trips any rule
The untouched project must pass every gate first.

Default project: starters/ios/template. Pass --project <new-app> to prove a new app's setup enforces the rules.
Work and tool downloads go to the cache folder if one is configured (see starters/ios/template/scripts/paths.py),
otherwise to .build/rule-tests/ and .tools/ (gitignored).
"""
from pathlib import Path
import argparse
import os
import shutil
import subprocess
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'starters/ios/template/scripts'))
from paths import cache_root  # noqa: E402
SKIP = {'.build', '.tools', 'Derived'}

parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument('--project', type=Path, default=ROOT / 'starters/ios/template', help='project root containing scripts/check.py')
parser.add_argument('--rule', action='append', help='only run this rule id (repeatable)')
args = parser.parse_args()

project = args.project.resolve()
if not (project / 'scripts/check.py').is_file():
    sys.exit(f'No scripts/check.py in {project}')

cache = cache_root()
work = (cache / 'rule-tests' if cache else ROOT / '.build/rule-tests') / project.name
work.mkdir(parents=True, exist_ok=True)
for item in work.iterdir():
    if item.name not in SKIP:
        shutil.rmtree(item) if item.is_dir() else item.unlink()
for item in project.iterdir():
    if item.name not in SKIP and not item.name.endswith(('.xcodeproj', '.xcworkspace')):
        (shutil.copytree if item.is_dir() else shutil.copy2)(item, work / item.name)
env = dict(os.environ) if cache else {**os.environ, 'BSTACK_TOOLS_DIR': str(ROOT / '.tools')}


def check(*gates: str) -> tuple[bool, str]:
    cmd = [sys.executable, 'scripts/check.py'] + [a for g in gates for a in ('--only', g)]
    proc = subprocess.run(cmd, cwd=work, env=env, capture_output=True, text=True)
    return proc.returncode == 0, proc.stdout + proc.stderr


def reset_targets(case_dir: Path | None = None) -> None:
    shutil.rmtree(work / 'Targets')
    shutil.copytree(project / 'Targets', work / 'Targets')
    if case_dir:
        shutil.copytree(case_dir / 'Targets', work / 'Targets', dirs_exist_ok=True)


def tail(output: str) -> str:
    lines = [l for l in output.splitlines() if l.strip()][-8:]
    return '\n'.join(f'      {l[:220]}' for l in lines)


counts = {'PASS': 0, 'SKIP': 0, 'FAIL': 0}
reset_targets()
ok, output = check()
print(f'{"PASS" if ok else "FAIL"}     (untouched project passes every gate)')
if not ok:
    print(tail(output))
    sys.exit(1)

for case_file in sorted(ROOT.glob('rules/*/ios/*/case.toml')):
    rule, name = case_file.parents[2].name, case_file.parent.name
    if args.rule and rule not in args.rule:
        continue
    case = tomllib.loads(case_file.read_text())
    missing = [m.name for m in (case_file.parent / 'Targets').iterdir() if not (project / 'Targets' / m.name).is_dir()]
    if missing:
        status, detail = 'SKIP', f'project has no target {", ".join(missing)}'
    else:
        reset_targets(case_file.parent)
        if case['expect'] == 'pass':
            ok, output = check()
            status, detail = ('PASS', '') if ok else ('FAIL', 'correct code tripped a gate\n' + tail(output))
        else:
            ok, output = check(case['enforced_by'])
            if ok:
                status, detail = 'FAIL', f'{case["enforced_by"]} let it through\n' + tail(output)
            elif case['diagnostic'] not in output:
                status, detail = 'FAIL', f'{case["enforced_by"]} failed, but without "{case["diagnostic"]}"\n' + tail(output)
            else:
                status, detail = 'PASS', ''
    counts[status] += 1
    label = f'{status:8} {rule} / {name}  [{case["enforced_by"]}]'
    print(label + (f'  ({detail})' if detail and '\n' not in detail else ''), flush=True)
    if '\n' in detail:
        print('      ' + detail)

reset_targets()
print('\n' + ', '.join(f'{n} {s.lower()}' for s, n in counts.items()) + f'  (project: {project})')
sys.exit(1 if counts['FAIL'] else 0)
