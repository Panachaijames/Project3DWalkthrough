"""Blind audit set of the held-out run on `presidential suite_layout.dwg` (cache suite_revit), step 5 of 7.
Done the way ../../tower/audit/make_audit_packets.py did it for L29 / L30, with a close-up picture per place.

  python -B keys/suite_revit/audit/make_audit_places.py [detections.json]      (Git Bash, from detector/)

  detections.json  default ../../../blind_run_suite_revit/output_first_mapping/suite_revit.json: the run the README
                   headlines (the mapping check of step 5 found the first mapping equal to the roles read from the
                   independent description, so there is no corrected run)
  prims.pkl        read from $OPENINGS_DATA/suite_revit/prims.pkl (else the WORK path written in ../drawing.json)

What goes in, by tools/score.py's own matching (the module is imported and used as it is; ../suite_revit.json is read only):
  - every detection the key does not match (the scorer's extras: paired with no scored and no optional key opening),
  - every scored key opening the detector missed, and every one it found but not RIGHT or of another kind,
  - controls: scored key openings the detector found RIGHT and of the same kind, about as many as the places above (all
    of them when there are fewer; real passages first, so that the kind gives the controls away less),
shuffled with a fixed seed into anonymous places P01, P02, ...

Writes, next to this file:
  places.json      WHAT THE AUDITORS SEE. Per place: centre, the two ends (ordered west to east, or south to north for
                   an opening closer to north-south), the claimed kind and width, the picture and its box. Every place
                   is worded the same way whatever its source (key openings and detections alike: kind door / window /
                   passage, width = the distance between the two ends, coordinates rounded to the millimetre).
  places/Pnn.png   one close-up per place, about 4 x 4 m centred on it (width + 1.6 m for a wider place), every layer
                   coloured as in ../pictures (../scripts/draw_pictures.py styles), labelled 1 m grid with 0.1 m minor
                   lines, room names and block names of the drawing, and one neutral marker: a translucent yellow band
                   from end to end with a tick at each end, the same for every place. Nothing else is marked: no other
                   place, no detector output, no key. The pictures are drawn in place order.
  secret_map.json  NOT FOR THE AUDITORS: which place came from where (source, key id, detection id, both versions,
                   the scorer's pair row, key entries, rejected places and detections within 1 m, nearby places).
The auditors must see only places.json, places/ and the drawing (its cache, description and pictures); not this script
(its seed and selection reveal the sources), not secret_map.json, not the key and not the detector output.
"""
import hashlib, json, math, os, random, sys
from pathlib import Path

sys.dont_write_bytecode = True                  # never leave a __pycache__ in tools/ or scripts/
HERE = Path(__file__).resolve().parent
DETECTOR = HERE.parents[2]
sys.path.insert(0, str(DETECTOR / 'tools'))
sys.path.insert(0, str(HERE.parent / 'scripts'))
import score as scorer                          # noqa: E402  tools/score.py, the referee
import draw_pictures as dp                      # noqa: E402  layer styles, cache loader and block labels of the step-2 pictures
import matplotlib                               # noqa: E402
matplotlib.use('Agg')
import matplotlib.pyplot as plt                 # noqa: E402
from matplotlib.collections import LineCollection, PolyCollection   # noqa: E402
from matplotlib.lines import Line2D             # noqa: E402
from matplotlib.patches import Patch, Polygon   # noqa: E402

SEED = 1011
KEY = HERE.parent / 'suite_revit.json'
DEFAULT_DET = DETECTOR / 'blind_run_suite_revit' / 'output_first_mapping' / 'suite_revit.json'
BOX_MIN, BOX_PAD = 4.0, 1.6        # m: picture side = max(4 m, place width + 1.6 m)
NEAR = 1.0                         # m: what counts as "near" in the secret map
MARK, MARK_TICK = '#ffd400', '#8a6d00'       # the marker's colours: used by no layer style of the pictures
PUBLIC_FIELDS = ['place', 'centre', 'ends', 'claimedKind', 'claimedWidth', 'picture', 'pictureBox']


def sha1(p):
    return hashlib.sha1(Path(p).read_bytes()).hexdigest()


def r3(p):
    return [round(float(p[0]), 3), round(float(p[1]), 3)]


def ordered_ends(a, b):
    """The two ends in a fixed order whatever the source's own a/b order: west to east, or south to north when the
    opening runs closer to north-south."""
    (ax, ay), (bx, by) = a, b
    if abs(bx - ax) >= abs(by - ay):
        return (a, b) if ax <= bx else (b, a)
    return (a, b) if ay <= by else (b, a)


