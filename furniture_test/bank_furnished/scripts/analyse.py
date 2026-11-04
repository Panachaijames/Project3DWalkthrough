"""The bank furniture models (banquet/*.glb) against the bank model: facts, matches, transforms, turns, coverage (3 Nov 2026).

    python -B analyse.py <work folder> <project folder> <result json>

Reads what glb_read.py, read_logs.py, dxf_pieces.py and block_variants.py wrote into <work folder> and the project's
bank_test/src/bank_model.json and bank_test/bank_furniture_list.csv (read only); writes the result JSON.
"""
import csv
import hashlib
import json
import math
import pickle
import sys
from pathlib import Path

import numpy as np
from shapely.geometry import MultiPoint, Polygon

sys.path.insert(0, str(Path(__file__).parent))
from register import register  # noqa: E402

sys.stdout.reconfigure(encoding='utf-8')
W, PROJ, RESULT = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
facts = json.loads((W / 'glb_facts.json').read_text(encoding='utf-8'))
logs = json.loads((W / 'glb_logs.json').read_text(encoding='utf-8'))
pieces = {p['id']: p for p in json.loads((W / 'dxf_pieces.json').read_text(encoding='utf-8'))}
variants = json.loads((W / 'block_variants.json').read_text(encoding='utf-8'))
geo = pickle.loads((W / 'dxf_geometry.pkl').read_bytes())
bank = json.loads((PROJ / 'bank_test/src/bank_model.json').read_text(encoding='utf-8'))
OFF = bank['offset']
LEVEL = {f['key']: f['level'] for f in bank['floors']}
with open(PROJ / 'bank_test/bank_furniture_list.csv', encoding='utf-8-sig', newline='') as fh:
    BASE = {r['id']: float(r['base_mm']) / 1000 for r in csv.DictReader(fh)}   # a box's underside above its level
r3 = lambda v: round(float(v), 3) + 0.0
r4 = lambda v: round(float(v), 4) + 0.0
wrap = lambda a: (a + 180.0) % 360.0 - 180.0
ang = lambda x, y: math.degrees(math.atan2(y, x)) % 360
FLIPS_FRONT = {'mirrored in y (y -> -y)', 'turned 180'}               # block drawings whose -Y side is the other way round


def quarter(delta, symmetry=360):
    """A turn difference (degrees) -> the nearest quarter turn, the rest and a verdict, for a shape with no symmetry (360)
    or one that looks the same turned half round (180)."""
    d = delta % 360.0
    q = int(round(d / 90.0)) % 4 * 90
    v = {0: 'right', 90: 'off by 90', 180: 'off by 180', 270: 'off by 90'}[q]
    if symmetry == 180 and q == 180:
        v = 'right (off by 180, which this shape does not show)'
    return {'difference': r3(wrap(d)), 'quarterTurn': q, 'residual': r3(wrap(d - q)), 'verdict': v}


def min_rect(points):
    hull = MultiPoint([tuple(p) for p in np.unique(np.round(points, 5), axis=0)]).convex_hull
    c = list(hull.minimum_rotated_rectangle.exterior.coords)[:4]
    e1, e2 = math.dist(c[0], c[1]), math.dist(c[1], c[2])
    a, b, w, d = (c[0], c[1], e1, e2) if e1 >= e2 else (c[1], c[2], e2, e1)
    return {'x': r4((c[0][0] + c[2][0]) / 2), 'y': r4((c[0][1] + c[2][1]) / 2), 'w': r4(w), 'd': r4(d),
            'longSideTurn': r3(math.degrees(math.atan2(b[1] - a[1], b[0] - a[0])) % 180), 'hullArea_m2': r4(hull.area)}


def load(name):
    z = np.load(W / f'{name}.npz')
    ks = sorted([k for k in z.files if k.endswith('_v')], key=lambda k: int(k[1:-2]))
    return [(z[k], z[k[:-2] + '_i']) for k in ks]


def rz(a):
    a = math.radians(a)
    return np.array([[math.cos(a), -math.sin(a), 0, 0], [math.sin(a), math.cos(a), 0, 0], [0, 0, 1, 0], [0, 0, 0, 1.0]])


def tr(x, y, z):
    m = np.eye(4)
    m[:3, 3] = [x, y, z]
    return m


def flip_of(rel):
    return {'as drawn': np.diag([1, 1, 1, 1.0]), 'mirrored in x (x -> -x)': np.diag([-1, 1, 1, 1.0]),
            'mirrored in y (y -> -y)': np.diag([1, -1, 1, 1.0]), 'turned 180': np.diag([-1, -1, 1, 1.0])}[rel]


VAR = {pid: (fam, g['group'], g['best']) for fam, gs in variants.items() for g in gs for pid in g['pieces']}
rel_of = lambda pid: VAR.get(pid, (None, 0, 'as drawn'))[2]


def is_round(pid):
    pts = np.vstack([np.asarray(pl) for pl in geo['pieces'][pid]])
    b = pieces[pid]['box']
    r = np.hypot(pts[:, 0] - b['x'], pts[:, 1] - b['y'])
    return bool(r.max() - r.min() < 0.003)


def box_matrix(pid):
    """Box frame (Max / DWG): origin at the box centre on its underside (level + base_mm), x along its long side (rot), z up."""
    p = pieces[pid]
    return tr(p['box']['x'], p['box']['y'], LEVEL[p['floor']] + BASE[pid]) @ rz(p['box']['rot'])


