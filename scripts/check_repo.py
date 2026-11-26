"""Check repo structure: rule and case format, catalog coverage, skill frontmatter, relative links.

Also, per rule and platform: a fail case that runs without the starter's example (so a real app's run proves the
rule), unless rules/example-only.toml lists it; and a gate key, or the rule's id in the starter's agent guidance
(AGENTS.template.md or the verify skill), so no rule is a convention nobody checks or tells the agent about."""
from pathlib import Path
import os
import re
import sys
import tomllib

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from platforms import PLATFORMS  # noqa: E402

RULE_KEYS = ['id', 'layer', 'summary', 'problem', 'message', 'escape_hatches', 'origin']
LAYERS = {'1', '2', '1+2', '3', 'foundation'}
LINK = re.compile(r'\]\(([^)\s]+)\)')
CASE_FEATURES = ROOT / 'rules' / 'case-feature'  # rules/case-feature/<platform>: a feature cases can bring; not a rule
FEATURE_NAME = re.compile(r'Feature\("([A-Z][A-Za-z0-9]*)"')  # same check as test_rules.py
FEATURES_FILE = Path('Tuist/ProjectDescriptionHelpers/Features.swift')
SHAPE = (ROOT / 'starters/ios/template/Tuist/ProjectDescriptionHelpers/ModuleShape.swift').read_text()
SHARED_LINKS = set(re.findall(r'case (\w+)', SHAPE.split('enum SharedLink', 1)[1].split('}', 1)[0]))
EXAMPLE_ONLY = ROOT / 'rules' / 'example-only.toml'  # shrink-only: rules proven on a platform only through its example
IOS_KEYS = ('case_feature', 'features', 'shared_links', 'generate_adapters', 'needs_fixtures')  # iOS-only case keys
errors = []


def rel(path: Path) -> str:
    return str(path.relative_to(ROOT))


def load(path: Path) -> dict:
    try:
        return tomllib.loads(path.read_text())
    except tomllib.TOMLDecodeError as error:
        errors.append(f'{rel(path)}: invalid TOML: {error}')
        return {}


def guidance(platform) -> str:
    """What the starter tells its agent: AGENTS.template.md and the verify skill."""
    files = [platform.starter / 'AGENTS.template.md', platform.starter / '.agents/skills/verify/SKILL.md']
    return '\n'.join(f.read_text() for f in files if f.is_file())


def check_cases(rule_dir: Path, rule: dict, platform) -> None:
    """A rule's cases on one platform: rules/<id>/<platform>/<case>/case.toml."""
    section = rule[platform.name]
    if 'layer' in section and section['layer'] not in LAYERS:
        errors.append(f'{rel(rule_dir)}/rule.toml: {platform.name}.layer must be one of {sorted(LAYERS)}')
    if not any(key in platform.gates for key in section) and not re.search(rf'\b{re.escape(rule_dir.name)}\b',
                                                                          guidance(platform)):
        errors.append(f'{rel(rule_dir)}/rule.toml: [{platform.name}] names no gate ({", ".join(platform.gates)}), and the '
                      f'{platform.name} starter\'s AGENTS.template.md and verify skill don\'t name {rule_dir.name}: an '
                      'agent is neither stopped nor told')
    expects = []
    example_free_fail = False
    for case_path in sorted((rule_dir / platform.name).glob('*/case.toml')):
        case = load(case_path)
        expects.append(case.get('expect'))
        example_free_fail |= case.get('expect') == 'fail' and case.get('uses_example') is False
        if case.get('expect') not in ('fail', 'pass'):
            errors.append(f'{rel(case_path)}: expect must be "fail" or "pass"')
        if case.get('enforced_by') not in platform.gates:
            errors.append(f'{rel(case_path)}: enforced_by must be one of {platform.gates}')
        if case.get('expect') == 'fail' and not case.get('diagnostic'):
            errors.append(f'{rel(case_path)}: fail cases need a diagnostic')
        if platform.name != 'ios' and (ios_only := [k for k in IOS_KEYS if k in case]):
            errors.append(f'{rel(case_path)}: iOS-only keys in a {platform.name} case: {", ".join(ios_only)}')
        for key in ('case_feature', 'generate_adapters'):
            if key in case and not isinstance(case[key], bool):
                errors.append(f'{rel(case_path)}: {key} must be true or false')
        features = case.get('features', [])
        if not isinstance(features, list) or not all(isinstance(f, str) and FEATURE_NAME.match(f) for f in features):
            errors.append(f'{rel(case_path)}: features must be a list of Swift declarations, each `Feature("<Name>", ...)` '
                          'with an UpperCamelCase name')
            features = []
        links = case.get('shared_links', [])
        if not isinstance(links, list) or not all(isinstance(l, str) and l in SHARED_LINKS for l in links):
            errors.append(f'{rel(case_path)}: shared_links must be a list of SharedLink cases: {sorted(SHARED_LINKS)}')
        needs = case.get('needs_fixtures', [])
        if not isinstance(needs, list) or not all(isinstance(n, str) for n in needs):
            errors.append(f'{rel(case_path)}: needs_fixtures must be a list of fixture names')
        uses = case.get('uses_example')
        if uses is not False and not (isinstance(uses, str) and uses.strip()):
            errors.append(f'{rel(case_path)}: uses_example must be false, or say how the case uses the '
                          f'{platform.example_name} example')
        if uses is False:
            # A case that claims to apply to any app may not touch the example.
            texts = [(f.relative_to(case_path.parent), f.read_text()) for f in case_path.parent.rglob('*')
                     if f.is_file() and f.name != 'case.toml']
            texts += [(Path('case.toml'), ' '.join([case.get('diagnostic', '')] + features
                                                  + [' '.join(e.values()) for e in case.get('edits', [])]))]
            if (case_path.parent / FEATURES_FILE).is_file():
                errors.append(f'{rel(case_path)}: uses_example = false, but {FEATURES_FILE} replaces the app\'s feature '
                              'declaration; add features with `features` (and `shared_links`) instead')
            for path, text in texts:
                hit = platform.example.search(text) or next(
                    (m for part in path.parts[1:-1] if (m := platform.example.match(part))), None) or (
                    path.parts[0] == platform.targets and len(path.parts) > 1 and platform.example.match(path.parts[1]))
                if hit:
                    errors.append(f'{rel(case_path)}: uses_example = false, but {path} uses the example ({hit.group(0)})')
                    break
        edits = case.get('edits', [])
        for edit in edits:
            if set(edit) != {'file', 'find', 'replace'} or edit.get('file') not in platform.editable:
                errors.append(f'{rel(case_path)}: each edit needs exactly file (one of {platform.editable}), find and replace')
        case_dir = case_path.parent
        if not (any(list(case_dir.glob(pattern)) for pattern in platform.case_files) or edits or features
                or case.get('case_feature')):
            errors.append(f'{rel(case_path)}: no {", ".join(platform.case_files)} files, edits, features or case_feature')
    if 'fail' not in expects and not section.get('tests_pending'):
        errors.append(f'{rel(rule_dir)}: needs a {platform.name} fail case, or {platform.name}.tests_pending explaining why not')
    listed = rule_dir.name in example_only.get(platform.name, [])
    if 'fail' in expects and not example_free_fail and not listed:
        errors.append(f'{rel(rule_dir)}: every {platform.name} fail case uses the example, so no real app proves the rule; '
                      'add a fail case with uses_example = false')
    elif listed and ('fail' not in expects or example_free_fail):
        errors.append(f'{rel(EXAMPLE_ONLY)}: {rule_dir.name} ({platform.name}) has a fail case without the example now: '
                      'take it off the list')


