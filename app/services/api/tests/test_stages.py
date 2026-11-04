"""Replay data v1 (DESIGN.md 7): the bank's stages copied, the suite's renamed, the house's built from house3d_stages.json,
and the oracle of 7.4: with the default Build settings filled in, every caption, fact, layer row and step title equals,
character for character, what the prototype page showed (fixtures/prototype/*.json) - for the house, the bank and the
suite. Also the JavaScript number formatting and the placeholder filling the captions rely on."""
from __future__ import annotations

import copy

import pytest

from kit import FIXTURES, PROTOTYPES, facts, read_json
from walkthrough_api.checks import STEP_KEYS, replay_issues
from walkthrough_api.jsfmt import fill_caption, js_locale, js_pct, js_round, js_str, js_to_fixed, model_settings
from walkthrough_api.seed import stages

DEFAULT_STEP_TITLES = {'read': 'Read the drawing', 'sort': 'Sort the layers', 'align': 'Line up the levels',
                       'pair': 'Find the wall faces', 'merge': 'Merge, cut the openings', 'raise': 'Raise the walls',
                       'finish': 'Floors, stairs, room names'}            # DESIGN.md 7.2
DEFAULT_LAYERS_TITLE = 'How the drawing was read'
REPLAYS = {('bank-sampeng', 1): 'bank-sampeng-v1', ('bank-sampeng', 2): 'bank-sampeng-v2',
           ('presidential-suite', 1): 'presidential-suite', ('sukhumvit-house', 1): 'sukhumvit-house'}


def stored(seeded, project_id, n):
    d = seeded / 'projects' / project_id / 'versions' / str(n)
    return read_json(d / 'stages.json'), read_json(d / 'model.json')


def intro_title(s: dict) -> str:
    """DESIGN.md 7.2: source.files joined with ' + ', else source.file, else ''."""
    src = s.get('source') or {}
    if s.get('introTitle') is not None:
        return s['introTitle']
    if src.get('files'):
        return ' + '.join(src['files'])
    return src.get('file') or ''


@pytest.mark.parametrize('key', list(REPLAYS), ids=lambda k: f'{k[0]}-v{k[1]}')
def test_oracle_the_card_and_the_captions_equal_the_page(seeded, key) -> None:
    s, model = stored(seeded, *key)
    card = facts(REPLAYS[key])['card']
    settings = model_settings(model)
    assert {k: (v['level'], round(v['height'], 9)) for k, v in settings.items()} == \
           {k: (v['level'], round(v['height'], 9)) for k, v in card['settings'].items()}
    assert [f'{v:.2f}' for f in model['floors'] for v in (f['level'], f['wallHeight'])] == [i['value'] for i in card['inputs']]
    assert intro_title(s) == card['introTitle']
    assert s['intro'] == card['facts']
    assert s['layers'] == card['layers']
    assert s.get('layersTitle', DEFAULT_LAYERS_TITLE) == card['layersTitle']
    titles = {**DEFAULT_STEP_TITLES, **(s.get('stepTitles') or {})}
    assert [titles[k] for k in STEP_KEYS] == [step['title'] for step in card['steps']]
    for step in card['steps']:
        assert fill_caption(s['captions'][step['key']], settings) == step['caption'], step['key']
    assert replay_issues(s, model) == []


def test_hotel_has_no_replay(seeded) -> None:
    d = seeded / 'projects' / 'hotel-lobby' / 'versions' / '1'
    assert not (d / 'stages.json').exists() and read_json(d / 'version.json')['hasStages'] is False
    assert facts('hotel-lobby')['card'] is None


@pytest.mark.parametrize('n, fixture', [(1, 'bank-v1'), (2, 'bank-v2')])
def test_bank_stages_are_copied_byte_for_byte(seeded, n, fixture) -> None:
    got = (seeded / 'projects' / 'bank-sampeng' / 'versions' / str(n) / 'stages.json').read_bytes()
    folder = 'bank_test/previous_before_fix_round_2026-10-27' if n == 1 else 'bank_test'
    assert got == (PROTOTYPES / folder / 'src' / 'bank_stages.json').read_bytes()
    assert got == (FIXTURES / 'stages' / f'{fixture}.stages.json').read_bytes()


