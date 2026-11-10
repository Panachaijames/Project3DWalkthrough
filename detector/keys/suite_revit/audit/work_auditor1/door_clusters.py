"""auditor1 helper: cluster every door-layer entity (A-DOOR, A-DOOR-HDLN, A-DOOR-FRAM) of the drawing and report each cluster's
box and its distance to the nearest audit place (segment between the place's two ends), to find doors no place covers."""
import os, json, pickle, math
from pathlib import Path

D = pickle.load(open(Path(os.environ['OPENINGS_DATA']) / 'suite_revit' / 'prims.pkl', 'rb'))
P = json.loads(Path(__file__).resolve().parent.parent.joinpath('places.json').read_text(encoding='utf-8'))['places']
LAY = {'A-DOOR', 'A-DOOR-HDLN', 'A-DOOR-FRAM'}
boxes = []
for d in D['items']:
    if d['lay'] not in LAY or 'pts' not in d: continue
    xs = [p[0] for p in d['pts']]; ys = [p[1] for p in d['pts']]
    boxes.append([min(xs), min(ys), max(xs), max(ys), {d['lay']}, 1])
# merge boxes closer than 0.12 m
changed = True
while changed:
    changed = False
    out = []
    for b in boxes:
        for o in out:
            if b[0] <= o[2] + 0.12 and o[0] <= b[2] + 0.12 and b[1] <= o[3] + 0.12 and o[1] <= b[3] + 0.12:
                o[0], o[1], o[2], o[3] = min(o[0], b[0]), min(o[1], b[1]), max(o[2], b[2]), max(o[3], b[3])
                o[4] |= b[4]; o[5] += b[5]; changed = True
                break
        else:
            out.append(b)
    boxes = out

def seg_dist(px, py, a, b):
    ax, ay = a; bx, by = b
    dx, dy = bx - ax, by - ay
    L2 = dx * dx + dy * dy
    t = 0 if L2 == 0 else max(0, min(1, ((px - ax) * dx + (py - ay) * dy) / L2))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))

def box_seg_dist(bx, a, b):
    # distance from a place segment to a box: sample the box edges
    best = 1e9
    x0, y0, x1, y1 = bx
    for i in range(21):
        for (px, py) in ((x0 + (x1 - x0) * i / 20, y0), (x0 + (x1 - x0) * i / 20, y1), (x0, y0 + (y1 - y0) * i / 20), (x1, y0 + (y1 - y0) * i / 20)):
            best = min(best, seg_dist(px, py, a, b))
    # segment inside the box
    for t in (0, 0.25, 0.5, 0.75, 1):
        px, py = a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t
        if x0 <= px <= x1 and y0 <= py <= y1: best = 0
    return best

boxes.sort(key=lambda b: (round(b[1]), b[0]))
for b in boxes:
    ds = sorted((box_seg_dist(b[:4], p['ends'][0], p['ends'][1]), p['place']) for p in P)
    print(f"box x {b[0]:.3f}-{b[2]:.3f} y {b[1]:.3f}-{b[3]:.3f}  n={b[5]:3d} {sorted(b[4])}  nearest places: {', '.join(f'{n} {d:.2f}' for d, n in ds[:3])}")
print(len(boxes), 'clusters')
