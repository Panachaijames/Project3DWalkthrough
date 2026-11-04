"""Hotel test (2 Nov 2026): the take-off read on two floor-plan PICTURES (takeoff.json, in picture pixels) + the owner's facts and
the assumptions (hotel_project.json) -> hotel_model.json in the bank model's format, hotel_summary.json, hotel_topview.png (here
and beside the pictures' folder) and the furniture proxies' family list ../hotel_furniture_list.csv.

There is no CAD: every position comes from takeoff.json, which read_pictures.py measured on the pictures; a person can correct
one entry there and run this script again. The rules, with sizes in metres (second round, 2 Nov, after the owner's answers:
the stair is 2.50 m wide, floor 2's west side is wall, the middle stair goes down to floor 1 and the upper one up to a floor 3,
the faceted form is a seating; and after the review; then, after the first page, floor 1's check-in is seating: the round
'table' and the 'desk' are a round sofa and a sofa, the five 'screens' on them their seat backs; then the second review's
small faults: the doors from their built jambs, a hatch's sill at the counter in it, the flight's side walls carried on to
its top, the flights' sides on the wall faces, low walls, the terrace railings to the walls, the picture's cut edge closed):
 1. SCALE. The owner's real dimension is the main stair's width, 2.50 m (scale.stairWidth): the clear width of floor 1's flight
    between its two side walls, at their inner faces (read_pictures rule 11), along the picture's x. The two pictures draw one
    lift core (the same structure), so the core's faces measured on both give the ratio between the pictures' scales, by least
    squares, ONE RATIO PER AXIS ('axes': 'per-axis'): floor 1 is drawn about 4 % wider than tall against floor 2 (the core's
    x faces give 1.409, its y faces 1.354; its big round sofa is 2.9 % wider than tall, its lift shafts 5 % against floor
    2's 1.4 %). Floor 2 is taken as drawn square (its round tables are round within their noise), so floor 2 has one scale
    k2 and floor 1 one per axis: kx1 = 1.409 k2, ky1 = 1.354 k2, with kx1 = the flight's clear width in px / 2.50 m. The lift
    doors (the owner's 1 m, rough) and floor 2's stair are checks: hotel_summary.json gives them at this scale. 'axes': 'one'
    is the single ratio of the first build; the methods 'cores' (the four lift doors average liftDoor) and 'doors-floor1'
    (floor 1's two doors exact) are kept for comparison.
 2. FRAME. Metres, y up (picture rows go down), the origin at the north-west outer corner of the lift core (its faces' stroke
    centres): the core's west and north faces as measured on floor 1, and on floor 2 the same point through the fit of rule 1,
    so the floors stack. The model is centred on its floor plates ('offset', as in the bank model: drawing frame = model +
    offset). Its key 'pictureFrame' keeps, per picture, the pixel of the origin and the pixels per metre ALONG EACH AXIS
    (pxPerMetreX, pxPerMetreY), so any model point goes back to a pixel:
    px = originPx[0] + pxPerMetreX * (x + offset x), py = originPx[1] - pxPerMetreY * (y + offset y).
 3. WALLS. The take-off's wall outlines (straight faces on the outline strokes, read_pictures rule 2) and wall bands of a floor,
    unioned, as high as the floor's wall height (to the next floor); its mullions are frame posts of the same height. A LOW
    WALL the take-off gives (drawn faintly, like the stair lines under it: the outside stair's spine) is a parapet, as high
    as a railing (railingHeight), not a wall.
 4. GLAZING. Each glazing line is a pane GLASS_T thick on the line (glassThickness, assumed), full height, its ends taken to
    the wall or mullion it meets (it is lengthened by 2 px of the picture each way and the walls and mullions are taken out).
 5. OPENINGS. A door cuts the walls, glass and mullions in its footprint (its width by the wall's thickness + 5 cm each side:
    the jambs are measured on the wall ends, so this only trims) and is open from the floor to its head (doorHead, assumed);
    above it a lintel to the top of the wall as deep as the wall at its jambs, or a glass transom when both jambs are glass,
    none when nothing stands at either jamb. A lift door is exactly liftDoorWidth wide (the owner), centred on the drawn gap:
    a gap drawn narrower is cut wider, a gap drawn wider gets wall back at its two ends. A passage is left as it is (no cut,
    no lintel). A HATCH (kind 'window', no glass: the serving hatches and the food lift's) cuts its wall in the same footprint
    and puts the wall back below its sill (a 'sill' part) and above its head (a 'lintel'): hatchSill / hatchHead, assumed; a
    hatch with a counter standing in it (a take-off piece of kind counter whose box reaches into the hatch's wall) has its
    sill at that counter's top instead (the kind's height above its base), so the counter reads flush through the hatch.
    THE BUILT JAMBS. Then every door and passage but the lift doors (exact already) is taken from the walls, glass and posts
    as built, after the cut: its jambs are the innermost ends of what stands along it on either side of its middle, on five
    lines across its recorded band (a pane beside a door may stand off its middle line), looked for up to JAMB_REACH past
    the recorded ends; its depth at each jamb is that of the jamb's first JAMB_LEN across the opening's own band, and its
    line goes through the middle of the two depths; its record (centre, width, wall thickness) is that gap, its lintel or
    transom fills the gap between the two jambs flush with each (their hull less what stands there), and Walk's skins are
    cut out of all of it (rule 11). So no slit opens beside a lintel and no lintel stands proud of a wall whose faces were
    fitted to the drawing's strokes; a jamb the walls do not give keeps the recorded end and depth.
    Each opening's record has the bank model's keys; 'inside' lists the sides a person can stand on (rule 11).
 6. STAIRS. 'steps' (floor 1's flight up to floor 2): solid steps between the side walls' inner faces (the measured 2.50 m), the
    floor-to-floor height in `risers` risers (2.90 / 17 = 0.171 m), each step a block two risers deep (as in the bank); the top
    riser lies on the arrival edge of the open stair above (its northmost tread line on floor 2) and the bottom riser on that
    stair's south edge as floor 2 draws it, so that no step runs under floor 2's slab (floor 1 draws its lowest tread line
    0.24 m further south, its 14 lines 0.40 m apart: schematic). 'void' (floor 2 over floor 1's flight): the floor is open
    over the flight, fitted to it: between its side walls' inner faces (floor 2 draws its stringers 0.10-0.14 m further out,
    over floor 1's side walls) and from its bottom riser to its top one, with railings (railingHeight, 5 cm) on the sides the
    take-off names, standing on the slab at the void's edge (floor 1's side walls rise to floor 2 under them: no slot). A
    side wall of the flight that stops short of its top riser (the picture's break line cuts it) is carried on to the top
    riser at its own section, taken SIDE_CUT back from where it stops, so no slot opens beside the high steps. No tread
    line is drawn over a void. 'steps-up' (a flight to a floor not in the pictures, the owner: floor 3): solid steps
    rising from the floor in the direction of 'up', one going between each two of the drawn riser lines, between the side
    walls' inner faces where those are measured (read_pictures rule 11) or else the take-off rectangle's sides, ending in
    the air at the last line. A flight's sides lie on the walls beside it: each is put on the face of the wall it stands
    within FACE_REACH of, as built, so no slot opens beside its steps. 'lines': the tread lines lie flat on the floor (the
    bank's 'below' lines), cut where a wall or a low wall stands (the outside stair's spine).
 7. SHAFTS (lift shafts, the small shafts): walls round them come from rule 3; on the lowest floor the shaft keeps its floor
    (the pit is not modelled), above it there is no floor plate inside the shaft (as the bank does over its lift shaft); a
    shaft the take-off marks 'closed' (the food lift: a dumbwaiter) keeps its floor.
 8. FLOOR PLATES. The inside of the walls, glass, mullions, opening spans and the take-off's plate closings (lines where the
    building is open to a stair bay or cut by the picture's edge), with gaps under 10 cm closed; a slab slabThickness thick
    (assumed) under each floor, its edge 3 cm proud of the outline (as in the bank); minus the voids of rules 6 and 7.
    Floor 1's FORECOURT (the paving outside the south facade, to the road) is an outdoor slab at 0.00 (assumed), the building's
    inside taken out of it. Floor 2's TERRACE runs on to the outline floor 1 dashes for the floor above: from floor 2's own
    west edge to that outline's east line, from its south line up to floor 2's band east of the facade (the picture's own
    edges inside it); a railing (terraceRailingHeight, assumed) stands on its open edges, each run on to the face of a wall
    its end lies within CLOSE_JOIN of. A plate closing the take-off marks 'wall' (where the picture cuts the building off
    and the floor would end in the air: floor 2's back of house at its top edge) also gets a full-height wall along it,
    pictureEdgeWall thick (assumed), just beyond the picture's edge, labelled as the take-off says, so nobody walks off it.
 9. ROOM NAMES. The take-off's labels at their place (the middle of the hand lettering, a red callout's dot or box); the
    pictures give no areas.
10. FURNITURE. One box per take-off piece: the minimum rotated rectangle of its outline (furniture_kit.box_of), the kind and
    family as read (block '', layer 'picture', handle ''; the note names the take-off entry). furniture_kit.finish gives the
    ids, rounds, sorts, puts an onTop piece on the table, counter or cabinet under it (none is: the plants stand clear of
    them, and the check-in's seat backs stand on the floor) and marks the boxes that stand in the approach of a door or
    passage. The family list is written by furniture_kit.write_csv.
11. WHERE A PERSON STANDS (for the viewer's tests). A side of an opening is 'inside' when a spot 0.40-0.90 m in front of it is
    on a floor plate with STAND_CLEAR (0.30 m) of room to every wall, pane, post, railing, sill, low wall or step below 1.5 m. A glass
    probe (the middle of each pane) keeps a side only when such a spot 0.6-1.0 m in front of it has a clear line to the pane.
    The Walk-collision skins (thin parts' invisible 8 cm skin, as in the bank) are cut out of every door's and passage's
    footprint, so Walk gets each opening's full width.
12. CHECKS (printed and in hotel_summary.json): nothing solid across a door or passage below its head, nor across a hatch
    between its sill and head; the cores of the two floors on top of each other (the fit's residuals); floor 1's flight under
    floor 2's void (the step area under the slab, the widest slot beside the flight along its whole run, the top step against
    the soffit); each opening taken from its jambs (rule 5), against its record.
Usage: python build_model.py [hotel_project.json]
"""
import collections, json, math, statistics, sys, time
from pathlib import Path
from shapely.geometry import Polygon, LineString, Point, box as sbox
from shapely.ops import unary_union, nearest_points

