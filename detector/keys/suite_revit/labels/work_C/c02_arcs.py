"""Labeller C, step 2: every ARC in model space and inside inserts (exact centre / radius / angles, metres),
with the swing-like ones flagged (r 0.28-2.0 m, sweep 15-125 deg). Reads the DXF with ezdxf."""
import math, sys, collections
from ezdxf import recover
DXF = 'C:/Users/DWP2/AppData/Local/Temp/claude/1a2f3fc736ce552c/e1e2f8a1-5b17-462a-bbe8-01925d989674/scratchpad/suite_revit_work/suite_revit/plan.dxf'
doc, aud = recover.readfile(DXF)
msp = doc.modelspace()
out = []
def walk(e, inh=None, path=''):
    lay = e.dxf.get('layer', '0')
    if lay == '0' and inh: lay = inh
    t = e.dxftype()
    if t == 'INSERT':
        for v in e.virtual_entities(): walk(v, lay, path + '>' + e.dxf.name)
        return
    if t == 'ARC':
        c = e.dxf.center; r = e.dxf.radius
        a0, a1 = e.dxf.start_angle % 360, e.dxf.end_angle % 360
        sw = (a1 - a0) % 360
        ez = e.dxf.get('extrusion', (0, 0, 1))
        s = e.start_point; en = e.end_point
        out.append(dict(lay=lay, path=path, h=str(e.dxf.get('handle')), c=(c.x/1000, c.y/1000), r=r/1000, a0=a0, a1=a1, sw=sw,
                        s=(s.x/1000, s.y/1000), e=(en.x/1000, en.y/1000), lt=e.dxf.get('linetype', 'BYLAYER'), ez=tuple(ez)))
for e in msp: walk(e)
print('arcs total', len(out))
cnt = collections.Counter(o['lay'] for o in out)
print(cnt)
sw = [o for o in out if 0.28 <= o['r'] <= 2.0 and 15 <= o['sw'] <= 125]
print('\nswing-like arcs (r 0.28-2.0, sweep 15-125):', len(sw))
for o in sorted(sw, key=lambda o: (o['lay'], o['c'])):
    print(f"  {o['lay']:12} h {o['h']:5} c ({o['c'][0]:.4f},{o['c'][1]:.4f}) r {o['r']:.4f} a {o['a0']:.2f}->{o['a1']:.2f} sw {o['sw']:.2f}"
          f" start ({o['s'][0]:.4f},{o['s'][1]:.4f}) end ({o['e'][0]:.4f},{o['e'][1]:.4f}) lt {o['lt']} ez {o['ez'][2]:.0f} {o['path'][:60]}")
# all door-layer arcs regardless of size
print('\nall arcs on A-DOOR* layers:')
for o in sorted([o for o in out if o['lay'].startswith('A-DOOR')], key=lambda o: o['c']):
    print(f"  {o['lay']:12} h {o['h']:5} c ({o['c'][0]:.4f},{o['c'][1]:.4f}) r {o['r']:.4f} a {o['a0']:.2f}->{o['a1']:.2f} sw {o['sw']:.2f} lt {o['lt']} {o['path'][:70]}")
