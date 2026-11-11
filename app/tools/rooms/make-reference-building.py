"""The reference building of the rooms milestone and everything derived from it (docs/rooms/ACCEPTANCE.md 2.5;
WORK_BREAKDOWN R0 item 8). Written by the scaffold R0. FROZEN with its outputs: they are the contract R1 - R7 build
against (a defect goes in your own docs/rooms/contract-issues file).

    node tools/run-builder-py.mjs tools/rooms/make-reference-building.py dxf <out dir>
    node tools/run-builder-py.mjs tools/rooms/make-reference-building.py fixtures [--tmp <dir>] [--check]
    node tools/run-builder-py.mjs tools/rooms/make-reference-building.py stairs [--tmp <dir>] [--check]

`dxf`       rooms-reference-ground.dxf, rooms-reference-upper.dxf and rooms-reference.json (what was drawn and what is
            expected of it: the same manifest as make-stair-dxf.py's, plus `truth`). Deterministic; made at test time
            (the root .gitignore ignores *.dxf): services/builder/tests/rooms_kit.py reference_plan().
`fixtures`  fixtures/models/rooms-reference.model.json (BuiltModel v2), fixtures/presentation/rooms-reference.json,
            fixtures/stages/rooms-reference.stages.json, fixtures/rooms/settings.reference.json (its BuildSettings),
            fixtures/rooms/build-result.reference.json (a BuildResult with every new report key),
            fixtures/rooms/overlay.reference.json (the overlay with the new floor fields and seven of the eight new
            flag kinds), fixtures/rooms/flags.every-kind.json (one flag of each new kind: those seven and a hand-written
            `stairs-none`, which a building whose stair climbs cannot raise) and fixtures/rooms/runs/reference-build/
            (a FakeJobRunner run folder: run.json, job.json, out/).
`stairs`    fixtures/models/stairs-{straight,L,U}.model.json: the v2 models of make-stair-dxf.py's three drawings, for
            the walker's tests.
`--check`   writes nothing and exits 1 when a file on disk differs. (It held at R0's state of the builder: the
            fixtures passed through the tracer's wiring in build/bank.py and build/model.py, which R1 rewrote. The
            integration step RI re-made `fixtures` and `stairs` with this tool on 11 Nov, after R1 - R7, so that what the
            real code now writes from the same definition (the rooms' areas, the stair outlines and the summary's stairs
            block, R3's outputs) is in them: docs/rooms/contract-issues/RI.md lists every file that moved and why. Since
            then `--check` holds again; the overlay is out/overlay.py's own, which writes the new fields and flags.)

THE BUILDING (sheet metres; drawn in millimetres). Two floors of 3.00 m, 12 x 9 m, 0.2 m walls drawn as solid fills.
  ground   HALL (x 0.2 - 6.9): two names in it, LIVING and DINING; the entrance door in the south wall.
           KITCHEN (x 7.1 - 11.8, y 0.2 - 4.4): a door from the hall; an X-marked box of 4.4 m2 (a void mark on the
           lowest floor: not cut, flagged).
           GARAGE (x 7.03 - 11.8, y 4.6 - 8.8): a 2.9 m opening with no door in its outside (north) wall, from the
           wall's end to the side of the east wall, so it is no room: an unfloored area with a mouth, and its name
           stands in no room. Between the hall and the garage a 0.06 m partition with a door-sized gap of 1.2 m
           between two wall ends and no door: a doorway closing keeps the hall closed. (The door finder is frozen and
           finds a gap between two ends of one wall line as a passage, up to 3.6 m, in walls of 7 cm or more: so the
           wide opening ends on a wall's side, and the doorway stands in a wall thinner than 7 cm. It finds the three
           doors and nothing else.)
           Stair S1 (L): 7 risers going north, a 1.2 m landing, 9 risers going east, every riser a nosing pair; the
           ground plan shows risers 1 - 12 with the word UP and a break line, the upper plan risers 12 - 16 with DN
           (riser 12 is on both plans). A 0.1 m cupboard wall stands under its tread 13: cut to the stair's underside.
           Stair S2: 16 risers going east along the north wall, drawn with no word, arrow or break line.
  upper    LOUNGE over the hall (x 0 - 7.1), a door onto a TERRACE (x 7.1 - 11.9, y 0.1 - 4.5) fenced by railings, an
           X-marked void of 5.2 m2 over the hall, and the well of S1.

HOW THE FIXTURES ARE MADE. The reference building needs the real rules, which the tracer does not have. So the plans
are read by the app's reader and built by build() with the new options, the openings and walls by the unchanged code
(bank.floor_walls, the real door finder), while the five calls of the rules (network_of, plate_of, find_stairs,
build_stairs, x_marks) are answered here from the building's own definition (`truth`): the rooms, the ring, the
terrace, the unfloored garage, the doorway closing, the X boxes, and the stairs computed by `stair_built` exactly as
DESIGN R-8.1, R-8.2 and R-8.5 say:
  * tread j lies between riser j and riser j + 1 of one flight, z1 = j x r, z0 = max(0, (j - 2) x r); the last tread
    runs 0.05 m past riser n; a landing after riser k has z1 = k x r and z0 = max(0, z1 - 0.15);
  * the well of the upper floor is the footprint of the treads and landings whose top is higher than
    rise - slab thickness - 2.10 m, grown 0.05 m on every side but the arrival, where its edge is riser n;
  * the stairway's `walk` runs from 1.0 m before riser 1 through the middle of the first and the last riser of each
    flight and the middle of each landing to 1.0 m past riser n; `width` is the median riser length of the narrowest
    flight, `going` the median going; `treads` and `landings` count the stairway's tread and landing parts (contract
    issue R0-1: R-8.5's example counts 20 treads for 21 risers and a landing);
  * a part of the lower floor is cut where its footprint overlaps a tread or landing whose underside is lower than its
    top by at least 2 cm in depth and 0.01 m2: that piece gets the lowest underside over it (R-8.3).
The overlay's new floor fields and the new flags are written here from the result, in the shapes of R-12.4 and with
the texts of R-6.1 (R3 writes the real overlay code against this fixture). Every date is fixed (11 Nov 2026 00:00 UTC)
and every timing is zero, so the same inputs give the same bytes.
"""
from __future__ import annotations

import argparse
import copy
import datetime as dt
import hashlib
import importlib.util
import json
import math
import os
import statistics
import subprocess
import sys
import tempfile
from pathlib import Path

APP = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(APP / 'services' / 'builder'))
sys.dont_write_bytecode = True

import ezdxf  # noqa: E402
from ezdxf import units as dxf_units  # noqa: E402
from shapely.geometry import LineString, Point, Polygon, box  # noqa: E402
from shapely.ops import unary_union  # noqa: E402

