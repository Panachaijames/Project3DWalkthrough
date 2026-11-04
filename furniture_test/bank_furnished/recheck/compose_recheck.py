# Writes the independent check's compact record (recheck_results.json) from the three runs' raw JSON files.
#   python compose_recheck.py <run1 json> <run2 json> <run3 json> <out json>
import json, sys
r1, r2, r3 = (json.load(open(p, encoding='utf-8')) for p in sys.argv[1:4])
C = r1['checks']
BUILDER_INTEL = {  # RESULTS.md, first runs (median of 3 Measures, ms a frame)
    ('orbit', 'A'): 8.9, ('orbit', 'B'): 14.2, ('orbit', 'C5000'): 10.7, ('walkL1', 'A'): 8.3, ('walkL1', 'B'): 9.2, ('walkL1', 'C5000'): 8.3,
    ('widestL1', 'A'): 11.4, ('widestL1', 'B'): 16.1, ('widestL1', 'C5000'): 12.8, ('orbit', 'Pfull'): 15.3, ('orbit', 'P10000'): 14.2,
    ('orbit', 'P5000'): 14.5, ('widestL1', 'Pfull'): 18.4, ('widestL1', 'P10000'): 15.7, ('widestL1', 'P5000'): 14.5,
}
rows = []
for run, src in (('run 1', r1['measure']['rows']), ('run 2', r2['measure2']['rows']), ('run 3', r3['measure']['rows'])):
    for x in src:
        b = BUILDER_INTEL.get((x['view'], x['config']))
        rows.append({'run': run, 'view': x['view'], 'way': x['config'], 'ms': x['ms'], 'msRuns': x['msRuns'], 'builderMs': b,
                     'difference_ms': round(x['ms'] - b, 2) if b is not None else None, 'triangles': x['triangles'], 'calls': x['calls'],
                     'cpuLoad': x['cpuLoad'], 'cpuMax': x['cpuMax'], **({'round': x['round']} if 'round' in x else {})})
counts = {}
for name in ['A', 'B', 'C20000', 'C10000', 'C5000', 'C2500', 'D', 'E', 'Pfull', 'P5000', 'A2']:
    c = C['counts' + name]
    counts[name] = {'rendererInfo': c['info'], 'independent': {k: c['expected'][k] for k in ('triangles', 'calls')}, 'modelTriangles': c['expected']['modelTrianglesAll'],
                    'panel': {k: c['panel'][k] for k in ('modelTris', 'tris', 'calls', 'dl', 'mem')},
                    'allEqual': c['info']['triangles'] == c['expected']['triangles'] == int(c['panel']['tris'].replace(',', '')) and c['info']['calls'] == c['expected']['calls'] == int(c['panel']['calls'].replace(',', ''))}
A = C['boxesA']
boxes = {}
for name in ['B', 'C20000', 'C10000', 'C5000', 'C2500', 'D', 'E', 'Pfull']:
    S = C['boxes' + name]
    hidden = sorted(k for k, v in S.items() if not v['matVisible'])
    untouched = all(S[k]['mat'] == A[k]['mat'] and S[k]['line'] == A[k]['line'] for k in S if k not in hidden)
    same = all(S[k][f] == A[k][f] for k in S for f in ('visible', 'collider', 'pos', 'scale'))
    boxes[name] = {'hidden': len(hidden), 'outlinesHiddenToo': all(not S[k]['lineVisible'] for k in hidden), 'othersUntouched': untouched,
                   'visibleColliderPositionScaleUnchanged': same}
boxes['backInA'] = all(C['boxesA2'][k] == A[k] for k in A)
facing = {k: [{'piece': x['key'], 'turn': x['turn'], 'mirror': x['mirror'], 'off_deg': x['frontOff']} for x in v] for k, v in r2['facing'].items()}
keep = ('model', 'key', 'floor', 'what', 'bottomVsBox_mm', 'height_m', 'insideBox', 'centreFromBox_m', 'inFloorGroup', 'visible', 'front', 'expected', 'frontOff',
        'support', 'screenOverSupport', 'keyboardMouseOverSupport', 'backPad')
placement = [{k: x[k] for k in keep if k in x} for x in C['copiesB']['copies']]
bboxSame = {}
B = {x['key']: x for x in C['copiesB']['copies']}
for name in ['C20000', 'C10000', 'C5000', 'C2500', 'D', 'E']:
    bboxSame[name + '_maxDifferenceFromB_mm'] = round(max(max(abs(a - b) for a, b in zip(x['bbox'], B[x['key']]['bbox'])) for x in C['copies' + name]['copies']) * 1000, 1)
out = {
    'what': 'Independent check of bank_furnished.html (3 Nov 2026): placement of every copy, the boxes, the panel counts, Walk / Ghost / Orbit, and the '
            'Intel Measures re-run (A, B, C 5,000; and P), headless Edge on the Intel chip at 1920 x 1080 inside the shared Edge lock. '
            'Scripts: recheck.mjs (with page_helpers.js), rederive.py, semantic.py, analyse_checks.py, compose_recheck.py.',
    'gpu': C['gpu'], 'canvas_innerW_innerH_dpr_pixelRatio_bufferW_bufferH': C['canvas'],
    'runs': {'run 1': {'at': r1['at'], 'lockWait_s': r1['lockWaitS'], 'cpu': r1['cpu']}, 'run 2': {'at': r2['at'], 'lockWait_s': r2['lockWaitS'], 'cpu': r2['cpu']},
             'run 3': {'at': r3['at'], 'lockWait_s': r3['lockWaitS'], 'cpu': r3['cpu']}},
    'measures': rows, 'counts': counts, 'boxes': boxes, 'slimmedWaysSamePlaceAsFull': bboxSame,
    'placementInB': placement, 'mollieChairFacingInOwnFrame': facing, 'walkGhostOrbit': C['walk'],
    'pageErrors': r1['pageErrors'] + r2['pageErrors'] + r3['pageErrors'],
}
json.dump(out, open(sys.argv[4], 'w', encoding='utf-8'), indent=1, ensure_ascii=False)
print('written', sys.argv[4], len(rows), 'measure rows')
for x in rows:
    print(f"{x['run']:6} {x['view']:9} {x['way']:18} {x['ms']:6.2f} ms  builder {x['builderMs']}  diff {x['difference_ms']}  cpu {x['cpuLoad']} % (max {x['cpuMax']})")
