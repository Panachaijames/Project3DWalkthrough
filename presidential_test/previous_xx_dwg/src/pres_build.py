"""Presidential suite test (19 Oct 2026): DWG from a different author -> merged walls, parapet, floor plate, replay data.

This author draws walls on layer 0 together with loose furniture, so walls are found by GEOMETRY, not by layer:
straight lines drawn directly on layer 0 (not inside blocks) are paired with a parallel partner a wall's thickness
away, as for the DWG house. Items that pair up but are furniture are excluded by hand (EXCLUDE below): that is the
job of the check-and-fix screen in the product.
Inputs: plan.dxf (from LibreDWG dwg2dxf). Outputs: pres3d_merged.json, pres3d_stages.json.
"""
import collections, json, math, sys
from pathlib import Path
from ezdxf import recover, path as ezpath
from shapely.geometry import LineString, Polygon, box
from shapely.ops import unary_union

HERE = Path(__file__).resolve().parent
for d in (HERE.parent / 'cadtest', HERE.parent.parent / 'cad_test' / 'src'):     # scratch layout / project layout
    sys.path.insert(0, str(d))
from merge_cad import strips, solidify                     # the same pairing and merging as the DWG house

FLOOR_TO_FLOOR = 3.0                                        # given by the project (19 Oct): 3 m floor to floor
PARAPET = 1.1                                               # balcony parapet height (m), a default
REGION = box(-0.5, -0.5, 38.0, 25.5)                        # the suite on the sheet (m); the corridor lines run on to 75 m
WALL_LAYERS = {'0', 'A-1.Netcat - tuong'}                   # this author: walls drawn directly on layer 0 (+ the cut-wall layer)
CATS = {'KT-Cua': 'door', 'KT-Lancan': 'railing'}           # doors/windows and the balcony railing, by layer
# Paired line work that is furniture, not walls (marked by hand; drawing coordinates in metres):
EXCLUDE = {
    'central dining table and the ring around it': (19.6, 9.6, 27.6, 14.8),
    'terrace dining table and chairs': (7.6, 2.9, 12.4, 5.0),
    'terrace bar / lounge unit': (3.2, 10.4, 5.6, 15.2),
    'bath tub': (25.3, 1.7, 27.5, 3.4),
    'stair treads in the core': (30.0, 16.0, 33.6, 19.5),
}

doc, _ = recover.readfile(str(HERE / 'plan.dxf')); msp = doc.modelspace()

def segments(e, step=15):
    try: p = ezpath.make_path(e)
    except Exception: return []
    pts = list(p.flattening(distance=step))
    out = []
    for a, b in zip(pts, pts[1:]):
        ls = LineString([(a.x / 1000, a.y / 1000), (b.x / 1000, b.y / 1000)]).intersection(REGION)
        if ls.is_empty or ls.geom_type != 'LineString' or ls.length < 0.02: continue
        (x1, y1), (x2, y2) = ls.coords[0], ls.coords[-1]
        out.append([x1, y1, x2, y2])
    return out

lines = collections.defaultdict(list)      # cat -> [x1, y1, x2, y2] (m, drawing frame)
read, layers_by_cat, texts = 0, collections.defaultdict(set), []
def walk(e, inh=None, in_block=False, depth=0):
    global read
    lay = e.dxf.get('layer', '0')
    if lay == '0' and inh: lay = inh
    t = e.dxftype()
    if t in ('INSERT', 'DIMENSION') and depth < 6:
        try:
            for v in e.virtual_entities(): walk(v, lay, True, depth + 1)
        except Exception: pass
        return
    if t in ('TEXT', 'MTEXT'):
        # Room names: the plan's own labels (not text inside furniture blocks), with at least one letter; not the floor tag.
        p = e.dxf.insert
        s = (e.plain_text() if t == 'MTEXT' else e.dxf.get('text', '')).strip()
        if (not in_block and any(ch.isalpha() for ch in s) and not s.upper().startswith('FL-')
                and REGION.contains(box(p.x / 1000, p.y / 1000, p.x / 1000 + 1e-6, p.y / 1000 + 1e-6))):
            texts.append({'text': s, 'x': p.x / 1000, 'y': p.y / 1000})
        return
    if t in ('POINT', 'ATTRIB', 'ATTDEF', 'WIPEOUT'): return
    segs = segments(e, 15 if not in_block else 40)
    if not segs: return
    read += 1
    if not in_block and lay in WALL_LAYERS and t in ('LINE', 'LWPOLYLINE', 'POLYLINE', 'ARC'): cat = 'wall'
    else: cat = CATS.get(lay, 'noise')
    layers_by_cat[cat].add(lay)
    lines[cat] += segs