FX = APP / 'fixtures'
NAME = 'rooms-reference'
BUILT_AT = dt.datetime(2026, 11, 11, 0, 0, 0, tzinfo=dt.timezone.utc)
AT = '2026-11-11T00:00:00Z'
G, U = 'ground', 'upper'
STOREY, GOING, WIDTH = 3.0, 0.28, 1.2
HEADROOM, LAP, GROW, RUN, LANDING_DEPTH = 2.10, 0.05, 0.05, 1.0, 0.15
CUT_KINDS = ('wall', 'column', 'glass', 'mullion', 'single', 'railing', 'parapet', 'lintel', 'sill')
LAYERS = {'0': 'other', 'A-WALL': 'wall', 'A-WALL-PATT': 'wall', 'A-DOOR': 'door', 'A-AREA-IDEN': 'room-name',
          'A-FLOR-HRAL': 'railing', 'A-FLOR-OTLN': 'other', 'S-GRID': 'grid', 'S-GRID-IDEN': 'grid', 'S-STRS': 'stair'}
COLOURS = {'A-WALL': 7, 'A-WALL-PATT': 8, 'A-DOOR': 2, 'A-AREA-IDEN': 7, 'A-FLOR-HRAL': 6, 'A-FLOR-OTLN': 4, 'S-GRID': 1,
           'S-GRID-IDEN': 1, 'S-STRS': 3}
PROJECT = {'name': 'Reference building', 'shortName': 'Reference', 'projectNo': None, 'photoName': 'Rooms-reference',
           'maxPrefix': 'RF', 'maxFileName': 'Rooms_reference.ms', 'exportedFrom': None}
PROJECT_ID = 'rooms-reference'

# ------------------------------------------------------------------------------------------- the building (metres)
WALLS = {
    G: [(0, 0, 4.5, 0.2), (5.4, 0, 12, 0.2), (0, 0.2, 0.2, 8.8), (0, 8.8, 8.9, 9.0), (11.8, 0.2, 12, 9.0),
        (6.9, 0.2, 7.1, 1.2), (6.9, 2.1, 7.1, 4.6), (6.97, 4.6, 7.03, 5.6), (6.97, 6.8, 7.03, 8.8), (7.1, 4.4, 11.8, 4.6),
        (3.3, 3.18, 3.4, 4.68)],
    U: [(0, 0, 7.1, 0.2), (0, 0.2, 0.2, 8.8), (0, 8.8, 7.1, 9.0), (6.9, 0.2, 7.1, 1.2), (6.9, 2.1, 7.1, 8.8)],
}
#: doors: (hinge, the leaf's open tip, the arc's start and end angle about the hinge)
DOORS = {G: [((4.5, 0.1), (4.5, 1.0), 0, 90), ((7.0, 1.2), (7.9, 1.2), 0, 90)], U: [((7.0, 1.2), (7.9, 1.2), 0, 90)]}
NAMES = {G: [('LIVING', (3.0, 5.8)), ('DINING', (5.2, 2.6)), ('KITCHEN', (8.6, 3.4)), ('GARAGE', (9.0, 6.6))],
         U: [('LOUNGE', (3.0, 6.0))]}
XBOX = {G: (9.4, 0.5, 11.6, 2.5), U: (3.4, 0.8, 6.0, 2.8)}
RAILS = [((7.1, 0.1), (11.9, 0.1)), ((11.9, 0.1), (11.9, 4.5)), ((11.9, 4.5), (7.1, 4.5))]      # the terrace, upper floor
HALL = [(0.2, 0.2), (6.9, 0.2), (6.9, 4.6), (6.97, 4.6), (6.97, 8.8), (0.2, 8.8)]         # the ground floor's hall
LOUNGE, KITCHEN, GARAGE = (0.2, 0.2, 6.9, 8.8), (7.1, 0.2, 11.8, 4.4), (7.03, 4.6, 11.8, 8.8)
TERRACE = (7.1, 0.1, 11.9, 4.5)
GAP = ((8.9, 8.9), (11.8, 8.9))                 # the garage's 2.9 m opening: its mouth (the wall's middle line)
DOORWAY = ((7.0, 5.6), (7.0, 6.8))              # the door-sized gap between two wall ends
S1_A = [((0.6, 1.8 + GOING * k), (1.8, 1.8 + GOING * k)) for k in range(7)]             # risers 1 - 7, going north
S1_LANDING = (0.6, 3.48, 1.8, 4.68)
S1_B = [((1.8 + GOING * k, 3.48), (1.8 + GOING * k, 4.68)) for k in range(9)]           # risers 8 - 16, going east
S2 = [((1.0 + GOING * k, 7.4), (1.0 + GOING * k, 8.6)) for k in range(16)]              # no word, arrow or break line


def R3(v: float) -> float:
    return round(v, 3) + 0.0


def mid(seg):
    (x0, y0), (x1, y1) = seg
    return ((x0 + x1) / 2, (y0 + y1) / 2)


def unit(v):
    n = math.hypot(*v) or 1.0
    return (v[0] / n, v[1] / n)


def sha1_file(p: Path) -> str:
    return hashlib.sha1(p.read_bytes()).hexdigest()


# ------------------------------------------------------------------------------------------------------- the drawings
def mm(p):
    return (round(p[0] * 1000), round(p[1] * 1000))


