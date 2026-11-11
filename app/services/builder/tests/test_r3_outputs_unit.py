"""R3: the diff, the replay's captions, the presentation and the top view of a BuiltModel v2 (docs/rooms/DESIGN.md R-3.4,
R-6.4, R-11; ACCEPTANCE 2.1 R3), on the reference building's frozen model and build result:

* the diff adds the rooms closed, the plate area and the stairs you can climb per floor when a side is v2, and a floor
  whose plate is 2 m2 or more smaller comes first (its plate row first); two v1 models give what they gave;
* the replay's finish caption says "N rooms closed" and "M stairs you can climb" only when they hold (1, 2 and 3 floors,
  with and without stairs, and with the old rule's facts);
* the legend's "Stairs" row covers treads and landings, no row for ceilings, the Ceilings tick keeps the viewer's label;
  the camera comes from the slabs;
* the top view draws treads and landings and never a ceiling; the void texts carry the new `what`s; v1 models keep the
  bank's title.
"""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

import kit
import test_u4_common as c
from walkthrough_builder.jsonfile import dumps
from walkthrough_builder.out import diff as df
from walkthrough_builder.out import pictures as pic
from walkthrough_builder.out import presentation as pres
from walkthrough_builder.out import replay as rp

REF = c.MODELS / 'rooms-reference.model.json'


def ref_model() -> dict:
    return json.loads(REF.read_bytes())


def ref_result() -> dict:
    return c.load_json(kit.ROOMS_FIXTURES / 'build-result.reference.json')


def as_v1(m: dict) -> dict:
    """The same building as a v1 model: no stairways, spaces, treads, landings or ceilings."""
    m = copy.deepcopy(m)
    for k in ('stairways', 'spaces'):
        m.pop(k, None)
    m['parts'] = [p for p in m['parts'] if p['kind'] not in ('tread', 'landing', 'ceiling')]
    for p in m['parts']:
        for k in ('stair', 'fit'):
            p.pop(k, None)
    for r in m['rooms']:
        r.pop('space', None)
    return m


def shrink_upper_slab(m: dict, by: float) -> dict:
    """The upper slab's outline moved in at its east edge so the plate loses about `by` m2."""
    m = copy.deepcopy(m)
    slab = next(p for p in m['parts'] if p['floor'] == 'upper' and p['kind'] == 'slab')
    x1 = max(q[0] for q in slab['o'])
    east = [q[1] for q in slab['o'] if abs(q[0] - x1) < 1e-9]
    dx = by / (max(east) - min(east))
    slab['o'] = [[x - dx if abs(x - x1) < 1e-9 else x, y] for x, y in slab['o']]
    return m


# ------------------------------------------------------------------------------------------------------------- diff
def test_two_v1_models_have_no_rooms_rows():
    body = df.diff(c.model('bank-v2'), c.model('bank-v1'))
    assert not any(k in fl for fl in body['counts'].values() for k in (df.ROOMS_CLOSED, df.PLATE_AREA, df.CLIMBABLE))


def test_v2_against_v1_counts_rooms_plate_and_stairs():
    m = ref_model()
    body = df.diff(m, as_v1(m))
    g, u = body['counts']['ground'], body['counts']['upper']
    assert g[df.ROOMS_CLOSED] == [0, 2] and u[df.ROOMS_CLOSED] == [0, 1]
    assert g[df.CLIMBABLE] == [0, 1] and df.CLIMBABLE not in u
    assert g[df.PLATE_AREA][0] == g[df.PLATE_AREA][1] == df.plate_area(m, 'ground')
    assert df.plate_area(m, 'upper') == pytest.approx(85.0 + 0.4 - 5.63 - 5.2 + 1.0, abs=2.0)        # the plate less its holes
    assert body['partsAdded'] and not body['roomsAdded'] and not body['roomsRemoved'], 'names compared as before'
    assert not df.empty(body)


def test_a_lost_floor_comes_first_with_its_plate_row_first(tmp_path: Path):
    m = ref_model()
    lost = df.diff(shrink_upper_slab(m, 3.0), m)
    assert list(lost['counts']) == ['upper', 'ground']
    assert list(lost['counts']['upper'])[0] == df.PLATE_AREA
    before, after = lost['counts']['upper'][df.PLATE_AREA]
    assert before - after == pytest.approx(3.0, abs=0.15)
    small = df.diff(shrink_upper_slab(m, 1.5), m)
    assert list(small['counts']) == ['ground', 'upper'] and list(small['counts']['upper'])[0] != df.PLATE_AREA
    assert df.empty(df.diff(m, copy.deepcopy(m)))
    p = tmp_path / 'diff.json'
    p.write_bytes(dumps({'format': 'build-diff/1', 'against': [{'kind': 'version', 'ref': 'v1', 'diff': lost},
                                                               {'kind': 'previous-run', 'ref': '0001-build', 'diff': small}]}, pretty=False))
    c.assert_checked([('diff', p)])


