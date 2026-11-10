"""Labeller C, step 11: door / window / panel block definitions in the DXF (used or not), with their arcs and line extents."""
import math, collections
from ezdxf import recover
DXF = 'C:/Users/DWP2/AppData/Local/Temp/claude/1a2f3fc736ce552c/e1e2f8a1-5b17-462a-bbe8-01925d989674/scratchpad/suite_revit_work/suite_revit/plan.dxf'
doc, aud = recover.readfile(DXF)
used = collections.Counter(e.dxf.name for e in doc.modelspace().query('INSERT'))
for b in doc.blocks:
    n = b.name
    U = n.upper()
    if not any(k in U for k in ('DOOR', 'WIN', 'SASH', 'SLID', 'OPEN', 'SHOWER', 'PANEL', 'LOUV', 'GLAZ')): continue
    ents = list(b)
    c = collections.Counter((e.dxf.get('layer', '0'), e.dxftype()) for e in ents)
    arcs = [e for e in ents if e.dxftype() == 'ARC']
    xs = []; ys = []
    for e in ents:
        if e.dxftype() == 'LINE':
            xs += [e.dxf.start.x, e.dxf.end.x]; ys += [e.dxf.start.y, e.dxf.end.y]
    ext = f"x {min(xs):.0f}..{max(xs):.0f} y {min(ys):.0f}..{max(ys):.0f}" if xs else ''
    print(f"{n[:95]:95} used {used.get(n, 0)}  {dict(c)}  {ext}")
    for a in arcs:
        print(f"      arc r {a.dxf.radius:.1f} {a.dxf.start_angle:.1f}->{a.dxf.end_angle:.1f} layer {a.dxf.get('layer')}")
