"""U4: the presentation of an uploaded version (docs/upload/DESIGN.md U-11.2) and the top view (U-11.4).

* presentation for the bank, suite and house models (and the hotel, mini and a three-floor model) validated by the API's
  checker (`check_file presentation --model`); hostile names stay plain runs; floor buttons for 1, 2, 3 floors; the
  ground plane for a plinth project;
* the camera rule, with the viewer's own camera maths (field of view 40, the fitSlabs target and pan, the panel's right
  edge, read from packages/viewer/src/core/context.ts and ui/css.ts) at 1400 x 880: every slab corner inside the canvas,
  clear of the panel;
* the top view: the bank's bytes equal v2's (should: f084b556503c), one floor and three floors draw (the prototype
  crashed on one), drawing text with `$` is text.
"""
from __future__ import annotations

import copy
import json
import re
from pathlib import Path

import pytest

import test_u4_common as c
from walkthrough_builder.out import pictures
from walkthrough_builder.out import presentation as pr

VIEWER = c.APP / 'packages' / 'viewer' / 'src'
NAMES = ('bank-v2', 'suite', 'house', 'hotel', 'mini')


def three_floor_model() -> dict:
    m = c.model('bank-v2')
    m['floors'].append({**copy.deepcopy(m['floors'][1]), 'key': 'L3', 'name': 'Level 3', 'level': 7.4})
    m['parts'] += [{**copy.deepcopy(p), 'floor': 'L3'} for p in m['parts'] if p['floor'] == 'L2']
    m['furniture'], m['furnitureKinds'] = [], []
    return m


def test_the_viewer_constants_are_still_what_camera_view_uses():
    ctx = (VIEWER / 'core' / 'context.ts').read_text(encoding='utf-8')
    assert re.search(r'new PerspectiveCamera\(40, ', ctx)
    assert 'panelRight = Math.min(right0, width / 2)' in ctx
    assert 'addScaledVector(right, -panelRight / 2 * metresPerPx)' in ctx
    assert "const metresPerPx = 2 * away.length() * Math.tan(camera.fov * Math.PI / 360) / height" in ctx
    css = (VIEWER / 'ui' / 'css.ts').read_text(encoding='utf-8')
    assert re.search(r'\.wtv \.wtv-panel \{ position: absolute; top: 12px; left: 12px; width: min\(330px, calc\(100% - 48px\)\)', css)
    assert 'border: 1px solid var(--line); border-radius: 10px; padding: 12px 14px;' in css
    assert 'box-sizing' not in css.split('.wtv .wtv-panel {')[1].split('}')[0]
    assert pr.PANEL_RIGHT_PX == 372


@pytest.mark.parametrize('name', NAMES)
def test_camera_rule_at_1400_x_880(name):
    m = c.model(name)
    p = pr.presentation(m)
    v = pr.camera_view(m, p)
    assert v['inside'], (name, p['camera'], [xy for xy in v['corners'] if not (v['panelRight'] <= xy[0] <= 1400 and 0 <= xy[1] <= 880)][:4])
    away = p['camera']['away']
    d = away[0] / 0.52
    assert abs(away[1] - 0.53 * d) < 0.002 and abs(away[2] - 0.63 * d) < 0.002          # the design's direction kept
    assert p['camera']['far'] >= 600 and p['camera']['targetY'] == 2.5 and p['camera']['panForPanel'] is True


