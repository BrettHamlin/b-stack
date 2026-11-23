"""Build the blind pick page: one page for every lane, two candidates at a time.

The config (TOML) lists lanes. Each lane points at a pairs file: a JSON list of
{"id", "title", "note", "x", "y"}, where x and y are image paths (absolute, or
relative to the pairs file). Which side each candidate lands on is fixed per pair
by a hash, so the judge never sees labels and the sides stay put between builds.

Animated WebP or GIF candidates become PNG frame strips that the page plays on a
canvas itself (this needs Pillow). Everything else is copied as is.

Answers are stored in the published page's db: collection "picks", one doc per
pair, id "<lane>__<pair id>", {lane, pair, choice: "x" | "y" | "tie", left, at}.
export.py turns them into answers.json per lane.

Output: <out>/index.html plus <out>/img/*. Publish index.html with img/ as files.
Usage: python3 build.py <config.toml> <out_dir>
"""
from pathlib import Path
import hashlib
import html
import json
import re
import shutil
import sys
import tomllib

TEMPLATE = Path(__file__).resolve().parent / 'template.html'
LANE_KEY = re.compile(r'^[a-z0-9]+(-[a-z0-9]+)*$')  # no "__", which separates lane and pair in doc ids
PAIR_ID = re.compile(r'^[A-Za-z0-9][A-Za-z0-9._-]*$')  # no "/", which would split the doc path
ANIMATED = ('.webp', '.gif')
IMAGES = ('.png', '.jpg', '.jpeg', '.webp', '.gif', '.svg')
LANE_FIELDS = ('key', 'name', 'question', 'how', 'layout', 'sizes')
BIG_IMAGE = 300_000  # bytes; larger images make the page slow to load


class ConfigError(Exception):
    pass


def load_config(path: Path) -> dict:
    config = tomllib.loads(path.read_text())
    lanes = config.get('lane', [])
    if not lanes:
        raise ConfigError(f'{path}: no [[lane]] tables')
    keys = set()
    for lane in lanes:
        for field in ('key', 'name', 'question', 'pairs'):
            if not isinstance(lane.get(field), str) or not lane[field].strip():
                raise ConfigError(f'{path}: every lane needs a "{field}"')
        if not LANE_KEY.match(lane['key']):
            raise ConfigError(f'{path}: lane key "{lane["key"]}" must be lowercase letters, digits and single dashes')
        if lane['key'] in keys:
            raise ConfigError(f'{path}: lane key "{lane["key"]}" is used twice')
        keys.add(lane['key'])
        if lane.get('layout', 'side') not in ('side', 'stack'):
            raise ConfigError(f'{path}: lane "{lane["key"]}": layout must be "side" or "stack"')
        sizes = lane.get('sizes', [])
        if not isinstance(sizes, list) or not all(isinstance(s, int) and s > 0 for s in sizes):
            raise ConfigError(f'{path}: lane "{lane["key"]}": sizes must be a list of widths in px')
        skip = lane.get('skip', [])
        if not isinstance(skip, list) or not all(isinstance(s, str) for s in skip):
            raise ConfigError(f'{path}: lane "{lane["key"]}": skip must be a list of id prefixes')
        for field in ('pairs', 'answers'):
            if field in lane:
                lane[field] = str((path.parent / lane[field]).resolve())
        lane.setdefault('answers', str(Path(lane['pairs']).with_name('answers.json')))
    return config


def side(lane: str, pair_id: str) -> str:
    """Which candidate goes on the left: fixed per pair, about half x and half y."""
    return 'x' if int(hashlib.sha1(f'{lane}:{pair_id}'.encode()).hexdigest(), 16) % 2 == 0 else 'y'


def animated_strip(src: Path, dest: Path) -> dict | None:
    """Animated WebP or GIF -> one horizontal PNG strip of its frames, or None if it has one frame."""
    from PIL import Image  # only animations need Pillow
    with Image.open(src) as im:
        n = getattr(im, 'n_frames', 1)
        if n < 2:
            return None
        w, h = im.size
        sheet = Image.new('RGBA', (w * n, h))
        durations = []
        for i in range(n):
            im.seek(i)
            sheet.paste(im.convert('RGBA'), (i * w, 0))
            durations.append(im.info.get('duration') or 0)
    sheet.save(dest, optimize=True)
    ms = round(sum(durations) / len(durations)) if any(durations) else 83
    return {'frames': n, 'w': w, 'h': h, 'ms': ms}


def lane_pairs(lane: dict, img: Path) -> list[dict]:
    src = Path(lane['pairs'])
    if not src.is_file():
        return []  # the lane has nothing to show yet; its tab says "coming"
    pairs = json.loads(src.read_text())
    if not isinstance(pairs, list):
        raise ConfigError(f'{src}: must be a JSON list of pairs')
    out, seen = [], set()
    for p in pairs:
        pid = str(p.get('id', ''))
        if not PAIR_ID.match(pid):
            raise ConfigError(f'{src}: pair id "{pid}" must be letters, digits, ".", "_" or "-"')
        if pid in seen:
            raise ConfigError(f'{src}: pair id "{pid}" is used twice')
        seen.add(pid)
        if any(pid.startswith(prefix) for prefix in lane.get('skip', [])):
            continue
        rec = {'id': pid, 'title': p.get('title', ''), 'note': p.get('note', ''), 'left': side(lane['key'], pid)}
        for s in ('x', 'y'):
            if s not in p:
                raise ConfigError(f'{src}: pair "{pid}" has no "{s}"')
            f = (src.parent / p[s]).resolve()
            if not f.is_file() or f.suffix.lower() not in IMAGES:
                raise ConfigError(f'{src}: pair "{pid}" {s}: {f} is not an image file ({", ".join(IMAGES)})')
            if f.stat().st_size > BIG_IMAGE:
                print(f'warning: {f} is over {BIG_IMAGE // 1000} KB; the page will load slowly', file=sys.stderr)
            stem = f'{lane["key"]}-{hashlib.sha1(f.read_bytes()).hexdigest()[:12]}'
            strip = animated_strip(f, img / f'{stem}-strip.png') if f.suffix.lower() in ANIMATED else None
            if strip:
                rec[s] = f'img/{stem}-strip.png'
                rec.setdefault('anim', {})[s] = strip
            else:
                shutil.copyfile(f, img / (stem + f.suffix.lower()))
                rec[s] = f'img/{stem}{f.suffix.lower()}'
        out.append(rec)
    return out


def build(config_path: Path, out: Path) -> dict[str, int]:
    config = load_config(config_path)
    img = out / 'img'
    if img.exists():
        shutil.rmtree(img)
    img.mkdir(parents=True)
    data = []
    for lane in config['lane']:
        data.append({k: lane[k] for k in LANE_FIELDS if k in lane} | {'pairs': lane_pairs(lane, img)})
    title = config.get('title', 'Art Picks')
    page = (TEMPLATE.read_text()
            .replace('__TITLE__', html.escape(title))
            .replace('__INTRO__', html.escape(config.get('intro', '')))
            .replace('/*DATA*/[]', json.dumps(data, separators=(',', ':')).replace('</', '<\\/')))
    (out / 'index.html').write_text(page)
    return {d['key']: len(d['pairs']) for d in data}


def main() -> None:
    if len(sys.argv) != 3:
        sys.exit(__doc__.strip().splitlines()[-1])
    try:
        counts = build(Path(sys.argv[1]).resolve(), Path(sys.argv[2]))
    except ConfigError as error:
        sys.exit(f'error: {error}')
    print('pairs per lane:', counts)


if __name__ == '__main__':
    main()
