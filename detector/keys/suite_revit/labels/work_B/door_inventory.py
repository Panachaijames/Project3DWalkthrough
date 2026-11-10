"""Labeller B: inventory of the door evidence in the DXF itself (exact arcs, leaves, frames, door blocks).

  python -B door_inventory.py <plan.dxf>

Lists, in drawing metres (DXF mm / 1000):
  - every INSERT in model space with its name, layer, insert point, rotation and scale;
  - every ARC (top level and inside inserts) on the door layers A-DOOR / A-DOOR-HDLN, with centre, radius, angles
    and the sweep, plus every arc on any layer with 0.28 <= r <= 2.0 m and a 20-125 degree sweep (swing-like);
  - every LINE on A-DOOR (leaves, arrows, bi-fold panels) longer than 0.3 m.
Reads only the drawing (no detector output).
"""
import math, sys
from ezdxf import recover

DOORL = {'A-DOOR', 'A-DOOR-HDLN'}


def walk(msp):
    for e in msp:
        if e.dxftype() == 'INSERT':
            lay = e.dxf.layer
            yield e, None, 0
            try:
                for v in e.virtual_entities():
                    yield v, e, 1
            except Exception:
                pass
        else:
            yield e, None, 0


def main(path):
    doc, aud = recover.readfile(path)
    msp = doc.modelspace()
    print('## INSERTS')
    for e in msp.query('INSERT'):
        p = e.dxf.insert
        print(f"INSERT {e.dxf.layer:<12} {e.dxf.name[:90]:<90} ins=({p.x/1000:.4f},{p.y/1000:.4f}) rot={e.dxf.get('rotation',0):.2f} "
              f"sx={e.dxf.get('xscale',1)} sy={e.dxf.get('yscale',1)} ext_z={tuple(round(c,3) for c in e.dxf.extrusion)}")
    print('## ARCS')
    for e, parent, depth in walk(msp):
        if e.dxftype() != 'ARC':
            continue
        lay = e.dxf.layer
        if lay == '0' and parent is not None:
            lay = parent.dxf.layer
        c = e.dxf.center
        r = e.dxf.radius / 1000
        a0, a1 = e.dxf.start_angle, e.dxf.end_angle
        sweep = (a1 - a0) % 360
        ext = tuple(round(v, 3) for v in e.dxf.extrusion)
        swing_like = 0.28 <= r <= 2.0 and 20 <= sweep <= 125
        if lay in DOORL or swing_like:
            # end points in world coordinates (ezdxf virtual entities are already in WCS for the 2D case)
            try:
                sp, ep = e.start_point, e.end_point
                se = f"start=({sp.x/1000:.4f},{sp.y/1000:.4f}) end=({ep.x/1000:.4f},{ep.y/1000:.4f})"
            except Exception:
                se = ''
            print(f"ARC {lay:<12} lt={e.dxf.get('linetype','BYLAYER'):<14} c=({c.x/1000:.4f},{c.y/1000:.4f}) r={r:.4f} "
                  f"a={a0:.2f}->{a1:.2f} sweep={sweep:.2f} ext={ext} {se} {'[in ' + parent.dxf.name[:50] + ']' if parent is not None else ''}")
    print('## A-DOOR LINES > 0.3 m')
    for e, parent, depth in walk(msp):
        if e.dxftype() != 'LINE':
            continue
        lay = e.dxf.layer
        if lay == '0' and parent is not None:
            lay = parent.dxf.layer
        if lay != 'A-DOOR':
            continue
        s, t = e.dxf.start, e.dxf.end
        L = math.dist((s.x, s.y), (t.x, t.y)) / 1000
        if L < 0.3:
            continue
        print(f"LINE A-DOOR ({s.x/1000:.4f},{s.y/1000:.4f})-({t.x/1000:.4f},{t.y/1000:.4f}) L={L:.4f} "
              f"{'[in ' + parent.dxf.name[:50] + ']' if parent is not None else ''}")


if __name__ == '__main__':
    main(sys.argv[1])