def block_matrix(pid, ref_pid=None):
    """Block frame (Max / DWG): the INSERT (insertion point, turn; no INSERT in the bank is scaled or mirrored) at the box's
    underside height; with ref_pid also the mirror that turns ref_pid's block drawing into this piece's (Revit bakes a flipped
    family instance into its block definition, not into the INSERT)."""
    p = pieces[pid]
    i = p['insert']
    m = tr(i['x'], i['y'], LEVEL[p['floor']] + BASE[pid]) @ rz(i['rotation']) @ np.diag([i['xscale'], i['yscale'], 1, 1.0])
    if ref_pid:
        m = m @ flip_of(rel_of(pid)) @ flip_of(rel_of(ref_pid))      # each its own inverse; they commute
    return m


def mirror_name(pid, ref_pid):
    c = flip_of(rel_of(pid)) @ flip_of(rel_of(ref_pid))
    return {(1, 1): 'none', (-1, 1): 'mirror x', (1, -1): 'mirror y', (-1, -1): 'turn 180'}[(int(c[0, 0]), int(c[1, 1]))]


C3 = np.array([[1, 0, 0, 0], [0, 0, 1, 0], [0, -1, 0, 0], [0, 0, 0, 1.0]])   # Max (x, y, z) -> three.js / glTF (x, z, -y)
to_three = lambda m: C3 @ m @ np.linalg.inv(C3)
mat = lambda m: [[round(float(v), 6) + 0.0 for v in row] for row in m]
dist = lambda a, b: math.hypot(a[0] - b[0], a[1] - b[1])
box_xy = lambda pid: (pieces[pid]['box']['x'], pieces[pid]['box']['y'])


def to_block(pid, xy):
    """A world point (x, y) in the piece's block frame."""
    q = np.linalg.inv(block_matrix(pid)) @ np.array([xy[0], xy[1], 0, 1.0])
    return q[:2]


def measured_fronts():
    """Fronts read off the geometry: the chair's backrest, the screen's display surface, the desk's modesty panel."""
    out = {}
    v = np.vstack([q for q, _ in load('visitor chair01')])
    c = (v[:, :2].min(0) + v[:, :2].max(0)) / 2
    d = v[v[:, 2] > 0.62][:, :2].mean(0) - c
    out['visitor chair01'] = (round(ang(-d[0], -d[1]), 1), f'the backrest (vertices above 0.62 m) lies {np.linalg.norm(d):.2f} m from the '
                              f'footprint centre towards {ang(*d):.1f} degrees, so the seat faces {ang(-d[0], -d[1]):.1f} degrees (west, towards '
                              'the desk L1-table-002); the block drawing has its backrest arc on its +Y side and the seat front on -Y')
    v, t = load('monitor')[2]
    a, b, cc = v[t[:, 0]], v[t[:, 1]], v[t[:, 2]]
    n = np.cross(b - a, cc - a).sum(0)
    out['monitor'] = (round(ang(n[0], n[1]), 1), f'the display surface (primitive 2 of the screen, {len(t)} triangles) faces {ang(n[0], n[1]):.1f} degrees, '
                      'west-south-west, towards the Aeron chair L1-seat-002 (its normal also leans 5 degrees up: the screen is tilted back)')
    parts = load('working table')
    allv = np.vstack([q for q, _ in parts])
    c = (allv[:, :2].min(0) + allv[:, :2].max(0)) / 2
    names = [p['name'] for p in facts['working table']['parts']]
    d = parts[names.index('Object13483')][0][:, :2].mean(0) - c
    out['working table'] = (round(ang(*d), 1), f'the modesty panel (part Object13483) stands {np.linalg.norm(d):.3f} m from the centre towards '
                            f'{ang(*d):.1f} degrees (east), on the block\'s -Y side: for this family the block\'s front is the visitor / '
                            'modesty-panel side and the user sits on its +Y side (west, where the Aeron chair L1-seat-002 is). The desk drawing '
                            'is the same turned half round, so only the model tells the panel side')
    return out


FRONTS = measured_fronts()


def facts_for_text():
    """The numbers the explanations quote, worked out here."""
    T = {}
    for name in facts:
        v = np.vstack([q for q, _ in load(name)])
        T[name] = min_rect(v[:, :2])
    return T


FP = facts_for_text()
RUN = ['L1-sofa-001', 'L1-sofa-002', 'L1-sofa-003', 'L1-sofa-004']
run_c = (float(np.mean([pieces[q]['box']['x'] for q in RUN])), float(np.mean([pieces[q]['box']['y'] for q in RUN])))


def monitor_numbers():
    parts = load('monitor')
    scr = np.vstack([parts[i][0] for i in (0, 1, 2)])
    kb = np.vstack([parts[i][0] for i in (3, 4, 5)])                 # the keyboard alone (the mouse, parts 6-7, lies beside it)
    sc = (scr[:, :2].min(0) + scr[:, :2].max(0)) / 2
    kc = (kb[:, :2].min(0) + kb[:, :2].max(0)) / 2
    # the block's own drawing: its screen is the long thin rectangle along local y = 0 .. -0.02, its keyboard the rectangle
    # x -0.24 .. 0.24, y -0.16 .. -0.30 (read off the drawing in the block frame)
    pid = 'L1-computer-003'
    i = pieces[pid]['insert']
    R = rz(i['rotation'])[:2, :2]
    drawn_kb = R @ np.array([0.0, -0.23]) + np.array([i['x'], i['y']])
    s_local = to_block(pid, sc)
    return {'screenCentre': sc, 'screenInBlock': s_local, 'keyboardCentre': kc, 'drawnKeyboard': drawn_kb,
            'keyboardMoved': dist(kc, drawn_kb), 'keyboardMovedTowards': ang(*(kc - drawn_kb))}


