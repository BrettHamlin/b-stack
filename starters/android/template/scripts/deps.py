"""The deps gate: where libraries come from, that Gradle checks them, and their licenses.

  - Repositories: settings.gradle.kts and build-logic/settings.gradle.kts name only google(), mavenCentral() and (for
    Gradle plugins) gradlePluginPortal(), and forbid repositories in modules (FAIL_ON_PROJECT_REPOS).
  - Checksums: gradle/verification-metadata.xml verifies every artifact's SHA-256, with no trusted-artifact exceptions.
    Gradle itself then refuses an artifact that isn't listed or doesn't match, in every gate.
  - Licenses: every component in the verification metadata, read from its POM (following parent POMs). The shipped app
    (app's release runtime classpath) may use only permissive licenses; build and test tools may also use the weak
    copyleft licenses below (JUnit's EPL, and the MPL and EPL parts of the Android Gradle Plugin's own tools). An unknown or missing license fails: add it to the table here
    (a code-owned change) once someone has read it.

Usage: python3 scripts/deps.py
"""
from pathlib import Path
import re
import subprocess
import sys
import xml.etree.ElementTree as ET

sys.path.insert(0, str(Path(__file__).resolve().parent))
from arch import modules  # noqa: E402
from tools import android_env, gradle_command  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
NS = {'v': 'https://schema.gradle.org/dependency-verification'}
PERMISSIVE = {'Apache-2.0', 'MIT', 'BSD-2-Clause', 'BSD-3-Clause', 'ISC', '0BSD', 'CC0-1.0', 'Unlicense',
              'Bouncy-Castle', 'EDL-1.0'}
TOOLS_ONLY = {'EPL-1.0', 'EPL-2.0', 'MPL-1.1', 'MPL-2.0', 'JDOM', 'Public-Domain', 'BSD-style'}
# POM license names and URLs as libraries write them, to SPDX (or our own name where SPDX has none).
NAMES = [
    (r'similar to apache license but with the acknowledgment clause removed', 'JDOM'), (r'apache', 'Apache-2.0'), (r'\bmit\b', 'MIT'), (r'bsd-3-clause|new bsd|3-clause', 'BSD-3-Clause'),
    (r'bsd-2-clause|simplified bsd|2-clause', 'BSD-2-Clause'), (r'bsd style', 'BSD-style'),
    (r'eclipse distribution license|\bedl\b', 'EDL-1.0'), (r'eclipse public license v?\.? ?2|epl-2', 'EPL-2.0'),
    (r'eclipse public license (v ?)?1|epl-1', 'EPL-1.0'), (r'mozilla public license 1\.1', 'MPL-1.1'),
    (r'mozilla public license.*2', 'MPL-2.0'), (r'lgpl.*2\.1', 'LGPL-2.1'),
    (r'gpl.*version 2 with the gnu classpath exception', 'GPL-2.0-with-classpath-exception'),
    (r'bouncy castle', 'Bouncy-Castle'),
    (r'^public domain', 'Public-Domain'), (r'\bisc\b', 'ISC'), (r'cc0', 'CC0-1.0'), (r'unlicense', 'Unlicense'),
]


def gradle_home() -> Path:
    return Path(android_env()['GRADLE_USER_HOME']) / 'caches/modules-2/files-2.1'


def spdx(name: str) -> str | None:
    lowered = name.lower()
    return next((license for pattern, license in NAMES if re.search(pattern, lowered)), None)


def pom(home: Path, group: str, name: str, version: str) -> ET.Element | None:
    found = sorted((home / group / name / version).glob(f'*/{name}-{version}.pom'))
    if not found:
        return None
    text = re.sub(r'\sxmlns="[^"]+"', '', found[0].read_text(errors='replace'), count=1)
    return ET.fromstring(text.encode())


def licenses(home: Path, group: str, name: str, version: str, depth: int = 0) -> list[str] | None:
    """The POM's license names (each name and URL), from the nearest POM in its parent chain that has any."""
    root = pom(home, group, name, version)
    if root is None:
        return None
    found = [f'{l.findtext("name") or ""} {l.findtext("url") or ""}'.strip() for l in root.findall('licenses/license')]
    if found or depth > 8:
        return found
    parent = root.find('parent')
    if parent is None:
        return []
    return licenses(home, parent.findtext('groupId'), parent.findtext('artifactId'), parent.findtext('version'), depth + 1)


