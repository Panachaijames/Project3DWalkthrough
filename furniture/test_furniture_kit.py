"""Tests for furniture_kit.py: plain asserts, no framework. Run: python -B furniture/test_furniture_kit.py"""
import csv, io, math, random, sys, tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import furniture_kit as fk
from shapely.geometry import LineString, Polygon

checks = 0


def ok(cond, *info):
    global checks
    checks += 1
    assert cond, info


def near(a, b, tol=1e-3):
    return abs(a - b) <= tol


def piece(**kw):
    p = dict(floor='L1', kind='cabinet', family='F', block='B', layer='Q-CASE', handle='', x=0.0, y=0.0, w=1.0, d=0.4, rot=0.0, on=None, n=1, note='')
    p.update(kw)
    return p


def rect_pts(cx, cy, w, d, rot):
    return list(fk.rect_of({'x': cx, 'y': cy, 'w': w, 'd': d, 'rot': rot}).exterior.coords)[:4]


# ---------------------------------------------------------------------------------------------------- the kinds table = the README's
rows = []
for line in (HERE / 'README.md').read_text(encoding='utf-8').splitlines():
    cells = [c.strip().replace('*', '') for c in line.strip().strip('|').split('|')]
    if line.startswith('| ') and len(cells) == 8 and cells[0] != 'key': rows.append(cells)
ok(len(rows) == len(fk.KINDS) == 22, len(rows), len(fk.KINDS))
for cells, k in zip(rows, fk.KINDS):
    ok([k['key'], k['label'], k['colour'], k['height'], k['base'], k['onTop'], k['support'], k['blocks']] ==
       [cells[0], cells[1], cells[2], int(cells[3]), int(cells[4]), cells[5] == 'yes', cells[6] == 'yes', cells[7] == 'yes'], k['key'])
ok(len({k['colour'] for k in fk.KINDS}) == 22 and all(len(k['colour']) == 7 for k in fk.KINDS))
ok({k['key'] for k in fk.KINDS if k['support']} == {'table', 'coffee-table', 'bar-table', 'counter', 'cabinet'})
ok({k['key'] for k in fk.KINDS if k['onTop']} == {'computer', 'printer', 'phone', 'lamp', 'plant'})
ok([k['key'] for k in fk.KINDS if not k['blocks']] == ['curtain'] and not any(k['onTop'] and k['support'] for k in fk.KINDS))
ok(all(kind in {k['key'] for k in fk.KINDS} for kind, _, _ in fk.RULES) and all(kind in {k['key'] for k in fk.KINDS} for kind, _ in fk.LAYER_WORDS))
# the seat back (2 Nov 2026: the back of a seat drawn as a piece of its own): right after sofa in the legend, 800 mm on the floor, on nothing
keys = [k['key'] for k in fk.KINDS]
seat_back = fk.KINDS[keys.index('seat-back')]
ok(keys.index('seat-back') == keys.index('sofa') + 1, keys)
ok((seat_back['label'], seat_back['height'], seat_back['base'], seat_back['onTop'], seat_back['support'], seat_back['blocks']) == ('Seat back', 800, 0, False, False, True), seat_back)


def lab(h):
    """'#rrggbb' -> CIELAB (sRGB, D65), for the colour distances below."""
    lin = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in (int(h[i:i + 2], 16) / 255 for i in (1, 3, 5))]
    xyz = [sum(m * c for m, c in zip(row, lin)) / n for row, n in zip(((0.4124564, 0.3575761, 0.1804375), (0.2126729, 0.7151522, 0.0721750),
                                                                     (0.0193339, 0.1191920, 0.9503041)), (0.95047, 1.0, 1.08883))]
    f = [t ** (1 / 3) if t > (6 / 29) ** 3 else t / (3 * (6 / 29) ** 2) + 4 / 29 for t in xyz]
    return 116 * f[1] - 16, 500 * (f[0] - f[1]), 200 * (f[1] - f[2])


rest = [k for k in fk.KINDS if k['key'] != 'seat-back']
far = min((math.dist(lab(seat_back['colour']), lab(k['colour'])), k['key']) for k in rest)
closest = min(math.dist(lab(a['colour']), lab(b['colour'])) for i, a in enumerate(rest) for b in rest[i + 1:])
ok(far[0] >= 25 and far[0] > closest, far, closest)            # salmon: further from every other kind's colour (nearest atm, 25.9) than the table's own closest pair (13.8)
ok(math.dist(lab(seat_back['colour']), lab(fk.KINDS[keys.index('seat')]['colour'])) >= 40)     # ... and well apart from the seat it stands on (41.7)