MON = monitor_numbers()

SPEC = {
    'working table': {'piece': 'L1-table-002', 'runnerUp': 'L1-table-003', 'confidence': 'high', 'symmetry': 360},
    'visitor chair01': {'piece': 'L1-seat-012', 'runnerUp': 'L1-seat-007', 'confidence': 'high', 'symmetry': 360},
    'visitor chair02': {'piece': 'L1-seat-007', 'runnerUp': 'L1-seat-008', 'confidence': 'high', 'symmetry': 0,
                        'front': 'round (0.472 m across both ways; its drawing a 0.5 m circle): no front, any turn looks the same'},
    'monitor': {'piece': 'L1-computer-003', 'runnerUp': 'L1-computer-002', 'confidence': 'high for the screen; its keyboard and mouse were moved',
                'symmetry': 360, 'screenParts': [0, 1, 2], 'keyboardParts': [3, 4, 5, 6, 7]},
    'banquet': {'piece': 'L1-sofa-002', 'runnerUp': 'L1-sofa-003', 'confidence': 'high for the run of four modules, medium for one piece',
                'symmetry': 180, 'run': RUN,
                'front': 'a backless bench (0.46-0.47 m high right across its depth, two equal cushions): it looks the same turned half '
                         'round, so only its long axis counts. The drawing\'s module has a 0.14 m band along its +Y (wall) side that the model does not have'},
    'sofa': {'piece': 'L1-seat-028', 'runnerUp': None,
             'runnerUpNote': 'none on level 1: the family has one piece there; its other two, L2-seat-024 and L2-seat-030, are on level 2',
             'confidence': 'family certain (the mesh carries its name); piece medium (the only one of the family on level 1, but the model '
                           'stands 0.47 m off it and a quarter turn round)', 'symmetry': 360,
             'front': 'a double-sided bench (seats on both long sides) with its back pad (0.32 x 0.73 m, above 0.5 m) off centre along the bench '
                      'and one slanted long side: the shape, not a front, fixes the turn'},
    'stool': {'piece': 'L1-seat-020', 'runnerUp': 'L1-seat-026', 'confidence': 'low', 'symmetry': None,
              'front': 'an irregular six-sided pouf (0.413 x 0.294 m, 0.45 m high, no back): no front; the CAD draws every VISIONA stool as a '
                       'circle, so the drawing gives no turn either'},
    'side table': {'piece': 'L1-coffee-table-002', 'runnerUp': 'L1-coffee-table-004', 'confidence': 'low', 'symmetry': 180,
                   'front': 'four legs and a 0.45 x 0.30 m top: it looks the same turned half round; its long side runs east-west (0 degrees). '
                            'The TA104 side tables are drawn as 0.5 m circles, so the drawing gives no turn'},
}
for k, (a, txt) in FRONTS.items():
    SPEC[k]['frontAngle'] = a
    SPEC[k]['front'] = txt