def plan_doc(key: str):
    doc = ezdxf.new('R2013', setup=False)
    doc.units = dxf_units.MM
    doc.header['$INSUNITS'] = 4
    doc.header['$MEASUREMENT'] = 1
    for layer, colour in COLOURS.items():
        doc.layers.add(layer, color=colour)
    msp = doc.modelspace()

    def line(a, b, layer='S-STRS'):
        msp.add_line(mm(a), mm(b), dxfattribs={'layer': layer})

    def text(s, at, layer, height):
        msp.add_text(s, height=height, dxfattribs={'layer': layer}).set_placement(mm(at))

    def riser(seg, along, pair=True):
        (a, b) = seg
        for s in ((-0.0075, 0.0075) if pair else (0.0,)):
            line((a[0] + along[0] * s, a[1] + along[1] * s), (b[0] + along[0] * s, b[1] + along[1] * s))

    for x0, y0, x1, y1 in WALLS[key]:
        pts = [mm((x0, y0)), mm((x1, y0)), mm((x1, y1)), mm((x0, y1))]
        msp.add_lwpolyline(pts, close=True, dxfattribs={'layer': 'A-WALL'})
        h = msp.add_hatch(color=8, dxfattribs={'layer': 'A-WALL-PATT'})
        h.set_solid_fill(color=8)
        h.paths.add_polyline_path(pts, is_closed=True)
    for hinge, tip, a0, a1 in DOORS[key]:
        msp.add_arc(mm(hinge), 900, a0, a1, dxfattribs={'layer': 'A-DOOR'})
        line(hinge, tip, 'A-DOOR')
    for x, label in ((0.0, '1'), (12.0, '2')):
        line((x, -2.0), (x, 11.0), 'S-GRID')
        msp.add_circle(mm((x, 11.4)), 400, dxfattribs={'layer': 'S-GRID-IDEN'})
        text(label, (x, 11.4), 'S-GRID-IDEN', 300)
    for y, label in ((0.0, 'A'), (9.0, 'B')):
        line((-2.0, y), (14.0, y), 'S-GRID')
        msp.add_circle(mm((-2.4, y)), 400, dxfattribs={'layer': 'S-GRID-IDEN'})
        text(label, (-2.4, y), 'S-GRID-IDEN', 300)
    for name, at in NAMES[key]:
        text(name, at, 'A-AREA-IDEN', 250)
    x0, y0, x1, y1 = XBOX[key]                                         # the X mark: a box and its two diagonals
    msp.add_lwpolyline([mm((x0, y0)), mm((x1, y0)), mm((x1, y1)), mm((x0, y1))], close=True, dxfattribs={'layer': 'A-FLOR-OTLN'})
    line((x0, y0), (x1, y1), 'A-FLOR-OTLN')
    line((x0, y1), (x1, y0), 'A-FLOR-OTLN')
    if key == G:
        for seg in S1_A:
            riser(seg, (0, 1))
        for seg in S1_B[:5]:                                           # risers 8 - 12: below the cut
            riser(seg, (1, 0))
        for a, b in (((0.6, 1.8), (0.6, 3.48)), ((1.8, 1.8), (1.8, 3.48)), ((0.6, 3.48), (0.6, 4.68)),
                     ((0.6, 4.68), (3.04, 4.68)), ((1.8, 3.48), (3.04, 3.48))):
            line(a, b)
        msp.add_lwpolyline([mm(p) for p in ((2.98, 3.38), (3.04, 3.98), (3.16, 4.04), (2.92, 4.12), (3.04, 4.18), (3.10, 4.78))],
                           dxfattribs={'layer': 'S-STRS'})             # the break line
        text('UP', (1.2, 1.55), 'S-STRS', 200)
        for seg in S2:
            riser(seg, (1, 0), pair=False)
        line((1.0, 7.4), (5.2, 7.4))
        line((1.0, 8.6), (5.2, 8.6))
    else:
        for seg in S1_B[4:]:                                           # risers 12 - 16; riser 12 is on both plans
            riser(seg, (1, 0))
        line((2.92, 3.48), (4.04, 3.48))
        line((2.92, 4.68), (4.04, 4.68))
        text('DN', (4.29, 4.08), 'S-STRS', 200)
        for a, b in RAILS:                                             # the terrace's railing: two lines 50 mm apart
            d = unit((b[0] - a[0], b[1] - a[1]))
            n = (-d[1], d[0])
            for s in (-0.025, 0.025):
                line((a[0] + n[0] * s, a[1] + n[1] * s), (b[0] + n[0] * s, b[1] + n[1] * s), 'A-FLOR-HRAL')
    return doc


def flight_row(risers, sense):
    lengths = [math.dist(a, b) for a, b in risers]
    gaps = [math.dist(mid(a), mid(b)) for a, b in zip(risers, risers[1:])]
    return {'risers': len(risers), 'going': round(statistics.median(gaps), 4), 'width': round(statistics.median(lengths), 4),
            'first': [round(v, 4) for v in mid(risers[0])], 'last': [round(v, 4) for v in mid(risers[-1])], 'sense': sense}


def rect(b):
    return [[b[0], b[1]], [b[2], b[3]]]


def write_dxf(out: Path) -> dict:
    """The two plans and the manifest into `out` -> the manifest."""
    ezdxf.options.write_fixed_meta_data_for_testing = True
    out.mkdir(parents=True, exist_ok=True)
    floors = []
    for key, name, level in ((G, 'Ground floor', 0.0), (U, 'Upper floor', STOREY)):
        p = out / f'{NAME}-{key}.dxf'
        plan_doc(key).saveas(p)
        floors.append({'key': key, 'name': name, 'level': level, 'wallHeight': 3.0, 'file': p.name, 'sha1': sha1_file(p)})
    r = STOREY / 16
    doc = {
        'format': 'stair-dxf/1', 'variant': NAME, 'name': PROJECT['name'], 'units': 'mm', 'storey': STOREY, 'floors': floors,
        'layers': dict(LAYERS),
        'stairs': [
            {'floor': G, 'flights': [flight_row(S1_A, 'leaves'), flight_row(S1_B, 'leaves')], 'landing': rect(S1_LANDING),
             'drawn': {G: 'risers 1 - 12, the word UP, a break line', U: 'risers 12 - 16, the word DN'}, 'sharedRiser': 12,
             'expect': {'state': 'climb', 'id': 'S1', 'from': G, 'to': U, 'kind': 'L', 'risers': 16, 'riser': round(r, 4),
                        'treads': 14, 'landings': 1, 'direction': 'word'}},
            {'floor': G, 'flights': [flight_row(S2, '')], 'expect': {'state': 'lines', 'why': 'no direction'}},
        ],
        'truth': {
            'rooms': {G: [{'names': ['LIVING', 'DINING'], 'outline': [list(p) for p in HALL]},
                          {'names': ['KITCHEN'], 'box': rect(KITCHEN)}],
                      U: [{'names': ['LOUNGE'], 'box': rect(LOUNGE)}]},
            'namesInNoRoom': {G: ['GARAGE'], U: []},
            'unfloored': {G: [{'box': rect(GARAGE), 'mouth': [list(GAP[0]), list(GAP[1])]}], U: []},
            'doorwayClosings': {G: [[list(DOORWAY[0]), list(DOORWAY[1])]], U: []},
            'terraces': {G: [], U: [rect(TERRACE)]},
            'xMarks': {G: [{'box': rect(XBOX[G]), 'what': 'void', 'cut': False}], U: [{'box': rect(XBOX[U]), 'what': 'void', 'cut': True}]},
            'cupboardWall': rect(WALLS[G][-1]),
        },
    }
    (out / f'{NAME}.json').write_text(json.dumps(doc, indent=2) + '\n', encoding='utf-8')
    return doc


