"""Hotel test (2 Nov 2026): two rendered floor-plan PICTURES (no CAD at all) -> takeoff.json, what was read, in picture pixels.

The pictures are presentation renders, partly hand-lettered: there are no layers, blocks or text entities to read, so a person
reads what cannot be measured (room names, what each piece of furniture is, which gap is a door) and types it, with rough
pixel positions, into picture_readings.json. This script measures everything else on the pixels and writes the exact result
to takeoff.json, which build_model.py turns into the model. Pixel coordinates: x right, y down; a pixel (c, r) is the square
c..c+1, r..r+1. A wall's FACE is the centre of the dark outline stroke drawn along it (not a half-way grey, which falls into
the drop shadow beside a wall); the faces are found as the first dark stroke met coming from the open side (picture_kit.
first_dip: a local minimum 30 grey levels or more below the floor and 6 or more below the wall's fill behind it), sub-pixel.
The rules, with sizes in pixels of the picture being read (second round, 2 Nov, after the owner's answers and the review):
 1. COLOUR CLASSES (picture_kit.colour_classes): walls are neutral dark grey (grey level 60-162) or a dark warm tint (below
    110: the RED BOX's walls), and the near-black lettering and outlines count too; floors are beige, mid grey or teal;
    furniture, glazing strips and the paper outside are near white; annotations are red. For the walls (rule 2) and the
    mullion ticks (rule 3) the red annotation strokes are first INPAINTED (picture_kit.inpaint: each red pixel, r >= 70,
    r - g and r - b >= 35, g < 140, and each reddish pixel beside one, r - g and r - b >= 15, g < 170, takes the colour
    around it; an inpainted pixel darker than HALF is wall): the red 'Luggage storage' box is drawn on the stair walls'
    inner faces and a red leader crosses the north wall (where it blends to a dark red), and cutting them out left notches
    and a slit (review issue 8). Floor 2's orange zone at its top edge (g >= 140) is not red.
 2. WALLS: the wall-grey pixels inside the reading's 'area' (the building: the traffic arrows, the site lines and the
    sheet's frame lie outside it), opened with a 5 x 5 square (every stroke thinner than 5 px goes: lettering, arrows,
    furniture outlines, tread lines, door swings), minus the parts thicker than 61 px both ways (a dark floor fill such
    as the pantry's, not a wall), minus the rectangles the reading erases (drop shadows on a grey floor are as dark as
    a wall, a black piece of furniture, sliding leaves drawn open), plus the brown-drawn walls in the reading's
    rectangle (stair sides: warm pixels darker than 172, opened with a 3 x 3 square). What is left in parts of 150 px2 or
    more is wall (smaller parts are lettering or a thick outline); each part is one outline (the union of its pixel rows,
    simplified by 1 px).
    STRAIGHT FACES (picture_kit.straighten, all of a floor's outlines together): an edge within 12 degrees of the
    picture's axes and 2.5 px or longer is a face; a face within 6 px of a flight's side wall's inner face measured by
    rule 11 (and facing the flight) is put on it (the red box hides those faces' strokes); the other faces of one axis
    facing the same way within 1.6 px of each other share one level (pieces in line come out in line); each level is
    moved onto the outline stroke drawn along it (the median over lines across its faces 1 px apart, where a stroke is
    found on 40 % of them or more, and less than half the wall's thickness in, so the two faces of a wall drawn as a
    single line never cross; a wall drawn as one dark band keeps its traced level); the corners are rebuilt. So a wall is
    as thick as its strokes are apart (face to face).
    Walls drawn as light lines on a dark or teal fill cannot be told from the fill by colour, and a wall that touches a
    dark fill goes with the fill: the reading gives those as bands (a centre line and a width). A wall drawn faintly, like
    the stair lines that run on under it (the outside stair's spine), is a LOW WALL: the reading gives it as a band under
    'lowWalls', copied to the take-off as it is (build_model.py builds it at railing height); it is not in the wall raster.
 3. MULLIONS: on a glazing line the reading marks 'ticks', the mullions are the dark ticks drawn on the line: the columns
    along it with 4 or more pixels darker than 95 within 5 px across it (and no more than 12 within 10 px: a wall end is
    taller), in runs 6 px long or more, each a post as long as its run and as deep as its dark pixels; the wall parts
    lying on such a line (its drop shadows) are not walls. On another glazing line a wall part of 40 to 400 px2 lying on it
    (its middle within 6 px) is a mullion of that glazing.
 4. LIFT DOORS (the owner's 1 m, a check of the scale): each lift door is the gap between the wall nibs on the lobby side of
    a lift, measured on every pixel column the reading names: a grey-level profile down the column, the first rise out of
    the wall and the next fall into it at the half-way grey HALF, then from each the nib's face (its stroke) a few px
    further in; the gap is the median over the columns.
 5. CORE FACES (the alignment): each named face of the lift core is found on profiles the reading draws across it (7, 1 px
    apart), in the direction it says ('down' = into the wall): the half-way crossing, then the face's stroke behind it;
    the median. The same names on both floors pair up for build_model.py's fit.
 6. OPENINGS: the reading gives each door and passage by two rough jamb points on the wall line. With 'refine', the jambs
    are measured on the wall raster (the straightened walls and the bands): along the line (5 lines 1 px apart, the
    majority), the run of non-wall pixels holding the middle; its ends are the jambs, and the wall's thickness is the wall
    run across the line 4 px beyond each jamb (the mean of the two; a run that reaches the end of its 40 px probe ran along
    a wall, at a corner, and does not count), the line moved onto the wall's middle. Lift doors take their jambs from
    rule 4. Without 'refine' (walls given as bands) the points are used as they are, with the reading's thickness 't'.
 7. GLAZING: the reading's line, moved across onto the measured middle of the drawn glazing: on 5 sections across it
    (6 px each way), the middle of the run of pixels darker than the half-way grey (a thin dark line) or, for a white
    strip with dark edges ('drawn': 'strip'), of light pixels; the median offset.
 8. STAIRS: tread lines are the local minima of a grey-level profile along the line the reading gives (red callout
    pixels taken out first) that lie 12 or more grey levels below the brightest grey within 4 px; minima closer than
    3 px are one line. The reading says which way is up and how the stair is built: 'steps' (the flight from this floor
    up to the next one), 'steps-up' (a flight up to a floor not in the pictures), 'lines' (flat tread lines) or 'void'
    (the floor is open over a stair from the floor below).
 9. SHAFTS, PLATE CLOSINGS, ROOM NAMES, HATCHES, OUTDOOR FLOORS: as the reading gives them (rectangles; lines across an
    opening in the building's edge or along the picture's edge; the words at the middle of the hand lettering or at a
    callout's dot; a hatch by two points on its wall line, moved onto the wall's middle, the wall's thickness measured
    across it on the raster; the forecourt's rectangle; the terrace's edges). A shaft marked 'closed' keeps its floor.
10. FURNITURE: the near-white pixels inside the area (light class, 15 px2 or more in one 8-connected part) are the
    furniture's bodies; drop shadows are darker and are not taken. A part that reaches the edge of the area is the paper
    around the building, and the parts in the reading's 'notFurniture' entries (rugs, the feature carpet, lift cars,
    stair treads, glazing strips, light symbols, a wall panel) are left out; both are listed with why. Each part is grown
    by 1 px (its drawn outline; the reading may say more for a thick frame). The reading names the kind, a short family
    (what the 3D team swaps models by) and a note: for every part whose middle lies in its rectangle (a row of bar stools:
    one piece each), for all of them as one piece ('merge': a sofa drawn as a frame and a cushion), for the thick dark
    shapes inside a circle (screens on a table top), or for a box drawn by hand where the picture has no white body (a
    black square, a plant) or where one body is several pieces (a U-shaped counter split into its straight legs, a
    faceted form followed by 3 boxes; the parts it replaces are named). A part that is round (it fills 70-86 % of its
    bounding box, sides within 20 %) keeps its bounding square; a rectangle within 4 degrees of the picture's axes is
    squared to them; any other keeps its minimum rotated rectangle. Parts the reading does not name are listed as unread.
11. STAIR WIDTH (the scale's reference, the owner's 2.50 m): on the rows the reading names (clear of tread lines and of red
    annotation), each side wall's inner face is the first stroke met coming from the stair; the width is the median over
    the rows of the two faces' distance (and, for a check over the walls, their outer strokes: the darkest point in the
    reading's windows, the median). On floor 2 (a check) the iconic staircase's stringers: the darkest point in the
    reading's windows for the west stringer's two lines and the east stringer's outer line (its inner line is lost in a
    shadow: taken as wide as the west one).
12. OUTLINE OF THE FLOOR ABOVE: the dashed lines floor 1 draws on the ground outside: on every row (column) of the
    reading's range the darkest point within its window, where it is darker than 215 (a dash, not a gap); the median.
Writes takeoff.json next to this script. A takeoff.json that was edited by hand since this script wrote it is not
overwritten: the new reading goes to takeoff.new.json and the script says so (use --force to overwrite).
Usage: python read_pictures.py [--force] [--debug <folder>]
"""
import hashlib, json, math, sys
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from shapely.geometry import LineString, Polygon, MultiPoint

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import picture_kit as pk

