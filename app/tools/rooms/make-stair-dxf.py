"""Synthetic stair drawings for the rooms milestone (docs/rooms/WORK_BREAKDOWN.md R0 items 7 and 8; ACCEPTANCE 2.5;
DESIGN R-7). Written by the scaffold R0; R2 owns it afterwards.

    node tools/run-builder-py.mjs tools/rooms/make-stair-dxf.py <variant> <out dir>
    variants: straight | L | U | two-floor | no-direction | down-up-pair | split-level | all

It writes one DXF per floor plan, `<out>/<variant>-<floor key>.dxf`, and `<out>/<variant>.json`: what was drawn (the
floors with their files, sha1, levels and wall heights; the layers with their roles; every stair with its flights'
riser counts, going, width, the middle of its first and last riser, and what the reader and the builder are expected
to make of it). Deterministic (ezdxf 1.4.4 with its fixed meta data, PYTHONHASHSEED=0: the same bytes on every run),
DXF R2013, millimetres. The root .gitignore ignores *.dxf, so tests make the drawings at test time (into their WT_TMP).

Every plan is the same 10 x 8 m building (200 mm walls as solid fills on A-WALL-PATT with their outlines on A-WALL, a
door in the south wall, grid lines 1, 2, A, B, a room name), at the same place on every floor, so the floors line up
with no shift. The stairs stand in its west half; every storey is 3.00 m, and a full stair has 16 risers of 0.1875 m,
going 0.28 m, 1.20 m wide.

  straight       THE TRACER's drawing. Ground plan: one straight flight of 16 single riser lines going north, its two
                 strings, the word UP at its bottom. Upper plan: no stair drawn.
  L              Ground plan: 7 risers going north, a 1.2 m square landing, 9 risers going east; every riser a nosing
                 pair (two lines 15 mm apart); no word; a walking line along the middle with a dot at the bottom and an
                 arrowhead (two strokes) at the top, on S-STRS-IDEN.
  U              Ground plan: 8 risers going north, a half landing, 8 risers coming back south; the word UP at the
                 bottom; a zig-zag break line across the second flight that cuts its fourth riser in two (one half on
                 S-STRS, the other on the hidden layer S-STRS-ABOV); the four risers beyond it are hidden
                 continuations on S-STRS-ABOV, one of them missing (a skipped going: the reader inserts and counts it).
  two-floor      One straight stair drawn on both plans: risers 1 - 9 on the ground plan (the first step 0.40 m deep
                 and 0.2 m wider on each side, a break line after riser 9), risers 9 - 16 on the upper plan with the
                 word DN at the top. Riser 9 is on both plans (the shared riser).
  no-direction   `straight` without its word: nothing says which end is the bottom.
  down-up-pair   Ground plan: `straight`'s flight. Upper plan: the top 9 risers of that stair with the word DN, and
                 0.76 m beside it a flight of 9 risers with the word UP at the same (north) end: the next stair up,
                 which leads to a floor that is not in the model. The two are never one stair.
  split-level    Three floors: ground (0.00), a mezzanine at +1.50 m that covers the east half only, upper (+3.00).
                 The ground plan's flight (`straight`'s) passes the mezzanine and rises to the upper floor.
"""
from __future__ import annotations

import hashlib
import json
import math
import os
import subprocess
import sys
from pathlib import Path

import ezdxf
from ezdxf import units

VARIANTS = ('straight', 'L', 'U', 'two-floor', 'no-direction', 'down-up-pair', 'split-level')
LAYERS = {'0': 'other', 'A-WALL': 'wall', 'A-WALL-PATT': 'wall', 'A-DOOR': 'door', 'A-AREA-IDEN': 'room-name',
          'S-GRID': 'grid', 'S-GRID-IDEN': 'grid', 'S-STRS': 'stair', 'S-STRS-ABOV': 'stair-above', 'S-STRS-IDEN': 'other'}
COLOURS = {'A-WALL': 7, 'A-WALL-PATT': 8, 'A-DOOR': 2, 'A-AREA-IDEN': 7, 'S-GRID': 1, 'S-GRID-IDEN': 1, 'S-STRS': 3,
           'S-STRS-ABOV': 3, 'S-STRS-IDEN': 3}
W, D = 10000, 8000                      # the building, mm
GOING, WIDTH, STOREY, RISERS = 280, 1200, 3.0, 16
X0, Y0 = 1000, 1500                     # the west end and the first riser of the flights going north
NOSE = 15                               # mm between the two lines of a nosing pair


