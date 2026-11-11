"""R0: the tracer (docs/rooms/DESIGN.md R-12.3; WORK_BREAKDOWN R0 item 7). Frozen after R0: it stays green while R1 and
R2 replace the tracer's bodies (build/network.py, rooms.py, slabs.py, xmarks.py, ceilings.py, stairs_read.py,
stairs_build.py) and R3 the outputs.

The whole chain on a two-floor drawing with one straight stair (`tools/rooms/make-stair-dxf.py straight`): the
drawings made at test time, read by the app's own reader, built by build() with the new options (the real door
finder), written by U4's write_outputs and checked by the API's own record checks. The result is a v2 model with one
stairway. What is asserted here is what the DESIGN fixes for any builder of these rules (R-8.1, R-8.2, R-8.5, R-12.1,
R-12.3), not the tracer's own shortcuts: a tread count, heights, the well, the walking line's ends.
"""
from __future__ import annotations

import pytest
from shapely.geometry import Point, Polygon

import rooms_kit
from test_contracts import walk
from test_u3_helpers import run_build, write_and_check
from walkthrough_builder import contracts, oslock

R = 3.0 / 16                    # the riser: a 3.00 m storey in 16 risers


@pytest.fixture(scope='module')
def straight(tmp_path_factory) -> dict:
    tmp = tmp_path_factory.mktemp('tracer')
    plan = rooms_kit.stair_plan('straight', tmp / 'dxf')
    s = rooms_kit.plan_settings(plan)
    with oslock.hold():                                     # the door finder runs in this process (U-3.5)
        res, logs = run_build(s, plan['sources'], tmp / 'build', 'tracer')
    return {'plan': plan, 'settings': s, 'res': res, 'logs': logs, 'tmp': tmp}


def sheet(straight: dict, key: str, p) -> tuple[float, float]:
    """A model point of floor `key` on the sheet (drawing metres)."""
    t = straight['res']['floors_frame'][key]['toSheet']
    return p[0] + t[0], p[1] + t[1]


def parts(model: dict, floor: str, kind: str) -> list[dict]:
    return [p for p in model['parts'] if p['floor'] == floor and p['kind'] == kind]


def covers(part_list: list[dict], p) -> bool:
    return any(Polygon(q['o'], q.get('h') or []).contains(Point(p)) for q in part_list)


def test_the_drawing_is_what_the_tool_says(straight) -> None:
    plan = straight['plan']
    assert [f['key'] for f in plan['floors']] == ['ground', 'upper'] and len(plan['sources']) == 2
    st = plan['stairs']
    assert len(st) == 1 and st[0]['flights'][0]['risers'] == 16 and st[0]['expect']['state'] == 'climb'


def test_a_v2_model_with_one_stairway(straight) -> None:
    m = straight['res']['model']
    assert [f['key'] for f in m['floors']] == ['ground', 'upper']
    assert len(m['stairways']) == 1, 'the v2 mark, and one stair you can climb'
    sw = m['stairways'][0]
    assert (sw['from'], sw['to'], sw['risers'], sw['kind'], sw['direction']) == ('ground', 'upper', 16, 'straight', 'word')
    assert sw['riser'] == pytest.approx(R, abs=6e-4) and sw['going'] == pytest.approx(0.28, abs=1e-3)   # to the millimetre
    assert sw['width'] == pytest.approx(1.2, abs=1e-3)
    assert sw['bottom'] == sw['walk'][0] and sw['top'] == sw['walk'][-1] and len(sw['walk']) >= 2
    # the walking line starts 1.0 m before riser 1 and ends 1.0 m past riser 16 (sheet: x 1.6, y 0.5 and 6.7)
    assert sheet(straight, 'ground', sw['bottom']) == pytest.approx((1.6, 0.5), abs=2e-3)
    assert sheet(straight, 'ground', sw['top']) == pytest.approx((1.6, 6.7), abs=2e-3)


def test_treads_on_the_lower_floor(straight) -> None:
    m = straight['res']['model']
    sid = m['stairways'][0]['id']
    treads = parts(m, 'ground', 'tread')
    assert len(treads) == 15 and not parts(m, 'upper', 'tread') and not parts(m, 'ground', 'landing')
    assert all(t['stair'] == sid and t['fit'] == 'storey' and t['follow'] is False for t in treads)
    by_top = sorted(treads, key=lambda t: t['z1'])
    assert [t['z1'] for t in by_top] == pytest.approx([j * R for j in range(1, 16)], abs=1e-3)
    assert [t['z0'] for t in by_top] == pytest.approx([max(0.0, (j - 2) * R) for j in range(1, 16)], abs=1e-3)
    assert [t['label'] for t in by_top] == [f'stair {sid} tread {j}' for j in range(1, 16)]
    # tread 1 lies between riser 1 (y 1.5) and riser 2 (y 1.78); the last one laps 0.05 m past riser 16 (y 5.7)
    ys = [sheet(straight, 'ground', p)[1] for p in by_top[0]['o']]
    assert (min(ys), max(ys)) == pytest.approx((1.5, 1.78), abs=2e-3)
    ys = [sheet(straight, 'ground', p)[1] for p in by_top[-1]['o']]
    assert (min(ys), max(ys)) == pytest.approx((5.42, 5.75), abs=2e-3)
    assert not any(p['kind'] == 'step' for p in m['parts']), 'no two-riser step blocks with the new rule'


