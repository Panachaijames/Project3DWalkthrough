"""Helper for labeller A: load the suite_revit cache (prims.pkl) and give small geometry utilities."""
import os, pickle, math, collections
WORK = 'C:/Users/DWP2/AppData/Local/Temp/claude/1a2f3fc736ce552c/e1e2f8a1-5b17-462a-bbe8-01925d989674/scratchpad/suite_revit_work'
PKL = WORK + '/suite_revit/prims.pkl'

def load():
    with open(PKL, 'rb') as f:
        return pickle.load(f)

def pts(d):
    return d.get('pts') or [q for l in d.get('loops', []) for q in l] or ([d['ins']] if 'ins' in d else [])

def bbox(d):
    P = pts(d)
    xs = [p[0] for p in P]; ys = [p[1] for p in P]
    return (min(xs), min(ys), max(xs), max(ys))

def inbox(d, x0, y0, x1, y1):
    b = bbox(d)
    return not (b[2] < x0 or b[0] > x1 or b[3] < y0 or b[1] > y1)
