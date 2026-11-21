"""The verify gate: every feature is in the feature map, and every journey it names passes against the built app.

Map check (feature-map/*.toml):
  - every crate in crates/features/ is in exactly one feature's `modules`, and every module named is such a crate
  - each journey has a `name` and a `proves`, and no journey is named twice (in one feature or across features)
Run: the journeys are the #[test] functions in crates/app/tests/journeys.rs, each running the built app binary.
  - every journey there is in the map, and every journey in the map is there (one that never runs fails)
  - each journey runs on its own; it fails if it doesn't pass
Evidence (each journey's result and output) goes to .build/evidence/latest/evidence.md.

Usage: python3 scripts/verify.py [map|run]     (default: run, which does the map check first)
"""
from pathlib import Path
import re
import subprocess
import sys
import tomllib

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tools import rust_env  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
JOURNEYS = ['cargo', 'test', '--package', 'app', '--test', 'journeys', '--']
EVIDENCE = ROOT / '.build/evidence/latest'


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
    crates = sorted(p.parent.name for p in (ROOT / 'crates/features').glob('*/Cargo.toml'))
    claimed: dict[str, str] = {}
    for feature in features:
        where = feature['file']
        for key in ('id', 'summary', 'modules', 'journeys'):
            if key not in feature:
                errors.append(f'[verified-features] {where}: missing `{key}`')
        for module in feature.get('modules', []):
            if module not in crates:
                errors.append(f'[verified-features] {where}: module `{module}` isn\'t a feature crate '
                              f'(crates/features/{module}). Name the feature crates this feature is made of.')
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
    for crate in crates:
        if crate not in claimed:
            errors.append(f'[verified-features] crates/features/{crate} isn\'t in the feature map. Add '
                          f'feature-map/<id>.toml naming it in `modules`, with journeys in crates/app/tests/journeys.rs '
                          'that prove it works in the app.')
    seen: dict[str, str] = {}
    for feature in features:
        for journey in feature.get('journeys', []):
            name = journey.get('name')
            if name in seen:
                errors.append(f'[verified-features] {feature["file"]}: journey `{name}` is already named in {seen[name]}')
            elif name:
                seen[name] = feature['file']
    return errors


def run(env: dict, features: list[dict]) -> list[str]:
    listed = subprocess.run(JOURNEYS + ['--list', '--format', 'terse'], cwd=ROOT, env=env, capture_output=True, text=True)
    if listed.returncode != 0:
        return [f'[verified-features] the journeys didn\'t build:\n{(listed.stdout + listed.stderr).strip()[-4000:]}']
    in_code = re.findall(r'^(\S+): test$', listed.stdout, re.M)
    mapped = {j['name']: f['file'] for f in features for j in f.get('journeys', []) if j.get('name')}
    errors = [f'[verified-features] journey `{name}` in crates/app/tests/journeys.rs isn\'t in the feature map. Add it '
              'to the feature it proves.' for name in in_code if name not in mapped]
    errors += [f'[verified-features] {mapped[name]}: journey `{name}` isn\'t in crates/app/tests/journeys.rs, so it '
               'never runs.' for name in mapped if name not in in_code]
    lines = ['# Verify evidence', '']
    for feature in features:
        lines += [f'## {feature.get("id")}: {feature.get("summary", "")}', '']
        for journey in feature.get('journeys', []):
            name = journey.get('name')
            if name not in in_code:
                continue
            proc = subprocess.run(JOURNEYS + ['--exact', name, '--nocapture', '--test-threads', '1'], cwd=ROOT, env=env,
                                  capture_output=True, text=True)
            passed = proc.returncode == 0 and re.search(r'^test result: ok\. 1 passed', proc.stdout, re.M)
            if not passed:
                errors.append(f'[verified-features] journey `{name}` failed ({feature["file"]}). Fix the app, or if the '
                              f'journey is wrong, say why; never weaken it.\n{(proc.stdout + proc.stderr).strip()[-3000:]}')
            # --nocapture prints the journey's output after `test <name> ... ` and the result after it.
            output = '\n'.join(re.sub(r'^test \S+ \.\.\. ', '', l) for l in proc.stdout.splitlines()
                               if not l.startswith(('running ', 'test result:')) and l.strip() not in ('ok', 'FAILED'))
            lines += [f'### {name}: {"PASS" if passed else "FAIL"}', '', journey.get('proves', ''), '', '```',
                      output.strip(), '```', '']
    EVIDENCE.mkdir(parents=True, exist_ok=True)
    (EVIDENCE / 'evidence.md').write_text('\n'.join(lines))
    return errors


if __name__ == '__main__':
    mode = sys.argv[1] if len(sys.argv) > 1 else 'run'
    if mode not in ('map', 'run'):
        sys.exit(__doc__)
    if mode == 'run':
        (EVIDENCE / 'evidence.md').unlink(missing_ok=True)  # never leave an earlier run's evidence as the latest
    features, errors = load_map()
    errors += map_errors(features)
    if mode == 'run' and not errors:
        errors += run(rust_env(), features)
    done = (f'verify: every feature mapped; every journey passed. Evidence: {EVIDENCE / "evidence.md"}' if mode == 'run'
            else 'verify map: every feature mapped (journeys not run)')
    print('\n'.join(errors) if errors else done)
    sys.exit(1 if errors else 0)