class Plan:
    """One floor plan: the document, with the drawing helpers."""

    def __init__(self, name: str, *, east_half: bool = False):
        doc = ezdxf.new('R2013', setup=False)
        doc.units = units.MM
        doc.header['$INSUNITS'] = 4
        doc.header['$MEASUREMENT'] = 1
        if 'HIDDEN' not in doc.linetypes:
            doc.linetypes.add('HIDDEN', pattern=[9.525, 6.35, -3.175], description='Hidden __ __ __ __')
        for layer, colour in COLOURS.items():
            doc.layers.add(layer, color=colour, linetype='HIDDEN' if layer == 'S-STRS-ABOV' else 'Continuous')
        self.doc, self.msp = doc, doc.modelspace()
        self.shell(name, east_half)

    def line(self, a, b, layer='S-STRS'):
        self.msp.add_line(a, b, dxfattribs={'layer': layer})

    def text(self, s, at, layer='S-STRS', height=200):
        self.msp.add_text(s, height=height, dxfattribs={'layer': layer}).set_placement(at)

    def wall(self, x0, y0, x1, y1):
        pts = [(x0, y0), (x1, y0), (x1, y1), (x0, y1)]
        self.msp.add_lwpolyline(pts, close=True, dxfattribs={'layer': 'A-WALL'})
        h = self.msp.add_hatch(color=8, dxfattribs={'layer': 'A-WALL-PATT'})
        h.set_solid_fill(color=8)
        h.paths.add_polyline_path(pts, is_closed=True)

    def shell(self, name, east_half):
        """The building's walls (or only its east half: the mezzanine), the door, the grid and the room name."""
        x0 = W // 2 if east_half else 0
        self.wall(x0, 0, 7000, 200)                        # south, west of the door
        self.wall(7900, 0, W, 200)                         # south, east of the door
        self.wall(x0, 200, x0 + 200, D - 200)              # west
        self.wall(W - 200, 200, W, D - 200)                # east
        self.wall(x0, D - 200, W, D)                       # north
        # the door: hinge (7000, 100), the leaf open along +y, the arc from the closed tip (7900, 100) to the open tip
        self.msp.add_arc((7000, 100), 900, 0, 90, dxfattribs={'layer': 'A-DOOR'})
        self.line((7000, 100), (7000, 1000), 'A-DOOR')
        for x, label in ((0, '1'), (W, '2')):
            self.line((x, -2000), (x, D + 2000), 'S-GRID')
            self.msp.add_circle((x, D + 2400), 400, dxfattribs={'layer': 'S-GRID-IDEN'})
            self.text(label, (x, D + 2400), 'S-GRID-IDEN', 300)
        for y, label in ((0, 'A'), (D, 'B')):
            self.line((-2000, y), (W + 2000, y), 'S-GRID')
            self.msp.add_circle((-2400, y), 400, dxfattribs={'layer': 'S-GRID-IDEN'})
            self.text(label, (-2400, y), 'S-GRID-IDEN', 300)
        self.text(name, (7000, 5000), 'A-AREA-IDEN', 250)

    def riser(self, a, b, *, layer='S-STRS', pair=False, along=(0, 1)):
        """One riser line from a to b; `pair`: a nosing pair, two lines 15 mm apart about it, along the walking way."""
        if not pair:
            self.line(a, b, layer)
            return
        for s in (-NOSE / 2, NOSE / 2):
            self.line((a[0] + along[0] * s, a[1] + along[1] * s), (b[0] + along[0] * s, b[1] + along[1] * s), layer)

    def flight_north(self, x0, y0, n, *, width=WIDTH, layer='S-STRS', pair=False, strings=True, skip=()):
        """n risers going north (up the sheet) from y0, `going` apart, x0 .. x0 + width; -> their middles (mm)."""
        mids = []
        for k in range(n):
            y = y0 + GOING * k
            mids.append((x0 + width / 2, y))
            if k not in skip:
                self.riser((x0, y), (x0 + width, y), layer=layer, pair=pair)
        if strings:
            for x in (x0, x0 + width):
                self.line((x, y0), (x, y0 + GOING * (n - 1)), layer)
        return mids


def sha1_file(p: Path) -> str:
    return hashlib.sha1(p.read_bytes()).hexdigest()


def m(p):
    return [round(p[0] / 1000, 4), round(p[1] / 1000, 4)]


def flight_row(mids, *, sense, going=GOING, width=WIDTH, risers=None):
    return {'risers': risers if risers is not None else len(mids), 'going': going / 1000, 'width': width / 1000,
            'first': m(mids[0]), 'last': m(mids[-1]), 'sense': sense}


def climb(frm, to, *, kind, direction, landings=0, risers=RISERS, storey=STOREY):
    return {'state': 'climb', 'from': frm, 'to': to, 'kind': kind, 'risers': risers, 'riser': round(storey / risers, 4),
            'treads': risers - 1 - landings, 'landings': landings, 'direction': direction}


def lines(why):
    return {'state': 'lines', 'why': why}


def floor(key, name, level, plan, wall_height=3.0):
    return {'key': key, 'name': name, 'level': level, 'wallHeight': wall_height, 'plan': plan}


