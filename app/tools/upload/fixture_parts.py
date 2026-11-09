"""The larger parts of make-fixtures.py (scaffold U0): drawing, conversion, result, runs, maxtexts. See make-fixtures.py.

Every provisional fixture here is valid against upload-contracts.ts (the API's check_file and the web type tests) and is
replaced or confirmed by its owner's real code at integration (U1: conversion; U2: drawing, plan; U3: build-result,
replay-input; U4: overlay, max-texts).
"""
from __future__ import annotations

import collections
import hashlib
import io
import json
import math
import pickle
import re
import shutil
import statistics
import subprocess
import tempfile
from pathlib import Path

import fixture_reader as fr
import fixture_settings as fs
from walkthrough_builder import names, roles

APP = Path(__file__).resolve().parents[2]
PROJECT = APP.parent
FX = APP / 'fixtures' / 'upload'
LIBREDWG = APP / 'vendor' / 'libredwg-0.14-win64'
AT = '2026-11-04T00:00:00Z'


def sha1b(b: bytes) -> str:
    return hashlib.sha1(b).hexdigest()


def manifest(ref: Path) -> dict:
    return json.loads((ref / 'manifest.json').read_text(encoding='utf-8'))


def load_json(p: Path):
    return json.loads(p.read_text(encoding='utf-8'))


def walk(ref: Path, name: str) -> dict:
    W = fr.walk_drawing(ref / 'proj' / 'detector' / name / 'plan.dxf')
    votes, leaf = fr.door_votes(W)
    W['leafArcs'] = leaf
    W['votes'] = votes
    return W


def check_against_prims(ref: Path, name: str, W: dict) -> str:
    with open(ref / 'proj' / 'detector' / name / 'prims.pkl', 'rb') as f:
        D = pickle.load(f)
    a = [{k: v for k, v in d.items() if k not in ('k', 'area')} for d in W['items']]
    b = [{k: v for k, v in d.items() if k != 'area'} for d in D['items']]
    same = a == b
    keys_unique = len({d['k'] for d in W['items']}) == len(W['items'])
    return f'{name}: {len(a)} items, equal to prims.py: {same}; keys unique: {keys_unique}'


# ============================================================================================================ drawing
def part_drawing(ref: Path, write, dumps) -> None:
    man = manifest(ref)
    for name in ('bank1', 'sukhumvit'):
        W = walk(ref, name)
        print('  ' + check_against_prims(ref, name, W))
        dim_median = statistics.median(W['dims']) if W['dims'] else None
        units = fr.decide_units(W['insUnits'], W['votes'], dim_median)
        src = {'sha1': man['drawings'][name]['dwgSha1'], 'name': fs.DWGS[name]}
        dr = fr.drawing_read(W, src, units)
        write(f'drawing/{name}.drawing.json', dumps(dr))
        write(f'plan/{name}.plan.json.gz', fr.gz(fr.plan_geometry(W, src['sha1'], units['used'], dr['extents'])))
        print(f'    units {units["used"]} ({units["verdict"]}, votes {units["votes"]}); level tags {len(dr["levelTags"])}, '
              f'grid labels {len(dr["gridLabels"])}, areas {len(dr["areas"])}')


# ========================================================================================================= conversion
DIM = re.compile(r'^DIMENSION_')
TYPE_MAP = {'VERTEX_2D': 'VERTEX', 'VERTEX_3D': 'VERTEX', 'VERTEX_MESH': 'VERTEX', 'VERTEX_PFACE': 'VERTEX',
            'VERTEX_PFACE_FACE': 'VERTEX', 'POLYLINE_2D': 'POLYLINE', 'POLYLINE_3D': 'POLYLINE',
            'POLYLINE_PFACE': 'POLYLINE', 'POLYLINE_MESH': 'POLYLINE', '_3DFACE': '3DFACE', '_3DSOLID': '3DSOLID',
            'TABLE': 'ACAD_TABLE', 'PROXY_ENTITY': 'ACAD_PROXY_ENTITY'}
STRUCT = {'BLOCK', 'ENDBLK', 'SEQEND'}
KEY = re.compile(r'^      "([A-Za-z_]+)": (.*?),?$')


def anon(n: str) -> str:
    return re.sub(r'^(\*[A-Z])\d*$', lambda m: m.group(1), n)


def dwg_side(lines):
    """docs/upload/reference/nothing_lost_stream.py dwg_side, on a stream of lines."""
    objs, cur = [], None
    for line in lines:
        if line.startswith('    {'):
            cur = {}
            objs.append(cur)
            continue
        if cur is None or not line.startswith('      "'):
            continue
        m = KEY.match(line.rstrip('\n'))
        if not m:
            continue
        k, v = m.group(1), m.group(2)
        if k in ('entity', 'object', 'name'):
            try:
                cur[k] = json.loads(v if v.endswith('"') else v + '"')
            except Exception:
                pass
        elif k in ('handle', 'layer', 'ownerhandle'):
            try:
                cur[k] = json.loads(v)[-1]
            except Exception:
                pass
        elif k == 'entmode':
            try:
                cur[k] = int(v)
            except ValueError:
                pass
    layers = {o['handle']: o.get('name', '?') for o in objs if o.get('object') == 'LAYER' and 'handle' in o}
    blocks = {o['handle']: o.get('name', '?') for o in objs if o.get('object') == 'BLOCK_HEADER' and 'handle' in o}
    unknown = sum(1 for o in objs if 'UNKNOWN' in str(o.get('entity') or o.get('object'))
                  or 'PROXY' in str(o.get('entity') or o.get('object')))
    byh = {o.get('handle'): o for o in objs if 'entity' in o}

    def owner(o, depth=0):
        b = blocks.get(o.get('ownerhandle'))
        if b:
            return b
        if o.get('entmode') in (1, 2):
            return {2: '*Model_Space', 1: '*Paper_Space'}[o['entmode']]
        par = byh.get(o.get('ownerhandle'))
        return owner(par, depth + 1) if par is not None and depth < 4 else '?'
    ents = {}
    for o in objs:
        t = o.get('entity')
        if not t or 'handle' not in o:
            continue
        t = 'DIMENSION' if DIM.match(t) else TYPE_MAP.get(t, t)
        if t in STRUCT:
            continue
        ents[o['handle']] = (t, layers.get(o.get('layer'), '?'), anon(owner(o).upper()))
    return ents, set(layers.values()), {anon(b.upper()) for b in blocks.values()}, unknown


