"""The settings gate: the enforcement settings in effect are the ones in arch/settings.json, so weakening a check fails
here as well as in code-owner review. It reads what the tools would use, not the files' text:

  compiler    each package's options as the compiler resolves them (effect-tsgo tsc --showConfig): the strict options
              for every package, lib and types for its role, and no role config (arch/tsconfig/) that replaces the
              Effect language service's plugin list, except the journeys' (plugins: [])
  effect      the Effect language service in tsconfig.effect.json: every diagnostic, override and option as recorded
  lint        vite.config.ts's lint settings as Node imports them: plugins, categories, options, ignorePatterns and
              every recorded rule unchanged; added rules may only be errors; no overrides
  test        vite.config.ts's test settings as Node imports them, unchanged
  workspace   pnpm-workspace.yaml: no hoisting, only the recorded install scripts (all off) and overrides
  codeowners  CODEOWNERS lists every enforcement path

Changing one of these on purpose means changing arch/settings.json in the same change (both are code-owned).

Usage: python3 scripts/settings.py
"""
from pathlib import Path
import json
import re
import subprocess
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent))
from tools import install, node_env  # noqa: E402

ROOT = Path(__file__).resolve().parents[1]
FIX = ('Restore it. If the change is meant, it needs the owner: they change the setting and arch/settings.json together. '
       'Never weaken a check to make code pass; fix the code, or stop and report.')


def jsonc(path: Path) -> dict:
    return json.loads(re.sub(r'^\s*//.*$', '', path.read_text(), flags=re.M))


def compiler_findings(env: dict, expected: dict) -> list[str]:
    out = []
    shape = json.loads((ROOT / 'arch/shape.json').read_text())
    configs = [(role, p) for role, spec in shape['roles'].items() for folder in spec['folders']
               for p in sorted(ROOT.glob(f'{folder}/tsconfig.json'))]
    configs.append(('journeys', ROOT / 'apps/desktop/journeys/tsconfig.json'))
    for role, config in configs:
        where = config.relative_to(ROOT)
        proc = subprocess.run(['effect-tsgo', 'tsc', '--showConfig', '-p', str(where)], cwd=ROOT, env=env,
                              capture_output=True, text=True)
        if proc.returncode != 0:
            out.append(f'[protected-enforcement] {where}: the compiler couldn\'t read it: {proc.stdout + proc.stderr}')
            continue
        options = json.loads(proc.stdout)['compilerOptions']
        wanted = {**expected['all'], **expected['roles'].get(role, {})}
        for key, value in wanted.items():
            if options.get(key) != value:
                out.append(f'[protected-enforcement] {where}: compiler option {key} is {options.get(key)!r}, '
                           f'not {value!r}. {FIX}')
    for config in sorted((ROOT / 'arch/tsconfig').glob('*.json')):
        plugins = jsonc(config).get('compilerOptions', {}).get('plugins')
        if plugins is not None and plugins != expected['plugins'].get(config.stem):
            out.append(f'[protected-enforcement] arch/tsconfig/{config.name}: replaces the Effect language service\'s '
                       f'plugins. {FIX}')
    return out


def effect_findings(expected: dict) -> list[str]:
    plugins = jsonc(ROOT / 'tsconfig.effect.json').get('compilerOptions', {}).get('plugins', [])
    actual = plugins[0] if plugins else {}
    if actual == expected:
        return []
    severity = actual.get('diagnosticSeverity', {})
    changed = sorted(k for k, v in expected.get('diagnosticSeverity', {}).items() if severity.get(k) != v)
    other = sorted(k for k in set(expected) | set(actual) if k != 'diagnosticSeverity' and expected.get(k) != actual.get(k))
    what = ', '.join([f'diagnostic {k}' for k in changed] + [f'`{k}`' for k in other]) or 'its settings'
    return [f'[protected-enforcement] tsconfig.effect.json: the Effect language service changed ({what}). {FIX}']


