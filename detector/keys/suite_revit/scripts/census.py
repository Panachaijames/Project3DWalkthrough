"""Layer census of the suite_revit DXF, written for description.md (step 2 of the held-out run).

Reads the DXF directly with ezdxf (not the detector) and prints, per layer:
  - entity counts at the top level of model space, and inside block definitions that model space uses (counted once
    per definition and once per expanded insert),
  - the extent of the layer's geometry in drawing metres (DXF units / 1000; the geometry is in millimetres),
  - line-length and arc-radius statistics, closed-polyline sizes, an example coordinate.
Also prints every block definition used by model space with its nesting, the layers of its contents and its inserts
(layer, insert point in metres, rotation, scale signs).

Usage: python -B census.py <plan.dxf>
"""
import collections, math, statistics, sys
from ezdxf import recover, bbox

doc, aud = recover.readfile(sys.argv[1])
msp = doc.modelspace()
M = 1000.0


def ent_layer(e, inh=None):
    lay = e.dxf.get('layer', '0')
    return inh if (lay == '0' and inh) else lay


def length(e):
    t = e.dxftype()
    if t == 'LINE':
        s, en = e.dxf.start, e.dxf.end
        return math.hypot(en.x - s.x, en.y - s.y)
    return None


# ---- top-level census -------------------------------------------------------------------------------------------
top = collections.defaultdict(collections.Counter)
for e in msp:
    top[e.dxf.get('layer', '0')][e.dxftype()] += 1

# ---- expanded census (virtual entities of inserts, recursively, with layer-0 inheritance) ------------------------
expd = collections.defaultdict(collections.Counter)          # layer -> (type) counts inside inserts (expanded)
blk_of_layer = collections.defaultdict(collections.Counter)  # layer -> block names holding it
lens = collections.defaultdict(list)                         # layer -> line lengths (m), all depths
radii = collections.defaultdict(list)                        # layer -> arc radii (m), all depths
arcs_span = collections.defaultdict(list)                    # layer -> arc sweep (deg)
example = {}
extent = {}


def note_geom(e, lay):
    t = e.dxftype()
    try:
        if t == 'LINE':
            s, en = e.dxf.start, e.dxf.end
            lens[lay].append(math.hypot(en.x - s.x, en.y - s.y) / M)
            pts = [(s.x, s.y), (en.x, en.y)]
        elif t == 'ARC':
            c = e.dxf.center
            radii[lay].append(e.dxf.radius / M)
            sw = (e.dxf.end_angle - e.dxf.start_angle) % 360
            arcs_span[lay].append(sw)
            pts = [(c.x, c.y)]
        elif t == 'CIRCLE':
            c = e.dxf.center
            pts = [(c.x, c.y)]
        elif t in ('LWPOLYLINE',):
            pts = [(p[0], p[1]) for p in e.get_points('xy')]
        elif t == 'INSERT':
            p = e.dxf.insert
            pts = [(p.x, p.y)]
        elif t in ('MTEXT', 'TEXT'):
            p = e.dxf.insert
            pts = [(p.x, p.y)]
        else:
            b = bbox.extents([e], fast=True)
            if not b.has_data:
                return
            pts = [(b.extmin.x, b.extmin.y), (b.extmax.x, b.extmax.y)]
    except Exception:
        return
    if not pts:
        return
    if lay not in example:
        example[lay] = (t, round(pts[0][0] / M, 3), round(pts[0][1] / M, 3))
    xs = [p[0] for p in pts]; ys = [p[1] for p in pts]
    if lay in extent:
        a = extent[lay]
        extent[lay] = (min(a[0], min(xs)), min(a[1], min(ys)), max(a[2], max(xs)), max(a[3], max(ys)))
    else:
        extent[lay] = (min(xs), min(ys), max(xs), max(ys))