def centre(o):
    return ((o['a'][0] + o['b'][0]) / 2, (o['a'][1] + o['b'][1]) / 2)


def version(o, who):
    """A record as the secret map keeps it (the full source record is in the key or the detector output)."""
    v = {'id': o.get('id'), 'kind': o['kind'], 'subtype': o.get('subtype', ''), 'a': o['a'], 'b': o['b'],
         'width': round(math.dist(o['a'], o['b']), 4)}
    if who == 'key':
        v['optional'] = bool(o.get('optional'))
    else:
        v['evidence'] = o.get('evidence', '')
        v['confidence'] = o.get('confidence')
    return v


def prims_path():
    if os.environ.get('OPENINGS_DATA'):
        return Path(os.environ['OPENINGS_DATA']) / 'suite_revit' / 'prims.pkl'
    return Path(json.loads((HERE.parent / 'drawing.json').read_text(encoding='utf-8'))['prims_pkl'])


def draw_place(items, labels, box, e1, e2, out, title, px=1400, grid=1.0, minor=0.1):
    """One close-up: the drawing as ../scripts/draw_pictures.draw shows it (every layer, colour by layer, solid fills,
    dashed linetypes, room names, block names), plus the neutral marker between e1 and e2."""
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    s = px / max(w, h)                                  # pixels per metre
    lw_scale = max(0.6, min(2.2, s / 160))
    segs, fills, texts = {}, {}, []
    for d in items:
        lay = d['lay']
        if d['t'] == 'INSERT':
            continue
        if 'text' in d:
            x, y = d['ins']
            if x0 <= x <= x1 and y0 <= y <= y1 and d['text'] and d['t'] != 'ATTRIB':
                texts.append(d)
            continue
        for p in ([d['pts']] if 'pts' in d else d.get('loops', [])):
            if not p:
                continue
            xs = [q[0] for q in p]; ys = [q[1] for q in p]
            if max(xs) < x0 or min(xs) > x1 or max(ys) < y0 or min(ys) > y1:
                continue
            if d['t'] == 'HATCH' and d.get('solid') and len(p) > 2:
                fills.setdefault(lay, []).append(p)
            pp = p + [p[0]] if (d.get('closed') or 'loops' in d) and len(p) > 2 else p
            if len(pp) == 1:
                pp = [pp[0], [pp[0][0] + 1e-4, pp[0][1]]]
            dashed = d.get('lt') not in (None, 'BYLAYER', 'BYBLOCK', 'Continuous', 'CONTINUOUS')
            segs.setdefault((lay, dashed), []).extend(zip(pp, pp[1:]))
    LEG = 8.6                                           # inches kept for the legend, as in draw_pictures
    W, H = w * s / 100 + LEG, h * s / 100 + 1.5
    fig = plt.figure(figsize=(W, H), dpi=100)
    ax = fig.add_axes([0.7 / W, 0.75 / H, (w * s / 100) / W, (h * s / 100) / H])
    for gx in [math.floor(x0 / minor) * minor + i * minor for i in range(int(w / minor) + 3)]:
        if x0 <= gx <= x1:
            major = abs(gx / grid - round(gx / grid)) < 1e-6
            ax.axvline(gx, color='#e8c48a' if major else '#f4e6cc', lw=0.8 if major else 0.4, zorder=0)
    for gy in [math.floor(y0 / minor) * minor + i * minor for i in range(int(h / minor) + 3)]:
        if y0 <= gy <= y1:
            major = abs(gy / grid - round(gy / grid)) < 1e-6
            ax.axhline(gy, color='#e8c48a' if major else '#f4e6cc', lw=0.8 if major else 0.4, zorder=0)
    # the marker: a translucent band under the line work, from end to end, and a tick across each end on top
    ux, uy = e2[0] - e1[0], e2[1] - e1[1]
    L = math.hypot(ux, uy) or 1.0
    ux, uy = ux / L, uy / L
    nx, ny = -uy, ux
    hw = 0.12
    ax.add_patch(Polygon([(e1[0] + nx * hw, e1[1] + ny * hw), (e2[0] + nx * hw, e2[1] + ny * hw),
                          (e2[0] - nx * hw, e2[1] - ny * hw), (e1[0] - nx * hw, e1[1] - ny * hw)],
                         closed=True, fc=MARK, ec='none', alpha=0.5, zorder=1))
    for e in (e1, e2):
        ax.plot([e[0] - nx * 0.32, e[0] + nx * 0.32], [e[1] - ny * 0.32, e[1] + ny * 0.32], color=MARK_TICK, lw=2.0,
                alpha=0.8, solid_capstyle='butt', zorder=22)
    used = []
    any_dashed = False
    for lay in sorted(set(k[0] for k in segs) | set(fills), key=lambda k: dp.STYLE.get(k, dp.OTHER)[3]):
        c, lw, ls, z, leg, fa = dp.STYLE.get(lay, dp.OTHER)
        if lay in fills:
            ax.add_collection(PolyCollection(fills[lay], facecolors=c, edgecolors='none', alpha=fa, zorder=z - 0.5))
        for dashed in (False, True):
            if (lay, dashed) in segs:
                any_dashed |= dashed and ls == '-'
                ax.add_collection(LineCollection(segs[(lay, dashed)], colors=c, linewidths=lw * lw_scale,
                                                 linestyles=(0, (5, 3)) if dashed else ls, zorder=z))
        leg = leg or {'I-FURN-CHAR': dp.STYLE['I-FURN'][4], 'I-WALL-HATT': dp.STYLE['G-IMPT'][4]}.get(lay, dp.OTHER[4])
        if not any(u[2] == leg for u in used):
            used.append((c, ls, leg))
    if any_dashed:
        used.append(('#555555', (0, (5, 3)), 'dashed: the entity itself has a dashed / hidden linetype (overhead or beyond)'))
    fs = 7.5
    for d in texts:
        ax.text(d['ins'][0], d['ins'][1], d['text'][:40], fontsize=fs * 1.4, color='#303030', weight='bold', zorder=20,
                va='top', ha='left', bbox=dict(boxstyle='round,pad=0.15', fc='white', ec='none', alpha=0.7))
    for b in labels:
        if not (x0 <= b['x'] <= x1 and y0 <= b['y'] <= y1):
            continue
        col = {'A-DOOR': '#b00000', 'A-WALL': '#000000', 'S-COLS': '#000000', 'A-GLAZ-CURT': '#006080',
               'A-GLAZ-CWMG': '#006d6d', 'Q-SPCQ': '#4d7a00', 'Q-CASE': '#8a6326'}.get(b['lay'], '#555555')
        nm = b['name'] + (' [mirrored]' if b['mir'] else '')
        small = b['lay'] in ('A-GLAZ-CWMG', 'A-GLAZ-CURT', 'Q-SPCQ', 'I-FURN-CHAR', 'Q-CASE')
        ax.plot(b['x'], b['y'], marker='+', color=col, ms=5, zorder=21)
        ax.text(b['x'], b['y'], ' ' + nm, fontsize=fs * (0.75 if small else 0.95), color=col, zorder=21,
                bbox=dict(boxstyle='square,pad=0.05', fc='white', ec='none', alpha=0.55))
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.set_aspect('equal')
    xt = [math.ceil(x0 / grid) * grid + i * grid for i in range(int(w / grid) + 2)]
    yt = [math.ceil(y0 / grid) * grid + i * grid for i in range(int(h / grid) + 2)]
    ax.set_xticks([v for v in xt if v <= x1]); ax.set_yticks([v for v in yt if v <= y1])
    ax.set_xticklabels([f'{v:g}' for v in xt if v <= x1]); ax.set_yticklabels([f'{v:g}' for v in yt if v <= y1])
    ax.tick_params(labelsize=fs * 1.3, top=True, right=True, labeltop=True, labelright=True)
    ax.set_xlabel('x (drawing metres)', fontsize=fs * 1.2); ax.set_ylabel('y (drawing metres)', fontsize=fs * 1.2)
    ax.set_title(title, fontsize=fs * 1.6, pad=fs * 3)
    handles = [Patch(fc=MARK, ec=MARK_TICK, alpha=0.6)] + [Line2D([0], [0], color=c, ls=ls, lw=2.2) for c, ls, _ in used]
    texts_leg = ['the place to judge: yellow band from one end to the other, a tick across each end'] + [t for _, _, t in used]
    fig.legend(handles, texts_leg, loc='upper left', fontsize=fs * 1.15, frameon=True,
               bbox_to_anchor=((0.7 + w * s / 100 + 0.75) / W, 1.0 - 0.75 / H))
    fig.savefig(out)
    plt.close(fig)