HERE = Path(__file__).resolve().parent
PROJECT = HERE.parent.parent                                       # the project folder: presidential_test/ and furniture/ live there
for sub, mod in (('presidential_test/src', 'geom.py'), ('furniture', 'furniture_kit.py')):
    if not (PROJECT / sub / mod).exists(): raise SystemExit(f'{sub}/{mod} not found (expected in the project folder)')
    sys.path.insert(0, str(PROJECT / sub))
from geom import polys, clean                            # presidential_test/src/geom.py, as the bank builder uses it
import furniture_kit as fk                               # furniture/furniture_kit.py: kinds, boxes, supports, approaches, CSV

t_start = time.time()
CFG_PATH = Path(sys.argv[1]).resolve() if len(sys.argv) > 1 else HERE / 'hotel_project.json'
CFG = json.loads(CFG_PATH.read_text(encoding='utf-8'))
DEF = CFG['defaults']
FURN = CFG.get('furniture', {})
TAKE = json.loads((CFG_PATH.parent / CFG['takeoff']).read_text(encoding='utf-8'))
TK = TAKE['floors']
KEYS = [f['key'] for f in CFG['floors']]
FLOOR = {f['key']: f for f in CFG['floors']}
try:
    KIND_TAB = {k['key']: k for k in fk.kinds_table(FURN.get('heights'), FURN.get('bases'))}     # the office's furniture heights
except ValueError as e:
    raise SystemExit(f'{CFG_PATH.name}: {e}')
COUNTER_TOP = (KIND_TAB['counter']['base'] + KIND_TAB['counter']['height']) / 1000            # rule 5: a hatch's sill at a counter in it

CUT_MARGIN = 0.05          # rule 5: a door's footprint reaches this far past the wall faces
GLASS_T = DEF['glassThickness']
RAIL_W = 0.05              # rules 6, 8: a railing band
PLATE_GAP = 0.05           # rule 8: gaps under 2 x this are closed before the inside is taken
SLAB_EDGE = 0.03           # rule 8: the slab edge stands 3 cm out from the outline (as in the bank)
CLOSE_W = 0.02             # rule 8: a plate closing line's band
CLOSE_JOIN = 0.15          # rule 8: a closing line's end within this of a wall is joined to it; the terrace's edges snap to the facades
JAMB_REACH = 0.6           # rule 5: a built jamb is looked for this far past the recorded end
JAMB_LEN = 0.05            # rule 5: the length of each jamb (its wall beside the gap) whose depth the lintel takes
SIDE_CUT = 0.15            # rule 6: a side wall cut short is carried on at its section this far back from where it stops
FACE_REACH = 0.25          # rule 6: a flight's side is put on the face of a wall within this
STAND_CLEAR = 0.30         # rule 11: room a person needs round a spot (the viewer's Walk body is 0.60 m wide)
SKIN = 0.08                # rule 11: the skin of thin colliders (as in the bank)
BLOCKING = ('wall', 'column', 'glass', 'single', 'railing', 'sill', 'parapet', 'mullion')
R3 = lambda v: round(v, 3) + 0.0


def unit(v):
    n = math.hypot(v[0], v[1])
    return (v[0] / n, v[1] / n) if n > 1e-12 else (1.0, 0.0)


def rect(a, u, s0, s1, l0, l1):
    """Rectangle in the frame of an opening (origin a, along u, across n = left of u), as in the bank builder."""
    n = (-u[1], u[0])
    P = lambda s, l: (a[0] + u[0] * s + n[0] * l, a[1] + u[1] * s + n[1] * l)
    return Polygon([P(s0, l0), P(s1, l0), P(s1, l1), P(s0, l1)])


def lines_of(g):
    """The LineStrings of a shapely result (a line cut by a polygon)."""
    if g is None or g.is_empty: return []
    if g.geom_type == 'LineString': return [g]
    return [x for y in getattr(g, 'geoms', []) for x in lines_of(y)]


def runs_along(S, p, d, lo, hi):
    """Where the segment p + d * s, s from lo to hi (d a unit vector), runs inside S -> sorted [(s0, s1)]."""
    seg = LineString([(p[0] + d[0] * lo, p[1] + d[1] * lo), (p[0] + d[0] * hi, p[1] + d[1] * hi)])
    out = []
    for g in lines_of(seg.intersection(S)):
        ss = [(x - p[0]) * d[0] + (y - p[1]) * d[1] for x, y in g.coords]
        out.append((min(ss), max(ss)))
    return sorted(out)


def fit_to_jambs(r, S):
    """Rule 5, the built jambs: a door or passage record r (drawing frame) taken from S, the walls, glass and posts as built (after
    the cut). On five lines along the opening, across its recorded band (a pane beside a door may stand off its middle line), the
    ends of S met on either side of its middle: the innermost on each side is that jamb; the part of S within JAMB_LEN beyond each
    jamb, across the band, gives the depth there, and the opening's line goes through the middle of the two depths. Sets r's a, b,
    w, t (the gap and its mean depth), 'span', 'gap' (the hull of the two jambs: the lintel's region before what stands there is
    taken out) and 'fit' (for the summary). A jamb not met keeps the recorded end and depth; a line that runs inside something at
    the opening's middle does not count."""
    a0, u, n, w0, t0 = r['a'], r['u'], r['n'], r['w'], r['t']
    P = lambda s, l: (a0[0] + u[0] * s + n[0] * l, a0[1] + u[1] * s + n[1] * l)
    sa = sb = None
    for k in (-0.4, -0.2, 0.0, 0.2, 0.4):
        runs = runs_along(S, P(0, k * t0), u, -JAMB_REACH, w0 + JAMB_REACH)
        if any(s0 < w0 / 2 < s1 for s0, s1 in runs): continue
        west, east = [s1 for s0, s1 in runs if s1 <= w0 / 2], [s0 for s0, s1 in runs if s0 >= w0 / 2]
        if west: sa = max(west) if sa is None else max(sa, max(west))
        if east: sb = min(east) if sb is None else min(sb, min(east))
    ends = []
    for s_, sg in ((sa, -1), (sb, 1)):
        piece = S.intersection(rect(a0, u, min(s_, s_ + sg * JAMB_LEN), max(s_, s_ + sg * JAMB_LEN), -t0 / 2, t0 / 2)) if s_ is not None else None
        ls = [(x - a0[0]) * n[0] + (y - a0[1]) * n[1] for g in polys(piece) for x, y in g.exterior.coords] if piece is not None else []
        ends.append((min(ls), max(ls), piece) if ls else (-t0 / 2, t0 / 2, None))
    sa, sb = (0.0 if sa is None else sa), (w0 if sb is None else sb)
    c = (ends[0][0] + ends[0][1] + ends[1][0] + ends[1][1]) / 4
    gap = unary_union([e[2] if e[2] is not None else LineString([P(s_, e[0]), P(s_, e[1])]) for s_, e in ((sa, ends[0]), (sb, ends[1]))]).convex_hull
    t = ((ends[0][1] - ends[0][0]) + (ends[1][1] - ends[1][0])) / 2
    r['fit'] = {'id': r['o']['id'], 'widthWas': R3(w0), 'width': R3(sb - sa), 'jambsMovedOut': [R3(-sa), R3(sb - w0)],
                'depthWas': R3(t0), 'depthAtJambs': [[R3(e[0] - c), R3(e[1] - c)] for e in ends], 'lineMovedAcross': R3(c),
                'jambsFound': [bool(ends[0][2] is not None), bool(ends[1][2] is not None)]}
    r.update(a=P(sa, c), b=P(sb, c), w=sb - sa, t=t, gap=gap, span=gap.buffer(0.02, join_style='mitre'))


def onto_faces(W, xa, xb, y0, y1):
    """Rule 6: the sides xa < xb (x, drawing frame) of a flight that runs from y0 to y1 put on the faces of the walls W beside them:
    across the flight at 5 places along it, the nearest wall face on each side within FACE_REACH of the side; the outermost one
    (so that no slot opens anywhere along it). A side with no wall face that near stays."""
    xm, wa, wb = (xa + xb) / 2, [], []
    for k in range(5):
        y = y0 + (y1 - y0) * (k + 0.5) / 5
        runs = runs_along(W, (xm, y), (1.0, 0.0), xa - xm - FACE_REACH, xb - xm + FACE_REACH)
        west, east = [xm + s1 for s0, s1 in runs if s1 <= 0], [xm + s0 for s0, s1 in runs if s0 >= 0]
        if west and abs(max(west) - xa) <= FACE_REACH: wa.append(max(west))
        if east and abs(min(east) - xb) <= FACE_REACH: wb.append(min(east))
    return (min(wa) if wa else xa), (max(wb) if wb else xb)


