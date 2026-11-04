"""Streaming 'nothing lost' check (constant memory): dwgread -O JSON (the DWG as decoded) against the DXF dwg2dxf wrote.

Usage: python nothing_lost_stream.py <dwgread.json> <plan.dxf>
DWG side: line scan of dwgread's pretty-printed JSON (top-level object keys sit at 6 spaces).
DXF side: raw group-code scan (no ezdxf), sections TABLES (LAYER, BLOCK_RECORD), BLOCKS and ENTITIES.
Per handle: type, layer, owner block. Prints counts and every difference class.
"""
import collections, json, re, sys, time

DIM = re.compile(r'^DIMENSION_')
MAP = {'VERTEX_2D': 'VERTEX', 'VERTEX_3D': 'VERTEX', 'VERTEX_MESH': 'VERTEX', 'VERTEX_PFACE': 'VERTEX', 'VERTEX_PFACE_FACE': 'VERTEX',
       'POLYLINE_2D': 'POLYLINE', 'POLYLINE_3D': 'POLYLINE', 'POLYLINE_PFACE': 'POLYLINE', 'POLYLINE_MESH': 'POLYLINE',
       '_3DFACE': '3DFACE', '_3DSOLID': '3DSOLID', 'TABLE': 'ACAD_TABLE', 'PROXY_ENTITY': 'ACAD_PROXY_ENTITY'}
STRUCT = {'BLOCK', 'ENDBLK', 'SEQEND'}
def anon(n): return re.sub(r'^(\*[A-Z])\d*$', lambda m: m.group(1), n)   # DWG keeps *D / *U / *X unnumbered; DXF numbers them


KEY = re.compile(r'^      "([A-Za-z_]+)": (.*?),?$')


def dwg_side(path):
    objs, cur = [], None
    with open(path, encoding='utf-8', errors='replace') as f:
        for line in f:
            if line.startswith('    {'):
                cur = {}; objs.append(cur); continue
            if cur is None or not line.startswith('      "'): continue
            m = KEY.match(line.rstrip('\n'))
            if not m: continue
            k, v = m.group(1), m.group(2)
            if k in ('entity', 'object', 'name'):
                if v.endswith('"'): cur[k] = json.loads(v)
                elif v.startswith('"'): cur[k] = json.loads(v + '"') if not v.endswith('"') else json.loads(v)
            elif k in ('handle', 'layer', 'ownerhandle'):
                try: cur[k] = json.loads(v)[-1]
                except Exception: pass
            elif k == 'entmode':
                cur[k] = int(v)
    layers = {o['handle']: o.get('name', '?') for o in objs if o.get('object') == 'LAYER'}
    blocks = {o['handle']: o.get('name', '?') for o in objs if o.get('object') == 'BLOCK_HEADER'}
    unknown = collections.Counter(o.get('entity') or o.get('object') for o in objs
                                  if 'UNKNOWN' in str(o.get('entity') or o.get('object')) or 'PROXY' in str(o.get('entity') or o.get('object')))
    byh = {o.get('handle'): o for o in objs if 'entity' in o}
    def owner(o, depth=0):
        b = blocks.get(o.get('ownerhandle'))
        if b: return b
        if o.get('entmode') in (1, 2): return {2: '*Model_Space', 1: '*Paper_Space'}[o['entmode']]
        par = byh.get(o.get('ownerhandle'))                  # VERTEX -> POLYLINE, ATTRIB -> INSERT
        return owner(par, depth + 1) if par is not None and depth < 4 else '?'
    ents, struct = {}, collections.Counter()
    for o in objs:
        t = o.get('entity')
        if not t: continue
        t = 'DIMENSION' if DIM.match(t) else MAP.get(t, t)
        if t in STRUCT: struct[t] += 1; continue
        ents[o['handle']] = (t, layers.get(o.get('layer'), '?'), anon(owner(o).upper()))
    return ents, set(layers.values()), set(b.upper() for b in blocks.values()), struct, len(objs), unknown


