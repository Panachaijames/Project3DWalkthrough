"""The slimming judge, step 4: what the proposed spec would make of the whole bank (3 Nov 2026).

    python spec_totals.py <project folder> <judge folder>

Reads furniture_test/bank_families_for_3d_team.csv (the bank's 54 families, 185 pieces) and <judge>/levels.json, sorts every
family into a spec class by its kind and name, and adds up the triangles of the bank's furniture at the spec: each piece at its
class's budget (an upper bound: a model already below its budget stays as it is), and for the 8 families whose models came on
3 Nov at what the spec makes of them (kept as they are when below the budget). Prints a table and writes
<judge>/spec_totals.json.
"""
import csv
import json
import sys
from pathlib import Path

PROJECT, JUDGE = Path(sys.argv[1]), Path(sys.argv[2])
rows = list(csv.DictReader((PROJECT / 'furniture_test' / 'bank_families_for_3d_team.csv').open(encoding='utf-8-sig')))
levels = {m['key']: m for m in json.loads((JUDGE / 'levels.json').read_text(encoding='utf-8'))['models']}

# the spec: triangles per piece (far: every piece; near: the close-up copy for the pieces within 2 m); see JUDGE.md
SPEC = {
    'chair':      {'far': 5000, 'near': 10000},
    'stool':      {'far': 3000, 'near': 6000},
    'sofa':       {'far': 5000, 'near': 10000},
    'table':      {'far': 2000, 'near': 4000},
    'electronics': {'far': 2500, 'near': 5000},
    # not measured: by likeness to the measured classes
    'cabinet':    {'far': 2000, 'near': 4000},
    'plant':      {'far': 5000, 'near': 10000},
    'sanitary':   {'far': 2500, 'near': 5000},
    'screen':     {'far': 500, 'near': 1000},
    'kiosk':      {'far': 5000, 'near': 10000},
}
MEASURED = {'chair', 'stool', 'sofa', 'table', 'electronics'}


def spec_class(kind, family):
    f = family.upper()
    if kind == 'Chair / stool':
        if 'BENCH' in f:
            return 'sofa'
        if 'STOOL' in f and 'CHAIR_STOOL' in f:
            return 'stool'
        return 'chair'
    return {
        'Sofa / armchair': 'sofa', 'Table / desk': 'table', 'Coffee / side table': 'table', 'Cabinet / casework': 'cabinet',
        'Tall cabinet / wardrobe': 'cabinet', 'Computer / monitor': 'electronics', 'Telephone': 'electronics',
        'Printer / copier': 'electronics', 'Plant': 'plant', 'Sanitary fitting': 'sanitary', 'Privacy screen / panel': 'screen',
        'TV / wall screen': 'screen', 'ATM / kiosk': 'kiosk',
    }[kind]


# the 3 Nov models by family: (judge key, the level the spec keeps, its triangles), from levels.json
MODEL_OF = {
    'mollie_chair_a685_revit - A685 2': 'visitor_chair01',
    'CHAIR_STOOL LOW_VITRA_VISIONA STOOL - 500W GRAY': 'visitor_chair02',
    'Enscape AssetDefinition - Computer 003 - Enscape AssetDefinition - Computer 003': 'monitor',
    'SOFA_BENCH_DIOR - TYPE 2': 'banquet',
    'CHAIR_BENCH BACK - SE107 STOOL LOW_VITRA_VISIONA STOOL': 'sofa',
    'CHAIR_STOOL LOW_VITRA_VISIONA STOOL - SE104 400W BLUE': 'stool',
    'TABLE_BEDSIDE_VITRA_OCCASIONAL - TA104 600W 400H': 'side_table',
    'IA_J15_WORKING TABLE - 1800W 1000D 750H': 'working_table',
}


def kept(key, budget):
    """The triangles the spec keeps of a model: as it is when at or below the budget, else its largest level at or below it."""
    m = levels[key]
    full = m['full']['triangles']
    if full <= budget:
        return full, 'as it is'
    fit = [l for l in m['levels'] if l['triangles'] <= budget * 1.05]   # the level made nearest the number (at most 5 % over)
    best = max(fit, key=lambda l: l['triangles'])
    return best['triangles'], f"slimmed to {best['label']}"