# ---------------------------------------------------------------------------------------------------- classify: real family names
REAL = [                                                       # (family name, layer, kind)
    ('ATM Machine - ATM Machine', 'A-GENM', 'atm'),
    ('TELEPHONE_HANDSET_DESKTOP_HTH_ITNE-049 - Type 1', 'E-COMM', 'phone'),                     # DESKTOP is not a desk
    ('PRINTER_DESKTOP_LASER_HTH_FQGE-057 - Type 1', 'Q-SPCQ', 'printer'),
    ('Enscape AssetDefinition - Computer 003 - Enscape AssetDefinition - Computer 003', 'I-FURN', 'computer'),
    ('APPLIANCE_TV_WALL MOUNT WITH BRACKET - 75_', 'Q-SPCQ', 'tv'),                             # a TV, not an appliance
    ('IF_J04_WALL TV - WALL TV 3800W', 'Q-CASE', 'tv'),
    ('Steelcase - Height-Adjustable Desk - Privacy Screen - Sarto - 30W x 19_5H', 'I-FURN', 'partition'),   # ADJUSTABLE has 'table' in it
    ('POTTED PLANT - STOOL LOW_VITRA_VISIONA STOOL', 'Q-CASE', 'plant'),                        # a plant, not a stool
    ('Enscape AssetDefinition - Bush 020 Fern - Enscape AssetDefinition - Bush 020 Fern', 'L-PLNT', 'plant'),
    ('Enscape AssetDefinition - Potted Plant 028 Peace Lily - Enscape AssetDefinition - Potted Plant 028 Peace Lily 2', 'L-PLNT', 'plant'),
    ('Enscape AssetDefinition - Vase 003 Heracleum - Enscape AssetDefinition - Vase 003 Heracleum', 'L-PLNT', 'plant'),
    ('COTTO Two piece toilet Elzra C13920 _1_ - COTTO Two piece toilet Elzra C13920', 'P-SANR-FIXT', 'sanitary'),
    ('COTTO Wall hung urinal Natasha C313BI _1_ - COTTO Wall hung urinal Natasha C313BI', 'P-SANR-FIXT', 'sanitary'),
    ('Wall-hung vitreous china basin-Meridian-327242xx0 - 327242000 White', 'P-SANR-FIXT', 'sanitary'),
    ('C12377 - C12377', 'P-SANR-FIXT', 'sanitary'),                                             # the name says nothing: the layer's SANR does
    ('อ่างล้างหน้าฝั่งครึ่งเคาน์เตอร์ - C0240 - อ่างล้างหน้าฝั่งครึ่งเคาน์เตอร์ - C0240', 'P-SANR-FIXT', 'sanitary'),   # Thai: a basin, not a counter
    ('อ่างล้างหน้าฝั่งครึ่งเคาน์เตอร์ - C0240', 'XYZ', 'sanitary'),                               # ... by its Thai word, whatever the layer
    ('สุขภัณฑ์แบบนั่งราบ - C1403 - C1403', 'P-SANR-FIXT', 'sanitary'),
    ('TALL CABINET - TALL CABINET 1875W', 'Q-CASE', 'tall-cabinet'),
    ('TALL CABINET 4200W - TALL CABINET 4200W', 'Q-CASE', 'tall-cabinet'),
    ('RACKS_DATA - 1100x600', 'Q-SPCQ', 'tall-cabinet'),
    ('IA_J07_WORK CABINET - IA_J07_WORK CABINET', 'Q-CASE', 'cabinet'),
    ('WORK CABINET-1 - WORK CABINET-1', 'Q-CASE', 'cabinet'),
    ('CONSOLE_CABINET_BAKER - TA13 1800W 400D', 'I-FURN', 'cabinet'),
    ('Casework 1 - Casework 2', 'Q-CASE', 'cabinet'),
    ('PANEL_ADJ_GEN - ADJUSTABLE CUPBOARD DOOR', 'Q-CASE', 'cabinet'),                          # ADJUSTABLE again
    ('PANEL_ADJ_GEN - ADJUSTABLE DRAWER', 'Q-CASE', 'cabinet'),
    ('WORKING TABLE - WORKING TABLE', 'Q-CASE', 'table'),
    ('IA_J15_WORKING TABLE - 1800W 1000D 750H', 'I-FURN', 'table'),
    ('TABLE_DINING_RECTANGLE CHAMPAGNE LEG - TA103 380W x 380D x 750H', 'I-FURN', 'table'),
    ('COFFEE TABLE RETANGLE - VENNATIVE - TYPE 1', 'I-FURN', 'coffee-table'),
    ('TABLE_BEDSIDE_VITRA_OCCASIONAL - TA104 600W 400H', 'I-FURN', 'coffee-table'),             # not a bed
    ('SOFA_BENCH_DIOR - TYPE 2', 'I-FURN', 'sofa'),                                             # a sofa, not a bench
    ('SOFA_03_1 - 1500W x 400D SE18', 'I-FURN', 'sofa'),
    ('Etta Armchair1 - TYPE 2', 'I-FURN', 'sofa'),
    ('CHAIR_BENCH BACK - SE107 STOOL LOW_VITRA_VISIONA STOOL', 'I-FURN', 'seat'),               # a seat, not a sofa
    ('CHAIR_STOOL LOW_VITRA_VISIONA STOOL - 500W GRAY', 'I-FURN', 'seat'),
    ('mollie_chair_a685_revit - A685 2', 'I-FURN', 'seat'),
    ('FU_Chair_Sandler_Tablet 8-4 - TABLET 8_4', 'I-FURN', 'seat'),                             # TABLET is not a table
    ('HermanMiller_Seating_AER1A_NewAeron_WorkChair_ASize - SE101_Size Low-Hgt Range', 'I-FURN', 'seat'),
    ('Meeting chair_Haworth_Chair_Very-Task - SE14 GM CHAIR', 'I-FURN', 'seat'),
    ('BENCH-INSTANCE GENERIC - TYPE 1', 'Q-CASE', 'seat'),
    ('Fritz-Hansen_SH200 - Default', 'I-FURN', 'other'),                                        # says nothing, and I-FURN says nothing
    ('Generic Models 1 - Generic Models 1', 'A-GENM', 'other'),
    # names of the other two projects
    ('dining chair', 'FURN', 'seat'), ('table lamp', 'FURN', 'lamp'), ('BEDSIDE TABLE', 'FURN', 'coffee-table'),
    ('Double Curtain', 'DA-FACILITIES', 'curtain'), ('Movable panel', 'FURN', 'partition'), ('SmartToilet', 'FURN', 'sanitary'),
    # word edges
    ('Sofas', '', 'sofa'), ('TVStand', '', 'cabinet'), ('TV unit', '', 'cabinet'), ('Desk chair', '', 'seat'), ('Computer desk', '', 'table'),
    ('Counter stool', '', 'seat'), ('Reception counter', '', 'counter'), ('Bar table', '', 'bar-table'), ('Bar stool', '', 'seat'),
    ('BED SIDE TABLE', '', 'coffee-table'), ('King Bed', '', 'bed'), ('Sofa bed', '', 'sofa'), ('Wardrobe', '', 'tall-cabinet'),
    ('Chesterfield', '', 'sofa'), ('Shower tray', '', 'sanitary'), ('Stable door', '', 'other'),
]
for fam, lay, kind in REAL: ok(fk.classify(fam, lay) == kind, fam, fk.classify(fam, lay), kind)
# the seat back's words are tried before the sofa and seat rules; the trap names keep their kinds (a whole word: LOVESEAT BACK is a sofa)
for fam, kind in (('SOFA BACK CUSHION', 'seat-back'), ('backrest', 'seat-back'), ('Back rest - 600W', 'seat-back'), ('SEAT_BACK-1', 'seat-back'),
                  ('Seatback', 'seat-back'), ('Back cushions', 'seat-back'), ('Sofa seat back', 'seat-back'), ('Chair backrest', 'seat-back'),
                  ('SOFA_BENCH_DIOR - TYPE 2', 'sofa'), ('CHAIR_BENCH BACK - SE107 STOOL LOW_VITRA_VISIONA STOOL', 'seat'), ('Sofa bed', 'sofa'),
                  ('LOVESEAT BACK', 'sofa'), ('Seating', 'seat'), ('Backpack', 'other'), ('Feedback', 'other'), ('Back', 'other')):
    ok(fk.classify(fam, 'I-FURN') == kind, fam, fk.classify(fam, 'I-FURN'), kind)
rule_order = [k for k, _, _ in fk.RULES]
ok(rule_order.index('seat-back') < rule_order.index('sofa') < rule_order.index('seat'), rule_order)
for fam in ('COVER - TYPE 1', 'TV OUTLET - TYPE 1', 'SAVING POINT OUTLET - DUPLEX', 'Rectangular Mullion - 100X50', 'Persian Rug', 'Floor box'):
    ok(fk.classify(fam, 'A-GENM') is None, fam)
ok(fk.classify('', 'Q-CASE') == 'cabinet' and fk.classify('', 'L-PLNT') == 'plant' and fk.classify('', 'P-SANR-FIXT') == 'sanitary'
   and fk.classify('', 'I-FURN') == 'other' and fk.classify('', '') == 'other')                # the layer words, only when the name says nothing
ok(fk.classify('Chair', 'P-SANR-FIXT') == 'seat')                                               # the name wins over the layer
ok(fk.classify('Hammock', 'I-FURN') == 'other' and fk.classify('Hammock', 'I-FURN', {'bed': ['hammock']}) == 'bed')
ok(fk.classify('Big hammock chair', 'I-FURN', {'bed': ['hammock']}) == 'bed')                   # the office's words win over the vocabulary
ok(fk.classify('Fritz-Hansen_SH200 - Default', 'I-FURN', {'seat': ['Fritz-Hansen']}) == 'seat')   # a maker's name the vocabulary cannot know: the office says what it is
ok(fk.classify('FRITZ-HANSEN_SH200', '', {'seat': ['Fritz-Hansen']}) == 'seat' and fk.classify('Fritz-Hansenberg_X', '', {'seat': ['Fritz-Hansen']}) == 'other')   # a whole word, any case
ok(fk.classify('Dummy chair', 'I-FURN') == 'seat' and fk.classify('Dummy chair', 'I-FURN', skip=['dummy']) is None)
ok(fk.classify('Dummy chair', 'I-FURN', {'seat': ['dummy']}, ['dummy']) is None)                # a skip word rules a name out before the office's words are tried
ok(fk.classify('Rest.Pro_1', '', {'bed': ['Rest.Pro']}) == 'bed' and fk.classify('Rest-Pro_1', '', {'bed': ['Rest.Pro']}) == 'other')       # the office's words are text, not regex: a dot is a dot
ok(fk.classify('Rest.Pro chair', '', skip=['Rest.Pro']) is None and fk.classify('Rest-Pro chair', '', skip=['Rest.Pro']) == 'seat')
ok(fk.classify('Mini bar', 'I-FURN', {'appliance': ['mini bar']}) == 'appliance' and fk.classify('Mini_Bar', '', {'appliance': ['mini bar']}) == 'appliance')
ok(fk.classify('x', '', {'_why': ['note'], 'bed': []}) == 'other')                              # notes and empty lists in the project file are ignored
try:
    fk.classify('x', '', {'sofabed': ['x']}); ok(False)
except ValueError as e:
    ok('sofabed' in str(e))

# ---------------------------------------------------------------------------------------------------- box_of
b = fk.box_of(rect_pts(3, 4, 2, 1, 0))
ok(near(b['x'], 3) and near(b['y'], 4) and near(b['w'], 2) and near(b['d'], 1) and near(b['rot'], 0), b)
for ang in range(-180, 541, 15):                                # a 2 x 1 box turned any way: found again, rot in [0, 180)
    b = fk.box_of(rect_pts(3, 4, 2, 1, ang))
    ok(0 <= b['rot'] < 180 and near(b['w'], 2) and near(b['d'], 1) and near(b['x'], 3) and near(b['y'], 4), ang, b)
    ok(min(abs(b['rot'] - ang % 180), 180 - abs(b['rot'] - ang % 180)) < 1e-3, ang, b['rot'])