def dxf_side(path):
    ents, layers, brec = {}, set(), {}
    section, cur, blk, in102 = None, None, None, False
    with open(path, encoding='utf-8', errors='replace') as f:
        it = iter(f)
        for code in it:
            code = code.strip(); val = next(it).rstrip('\r\n')
            if code == '0':
                if cur is not None and section in ('ENTITIES', 'BLOCKS') and cur.get('h') is not None:
                    ents[cur['h']] = cur
                cur = None
                if val == 'SECTION': section = 'pending'; blk = None; continue
                if val == 'ENDSEC': section = None; continue
                if section in ('ENTITIES', 'BLOCKS'):
                    cur = {'t': val, 'lay': '0', 'own': None, 'blk': blk}
                elif section == 'TABLES':
                    cur = {'t': val, 'tab': True}
                continue
            if section == 'pending' and code == '2': section = val; continue
            if cur is None: continue
            if code == '102': in102 = val.startswith('{'); continue
            if cur.get('tab'):
                if code == '5': cur['h'] = int(val, 16)
                if code == '2':
                    if cur['t'] == 'LAYER': layers.add(val)
                    if cur['t'] == 'BLOCK_RECORD' and 'h' in cur: brec[cur['h']] = val.upper()
                continue
            if code == '5' and 'h' not in cur: cur['h'] = int(val, 16)
            elif code == '8': cur['lay'] = val
            elif code == '330' and not in102 and cur['own'] is None: cur['own'] = int(val, 16)
            elif code == '2' and cur['t'] == 'BLOCK': blk = val.upper(); cur['blk'] = blk
    out, struct = {}, collections.Counter()
    for h, c in ents.items():
        if c['t'] in STRUCT: struct[c['t']] += 1; continue
        k, own = c, None
        for _ in range(4):                                   # VERTEX -> POLYLINE, ATTRIB -> INSERT -> block record
            own = brec.get(k['own'])
            if own or k['own'] not in ents: break
            k = ents[k['own']]
        own = own or (c['blk'] if c['blk'] else '?')
        out[h] = (c['t'], c['lay'], anon(own.upper()))
    return out, layers, set(brec.values()), struct


def main():
    t0 = time.time()
    E1, L1, B1, S1, nobj, unk = dwg_side(sys.argv[1]); t1 = time.time()
    E2, L2, B2, S2 = dxf_side(sys.argv[2]); t2 = time.time()
    print(f'DWG: {nobj} objects, {len(E1)} graphical entities, {len(L1)} layers, {len(B1)} blocks, structure {dict(S1)}, unknown/proxy {dict(unk)}  [{t1 - t0:.1f} s]')
    print(f'DXF: {len(E2)} graphical entities, {len(L2)} layers, {len(B2)} blocks, structure {dict(S2)}  [{t2 - t1:.1f} s]')
    miss = [h for h in E1 if h not in E2]; extra = [h for h in E2 if h not in E1]
    td = [h for h in E1 if h in E2 and E1[h][0] != E2[h][0]]
    ld = [h for h in E1 if h in E2 and E1[h][1] != E2[h][1]]
    od = [h for h in E1 if h in E2 and E1[h][2] != E2[h][2]]
    print(f'missing {len(miss)}, extra {len(extra)}, type changed {len(td)}, layer changed {len(ld)}, owner changed {len(od)}')
    if miss: print('  missing:', collections.Counter(E1[h][:2] for h in miss).most_common(10))
    if extra: print('  extra:', collections.Counter(E2[h][:2] for h in extra).most_common(10))
    if td: print('  types:', collections.Counter((E1[h][0], E2[h][0]) for h in td).most_common(10))
    if ld: print('  layers:', collections.Counter((E1[h][1], E2[h][1]) for h in ld).most_common(10))
    if od: print('  owners:', collections.Counter((E1[h][2], E2[h][2]) for h in od).most_common(10))
    B1 = {anon(b) for b in B1}; B2 = {anon(b) for b in B2}
    print('layers only DWG', sorted(L1 - L2)[:10], 'only DXF', sorted(L2 - L1)[:10]); print('blocks only DWG', sorted(B1 - B2)[:10], 'only DXF', sorted(B2 - B1)[:10])
    print('DWG types', collections.Counter(t for t, _, _ in E1.values()).most_common())


if __name__ == '__main__':
    main()