def walk(e, inh=None, depth=0, path=()):
    lay = ent_layer(e, inh)
    t = e.dxftype()
    if depth > 0:
        expd[lay][t] += 1
        blk_of_layer[lay][path[0]] += 1
    note_geom(e, lay)
    if t == 'INSERT' and depth < 8:
        try:
            for v in e.virtual_entities():
                walk(v, lay, depth + 1, path + (e.dxf.name,))
        except Exception as ex:
            print('  ! could not expand', e.dxf.name, ex)


for e in msp:
    walk(e)

print('INSUNITS', doc.header.get('$INSUNITS'), '| MEASUREMENT', doc.header.get('$MEASUREMENT'), '| LUNITS', doc.header.get('$LUNITS'),
      '| DIMSCALE', doc.header.get('$DIMSCALE'), '| LTSCALE', doc.header.get('$LTSCALE'))
b = bbox.extents(msp, fast=True)
print('model-space extent (m): x %.3f .. %.3f  y %.3f .. %.3f' % (b.extmin.x / M, b.extmax.x / M, b.extmin.y / M, b.extmax.y / M))
print()
print('LAYER TABLE (name, colour, linetype, on/frozen):')
for l in doc.layers:
    print('  %-16s colour %4s  lt %-22s on=%s frozen=%s' % (l.dxf.name, l.dxf.get('color'), l.dxf.get('linetype'), l.is_on(), l.is_frozen()))
print()
for lay in sorted(set(top) | set(expd), key=lambda k: -(sum(top[k].values()) + sum(expd[k].values()))):
    T, X = top[lay], expd[lay]
    print('=== %s  top %d  in inserts %d' % (lay, sum(T.values()), sum(X.values())))
    print('   top:', dict(T.most_common()))
    if X:
        print('   in inserts:', dict(X.most_common()), '| blocks:', [(k[:60], n) for k, n in blk_of_layer[lay].most_common(6)])
    if lay in extent:
        a = extent[lay]
        print('   extent m: x %.2f..%.2f  y %.2f..%.2f   example %s' % (a[0] / M, a[2] / M, a[1] / M, a[3] / M, example.get(lay)))
    L = lens.get(lay)
    if L:
        qs = statistics.quantiles(L, n=10) if len(L) > 10 else sorted(L)
        print('   lines %d: min %.3f  deciles %s  max %.3f m' % (len(L), min(L), [round(q, 3) for q in qs], max(L)))
        lc = collections.Counter(round(v, 2) for v in L)
        print('   most common lengths (m):', lc.most_common(10))
    R = radii.get(lay)
    if R:
        rc = collections.Counter(round(v, 3) for v in R)
        sc = collections.Counter(round(v) for v in arcs_span[lay])
        print('   arcs %d: radii (m) %s | sweeps (deg) %s' % (len(R), rc.most_common(10), sc.most_common(6)))
print()
print('BLOCK DEFINITIONS used by model space (direct inserts), with contents:')
used = collections.Counter(e.dxf.name for e in msp.query('INSERT'))
seen = set()


def show_block(name, ind=1):
    if name in seen:
        return
    seen.add(name)
    blk = doc.blocks.get(name)
    if blk is None:
        print('  ' * ind, name, 'MISSING')
        return
    c = collections.Counter((e.dxf.get('layer', '0'), e.dxftype()) for e in blk)
    print('  ' * ind + '- %s  base %s : %s' % (name, tuple(round(v, 1) for v in blk.block.dxf.base_point)[:2], dict(c.most_common(8))))
    for e in blk.query('INSERT'):
        show_block(e.dxf.name, ind + 1)


for nm, n in used.most_common():
    show_block(nm)
print()
print('INSERTS in model space (layer, name, insert m, rotation, xscale, yscale):')
for e in msp.query('INSERT'):
    p = e.dxf.insert
    print('  %-12s %-90s (%.3f, %.3f) rot %.1f  sx %.3f sy %.3f' % (e.dxf.layer, e.dxf.name[:90], p.x / M, p.y / M, e.dxf.get('rotation', 0),
                                                                   e.dxf.get('xscale', 1), e.dxf.get('yscale', 1)))