def carry_side_walls(W, F):
    """Rule 6: a side wall of floor 1's flight F (drawing frame) that stops short of its top riser is carried on to the top riser at
    its own section, taken SIDE_CUT back from where it stops (the picture's break line cuts the drawing there, not the wall).
    -> (the walls, what was carried on)."""
    adds, said = [], []
    for side, x_in, sg in (('west', F['x0'], -1), ('east', F['x1'], 1)):
        along = runs_along(W, (x_in + sg * 0.01, F['yb']), (0.0, 1.0), 0.0, F['yt'] - F['yb'])
        if not along: continue
        y_end = F['yb'] + along[-1][1]
        if y_end >= F['yt'] - 0.005: continue
        y_sec = y_end - SIDE_CUT
        across = runs_along(W, (x_in, y_sec), (sg, 0.0), -0.001, 0.6)
        if not across or across[0][0] > 0.005 or across[0][1] >= 0.6 - 1e-6: continue
        x_out = x_in + sg * across[0][1]
        adds.append(sbox(min(x_in, x_out), y_sec, max(x_in, x_out), F['yt']))
        said.append({'side': side, 'stoppedAtY': R3(y_end), 'carriedToY': R3(F['yt']), 'carriedOn': R3(F['yt'] - y_end), 'thickness': R3(across[0][1])})
    return (unary_union([W] + adds) if adds else W), said


def run_to_walls(b, W, reach):
    """Rule 8: a railing band (x0, y0, x1, y1) run on, at each end of its long side, to the face of a wall in W met within reach
    along its middle line."""
    x0, y0, x1, y1 = b
    if x1 - x0 >= y1 - y0:
        yc = (y0 + y1) / 2
        r0, r1 = runs_along(W, (x0, yc), (-1.0, 0.0), 0.0, reach), runs_along(W, (x1, yc), (1.0, 0.0), 0.0, reach)
        x0, x1 = x0 - (r0[0][0] if r0 else 0.0), x1 + (r1[0][0] if r1 else 0.0)
    else:
        xc = (x0 + x1) / 2
        r0, r1 = runs_along(W, (xc, y0), (0.0, -1.0), 0.0, reach), runs_along(W, (xc, y1), (0.0, 1.0), 0.0, reach)
        y0, y1 = y0 - (r0[0][0] if r0 else 0.0), y1 + (r1[0][0] if r1 else 0.0)
    return sbox(x0, y0, x1, y1)


# ---------------------------------------------------------------------------------------------------- rule 1: the scale
def faces(key):
    return {(c['edge'], c['axis']): c['at'] for c in TK[key]['core']}


def fit_line(ps):
    """least squares b = s a + t over pairs (a, b) -> (s, t)."""
    ma, mb = statistics.mean(a for a, _ in ps), statistics.mean(b for _, b in ps)
    s = sum((a - ma) * (b - mb) for a, b in ps) / sum((a - ma) ** 2 for a, _ in ps)
    return s, mb - s * ma


F1F, F2F = faces('F1'), faces('F2')
pairs = [(k, F2F[k], F1F[k]) for k in F1F if k in F2F]
if len(pairs) < 4: raise SystemExit('the take-off needs at least 4 core faces measured on both floors')
xs = [(a, b) for (e, ax), a, b in pairs if ax == 'x']
ys = [(a, b) for (e, ax), a, b in pairs if ax == 'y']
SX, TX = fit_line(xs)                                    # floor-1 pixels per floor-2 pixel, along x
SY, TY = fit_line(ys)                                    # ... along y
mx2, mx1 = statistics.mean(a for a, _ in xs), statistics.mean(b for _, b in xs)
my2, my1 = statistics.mean(a for a, _ in ys), statistics.mean(b for _, b in ys)
S1 = (sum((a - mx2) * (b - mx1) for a, b in xs) + sum((a - my2) * (b - my1) for a, b in ys)) / \
     (sum((a - mx2) ** 2 for a, _ in xs) + sum((a - my2) ** 2 for a, _ in ys))       # the single ratio of the first build
scale_cfg = CFG['scale']
method, axes = scale_cfg['method'], scale_cfg.get('axes', 'per-axis')
if axes == 'per-axis': RX, RY, OX, OY = SX, SY, TX, TY
elif axes == 'one': RX, RY, OX, OY = S1, S1, mx1 - S1 * mx2, my1 - S1 * my2
else: raise SystemExit(f"scale.axes {axes!r}: 'per-axis' or 'one'")
door_px = {k: [d['width'] for d in TK[k]['liftDoors']] for k in KEYS}
stair_ref = next(s for s in TK['F1']['stairs'] if s['id'] == scale_cfg.get('stair', 'F1-S1'))
W1 = stair_ref['width']['clear']                         # px along x on floor 1


def k2_for(m):
    """floor 2's pixels per metre (both axes) for a scale method."""
    if m == 'stair': return W1 / scale_cfg['stairWidth'] / RX
    if m == 'cores': return statistics.mean([w / RY for w in door_px['F1']] + door_px['F2']) / scale_cfg['liftDoor']
    if m == 'doors-floor1': return statistics.mean(door_px['F1']) / scale_cfg['liftDoor'] / RY
    raise SystemExit(f"scale.method {m!r}: one of stair, cores, doors-floor1")


K2 = k2_for(method)
PX = {'F1': (RX * K2, RY * K2), 'F2': (K2, K2)}          # (px per metre along x, along y)
# rule 2: the origin, the core's north-west outer corner (floor 1 as measured, floor 2 through the fit)
O1 = (F1F[('core west face', 'x')], F1F[('core north face', 'y')])
O2 = ((O1[0] - OX) / RX, (O1[1] - OY) / RY)
ORIGIN = {'F1': O1, 'F2': O2}
resid = [{'face': e, 'axis': ax, 'floor1Px': b, 'floor2PxOnFloor1': R3((RX if ax == 'x' else RY) * a + (OX if ax == 'x' else OY)),
          'offM': R3((b - ((RX if ax == 'x' else RY) * a + (OX if ax == 'x' else OY))) / PX['F1'][0 if ax == 'x' else 1])} for (e, ax), a, b in pairs]
resid_one = [abs(b - (S1 * a + (mx1 - S1 * mx2 if ax == 'x' else my1 - S1 * my2))) for (e, ax), a, b in pairs]
print(f"scale: floor 2 -> floor 1 pixels x {SX:.4f}, y {SY:.4f} (one ratio {S1:.4f}); axes {axes}; method {method}: floor 1 "
      f"{PX['F1'][0]:.3f} x {PX['F1'][1]:.3f} px/m, floor 2 {K2:.3f} px/m; core fit residuals up to {max(abs(r['offM']) for r in resid):.3f} m "
      f"({max(abs(r['floor1Px'] - r['floor2PxOnFloor1']) for r in resid):.2f} px; one ratio: {max(resid_one):.2f} px)")


def m_of(key, x, y):
    """A picture pixel of floor `key` -> metres in the drawing frame (rule 2)."""
    ox, oy = ORIGIN[key]; kx, ky = PX[key]
    return ((x - ox) / kx, -(y - oy) / ky)


def pts_m(key, pts):
    return [m_of(key, x, y) for x, y in pts]


def poly_m(key, o, h=()):
    g = Polygon(pts_m(key, o), [pts_m(key, r) for r in h])
    return g if g.is_valid else g.buffer(0)


def band_m(key, line, w_px):
    """A band drawn w_px wide in the picture -> its outline in metres (each axis at its own scale)."""
    g = LineString(line).buffer(w_px / 2, cap_style='flat', join_style='mitre')
    return Polygon(pts_m(key, list(g.exterior.coords)))


def across_m(key, a_px, b_px, t_px):
    """A thickness of t_px across the line a -> b of floor `key` (pixels) -> metres."""
    u = unit((b_px[0] - a_px[0], b_px[1] - a_px[1])); n = (-u[1], u[0])
    kx, ky = PX[key]
    return t_px * math.hypot(n[0] / kx, n[1] / ky)


# ---------------------------------------------------------------------------------------------------- rule 6, first: the stair
stair_x = {}            # the open stairs of a floor (for 'topFrom'): id -> (its take-off record, its floor)
for key in KEYS:
    for s in TK[key]['stairs']: stair_x[s['id']] = (s, key)
FLIGHT = None           # floor 1's flight: (x west, x east, y bottom riser, y top riser) in the drawing frame
for key in KEYS:
    for s in TK[key]['stairs']:
        if s['build'] != 'steps': continue
        if s['up'] != 'north': raise SystemExit(f"{s['id']}: steps are built for 'up': 'north' only (this take-off)")
        w = s.get('width') or {}
        xa = m_of(key, w.get('west', s['rect'][0]), 0)[0]; xb = m_of(key, w.get('east', s['rect'][2]), 0)[0]
        above, akey = stair_x[s['topFrom']['stair']]
        yt = m_of(akey, 0, min(above['treadLines']))[1]                     # the arrival: the open stair's northmost line
        yb_drawn = m_of(key, 0, s['bottom'])[1]
        yb = m_of(akey, 0, max(above['treadLines']))[1] if above['build'] == 'void' else yb_drawn
        FLIGHT = {'id': s['id'], 'floor': key, 'x0': xa, 'x1': xb, 'yb': yb, 'yt': yt, 'ybDrawn': yb_drawn, 'void': above['id'],
                  'voidFloor': akey}