READ = json.loads((HERE / 'picture_readings.json').read_text(encoding='utf-8'))
OUT = HERE / 'takeoff.json'
FORCE = '--force' in sys.argv
DEBUG = Path(sys.argv[sys.argv.index('--debug') + 1]) if '--debug' in sys.argv else None

OPEN_R = 2            # rule 2: strokes thinner than 2 * 2 + 1 = 5 px are not walls
FILL_R = 30           # rule 2: parts thicker than 61 px both ways are floor fills
MIN_WALL = 150        # rule 2: px2 (a smaller dark part is lettering or a thick outline)
MIN_MULLION = 40      # rule 3: px2
WALL_SIMPLIFY = 1.0   # rule 2: px (about 2 cm): a wall outline a person can edit
MULLION_MAX = 400     # rule 3: px2
MULLION_REACH = 6     # rule 3: px from the glazing line
TICK_GREY = 95        # rule 3: a tick's pixels are darker than this (the glazing line itself is about 130-150)
TICK_MIN = 4          # rule 3: dark pixels within 5 px across the line for a column of a tick
TICK_LONG = 6         # rule 3: px, the shortest tick
JAMB_PROBE = 4        # rule 6: px beyond a jamb where the wall's thickness is taken
TREAD_DIP = 12        # rule 8: grey levels
MIN_BLOB = 15         # rule 10: px2
HALF = 162.0          # rules 4, 5: the half-way grey between a wall's inside (about 120) and the floor (about 205)
DASH = 215.0          # rule 12: a dash is darker than this
R1 = lambda v: round(float(v), 1)
R2 = lambda v: round(float(v), 2)


def poly_mask(pts, shape):
    """A polygon given by its points -> a boolean mask (pixels whose centre is inside)."""
    im = Image.new('L', (shape[1], shape[0]), 0)
    ImageDraw.Draw(im).polygon([tuple(p) for p in pts], fill=1)
    return np.asarray(im, dtype=bool)


def polys_mask(gs, shape):
    """Shapely polygons (holes too) -> a boolean mask: each polygon's outline filled, its holes taken out, the polygons OR-ed."""
    m = np.zeros(shape, dtype=bool)
    for g in gs:
        for p in polys(g):
            one = poly_mask(list(p.exterior.coords), shape)
            for h in p.interiors: one &= ~poly_mask(list(h.coords), shape)
            m |= one
    return m


def rect_mask(rect, shape):
    m = np.zeros(shape, dtype=bool)
    x0, y0, x1, y1 = [int(round(v)) for v in rect]
    m[max(y0, 0):max(y1, 0), max(x0, 0):max(x1, 0)] = True
    return m


def band_polygon(line, w):
    """A centre line and a width (px) -> the band as a shapely polygon (flat ends, mitred corners)."""
    return LineString(line).buffer(w / 2, cap_style='flat', join_style='mitre')


def ring(coords):
    pts = [[R1(x), R1(y)] for x, y in list(coords)[:-1]]
    return [p for i, p in enumerate(pts) if i == 0 or p != pts[i - 1]]


def polys(g):
    if g is None or g.is_empty: return []
    if g.geom_type == 'Polygon': return [g]
    return [p for x in getattr(g, 'geoms', []) for p in polys(x)]


def soft_red(a):
    """Red annotation strokes (rule 1): r >= 70, r - g and r - b >= 35, g < 140 (the brown stair walls stay under 35; a red stroke
    crossing a dark wall blends to a dark red such as 90, 45, 44; the orange zone at floor 2's top edge has g >= 140)."""
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    return (r >= 70) & (r - g >= 35) & (r - b >= 35) & (g < 140)


