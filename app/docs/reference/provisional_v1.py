"""Provisional BuiltModel v1 fixtures, written by the architect (3 Nov 2026) for the parallel build phase.

The scaffold runs it once (WORK_BREAKDOWN.md S.8) to make fixtures/models/suite.model.json, house.model.json and
mini.model.json, so builders A, C and D can test against the suite, the house and the furniture harness model before the
seed exists. It is NOT the product's converter: the seed (builder E, walkthrough_api/seed/convert_*.py) implements
DESIGN.md 6.3 and 6.4 itself, and E's pytest compares its output with these files as parsed JSON (deep equality, key order
ignored). A difference goes to docs/contract-issues/E.md and the integration step settles it with the architect.

Usage (system Python 3.14.3, which has jsonschema; never writes outside --out, never writes bytecode):
    python -B docs/reference/provisional_v1.py --prototypes .. --out fixtures/models
Rules: DESIGN.md 6.3 (suite), 6.4 (house), 17.1 (mini). Output: UTF-8, no BOM, json.dumps(ensure_ascii=False,
separators=(',', ':')) + '\\n' (DESIGN.md 9.1). Each file is checked against docs/built-model.schema.json and the 5.6
cross-reference rules in their strict (API) form before it is written; the script exits 1 on any issue."""
import argparse, json, sys
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
r6 = lambda v: round(v, 6)


def suite(root):
    """DESIGN.md 6.3: presidential_test/src/pres2_model.json -> v1."""
    S = json.loads((root / 'presidential_test/src/pres2_model.json').read_text(encoding='utf-8'))
    follow_by_kind = {'wall': True, 'column': True, 'lintel': True, 'glass': True, 'low': False, 'builtin': False,
                      'balustrade': False, 'deck': False, 'post': False, 'slab': False}
    parts = []
    for p in S['parts']:
        q = {'floor': 'suite', 'kind': p['kind'], 'z0': p['z0'], 'z1': p['z1'], 'follow': p.get('follow', follow_by_kind[p['kind']]),
             'o': p['o'], 'h': p['h']}
        if 'label' in p:
            q['label'] = p['label']
        parts.append(q)
    area = lambda a: None if a in (None, '') else float(a)
    openings = []
    for d in S['doors']:
        o = {'id': d['id'], 'floor': 'suite', 'kind': 'door' if d['id'].startswith('D') else 'passage', 'label': d['name'],
             'x': d['x'], 'y': d['y'], 'nx': d['nx'], 'ny': d['ny'], 'width': d['width']}
        if d.get('exterior'):
            o['exterior'] = True
        openings.append(o)
    return {
        'project': 'Presidential suite', 'shortName': 'Presidential suite', 'projectNo': None, 'source': [S['source']],
        'units': 'm', 'offset': S['offset'], 'photoName': 'Presidential', 'maxPrefix': 'PS',
        'floors': [{'key': 'suite', 'name': 'Suite (FL-01)', 'level': S['level'], 'wallHeight': S['floorToFloor'],
                    'slabThickness': S['slabThickness']}],
        'railingHeight': S['balustradeHeight'], 'singleLineHeight': 1.0, 'doorHeadDefault': S['doorHead'],
        'parts': parts,
        'stairs': {'suite': {'below': [], 'above': []}}, 'voids': {'suite': []}, 'closures': {'suite': []},
        'stairOutlines': {'suite': []},
        'rooms': [{'floor': 'suite', 'name': r['name'], 'label': r['label'], 'area': area(r.get('area')), 'x': r['x'], 'y': r['y']}
                  for r in S['rooms']],
        'openings': openings,
        'probes': [{'floor': 'suite', 'id': 'suite-glass-west', 'what': 'glass facade', 'x': S['probe']['glassWestX'],
                    'y': S['probe']['glassWestY'], 'nx': 1.0, 'ny': 0.0, 'inside': [1],
                    'label': "the living room's west glass (its room-side face)"}],
        'colliderSkins': {'suite': []},
        'furnitureKinds': S['furnitureKinds'], 'furniture': S['furniture'],
    }


