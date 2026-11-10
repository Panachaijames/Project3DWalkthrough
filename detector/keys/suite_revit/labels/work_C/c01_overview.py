"""Labeller C, step 1: overview of the cache (prims.pkl): inserts, door-layer entities, all swing-like arcs on any layer."""
import pickle, math, collections, sys, os
P = 'C:/Users/DWP2/AppData/Local/Temp/claude/1a2f3fc736ce552c/e1e2f8a1-5b17-462a-bbe8-01925d989674/scratchpad/suite_revit_work/suite_revit/prims.pkl'
D = pickle.load(open(P, 'rb'))
items = D['items']
print('items', len(items))
c = collections.Counter((d['lay'], d['t']) for d in items)
for (l, t), n in sorted(c.items()): print(f'  {l:20} {t:12} {n}')
print('\nINSERTS')
for d in items:
    if d['t'] == 'INSERT':
        print(f"  {d['lay']:14} {d['name'][:90]:90} ins ({d['ins'][0]:.4f},{d['ins'][1]:.4f}) rot {d['rot']} s {d['sx']},{d['sy']} h {d['h']}")