def red_halo(a, red):
    """The red strokes and their anti-aliased edge (rule 1): a reddish pixel (r - g, r - b >= 15, g < 170) next to a red one."""
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    return red | (pk.dilate(red, 1) & (r >= 70) & (r - g >= 15) & (r - b >= 15) & (g < 170))


def brown_wall(a):
    """The timber-brown walls (rule 2, inside the reading's rectangle only): warm (r > g >= b, r - b >= 25) and darker than 172,
    which takes in the lighter parts of their fill (colour_classes' brown stops at 150)."""
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    m = a.mean(axis=2)
    return (r > g) & (g >= b) & (r - b >= 25) & (m >= 70) & (m < 172)


# ---------------------------------------------------------------------------------------------------- measuring
def walk_dip(prof, start, direction, n=9):
    """The first dark stroke met walking along a 1-D grey profile (index = pixel) from pixel `start` in `direction` (+1 / -1)
    over n pixels -> its centre in pixel-edge coordinates, or None."""
    idx = [start + direction * k for k in range(n) if 0 <= start + direction * k < len(prof)]
    if len(idx) < 4: return None
    hit = pk.first_dip([prof[i] for i in idx])
    if hit is None: return None
    t, _ = hit
    return idx[0] + direction * t + 0.5


def lift_door(grey, rd):
    """Rule 4: the gap between the nibs' faces on the lobby side, the median over the reading's columns."""
    tops, bots, halves = [], [], []
    for x in range(rd['x'][0], rd['x'][1] + 1):
        col = grey[:, x]
        cs = pk.crossings(col[rd['y'][0]:rd['y'][1]], rd['y'][0], HALF)
        up = next((c for c, d in cs if d == 'up'), None)
        down = next((c for c, d in cs if d == 'down' and up is not None and c > up), None)
        if up is None or down is None: continue
        t = walk_dip(col, int(math.floor(up)) + 2, -1)
        b = walk_dip(col, int(math.floor(down)) - 2, +1)
        if t is None or b is None: continue
        tops.append(t); bots.append(b); halves.append(down - up)
    if not tops: raise SystemExit(f"{rd['id']}: no gap found between the nibs")
    top, bot = float(np.median(tops)), float(np.median(bots))
    w = [b - t for t, b in zip(tops, bots)]
    return {'id': rd['id'], 'lift': rd['lift'], 'x': R1((rd['x'][0] + rd['x'][1] + 1) / 2), 'gap': [R2(top), R2(bot)],
            'width': R2(bot - top), 'halfWay': R2(float(np.median(halves))), 'columns': len(tops), 'spread': R2(max(w) - min(w))}


def core_face(grey, rd, half=3):
    """Rule 5: the face's stroke behind the half-way crossing on 7 profiles 1 px apart, in the reading's direction; the median."""
    (x0, y0), (x1, y1) = rd['from'], rd['to']
    found, halves = [], []
    for k in range(-half, half + 1):
        if rd['axis'] == 'x':
            prof = grey[int(y0) + k, :]; lo, hi = int(x0), int(x1)
        else:
            prof = grey[:, int(x0) + k]; lo, hi = int(y0), int(y1)
        cs = pk.crossings(prof[lo:hi], lo, HALF)
        hit = next((c for c, d in cs if d == rd['cross']), None)
        if hit is None: continue
        s = walk_dip(prof, int(math.floor(hit)) - 2, +1) if rd['cross'] == 'down' else walk_dip(prof, int(math.floor(hit)) + 2, -1)
        if s is None: continue
        found.append(s); halves.append(hit)
    if not found: raise SystemExit(f"core face {rd['edge']!r}: no face found on its profiles")
    return {'edge': rd['edge'], 'axis': rd['axis'], 'at': R2(float(np.median(found))), 'halfWay': R2(float(np.median(halves))),
            'probe': [rd['from'], rd['to']]}


def stair_width(grey, red, s):
    """Rule 11: the clear width between a flight's side walls (floor 1, the reference) or a stair's stringers (floor 2, a check)."""
    w = s['width']
    rows = [y for lo, hi in w['rows'] for y in range(lo, hi + 1)]
    if 'west' in w:
        (wa, wb), (ea, eb) = w['west'], w['east']
        ws, es, used = [], [], []
        for y in rows:
            if red[y - 1:y + 2, min(wa, wb) - 3:max(wa, wb) + 4].any() or red[y - 1:y + 2, min(ea, eb) - 3:max(ea, eb) + 4].any(): continue
            xw = walk_dip(grey[y], wa, -1 if wb < wa else 1, abs(wb - wa) + 1)
            xe = walk_dip(grey[y], ea, -1 if eb < ea else 1, abs(eb - ea) + 1)
            if xw is None or xe is None: continue
            ws.append(xw); es.append(xe); used.append(y)
        if not used: raise SystemExit(f"{s['id']}: no row gave both side walls' faces")
        widths = [e - x for x, e in zip(ws, es)]
        out = {'west': R2(np.median(ws)), 'east': R2(np.median(es)), 'clear': R2(np.median(widths)), 'rows': len(used),
               'spread': R2(max(widths) - min(widths)), 'reference': bool(w.get('reference'))}
        if 'westOuter' in w:                                          # the walls' outer strokes, for the check over the walls
            for name in ('westOuter', 'eastOuter'):
                lo, hi = w[name]
                out[name] = R2(np.median([lo + pk.dip(grey[y, lo:hi + 1])[0] + 0.5 for y in used]))
            out['overWalls'] = R2(out['eastOuter'] - out['westOuter'])
        return out
    out = {}
    for name in ('westOuter', 'westInner', 'eastOuter'):
        lo, hi = w[name]
        out[name] = R2(np.median([lo + pk.dip(grey[y, lo:hi + 1])[0] + 0.5 for y in rows]))
    inner_east = out['eastOuter'] - (out['westInner'] - out['westOuter'])
    return {**out, 'eastInner': R2(inner_east), 'clear': R2(inner_east - out['westInner']), 'overStringers': R2(out['eastOuter'] - out['westOuter']),
            'rows': len(rows), 'reference': bool(w.get('reference'))}