def dxf_side(path: Path):
    """nothing_lost_stream.py dxf_side: a raw group-code scan (no ezdxf). Also $ACADVER and $INSUNITS."""
    ents, layers, brec = {}, set(), {}
    section, cur, blk, in102 = None, None, None, False
    header = {}
    hvar = None
    with open(path, encoding='utf-8', errors='replace') as f:
        it = iter(f)
        for code in it:
            code = code.strip()
            val = next(it).rstrip('\r\n')
            if section == 'HEADER':
                if code == '9':
                    hvar = val
                elif hvar in ('$ACADVER', '$INSUNITS') and hvar not in header:
                    header[hvar] = val.strip()
            if code == '0':
                if cur is not None and section in ('ENTITIES', 'BLOCKS') and cur.get('h') is not None:
                    ents[cur['h']] = cur
                cur = None
                if val == 'SECTION':
                    section = 'pending'
                    blk = None
                    continue
                if val == 'ENDSEC':
                    section = None
                    continue
                if section in ('ENTITIES', 'BLOCKS'):
                    cur = {'t': val, 'lay': '0', 'own': None, 'blk': blk}
                elif section == 'TABLES':
                    cur = {'t': val, 'tab': True}
                continue
            if section == 'pending' and code == '2':
                section = val
                continue
            if cur is None:
                continue
            if code == '102':
                in102 = val.startswith('{')
                continue
            if cur.get('tab'):
                if code == '5':
                    cur['h'] = int(val, 16)
                if code == '2':
                    if cur['t'] == 'LAYER':
                        layers.add(val)
                    if cur['t'] == 'BLOCK_RECORD' and 'h' in cur:
                        brec[cur['h']] = val.upper()
                continue
            if code == '5' and 'h' not in cur:
                cur['h'] = int(val, 16)
            elif code == '8':
                cur['lay'] = val
            elif code == '330' and not in102 and cur['own'] is None:
                cur['own'] = int(val, 16)
            elif code == '2' and cur['t'] == 'BLOCK':
                blk = val.upper()
                cur['blk'] = blk
    out = {}
    for h, c in ents.items():
        if c['t'] in STRUCT:
            continue
        k, own = c, None
        for _ in range(4):
            own = brec.get(k['own'])
            if own or k['own'] not in ents:
                break
            k = ents[k['own']]
        own = own or (c['blk'] if c['blk'] else '?')
        out[h] = (c['t'], c['lay'], anon(own.upper()))
    return out, layers, {anon(b) for b in brec.values()}, header


MESSAGE_CLASSES = [
    ('hatch-short-handles', re.compile(r'Skip HATCH common handles')),
    ('handle-not-found', re.compile(r'Object handle not found')),
    ('unstable-class', re.compile(r'Unstable Class')),
    ('unhandled-class', re.compile(r'Unhandled (Class|Object)')),
    ('unknown-flag', re.compile(r'Unknown flag')),
    ('unknown-object', re.compile(r'Unknown object')),
    ('wrong-layer', re.compile(r'Wrong [A-Z_]+\.layer')),
]
ERROR_KIND = re.compile(r'ERROR:\s*([^:0-9]+?)\s*(?::|\d|$)')


def classify(line: str) -> str | None:
    s = line.strip()
    if not s or s.startswith(('Reading DWG', 'Writing DXF')):
        return None
    for name, rx in MESSAGE_CLASSES:
        if rx.search(s):
            return name
    m = ERROR_KIND.search(s)
    if m:
        return 'error:' + m.group(1).strip()
    return 'other'


