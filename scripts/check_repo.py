"""Check repo structure: rule and case format, catalog coverage, skill frontmatter, relative links."""
from pathlib import Path
import os
import re
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[1]
RULE_KEYS = ['id', 'layer', 'summary', 'problem', 'message', 'escape_hatches', 'origin', 'ios']
LAYERS = {'1', '2', '1+2', '3', 'foundation'}
ENFORCERS = ('compiler', 'tuist', 'swiftlint', 'harmonize', 'tests', 'verify')
LINK = re.compile(r'\]\(([^)\s]+)\)')
EXAMPLE = re.compile(r'[\w.-]*(?:Settings|notification|save-fails)[\w.-]*')  # the starter's example feature
errors = []


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def load(path: Path) -> dict:
    try:
        return tomllib.loads(path.read_text())
    except tomllib.TOMLDecodeError as error:
        errors.append(f'{rel(path)}: invalid TOML: {error}')
        return {}


rule_dirs = sorted(p for p in (ROOT / 'rules').iterdir() if p.is_dir())
for rule_dir in rule_dirs:
    path = rule_dir / 'rule.toml'
    if not path.is_file():
        errors.append(f'{rel(rule_dir)}: missing rule.toml')
        continue
    rule = load(path)
    for key in RULE_KEYS:
        if key not in rule:
            errors.append(f'{rel(path)}: missing "{key}"')
    if rule.get('id') != rule_dir.name:
        errors.append(f'{rel(path)}: id must be "{rule_dir.name}"')
    if rule.get('layer') not in LAYERS:
        errors.append(f'{rel(path)}: layer must be one of {sorted(LAYERS)}')
    if not isinstance(rule.get('escape_hatches'), list):
        errors.append(f'{rel(path)}: escape_hatches must be a list')

    cases = sorted((rule_dir / 'ios').glob('*/case.toml'))
    expects = []
    for case_path in cases:
        case = load(case_path)
        expects.append(case.get('expect'))
        if case.get('expect') not in ('fail', 'pass'):
            errors.append(f'{rel(case_path)}: expect must be "fail" or "pass"')
        if case.get('enforced_by') not in ENFORCERS:
            errors.append(f'{rel(case_path)}: enforced_by must be one of {ENFORCERS}')
        if case.get('expect') == 'fail' and not case.get('diagnostic'):
            errors.append(f'{rel(case_path)}: fail cases need a diagnostic')
        uses = case.get('uses_example')
        if uses is not False and not (isinstance(uses, str) and uses.strip()):
            errors.append(f'{rel(case_path)}: uses_example must be false, or say how the case uses the Settings example')
        if uses is False:
            # A case that claims to apply to any app may not touch the example.
            texts = [(f.relative_to(case_path.parent), f.read_text()) for f in case_path.parent.rglob('*')
                     if f.is_file() and f.name != 'case.toml']
            texts += [(Path('case.toml'), ' '.join([case.get('diagnostic', '')] + [' '.join(e.values()) for e in case.get('edits', [])]))]
            for path, text in texts:
                hit = EXAMPLE.search(text) or (path.parts[0] == 'Targets' and len(path.parts) > 1 and EXAMPLE.match(path.parts[1]))
                if hit:
                    errors.append(f'{rel(case_path)}: uses_example = false, but {path} uses the example ({hit.group(0)})')
                    break
        edits = case.get('edits', [])
        for edit in edits:
            if set(edit) != {'file', 'find', 'replace'} or edit.get('file') != 'Project.swift':
                errors.append(f'{rel(case_path)}: each edit needs exactly file = "Project.swift", find and replace')
        case_dir = case_path.parent
        if not (list((case_dir / 'Targets').glob('*/*.swift')) or list((case_dir / 'feature-map').glob('*.toml'))
                or list((case_dir / 'Tuist/ProjectDescriptionHelpers').glob('*.swift')) or edits):
            errors.append(f'{rel(case_path)}: no Targets/<Target>/*.swift, feature-map/*.toml, '
                          'Tuist/ProjectDescriptionHelpers/*.swift files or edits')
    if 'fail' not in expects and not rule.get('ios', {}).get('tests_pending'):
        errors.append(f'{rel(rule_dir)}: needs an ios fail case, or ios.tests_pending explaining why not')

catalog = (ROOT / 'rules' / 'README.md').read_text()
for rule_dir in rule_dirs:
    if f'({rule_dir.name}/rule.toml)' not in catalog:
        errors.append(f'rules/README.md: "{rule_dir.name}" missing from the catalog table')

for skill in sorted((ROOT / 'skills').glob('*/SKILL.md')):
    head = skill.read_text().split('---')
    if len(head) < 3 or f'name: {skill.parent.name}' not in head[1] or 'description:' not in head[1]:
        errors.append(f'{rel(skill)}: frontmatter needs name: {skill.parent.name} and a description')

for doc in ROOT.rglob('*.md'):
    parts = set(doc.relative_to(ROOT).parts)
    if parts & {'.git', 'artifacts', '.build'}:
        continue
    for target in LINK.findall(doc.read_text()):
        if re.match(r'^[a-z]+:', target) or target.startswith(('#', '/')):
            continue
        path = doc.parent / target.split('#', 1)[0]
        if Path(os.path.normpath(path)).is_relative_to(ROOT / 'artifacts'):
            continue  # media outside Git; checked by verify_artifacts.py
        if not path.exists():
            errors.append(f'{rel(doc)}: broken link "{target}"')

if errors:
    print('\n'.join(errors))
    sys.exit(1)
case_count = len(list((ROOT / 'rules').glob('*/ios/*/case.toml')))
print(f'Repo OK: {len(rule_dirs)} rules, {case_count} cases, all in the catalog; skills and links valid.')
