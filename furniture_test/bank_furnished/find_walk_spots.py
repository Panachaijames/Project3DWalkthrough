"""The busiest furnished spot on each level of the bank, for the Walk timings (3 Nov 2026).

    python -B find_walk_spots.py            (run from anywhere; reads ../../bank_test/src/bank_model.json and placements.json)

A spot is an eye position (1.6 m above the level) on the floor plate, at least 0.55 m from every wall, column, glass pane,
railing and furniture box (Walk's own start-up check wants 0.5 m of room), on a 0.2 m grid. From each spot, every direction in
2-degree steps is scored by the triangles at FULL detail of the team's models inside Walk's field of view (24 mm lens at 16:9:
83 degrees across, less 3 degrees each side) within 12 m that can be seen from the eye (the line from the eye to the model's
centre crosses no wall or column; glass hides nothing); ties go to the triangles of the models within 3 m (the level-of-detail
radius of mode D). Two views per level:
  busiest  the spot with the most model triangles at full detail within 3 m (seen from the eye), looking the way that scores best
  widest   the spot and direction with the highest score of all (the most model triangles in view)
Writes walk_spots.json here (with the address parameters for the page).
"""
import json
import math
import sys
from pathlib import Path

import numpy as np
from shapely.geometry import LineString, Point, Polygon
from shapely.ops import unary_union
from shapely.prepared import prep

sys.stdout.reconfigure(encoding='utf-8')
HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent.parent
bank = json.loads((PROJECT / 'bank_test/src/bank_model.json').read_text(encoding='utf-8'))
pl = json.loads((HERE / 'placements.json').read_text(encoding='utf-8'))
RADIUS, CLEAR, STEP, VIEW_DEG, FAR, EYE, PITCH = 3.0, 0.55, 0.2, 83.3, 12.0, 1.6, -8.0
YAWS = np.arange(-180, 180, 2)


def poly(p):
    g = Polygon(p['o'], p['h'])
    return g if g.is_valid else g.buffer(0)


# the team's models where the page puts them: the centre of the normalised model's box, placed (plan x, y = -z)
models = []
for name, m in pl['models'].items():
    c = np.array(m['centreNormalised'] + [1.0])
    for p in m['pieces']:
        w = np.array(p['place']) @ c
        models.append({'model': name, 'key': p['key'], 'floor': p['floor'], 'x': float(w[0]), 'y': float(-w[2]), 'triangles': m['triangles']})

