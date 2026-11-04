"""Prototype of the READ step for the layer-mapping screen (scratch, not product code).

Usage: python read_drawing.py <plan.dxf> <out.json> [--preview out.png]
One pass over the DXF (ezdxf recover; blocks unpacked like detector/tools/prims.py, effective layer = the INSERT's
layer for items on layer 0 inside a block) -> drawing.json:
  file: dxf version, $INSUNITS, extents, audit counts, counts
  units: declared, door-swing test, dimension test, verdict
  layers[]: name, state (on/off/frozen/locked), linetype, colour, counts by type (top level and inside blocks),
            n, extents (robust 1-99 % box) in metres, total line length, closed shapes, hatches (solid / pattern),
            arcs of door size, parallel-line spacings (wall-like 4-45 cm, glass-like 0.5-7 cm), texts, inserts (top block names),
            a few signature features for suggesting a role
  blocks[]: name, inserts (count, layers), size (m), layers inside, attrib tags, mirrored count, nesting
  texts[]: layer, x, y, height, text (plain, untrusted), from (TEXT / MTEXT / ATTRIB tag)
  levelTags[], gridLabels[]
"""
import collections, json, math, re, sys, time
from ezdxf import recover, path as ezpath

U_NAMES = {0: 'unitless', 1: 'in', 2: 'ft', 4: 'mm', 5: 'cm', 6: 'm', 14: 'dm'}
U_TO_M = {'in': 0.0254, 'ft': 0.3048, 'mm': 0.001, 'cm': 0.01, 'm': 1.0, 'dm': 0.1}
LEVEL_RE = re.compile(r'^\s*(?:(?:F\.?F\.?L|S\.?S\.?L|T\.?O\.?S|FL|EL|LEVEL|LVL|LV)\.?\s*[:=]?\s*)?([+\-±]?\s*\d{1,3}(?:[.,]\d{2,3}))\s*(?:M|m)?\s*$')
GRID_RE = re.compile(r'^[A-Z]{1,2}[\'′]?$|^\d{1,2}[\'′]?$|^[A-Z]{1,2}[.\-]?\d{1,2}$|^\d{1,2}[.\-/]\d{1,2}$')
CELLS = (0.001, 0.01, 0.1, 1.0, 10.0, 100.0)
SKIP = ('VIEWPORT', 'OLE2FRAME', '3DSOLID', 'REGION', 'BODY', 'MESH')