def make(variant: str) -> dict:
    """-> { floors: [{ key, name, level, wallHeight, plan: Plan }], stairs: [...] } of one variant."""
    ground, upper = Plan('HALL'), Plan('LANDING')
    floors = [floor('ground', 'Ground floor', 0.0, ground), floor('upper', 'Upper floor', 3.0, upper)]
    stairs = []
    if variant in ('straight', 'no-direction', 'down-up-pair', 'split-level'):
        mids = ground.flight_north(X0, Y0, RISERS)
        word = variant != 'no-direction'
        if word:
            ground.text('UP', (X0 + WIDTH / 2, Y0 - 250))
        stairs.append({'floor': 'ground', 'flights': [flight_row(mids, sense='leaves' if word else '')],
                       'expect': climb('ground', 'upper', kind='straight', direction='word') if word
                       else lines('no direction')})
        if variant == 'down-up-pair':
            top = Y0 + GOING * (RISERS - 1)
            a = upper.flight_north(X0, top - GOING * 8, 9)                     # the top 9 risers of the stair from below
            upper.text('DN', (X0 + WIDTH / 2, top + 250))
            xb = X0 + WIDTH + 760
            b = upper.flight_north(xb, top - GOING * 8, 9)                     # the next stair up, 0.76 m beside it
            upper.text('UP', (xb + WIDTH / 2, top + 250))
            stairs.append({'floor': 'upper', 'flights': [flight_row(a, sense='arrives')],
                           'expect': {'state': 'part', 'of': 'the stair from ground (its top 9 risers)'}})
            stairs.append({'floor': 'upper', 'flights': [flight_row(b[::-1], sense='leaves')],
                           'expect': lines('it leaves the top floor')})
        if variant == 'split-level':
            mezz = Plan('MEZZANINE', east_half=True)
            floors.insert(1, floor('mezz', 'Mezzanine', 1.5, mezz, 1.5))
    elif variant == 'L':
        a = ground.flight_north(X0, Y0, 7, pair=True)
        y1 = Y0 + GOING * 6                                                    # the landing: X0 .. X0 + WIDTH, y1 .. y1 + WIDTH
        b = []
        for k in range(9):                                                     # 9 risers going east from the landing
            x = X0 + WIDTH + GOING * k
            b.append((x, y1 + WIDTH / 2))
            ground.riser((x, y1), (x, y1 + WIDTH), pair=True, along=(1, 0))
        xe = X0 + WIDTH + GOING * 8
        ground.line((X0, y1), (X0, y1 + WIDTH))                                # the landing's west and north edges
        ground.line((X0, y1 + WIDTH), (xe, y1 + WIDTH))
        ground.line((X0 + WIDTH, y1), (xe, y1))                                # the second flight's south string
        mid = (X0 + WIDTH / 2, y1 + WIDTH / 2)
        tip = (xe + 300, y1 + WIDTH / 2)
        ground.msp.add_lwpolyline([(X0 + WIDTH / 2, Y0 - 300), mid, tip], dxfattribs={'layer': 'S-STRS-IDEN'})
        ground.msp.add_circle((X0 + WIDTH / 2, Y0 - 300), 50, dxfattribs={'layer': 'S-STRS-IDEN'})     # the dot
        for s in (1, -1):                                                      # the arrowhead: two strokes of 0.2 m
            ground.line(tip, (tip[0] - 200 * math.cos(math.radians(25)), tip[1] + s * 200 * math.sin(math.radians(25))),
                        'S-STRS-IDEN')
        stairs.append({'floor': 'ground', 'flights': [flight_row(a, sense=''), flight_row(b, sense='')],
                       'landing': [m((X0, y1)), m((X0 + WIDTH, y1 + WIDTH))],
                       'expect': climb('ground', 'upper', kind='L', direction='arrow', landings=1)})
    elif variant == 'U':
        a = ground.flight_north(X0, Y0, 8)
        ground.text('UP', (X0 + WIDTH / 2, Y0 - 250))
        y1 = Y0 + GOING * 7                                                    # the half landing: y1 .. y1 + WIDTH
        xb = X0 + WIDTH + 100                                                  # the second flight, a 0.1 m well between
        ground.line((X0, y1), (X0, y1 + WIDTH))
        ground.line((X0, y1 + WIDTH), (xb + WIDTH, y1 + WIDTH))
        ground.line((xb + WIDTH, y1 + WIDTH), (xb + WIDTH, y1))
        b = [(xb + WIDTH / 2, y1 - GOING * k) for k in range(8)]              # coming back south, from the landing down the sheet
        for k in range(3):
            ground.riser((xb, y1 - GOING * k), (xb + WIDTH, y1 - GOING * k))
        yk = y1 - GOING * 3                                                    # the riser the break line cuts in two
        ground.line((xb, yk), (xb + 600, yk))
        ground.line((xb + 600, yk), (xb + WIDTH, yk), 'S-STRS-ABOV')
        zig = [(xb - 100, yk - 140), (xb + 500, yk - 40), (xb + 560, yk + 120), (xb + 640, yk - 120), (xb + 700, yk + 40),
               (xb + WIDTH + 100, yk + 140)]
        ground.msp.add_lwpolyline(zig, dxfattribs={'layer': 'S-STRS'})         # the break line
        for k in (4, 5, 7):                                                    # hidden continuations; riser k = 6 is missing
            ground.riser((xb, y1 - GOING * k), (xb + WIDTH, y1 - GOING * k), layer='S-STRS-ABOV')
        for x in (xb, xb + WIDTH):
            ground.line((x, y1), (x, yk))
            ground.line((x, yk), (x, y1 - GOING * 7), 'S-STRS-ABOV')
        stairs.append({'floor': 'ground', 'flights': [flight_row(a, sense='leaves'), flight_row(b, sense='leaves')],
                       'landing': [m((X0, y1)), m((xb + WIDTH, y1 + WIDTH))], 'missingRiser': m(b[6]),
                       'cutRiser': m(b[3]), 'expect': climb('ground', 'upper', kind='U', direction='word', landings=1)})
    elif variant == 'two-floor':
        ys = [Y0, Y0 + 400] + [Y0 + 400 + GOING * k for k in range(1, 15)]     # 16 risers; the first step 0.40 m deep
        mids = [(X0 + WIDTH / 2, y) for y in ys]
        ground.riser((X0 - 200, ys[0]), (X0 + WIDTH + 200, ys[0]))             # the flared bottom step
        for y in ys[1:9]:
            ground.riser((X0, y), (X0 + WIDTH, y))
        for x in (X0, X0 + WIDTH):
            ground.line((x, ys[1]), (x, ys[8]))
        yb = ys[8] + 120                                                       # the break line, after riser 9
        ground.msp.add_lwpolyline([(X0 - 100, yb - 60), (X0 + 500, yb), (X0 + 560, yb + 120), (X0 + 640, yb - 120),
                                   (X0 + 700, yb), (X0 + WIDTH + 100, yb + 60)], dxfattribs={'layer': 'S-STRS'})
        for y in ys[8:]:
            upper.riser((X0, y), (X0 + WIDTH, y))
        for x in (X0, X0 + WIDTH):
            upper.line((x, ys[8]), (x, ys[15]))
        upper.text('DN', (X0 + WIDTH / 2, ys[15] + 250))
        stairs.append({'floor': 'ground', 'flights': [flight_row(mids[:9], sense='')], 'firstStep': 0.4,
                       'expect': climb('ground', 'upper', kind='straight', direction='floors')})
        stairs.append({'floor': 'upper', 'flights': [flight_row(mids[8:], sense='arrives')], 'sharedRiser': m(mids[8]),
                       'expect': {'state': 'part', 'of': 'the stair from ground (risers 9 - 16)'}})
    else:
        raise ValueError(variant)
    return {'floors': floors, 'stairs': stairs}


