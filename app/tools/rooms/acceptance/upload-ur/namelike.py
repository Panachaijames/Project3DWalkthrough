"""UR experiment: name-like texts inside each floor's slab on layers not used as room names (read-only)."""
import collections
import glob
import json
import os
import re
import sys

from shapely.geometry import Point, Polygon
from shapely.ops import unary_union

TAG_RE = re.compile(r'^[A-Z]{1,3}[-.]?\d{1,3}[A-Z]?$', re.I)


def name_like(t):
    return sum(1 for ch in t if ch.isalpha()) >= 2 and not TAG_RE.match(t)


base = os.path.join(os.environ['TEMP'], 'wt-ui', 'acc', 'data', 'projects')
for run in sorted(glob.glob(os.path.join(base, '*', 'builds', '*', 'runs', '*-build'))):
    spec = json.load(open(os.path.join(run, 'spec.json'), encoding='utf-8'))
    s = spec['settings']
    if 'bank' in run and len(sys.argv) > 1: s['layers']['G-ANNO-TEXT'] = 'ignore'
    ov = json.load(open(os.path.join(run, 'out', 'overlay.json'), encoding='utf-8'))
    prep = sorted(glob.glob(os.path.join(os.path.dirname(run), '*-prepare')))
    drawings = {}
    for p in prep:
        for d in glob.glob(os.path.join(p, 'out', 'sources', '*', 'drawing.json')):
            drawings[os.path.basename(os.path.dirname(d))] = json.load(open(d, encoding='utf-8'))
    for fl in ov['floors']:
        slab = unary_union([Polygon(x['o'], x['h']).buffer(0) for x in fl['slabs']])
        dr = drawings.get(fl['source'])
        if dr is None:
            continue
        by = collections.defaultdict(list)
        for t in dr['texts']:
            role = s['layers'].get(t['layer'], 'other')
            if role not in ('ignore', 'other') or t['kind'] == 'ATTRIB' or t.get('block'):
                continue
            txt = t['text'].strip()
            if not name_like(txt) or not slab.contains(Point(t['x'], t['y'])):
                continue
            by[(t['layer'], role)].append(txt)
        hits = {k: v for k, v in by.items() if len(v) >= 3}
        print(run.split('projects')[1][1:].split(os.sep)[0][:20].ljust(20), fl['key'].ljust(7),
              {f'{k[0]}({k[1]})': (len(v), v[:4]) for k, v in hits.items()})