for ang in (0, 30, 120, 200):                                   # a square: rot in [0, 90), the same box whichever way it is turned
    b = fk.box_of(rect_pts(0, 0, 1, 1, ang))
    ok(near(b['w'], 1) and near(b['d'], 1) and 0 <= b['rot'] < 90, ang, b)
    ok(min(abs(b['rot'] - ang % 90), 90 - abs(b['rot'] - ang % 90)) < 1e-3, ang, b)
ring = [(0.25 * math.cos(t * math.pi / 12), 0.25 * math.sin(t * math.pi / 12)) for t in range(24)]
b = fk.box_of(ring)
ok(b['w'] <= 0.5 + 1e-6 and b['d'] >= 0.49 and b['rot'] < 90, b)
ok(fk.box_of([]) is None and fk.box_of([(1, 1)]) is None and fk.box_of([(1, 1), (1, 1)]) is None)
ok(fk.box_of([(0, 0), (1, 1)]) is None and fk.box_of([(0, 0), (1, 1), (2, 2), (0.5, 0.5)]) is None and fk.box_of([(0, 0), (3, 0), (1, 0)]) is None)   # a line
ok(fk.box_of(rect_pts(0, 0, 2, 0.0005, 0)) is None)             # no thickness at all
b = fk.box_of(rect_pts(0, 0, 2, 0.004, 40))                     # thin: given the minimum thickness
ok(near(b['d'], fk.MIN_SIDE) and near(b['w'], 2, 0.01) and near(b['rot'], 40, 0.1), b)
ok(all(math.isfinite(v) for v in fk.box_of([(1e-9, 0), (5, 1e-9), (5, 3), (0, 3)]).values()))
ok(set(fk.box_of(rect_pts(0, 0, 2, 1, 10))) == {'x', 'y', 'w', 'd', 'rot'})

# ---------------------------------------------------------------------------------------------------- merge_fronts
def front(x, y, rot=0.0, w=0.5, **kw): return piece(**{**dict(family='DOOR', block='DOOR-1', x=x, y=y, w=w, d=0.025, rot=rot), **kw})
carcass = lambda **kw: piece(**{**dict(kind='tall-cabinet', family='TALL', block='TALL-1', handle='AB', x=0.0, y=0.0, w=4.0, d=0.4), **kw})

out, st = fk.merge_fronts([carcass(), front(-1.0, 0.19), front(0.0, 0.19), front(1.0, 0.19)])     # doors in the cabinet's face
ok(len(out) == 1 and out[0]['n'] == 4 and st == {'absorbed': 3, 'grown': 0, 'runs': 0, 'inRuns': 0}, out, st)
ok((out[0]['x'], out[0]['y'], out[0]['w'], out[0]['d'], out[0]['rot']) == (0.0, 0.0, 4.0, 0.4, 0.0) and out[0]['kind'] == 'tall-cabinet', out[0])
ok(out[0]['handle'] == 'AB' and out[0]['family'] == 'TALL' and '3 x DOOR' in out[0]['note'], out[0])
out, st = fk.merge_fronts([carcass(), front(0.5, 0.2)])                              # a front a little proud of the face: the box grows
ok(len(out) == 1 and st['grown'] == 1 and near(out[0]['d'], 0.4125) and near(out[0]['y'], 0.00625) and near(out[0]['w'], 4.0), out, st)
out, st = fk.merge_fronts([carcass(), front(1.0, 0.45, 90)])                         # a door swung open: absorbed and counted, the box stays
ok(len(out) == 1 and out[0]['n'] == 2 and st['grown'] == 0 and (out[0]['d'], out[0]['w']) == (0.4, 4.0), out, st)
out, st = fk.merge_fronts([carcass(), front(0.0, 0.2 + 0.1 + 0.0125)])               # 10 cm off the face: still the cabinet's
ok(len(out) == 1 and out[0]['n'] == 2, out)
out, st = fk.merge_fronts([carcass(), front(0.0, 0.2 + 0.4)])                        # 40 cm off: not its front
ok(len(out) == 2 and st['absorbed'] == 0, out)
out, st = fk.merge_fronts([carcass(floor='L2'), front(0.0, 0.19)])                   # a cabinet on another floor is not near
ok(len(out) == 2 and st['absorbed'] == 0)
small, big = carcass(w=1.0, d=0.4, kind='cabinet', family='S'), carcass(w=4.0, d=0.6, kind='counter', family='B')
out, st = fk.merge_fronts([big, small, front(0.0, 0.19)])                            # inside two boxes: the smaller one
ok(len(out) == 2 and [p['n'] for p in out if p['family'] == 'S'] == [2] and [p['n'] for p in out if p['family'] == 'B'] == [1], out)
out, st = fk.merge_fronts([piece(kind='cabinet', x=0, y=0, w=1.0, d=0.4), piece(kind='cabinet', x=0, y=0.3, w=1.0, d=0.4)])   # real cabinets are not fronts
ok(len(out) == 2 and st['absorbed'] == 0)
out, st = fk.merge_fronts([piece(kind='seat', x=0, y=0, w=0.5, d=0.03), piece(kind='seat', x=0.51, y=0, w=0.5, d=0.03)])   # only cabinet kinds have fronts
ok(len(out) == 2 and st['runs'] == 0)
out, st = fk.merge_fronts([front(0.0, 3.0), front(0.51, 3.0), front(1.02, 3.0)])      # no cabinet: three fronts edge to edge are a run
ok(len(out) == 1 and st == {'absorbed': 0, 'grown': 0, 'runs': 1, 'inRuns': 3}, out, st)
r = out[0]
ok(near(r['x'], 0.51) and near(r['y'], 3.0) and near(r['w'], 1.52) and near(r['d'], fk.RUN_DEPTH) and near(r['rot'], 0) and r['n'] == 3 and r['handle'] == ''
   and r['kind'] == 'cabinet' and r['family'] == 'DOOR' and 'run of 3 fronts' in r['note'], r)
mixed = [front(0.0, 3.0), dict(front(0.51, 3.0), family='DRAWER', block='DRAWER-9', layer='Q-CASE-X', kind='tall-cabinet'), front(1.02, 3.0, family='DOOR', block='DOOR-2')]
out, st = fk.merge_fronts(mixed)                                                     # a run takes family, block, layer and kind from its commonest front
ok(len(out) == 1 and out[0]['family'] == 'DOOR' and out[0]['block'] == 'DOOR-1' and out[0]['layer'] == 'Q-CASE' and out[0]['kind'] == 'cabinet', out)
ok('2 x DOOR' in out[0]['note'] and '1 x DRAWER' in out[0]['note'], out[0]['note'])
out, st = fk.merge_fronts([front(0.0, 3.0, w=0.1), front(0.11, 3.0, w=0.1)])         # a run shorter than it is deep: long side first
ok(len(out) == 1 and near(out[0]['w'], fk.RUN_DEPTH) and near(out[0]['d'], 0.21) and near(out[0]['rot'], 90) and near(out[0]['x'], 0.055) and near(out[0]['y'], 3.0), out)
out, st = fk.merge_fronts([front(3.0, 0.0, 90), front(3.0, 0.52, 90), front(3.0, -0.52, 90)])   # a run along y
ok(len(out) == 1 and near(out[0]['rot'], 90) and near(out[0]['w'], 1.54) and near(out[0]['y'], 0.0) and near(out[0]['x'], 3.0), out)
out, st = fk.merge_fronts([front(0.0, 3.0), front(0.7, 3.0)])                        # a 0.2 m gap: no run
ok(len(out) == 2 and st['runs'] == 0 and all(p['d'] == 0.025 for p in out))
out, st = fk.merge_fronts([front(0.0, 3.0), front(0.51, 3.0, 10)])                   # 10 degrees apart: no run
ok(len(out) == 2 and st['runs'] == 0)
out, st = fk.merge_fronts([front(0.0, 3.0), front(0.51, 3.0, 4)])                    # 4 degrees apart: a run
ok(len(out) == 1 and st['runs'] == 1)
out, st = fk.merge_fronts([front(0.0, 3.0), front(0.51, 3.0, floor='L2')])           # on different floors: no run
ok(len(out) == 2)
out, st = fk.merge_fronts([front(0.0, 3.0)])                                         # a lone front stays as drawn
ok(len(out) == 1 and out[0]['d'] == 0.025 and out[0]['n'] == 1)
src = [carcass(), front(0.5, 0.2)]
fk.merge_fronts(src)
ok(src[0]['d'] == 0.4 and src[0]['n'] == 1 and len(src) == 2)                        # the input is not changed

