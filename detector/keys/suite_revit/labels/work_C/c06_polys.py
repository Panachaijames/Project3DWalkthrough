"""Labeller C, step 6: exact vertices of selected fills (by handle) and of every non-rectangular wall fill."""
import pickle, sys
P = 'C:/Users/DWP2/AppData/Local/Temp/claude/1a2f3fc736ce552c/e1e2f8a1-5b17-462a-bbe8-01925d989674/scratchpad/suite_revit_work/suite_revit/prims.pkl'
D = pickle.load(open(P, 'rb'))
want = set(sys.argv[1:])
for d in D['items']:
    if d['t'] == 'HATCH' and d['lay'] in ('0', 'A-WALL', 'S-COLS') and (not want or d['h'] in want):
        for lp in d['loops']:
            print(d['lay'], d['h'], ' '.join(f'({x:.4f},{y:.4f})' for x, y in lp))