def conversion_report(ref: Path, name: str) -> dict:
    man = manifest(ref)
    rec = man['drawings'][name]
    dwg = PROJECT / fs.DWGS[name]
    head = dwg.read_bytes()[:6].decode('ascii', 'replace')
    with tempfile.TemporaryDirectory() as t:
        shutil.copyfile(dwg, Path(t) / 'input.dwg')
        with open(Path(t) / 'dwgread.err', 'wb') as err:
            p = subprocess.Popen([str(LIBREDWG / 'dwgread.exe'), '-O', 'JSON', 'input.dwg'], cwd=t,
                                 stdout=subprocess.PIPE, stderr=err, stdin=subprocess.DEVNULL,
                                 creationflags=getattr(subprocess, 'CREATE_NO_WINDOW', 0))
            E1, L1, B1, unknown = dwg_side(io.TextIOWrapper(p.stdout, encoding='utf-8', errors='replace'))
            p.wait()
    dxf = ref / 'proj' / 'detector' / name / 'plan.dxf'
    E2, L2, B2, header = dxf_side(dxf)
    with open(ref / 'proj' / 'detector' / name / 'prims.pkl', 'rb') as f:
        D = pickle.load(f)
    inserted = {'*MODEL_SPACE'} | {d['name'].upper() for d in D['items'] if d['t'] == 'INSERT'}
    missing = [h for h in E1 if h not in E2]
    extra = [h for h in E2 if h not in E1]
    type_changed = [h for h in E1 if h in E2 and E1[h][0] != E2[h][0]]
    layer_changed = [h for h in E1 if h in E2 and E1[h][1] != E2[h][1]]
    owner_changed = [h for h in E1 if h in E2 and E1[h][2] != E2[h][2]]
    lost_in_ms = [h for h in missing if E1[h][2] in inserted]
    # lost blocks: block definitions with fewer entities in the DXF than in the DWG
    by_owner_dwg = collections.Counter(o for _, _, o in E1.values())
    by_owner_dxf = collections.Counter(o for _, _, o in E2.values())
    lost_blocks = []
    for blk, n in sorted(by_owner_dwg.items()):
        if blk.startswith('*MODEL_SPACE') or blk.startswith('*PAPER_SPACE') or by_owner_dxf.get(blk, 0) >= n:
            continue
        miss = [h for h in missing if E1[h][2] == blk]
        if not miss:
            continue
        ins = [d for d in D['items'] if d['t'] == 'INSERT' and d['name'].upper() == blk]
        lost_blocks.append({'name': blk, 'entities': len(miss),
                            'byLayer': dict(sorted(collections.Counter(E1[h][1] for h in miss).items())),
                            'inserts': [{'x': round(d['ins'][0], 3), 'y': round(d['ins'][1], 3), 'layer': d['lay']}
                                        for d in ins[:200]]})
    lay1 = collections.Counter(l for _, l, _ in E1.values())
    lay2 = collections.Counter(l for _, l, _ in E2.values())
    by_layer = [{'layer': la, 'dwg': lay1.get(la, 0), 'dxf': lay2.get(la, 0)}
                for la in sorted(set(lay1) | set(lay2)) if lay1.get(la, 0) != lay2.get(la, 0)]
    # the converter's messages, by class
    msgs = collections.OrderedDict()
    for line in (ref / 'logs' / f'{name}.dwg2dxf.err.txt').read_text(encoding='utf-8', errors='replace').splitlines():
        c = classify(line)
        if c is None:
            continue
        if c not in msgs:
            msgs[c] = {'class': c, 'count': 0, 'example': line.strip().replace('input.dwg', '<drawing>')}
        msgs[c]['count'] += 1
    if lost_in_ms:
        verdict = 'loss'
    elif missing or type_changed or layer_changed or owner_changed:
        verdict = 'minor'
    else:
        verdict = 'ok'
    notes = []
    if verdict == 'loss':
        notes.append(f'{len(missing):,} of {len(E1):,} drawing items did not come through the conversion; '
                     f'{len(lost_in_ms):,} of them belong to the plan or to blocks placed in it. Export a DXF from '
                     f'AutoCAD for a complete build.')
    elif verdict == 'minor':
        notes.append('Nothing is missing; some items changed layer or owner in the conversion.')
    for c, m in msgs.items():
        if (c.startswith('error:') or c in ('unknown-object', 'other')) and verdict != 'loss':
            notes.append(f'the converter reported {m["count"]} message(s) of the class {c}; nothing is missing')
    vman = load_json(APP / 'vendor' / 'libredwg.manifest.json')
    exe = next(f['sha1'] for f in vman['files'] if f['path'] == 'dwg2dxf.exe')
    from ezdxf import recover
    _doc, aud = recover.readfile(str(dxf))
    ins_units = header.get('$INSUNITS')
    return {
        'format': 'conversion-report/1',
        'source': {'sha1': rec['dwgSha1'], 'name': fs.DWGS[name], 'bytes': rec['dwgBytes'], 'kind': 'dwg',
                   'formatVersion': head if head.startswith('AC') else None},
        'converter': {'name': 'libredwg', 'version': '0.14', 'exeSha1': exe},
        'dxf': {'sha1': rec['dxfSha1'], 'bytes': rec['dxfBytes'], 'acadVersion': header.get('$ACADVER'),
                'insUnits': int(ins_units) if ins_units not in (None, '') else None,
                'auditErrors': len(aud.errors), 'auditFixes': len(aud.fixes)},
        'seconds': rec['seconds']['convert'],
        'peakMemoryMB': None,
        'exitCode': 0,
        'messages': list(msgs.values()),
        'totals': {'dwgEntities': len(E1), 'dxfEntities': len(E2), 'missing': len(missing), 'extra': len(extra),
                   'layerChanged': len(layer_changed), 'emptyLayer': sum(1 for _, la, _ in E2.values() if la == '')},
        'byLayer': by_layer,
        'lostBlocks': lost_blocks,
        'renamedBlocks': [],
        'unknownObjects': unknown,
        'verdict': verdict,
        'notes': notes,
    }


def part_conversion(ref: Path, write, dumps) -> None:
    for name in ('bank1', 'presidential'):
        r = conversion_report(ref, name)
        write(f'conversion/{name}.conversion.json', dumps(r))
        print(f'    {name}: verdict {r["verdict"]}, missing {r["totals"]["missing"]} of {r["totals"]["dwgEntities"]}, '
              f'lost blocks {len(r["lostBlocks"])}, messages {[(m["class"], m["count"]) for m in r["messages"]][:6]}')


# ============================================================================================ the bank's build result
def flat(values, n):
    return [list(values[i:i + n]) for i in range(0, len(values), n)]