def house(root):
    """DESIGN.md 6.4: cad_test/src/house3d_merged.json + furniture_house.json -> v1."""
    H = json.loads((root / 'cad_test/src/house3d_merged.json').read_text(encoding='utf-8'))
    FH = json.loads((root / 'cad_test/src/furniture_house.json').read_text(encoding='utf-8'))
    if FH['offset'] != H['centre']:
        raise SystemExit(f"furniture_house.offset {FH['offset']} != house3d_merged.centre {H['centre']}")
    order = [f['key'] for f in FH['floors']]
    names = {f['key']: f['name'] for f in FH['floors']}
    lowest = order[0]
    H0 = {k: r6(H['tops'][k] - H['levels'][k]) for k in order}
    shift = (FH.get('frame') or {}).get('shift') or {}
    parts = []
    for key, rings in H['solids'].items():
        fl, kind = key.split(':')
        z1 = {'wall': H0[fl], 'glass': r6(H0[fl] - 0.6), 'single': 1.0}[kind]
        for r in rings:
            parts.append({'floor': fl, 'kind': kind, 'z0': 0.0, 'z1': z1, 'follow': kind != 'single', 'o': r['o'], 'h': r['h']})
    for fl in order:
        for p in H['pieces'].get(fl, []):
            if p['kind'] == 'lintel' or (p['kind'] == 'pane' and p.get('top')):
                fit, follow = 'top', True
            else:
                fit, follow = 'clip', False
            parts.append({'floor': fl, 'kind': p['kind'], 'z0': p['z0'], 'z1': p['z1'], 'follow': follow, 'o': p['o'], 'h': p['h'],
                          'label': p['id'], 'fit': fit})
    for fl in order:
        thick = H['levels'][fl] if fl == lowest else 0.25
        for r in H['plates'].get(fl, []):
            q = {'floor': fl, 'kind': 'slab', 'z0': r6(-thick), 'z1': 0.0, 'follow': False, 'o': r['o'], 'h': r['h']}
            if fl == lowest:
                q['plinth'] = True
            parts.append(q)
    openings = []
    for fl in order:
        for o in H['openings'].get(fl, []):
            q = {'id': o['id'], 'floor': fl, **{k: v for k, v in o.items() if k not in ('id', 'lintel')},
                 'lintel': 'lintel' if o['lintel'] else None}
            openings.append(q)
    floors = []
    for k in order:
        f = {'key': k, 'name': names[k], 'level': H['levels'][k], 'wallHeight': H0[k],
             'slabThickness': H['levels'][k] if k == lowest else 0.25}
        if shift.get(k):
            f['sheetShift'] = [r6(-shift[k]), 0.0]          # sheet = model + offset + sheetShift (frame: model = sheet + shift - centre)
        floors.append(f)
    flat = lambda segs: [v for s in segs for v in s]
    return {
        'project': 'Test Sukhumvit Residence', 'shortName': 'Sukhumvit house', 'projectNo': None,
        'source': ['Test Sukhumvit Residence.dwg'], 'units': 'm', 'offset': FH['offset'], 'photoName': 'Sukhumvit', 'maxPrefix': 'SK',
        'floors': floors,
        'railingHeight': 1.0, 'singleLineHeight': 1.0, 'doorHeadDefault': H['heights']['defaults'][lowest]['doorHead'],
        'parts': parts,
        'stairs': {k: {'below': [], 'above': [], 'panels': flat(H['stairs'].get(k, []))} for k in order},
        'voids': {k: [] for k in order}, 'closures': {k: [] for k in order}, 'stairOutlines': {k: [] for k in order},
        'rooms': [], 'openings': openings, 'probes': [], 'colliderSkins': {k: [] for k in order},
        'furnitureKinds': FH['furnitureKinds'], 'furniture': FH['furniture'],
    }


def mini(root):
    """DESIGN.md 17.1: furniture/fixtures/mini_model.json -> v1, with the bare scene furniture/fixtures/harness.html draws for a
    model without parts (per floor: a 0.25 m plate over the furniture's extent plus 3 m, and a 0.2 m wall 1 m in from its east
    edge) as parts, and a door record for every id the pieces' approach lists name (the harness has no doors: these records
    only make the approach rule checkable)."""
    M = json.loads((root / 'furniture/fixtures/mini_model.json').read_text(encoding='utf-8'))
    parts = []
    for f in M['floors']:
        x0 = y0 = float('inf'); x1 = y1 = float('-inf')
        for p in M['furniture']:
            if p['floor'] != f['key']:
                continue
            r = (p['w'] + p['d']) / 2
            x0, x1, y0, y1 = min(x0, p['x'] - r), max(x1, p['x'] + r), min(y0, p['y'] - r), max(y1, p['y'] + r)
        if x0 == float('inf'):
            x0, x1, y0, y1 = -2.0, 2.0, -2.0, 2.0
        x0, x1, y0, y1 = r6(x0 - 3), r6(x1 + 3), r6(y0 - 3), r6(y1 + 3)
        parts.append({'floor': f['key'], 'kind': 'wall', 'z0': 0.0, 'z1': f['wallHeight'], 'follow': True,
                      'o': [[r6(x1 - 1.1), y0], [r6(x1 - 0.9), y0], [r6(x1 - 0.9), y1], [r6(x1 - 1.1), y1]], 'h': []})
        parts.append({'floor': f['key'], 'kind': 'slab', 'z0': -0.25, 'z1': 0.0, 'follow': False,
                      'o': [[x0, y0], [x1, y0], [x1, y1], [x0, y1]], 'h': []})
    openings, seen = [], set()
    for p in M['furniture']:
        ids = [a for a in p['approach'] if a not in seen]
        for i, a in enumerate(ids):
            seen.add(a)
            openings.append({'id': a, 'floor': p['floor'], 'kind': 'door', 'x': r6(p['x'] + (i - (len(ids) - 1) / 2) * 1.0),
                             'y': r6(p['y'] - p['d'] / 2 - 0.45), 'nx': 0.0, 'ny': 1.0, 'width': 0.9})
    return {
        'project': M['project'], 'shortName': M['shortName'], 'projectNo': None, 'source': ['furniture/fixtures/mini_model.json'],
        'units': 'm', 'offset': M['offset'], 'photoName': 'Fixture', 'maxPrefix': M['maxPrefix'],
        'floors': [dict(f, slabThickness=0.25) for f in M['floors']],
        'railingHeight': 1.0, 'singleLineHeight': 1.0, 'doorHeadDefault': 2.1,
        'parts': parts, 'stairs': {}, 'voids': {}, 'closures': {}, 'stairOutlines': {},
        'rooms': [], 'openings': openings, 'probes': [], 'colliderSkins': {},
        'furnitureKinds': M['furnitureKinds'], 'furniture': M['furniture'],
    }