def why(name, reg):
    fp = FP[name]
    s = SPEC[name]
    d = lambda pid: dist((fp['x'], fp['y']), box_xy(pid))
    iou = reg['asExported']['iou']
    if name == 'working table':
        return (f"Its footprint ({fp['d']:.3f} x {fp['w']:.3f} m, long side north-south) lies on L1-table-002's box (1.787 x 1.000 m at 90 "
                f"degrees): centres {1000 * d('L1-table-002'):.0f} mm apart, and the silhouette fits the block drawing as exported (IoU {iou:.2f}). "
                f"The family's other four tables are {d('L1-table-003'):.2f} m or more away.")
    if name == 'visitor chair01':
        return (f"It stands on L1-seat-012: centres {1000 * d('L1-seat-012'):.0f} mm apart, footprint {fp['w']:.3f} x {fp['d']:.3f} m against "
                f"the box's 0.599 x 0.563 m, and it fits that chair drawing as exported (IoU {iou:.2f}). The next box that fits its size is the "
                f"stool L1-seat-007 ({d('L1-seat-007'):.2f} m); the nearest other mollie chairs, L1-seat-011 and -013, are "
                f"{d('L1-seat-013'):.1f} m away.")
    if name == 'visitor chair02':
        return (f"A 0.472 m round stool centred {1000 * d('L1-seat-007'):.0f} mm from L1-seat-007, a 0.5 m circle in the drawing (IoU {iou:.2f} "
                f"as exported). Runner-up: L1-seat-008, the same family by the next desk north ({d('L1-seat-008'):.2f} m); L2-seat-010, a "
                f"blue VISIONA stool only {d('L2-seat-010'):.1f} m away in plan, is on level 2.")
    if name == 'monitor':
        sl = MON['screenInBlock']
        return (f"The model is a 27-inch screen with a keyboard and a mouse; the block Computer 003 draws a screen, a keyboard and a mouse too. "
                f"The screen stands on L1-computer-003's drawing, {abs(sl[1]):.2f} m in front of the drawn screen line (block y {sl[1]:.3f}, x "
                f"{sl[0]:.3f}) and facing the way the block does (0.4 degrees apart). Its keyboard was moved "
                f"{MON['keyboardMoved']:.2f} m towards {MON['keyboardMovedTowards']:.0f} degrees (south-south-west) from where the block draws "
                f"one, with the mouse beside it, in front of the Aeron chair L1-seat-002, so the "
                f"whole model's footprint ({fp['w']:.2f} x {fp['d']:.2f} m) is {d('L1-computer-003'):.2f} m off the box centre and does not "
                f"match the box. Its base is at 0.750 m, the top of L1-table-002, which the piece stands on. Runner-up: L1-computer-002, the "
                f"same block on the next desk south ({d('L1-computer-002'):.2f} m).")
    if name == 'banquet':
        return (f"A {fp['w']:.2f} m long, {fp['d']:.2f} m deep backless bench on the run of four 1.0 x 0.7 m SOFA_BENCH_DIOR - TYPE 2 modules "
                f"(L1-sofa-001 to -004, 4.0 m long): it fills the run's width exactly (x 5.327-6.020 against 5.322-6.022) and is centred on "
                f"the run ({1000 * dist((fp['x'], fp['y']), run_c):.0f} mm off), but it is {4.0 - fp['w']:.2f} m shorter, reaching from the "
                f"middle of L1-sofa-001 to the middle of L1-sofa-004. So it was exported from the run, not from one piece: L1-sofa-002 is the "
                f"nearest single piece ({d('L1-sofa-002'):.2f} m), L1-sofa-003 the runner-up ({d('L1-sofa-003'):.2f} m).")
    if name == 'sofa':
        return (f"Its mesh is called 'CHAIR_BENCH BACK SE107 STOOL LOW_VITRA_VISIONA STOOL [2572013]', the family of L1-seat-028, L2-seat-024 "
                f"and L2-seat-030, and its {fp['w']:.3f} x {fp['d']:.3f} m footprint matches their boxes (1.900 x 1.182-1.200 m). But it stands "
                f"{d('L1-seat-028'):.2f} m from L1-seat-028, the family's only piece on level 1, and a quarter turn from it, overlapping "
                f"L1-coffee-table-004, L1-seat-033 and the side table model: its place in the scene is not the drawing's. No runner-up on "
                f"level 1.")
    if name == 'stool':
        return (f"It stands on no stool: it stands inside the box of L1-seat-026, a mollie chair ({d('L1-seat-026'):.2f} m from its centre; "
                f"box 0.599 x 0.563 m against the model's {fp['w']:.3f} x {fp['d']:.3f} m), whose own model is visitor chair01. By its name and "
                f"size it is most likely a CHAIR_STOOL LOW_VITRA_VISIONA STOOL, and the smallest of those, SE104 400W BLUE (drawn as 0.4 m "
                f"circles), is the nearest in size; that family's nearest piece is L1-seat-020, {d('L1-seat-020'):.2f} m away. Runner-up: "
                f"L1-seat-026, the piece it stands in.")
    if name == 'side table':
        return (f"It stands on no piece of the drawing: between L1-seat-026 and L1-coffee-table-002 ({d('L1-coffee-table-002'):.2f} m from "
                f"that table's centre), and it overlaps the sofa model. No table family in the bank has its {fp['w']:.2f} x {fp['d']:.2f} m "
                f"top; the nearest of its kind is TABLE_BEDSIDE_VITRA_OCCASIONAL - TA104 600W 400H, drawn as 0.5 m circles. Most likely "
                f"L1-coffee-table-002 (the nearest side table), runner-up L1-coffee-table-004 (same family, {d('L1-coffee-table-004'):.2f} m). "
                f"It may be a piece the drawing does not have: the 3D team should say which family it is.")


def candidates(name, level):
    """Every piece on the model's level by centre distance, and those whose box is within 25 % of the model's footprint (long
    and short side each; a quarter turn is allowed, as both are sorted long side first)."""
    fp = FP[name]
    rows = []
    for p in pieces.values():
        if p['floor'] != level:
            continue
        b = p['box']
        err = max(abs(fp['w'] - b['w']) / max(fp['w'], b['w']), abs(fp['d'] - b['d']) / max(fp['d'], b['d']))
        rows.append({'piece': p['id'], 'family': p['family'], 'kind': p['kind'], 'distance_m': r3(dist((fp['x'], fp['y']), (b['x'], b['y']))),
                     'sizeDifference': r3(err), 'box': f"{b['w']:.3f} x {b['d']:.3f} at {b['rot']}",
                     'axisTurn': r3((fp['longSideTurn'] - b['rot']) % 180)})
    near = sorted(rows, key=lambda r: r['distance_m'])
    return {'footprint': f"{fp['w']:.3f} x {fp['d']:.3f} m, long side at {fp['longSideTurn']} degrees",
            'nearest': near[:5], 'nearestWithBoxWithin25Percent': [r for r in near if r['sizeDifference'] <= 0.25][:5]}


