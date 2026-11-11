"""R1's test helpers (docs/rooms/WORK_BREAKDOWN.md R1; ACCEPTANCE 2.1 R1), with their own self-checks.

* A synthetic floor made by hand, with no drawing and no door finder: `floor(...)` gives a contracts.FloorBuilt (walls as
  polygons, opening spans, drawn lines as reader items, today's plate by the builder's own `plates_of`) and `context(...)`
  the builder's context for it, so one rule can be tested on one shape in milliseconds: `run(fb, X)` is pass 1
  (network_of, plate_of), `slab(fb, X, ...)` pass 3 (cut_slab, ceilings_of).
* Small shapes: `box`, `room` (the four walls of a rectangular room, with openings left in them), `line` / `text` (reader
  items on a layer of a given role).
* `rooms_dxf`: a two-room drawing (ezdxf, deterministic) with a doorway that has wall lines drawn across it, read by
  the upload milestone's minimal reader with keys, for the set-aside tests through prepare_floors and build().
* `floors_of`: the floors of a `*-rooms` drawing after prepare_floors and floor_walls (the inputs of the rules), for the
  heavy tests that run a rule again with something changed (a door undone, another disc).
"""
from __future__ import annotations

import copy
import math
import types
from pathlib import Path

import pytest
from shapely.geometry import Point, Polygon, box as _box
from shapely.ops import unary_union

import kit
import rooms_kit
from test_u3_helpers import build_ctx
from walkthrough_builder import contracts
from walkthrough_builder.build import bank as BK
from walkthrough_builder.build import ceilings as CE
from walkthrough_builder.build import network as NW
from walkthrough_builder.build import settings as ST
from walkthrough_builder.build import slabs as SL

ROLE_LAYER = {'wall': 'A-WALL', 'column': 'S-COLS', 'glass': 'A-GLAZ', 'window': 'A-WIND', 'screen': 'A-SCRN',
              'railing': 'A-HRAL', 'room-name': 'A-AREA-IDEN', 'room-outline': 'A-AREA', 'other': 'A-ANNO',
              'ignore': 'X-IGNORE', 'furniture': 'I-FURN', 'grid': 'S-GRID', 'stair': 'S-STRS'}


def box(x0, y0, x1, y1):
    return _box(min(x0, x1), min(y0, y1), max(x0, x1), max(y0, y1))


def room(x0, y0, x1, y1, t=0.2, gaps=None) -> list:
    """The four walls of a rectangular room, outer faces at x0, y0, x1, y1, `t` thick, as polygons. gaps: { 'S' | 'N':
    [(xa, xb), ...], 'W' | 'E': [(ya, yb), ...] }: openings left in a wall (two wall ends face each other across each)."""
    gaps = gaps or {}
    walls = {'S': box(x0, y0, x1, y0 + t), 'N': box(x0, y1 - t, x1, y1), 'W': box(x0, y0 + t, x0 + t, y1 - t),
             'E': box(x1 - t, y0 + t, x1, y1 - t)}
    out = []
    for side, g in walls.items():
        for a, b in gaps.get(side, []):
            cut = box(a, y0 - 1, b, y1 + 1) if side in 'SN' else box(x0 - 1, a, x1 + 1, b)
            g = g.difference(cut)
        out += BK.polys(g)
    return out


def line(role, pts, *, closed=False, cont=True, t=None, layer=None) -> dict:
    """A drawn line or polyline as the reader gives it (sheet m), on a layer of the given builder role."""
    return {'t': t or ('LINE' if len(pts) == 2 else 'LWPOLYLINE'), 'lay': layer or ROLE_LAYER[role], 'roles': frozenset({role}),
            'cont': cont, 'pts': [[float(x), float(y)] for x, y in pts], 'closed': closed, 'depth': 0, 'path': '', 'h': 'H'}


def text(s, at, role='room-name') -> dict:
    return {'t': 'TEXT', 'lay': ROLE_LAYER[role], 'roles': frozenset({role}), 'cont': True, 'text': s, 'ins': [float(at[0]), float(at[1])],
            'depth': 0, 'path': '', 'h': 'H'}


def span(a, b, t=0.2, kind='door', rid='F1-001', lift=False) -> dict:
    """An opening record as bank.build_openings leaves it: its span (the wall thickness + 4 cm across) and its kind."""
    u = BK.unit((b[0] - a[0], b[1] - a[1]))
    w = math.dist(a, b)
    return {'o': {'id': rid, 'kind': kind, 'subtype': '', 'a': list(a), 'b': list(b)}, 'a': tuple(a), 'b': tuple(b), 'u': u,
            'n': (-u[1], u[0]), 'w': w, 't': t, 'span': BK.rect(a, u, 0, w, -t / 2 - 0.02, t / 2 + 0.02),
            'foot': BK.rect(a, u, 0, w, -(t / 2 + BK.CUT_MARGIN), t / 2 + BK.CUT_MARGIN), 'liftDoor': lift}


