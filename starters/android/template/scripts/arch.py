"""The arch gate: what the build itself can't see. A text check, so no annotation or comment in a file can switch it off.

  - no-suppressions: no @Suppress, @SuppressWarnings, @SuppressLint, @TargetApi (which switches off Lint's NewApi) or
    @OptIn (with any use-site target or
    qualifier), no import of them, no tools:ignore or tools:targetApi, and no -opt-in or -Xsuppress flag, in any project file outside
    build-logic/ and arch/ (a text match, so the words in a string fail too). Kotlin lets @Suppress switch off
    compiler errors such as DEPRECATION_ERROR and OPT_IN_USAGE_ERROR, and detekt and Konsist both honor it, so none
    of them can hold this ban.
  - module-boundaries: every folder is a module of a role in arch/shape.json, or one of the project's own; each
    features/<name> has exactly api, logic and ui; no build, settings or tool config files inside modules; no Java
    (detekt and Konsist read Kotlin only); code-owned modules (shape `fixed`) have no module.toml.
  - source sets: a common module has only src/commonMain/kotlin and src/commonTest/kotlin (any other source set, such
    as jvmMain, would see the JDK); an Android module only src/main (kotlin, AndroidManifest.xml, res) and
    src/test/kotlin. Other source sets (src/debug, src/androidTest, ...) would build into the app or never run.

Usage: python3 scripts/arch.py
"""
from pathlib import Path
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
OWN = {'.build', '.tools', '.git', '.github', '.githooks', '.claude', '.agents', '.gradle', '.kotlin', '.idea', 'build', 'arch', 'build-logic',
       'feature-map', 'gradle', 'scripts', 'features', 'platform', 'verify'}
OWN_FILES = {'settings.gradle.kts', 'build.gradle.kts', 'gradle.properties', 'tools.toml', 'CODEOWNERS', 'AGENTS.md',
             'AGENTS.template.md', 'CLAUDE.md', 'README.md', '.gitignore', 'local.properties'}
SUPPRESSION = re.compile(
    r'@\s*(?:[a-zA-Z]+\s*:\s*)?(?:\[\s*)?(?:[\w.]+\.)?(Suppress|SuppressWarnings|SuppressLint|TargetApi|OptIn)\b'
    r'|\bimport\s+[\w.]*\b(Suppress|SuppressWarnings|SuppressLint|TargetApi|OptIn)\b'
    r'|\btools:(?:ignore|targetApi)\b|-X?opt-in\b|-Xsuppress|\bkotlin\.OptIn\b|\bkotlin\.Suppress\b'
    # Annotating a declaration with an opt-in marker passes the requirement on instead of opting in.
    r'|@\s*(?:[\w.]+\.)?(?:Experimental\w*Api|Delicate\w*Api|Internal\w*Api|\w+Preview\w*Api)\b')
TEXT = ('.kt', '.kts', '.xml', '.properties', '.toml', '.java', '.pro', '.yml', '.yaml', '.json')


def shape() -> dict:
    return json.loads((ROOT / 'arch/shape.json').read_text())


def modules() -> list[tuple[str, dict]]:
    """(folder, role) for every module folder in the shape, as settings.gradle.kts includes them."""
    found = []
    for name, role in shape()['roles'].items():
        for pattern in role['folders']:
            for path in sorted(ROOT.glob(pattern)):
                if path.is_dir():
                    found.append((path.relative_to(ROOT).as_posix(), {**role, 'name': name}))
    return sorted(found)


def suppressions() -> list[str]:
    found = []
    skip = ('.build', '.tools', 'build', '.git', 'build-logic', 'arch', '.gradle', '.kotlin')
    for path in sorted(ROOT.rglob('*')):
        relative = path.relative_to(ROOT)
        if not path.is_file() or relative.parts[0] in skip or path.suffix not in TEXT:
            continue
        for number, line in enumerate(path.read_text(errors='replace').splitlines(), 1):
            if match := SUPPRESSION.search(line):
                found.append(f'[no-suppressions] {relative}:{number}: `{match.group(0).strip()}`. Suppressions and '
                             'opt-ins aren\'t allowed: fix the underlying issue. If the rule is wrong here, stop and '
                             'report; opt-ins a role needs are granted in build-logic by the owner.')
    return found


def layout() -> list[str]:
    found = []
    mods = dict(modules())
    for path in sorted(ROOT.iterdir()):
        name = path.name
        if path.is_dir() and name not in OWN and name not in mods:
            found.append(f'[module-boundaries] {name}/ isn\'t a module folder in arch/shape.json. A module\'s folder '
                         'gives its role (core, core-ui, features/<name>/api|logic|ui, platform/<name>, fixtures, app, '
                         'app-verify); if code needs a new kind of module, stop and report.')
        elif path.is_file() and name not in OWN_FILES:
            found.append(f'[module-boundaries] {name}: only the project\'s own files sit at the top level.')
    for group in ('features', 'platform', 'verify'):
        for path in sorted((ROOT / group).iterdir()) if (ROOT / group).is_dir() else []:
            if group == 'features' and path.is_dir():
                parts = sorted(p.name for p in path.iterdir() if not p.name.startswith('.'))
                if parts != ['api', 'logic', 'ui']:
                    found.append(f'[module-boundaries] features/{path.name} holds {", ".join(parts) or "nothing"}; a '
                                 'feature is exactly api, logic and ui (each a module).')
            elif path.relative_to(ROOT).as_posix() not in mods:
                found.append(f'[module-boundaries] {path.relative_to(ROOT)} isn\'t a module folder in arch/shape.json.')
    for folder, role in mods.items():
        if folder.startswith('arch/'):
            continue
        base = ROOT / folder
        if role['kind'] == 'common':
            sets = {'src/commonMain/kotlin', 'src/commonTest/kotlin'}
        elif role['kind'] == 'android-test':
            sets = {'src/main/kotlin'}
        else:
            sets = {'src/main/kotlin', 'src/main/res', 'src/test/kotlin'}
            if role['kind'] == 'android-app':
                # Only the apps have a manifest: a library's permissions or exported components would be merged into the
                # shipped app without anyone reading them.
                sets.add('src/main/AndroidManifest.xml')
        for path in sorted(base.rglob('*')):
            relative = path.relative_to(base).as_posix()
            if path.is_dir() or relative == 'module.toml' and not role.get('fixed'):
                continue
            if not any(relative == s or relative.startswith(s + '/') for s in sets):
                found.append(f'[module-boundaries] {folder}/{relative}: a {role["name"]} module holds only '
                             f'{", ".join(sorted(sets))}{"" if role.get("fixed") else " and module.toml"}. Build '
                             'settings come from build-logic, and other source sets would build into the app or '
                             'never run; if you need one, stop and report.')
            elif path.suffix == '.java':
                found.append(f'[module-boundaries] {folder}/{relative}: write Kotlin; the checks read Kotlin only.')
    return found


def findings() -> list[str]:
    return layout() + suppressions()


if __name__ == '__main__':
    problems = findings()
    print('\n'.join(problems) if problems else 'arch: OK')
    sys.exit(1 if problems else 0)