def vite_config(env: dict) -> dict:
    proc = subprocess.run(['node', '--input-type=module', '-e',
                           'process.stdout.write(JSON.stringify((await import("./vite.config.ts")).default))'],
                          cwd=ROOT, env=env, capture_output=True, text=True)
    if proc.returncode != 0:
        sys.exit(f'vite.config.ts couldn\'t be loaded:\n{(proc.stdout + proc.stderr)[-2000:]}')
    return json.loads(proc.stdout)


def severity(value: object) -> object:
    return value[0] if isinstance(value, list) and value else value


def lint_findings(actual: dict, expected: dict) -> list[str]:
    out = []
    for key in sorted(set(expected) | set(actual)):
        if key == 'rules':
            continue
        if actual.get(key) != expected.get(key):
            out.append(f'[protected-enforcement] vite.config.ts: lint `{key}` changed. {FIX}')
    rules = actual.get('rules', {})
    for rule, value in expected.get('rules', {}).items():
        if rules.get(rule) != value:
            out.append(f'[protected-enforcement] vite.config.ts: lint rule {rule} is {rules.get(rule)!r}, '
                       f'not {value!r}. {FIX}')
    for rule, value in rules.items():
        if rule not in expected.get('rules', {}) and severity(value) != 'error':
            out.append(f'[protected-enforcement] vite.config.ts: added lint rule {rule} must be an error, not '
                       f'{severity(value)!r}. {FIX}')
    return out


def workspace_findings(expected: dict) -> list[str]:
    text = (ROOT / 'pnpm-workspace.yaml').read_text()
    out = []
    checks = {
        'hoist': re.search(r'^hoist:\s*false\s*$', text, re.M),
        'publicHoistPattern': re.search(r'^publicHoistPattern:\s*\[\]\s*$', text, re.M),
    }
    out += [f'[protected-enforcement] pnpm-workspace.yaml: `{key}` must be {json.dumps(expected[key])}. {FIX}'
            for key, found in checks.items() if not found]
    for section in ('allowBuilds', 'overrides'):
        block = re.search(rf'^{section}:\n((?:[ \t]+.*\n?|\s*#.*\n?)*)', text, re.M)
        entries = dict(re.findall(r'^[ \t]+["\']?([^"\'#:\s][^:#]*?)["\']?:\s*(\S.*?)\s*$', block.group(1), re.M)) if block else {}
        wanted = {k: json.dumps(v) if isinstance(v, bool) else v for k, v in expected[section].items()}
        if entries != wanted:
            out.append(f'[protected-enforcement] pnpm-workspace.yaml: `{section}` must be exactly {expected[section]}. {FIX}')
    return out


def codeowners_findings(expected: list[str]) -> list[str]:
    path = ROOT / 'CODEOWNERS'
    owned = {line.split()[0] for line in path.read_text().splitlines()
             if line.strip() and not line.startswith('#') and len(line.split()) > 1} if path.is_file() else set()
    missing = [p for p in expected if p not in owned]
    return [f'[protected-enforcement] CODEOWNERS: no code owner for {", ".join(missing)}. Every enforcement path needs '
            f'one. {FIX}'] if missing else []


def findings(env: dict) -> list[str]:
    expected = json.loads((ROOT / 'arch/settings.json').read_text())
    config = vite_config(env)
    out = compiler_findings(env, expected['compiler'])
    out += effect_findings(expected['effect'])
    out += lint_findings(config.get('lint', {}), expected['lint'])
    if config.get('test') != expected['test']:
        out.append(f'[protected-enforcement] vite.config.ts: the test settings changed (retries, `.only`, which files '
                   f'run, fake timers). {FIX}')
    out += workspace_findings(expected['workspace'])
    out += codeowners_findings(expected['codeowners'])
    return out


if __name__ == '__main__':
    env = node_env()
    install(env)
    found = findings(env)
    print('\n'.join(found) if found else 'settings: every enforcement setting is as recorded')
    sys.exit(1 if found else 0)
