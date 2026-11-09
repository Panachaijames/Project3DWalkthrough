"""U2: the settings proposal (docs/upload/DESIGN.md U-3.3, U-7.4, U-9, U-10.4; ACCEPTANCE 2.1 U2, A-8) on DrawingReads
made here: floors from sources or plan areas, units and their confirmation, layers from the suggestions, what the spec's
revision-0 settings carry, a new version of a seeded project (keys, names, levels, naming and offset from its latest
model), each proposal checked by the API's check_file and by the rules of U-13.2. The real drawings' proposals are in
test_u2_reference.py (heavy)."""
from __future__ import annotations

import json
import re

import pytest

import kit
import test_u2_kit as K
from walkthrough_builder import propose as P
from walkthrough_builder import roles

SHA = ['1' * 40, '2' * 40, '3' * 40]


def units(used='mm', verdict='agree', declared='mm', note=''):
    return {'declared': declared, 'votes': {'mm': 5, 'cm': 0, 'm': 0, 'in': 0, 'ft': 0}, 'dimensionMedian': None,
            'used': used, 'verdict': verdict, 'note': note or f'{verdict} note'}


def area(i, bbox, looks):
    return {'id': f'a{i}', 'bbox': bbox, 'items': 100, 'wallItems': 10, 'looks': looks}


def drawing(sha, areas=(), u=None, blocks=()):
    return {'source': {'sha1': sha, 'name': f'{sha[:4]}.dwg'}, 'units': u or units(), 'areas': list(areas),
            'blocks': [{'name': b, 'family': b, 'inserts': 1, 'byLayer': {}, 'mirrored': 0, 'maxDepth': 0,
                        'attribTags': []} for b in blocks], 'layers': []}


def spec(shas, settings=None, project_id='p-test', office=None):
    return {'projectId': project_id, 'office': office, 'settings': settings,
            'sources': [{'sha1': s, 'name': f'File {i + 1}.dwg', 'kind': 'dwg', 'path': f'C:/x/{s}', 'units': None}
                        for i, s in enumerate(shas)]}


SUG = {'format': 'layer-suggestions/1', 'office': None,
       'layers': {'B-WALL': {'role': 'wall', 'from': 'name', 'evidence': ['x']},
                  'A-DOOR': {'role': 'door', 'from': 'name', 'evidence': ['x']},
                  'ODD': {'role': 'not-a-role', 'from': 'default', 'evidence': ['x']}}}

KEY_RE = re.compile(r'^[A-Za-z0-9_]{1,32}$')


def rule_issues(s: dict) -> list[str]:
    """U-13.2's settings rules that settings_issues (U5) will check, here so the proposal is known to pass them."""
    out = []
    keys = [f['key'] for f in s['floors']]
    if len(set(keys)) != len(keys) or not all(KEY_RE.match(k) for k in keys):
        out.append(f'floor keys {keys}')
    levels = [f['level'] for f in s['floors']]
    if any(b <= a for a, b in zip(levels, levels[1:])):
        out.append(f'levels {levels}')
    shas = {x['sha1'] for x in s['sources']}
    for f in s['floors']:
        if f['source'] not in shas:
            out.append(f'floor {f["key"]} source')
        if f['area']['kind'] == 'box':
            x0, y0, x1, y1 = f['area']['bbox']
            if not (x0 < x1 and y0 < y1):
                out.append(f'floor {f["key"]} box')
        if not 0.05 <= f['wallHeight'] <= 50:
            out.append(f'floor {f["key"]} wall height')
    pr = s['project']
    if not (P.PHOTO_RE.match(pr['photoName']) and P.PREFIX_RE.match(pr['maxPrefix']) and P.MS_RE.match(pr['maxFileName'])):
        out.append(f'naming {pr}')
    if any(x['units'] is None for x in s['sources']):
        out.append('units null')
    if any(r not in roles.STAFF_ROLES for r in s['layers'].values()):
        out.append('roles')
    if s['office'] is not None and not P.OFFICE_RE.match(s['office']):
        out.append('office')
    return out


def check(s: dict) -> dict:
    assert rule_issues(s) == []
    json.dumps(s, allow_nan=False)
    return s


