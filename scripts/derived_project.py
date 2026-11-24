"""Make a project from a starter the way skills/new-project/SKILL.md does, then run its gates and the rule cases on it.

b-stack's other tests run each starter as shipped: its example present, placeholders unfilled, a plain checkout. A
real app is none of those, so this does the mechanical part of the skill for one platform, in a scratch folder in the
cache folder:

  1. copy the template (leaving out build output and installed packages)
  2. fill the placeholders: CODEOWNERS' @OWNER, AGENTS.template.md -> AGENTS.md (+ CLAUDE.md), the app's id
  3. remove the example exactly as the skill lists it (a path the skill names that the starter lacks is an error)
  4. put back what removing it leaves broken, as an agent would before its first feature (scripts/derived/<platform>/
     skeleton/: the composition roots and journey files without the example's parts)
  5. make it a git repo, commit that as `main`, and add a linked worktree on a branch `feature`
  6. in the worktree: add one feature with the starter's new_feature.py, then write its stubs
     (scripts/derived/<platform>/feature/: a tiny real test and journey), and commit
  7. in the worktree: scripts/check.py (every gate, against `main` as the base branch), then
     scripts/test_rules.py --project <worktree> from b-stack

Usage: python3 scripts/derived_project.py <platform> [--setup-only] [--no-rules]
  --setup-only   make the project and print where it is; run nothing
  --no-rules     run check.py only, not the rule cases
"""
from dataclasses import dataclass, field
from pathlib import Path
import argparse
import hashlib
import os
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'starters/ios/template/scripts'))
from paths import cache_root  # noqa: E402
sys.path.insert(0, str(ROOT / 'scripts'))
from platforms import PLATFORMS  # noqa: E402

OWNER = '@derived-owner'
APP_NAME = 'Derived'
NOT_COPIED = {'.build', '.tools', 'Derived', 'node_modules', 'dist', 'build', '.gradle', '.kotlin', 'target'}


@dataclass(frozen=True)
class Plan:
    feature: str | None  # the feature new_feature.py adds (None: the starter has none)
    remove: tuple[str, ...]  # the example, as the new-project skill lists it
    fill: dict[str, tuple[tuple[str, str], ...]] = field(default_factory=dict)  # file: (find, replace), each once
    settle: tuple[str, ...] = ()  # run before the feature's commit, outside CI: brings lock files (and generated
    # journey adapters) up to date, as an agent's local run does


PLANS = {
    'rust': Plan(
        feature='greeting',
        remove=('crates/features/tally', 'crates/platform/files', 'crates/app/src/main.rs',
                'crates/app/tests/journeys.rs', 'feature-map/tally.toml'),
        settle=('scripts/check.py', '--only', 'compiler')),
    'typescript': Plan(
        feature='greeting',
        remove=('packages/features/tally', 'packages/platform/files', 'packages/contracts/src/index.ts',
                'packages/contracts/src/ipc.ts', 'packages/fixtures/src', 'apps/desktop/src', 'apps/web/src',
                'apps/desktop/journeys/tally.journey.ts', 'apps/desktop/journeys/smoke.json', 'feature-map/tally.toml'),
        fill={'apps/web/index.html': (('<title>Tally</title>', f'<title>{APP_NAME}</title>'),)},
        settle=('scripts/tools.py', 'install')),
    'android': Plan(
        feature='greeting',
        remove=('features/tally', 'platform/files', 'fixtures/src/main/kotlin/fixtures/Fixtures.kt',
                'app/src/main/kotlin/app/StarterApp.kt', 'app/src/main/kotlin/app/MainActivity.kt',
                'app-verify/src/main/kotlin/appverify/VerifyApp.kt',
                'app-verify/src/main/kotlin/appverify/VerifyActivity.kt',
                'verify/journeys/src/commonMain/kotlin/journeys/TallyJourneys.kt', 'feature-map/tally.toml'),
        fill={'gradle.properties': (('bstack.applicationId=dev.bstack.starter', 'bstack.applicationId=dev.bstack.derived'),)},
        settle=('scripts/verify.py', 'adapters')),
    'ios': Plan(
        feature=None,  # the iOS starter has no new_feature.py: the feature's targets are written whole
        remove=('Targets/Settings', 'Targets/SettingsInterface', 'Targets/SettingsLogic', 'Targets/SettingsTests',
                'Targets/Platform/Platform.swift', 'Targets/Fixtures/Fixtures.swift', 'Targets/App/App.swift',
                'Targets/AppVerify/AppVerify.swift', 'Targets/AppVerifyJourneys/NotificationSettingsJourneys.swift',
                'feature-map/notification-settings.toml'),
        settle=('scripts/verify.py', 'adapters')),
}


def git(cwd: Path, *cmd: str) -> str:
    env = {**os.environ, 'GIT_AUTHOR_NAME': 'derived', 'GIT_AUTHOR_EMAIL': 'derived@example.invalid',
           'GIT_COMMITTER_NAME': 'derived', 'GIT_COMMITTER_EMAIL': 'derived@example.invalid'}
    return subprocess.run(['git', '-c', 'commit.gpgsign=false', *cmd], cwd=cwd, env=env, check=True,
                          capture_output=True, text=True).stdout.strip()