# ---------------------------------------------------------------------------------------------------- rules 3-9, per floor
parts_geo = []          # (floor key, kind, polygon, z0, z1, follow, label)
built = {}
for fi, key in enumerate(KEYS):
    T, fc = TK[key], FLOOR[key]
    top, lowest = fc['wallHeight'], fi == 0
    H = (CFG['floors'][fi + 1]['level'] - fc['level']) if fi + 1 < len(KEYS) else top
    # rule 3: walls and mullions (rule 6: floor 1's flight's side walls carried on to its top riser), low walls
    W0 = unary_union([poly_m(key, w['o'], w['h']) for w in T['walls']] + [band_m(key, b['line'], b['w']) for b in T['wallBands']])
    carried = []
    if FLIGHT and FLIGHT['floor'] == key: W0, carried = carry_side_walls(W0, FLIGHT)
    M0 = unary_union([poly_m(key, m['o'], m['h']) for m in T['mullions']]) if T['mullions'] else Polygon()
    lows = [(b, band_m(key, b['line'], b['w'])) for b in T.get('lowWalls', [])]
    LW = unary_union([g for _, g in lows]) if lows else Polygon()
    counters = [fk.rect_of(bx) for bx in (fk.box_of(pts_m(key, pc['outline'])) for pc in T['furniture'] if pc['kind'] == 'counter') if bx]
    # rule 4: glazing
    panes = []
    for g in T['glazing']:
        (ax_, ay_), (bx_, by_) = g['line']
        u = unit((bx_ - ax_, by_ - ay_))
        line = [(ax_ - u[0] * 2, ay_ - u[1] * 2), (bx_ + u[0] * 2, by_ + u[1] * 2)]
        pane = LineString(pts_m(key, line)).buffer(GLASS_T / 2, cap_style='flat').difference(unary_union([W0, M0]).buffer(0.001))
        panes.append((g, pane))
    G0 = unary_union([p for _, p in panes]) if panes else Polygon()
    # rule 5: openings and hatches
    recs = []
    for o in T['openings'] + T.get('hatches', []):
        a, b = m_of(key, *o['a']), m_of(key, *o['b'])
        u = unit((b[0] - a[0], b[1] - a[1])); w_drawn = math.dist(a, b); t = max(across_m(key, o['a'], o['b'], o['t']), 0.02)
        if o.get('lift'):
            c = ((a[0] + b[0]) / 2, (a[1] + b[1]) / 2); half = DEF['liftDoorWidth'] / 2
            a, b = (c[0] - u[0] * half, c[1] - u[1] * half), (c[0] + u[0] * half, c[1] + u[1] * half)
        w = math.dist(a, b)
        rec = {'o': o, 'a': a, 'b': b, 'u': u, 'n': (-u[1], u[0]), 'w': w, 't': t, 'drawn': w_drawn,
               'foot': rect(a, u, 0, w, -(t / 2 + CUT_MARGIN), t / 2 + CUT_MARGIN), 'span': rect(a, u, 0, w, -t / 2 - 0.02, t / 2 + 0.02)}
        if o.get('lift') and w_drawn > w + 0.005:            # the drawn gap is wider than the door: wall back at its two ends
            a0 = (a[0] - u[0] * (w_drawn - w) / 2, a[1] - u[1] * (w_drawn - w) / 2)
            rec['fill'] = [rect(a0, u, 0, (w_drawn - w) / 2, -t / 2, t / 2), rect(b, u, 0, (w_drawn - w) / 2, -t / 2, t / 2)]
        recs.append(rec)
    fills = [f for r in recs for f in r.get('fill', [])]
    if fills: W0 = unary_union([W0] + fills)
    hatch_pieces = [(r, W0.intersection(r['foot'])) for r in recs if r['o'].get('hatch')]
    CUT = unary_union([r['foot'] for r in recs if r['o']['kind'] in ('door', 'window')]) if recs else Polygon()
    Wc, Gc, Mc = W0.difference(CUT), G0.difference(CUT), M0.difference(CUT)
    SOL = unary_union([Wc, Gc, Mc])
    solid = SOL.buffer(0.001)
    for r in recs:                                       # rule 5: the built jambs (the lift doors are exact already)
        if r['o']['kind'] in ('door', 'passage') and not r['o'].get('lift'): fit_to_jambs(r, SOL)

    def mat(p):
        P = Point(p)
        if Wc.distance(P) <= 0.01 or Mc.distance(P) <= 0.01: return 'wall'
        if Gc.distance(P) <= 0.01: return 'glass'
        return None
    extra = []                                           # (kind, polygon, z0, z1, follow, label)
    for r in recs:
        o, a, u, w, t = r['o'], r['a'], r['u'], r['w'], r['t']
        if o['kind'] != 'door': continue
        r['head'] = DEF['doorHead']
        r['jambs'] = (mat((a[0] - u[0] * 0.03, a[1] - u[1] * 0.03)), mat((a[0] + u[0] * (w + 0.03), a[1] + u[1] * (w + 0.03))))   # 3 cm beyond each jamb
        r['lintel'], r['lintelTop'] = None, None
        ja, jb = r['jambs']
        if r['head'] < top - 0.005 and (ja or jb):
            kind = 'glass' if ja == jb == 'glass' else 'lintel'
            piece = (r['gap'] if 'gap' in r else rect(a, u, 0, w, -t / 2, t / 2)).difference(solid)
            ps = [p for p in polys(piece) if p.area > (0.002 if kind == 'lintel' else 0.0005)]
            if ps:
                r['lintel'], r['lintelTop'] = ('transom' if kind == 'glass' else 'lintel'), top
                for p in ps: extra.append((kind, p, r['head'], top, True, o['id'] + (' transom' if kind == 'glass' else '')))
    for r, piece in hatch_pieces:                        # rule 5: a hatch keeps its wall below the sill and above the head
        under = [g for g in counters if g.intersection(piece).area > 1e-4]       # a counter standing in it: the sill is its top
        r['sill'], r['head'] = (COUNTER_TOP if under else DEF['hatchSill']), DEF['hatchHead']
        r['sillFrom'] = 'the top of the counter standing in it' if under else 'project default (assumed)'
        for p in polys(piece):
            if p.area <= 0.0005: continue
            extra.append(('sill', p, 0.0, r['sill'], False, r['o']['id'] + ' below the hatch'))
            extra.append(('lintel', p, r['head'], top, True, r['o']['id'] + ' above the hatch'))
        r['jambs'], r['lintel'], r['lintelTop'] = (mat(r['a']), mat(r['b'])), 'lintel', top
    # rule 6: stairs
    steps, lines, voids, rails, outlines = [], [], [], [], []
    riser = H / DEF['risers']
    for s in T['stairs']:
        x0, y0, x1, y1 = s['rect']
        outline = Polygon(pts_m(key, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]))
        if s['build'] == 'steps':
            F = FLIGHT
            goings = DEF['risers'] - 1
            run = (F['yt'] - F['yb']) / goings
            for j in range(1, goings + 1):
                lo, hi = F['yb'] + (j - 1) * run, F['yb'] + j * run
                steps.append((sbox(F['x0'], lo, F['x1'], hi), R3((j - 2) * riser), R3(j * riser), f"{s['id']} step {j} up"))
            outlines.append({'id': s['id'], 'poly': sbox(F['x0'], F['yb'], F['x1'], F['yt']), 'flights': 1, 'withWord': 1,
                             'run': R3(F['yt'] - F['yb']), 'going': R3(run), 'riser': R3(riser), 'width': R3(F['x1'] - F['x0']),
                             'drawnTreads': len(s['treadLines']), 'drawnSpacing': R3(s['spacing'] / PX[key][1]) if s['spacing'] else None,
                             'bottomMovedNorth': R3(F['yb'] - F['ybDrawn'])})
        elif s['build'] == 'steps-up':
            if s['up'] != 'north' or s['treadAxis'] != 'y': raise SystemExit(f"{s['id']}: steps-up are built for 'up': 'north' only")
            sw_ = s.get('width') or {}                                          # the side walls' inner faces, when measured
            xa, xb = m_of(key, sw_.get('west', x0), 0)[0], m_of(key, sw_.get('east', x1), 0)[0]
            ys_ = sorted(m_of(key, 0, v)[1] for v in s['treadLines'])           # the riser lines, south to north
            sides_were = (xa, xb)
            xa, xb = onto_faces(Wc, xa, xb, ys_[0], ys_[-1])                    # ... on the wall faces as built
            for j in range(1, len(ys_)):
                steps.append((sbox(xa, ys_[j - 1], xb, ys_[j]), R3(max(j - 2, 0) * riser), R3(j * riser), f"{s['id']} step {j} up (to a floor 3, not drawn)"))
            outlines.append({'id': s['id'], 'poly': sbox(xa, ys_[0], xb, ys_[-1]), 'flights': 1, 'withWord': 1, 'run': R3(ys_[-1] - ys_[0]),
                             'going': R3((ys_[-1] - ys_[0]) / (len(ys_) - 1)), 'riser': R3(riser), 'width': R3(xb - xa),
                             'steps': len(ys_) - 1, 'top': R3((len(ys_) - 1) * riser), 'drawnTreads': len(s['treadLines']),
                             'endsInTheAir': True, 'sidesFrom': 'the side walls\' inner faces (rule 11)' if sw_ else 'the take-off rectangle',
                             'sidesMovedOntoWallFaces': [R3(sides_were[0] - xa), R3(xb - sides_were[1])],
                             'drawnClearWidth': R3((sw_['east'] - sw_['west']) / PX[key][0]) if sw_ else None})
        else:
            if s['build'] == 'lines':
                for v in s['treadLines']:
                    seg = [(x0, v), (x1, v)] if s['treadAxis'] == 'y' else [(v, y0), (v, y1)]
                    lines.append(LineString(pts_m(key, seg)))
            outlines.append({'id': s['id'], 'poly': outline, 'flights': 1, 'withWord': 1 if s['build'] != 'lines' or s.get('up') else 0,
                             'drawnTreads': len(s['treadLines']),
                             'drawnSpacing': R3(s['spacing'] / PX[key][0 if s['treadAxis'] == 'x' else 1]) if s['spacing'] else None})
        if s['build'] == 'void':
            F = FLIGHT
            vx0, vx1, vy0, vy1 = F['x0'], F['x1'], F['yb'], F['yt']
            voids.append(('stair', sbox(vx0, vy0, vx1, vy1)))
            outlines[-1].update(poly=sbox(vx0, vy0, vx1, vy1), drawnWidth=R3(m_of(key, s['width']['eastInner'], 0)[0] - m_of(key, s['width']['westInner'], 0)[0]) if s.get('width') else None)
            side = {'west': sbox(vx0 - RAIL_W, vy0 - RAIL_W, vx0, vy1), 'east': sbox(vx1, vy0 - RAIL_W, vx1 + RAIL_W, vy1),
                    'south': sbox(vx0 - RAIL_W, vy0 - RAIL_W, vx1 + RAIL_W, vy0), 'north': sbox(vx0 - RAIL_W, vy1, vx1 + RAIL_W, vy1 + RAIL_W)}
            for sd in s.get('railings', []):
                rails.append((side[sd], DEF['railingHeight'], f"railing at the open stair, {sd}"))
    # rule 7: shafts
    shafts = []
    for sh in T['shafts']:
        x0, y0, x1, y1 = sh['rect']
        g = Polygon(pts_m(key, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]))
        shafts.append((sh, g))
        if not lowest and not sh.get('closed'): voids.append((sh['what'], g))
    # rule 8: floor plates (a closing line's ends are joined to the wall, glass or post within 15 cm of them)
    closes = []
    for c in T['plateClose']:
        pts = pts_m(key, c['line'])
        bits = [LineString(pts)]
        for end in (pts[0], pts[-1]):
            d_ = SOL.distance(Point(end))
            if 0 < d_ <= CLOSE_JOIN:
                q = nearest_points(SOL, Point(end))[0]
                bits.append(LineString([end, (q.x, q.y)]))
        closes.append(unary_union([b.buffer(CLOSE_W / 2, cap_style='square') for b in bits]))
    edge_walls = []                                      # rule 8: a closing at the picture's cut edge marked 'wall': a wall just beyond it
    pw, ph = T['picture']['size']
    pic = Polygon(pts_m(key, [(0, 0), (pw, 0), (pw, ph), (0, ph)]))
    for c in T['plateClose']:
        if not c.get('wall'): continue
        A, B = m_of(key, *c['line'][0]), m_of(key, *c['line'][-1])
        uu = unit((B[0] - A[0], B[1] - A[1])); nn = (-uu[1], uu[0]); mid = ((A[0] + B[0]) / 2, (A[1] + B[1]) / 2)
        out_ = -1 if pic.contains(Point(mid[0] + nn[0] * 0.05, mid[1] + nn[1] * 0.05)) else 1      # the side off the picture
        g = rect(A, uu, 0, math.dist(A, B), min(0.0, out_ * DEF['pictureEdgeWall']), max(0.0, out_ * DEF['pictureEdgeWall'])).difference(W0)
        edge_walls += [(p, c['wall']) for p in polys(g) if p.area > 0.002]
    E = unary_union([Wc, Gc, Mc] + [x[1] for x in extra] + [r['span'] for r in recs] + closes + [g for g, _ in edge_walls])
    E = E.buffer(PLATE_GAP, join_style='mitre').buffer(-PLATE_GAP, join_style='mitre')
    inner = unary_union([Polygon(p.exterior) for p in polys(E) if Polygon(p.exterior).area > 4])
    terrace = None
    if 'terrace' in T:                                   # rule 8: floor 2's terrace, on to floor 1's outline of the floor above
        ao = next(TK[k]['aboveOutline'] for k in KEYS if 'aboveOutline' in TK[k])
        ok_ = next(k for k in KEYS if 'aboveOutline' in TK[k])
        tw, tn, tf = m_of(key, T['terrace']['west'], 0)[0], m_of(key, 0, T['terrace']['north'])[1], m_of(key, T['terrace']['eastFacade'], 0)[0]
        near_t = Wc.intersection(sbox(-1e3, tn - 0.1, 1e3, tn + 2.0))    # the walls just north of the terrace: its edges in line with
        fw, fe = (near_t.bounds[0], near_t.bounds[2]) if not near_t.is_empty else (tw, tf)   # the facades' outer faces there
        if abs(tw - fw) <= CLOSE_JOIN: tw = fw
        if abs(tf - fe) <= CLOSE_JOIN: tf = fe
        te, ts = m_of(ok_, ao['east'], 0)[0], m_of(ok_, 0, ao['south'])[1]
        terrace = {'poly': sbox(tw, ts, te, tn), 'west': tw, 'east': te, 'south': ts, 'north': tn, 'eastFacade': tf,
                   'wrapNorthFloor1': m_of(ok_, 0, ao['wrapNorth'])[1], 'outlineWest': m_of(ok_, ao['west'], 0)[0]}
        inner = unary_union([inner, terrace['poly']])
    V = unary_union([v for _, v in voids]) if voids else Polygon()
    plate = inner.difference(V.buffer(0.001)) if voids else inner
    plates = [Polygon(p.exterior, [h for h in p.interiors if Polygon(h).area >= 0.5]).simplify(0.02).buffer(SLAB_EDGE, join_style='mitre')
              for p in polys(plate) if p.area > 4]
    if voids: plates = [x for p in plates for x in polys(p.difference(V.buffer(0.001)))]
    plate_u = unary_union(plates) if plates else Polygon()
    forecourt = None
    if 'forecourt' in T:                                 # rule 8: floor 1's forecourt, an outdoor slab at 0.00
        x0, y0, x1, y1 = T['forecourt']['rect']
        fcp = Polygon(pts_m(key, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)])).difference(plate_u.buffer(0.0005))
        forecourt = [p.simplify(0.02) for p in polys(fcp) if p.area > 1.0]
    if terrace:                                          # rule 8: a railing on the terrace's open edges, each run on to the walls
        tw, te, ts, tn, tf = terrace['west'], terrace['east'], terrace['south'], terrace['north'], terrace['eastFacade']
        edge = [(tw, ts, tw + RAIL_W, tn), (tw, ts, te, ts + RAIL_W), (te - RAIL_W, ts, te, tn), (tf, tn - RAIL_W, te, tn)]
        for e in edge:
            for p in polys(run_to_walls(e, Wc, CLOSE_JOIN).difference(Wc)):
                if p.area > 0.002: rails.append((p, DEF['terraceRailingHeight'], 'railing at the terrace edge'))
    # 'below' lines: none over a void, cut where a wall or a low wall stands
    lines_out = []
    for ln in lines:
        rest = ln.difference(unary_union([Wc, LW, V]).buffer(0.001)) if (not Wc.is_empty or voids or lows) else ln
        for seg in ([rest] if rest.geom_type == 'LineString' else list(getattr(rest, 'geoms', []))):
            if seg.length > 0.05: lines_out.append(list(seg.coords[0]) + list(seg.coords[-1]))
    # the parts
    for p in polys(Wc):
        if p.area > 0.002: parts_geo.append((key, 'wall', p, 0.0, top, True, None))
    for p, label in edge_walls: parts_geo.append((key, 'wall', p, 0.0, top, True, label))
    for b, g in lows:
        for p in polys(g.difference(Wc)):
            if p.area > 0.002: parts_geo.append((key, 'parapet', p, 0.0, DEF['railingHeight'], False, b.get('label') or 'low wall'))
    for p in polys(Mc):
        if p.area > 0.0002: parts_geo.append((key, 'mullion', p, 0.0, top, True, 'mullion'))
    for g, pane in panes:
        for p in polys(pane.difference(CUT)):
            if p.area > 0.0005: parts_geo.append((key, 'glass', p, 0.0, top, True, g['id'] + ' glazing'))
    for kind, p, z0, z1, follow, label in extra: parts_geo.append((key, kind, p, z0, z1, follow, label))
    for p, h, label in rails: parts_geo.append((key, 'railing', p, 0.0, h, False, label))
    for poly, z0, z1, label in steps: parts_geo.append((key, 'step', poly, z0, z1, False, label))
    for p in plates: parts_geo.append((key, 'slab', p, -DEF['slabThickness'], 0.0, False, None))
    for p in forecourt or []: parts_geo.append((key, 'slab', p, -DEF['slabThickness'], 0.0, False, 'forecourt (outdoor paving, assumed)'))
    built[key] = {'recs': recs, 'lines': lines_out, 'voids': voids, 'outlines': outlines, 'shafts': shafts, 'plates': plates,
                  'plate_u': plate_u, 'steps': steps, 'rails': rails, 'panes': panes, 'riser': riser, 'terrace': terrace,
                  'forecourt': forecourt, 'fills': len(fills), 'liftDrawn': [R3(r['drawn']) for r in recs if r['o'].get('lift')],
                  'carried': carried, 'edgeWalls': [(R3(p.area), label) for p, label in edge_walls],
                  'lows': [(b.get('label'), R3(g.area)) for b, g in lows]}
    print(f"{key}: {len(polys(Wc))} wall pieces, {len(polys(Mc))} mullions, {len(panes)} glazing lines, {len(recs)} openings "
          f"{dict(collections.Counter(r['o']['kind'] for r in recs))}, lintels {sum(1 for x in extra if x[0] == 'lintel')}, "
          f"sills {sum(1 for x in extra if x[0] == 'sill')}, transoms {sum(1 for x in extra if x[0] == 'glass')}, {len(steps)} steps "
          f"(riser {riser:.3f} m), {len(lines_out)} tread lines, {len(rails)} railings, voids {[(w, round(v.area, 2)) for w, v in voids]}, "
          f"plate {sum(p.area for p in plates):.1f} m2" + (f", forecourt {sum(p.area for p in forecourt):.1f} m2" if forecourt else ''))

