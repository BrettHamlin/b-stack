"""Run every enforcement gate. Exit non-zero if any gate fails. CI runs this; agents run it before handing back.

Gates:
  compiler   generate the Xcode project with Tuist, then build every target with strict Swift settings
  tuist      every import of a project module is declared in Project.swift, and every declared one is used
  swiftlint  no force unwraps, force try/cast, or suppression comments
  harmonize  architecture rules in Rules/ (allowed imports, no singletons, concurrency escapes, ...)
  tests      unit tests on an iOS Simulator (TCA TestStore tests are exhaustive)
  verify     the feature map is complete, and every journey passes in the running app (scripts/verify.py)

Usage: python3 scripts/check.py [--only GATE ...]
"""
from pathlib import Path
import argparse
import os
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import link_build_dirs  # noqa: E402
from simulator import simulator  # noqa: E402
from tools import tool_path  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
GATES = ['compiler', 'tuist', 'swiftlint', 'harmonize', 'tests', 'verify']
ENV = {**os.environ, 'TUIST_STATS_OPT_OUT': '1', 'TUIST_DISABLE_ANALYTICS': '1'}


def run(cmd: list[str], cwd: Path = ROOT) -> bool:
    proc = subprocess.run(cmd, cwd=cwd, env=ENV, capture_output=True, text=True)
    if proc.returncode != 0:
        output = proc.stdout + proc.stderr
        errors = [l.strip() for l in output.splitlines() if 'error:' in l and len(l) < 1000]
        if errors:
            print('\n'.join(list(dict.fromkeys(errors))[:50]))
        else:
            print(output.strip()[-4000:])
    return proc.returncode == 0


def generate(tuist: str) -> bool:
    return run([tuist, 'install']) and run([tuist, 'generate', '--no-open'])


def gate(name: str) -> bool:
    tuist = str(tool_path('tuist'))
    if name == 'compiler':
        return generate(tuist) and run([
            'xcodebuild', '-workspace', 'Starter.xcworkspace', '-scheme', 'App',
            '-destination', 'generic/platform=iOS Simulator', '-derivedDataPath', '.build/DerivedData',
            '-quiet', '-skipMacroValidation', 'build', 'CODE_SIGNING_ALLOWED=NO',
        ]) and run([
            'xcodebuild', '-workspace', 'Starter.xcworkspace', '-scheme', 'AppVerify',
            '-destination', 'generic/platform=iOS Simulator', '-derivedDataPath', '.build/DerivedData',
            '-quiet', '-skipMacroValidation', 'build-for-testing', 'CODE_SIGNING_ALLOWED=NO',
        ])
    if name == 'tests':
        return generate(tuist) and run([
            'xcodebuild', '-workspace', 'Starter.xcworkspace', '-scheme', 'SettingsTests',
            '-destination', f'platform=iOS Simulator,id={simulator()}', '-derivedDataPath', '.build/DerivedData',
            '-quiet', '-skipMacroValidation', 'test', 'CODE_SIGNING_ALLOWED=NO',
        ])
    if name == 'tuist':
        return run([tuist, 'install']) and run([tuist, 'inspect', 'dependencies', '--only', 'implicit', '--only', 'redundant'])
    if name == 'swiftlint':
        return run([str(tool_path('swiftlint')), 'lint', '--strict', '--quiet'])
    if name == 'harmonize':
        # Serial: run in parallel, Harmonize 1.3.0 rules can deadlock on its shared source cache and hang forever.
        return run(['swift', 'test', '--no-parallel', '--package-path', 'Rules', '--scratch-path', '.build/rules'])
    if name == 'verify':
        return subprocess.run([sys.executable, str(ROOT / 'scripts/verify.py'), 'run'], cwd=ROOT, env=ENV).returncode == 0
    raise ValueError(name)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--only', action='append', choices=GATES)
    selected = parser.parse_args().only or GATES
    link_build_dirs(ROOT)
    failed = []
    for name in selected:
        ok = gate(name)
        print(f'{"PASS" if ok else "FAIL"} {name}', flush=True)
        if not ok:
            failed.append(name)
    sys.exit(1 if failed else 0)
