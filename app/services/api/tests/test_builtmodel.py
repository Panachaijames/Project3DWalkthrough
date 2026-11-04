"""builtmodel.validate (DESIGN.md 5.6, strict): the schema copy, every real model, the shared broken corpus at the paths of
its manifest (the furniture cases included: the API is strict), and the rules one by one."""
from __future__ import annotations

import copy
import json

import pytest

from kit import APP, FIXTURES, read_json
from walkthrough_api import builtmodel as bm
from walkthrough_api.builtmodel import ModelInvalid

BROKEN = FIXTURES / 'models' / 'broken'
MANIFEST = read_json(BROKEN / 'expected.json')
MODELS = sorted((FIXTURES / 'models').glob('*.json'))


def paths(model: object) -> list[str]:
    return [i.path for i in bm.issues(model)]


def test_schema_copy_is_identical_to_docs() -> None:
    assert bm.SCHEMA_PATH.read_bytes() == (APP / 'docs' / 'built-model.schema.json').read_bytes()


@pytest.mark.parametrize('path', MODELS, ids=lambda p: p.name)
def test_every_fixture_model_is_valid(path) -> None:
    assert bm.issues(read_json(path)) == []
    assert bm.validate_bytes(path.read_bytes()) == read_json(path)


def test_every_seeded_model_is_valid(seeded) -> None:
    models = sorted(seeded.glob('projects/*/versions/*/model.json'))
    assert len(models) == 5
    for p in models:
        assert bm.issues(read_json(p)) == [], p


@pytest.mark.parametrize('name', sorted(MANIFEST['cases']), ids=str)
def test_broken_corpus_is_rejected_at_the_manifest_path(name: str) -> None:
    case = MANIFEST['cases'][name]
    model = read_json(BROKEN / name)
    assert case['path'] in paths(model), (name, [str(i) for i in bm.issues(model)])
    with pytest.raises(ModelInvalid) as e:
        bm.validate(model)
    assert case['path'] in [i.path for i in e.value.issues]


def test_broken_corpus_covers_both_kinds() -> None:
    kinds = {c['kind'] for c in MANIFEST['cases'].values()}
    assert kinds == {'schema', 'cross'}
    assert sum(c['viewer'] == 'warns' for c in MANIFEST['cases'].values()) == 4      # the furniture cases: still refused here


@pytest.fixture
def bank() -> dict:
    return read_json(FIXTURES / 'models' / 'bank-v2.model.json')


def test_repeated_floor_key_reported_at_its_later_occurrence(bank) -> None:
    m = copy.deepcopy(bank)
    m['floors'][1]['key'] = m['floors'][0]['key']
    assert '/floors/1/key' in paths(m)


def test_floors_out_of_level_order(bank) -> None:
    m = copy.deepcopy(bank)
    m['floors'][1]['level'] = -1.0
    assert '/floors/1/level' in paths(m)


def test_plinth_only_on_slabs(bank) -> None:
    m = copy.deepcopy(bank)
    i = next(i for i, p in enumerate(m['parts']) if p['kind'] == 'wall')
    m['parts'][i]['plinth'] = True
    assert f'/parts/{i}/plinth' in paths(m)
    j = next(i for i, p in enumerate(m['parts']) if p['kind'] == 'slab')
    m2 = copy.deepcopy(bank)
    m2['parts'][j]['plinth'] = True
    assert paths(m2) == []


def test_per_floor_map_with_an_unknown_floor(bank) -> None:
    m = copy.deepcopy(bank)
    m['voids']['L7'] = []
    assert '/voids/L7' in paths(m)


def test_floor_references_of_rooms_openings_probes_furniture(bank) -> None:
    for coll in ('rooms', 'openings', 'probes', 'furniture'):
        m = copy.deepcopy(bank)
        m[coll][0]['floor'] = 'L9'
        assert f'/{coll}/0/floor' in paths(m), coll


def test_skins_and_stair_panels(bank) -> None:
    m = copy.deepcopy(bank)
    key = next(k for k, v in m['colliderSkins'].items() if v)
    m['colliderSkins'][key][0]['z1'] = m['colliderSkins'][key][0]['z0']
    m['stairs']['L1']['panels'] = [0, 0, 1]
    found = paths(m)
    assert f'/colliderSkins/{key}/0/z1' in found and '/stairs/L1/panels' in found


def test_repeated_furniture_id_and_kind_key(bank) -> None:
    m = copy.deepcopy(bank)
    m['furniture'][2]['id'] = m['furniture'][1]['id']
    m['furnitureKinds'][1]['key'] = m['furnitureKinds'][0]['key']
    found = paths(m)
    assert '/furniture/2/id' in found and '/furnitureKinds/1/key' in found


def test_furniture_needs_kinds(bank) -> None:
    m = copy.deepcopy(bank)
    del m['furnitureKinds']
    assert '' in paths(m)            # dependentRequired: reported at the root


def test_pointer_escaping() -> None:
    assert bm.pointer(['a/b', 'c~d', 3]) == '/a~1b/c~0d/3'
    assert bm.pointer([]) == ''


@pytest.mark.parametrize('raw', [b'\xef\xbb\xbf{}', b'{"a": NaN}', b'{"a": Infinity}', b'{"a": 1, "a": 2}', b'\xff\xfe', b'{'],
                         ids=['bom', 'nan', 'infinity', 'repeated-key', 'not-utf8', 'syntax'])
def test_validate_bytes_wants_strict_json(raw: bytes) -> None:
    with pytest.raises(ModelInvalid) as e:
        bm.validate_bytes(raw)
    assert e.value.issues[0].path == ''


def test_issue_message_lists_paths(bank) -> None:
    m = copy.deepcopy(bank)
    m['parts'][3]['z1'] = 'x'
    with pytest.raises(ModelInvalid) as e:
        bm.validate(m, 'the bank')
    assert '/parts/3/z1' in str(e.value) and str(e.value).startswith('the bank: 1 issue')


def test_rules_need_a_valid_shape_first(bank) -> None:
    m = copy.deepcopy(bank)
    m['parts'][3]['z1'] = 'not a number'              # the z1 > z0 rule would fail on it: the schema reports it alone
    assert bm.schema_issues(m) and bm.issues(m) == bm.schema_issues(m)


def test_models_round_trip_through_json(bank) -> None:
    assert bm.validate(json.loads(json.dumps(bank))) == bank