# ---------------------------------------------------------------------------------------------------- centre, clean, write
allp = unary_union([p for _, kd, p, _, _, _, _ in parts_geo if kd == 'slab'])
minx, miny, maxx, maxy = allp.bounds
cx, cy = R3((minx + maxx) / 2), R3((miny + maxy) / 2)
parts, counts = [], collections.defaultdict(collections.Counter)
for key, kind, p, z0, z1, follow, label in parts_geo:
    min_area = {'slab': 1.0, 'glass': 0.0002, 'mullion': 0.0002, 'lintel': 0.002, 'railing': 0.0005, 'sill': 0.0005}.get(kind, 0.002)
    for r in clean([p], min_area, cx, cy):
        assert Polygon(r['o'], r['h']).is_valid, (key, kind, label)
        parts.append({'floor': key, 'kind': kind, 'z0': R3(z0), 'z1': R3(z1), 'follow': follow, **r, **({'label': label} if label else {})})
        counts[key][kind] += 1

# rule 11: where a person can stand (the model frame)
plates_by = {k: unary_union([Polygon(p['o'], p['h']) for p in parts if p['floor'] == k and p['kind'] == 'slab']) for k in KEYS}
solid_parts = {k: [(p, Polygon(p['o'], p['h'])) for p in parts if p['floor'] == k and (p['kind'] in BLOCKING or p['kind'] == 'step') and p['z0'] < 1.5]
               for k in KEYS}