def test_the_upper_slab_is_open_over_the_high_treads_only(straight) -> None:
    m = straight['res']['model']
    slabs = parts(m, 'upper', 'slab')
    assert slabs and parts(m, 'ground', 'slab')
    at = lambda x, y: (x - straight['res']['floors_frame']['upper']['toSheet'][0],   # noqa: E731
                       y - straight['res']['floors_frame']['upper']['toSheet'][1])
    # headroom 2.10 m under a 0.25 m slab: the well starts at the first tread whose top is above 0.65 m (tread 4,
    # from riser 4 at y 2.34) and ends on riser 16 (y 5.7): the slab laps the last tread
    assert covers(slabs, at(1.6, 2.0)), 'floor over the low treads'
    assert not covers(slabs, at(1.6, 2.6)) and not covers(slabs, at(1.6, 5.6)), 'open over the high treads'
    assert covers(slabs, at(1.6, 5.72)) and covers(slabs, at(1.6, 6.7)), 'the arrival stands on the slab'
    assert covers(slabs, at(5.0, 4.0))
    assert any(v['what'] == 'stair well' for v in m['voids']['upper']) and not m['voids']['ground']


def test_rooms_names_and_ceilings(straight) -> None:
    m = straight['res']['model']
    by_floor = {k: [s for s in m['spaces'] if s['floor'] == k] for k in ('ground', 'upper')}
    assert len(by_floor['ground']) == 1 and len(by_floor['upper']) == 1
    hall = by_floor['ground'][0]
    assert hall['name'] == 'HALL' and hall['names'] == ['HALL'] and hall['source'] == 'network' and hall['ceiling'] is True
    assert hall['area'] == pytest.approx(9.6 * 7.6, abs=1.0)
    assert {r['name']: r.get('space') for r in m['rooms']} == {'HALL': hall['id'], 'LANDING': by_floor['upper'][0]['id']}
    for key in ('ground', 'upper'):
        c = parts(m, key, 'ceiling')
        assert c and all(p['follow'] is False and p['z1'] - p['z0'] == pytest.approx(0.02, abs=1e-6) for p in c), key
    assert parts(m, 'ground', 'ceiling')[0]['z1'] == pytest.approx(2.7)          # min(3.00, wall height - 0.30)


def test_the_report_carries_the_new_keys_in_the_typed_shape(straight) -> None:
    res = straight['res']
    assert walk({k: v for k, v in res.items() if not k.startswith('_')}, contracts.BuildResult) == []
    for key, fl in res['report']['floors'].items():
        assert walk(fl, contracts.FloorUploadReportRooms) == [], key
        assert {'rooms', 'slab', 'stairways', 'stairClash'} <= set(fl), key
        assert fl['rooms']['spaces'] == 1 and fl['rooms']['named'] == 1
        assert fl['slab']['plate'] >= fl['slab']['old'] > 0
    rows = res['report']['floors']['ground']['stairways']
    assert [(r['id'], r['state'], r['to'], r['risers']) for r in rows] == [(res['model']['stairways'][0]['id'], 'climb', 'upper', 16)]
    assert res['report']['fixes']['closings'] == [] and res['report']['fixes']['rooms'] == []
    assert res['report']['fixes']['stairs'] == []
    facts = res['replay']['facts']
    assert facts['climbable'] == 1 and facts['ceilings'] is True and set(facts['rooms']) == {'ground', 'upper'}


def test_every_output_passes_the_apis_checks(straight) -> None:
    written, problems = write_and_check(straight['res'], straight['settings'], straight['plan']['sources'],
                                        straight['tmp'] / 'outputs', 'tracer')
    assert problems == []
    assert {'model.json', 'stages.json', 'presentation.json', 'report.json', 'overlay.json', 'topview.png'} <= set(written)


def test_the_same_drawing_with_the_old_rule_is_v1(straight, tmp_path) -> None:
    plan = straight['plan']
    s = rooms_kit.plan_settings(plan, rules={})                     # no key of the rooms milestone: the old rule
    with oslock.hold():
        res, _logs = run_build(s, plan['sources'], tmp_path / 'old', 'tracer')
    m = res['model']
    assert 'stairways' not in m and 'spaces' not in m
    assert not any(p['kind'] in ('tread', 'landing', 'ceiling') for p in m['parts'])
    assert any(p['kind'] == 'step' for p in m['parts']), "today's two-riser blocks"
    assert set(res['report']['fixes']) == {'setAside', 'openings', 'outlineEdges'}
    assert not ({'rooms', 'slab', 'stairways', 'stairClash'} & set(res['report']['floors']['ground']))


def test_stairs_kept_as_lines_is_still_v2(straight, tmp_path) -> None:
    plan = straight['plan']
    s = rooms_kit.plan_settings(plan, rules={'slabs': 'network', 'ceilings': 'off', 'stairs': 'lines'})
    with oslock.hold():
        res, _logs = run_build(s, plan['sources'], tmp_path / 'lines', 'tracer')
    m = res['model']
    assert m['stairways'] == [] and m['spaces'], 'the v2 mark is there with no stair to climb'
    assert not any(p['kind'] in ('tread', 'landing', 'ceiling') for p in m['parts'])
    rows = res['report']['floors']['ground']['stairways']
    assert len(rows) == 1 and rows[0]['state'] == 'lines'
    assert m['stairs']['ground']['below'], 'its lines are still drawn'


def test_the_options_must_agree(straight, tmp_path) -> None:
    from walkthrough_builder.build.errors import BuildError
    plan = straight['plan']
    s = rooms_kit.plan_settings(plan, rules={'slabs': 'closed-rooms', 'ceilings': 'auto', 'stairs': 'lines'})
    with pytest.raises(BuildError) as e:
        run_build(s, plan['sources'], tmp_path / 'bad', 'tracer')
    assert e.value.code == 'bad_settings'