# ---------------------------------------------------------------------------------------------------- loose_boxes
rect = [LineString([(0, 0), (2, 0)]), LineString([(2, 0), (2, 0.6)]), LineString([(2, 0.6), (0, 0.6)]), LineString([(0, 0.6), (0, 0)]),
        LineString([(0.5, 0.3), (0.52, 0.31)]), LineString([(0.5, 0.3), (0.5, 0.35)])]     # an outline, and two strokes that touch only each other
boxes, left = fk.loose_boxes(rect)
ok(len(boxes) == 1 and boxes[0]['n'] == 4 and near(boxes[0]['w'], 2) and near(boxes[0]['d'], 0.6) and len(left) == 1 and left[0][0] == 2, boxes, left)
boxes, left = fk.loose_boxes(rect[:4] + [LineString([(1, 0.3), (1.0, 0.0)])])             # a line meeting the outline joins the cluster
ok(len(boxes) == 1 and boxes[0]['n'] == 5 and not left)
boxes, left = fk.loose_boxes([LineString([(0, 0), (2, 0)]), LineString([(2.009, 0), (2.009, 0.6)]), LineString([(2.5, 0), (2.5, 1)])])   # 9 mm gap joins, 50 cm does not
ok(not boxes and sorted(n for n, _ in left) == [1, 2] and any('no area' in w or 'fewer' in w for _, w in left), left)
boxes, left = fk.loose_boxes([Polygon([(0, 0), (1, 0), (1, 0.5), (0, 0.5)])])             # one closed outline is a piece
ok(len(boxes) == 1 and boxes[0]['n'] == 1 and near(boxes[0]['w'], 1) and near(boxes[0]['d'], 0.5))
boxes, left = fk.loose_boxes([LineString([(0, 0), (2, 0)]), LineString([(0, 0), (0, 2)]), LineString([(0, 2), (2, 0)])])   # a triangle drawn as three lines: half its box
ok(not boxes and len(left) == 1 and 'fills' in left[0][1], left)
boxes, left = fk.loose_boxes([LineString([(0, 0), (1, 0)]), LineString([(1, 0), (2, 0)]), LineString([(2, 0), (3, 0)])])      # a straight line
ok(not boxes and left == [(3, 'no area')], left)
boxes, left = fk.loose_boxes([Polygon([(0, 0), (1, 0), (1, 0.5), (0, 0.5)]), Polygon([(5, 5), (6, 5), (6, 6), (5, 6)])])   # two apart: two boxes, in input order
ok(len(boxes) == 2 and boxes[0]['x'] < boxes[1]['x'] and not left)
ok(fk.loose_boxes([]) == ([], []))

# ---------------------------------------------------------------------------------------------------- finish: ids, supports, kinds
table = piece(kind='table', family='T', block='T-1', layer='I-FURN', x=0.0, y=0.0, w=2.0, d=1.0)
counter = piece(kind='counter', family='C', block='C-1', layer='Q-CASE', x=0.5, y=0.2, w=0.8, d=0.6)
pcs = [table, counter,
       piece(kind='computer', family='PC', x=0.5, y=0.2, w=0.74, d=0.43, layer='I-FURN'),          # inside the table and the counter: the smaller one
       piece(kind='computer', family='PC', x=-0.8, y=0.0, w=0.74, d=0.43, layer='I-FURN'),         # inside the table only
       piece(kind='computer', family='PC', x=5.0, y=5.0, w=0.74, d=0.43, layer='I-FURN'),          # on nothing
       piece(kind='computer', family='PC', x=0.5, y=0.2, w=0.74, d=0.43, layer='I-FURN', floor='L2'),   # same place on the other floor: nothing there
       piece(kind='seat', family='CH', x=3.0, y=1.0, w=0.5, d=0.5), piece(kind='seat', family='CH', x=1.0, y=1.0, w=0.5, d=0.5),
       piece(kind='seat', family='CH', x=2.0, y=1.0, w=0.5, d=0.5), piece(kind='seat', family='CH', x=2.0, y=-4.0, w=0.5, d=0.5)]
fur, kinds = fk.finish(pcs, ['L1', 'L2'])
ids = [p['id'] for p in fur]
ok(len(set(ids)) == len(ids) == len(pcs))
byid = {p['id']: p for p in fur}
ok([p['id'] for p in fur if p['kind'] == 'seat'] == ['L1-seat-001', 'L1-seat-002', 'L1-seat-003', 'L1-seat-004'])
ok([(p['x'], p['y']) for p in fur if p['kind'] == 'seat'] == [(1.0, 1.0), (2.0, -4.0), (2.0, 1.0), (3.0, 1.0)])      # x, then y
comps = [p for p in fur if p['kind'] == 'computer']
ok([p['id'] for p in comps] == ['L1-computer-001', 'L1-computer-002', 'L1-computer-003', 'L2-computer-001'], [p['id'] for p in comps])
ok([p['on'] for p in comps] == ['L1-table-001', 'L1-counter-001', None, None], [p['on'] for p in comps])
ok(all(p['on'] is None for p in fur if p['kind'] != 'computer'))                                                  # supports never sit on anything
ok(all(p['on'] is None or (byid[p['on']]['floor'] == p['floor'] and fk.KINDS[[k['key'] for k in fk.KINDS].index(byid[p['on']]['kind'])]['support']) for p in fur))
ok(list(fur[0]) == ['id', 'floor', 'kind', 'family', 'block', 'layer', 'handle', 'x', 'y', 'w', 'd', 'rot', 'on', 'approach', 'n', 'note'])
ok(all(p['approach'] == [] for p in fur) and len({id(p['approach']) for p in fur}) == len(fur))                  # no openings given: every box still has its own empty list
ok([p['floor'] for p in fur] == ['L1'] * 9 + ['L2'] and [k['key'] for k in kinds] == ['computer', 'seat', 'table', 'counter'], [k['key'] for k in kinds])
ok({k['key']: k['count'] for k in kinds} == {'computer': 4, 'seat': 4, 'table': 1, 'counter': 1} and sum(k['count'] for k in kinds) == len(fur))
ok(all(set(k) == {'key', 'label', 'colour', 'height', 'base', 'onTop', 'support', 'blocks', 'count'} for k in kinds))
for _ in range(5):                                                                                                  # the order of the input does not matter
    shuffled = pcs[:]; random.shuffle(shuffled)
    ok(fk.finish(shuffled, ['L1', 'L2']) == (fur, kinds))
fur2, kinds2 = fk.finish(pcs, ['L1', 'L2'], {'table': 740, '_why': 1}, {'tv': 950})
ok({k['key']: k['height'] for k in kinds2}['table'] == 740 and {k['key']: k['height'] for k in kinds2}['seat'] == 450)
ok(fk.finish([piece(kind='tv')], ['L1'], None, {'tv': 950})[1][0]['base'] == 950 and fk.finish([piece(kind='tv')], ['L1'])[1][0]['base'] == 900)
ok('seat-back' not in [k['key'] for k in kinds])                                                                    # a model lists only the kinds that occur
# a seat back stands on the floor, never on a support, even drawn over a table (the hotel's were first read as screens on a table)
fur3, kinds3 = fk.finish([piece(kind='table', family='T', x=0.0, y=0.0, w=2.0, d=2.0), piece(kind='seat-back', family='seat back', x=0.5, y=0.0, w=0.8, d=0.2),
                          piece(kind='seat', family='round sofa', x=0.0, y=0.0, w=2.0, d=2.0), piece(kind='sofa', family='S', x=5.0, y=0.0, w=2.0, d=0.8)], ['L1'])