def settle(plan: Plan, project: Path) -> None:
    if not plan.settle:
        return
    env = {k: v for k, v in os.environ.items() if k != 'CI'}
    proc = subprocess.run([sys.executable, *plan.settle], cwd=project, env=env, capture_output=True, text=True)
    if proc.returncode != 0:
        sys.exit(f'{" ".join(plan.settle)} failed in {project}:\n{(proc.stdout + proc.stderr)[-3000:]}')


def overlay(source: Path, project: Path) -> None:
    if source.is_dir():
        shutil.copytree(source, project, dirs_exist_ok=True)


def replace_once(path: Path, find: str, replace: str) -> None:
    text = path.read_text()
    if text.count(find) != 1:
        sys.exit(f'{path.name}: "{find}" must occur exactly once to fill it in (found {text.count(find)})')
    path.write_text(text.replace(find, replace))


def make(name: str, folder: Path) -> Path:
    """Steps 1 to 6. Returns the linked worktree."""
    platform, plan = PLATFORMS[name], PLANS[name]
    here = ROOT / 'scripts/derived' / name
    repo, worktree = folder / 'repo', folder / 'worktree'
    if folder.exists():
        shutil.rmtree(folder)
    folder.mkdir(parents=True)
    shutil.copytree(platform.starter, repo, symlinks=True, ignore=lambda _, names: NOT_COPIED & set(names))

    # Placeholders.
    codeowners = repo / 'CODEOWNERS'
    codeowners.write_text(codeowners.read_text().replace('@OWNER', OWNER))
    agents = (repo / 'AGENTS.template.md').read_text().replace('<App name>', APP_NAME)
    (repo / 'AGENTS.template.md').unlink()
    (repo / 'AGENTS.md').write_text(agents)
    (repo / 'CLAUDE.md').write_text('@AGENTS.md\n')
    for file, edits in plan.fill.items():
        for find, replace in edits:
            replace_once(repo / file, find, replace)

    # The example.
    missing = [path for path in plan.remove if not (repo / path).exists()]
    if missing:
        sys.exit(f'The new-project skill removes {", ".join(missing)}, which the {name} starter doesn\'t have.')
    for path in plan.remove:
        shutil.rmtree(repo / path) if (repo / path).is_dir() else (repo / path).unlink()
    overlay(here / 'skeleton', repo)

    git(repo, 'init', '-q', '-b', 'main')
    git(repo, 'config', 'core.hooksPath', '.githooks')
    git(repo, 'add', '-A')
    git(repo, 'commit', '-q', '--no-verify', '-m', 'Set up from the b-stack starter, example removed')
    git(repo, 'worktree', 'add', '-q', '-b', 'feature', str(worktree))

    if plan.feature:
        proc = subprocess.run([sys.executable, 'scripts/new_feature.py', plan.feature], cwd=worktree,
                              capture_output=True, text=True)
        if proc.returncode != 0:
            sys.exit(f'new_feature.py {plan.feature} failed in the derived project:\n{proc.stdout}{proc.stderr}')
    overlay(here / 'feature', worktree)
    settle(plan, worktree)
    git(worktree, 'add', '-A')
    git(worktree, 'commit', '-q', '--no-verify', '-m', 'Add the first feature')
    return worktree


def run(cmd: list[str], cwd: Path, env: dict) -> int:
    print(f'$ {" ".join(cmd)}   (in {cwd})', flush=True)
    return subprocess.run(cmd, cwd=cwd, env=env).returncode


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('platform', choices=sorted(PLANS))
    parser.add_argument('--setup-only', action='store_true')
    parser.add_argument('--no-rules', action='store_true')
    args = parser.parse_args()
    cache = cache_root()
    base = cache / 'derived' if cache else ROOT / '.build/derived'
    folder = base / f'{args.platform}-{hashlib.sha256(str(ROOT).encode()).hexdigest()[:8]}'
    worktree = make(args.platform, folder)
    print(f'Derived {args.platform} project: {worktree} (a linked worktree of {folder / "repo"})', flush=True)
    if args.setup_only:
        return 0
    env = {**os.environ, 'BSTACK_BASE_REF': 'main'}
    results = {'check.py': run([sys.executable, 'scripts/check.py'], worktree, env)}
    if not args.no_rules:
        # Cases add packages, so the package manager must update lock files in their copies, which CI=true forbids.
        results['test_rules.py --project'] = run(
            [sys.executable, str(ROOT / 'scripts/test_rules.py'), '--project', str(worktree)], ROOT, {**env, 'CI': 'false'})
    print('\nDerived project: ' + ', '.join(f'{step} {"PASS" if code == 0 else "FAIL"}' for step, code in results.items()))
    return 0 if all(code == 0 for code in results.values()) else 1


if __name__ == '__main__':
    sys.exit(main())