def main():
    src, dst = sys.argv[1], sys.argv[2]
    png = sys.argv[sys.argv.index('--preview') + 1] if '--preview' in sys.argv else None
    t0 = time.time()
    doc, aud = recover.readfile(src)
    t_read = time.time() - t0
    ins_units = doc.header.get('$INSUNITS', 0)
    lay_tab = {}
    for l in doc.layers:
        lay_tab[l.dxf.name] = {'off': l.is_off(), 'frozen': l.is_frozen(), 'locked': l.is_locked(),
                               'linetype': l.dxf.get('linetype', 'Continuous'), 'color': l.dxf.get('color', 7),
                               'plot': bool(l.dxf.get('plot', 1))}
    L = collections.defaultdict(lambda: {'top': collections.Counter(), 'inBlocks': collections.Counter(), 'pts': [], 'len': 0.0,
                                          'closed': 0, 'hatchSolid': 0, 'hatchPattern': collections.Counter(), 'arcR': [],
                                          'texts': 0, 'blocks': collections.Counter(), 'segs': [], 'lt': collections.Counter()})
    blocks = collections.defaultdict(lambda: {'inserts': 0, 'layers': collections.Counter(), 'mirrored': 0, 'depths': collections.Counter(),
                                               'tags': set()})
    texts, dims, preview = [], [], []
    quarter, ends = [], collections.defaultdict(list)

    def add_pts(rec, pts):
        if len(rec['pts']) < 200000: rec['pts'].extend(pts[:: max(1, len(pts) // 8)])

    def walk(e, inh=None, depth=0):
        lay = e.dxf.get('layer', '0')
        if lay == '0' and inh: lay = inh
        t = e.dxftype()
        rec = L[lay]
        (rec['top'] if depth == 0 else rec['inBlocks'])[t] += 1
        if t == 'INSERT':
            nm = e.dxf.get('name', '')
            b = blocks[nm]; b['inserts'] += 1; b['layers'][lay] += 1; b['depths'][depth] += 1
            rec['blocks'][nm] += 1
            try:
                m = e.matrix44(); ux, uy = m.transform_direction((1, 0, 0)), m.transform_direction((0, 1, 0))
                if ux.x * uy.y - ux.y * uy.x < 0: b['mirrored'] += 1
                p = e.dxf.insert; add_pts(rec, [(p.x, p.y)])
            except Exception:
                pass
            for a in e.attribs:
                b['tags'].add(a.dxf.get('tag', ''))
                p = a.dxf.insert
                texts.append({'layer': a.dxf.get('layer', lay), 'x': p.x, 'y': p.y, 'h': a.dxf.get('height', 0), 'text': a.dxf.get('text', ''),
                              'from': 'ATTRIB', 'tag': a.dxf.get('tag', ''), 'block': nm, 'depth': depth})
            if depth < 8:
                try:
                    for v in e.virtual_entities(): walk(v, lay, depth + 1)
                except Exception:
                    pass
            return
        if t == 'DIMENSION':
            try:
                dims.append({'layer': lay, 'type': e.dimtype, 'actual': e.dxf.get('actual_measurement', None), 'text': e.dxf.get('text', ''),
                             'p13': tuple(e.dxf.get('defpoint2', (0, 0, 0)))[:2], 'p14': tuple(e.dxf.get('defpoint3', (0, 0, 0)))[:2],
                             'angle': e.dxf.get('angle', 0.0), 'style': e.dxf.get('dimstyle', '')})
            except Exception:
                pass
            return
        if t in ('TEXT', 'MTEXT'):
            try:
                p = e.dxf.insert
                s = e.plain_text() if t == 'MTEXT' else e.dxf.get('text', '')
                h = e.dxf.get('char_height' if t == 'MTEXT' else 'height', 0)
                texts.append({'layer': lay, 'x': p.x, 'y': p.y, 'h': h, 'text': s, 'from': t, 'depth': depth})
                rec['texts'] += 1; add_pts(rec, [(p.x, p.y)])
            except Exception:
                pass
            return
        if t == 'HATCH':
            if e.dxf.get('solid_fill', 0): rec['hatchSolid'] += 1
            else: rec['hatchPattern'][e.dxf.get('pattern_name', '')] += 1
            try:
                for bp in ezpath.from_hatch(e):
                    add_pts(rec, [(v.x, v.y) for v in bp.flattening(distance=10)])
            except Exception:
                pass
            return
        if t in SKIP or t in ('ATTDEF', 'POINT'): return
        rec['lt'][e.dxf.get('linetype', 'BYLAYER')] += 1
        if t == 'ARC':
            sweep = (e.dxf.end_angle - e.dxf.start_angle) % 360
            rec['arcR'].append((e.dxf.radius, sweep))
            if 80 <= sweep <= 100:
                c = e.dxf.center; a0 = math.radians(e.dxf.start_angle); a1 = math.radians(e.dxf.end_angle); r = e.dxf.radius
                quarter.append(((c.x, c.y), r, [(c.x + r * math.cos(a), c.y + r * math.sin(a)) for a in (a0, a1)]))
        try:
            pts = [(v.x, v.y) for v in ezpath.make_path(e).flattening(distance=10)]
        except Exception:
            return
        if not pts: return
        add_pts(rec, pts)
        rec['len'] += sum(math.dist(a, b) for a, b in zip(pts, pts[1:]))
        closed = (t == 'CIRCLE') or (t == 'LWPOLYLINE' and e.closed) or (t == 'POLYLINE' and e.is_closed)
        if closed: rec['closed'] += 1
        if t == 'LINE' and len(rec['segs']) < 20000: rec['segs'].append((pts[0], pts[-1]))
        if t in ('LINE', 'LWPOLYLINE', 'POLYLINE'):
            for a, b in zip(pts, pts[1:]):
                for cs in CELLS:
                    for q in (a, b): ends[(cs, math.floor(q[0] / cs), math.floor(q[1] / cs))].append((a, b))
        if len(preview) < 400000: preview.append((lay, pts))

    for e in doc.modelspace(): walk(e)
    t_walk = time.time() - t0 - t_read

    # ---- units: declared, door swings, dimensions
    declared = U_NAMES.get(ins_units, f'code {ins_units}')
    def has_leaf(c, r, tips):
        # a straight leaf from the hinge (the arc centre) to one end of the arc, as long as the radius (within 5 %)
        cs = min(CELLS, key=lambda v: abs(math.log10(v) - math.log10(max(1e-9, 0.08 * r))))
        cx, cy = math.floor(c[0] / cs), math.floor(c[1] / cs)
        for i in (-1, 0, 1):
            for j in (-1, 0, 1):
                for a, b in ends.get((cs, cx + i, cy + j), ()):
                    for h, t in ((a, b), (b, a)):
                        if math.dist(h, c) <= 0.08 * r and any(math.dist(t, q) <= 0.08 * r for q in tips) and abs(math.dist(h, t) - r) <= 0.1 * r: return True
        return False
    door_r = [r for c, r, tips in quarter if has_leaf(c, r, tips)]
    votes = {u: sum(1 for r in door_r if 0.6 <= r * kk <= 1.25) for u, kk in U_TO_M.items()}   # door-leaf-sized quarter arcs per unit
    dim_m = sorted(d['actual'] for d in dims if d['actual'])
    med_dim = dim_m[len(dim_m) // 2] if dim_m else None
    plaus = {u: (med_dim is None or 0.3 <= med_dim * kk <= 40) for u, kk in U_TO_M.items()}
    ranked = sorted(U_TO_M, key=lambda u: (-plaus[u], -votes[u]))
    guess = ranked[0] if votes[ranked[0]] >= 3 else None
    med_r = None
    dim_ratio = []
    for d in dims:
        if d['actual'] and d['type'] in (0, 1):
            a = math.radians(d['angle']) if d['type'] == 0 else math.atan2(d['p14'][1] - d['p13'][1], d['p14'][0] - d['p13'][0])
            # the measured points of a linear dimension are 13 / 14; 'actual' is in drawing units x DIMLFAC
            pass
        txt = (d['text'] or '').strip()
        if d['actual'] and re.fullmatch(r'\d+(?:[.,]\d+)?', txt): dim_ratio.append(float(txt.replace(',', '.')) / d['actual'])
    units = {'declared': declared, 'quarterArcs': len(door_r), 'doorArcVotes': votes, 'dimsPlausible': plaus, 'geometrySays': guess,
             'dimensions': len(dims), 'dimensionActualMedian': sorted(d['actual'] for d in dims if d['actual'])[len(dims) // 2] if dims else None,
             'dimTextOverrides': len(dim_ratio)}
    units['verdict'] = 'agree' if guess in (None, declared) else f'check: the file says {declared}, door swings say {guess}'
    k = U_TO_M.get(guess or declared, 0.001)

    # ---- layers
    def robust_box(pts):
        if not pts: return None
        xs = sorted(p[0] for p in pts); ys = sorted(p[1] for p in pts)
        lo, hi = int(len(xs) * 0.01), max(0, int(len(xs) * 0.99) - 1)
        return [round(xs[lo] * k, 2), round(ys[lo] * k, 2), round(xs[hi] * k, 2), round(ys[hi] * k, 2)]

    def spacings(segs):
        """Parallel-line spacing histogram (m): pairs of near-parallel, overlapping LINEs 5 mm - 60 cm apart."""
        out = collections.Counter()
        S = [(a, b) for a, b in segs if math.dist(a, b) * k > 0.2][:3000]
        for i in range(len(S)):
            (a, b) = S[i]; ux, uy = (b[0] - a[0]), (b[1] - a[1]); n = math.hypot(ux, uy); ux, uy = ux / n, uy / n
            for j in range(i + 1, min(len(S), i + 60)):
                c, d = S[j]; vx, vy = d[0] - c[0], d[1] - c[1]; m = math.hypot(vx, vy)
                if abs(ux * vy - uy * vx) / m > 0.02: continue
                dist = abs((c[0] - a[0]) * -uy + (c[1] - a[1]) * ux) * k
                if 0.005 <= dist <= 0.6:
                    out['glass-like 0.5-7 cm' if dist < 0.07 else 'wall-like 7-45 cm' if dist <= 0.45 else 'wide 45-60 cm'] += 1
        return dict(out)

    layers = []
    for name in sorted(set(L) | set(lay_tab)):
        rec = L.get(name)
        st = lay_tab.get(name, {})
        if rec is None:
            layers.append({'name': name, **st, 'n': 0}); continue
        n = sum(rec['top'].values()) + sum(rec['inBlocks'].values())
        door_arcs = sum(1 for r, sw in rec['arcR'] if 0.28 <= r * k <= 2.0 and 20 <= sw <= 125)
        layers.append({'name': name, **st, 'n': n, 'top': dict(rec['top']), 'inBlocks': dict(rec['inBlocks']),
                       'extentsM': robust_box(rec['pts']), 'lengthM': round(rec['len'] * k, 1), 'closed': rec['closed'],
                       'hatchSolid': rec['hatchSolid'], 'hatchPattern': dict(rec['hatchPattern'].most_common(4)),
                       'doorSizeArcs': door_arcs, 'texts': rec['texts'], 'topBlocks': dict(rec['blocks'].most_common(5)),
                       'linetypes': dict(rec['lt'].most_common(3)), 'parallel': spacings(rec['segs'])})

    # ---- texts, level tags, grid labels
    for t in texts: t['x'] = round(t['x'] * k, 3); t['y'] = round(t['y'] * k, 3); t['h'] = round((t['h'] or 0) * k, 3)
    level_tags = [t for t in texts if LEVEL_RE.match(t['text'] or '') or t.get('tag', '').upper() in ('LEVEL', 'ELEV', 'EL', 'LV', 'FFL')]
    grid = [t for t in texts if GRID_RE.match((t['text'] or '').strip()) and ('GRID' in t['layer'].upper() or 'AXIS' in t['layer'].upper()
                                                                           or 'GRID' in t.get('block', '').upper())]
    out = {'file': {'dxfversion': doc.dxfversion, 'insunits': ins_units, 'extmin': list(doc.header.get('$EXTMIN', (0, 0, 0)))[:2],
                    'extmax': list(doc.header.get('$EXTMAX', (0, 0, 0)))[:2], 'auditFixes': len(aud.fixes), 'auditErrors': len(aud.errors),
                    'readS': round(t_read, 2), 'walkS': round(t_walk, 2)},
           'units': units, 'layers': layers,
           'blocks': sorted([{'name': n, 'inserts': b['inserts'], 'layers': dict(b['layers'].most_common(4)), 'mirrored': b['mirrored'],
                              'depths': dict(b['depths']), 'tags': sorted(b['tags'])[:8]} for n, b in blocks.items()], key=lambda b: -b['inserts']),
           'texts': len(texts), 'textSample': [t['text'][:40] for t in texts[:30]],
           'levelTags': level_tags[:200], 'gridLabels': grid[:400], 'dimensions': len(dims)}
    with open(dst, 'w', encoding='utf-8') as f: json.dump(out, f, ensure_ascii=False, default=list)
    if png:
        import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
        from matplotlib.collections import LineCollection
        fig, ax = plt.subplots(figsize=(10, 10), dpi=100)
        ax.add_collection(LineCollection([[(x * k, y * k) for x, y in p] for _, p in preview], linewidths=0.2, colors='#555'))
        ax.autoscale(); ax.set_aspect('equal'); ax.axis('off'); fig.savefig(png, bbox_inches='tight'); plt.close(fig)
    print(f'read {t_read:.1f} s, walk {t_walk:.1f} s, total {time.time() - t0:.1f} s; {len(layers)} layers, {len(blocks)} blocks, '
          f'{len(texts)} texts, {len(level_tags)} level tags, {len(grid)} grid labels, {len(dims)} dimensions; units {units}')


if __name__ == '__main__':
    main()
