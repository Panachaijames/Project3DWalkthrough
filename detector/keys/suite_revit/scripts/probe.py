"""Probes of the suite_revit DXF used to write description.md (step 2 of the held-out run). Reads the DXF with ezdxf.

Usage: python -B probe.py <plan.dxf>
Prints: entities not in model space (points, wipeouts), unused block definitions, text positions, door-layer arcs and
the arcs on other layers that a swing rule (r 0.28-2 m, sweep 20-125 deg) could take for a door, linetypes in use.
"""
import collections, math, sys
from ezdxf import recover

doc, aud = recover.readfile(sys.argv[1])
msp = doc.modelspace()
M = 1000.0

print('== entities by space / block (POINT, WIPEOUT, SOLID, DIMENSION):')
for e in doc.entitydb.values():
    t = e.dxftype()
    if t in ('POINT', 'WIPEOUT', 'SOLID', 'DIMENSION'):
        owner = e.dxf.get('owner')
        try:
            o = doc.entitydb[owner]
            on = o.dxf.get('name', '?') if o.dxftype() == 'BLOCK_RECORD' else o.dxftype()
        except Exception:
            on = owner
        p = None
        for k in ('location', 'insert', 'vtx0'):
            if e.dxf.is_supported(k) and e.dxf.hasattr(k):
                p = e.dxf.get(k)
                break
        print('  ', t, e.dxf.get('layer'), str(on)[:70], None if p is None else (round(p[0] / M, 3), round(p[1] / M, 3)))

print('\n== block definitions:', len(doc.blocks))
used = set()


def collect(name):
    if name in used:
        return
    used.add(name)
    b = doc.blocks.get(name)
    if b is None:
        return
    for e in b.query('INSERT'):
        collect(e.dxf.name)


for e in msp.query('INSERT'):
    collect(e.dxf.name)
unused = [b.name for b in doc.blocks if b.name not in used and not b.name.startswith('*')]
layouts = [b.name for b in doc.blocks if b.name.startswith('*')]
print('  used by model space (incl. nested):', len(used), '| layout blocks:', layouts, '| unused:', len(unused))
fam = collections.Counter(n.split(' - ')[0].split('-')[0][:40] for n in unused)
print('  unused, by name start:', fam.most_common(25))
nested = [(b.name, [e.dxf.name for e in b.query('INSERT')]) for b in doc.blocks if b.name in used and len(b.query('INSERT'))]
print('  used blocks that contain inserts (nesting):', nested[:10])

print('\n== texts:')
for e in msp.query('TEXT MTEXT'):
    p = e.dxf.insert
    s = e.plain_text() if e.dxftype() == 'MTEXT' else e.dxf.text
    print('  %-12s (%.3f, %.3f) h=%.0f  %r' % (e.dxf.layer, p.x / M, p.y / M, e.dxf.get('char_height', 0), s.replace('\n', ' | ')))


def arcs(entities, where):
    for e in entities:
        if e.dxftype() == 'ARC':
            c = e.dxf.center
            sw = (e.dxf.end_angle - e.dxf.start_angle) % 360
            yield where, e.dxf.layer, c.x / M, c.y / M, e.dxf.radius / M, e.dxf.start_angle, e.dxf.end_angle, sw, e.dxf.get('linetype', 'BYLAYER')


print('\n== door-layer arcs (top level), centre, radius, start-end angle, sweep:')
for w, lay, x, y, r, a0, a1, sw, lt in arcs(msp, 'top'):
    if lay.startswith('A-DOOR'):
        print('   %-12s c (%.3f, %.3f) r %.3f  %.1f..%.1f  sweep %.1f  lt %s' % (lay, x, y, r, a0, a1, sw, lt))
print('\n== door-layer arcs inside door blocks (block coordinates are world: base 0,0; inserts listed by census.py):')
for ins in msp.query('INSERT[layer=="A-DOOR"]'):
    for v in ins.virtual_entities():
        if v.dxftype() == 'ARC':
            c = v.dxf.center
            sw = (v.dxf.end_angle - v.dxf.start_angle) % 360
            print('   %-40s %-12s c (%.3f, %.3f) r %.3f sweep %.1f' % (ins.dxf.name[:40], v.dxf.layer, c.x / M, c.y / M, v.dxf.radius / M, sw))

print('\n== arcs on other layers with r 0.28-2 m and sweep 20-125 deg (what a swing rule could pick up):')
cnt = collections.Counter()
for w, lay, x, y, r, a0, a1, sw, lt in arcs(msp, 'top'):
    if not lay.startswith('A-DOOR') and 0.28 <= r <= 2.0 and 20 <= sw <= 125:
        cnt[lay] += 1
        print('   %-12s c (%.3f, %.3f) r %.3f sweep %.1f' % (lay, x, y, r, sw))
for ins in msp.query('INSERT'):
    if ins.dxf.layer.startswith('A-DOOR'):
        continue
    for v in ins.virtual_entities():
        if v.dxftype() == 'ARC':
            r = v.dxf.radius / M; sw = (v.dxf.end_angle - v.dxf.start_angle) % 360
            lay = v.dxf.layer if v.dxf.layer != '0' else ins.dxf.layer
            if 0.28 <= r <= 2.0 and 20 <= sw <= 125:
                cnt[lay + ' (in block)'] += 1
print('  counts:', dict(cnt))

print('\n== linetypes used by entities (layer, linetype): count')
lt = collections.Counter((e.dxf.get('layer'), e.dxf.get('linetype', 'BYLAYER')) for e in msp)
for k, n in sorted(lt.items()):
    if k[1] not in ('BYLAYER',):
        print('  ', k, n)
print('  (all others BYLAYER)')