def test_fields_for_the_bank():
    m = c.model('bank-v2')
    p = pr.presentation(m)
    assert p['documentTitle'] == 'Bank branch' and p['heading'] == 'Bangkok Bank, Sampeng Branch'
    assert p['intro'] == [{'text': 'Built from 2 drawings (I1201 - LEVEL 1 GENERAL ARRANGEMENT.dwg and I1202 - LEVEL 2 GENERAL '
                                   'ARRANGEMENT.dwg): walls from the wall layers, glass from the glass layers, and 39 doors, 7 '
                                   'windows and 3 passages from the openings detector. 185 furniture boxes in 14 kinds. Levels '
                                   '+0.00 / +3.70 m. No AI used.'}]
    assert p['accent'] == '#2f6f8f'
    assert p['legend'] == {'layout': 'inline', 'items': [
        {'colour': '#e3ddd3', 'text': 'Walls and lintels'}, {'colour': '#9cc3d5', 'text': 'Glass'},
        {'colour': '#5d6b74', 'text': 'Glass frames'}, {'colour': '#6f6a75', 'text': 'Railings'},
        {'colour': '#b9c7b4', 'text': 'Stairs'}, {'colour': '#d4d8d2', 'text': 'Floor plates'}]}
    assert p['floorButtons'] == {'all': 'Both floors'}
    assert p['groundPlane'] is None
    assert 'creaseAngle' not in p and 'partStyles' not in p and 'toggles' not in p
    assert '(test)' not in json.dumps(p) and '→' not in json.dumps(p, ensure_ascii=False)


def test_floor_buttons_and_ground_plane():
    one = pr.presentation(c.model('suite'))
    assert 'floorButtons' not in one
    three = pr.presentation(three_floor_model())
    assert three['floorButtons'] == {'all': 'All floors'}
    house = pr.presentation(c.model('house'))
    b = pr.slab_bounds(c.model('house'))
    w, d = b[2] - b[0], b[3] - b[1]
    gp = house['groundPlane']
    assert gp['colour'] == '#dfe3e0'
    for size, ext in zip(gp['size'], (w, d)):
        assert size % 10 == 0 and ext + 20 <= size < ext + 30
    assert {'colour': '#e0a458', 'text': 'Single-line items'} in house['legend']['items']


def test_hostile_names_are_plain_runs():
    m = c.model('mini')
    m['project'] = c.HOSTILE[0] + ' & ' + c.HOSTILE[1]
    m['shortName'] = c.HOSTILE[6]
    m['source'] = [c.HOSTILE[0] + '.dwg', c.HOSTILE[2] + c.HOSTILE[3] + '.dwg']
    p = pr.presentation(m)
    assert p['heading'] == m['project'] and p['documentTitle'] == 'ห้องนอน'
    assert len(p['intro']) == 1 and set(p['intro'][0]) == {'text'}
    assert f"({m['source'][0]} and {m['source'][1]})" in p['intro'][0]['text']


def test_every_presentation_passes_the_api_checker(tmp_path: Path):
    items = []
    models = {n: c.model(n) for n in NAMES}
    models['three'] = three_floor_model()
    hostile = c.model('mini')
    hostile['project'] = c.HOSTILE[0] + ' & ' + c.HOSTILE[1]
    hostile['source'] = [c.HOSTILE[0] + '.dwg']
    models['hostile'] = hostile
    for name, m in models.items():
        mp = tmp_path / f'{name}.model.json'
        mp.write_bytes(json.dumps(m, ensure_ascii=False, separators=(',', ':')).encode('utf-8'))
        pp = tmp_path / f'{name}.presentation.json'
        pp.write_bytes(json.dumps(pr.presentation(m), ensure_ascii=False).encode('utf-8'))
        items.append(('presentation', pp, mp))
        if name in ('three', 'hostile'):
            items.append(('model', mp))
    c.assert_checked(items)


# ------------------------------------------------------------------------------------------------------------ top view
PNG = b'\x89PNG\r\n\x1a\n'


def test_bank_top_view_equals_v2():
    got = pictures.topview_png(c.model('bank-v2'))
    assert c.sha1(got) == c.BANK_TOPVIEW_SHA1
    proto = c.PROJECT / 'bank_test' / 'src' / 'bank_topview.png'
    if proto.exists():
        assert got == proto.read_bytes()


@pytest.mark.parametrize('name', ['suite', 'house', 'hotel', 'three'])
def test_top_view_of_one_two_three_floors(name):
    m = three_floor_model() if name == 'three' else c.model(name)
    if name == 'suite':
        m['rooms'].append({**m['rooms'][0], 'label': 'cost $5 $x$ ' + c.HOSTILE[0]})
        m['floors'][0]['name'] = '$\\frac{1'                       # broken mathtext, if it were read as mathtext
    b = pictures.topview_png(m)
    assert b.startswith(PNG) and len(b) > 20000
