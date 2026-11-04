import json, math, re, collections, ezdxf
ROOT = 'C:/Users/DWP2/Desktop/Project walkthrough/'
g = json.load(open(ROOT + 'srisawan-rebuild/model_geometry.json', encoding='utf-8'))
S = g['scale']; d = g['data']
def xy(p): return ((p[0] - 754) * S, (301 - p[1]) * S)          # identical to generate_maxscript.py
THICK = {'wall': 0.18, 'core': 0.24, 'envelope': 0.22, 'glass': 0.06}  # identical to the MaxScript
LEVEL = {1: 0.0, 2: 5.0}; HEIGHT = {1: 4.0, 2: 4.0}
def zone_of(name):
    m = re.match(r'SR_L\d_(.+?)_\d{3}(?:_\d+_\d+)?$', name)
    return (m.group(1) if m else name).replace('_', ' ')
boxes = collections.defaultdict(list); info = collections.defaultdict(list)
for s in g['segments']:
    a, b = xy(s['a']), xy(s['b'])
    if math.dist(a, b) < 1e-6: continue
    key = f"L{s['level']}:{s['kind']}"
    boxes[key].append([round(v, 3) for v in (*a, *b)] + [THICK[s['kind']], LEVEL[s['level']], HEIGHT[s['level']]])
    info[key].append(zone_of(s['name']))
# slabs: L1 outline at -0.25..0; L2 outline + 2 voids + 6 shaft holes at 4.75..5.0 (as in the MaxScript)
slabs = {'L1': {'outer': [xy(q) for q in d['outlines']['1']], 'holes': [], 'z': -0.25},
         'L2': {'outer': [xy(q) for q in d['outlines']['2']], 'holes': [[xy(q) for q in h] for h in d['voids'] + g['shaft_holes']], 'z': 4.75}}
# floor 6: separate trace (own origin, unknown level) -> shown alone at z=0
doc = ezdxf.readfile(ROOT + 'floor6-dxf/Srisawan_Floor6_Interior_Walls.dxf')
for e in doc.modelspace().query('LINE'):
    lay = e.dxf.layer
    if lay == 'AXIS_REFERENCE': continue
    kind = 'core' if lay == 'LIFT_CORE_REFERENCE' else 'wall'
    a, b = (e.dxf.start.x, e.dxf.start.y), (e.dxf.end.x, e.dxf.end.y)
    if math.dist(a, b) < 1e-6: continue
    boxes[f'F6:{kind}'].append([round(v, 3) for v in (*a, *b)] + [THICK[kind], 0.0, 4.0])
    info[f'F6:{kind}'].append('Floor 6 lift core (reference)' if kind == 'core' else 'Floor 6 interior wall')
# centre each building on its own footprint
def centre(keys):
    P = [(bx[0], bx[1]) for k in keys for bx in boxes[k]] + [(bx[2], bx[3]) for k in keys for bx in boxes[k]]
    return ((min(p[0] for p in P) + max(p[0] for p in P)) / 2, (min(p[1] for p in P) + max(p[1] for p in P)) / 2,
            max(p[0] for p in P) - min(p[0] for p in P), max(p[1] for p in P) - min(p[1] for p in P))
cH = centre([k for k in boxes if k.startswith('L')]); c6 = centre([k for k in boxes if k.startswith('F6')])
for k in boxes:
    cx, cy = (c6 if k.startswith('F6') else cH)[:2]
    boxes[k] = [[round(b[0]-cx, 3), round(b[1]-cy, 3), round(b[2]-cx, 3), round(b[3]-cy, 3), *b[4:]] for b in boxes[k]]
for sl in slabs.values():
    sl['outer'] = [[round(x-cH[0], 3), round(y-cH[1], 3)] for x, y in sl['outer']]
    sl['holes'] = [[[round(x-cH[0], 3), round(y-cH[1], 3)] for x, y in h] for h in sl['holes']]
out = {'boxes': boxes, 'info': info, 'slabs': slabs, 'size': [round(cH[2], 1), round(cH[3], 1)], 'size6': [round(c6[2], 1), round(c6[3], 1)]}
json.dump(out, open('srisawan3d.json', 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print({k: len(v) for k, v in boxes.items()}, '| hospital footprint', out['size'], 'm | floor 6 footprint', out['size6'], 'm')
print('L2 slab holes:', len(slabs['L2']['holes']))