def context(*, floors=None, fixes=None, options=None, aside=None, shift=None):
    """The builder's context for hand-made floors: settings (floors: [{ key, level, wallHeight, slabThickness,
    ceilingHeight }]), options (the new rules), the defaults, the vocabulary, and floor_info (aside: { key: [items] };
    shift: { key: (dx, dy) })."""
    floors = floors or [{'key': 'F1', 'level': 0.0, 'wallHeight': 3.0}]
    fl = [{'slabThickness': None, 'ceilingHeight': None, **f} for f in floors]
    fx = {'setAside': [], 'openings': [], 'outlineEdges': [], 'closings': [], 'rooms': [], 'stairs': [], **(fixes or {})}
    X = types.SimpleNamespace()
    X.settings = {'floors': fl, 'fixes': fx, 'defaults': dict(ST.DEFAULTS)}
    X.options = {**ST.OPTIONS, **contracts.NEW_RULES, **(options or {})}
    X.DEF = dict(ST.DEFAULTS)
    X.V = BK.Vocab(None)
    X.floor_info = {f['key']: {'shift': tuple((shift or {}).get(f['key'], (0.0, 0.0))), 'aside': list((aside or {}).get(f['key'], []))}
                    for f in fl}
    X.new_rule = None
    return X


def floor(key='F1', *, walls=(), glass=(), spans=(), singles=(), items=(), rails=(), parapets=(), index=0, level=0.0,
          top=3.0, lowest=None, stairs=(), wall_lines=True) -> dict:
    """A contracts.FloorBuilt made by hand. walls / glass: polygons (built parts); spans: `span()` records; singles:
    polygons of single-line parts; items: reader items (`line`, `text`); rails / parapets: polygons; stairs: today's
    stair groups ([{ 'hull': polygon, 'flights': [], 'lines': [] }]). Today's plate is the builder's own (`plates_of`).
    wall_lines: the walls' outlines are also drawn lines on the wall layer, as in a drawing (R-2.1 point 4)."""
    walls, glass, spans = list(walls), list(glass), list(spans)
    its = list(items)
    if wall_lines:
        for w in walls:
            for p in BK.polys(w):
                its.append(line('wall', list(p.exterior.coords)[:-1], closed=True))
    e_walls = [unary_union(walls) if walls else Polygon(), unary_union(glass) if glass else Polygon()]
    lowest = (index == 0) if lowest is None else lowest
    old_stairs = {'stairs': list(stairs), 'below': [], 'above': [], 'steps': [], 'lines': []}
    plate, report, _dropped = BK.plates_of(e_walls, list(rails) + list(parapets), spans, old_stairs['stairs'], lowest)
    parts = [{'floor': key, 'kind': 'wall', 'poly': p, 'z0': 0.0, 'z1': top, 'follow': True, 'label': None, 'extra': {}}
             for w in walls for p in BK.polys(w)]
    parts += [{'floor': key, 'kind': 'glass', 'poly': p, 'z0': 0.0, 'z1': top, 'follow': True, 'label': None, 'extra': {}}
              for g in glass for p in BK.polys(g)]
    parts += [{'floor': key, 'kind': 'single', 'poly': p, 'z0': 0.0, 'z1': 1.0, 'follow': False, 'label': None, 'extra': {'_single': True}}
              for p in singles]
    return {'key': key, 'index': index, 'level': level, 'top': top, 'lowest': lowest, 'items': its, 'parts': parts,
            'e_walls': e_walls, 'recs': spans, 'rails': list(rails), 'parapets': list(parapets), 'singles': list(singles),
            'old_plate': plate, 'old_report': report, 'old_stairs': old_stairs}


def run(fb, X=None):
    """Pass 1 on one hand-made floor -> { net, plate0, unfloored, report, X }."""
    X = X or context(floors=[{'key': fb['key'], 'level': fb['level'], 'wallHeight': fb['top']}])
    net = NW.network_of(fb, X.settings['fixes'], X)
    plate0, unfloored, report = NW.plate_of(fb, net, X.settings['fixes'], X)
    return {'net': net, 'plate0': plate0, 'unfloored': unfloored, 'report': report, 'X': X, 'fb': fb}


NO_STAIRS = {'built': [], 'left': [], 'pairs': [], 'fixes': []}


def slab(r, stairs=None, holes_above=None, headroom=None):
    """Pass 3 on the result of `run` -> { parts, voids, holes, dropped, ceilings }."""
    fb, X = r['fb'], r['X']
    parts, voids, rep = SL.cut_slab(fb, r['net'], r['plate0'], stairs or NO_STAIRS, X.settings['fixes'], X)
    ceilings = CE.ceilings_of(fb, r['net'], r['plate0'], holes_above, headroom, X) if X.options['ceilings'] == 'auto' else []
    return {'parts': parts, 'voids': voids, 'holes': rep['holes'], 'dropped': rep['dropped'], 'ceilings': ceilings}


def closings(r, kind=None) -> list:
    return [c for c in r['net']['closings'] if kind is None or c['kind'] == kind]


def room_at(r, x, y):
    """The room (contracts.SpaceGeo) that contains the point, or None."""
    return next((s for s in r['net']['spaces'] if s['poly'].contains(Point(x, y))), None)