def test_several_sources_one_floor_each() -> None:
    drs = [drawing(SHA[0]), drawing(SHA[1], u=units('mm', 'votes-win', 'in'))]
    s = check(P.propose_settings(spec(SHA[:2]), drs, SUG, [], None))
    assert [(f['key'], f['name'], f['source'], f['area'], f['level'], f['wallHeight'], f['align'])
            for f in s['floors']] == [('L1', 'Level 1', SHA[0], {'kind': 'wholeFile'}, 0.0, 3.0, {'method': 'auto'}),
                                      ('L2', 'Level 2', SHA[1], {'kind': 'wholeFile'}, 3.0, 3.0, {'method': 'auto'})]
    assert [(x['sha1'], x['name'], x['units'], x['unitsConfirmed']) for x in s['sources']] == [
        (SHA[0], 'File 1.dwg', 'mm', True), (SHA[1], 'File 2.dwg', 'mm', False)]
    assert s['layers'] == {'A-DOOR': 'door', 'B-WALL': 'wall', 'ODD': 'other'}
    assert all(f[k] is None for f in s['floors'] for k in ('slabThickness', 'doorHead', 'windowSill', 'windowHead'))
    assert s['defaults'] == P.DEFAULTS and s['furniture'] == P.FURNITURE and s['options'] == P.OPTIONS
    assert s['fixes'] == P.FIXES and s['vocabulary'] == {} and s['format'] == 'build-settings/1'


@pytest.mark.parametrize('verdict, confirmed', [('agree', True), ('declared-only', True), ('votes-win', False),
                                                ('unknown', False)])
def test_units_confirmed_by_the_readers_verdict(verdict, confirmed) -> None:
    s = P.propose_settings(spec(SHA[:1]), [drawing(SHA[0], u=units('cm', verdict))], SUG, [], None)
    assert (s['sources'][0]['units'], s['sources'][0]['unitsConfirmed']) == ('cm', confirmed)


def test_one_sheet_with_several_plans_one_floor_per_plan() -> None:
    dr = drawing(SHA[0], areas=[area(1, [3, 38, 48, 62], 'elevation'), area(2, [0, 5, 57, 36], 'plan'),
                                area(3, [73, 18, 78, 25], 'other'), area(4, [77, 5, 129, 36], 'plan')])
    s = check(P.propose_settings(spec(SHA[:1]), [dr], SUG, [], None))
    assert [(f['key'], f['area'], f['level']) for f in s['floors']] == [
        ('L1', {'kind': 'box', 'bbox': [0.0, 5.0, 57.0, 36.0], 'pad': 0.5, 'match': 'all'}, 0.0),
        ('L2', {'kind': 'box', 'bbox': [77.0, 5.0, 129.0, 36.0], 'pad': 0.5, 'match': 'all'}, 3.0)]
    one = drawing(SHA[0], areas=[area(1, [0, 0, 10, 10], 'plan'), area(2, [20, 0, 30, 10], 'elevation')])
    assert P.propose_settings(spec(SHA[:1]), [one], SUG, [], None)['floors'][0]['area'] == {'kind': 'wholeFile'}
    notes = P.notes(s, [dr])
    assert notes[0].startswith('The floors are a guess: 2 plans were found side by side on one sheet')


def test_what_the_spec_settings_carry() -> None:
    base = {'format': 'build-settings/1', 'office': 'dwp-revit',
            'project': {'name': 'Bangkok Bank & Co', 'shortName': 'Bank', 'projectNo': '26-0216', 'photoName': 'Bank-1',
                        'maxPrefix': 'BK', 'maxFileName': 'Bank_1.ms', 'exportedFrom': 'Revit'},
            'sources': [], 'layers': {}, 'floors': [],
            'defaults': {'doorHead': 2.4, 'windowSill': 0, 'windowHead': 2.1, 'railingHeight': 1.1, 'slabThickness': 0.25,
                         'singleLineHeight': 1.0},
            'furniture': dict(P.FURNITURE, words={'seat': ['Fritz-Hansen']}),
            'vocabulary': {'stairUp': 'UP'}, 'options': dict(P.OPTIONS, offset=[1.212, 0.348]),
            'fixes': {'setAside': [], 'openings': [], 'outlineEdges': []}}
    s = check(P.propose_settings(spec(SHA[:1], base), [drawing(SHA[0])], SUG, [], None))
    assert s['office'] == 'dwp-revit' and s['project'] == base['project']
    assert s['defaults']['doorHead'] == 2.4 and s['defaults']['windowSill'] == 0.0
    assert isinstance(s['defaults']['windowSill'], float)                     # every number a float (U-10.4)
    assert s['furniture']['words'] == {'seat': ['Fritz-Hansen']} and s['vocabulary'] == {'stairUp': 'UP'}
    assert s['options']['offset'] == [1.212, 0.348]
    # the office from the spec's memory when the settings have none
    s2 = P.propose_settings(spec(SHA[:1], dict(base, office=None), office={'id': 'east-office'}), [drawing(SHA[0])],
                            SUG, [], None)
    assert s2['office'] == 'east-office'
    # a part with keys missing keeps what it has and takes the defaults for the rest; unknown keys are not carried
    part = dict(base, options={'offset': [5.0, 6.0], 'plinth': 'off', 'colour': 'red'}, furniture={'minSize': 0.1})
    s3 = check(P.propose_settings(spec(SHA[:1], part), [drawing(SHA[0])], SUG, [], None))
    assert s3['options'] == dict(P.OPTIONS, offset=[5.0, 6.0], plinth='off')
    assert s3['furniture'] == dict(P.FURNITURE, minSize=0.1)