def quads(values):
    return [[[values[i + 2 * j], values[i + 2 * j + 1]] for j in range(4)] for i in range(0, len(values), 8)]


def bank_parts(ref: Path) -> dict:
    """Everything the bank's fixtures share: the model, stages, summary, settings, detector records, keyed items."""
    man = manifest(ref)
    sha = {n: man['drawings'][n]['dwgSha1'] for n in ('bank1', 'bank2')}
    return {
        'model': load_json(APP / 'fixtures' / 'models' / 'bank-v2.model.json'),
        'stages': load_json(APP / 'fixtures' / 'stages' / 'bank-v2.stages.json'),
        'summary': load_json(PROJECT / 'bank_test' / 'src' / 'bank_summary.json'),
        'settings': load_json(FX / 'settings' / 'bank.json'),
        'records': {'L1': load_json(PROJECT / 'detector' / 'output' / 'bank1_openings.json')['openings'],
                    'L2': load_json(PROJECT / 'detector' / 'output' / 'bank2_openings.json')['openings']},
        'sha': {'L1': sha['bank1'], 'L2': sha['bank2']},
        'ref_name': {'L1': 'bank1', 'L2': 'bank2'},
        'man': man,
    }


def keyed_items(ref: Path, name: str) -> list[dict]:
    return fr.walk_drawing(ref / 'proj' / 'detector' / name / 'plan.dxf')['items']


def placements(B: dict, items_by_floor: dict) -> list[dict]:
    """FurniturePlacements.pieces: each model furniture piece's INSERT found by its block name and top-level handle,
    the nearest insertion point to the box centre (sheet m) winning among copies."""
    ox, oy = B['model']['offset']
    out = []
    for f in B['model']['furniture']:
        cands = [d for d in items_by_floor[f['floor']]
                 if d['t'] == 'INSERT' and d['name'] == f.get('block') and d['h'] == f.get('handle')]
        if not cands:
            cands = [d for d in items_by_floor[f['floor']] if d['t'] == 'INSERT' and d['name'] == f.get('block')]
        c = (f['x'] + ox, f['y'] + oy)
        d = min(cands, key=lambda d: math.dist(d['ins'], c)) if cands else None
        chain = (names.split_path(d['path']) + [d['name']]) if d else []
        out.append({
            'id': f['id'], 'floor': f['floor'], 'source': B['sha'][f['floor']],
            'key': d['k'] if d else None, 'block': d['name'] if d else f.get('block'),
            'family': f.get('family'), 'elementId': names.element_id(chain) if d else None,
            'ins': [round(d['ins'][0], 4), round(d['ins'][1], 4)] if d else None,
            'rot': d['rot'] if d else None, 'sx': d['sx'] if d else None, 'sy': d['sy'] if d else None,
            'insertMirrored': (d['sx'] * d['sy'] < 0) if d else None,
            'drawnVariant': None,
            'boxRot': f['rot'],
        })
    return out


