"""R2's contract test (docs/rooms/WORK_BREAKDOWN.md R2; ACCEPTANCE RA-9, the last point; DESIGN R-14): the reference
building built from its DXFs through build() with the real rules. Its treads, landings, well and stairway equal the
frozen model fixture (fixtures/models/rooms-reference.model.json) within 1 mm: the fixture the walker's tests climb.

The same for the three stair drawings (straight, L, U) against fixtures/models/stairs-*.model.json.
"""
from __future__ import annotations

import json

import pytest
from shapely.geometry import LineString, Polygon

import kit
from test_r2_helpers import close, model_poly, staged, synthetic
from walkthrough_builder import oslock

MM = 0.001 + 1e-9               # 1 mm per coordinate (the model rounds to mm; the drawings draw nosing pairs at whole mm)
MM_SHAPE = 0.0015               # ... which is up to 1.42 mm between two outlines at a corner


def fixture(name: str) -> dict:
    return json.loads((kit.FIXTURES / 'models' / f'{name}.model.json').read_text(encoding='utf-8'))


@pytest.fixture(scope='module')
def built(reference_building, tmp_path_factory) -> dict:
    tmp = tmp_path_factory.mktemp('r2-reference')
    with oslock.hold():
        return staged(reference_building['settings'], reference_building['sources'], tmp / 'build', 'rooms-reference')


def same_stair(model: dict, want: dict, sid: str = 'S1') -> None:
    """The stairway record, the tread and landing parts and the cut parts of one stair, within 1 mm."""
    got_sw = next(s for s in model['stairways'] if s['id'] == sid)
    want_sw = next(s for s in want['stairways'] if s['id'] == sid)
    for k in ('id', 'from', 'to', 'kind', 'risers', 'direction', 'treads', 'landings'):
        assert got_sw[k] == want_sw[k], k
    for k in ('riser', 'going', 'width'):
        assert abs(got_sw[k] - want_sw[k]) <= MM, k
    for k in ('bottom', 'top'):
        assert max(abs(a - b) for a, b in zip(got_sw[k], want_sw[k])) <= MM, k
    # the walking line as a line (the fixture's and the builder's may keep different points on it: R0.md section 4)
    assert LineString(got_sw['walk']).hausdorff_distance(LineString(want_sw["walk"])) <= MM_SHAPE
    assert max(abs(a - b) for a, b in zip(got_sw['walk'][-2], want_sw['walk'][-2])) <= MM, 'the middle of the top riser'

    def parts(m):
        return sorted((p for p in m['parts'] if p.get('stair') == sid), key=lambda p: (p['kind'], p.get('label') or '', p['z1']))
    got, exp = parts(model), parts(want)
    assert [(p['kind'], p.get('label'), p['floor']) for p in got] == [(p['kind'], p.get('label'), p['floor']) for p in exp]
    for g, e in zip(got, exp):
        assert abs(g['z0'] - e['z0']) <= MM and abs(g['z1'] - e['z1']) <= MM, g.get('label')
        assert g['follow'] is False and g.get('fit') == 'storey'
        assert close(model_poly(g), model_poly(e), MM_SHAPE), g.get('label') or g['kind']


def same_well(model: dict, want: dict) -> None:
    for key, voids in want['voids'].items():
        wells = [v for v in voids if v['what'] == 'stair well']
        mine = [v for v in model['voids'][key] if v['what'] == 'stair well']
        assert len(mine) == len(wells), key
        for g, e in zip(mine, wells):
            assert abs(g['area'] - e['area']) <= 0.01 and abs(g['x'] - e['x']) <= MM and abs(g['y'] - e['y']) <= MM


def test_the_reference_building_equals_its_fixture(built) -> None:
    """Treads, landings, the cut wall, the stairway and the well: the model fixture, within 1 mm."""
    want = fixture('rooms-reference')
    model = built['res']['model']
    same_stair(model, want)
    same_well(model, want)
    assert not [p for p in model['parts'] if p['kind'] == 'step'], 'no two-riser step part with the new rule'


def test_the_reference_well_and_the_report(built) -> None:
    """The well as the builder made it: the outline test_r_fixtures.py pins; the report's rows as the fixture's."""
    sb = built['stairs']['built'][0]
    well = sb['wellOf']['upper']
    assert close(well, Polygon([(0.55, 2.59), (1.85, 2.59), (1.85, 3.43), (4.04, 3.43), (4.04, 4.73), (0.55, 4.73)]), MM)
    want = json.loads((kit.ROOMS_FIXTURES / 'build-result.reference.json').read_text(encoding='utf-8'))['report']['floors']
    rep = built['res']['report']['floors']
    for key in ('ground', 'upper'):
        got = [(r['id'], r['state'], r['why'], r['severity'], r['text'], r['to'], r['risers'], r['riser']) for r in rep[key]['stairways']]
        exp = [(r['id'], r['state'], r['why'], r['severity'], r['text'], r['to'], r['risers'], r['riser']) for r in want[key]['stairways']]
        assert got == exp, key
        assert [(c['stair'], c['kind'], c['area'], c['z1']) for c in rep[key]['stairClash']] == \
            [(c['stair'], c['kind'], c['area'], c['z1']) for c in want[key]['stairClash']], key
    holes = {h['what']: h for h in rep['upper']['slab']['holes']}
    assert holes['stair well']['cut'] and holes['stair well']['area'] == 5.63


def test_the_reference_stair_was_read_from_both_plans(built) -> None:
    """S1: 7 risers, a landing, then 9: 5 on the ground plan (the word UP, a break line) and 5 on the upper plan (DN),
    riser 12 on both; S2 has no direction; the upper plan's drawing is no stair of its own."""
    g, u = built['found']['ground'], built['found']['upper']
    assert [len(f['risers']) for f in g[0]['flights']] == [7, 5] and g[0]['more']['by'] == 'word'
    assert [len(f['risers']) for f in g[1]['flights']] == [16] and g[1]['more']['by'] is None
    assert [len(f['risers']) for f in u[0]['flights']] == [5] and u[0]['flights'][0]['sense'] == 'arrives'
    res = built['stairs']
    assert [(s['id'], s['why'], s['severity']) for s in res['left']] == [('ground-ST2', 'no direction', 'check')]
    assert res['pairs'] == [] and len(res['built']) == 1
    sb = res['built'][0]
    assert sb['linesUsed']['ground'] and sb['linesUsed']['upper']
    assert [(c['part'], round(c['z1'], 4)) for c in sb['cuts']] and len(sb['cuts']) == 1, 'only the cupboard wall is cut'


@pytest.mark.parametrize('variant', ['straight', 'L', 'U'])
def test_the_stair_drawings_equal_their_fixtures(variant: str, tmp_path) -> None:
    """make-stair-dxf.py's three drawings, read and built by the rules: the walker's fixtures within 1 mm."""
    b = synthetic(variant, tmp_path)
    want = fixture(f'stairs-{variant}')
    same_stair(b['res']['model'], want)
    same_well(b['res']['model'], want)