# --------------------------------------------------------------------------------------------- the stairs, by the rules
def stair_built(sid, frm, to, flights, landings, *, rise, thickness, ceiling, kind, direction):
    """A climbable stair as DESIGN R-8.1, R-8.2 and R-8.5 build it -> contracts.StairBuilt without `cuts` and
    `linesUsed`, plus `_steps` [(footprint without the lap, z0, z1)] and `_outline`. flights: the riser segments of each
    flight, bottom to top; landings: [{ after: the riser it follows, poly }]; sheet metres."""
    n = sum(len(f) for f in flights)
    r = rise / n
    treads, lands, steps, walk = [], [], [], []
    j = 0

    def part(kind_, poly, z0, z1, label):
        return {'floor': frm, 'kind': kind_, 'poly': poly, 'z0': R3(z0), 'z1': R3(z1), 'follow': False, 'label': label,
                'extra': {'fit': 'storey', 'stair': sid}}
    for risers in flights:
        walk += [mid(risers[0]), mid(risers[-1])]
        for k in range(len(risers)):
            j += 1
            if k + 1 == len(risers):
                break
            (a0, a1), (b0, b1) = risers[k], risers[k + 1]
            base = Polygon([a0, a1, b1, b0])
            poly = base
            if j == n - 1:                                             # the last tread laps 0.05 m past riser n
                d = unit((mid(risers[k + 1])[0] - mid(risers[k])[0], mid(risers[k + 1])[1] - mid(risers[k])[1]))
                poly = Polygon([a0, a1, (b1[0] + d[0] * LAP, b1[1] + d[1] * LAP), (b0[0] + d[0] * LAP, b0[1] + d[1] * LAP)])
            z0, z1 = max(0.0, (j - 2) * r), j * r
            treads.append(part('tread', poly, z0, z1, f'stair {sid} tread {j}'))
            steps.append((base, z0, z1))
        for L in landings:
            if L['after'] == j:
                z1 = j * r
                z0 = max(0.0, z1 - LANDING_DEPTH)
                lands.append(part('landing', L['poly'], z0, z1, f'stair {sid} landing {j}'))
                steps.append((L['poly'], z0, z1))
                c = L['poly'].centroid
                walk.append((c.x, c.y))
    first, last = flights[0], flights[-1]
    d1 = unit((mid(first[1])[0] - mid(first[0])[0], mid(first[1])[1] - mid(first[0])[1]))
    dn = unit((mid(last[-1])[0] - mid(last[-2])[0], mid(last[-1])[1] - mid(last[-2])[1]))
    bottom = (mid(first[0])[0] - d1[0] * RUN, mid(first[0])[1] - d1[1] * RUN)
    top = (mid(last[-1])[0] + dn[0] * RUN, mid(last[-1])[1] + dn[1] * RUN)
    walk = [bottom] + walk + [top]
    need = rise - thickness - HEADROOM
    high = [b for b, _z0, z1 in steps if z1 > need + 1e-9]
    (p0, p1) = last[-1]
    t = unit((p1[0] - p0[0], p1[1] - p0[1]))
    e = GROW + 0.01
    beyond = Polygon([(p0[0] - t[0] * e, p0[1] - t[1] * e), (p1[0] + t[0] * e, p1[1] + t[1] * e),
                      (p1[0] + t[0] * e + dn[0], p1[1] + t[1] * e + dn[1]), (p0[0] - t[0] * e + dn[0], p0[1] - t[1] * e + dn[1])])
    well = unary_union(high).buffer(GROW, join_style='mitre').difference(beyond) if high else Polygon()
    head = [b for b, _z0, z1 in steps if z1 > ceiling - HEADROOM + 1e-9]
    goings = [math.dist(mid(a), mid(b)) for f in flights for a, b in zip(f, f[1:])]
    width = min(statistics.median([math.dist(a, b) for a, b in f]) for f in flights)
    stairway = {'id': sid, 'from': frm, 'to': to, 'kind': kind, 'risers': n, 'riser': R3(r), 'going': R3(statistics.median(goings)),
                'width': R3(width), 'bottom': bottom, 'top': top, 'walk': walk, 'direction': direction, 'treads': len(treads),
                'landings': len(lands)}
    return {'stairway': stairway, 'treads': treads, 'landings': lands, 'wellOf': {to: well},
            'headroom': unary_union(head) if head else None, 'arrival': top, 'cuts': [], 'linesUsed': {},
            '_steps': steps, '_outline': unary_union([p['poly'] for p in treads + lands])}


def clash_cuts(fb, steps) -> list:
    """R-8.3: the parts of the lower floor in the way of the stair -> [contracts.StairCut]."""
    cuts = []
    for i, p in enumerate(fb['parts']):
        if p['kind'] not in CUT_KINDS:
            continue
        over = [(b, z0) for b, z0, _z1 in steps if z0 < p['z1'] - 1e-9 and b.intersection(p['poly']).area > 1e-6]
        if not over:
            continue
        foot = p['poly'].intersection(unary_union([b for b, _ in over]))
        if foot.area < 0.01 or foot.buffer(-0.01).is_empty:            # at least 0.01 m2 and 2 cm in depth
            continue
        cuts.append({'floor': fb['key'], 'part': i, 'footprint': foot, 'z1': min(z0 for _b, z0 in over)})
    return cuts


def lines_used(fb, outline) -> list:
    zone = outline.buffer(0.06)
    return [i for i, ls in enumerate(fb['old_stairs'].get('lines') or []) if zone.contains(ls.interpolate(0.5, normalized=True))]