def above_outline(grey, rd):
    """Rule 12: the dashed lines of the outline of the floor above (floor 1)."""
    out = {}
    for name in ('west', 'east'):
        lo, hi = rd[name]['x']; vals = []
        for y in range(rd[name]['rows'][0], rd[name]['rows'][1] + 1):
            t, v = pk.dip(grey[y, lo:hi + 1])
            if v < DASH: vals.append(lo + t + 0.5)
        out[name] = R2(np.median(vals)); out[name + 'Samples'] = len(vals)
    for name in ('south', 'wrapNorth'):
        lo, hi = rd[name]['y']; vals = []
        for x in range(rd[name]['cols'][0], rd[name]['cols'][1] + 1):
            t, v = pk.dip(grey[lo:hi + 1, x])
            if v < DASH: vals.append(lo + t + 0.5)
        out[name] = R2(np.median(vals)); out[name + 'Samples'] = len(vals)
    out['wrapFrom'] = rd['wrapFrom']
    return out


def ticks(grey, g):
    """Rule 3: the dark ticks on a horizontal glazing line -> mullion outlines (px)."""
    (x0, y0), (x1, y1) = g['line']
    yc = (y0 + y1) / 2
    r0, r1 = int(math.floor(yc - 5)), int(math.floor(yc + 5)) + 1
    R0, R1_ = int(math.floor(yc - 10)), int(math.floor(yc + 10)) + 1
    cols = []
    for x in range(int(math.floor(min(x0, x1))), int(math.ceil(max(x0, x1)))):
        near = int((grey[r0:r1, x] < TICK_GREY).sum()); far = int((grey[R0:R1_, x] < TICK_GREY).sum())
        cols.append(near >= TICK_MIN and far <= 12)
    out, x = [], int(math.floor(min(x0, x1)))
    i = 0
    while i < len(cols):
        if not cols[i]: i += 1; continue
        j = i
        while j + 1 < len(cols) and cols[j + 1]: j += 1
        if j - i + 1 >= TICK_LONG:
            xa, xb = x + i, x + j + 1
            rows = [r for r in range(r0, r1) if (grey[r, xa:xb] < TICK_GREY).any()]
            out.append({'o': [[xa, rows[0]], [xb, rows[0]], [xb, rows[-1] + 1], [xa, rows[-1] + 1]], 'h': [], 'area': float((xb - xa) * (rows[-1] + 1 - rows[0])),
                        'glazing': g['id'], 'from': 'tick'})
        i = j + 1
    return out


def run_at(mask, p, u, lo, hi, step=0.25):
    """Samples of a mask along p + u * t for t in [lo, hi] -> (ts, values)."""
    ts = np.arange(lo, hi + 1e-9, step)
    H, W = mask.shape
    vals = []
    for t in ts:
        x, y = p[0] + u[0] * t, p[1] + u[1] * t
        c, r = int(math.floor(x)), int(math.floor(y))
        vals.append(bool(mask[r, c]) if 0 <= r < H and 0 <= c < W else False)
    return ts, np.array(vals)


def wall_across(raster, p, n, reach=20):
    """The wall run across a wall line at p (along n): (its thickness, the offset of its middle from p) or None."""
    ts2, w2 = run_at(raster, p, n, -reach, reach)
    j = int(np.argmin(np.abs(ts2)))
    if not w2[j]: return None
    s0 = j
    while s0 > 0 and w2[s0 - 1]: s0 -= 1
    s1 = j
    while s1 < len(w2) - 1 and w2[s1 + 1]: s1 += 1
    if s0 == 0 or s1 == len(w2) - 1: return None
    return ts2[s1] - ts2[s0] + 0.25, (ts2[s0] + ts2[s1]) / 2


def refine_opening(wall, rd):
    """Rule 6: the jambs and the wall's thickness of an opening, measured on the wall raster."""
    a0, b0 = np.array(rd['near'][0], float), np.array(rd['near'][1], float)
    L = float(np.hypot(*(b0 - a0)))
    u = (b0 - a0) / L; n = np.array([-u[1], u[0]])
    mid = (a0 + b0) / 2
    reach = L / 2 + 30
    votes = []
    for k in (-2, -1, 0, 1, 2):
        ts, v = run_at(wall, mid + n * k, u, -reach, reach)
        votes.append(v)
    v = np.sum(votes, axis=0) >= 3
    i0 = int(np.argmin(np.abs(ts)))
    if v[i0]: raise SystemExit(f"{rd['id']}: the middle of the opening is wall")
    lo = i0
    while lo > 0 and not v[lo - 1]: lo -= 1
    hi = i0
    while hi < len(v) - 1 and not v[hi + 1]: hi += 1
    ta, tb = ts[lo] - 0.125, ts[hi] + 0.125
    found_a, found_b = lo > 0, hi < len(v) - 1
    a = mid + u * ta if found_a else a0
    b = mid + u * tb if found_b else b0
    ths = []
    for end, sgn, found in ((a, -1, found_a), (b, 1, found_b)):
        if not found: continue
        x = wall_across(wall, end + u * sgn * JAMB_PROBE, n)
        if x: ths.append(x)
    t = float(np.mean([x[0] for x in ths])) if ths else float(rd.get('t', 8))
    off = float(np.mean([x[1] for x in ths])) if ths else 0.0          # the wall's middle, across the reading's line
    a, b = a + n * off, b + n * off
    return [R1(a[0]), R1(a[1])], [R1(b[0]), R1(b[1])], round(t, 1), found_a and found_b


def hatch(raster, rd):
    """Rule 9: a hatch's two points moved onto the middle of the wall it is in, and that wall's thickness (on the raster)."""
    a0, b0 = np.array(rd['near'][0], float), np.array(rd['near'][1], float)
    u = (b0 - a0) / float(np.hypot(*(b0 - a0))); n = np.array([-u[1], u[0]])
    x = wall_across(raster, (a0 + b0) / 2, n)
    if x is None: raise SystemExit(f"{rd['id']}: the hatch's line is not on a wall")
    t, off = x
    a, b = a0 + n * off, b0 + n * off
    return {'id': rd['id'], 'kind': 'window', 'subtype': rd['subtype'], 'label': rd.get('label', ''), 'a': [R1(a[0]), R1(a[1])],
            'b': [R1(b[0]), R1(b[1])], 't': round(t, 1), 'hatch': True, 'measured': 'the wall across it measured (rule 9)',
            'width': R1(math.dist(a, b))}