solid_by = {k: unary_union([g for _, g in solid_parts[k]]) for k in KEYS}


def stand(k, x, y):
    """A spot (model frame) on floor k's plate with STAND_CLEAR of room to everything solid."""
    P = Point(x, y)
    return plates_by[k].contains(P) and solid_by[k].distance(P) >= STAND_CLEAR


openings, probes = [], []
for key in KEYS:
    for r in built[key]['recs']:
        o, a, u, nrm, w = r['o'], r['a'], r['u'], r['n'], r['w']
        mx_, my_ = a[0] + u[0] * w / 2 - cx, a[1] + u[1] * w / 2 - cy
        sides = [any(stand(key, mx_ + nrm[0] * sd * b, my_ + nrm[1] * sd * b) for b in (0.9, 0.7, 0.55, 0.45, 0.4)) for sd in (1, -1)]
        rec = {'id': o['id'], 'floor': key, 'kind': o['kind'], 'subtype': o['subtype'], 'x': R3(mx_), 'y': R3(my_),
               'nx': R3(nrm[0]), 'ny': R3(nrm[1]), 'width': R3(w), 'wallThickness': R3(r['t']), 'eitherKind': False,
               'inside': [sd for sd, ok in zip((1, -1), sides) if ok], 'label': o.get('label', ''), 'drawnWidth': R3(r['drawn'])}
        if o['kind'] == 'door':
            rec.update(head=R3(r['head']), headFrom='project default (assumed)', lintel=r['lintel'],
                       lintelTop=R3(r['lintelTop']) if r['lintelTop'] else None, glassDoor=r['jambs'] == ('glass', 'glass'),
                       liftDoor=bool(o.get('lift')), jambs=list(r['jambs']), lintelDepth=[R3(-r['t'] / 2), R3(r['t'] / 2)])
        elif o.get('hatch'):
            rec.update(sill=R3(r['sill']), sillFrom=r['sillFrom'], head=R3(r['head']), headFrom='project default (assumed)', curtain=False, glass=False, hatch=True,
                       lintel='lintel', lintelTop=R3(r['lintelTop']), jambs=list(r['jambs']), lintelDepth=[R3(-r['t'] / 2), R3(r['t'] / 2)])
        rec['exterior'] = len(rec['inside']) == 1
        openings.append(rec)
    # drawn glass (rule 4): a probe at the middle of each pane, for the tests to walk into, on the sides a person can stand on
    for p in parts:
        if p['floor'] != key or p['kind'] != 'glass' or p['z0'] > 0.01 or (p.get('label') or '').endswith(' transom'): continue
        g = Polygon(p['o'], p['h'])
        mrr = list(g.minimum_rotated_rectangle.exterior.coords)[:4]
        e1, e2 = math.dist(mrr[0], mrr[1]), math.dist(mrr[1], mrr[2])
        if max(e1, e2) < 0.6: continue
        a0, a1 = (mrr[0], mrr[1]) if e1 >= e2 else (mrr[1], mrr[2])
        uu = unit((a1[0] - a0[0], a1[1] - a0[1])); nn = (-uu[1], uu[0])
        c = g.representative_point()
        others = unary_union([q for pp, q in solid_parts[key] if pp is not p])
        side = []
        for sd in (1, -1):
            for b in (1.0, 0.8, 0.6):
                sx, sy = c.x + nn[0] * sd * b, c.y + nn[1] * sd * b
                path = LineString([(c.x + nn[0] * sd * GLASS_T, c.y + nn[1] * sd * GLASS_T), (sx, sy)]).buffer(0.25, cap_style='flat')
                if stand(key, sx, sy) or (plates_by[key].contains(Point(sx, sy)) and others.distance(Point(sx, sy)) >= STAND_CLEAR):
                    if others.intersection(path).area < 1e-4:
                        side.append(sd); break
        if not side: continue
        probes.append({'floor': key, 'id': f"{key} glass {len(probes) + 1}", 'what': 'glazing', 'x': R3(c.x), 'y': R3(c.y),
                       'nx': R3(nn[0]), 'ny': R3(nn[1]), 'inside': side, 'top': p['z1'], 'label': p.get('label')})

# Self-checks (rule 12): in every door and passage, nothing that stops you below the head crosses the opening's line; in a hatch,
# nothing between its sill and its head.
blockers = collections.defaultdict(list)
for p in parts:
    if p['kind'] in BLOCKING: blockers[p['floor']].append((p['z0'], p['z1'], Polygon(p['o'], p['h'])))
blocked = []
for rec in openings:
    ux, uy = rec['ny'], -rec['nx']
    h = rec['width'] / 2 * 0.8
    a0 = (rec['x'] - ux * h, rec['y'] - uy * h)
    if rec['kind'] == 'passage':
        zone, zlo, zhi = LineString([a0, (rec['x'] + ux * h, rec['y'] + uy * h)]), 0.0, 1.5
    else:
        zone = rect(a0, (ux, uy), 0, 2 * h, -(rec['wallThickness'] / 2 + 0.02), rec['wallThickness'] / 2 + 0.02)     # the wall's band (+2 cm)
        zlo, zhi = (rec['sill'] + 0.001, rec['head'] - 0.001) if rec.get('hatch') else (0.0, 1.5)
    hits = [g for z0, z1, g in blockers[rec['floor']] if z0 < zhi and z1 > zlo and g.intersects(zone)
            and (zone.geom_type == 'LineString' or g.intersection(zone).area > 1e-5)]
    if hits: blocked.append((rec['id'], rec['kind'], len(hits)))
print('self-check: openings with something solid across them:', blocked or 'none')

# Walk-collision skins (viewer only, as in the bank): thin colliders (panes, rails) get an invisible 8 cm skin up to 2 m, cut out of
# every door's and passage's footprint (rule 11).
door_cut = collections.defaultdict(list)
for key in KEYS:
    for r in built[key]['recs']:
        if r['o']['kind'] in ('door', 'passage'):
            a = (r['a'][0] - cx, r['a'][1] - cy)
            door_cut[key].append(rect(a, r['u'], 0, r['w'], -(r['t'] / 2 + 0.25), r['t'] / 2 + 0.25))
door_cut = {k: unary_union(v) for k, v in door_cut.items()}
skins = collections.defaultdict(list)
for p in parts:
    if p['kind'] not in BLOCKING or p['z0'] >= 1.5: continue
    g = Polygon(p['o'], p['h'])
    thin = g.difference(g.buffer(-SKIN / 2, join_style='mitre').buffer(SKIN / 2, join_style='mitre'))
    thin = [q for q in polys(thin) if q.area > 0.0002 and q.length > 0.12]
    if not thin: continue
    skin = unary_union(thin).buffer(0.035, join_style='mitre')
    if p['floor'] in door_cut: skin = skin.difference(door_cut[p['floor']])
    for r in clean([skin], 0.0005, 0, 0):
        skins[p['floor']].append({**r, 'z0': p['z0'], 'z1': R3(min(p['z1'], 2.0)), 'glass': p['kind'] == 'glass'})

rooms_out = []
for key in KEYS:
    for r in TK[key]['rooms']:
        x, y = m_of(key, *r['at'])
        rooms_out.append({'floor': key, 'name': r['name'], 'label': r['name'], 'area': None, 'x': R3(x - cx), 'y': R3(y - cy),
                          **({'callout': True} if r.get('callout') else {})})

# rule 10: the furniture boxes
furn_pieces = []
for key in KEYS:
    for pc in TK[key]['furniture']:
        bx = fk.box_of(pts_m(key, pc['outline']))
        if bx is None: raise SystemExit(f"{pc['id']}: its outline encloses no area")
        note = '; '.join(x for x in (pc.get('note', ''), f"take-off {pc['id']}") if x)
        furn_pieces.append({'floor': key, 'kind': pc['kind'], 'family': pc['family'], 'block': '', 'layer': 'picture', 'handle': '',
                            **{**bx, 'x': bx['x'] - cx, 'y': bx['y'] - cy}, 'on': None, 'n': pc.get('n', 1), 'note': note})
try:
    furniture, furn_kinds = fk.finish(furn_pieces, KEYS, FURN.get('heights'), FURN.get('bases'), openings)
except ValueError as e:
    raise SystemExit(f'{CFG_PATH.name}: {e}')
approach = {k: {'pieces': sum(1 for p in furniture if p['floor'] == k and p['approach']),
                'openingIds': sorted({o for p in furniture if p['floor'] == k for o in p['approach']})} for k in KEYS}
for k in KEYS:
    mine = collections.Counter(p['kind'] for p in furniture if p['floor'] == k)
    print(f"{k}: {sum(mine.values())} furniture boxes {dict(mine)} | {approach[k]['pieces']} in the approach of "
          f"{len(approach[k]['openingIds'])} doors / passages {approach[k]['openingIds']} | on a support: "
          f"{sum(1 for p in furniture if p['floor'] == k and p['on'])}")

flat = lambda segs, nd=3: [round(v - (cx if i % 2 == 0 else cy), nd) for s in segs for i, v in enumerate(s)]
frame = {k: {'file': TK[k]['picture']['file'], 'size': TK[k]['picture']['size'],
             'pxPerMetreX': round(PX[k][0], 4), 'pxPerMetreY': round(PX[k][1], 4),
             'originPx': [round(ORIGIN[k][0], 3), round(ORIGIN[k][1], 3)], 'yDown': True,
             '_': 'picture pixel x = originPx[0] + pxPerMetreX * (model x + offset x), y = originPx[1] - pxPerMetreY * (model y + offset y); '
                  'the picture is a plane size[0] / pxPerMetreX by size[1] / pxPerMetreY metres'} for k in KEYS}