# ----------------------------------------------------------------------------- the rules' five calls, answered by a truth
class Injected:
    """While open, the tracer's network_of, plate_of, find_stairs, build_stairs and x_marks answer from `truth`:
    { floors: { key: { spaces: [(polygon, source)], ring, terraces: [polygon], closings: [contracts.Closing],
    unfloored: [contracts.Unfloored], xmarks: [{ poly, area, what }] } }, stairs: [{ state: 'climb', id, from, to, kind,
    direction, flights, landings } | { state: 'lines', floor, why, text, severity, outline, risers }] }."""

    def __init__(self, truth: dict):
        self.T = truth

    def __enter__(self):
        from walkthrough_builder.build import network as NW, rooms as RM, stairs_build as SB, stairs_read as SR, xmarks as XM
        T = self.T
        self.saved = [(NW, 'network_of', NW.network_of), (NW, 'plate_of', NW.plate_of), (SR, 'find_stairs', SR.find_stairs),
                      (SB, 'build_stairs', SB.build_stairs), (XM, 'x_marks', XM.x_marks)]

        def network_of(fb, fixes, X):
            t = T['floors'][fb['key']]
            strips = [LineString([c['a'], c['b']]).buffer(0.01, cap_style='flat') for c in t['closings']]
            N = unary_union([g for g in fb['e_walls'] if g is not None and not g.is_empty] + [r['span'] for r in fb['recs']] + strips)
            spaces = RM.spaces_of(fb, [p for p, _src in t['spaces']], X)
            source = {id(p): src for p, src in t['spaces']}
            for s in spaces:
                s['source'] = source[id(s['poly'])]
            return {'N': N, 'closings': [dict(c) for c in t['closings']], 'faces': [s['poly'] for s in spaces], 'spaces': spaces,
                    'shapes': 0, 'ring': t['ring']}

        def plate_of(fb, net, fixes, X):
            t = T['floors'][fb['key']]
            plate0 = unary_union([t['ring']] + list(t['terraces']))
            old = fb['old_plate']
            lost = old.difference(plate0.buffer(0.05)).area
            assert lost < 0.5, (f'{fb["key"]}: {lost:.2f} m2 of today\'s plate lies outside the new one (R-4.1): '
                                f'{fb["old_report"]}; openings {[(r["o"]["id"], r["o"]["kind"], r["o"].get("width")) for r in fb["recs"]]}')
            report = {'ring': round(t['ring'].area, 1), 'terraces': round(sum(p.area for p in t['terraces']), 1),
                      'old': round(old.area, 1), 'plate': round(plate0.area, 1), 'holes': [], 'unfloored': [], 'closings': [],
                      'dropped': []}
            return plate0, [dict(u) for u in t['unfloored']], report

        def find_stairs(fb, net, fixes, X):
            out = []
            for st in T['stairs']:
                if (st['from'] if st['state'] == 'climb' else st['floor']) != fb['key']:
                    continue
                if st['state'] == 'climb':
                    flights = [{'risers': list(f), 'going': GOING, 'width': math.dist(*f[0]), 'sense': 'leaves', 'lines': []}
                               for f in st['flights']]
                    outline = unary_union([Polygon([f[0][0], f[0][1], f[-1][1], f[-1][0]]) for f in st['flights']]
                                          + [L['poly'] for L in st['landings']])
                    end = mid(st['flights'][0][0])
                else:
                    flights, outline, end = [], st['outline'], None
                out.append({'id': f'{fb["key"]}-ST{len(out) + 1}', 'floor': fb['key'], 'flights': flights,
                            'landings': [L['poly'] for L in st.get('landings', [])], 'outline': outline, 'hull': outline.convex_hull,
                            'floorEnd': end, 'lines': []})
            return out

        def build_stairs(floors, found, nets, plate0, fixes, X):
            from walkthrough_builder.build.ceilings import ceiling_height
            by_key = {fb['key']: fb for fb in floors}
            built, left = [], []
            for st in T['stairs']:
                if st['state'] == 'climb':
                    lo, hi = by_key[st['from']], by_key[st['to']]
                    f_hi = X.settings['floors'][hi['index']]
                    thick = f_hi['slabThickness'] if f_hi['slabThickness'] is not None else X.DEF['slabThickness']
                    sb = stair_built(st['id'], st['from'], st['to'], st['flights'], st['landings'], rise=hi['level'] - lo['level'],
                                     thickness=thick, ceiling=ceiling_height(lo['index'], X), kind=st['kind'],
                                     direction=st['direction'])
                    assert plate0[st['from']].buffer(0.25).contains(Point(sb['stairway']['bottom'])), 'the bottom is off the plate'
                    assert plate0[st['to']].buffer(0.25).contains(Point(sb['arrival'])), 'the arrival is off the plate'
                    sb['cuts'] = clash_cuts(lo, sb.pop('_steps'))
                    outline = sb.pop('_outline')
                    sb['linesUsed'] = {k: lines_used(by_key[k], outline) for k in (st['from'], st['to'])}
                    built.append(sb)
                else:
                    at = st['outline'].representative_point()
                    left.append({'id': f'{st["floor"]}-ST{st["n"]}', 'floor': st['floor'], 'why': st['why'],
                                 'text': st['text'].format(x=at.x, y=at.y), 'severity': st['severity'], 'at': (at.x, at.y),
                                 'outline': st['outline'], 'keptVoid': None, 'risers': st['risers']})
            return {'built': built, 'left': left, 'pairs': [], 'fixes': []}

        def x_marks(fb, net, X):
            return [dict(x) for x in T['floors'][fb['key']]['xmarks']]

        NW.network_of, NW.plate_of, SR.find_stairs, SB.build_stairs, XM.x_marks = network_of, plate_of, find_stairs, build_stairs, x_marks
        return self

    def __exit__(self, *exc):
        for mod, name, fn in self.saved:
            setattr(mod, name, fn)
        return False


def reference_truth() -> dict:
    hall, kitchen, garage, lounge = Polygon(HALL), box(*KITCHEN), box(*GARAGE), box(*LOUNGE)
    ring_g = box(0, 0, 12, 9).difference(garage).difference(box(GAP[0][0], 8.8, GAP[1][0], 9.0))
    return {
        'floors': {
            G: {'spaces': [(hall, 'network'), (kitchen, 'network')], 'ring': ring_g, 'terraces': [],
                'closings': [{'kind': 'doorway', 'a': DOORWAY[0], 'b': DOORWAY[1], 'width': 1.2}],
                'unfloored': [{'poly': garage, 'area': garage.area, 'at': (garage.centroid.x, garage.centroid.y), 'mouth': GAP,
                               'answered': False}],
                'xmarks': [{'poly': box(*XBOX[G]), 'area': box(*XBOX[G]).area, 'what': 'void'}]},
            U: {'spaces': [(lounge, 'network')], 'ring': box(0, 0, 7.1, 9), 'terraces': [box(*TERRACE)], 'closings': [],
                'unfloored': [], 'xmarks': [{'poly': box(*XBOX[U]), 'area': box(*XBOX[U]).area, 'what': 'void'}]},
        },
        'stairs': [
            {'state': 'climb', 'id': 'S1', 'from': G, 'to': U, 'kind': 'L', 'direction': 'word', 'flights': [S1_A, S1_B],
             'landings': [{'after': 7, 'poly': box(*S1_LANDING)}]},
            {'state': 'lines', 'floor': G, 'n': 2, 'why': 'no direction', 'severity': 'check', 'risers': 16,
             'text': 'Stair at ({x:.1f}, {y:.1f}): kept as lines: which end is the bottom was not found.',
             'outline': box(1.0, 7.4, 5.2, 8.6)},
        ],
    }