def per_model(name):
    f = facts[name]
    s = SPEC[name]
    pid = s['piece']
    p = pieces[pid]
    parts = load(name)
    allv = np.vstack([v for v, _ in parts])
    fp = FP[name]
    level = 'L1' if allv[:, 2].min() < 1.85 else 'L2'
    sym = s['symmetry']
    ins = p['insert']
    rho = ins['rotation']
    rho_eff = (rho + (180 if rel_of(pid) in FLIPS_FRONT else 0)) % 360
    box_rot = p['box']['rot']
    round_drawing = is_round(pid)
    sel = s.get('screenParts')
    tris = np.concatenate([v[t][:, :, :2] for i, (v, t) in enumerate(parts) if sel is None or i in sel])
    target = s.get('run', [pid])
    lines = [pl for q in target for pl in geo['pieces'][q]]
    bx, by = run_c if 'run' in s else box_xy(pid)
    reg = register(tris, lines, (bx, by))
    k = reg['best']['turn']
    if name == 'monitor':
        k = 0                       # the screen's silhouette is nearly the same turned half round; its display surface decides
    fine = None
    if sym and not round_drawing:
        # the turn in half-degree steps within 10 degrees of the quarter turn: how exactly the model sits on its drawing
        fr = register(tris, lines, (bx, by), fine_turns=[k + d for d in np.arange(-10, 10.01, 0.5)], search=0.06)
        bm = fr['best']['mean']
        near = [t['turn'] - k for t in fr['turns'] if t['mean'] <= bm * 1.02]
        fine = {'bestTurnOffQuarter': r3(fr['best']['turn'] - k), 'mean': fr['best']['mean'], 'iou': fr['best']['iou'],
                'turnsWithin2PercentOfBest': [r3(min(near)), r3(max(near))]}
    if sym is None:
        real, how = None, 'no front'
    elif sym == 0:
        real, how = None, 'round: no turn'
    elif name == 'monitor':
        real = (s['frontAngle'] + 90) % 360
        how = (f"its display surface faces {s['frontAngle']} degrees (turn = front + 90); the silhouette fit alone cannot tell (the screen is "
               f"nearly the same turned half round: best at {reg['best']['turn']} degrees)")
    elif round_drawing:
        real, how = fp['longSideTurn'], 'its own long side (the drawing is round and gives no turn)'
    elif sym == 180 and k in (0, 180):
        real, how = rho_eff, 'the block turn: the silhouette fits as exported and turned half round alike, as the shape does'
    else:
        real = (rho_eff - k) % 360
        how = ('the block turn: the silhouette fits the drawing as exported' if k == 0 else
               f'the block turn minus the {k} degrees the silhouette needs to fit the drawing')
        if fine:
            spread = max(abs(fine['turnsWithin2PercentOfBest'][0]), abs(fine['turnsWithin2PercentOfBest'][1]))
            how += (' (to the half-degree step of the search)' if spread < 0.5 else
                    f' (to within {spread:.1f} degrees: a half-degree search fits about as well anywhere in that range)')
        if 'frontAngle' in s:
            chk = (s['frontAngle'] + 90) % 360
            how += f"; check: the measured front gives {chk:.1f}, {abs(wrap(chk - real)):.1f} degrees from it"
    if sym in (0, None):
        box_v = blk_v = {'verdict': 'any turn looks the same (round)' if sym == 0 else 'no front: any turn will do'}
    elif round_drawing:
        box_v = {'difference': r3(wrap(real - box_rot)), 'verdict': f'not comparable: the box of a round drawing has an arbitrary turn ({box_rot} degrees)'}
        blk_v = {'difference': r3(wrap(real - rho_eff)), 'verdict': 'not comparable: the drawing is round'}
    else:
        box_v = quarter(real - box_rot, sym)
        blk_v = quarter(real - rho_eff, sym)
    drawing_v = (quarter(rho_eff - box_rot, sym) if (sym and not round_drawing) else
                 {'verdict': 'round drawing: no turn to compare' if round_drawing else 'any turn looks the same (round)'})
    # a suggested placement where the scene's is not the drawing's
    c_m = np.array(reg['modelFootprintCentre'])
    suggested = None
    if name == 'sofa':
        t = np.array(reg['best']['shift'])
        P = tr(*(c_m + t), 0) @ rz(k) @ tr(-c_m[0], -c_m[1], 0)
        suggested = (P, f'turned {k} degrees about its footprint centre and moved {np.linalg.norm(t):.3f} m: the pose that fits the block '
                        f"drawing best (mean line distance {reg['best']['mean']:.3f} m against {reg['asExported']['mean']:.3f} m as exported)")
    elif name in ('stool', 'side table'):
        P = tr(p['box']['x'] - fp['x'], p['box']['y'] - fp['y'], 0)
        suggested = (P, f"moved {dist((fp['x'], fp['y']), box_xy(pid)):.3f} m so that its footprint centre is on the box centre, its turn "
                        'kept (the drawing is round and gives none)')
    elif name == 'banquet':
        P = tr(bx - fp['x'], by - fp['y'], 0)
        suggested = (P, f"moved {dist((fp['x'], fp['y']), (bx, by)):.3f} m onto the centre of the run of four, and placed once for the "
                        'whole run (relative to the run, not to one piece)')
    Mb = np.linalg.inv(box_matrix(pid))
    Mi = np.linalg.inv(block_matrix(pid))
    c_world = np.array([fp['x'], fp['y'], allv[:, 2].min(), 1.0])
    cb, ci = Mb @ c_world, Mi @ c_world

    turn_after = None if real is None else ((real + k) % 360 if name == 'sofa' else real)

    def sugg(M, keyname, frame_turn):
        if suggested is None:
            return None
        Q = M @ suggested[0]
        cc = suggested[0] @ c_world                   # the footprint centre after the suggested move, then in the frame
        return {'why': suggested[1], f'maxWorldTo{keyname}Frame_rowMajor': mat(Q), f'gltfSceneTo{keyname}FrameThree_rowMajor': mat(to_three(Q)),
                'modelFootprintCentre': [r4(v) for v in (M @ cc)[:3]],
                'modelTurnInFrame': None if turn_after is None else r3((turn_after - frame_turn) % 360)}

    ru = s['runnerUp']
    return {
        'file': {'name': f['file'], 'bytes': f['fileBytes'], 'sha256': hashlib.sha256((PROJ / 'banquet' / f['file']).read_bytes()).hexdigest(),
                 'gltfVersion': f['gltfVersion'], 'generator': f['generator'], 'chunks': f['chunks'], 'counts': f['counts'],
                 'extensionsUsed': f['extensionsUsed']},
        'triangles': f['triangles'], 'vertices': f['vertices'],
        'parts': [{'node': q['node'], 'name': q['name'], 'primitive': q['primitive'], 'triangles': q['triangles'], 'vertices': q['vertices'],
                   'material': q['material'], 'attributes': q['attributes'], 'indexType': q['indexType'], 'maxWorldBox': q['maxBox']}
                  for q in f['parts']],
        'materials': f['materials'],
        'textureCoordinates': {'declared': f['texcoordsDeclared'], 'attributesDeclared': f['attributesUsed'],
                               'vertexBuffers': f['interleavedBufferViews']},
        'rootNodes': f['rootNodes'],
        'worldBox': f['worldBox'],
        'size_m': {'x': f['worldBox']['maxZup']['size'][0], 'y': f['worldBox']['maxZup']['size'][1], 'height': f['worldBox']['maxZup']['size'][2],
                   'footprintLong': fp['w'], 'footprintShort': fp['d']},
        'footprint': fp, 'level': level, 'baseZ_m': r4(allv[:, 2].min()), 'topZ_m': r4(allv[:, 2].max()),
        'exportLog': logs[name],
        'match': {'piece': pid, 'family': p['family'], 'kind': p['kind'], 'block': p['block'], 'handle': p['handle'],
                  'distance_m': r3(dist((fp['x'], fp['y']), box_xy(pid))), 'box': p['box'], 'boxBase_m': BASE[pid],
                  'confidence': s['confidence'], 'why': why(name, reg),
                  'runnerUp': ({'piece': None, 'note': s.get('runnerUpNote')} if ru is None else
                               {'piece': ru, 'family': pieces[ru]['family'], 'floor': pieces[ru]['floor'],
                                'distance_m': r3(dist((fp['x'], fp['y']), box_xy(ru)))}),
                  'run': s.get('run'), 'runCentre': [r4(bx), r4(by)] if 'run' in s else None,
                  'runDistance_m': r3(dist((fp['x'], fp['y']), (bx, by))) if 'run' in s else None,
                  'candidates': candidates(name, level)},
        'fitToDrawing': {'against': target, 'silhouette': 'the screen only' if sel else 'the whole model', 'drawingIsRound': round_drawing,
                         'how': 'the model\'s plan silhouette (its triangles filled at 1 cm) against the block drawing\'s lines: for each quarter '
                                'turn about the footprint centre, the shift (centre on the box centre, then +-0.10 m in 1 cm steps) with the least '
                                'mean distance between the drawing\'s lines and the silhouette\'s outline (both ways, capped at 0.15 m); IoU = the '
                                'silhouette against the drawing\'s outline filled (meaningless where the drawing is not closed)',
                         **reg, 'halfDegreeFit': fine},
        'relativeToBox': {
            'frame': 'origin at the box centre on the box underside (level + base_mm), x along the box long side (its rot), z up; Max / DWG metres',
            'modelFootprintCentre': {'along': r4(cb[0]), 'across': r4(cb[1]), 'up': r4(cb[2])},
            'modelTurnInFrame': r3((real - box_rot) % 360) if real is not None else None,
            'maxWorldToBoxFrame_rowMajor': mat(Mb), 'gltfSceneToBoxFrameThree_rowMajor': mat(to_three(Mb)),
            'suggested': sugg(Mb, 'Box', box_rot),
            'use': 'Max: v_world = BoxM(P) @ maxWorldToBoxFrame @ v_exported, BoxM(P) = T(x_m, y_m, level + base_mm / 1000) Rz(rot). three.js '
                   'on the bank page: object.matrix = T(x, level + base_mm / 1000, -y) Ry(rot) @ gltfSceneToBoxFrameThree, with x, y, rot of P '
                   'from bank_model.json and the GLB scene as loaded'},
        'relativeToBlock': {
            'frame': "origin at the block's insertion point at the box underside height, x / y the block's own axes (the INSERT's turn undone; no "
                     'INSERT in the bank is scaled or mirrored), z up; Max / DWG metres',
            'insert': ins, 'drawingVariant': {'group': VAR[pid][1], 'vsFamilyGroup0': VAR[pid][2]} if pid in VAR else None,
            'modelFootprintCentre': {'x': r4(ci[0]), 'y': r4(ci[1]), 'up': r4(ci[2])},
            'modelTurnInFrame': r3((real - rho_eff) % 360) if real is not None else None,
            'maxWorldToBlockFrame_rowMajor': mat(Mi), 'gltfSceneToBlockFrameThree_rowMajor': mat(to_three(Mi)),
            'suggested': sugg(Mi, 'Block', rho_eff),
            'use': "Max: v_world = InsM(P) @ F(P) @ maxWorldToBlockFrame @ v_exported, InsM(P) = T(insert x, y, level + base_mm / 1000) Rz(insert "
                   "turn), F(P) = the mirror that turns this piece's block drawing into P's (families.<model>.perPiece[].mirrorToMatchedPiece; "
                   "mirror y = diag(1, -1, 1)). three.js: object.matrix = T(ix - 1.212, level + base_mm / 1000, -(iy - 0.348)) Ry(insert turn) "
                   "F3(P) @ gltfSceneToBlockFrameThree, F3 for mirror y = diag(1, 1, -1)"},
        'orientation': {
            'frontFoundBy': s['front'],
            'symmetry': {360: 'none', 180: 'looks the same turned half round', 0: 'round', None: 'no front'}[sym],
            'realTurnInScene': r3(real) if real is not None else None, 'realTurnFrom': how,
            'boxTurn': box_rot, 'boxVerdict': box_v,
            'blockTurn': rho, 'blockMirrored': ins['mirrored'], 'blockDrawing': rel_of(pid), 'blockTurnWithDrawing': r3(rho_eff),
            'blockVerdict': blk_v, 'boxTurnAgainstBlockTurn': drawing_v,
        },
    }


