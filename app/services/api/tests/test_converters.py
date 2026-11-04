"""The conversions to BuiltModel v1 (DESIGN.md 6, checks of 6.5): counts, byte-identical bank and hotel, stamps against
the Max scripts' line 2 and stampSource, the house's plates, rings and sheetShift, the suite's openings and probe, and the
converted suite and house against the architect's provisional fixtures (parsed JSON, and here also byte for byte)."""
from __future__ import annotations

import copy
import hashlib

import pytest

from kit import FIXTURES, PROTOTYPES, VERSION_IDS, VERSIONS, read_json
from walkthrough_api.jsonio import dumps_compact
from walkthrough_api.seed import convert_house, convert_suite
from walkthrough_api.seed.build import ms_stamp
from walkthrough_api.seed.sources import SEED_TABLE

# DESIGN.md 6.5: floors, parts, openings, probes, rooms, furniture (kinds), stamp
COUNTS = {
    ('bank-sampeng', 1): (2, 124, 55, 19, 18, 0, 0, '4b02dc17f286'),
    ('bank-sampeng', 2): (2, 124, 49, 19, 18, 185, 14, 'c3a9408304a2'),
    ('presidential-suite', 1): (1, 62, 22, 1, 16, 120, 13, 'f1b95c53eb3d'),
    ('sukhumvit-house', 1): (2, 197, 86, 0, 0, 76, 9, None),            # the house: sha1 of its model.json
    ('hotel-lobby', 1): (2, 89, 20, 9, 24, 159, 8, '6ab030750886'),
}


def vdir(seeded, project_id, n):
    return seeded / 'projects' / project_id / 'versions' / str(n)


@pytest.fixture(scope='module')
def suite_src():
    return read_json(PROTOTYPES / 'presidential_test' / 'src' / 'pres2_model.json')


@pytest.fixture(scope='module')
def house_src():
    return (read_json(PROTOTYPES / 'cad_test' / 'src' / 'house3d_merged.json'),
            read_json(PROTOTYPES / 'cad_test' / 'src' / 'furniture_house.json'))


def test_converted_suite_equals_the_provisional_fixture(suite_src) -> None:
    fixture = FIXTURES / 'models' / 'suite.model.json'
    got = convert_suite.convert(suite_src)
    assert got == read_json(fixture)                       # as parsed JSON (DESIGN.md 6.5)
    assert dumps_compact(got) == fixture.read_bytes()      # and byte for byte


def test_converted_house_equals_the_provisional_fixture(house_src) -> None:
    fixture = FIXTURES / 'models' / 'house.model.json'
    got = convert_house.convert(*house_src)
    assert got == read_json(fixture)
    assert dumps_compact(got) == fixture.read_bytes()


@pytest.mark.parametrize('key', list(VERSIONS), ids=VERSION_IDS)
def test_counts_and_stamps_of_every_version(seeded, key) -> None:
    floors, parts, openings, probes, rooms, furniture, kinds, stamp = COUNTS[key]
    d = vdir(seeded, *key)
    m = read_json(d / 'model.json')
    v = read_json(d / 'version.json')
    assert (len(m['floors']), len(m['parts']), len(m['openings']), len(m['probes']), len(m['rooms']),
            len(m.get('furniture') or []), len(m.get('furnitureKinds') or [])) == (floors, parts, openings, probes, rooms,
                                                                                 furniture, kinds)
    assert v['counts'] == {'floors': floors, 'parts': parts, 'openings': openings, 'furniture': furniture,
                           'furnitureKinds': kinds, 'rooms': rooms}
    model_sha1 = hashlib.sha1((d / 'model.json').read_bytes()).hexdigest()
    assert v['modelSha1'] == model_sha1
    assert v['stamp'] == hashlib.sha1((d / v['stampSource']).read_bytes()).hexdigest()[:12]
    assert v['stamp'] == (stamp or model_sha1[:12])


def test_house_stamp_is_its_model_and_it_has_no_max_script(seeded) -> None:
    v = read_json(vdir(seeded, 'sukhumvit-house', 1) / 'version.json')
    assert v['stampSource'] == 'model.json' and v['downloads']['maxScript'] is None
    assert v['stamp'] == hashlib.sha1((FIXTURES / 'models' / 'house.model.json').read_bytes()).hexdigest()[:12]


