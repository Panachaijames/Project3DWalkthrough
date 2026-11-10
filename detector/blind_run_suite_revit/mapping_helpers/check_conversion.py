"""Compare entity layers between LibreDWG's JSON dump of the DWG (dwgread -O JSON) and the converted DXF.

Usage: python -B check_conversion.py <dump.json> <plan.dxf>
Prints, per entity type, how many entities the dump and the DXF hold, and every entity whose layer differs (matched by
handle). Used to check whether the 'Skip HATCH common handles' warnings of dwg2dxf moved hatches to layer 0.
"""
import collections, json, sys
from ezdxf import recover


def main():
    J = json.load(open(sys.argv[1], encoding='utf-8', errors='replace'))
    objs = J.get('OBJECTS', [])
    by_handle = {}
    layer_name = {}
    for o in objs:
        h = o.get('handle')
        hv = h[-1] if isinstance(h, list) and h else None
        if o.get('object') == 'LAYER': layer_name[hv] = o.get('name')
        by_handle[hv] = o
    dump_types, dump_layer = collections.Counter(), {}
    owner_of = {}
    for hv, o in by_handle.items():
        t = o.get('entity')
        if not t: continue
        dump_types[t] += 1
        lr = o.get('layer')
        lv = lr[-1] if isinstance(lr, list) and lr else None
        dump_layer[hv] = layer_name.get(lv, f'?{lv}')
        ow = o.get('ownerhandle')
        owner_of[hv] = ow[-1] if isinstance(ow, list) and ow else None

    doc, _ = recover.readfile(sys.argv[2])
    dxf_types, dxf_layer = collections.Counter(), {}
    for blk in doc.blocks:          # model space, paper space and every block definition
        for e in blk:
            t = e.dxftype()
            dxf_types[t] += 1
            try: dxf_layer[int(e.dxf.handle, 16)] = e.dxf.get('layer', '0')
            except Exception: pass

    print('entity counts, dump vs DXF (all spaces and block definitions):')
    for t in sorted(set(dump_types) | set(dxf_types)):
        flag = '' if dump_types[t] == dxf_types[t] else '   <-- differs'
        print(f'  {t:16} dump {dump_types[t]:7}  dxf {dxf_types[t]:7}{flag}')
    diff = collections.Counter()
    missing = collections.Counter()
    for hv, lay in dump_layer.items():
        if hv not in dxf_layer: missing[by_handle[hv].get('entity')] += 1; continue
        if dxf_layer[hv] != lay: diff[(by_handle[hv].get('entity'), lay, dxf_layer[hv])] += 1
    print('\nentities of the dump not found in the DXF by handle:', dict(missing))
    print('entities whose layer differs (type, dump layer, DXF layer): count')
    for k, n in diff.most_common(): print('  ', k, n)
    hl = collections.Counter(lay for hv, lay in dump_layer.items() if by_handle[hv].get('entity') == 'HATCH')
    print('\nHATCH layers in the dump:', dict(hl.most_common()))
    hx = collections.Counter(e.dxf.get('layer', '0') for blk in doc.blocks for e in blk if e.dxftype() == 'HATCH')
    print('HATCH layers in the DXF: ', dict(hx.most_common()))


if __name__ == '__main__':
    main()