out, by_class = [], {}
for r in rows:
    n = int(r['pieces in the bank'])
    fam, kind = r['family (as in the CAD)'], r['kind']
    c = spec_class(kind, fam)
    far = SPEC[c]['far']
    row = {'family': fam, 'kind': kind, 'class': c, 'pieces': n, 'budgetEach': far, 'atBudget': n * far}
    key = MODEL_OF.get(fam)
    if key:
        each, how = kept(key, far)
        if fam == 'SOFA_BENCH_DIOR - TYPE 2':       # the banquet: one 3 m bench for the run of four modules (analysis.json)
            row.update(model=key, fullEach=levels[key]['full']['triangles'], keptEach=each, keptHow=how, copies=1, fullDetail=levels[key]['full']['triangles'], atSpec=each)
        else:
            row.update(model=key, fullEach=levels[key]['full']['triangles'], keptEach=each, keptHow=how, copies=n, fullDetail=n * levels[key]['full']['triangles'], atSpec=n * each)
    out.append(row)
    b = by_class.setdefault(c, {'class': c, 'measured': c in MEASURED, 'families': 0, 'pieces': 0, 'atBudget': 0})
    b['families'] += 1; b['pieces'] += n; b['atBudget'] += n * far

with_models = [r for r in out if 'model' in r]
tot = {
    'pieces': sum(r['pieces'] for r in out), 'families': len(out),
    'allAtBudget': sum(r['atBudget'] for r in out),
    'eightFamilies': {'pieces': sum(r['pieces'] for r in with_models), 'fullDetail': sum(r['fullDetail'] for r in with_models), 'atSpec': sum(r['atSpec'] for r in with_models)},
}
tot['eightAtSpecPlusRestAtBudget'] = tot['eightFamilies']['atSpec'] + sum(r['atBudget'] for r in out if 'model' not in r)
# close-up copies: the most extra triangles the pieces within 2 m of one standing place would add at their near numbers
# (a 0.5 m grid over each level; the pieces from bank_model.json, their class from their family as above)
import math
bank = json.loads((PROJECT / 'bank_test' / 'src' / 'bank_model.json').read_text(encoding='utf-8'))
KIND_LABEL = {'seat': 'Chair / stool', 'sofa': 'Sofa / armchair', 'table': 'Table / desk', 'coffee-table': 'Coffee / side table',
              'cabinet': 'Cabinet / casework', 'tall-cabinet': 'Tall cabinet / wardrobe', 'computer': 'Computer / monitor',
              'phone': 'Telephone', 'printer': 'Printer / copier', 'plant': 'Plant', 'sanitary': 'Sanitary fitting',
              'partition': 'Privacy screen / panel', 'tv': 'TV / wall screen', 'atm': 'ATM / kiosk'}
extra = lambda q: SPEC[spec_class(KIND_LABEL[q['kind']], q.get('family') or '')]['near'] - SPEC[spec_class(KIND_LABEL[q['kind']], q.get('family') or '')]['far']
worst = {'pieces': 0, 'extraTriangles': 0, 'at': None}
for fl in sorted({q['floor'] for q in bank['furniture']}):
    G = [q for q in bank['furniture'] if q['floor'] == fl]
    x0, x1 = min(q['x'] for q in G), max(q['x'] for q in G)
    y0, y1 = min(q['y'] for q in G), max(q['y'] for q in G)
    for i in range(int((x1 - x0) / 0.5) + 1):
        for j in range(int((y1 - y0) / 0.5) + 1):
            x, y = x0 + 0.5 * i, y0 + 0.5 * j
            near = [q for q in G if math.hypot(q['x'] - x, q['y'] - y) <= 2.0]
            e = sum(extra(q) for q in near)
            if e > worst['extraTriangles']:
                worst = {'pieces': len(near), 'extraTriangles': e, 'at': [fl, round(x, 1), round(y, 1)]}
tot['closeUpCopiesWorstPlace'] = worst
tot['worstCase'] = tot['allAtBudget'] + worst['extraTriangles']
for c in sorted(by_class.values(), key=lambda b: -b['atBudget']):
    print(f"{c['class']:12} {'measured' if c['measured'] else 'by likeness':12} {c['families']:3} families {c['pieces']:4} pieces  {c['atBudget']:>9,} triangles at the budget")
print(json.dumps(tot, indent=1))
for r in with_models:
    print(f"  {r['model']:16} {r['pieces']:3} pieces x {r['fullEach']:>7,} = {r['fullDetail']:>9,} full; {r['keptHow']:22} {r['keptEach']:>6,} each -> {r['atSpec']:>8,}")
(JUDGE / 'spec_totals.json').write_text(json.dumps({'spec': SPEC, 'classes': list(by_class.values()), 'totals': tot, 'families': out}, indent=1, ensure_ascii=False), encoding='utf-8')
print('wrote', JUDGE / 'spec_totals.json')
