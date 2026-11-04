import collections, json, statistics
from ezdxf import recover, bbox
doc, _ = recover.readfile('plan.dxf'); msp = doc.modelspace()
XS, YS = 68171, 34160
def quad(x, y): return ('plan' if y <= YS else 'elev') + ('_left' if x < XS else '_right')
# --- grid labels (TEXT on GRID-01 + ATTRIBs of _GRID inserts) ---
grid = collections.defaultdict(list)
for t in msp.query('TEXT[layer=="GRID-01"]'):
    p = t.dxf.insert; grid[quad(p.x, p.y)].append((t.dxf.text.strip(), p.x, p.y))
for ins in msp.query('INSERT[layer=="GRID-01"]'):
    for a in ins.attribs:
        p = a.dxf.insert; grid[quad(p.x, p.y)].append((a.dxf.text.strip(), p.x, p.y))
for k in ('plan_left', 'plan_right'):
    labels = sorted(set(l for l, _, _ in grid[k]))
    print(f"{k} grid labels ({len(grid[k])}):", labels)
common = set(l for l,_,_ in grid['plan_left']) & set(l for l,_,_ in grid['plan_right'])
print("labels in both plans:", sorted(common))
# translation: for each common label, compare positions (letters -> x-lines? digits -> y-lines?)
dx, dy = [], []
L = {l: (x, y) for l, x, y in grid['plan_left']}; R = {l: (x, y) for l, x, y in grid['plan_right']}
for l in common:
    dx.append(R[l][0] - L[l][0]); dy.append(R[l][1] - L[l][1])
print("per-label dx:", sorted(round(v) for v in dx)); print("per-label dy:", sorted(round(v) for v in dy))
# --- level tags vs Thai floor labels in the elevations ---
levels = []
for ins in msp.query('INSERT[layer=="SPEC"]'):
    for a in ins.attribs:
        if a.dxf.tag == 'LEVEL' and a.dxf.text.strip():
            p = ins.dxf.insert; levels.append((a.dxf.text.strip(), round(p.x), round(p.y), quad(p.x, p.y)))
labels = [(t.dxf.text.strip(), round(t.dxf.insert.x), round(t.dxf.insert.y), quad(t.dxf.insert.x, t.dxf.insert.y)) for t in msp.query('TEXT[layer=="RNAME"]')]
print("\nThai level labels:", labels)
for txt, x, y, q in labels:
    near = sorted((abs(ly - y) + 0.05*abs(lx - x), lv, lx, ly) for lv, lx, ly, lq in levels if lq == q)[:2]
    print(f"  '{txt}' at y={y}  -> nearest level tags: {[(n[1], n[3]) for n in near]}")
json.dump({'grid': grid, 'levels': levels, 'labels': labels}, open('levels_grid.json', 'w'), ensure_ascii=False)