def glazing_offset(C, line, drawn):
    """Rule 7: the reading's line moved onto the middle of the drawn glazing (median over 5 sections): a thin dark line
    ('line': the run of wall-grey and darker pixels) or a white strip between dark edges ('strip': the run of light pixels)."""
    p0, p1 = np.array(line[0], float), np.array(line[1], float)
    L = float(np.hypot(*(p1 - p0)))
    u = (p1 - p0) / L; n = np.array([-u[1], u[0]])
    target = C['light'] if drawn == 'strip' else (C['grey'] < HALF)
    offs = []
    for f in (0.15, 0.3, 0.5, 0.7, 0.85):
        p = p0 + u * L * f
        ts, v = run_at(target, p, n, -6, 6)
        j = int(np.argmin(np.abs(ts)))
        if not v[j]:
            near = [k for k in range(len(v)) if v[k]]
            if not near: continue
            j = min(near, key=lambda k: abs(ts[k]))
        s0 = j
        while s0 > 0 and v[s0 - 1]: s0 -= 1
        s1 = j
        while s1 < len(v) - 1 and v[s1 + 1]: s1 += 1
        offs.append(((ts[s0] + ts[s1]) / 2, ts[s1] - ts[s0] + 0.25))
    if not offs: return line, 0.0, None
    off = float(np.median([o for o, _ in offs])); width = float(np.median([w for _, w in offs]))
    return [[R1(p0[0] + n[0] * off), R1(p0[1] + n[1] * off)], [R1(p1[0] + n[0] * off), R1(p1[1] + n[1] * off)]], round(off, 1), round(width, 1)


def treads(grey, red, along):
    """Rule 8: tread lines along the reading's line -> positions (px along the line from its start, and the points)."""
    g = grey.copy(); g[red] = 248.0
    ts, v = pk.profile(g, along[:2], along[2:], step=0.5, half=2)
    out = []
    for i in range(len(v)):
        w0, w1 = max(0, i - 8), min(len(v), i + 9)
        if v[i] > v[w0:w1].min() + 1e-6: continue                      # not the lowest in +-4 px
        if v[w0:w1].max() - v[i] < TREAD_DIP: continue
        if out and ts[i] - out[-1] < 3: continue
        out.append(float(ts[i]))
    p0 = np.array(along[:2], float); p1 = np.array(along[2:], float)
    u = (p1 - p0) / float(np.hypot(*(p1 - p0)))
    return [[R1(p0[0] + u[0] * t), R1(p0[1] + u[1] * t)] for t in out]


# ---------------------------------------------------------------------------------------------------- furniture
def blob_outline(comp, grow, shape):
    """Rule 10: a light part grown by `grow` px -> (4 corners, round?)."""
    m = pk.comp_mask(comp, shape)
    if grow: m = pk.dilate(m, int(math.ceil(grow)))
    ys, xs = np.nonzero(m)
    x0, y0, x1, y1 = xs.min(), ys.min(), xs.max() + 1, ys.max() + 1
    w, h = x1 - x0, y1 - y0
    fill = comp['area'] / ((comp['bbox'][2] - comp['bbox'][0]) * (comp['bbox'][3] - comp['bbox'][1]))
    if 0.70 <= fill <= 0.86 and max(w, h) <= 1.2 * min(w, h):
        return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]], True
    pts = set()
    for r, c in zip(ys, xs):
        pts.update(((c, r), (c + 1, r), (c, r + 1), (c + 1, r + 1)))
    hull = MultiPoint(sorted(pts)).convex_hull
    mrr = list(hull.minimum_rotated_rectangle.exterior.coords)[:4]
    ang = math.degrees(math.atan2(mrr[1][1] - mrr[0][1], mrr[1][0] - mrr[0][0])) % 90
    if min(ang, 90 - ang) <= 4:
        return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]], False
    return [[R1(x), R1(y)] for x, y in mrr], False


def box_corners(rd):
    """A piece the reading draws by hand: 'box' [x0, y0, x1, y1], 'corners' [[x, y] x 4] or 'circle' [cx, cy, r]."""
    if 'box' in rd:
        x0, y0, x1, y1 = rd['box']
        return [[x0, y0], [x1, y0], [x1, y1], [x0, y1]], False
    if 'corners' in rd: return [list(p) for p in rd['corners']], False
    cx, cy, r = rd['circle']
    return [[cx - r, cy - r], [cx + r, cy - r], [cx + r, cy + r], [cx - r, cy + r]], True


