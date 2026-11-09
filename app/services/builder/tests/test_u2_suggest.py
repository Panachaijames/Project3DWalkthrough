"""U2: layer role suggestions (docs/upload/DESIGN.md U-8.3, U-8.4; ACCEPTANCE 2.1 U2, A-8) on DrawingReads made here:
the name table in its order, the conditions, the contents rules, a name the contents contradict, the office memory
(exact and similar names), counts added up across sources, and the output checked by the API's check_file. The real
drawings' suggestions are in test_u2_reference.py (heavy)."""
from __future__ import annotations

import json

import pytest

import test_u2_kit as K
from walkthrough_builder import suggest as S


def layer(name: str, **kw) -> dict:
    row = {'name': name, 'normalised': name.upper(), 'state': {'on': True, 'frozen': False, 'locked': False, 'plot': True},
           'linetype': 'Continuous', 'colour': 7, 'items': 0, 'byType': {}, 'inBlocks': 0, 'closedShapes': 0,
           'solidHatches': 0, 'hatchPatterns': {}, 'length': 0.0, 'doorArcs': 0, 'doorArcsWithLeaf': 0, 'texts': 0,
           'inserts': 0, 'topBlocks': [], 'linetypes': {}, 'pairs': {'glassLike': 0, 'wallLike': 0}, 'extents': None}
    for k, v in kw.items():
        row[k] = v
    if 'items' not in kw:
        row['items'] = sum(v for t, v in row['byType'].items() if t != 'DIMENSION')
    return row


def drawing(layers: list[dict], texts=(), levels=(), grid=()) -> dict:
    return {'layers': layers, 'texts': [{'layer': la, 'x': 0.0, 'y': 0.0, 'height': None, 'text': t, 'kind': 'TEXT',
                                         'tag': None, 'block': None} for la, t in texts],
            'levelTags': [{'x': 0.0, 'y': 0.0, 'value': 1.0, 'text': t, 'layer': la, 'source': 'text', 'label': None}
                          for la, t in levels],
            'gridLabels': [{'text': t, 'x': 0.0, 'y': 0.0, 'layer': la, 'block': None, 'direction': None, 'line': None}
                           for la, t in grid]}


def one(name: str, office=None, **kw) -> dict:
    return S.suggest([drawing([layer(name, **kw)])], office)['layers'][name]


