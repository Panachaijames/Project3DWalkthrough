"""A gap report section: an uploaded version's model against its prototype's (docs/upload/ACCEPTANCE.md A-5, A-6; owner U4).

    node tools/run-builder-py.mjs tools/upload/gap-report.py <prototype version dir> <uploaded version dir>
        [--title <text>] [--classes <classes.json>] [--walk <walk.json>] [--out <file.md>]

Each version dir holds a model.json (a store's versions/<n>/, or any folder with one). Prints (or writes) one markdown
section for docs/upload/GAPS.md: per floor, in DRAWING coordinates (model + offset + the floor's sheetShift), the metrics
of A-5 side by side:

* wall area (union of the wall, column and parapet footprints at z0 < 0.01) and the area of the symmetric difference;
* wall runs (wall parts at z0 < 0.01);
* glass area (union of glass and pane footprints) and glass pieces;
* openings by kind, and how many of the upload's match a prototype opening of the same kind by centre within 0.2 m;
* lintels, sills, panes;
* plate area (union of the slabs) and its symmetric difference;
* rooms (count, names matched);
* furniture by kind;

then every difference over 0.05 m2, 1 opening or 1 piece as a row with its cause and class: one of "option now",
"option later", "check-and-fix now", "check-and-fix later", "accepted difference", or "to classify" until a
--classes file says (a JSON list of {"floor": key or null, "metric": text, "cause": text, "class": text}; a row takes the
first entry whose floor and metric match). --walk (A-6) gives the walk checks of the uploaded version: a JSON list, or
{"probes": [...]}, of {floor, kind, id, passed, detail}; the failing ones are listed with a class column the same way.
Floors are matched by key, else by their order. Drawing names are quoted as they are (markdown text; | escaped).
Read only: nothing is written but --out.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from pathlib import Path

from shapely.geometry import Polygon
from shapely.ops import unary_union

AREA_TOL = 0.05            # m2
COUNT_TOL = 1              # openings, pieces
MATCH_DIST = 0.2           # m, opening centres
CLASSES = ('option now', 'option later', 'check-and-fix now', 'check-and-fix later', 'accepted difference', 'to classify')
WALL_KINDS = ('wall', 'column', 'parapet')
GLASS_KINDS = ('glass', 'pane')


def load_model(d: Path) -> dict:
    p = d / 'model.json' if d.is_dir() else d
    return json.loads(p.read_bytes().decode('utf-8'))


def to_sheet(m: dict) -> dict[str, tuple[float, float]]:
    ox, oy = m['offset']
    return {f['key']: (ox + (f.get('sheetShift') or (0, 0))[0], oy + (f.get('sheetShift') or (0, 0))[1]) for f in m['floors']}


def _poly(p: dict, dx: float, dy: float):
    try:
        g = Polygon([(x + dx, y + dy) for x, y in p['o']], [[(x + dx, y + dy) for x, y in h] for h in p.get('h') or []])
        return g if g.is_valid else g.buffer(0)
    except (ValueError, TypeError):
        return None


def union(m: dict, floor: str, kinds: tuple[str, ...], ground_only: bool = True):
    dx, dy = to_sheet(m)[floor]
    polys = [_poly(p, dx, dy) for p in m['parts'] if p['floor'] == floor and p['kind'] in kinds
             and (not ground_only or p['z0'] < 0.01)]
    polys = [g for g in polys if g is not None and not g.is_empty]
    return unary_union(polys) if polys else Polygon()


def openings(m: dict, floor: str) -> list[dict]:
    dx, dy = to_sheet(m)[floor]
    return [{'id': o['id'], 'kind': o['kind'], 'c': (o['x'] + dx, o['y'] + dy)} for o in m['openings'] if o['floor'] == floor]


def matched_openings(a: list[dict], b: list[dict]) -> int:
    pairs = sorted((math.dist(x['c'], y['c']), i, j) for i, x in enumerate(a) for j, y in enumerate(b)
                   if x['kind'] == y['kind'] and math.dist(x['c'], y['c']) <= MATCH_DIST)
    ua, ub, n = set(), set(), 0
    for _, i, j in pairs:
        if i not in ua and j not in ub:
            ua.add(i)
            ub.add(j)
            n += 1
    return n


def floor_metrics(m: dict, floor: str) -> dict:
    parts = [p for p in m['parts'] if p['floor'] == floor]
    ops = openings(m, floor)
    rooms = [r['name'] for r in m['rooms'] if r['floor'] == floor]
    return {
        'walls': union(m, floor, WALL_KINDS),
        'glass': union(m, floor, GLASS_KINDS, ground_only=False),
        'plate': union(m, floor, ('slab',), ground_only=False),
        'wall runs': sum(1 for p in parts if p['kind'] == 'wall' and p['z0'] < 0.01),
        'glass pieces': sum(1 for p in parts if p['kind'] in GLASS_KINDS),
        'openings': ops,
        'lintels': sum(1 for p in parts if p['kind'] == 'lintel'),
        'sills': sum(1 for p in parts if p['kind'] == 'sill'),
        'panes': sum(1 for p in parts if p['kind'] == 'pane'),
        'rooms': rooms,
        'furniture': Counter(f['kind'] for f in m.get('furniture') or [] if f['floor'] == floor),
    }


def pair_floors(proto: dict, up: dict) -> list[tuple[str | None, str | None]]:
    pk, uk = [f['key'] for f in proto['floors']], [f['key'] for f in up['floors']]
    if set(pk) & set(uk):
        out = [(k, k if k in uk else None) for k in pk] + [(None, k) for k in uk if k not in pk]
    else:
        out = [(pk[i] if i < len(pk) else None, uk[i] if i < len(uk) else None) for i in range(max(len(pk), len(uk)))]
    return out


def md(s) -> str:
    return str(s).replace('|', '\\|').replace('\n', ' ')


def classify(rows: list[dict], classes: list[dict]) -> None:
    for r in rows:
        hit = next((c for c in classes if c.get('metric') == r['metric'] and c.get('floor') in (None, r['floor'])), None)
        r['cause'] = hit.get('cause', '') if hit else ''
        r['class'] = hit.get('class', 'to classify') if hit else 'to classify'
        if r['class'] not in CLASSES:
            raise ValueError(f'class {r["class"]!r} is not one of {", ".join(CLASSES)}')


def report(proto: dict, up: dict, *, title: str, classes: list[dict], walk: list[dict] | None) -> tuple[str, dict]:
    lines = [f'## {md(title)}', '',
             f'Prototype: {md(proto.get("project"))} ({len(proto["floors"])} floor(s), {len(proto["parts"])} parts); '
             f'upload: {md(up.get("project"))} ({len(up["floors"])} floor(s), {len(up["parts"])} parts). Drawing '
             f'coordinates (model + offset + sheetShift). Differences over {AREA_TOL} m2, {COUNT_TOL} opening or '
             f'{COUNT_TOL} piece are listed below the table.', '']
    gaps: list[dict] = []
    summary: dict = {'floors': {}}
    for pk, uk in pair_floors(proto, up):
        name = uk or pk
        lines.append(f'### Floor {md(pk)} (prototype) / {md(uk)} (upload)')
        lines.append('')
        if pk is None or uk is None:
            lines += [f'Only in the {"upload" if pk is None else "prototype"}.', '']
            gaps.append({'floor': name, 'metric': 'floor', 'prototype': pk or '-', 'upload': uk or '-', 'difference': 'missing'})
            continue
        a, b = floor_metrics(proto, pk), floor_metrics(up, uk)
        sym = {k: a[k].symmetric_difference(b[k]).area for k in ('walls', 'glass', 'plate')}
        matched = matched_openings(b['openings'], a['openings'])
        rows = [('wall area (m2)', f'{a["walls"].area:.2f}', f'{b["walls"].area:.2f}', f'sym. difference {sym["walls"]:.2f}'),
                ('wall runs', a['wall runs'], b['wall runs'], b['wall runs'] - a['wall runs']),
                ('glass area (m2)', f'{a["glass"].area:.2f}', f'{b["glass"].area:.2f}', f'sym. difference {sym["glass"]:.2f}'),
                ('glass pieces', a['glass pieces'], b['glass pieces'], b['glass pieces'] - a['glass pieces'])]
        ka, kb = Counter(o['kind'] for o in a['openings']), Counter(o['kind'] for o in b['openings'])
        for k in ('door', 'window', 'passage'):
            rows.append((f'{k}s', ka[k], kb[k], kb[k] - ka[k]))
        rows.append(('openings matched (centre within 0.2 m)', '-', f'{matched} of {len(b["openings"])}',
                     f'{len(a["openings"]) - matched} prototype openings unmatched'))
        for k in ('lintels', 'sills', 'panes'):
            rows.append((k, a[k], b[k], b[k] - a[k]))
        rows.append(('plate area (m2)', f'{a["plate"].area:.2f}', f'{b["plate"].area:.2f}', f'sym. difference {sym["plate"]:.2f}'))
        names_a, names_b = Counter(a['rooms']), Counter(b['rooms'])
        rows.append(('rooms', len(a['rooms']), len(b['rooms']), f'{sum((names_a & names_b).values())} names matched'))
        for k in sorted(set(a['furniture']) | set(b['furniture'])):
            rows.append((f'furniture: {k}', a['furniture'][k], b['furniture'][k], b['furniture'][k] - a['furniture'][k]))
        lines += ['| Metric | Prototype | Upload | Difference |', '|---|---|---|---|']
        lines += [f'| {md(r[0])} | {md(r[1])} | {md(r[2])} | {md(r[3])} |' for r in rows]
        lines.append('')
        for k, label in (('walls', 'wall area'), ('glass', 'glass area'), ('plate', 'plate area')):
            if sym[k] > AREA_TOL:
                gaps.append({'floor': name, 'metric': label, 'prototype': f'{a[k].area:.2f}', 'upload': f'{b[k].area:.2f}',
                             'difference': f'{sym[k]:.2f} m2 symmetric difference'})
        for k in ('wall runs', 'glass pieces', 'lintels', 'sills', 'panes'):
            if abs(b[k] - a[k]) >= COUNT_TOL and a[k] != b[k]:
                gaps.append({'floor': name, 'metric': k, 'prototype': a[k], 'upload': b[k], 'difference': f'{b[k] - a[k]:+d}'})
        for k in ('door', 'window', 'passage'):
            if ka[k] != kb[k]:
                gaps.append({'floor': name, 'metric': f'{k}s', 'prototype': ka[k], 'upload': kb[k], 'difference': f'{kb[k] - ka[k]:+d}'})
        if matched < max(len(a['openings']), len(b['openings'])):
            gaps.append({'floor': name, 'metric': 'openings matched', 'prototype': len(a['openings']), 'upload': len(b['openings']),
                         'difference': f'{matched} matched by centre'})
        if names_a != names_b:
            gaps.append({'floor': name, 'metric': 'rooms', 'prototype': len(a['rooms']), 'upload': len(b['rooms']),
                         'difference': ', '.join(sorted((names_a - names_b).elements())[:8]) or 'names differ'})
        for k in sorted(set(a['furniture']) | set(b['furniture'])):
            if a['furniture'][k] != b['furniture'][k]:
                gaps.append({'floor': name, 'metric': f'furniture: {k}', 'prototype': a['furniture'][k],
                             'upload': b['furniture'][k], 'difference': f'{b["furniture"][k] - a["furniture"][k]:+d}'})
        summary['floors'][name] = {'wallArea': [round(a['walls'].area, 2), round(b['walls'].area, 2)],
                                   'wallSymDiff': round(sym['walls'], 2), 'openingsMatched': matched,
                                   'plateSymDiff': round(sym['plate'], 2)}
    classify(gaps, classes)
    lines += ['### Differences', '']
    if gaps:
        lines += ['| Floor | Metric | Prototype | Upload | Difference | Cause | Class |', '|---|---|---|---|---|---|---|']
        lines += [f'| {md(g["floor"])} | {md(g["metric"])} | {md(g["prototype"])} | {md(g["upload"])} | {md(g["difference"])} | '
                  f'{md(g["cause"])} | {md(g["class"])} |' for g in gaps]
    else:
        lines.append('None over the thresholds.')
    lines.append('')
    summary['gaps'] = len(gaps)
    summary['toClassify'] = sum(1 for g in gaps if g['class'] == 'to classify')
    if walk is not None:
        failing = [w for w in walk if not w.get('passed')]
        lines += ['### Walk checks (A-6)', '', f'{len(walk) - len(failing)} of {len(walk)} probes pass.', '']
        if failing:
            rows = [{'floor': w.get('floor'), 'metric': f'walk: {w.get("kind")}', 'id': w.get('id'), 'detail': w.get('detail', '')}
                    for w in failing]
            classify(rows, classes)
            lines += ['| Floor | Probe | Id | Detail | Cause | Class |', '|---|---|---|---|---|---|']
            lines += [f'| {md(r["floor"])} | {md(r["metric"])} | {md(r["id"])} | {md(r["detail"])} | {md(r["cause"])} | {md(r["class"])} |'
                      for r in rows]
            lines.append('')
        summary['walk'] = {'probes': len(walk), 'failing': len(failing)}
    return '\n'.join(lines) + '\n', summary


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog='gap-report.py', description=__doc__.splitlines()[0])
    ap.add_argument('prototype', type=Path, help="the prototype version's folder (or its model.json)")
    ap.add_argument('upload', type=Path, help="the uploaded version's folder (or its model.json)")
    ap.add_argument('--title', help='the section title (default: the upload folder against the prototype folder)')
    ap.add_argument('--classes', type=Path, help='known causes and classes (JSON list)')
    ap.add_argument('--walk', type=Path, help="the uploaded version's walk checks (JSON)")
    ap.add_argument('--out', type=Path, help='write the section here instead of printing it')
    ap.add_argument('--json', action='store_true', help='also print a one-line JSON summary on stderr')
    a = ap.parse_args(argv)
    try:
        proto, up = load_model(a.prototype), load_model(a.upload)
        classes = json.loads(a.classes.read_text(encoding='utf-8')) if a.classes else []
        walk = None
        if a.walk:
            w = json.loads(a.walk.read_text(encoding='utf-8'))
            walk = w['probes'] if isinstance(w, dict) else w
        title = a.title or f'{a.upload.name or a.upload} against {a.prototype.name or a.prototype}'
        text, summary = report(proto, up, title=title, classes=classes, walk=walk)
    except (OSError, ValueError, KeyError) as exc:
        print(f'gap-report: {exc}', file=sys.stderr)
        return 2
    if a.out:
        a.out.write_text(text, encoding='utf-8')
    else:
        sys.stdout.write(text)
    if a.json:
        print(json.dumps(summary), file=sys.stderr)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
