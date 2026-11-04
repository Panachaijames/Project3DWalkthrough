"""How many INSERTs does a prims-style walk fail to expand (virtual_entities raising), and what is in model space?
Usage: python expand_probe.py <plan.dxf>"""
import collections, sys, time
from ezdxf import recover
t0 = time.time()
doc, aud = recover.readfile(sys.argv[1])
print(f'read {time.time() - t0:.1f} s')
msp = doc.modelspace()
top = collections.Counter(e.dxftype() for e in msp)
print('model space top level:', sum(top.values()), top.most_common(10))
fails, empty, ok = collections.Counter(), collections.Counter(), 0
errs = collections.Counter()
def walk(e, depth=0):
    global ok
    if e.dxftype() != 'INSERT': return
    nm = e.dxf.get('name', '')
    try:
        V = list(e.virtual_entities())
    except Exception as ex:
        fails[nm[:60]] += 1; errs[type(ex).__name__ + ': ' + str(ex)[:80]] += 1; return
    blk = doc.blocks.get(nm)
    if not V: empty[(nm[:60], 'block has %s entities' % (len(blk) if blk is not None else 'NO DEFINITION'))] += 1
    ok += 1
    if depth < 8:
        for v in V: walk(v, depth + 1)
for e in msp: walk(e)
print('inserts expanded', ok, '| failed', sum(fails.values()), '| expanded to nothing', sum(empty.values()))
print('failed by block:', fails.most_common(10)); print('errors:', errs.most_common(5)); print('empty:', empty.most_common(12))