# ------------------------------------------------------------------------------------------ a drawing with keys (ezdxf)
ROOMS_LAYERS = {'A-WALL': 'wall', 'A-AREA-IDEN': 'room-name', '0': 'other'}


def rooms_dxf(path: Path, names=('WEST', 'EAST')) -> Path:
    """Two rooms side by side (mm; 0.2 m walls drawn as solid fills on A-WALL): WEST x 0 - 5 m and EAST x 5 - 10 m, both
    y 0 - 4 m, the wall between them at x 4.9 - 5.1 with a doorway at y 1.5 - 2.5. Two wall LINES are drawn across the
    doorway (x 4.9 and x 5.1, y 1.5 - 2.5), as a designer draws a wall through an opening: they pair into a wall piece
    that stands in the doorway until staff set them aside (DESIGN R-2.6, the last point). The names WEST and EAST (or
    those of `names` that are given: a room can be left with no drawn name)."""
    import ezdxf
    from ezdxf import units
    doc = ezdxf.new('R2013')
    doc.units = units.MM
    for name in ('A-WALL', 'A-AREA-IDEN'):
        doc.layers.add(name)
    msp = doc.modelspace()
    for x0, y0, x1, y1 in ((0, 0, 10000, 200), (0, 3800, 10000, 4000), (0, 200, 200, 3800), (9800, 200, 10000, 3800),
                           (4900, 200, 5100, 1500), (4900, 2500, 5100, 3800)):
        h = msp.add_hatch(color=8, dxfattribs={'layer': 'A-WALL'})
        h.set_solid_fill(color=8)
        h.paths.add_polyline_path([(x0, y0), (x1, y0), (x1, y1), (x0, y1)], is_closed=True)
    msp.add_line((4900, 1500), (4900, 2500), dxfattribs={'layer': 'A-WALL'})
    msp.add_line((5100, 1500), (5100, 2500), dxfattribs={'layer': 'A-WALL'})
    for name, at in (('WEST', (2000, 2000)), ('EAST', (7000, 2000))):
        if name in names:
            msp.add_text(name, height=250, dxfattribs={'layer': 'A-AREA-IDEN'}).set_placement(at)
    doc.saveas(path)
    return path


# ------------------------------------------------------------------------------------- the floors of a real drawing
def floors_of(name: str, ref: Path, tmp: Path) -> dict:
    """A `*-rooms` drawing after prepare_floors and floor_walls (the caller holds the machine run lock: the door finder
    runs) -> { name, X, floors: the working dicts, fbs: [contracts.FloorBuilt] }. The floors are the build's own
    objects: copy a FloorBuilt (`undone`, `dict(fb)`) before changing it."""
    from walkthrough_builder.build import prepare_floors
    s = rooms_kit.rooms_settings(name)
    sources = rooms_kit.rooms_sources(name, s, ref)
    floors = prepare_floors(build_ctx(s, sources, tmp, rooms_kit.ROOMS_BUILDS[name]), lambda _m: None, lambda _s, _f: None)
    return {'name': name, 'X': floors.X, 'floors': list(floors), 'fbs': [BK.floor_walls(F, floors.X) for F in floors]}


def undone(fb, i: int) -> dict:
    """The floor with its opening record i undone (RA-18): its span out of the records, what is built in its footprint
    out of the walls, and today's plate made again without it."""
    r = fb['recs'][i]
    cut = r['span'].buffer(0.005, join_style='mitre')
    out = dict(fb)
    out['recs'] = [x for j, x in enumerate(fb['recs']) if j != i]
    out['e_walls'] = [g.difference(cut) for g in fb['e_walls']]
    out['old_plate'] = BK.plates_of(out['e_walls'], list(fb['rails']) + list(fb['parapets']), out['recs'],
                                    fb['old_stairs'].get('stairs') or [], fb['lowest'])[0]
    return out


# ------------------------------------------------------------------------------------------------------ self-checks
def test_a_hand_made_room_is_one_room_with_its_floor() -> None:
    fb = floor(walls=room(0, 0, 6, 4), spans=[span((2.0, 0.1), (3.0, 0.1))])
    r = run(fb)
    assert len(r['net']['spaces']) == 1 and r['net']['shapes'] == 0 and closings(r) == []
    assert r['net']['spaces'][0]['poly'].area == pytest.approx(5.6 * 3.6, abs=0.05)      # between the wall faces
    assert r['plate0'].area > 23.9 and r['unfloored'] == []
    assert room_at(r, 3, 2)['id'] == 'F1-R001'
    s = slab(r)
    assert len(s['parts']) == 1 and len(s['ceilings']) == 1 and s['voids'] == []


def test_the_helpers_leave_their_inputs_alone() -> None:
    fb = floor(walls=room(0, 0, 6, 4), spans=[span((2.0, 0.1), (3.0, 0.1))])
    before = copy.deepcopy({k: fb[k] for k in ('recs', 'parts', 'items')})
    run(fb)
    u = undone(fb, 0)
    assert len(u['recs']) == 0 and len(fb['recs']) == 1
    assert [p['kind'] for p in fb['parts']] == [p['kind'] for p in before['parts']] and len(fb['items']) == len(before['items'])
    assert kit.ROOMS_FIXTURES.is_dir()