def test_suite_conversion() -> None:
    S = read_json(PROTOTYPES / 'presidential_test' / 'src' / 'pres2_stages.json')
    s = stages.suite(S)
    assert 'floor' not in s and s['floors'] == {'suite': S['floor']}
    assert s['captions']['align'] == S['captions']['align'].replace('{level}', '{suitelevel}')
    assert s['captions']['raise'] == S['captions']['raise'].replace('{height}', '{suiteheight}')
    assert '{level}' not in str(s['captions']) and '{height}' not in str(s['captions'])
    assert {k: v for k, v in s['captions'].items() if k not in ('align', 'raise')} == \
           {k: v for k, v in S['captions'].items() if k not in ('align', 'raise')}
    assert s['stepTitles'] == stages.SUITE_STEP_TITLES and s['colors'] == stages.SUITE_COLORS
    assert 'layersTitle' not in s
    for k in ('source', 'panelIntro', 'intro', 'layers', 'stats'):
        assert s[k] == S[k]


def test_suite_page_replaced_only_the_first_placeholder() -> None:
    S = {'floor': {}, 'captions': {k: '' for k in STEP_KEYS}}
    S['captions']['align'] = 'at {level} m, and {level}'
    S['captions']['raise'] = '{height} / {height}'
    s = stages.suite(S)
    assert s['captions']['align'] == 'at {suitelevel} m, and {level}'      # as String.prototype.replace did on the page
    assert fill_caption(s['captions']['align'], {'suite': {'level': 0.0, 'height': 3.0}}) == 'at 0.00 m, and {level}'


@pytest.fixture(scope='module')
def house():
    root = PROTOTYPES / 'cad_test' / 'src'
    S, D, FH = (read_json(root / n) for n in ('house3d_stages.json', 'house3d_merged.json', 'furniture_house.json'))
    return S, D, FH, stages.house(S, D, FH, ['ground', 'upper'])


def test_house_lines_pieces_and_rings(house) -> None:
    S, D, _, s = house
    for k in ('ground', 'upper'):
        src, got = S['floors'][k], s['floors'][k]
        assert got['sheet'] == src['sheet'] and set(got) == {'sheet', 'lines', 'pieces', 'rings'}
        assert len(got['lines']['noise']) == min(len(src['lines']['noise']), 24000) == 24000
        for cat, a in src['lines'].items():
            want = a[:24000] if cat == 'noise' else a
            assert got['lines'][cat] == [round(v, 2) for v in want], cat
        assert got['pieces'] == {c: [round(v, 2) for v in q] for c, q in src['pairs'].items()}
        assert got['rings']['wall'] == D['solids'][f'{k}:wall']
        panes = [{'o': p['o'], 'h': p['h']} for p in D['pieces'][k] if p['kind'] == 'pane']
        assert got['rings']['glass'] == D['solids'][f'{k}:glass'] + panes and panes


def test_house_texts(house) -> None:
    S, _, _, s = house
    assert s['source'] == {**S['source'], 'layersUsed': 38}
    assert s['layersTitle'] == 'Layers found'
    assert s['stepTitles'] == stages.HOUSE_STEP_TITLES and s['colors'] == stages.HOUSE_COLORS
    assert s['layers'][0] == ['Walls', 'COL, WALL, A-WALL (incl. 1 from linked drawings)']
    assert s['layers'][-1] == ['Ignored', '26 other layers: furniture, floor patterns, grid, dimensions, labels']
    assert s['stats'] == S['stats'] and 'panelIntro' not in s
    assert '{groundlevel+}' in s['captions']['align'] and '{upperheight}' in s['captions']['raise']