def build_result(ref: Path) -> dict:
    B = bank_parts(ref)
    M, S, SM, ST = B['model'], B['stages'], B['summary'], B['settings']
    ox, oy = M['offset']
    keyed = {fl: keyed_items(ref, B['ref_name'][fl]) for fl in ('L1', 'L2')}
    grid_labels = sorted({d['text'] for d in keyed['L1'] if d['lay'] == 'S-GRID-IDEN' and 'text' in d})
    room_layers = {n for n, r in ST['layers'].items() if r == 'room-name'}
    floors_report = {}
    for fl in ('L1', 'L2'):
        fsum = SM['floors'][fl]
        labels = []
        for text in fsum['notRoomNames']:
            hits = [d for d in keyed[fl] if d.get('text') == text and d['lay'] in room_layers
                    and not any(x['text'] == text and x['at'] == [round(d['ins'][0], 3), round(d['ins'][1], 3)]
                                for x in labels)]
            if hits:
                labels.append({'text': text, 'at': [round(hits[0]['ins'][0], 3), round(hits[0]['ins'][1], 3)]})
        plates = [{'area': p['area'], 'at': [round((p['bbox'][0] + p['bbox'][2]) / 2, 3),
                                             round((p['bbox'][1] + p['bbox'][3]) / 2, 3)]}
                  for p in fsum['plate']['dropped']]
        det = B['man']['drawings'][B['ref_name'][fl]]
        floors_report[fl] = {
            'source': B['sha'][fl], 'area': {'kind': 'wholeFile'}, 'items': fsum['items'], 'itemsNoPoints': 0,
            'subtreesOutside': 0,
            'alignment': ({'method': 'none', 'shift': [0.0, 0.0], 'spread': None, 'labels': [], 'families': 0}
                          if fl == 'L1' else
                          {'method': 'grid', 'shift': [0.0, 0.0], 'spread': fsum['grid']['spread'], 'labels': grid_labels,
                           'families': 2}),
            'singles': [], 'outlineSuggestions': [], 'swingsUnmatched': [], 'railsLeftOut': [],
            'roomLabels': labels, 'platesDropped': plates,
            'detector': {'seconds': det['seconds']['detector'], 'slow': False, 'frameRowsSkipped': None,
                         'records': len(B['records'][fl])},
            'lost': [],
        }
    from_map = {'name': 'name', 'most common': 'drawing', 'default': 'default', 'floor': 'floor'}
    door_heads_from = {o['id']: from_map.get(o.get('headFrom'), 'default') for o in M['openings'] if o['kind'] == 'door'}
    model_ids = {o['id'] for o in M['openings']}
    detector = {fl: [{'record': {**r, 'floor': f'bank-sampeng:{fl}'}, 'modelId': r['id'] if r['id'] in model_ids else None,
                      'fix': None} for r in B['records'][fl]] for fl in ('L1', 'L2')}
    # replay input: the bank's stages regrouped (lines in fours, pieces in quads), and the facts the captions quote
    rfloors = {}
    for fl, f in S['floors'].items():
        rfloors[fl] = {'lines': {c: flat(v, 4) for c, v in f['lines'].items()},
                       'pieces': {c: quads(v) for c, v in f['pieces'].items()},
                       'rings': {c: v for c, v in f['rings'].items()},
                       'sheet': [float(f['sheet'][0]), float(f['sheet'][1])]}
    part_counts = {fl: dict(sorted(collections.Counter(p['kind'] for p in M['parts'] if p['floor'] == fl).items()))
                   for fl in ('L1', 'L2')}
    op_counts = {fl: {k: sum(1 for o in M['openings'] if o['floor'] == fl and o['kind'] == k)
                      for k in ('door', 'window', 'passage')} for fl in ('L1', 'L2')}
    facts = {
        'floors': [{'key': f['key'], 'name': f['name'], 'level': f['level'], 'wallHeight': f['wallHeight'],
                    'source': fs.DWGS[B['ref_name'][f['key']]], 'align': floors_report[f['key']]['alignment']}
                   for f in M['floors']],
        'sources': [{'name': s['name'], 'units': s['units'], 'kind': s['kind']} for s in ST['sources']],
        'exportedFrom': ST['project']['exportedFrom'],
        'counts': {fl: {c: len(v) // 4 for c, v in S['floors'][fl]['lines'].items()} for fl in ('L1', 'L2')},
        'parts': part_counts,
        'openings': op_counts,
        'layersByRole': roles.builder_layers(ST['layers']),
        'liftShaft': any(v.get('what') == 'lift shaft' for vs in M['voids'].values() for v in vs),
        'stairs': sum(SM['floors'][fl]['stairs']['stairs'] for fl in ('L1', 'L2')),
        'furniturePieces': len(M['furniture']),
        'furnitureKinds': len(M['furnitureKinds']),
    }
    secs = {f'detect:{fl}': B['man']['drawings'][B['ref_name'][fl]]['seconds']['detector'] for fl in ('L1', 'L2')}
    secs['build'] = B['man']['bank']['seconds']['build']
    return {
        'model': M,
        'report': {'summary': SM, 'floors': floors_report,
                   'fixes': {'setAside': [], 'openings': [], 'outlineEdges': []}, 'doorHeadsFrom': door_heads_from},
        'replay': {'floors': rfloors, 'facts': facts},
        'detector': detector,
        'placements': placements(B, keyed),
        'floors_frame': {fl: {'source': B['sha'][fl], 'toSheet': [ox, oy], 'area': {'kind': 'wholeFile'}}
                         for fl in ('L1', 'L2')},
        'seconds': secs,
    }


def flag(kind, floor, what, severity, title, detail, at=None, bbox=None, ref=None) -> dict:
    h = hashlib.sha1(json.dumps(what, sort_keys=True).encode()).hexdigest()[:12]
    return {'id': f'{kind}:{floor}:{h}', 'kind': kind, 'floor': floor, 'severity': severity, 'title': title,
            'detail': detail, 'at': at, 'bbox': bbox, 'ref': ref or {}}


def overlay(result: dict) -> dict:
    """BuildOverlay of the bank in each floor's sheet coordinates (model + offset), with the flags of U-12.2 that the
    bank's data raise: openings (passage, confidence <= 0.55, eitherKind, host none / line work, ends from the swing,
    sidelights), room labels, dropped plates."""
    M = result['model']
    ox, oy = M['offset']
    sh = lambda p: [round(p[0] + ox, 4), round(p[1] + oy, 4)]                    # noqa: E731
    floors, flags = [], []
    for fl, frame in result['floors_frame'].items():
        recs = {r['record']['id']: r['record'] for r in result['detector'][fl]}
        parts = [{'i': i, 'kind': p['kind'], 'label': p.get('label'), 'o': [sh(q) for q in p['o']],
                  'h': [[sh(q) for q in hole] for hole in p.get('h', [])]}
                 for i, p in enumerate(M['parts']) if p['floor'] == fl and p['kind'] != 'slab']
        slabs = [{'o': [sh(q) for q in p['o']], 'h': [[sh(q) for q in hole] for hole in p.get('h', [])]}
                 for p in M['parts'] if p['floor'] == fl and p['kind'] == 'slab']
        openings = []
        for o in M['openings']:
            if o['floor'] != fl:
                continue
            r = recs.get(o['id'])
            if r is not None:
                a, b = r['a'], r['b']
            else:
                dx, dy = o['ny'] * o['width'] / 2, -o['nx'] * o['width'] / 2
                a, b = sh((o['x'] - dx, o['y'] - dy)), sh((o['x'] + dx, o['y'] + dy))
            why = []
            if r is not None:
                if r['kind'] == 'passage':
                    why.append('a passage')
                if r['confidence'] <= 0.55:
                    why.append(f'confidence {r["confidence"]}')
                if r.get('eitherKind'):
                    why.append('a door or a window')
                if r['host'] in ('none', 'line work'):
                    why.append(f'host {r["host"]}')
                if any('ends from the swing' in e for e in r.get('evidence', [])):
                    why.append('ends from the swing')
                if r['kind'] == 'door' and r.get('sidelights'):
                    why.append('sidelights')
            openings.append({'id': o['id'], 'kind': o['kind'], 'a': [round(a[0], 4), round(a[1], 4)],
                             'b': [round(b[0], 4), round(b[1], 4)], 'flagged': bool(why), 'fixed': False})
            if why:
                mid = [round((a[0] + b[0]) / 2, 3), round((a[1] + b[1]) / 2, 3)]
                flags.append(flag('opening', fl, o['id'], 'check', f'{o["id"]}: {o["kind"]} to check',
                                  'Check this opening: ' + ', '.join(why) + '.', mid, None, {'openingId': o['id']}))
        furniture = [{'id': f['id'], 'kind': f['kind'], 'x': round(f['x'] + ox, 4), 'y': round(f['y'] + oy, 4),
                      'w': f['w'], 'd': f['d'], 'rot': f['rot']} for f in M['furniture'] if f['floor'] == fl]
        rooms = [{'name': r['name'], 'x': round(r['x'] + ox, 4), 'y': round(r['y'] + oy, 4)}
                 for r in M['rooms'] if r['floor'] == fl]
        rep = result['report']['floors'][fl]
        for lab in rep['roomLabels']:
            flags.append(flag('room-label', fl, lab, 'info', f'"{lab["text"]}" is not a room name',
                              'A text on a room-name layer that names no room (a tag or a code): left out of the rooms.',
                              lab['at']))
        for p in rep['platesDropped']:
            flags.append(flag('plate-dropped', fl, p, 'info', 'A floor area was left out',
                              f'An area of {p["area"]} m2 inside a railing was left out of the floor plate.', p['at']))
        floors.append({'key': fl, 'source': frame['source'], 'toSheet': frame['toSheet'], 'area': frame['area'],
                       'parts': parts, 'slabs': slabs, 'openings': openings, 'furniture': furniture, 'rooms': rooms,
                       'setAside': []})
    return {'format': 'build-overlay/1', 'floors': floors, 'flags': flags}


def part_result(ref: Path, write, dumps) -> None:
    res = build_result(ref)
    write('build-result.bank.json', dumps(res, pretty=False))             # compact: 3 MB pretty
    write('replay-input.bank.json', dumps(res['replay'], pretty=False))
    write('overlay/bank.overlay.json', dumps(overlay(res)))
    print(f'    placements: {len(res["placements"])} pieces, {sum(1 for p in res["placements"] if p["key"])} with a key, '
          f'{sum(1 for p in res["placements"] if p["insertMirrored"])} mirrored inserts')


# ================================================================================================ the FakeJobRunner's runs
def presentation(model: dict, settings: dict) -> dict:
    """U-11.2's presentation for an uploaded version (text runs, the fitSlabs camera)."""
    doors = sum(1 for o in model['openings'] if o['kind'] == 'door')
    windows = sum(1 for o in model['openings'] if o['kind'] == 'window')
    passages = sum(1 for o in model['openings'] if o['kind'] == 'passage')
    files = ' and '.join(s['name'] for s in settings['sources'])
    xs = [q[0] for p in model['parts'] if p['kind'] == 'slab' for q in p['o']]
    ys = [q[1] for p in model['parts'] if p['kind'] == 'slab' for q in p['o']]
    d = max(20.0, math.hypot(max(xs) - min(xs), max(ys) - min(ys)))
    levels = ' and '.join(f'{f["level"]:.2f}' for f in model['floors'])
    kinds = {p['kind'] for p in model['parts']}
    legend = [(('wall', 'column', 'lintel', 'sill', 'parapet'), '#e3ddd3', 'Walls and lintels'),
              (('glass',), '#9cc3d5', 'Glass'), (('mullion',), '#5d6b74', 'Glass frames'),
              (('railing',), '#6f6a75', 'Railings'), (('step',), '#b9c7b4', 'Stairs'),
              (('single',), '#e0a458', 'Single-line items'), (('slab',), '#d4d8d2', 'Floor plates')]
    return {
        'documentTitle': settings['project']['shortName'],
        'heading': settings['project']['name'],
        'intro': [{'text': f'Built from {len(settings["sources"])} drawing(s) ({files}): walls from the wall layers, glass '
                           f'from the glass layers, and {doors} doors, {windows} windows and {passages} passages from '
                           f'the openings detector. {len(model["furniture"])} furniture boxes in '
                           f'{len(model["furnitureKinds"])} kinds. Levels {levels} m. No AI used.'}],
        'accent': '#2f6f8f',
        'legend': {'layout': 'inline', 'items': [{'colour': c, 'text': t} for ks, c, t in legend if kinds & set(ks)]},
        'floorButtons': {'all': 'Both floors'},
        'camera': {'kind': 'fitSlabs', 'away': [round(0.52 * d, 3), round(0.53 * d, 3), round(0.63 * d, 3)],
                   'targetY': 2.5, 'panForPanel': True, 'far': round(max(600.0, 6 * d), 3)},
        'groundPlane': None,
    }


def job_record(kind: str, run_id: str, steps: list[tuple[str, str, float]], outputs: dict) -> dict:
    return {'format': 'job/1', 'kind': kind, 'runId': run_id, 'status': 'done', 'pid': None, 'procStart': None,
            'queuedAt': AT, 'startedAt': AT, 'finishedAt': AT, 'step': steps[-1][0], 'progress': 1.0,
            'steps': [{'name': n, 'label': lab, 'status': 'done', 'seconds': round(s, 2), 'note': ''} for n, lab, s in steps],
            'messages': [{'at': AT, 'level': 'info', 'text': f'{lab}: done'} for _, lab, _ in steps][-200:],
            'error': None, 'outputs': outputs}


def part_runs(ref: Path, write, dumps) -> None:
    """runs/<name>/run.json lists each output of the run: {"fixture": <path under app/>} (copied as it is),
    {"prototype": <path under the project folder>} or {"file": <path under the run folder>}; job.json is the JobRecord
    a FakeJobRunner writes when the run is done (its outputs' sizes and sha1s match those files)."""
    man = manifest(ref)
    B = bank_parts(ref)
    ST = B['settings']
    # ---- prepare: per source conversion, drawing and plan; suggestions; the proposed settings
    sources = {}
    for fl, name in B['ref_name'].items():
        sha = B['sha'][fl]
        if name == 'bank1':
            sources[f'sources/{sha}/conversion.json'] = {'fixture': 'fixtures/upload/conversion/bank1.conversion.json'}
            sources[f'sources/{sha}/drawing.json'] = {'fixture': 'fixtures/upload/drawing/bank1.drawing.json'}
            sources[f'sources/{sha}/plan.json.gz'] = {'fixture': 'fixtures/upload/plan/bank1.plan.json.gz'}
        else:
            W = walk(ref, name)
            units = fr.decide_units(W['insUnits'], W['votes'], statistics.median(W['dims']) if W['dims'] else None)
            dr = fr.drawing_read(W, {'sha1': sha, 'name': fs.DWGS[name]}, units)
            write(f'runs/bank-prepare/out/sources/{sha}/drawing.json', dumps(dr))
            write(f'runs/bank-prepare/out/sources/{sha}/plan.json.gz',
                  fr.gz(fr.plan_geometry(W, sha, units['used'], dr['extents'])))
            write(f'runs/bank-prepare/out/sources/{sha}/conversion.json', dumps(conversion_report(ref, name)))
            for f in ('conversion.json', 'drawing.json', 'plan.json.gz'):
                sources[f'sources/{sha}/{f}'] = {'file': f'out/sources/{sha}/{f}'}
    suggestions = {'format': 'layer-suggestions/1', 'office': None,
                   'layers': {n: {'role': r, 'from': 'name' if r != 'other' else 'default',
                                  'evidence': [f'provisional fixture: {n} is {r} in bank_project.json']}
                              for n, r in ST['layers'].items()}}
    write('runs/bank-prepare/out/suggestions.json', dumps(suggestions))
    proposed = json.loads(json.dumps(ST))
    proposed['furniture']['words'] = {}
    for f in proposed['floors']:
        f['level'] = 0.0 if f['key'] == 'L1' else 3.0
        f['wallHeight'] = 3.0
    write('runs/bank-prepare/out/proposed-settings.json', dumps(proposed))
    prep_out = {**sources, 'suggestions.json': {'file': 'out/suggestions.json'},
                'proposed-settings.json': {'file': 'out/proposed-settings.json'}}
    steps = []
    for i, (fl, name) in enumerate(B['ref_name'].items()):
        sec = man['drawings'][name]['seconds']
        steps += [(f'convert:{i}', f'Converting {fs.DWGS[name]}', sec['convert']),
                  (f'check:{i}', f'Checking {fs.DWGS[name]}', 1.0), (f'read:{i}', f'Reading {fs.DWGS[name]}', sec['prims'])]
    steps.append(('suggest', 'Suggesting layer roles', 0.5))
    finish_run(write, dumps, 'bank-prepare', 'prepare', '0001-prepare', steps, prep_out)
    # ---- build
    res = load_json(FX / 'build-result.bank.json')
    M = res['model']
    report = res['report']
    openings = {'format': 'openings/1', 'floors': {fl: recs for fl, recs in res['detector'].items()}}
    pieces = {'format': 'furniture-placements/1', 'pieces': res['placements']}
    empty_diff = {'counts': {fl: {} for fl in ('L1', 'L2')}, 'partsAdded': [], 'partsRemoved': [], 'openingsAdded': [],
                  'openingsRemoved': [], 'openingsChanged': [], 'furnitureByKind': {}, 'roomsAdded': [], 'roomsRemoved': []}
    diff = {'format': 'build-diff/1', 'against': [{'kind': 'version', 'ref': 'v2', 'diff': empty_diff}]}
    vman = load_json(APP / 'vendor' / 'libredwg.manifest.json')
    inputs = {'format': 'version-inputs/1', 'buildId': '20261104T000000-000000', 'runId': '0002-build',
              'settingsRevision': 2, 'builtAt': AT,
              'sources': [{'sha1': B['sha'][fl], 'name': fs.DWGS[n], 'bytes': man['drawings'][n]['dwgBytes'], 'kind': 'dwg',
                           'units': 'mm', 'verdict': 'ok', 'dxfSha1': man['drawings'][n]['dxfSha1']}
                          for fl, n in B['ref_name'].items()],
              'converter': {'name': 'libredwg', 'version': '0.14',
                            'exeSha1': next(f['sha1'] for f in vman['files'] if f['path'] == 'dwg2dxf.exe')},
              'builder': {'version': '1', 'python': '3.14.3',
                          'packages': {'ezdxf': '1.4.4', 'shapely': '2.1.2', 'numpy': '2.4.4', 'matplotlib': '3.11.2',
                                       'pillow': '12.2.0'},
                          'vendor': {f['path']: f['sha1'] for f in load_json(APP / 'services' / 'builder' /
                                                                             'walkthrough_builder' / 'vendor' / 'VENDOR.json')['files']}},
              'seconds': res['seconds']}
    write('runs/bank-build/out/presentation.json', dumps(presentation(M, B['settings'])))
    write('runs/bank-build/out/report.json', dumps(report))
    write('runs/bank-build/out/diff.json', dumps(diff))
    write('runs/bank-build/out/openings.json', dumps(openings))
    write('runs/bank-build/out/pieces.json', dumps(pieces))
    write('runs/bank-build/out/inputs.json', dumps(inputs))
    build_out = {
        'model.json': {'fixture': 'fixtures/models/bank-v2.model.json'},
        'stages.json': {'fixture': 'fixtures/stages/bank-v2.stages.json'},
        'presentation.json': {'file': 'out/presentation.json'},
        'report.json': {'file': 'out/report.json'},
        'overlay.json': {'fixture': 'fixtures/upload/overlay/bank.overlay.json'},
        'diff.json': {'file': 'out/diff.json'},
        'openings.json': {'file': 'out/openings.json'},
        'pieces.json': {'file': 'out/pieces.json'},
        'topview.png': {'prototype': 'bank_test/src/bank_topview.png'},
        'Bangkok_Bank_Sampeng.ms': {'prototype': 'bank_test/Bangkok_Bank_Sampeng.ms'},
        'inputs.json': {'file': 'out/inputs.json'},
    }
    steps = [('ensure', 'Checking the readings', 0.1), ('align', 'Lining up the floors', 0.1),
             ('detect:L1', 'Finding doors and windows on Level 1', res['seconds']['detect:L1']),
             ('detect:L2', 'Finding doors and windows on Level 2', res['seconds']['detect:L2']),
             ('walls', 'Building walls and glass', 2.0), ('openings', 'Cutting the openings', 2.0),
             ('furniture', 'Placing the furniture boxes', 1.0), ('outputs', 'Writing the outputs', 2.0),
             ('validate', 'Checking the outputs', 0.5)]
    finish_run(write, dumps, 'bank-build', 'build', '0002-build', steps, build_out)


def finish_run(write, dumps, folder: str, kind: str, run_id: str, steps, outs: dict) -> None:
    outputs = {}
    for name, src in outs.items():
        if 'fixture' in src:
            p = APP / src['fixture']
        elif 'prototype' in src:
            p = PROJECT / src['prototype']
        else:
            p = FX / 'runs' / folder / src['file']
        data = p.read_bytes()
        outputs[name] = {'bytes': len(data), 'sha1': sha1b(data)}
    write(f'runs/{folder}/run.json', dumps({'format': 'fake-run/1', 'kind': kind, 'runId': run_id, 'outputs': outs}))
    write(f'runs/{folder}/job.json', dumps(job_record(kind, run_id, steps, outputs)))


# ============================================================================================== provisional MaxTexts
def header_lines(ms: Path) -> list[str]:
    lines = ms.read_bytes().decode('utf-8').split('\r\n')
    out = []
    for line in lines:
        if not line.startswith('--'):
            break
        out.append(line)
    return out


def grep(ms: Path, pattern: str) -> list[str]:
    rx = re.compile(pattern)
    return [line for line in ms.read_bytes().decode('utf-8').split('\r\n') if rx.search(line)]


def part_maxtexts(ref: Path, write, dumps) -> None:
    del ref
    for key, ms, pictures in (('bank-27oct', PROJECT / 'bank_test' / 'Bangkok_Bank_Sampeng.ms', False),
                              ('hotel-2nov', PROJECT / 'hotel_test' / 'Hotel_Lobby.ms', True)):
        tip = grep(ms, r'checkbox dwg .*tooltip:')
        source = grep(ms, r'setUserProp origin "Source"')
        rollout = grep(ms, r'^rollout ')
        write(f'max-texts/{key}.json', dumps({
            'format': 'max-texts/1', 'profile': key,
            '_provisional': 'Scaffold U0: the verbatim lines read from the prototype script (header = its leading '
                            'comment block). U4 owns this file and makes it reproduce the script byte for byte '
                            '(placeholders, the computed follow / keep, stair and door sentences, U-11.5).',
            'header': header_lines(ms),
            'tooltip': re.search(r'tooltip:"([^"]*)"', tip[0]).group(1) if tip else '',
            'placedAt': [line for line in header_lines(ms) if 'Placed at' in line or 'if you untick' in line],
            'datumSource': re.search(r'"Source" "([^"]*)"', source[0]).group(1) if source else '',
            'datumExtra': [],
            'titleSuffix': ' (test)',
            'builtBy': 'the CAD-to-3D test pipeline',
            'page': '',
            'rolloutSuffix': ' (test)' if rollout and '(test)' in rollout[0] else '',
            'notes': [],
            'pictures': pictures,
        }))
    write('max-texts/upload.json', dumps({
        'format': 'max-texts/1', 'profile': 'upload',
        '_provisional': 'Scaffold U0: the upload profile of U-11.5 in outline; U4 owns this file and writes its lines.',
        'header': ['-- __PROJECT__ / from "__FILES__" / built by the walkthrough app, __DATE__',
                   '-- Model data __STAMP__. Floor levels __LEVELS__ m, wall heights __HEIGHTS__ m.',
                   '-- Converted with LibreDWG 0.14; drawing units __UNITS__.'],
        'tooltip': 'Untick to centre the model on the origin',
        'placedAt': ["-- Placed at the drawing's own coordinates in metres, or centred on the origin",
                     "-- if you untick that box in the script's window."],
        'datumSource': '__FILES__, converted with LibreDWG; drawing units __UNITS__, model in metres',
        'datumExtra': [], 'titleSuffix': '', 'builtBy': 'the walkthrough app', 'page': 'the walkthrough app',
        'rolloutSuffix': '', 'notes': [], 'pictures': False,
    }))