# ---------------------------------------------------------------------------------------------------------- the build
def read_plans(manifest: dict, folder: Path) -> list[dict]:
    """Each plan read by the app's reader -> the SourceContexts, in the manifest's file order."""
    from walkthrough_builder import contracts
    out, seen = [], set()
    for f in manifest['floors']:
        if f['file'] in seen:
            continue
        seen.add(f['file'])
        d = folder / 'read' / Path(f['file']).stem
        d.mkdir(parents=True, exist_ok=True)
        got = contracts.read_source(folder / f['file'], 'mm', d, source={'sha1': f['sha1'], 'name': f['file']}, log=lambda _m: None)
        out.append({'sha1': f['sha1'], 'name': f['file'], 'kind': 'dxf', 'units': got['units']['used'], 'conversion': None,
                    'drawing': got['drawing'], 'items': got['items'], 'plan': got['plan'], 'dxfSha1': f['sha1']})
    return out


def settings_of(manifest: dict, project: dict) -> dict:
    from walkthrough_builder import contracts
    s = json.loads((FX / 'upload' / 'settings' / 'small.json').read_text(encoding='utf-8'))
    s['project'] = dict(project)
    by_file = {}
    for f in manifest['floors']:
        by_file.setdefault(f['file'], f['sha1'])
    s['sources'] = [{'sha1': sha, 'name': name, 'kind': 'dxf', 'units': 'mm', 'unitsConfirmed': True} for name, sha in by_file.items()]
    s['layers'] = dict(manifest['layers'])
    s['floors'] = [{'key': f['key'], 'name': f['name'], 'source': f['sha1'], 'area': {'kind': 'wholeFile'}, 'level': f['level'],
                    'wallHeight': f['wallHeight'], 'slabThickness': None, 'doorHead': None, 'windowSill': None,
                    'windowHead': None, 'align': {'method': 'auto'}} for f in manifest['floors']]
    s['options'].update(contracts.NEW_RULES)
    return s


def context(s: dict, sources: list[dict], tmp: Path, project_id: str) -> dict:
    ctx = {'spec': {'format': 'job-spec/1', 'kind': 'build', 'settings': s, 'projectId': project_id, 'runId': '0002-build',
                    'buildId': '20261111T000000-0000r0', 'settingsRevision': 1, 'only': None, 'office': None,
                    'sources': [{'sha1': x['sha1'], 'name': x['name'], 'kind': x['kind'], 'path': 'no-original', 'units': x['units']}
                                for x in sources]},
           'sources': sources, 'converter': None, 'previousRunModel': None, 'versionModel': None,
           'outDir': str(tmp / 'out'), 'tmpDir': str(tmp / 'tmp')}
    for d in (ctx['outDir'], ctx['tmpDir']):
        Path(d).mkdir(parents=True, exist_ok=True)
    return ctx


def build_with(truth: dict, s: dict, sources: list[dict], tmp: Path, project_id: str) -> tuple[dict, dict]:
    """build() with the rules answered by `truth` -> (the BuildResult with every timing zero, the BuildContext)."""
    from walkthrough_builder import oslock
    from walkthrough_builder.build import build
    ctx = context(s, sources, tmp, project_id)
    with oslock.hold(), Injected(truth):
        res = build(ctx, lambda _m: None, lambda _s, _f: None)
    res['seconds'] = {k: 0.0 for k in res['seconds']}
    for fl in res['report']['floors'].values():
        if 'seconds' in fl.get('detector', {}):
            fl['detector']['seconds'] = 0.0
    return res, ctx


def write_outputs(res: dict, ctx: dict) -> dict[str, Path]:
    """U4's outputs with the build's moment fixed and inputs.json's timings zero."""
    import walkthrough_builder.out as OUT
    from walkthrough_builder import contracts
    saved = OUT._now
    OUT._now = lambda: BUILT_AT
    try:
        written = contracts.write_outputs(res, ctx, lambda _m: None)
    finally:
        OUT._now = saved
    inputs = json.loads(written['inputs.json'].read_bytes())
    inputs['seconds'] = {k: 0.0 for k in inputs['seconds']}
    written['inputs.json'].write_bytes(OUT.dumps(inputs))
    return written


# --------------------------------------------------------------------------------- the overlay's new fields and flags
def overlay_rooms(ov: dict, res: dict) -> dict:
    """The overlay U4 wrote plus the new floor fields of R-12.4 (sheet m) and the new flags of R-6.1."""
    from walkthrough_builder.out.overlay import flag
    ov = copy.deepcopy(ov)
    M, report = res['model'], res['report']
    names = {f['key']: f['name'] for f in M['floors']}
    flags = []
    for fl in ov['floors']:
        key = fl['key']
        tx, ty = res['floors_frame'][key]['toSheet']
        sh = lambda p: [round(p[0] + tx, 4) + 0.0, round(p[1] + ty, 4) + 0.0]              # noqa: E731
        rep = report['floors'][key]
        fl['spaces'] = [{'id': s['id'], 'name': s['name'], 'names': list(s['names']), 'area': s['area'],
                         'o': [sh(q) for q in s['o']], 'h': [[sh(q) for q in h] for h in s['h']], 'ceiling': s['ceiling'],
                         'source': s['source']} for s in M['spaces'] if s['floor'] == key]
        fl['holes'] = [{'what': h['what'], 'o': h['o'], 'h': []} for h in rep['slab']['holes'] if h['cut']]
        fl['stairs'] = [{k: r[k] for k in ('id', 'state', 'why', 'text', 'outline', 'walk', 'bottom', 'to', 'risers', 'riser')}
                        for r in rep['stairways']]
        fl['closings'] = [{'kind': c['kind'], 'a': c['a'], 'b': c['b']} for c in rep['slab']['closings']]
        fl['unfloored'] = [{'area': u['area'], 'o': u['o'], 'mouth': u['mouth'], 'answered': u['answered']}
                           for u in rep['slab']['unfloored']]
        for u in rep['slab']['unfloored']:
            if u['answered'] or u['area'] < 4:
                continue
            xs, ys = [p[0] for p in u['o']], [p[1] for p in u['o']]
            a, b = u['mouth'] or (None, None)
            flags.append(flag('slab-gap', key, {'at': u['at']}, 'check', 'No floor beside the walls',
                              f'About {u["area"]:.0f} m2 beside the walls has no floor: the walls do not close here.'
                              + ('' if a else ' Draw a line across the gap if it is inside the building, or say it is outdoors.'),
                              [round((a[0] + b[0]) / 2, 3), round((a[1] + b[1]) / 2, 3)] if a else u['at'],
                              [min(xs), min(ys), max(xs), max(ys)], {'a': a, 'b': b} if a else {}))
        for r in rep['rooms']['open']:
            flags.append(flag('room-open', key, {'name': r['name'], 'at': r['at']}, 'check', f'{r["name"]}: its room is not closed',
                              f'{r["name"]}: its room is not closed (a gap in its walls). Close the gap or place the name.',
                              r['at'], None, {}))
        for r in rep['rooms']['several']:
            sp = next(s for s in fl['spaces'] if s['id'] == r['space'])
            xs, ys = [p[0] for p in sp['o']], [p[1] for p in sp['o']]
            flags.append(flag('room-names', key, {'room': r['space']}, 'info', f'{len(r["names"])} names in one room',
                              f'{len(r["names"])} names in one room: an open-plan room, or a wall between them is missing.',
                              [round((min(xs) + max(xs)) / 2, 3), round((min(ys) + max(ys)) / 2, 3)], None, {'room': r['space']}))
        for c in rep['slab']['closings']:
            if c['kind'] == 'doorway':
                flags.append(flag('doorway', key, {'a': c['a'], 'b': c['b']}, 'info', 'A gap closed as a doorway',
                                  f'A gap of {c["width"]:.2f} m between two wall ends was closed as a doorway: no door was found here.',
                                  [round((c['a'][0] + c['b'][0]) / 2, 3), round((c['a'][1] + c['b'][1]) / 2, 3)], None,
                                  {'a': c['a'], 'b': c['b']}))
        for r in rep['stairways']:
            if r['state'] == 'lines':
                flags.append(flag('stair', key, {'stair': r['id']}, r['severity'], 'Stair kept as lines', r['text'], r['at'], None,
                                  {'stair': r['id']}))
        if rep['stairClash']:
            n = len(rep['stairClash'])
            words = {'wall': 'wall', 'glass': 'glass', 'column': 'column'}
            kind = words.get(rep['stairClash'][0]['kind'], 'part') if len({c['kind'] for c in rep['stairClash']}) == 1 else 'part'
            flags.append(flag('stair-clash', key, {'stair': rep['stairClash'][0]['stair'], 'n': n}, 'info', 'Walls cut under a stair',
                              f'{n} {kind} piece{"" if n == 1 else "s"} of {names[key]} under the stair '
                              f'{"was" if n == 1 else "were"} cut to the stair\'s underside.', rep['stairClash'][0]['at'], None,
                              {'stair': rep['stairClash'][0]['stair']}))
        for h in rep['slab']['holes']:
            if not h['cut']:
                flags.append(flag('hole-skipped', key, {'at': h['at']}, 'info', 'A void mark was not cut',
                                  'An X marks a void on the lowest floor: not cut.', h['at'], None, {}))
    ov['flags'] = ov['flags'] + flags
    return ov