def shipped(env: dict) -> set[str]:
    """group:name of every library in the shipped app (app's release runtime classpath)."""
    proc = subprocess.run(gradle_command('-q', ':app:dependencies', '--configuration', 'releaseRuntimeClasspath'),
                          cwd=ROOT, env=env, capture_output=True, text=True)
    if proc.returncode != 0:
        sys.exit(f'Couldn\'t list the app\'s libraries:\n{(proc.stdout + proc.stderr)[-3000:]}')
    return {m.group(1) for m in re.finditer(r'--- ([\w.-]+:[\w.-]+):', proc.stdout)}


def findings() -> list[str]:
    found = []
    for settings in ('settings.gradle.kts', 'build-logic/settings.gradle.kts'):
        text = (ROOT / settings).read_text()
        repositories = set(re.findall(r'\b(\w+)\s*\(\s*\)\s*(?=[;}\n])', ' '.join(re.findall(r'repositories\s*\{([^}]*)\}', text))))
        if not repositories <= {'google', 'mavenCentral', 'gradlePluginPortal'} or 'FAIL_ON_PROJECT_REPOS' not in text \
                or re.search(r'\bmaven\s*[({]|\burl\s*[=(]|mavenLocal|flatDir|ivy\s*[({]', text):
            found.append(f'[allowed-dependencies] {settings}: libraries come only from google(), mavenCentral() and '
                         'gradlePluginPortal(), and modules can\'t add repositories (FAIL_ON_PROJECT_REPOS).')
    metadata_file = ROOT / 'gradle/verification-metadata.xml'
    if not metadata_file.is_file():
        return found + ['[allowed-dependencies] gradle/verification-metadata.xml is missing: Gradle checks every '
                        'library against it.']
    metadata = ET.parse(metadata_file).getroot()
    configuration = metadata.find('v:configuration', NS)
    if configuration is None or configuration.findtext('v:verify-metadata', namespaces=NS) != 'true' \
            or configuration.find('v:trusted-artifacts', NS) is not None:
        found.append('[allowed-dependencies] gradle/verification-metadata.xml must verify every artifact '
                     '(verify-metadata true) and trust none without a checksum.')
    env = android_env()
    home, in_app = gradle_home(), shipped(env)
    components = [(c.get('group'), c.get('name'), c.get('version')) for c in metadata.findall('v:components/v:component', NS)]
    if any(pom(home, *c) is None for c in components):
        # A cold cache: have Gradle fetch (and verify) every project's libraries, whose POMs the license check reads.
        tasks = [':' + folder.replace('/', ':') + ':dependencies' for folder, _ in modules()]
        proc = subprocess.run(gradle_command('-q', *tasks), cwd=ROOT, env=env, capture_output=True, text=True)
        if proc.returncode != 0:
            return found + [f'[allowed-dependencies] Gradle couldn\'t resolve the libraries:\n{(proc.stdout + proc.stderr)[-3000:]}']
    for component in metadata.findall('v:components/v:component', NS):
        group, name, version = component.get('group'), component.get('name'), component.get('version')
        artifacts = [a.get('name') for a in component.findall('v:artifact', NS)]
        if all(a.endswith('.pom') for a in artifacts) or name.endswith('.gradle.plugin'):
            continue  # a parent POM, BOM or plugin marker: no code of its own
        names = licenses(home, group, name, version)
        coordinate = f'{group}:{name}:{version}'
        if not names:
            found.append(f'[allowed-dependencies] {coordinate}: no license found in its POM or parents. Don\'t use it '
                         'until someone has read its license; stop and report.')
            continue
        ids = [spdx(n) for n in names]
        allowed = PERMISSIVE if f'{group}:{name}' in in_app else PERMISSIVE | TOOLS_ONLY
        if not any(i in allowed for i in ids if i):  # several licenses in a POM are alternatives
            where = 'shipped in the app' if f'{group}:{name}' in in_app else 'a build or test tool'
            found.append(f'[allowed-dependencies] {coordinate} ({where}): license {"; ".join(names)} isn\'t allowed '
                         f'there. Shipped libraries are permissive only. Write the code without it, or stop and report.')
    return found


if __name__ == '__main__':
    problems = findings()
    print('\n'.join(problems) if problems else 'deps: OK')
    sys.exit(1 if problems else 0)