def test_suite_stamp_comes_from_its_source_model(seeded) -> None:
    d = vdir(seeded, 'presidential-suite', 1)
    v = read_json(d / 'version.json')
    assert v['stampSource'] == 'source/pres2_model.json' and v['stamp'] == 'f1b95c53eb3d'
    assert (d / 'source' / 'pres2_model.json').read_bytes() == (PROTOTYPES / 'presidential_test/src/pres2_model.json').read_bytes()
    assert v['modelSha1'] != hashlib.sha1((d / 'source' / 'pres2_model.json').read_bytes()).hexdigest()   # the stored model is v1


@pytest.mark.parametrize('src', [s for s in SEED_TABLE if s.max_script], ids=lambda s: f'{s.project_id}-v{s.version}')
def test_max_script_line_2_carries_the_stamp(seeded, src) -> None:
    d = vdir(seeded, src.project_id, src.version)
    script = (d / 'downloads' / src.max_script).read_bytes()
    assert script == (PROTOTYPES / src.folder / src.max_script).read_bytes()       # served as seeded (DESIGN.md 18.7)
    assert ms_stamp(script) == read_json(d / 'version.json')['stamp']


@pytest.mark.parametrize('src', [s for s in SEED_TABLE if s.model == 'copy'], ids=lambda s: f'{s.project_id}-v{s.version}')
def test_bank_and_hotel_models_are_copied_byte_for_byte(seeded, src) -> None:
    stored = (vdir(seeded, src.project_id, src.version) / 'model.json').read_bytes()
    source = (PROTOTYPES / src.path(src.model_files[0])).read_bytes()
    assert stored == source and hashlib.sha1(stored).hexdigest() == hashlib.sha1(source).hexdigest()
    fixture = {('bank-sampeng', 1): 'bank-v1', ('bank-sampeng', 2): 'bank-v2', ('hotel-lobby', 1): 'hotel'}
    assert stored == (FIXTURES / 'models' / f'{fixture[(src.project_id, src.version)]}.model.json').read_bytes()


# ---------------------------------------------------------------------------------------------------- the house (6.4)
def test_house_plates_equal_the_merged_files_plates(house_src) -> None:
    H, FH = house_src
    m = convert_house.convert(H, FH)
    for floor, plates in H['plates'].items():
        slabs = [{'o': p['o'], 'h': p['h']} for p in m['parts'] if p['kind'] == 'slab' and p['floor'] == floor]
        assert slabs == [{'o': r['o'], 'h': r['h']} for r in plates], floor


def test_every_house_ring_appears_once_with_its_points(house_src) -> None:
    H, FH = house_src
    m = convert_house.convert(H, FH)
    got = [(p['floor'], p['kind'], p['o'], p['h']) for p in m['parts']]
    want = [(k.split(':')[0], k.split(':')[1], r['o'], r['h']) for k, rings in H['solids'].items() for r in rings]
    want += [(fl, p['kind'], p['o'], p['h']) for fl in ('ground', 'upper') for p in H['pieces'][fl]]
    want += [(fl, 'slab', r['o'], r['h']) for fl in ('ground', 'upper') for r in H['plates'][fl]]
    assert len(got) == len(want) == 197
    for w in want:
        assert got.count(w) == 1, w[:2]


def test_house_floors_sheet_shift_and_heights(house_src) -> None:
    m = convert_house.convert(*house_src)
    ground, upper = m['floors']
    assert (ground['key'], ground['level'], ground['wallHeight'], ground['slabThickness']) == ('ground', 0.9, 3.9, 0.9)
    assert (upper['key'], upper['level'], upper['wallHeight'], upper['slabThickness']) == ('upper', 4.8, 3.5, 0.25)
    assert 'sheetShift' not in ground and upper['sheetShift'] == [74.021, 0.0]
    H, FH = house_src
    assert FH['frame']['shift']['upper'] == -74.021 and m['offset'] == FH['offset'] == H['centre']
    assert (m['railingHeight'], m['singleLineHeight'], m['doorHeadDefault']) == (1.0, 1.0, 3)