def cross_issues(m):
    """The 5.6 cross-reference rules in their strict form (the API refuses on any of them)."""
    out = []
    keys = [f['key'] for f in m['floors']]
    ks = set(keys)
    if len(ks) != len(keys): out.append('/floors: duplicate floor keys')
    if [f['level'] for f in m['floors']] != sorted(f['level'] for f in m['floors']): out.append('/floors: not in level order')
    for i, p in enumerate(m['parts']):
        if p['floor'] not in ks: out.append(f'/parts/{i}/floor: unknown floor {p["floor"]}')
        if not p['z1'] > p['z0']: out.append(f'/parts/{i}/z1: not above z0')
        if p.get('plinth') and p['kind'] != 'slab': out.append(f'/parts/{i}/plinth: only on slabs')
    for name in ('stairs', 'voids', 'closures', 'stairOutlines', 'colliderSkins', 'pictureFrame'):
        for k in (m.get(name) or {}):
            if k not in ks: out.append(f'/{name}/{k}: unknown floor')
    for k, s in m['stairs'].items():
        for a in ('below', 'above', 'panels'):
            if a in s and len(s[a]) % 4: out.append(f'/stairs/{k}/{a}: length {len(s[a])} is not a multiple of 4')
    for coll in ('rooms', 'openings', 'probes'):
        for i, x in enumerate(m[coll]):
            if x['floor'] not in ks: out.append(f'/{coll}/{i}/floor: unknown floor {x["floor"]}')
    ids = [o['id'] for o in m['openings']]
    if len(set(ids)) != len(ids): out.append('/openings: duplicate ids')
    if 'furniture' in m:
        kinds = {k['key'] for k in m['furnitureKinds']}
        fid = [p['id'] for p in m['furniture']]
        if len(set(fid)) != len(fid): out.append('/furniture: duplicate ids')
        for i, p in enumerate(m['furniture']):
            if p['kind'] not in kinds: out.append(f'/furniture/{i}/kind: unknown kind {p["kind"]}')
            if p['floor'] not in ks: out.append(f'/furniture/{i}/floor: unknown floor {p["floor"]}')
            if p['on'] is not None and p['on'] not in set(fid): out.append(f'/furniture/{i}/on: no piece {p["on"]}')
            for j, a in enumerate(p['approach']):
                if a not in set(ids): out.append(f'/furniture/{i}/approach/{j}: no opening {a}')
        n = {}
        for p in m['furniture']: n[p['kind']] = n.get(p['kind'], 0) + 1
        for i, k in enumerate(m['furnitureKinds']):
            if n.get(k['key'], 0) != k['count']: out.append(f'/furnitureKinds/{i}/count: {k["count"]}, pieces {n.get(k["key"], 0)}')
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--prototypes', required=True, type=Path)
    ap.add_argument('--out', required=True, type=Path)
    a = ap.parse_args()
    from jsonschema import Draft202012Validator
    schema = json.loads((HERE.parent / 'built-model.schema.json').read_text(encoding='utf-8'))
    Draft202012Validator.check_schema(schema)
    validator = Draft202012Validator(schema)
    made, bad = {}, 0
    for name, fn in (('suite', suite), ('house', house), ('mini', mini)):
        m = fn(a.prototypes)
        errs = ['/' + '/'.join(map(str, e.absolute_path)) + ': ' + e.message for e in validator.iter_errors(m)] + cross_issues(m)
        for e in errs[:20]:
            print(f'{name}: {e}')
        bad += len(errs)
        made[name] = m
    if bad:
        raise SystemExit(f'{bad} issue(s); nothing written')
    a.out.mkdir(parents=True, exist_ok=True)
    for name, m in made.items():
        (a.out / f'{name}.model.json').write_bytes((json.dumps(m, ensure_ascii=False, separators=(',', ':')) + '\n').encode('utf-8'))
        print(f"{name}.model.json: floors {len(m['floors'])}, parts {len(m['parts'])}, openings {len(m['openings'])}, "
              f"probes {len(m['probes'])}, rooms {len(m['rooms'])}, furniture {len(m.get('furniture') or [])} "
              f"({len(m.get('furnitureKinds') or [])} kinds)")


if __name__ == '__main__':
    main()