model = {
    'project': CFG['project'], 'shortName': CFG.get('shortName', CFG['project']), 'projectNo': CFG.get('projectNo'),
    'source': CFG['source'],
    'units': 'm', 'offset': [cx, cy], 'photoName': CFG.get('photoName', 'Model'), 'maxPrefix': CFG.get('maxPrefix', 'M'),
    'floors': [{'key': f['key'], 'name': f['name'], 'level': f['level'], 'wallHeight': f['wallHeight'],
                'slabThickness': DEF['slabThickness']} for f in CFG['floors']],
    'railingHeight': DEF['railingHeight'], 'singleLineHeight': DEF['singleLineHeight'], 'doorHeadDefault': DEF['doorHead'],
    'pictureFrame': frame,
    'parts': parts,
    'stairs': {k: {'below': flat(built[k]['lines']), 'above': []} for k in KEYS},
    'voids': {k: [{'what': w, 'x': R3(v.representative_point().x - cx), 'y': R3(v.representative_point().y - cy),
                   'area': round(v.area, 2)} for w, v in built[k]['voids']] for k in KEYS},
    'closures': {k: [] for k in KEYS},
    'stairOutlines': {k: [{'id': s['id'], 'x': R3(s['poly'].representative_point().x - cx), 'y': R3(s['poly'].representative_point().y - cy),
                           'bbox': [R3(v - (cx if i % 2 == 0 else cy)) for i, v in enumerate(s['poly'].bounds)],
                           'flights': s['flights'], 'withWord': s['withWord']} for s in built[k]['outlines']] for k in KEYS},
    'rooms': rooms_out, 'openings': openings, 'probes': probes, 'colliderSkins': skins,
    'furnitureKinds': furn_kinds, 'furniture': furniture,
}
out_model = HERE / 'hotel_model.json'
out_model.write_text(json.dumps(model, separators=(',', ':'), ensure_ascii=False), encoding='utf-8')

# ---------------------------------------------------------------------------------------------------- rule 12: checks, summary
F = FLIGHT
soffit = FLOOR[F['voidFloor']]['level'] - DEF['slabThickness']
f2_plate = unary_union([Polygon(p['o'], p['h']) for p in parts if p['floor'] == F['voidFloor'] and p['kind'] == 'slab'])
f1_steps = [p for p in parts if p['floor'] == F['floor'] and p['kind'] == 'step' and (p.get('label') or '').startswith(F['id'])]
under = [(p, Polygon(p['o'], p['h']).intersection(f2_plate).area) for p in f1_steps]
void_poly = next(v for w, v in built[F['voidFloor']]['voids'] if w == 'stair')
f1_walls = unary_union([Polygon(p['o'], p['h']) for p in parts if p['floor'] == F['floor'] and p['kind'] == 'wall'])
vx0, vy0, vx1, vy1 = [v - (cx if i % 2 == 0 else cy) for i, v in enumerate(void_poly.bounds)]
slot, slot_at = {}, {}                                  # the widest slot beside the flight, every 0.1 m along its whole run
ys_probe = [vy0 + 0.05 + k * 0.1 for k in range(int((vy1 - vy0 - 0.1) / 0.1) + 1)]
for sd, x_edge, sgn in (('west', vx0, -1), ('east', vx1, 1)):
    worst = max(((runs_along(f1_walls, (x_edge, y), (sgn, 0.0), 0.0, 0.6) or [(0.6, 0.6)])[0][0], y) for y in ys_probe)
    slot[sd], slot_at[sd] = R3(worst[0]), R3(worst[1])
stair_check = {'flight': [R3(F['x0'] - cx), R3(F['yb'] - cy), R3(F['x1'] - cx), R3(F['yt'] - cy)], 'floor2Void': [R3(vx0), R3(vy0), R3(vx1), R3(vy1)],
               'flightWidth': R3(F['x1'] - F['x0']), 'stepAreaUnderFloor2Slab': R3(sum(a for _, a in under)),
               'stepsUnderSlab': [p['label'] for p, a in under if a > 1e-4], 'topStepTop': max(p['z1'] for p in f1_steps) if f1_steps else None,
               'soffit': R3(soffit), 'slotBesideFlight': slot, 'slotBesideFlightWidestAtY': slot_at, 'slotProbes': len(ys_probe),
               'sideWallsCarriedOn': built[F['floor']]['carried'], 'bottomRiserMovedNorth': R3(F['yb'] - F['ybDrawn']),
               'drawnBottomTreadLineY': R3(F['ybDrawn'] - cy)}
print('stair: floor 1 flight under floor 2', stair_check)
core_boxes = {}
for k in KEYS:
    lifts = [g for sh, g in built[k]['shafts'] if sh['what'].startswith('lift')]
    core_boxes[k] = [R3(v) for v in unary_union(lifts).bounds] if lifts else None
f1_w = [p for p in parts if p['floor'] == 'F1' and p['kind'] == 'wall']
f1_ext = [min(q[0] for p in f1_w for q in p['o']), min(q[1] for p in f1_w for q in p['o']), max(q[0] for p in f1_w for q in p['o']), max(q[1] for p in f1_w for q in p['o'])]
sw2 = next((s['width'] for s in TK['F2']['stairs'] if s.get('width') and s['build'] == 'void'), None)     # floor 2's stringers (a check)
by_family = collections.defaultdict(list)
for p in furniture: by_family[(p['floor'], p['family'])].append([R3(p['w']), R3(p['d'])])
term = TK['F1'].get('aboveOutline')
summary = {
    'scale': {'method': method, 'axes': axes, 'stairWidthM': scale_cfg['stairWidth'], 'stairClearPx': W1,
              'floor2ToFloor1Px': {'x': round(SX, 5), 'y': round(SY, 5), 'oneRatio': round(S1, 5)},
              'pxPerMetre': {k: {'x': round(PX[k][0], 3), 'y': round(PX[k][1], 3)} for k in KEYS},
              'floor1DrawnWiderThanTall': round(SX / SY, 4),
              'liftDoorsPx': door_px, 'liftDoorsHalfWayPx': {k: [d['halfWay'] for d in TK[k]['liftDoors']] for k in KEYS},
              'liftDoorsAtThisScaleM': {k: [R3(w / PX[k][1]) for w in door_px[k]] for k in KEYS},
              'liftDoorsMeanAtThisScaleM': R3(statistics.mean([w / PX[k][1] for k in KEYS for w in door_px[k]])),
              'liftShaftsInsideM': {k: [R3((F_[('shaft east inside face', 'x')] - F_[('shaft west inside face', 'x')]) / PX[k][0]),
                                        R3((F_[('lift 1 south inside face', 'y')] - F_[('lift 1 north inside face', 'y')]) / PX[k][1]),
                                        R3((F_[('lift 2 south inside face', 'y')] - F_[('lift 2 north inside face', 'y')]) / PX[k][1])]
                                    for k, F_ in (('F1', F1F), ('F2', F2F))},
              'stairs': {'floor1ClearM': R3(W1 / PX['F1'][0]),
                         'floor1OverSideWallsM': R3(stair_ref['width']['overWalls'] / PX['F1'][0]) if 'overWalls' in stair_ref['width'] else None,
                         'floor2BetweenStringersM': R3(sw2['clear'] / PX['F2'][0]) if sw2 else None,
                         'floor2OverStringersM': R3(sw2['overStringers'] / PX['F2'][0]) if sw2 else None},
              'otherMethods': {m: {'floor2PxPerM': round(k2_for(m), 3), 'modelSizeAgainstThisScale': round(K2 / k2_for(m), 4)} for m in ('cores', 'doors-floor1')},
              'coreFitResiduals': resid, 'coreFitResidualMaxPx': {'perAxis': R3(max(abs(r['floor1Px'] - r['floor2PxOnFloor1']) for r in resid)),
                                                                   'oneRatio': R3(max(resid_one))}},
    'origin': {k: [round(v, 3) for v in ORIGIN[k]] for k in KEYS}, 'offset': [cx, cy], 'liftShaftsBounds': core_boxes,
    'floor1WallsExtentM': {'x': R3(f1_ext[2] - f1_ext[0]), 'y': R3(f1_ext[3] - f1_ext[1]),
                           '_': 'all of floor 1\'s walls: the stair bay north of the north wall and the RED BOX south of the facade included'},
    'floor1MainBoxM': {'x': R3((F1F[('core east face', 'x')] - min(q[0] for w in TK['F1']['walls'] for q in w['o'])) / PX['F1'][0]),
                       'y': R3((max(q[1] for w in TK['F1']['walls'] for q in w['o'] if q[0] < 445)
                                - min(q[1] for w in TK['F1']['walls'] for q in w['o'] if 620 < q[0] < 860)) / PX['F1'][1]),
                       '_': 'west face to the core\'s east face, and the north wall\'s outer face to the south wall stubs\' outer faces'},
    'floor2OutlineOnFloor1': ({'westLineM': R3(m_of('F1', term['west'], 0)[0] - cx), 'floor2WestFacadeM': R3(built['F2']['terrace']['west'] - cx) if built['F2']['terrace'] else None,
                               'southLineM': R3(m_of('F1', 0, term['south'])[1] - cy), 'eastLineM': R3(m_of('F1', term['east'], 0)[0] - cx),
                               'wrapNorthM': R3(m_of('F1', 0, term['wrapNorth'])[1] - cy)} if term else None),
    'furnitureSizes': {f'{k} {fam}': sorted(v) for (k, fam), v in sorted(by_family.items())
                       if fam in ('armchair', '3-seat sofa', 'dining chair', 'bar stool', 'chair', 'sculptural seating', 'built-in bench',
                                  'round sofa', 'check-in sofa', 'sofa', 'seat back', 'worktop')},
    'stairCheck': stair_check, 'blocked': blocked, 'floors': {},
}
for k in KEYS:
    ops = [o for o in openings if o['floor'] == k]
    summary['floors'][k] = {
        'counts': dict(counts[k]), 'openings': dict(collections.Counter(o['kind'] for o in ops)),
        'doorsWith': dict(collections.Counter(o.get('lintel') or 'no lintel' for o in ops if o['kind'] == 'door')),
        'exterior': [o['id'] for o in ops if o['exterior']],
        'oneSided': {o['id']: o['inside'] for o in ops if len(o['inside']) < 2},
        'liftDoorsDrawnM': built[k]['liftDrawn'], 'liftDoorWallFills': built[k]['fills'],
        'rooms': [r['name'] for r in rooms_out if r['floor'] == k],
        'stairs': [{x: v for x, v in s.items() if x != 'poly'} for s in built[k]['outlines']],
        'voids': [{'what': w, 'area': round(v.area, 2)} for w, v in built[k]['voids']],
        'plateArea': round(sum(Polygon(p['o'], p['h']).area for p in parts if p['floor'] == k and p['kind'] == 'slab' and not p.get('label')), 1),
        'outdoorSlabArea': round(sum(Polygon(p['o'], p['h']).area for p in parts if p['floor'] == k and p['kind'] == 'slab' and p.get('label')), 1),
        'terrace': ({x: R3(v - (cx if x in ('west', 'east', 'eastFacade', 'outlineWest') else cy)) for x, v in built[k]['terrace'].items() if x != 'poly'}
                    if built[k]['terrace'] else None),
        'wallArea': round(sum(Polygon(p['o'], p['h']).area for p in parts if p['floor'] == k and p['kind'] == 'wall'), 2),
        'glassLength': round(sum(LineString(pts_m(k, g['line'])).length for g, _ in built[k]['panes']), 2),
        'probes': len([p for p in probes if p['floor'] == k]),
        'furniture': {kk['key']: sum(1 for p in furniture if p['floor'] == k and p['kind'] == kk['key']) for kk in furn_kinds},
        'furnitureApproach': approach[k],
        'openingsFromJambs': [r['fit'] for r in built[k]['recs'] if 'fit' in r],
        'hatchSills': {o['id']: [o['sill'], o['sillFrom']] for o in ops if o.get('hatch')},
        'lowWalls': built[k]['lows'], 'pictureEdgeWalls': built[k]['edgeWalls'],
    }