ok([k['key'] for k in kinds3] == ['seat', 'sofa', 'seat-back', 'table'] and all(p['on'] is None for p in fur3), [k['key'] for k in kinds3], [p['on'] for p in fur3])
ok([p['id'] for p in fur3] == ['L1-seat-001', 'L1-sofa-001', 'L1-seat-back-001', 'L1-table-001'], [p['id'] for p in fur3])
sb_row = next(r for r in csv.reader(io.StringIO(fk.csv_text(fur3, kinds3, ['L1'], [0.0, 0.0]), newline='')) if r[0] == 'L1-seat-back-001')
ok(sb_row[2:4] == ['seat-back', 'Seat back'] and sb_row[12:16] == ['800', '0', '0.0', ''], sb_row)                   # 800 mm from the floor, on top of nothing
for bad in (({'sofabed': 1}, None), ({'table': -5}, None), ({'table': 'tall'}, None), (None, {'tv': -1}), ({'table': True}, None), ({'table': 0}, None)):
    try:
        fk.finish(pcs, ['L1', 'L2'], *bad); ok(False, bad)
    except ValueError:
        ok(True)
try:
    fk.finish([piece(floor='L9')], ['L1']); ok(False)
except ValueError:
    ok(True)
o = fk.finish([piece(x=-0.0004, y=1.23449, rot=179.996, w=0.9996, d=0.1)], ['L1'])[0][0]
ok(str(o['x']) == '0.0' and o['y'] == 1.234 and o['rot'] == 0.0 and o['w'] == 1.0 and o['d'] == 0.1, o)       # no -0.0; mm; 180 wraps to 0
ok(fk.finish([], ['L1']) == ([], []))
ok(fk.finish([piece(rot=-10.0)], ['L1'])[0][0]['rot'] == 170.0)
rot_of = lambda rot, w=0.38, d=0.38: fk.finish([piece(w=w, d=d, rot=rot)], ['L1'])[0][0]['rot']
ok(rot_of(89.996) == 0.0 and rot_of(89.994) == 89.99 and rot_of(90.0) == 0.0 and rot_of(135.0) == 45.0 and rot_of(0.004) == 0.0 and rot_of(-0.004) == 0.0)   # a square: rot in [0, 90), the rounding never reaches 90
ok(rot_of(179.996) == 0.0 and rot_of(179.994) == 89.99 and rot_of(269.996) == 0.0 and rot_of(-90.0) == 0.0)                                              # ... whichever way it was turned
ok(rot_of(179.996, 0.9, 0.4) == 0.0 and rot_of(179.994, 0.9, 0.4) == 179.99 and rot_of(89.996, 0.9, 0.4) == 90.0 and rot_of(90.0, 0.9, 0.4) == 90.0)      # not a square: [0, 180), 90 is a rot like any other
ok(rot_of(135.0, 0.3809, 0.38) == 45.0 and rot_of(135.0, 0.3811, 0.38) == 135.0)    # square or not is decided on w - d before the rounding: 1 mm apart after it either way
ok(rot_of(135.0, 0.5, 0.5) == 45.0 and rot_of(135.0, 0.5, 0.4991) == 45.0 and rot_of(135.0, 0.5, 0.4989) == 135.0)
sweep = [(base + k * 0.0001) % 360 for base in (0, 90, 180, 270, 360) for k in range(-60, 61)]                                                              # angles either side of every quarter turn
pcs = [piece(x=float(i), w=w, d=d, rot=a) for w, d in ((0.38, 0.38), (0.9, 0.4)) for i, a in enumerate(sweep, 1 if w == 0.38 else len(sweep) + 1)]
fur, _ = fk.finish(pcs, ['L1'])
ok(len(fur) == 2 * len(sweep) and all(0 <= p['rot'] < (90 if p['w'] == p['d'] else 180) and p['rot'] == round(p['rot'], 2) for p in fur), [p['rot'] for p in fur if p['rot'] >= 90 and p['w'] == p['d']])

# ---------------------------------------------------------------------------------------------------- supports: inside a box, or within 10 cm of it
def supports(*pcs):
    """assign_supports on pieces numbered p0, p1 ... -> what each stands on (an id, or None)."""
    pcs = [dict(p, id=f'p{i}') for i, p in enumerate(pcs)]
    fk.assign_supports(pcs, fk.KINDS)
    return [p['on'] for p in pcs]


counter = piece(kind='counter', x=0.0, y=0.0, w=2.0, d=0.6)                          # x -1..1, y -0.3..0.3
prn = lambda x, y, **kw: piece(**{**dict(kind='printer', family='P', x=x, y=y, w=0.4, d=0.4), **kw})
ok(fk.OVERHANG == 0.10 and next(k for k in fk.KINDS if k['key'] == 'tall-cabinet')['support'] is False)
ok(supports(counter, prn(0.3, 0.1)) == [None, 'p0'])                                 # inside: as before
ok(supports(counter, prn(0.0, 0.3 + 0.08)) == [None, 'p0'])                          # 8 cm outside its long edge: on the counter's overhang
ok(supports(counter, prn(-1.0 - 0.08, 0.1)) == [None, 'p0'])                         # 8 cm past its end
ok(supports(counter, prn(0.0, 0.3 + 0.10)) == [None, 'p0'])                          # 10 cm exactly: still on it
ok(supports(counter, prn(0.0, 0.3 + 0.101)) == [None, None] and supports(counter, prn(0.0, 0.3 + 0.12)) == [None, None])     # 10.1 and 12 cm: on nothing
ok(supports(counter, prn(1.07, 0.37)) == [None, 'p0'] and supports(counter, prn(1.08, 0.38)) == [None, None])    # past a corner: the straight distance to it, 9.9 and 11.3 cm
ok(near(fk._gap(prn(1.08, 0.38), counter), math.hypot(0.08, 0.08)) and fk._gap(prn(0.3, 0.1), counter) == 0 and near(fk._gap(prn(0.0, 0.38), counter), 0.08))
turned = piece(kind='counter', x=3.0, y=1.0, w=2.0, d=0.6, rot=30.0)                 # the same counter turned 30 degrees about its centre
ux, uy = (math.cos(math.radians(30)), math.sin(math.radians(30))), (-math.sin(math.radians(30)), math.cos(math.radians(30)))
at = lambda a, b: prn(3.0 + a * ux[0] + b * uy[0], 1.0 + a * ux[1] + b * uy[1])      # a metres from its centre along its long axis, b across
ok(supports(turned, at(0.5, 0.2)) == [None, 'p0'] and supports(turned, at(1.08, 0.0)) == [None, 'p0'] and supports(turned, at(-0.4, -0.38)) == [None, 'p0'])
ok(supports(turned, at(1.12, 0.0)) == [None, None] and supports(turned, at(-0.4, -0.42)) == [None, None] and supports(turned, at(1.08, 0.38)) == [None, None])
ok(supports(turned, prn(4.08, 1.0)) == [None, None])                                 # 6 cm off the turned counter's bounding box, but 24 cm from the counter itself
ok(supports(counter, prn(0.0, 0.38, floor='L2')) == [None, None])                    # a counter on another floor is out of reach, however close

low, high = counter, piece(kind='cabinet', x=0.0, y=0.67, w=1.0, d=0.5)              # a 12 cm gap between a counter (area 1.2) and a cabinet (area 0.5)
ok(supports(low, high, prn(0.0, 0.35)) == [None, None, 'p0'])                        # 5 and 7 cm: the nearer, though it is the bigger box
ok(supports(low, high, prn(0.0, 0.37)) == [None, None, 'p1'])                        # 7 and 5 cm: the cabinet
ok(supports(low, high, prn(0.0, 0.36)) == [None, None, 'p1'] and supports(high, low, prn(0.0, 0.36)) == [None, None, 'p0'])   # 6 and 6 cm: the smaller box, in either order
ok(supports(low, high, prn(0.0, 0.27)) == [None, None, 'p0'])                        # inside the counter (0), 15 cm from the cabinet
ok(supports(low, piece(kind='cabinet', x=0.0, y=0.57, w=1.0, d=0.5), prn(0.0, 0.27)) == [None, None, 'p0'])    # inside one, 5 cm from a smaller one: the one it is inside
ok(supports(low, piece(kind='cabinet', x=0.0, y=0.0, w=0.5, d=0.3), prn(0.1, 0.0)) == [None, None, 'p1'])      # inside both: the smaller box, as before
twin = [piece(kind='cabinet', x=-0.55, y=0.0), piece(kind='cabinet', x=0.55, y=0.0), prn(0.0, 0.0)]            # 5 cm from each of two cabinets of one size
for _ in range(4):
    random.shuffle(twin)
    ok([p['on'] for p in fk.finish(twin, ['L1'])[0] if p['kind'] == 'printer'] == ['L1-cabinet-001'])           # the lower id, whatever the order of the input

