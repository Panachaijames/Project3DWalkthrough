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

The rooms milestone (docs/rooms/ACCEPTANCE.md RA-3 - RA-6; R3). When either model is a BuiltModel v2 (it has
`stairways`), each floor's table gains the rows of RA-3 - RA-5: rooms closed, rooms named, names in no room, rooms with
several names (RA-3); plate0, terraces, unfloored areas and the closings from the build report (RA-4); the holes by what,
with their areas (RA-5); the stairs you can climb and those kept as lines. The build report is read from the version
folder (`source/build-report.json`, or `report.json` beside the model of a run's out folder) or --report / --proto-report.
Then a section "Storeys and stairs" per pair of floors next to each other: the storey, and the window of storeys that
fits every stair read between them (risers x 0.14 - 0.21 m, R-7.6; the climbable ones from the model, the ones kept as
lines from the report): a storey outside its window (the tower's, 4.00 m against 2.80 - 3.78 m) is a gap row.
--probes <fixtures/rooms/keys/probes.json> --drawing <house|suite|tower|suite-revit> (RA-6): for each probe of that
drawing, whether the upload's plate holds a point 0.4 - 0.9 m in front of it on each side that had no floor; a probe
that still has none is a gap row. With two v1 models and none of these options the section is what it was.
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
#: a riser that a stair you can climb may have (m; docs/rooms/DESIGN.md R-7.6)
RISER = (0.14, 0.21)
#: RA-6: the plate must hold a point this far in front of a probe (m)
PROBE_DEPTHS = (0.4, 0.5, 0.6, 0.7, 0.8, 0.9)


def load_model(d: Path) -> dict:
    p = d / 'model.json' if d.is_dir() else d
    return json.loads(p.read_bytes().decode('utf-8'))


def load_report(d: Path, given: Path | None = None) -> dict | None:
    """The build report of a version folder (source/build-report.json) or of a run's out folder (report.json beside the
    model), or `given`; None when there is none."""
    folder = d if d.is_dir() else d.parent
    for p in ([given] if given else []) + [folder / 'source' / 'build-report.json', folder / 'report.json']:
        if p is not None and p.is_file():
            return json.loads(p.read_bytes().decode('utf-8'))
    return None


def is_v2(m: dict) -> bool:
    return 'stairways' in m


def rooms_metrics(m: dict, rep: dict | None, floor: str) -> dict:
    """RA-3 - RA-5 of one floor: from the model, and from its build report when there is one."""
    spaces = [s for s in m.get('spaces') or [] if s['floor'] == floor]
    names = [r for r in m['rooms'] if r['floor'] == floor]
    fr = ((rep or {}).get('floors') or {}).get(floor) or {}
    slab = fr.get('slab') or {}
    holes: dict[str, list[float]] = {}
    for v in (m.get('voids') or {}).get(floor) or []:
        holes.setdefault(str(v.get('what')), []).append(float(v.get('area') or 0.0))
    unf = slab.get('unfloored') or []
    lines_rows = [r for r in fr.get('stairways') or [] if r.get('state') == 'lines']
    return {
        'rooms closed': len(spaces),
        'rooms named': sum(1 for s in spaces if s.get('name')),
        'names in no room': sum(1 for r in names if not r.get('space')) if is_v2(m) else '-',
        'rooms with several names': sum(1 for s in spaces if len(s.get('names') or []) > 1),
        'enclosed shapes left out': (fr.get('rooms') or {}).get('shapes', '-'),
        'plate0 (m2)': f'{slab["plate"]:.1f}' if 'plate' in slab else '-',
        'terraces (m2)': f'{slab["terraces"]:.1f}' if 'terraces' in slab else '-',
        'unfloored areas': f'{len(unf)} ({sum(u.get("area") or 0 for u in unf):.1f} m2)' if slab else '-',
        'closings (doorway / bridge / staff)': ' / '.join(str(sum(1 for c in slab.get('closings') or [] if c.get('kind') == k))
                                                          for k in ('doorway', 'bridge', 'staff')) if slab else '-',
        'holes': '; '.join(f'{w} {len(a)} ({sum(a):.2f} m2)' for w, a in sorted(holes.items())) or 'none',
        'stairs you can climb': sum(1 for s in m.get('stairways') or [] if s['from'] == floor),
        'stairs kept as lines': len(lines_rows) if fr.get('stairways') is not None else '-',
    }


def storey_windows(m: dict, rep: dict | None) -> list[dict]:
    """Per pair of floors next to each other (one stack, by level): the storey and the window of storeys that fits
    every stair read between them: the climbable stairways (the model) and the stairs kept as lines whose riser does not
    fit (the report: their risers counted on the two plans). Empty for a model with no stair read."""
    reps = (rep or {}).get('floors') or {}
    stacks: dict[str, list[dict]] = {}
    for f in m['floors']:
        stacks.setdefault(f.get('stack') or 'main', []).append(f)
    out = []
    for fs in stacks.values():
        fs = sorted(fs, key=lambda f: f['level'])
        for lo, hi in zip(fs, fs[1:]):
            stairs = [(s['id'], int(s['risers']), 'climb') for s in m.get('stairways') or []
                      if s['from'] == lo['key'] and s['to'] == hi['key']]
            stairs += [(r['id'], int(r['risers']), 'lines') for r in (reps.get(lo['key']) or {}).get('stairways') or []
                       if r.get('state') == 'lines' and r.get('why') == 'the riser does not fit' and r.get('risers')]
            if not stairs:
                continue
            a = max(n * RISER[0] for _, n, _ in stairs)
            b = min(n * RISER[1] for _, n, _ in stairs)
            storey = round(hi['level'] - lo['level'], 3)
            out.append({'from': lo['key'], 'to': hi['key'], 'storey': storey, 'window': [round(a, 2), round(b, 2)] if a <= b else None,
                        'stairs': [{'id': i, 'risers': n, 'state': st, 'fits': n * RISER[0] - 1e-9 <= storey <= n * RISER[1] + 1e-9}
                                   for i, n, st in stairs]})
    return out


def probe_rows(m: dict, key: dict, drawing: str) -> list[dict]:
    """RA-6: each probe of `drawing` in the answer key (fixtures/rooms/keys/probes.json): does the plate (slabs, sheet m)
    hold a point 0.4 - 0.9 m in front of it, on each side that had no floor?"""
    d = (key.get('drawings') or {}).get(drawing)
    if d is None:
        raise ValueError(f'the probes key has no drawing {drawing!r} (it has {", ".join(key.get("drawings") or {})})')
    from shapely.geometry import Point
    out = []
    for p in d['probes']:
        fl = p['floor'] if any(f['key'] == p['floor'] for f in m['floors']) else None
        plate = union(m, fl, ('slab',), ground_only=False) if fl else Polygon()
        sides = {}
        for s in p['sides']:
            sides[s] = any(plate.contains(Point(p['at'][0] + s * dd * p['n'][0], p['at'][1] + s * dd * p['n'][1])) for dd in PROBE_DEPTHS)
        out.append({'id': p['id9Nov'], 'floor': p['floor'], 'kind': p.get('kind'), 'grade': d.get('grade', 'must'), 'sides': sides,
                    'passed': fl is not None and all(sides.values())})
    return out


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


def _difference(a, b) -> str:
    return f'{b - a:+d}' if isinstance(a, int) and isinstance(b, int) and not isinstance(a, bool) else '-'


def report(proto: dict, up: dict, *, title: str, classes: list[dict], walk: list[dict] | None,
           proto_report: dict | None = None, up_report: dict | None = None,
           probes: tuple[dict, str] | None = None) -> tuple[str, dict]:
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
        rooms_b = None
        if is_v2(proto) or is_v2(up):                  # the rooms milestone: RA-3 - RA-5 (information rows)
            rooms_a, rooms_b = rooms_metrics(proto, proto_report, pk), rooms_metrics(up, up_report, uk)
            rows += [(k, rooms_a[k], rooms_b[k], _difference(rooms_a[k], rooms_b[k])) for k in rooms_b]
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
        if rooms_b is not None:
            summary['floors'][name]['rooms'] = rooms_b
    if is_v2(up):                                      # the stairs against the storeys (the tower's window, R2.md N-13)
        windows = storey_windows(up, up_report)
        lines += ['### Storeys and stairs (upload)', '']
        if windows:
            lines += ['| Floors | Storey (m) | Storeys that fit every stair (m) | Stairs read |', '|---|---|---|---|']
            for w in windows:
                win = f'{w["window"][0]:.2f} - {w["window"][1]:.2f}' if w['window'] else 'none: the stairs disagree'
                st = ', '.join(f'{s["id"]} {s["risers"]} risers ({"climbable" if s["state"] == "climb" else "kept as lines"}'
                               f'{"" if s["fits"] else ", does not fit"})' for s in w['stairs'])
                lines.append(f'| {md(w["from"])} - {md(w["to"])} | {w["storey"]:.2f} | {win} | {md(st)} |')
                if w['window'] is None or not (w['window'][0] - 1e-9 <= w['storey'] <= w['window'][1] + 1e-9):
                    gaps.append({'floor': w['from'], 'metric': 'storey window', 'prototype': '-', 'upload': f'{w["storey"]:.2f}',
                                 'difference': f'outside {win}'})
        else:
            lines.append('No stair was read between two floors.')
        lines.append('')
        summary['storeyWindows'] = windows
    if probes is not None:                             # RA-6: the probes that had no floor at their start
        rows_p = probe_rows(up, probes[0], probes[1])
        lines += [f'### Probes that had no floor on 9 Nov (RA-6, {md(probes[1])})', '',
                  f'{sum(1 for p in rows_p if p["passed"])} of {len(rows_p)} stand on the plate.', '',
                  '| Probe | Floor | Grade | Sides on the plate (0.4 - 0.9 m in front) |', '|---|---|---|---|']
        for p in rows_p:
            sides = ', '.join(f'{s:+d}: {"floor" if ok else "no floor"}' for s, ok in p['sides'].items())
            lines.append(f'| {md(p["id"])} | {md(p["floor"])} | {md(p["grade"])} | {md(sides)} |')
            if not p['passed']:
                gaps.append({'floor': p['floor'], 'metric': f'probe {p["id"]}', 'prototype': '-', 'upload': 'no floor',
                             'difference': sides})
        lines.append('')
        summary['probes'] = {'total': len(rows_p), 'passed': sum(1 for p in rows_p if p['passed']),
                             'failing': [p['id'] for p in rows_p if not p['passed']]}
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
    ap.add_argument('--report', type=Path, help="the upload's build report (default: source/build-report.json or report.json "
                                                'in its folder)')
    ap.add_argument('--proto-report', type=Path, help="the prototype's build report, when it has one")
    ap.add_argument('--probes', type=Path, help='RA-6: fixtures/rooms/keys/probes.json (with --drawing)')
    ap.add_argument('--drawing', help='RA-6: the drawing of the probes key (house, suite, tower, suite-revit)')
    a = ap.parse_args(argv)
    try:
        proto, up = load_model(a.prototype), load_model(a.upload)
        classes = json.loads(a.classes.read_text(encoding='utf-8')) if a.classes else []
        walk = None
        if a.walk:
            w = json.loads(a.walk.read_text(encoding='utf-8'))
            walk = w['probes'] if isinstance(w, dict) else w
        if bool(a.probes) != bool(a.drawing):
            raise ValueError('--probes and --drawing go together')
        probes = (json.loads(a.probes.read_text(encoding='utf-8')), a.drawing) if a.probes else None
        title = a.title or f'{a.upload.name or a.upload} against {a.prototype.name or a.prototype}'
        text, summary = report(proto, up, title=title, classes=classes, walk=walk,
                               proto_report=load_report(a.prototype, a.proto_report), up_report=load_report(a.upload, a.report),
                               probes=probes)
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