def family_coverage(name, res):
    """Every piece of the matched family: the model put there by the box turn and by the block turn (mirror included)."""
    s = SPEC[name]
    mid = s['piece']
    fam = pieces[mid]['family']
    m = res['models'][name]
    allv = np.vstack([v for v, _ in load(name)])
    pts = np.c_[allv, np.ones(len(allv))]
    pts = pts[np.linspace(0, len(pts) - 1, min(len(pts), 4000)).astype(int)]
    Mb = np.linalg.inv(box_matrix(mid))
    Mi = np.linalg.inv(block_matrix(mid))
    sym = s['symmetry']
    rows = []
    for pid, p in pieces.items():
        if p['family'] != fam:
            continue
        a = (pts @ (box_matrix(pid) @ Mb).T)[:, :3]
        b = (pts @ (block_matrix(pid, mid) @ Mi).T)[:, :3]
        mir = mirror_name(pid, mid)
        f_blk = p['insert']['rotation'] + (180 if mir in ('mirror y', 'turn 180') else 0) - pieces[mid]['insert']['rotation']
        f_box = p['box']['rot'] - pieces[mid]['box']['rot']
        if sym is None:
            v = {'verdict': 'no front: any turn will do', 'difference': r3(wrap(f_blk - f_box))}
        elif sym == 0:
            v = {'verdict': 'any turn looks the same (round)', 'difference': r3(wrap(f_blk - f_box))}
        elif is_round(pid):
            v = {'verdict': 'round drawing: neither turn is in the drawing', 'difference': r3(wrap(f_blk - f_box))}
        else:
            v = quarter(f_blk - f_box, sym)
        row = {'id': p['id'], 'floor': p['floor'], 'box': {k: p['box'][k] for k in ('x', 'y', 'rot')}, 'insertTurn': p['insert']['rotation'],
               'blockDrawing': rel_of(pid), 'mirrorToMatchedPiece': mir,
               'blockTurnMinusBoxTurn': r3((p['insert']['rotation'] + (180 if rel_of(pid) in FLIPS_FRONT else 0) - p['box']['rot']) % 360),
               'byBoxTurnInsteadOfBlock': {**v, 'mirrorImage': mir in ('mirror x', 'mirror y'),
                                          'meanPointGap_m': r3(np.linalg.norm(a - b, axis=1).mean()),
                                          'centreGap_m': r3(np.linalg.norm(a.mean(0) - b.mean(0)))}}
        if s.get('keyboardParts') and p['on']:
            sb = pieces[p['on']]['box']
            ca, sa = math.cos(math.radians(sb['rot'])), math.sin(math.radians(sb['rot']))
            hw, hd = sb['w'] / 2, sb['d'] / 2
            poly = Polygon([(sb['x'] + sx * hw * ca - sy * hd * sa, sb['y'] + sx * hw * sa + sy * hd * ca) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))])
            kv = np.vstack([v for i, (v, _) in enumerate(load(name)) if i in s['keyboardParts']])
            kb = (np.c_[kv, np.ones(len(kv))] @ (block_matrix(pid, mid) @ Mi).T)[:, :2]
            hull = MultiPoint([tuple(q) for q in np.unique(np.round(kb, 4), axis=0)]).convex_hull
            row['keyboardAndMouseOnSupport'] = {'support': p['on'], 'shareOfTheirFootprintOnIt': r3(hull.intersection(poly).area / hull.area)}
        rows.append(row)
    tally = {}
    for r in rows:
        key = r['byBoxTurnInsteadOfBlock']['verdict'] + (' (mirror image)' if r['byBoxTurnInsteadOfBlock']['mirrorImage'] else '')
        tally[key] = tally.get(key, 0) + 1
    plain = {}
    for r in rows:                  # the chair test's way: the model's front at -Y turned by the box's rot, against the drawing
        if sym in (0, None) or is_round(r['id']):
            key = 'no turn to compare'
        else:
            # the real turn at P (the drawing's, plus the model's own offset from its block at the matched piece) minus P's box rot
            # (the sofa, which the scene turned off its drawing, is taken as the drawing has it: its offset from the block is 0)
            own = 0.0 if name == 'sofa' else m['orientation']['realTurnInScene'] - m['orientation']['blockTurnWithDrawing']
            key = quarter(r['blockTurnMinusBoxTurn'] + own, sym)['verdict']
        r['plainBoxTurn'] = key
        plain[key] = plain.get(key, 0) + 1
    return {'family': fam, 'kind': pieces[mid]['kind'], 'pieces': len(rows),
            'perLevel': {lv: sum(1 for r in rows if r['floor'] == lv) for lv in sorted({r['floor'] for r in rows})},
            'ids': [r['id'] for r in rows], 'trianglesEach': m['triangles'], 'trianglesFullDetail': m['triangles'] * len(rows),
            'byBoxTurnInsteadOfBlockTurn': tally, 'plainBoxTurnAsTheChairTest': plain, 'perPiece': rows}


