"""Presentation v1 (DESIGN.md 8): the ports of the four generators against the provisional fixtures/presentation/*.json
(exactly, and after filling the defaults as parsePresentation does) and against the prototype pages' facts (the oracle of
8: heading, intro text, legend colours and texts, floor buttons, ticks and their labels, camera start, title)."""
from __future__ import annotations

import copy
import math

import pytest

from kit import FIXTURES, VERSION_IDS, VERSIONS, facts, read_json
from walkthrough_api.checks import presentation_issues
from walkthrough_api.seed.presentation import DEFAULT_LABELS, IntroMarkupError, intro_runs, page_text

DEFAULT_TOGGLES = {'plates': True, 'glass': True, 'rooms': True, 'single': True, 'picture': False}


def stored(seeded, project_id, n):
    d = seeded / 'projects' / project_id / 'versions' / str(n)
    return read_json(d / 'version.json')['presentation'], read_json(d / 'model.json')


def resolve(p: dict, model: dict) -> dict:
    """The defaults of DESIGN.md 8 filled in (as the viewer's parsePresentation / resolvePresentation do)."""
    fb = p.get('floorButtons') or {}
    return {
        'documentTitle': p['documentTitle'], 'heading': p['heading'], 'intro': p['intro'],
        'accent': p.get('accent', '#2f6f8f'), 'legend': p['legend'],
        'floorButtons': {'all': fb.get('all', 'Both floors'),
                         'labels': {f['key']: (fb.get('labels') or {}).get(f['key'], f['name']) for f in model['floors']}},
        'labels': {**DEFAULT_LABELS, **(p.get('labels') or {})},
        'camera': {**p['camera'], 'far': p['camera'].get('far', 600)},
        'partStyles': p.get('partStyles') or {}, 'creaseAngle': p.get('creaseAngle', 25),
        'groundPlane': p.get('groundPlane'), 'toggles': {**DEFAULT_TOGGLES, **(p.get('toggles') or {})},
    }


@pytest.mark.parametrize('key', list(VERSIONS), ids=VERSION_IDS)
def test_port_equals_the_provisional_fixture(seeded, key) -> None:
    p, model = stored(seeded, *key)
    fixture = read_json(FIXTURES / 'presentation' / f"{VERSIONS[key]['facts']}.json")
    assert p == fixture
    assert resolve(p, model) == resolve(fixture, model)
    assert presentation_issues(p, model) == []


def ticks_shown(model: dict) -> list[str]:
    """DESIGN.md 8: Floor plates and Glass always; Room names with rooms; Single-line items with single parts; Plan
    picture when a floor has a picture."""
    kinds = {p['kind'] for p in model['parts']}
    return ['plates', 'glass'] + (['rooms'] if model['rooms'] else []) + (['single'] if 'single' in kinds else []) \
        + (['picture'] if model.get('pictureFrame') else [])


@pytest.mark.parametrize('key', list(VERSIONS), ids=VERSION_IDS)
def test_oracle_the_panel_equals_the_page(seeded, key) -> None:
    p, model = stored(seeded, *key)
    f = facts(VERSIONS[key]['facts'])
    r = resolve(p, model)
    assert r['documentTitle'] == f['title']
    assert r['heading'] == f['heading']
    assert ''.join(run['text'] for run in r['intro']) == f['intro']['text']
    assert ''.join(f"<b>{run['text']}</b>" if run.get('bold') else run['text'] for run in r['intro']) == f['intro']['html']
    assert r['accent'] == f['accent']
    assert r['legend'] == f['legend']
    buttons = [{'key': 'both', 'text': r['floorButtons']['all']}] + \
              [{'key': fl['key'], 'text': r['floorButtons']['labels'][fl['key']]} for fl in model['floors']]
    assert ([b for b in buttons] if len(model['floors']) > 1 else []) == [{'key': b['key'], 'text': b['text']} for b in f['floorButtons']]
    assert [t['id'] for t in f['ticks']] == ticks_shown(model)
    assert [r['labels'][t['id']] for t in f['ticks']] == [t['label'] for t in f['ticks']]
    assert [r['toggles'][t['id']] for t in f['ticks']] == [t['checked'] for t in f['ticks']]
    for t in f['ticks']:
        if t['title']:
            assert r['labels']['pictureTitle'] == t['title']