# ------------------------------------------------------------------------------------------------------- the replay
def one_floor(res: dict) -> tuple[dict, dict]:
    m, rep = copy.deepcopy(res['model']), copy.deepcopy(res['replay'])
    m['floors'] = m['floors'][:1]
    m['rooms'] = [r for r in m['rooms'] if r['floor'] == 'ground']
    m['source'] = m['source'][:1]
    rep['floors'] = {'ground': rep['floors']['ground']}
    f = rep['facts']
    f['floors'] = f['floors'][:1]
    f['sources'] = f['sources'][:1]
    f['rooms'] = {'ground': f['rooms']['ground']}
    f['climbable'] = 0
    return rep, m


def three_floors(res: dict) -> tuple[dict, dict]:
    m, rep = copy.deepcopy(res['model']), copy.deepcopy(res['replay'])
    m['floors'].append({**m['floors'][1], 'key': 'roof', 'name': 'Roof', 'level': 6.0})
    rep['floors']['roof'] = rep['floors']['upper']
    f = rep['facts']
    f['floors'].append({**f['floors'][1], 'key': 'roof', 'name': 'Roof', 'level': 6.0})
    for k in ('counts', 'parts', 'openings'):
        f[k]['roof'] = f[k]['upper']
    f['rooms']['roof'] = {'spaces': 4, 'named': 1}
    f['climbable'] = 2
    return rep, m


def finish(rep: dict, m: dict, report: dict | None = None) -> str:
    return rp.stages(rep, m, report)['captions']['finish']


def test_the_finish_caption_says_rooms_closed_and_stairs_you_can_climb_only_when_they_hold():
    res = ref_result()
    assert finish(res['replay'], res['model'], res['report']).endswith(
        'Done: 2 levels, 5 wall runs, 3 lintels, 5 rooms named, 3 rooms closed, 1 stair you can climb.')
    no_stairs = copy.deepcopy(res['replay'])
    no_stairs['facts']['climbable'] = 0
    assert finish(no_stairs, res['model']).endswith('5 rooms named, 3 rooms closed.')
    old = copy.deepcopy(res['replay'])
    for k in ('rooms', 'climbable', 'ceilings'):
        old['facts'].pop(k)
    assert finish(old, res['model']).endswith('5 rooms named.')
    closed_none = copy.deepcopy(res['replay'])
    closed_none['facts']['rooms'] = {k: {'spaces': 0, 'named': 0} for k in closed_none['facts']['rooms']}
    assert 'closed' not in finish(closed_none, res['model'])
    rep1, m1 = one_floor(res)
    assert finish(rep1, m1).endswith('Done: 1 level, 4 wall runs, 2 lintels, 4 rooms named, 2 rooms closed.')
    rep3, m3 = three_floors(res)
    assert finish(rep3, m3).endswith('Done: 3 levels, 6 wall runs, 4 lintels, 5 rooms named, 7 rooms closed, 2 stairs you can climb.')
    # lines, pieces and rings are as before
    st = rp.stages(res['replay'], res['model'], res['report'])
    assert st['floors'] == rp.replay_floors(res['replay'], res['model'])


def test_the_old_rule_replay_does_not_move():
    st = rp.stages(c.replay_input(), c.model('bank-v2'), c.build_result()['report'])
    assert 'closed' not in st['captions']['finish'] and 'climb' not in st['captions']['finish']