for e in msp: walk(e)

# Walls: pair face lines 60-330 mm apart (partitions and walls) and 450-520 mm apart (the thick outer band).
def keep(r):
    c = r.centroid
    return not any(x0 <= c.x <= x1 and y0 <= c.y <= y1 for x0, y0, x1, y1 in EXCLUDE.values())
thin, n_thin, _ = strips(lines['wall'], 0.06, 0.33)
thick, n_thick, _ = strips(lines['wall'], 0.45, 0.52)
excluded = sum(1 for r in thin + thick if not keep(r))
thin, thick = [r for r in thin if keep(r)], [r for r in thick if keep(r)]
every = unary_union([p for p in solidify(thin, 0.12) + solidify(thick, 0.12) if p.area > 0.1])
outline = every.buffer(2.0, join_style='mitre').buffer(-2.0, join_style='mitre')
outer = unary_union([Polygon(g.exterior) for g in (outline.geoms if hasattr(outline, 'geoms') else [outline]) if g.area > 20])
# Wall line work under the balcony railing (layer KT-Lancan) is the edge parapet: 1.1 m, not a full-height wall.
rail_zone = unary_union([LineString([(a, b), (c, d)]) for a, b, c, d in lines['railing']]).buffer(0.65)
polys = lambda g: [x for x in (g.geoms if hasattr(g, 'geoms') else [g]) if x.geom_type == 'Polygon']
parapet = [g for g in polys(every.intersection(rail_zone)) if g.area > 0.05]
walls = [g for g in polys(every.difference(rail_zone)) if g.area > 0.1]
plate = [Polygon(g.exterior).simplify(0.02) for g in (outer.geoms if hasattr(outer, 'geoms') else [outer]) if g.area > 20]

# Centre the model on the walls, as for the house.
minx, miny, maxx, maxy = unary_union(walls + parapet).bounds
cx, cy = (minx + maxx) / 2, (miny + maxy) / 2
R = lambda v: round(v, 3)

def clean(polys, min_area):
    """Outlines that survive rounding to the millimetre: repaired, simplified by 3 mm, no repeated points, valid.
    (Cutting walls at the railing zone and flattening curves leave near-duplicate points and touching loops.)"""
    out = []
    for p in polys:
        g = p.buffer(0).simplify(0.003, preserve_topology=True)
        for part in (g.geoms if hasattr(g, 'geoms') else [g]):
            if part.geom_type != 'Polygon' or part.area < min_area: continue
            def loop(coords):
                pts = []
                for x, y in list(coords)[:-1]:
                    q = (R(x - cx), R(y - cy))
                    if not pts or q != pts[-1]: pts.append(q)
                while len(pts) > 1 and pts[0] == pts[-1]: pts.pop()
                return pts
            o, hs = loop(part.exterior.coords), [h for h in (loop(i.coords) for i in part.interiors) if len(h) >= 3]
            if len(o) < 3: continue
            q = Polygon(o, hs)
            if not q.is_valid:                     # rounding made it touch itself: repair once more, in rounded units
                fixed = q.buffer(0)
                parts = [x for x in (fixed.geoms if hasattr(fixed, 'geoms') else [fixed]) if x.geom_type == 'Polygon' and x.area >= min_area]
                for x in parts:
                    o2 = loop([(a + cx, b + cy) for a, b in x.exterior.coords])
                    h2 = [h for h in (loop([(a + cx, b + cy) for a, b in i.coords]) for i in x.interiors) if len(h) >= 3]
                    if len(o2) >= 3 and Polygon(o2, h2).is_valid: out.append({'o': [list(v) for v in o2], 'h': [[list(v) for v in h] for h in h2]})
                continue
            out.append({'o': [list(v) for v in o], 'h': [[list(v) for v in h] for h in hs]})
    return out