def furniture(C, shape, area, fr, key):
    """Rule 10 -> (pieces, unread parts, parts left out with why, the light parts). A reading names its piece(s) by:
      'rect' [x0, y0, x1, y1]: every light part whose middle (of its bounding box) lies in it is a piece ('minArea' px2 at
              least), or, with 'merge', they are all one piece;
      'box' [x0, y0, x1, y1], 'corners' [[x, y] x 4], 'circle' [cx, cy, r]: drawn by hand; 'absorbs' [rects] then names the
              light parts that this hand-drawn piece replaces (their middles in the rects);
      'darkInCircle' [cx, cy, r]: every dark shape inside the circle ('minArea' to 'maxArea' px2) is a piece (screens drawn
              as thick outlines on a white table top).
    The reading's 'notFurniture' entries ('rect' as above, or 'at' [x, y]: the light part holding that pixel) come first."""
    light = C['light'] & area & ~C['red']
    comps = pk.components(light, MIN_BLOB)
    centre = lambda c: ((c['bbox'][0] + c['bbox'][2]) / 2, (c['bbox'][1] + c['bbox'][3]) / 2)
    inside = lambda c, r: r[0] <= centre(c)[0] <= r[2] and r[1] <= centre(c)[1] <= r[3]
    holds = lambda c, p: any(row == int(p[1]) and c0 <= p[0] < c1 for row, c0, c1 in c['runs'])
    left_out, taken = [], set()
    rim = pk.dilate(~area, 1) & area                     # the reading area's edge: a light part reaching it is the paper outside
    for i, c in enumerate(comps):
        if any(rim[row, c0:c1].any() for row, c0, c1 in c['runs']):
            left_out.append({'bbox': list(c['bbox']), 'area': c['area'], 'why': 'the paper around the building (it reaches the edge of the reading area)'})
            taken.add(i)
    for nf in fr.get('notFurniture', []):
        hits = [i for i, c in enumerate(comps) if i not in taken and (inside(c, nf['rect']) if 'rect' in nf else holds(c, nf['at']))]
        if not hits: raise SystemExit(f"{key}: notFurniture {nf}: no light part there")
        for i in hits:
            left_out.append({'bbox': list(comps[i]['bbox']), 'area': comps[i]['area'], 'why': nf['why']}); taken.add(i)
    pieces = []

    def add(rd, n, corners, rnd, how):
        pieces.append({'kind': rd['kind'], 'family': rd['family'], 'outline': [[R1(x), R1(y)] for x, y in corners], 'round': rnd,
                       'n': rd.get('n', n), 'from': how, 'note': rd.get('note', '')})
    for rd in fr.get('furniture', []):
        grow = rd.get('grow', 1)
        if any(k in rd for k in ('box', 'corners', 'circle')):
            corners, rnd = box_corners(rd)
            gone = [i for i, c in enumerate(comps) if i not in taken and any(inside(c, r) for r in rd.get('absorbs', []))]
            taken.update(gone)
            add(rd, 1, corners, rnd, 'drawn by hand' + (f' (replaces {len(gone)} light parts)' if gone else '')); continue
        if 'darkInCircle' in rd:
            cx, cy, r = rd['darkInCircle']
            yy, xx = np.mgrid[0:shape[0], 0:shape[1]]
            disc = (xx + 0.5 - cx) ** 2 + (yy + 0.5 - cy) ** 2 <= r * r
            found = [c for c in pk.components((C['ink'] | C['dark']) & disc, rd.get('minArea', 20))
                     if c['area'] <= rd.get('maxArea', 10 ** 9)]
            if not found: raise SystemExit(f"{key}: furniture {rd['family']!r}: no dark shape in the circle {rd['darkInCircle']}")
            for c in found:
                corners, rnd = blob_outline(c, 0, shape)
                add(rd, 1, corners, False, 'dark shape')
            continue
        hits = [i for i, c in enumerate(comps) if i not in taken and inside(c, rd['rect']) and c['area'] >= rd.get('minArea', 0)]
        if not hits: raise SystemExit(f"{key}: furniture {rd['family']!r}: no light part in rect {rd['rect']}")
        if rd.get('merge'):
            m = {'runs': [r for i in hits for r in comps[i]['runs']], 'area': sum(comps[i]['area'] for i in hits),
                 'bbox': (min(comps[i]['bbox'][0] for i in hits), min(comps[i]['bbox'][1] for i in hits),
                          max(comps[i]['bbox'][2] for i in hits), max(comps[i]['bbox'][3] for i in hits))}
            corners, rnd = blob_outline(m, grow, shape)
            taken.update(hits); add(rd, 1, corners, rnd, f'{len(hits)} light parts merged' if len(hits) > 1 else 'light part')
        else:
            for i in hits:
                corners, rnd = blob_outline(comps[i], grow, shape)
                taken.add(i); add(rd, 1, corners, rnd, 'light part')
    unread = [{'bbox': list(c['bbox']), 'area': c['area']} for i, c in enumerate(comps) if i not in taken]
    return pieces, unread, left_out, comps


