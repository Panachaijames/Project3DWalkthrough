"""R2's test helpers (docs/rooms/WORK_BREAKDOWN.md R2; ACCEPTANCE 2.1 R2), with their own self-check.

* `staged(settings, sources, tmp, project)`: one build through build() with the stair pass watched: the reader's rows
  per floor (`found`), the builder's result (`stairs`), the floors, plates and context it was called with, and the
  build's result (`res`). The caller holds the machine run lock when the door finder runs.
* `synthetic(variant, tmp, ...)`: a drawing of tools/rooms/make-stair-dxf.py read by the app's reader and built that
  way, with levels, fixes or options changed.
* `stages_of(name, ref, tmp)`: the inputs of the stair rules of a `*-rooms` drawing (prepare_floors, floor_walls,
  network_of, plate_of), then the reader and the builder alone: no model, no outputs.
* small geometry: `mid`, `counts`, `close` (two polygons equal within a tolerance), `model_poly`.
"""
from __future__ import annotations

import copy
import math
from pathlib import Path

from shapely.geometry import Polygon

import kit
import rooms_kit
from test_u3_helpers import build_ctx, run_build
from walkthrough_builder import oslock
from walkthrough_builder.build import bank as BK
from walkthrough_builder.build import network as NW
from walkthrough_builder.build import stairs_build as SB
from walkthrough_builder.build import stairs_read as SR


def mid(seg):
    (x0, y0), (x1, y1) = seg
    return ((x0 + x1) / 2, (y0 + y1) / 2)


def counts(row) -> list:
    """The riser count of every flight of a reader's row."""
    return [len(f['risers']) for f in row['flights']]


def close(a, b, tol=0.001) -> bool:
    """Two shapes are the same within `tol` (the Hausdorff distance of their outlines)."""
    return a.boundary.hausdorff_distance(b.boundary) <= tol


def model_poly(part, offset=(0.0, 0.0)) -> Polygon:
    """A model part's outline (model frame) as a polygon in the sheet frame."""
    ox, oy = offset
    return Polygon([(x + ox, y + oy) for x, y in part['o']], [[(x + ox, y + oy) for x, y in h] for h in part.get('h') or []])


def staged(settings: dict, sources: list, tmp: Path, project: str = 'test') -> dict:
    """One build with the stair pass watched (the caller holds the run lock)."""
    seen = {}
    real = SB.build_stairs

    def watch(floors, found, nets, plate0, fixes, X):
        res = real(floors, found, nets, plate0, fixes, X)
        seen.update(floors=floors, found=found, nets=nets, plate0=plate0, X=X, stairs=res)
        return res
    SB.build_stairs = watch
    try:
        res, logs = run_build(settings, sources, tmp, project)
    finally:
        SB.build_stairs = real
    return {**seen, 'res': res, 'logs': logs, 'settings': settings}


def synthetic(variant: str, tmp: Path, *, levels: dict | None = None, fixes: list | None = None, rules: dict | None = None) -> dict:
    """`make-stair-dxf.py <variant>` built with the new rules -> staged(...) plus `plan` (the tool's manifest)."""
    plan = rooms_kit.stair_plan(variant, tmp / 'dxf')
    s = rooms_kit.plan_settings(plan, rules=rules)
    for f in s['floors']:
        if levels and f['key'] in levels:
            f['level'] = levels[f['key']]
    if fixes:
        s['fixes'] = {**s['fixes'], 'stairs': copy.deepcopy(fixes)}
    with oslock.hold():
        out = staged(s, plan['sources'], tmp / 'build', f'stairs-{variant.lower()}')
    out['plan'] = plan
    return out


def stages_of(name: str, ref: Path, tmp: Path) -> dict:
    """The stair rules alone on a `*-rooms` drawing (the caller holds the run lock: the door finder runs) ->
    { X, fbs, nets, plate0, found, stairs }."""
    from walkthrough_builder.build import prepare_floors
    s = rooms_kit.rooms_settings(name)
    sources = rooms_kit.rooms_sources(name, s, ref)
    floors = prepare_floors(build_ctx(s, sources, tmp, rooms_kit.ROOMS_BUILDS[name]), lambda _m: None, lambda _s, _f: None)
    X = floors.X
    BK.storeys(list(floors))
    fixes = X.settings['fixes']
    fbs, nets, plate0, found = [], {}, {}, {}
    for F in floors:
        fb = BK.floor_walls(F, X)
        fbs.append(fb)
        nets[fb['key']] = NW.network_of(fb, fixes, X)
        plate0[fb['key']], _u, _r = NW.plate_of(fb, nets[fb['key']], fixes, X)
        found[fb['key']] = SR.find_stairs(fb, nets[fb['key']], fixes, X)
    stairs = SB.build_stairs(fbs, found, nets, plate0, fixes, X)
    return {'X': X, 'fbs': fbs, 'nets': nets, 'plate0': plate0, 'found': found, 'stairs': stairs}


def row_at(rows: list, x: float, y: float, reach: float = 0.5):
    """The reader's row whose outline holds the point (or lies within `reach` of it), with flights first."""
    from shapely.geometry import Point
    hits = [r for r in rows if r['outline'].distance(Point(x, y)) <= reach]
    hits.sort(key=lambda r: (not r['flights'], r['outline'].distance(Point(x, y))))
    return hits[0] if hits else None


def test_the_helpers_shapes() -> None:
    a = Polygon([(0, 0), (1, 0), (1, 1), (0, 1)])
    b = Polygon([(0, 0.0004), (1, 0), (1, 1), (0, 1)])
    assert close(a, b) and not close(a, Polygon([(0, 0.01), (1, 0), (1, 1), (0, 1)]))
    assert mid(((0, 0), (2, 4))) == (1, 2) and math.isclose(model_poly({'o': [[0, 0], [1, 0], [1, 1]]}, (2, 3)).area, 0.5)
    assert kit.APP.is_dir()