merged = {'levels': {'suite': 0.0}, 'tops': {'suite': FLOOR_TO_FLOOR},
          'solids': {'suite:wall': clean(walls, 0.1), 'suite:parapet': clean(parapet, 0.05)},
          'plates': {'suite': clean(plate, 20)}, 'stairs': {'suite': []}, 'parapetHeight': PARAPET,
          'offset': [R(cx), R(cy)],                  # add back to get the drawing's own coordinates (m)
          'rooms': [{'name': t['text'].replace('\n', ' '), 'x': R(t['x'] - cx), 'y': R(t['y'] - cy)} for t in texts]}
json.dump(merged, open(HERE / 'pres3d_merged.json', 'w', encoding='utf-8'), separators=(',', ':'), ensure_ascii=False)

flat = lambda segs, nd=3: [round(v - (cx if i % 2 == 0 else cy), nd) for s in segs for i, v in enumerate(s)]
noise = sorted(lines['noise'], key=lambda s: -math.dist(s[:2], s[2:]))[:6000]
quads = lambda rects: [round(v, 3) for r in rects for x, y in list(r.exterior.coords)[:4] for v in (x - cx, y - cy)]
wall_len = sum(math.dist(s[:2], s[2:]) for s in lines['wall'])
stages = {
    'source': {'file': 'layout presidential xx.dwg', 'layers': len(doc.layers), 'units': 'mm'},
    'floors': {'suite': {'sheet': [0.0, 0.0],
                         'lines': {'wall': flat(lines['wall']), 'door': flat(lines['door']), 'railing': flat(lines['railing']), 'noise': flat(noise, 2)},
                         'pairs': {'wall': quads(thin), 'parapet': quads(thick)}}},
    'stats': {'read': read, 'kept': {k: len(lines[k]) for k in ('wall', 'door', 'railing')}, 'ignoredLines': len(lines['noise']),
              'pieces': {'wall': len(thin), 'parapet': len(thick)}, 'excluded': excluded, 'excludedAreas': list(EXCLUDE),
              'runs': {'wall': len(walls), 'parapet': len(parapet)}, 'rooms': len(texts),
              'layers': {k: sorted(v) for k, v in layers_by_cat.items()}, 'planLayers': len(set().union(*layers_by_cat.values())),
              'wallLineLength': round(wall_len, 1)},
}
json.dump(stages, open(HERE / 'pres3d_stages.json', 'w', encoding='utf-8'), separators=(',', ':'), ensure_ascii=False)
print(json.dumps(stages['stats'], indent=1, ensure_ascii=False))
print('plate area', round(sum(p.area for p in plate)), 'm2 | wall solids', len(walls), 'area', round(sum(p.area for p in walls), 1), 'm2 | parapet', len(parapet))

# A top view to check by eye.
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MP
fig, ax = plt.subplots(figsize=(20, 13), dpi=90)
for p in plate: ax.add_patch(MP(list(p.exterior.coords), facecolor='#eef0ec', edgecolor='#999', lw=0.8))
for p in walls: ax.add_patch(MP(list(p.exterior.coords), facecolor='#8c7b6a', edgecolor='none'))
for p in parapet: ax.add_patch(MP(list(p.exterior.coords), facecolor='#c9a26b', edgecolor='none'))
for name, (x0, y0, x1, y1) in EXCLUDE.items(): ax.add_patch(MP([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], fill=False, edgecolor='red', ls='--'))
for t in texts: ax.text(t['x'], t['y'], t['text'].split('\n')[0], fontsize=8, color='#1f4e79')
ax.autoscale(); ax.set_aspect('equal'); plt.tight_layout(); plt.savefig(HERE / 'pres_topview.png'); plt.close()