for k in fk.KINDS:                                                                   # only the support kinds hold a top: not a tall cabinet, a seat, a TV ...
    ok(supports(piece(kind=k['key'], x=0.0, y=0.0, w=2.0, d=0.6), prn(0.0, 0.0))[1] == ('p0' if k['support'] else None), k['key'])
    ok(supports(piece(kind=k['key'], x=0.0, y=0.0, w=2.0, d=0.6), prn(0.0, 0.38))[1] == ('p0' if k['support'] else None), k['key'])
tall = piece(kind='tall-cabinet', x=0.0, y=0.0, w=2.0, d=0.6)
ok(supports(tall, piece(kind='cabinet', x=0.0, y=0.54, w=1.0, d=0.4), prn(0.0, 0.25)) == [None, None, 'p1'])  # inside a tall cabinet, 9 cm from a cabinet: the cabinet's
ok(supports(tall, piece(kind='cabinet', x=0.0, y=0.58, w=1.0, d=0.4), prn(0.0, 0.25)) == [None, None, None])  # ... and 13 cm from it: nobody's
big = piece(kind='counter', x=0.0, y=0.0, w=4.0, d=2.0)                              # y -1..1
for kind in (k['key'] for k in fk.KINDS if k['support']):                            # a support never stands on anything: inside a counter, or 5 cm outside it
    ok(supports(big, piece(kind=kind, x=0.0, y=0.2, w=1.0, d=0.5)) == [None, None] and supports(big, piece(kind=kind, x=0.0, y=1.05, w=1.0, d=0.5)) == [None, None], kind)
pcs = [dict(counter, id='c'), dict(prn(0.0, 0.38), id='p')]
fk.assign_supports(pcs, {k['key']: k for k in fk.KINDS})                             # the kinds as a dict (key -> kind) do as well as the list
ok([p['on'] for p in pcs] == [None, 'c'])

ov = [piece(kind='counter', family='C', block='C-1', x=0.0, y=0.0, w=2.0, d=0.6), prn(0.5, 0.38, block='P-1'), prn(-0.5, 0.52, block='P-2'),       # 8 and 22 cm beyond the counter's edge
      piece(kind='tall-cabinet', family='T', block='T-1', x=5.0, y=0.0, w=1.0, d=0.6), prn(5.0, 0.38, block='P-3')]                              # 8 cm beside a tall cabinet
fur, kinds = fk.finish(ov, ['L1'])
by = {p['block']: p for p in fur}
ok([(by[b]['id'], by[b]['on']) for b in ('P-1', 'P-2', 'P-3')] == [('L1-printer-002', 'L1-counter-001'), ('L1-printer-001', None), ('L1-printer-003', None)], [(p['id'], p['on']) for p in fur])
rows = {r[0]: r for r in csv.reader(io.StringIO(fk.csv_text(fur, kinds, ['L1'], [0.0, 0.0]), newline=''))}
ok(rows['L1-printer-002'][13] == '850' and rows['L1-printer-002'][15] == 'L1-counter-001' and rows['L1-printer-001'][13] == '0' and rows['L1-printer-003'][15] == '')   # base = the counter's top
typed = {r[0]: r for r in csv.reader(io.StringIO(fk.csv_text(fur, kinds, ['L1'], [0.0, 0.0], {'counter': 900}), newline=''))}
ok(typed['L1-printer-002'][13] == '900' and typed['L1-printer-001'][13] == '0')      # a typed counter height moves the printer on it

# ---------------------------------------------------------------------------------------------------- approaches: what a person needs to walk through a door
def opening(oid='D1', kind='door', floor='L1', x=0.0, y=0.0, nx=0.0, ny=1.0, width=0.9, **kw):
    """An opening as the model's list has it: in the middle of its gap (x, y), the wall along x unless the normal (nx, ny) says otherwise."""
    return dict(id=oid, kind=kind, floor=floor, x=x, y=y, nx=nx, ny=ny, width=width, wallThickness=0.1, **kw)


def approaches(openings, *pcs):
    """mark_approaches on copies of the pieces -> the 'approach' of each."""
    pcs = [dict(p) for p in pcs]
    fk.mark_approaches(pcs, openings)
    return [p['approach'] for p in pcs]


chair = lambda x, y, **kw: piece(**{**dict(kind='seat', family='CH', x=x, y=y, w=0.45, d=0.45), **kw})
desk = lambda x, y, rot, w=1.6, d=0.6, **kw: piece(**{**dict(kind='table', family='DESK', x=x, y=y, w=w, d=d, rot=rot), **kw})
cab = lambda x, y, w, d=0.5, rot=0.0, **kw: piece(**{**dict(kind='cabinet', family='CAB', x=x, y=y, w=w, d=d, rot=rot), **kw})
door = opening()                                                       # 0.9 wide in a wall along x: Z reaches 0.75 each way along the wall and 0.9 across it, the corridor 0.45 and 0.9
readme = (HERE / 'README.md').read_text(encoding='utf-8')
ok(fk.PERSON == 0.30 and fk.APPROACH_SIDE == 0.90 and fk.APPROACH_AREA == 0.0025 and fk.APPROACH_KINDS == ('door', 'passage'))
ok('0.30 m' in readme and '1.80 m' in readme and '0.0025 m2' in readme and f'{fk.PERSON:.2f} m' in readme and f'{2 * fk.APPROACH_SIDE:.2f} m' in readme, 'the README states the same numbers')

# a chair 0.6 m to the side of a 0.68 m door: its centre is in Z (0.34 + 0.30 = 0.64), its box (0.375 .. 0.825) is clear of the corridor (0.34): the centre says so
d68 = [opening(width=0.68)]
ok(approaches(d68, chair(0.60, 0.5), chair(0.64, 0.5), chair(0.66, 0.5)) == [['D1'], ['D1'], []])                    # the edge of Z counts, 2 cm past it does not
ok(approaches(d68, chair(0.60, 0.89), chair(0.60, 0.91), chair(0.60, -0.89), chair(0.60, -0.91)) == [['D1'], [], ['D1'], []])   # 0.90 m out of the wall, each side
ok(approaches(d68, chair(0.0, 0.0), chair(-0.60, 0.5), chair(-0.66, 0.5), chair(0.0, -0.5)) == [['D1'], ['D1'], [], ['D1']])  # in the wall's line, and the other way along the wall

# a desk across the corridor with its centre outside Z
ok(approaches([door], desk(0.0, 1.6, 90)) == [['D1']] and approaches([door], desk(0.0, -1.6, 90)) == [['D1']])       # standing out from the wall, y 0.8 .. 2.4: 0.1 m of it lies across the corridor (600 cm2); either side
ok(approaches([door], desk(0.0, 1.8, 90)) == [[]] and approaches([door], desk(0.0, -1.8, 90)) == [[]])              # y 1.0 .. 2.6: stops short of it
ok(approaches([door], desk(2.0, 0.5, 0, 3.4, 0.5)) == [['D1']] and approaches([door], desk(-2.0, 0.5, 0, 3.4, 0.5)) == [['D1']])   # lying along the wall, x 0.3 .. 3.7: its end is 15 cm into the corridor, its centre 2 m along

