"""Layer census of a plan DXF for writing a layer-role mapping (held-out run on the presidential suite Revit export).

Reads the DXF only (never the detector's output). Walks model space the way tools/prims.py does (blocks unpacked to
depth 8, an entity on layer 0 inside a block takes the INSERT's layer) and, per effective layer, counts entity types at
the top level (depth 0) and inside blocks (depth > 0), with sizes in DXF units: line lengths, arc radii and sweeps,
closed-outline widths, hatch kinds, linetypes and the blocks inserted on the layer. Also lists the layer table and the raw
layers used inside block definitions.

Usage: python -B layer_census.py <plan.dxf> [out.txt]
"""
import collections, math, sys
from ezdxf import recover, path as ezpath
from ezdxf.math import area as poly_area


def q(vals, ps=(0, 10, 50, 90, 100)):
    if not vals: return '-'
    v = sorted(vals)
    return ' / '.join(f'{v[min(len(v) - 1, int(round(p / 100 * (len(v) - 1))))]:.0f}' for p in ps)


def main():
    doc, aud = recover.readfile(sys.argv[1])
    out = open(sys.argv[2], 'w', encoding='utf-8') if len(sys.argv) > 2 else sys.stdout
    P = lambda *a: print(*a, file=out)
    h = doc.header
    P(f'DXF {doc.dxfversion}  INSUNITS {h.get("$INSUNITS")}  MEASUREMENT {h.get("$MEASUREMENT")}  LUNITS {h.get("$LUNITS")}  '
      f'EXTMIN {tuple(round(v) for v in h.get("$EXTMIN", (0, 0, 0)))}  EXTMAX {tuple(round(v) for v in h.get("$EXTMAX", (0, 0, 0)))}')

    S = collections.defaultdict(lambda: {'types0': collections.Counter(), 'typesB': collections.Counter(),
                                         'line': [], 'arc_r': [], 'arc_sw': [], 'circ_r': [], 'pl_open': 0,
                                         'closed_w': [], 'closed_big': [], 'hatch': collections.Counter(), 'hatch_area': [],
                                         'lt': collections.Counter(), 'blocks': collections.Counter(), 'raw': collections.Counter(),
                                         'ell': 0, 'spline': 0, 'xs': [], 'ys': []})

    def note_pts(s, pts):
        if pts:
            s['xs'] += [p[0] for p in pts[:: max(1, len(pts) // 4)]]
            s['ys'] += [p[1] for p in pts[:: max(1, len(pts) // 4)]]

    def walk(e, inh=None, depth=0):
        raw = e.dxf.get('layer', '0')
        lay = inh if (raw == '0' and inh) else raw
        t = e.dxftype()
        s = S[lay]
        (s['types0'] if depth == 0 else s['typesB'])[t] += 1
        s['raw'][raw] += 1
        s['lt'][e.dxf.get('linetype', 'BYLAYER')] += 1
        if t == 'INSERT':
            s['blocks'][e.dxf.get('name', '')] += 1
            if depth < 8:
                try:
                    for v in e.virtual_entities(): walk(v, lay, depth + 1)
                except Exception:
                    pass
            return
        try:
            if t == 'LINE':
                a, b = e.dxf.start, e.dxf.end
                s['line'].append(math.hypot(b.x - a.x, b.y - a.y)); note_pts(s, [(a.x, a.y), (b.x, b.y)])
            elif t == 'ARC':
                sw = (e.dxf.end_angle - e.dxf.start_angle) % 360
                s['arc_r'].append(e.dxf.radius); s['arc_sw'].append(sw); note_pts(s, [(e.dxf.center.x, e.dxf.center.y)])
            elif t == 'CIRCLE':
                s['circ_r'].append(e.dxf.radius); note_pts(s, [(e.dxf.center.x, e.dxf.center.y)])
            elif t in ('LWPOLYLINE', 'POLYLINE'):
                pts = [(v.x, v.y) for v in ezpath.make_path(e).flattening(distance=10)]
                closed = bool(e.closed) if t == 'LWPOLYLINE' else e.is_closed
                note_pts(s, pts)
                if closed and len(pts) >= 3:
                    A = abs(poly_area([*pts]))
                    L = sum(math.dist(p, q2) for p, q2 in zip(pts, pts[1:] + pts[:1]))
                    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
                    w = 2 * A / L if L else 0
                    s['closed_w'].append(w)
                    s['closed_big'].append(max(max(xs) - min(xs), max(ys) - min(ys)))
                else:
                    s['pl_open'] += 1
            elif t == 'HATCH':
                s['hatch'][('solid' if e.dxf.get('solid_fill', 0) else e.dxf.get('pattern_name', '?'))] += 1
                try:
                    A = 0
                    for bp in ezpath.from_hatch(e):
                        pts = [(v.x, v.y) for v in bp.flattening(distance=10)]
                        if len(pts) >= 3: A += abs(poly_area(pts))
                        note_pts(s, pts)
                    s['hatch_area'].append(A)
                except Exception:
                    pass
            elif t == 'ELLIPSE':
                s['ell'] += 1
            elif t == 'SPLINE':
                s['spline'] += 1
        except Exception:
            pass

    for e in doc.modelspace(): walk(e)

    P('\n== layer table (name | colour | linetype | on/off frozen) and items per effective layer (top level / inside blocks)')
    used = set(S)
    for l in sorted(doc.layers, key=lambda l: l.dxf.name.upper()):
        n = l.dxf.name
        s = S.get(n)
        n0 = sum(s['types0'].values()) if s else 0
        nb = sum(s['typesB'].values()) if s else 0
        P(f'  {n:42} col {l.dxf.get("color", 7):4} lt {l.dxf.get("linetype", "?"):14} {"OFF" if l.is_off() else "on ":3} '
          f'{"FROZEN" if l.is_frozen() else "      "} top {n0:6}  in blocks {nb:6}')
    for n in sorted(used - {l.dxf.name for l in doc.layers}):
        P(f'  {n:42} (not in the layer table)')

    P('\n== per effective layer (sizes in DXF units)')
    for lay, s in sorted(S.items(), key=lambda kv: -(sum(kv[1]['types0'].values()) + sum(kv[1]['typesB'].values()))):
        P(f'\n-- {lay}')
        P(f'   top level:     {dict(s["types0"].most_common())}')
        P(f'   inside blocks: {dict(s["typesB"].most_common())}')
        if len(s['raw']) > 1 or lay not in s['raw']: P(f'   raw layers of these items: {dict(s["raw"].most_common(6))}')
        P(f'   linetypes: {dict(s["lt"].most_common(5))}')
        if s['line']: P(f'   LINE lengths n={len(s["line"])} min/p10/med/p90/max {q(s["line"])}')
        if s['arc_r']:
            r = s['arc_r']; sw = s['arc_sw']
            door_like = sum(1 for a, b in zip(r, sw) if 280 <= a <= 2000 and 20 <= b <= 125)
            P(f'   ARC radius n={len(r)} min/p10/med/p90/max {q(r)}; sweep {q(sw)}; r 280-2000 & sweep 20-125 deg: {door_like}')
            hist = collections.Counter(int(a // 100) * 100 for a, b in zip(r, sw) if 20 <= b <= 125 and a >= 280)
            if hist: P(f'   door-like arc radii by 100s: {dict(sorted(hist.items()))}')
        if s['circ_r']: P(f'   CIRCLE radius n={len(s["circ_r"])} {q(s["circ_r"])}')
        if s['closed_w']: P(f'   closed outlines n={len(s["closed_w"])} mean width {q(s["closed_w"])}; long side {q(s["closed_big"])}')
        if s['pl_open']: P(f'   open polylines {s["pl_open"]}')
        if s['hatch']: P(f'   HATCH {dict(s["hatch"].most_common(6))}; area (units^2) {q(s["hatch_area"])}')
        if s['ell'] or s['spline']: P(f'   ellipses {s["ell"]}, splines {s["spline"]}')
        if s['blocks']: P(f'   blocks: {dict(s["blocks"].most_common(8))}' + (f' ... ({len(s["blocks"])} names)' if len(s['blocks']) > 8 else ''))
        if s['xs']: P(f'   extent x {min(s["xs"]):.0f}..{max(s["xs"]):.0f}  y {min(s["ys"]):.0f}..{max(s["ys"]):.0f}')

    P('\n== raw layers used inside block definitions (entity counts per block definition, not per insert)')
    raw = collections.Counter()
    for b in doc.blocks:
        if b.name.startswith('*') and b.name.upper().startswith(('*MODEL', '*PAPER')): continue
        for e in b: raw[e.dxf.get('layer', '0')] += 1
    for k, v in raw.most_common(): P(f'  {k:42} {v}')
    P(f'\naudit errors {len(aud.errors)} fixes {len(aud.fixes)}')
    out.flush()
    if out is not sys.stdout: out.close()


if __name__ == '__main__':
    main()