@pytest.mark.parametrize('key', list(VERSIONS), ids=VERSION_IDS)
def test_oracle_the_camera_start(seeded, key) -> None:
    p, _ = stored(seeded, *key)
    cam = facts(VERSIONS[key]['facts'])['scene']['camera']
    close = lambda a, b: all(math.isclose(x, y, abs_tol=1e-6) for x, y in zip(a, b, strict=True))   # noqa: E731
    assert p['camera']['far'] == cam['far'] and cam['near'] == 0.1
    if p['camera']['kind'] == 'fixed':
        assert close(p['camera']['position'], cam['position']) and close(p['camera']['target'], cam['target'])
    else:                                       # the hotel: target from the slabs, camera = target + away (DESIGN.md 13)
        assert p['camera']['away'] == [21.6, 22.05, 26.1]
        assert close([c - t for c, t in zip(cam['position'], cam['target'], strict=True)], p['camera']['away'])
        assert math.isclose(cam['target'][1], p['camera']['targetY'], abs_tol=1e-9) and p['camera']['panForPanel'] is True


def test_house_extras() -> None:
    p = read_json(FIXTURES / 'presentation' / 'sukhumvit-house.json')
    assert p['creaseAngle'] == 40 and p['groundPlane'] == {'size': [80, 50], 'colour': '#dfe3e0'}
    assert p['partStyles']['glass']['renderOrder'] == 0 and p['partStyles']['pane']['renderOrder'] == 0


# ---------------------------------------------------------------------------------------------------- intro runs, page texts
def test_intro_runs() -> None:
    assert intro_runs('Built from <b>layout.dwg</b>. Done.') == [{'text': 'Built from '}, {'text': 'layout.dwg', 'bold': True},
                                                                  {'text': '. Done.'}]
    assert intro_runs('<b>A</b><b>B</b>') == [{'text': 'A', 'bold': True}, {'text': 'B', 'bold': True}]
    assert intro_runs('Tom &amp; Jerry &lt;3 &#39;x&#x27; &quot;') == [{'text': 'Tom & Jerry <3 \'x\' "'}]
    assert intro_runs('Living & Dining') == [{'text': 'Living & Dining'}]
    assert intro_runs('') == []


@pytest.mark.parametrize('markup', ['a <i>b</i>', '<b>a <b>b</b></b>', 'a</b>', '<b>a', '<img src=x onerror=alert(1)>',
                                    'a &copy; b', 'a &amp b', '<br>', 'x <!-- y -->'])
def test_intro_runs_refuse_other_markup(markup: str) -> None:
    with pytest.raises(IntroMarkupError):
        intro_runs(markup)


def test_page_text() -> None:
    assert page_text('Railings (1.10 m) & the parapet') == 'Railings (1.10 m) & the parapet'
    with pytest.raises(IntroMarkupError):
        page_text('a <span>b</span>')


def test_presentation_check_finds_faults() -> None:
    model = read_json(FIXTURES / 'models' / 'bank-v2.model.json')
    p = copy.deepcopy(read_json(FIXTURES / 'presentation' / 'bank-sampeng-v2.json'))
    assert presentation_issues(p, model) == []
    p['accent'] = 'blue'
    p['legend']['layout'] = 'grid'
    p['floorButtons']['labels'] = {'L9': 'x'}
    p['camera'] = {'kind': 'orbit'}
    p['partStyles'] = {'wall': {'colour': '#ffffff'}}
    p['toggles'] = {'picture': 'yes'}
    p['nope'] = 1
    del p['heading']
    found = {i.path for i in presentation_issues(p, model)}
    assert {'/accent', '/legend/layout', '/floorButtons/labels/L9', '/camera/kind', '/partStyles/wall/colour',
            '/toggles/picture', '/nope', ''} <= found