def test_house_parts_heights_fit_and_plinth(house_src) -> None:
    m = convert_house.convert(*house_src)
    H0 = {'ground': 3.9, 'upper': 3.5}
    for p in m['parts']:
        if p['kind'] == 'wall':
            assert (p['z0'], p['z1'], p['follow']) == (0.0, H0[p['floor']], True) and 'fit' not in p
        elif p['kind'] == 'glass':
            assert (p['z1'], p['follow']) == (round(H0[p['floor']] - 0.6, 6), True)
        elif p['kind'] == 'single':
            assert (p['z1'], p['follow']) == (1.0, False)
        elif p['kind'] == 'lintel':
            assert (p['fit'], p['follow']) == ('top', True) and p['label']
        elif p['kind'] == 'sill':
            assert (p['fit'], p['follow']) == ('clip', False)
        elif p['kind'] == 'pane':
            assert p['fit'] in ('top', 'clip') and p['follow'] == (p['fit'] == 'top')
        elif p['kind'] == 'slab':
            assert p['z1'] == 0.0 and p['follow'] is False
            assert p.get('plinth') == (True if p['floor'] == 'ground' else None)
            assert p['z0'] == (-0.9 if p['floor'] == 'ground' else -0.25)
    H, _ = house_src
    tops = {p['id'] for fl in H['pieces'] for p in H['pieces'][fl] if p['kind'] == 'pane' and p.get('top')}
    assert {p['label'] for p in m['parts'] if p['kind'] == 'pane' and p['fit'] == 'top'} == tops
    assert sum(1 for p in m['parts'] if p.get('plinth')) == 3


def test_house_openings_keep_every_field(house_src) -> None:
    H, FH = house_src
    m = convert_house.convert(H, FH)
    src = [(fl, o) for fl in ('ground', 'upper') for o in H['openings'][fl]]
    assert len(m['openings']) == len(src) == 86
    for got, (fl, o) in zip(m['openings'], src):
        assert got['floor'] == fl and got['lintel'] == ('lintel' if o['lintel'] else None)
        assert {k: v for k, v in got.items() if k not in ('floor', 'lintel')} == {k: v for k, v in o.items() if k != 'lintel'}
    assert m['rooms'] == [] and m['probes'] == []
    assert m['stairs'] == {k: {'below': [], 'above': [], 'panels': [v for s in H['stairs'][k] for v in s]} for k in ('ground', 'upper')}


def test_house_converter_refuses_an_offset_that_is_not_the_centre(house_src) -> None:
    H, FH = copy.deepcopy(house_src)
    FH['offset'] = [0, 0]
    with pytest.raises(convert_house.HouseSourceError):
        convert_house.convert(H, FH)


# ---------------------------------------------------------------------------------------------------- the suite (6.3)
def test_suite_openings_from_its_doors(suite_src) -> None:
    m = convert_suite.convert(suite_src)
    assert len(m['openings']) == len(suite_src['doors']) == 22
    for o, d in zip(m['openings'], suite_src['doors']):
        assert o['kind'] == ('door' if d['id'].startswith('D') else 'passage')
        assert (o['id'], o['label'], o['x'], o['y'], o['nx'], o['ny'], o['width'], o['floor']) == \
               (d['id'], d['name'], d['x'], d['y'], d['nx'], d['ny'], d['width'], 'suite')
        assert o.get('exterior') == (True if d.get('exterior') else None)


def test_suite_probe_rooms_floor_and_heights(suite_src) -> None:
    m = convert_suite.convert(suite_src)
    assert m['probes'] == [{'floor': 'suite', 'id': 'suite-glass-west', 'what': 'glass facade',
                            'x': suite_src['probe']['glassWestX'], 'y': suite_src['probe']['glassWestY'], 'nx': 1.0,
                            'ny': 0.0, 'inside': [1], 'label': "the living room's west glass (its room-side face)"}]
    assert [r['area'] for r in m['rooms']][:3] == [153.0, 56.0, 33.0]
    assert all(isinstance(r['area'], float) or r['area'] is None for r in m['rooms'])
    assert m['floors'] == [{'key': 'suite', 'name': 'Suite (FL-01)', 'level': 0, 'wallHeight': 3, 'slabThickness': 0.25}]
    assert (m['railingHeight'], m['singleLineHeight'], m['doorHeadDefault']) == (1.1, 1.0, 2.1)
    assert (m['photoName'], m['maxPrefix'], m['project'], m['shortName']) == ('Presidential', 'PS', 'Presidential suite',
                                                                            'Presidential suite')


def test_suite_follow_by_kind_unless_the_part_says(suite_src) -> None:
    m = convert_suite.convert(suite_src)
    for p, src in zip(m['parts'], suite_src['parts']):
        assert p['follow'] == src.get('follow', convert_suite.FOLLOW_BY_KIND[src['kind']])
        assert p.get('label') == src.get('label')
    assert any('follow' in p for p in suite_src['parts'])        # the full-height built-in decides for itself


def test_suite_area_empty_string_is_null(suite_src) -> None:
    src = copy.deepcopy(suite_src)
    src['rooms'][0]['area'] = ''
    assert convert_suite.convert(src)['rooms'][0]['area'] is None