NEW_KINDS = ('slab-gap', 'room-open', 'room-names', 'doorway', 'stair', 'stairs-none', 'stair-clash', 'hole-skipped')


def every_kind(ov: dict) -> dict:
    """One flag of each new kind: the reference overlay's, and a hand-written `stairs-none`."""
    from walkthrough_builder.out.overlay import flag
    seen = {}
    for f in ov['flags']:
        if f['kind'] in NEW_KINDS:
            seen.setdefault(f['kind'], f)
    seen['stairs-none'] = flag('stairs-none', G, {'from': G, 'to': U}, 'check', 'No stair can be climbed',
                               'No stair between Ground floor and Upper floor can be climbed. Stair at (3.1, 8.0): kept as '
                               'lines: which end is the bottom was not found.', [3.1, 8.0], None, {})
    assert set(seen) == set(NEW_KINDS), sorted(set(NEW_KINDS) - set(seen))
    return {'format': 'flag-examples/1',
            'note': 'One Flag of each kind the rooms milestone adds (docs/rooms/DESIGN.md R-6.1). Seven are the reference '
                    "building's own (fixtures/rooms/overlay.reference.json); `stairs-none` is written by hand, since a "
                    'building whose stair climbs raises none. Made by tools/rooms/make-reference-building.py.',
            'flags': [seen[k] for k in NEW_KINDS]}


# --------------------------------------------------------------------------------------------------------- the fixtures
def pretty(obj) -> bytes:
    return (json.dumps(obj, indent=2, ensure_ascii=False, allow_nan=False) + '\n').encode('utf-8')


def compact(obj) -> bytes:
    return json.dumps(obj, separators=(',', ':'), ensure_ascii=False, allow_nan=False).encode('utf-8')


def job_record(model: dict) -> dict:
    steps = [('ensure', 'Checking the readings'), ('align', 'Lining up the floors')]
    steps += [(f'detect:{f["key"]}', f'Finding doors and windows on {f["name"]}') for f in model['floors']]
    steps += [('walls', 'Building walls and glass'), ('openings', 'Cutting the openings'), ('furniture', 'Placing the furniture boxes'),
              ('outputs', 'Writing the outputs'), ('validate', 'Checking the outputs')]
    return {'format': 'job/1', 'kind': 'build', 'runId': '0002-build', 'status': 'done', 'pid': None, 'procStart': None,
            'queuedAt': AT, 'startedAt': AT, 'finishedAt': AT, 'step': 'validate', 'progress': 1.0,
            'steps': [{'name': n, 'label': label, 'status': 'done', 'seconds': 0.1, 'note': ''} for n, label in steps],
            'messages': [{'at': AT, 'level': 'info', 'text': f'{label}: done'} for _n, label in steps], 'error': None,
            'outputs': {}}


def reference_files(tmp: Path) -> dict[str, bytes]:
    """Every fixture of the reference building: { path under fixtures/: bytes }."""
    from walkthrough_builder import jsonfile
    manifest = write_dxf(tmp / 'dxf')
    sources = read_plans(manifest, tmp / 'dxf')
    s = settings_of(manifest, PROJECT)
    res, ctx = build_with(reference_truth(), s, sources, tmp / 'build', PROJECT_ID)
    written = write_outputs(res, ctx)
    ov = json.loads(written['overlay.json'].read_bytes())
    if not all('spaces' in fl for fl in ov['floors']):      # RI (11 Nov): out/overlay.py (R3) writes the new fields and
        ov = overlay_rooms(ov, res)                          # flags itself now; overlay_rooms is how R0 made them before
    files = {
        f'models/{NAME}.model.json': written['model.json'].read_bytes(),
        f'presentation/{NAME}.json': written['presentation.json'].read_bytes(),
        f'stages/{NAME}.stages.json': written['stages.json'].read_bytes(),
        'rooms/settings.reference.json': pretty(s),
        'rooms/build-result.reference.json': jsonfile.dumps(res, pretty=False),
        'rooms/overlay.reference.json': compact(ov),
        'rooms/flags.every-kind.json': pretty(every_kind(ov)),
    }
    run = 'rooms/runs/reference-build'
    outputs = {'model.json': {'fixture': f'fixtures/models/{NAME}.model.json'},
               'stages.json': {'fixture': f'fixtures/stages/{NAME}.stages.json'},
               'presentation.json': {'fixture': f'fixtures/presentation/{NAME}.json'},
               'report.json': {'file': 'out/report.json'}, 'overlay.json': {'fixture': 'fixtures/rooms/overlay.reference.json'}}
    for name in ('diff.json', 'openings.json', 'pieces.json', 'topview.png', PROJECT['maxFileName'], 'inputs.json'):
        outputs[name] = {'file': f'out/{name}'}
    for name in ('report.json', 'diff.json', 'openings.json', 'pieces.json', 'topview.png', PROJECT['maxFileName'], 'inputs.json'):
        files[f'{run}/out/{name}'] = written[name].read_bytes()
    files[f'{run}/run.json'] = pretty({'format': 'fake-run/1', 'kind': 'build', 'runId': '0002-build', 'outputs': outputs})
    job = job_record(res['model'])
    for name, src in outputs.items():
        data = files[src['fixture'][len('fixtures/'):]] if 'fixture' in src else files[f'{run}/{src["file"]}']
        job['outputs'][name] = {'bytes': len(data), 'sha1': hashlib.sha1(data).hexdigest()}
    files[f'{run}/job.json'] = pretty(job)
    summary(res)
    return files


