"""Compare the block definitions of one family with each other: same drawing, or mirrored in x / y, or turned (3 Nov 2026).

    python -B block_variants.py <L1.dxf> <L2.dxf> <out folder> [family ...]

Revit bakes a flipped family instance into the block definition it exports (the INSERT itself is not mirrored), so two
pieces of one family can have mirror-image blocks. For every family asked (default: all with more than one piece) the
blocks are grouped by drawing, and each group is compared with the first group as it is, mirrored in x, mirrored in y,
and turned 180 degrees, by the mean distance between the two drawings' points (both ways). Writes <out>/block_variants.json.
"""
import json
import math
import sys
from pathlib import Path

import ezdxf
import numpy as np
from ezdxf import disassemble

sys.stdout.reconfigure(encoding='utf-8')
MM = 0.001


def sample(entities, step=0.005):
    pts = []
    for prim in disassemble.to_primitives(disassemble.recursive_decompose(entities)):
        try:
            v = np.array([(p.x * MM, p.y * MM) for p in prim.vertices()])
        except Exception:
            continue
        if len(v) == 0:
            continue
        pts.append(v[:1])
        for a, b in zip(v[:-1], v[1:]):
            n = max(1, int(math.dist(a, b) / step))
            t = np.linspace(0, 1, n + 1)[1:, None]
            pts.append(a + (b - a) * t)
    return np.vstack(pts) if pts else np.zeros((0, 2))


def nn_mean(a, b):
    """Mean distance from each point of a to its nearest point of b (chunked brute force)."""
    if len(a) == 0 or len(b) == 0:
        return float('inf')
    out = []
    for i in range(0, len(a), 2000):
        d = ((a[i:i + 2000, None, :] - b[None, :, :]) ** 2).sum(-1)
        out.append(np.sqrt(d.min(1)))
    return float(np.concatenate(out).mean())


def sym(a, b):
    return (nn_mean(a, b) + nn_mean(b, a)) / 2


def thin(p, cell=0.004):
    if len(p) == 0:
        return p
    k = np.unique(np.round(p / cell).astype(np.int64), axis=0, return_index=True)[1]
    return p[np.sort(k)]


def main(l1, l2, out, fams):
    out = Path(out)
    rows = json.loads((out / 'dxf_pieces.json').read_text(encoding='utf-8'))
    docs = {'L1': ezdxf.readfile(l1), 'L2': ezdxf.readfile(l2)}
    by_fam = {}
    for r in rows:
        if r['insert']:
            by_fam.setdefault(r['family'], []).append(r)
    if not fams:
        fams = [f for f, rs in by_fam.items() if len(rs) > 1]
    result = {}
    for fam in fams:
        rs = by_fam.get(fam, [])
        groups = []                     # [(points, [piece ids], block names)]
        for r in rs:
            blk = docs[r['floor']].blocks.get(r['insert']['name'])
            base = blk.block.dxf.base_point
            p = thin(sample(list(blk)) - np.array([base[0] * MM, base[1] * MM]))
            for g in groups:
                if len(g['points']) and abs(len(g['points']) - len(p)) <= 0.2 * len(p) and sym(p, g['points']) < 0.002:
                    g['pieces'].append(r['id']); g['blocks'].append(r['insert']['name'])
                    break
            else:
                groups.append({'points': p, 'pieces': [r['id']], 'blocks': [r['insert']['name']]})
        ref = groups[0]['points']
        res = []
        for gi, g in enumerate(groups):
            p = g['points']
            cmp = {'as drawn': sym(p, ref), 'mirrored in x (x -> -x)': sym(p * [-1, 1], ref),
                   'mirrored in y (y -> -y)': sym(p * [1, -1], ref), 'turned 180': sym(p * [-1, -1], ref)}
            best = min(cmp, key=cmp.get)
            res.append({'group': gi, 'pieces': g['pieces'], 'points': int(len(p)),
                        'bbox': [round(float(v), 4) for v in (*p.min(0), *p.max(0))] if len(p) else None,
                        'vsFirstGroup_meanDistance_m': {k: round(v, 4) for k, v in cmp.items()}, 'best': best})
        result[fam] = res
        print('==', fam, f'{len(rs)} pieces, {len(groups)} drawings')
        for x in res:
            print('   group', x['group'], x['best'], x['vsFirstGroup_meanDistance_m'], x['bbox'], ' '.join(x['pieces']))
    (out / 'block_variants.json').write_text(json.dumps(result, indent=1, ensure_ascii=False), encoding='utf-8')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4:])
