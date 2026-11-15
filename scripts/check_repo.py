"""Check repo structure: rule and case format, catalog coverage, skill frontmatter, relative links."""
from pathlib import Path
import re
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[1]
RULE_KEYS = ['id', 'layer', 'summary', 'problem', 'message', 'escape_hatches', 'origin', 'ios']
LAYERS = {'1', '2', '1+2', '3', 'foundation'}
LINK = re.compile(r'\]\(([^)\s]+)\)')
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
        if case.get('enforced_by') not in ('compiler', 'checker'):
            errors.append(f'{rel(case_path)}: enforced_by must be "compiler" or "checker"')
        if case.get('enforced_by') == 'compiler' and case.get('expect') == 'fail' and not case.get('diagnostic'):
            errors.append(f'{rel(case_path)}: compiler fail cases need a diagnostic')
        if not list((case_path.parent / 'Sources').glob('*/*.swift')):
            errors.append(f'{rel(case_path)}: no Sources/<Module>/*.swift files')
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
        if not (doc.parent / target.split('#', 1)[0]).exists():
            errors.append(f'{rel(doc)}: broken link "{target}"')

if errors:
    print('\n'.join(errors))
    sys.exit(1)
case_count = len(list((ROOT / 'rules').glob('*/ios/*/case.toml')))
print(f'Repo OK: {len(rule_dirs)} rules, {case_count} cases, all in the catalog; skills and links valid.')