def summary(res: dict) -> None:
    m = res['model']
    kinds = {}
    for p in m['parts']:
        kinds[p['kind']] = kinds.get(p['kind'], 0) + 1
    print(f'  {m["project"]}: {len(m["parts"])} parts {kinds}; openings {[(o["id"], o["kind"]) for o in m["openings"]]}; '
          f'stairways {[(s["id"], s["kind"], s["risers"], s["riser"], s["treads"], s["landings"]) for s in m["stairways"]]}; '
          f'spaces {[(s["id"], s["name"], s["area"]) for s in m["spaces"]]}')
    for key, fl in res['report']['floors'].items():
        print(f'  {key}: rooms {fl["rooms"]}; slab ring {fl["slab"]["ring"]} terraces {fl["slab"]["terraces"]} old {fl["slab"]["old"]} '
              f'plate {fl["slab"]["plate"]} holes {fl["slab"]["holes"]} unfloored {[(u["area"], u["mouth"]) for u in fl["slab"]["unfloored"]]} '
              f'closings {fl["slab"]["closings"]} dropped {fl["slab"]["dropped"]}; stairs '
              f'{[(r["id"], r["state"], r["why"]) for r in fl["stairways"]]}; clash {fl["stairClash"]}')


def stair_files(tmp: Path) -> dict[str, bytes]:
    """fixtures/models/stairs-{straight,L,U}.model.json from make-stair-dxf.py's drawings."""
    spec = importlib.util.spec_from_file_location('make_stair_dxf', Path(__file__).with_name('make-stair-dxf.py'))
    tool = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tool)
    files = {}
    for variant in ('straight', 'L', 'U'):
        manifest = tool.write(variant, tmp / 'dxf')
        sources = read_plans(manifest, tmp / 'dxf')
        st = manifest['stairs'][0]
        flights = []
        for f in st['flights']:
            (fx, fy), (lx, ly), n = f['first'], f['last'], f['risers']
            d = unit((lx - fx, ly - fy))
            t = (-d[1] * f['width'] / 2, d[0] * f['width'] / 2)
            mids = [(fx + (lx - fx) * k / (n - 1), fy + (ly - fy) * k / (n - 1)) for k in range(n)]
            flights.append([((x - t[0], y - t[1]), (x + t[0], y + t[1])) for x, y in mids])
        landings = []
        if 'landing' in st:
            (x0, y0), (x1, y1) = st['landing']
            landings = [{'after': len(flights[0]), 'poly': box(x0, y0, x1, y1)}]
        room = lambda: box(0.2, 0.2, 9.8, 7.8)                                   # noqa: E731
        truth = {'floors': {f['key']: {'spaces': [(room(), 'network')], 'ring': box(0, 0, 10, 8), 'terraces': [], 'closings': [],
                                       'unfloored': [], 'xmarks': []} for f in manifest['floors']},
                 'stairs': [{'state': 'climb', 'id': 'S1', 'from': G, 'to': U, 'kind': st['expect']['kind'],
                             'direction': st['expect']['direction'], 'flights': flights, 'landings': landings}]}
        name = f'Stair {variant}'
        project = {'name': name, 'shortName': name, 'projectNo': None, 'photoName': f'Stairs-{variant}', 'maxPrefix': 'ST',
                   'maxFileName': f'Stairs_{variant}.ms', 'exportedFrom': None}
        res, _ctx = build_with(truth, settings_of(manifest, project), sources, tmp / f'build-{variant}', f'stairs-{variant.lower()}')
        from walkthrough_builder.out import model_bytes
        files[f'models/stairs-{variant}.model.json'] = model_bytes(res['model'])
        summary(res)
    return files


def emit(files: dict[str, bytes], check: bool) -> int:
    bad = 0
    for rel, data in files.items():
        p = FX / rel
        if check:
            same = p.is_file() and p.read_bytes() == data
            bad += not same
            print(f'  {rel}: {"as this tool writes it" if same else "DIFFERENT (or missing)"}')
        else:
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_bytes(data)
            print(f'  fixtures/{rel}  {len(data):,} B  {hashlib.sha1(data).hexdigest()[:12]}')
    return 1 if bad else 0


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('what', choices=('dxf', 'fixtures', 'stairs'))
    ap.add_argument('out', nargs='?')
    ap.add_argument('--tmp', default=None)
    ap.add_argument('--check', action='store_true')
    a = ap.parse_args(argv)
    if os.environ.get('PYTHONHASHSEED') != '0':                        # ezdxf's OBJECTS order follows string hashing
        env = dict(os.environ, PYTHONHASHSEED='0')
        return subprocess.run([sys.executable, '-B', str(Path(__file__).resolve()), *argv], env=env).returncode
    if a.what == 'dxf':
        if not a.out:
            ap.error('dxf needs <out dir>')
        doc = write_dxf(Path(a.out))
        print(f'make-reference-building: {", ".join(f["file"] for f in doc["floors"])}, {NAME}.json -> {a.out}')
        return 0
    tmp = Path(a.tmp) if a.tmp else Path(tempfile.mkdtemp(prefix='wt-reference-'))
    tmp.mkdir(parents=True, exist_ok=True)
    os.environ.setdefault('WALKTHROUGH_CACHE_DIR', str(tmp / 'cache'))
    print(f'make-reference-building: {a.what} (work folder {tmp})')
    return emit(reference_files(tmp / 'reference') if a.what == 'fixtures' else stair_files(tmp / 'stairs'), a.check)


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