# a long cabinet that only touches the margin of Z with its end is not in the approach
ok(approaches([door], cab(2.1, 0.5, 3.0), cab(-2.1, 0.5, 3.0)) == [[], []])                                          # x 0.6 .. 3.6: its end is in the 0.30 m margin (0.45 .. 0.75), clear of the corridor
ok(approaches([door], cab(1.95, 0.5, 3.0), cab(-1.95, 0.5, 3.0, rot=180.0)) == [[], []])                            # x 0.45 .. 3.45: touches the corridor's edge and no more: no area
ok(approaches([door], cab(1.9452, 0.5, 3.0), cab(1.945, 0.5, 3.0), cab(1.9448, 0.5, 3.0)) == [[], ['D1'], ['D1']])  # 24 cm2 of the corridor: not in it; exactly 25: in it; 26: in it
ok(approaches([door], cab(1.9452, 0.9, 3.0, d=1.0), cab(1.9448, 0.9, 3.0, d=1.0)) == [[], ['D1']])                  # y 0.4 .. 1.4: the half beyond the corridor's 0.9 does not count, so 24 and 26 cm2 again
ok(approaches([door], desk(1.2, 0.0, 90, 1.0, 0.5), desk(0.0, 1.2, 0, 1.0, 0.5)) == [[], []])                       # near and clear: x 0.95 .. 1.45 beside the corridor, y 0.95 .. 1.45 beyond it

# a window has no approach; neither does a door on another floor
ok(approaches([opening(kind='window')], chair(0.0, 0.3)) == [[]] and approaches([opening('W1', kind='window'), door], chair(0.0, 0.3)) == [['D1']])
ok(approaches([opening(floor='L2')], chair(0.0, 0.3), chair(0.0, 0.3, floor='L2')) == [[], ['D1']])
ok(approaches([opening('A', floor='L1'), opening('B', floor='L2')], chair(0.0, 0.3), chair(0.0, 0.3, floor='L2'), chair(0.0, 0.3, floor='L3')) == [['A'], ['B'], []])
p1 = [opening('P1', kind='passage', width=1.2)]                                                                      # a passage is a door as far as the approach goes: Z reaches 0.9, the corridor 0.6
ok(approaches(p1, chair(0.0, 0.3), chair(0.85, 0.3), chair(0.95, 0.3), desk(0.0, 1.6, 90, 1.6, 0.6)) == [['P1'], ['P1'], [], ['P1']])

# a rotated opening and rotated pieces: the same cases in the opening's own frame (30 degrees: the wall runs along 120)
th = math.radians(30)
slant = [opening('S1', x=3.0, y=2.0, nx=math.cos(th), ny=math.sin(th))]
spot = lambda a, c: (3.0 - a * math.sin(th) + c * math.cos(th), 2.0 + a * math.cos(th) + c * math.sin(th))             # a m along the wall from the opening's middle, c m across it
local = lambda a, c, w, d, rot, **kw: piece(**{**dict(kind='cabinet', family='C', x=spot(a, c)[0], y=spot(a, c)[1], w=w, d=d, rot=rot), **kw})
ALONG, ACROSS = 120.0, 30.0                                                                                          # rot of a box whose long side runs along / across that wall
ok(approaches(slant, local(0.7, 0.5, 0.45, 0.45, ALONG), local(0.78, 0.5, 0.45, 0.45, ALONG), local(0.7, -0.5, 0.45, 0.45, ACROSS), local(0.7, 0.92, 0.45, 0.45, ACROSS)) == [['S1'], [], ['S1'], []])
ok(approaches(slant, local(0.0, 1.6, 1.6, 0.6, ACROSS), local(0.0, 1.8, 1.6, 0.6, ACROSS), local(2.0, 0.5, 3.4, 0.5, ALONG), local(2.1, 0.5, 3.0, 0.5, ALONG)) == [['S1'], [], ['S1'], []])
ok(approaches(slant, local(1.9452, 0.5, 3.0, 0.5, ALONG), local(1.945, 0.5, 3.0, 0.5, ALONG), local(1.9448, 0.5, 3.0, 0.5, ALONG)) == [[], ['S1'], ['S1']])   # 24 / 25 / 26 cm2 on the turned box
ok(approaches([door], piece(kind='partition', x=1.0, y=1.0, w=1.6, d=0.1, rot=135.0)) == [[]])                      # a thin box on the diagonal: its bounding box reaches the corridor, the box itself is 0.46 m away
diamond = lambda t: piece(kind='cabinet', x=0.45 + 0.5 * math.sqrt(2) - t, y=0.0, w=1.0, d=1.0, rot=45.0)            # a 1 m square on its corner, its left tip t m into the corridor: a triangle of t x t
ok(approaches([door], diamond(0.049), diamond(0.05), diamond(0.051), diamond(0.0), diamond(-0.05)) == [[], ['D1'], ['D1'], [], []])   # 24 cm2: no; 25 and 26: yes
ok(approaches([opening('R', x=-5.0, y=7.0, nx=-1.0, ny=0.0, width=1.0)], chair(-5.8, 7.7), chair(-5.8, 7.85), chair(-5.95, 7.0), chair(-4.05, 7.0)) == [['R'], [], ['R'], ['R']])    # a wall along y: Z reaches 0.8 along it (y) and 0.9 across it (x); the last two are caught by the corridor

# the exact edges stand whatever the float noise: 1.34 - 0.7 comes out a hair over 0.64 in floats, and so does 1.6 - 0.7 over 0.9
ok(approaches([opening(x=0.7, width=0.68)], chair(1.34, 0.5)) == [['D1']] and approaches([opening(y=0.7, width=0.68)], chair(0.60, 1.6)) == [['D1']])
ok(approaches([opening(x=0.7, width=0.68)], chair(1.341, 0.5)) == [[]] and approaches([opening(y=0.7, width=0.68)], chair(0.60, 1.601)) == [[]])      # 1 mm further out: not in

# several openings: the ids sorted, whatever the order they come in, and only the doors and passages among them
two = [opening('D9', x=0.5), opening('W3', kind='window', x=0.0), opening('D2', x=-0.5)]                              # Z of D9 runs from -0.25 to 1.25, Z of D2 from -1.25 to 0.25
ok(approaches(two, chair(0.0, 0.3), chair(1.1, 0.3), chair(-1.1, 0.3), chair(3.0, 0.3)) == [['D2', 'D9'], ['D9'], ['D2'], []])
ok(approaches([], chair(0.0, 0.3)) == [[]] and approaches([opening(kind='window')], chair(0.0, 0.3)) == [[]])         # no openings at all, or none that count

# the note: after any other note, joined by '; '; none when there is no approach; marking again gives the same
ps = [chair(0.0, 0.3, note='fronts merged: 3 x DOOR'), chair(0.0, 0.3), chair(0.0, 5.0, note='inside block X'), chair(0.0, 0.3, note='inside block X; run of 2 fronts: 2 x A'), chair(0.0, 5.0)]
fk.mark_approaches(ps, two)
ok([p['note'] for p in ps] == ['fronts merged: 3 x DOOR; in the approach of D2, D9', 'in the approach of D2, D9', 'inside block X',
                                'inside block X; run of 2 fronts: 2 x A; in the approach of D2, D9', ''], [p['note'] for p in ps])
ok([p['approach'] for p in ps] == [['D2', 'D9'], ['D2', 'D9'], [], ['D2', 'D9'], []])
once = [dict(p) for p in ps]
fk.mark_approaches(ps, two)
ok(ps == once)                                                                                                       # a second marking changes nothing
fk.mark_approaches(ps, [opening('D2', x=-0.5)])
ok([p['note'] for p in ps][:2] == ['fronts merged: 3 x DOOR; in the approach of D2', 'in the approach of D2'] and ps[2]['note'] == 'inside block X')
fk.mark_approaches(ps, [])
ok([p['note'] for p in ps] == ['fronts merged: 3 x DOOR', '', 'inside block X', 'inside block X; run of 2 fronts: 2 x A', ''] and all(p['approach'] == [] for p in ps))   # the sentence goes with the approach
ps = [chair(0.0, 0.3), chair(0.0, 5.0)]
before = [dict(p) for p in ps]; ops = [dict(o) for o in two]
fk.mark_approaches(ps, two)
ok(two == ops and all({k: v for k, v in a.items() if k not in ('approach', 'note')} == {k: v for k, v in b.items() if k not in ('approach', 'note')} for a, b in zip(ps, before)))   # nothing else is touched
ok(ps[0]['approach'] is not ps[1]['approach'])

