"""Draw the entities that the DXF lacks (from the dwgread JSON, placed through their INSERT chain) over the suite as the DXF
has it (prims cache). Usage: python missing_plot.py <dwgread.json> <plan.dxf> <prims.pkl> <out.png> x0 y0 x1 y1 (m)"""
import collections, json, math, pickle, sys
sys.path.insert(0, __file__.rsplit('\\', 1)[0] if '\\' in __file__ else '.')
import nothing_lost_stream as N
from missing_detail import objects


def mat(o, bh):
    """INSERT -> 2D affine (a, b, c, d, e, f): x' = a x + b y + e, y' = c x + d y + f; includes the block base point."""
    sx, sy = (o.get('scale') or [1, 1, 1])[:2]
    r = o.get('rotation', 0.0)
    ip = o.get('ins_pt') or [0, 0, 0]
    blk = bh.get((o.get('block_header') or [None])[-1], {})
    bp = blk.get('base_pt') or [0, 0, 0]
    ca, sa = math.cos(r), math.sin(r)
    a, b, c, d = ca * sx, -sa * sy, sa * sx, ca * sy
    e = ip[0] - (a * bp[0] + b * bp[1]); f = ip[1] - (c * bp[0] + d * bp[1])
    if (o.get('extrusion') or [0, 0, 1])[2] < 0: a, b, e = -a, -b, -e      # OCS flip (mirrored about y in world)
    return (a, b, c, d, e, f)


def compose(m1, m2):          # m1 after m2
    a, b, c, d, e, f = m1; A, B, C, D, E, F = m2
    return (a * A + b * C, a * B + b * D, c * A + d * C, c * B + d * D, a * E + b * F + e, c * E + d * F + f)


def ap(m, p): return (m[0] * p[0] + m[1] * p[1] + m[4], m[2] * p[0] + m[3] * p[1] + m[5])


def geom(o):
    t = o['entity']
    if t == 'LINE': return [o['start'][:2], o['end'][:2]]
    if t == 'LWPOLYLINE':
        P = [p[:2] for p in o.get('points', [])]
        return P + P[:1] if (o.get('flag', 0) & 512 or o.get('flag', 0) & 1) else P
    if t in ('ARC', 'CIRCLE'):
        c, r = o['center'], o['radius']; s, e = (o.get('start_angle', 0), o.get('end_angle', 2 * math.pi))
        if e < s: e += 2 * math.pi
        return [(c[0] + r * math.cos(s + (e - s) * i / 16), c[1] + r * math.sin(s + (e - s) * i / 16)) for i in range(17)]
    return None


def main():
    js, dxf, pk, png = sys.argv[1:5]; box = [float(v) for v in sys.argv[5:9]]
    E2, _, _, _ = N.dxf_side(dxf)
    O = list(objects(js))
    bh = {o['handle'][-1]: o for o in O if o.get('object') == 'BLOCK_HEADER'}
    lay = {o['handle'][-1]: o.get('name') for o in O if o.get('object') == 'LAYER'}
    ents = {o['handle'][-1]: o for o in O if 'entity' in o}
    ins_of = collections.defaultdict(list)
    for o in ents.values():
        if o['entity'] == 'INSERT': ins_of[(o.get('block_header') or [None])[-1]].append(o)
    def owner_bh(o):
        oh = (o.get('ownerhandle') or [None])[-1]
        return oh if oh in bh else None
    def world_mats(bhh, depth=0):
        """All placements of block bhh in model space (through nested inserts)."""
        out = []
        for i in ins_of.get(bhh, []):
            m = mat(i, bh)
            if i.get('entmode') == 2: out.append(m)
            elif depth < 5:
                ob = owner_bh(i)
                if ob is not None and bh[ob].get('name', '').upper() != '*MODEL_SPACE':
                    out += [compose(M, m) for M in world_mats(ob, depth + 1)]
                elif ob is not None: out.append(m)
        return out
    miss = [o for h, o in ents.items() if o['entity'] not in ('BLOCK', 'ENDBLK', 'SEQEND') and h not in E2]
    segs = collections.defaultdict(list); inbox = collections.Counter()
    cache = {}
    for o in miss:
        g = geom(o)
        if not g: continue
        L = lay.get((o.get('layer') or [None])[-1], '?')
        ob = owner_bh(o)
        if ob is None or bh[ob].get('name', '').upper() == '*MODEL_SPACE': mats = [(1, 0, 0, 1, 0, 0)] if o.get('entmode') == 2 or ob else []
        else:
            if ob not in cache: cache[ob] = world_mats(ob)
            mats = cache[ob]
        for m in mats:
            w = [(x / 1000, y / 1000) for x, y in (ap(m, p) for p in g)]
            if any(box[0] <= x <= box[2] and box[1] <= y <= box[3] for x, y in w):
                segs[L].append(w); inbox[(L, bh[ob]['name'][:40] if ob else 'MS')] += 1
    print('missing entities drawn inside the box, by (layer, owner block):')
    for k, v in inbox.most_common(30): print(' ', v, k)
    D = pickle.load(open(pk, 'rb'))
    import matplotlib; matplotlib.use('Agg'); import matplotlib.pyplot as plt
    from matplotlib.collections import LineCollection
    fig, ax = plt.subplots(figsize=(16, 13), dpi=110)
    have = [d['pts'] for d in D['items'] if d.get('area') == 'suite' and 'pts' in d]
    ax.add_collection(LineCollection(have, linewidths=0.25, colors='#9a9a9a'))
    walls = [d['pts'] for d in D['items'] if d.get('area') == 'suite' and 'pts' in d and d['lay'] == 'A-1.Netcat - tuong']
    ax.add_collection(LineCollection(walls, linewidths=0.6, colors='#202020'))
    col = {'A-1.Netcat - tuong': '#d62728', 'A.Cot 1': '#9467bd', 'Openning': '#ff7f0e'}
    for L, S in segs.items():
        ax.add_collection(LineCollection(S, linewidths=1.0 if L in col else 0.4, colors=col.get(L, '#1f77b4')))
    ax.set_xlim(box[0], box[2]); ax.set_ylim(box[1], box[3]); ax.set_aspect('equal')
    ax.set_title('grey/black: in the DXF (black = wall layer). red: wall layer, purple: column layer, orange: Openning, blue: other layers = in the DWG but NOT in the DXF')
    fig.savefig(png, bbox_inches='tight'); print('->', png)


if __name__ == '__main__':
    main()
