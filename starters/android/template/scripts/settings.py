"""The settings gate: the enforcement settings in effect are the ones in arch/settings.json, so weakening a check fails
here as well as in code-owner review. It reads what the tools will use, not the files' text: build-logic's
`bstackSettings` task writes them after every script, property and init script has had its say.

  build       Gradle: dependency verification strict, no build cache, no init scripts (including GRADLE_USER_HOME's
              init.d), not offline
  modules     every module's settings, exactly as recorded for its role (arch/shape.json): each Kotlin compilation's
              warnings as errors, suppressed warnings, progressive mode, opt-ins, extra compiler arguments, language
              and API version and JVM target; the Android SDK levels and Lint options; the shipped app's release
              shrinking; each detekt task's config, failure handling and baseline; each test task's failure
              handling and filters
  codeowners  /CODEOWNERS is the only one, every rule names an owner, and it lists every enforcement path

Changing one of these on purpose means changing arch/settings.json in the same change (both are code-owned):
`python3 scripts/settings.py record` writes it from the settings in effect, for the owner to review.

Usage: python3 scripts/settings.py [record]
"""
from pathlib import Path
import json
import re
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from arch import modules  # noqa: E402
from tools import android_env, gradle_command  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
RECORD = ROOT / 'arch/settings.json'
FIX = ('Restore it. If the change is meant, it needs the owner: they change the setting and arch/settings.json together. '
       'Never weaken a check to make code pass; fix the code, or stop and report.')


def effective() -> dict:
    out = ROOT / '.build/settings/effective.json'
    out.unlink(missing_ok=True)
    proc = subprocess.run(gradle_command('-q', '--no-configuration-cache', 'bstackSettings'), cwd=ROOT,
                          env=android_env(), capture_output=True, text=True)
    if proc.returncode != 0 or not out.is_file():
        sys.exit(f'[protected-enforcement] Couldn\'t read the settings in effect:\n{(proc.stdout + proc.stderr)[-3000:]}')
    return json.loads(out.read_text())


def by_role(found: dict) -> tuple[dict, list[str]]:
    """Each role's settings, from its modules (which must agree), and the modules that don't."""
    roles: dict[str, dict] = {}
    differ = []
    for folder, role in modules():
        settings = found['modules'].get(folder)
        if settings is None:
            continue
        if role['name'] in roles and roles[role['name']] != settings:
            differ.append(folder)
        roles.setdefault(role['name'], settings)
    return roles, differ


def differences(expected, actual, where: str) -> list[str]:
    """Each setting that differs, as `where.key: expected X, found Y`."""
    if isinstance(expected, dict) and isinstance(actual, dict):
        out = []
        for key in sorted(set(expected) | set(actual)):
            out += differences(expected.get(key), actual.get(key), f'{where}.{key}' if where else key)
        return out
    return [] if expected == actual else [f'{where}: arch/settings.json records {json.dumps(expected)}, in effect '
                                          f'{json.dumps(actual)}']


def codeowners_paths() -> list[str]:
    return [rule[0] for rule in codeowners_rules() if len(rule) > 1]


def codeowners_rules() -> list[list[str]]:
    path = ROOT / 'CODEOWNERS'
    # An inline `#` starts a comment, which isn't an owner.
    lines = [re.sub(r'(^|\s)#.*$', '', line).strip() for line in path.read_text().splitlines()] if path.is_file() else []
    return [line.split() for line in lines if line]


def codeowners_findings(expected: list[str]) -> list[str]:
    out = [f'[protected-enforcement] {other}: GitHub reads this CODEOWNERS before the root one. Keep code owners only in '
           f'/CODEOWNERS. {FIX}' for other in ('.github/CODEOWNERS', 'docs/CODEOWNERS') if (ROOT / other).exists()]
    rules = codeowners_rules()
    # A pattern with no owner removes ownership from what it matches, so every rule must name one.
    out += [f'[protected-enforcement] CODEOWNERS: `{rule[0]}` has no owner, which removes code-owner review from what '
            f'it matches. {FIX}' for rule in rules if len(rule) < 2]
    owned = set(codeowners_paths())
    missing = [p for p in expected if p not in owned]
    if missing:
        out.append(f'[protected-enforcement] CODEOWNERS: no code owner for {", ".join(missing)}. Every enforcement '
                   f'path needs one. {FIX}')
    return out


def findings() -> list[str]:
    expected = json.loads(RECORD.read_text())
    found = effective()
    out = [f'[protected-enforcement] Gradle {d}. {FIX}' for d in differences(expected['build'], found['build'], '')]
    roles, differ = by_role(found)
    out += [f'[protected-enforcement] {folder}: its settings differ from the other {role["name"]} modules\'. {FIX}'
            for folder, role in modules() if folder in differ]
    for folder, role in modules():
        settings = found['modules'].get(folder)
        if settings is None:
            continue
        recorded = expected['roles'].get(role['name'])
        if recorded is None:
            out.append(f'[protected-enforcement] {folder}: arch/settings.json records no settings for the '
                       f'{role["name"]} role. {FIX}')
            continue
        out += [f'[protected-enforcement] {folder}: {d}. {FIX}' for d in differences(recorded, settings, '')]
    out += codeowners_findings(expected['codeowners'])
    return out


def record() -> None:
    found = effective()
    roles, differ = by_role(found)
    if differ:
        sys.exit(f'Not recorded: {", ".join(differ)} differ from other modules of their role.')
    RECORD.write_text(json.dumps({
        'about': 'The enforcement settings in effect, recorded by `python3 scripts/settings.py record` (protected). The '
                 'settings gate fails when what Gradle, Kotlin, the Android plugin and detekt will use differs from '
                 'this, or when CODEOWNERS stops covering a path listed here.',
        'build': found['build'], 'roles': dict(sorted(roles.items())), 'codeowners': codeowners_paths(),
    }, indent=1) + '\n')
    print(f'recorded {RECORD.relative_to(ROOT)}')


if __name__ == '__main__':
    if sys.argv[1:] == ['record']:
        record()
        sys.exit(0)
    if sys.argv[1:]:
        sys.exit(__doc__)
    problems = findings()
    shown = problems[:30] + ([f'... and {len(problems) - 30} more'] if len(problems) > 30 else [])
    print('\n'.join(shown) if problems else 'settings: every enforcement setting is as recorded')
    sys.exit(1 if problems else 0)
