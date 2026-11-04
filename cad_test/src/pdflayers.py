import pymupdf, collections, re, math, time
doc = pymupdf.open('show.pdf')
# 1) find the floor-plan pages: titles in the text
for i in range(doc.page_count):
    t = doc[i].get_text('text')
    m = re.findall(r'(?im)^(.*(?:FLOOR PLAN|FURNITURE PLAN|LAYOUT PLAN|CEILING PLAN|ELEVATION|SECTION).*)$', t)
    scales = sorted(set(re.findall(r'1\s*:\s*\d{2,3}', t)))
    if m or i in (7, 8):
        print(f"page {i+1}: {[s.strip()[:60] for s in m[:3]]} scales={scales[:4]}")
    if i > 40: break
# 2) do drawings carry their layer name?
t0 = time.time()
page = doc[7]
dr = page.get_drawings()
print(f"\npage 8: {len(dr)} paths in {round(time.time()-t0,1)} s; keys of first path: {sorted(dr[0].keys())}")
by_layer = collections.Counter(); length = collections.Counter(); widths = collections.defaultdict(collections.Counter)
def plen(d):
    L = 0.0
    for it in d['items']:
        if it[0] == 'l': L += math.dist(it[1], it[2])
        elif it[0] == 'c': L += math.dist(it[1], it[4])
        elif it[0] == 're': r = it[1]; L += 2 * (r.width + r.height)
        elif it[0] == 'qu': q = it[1]; L += 2 * (math.dist(q.ul, q.ur) + math.dist(q.ul, q.ll))
    return L
for d in dr:
    lay = d.get('layer') or '(none)'
    by_layer[lay] += 1; length[lay] += plen(d)
    widths[lay][round(d.get('width') or 0, 2)] += 1
print("paths per PDF layer on page 8 (top 25):")
for lay, n in by_layer.most_common(25):
    print(f"   {lay[:55]:55} {n:6} paths, {round(length[lay]*25.4/72/10):6} cm of line on paper, widths {dict(widths[lay].most_common(3))}")
