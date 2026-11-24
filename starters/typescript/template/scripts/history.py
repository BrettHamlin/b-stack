"""What the base branch proves stays proved: the verify gate's check of the feature map against the base branch.

Journeys and feature-map entries aren't code-owned, so a feature's change merges without the owner. This keeps that
from removing proof. Against the base (the merge base of HEAD and $BSTACK_BASE_REF, else origin/HEAD, else
origin/main), it fails when
  - a journey the base's feature map names is no longer in the map (deleted or renamed), unless its feature is gone
  - a feature the base's map has (by `id`) is no longer in the map while any of its modules is still here
unless the journey or feature is listed in arch/retired.toml, which is code-owned: removing proof needs the owner.
With no base (not a git checkout, or no such branch and $BSTACK_BASE_REF unset) it says so and passes; with
$BSTACK_BASE_REF set (CI on a pull request sets it), a base it can't find fails.

The same file is in every starter; the caller passes the folder its feature modules are in.
"""
from pathlib import Path
import os
import subprocess
import tomllib

RETIRED = 'arch/retired.toml'


def git(root: Path, *args: str) -> str | None:
    proc = subprocess.run(['git', *args], cwd=root, capture_output=True, text=True)
    return proc.stdout.strip() if proc.returncode == 0 else None


def base_commit(root: Path) -> tuple[str | None, str | None]:
    """(merge-base commit, error). Both None: no base to compare with."""
    if git(root, 'rev-parse', '--verify', 'HEAD^{commit}') is None:
        return None, None
    explicit = os.environ.get('BSTACK_BASE_REF', '').strip()
    candidates = [explicit] if explicit else ['origin/HEAD', 'origin/main']
    for ref in candidates:
        if git(root, 'rev-parse', '--verify', '--quiet', f'{ref}^{{commit}}') is not None:
            merge_base = git(root, 'merge-base', 'HEAD', ref)
            if merge_base or not explicit:
                return merge_base, None
    if explicit:
        return None, (f'[verified-features] BSTACK_BASE_REF is {explicit}, which isn\'t a commit in this checkout, so '
                      'removed journeys can\'t be found. In CI, check out with fetch-depth: 0.')
    return None, None


def base_map(root: Path, base: str) -> list[dict]:
    names = git(root, 'ls-tree', '--name-only', base, '--', 'feature-map/') or ''
    features = []
    for name in names.splitlines():
        if not name.endswith('.toml'):
            continue
        try:
            entry = tomllib.loads(git(root, 'show', f'{base}:./{name}') or '')
        except tomllib.TOMLDecodeError:
            continue
        entry['file'] = name
        features.append(entry)
    return features


def retired(root: Path) -> tuple[set[str], set[str]]:
    path = root / RETIRED
    data = tomllib.loads(path.read_text()) if path.is_file() else {}
    return set(data.get('journeys', [])), set(data.get('features', []))


def removed(root: Path, features: list[dict], feature_folder: str) -> list[str]:
    """Errors for proof the base branch has and this checkout lost. `features` is the current map (verify.py's
    load_map); `feature_folder` is where feature modules live (features, packages/features)."""
    base, error = base_commit(root)
    if error:
        return [error]
    if base is None:
        print('verify: no base branch to compare the feature map with (origin/main, or $BSTACK_BASE_REF); '
              'removed journeys aren\'t checked')
        return []
    current_ids = {f.get('id') for f in features}
    current_journeys = {j.get('name') for f in features for j in f.get('journeys', [])}
    gone_journeys, gone_features = retired(root)
    short = base[:10]
    errors = []
    for feature in base_map(root, base):
        fid = feature.get('id')
        if fid in gone_features:
            continue
        here = [m for m in feature.get('modules', []) if (root / feature_folder / m).is_dir()]
        if not here and fid not in current_ids:
            continue  # the feature was removed, modules and all
        if fid not in current_ids:
            errors.append(f'[verified-features] feature `{fid}` ({feature["file"]} on the base branch, {short}) is gone '
                          f'from the feature map, but its modules ({", ".join(here)}) are still here. Put its entry '
                          f'back. Retiring or renaming a feature needs the owner: list it in {RETIRED} (code-owned).')
        for journey in feature.get('journeys', []):
            name = journey.get('name')
            if name and name not in current_journeys and name not in gone_journeys:
                errors.append(f'[verified-features] journey `{name}` ({feature["file"]} on the base branch, {short}) '
                              'is gone from the feature map. Put it back (map entry and journey). Never delete or '
                              f'rename a journey to get verify to pass; if it must go, that needs the owner: list it '
                              f'in {RETIRED} (code-owned).')
    return errors