summary['furniture'] = {'pieces': len(furniture), 'kinds': {kk['key']: kk['count'] for kk in furn_kinds}}
(HERE / 'hotel_summary.json').write_text(json.dumps(summary, indent=1, ensure_ascii=False), encoding='utf-8', newline='\n')
for k in KEYS:
    print(k, dict(counts[k]), summary['floors'][k]['openings'], summary['floors'][k]['doorsWith'], 'exterior', summary['floors'][k]['exterior'],
          'one-sided', summary['floors'][k]['oneSided'])
    for f_ in summary['floors'][k]['openingsFromJambs']:
        if abs(f_['width'] - f_['widthWas']) >= 0.001 or abs(f_['lineMovedAcross']) >= 0.001 or any(abs(d) > f_['depthWas'] / 2 + 0.001 for e in f_['depthAtJambs'] for d in e):
            print(f"   {f_['id']} from its jambs: width {f_['widthWas']} -> {f_['width']} m (jambs out {f_['jambsMovedOut']}), depth {f_['depthWas']} -> "
                  f"{f_['depthAtJambs']} at its jambs, line moved {f_['lineMovedAcross']} m across")
print(f'written {out_model.name} ({out_model.stat().st_size // 1024} KB), offset ({cx}, {cy}) | {time.time() - t_start:.1f} s')

# ---------------------------------------------------------------------------------------------------- the family list, the top view
fk.write_csv(HERE.parent / 'hotel_furniture_list.csv', fk.csv_text(furniture, furn_kinds, CFG['floors'], model['offset']))
import matplotlib; matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import PathPatch, Patch, Polygon as MPoly
from matplotlib.path import Path as MPath
STY = {'slab': dict(facecolor='#eef0ec', edgecolor='#999', lw=0.8), 'wall': dict(facecolor='#8c7b6a', edgecolor='none'),
       'lintel': dict(facecolor='#d8a25e', edgecolor='none'), 'glass': dict(facecolor='#3f9fd0', edgecolor='#1f6f9f', lw=0.6),
       'railing': dict(facecolor='#b04ab8', edgecolor='none'), 'mullion': dict(facecolor='#2c5a74', edgecolor='none'),
       'step': dict(facecolor='#7cc48a', edgecolor='#2e8b47', lw=0.5), 'sill': dict(facecolor='#c9b79c', edgecolor='#8c7b6a', lw=0.5),
       'parapet': dict(facecolor='#c4b39f', edgecolor='#8c7b6a', lw=0.5)}
kind_by = {kk['key']: kk for kk in furn_kinds}
fig, axs = plt.subplots(1, len(KEYS), figsize=(12 * len(KEYS), 13), dpi=90)
for ax, key in zip(axs, KEYS):
    for kind in ('slab', 'step', 'railing', 'wall', 'sill', 'parapet', 'mullion', 'glass', 'lintel'):
        for p in parts:
            if p['floor'] != key or p['kind'] != kind: continue
            verts, codes = [], []
            for loop in [p['o']] + p['h']:
                verts += [tuple(v) for v in loop] + [tuple(loop[0])]
                codes += [MPath.MOVETO] + [MPath.LINETO] * (len(loop) - 1) + [MPath.CLOSEPOLY]
            sty = dict(STY[kind])
            if kind == 'slab' and p.get('label'): sty.update(facecolor='#e4e0d0', hatch='..')
            if kind == 'wall' and p.get('label'): sty.update(facecolor='#b3a596', hatch='//', edgecolor='#8c7b6a')      # an assumed wall
            ax.add_patch(PathPatch(MPath(verts, codes), **sty, zorder=1 + (kind in ('wall', 'glass', 'mullion', 'sill', 'parapet'))))
    arr = model['stairs'][key]['below']
    for i in range(0, len(arr), 4):
        ax.plot([arr[i], arr[i + 2]], [arr[i + 1], arr[i + 3]], color='#2e8b47', lw=0.8, zorder=2)
    for v in model['voids'][key]:
        ax.text(v['x'], v['y'], f"open: {v['what']}", fontsize=7, color='#555', ha='center', style='italic', zorder=6)
    for f in sorted((f for f in furniture if f['floor'] == key), key=lambda f: kind_by[f['kind']]['onTop']):
        ax.add_patch(MPoly(list(fk.rect_of(f).exterior.coords), closed=True, fc=kind_by[f['kind']]['colour'], ec='black', lw=0.35,
                           alpha=0.9, zorder=3 + kind_by[f['kind']]['onTop']))
    for o in openings:
        if o['floor'] != key: continue
        col = {'door': '#c0392b', 'window': '#1f6fb2', 'passage': '#2e8b47'}[o['kind']]
        ux, uy = o['ny'], -o['nx']; h = o['width'] / 2
        ax.plot([o['x'] - ux * h, o['x'] + ux * h], [o['y'] - uy * h, o['y'] + uy * h], color=col, lw=2.2,
                ls='--' if o['kind'] == 'passage' else (':' if o['kind'] == 'window' else '-'), zorder=5)
        ax.text(o['x'] + o['nx'] * 0.35, o['y'] + o['ny'] * 0.35, o['id'].split('-')[-1], fontsize=7, color=col, ha='center',
                va='center', zorder=6, fontweight='bold')
    for r in rooms_out:
        if r['floor'] == key:
            ax.text(r['x'], r['y'], r['label'], fontsize=8.5, color='#1f4e79', ha='center', va='center', zorder=7,
                    style='italic' if r.get('callout') else 'normal',
                    bbox=dict(boxstyle='round,pad=0.15', fc='white', ec='none', alpha=0.6))
    ax.set_title(f"{FLOOR[key]['name']} ({FLOOR[key]['level']:+.2f} m), read from {TK[key]['picture']['file'].split('/')[-1]} at "
                 f"{PX[key][0]:.2f} x {PX[key][1]:.2f} px/m; {sum(1 for f in furniture if f['floor'] == key)} furniture boxes", fontsize=11)
    ax.set_xlim(minx - cx - 0.8, maxx - cx + 0.8); ax.set_ylim(miny - cy - 0.8, maxy - cy + 0.8)
    ax.set_aspect('equal'); ax.axis('off')
legend = [Patch(fc=kk['colour'], ec='black', label=f"{kk['label']}: {' + '.join(str(sum(1 for f in furniture if f['floor'] == k and f['kind'] == kk['key'])) for k in KEYS)}, "
                f"{kk['height']} mm") for kk in furn_kinds]
fig.legend(handles=legend, loc='lower center', ncol=4, fontsize=10.5, frameon=False,
           title=f"Furniture kind: boxes on {' + '.join(KEYS)}, default height")
fig.suptitle('Walls brown (hatched: assumed, at the picture\'s cut edge), low walls light brown, lintels tan, sills beige, glass blue, '
             'railings purple, steps green; opening numbers: doors red, passages green (dashed), hatches blue (dotted);\nfurniture boxes in '
             'their kind\'s colour; "open" = no floor (stair, shafts); dotted slab = outdoor floor (floor 1\'s forecourt)', fontsize=11)
fig.tight_layout(rect=(0, 0.075, 1, 0.95))
fig.savefig(HERE.parent / 'hotel_topview.png'); plt.close()
print(f"written hotel_summary.json, ../hotel_furniture_list.csv ({len(furniture)} rows), ../hotel_topview.png")