out = {'how': ' '.join(__doc__.strip().split('\n\n')[1].split()), 'radius_m': RADIUS, 'levels': {}}
for f in bank['floors']:
    key = f['key']
    parts = [p for p in bank['parts'] if p['floor'] == key]
    slab = unary_union([poly(p) for p in parts if p['kind'] == 'slab'])
    hide = prep(unary_union([poly(p) for p in parts if p['kind'] in ('wall', 'column') and p['z0'] < 0.5]))
    stop = unary_union([poly(p) for p in parts if p['kind'] in ('wall', 'column', 'glass', 'railing', 'mullion', 'parapet', 'step') and p['z0'] < 1.0])
    boxes = []
    for d in bank['furniture']:
        if d['floor'] != key:
            continue
        a = math.radians(d['rot']); ca, sa = math.cos(a), math.sin(a); hw, hd = d['w'] / 2, d['d'] / 2
        boxes.append(Polygon([(d['x'] + ca * u - sa * v, d['y'] + sa * u + ca * v) for u, v in ((-hw, -hd), (hw, -hd), (hw, hd), (-hw, hd))]))
    free = prep(slab.buffer(-CLEAR).difference(unary_union([stop] + boxes).buffer(CLEAR)))
    walkable = prep(slab.buffer(-0.32).difference(unary_union([stop] + boxes).buffer(0.32)))     # Walk's own radius is 0.3 m
    here = [m for m in models if m['floor'] == key]

    def views(x, y):
        """the models seen from (x, y) within FAR, and per direction the full-detail triangles in view (all; within 3 m)"""
        seen = [m for m in here if math.hypot(m['x'] - x, m['y'] - y) <= FAR and not hide.intersects(LineString([(x, y), (m['x'], m['y'])]))]
        if not seen:
            return seen, np.zeros(len(YAWS)), np.zeros(len(YAWS))
        ang = np.degrees(np.arctan2([-(m['x'] - x) for m in seen], [m['y'] - y for m in seen]))      # the yaw that looks straight at it
        tri = np.array([m['triangles'] for m in seen], float)
        near = np.array([math.hypot(m['x'] - x, m['y'] - y) <= RADIUS for m in seen])
        inside = np.abs((ang[None, :] - YAWS[:, None] + 180) % 360 - 180) <= VIEW_DEG / 2 - 3
        return seen, (inside * tri).sum(1), (inside * tri * near).sum(1)

    x0, y0, x1, y1 = slab.bounds
    best = most_near = None
    for x in np.arange(math.floor(x0), x1, STEP):
        for y in np.arange(math.floor(y0), y1, STEP):
            if not free.contains(Point(x, y)):
                continue
            seen, all_, near_ = views(x, y)
            if not seen:
                continue
            i = int(np.lexsort((near_, all_))[-1])
            if best is None or (all_[i], near_[i]) > best[0]:
                best = ((all_[i], near_[i]), float(x), float(y), int(YAWS[i]))
            n3 = [m for m in seen if math.hypot(m['x'] - x, m['y'] - y) <= RADIUS]
            s3 = (sum(m['triangles'] for m in n3), len(n3))
            if most_near is None or s3 > most_near[0]:
                most_near = (s3, float(x), float(y))
    def describe(x, y, yaw):
        seen, _, _ = views(x, y)
        dist = lambda m: math.hypot(m['x'] - x, m['y'] - y)
        view = [m for m in seen if abs((math.degrees(math.atan2(-(m['x'] - x), m['y'] - y)) - yaw + 180) % 360 - 180) <= VIEW_DEG / 2 - 3]
        near = [m for m in seen if dist(m) <= RADIUS]
        rooms = sorted(((math.hypot(r['x'] - x, r['y'] - y), r['label']) for r in bank['rooms'] if r['floor'] == key))[:2]
        count = lambda ms: {n: sum(1 for m in ms if m['model'] == n) for n in sorted({m['model'] for m in ms})}
        return {
            'x': round(x, 2), 'y': round(y, 2), 'yawDeg': yaw, 'pitchDeg': PITCH, 'eye_m': EYE,
            'facing': ['north', 'north-west', 'west', 'south-west', 'south', 'south-east', 'east', 'north-east'][int(((yaw % 360) + 22.5) // 45) % 8],
            'url': f"mode=walk&floor={key}&x={x:.2f}&z={-y:.2f}&yaw={yaw}&pitch={PITCH:g}",
            'nearestRooms': [r[1] for r in rooms],
            'inView': {'models': len(view), 'trianglesFullDetail': sum(m['triangles'] for m in view), 'byModel': count(view),
                       'within3m': sum(1 for m in view if dist(m) <= RADIUS), 'within3mTriangles': sum(m['triangles'] for m in view if dist(m) <= RADIUS),
                       'pieces': sorted(m['key'] for m in view)},
            'around3m': {'models': len(near), 'trianglesFullDetail': sum(m['triangles'] for m in near), 'byModel': count(near), 'pieces': sorted(m['key'] for m in near)},
        }
    _, bx, by = most_near
    _, all_, near_ = views(bx, by)
    byaw = int(YAWS[int(np.lexsort((near_, all_))[-1])])
    _, wx, wy, wyaw = best
    out['levels'][key] = {'busiest': describe(bx, by, byaw), 'widest': describe(wx, wy, wyaw)}
    # a straight walk through the busiest spot, for the level-of-detail check: the longest free straight line through it
    # with Walk's own 0.3 m of room (up to 4 m each way, 5 cm steps, every 5 degrees), walked from one end to the other
    def reach(a, sign):
        dx, dy = math.cos(math.radians(a)) * sign, math.sin(math.radians(a)) * sign
        r = 0.0
        while r < 4.0 and walkable.contains(Point(bx + dx * (r + 0.05), by + dy * (r + 0.05))):
            r += 0.05
        return r
    best_path = max(((reach(a, 1) + reach(a, -1), a) for a in range(0, 180, 5)))
    a = best_path[1]
    r1, r0 = reach(a, 1), reach(a, -1)
    ca, sa = math.cos(math.radians(a)), math.sin(math.radians(a))
    out['levels'][key]['busiest']['path'] = {'from': [round(bx - ca * r0, 2), round(by - sa * r0, 2)], 'to': [round(bx + ca * r1, 2), round(by + sa * r1, 2)],
                                             'metres': round(r0 + r1, 2), 'directionDeg': a}
    print(key, 'walk path', out['levels'][key]['busiest']['path'])
    for k, v in out['levels'][key].items():
        print(key, k, json.dumps({q: v[q] for q in ('x', 'y', 'yawDeg', 'facing', 'nearestRooms')}, ensure_ascii=False),
              'in view', v['inView']['models'], v['inView']['trianglesFullDetail'], v['inView']['byModel'], '| within 3 m', v['around3m']['models'], v['around3m']['trianglesFullDetail'])
(HERE / 'walk_spots.json').write_text(json.dumps(out, indent=1, ensure_ascii=False), encoding='utf-8')