def main():
    det_path = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else DEFAULT_DET
    key = json.loads(KEY.read_text(encoding='utf-8'))
    det = json.loads(det_path.read_text(encoding='utf-8'))
    KEYS = {o['id']: o for o in key['openings']}
    DETS = {o['id']: o for o in det['openings']}
    assert len(KEYS) == len(key['openings']) and len(DETS) == len(det['openings']), 'ids must be unique'
    rep = scorer.score(key, det)
    rng = random.Random(SEED)

    cands = []
    for fl, fr in rep['floors'].items():
        for x in fr['extra']:
            cands.append({'source': 'detector extra', 'claim': DETS[x['det']], 'claimFrom': 'detection',
                          'keyId': None, 'detId': x['det'], 'pair': None, 'floor': fl})
        for x in fr['missed']:
            cands.append({'source': 'key opening missed', 'claim': KEYS[x['key']], 'claimFrom': 'key',
                          'keyId': x['key'], 'detId': None, 'pair': None, 'floor': fl})
        wrong = [p for p in fr['pairs'] if not p['right'] or not p['kindOk']]
        for p in wrong:
            cands.append({'source': 'key opening found but not right', 'claim': KEYS[p['key']], 'claimFrom': 'key',
                          'keyId': p['key'], 'detId': p['det'], 'pair': p, 'floor': fl})
        good = [p for p in fr['pairs'] if p['right'] and p['kindOk']]
        target = len(fr['extra']) + len(fr['missed']) + len(wrong)      # about as many controls as places in dispute
        pas = [p for p in good if p['kindKey'] == 'passage']
        rest = [p for p in good if p not in pas]
        ctrl = pas + rng.sample(rest, min(max(target - len(pas), 0), len(rest)))
        for p in ctrl:
            cands.append({'source': 'control: key opening found right', 'claim': KEYS[p['key']], 'claimFrom': 'key',
                          'keyId': p['key'], 'detId': p['det'], 'pair': p, 'floor': fl})
    rng.shuffle(cands)

    pkl = prims_path()
    D = dp.load(str(pkl))
    items = D['items']
    labels = dp.block_labels(items)

    places, secret = [], {}
    for i, c in enumerate(cands, 1):
        pid = f'P{i:02d}'
        o = c['claim']
        e1, e2 = ordered_ends(o['a'], o['b'])
        e1, e2 = r3(e1), r3(e2)
        cx, cy = (o['a'][0] + o['b'][0]) / 2, (o['a'][1] + o['b'][1]) / 2
        wd = math.dist(o['a'], o['b'])
        side = max(BOX_MIN, round(wd + BOX_PAD, 1))
        box = [round(cx - side / 2, 3), round(cy - side / 2, 3), round(cx + side / 2, 3), round(cy + side / 2, 3)]
        places.append({'place': pid, 'centre': r3((cx, cy)), 'ends': [e1, e2], 'claimedKind': o['kind'],
                       'claimedWidth': round(wd, 3), 'picture': f'places/{pid}.png', 'pictureBox': box})
        cc = (cx, cy)
        near_keys = sorted(({'id': k['id'], 'kind': k['kind'], 'optional': bool(k.get('optional')),
                             'width': round(math.dist(k['a'], k['b']), 3), 'centreDistance': round(math.dist(cc, centre(k)), 3)}
                            for k in key['openings'] if k.get('floor') == c['floor'] and k['id'] != c['keyId']
                            and math.dist(cc, centre(k)) <= NEAR), key=lambda r: r['centreDistance'])
        near_dets = sorted(({'id': d['id'], 'kind': d['kind'], 'width': round(math.dist(d['a'], d['b']), 3),
                             'centreDistance': round(math.dist(cc, centre(d)), 3)}
                            for d in det['openings'] if d.get('floor') == c['floor'] and d['id'] != c['detId']
                            and math.dist(cc, centre(d)) <= NEAR), key=lambda r: r['centreDistance'])
        near_rej = [{'id': r['id'], 'where': r['where'], 'distance': round(math.dist(cc, r['where']), 3)}
                    for r in key.get('rejected', []) if r.get('floor') == c['floor'] and math.dist(cc, r['where']) <= NEAR]
        secret[pid] = {'source': c['source'], 'claimFrom': c['claimFrom'], 'keyId': c['keyId'], 'detId': c['detId'],
                       'key': version(KEYS[c['keyId']], 'key') if c['keyId'] else None,
                       'detection': version(DETS[c['detId']], 'detection') if c['detId'] else None,
                       'scorePair': c['pair'],
                       'keyEntriesWithin1m': near_keys, 'otherDetectionsWithin1m': near_dets,
                       'keyRejectedPlacesWithin1m': near_rej}
    for p in places:                                    # places near each other (for the analysis, not for the auditors)
        secret[p['place']]['otherPlacesWithin1m'] = [q['place'] for q in places if q is not p
                                                     and math.dist(p['centre'], q['centre']) <= NEAR]

    assert all(list(p) == PUBLIC_FIELDS for p in places)
    src_count = {}
    for v in secret.values():
        src_count[v['source']] = src_count.get(v['source'], 0) + 1
    public = {
        'what': 'Candidate openings of "presidential suite_layout.dwg" (drawing cache suite_revit) to judge from the drawing.',
        'how to read': ('Each place claims that an opening of the claimed kind (door, window or passage) runs between its two '
                        'ends. A claim may be right, wrong in kind, width or ends, or there may be no opening there at all: '
                        'judge every place from the drawing, the same way for each.'),
        'coordinates': 'drawing metres (DXF millimetres / 1000), the same as prims.pkl and the pictures of the drawing',
        'fields': {'centre': 'midpoint of the two ends', 'ends': 'the two ends, west to east (south to north when the line runs '
                   'closer to north-south)', 'claimedKind': 'door, window or passage', 'claimedWidth': 'distance between '
                   'the two ends, m', 'picture': 'close-up of every layer, 1 m labelled grid, 0.1 m minor lines, the place '
                   'marked by a yellow band with a tick at each end', 'pictureBox': '[xmin, ymin, xmax, ymax] of the picture'},
        'places': places,
    }
    (HERE / 'places.json').write_text(json.dumps(public, indent=1, ensure_ascii=False), encoding='utf-8')
    (HERE / 'secret_map.json').write_text(json.dumps({
        'about': 'NOT FOR THE AUDITORS. Which place of places.json came from where. Made by make_audit_places.py '
                 '(step 5 of 7 of the held-out test on suite_revit).',
        'detections': str(det_path.relative_to(DETECTOR)).replace('\\', '/'), 'detectionsSha1': sha1(det_path),
        'key': str(KEY.relative_to(DETECTOR)).replace('\\', '/'), 'keySha1': sha1(KEY),
        'prims': str(pkl).replace('\\', '/'), 'primsSha1': sha1(pkl), 'seed': SEED,
        'rules': {'detector extra': "a detection the key does not match (score.py's extra: paired with no scored and no optional key opening); the claim is the detection's",
                  'key opening missed': 'a scored key opening no detection is paired with; the claim is the key\'s',
                  'key opening found but not right': 'a scored key opening paired with a detection that is not RIGHT or not of the same kind; the claim is the key\'s, the detection is in "detection" and "scorePair"',
                  'control: key opening found right': 'a scored key opening paired with a detection that is RIGHT and of the same kind; the claim is the key\'s'},
        'counts': src_count, 'total': len(places),
        'score': rep['total'],
        'places': secret}, indent=1, ensure_ascii=False), encoding='utf-8')

    outdir = HERE / 'places'
    outdir.mkdir(exist_ok=True)
    for p in places:                                    # in place order, so file times say nothing about the sources
        x0, y0, x1, y1 = p['pictureBox']
        (ax_, ay_), (bx_, by_) = p['ends']
        title = (f"{p['place']}: centre ({p['centre'][0]:.3f}, {p['centre'][1]:.3f}), ends ({ax_:.3f}, {ay_:.3f}) and "
                 f"({bx_:.3f}, {by_:.3f})\npicture x {x0:.2f} to {x1:.2f}, y {y0:.2f} to {y1:.2f} (drawing metres); "
                 f"every layer; 1 m grid, 0.1 m minor lines")
        draw_place(items, labels, p['pictureBox'], p['ends'][0], p['ends'][1], outdir / f"{p['place']}.png", title)
    print(f'{len(places)} places from {det_path.name}:', ', '.join(f'{k} {v}' for k, v in src_count.items()))
    print('claimed kinds:', {k: sum(1 for p in places if p['claimedKind'] == k) for k in ('door', 'window', 'passage')})
    print('wrote', HERE / 'places.json', HERE / 'secret_map.json', outdir)


if __name__ == '__main__':
    main()