# ---------------------------------------------------------------------------------------------------- one floor
def read_floor(key, fr):
    path = (HERE / fr['picture']).resolve()
    a = pk.load(path)
    C = pk.colour_classes(a)
    grey = C['grey']
    shape = grey.shape
    area = poly_mask(fr['area'], shape)
    red = soft_red(a)
    out = {'picture': {'file': fr['picture'], 'size': [shape[1], shape[0]]}}
    # rules 4, 5 and 11: lift doors, core faces, stair widths
    out['liftDoors'] = [lift_door(grey, rd) for rd in fr['liftDoors']]
    out['core'] = [core_face(grey, rd) for rd in fr['core']]
    widths = {s['id']: stair_width(grey, red, s) for s in fr.get('stairs', []) if 'width' in s}
    known = []                                                         # rule 2: the flight's side walls' inner faces are rule 11's
    for s in fr.get('stairs', []):
        w = widths.get(s['id'])
        if not w or 'west' not in w: continue
        span = (s['rect'][1] - 40, s['rect'][3] + 40)
        known += [{'axis': 'x', 'in': -1, 'at': w['west'], 'tol': 6.0, 'span': span, 'why': f"{s['id']}: the west side wall's inner face (rule 11)"},
                  {'axis': 'x', 'in': 1, 'at': w['east'], 'tol': 6.0, 'span': span, 'why': f"{s['id']}: the east side wall's inner face (rule 11)"}]
    # rules 1-2: walls, on the picture with its red annotation inpainted
    painted = red_halo(a, red)
    aw = pk.inpaint(a, painted)
    Cw = pk.colour_classes(aw)
    gw = Cw['grey']
    wallgrey = (Cw['dark'] | Cw['ink'] | (painted & (gw < HALF))) & area
    opened = pk.opening(wallgrey, OPEN_R)
    fills = pk.opening(opened, FILL_R)
    walls = opened & ~pk.dilate(fills, 2)
    for er in fr.get('wallErase', []): walls &= ~rect_mask(er['rect'], shape)
    if 'brownWalls' in fr:
        walls |= pk.opening(brown_wall(aw) & rect_mask(fr['brownWalls']['rect'], shape), 1)
    comps = pk.components(walls, MIN_MULLION)
    glz = {g['id']: LineString(g['line']) for g in fr.get('glazing', [])}
    tick_lines = {g['id'] for g in fr.get('glazing', []) if g.get('mullions') == 'ticks'}
    wall_geo, mullions, specks, shadows = [], [], 0, 0
    for c in comps:
        g = pk.comp_polygon(c, WALL_SIMPLIFY)
        near = [gid for gid, ln in glz.items() if ln.distance(g.centroid) <= MULLION_REACH]
        if c['area'] < MULLION_MAX and near and near[0] in tick_lines:
            shadows += 1; continue                                         # rule 3: a tick and its shadow, read as a tick below
        if not (c['area'] < MULLION_MAX and near) and c['area'] < MIN_WALL:
            specks += 1; continue                                          # lettering, a thick outline: not a wall
        for p in polys(g):
            if c['area'] < MULLION_MAX and near:
                mullions.append({'o': ring(p.exterior.coords), 'h': [], 'area': R1(p.area), 'glazing': near[0], 'from': 'wall part'})
            elif p.area >= 4: wall_geo.append(p)
    straight, levels = pk.straighten(wall_geo, gw, mask=walls, known=known)
    wall_parts = []
    for p in straight:
        for q in polys(p):
            if q.area >= 4:
                wall_parts.append({'o': ring(q.exterior.coords), 'h': [ring(h.coords) for h in q.interiors if Polygon(h).area >= 4], 'area': R1(q.area)})
    for g in fr.get('glazing', []):
        if g['id'] in tick_lines: mullions += ticks(gw, g)
    wall_parts.sort(key=lambda e: (round(min(y for _, y in e['o'])), round(min(x for x, _ in e['o']))))
    mullions.sort(key=lambda e: (round(min(x for x, _ in e['o'])), round(min(y for _, y in e['o']))))
    out['walls'] = [{'id': f'{key}-W{i + 1:02d}', **e} for i, e in enumerate(wall_parts)]
    moved = [lv['moved'] for lv in levels if lv['moved'] and not lv.get('known')]
    out['wallFaces'] = {'levels': len(levels), 'movedOntoStrokes': len(moved), 'medianMovePx': R2(np.median(moved)) if moved else 0.0,
                        'onKnownFaces': [[lv['known'], lv['faces'], lv['level']] for lv in levels if lv.get('known')],
                        'keptTraced': sum(1 for lv in levels if not lv['moved'] and not lv.get('known')), 'rule': 'rule 2: straight faces on the outline strokes'}
    out['wallBands'] = [{'id': f'{key}-B{i + 1:02d}', 'line': b['line'], 'w': b['w'], 'why': b['why']} for i, b in enumerate(fr.get('wallBands', []))]
    if fr.get('lowWalls'):                                             # rule 2: low walls (not in the wall raster below)
        out['lowWalls'] = [{'id': f'{key}-L{i + 1:02d}', 'line': b['line'], 'w': b['w'], 'label': b.get('label', 'low wall'), 'why': b['why']}
                           for i, b in enumerate(fr['lowWalls'])]
    out['mullions'] = [{'id': f'{key}-M{i + 1:02d}', **e} for i, e in enumerate(mullions)]
    # the wall raster the openings are measured on: the straightened walls and the bands
    raster = polys_mask([Polygon(w['o'], w['h']) for w in out['walls']], shape)
    for b in fr.get('wallBands', []):
        raster |= poly_mask(list(band_polygon(b['line'], b['w']).exterior.coords), shape)
    # rule 6: openings
    lifts = {d['id']: d for d in out['liftDoors']}
    ops = []
    for rd in fr.get('openings', []):
        rec = {'id': rd['id'], 'kind': rd['kind'], 'subtype': rd['subtype'], 'label': rd.get('label', '')}
        if rd.get('lift'):
            d = lifts[rd['id']]
            a_, b_, t, ok = refine_opening(raster, rd)
            x = (a_[0] + b_[0]) / 2
            rec.update(a=[R1(x), d['gap'][0]], b=[R1(x), d['gap'][1]], t=t, lift=True, measured='lift door gap at the nibs\' faces (rule 4)')
        elif rd.get('refine'):
            a_, b_, t, ok = refine_opening(raster, rd)
            rec.update(a=a_, b=b_, t=t, measured='jambs measured (rule 6)' if ok else 'one jamb measured, the other as read')
        else:
            rec.update(a=list(rd['near'][0]), b=list(rd['near'][1]), t=float(rd.get('t', 8)), measured='as read (a wall drawn as a band)')
        rec['width'] = R1(math.dist(rec['a'], rec['b']))
        ops.append(rec)
    out['openings'] = ops
    out['hatches'] = [hatch(raster, rd) for rd in fr.get('hatches', [])]
    # rule 7: glazing
    out['glazing'] = []
    for g in fr.get('glazing', []):
        line, off, width = glazing_offset(C, g['line'], g.get('drawn', 'line'))
        out['glazing'].append({'id': g['id'], 'line': line, 'drawnWidth': width, 'moved': off, 'label': g.get('label', ''),
                               **({'mullions': 'ticks'} if g['id'] in tick_lines else {})})
    # rules 8 and 11: stairs and their widths
    out['stairs'] = []
    for s in fr.get('stairs', []):
        tl = treads(grey, C['red'], s['treadsAlong'])
        axis = 1 if s.get('axis', 'y') == 'y' else 0
        pos = [p[axis] for p in tl]
        sp = [round(b - a, 1) for a, b in zip(pos, pos[1:])]
        rec = {k: v for k, v in s.items() if not k.startswith('_') and k not in ('treadsAlong', 'width')}
        rec.update(treadLines=[R1(v) for v in pos], treadAxis='y' if axis else 'x', spacing=round(float(np.median(np.abs(sp))), 2) if sp else None)
        if 'width' in s: rec['width'] = widths[s['id']]
        out['stairs'].append(rec)
    # rules 9 and 12
    out['shafts'] = [{k: v for k, v in s.items() if not k.startswith('_')} for s in fr.get('shafts', [])]
    out['plateClose'] = fr.get('plateClose', [])
    for k in ('forecourt', 'terrace'):
        if k in fr: out[k] = {x: v for x, v in fr[k].items() if not x.startswith('_')}
    if 'aboveOutline' in fr: out['aboveOutline'] = above_outline(grey, fr['aboveOutline'])
    out['rooms'] = [{k: v for k, v in r.items() if not k.startswith('_')} for r in fr.get('rooms', [])]
    out['notRooms'] = fr.get('notRooms', [])
    # rule 10: furniture
    pieces, unread, left_out, blobs = furniture(C, shape, area, fr, key)
    pieces.sort(key=lambda p: (min(y for _, y in p['outline']), min(x for x, _ in p['outline'])))
    out['furniture'] = [{'id': f'{key}-P{i + 1:03d}', **p} for i, p in enumerate(pieces)]
    out['furnitureUnread'] = unread
    out['notFurniture'] = left_out
    sw = [(s['id'], s['width'].get('clear')) for s in out['stairs'] if 'width' in s]
    low = f" + {len(out['lowWalls'])} low walls" if out.get('lowWalls') else ''
    print(f"{key}: lift doors {[d['width'] for d in out['liftDoors']]} px (half-way {[d['halfWay'] for d in out['liftDoors']]}), "
          f"{len(out['walls'])} wall parts ({specks} specks, {shadows} tick shadows left out; faces: {out['wallFaces']['levels']} levels, "
          f"{out['wallFaces']['movedOntoStrokes']} moved onto strokes, median {out['wallFaces']['medianMovePx']} px) + {len(out['wallBands'])} bands{low}, "
          f"{len(out['mullions'])} mullions, {len(ops)} openings, {len(out['hatches'])} hatches, {len(out['glazing'])} glazing lines, stairs "
          f"{[(s['id'], len(s['treadLines']), s['spacing']) for s in out['stairs']]}, stair widths {sw} px, {len(out['rooms'])} room names, "
          f"{len(pieces)} furniture pieces, {len(unread)} light parts unread, {len(left_out)} left out")
    if DEBUG: debug_picture(key, a, out, walls, blobs, unread, levels)
    return out