def write(variant: str, out: Path) -> dict:
    ezdxf.options.write_fixed_meta_data_for_testing = True
    out.mkdir(parents=True, exist_ok=True)
    made = make(variant)
    floors = []
    for f in made['floors']:
        p = out / f'{variant}-{f["key"]}.dxf'
        f['plan'].doc.saveas(p)
        floors.append({'key': f['key'], 'name': f['name'], 'level': f['level'], 'wallHeight': f['wallHeight'],
                       'file': p.name, 'sha1': sha1_file(p)})
    doc = {'format': 'stair-dxf/1', 'variant': variant, 'units': 'mm', 'storey': STOREY, 'floors': floors,
           'layers': dict(LAYERS), 'stairs': made['stairs']}
    (out / f'{variant}.json').write_text(json.dumps(doc, indent=2) + '\n', encoding='utf-8')
    return doc


def main(argv: list[str]) -> int:
    if len(argv) != 2 or argv[0] not in VARIANTS + ('all',):
        print(f'usage: make-stair-dxf.py {"|".join(VARIANTS)}|all <out dir>', file=sys.stderr)
        return 2
    if os.environ.get('PYTHONHASHSEED') != '0':
        env = dict(os.environ, PYTHONHASHSEED='0')
        return subprocess.run([sys.executable, '-B', str(Path(__file__).resolve()), *argv], env=env).returncode
    for v in VARIANTS if argv[0] == 'all' else (argv[0],):
        doc = write(v, Path(argv[1]))
        print(f'make-stair-dxf: {v} -> {", ".join(f["file"] for f in doc["floors"])}, {v}.json')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
