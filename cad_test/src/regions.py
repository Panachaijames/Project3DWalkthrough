import collections, json, ezdxf
from ezdxf import recover, bbox
doc, _ = recover.readfile('plan.dxf')
msp = doc.modelspace()
cache = bbox.Cache()
# use WALL + WIN + DOOR + STAIR geometry to find the 4 drawings
items = []
for e in msp:
    if e.dxf.layer in ('WALL','WIN','STAIR','DOOR','D-JAMB','WALL-GL','COL'):
        b = bbox.extents([e], cache=cache)
        if b.has_data: items.append(b)
xs = sorted(b.center.x for b in items); ys = sorted(b.center.y for b in items)
# split by the biggest gaps in x and y
def split(vals):
    gaps = [(vals[i+1]-vals[i], (vals[i+1]+vals[i])/2) for i in range(len(vals)-1)]
    return max(gaps)[1]
xsplit, ysplit = split(xs), split(ys)
print('x split', round(xsplit), 'y split', round(ysplit))
regions = {}
for name, fx, fy in (('elev_left', lambda x: x<xsplit, lambda y: y>ysplit), ('elev_right', lambda x: x>=xsplit, lambda y: y>ysplit),
                     ('plan_left', lambda x: x<xsplit, lambda y: y<=ysplit), ('plan_right', lambda x: x>=xsplit, lambda y: y<=ysplit)):
    sel = [b for b in items if fx(b.center.x) and fy(b.center.y)]
    x0=min(b.extmin.x for b in sel); y0=min(b.extmin.y for b in sel); x1=max(b.extmax.x for b in sel); y1=max(b.extmax.y for b in sel)
    regions[name] = [x0,y0,x1,y1]
    print(f"{name}: {len(sel)} items, {round((x1-x0)/1000,1)} x {round((y1-y0)/1000,1)} m")
json.dump(regions, open('regions.json','w'))
