"""The verify gate: every feature is in the feature map, and every journey it names passes against the built app.

Map check (feature-map/*.toml):
  - every package in packages/features/ is in exactly one feature's `modules`, and every module named is such a package
  - each journey has a `name` and a `proves`, and no journey is named twice (in one feature or across features)
Run: the renderer and the desktop app are built (vp build, vp pack), then the journeys run: the top-level tests in
apps/desktop/journeys/*.journey.ts, each launching the built Electron app through Playwright.
  - every journey there is in the map, and every journey in the map is there (one that never runs fails)
  - a journey fails if it doesn't pass or saves no screenshot (journeys/support/app.ts `checkpoint`)
Evidence (screenshots per journey, and evidence.md listing them) goes to .build/evidence/latest/.

Usage: python3 scripts/verify.py [map|run]     (default: run, which does the map check first)
"""
from pathlib import Path
import json
import shutil
import subprocess
import sys
import tomllib

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tools import install, node_env  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
EVIDENCE = ROOT / '.build/evidence/latest'
JOURNEYS = 'apps/desktop/journeys'


def load_map() -> tuple[list[dict], list[str]]:
    features, errors = [], []
    for path in sorted((ROOT / 'feature-map').glob('*.toml')):
        try:
            entry = tomllib.loads(path.read_text())
        except tomllib.TOMLDecodeError as error:
            errors.append(f'[verified-features] feature-map/{path.name}: invalid TOML: {error}')
            continue
        entry['file'] = f'feature-map/{path.name}'
        features.append(entry)
    return features, errors


def map_errors(features: list[dict]) -> list[str]:
    errors = []
    packages = sorted(p.parent.name for p in (ROOT / 'packages/features').glob('*/package.json'))
    claimed: dict[str, str] = {}
    for feature in features:
        where = feature['file']
        for key in ('id', 'summary', 'modules', 'journeys'):
            if key not in feature:
                errors.append(f'[verified-features] {where}: missing `{key}`')
        for module in feature.get('modules', []):
            if module not in packages:
                errors.append(f'[verified-features] {where}: module `{module}` isn\'t a feature package '
                              f'(packages/features/{module}). Name the feature packages this feature is made of.')
            elif module in claimed:
                errors.append(f'[verified-features] {where}: module `{module}` is already in {claimed[module]}')
            else:
                claimed[module] = where
        if not feature.get('journeys'):
            errors.append(f'[verified-features] {where}: no journeys. Each feature needs at least one journey that '
                          'runs the app and shows the feature working.')
        for journey in feature.get('journeys', []):
            if not journey.get('name') or not journey.get('proves'):
                errors.append(f'[verified-features] {where}: each journey needs a `name` and what it `proves`')
    for package in packages:
        if package not in claimed:
            errors.append(f'[verified-features] packages/features/{package} isn\'t in the feature map. Add '
                          f'feature-map/<id>.toml naming it in `modules`, with journeys in {JOURNEYS}/ that prove it '
                          'works in the app.')
    seen: dict[str, str] = {}
    for feature in features:
        for journey in feature.get('journeys', []):
            name = journey.get('name')
            if name in seen:
                errors.append(f'[verified-features] {feature["file"]}: journey `{name}` is already named in {seen[name]}')
            elif name:
                seen[name] = feature['file']
    return errors


def build(env: dict) -> list[str]:
    for cmd in (['vp', '-C', 'apps/web', 'build'], ['vp', '-C', 'apps/desktop', 'pack']):
        proc = subprocess.run(cmd, cwd=ROOT, env=env, capture_output=True, text=True)
        if proc.returncode != 0:
            return [f'[verified-features] `{" ".join(cmd)}` failed, so the app can\'t run:\n'
                    f'{(proc.stdout + proc.stderr).strip()[-3000:]}']
    return []


