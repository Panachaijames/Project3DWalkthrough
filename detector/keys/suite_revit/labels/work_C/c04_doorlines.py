"""Labeller C, step 4: all LINE/LWPOLYLINE geometry on A-DOOR, A-DOOR-FRAM (top level and in the door blocks),
clustered by proximity, so each door's leaf, frame and arrows can be read."""
import pickle, math, collections
P = 'C:/Users/DWP2/AppData/Local/Temp/claude/1a2f3fc736ce552c/e1e2f8a1-5b17-462a-bbe8-01925d989674/scratchpad/suite_revit_work/suite_revit/prims.pkl'
D = pickle.load(open(P, 'rb'))
segs = []
for d in D['items']:
    if d['lay'] not in ('A-DOOR', 'A-DOOR-FRAM') or 'pts' not in d or d['t'] == 'ARC': continue
    p = d['pts']
    for a, b in zip(p, p[1:] + ([p[0]] if d.get('closed') else [])):
        segs.append((d['lay'], d['h'], d['path'][:28], a, b, d.get('lt')))
print('segments', len(segs))
# cluster by bbox proximity (0.3 m)
cl = []
for s in segs:
    bx = (min(s[3][0], s[4][0]), min(s[3][1], s[4][1]), max(s[3][0], s[4][0]), max(s[3][1], s[4][1]))
    hit = None
    for c in cl:
        if bx[0] <= c['bb'][2] + 0.3 and bx[2] >= c['bb'][0] - 0.3 and bx[1] <= c['bb'][3] + 0.3 and bx[3] >= c['bb'][1] - 0.3:
            hit = c; break
    if hit is None: cl.append({'bb': list(bx), 's': [s]})
    else:
        hit['s'].append(s); hit['bb'] = [min(hit['bb'][0], bx[0]), min(hit['bb'][1], bx[1]), max(hit['bb'][2], bx[2]), max(hit['bb'][3], bx[3])]
# merge clusters transitively
changed = True
while changed:
    changed = False
    for i in range(len(cl)):
        for j in range(i + 1, len(cl)):
            a, b = cl[i]['bb'], cl[j]['bb']
            if a[0] <= b[2] + 0.3 and a[2] >= b[0] - 0.3 and a[1] <= b[3] + 0.3 and a[3] >= b[1] - 0.3:
                cl[i]['s'] += cl[j]['s']; cl[i]['bb'] = [min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3])]
                del cl[j]; changed = True; break
        if changed: break
for c in sorted(cl, key=lambda c: (c['bb'][1], c['bb'][0])):
    print(f"\n== cluster x {c['bb'][0]:.3f}-{c['bb'][2]:.3f} y {c['bb'][1]:.3f}-{c['bb'][3]:.3f}  ({len(c['s'])} segs)")
    for lay, h, path, a, b, lt in sorted(c['s'], key=lambda s: (s[0], s[3][0], s[3][1])):
        L = math.dist(a, b); ang = math.degrees(math.atan2(b[1] - a[1], b[0] - a[0])) % 180
        print(f"   {lay:11} h {h:5} ({a[0]:.4f},{a[1]:.4f})-({b[0]:.4f},{b[1]:.4f}) L {L:.3f} ang {ang:5.1f} {lt or ''} {path}")
