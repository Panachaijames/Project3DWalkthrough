import collections, json, statistics
from ezdxf import recover
doc, _ = recover.readfile('plan.dxf'); msp = doc.modelspace()
XS, YS = 68171, 34160
def quad(x, y): return ('plan' if y <= YS else 'elev') + ('_left' if x < XS else '_right')
grid = collections.defaultdict(list)
def walk(e, inh=None):
    lay = e.dxf.get('layer', '0')
    if lay == '0' and inh: lay = inh
    t = e.dxftype()
    if t == 'INSERT':
        for a in e.attribs:
            if 'GRID' in lay.upper(): p = a.dxf.insert; grid[quad(p.x, p.y)].append((a.dxf.text.strip(), p.x, p.y))
        try:
            for v in e.virtual_entities(): walk(v, lay)
        except Exception: pass
    elif t in ('TEXT', 'ATTRIB', 'ATTDEF') and 'GRID' in lay.upper():
        p = e.dxf.insert; txt = e.dxf.get('text', '') or e.dxf.get('tag', '')
        grid[quad(p.x, p.y)].append((txt.strip(), p.x, p.y))
    elif t == 'MTEXT' and 'GRID' in lay.upper():
        p = e.dxf.insert; grid[quad(p.x, p.y)].append((e.plain_text().strip(), p.x, p.y))
for e in msp: walk(e)
for k in ('plan_left', 'plan_right'):
    print(k, len(grid[k]), sorted(set(l for l,_,_ in grid[k])))
# Each label can appear twice (bubbles at both ends of a grid line). Letters label lines in one
# direction, numbers in the other; match bubbles by label and take the median offset per axis.
def by_label(items):
    d = collections.defaultdict(list)
    for l, x, y in items: d[l].append((x, y))
    return d
Lb, Rb = by_label(grid['plan_left']), by_label(grid['plan_right'])
common = sorted(set(Lb) & set(Rb))
print("common labels:", common)
dxs, dys = [], []
for l in common:
    # vertical grid lines (same x along the line): compare x of bubbles; horizontal: compare y
    lx = statistics.median(x for x, _ in Lb[l]); rx = statistics.median(x for x, _ in Rb[l])
    ly = statistics.median(y for _, y in Lb[l]); ry = statistics.median(y for _, y in Rb[l])
    dxs.append((l, rx - lx)); dys.append((l, ry - ly))
print("dx per label:", [(l, round(v)) for l, v in dxs])
print("dy per label:", [(l, round(v)) for l, v in dys])
json.dump({k: v for k, v in grid.items()}, open('grid.json', 'w', encoding='utf-8'), ensure_ascii=False)