# the opening's normal: only its direction counts
ok(approaches([opening(width=0.68, ny=2.5)], chair(0.60, 0.89), chair(0.60, 0.91)) == [['D1'], []] and approaches([opening(width=0.68, ny=-1.0)], chair(0.60, 0.89), chair(0.60, 0.91)) == [['D1'], []])
grid = [chair(x / 10, y / 10, w=0.2, d=0.1, rot=r) for x in range(-20, 21, 3) for y in range(-20, 21, 3) for r in (0.0, 33.0)]
res = approaches([opening(nx=3.0, ny=4.0, width=1.1)], *grid)                                                        # 3, 4 and its direction in unit length, and turned the other way round
ok(res == approaches([opening(nx=0.6, ny=0.8, width=1.1)], *grid) == approaches([opening(nx=-0.6, ny=-0.8, width=1.1)], *grid) and 20 < sum(1 for r in res if r) < len(res) - 20)
try:
    approaches([opening(nx=0.0, ny=0.0)], chair(0.0, 0.3)); ok(False)
except ValueError as e:
    ok('D1' in str(e))

# through finish(): every box has its list, in the README's place; supports and approaches are worked out apart (a computer on a table across a door is marked by its own box)
tbl = piece(kind='table', family='T', x=0.0, y=1.0, w=1.6, d=0.8)                                                    # x -0.8 .. 0.8, y 0.6 .. 1.4: across the corridor
pc = lambda x: piece(kind='computer', family='PC', x=x, y=1.0, w=0.4, d=0.4)
fur, kinds = fk.finish([tbl, pc(0.7), pc(0.3), pc(-0.1), chair(0.0, 5.0)], ['L1'], openings=[door])
ok({p['id']: p['approach'] for p in fur} == {'L1-computer-001': ['D1'], 'L1-computer-002': ['D1'], 'L1-computer-003': [], 'L1-seat-001': [], 'L1-table-001': ['D1']}, [(p['id'], p['approach']) for p in fur])
ok([p['on'] for p in fur if p['kind'] == 'computer'] == ['L1-table-001'] * 3 and list(fur[0]) == ['id', 'floor', 'kind', 'family', 'block', 'layer', 'handle', 'x', 'y', 'w', 'd', 'rot', 'on', 'approach', 'n', 'note'])
ok({p['id']: p['note'] for p in fur} == {'L1-computer-001': 'in the approach of D1', 'L1-computer-002': 'in the approach of D1', 'L1-computer-003': '', 'L1-seat-001': '', 'L1-table-001': 'in the approach of D1'})
ok(fk.finish([tbl, pc(0.7), pc(0.3), pc(-0.1), chair(0.0, 5.0)], ['L1']) == fk.finish([tbl, pc(0.7), pc(0.3), pc(-0.1), chair(0.0, 5.0)], ['L1'], openings=[]))   # none, or none given: no approaches
ok(approaches([door], *[dict(p) for p in fur]) == [p['approach'] for p in fur])                                      # the model JSON's own numbers give the same answer again
for x, want in ((0.6404, ['D1']), (0.6406, []), (-0.6404, ['D1']), (-0.6406, [])):                                  # on the boxes as rounded to the millimetre: 0.6404 is 0.640, on the edge of Z; 0.6406 is 0.641
    ok(fk.finish([chair(x, 0.5)], ['L1'], openings=d68)[0][0]['approach'] == want, x)
ok(approaches(d68, chair(0.6404, 0.5)) == [[]])                                                                      # (marked unrounded, it is 0.4 mm out)
rows = list(csv.reader(io.StringIO(fk.csv_text(*fk.finish([chair(0.0, 0.3, note='a; b'), chair(0.0, 5.0)], ['L1'], openings=two), ['L1'], [0.0, 0.0]), newline='')))
ok(rows[1][17] == 'a; b; in the approach of D2, D9' and rows[2][17] == '')                                           # the CSV carries the note, quoted (it has a comma)
ok('"a; b; in the approach of D2, D9"' in fk.csv_text(*fk.finish([chair(0.0, 0.3, note='a; b')], ['L1'], openings=two), ['L1'], [0.0, 0.0]))

# ---------------------------------------------------------------------------------------------------- csv
fam = 'He said "hi", ok'
src = [piece(kind='table', family='อ่างล้างหน้า - Thai', block='Thai-1', layer='I-FURN', handle='2A4F', x=-0.0002, y=1.0, w=2.0, d=1.0, rot=37.5, note=''),
       piece(kind='computer', family=fam, block='PC-1', layer='I-FURN', x=0.5, y=1.0, w=0.74, d=0.43, rot=0.0, note='line one\r\nline two'),
       piece(kind='seat', family='mollie_chair', block='CH-1', layer='I-FURN', x=1.0, y=2.0, w=0.6, d=0.57, rot=90.0, n=3),
       piece(kind='seat', family='mollie_chair', block='CH-2', layer='I-FURN', x=1.0, y=2.0, w=0.6, d=0.57, rot=45.0, floor='L2')]
fur, kinds = fk.finish(src, ['L1', 'L2'])
off = [1.212, 0.348]
text = fk.csv_text(fur, kinds, [{'key': 'L1'}, {'key': 'L2'}], off)
ok(not text.startswith('﻿') and text.endswith('\r\n'))                                  # no byte-order mark in the text; every row ends CRLF
ok(text.count('\r\n') == len(fur) + 1 + 1 and text.count('\n') == text.count('\r') == text.count('\r\n'))   # header + rows + the note's own CR LF (in quotes); no bare CR or LF
rows = list(csv.reader(io.StringIO(text, newline='')))
ok(rows[0] == list(fk.CSV_COLUMNS) and rows[0] == ['id', 'level', 'kind', 'kind_label', 'family', 'block', 'layer', 'dxf_handle', 'x_m', 'y_m', 'width_mm',
                                                      'depth_mm', 'height_mm', 'base_mm', 'rotation_deg', 'on_top_of', 'merged', 'note'])
ok(len(rows) == len(fur) + 1 and all(len(r) == 18 for r in rows), len(rows))
ok([r[0] for r in rows[1:]] == ['L1-computer-001', 'L1-seat-001', 'L1-table-001', 'L2-seat-001'], [r[0] for r in rows[1:]])           # floor, kind (table order), id
pc, ch, tb, ch2 = rows[1:]
ok(pc[1:] == ['L1', 'computer', 'Computer / monitor', fam, 'PC-1', 'I-FURN', '', '1.712', '1.348', '740', '430', '450', '750', '0.0', 'L1-table-001', '1', 'line one\r\nline two'], pc)
ok(tb[1:] == ['L1', 'table', 'Table / desk', 'อ่างล้างหน้า - Thai', 'Thai-1', 'I-FURN', '2A4F', '1.212', '1.348', '2000', '1000', '750', '0', '37.5', '', '1', ''], tb)   # not -0.000
ok(ch[1:] == ['L1', 'seat', 'Chair / stool', 'mollie_chair', 'CH-1', 'I-FURN', '', '2.212', '2.348', '600', '570', '450', '0', '90.0', '', '3', ''], ch)
ok(ch2[1] == 'L2' and ch2[14] == '45.0')
ok('"He said ""hi"", ok"' in text and '"line one\r\nline two"' in text)                         # RFC 4180 quoting
typed = fk.csv_text(fur, kinds, ['L1', 'L2'], off, {'table': 700, 'seat': 460})                # the viewer's typed-in heights
prow = list(csv.reader(io.StringIO(typed, newline='')))
ok(prow[1][12] == '450' and prow[1][13] == '700' and prow[3][12] == '700' and prow[2][12] == '460', prow)
ok(fk.csv_text(fur, kinds, ['L1', 'L2'], off) == text == fk.csv_text(list(reversed(fur)), kinds, ['L1', 'L2'], off))   # deterministic
tmp = Path(tempfile.mkdtemp()) / 'list.csv'
fk.write_csv(tmp, text)
raw = tmp.read_bytes()
ok(raw[:3] == b'\xef\xbb\xbf' and raw[3:].decode('utf-8') == text and b'\r\r' not in raw and 'อ่างล้างหน้า'.encode('utf-8') in raw)
ok(tmp.read_text(encoding='utf-8-sig', newline='') == text)
tmp.unlink(); tmp.parent.rmdir()
ok(fk.csv_text([], [], ['L1'], off) == ','.join(fk.CSV_COLUMNS) + '\r\n')

print(f'furniture_kit: all {checks} checks passed')