# ------------------------------------------------------------------------------------------------- the presentation
def test_the_legend_covers_treads_and_landings_and_never_ceilings():
    m = ref_model()
    texts = lambda mm: [it['text'] for it in pres.presentation(mm)['legend']['items']]           # noqa: E731
    assert texts(m) == ['Walls and lintels', 'Railings', 'Stairs', 'Floor plates']
    no_lines = copy.deepcopy(m)
    no_lines['stairs'] = {k: {'below': [], 'above': []} for k in m['stairs']}
    assert 'Stairs' in texts(no_lines), 'the treads alone make the row'
    only_landing = copy.deepcopy(no_lines)
    only_landing['parts'] = [p for p in only_landing['parts'] if p['kind'] != 'tread']
    assert 'Stairs' in texts(only_landing)
    flat = copy.deepcopy(no_lines)
    flat['parts'] = [p for p in flat['parts'] if p['kind'] not in ('tread', 'landing')]
    assert 'Stairs' not in texts(flat) and not any('eiling' in t for t in texts(m))
    p = pres.presentation(m)
    assert 'labels' not in p and 'toggles' not in p, "the Ceilings tick keeps the viewer's own label, 'Ceilings'"
    labels = (kit.APP / 'packages' / 'viewer' / 'src' / 'model' / 'presentation.ts').read_text(encoding='utf-8')
    assert "ceilings: 'Ceilings'" in labels
    assert pres.camera_view(m, p, margin=pres.CAMERA_MARGIN_PX)['inside']


def test_the_camera_and_ground_plane_come_from_the_slabs():
    m = ref_model()
    big = copy.deepcopy(m)
    slab = next(q for q in big['parts'] if q['kind'] == 'slab' and q['floor'] == 'ground')
    slab['o'] = [[x * 2.0, y * 2.0] for x, y in slab['o']]
    a, b = pres.presentation(m)['camera']['away'], pres.presentation(big)['camera']['away']
    assert b[0] > a[0] and b[2] > a[2]
    plinth = copy.deepcopy(big)
    next(q for q in plinth['parts'] if q['kind'] == 'slab' and q['floor'] == 'ground')['plinth'] = True
    gp = pres.presentation(plinth)['groundPlane']
    x0, y0, x1, y1 = pres.slab_bounds(plinth)
    assert gp['size'][0] >= x1 - x0 + 20 and gp['size'][1] >= y1 - y0 + 20


# --------------------------------------------------------------------------------------------------- the top view
@pytest.fixture
def texts(monkeypatch):
    """Every text the top view puts on its axes: (text, fontsize, colour)."""
    import matplotlib
    matplotlib.use('Agg')
    from matplotlib.axes import Axes
    seen: list[tuple] = []
    orig = Axes.text

    def text(self, x, y, s, *a, **kw):
        seen.append((s, kw.get('fontsize'), kw.get('color')))
        return orig(self, x, y, s, *a, **kw)

    monkeypatch.setattr(Axes, 'text', text)
    return seen


def test_the_top_view_draws_treads_and_landings_and_never_a_ceiling(texts):
    m = ref_model()
    png = pic.topview_png(m)
    no_ceiling = copy.deepcopy(m)
    no_ceiling['parts'] = [p for p in m['parts'] if p['kind'] != 'ceiling']
    assert pic.topview_png(no_ceiling) == png, 'a ceiling is never drawn'
    no_treads = copy.deepcopy(no_ceiling)
    no_treads['parts'] = [p for p in no_treads['parts'] if p['kind'] != 'tread']
    assert pic.topview_png(no_treads) != png
    no_landing = copy.deepcopy(no_ceiling)
    no_landing['parts'] = [p for p in no_landing['parts'] if p['kind'] != 'landing']
    assert pic.topview_png(no_landing) != png
    assert pic.STY['tread']['facecolor'] == pic.STY['step']['facecolor'] == '#7cc48a' and pic.STY['landing']['facecolor'] == '#b8dcbc'
    assert 'ceiling' not in pic.ORDER and pic.ORDER.index('tread') < pic.ORDER.index('wall')
    texts.clear()
    pic.topview_png(m)
    shown = [t[0] for t in texts]
    assert 'open: stair well' in shown and 'open: void' in shown
    assert sum(1 for t in texts if t[1] == 8 and t[2] == '#1f4e79') == len(m['rooms']) == 5


def test_the_title_names_treads_only_for_a_model_with_them(monkeypatch):
    titles = []
    from matplotlib.axes import Axes
    orig = Axes.set_title
    monkeypatch.setattr(Axes, 'set_title', lambda self, s, *a, **kw: (titles.append(s), orig(self, s, *a, **kw))[1])
    pic.topview_png(ref_model())
    pic.topview_png(as_v1(ref_model()))
    assert pic.TITLE_TAIL_V2 in titles[0] and 'treads filled' in titles[0]
    assert titles[2].endswith(pic.TITLE_TAIL) and 'treads' not in titles[2]
