import pymupdf, collections, json, math, time
t0 = time.time()
doc = pymupdf.open('show.pdf')
PT2M = 25.4 / 72 * 100 / 1000        # paper points -> real metres at 1:100
PAGES = {'ground': 9, 'upper': 10}   # pages 10 and 11 (furniture layouts)
LEVELS = {'ground': 0.0, 'upper': 3.8}   # upper level NOT in the PDF set -> assumed
TOPS = {'ground': 3.8, 'upper': 7.1}
def cat_of(layer):
    L = (layer or '').split('|')[-1].upper()
    if L in ('A-WALL', 'A-WALL-FULL', 'A-WALL-IN', 'A-COLUMN', 'A-COLUMN-FULL'): return 'wall'
    if L in ('A-DW', 'I-DOOR'): return 'window'
    if L == 'I-STAIR': return 'stair'
    return None
segs = collections.defaultdict(list); skipped = collections.Counter()
for floor, pno in PAGES.items():
    for d in doc[pno].get_drawings():
        cat = cat_of(d.get('layer'))
        if not cat: continue
        if d.get('dashes') and d['dashes'] not in ('[] 0', '[] 0.0'): skipped['dashed'] += 1; continue
        if cat == 'wall' and (d.get('width') or 0) < 0.7: skipped['thin line on wall layer (pattern)'] += 1; continue
        for it in d['items']:
            if it[0] == 'l': pairs = [(it[1], it[2])]
            elif it[0] == 'c':
                if cat == 'window': skipped['door-swing curve'] += 1; continue
                pairs = [(it[1], it[4])]
            elif it[0] == 're':
                r = it[1]; p = [r.tl, r.tr, r.br, r.bl]; pairs = [(p[i], p[(i+1) % 4]) for i in range(4)]
            elif it[0] == 'qu':
                q = it[1]; p = [q.ul, q.ur, q.lr, q.ll]; pairs = [(p[i], p[(i+1) % 4]) for i in range(4)]
            else: continue
            for a, b in pairs:
                L = math.dist(a, b) * PT2M
                if L < 0.02: skipped['tiny piece'] += 1; continue
                segs[(floor, cat)].append([a.x * PT2M, -a.y * PT2M, b.x * PT2M, -b.y * PT2M])
for k in sorted(segs): print(k, len(segs[k]), 'segments')
print('skipped:', dict(skipped))
allw = [s for (f, c), v in segs.items() for s in v if c == 'wall']
cx = (min(min(s[0], s[2]) for s in allw) + max(max(s[0], s[2]) for s in allw)) / 2
cy = (min(min(s[1], s[3]) for s in allw) + max(max(s[1], s[3]) for s in allw)) / 2
out = {'levels': LEVELS, 'tops': TOPS, 'segments': {f'{f}:{c}': [[round(s[0]-cx, 3), round(s[1]-cy, 3), round(s[2]-cx, 3), round(s[3]-cy, 3)] for s in v] for (f, c), v in segs.items()}}
json.dump(out, open('house3d_pdf.json', 'w'))
print('extent (m):', round(max(max(s[0], s[2]) for s in allw) - min(min(s[0], s[2]) for s in allw), 1), 'x',
      round(max(max(s[1], s[3]) for s in allw) - min(min(s[1], s[3]) for s in allw), 1), '| time', round(time.time() - t0, 1), 's')