def main():
    res = {'what': "The 3D team's bank furniture models (banquet/, 8 GLB files received 3 Nov 2026) against the bank model: what each file "
                   'holds, the piece it was exported from, its transform relative to that piece\'s box and block, its turn against the box '
                   'turn and the block turn, and the pieces its family would furnish. Analysis only: nothing drawn in a browser, nothing timed.',
           'made': '2026-11-03',
           'inputs': {'models': 'banquet/*.glb and *.glb.log (read only)', 'bankModel': 'bank_test/src/bank_model.json (furniture[], offset, floors)',
                      'furnitureList': 'bank_test/bank_furniture_list.csv (base_mm, the DXF handles)',
                      'drawings': 'I1201 / I1202 *.dwg converted with LibreDWG 0.14 dwg2dxf into a temp folder (not kept; byte for byte the same '
                                  'as the 26 Oct conversions); every furniture INSERT read back by its handle with ezdxf 1.4.4: 174 of the 185 '
                                  'pieces (the other 11 sit inside another block or are loose shapes, none in the 8 families here)',
                      'checkedWith': 'three.js 0.186.1 GLTFLoader (read from app/node_modules): the same triangles, vertices, attributes and '
                                     'world boxes, and every box / block matrix here puts its model back where it was exported (crosscheck.mjs)'},
           'frames': {'maxWorld': '3ds Max / DWG coordinates of bank_test/Bangkok_Bank_Sampeng.ms: metres, x east, y north, z up; L1 floor 0.00, '
                                  'L2 floor 3.70; = bank_furniture_list.csv x_m, y_m',
                      'bankModelPlan': 'bank_model.json x, y = maxWorld x, y minus offset (1.212, 0.348)',
                      'gltfScene': "the GLB as loaded: y up, (x, y, z) = (max x, max z, -max y). The bank page's three.js world is (plan x, "
                                   'level + z, -plan y) = gltfScene + (-1.212, 0, +0.348) on level 1',
                      'turns': "degrees counter-clockwise seen from above, 0 = +x (east). A box rot is the turn of the box's long side, folded "
                               "into 0-180 (0-90 for a square). A model's turn = the turn of its family's block drawing (front = the block's -Y) "
                               'that gives the model as it stands; a front at angle a (the way it faces) is turn a + 90',
                      'matrices': "row-major 4 x 4, column vectors (v' = M v)"},
           'models': {}, 'families': {}}
    for name in facts:
        res['models'][name] = per_model(name)
    for name in facts:
        res['families'][name] = family_coverage(name, res)
        res['models'][name]['furnishes'] = {k: v for k, v in res['families'][name].items() if k != 'perPiece'}
    fams = res['families']
    res['totals'] = {
        'piecesOfTheEightFamilies': sum(f['pieces'] for f in fams.values()),
        'ofBankPieces': len(pieces),
        'trianglesFullDetail_banquetOncePerRun': sum(f['trianglesFullDetail'] for k, f in fams.items() if k != 'banquet') + facts['banquet']['triangles'],
        'trianglesFullDetail_onePerPiece': sum(f['trianglesFullDetail'] for f in fams.values()),
        'laptopBudgetTriangles': 2000000,
        'visitorChair01Alone': fams['visitor chair01']['trianglesFullDetail'],
    }
    rows = []
    for name, m in res['models'].items():
        fam = fams[name]
        rows.append({'model': name, 'triangles': m['triangles'],
                     'size_m': f"{m['size_m']['footprintLong']:.2f} x {m['size_m']['footprintShort']:.2f} x {m['size_m']['height']:.2f}",
                     'piece': m['match']['piece'], 'family': m['match']['family'], 'distance_m': m['match']['distance_m'],
                     'confidence': m['match']['confidence'], 'runnerUp': m['match']['runnerUp']['piece'],
                     'piecesFurnished': fam['pieces'], 'trianglesFullDetail': fam['trianglesFullDetail'],
                     'realTurn': m['orientation']['realTurnInScene'], 'boxTurn': m['orientation']['boxTurn'],
                     'boxVerdict': m['orientation']['boxVerdict']['verdict'], 'blockTurn': m['orientation']['blockTurnWithDrawing'],
                     'blockVerdict': m['orientation']['blockVerdict']['verdict'],
                     'logWarnings': m['exportLog']['warnings'], 'logErrors': m['exportLog']['errors']})
    res['summary'] = rows
    RESULT.parent.mkdir(parents=True, exist_ok=True)
    RESULT.write_text(json.dumps(res, indent=1, ensure_ascii=False), encoding='utf-8')
    for r in rows:
        print(f"{r['model']:16s} {r['triangles']:>8,} {r['size_m']:>19s} {r['piece']:20s} {r['distance_m']:5.3f} m x{r['piecesFurnished']:<3d} "
              f"{r['trianglesFullDetail']:>10,} real {r['realTurn']} box {r['boxTurn']}: {r['boxVerdict']} | block {r['blockTurn']}: {r['blockVerdict']} | warn {r['logWarnings']} err {r['logErrors']}")
    for name, fam in fams.items():
        print(f"  {name:16s} {fam['perLevel']} by box instead of block: {fam['byBoxTurnInsteadOfBlockTurn']} | plain box turn: {fam['plainBoxTurnAsTheChairTest']}")
    print('totals', res['totals'])
    for name in res['models']:
        print('WHY', name, ':', res['models'][name]['match']['why'])


if __name__ == '__main__':
    main()