@pytest.mark.parametrize('name, role', [
    ('A-WALL', 'wall'), ('A-WALL-PATT', 'wall'), ('XR_L44 Plan$0$A-WALL', 'wall'), ('WALL', 'wall'), ('XR-WALL', 'wall'),
    ('A-1.Netcat - tuong', 'wall'),
    ('S-COLS', 'column'), ('COL', 'column'), ('S-COL', 'column'), ('A.Cot 1', 'column'), ('KC COT 2', 'column'),
    ('A-GLAZ', 'window'), ('a-glaz', 'window'),
    ('A-GLAZ-CURT', 'glass'), ('A-GLAZ-CWMG', 'glass'), ('WALL-GL', 'glass'), ('GLASS', 'glass'), ('KINH', 'glass'),
    ('A-WIND', 'window'), ('WIN', 'window'), ('X-WINDOW-1', 'window'),
    ('A-DOOR-IDEN', 'other'), ('A-GLAZ-IDEN', 'other'), ('A-WIND-IDEN', 'other'),
    ('A-DOOR', 'door'), ('A-DOOR-GLAZ', 'door'), ('DOOR', 'door'), ('XR_L44$0$I-DOOR', 'door'), ('D-JAMB', 'door'),
    ('DSYM', 'door'), ('Xr_SDC_DD_ID-PRS-ID wall$0$DA-DOOR-WIND', 'door'),
    ('A_Grill', 'screen'), ('W_Grill', 'screen'), ('LOUVRE', 'screen'),
    ('S-STRS', 'stair'), ('STAIR', 'stair'), ('CAU THANG', 'stair'),
    ('S-STRS-MBND', 'stair-above'), ('STAIR ABOVE', 'stair-above'),
    ('A-FLOR-HRAL', 'railing'), ('HANDRAIL', 'railing'), ('KT-Lancan', 'railing'), ('BALUSTRADE', 'railing'),
    ('I-FURN', 'furniture'), ('XR_L44$0$I-FURN', 'furniture'), ('FUR', 'furniture'), ('Q-CASE-HDLN', 'furniture'),
    ('Q-SPCQ', 'furniture'), ('P-SANR-FIXT', 'furniture'), ('Xr_SDC_DD_ID-PRS-ID wall$0$DA-SANR', 'furniture'),
    ('FIXT', 'furniture'), ('L-PLNT', 'furniture'), ('A-2.Noi That', 'furniture'), ('A-4. Cay', 'furniture'),
    ('A-AREA-IDEN', 'room-name'), ('ROOM NAME', 'room-name'), ('RNAME', 'room-name'), ('A-Text', 'room-name'),
    ('X-AREA-IDEN', 'room-name'),
    ('S-GRID', 'grid'), ('S-GRID-IDEN', 'grid'), ('GRID-01', 'grid'), ('DA-GRID-NAME', 'grid'), ('AXIS', 'grid'),
    ('E-LITE-EQPM', 'light'), ('DA-LEVEL-LIGHT', 'light'),
    ('A-ANNO-DIMS', 'ignore'), ('DIM25', 'ignore'), ('G-ANNO-TEXT', 'ignore'), ('HATCH', 'ignore'),
    ('FLOOR-PATTERN', 'ignore'), ('G-ANNO-TTLB', 'ignore'), ('TITLE', 'ignore'), ('VIEWPORTS', 'ignore'),
    ('A-FLOR', 'other'), ('A-DETL', 'other'), ('A-AREA', 'other'), ('Defpoints', 'other'), ('LEVEL', 'other'),
])
def test_the_name_table(name, role) -> None:
    got = one(name)
    assert got['role'] == role
    assert got['from'] == ('default' if role == 'other' and name not in ('A-DOOR-IDEN', 'A-GLAZ-IDEN', 'A-WIND-IDEN')
                           else 'name')
    assert got['evidence'] and all(isinstance(e, str) and e for e in got['evidence'])


def test_name_evidence_reads_as_a_sentence() -> None:
    assert one('A-WALL')['evidence'] == ['named like a wall layer (A-WALL*)']
    assert one('A-ANNO-DIMS')['evidence'] == ['named like an ignore layer (*DIM*)']
    assert one('A-DOOR-IDEN')['evidence'] == ['named like a door or window tag layer (A-DOOR-IDEN)']
    texts = S.suggest([drawing([layer('G-ANNO-TEXT', byType={'TEXT': 3}, texts=3)],
                               texts=[('G-ANNO-TEXT', t) for t in ('BANK HALL', 'LOBBY', 'STORE')])], None)
    assert texts['layers']['G-ANNO-TEXT']['evidence'] == [
        'named like an ignore layer (*ANNO*)', 'named like an ignore layer, but only texts (3), such as LOBBY, STORE, '
                                               'BANK HALL']


def test_conditions_on_the_contents() -> None:
    outlines = dict(closedShapes=4, length=40.0, byType={'LWPOLYLINE': 4})
    assert one('A-AREA', **outlines)['role'] == 'room-outline'
    assert one('DEFPOINTS', **outlines)['role'] == 'room-outline'
    assert one('A-AREA', closedShapes=2, length=40.0, byType={'LWPOLYLINE': 2})['role'] == 'other'
    tagged = S.suggest([drawing([layer('LEVEL MARKS', byType={'TEXT': 3}, texts=3)],
                                levels=[('LEVEL MARKS', '+0.90'), ('LEVEL MARKS', '+4.80')])], None)
    assert tagged['layers']['LEVEL MARKS']['role'] == 'level'
    assert tagged['layers']['LEVEL MARKS']['from'] == 'name'


