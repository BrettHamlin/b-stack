"""Run every rule's iOS test cases against a Swift package (default: the starter template).

Each case overlays its Sources/ onto a copy of the package and runs `swift build`:
  compiler + fail   build must fail, and the output must contain the case's diagnostic
  compiler + pass   build must succeed
  checker           build must succeed (valid Swift the compiler can't catch); reported
                    PENDING until the checker exists to enforce it
Point --package at a new project's Modules package to prove its setup enforces the rules.
"""
from pathlib import Path
import argparse
import re
import shutil
import subprocess
import sys
import tempfile
import tomllib

ROOT = Path(__file__).resolve().parents[1]
ANSI = re.compile(r'\x1b\[[0-9;]*m|\x1b\]8;;.*?\x1b\\')

parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
parser.add_argument('--package', type=Path, default=ROOT / 'starters/ios/template/Modules',
                    help='Swift package to test against (default: the starter template)')
parser.add_argument('--rule', action='append', help='only run this rule id (repeatable)')
args = parser.parse_args()

base = args.package.resolve()
if not (base / 'Package.swift').is_file():
    sys.exit(f'No Package.swift in {base}')

work = Path(tempfile.mkdtemp(prefix='b-stack-rules-'))
for item in base.iterdir():
    if item.name not in ('.build', '.swiftpm', 'Sources'):
        (shutil.copytree if item.is_dir() else shutil.copy2)(item, work / item.name)


def errors(output: str) -> str:
    lines = [l.strip() for l in output.splitlines() if 'error:' in l and 'SwiftDriver' not in l and 'SwiftCompile' not in l]
    return '\n'.join(f'      {l[-200:]}' for l in dict.fromkeys(lines).keys() if l) or '      (no error lines)'


counts = {'PASS': 0, 'PENDING': 0, 'SKIP': 0, 'FAIL': 0}
try:
    for case_file in sorted(ROOT.glob('rules/*/ios/*/case.toml')):
        rule, name = case_file.parents[2].name, case_file.parent.name
        if args.rule and rule not in args.rule:
            continue
        case = tomllib.loads(case_file.read_text())
        case_sources = case_file.parent / 'Sources'
        missing = [m.name for m in case_sources.iterdir() if not (base / 'Sources' / m.name).is_dir()]
        if missing:
            status, detail = 'SKIP', f'package has no module {", ".join(missing)}'
        else:
            shutil.rmtree(work / 'Sources', ignore_errors=True)
            shutil.rmtree(work / '.build', ignore_errors=True)  # clean build: results must not depend on earlier cases
            shutil.copytree(base / 'Sources', work / 'Sources')
            shutil.copytree(case_sources, work / 'Sources', dirs_exist_ok=True)
            proc = subprocess.run(['swift', 'build'], cwd=work, capture_output=True, text=True)
            output = ANSI.sub('', proc.stdout + proc.stderr)
            built = proc.returncode == 0
            if case['enforced_by'] == 'checker':
                status, detail = ('PENDING', 'valid Swift; needs the checker') if built else \
                    ('FAIL', 'does not compile: fix the case, or the compiler now catches it (move the rule up)\n' + errors(output))
            elif case['expect'] == 'pass':
                status, detail = ('PASS', '') if built else ('FAIL', 'should compile but failed\n' + errors(output))
            elif built:
                status, detail = 'FAIL', 'compiled, but the compiler should reject it'
            elif case['diagnostic'] not in output:
                status, detail = 'FAIL', f'failed, but not with "{case["diagnostic"]}"\n' + errors(output)
            else:
                status, detail = 'PASS', ''
        counts[status] += 1
        print(f'{status:8} {rule} / {name}' + (f'  ({detail})' if detail and '\n' not in detail else ''))
        if '\n' in detail:
            print('      ' + detail)
finally:
    shutil.rmtree(work, ignore_errors=True)

print('\n' + ', '.join(f'{n} {s.lower()}' for s, n in counts.items()) + f'  (package: {base})')
sys.exit(1 if counts['FAIL'] else 0)