def debug_picture(key, a, out, walls, blobs, unread, levels):
    """The take-off over the picture, for looking at (not the model: overlay.py draws that), and the face levels as text."""
    DEBUG.mkdir(parents=True, exist_ok=True)
    im = Image.fromarray((a * 0.55 + 110).clip(0, 255).astype(np.uint8)).convert('RGB')
    d = ImageDraw.Draw(im)
    for w in out['walls']:
        d.polygon([tuple(p) for p in w['o']], outline=(30, 60, 230))
        for h in w['h']: d.polygon([tuple(p) for p in h], outline=(30, 60, 230))
    for b in out['wallBands']: d.polygon([tuple(p) for p in band_polygon(b['line'], b['w']).exterior.coords], outline=(0, 160, 255))
    for b in out.get('lowWalls', []): d.polygon([tuple(p) for p in band_polygon(b['line'], b['w']).exterior.coords], outline=(160, 90, 255))
    for m in out['mullions']: d.polygon([tuple(p) for p in m['o']], outline=(0, 200, 200))
    for o in out['openings'] + out['hatches']:
        d.line([tuple(o['a']), tuple(o['b'])], fill=(220, 0, 0) if o['kind'] == 'door' else (0, 150, 0), width=2)
        d.text(((o['a'][0] + o['b'][0]) / 2 + 3, (o['a'][1] + o['b'][1]) / 2 + 3), o['id'].split('-')[1], fill=(200, 0, 0))
    for g in out['glazing']: d.line([tuple(p) for p in g['line']], fill=(0, 170, 255), width=2)
    for s in out['stairs']:
        x0, y0, x1, y1 = s['rect']; d.rectangle([x0, y0, x1, y1], outline=(0, 140, 60))
        for v in s['treadLines']:
            if s['treadAxis'] == 'y': d.line([(x0, v), (x1, v)], fill=(0, 200, 80))
            else: d.line([(v, y0), (v, y1)], fill=(0, 200, 80))
    for p in out['furniture']:
        d.polygon([tuple(q) for q in p['outline']], outline=(230, 120, 0))
        d.text((p['outline'][0][0] + 1, p['outline'][0][1]), p['id'].split('-P')[1], fill=(170, 60, 0))
    for u in unread:
        d.rectangle([u['bbox'][0], u['bbox'][1], u['bbox'][2] - 1, u['bbox'][3] - 1], outline=(255, 0, 255))
    im.save(DEBUG / f'takeoff_{key}.png')
    (DEBUG / f'faces_{key}.txt').write_text('\n'.join(json.dumps(lv) for lv in levels) + '\n', encoding='utf-8')


def plain(v):
    """numpy numbers -> Python numbers (json cannot write numpy's)."""
    return v.item() if hasattr(v, 'item') else str(v)


def canonical(obj):
    return json.dumps(obj, ensure_ascii=False, separators=(',', ':'), default=plain)


def compact(v):
    return json.dumps(v, ensure_ascii=False, separators=(', ', ': '), default=plain)


def pretty(take):
    """takeoff.json's layout: each floor's sections one under the other, one entry of a list per line, so that a person can
    find and correct one entry (and a file compare shows which entries changed)."""
    lines = ['{']
    keys = list(take)
    for i, k in enumerate(keys):
        end = ',' if i < len(keys) - 1 else ''
        if k != 'floors':
            lines.append(f' {json.dumps(k)}: {compact(take[k])}{end}'); continue
        lines.append(' "floors": {')
        fkeys = list(take['floors'])
        for j, f in enumerate(fkeys):
            lines.append(f'  {json.dumps(f)}: {{')
            secs = list(take['floors'][f])
            for m, s in enumerate(secs):
                v = take['floors'][f][s]
                c = ',' if m < len(secs) - 1 else ''
                if isinstance(v, list) and v:
                    lines.append(f'   {json.dumps(s)}: [')
                    lines += ['    ' + compact(e) + (',' if q < len(v) - 1 else '') for q, e in enumerate(v)]
                    lines.append('   ]' + c)
                else:
                    lines.append(f'   {json.dumps(s)}: {compact(v)}{c}')
            lines.append('  }' + (',' if j < len(fkeys) - 1 else ''))
        lines.append(' }' + end)
    return '\n'.join(lines) + '\n}\n'


if __name__ == '__main__':
    take = {'_about': 'What was read on the two pictures, in picture pixels (x right, y down). Written by read_pictures.py from the '
                      'pictures and picture_readings.json; build_model.py turns it into hotel_model.json with hotel_project.json. '
                      'Correct an entry here and run build_model.py; re-running read_pictures.py measures the pictures again '
                      '(it will not overwrite this file once it has been edited by hand, see its docstring).',
            'floors': {}}
    for key in ('F1', 'F2'):
        take['floors'][key] = read_floor(key, READ[key])
    body = canonical(take)
    take['_written'] = {'by': 'read_pictures.py', 'sha1': hashlib.sha1(body.encode('utf-8')).hexdigest()[:12]}
    text = pretty(take)
    target = OUT
    if OUT.exists() and not FORCE:
        old = json.loads(OUT.read_text(encoding='utf-8'))
        mark = old.pop('_written', {})
        if mark.get('sha1') != hashlib.sha1(canonical(old).encode('utf-8')).hexdigest()[:12]:
            target = HERE / 'takeoff.new.json'
            print(f'{OUT.name} was edited by hand since it was written: the new reading goes to {target.name} (--force to overwrite)')
    target.write_text(text, encoding='utf-8', newline='\n')          # LF on every machine, so a file compare shows only real changes
    print('written', target.name, f'({len(text) // 1024} KB)')