def test_a_name_hit_the_contents_contradict_keeps_the_name_with_evidence() -> None:
    tags = [f'D{i}' for i in range(1, 24)] + [f'W{i}' for i in range(1, 19)]
    dr = drawing([layer('RNAME', byType={'TEXT': 41}, texts=41)], texts=[('RNAME', t) for t in tags])
    got = S.suggest([dr], None)['layers']['RNAME']
    assert (got['role'], got['from']) == ('room-name', 'name')
    assert got['evidence'][1] == 'named like a room-name layer, but its 41 texts are door or window tags D1 ... W18'
    # door swings on a wall layer are worth saying; on a door or furniture layer they are what the name says
    walls = one('WALL', doorArcs=4, doorArcsWithLeaf=4, byType={'ARC': 4, 'LINE': 20})
    assert walls['role'] == 'wall' and 'but 4 door swings with their leaves' in walls['evidence'][1]
    assert len(one('FUR', doorArcs=8, doorArcsWithLeaf=8, byType={'ARC': 8})['evidence']) == 1
    # weak geometry (line pairs) never argues with a name
    assert len(one('S-STRS', pairs={'glassLike': 50, 'wallLike': 0}, byType={'LINE': 100})['evidence']) == 1
    agree = one('A-WALL', solidHatches=10, pairs={'glassLike': 0, 'wallLike': 20}, byType={'HATCH': 10, 'LINE': 40})
    assert agree['evidence'][1].startswith('its contents agree: 10 solid fills')


@pytest.mark.parametrize('kw, texts, role', [
    (dict(byType={'DIMENSION': 12}), [], 'ignore'),
    (dict(byType={'ARC': 3, 'LINE': 9}, doorArcs=3, doorArcsWithLeaf=3), [], 'door'),
    (dict(byType={'HATCH': 5, 'LINE': 20}, solidHatches=5, pairs={'glassLike': 0, 'wallLike': 6}), [], 'wall'),
    (dict(byType={'LINE': 12}, pairs={'glassLike': 6, 'wallLike': 0}), [], 'glass'),
    (dict(byType={'INSERT': 14}, inserts=14, topBlocks=[{'family': 'Chair - Mollie', 'count': 12},
                                                          {'family': 'Desk 1600x800', 'count': 2}]), [], 'furniture'),
    (dict(byType={'TEXT': 3}, texts=3), ['LOBBY', 'MEETING ROOM', 'ห้องน้ำ'], 'room-name'),
    (dict(byType={'TEXT': 3}, texts=3), ['D1', 'D2', 'W1'], 'other'),
    (dict(byType={'TEXT': 3}, texts=3), ['1', '27', 'o'], 'other'),
    (dict(byType={'CIRCLE': 4, 'TEXT': 4}, texts=4), ['A', 'B', '1', '2'], 'grid'),
])
def test_contents_rules(kw, texts, role) -> None:
    dr = drawing([layer('X-CONTENTS', **kw)], texts=[('X-CONTENTS', t) for t in texts])
    got = S.suggest([dr], None)['layers']['X-CONTENTS']
    assert (got['role'], got['from']) == (role, 'contents'), got


def test_weak_contents_need_enough_of_it() -> None:
    assert one('X', byType={'LINE': 100}, pairs={'glassLike': 6, 'wallLike': 0})['role'] == 'other'   # 12 of 100
    assert one('X', byType={'HATCH': 1, 'LINE': 4}, solidHatches=1, pairs={'glassLike': 0, 'wallLike': 2})['role'] == 'other'
    assert one('X', byType={'INSERT': 9}, topBlocks=[{'family': 'Chair', 'count': 9}])['role'] == 'other'
    assert one('X', byType={'INSERT': 30}, topBlocks=[{'family': 'Outlet 2G', 'count': 30}])['role'] == 'other'