def test_a_project_with_no_naming_gets_one_derived() -> None:
    s = check(P.propose_settings(spec(SHA[:1], project_id='tower-29'), [drawing(SHA[0])], SUG, [], None))
    assert s['project']['name'] == 'tower-29' and s['project']['maxFileName'] == 'tower_29.ms'
    assert P.derived_naming('Sukhumvit house', 'Test Sukhumvit Residence') == {
        'photoName': 'Sukhumvit-house', 'maxPrefix': 'SH', 'maxFileName': 'Test_Sukhumvit_Residence.ms'}
    thai = P.derived_naming('บ้านสุขุมวิท', 'บ้านสุขุมวิท')
    assert thai == {'photoName': 'Project', 'maxPrefix': 'XX', 'maxFileName': 'Project.ms'}
    assert P.derived_naming('Q', 'Q')['maxPrefix'] == 'QX'


def test_revit_exports_are_told_by_their_block_names() -> None:
    revit = [f'Chair - Mollie-{100000 + i}-Level 1' for i in range(25)] + ['BA', 'Grid - CIRCLE']
    s = P.propose_settings(spec(SHA[:1]), [drawing(SHA[0], blocks=revit)], SUG, [], None)
    assert s['project']['exportedFrom'] == 'Revit'
    s = P.propose_settings(spec(SHA[:1]), [drawing(SHA[0], blocks=['_GRID', 'DOOR-90'] * 20)], SUG, [], None)
    assert s['project']['exportedFrom'] is None


def model(name: str) -> dict:
    return json.loads((kit.FIXTURES / 'models' / f'{name}.model.json').read_text(encoding='utf-8'))


def test_new_version_of_a_seeded_bank_keeps_its_keys_naming_and_offset() -> None:
    drs = [drawing(SHA[0]), drawing(SHA[1])]
    s = check(P.propose_settings(spec(SHA[:2], project_id='bank-sampeng'), drs, SUG, [],
                                 {'model': model('bank-v2'), 'msName': 'Bangkok_Bank_Sampeng.ms'}))
    assert [(f['key'], f['name'], f['level'], f['wallHeight']) for f in s['floors']] == [
        ('L1', 'Level 1', 0.0, 3.7), ('L2', 'Level 2', 3.7, 3.7)]
    assert s['project'] == {'name': 'Bangkok Bank, Sampeng Branch', 'shortName': 'Bank branch', 'projectNo': '26-0216',
                            'photoName': 'BangkokBank-Sampeng', 'maxPrefix': 'BB',
                            'maxFileName': 'Bangkok_Bank_Sampeng.ms', 'exportedFrom': None}
    assert s['options']['offset'] == [1.212, 0.348] and s['office'] is None


def test_new_version_of_the_seeded_house_on_one_sheet() -> None:
    dr = drawing(SHA[0], areas=[area(1, [0, 5, 57, 36], 'plan'), area(2, [77, 5, 129, 36], 'plan')],
                 u=units('mm', 'votes-win', 'in'))
    s = check(P.propose_settings(spec(SHA[:1], project_id='sukhumvit-house'), [dr], SUG, [],
                                 {'model': model('house'), 'msName': 'Sukhumvit_House.ms'}))
    assert [(f['key'], f['name'], f['level'], f['wallHeight'], f['area']['kind']) for f in s['floors']] == [
        ('ground', 'Ground floor', 0.9, 3.9, 'box'), ('upper', 'Upper floor', 4.8, 3.5, 'box')]
    assert s['options']['offset'] == [30.8095, 16.3425]
    assert (s['project']['photoName'], s['project']['maxPrefix'], s['project']['maxFileName']) == (
        'Sukhumvit', 'SK', 'Sukhumvit_House.ms')