def run(env: dict, features: list[dict]) -> list[str]:
    errors = build(env)
    if errors:
        return errors
    results = EVIDENCE / 'results.json'
    proc = subprocess.run(['vp', 'test', 'run', '--project', 'journeys', '--reporter=json', f'--outputFile={results}'],
                          cwd=ROOT, env=env, capture_output=True, text=True)
    if not results.is_file():
        return [f'[verified-features] the journeys didn\'t run:\n{(proc.stdout + proc.stderr).strip()[-4000:]}']
    report = json.loads(results.read_text())
    ran: dict[str, dict] = {}
    titles = [test['title'] for suite in report.get('testResults', []) for test in suite.get('assertionResults', [])]
    for suite in report.get('testResults', []):
        if suite.get('status') == 'failed' and not suite.get('assertionResults'):
            errors.append(f'[verified-features] {suite.get("name")} didn\'t load:\n{suite.get("message", "")[-3000:]}')
        for test in suite.get('assertionResults', []):
            if test.get('ancestorTitles'):
                errors.append(f'[verified-features] journey `{test.get("fullName")}`: journeys are top-level tests, '
                              'named as in the feature map (no describe blocks).')
            ran[test['title']] = test
    errors += [f'[verified-features] journey `{name}` is defined {titles.count(name)} times in {JOURNEYS}/. Each journey '
               'has one name, as in the feature map.' for name in sorted(set(titles)) if titles.count(name) > 1]
    mapped = {j['name']: f['file'] for f in features for j in f.get('journeys', []) if j.get('name')}
    errors += [f'[verified-features] journey `{name}` in {JOURNEYS}/ isn\'t in the feature map. Add it to the feature '
               'it proves.' for name in ran if name not in mapped]
    errors += [f'[verified-features] {mapped[name]}: journey `{name}` isn\'t in {JOURNEYS}/, so it never runs.'
               for name in mapped if name not in ran]
    lines = ['# Verify evidence', '']
    for feature in features:
        lines += [f'## {feature.get("id")}: {feature.get("summary", "")}', '']
        for journey in feature.get('journeys', []):
            name = journey.get('name')
            test = ran.get(name)
            if test is None:
                continue
            shots = sorted((EVIDENCE / name).glob('*.png')) if (EVIDENCE / name).is_dir() else []
            passed = test.get('status') == 'passed' and titles.count(name) == 1
            if titles.count(name) > 1:
                pass  # reported above
            elif not passed:
                message = '\n'.join(test.get('failureMessages', []))[-3000:]
                errors.append(f'[verified-features] journey `{name}` failed ({feature["file"]}). Fix the app, or if the '
                              f'journey is wrong, say why; never weaken it.\n{message}')
            elif not shots:
                errors.append(f'[verified-features] journey `{name}` saved no screenshot. Call checkpoint() where it '
                              'shows the feature working: screenshots are the evidence.')
            lines += [f'### {name}: {"PASS" if passed and shots else "FAIL"}', '', journey.get('proves', ''), '']
            lines += [f'- ![{shot.stem}]({name}/{shot.name})' for shot in shots] + ['']
    (EVIDENCE / 'evidence.md').write_text('\n'.join(lines))
    if proc.returncode != 0 and not errors:
        errors.append(f'[verified-features] the journeys failed:\n{(proc.stdout + proc.stderr).strip()[-3000:]}')
    return errors


if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else 'run'
    if mode not in ('map', 'run'):
        sys.exit(__doc__)
    if mode == 'run':
        shutil.rmtree(EVIDENCE, ignore_errors=True)  # never leave an earlier run's evidence as the latest
    features, errors = load_map()
    errors += map_errors(features)
    if mode == 'run' and not errors:
        EVIDENCE.mkdir(parents=True)
        env = node_env()
        install(env)
        errors += run(env, features)
    done = (f'verify: every feature mapped; every journey passed. Evidence: {EVIDENCE / "evidence.md"}' if mode == 'run'
            else 'verify map: every feature mapped (journeys not run)')
    print('\n'.join(errors) if errors else done)
    sys.exit(1 if errors else 0)
