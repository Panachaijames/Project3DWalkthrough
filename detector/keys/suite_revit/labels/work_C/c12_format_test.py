"""Labeller C, step 12: format test of labels/C.json with the existing tools (read-only use): the three_way.py inventory
filter (floor + box) must skip the header, and score.py must accept the openings (scored against themselves)."""
import json, sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', '..', '..', 'tools'))
from score import centre, score
inv = json.load(open(sys.argv[1], encoding='utf-8'))
box = [0, 0, 30, 15]
sel = [dict(o, kind=o['kind'].rstrip('?')) for o in inv if o.get('floor') == 'suite_revit'
       and box[0] <= centre(o)[0] <= box[2] and box[1] <= centre(o)[1] <= box[3]]
print('inventory entries kept by the three_way filter:', len(sel), 'of', len(inv), '(header skipped:', inv[0].get('kind') == 'header', ')')
ops = [dict(o, kind=o['kind'].rstrip('?')) for o in inv[1:]]
rep = score({'openings': ops}, {'openings': ops})
t = rep['total']
print('self-score:', t)
f = rep['floors']['suite_revit']
print('optional found', len(f['optionalFound']), 'of', f['optionalKeys'], '| extras', len(f['extra']))
