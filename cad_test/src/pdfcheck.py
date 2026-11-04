import pymupdf, collections, re, math
doc = pymupdf.open('show.pdf')
PT2MM = 25.4 / 72 * 100          # paper points -> real mm at 1:100
def segs_of(d):
    out = []
    for it in d['items']:
        if it[0] == 'l': out.append((it[1], it[2]))
        elif it[0] == 'c': out.append((it[1], it[4]))
        elif it[0] == 're':
            r = it[1]; p = [r.tl, r.tr, r.br, r.bl]; out += [(p[i], p[(i+1) % 4]) for i in range(4)]
        elif it[0] == 'qu':
            q = it[1]; p = [q.ul, q.ur, q.lr, q.ll]; out += [(p[i], p[(i+1) % 4]) for i in range(4)]
    return out
for pno in (9, 10):
    dr = doc[pno].get_drawings()
    sizes = collections.Counter(); dashed = 0
    for d in dr:
        if (d.get('layer') or '').endswith('A-WALL'):
            if d.get('dashes') and d['dashes'] not in ('[] 0', '[] 0.0'): dashed += 1
            for a, b in segs_of(d):
                L = math.dist(a, b) * PT2MM
                sizes['<20mm' if L < 20 else '20-100mm' if L < 100 else '100-500mm' if L < 500 else '>=500mm'] += 1
    print(f"page {pno+1} A-WALL segment lengths (real):", dict(sizes), "| dashed paths:", dashed)
# do the two plan pages share the same framing? compare full-column rectangles
def col_centres(pno):
    pts = []
    for d in doc[pno].get_drawings():
        if (d.get('layer') or '').endswith('A-COLUMN-FULL') or (d.get('layer') or '').endswith('A-COLUMN'):
            r = d['rect']
            if 1 < r.width < 15 and 1 < r.height < 15: pts.append((round(r.x0 + r.width/2, 1), round(r.y0 + r.height/2, 1)))
    return sorted(set(pts))
g, u = col_centres(9), col_centres(10)
match = [p for p in g if any(math.dist(p, q) < 1.0 for q in u)]
print(f"\ncolumn markers: ground {len(g)}, upper {len(u)}, same position on the sheet (within 1 pt = 3.5 cm real): {len(match)}")
# any upper-floor level anywhere in the 104 pages?
lv = collections.Counter()
for p in doc:
    for w in p.get_text('words'):
        if re.search(r'(FFL|SSL|FL\.|CL\.|C\.H|\+\d{1,2}\.\d{2}|\+\d{3,4}\b)', w[4]): lv[w[4]] += 1
print("\nlevel / height words in all pages:", lv.most_common(25))