def test_house_without_openings_or_doors_says_so(house) -> None:
    S, D, FH, _ = house
    S2 = copy.deepcopy(S)
    for f in S2['stats']['floors'].values():
        f.pop('openings')
        f['kept'].pop('door')
    S2['stats']['layers'].pop('door')
    s = stages.house(S2, D, FH, ['ground', 'upper'])
    assert s['captions']['merge'].endswith('one solid each, no seams.')
    assert s['captions']['raise'] == 'The walls rise to their height: ground floor {groundheight} m, upper floor {upperheight} m.'
    assert 'lines ignored: furniture, floor patterns, doors, grid and dimensions.' in s['captions']['sort']
    assert s['captions']['finish'].endswith('11 glass runs. The real build takes seconds; this replay slows it down so you can follow it.')
    assert s['layers'][-1][1].endswith('furniture, floor patterns, doors, grid, dimensions, labels')
    s3 = stages.house(S, D, {}, ['ground', 'upper'])
    assert s3['captions']['finish'].startswith('Floor plates and stairs go in. Done:')


def test_layer_list() -> None:
    assert stages.layer_list(['A', 'XR_L1$0$A', 'X$0$B', 'C']) == 'A, B, C (incl. 2 from linked drawings)'
    assert stages.layer_list(['A', 'A']) == 'A'


def test_replay_check_finds_faults(seeded) -> None:
    s, model = stored(seeded, 'bank-sampeng', 2)
    bad = copy.deepcopy(s)
    del bad['captions']['finish']
    bad['floors']['L1']['lines']['wall'] = [0, 0, 1]
    bad['floors']['L1']['pieces']['wall'] = [0] * 12
    bad['floors']['L9'] = bad['floors']['L2']
    bad['colors'] = {'wall': 'red'}
    bad['extra'] = 1
    found = {i.path for i in replay_issues(bad, model)}
    assert {'/captions', '/floors/L1/lines/wall', '/floors/L1/pieces/wall', '/floors/L9', '/colors/wall', '/extra'} <= found
    missing = copy.deepcopy(s)
    del missing['floors']['L2']
    assert '/floors' in {i.path for i in replay_issues(missing, model)}


# ---------------------------------------------------------------------------------------------------- JavaScript formatting
@pytest.mark.parametrize('x, want', [(2.5, 3), (-2.5, -2), (0.5, 1), (-0.5, 0), (0.49999999999999994, 0), (94.39999999999999, 94),
                                     (1.5, 2), (-1.5, -1), (7, 7)])
def test_js_round(x, want) -> None:
    assert js_round(x) == want


@pytest.mark.parametrize('x, d, want', [(0.125, 2, '0.13'), (1.005, 2, '1.00'), (74.021, 2, '74.02'), (3.500000000000001, 2, '3.50'),
                                        (-0.0, 2, '0.00'), (-0.001, 2, '-0.00'), (2.5, 0, '3'), (-2.5, 0, '-3'), (0.9, 2, '0.90'),
                                        (12345.678, 1, '12345.7')])
def test_js_to_fixed(x, d, want) -> None:
    assert js_to_fixed(x, d) == want


def test_js_exponent_forms_are_refused_not_guessed() -> None:
    with pytest.raises(ValueError):
        js_to_fixed(1e21, 2)          # JavaScript prints '1e+21': never needed here, so not emulated
    with pytest.raises(ValueError):
        js_str(1e-7)


def test_js_locale_pct_str() -> None:
    assert js_locale(30644) == '30,644' and js_locale(1234567.5) == '1,234,568' and js_locale(-1234) == '-1,234'
    assert js_pct(0.944) == '94%' and js_pct(0.98) == '98%' and js_pct(0.005) == '1%'
    assert js_str(59) == '59' and js_str(3.0) == '3' and js_str(2.5) == '2.5' and js_str(True) == 'true'


def test_fill_caption_forms() -> None:
    s = {'ground': {'level': 0.9, 'height': 3.9}, 'L1': {'level': -0.5, 'height': 3.0}, 'sub_level': {'level': 1.0, 'height': 2.0}}
    assert fill_caption('{groundlevel} {groundheight} {groundlevel+}', s) == '0.90 3.90 +0.90'
    assert fill_caption('{L1level+} / {L1height}', s) == '-0.50 / 3.00'
    assert fill_caption('{L9level} {level} {groundwidth}', s) == '{L9level} {level} {groundwidth}'      # unknown: kept
    assert fill_caption('{sub_levellevel}', s) == '1.00'
    assert fill_caption('{grøundlevel}', {'grøund': {'level': 1.0, 'height': 1.0}}) == '{grøundlevel}'     # \w is ASCII