def test_layer_zero_is_left_as_context() -> None:
    dr = drawing([layer('0', byType={'TEXT': 10, 'ARC': 2000, 'LINE': 2500}, texts=10, doorArcs=40,
                        doorArcsWithLeaf=40)], levels=[('0', f'+{i}.00') for i in range(8)])
    got = S.suggest([dr], None)['layers']['0']
    assert (got['role'], got['from']) == ('other', 'default') and 'layer 0' in got['evidence'][0]


OFFICE = {'format': 'office-mapping/1', 'id': 'dwp-revit', 'name': 'DWP (Revit)', 'createdAt': 'x', 'updatedAt': 'x',
          'layers': {'A-WALL': {'role': 'wall', 'names': ['A-WALL'], 'uses': 2, 'lastProject': 'bank-sampeng',
                                'lastUsedAt': 'x', 'was': None},
                     'A-GENM': {'role': 'furniture', 'names': ['A-GENM'], 'uses': 1, 'lastProject': 'bank-sampeng',
                                'lastUsedAt': 'x', 'was': 'other'},
                     'DA-DOOR-WIND': {'role': 'door', 'names': ['Xr_A$0$DA-DOOR-WIND'], 'uses': 1,
                                      'lastProject': 'suite', 'lastUsedAt': 'x', 'was': None},
                     'BROKEN': {'role': 'not-a-role', 'names': ['BROKEN'], 'uses': 1, 'lastProject': 'x',
                                'lastUsedAt': 'x', 'was': None}},
          'furnitureWords': {}}


def test_office_memory_exact_then_similar_then_the_rest() -> None:
    dr = drawing([layer('A-WALL'), layer('A-GENM', byType={'HATCH': 24, 'LINE': 300}, solidHatches=24,
                                         pairs={'glassLike': 0, 'wallLike': 9}),
                  layer('Xr_B$0$DA-DOOR-WIND'), layer('a-wall'), layer('BROKEN'), layer('S-COLS')])
    got = S.suggest([dr], OFFICE)
    L = got['layers']
    assert got['office'] == 'dwp-revit' and got['format'] == 'layer-suggestions/1'
    assert (L['A-WALL']['role'], L['A-WALL']['from']) == ('wall', 'office')
    assert (L['A-GENM']['role'], L['A-GENM']['from']) == ('furniture', 'office')       # beats its contents (wall)
    assert 'remembered for DWP (Revit) as furniture (used 1 time, last in bank-sampeng)' == L['A-GENM']['evidence'][0]
    assert (L['Xr_B$0$DA-DOOR-WIND']['role'], L['Xr_B$0$DA-DOOR-WIND']['from']) == ('door', 'office-similar')
    # an entry with a role outside the 17 is not used; the name table and the default carry on
    assert (L['a-wall']['from'], L['BROKEN']['from'], L['S-COLS']['from']) == ('office-similar', 'default', 'name')
    assert S.suggest([dr], None)['office'] is None


def test_counts_add_up_across_the_sources_and_names_are_sorted() -> None:
    a = drawing([layer('X-DOORS', byType={'ARC': 1}, doorArcs=1, doorArcsWithLeaf=1), layer('B')])
    b = drawing([layer('X-DOORS', byType={'ARC': 1}, doorArcs=1, doorArcsWithLeaf=1), layer('A')])
    got = S.suggest([a, b], None)
    assert list(got['layers']) == ['A', 'B', 'X-DOORS']
    assert got['layers']['X-DOORS']['role'] == 'door'                   # 1 + 1 swings: two
    assert S.suggest([a], None)['layers']['X-DOORS']['role'] == 'other'


def test_suggestions_pass_the_apis_record_check(tmp_path) -> None:
    dr = drawing([layer(n) for n in ('A-WALL', '<img src=x onerror=alert(1)>', "A-DOOR</script>$'", 'S-GRID-IDEN')])
    p = tmp_path / 'suggestions.json'
    p.write_text(json.dumps(S.suggest([dr], OFFICE), ensure_ascii=False), encoding='utf-8')
    assert K.api_issues([('suggestions', p)]) == {str(p): []}