def test_more_floors_than_the_latest_version_had() -> None:
    drs = [drawing(SHA[0]), drawing(SHA[1]), drawing(SHA[2])]
    s = check(P.propose_settings(spec(SHA), drs, SUG, [], {'model': model('suite'), 'msName': 'odd name.ms'}))
    assert [(f['key'], f['level']) for f in s['floors']] == [('suite', 0.0), ('L1', 3.0), ('L2', 6.0)]
    assert s['project']['maxFileName'] != 'odd name.ms'                    # not a valid stored name: derived instead


def test_proposals_pass_the_apis_record_check(tmp_path) -> None:
    files = []
    cases = {
        'two': P.propose_settings(spec(SHA[:2]), [drawing(SHA[0]), drawing(SHA[1])], SUG, [], None),
        'house': P.propose_settings(spec(SHA[:1]), [drawing(SHA[0], areas=[area(1, [0, 5, 57, 36], 'plan'),
                                                                          area(2, [77, 5, 129, 36], 'plan')])],
                                    SUG, [], {'model': model('house'), 'msName': 'Sukhumvit_House.ms'}),
        'bank': P.propose_settings(spec(SHA[:2]), [drawing(SHA[0]), drawing(SHA[1])], SUG, [],
                                   {'model': model('bank-v2'), 'msName': 'Bangkok_Bank_Sampeng.ms'}),
    }
    for name, s in cases.items():
        p = tmp_path / f'{name}.json'
        p.write_text(json.dumps(s, ensure_ascii=False), encoding='utf-8')
        files.append(('settings', p))
    assert K.api_issues(files) == {str(p): [] for _k, p in files}


def test_the_prepare_path_through_contracts(tmp_path) -> None:
    """U1 calls U2 only through contracts.py: read each source, suggest over them, propose (U-3.1's prepare)."""
    from walkthrough_builder import contracts
    dxf = K.small_dxf(tmp_path / 'small.dxf')
    lines: list[str] = []
    res = contracts.read_source(dxf, None, tmp_path / 'read', source={'sha1': SHA[0], 'name': 'Small.dxf'},
                                log=lines.append)
    dr = json.loads((tmp_path / 'read' / 'drawing.json').read_text(encoding='utf-8'))
    assert res['drawing'] == str(tmp_path / 'read' / 'drawing.json') and lines
    sug = contracts.suggest([dr], None)
    s = contracts.propose_settings(spec(SHA[:1]) | {'sources': [{'sha1': SHA[0], 'name': 'Small.dxf', 'kind': 'dxf',
                                                                 'path': str(dxf), 'units': None}]},
                                   [dr], sug, [], None)
    check(s)
    assert s['sources'] == [{'sha1': SHA[0], 'name': 'Small.dxf', 'kind': 'dxf', 'units': 'mm',
                             'unitsConfirmed': True}]
    assert {n: s['layers'][n] for n in ('A-WALL', 'A-WALL-PATT', 'A-GLAZ', 'A-DOOR', 'S-STRS', 'I-FURN', 'S-GRID-IDEN')} \
        == {'A-WALL': 'wall', 'A-WALL-PATT': 'wall', 'A-GLAZ': 'window', 'A-DOOR': 'door', 'S-STRS': 'stair',
            'I-FURN': 'furniture', 'S-GRID-IDEN': 'grid'}
    assert s['floors'] == [P._floor('L1', 'Level 1', SHA[0], {'kind': 'wholeFile'}, 0.0, 3.0)]
    sp, pp = tmp_path / 'suggestions.json', tmp_path / 'proposed-settings.json'
    sp.write_text(json.dumps(sug, ensure_ascii=False), encoding='utf-8')
    pp.write_text(json.dumps(s, ensure_ascii=False), encoding='utf-8')
    assert K.api_issues([('suggestions', sp), ('settings', pp)]) == {str(sp): [], str(pp): []}
