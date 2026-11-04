import pymupdf, collections, re
doc = pymupdf.open('show.pdf')
for pno in (9, 10):   # pages 10 and 11 (0-based)
    page = doc[pno]
    dr = page.get_drawings()
    lays = collections.Counter(d.get('layer') or '(none)' for d in dr)
    print(f"\npage {pno+1}: {len(dr)} paths; layers:", [f"{l.split('|')[-1]}:{n}" for l, n in lays.most_common(30)])
    # grid labels: short texts (1-2 chars) - list with positions
    words = page.get_text('words')
    short = [(w[4], round(w[0]), round(w[1])) for w in words if re.fullmatch(r'[A-Z]|[0-9]{1,2}|[A-Z][0-9]', w[4])]
    print("   short labels (grid?):", short[:40])
    dims = [w[4] for w in words if re.fullmatch(r'\d{3,5}', w[4])]
    print("   number words (dimensions?):", dims[:30])
# level texts anywhere in plans/elevations
lv = collections.Counter()
for pno in range(7, 37):
    for w in doc[pno].get_text('words'):
        if re.search(r'(FFL|FL\.|SSL|\+\d+\.\d{2}|±0\.00|\+0\.00)', w[4]): lv[w[4]] += 1
print("\nlevel-like words in pages 8-37:", lv.most_common(30))
