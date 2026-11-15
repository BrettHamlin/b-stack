"""Check the guide's structure: rule entries complete, every rule mapped per platform, relative links resolve."""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
REQUIRED_SECTIONS = ['## Problem', '## Layer', '## Enforcement', '## Error message', '## Escape hatches', '## Origin']
SKIP_DIRS = {'.git', 'artifacts'}
LINK = re.compile(r'\]\(([^)\s]+)\)')

errors = []

rules = sorted(p for p in (ROOT / 'rules').glob('*.md') if p.name != 'README.md')
rule_ids = [p.stem for p in rules]
for path in rules:
    text = path.read_text()
    if not text.startswith(f'# {path.stem}\n'):
        errors.append(f'{path.relative_to(ROOT)}: first line must be "# {path.stem}"')
    for marker in ['**Status:**', '**Layer:**', *REQUIRED_SECTIONS]:
        if marker not in text:
            errors.append(f'{path.relative_to(ROOT)}: missing "{marker}"')

catalog = (ROOT / 'rules' / 'README.md').read_text()
for rule_id in rule_ids:
    if f'({rule_id}.md)' not in catalog:
        errors.append(f'rules/README.md: rule "{rule_id}" not listed in the catalog table')

for platform in sorted((ROOT / 'platforms').glob('*.md')):
    if platform.name == 'README.md':
        continue
    text = platform.read_text()
    if '## Rule mapping' not in text:
        errors.append(f'{platform.relative_to(ROOT)}: missing "## Rule mapping" section')
        continue
    mapping = text.split('## Rule mapping', 1)[1]
    for rule_id in rule_ids:
        if f'rules/{rule_id}.md)' not in mapping:
            errors.append(f'{platform.relative_to(ROOT)}: rule "{rule_id}" missing from rule mapping')

for doc in ROOT.rglob('*.md'):
    if SKIP_DIRS & set(doc.relative_to(ROOT).parts):
        continue
    for target in LINK.findall(doc.read_text()):
        if re.match(r'^[a-z]+:', target) or target.startswith('#') or target.startswith('/'):
            continue
        if not (doc.parent / target.split('#', 1)[0]).exists():
            errors.append(f'{doc.relative_to(ROOT)}: broken link "{target}"')

if errors:
    print('\n'.join(errors))
    sys.exit(1)
print(f'Guide OK: {len(rule_ids)} rules, all mapped per platform, all relative links resolve.')