rule_dirs = sorted(p for p in (ROOT / 'rules').iterdir() if p.is_dir() and p != CASE_FEATURES)
example_only = load(EXAMPLE_ONLY) if EXAMPLE_ONLY.is_file() else {}
for name, listed in example_only.items():
    if name not in PLATFORMS or not isinstance(listed, list):
        errors.append(f'{rel(EXAMPLE_ONLY)}: {name} must be a platform ({", ".join(PLATFORMS)}) with a list of rule ids')
    elif missing := [r for r in listed if not (ROOT / 'rules' / r / name).is_dir()]:
        errors.append(f'{rel(EXAMPLE_ONLY)}: {", ".join(missing)} ({name}) has no {name} cases: take it off the list')
for kit_dir in sorted(p for p in CASE_FEATURES.iterdir() if p.is_dir()) if CASE_FEATURES.is_dir() else []:
    platform = PLATFORMS.get(kit_dir.name)
    kit = load(kit_dir / 'feature.toml') if (kit_dir / 'feature.toml').is_file() else {}
    if platform is None or platform.name != 'ios' or not kit.get('features') \
            or not all(isinstance(f, str) and FEATURE_NAME.match(f) for f in kit['features']) \
            or not list((kit_dir / platform.targets).glob('*/*.swift')):
        errors.append(f'{rel(kit_dir)}: the case feature (iOS only) needs feature.toml with `features` and Targets/<Target>/*.swift')
        continue
    for f in sorted(kit_dir.rglob('*')):
        if f.is_file() and (hit := platform.example.search(f.read_text() + ' ' + str(f.relative_to(kit_dir)))):
            errors.append(f'{rel(f)}: the case feature must apply to any app, but uses the example ({hit.group(0)})')
            break
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
    if not any(isinstance(rule.get(name), dict) for name in PLATFORMS):
        errors.append(f'{rel(path)}: needs a table for at least one platform ({", ".join(PLATFORMS)})')
    for folder in rule_dir.iterdir():
        if folder.is_dir() and folder.name not in PLATFORMS:
            errors.append(f'{rel(folder)}: not a platform ({", ".join(PLATFORMS)})')
    for platform in PLATFORMS.values():
        if isinstance(rule.get(platform.name), dict):
            check_cases(rule_dir, rule, platform)
        elif (rule_dir / platform.name).is_dir():
            errors.append(f'{rel(rule_dir)}: has {platform.name} cases but no [{platform.name}] table in rule.toml')

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
counts = {name: len(list((ROOT / 'rules').glob(f'*/{name}/*/case.toml'))) for name in PLATFORMS}
print(f'Repo OK: {len(rule_dirs)} rules, ' + ', '.join(f'{n} {name} cases' for name, n in counts.items())
      + ', all in the catalog; skills and links valid.')
