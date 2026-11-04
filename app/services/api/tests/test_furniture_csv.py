"""furniture_csv (DESIGN.md 18.8): the port of furniture_kit.csv_text gives the prototype CSVs byte for byte with no saved
heights (the BOM included), the scaffold's typed-height goldens with heights, and the awkward cases furniture/test_boxes.mjs
checks (quoting, CR / LF, no -0.000, exact ties, whole mm half up, the model's floor order, unsorted input)."""
from __future__ import annotations

import copy
import os
import shutil
import subprocess

import pytest

from kit import FIXTURES, PROTOTYPES, RUN, read_json
from walkthrough_api import furniture_csv as fc
from walkthrough_api.jsonio import dumps_compact

TYPED = {'table': 600, 'seat': 300, 'cabinet': 1000, 'other': 2100}      # the goldens' heights (fixtures/README.md)
FURNISHED = ['bank-v2', 'suite', 'house', 'hotel']


def model(name: str) -> dict:
    return read_json(FIXTURES / 'models' / f'{name}.model.json')


@pytest.mark.parametrize('name', FURNISHED)
def test_default_heights_equal_the_prototype_csv(name: str) -> None:
    assert fc.csv_bytes(model(name)) == (FIXTURES / 'csv' / f'{name}.csv').read_bytes()


@pytest.mark.parametrize('name', FURNISHED)
def test_typed_heights_equal_the_goldens(name: str) -> None:
    m = model(name)
    kinds = {k['key'] for k in m['furnitureKinds']}
    heights = {k: v for k, v in TYPED.items() if k in kinds}
    assert fc.csv_bytes(m, heights) == (FIXTURES / 'csv' / f'{name}-typed.csv').read_bytes()


def test_csv_text_has_no_bom_and_crlf_rows() -> None:
    text = fc.model_csv_text(model('bank-v2'))
    assert not text.startswith('\ufeff') and text.endswith('\r\n')
    assert text.split('\r\n')[0] == ','.join(fc.CSV_COLUMNS)
    assert fc.csv_bytes(model('bank-v2')).startswith(b'\xef\xbb\xbf')


def test_file_names() -> None:
    assert fc.file_name(model('bank-v2')) == 'BangkokBank-Sampeng_furniture_list.csv'
    assert fc.file_name(model('suite')) == 'Presidential_furniture_list.csv'
    assert fc.file_name(model('house')) == 'Sukhumvit_furniture_list.csv'


def test_no_furniture_no_list() -> None:
    with pytest.raises(ValueError):
        fc.csv_bytes(model('bank-v1'))


@pytest.mark.parametrize('v, want', [(62.5, 63), (460.5, 461), (10.5, 11), (0.4999, 0), (-0.5, 0), (750, 750)])
def test_whole_mm_half_up(v, want) -> None:
    assert fc.whole(v) == want


@pytest.mark.parametrize('v, nd, want', [(-0.0004, 3, '0.000'), (-0.0, 3, '0.000'), (12.25, 1, '12.2'), (0.0625, 3, '0.062'),
                                         (-1.5, 1, '-1.5'), (179.95, 1, '179.9')])
def test_fixed(v, nd, want) -> None:
    assert fc.fixed(v, nd) == want


@pytest.mark.parametrize('v, want', [('a,b', '"a,b"'), ('say "hi"', '"say ""hi"""'), ('a\rb', '"a\rb"'), ('a\nb', '"a\nb"'),
                                     ('plain', 'plain'), (7, '7'), ('', '')])
def test_field_quoting(v, want) -> None:
    assert fc.field(v) == want


def awkward() -> dict:
    """furniture/test_boxes.mjs's awkward variant, made from the v1 mini model (its furniture fields kept)."""
    m = copy.deepcopy(model('mini'))
    m['furnitureKinds'].insert(0, {'key': 'atm', 'label': 'ATM / kiosk', 'colour': '#c0392b', 'height': 1500, 'base': 0,
                                   'onTop': False, 'support': False, 'blocks': True, 'count': 0})
    kind = {k['key']: k for k in m['furnitureKinds']}
    kind['seat']['height'] = 460.5
    kind['plant']['base'] = 10.5
    by = {p['id']: p for p in m['furniture']}
    by['L1-seat-001'].update(family='Chair, "Lux" model', x=-1.0004, y=0.0625 - 2.0, rot=12.25, w=0.0625)
    by['L1-seat-002'].update(block='Block A\nsecond line', note='run of 4, "fronts"', rot=0.75, w=0.0635, d=0.6005)
    by['L1-seat-003'].update(layer='I-FURN\rCR', x=2.4995, y=-2.0004)
    by['L1-plant-001'].update(handle='', family='', rot=179.95, n=7)
    key = {'L1': 'Z1', 'L2': 'A2'}
    rename = lambda s: (key[s[:2]] + s[2:]) if s and s[:2] in key and s[2:3] == '-' else s   # noqa: E731
    for f in m['floors']:
        f['key'] = key[f['key']]
    for p in m['furniture']:
        p['floor'], p['id'], p['on'] = key[p['floor']], rename(p['id']), rename(p['on'])
    m['furniture'].reverse()
    return m


def test_awkward_model_as_test_boxes_checks_it() -> None:
    text = fc.model_csv_text(awkward())
    assert '"Chair, ""Lux"" model"' in text and '"Block A\nsecond line"' in text and '"run of 4, ""fronts"""' in text
    assert '"I-FURN\rCR"' in text and '-0.000' not in text
    assert ',0.000,0.062,63,570,461,0,12.2,' in text
    assert ',7.000,2.000,500,500,600,11,179.9,,7,' in text
    assert text.index('\r\nZ1-') < text.index('\r\nA2-')
    assert 'atm' not in [line.split(',')[2] for line in text.split('\r\n')[1:] if line]          # a kind nobody uses: no row


def _system_python() -> str | None:
    return shutil.which('python') or shutil.which('py')


@pytest.mark.skipif(_system_python() is None, reason='no system Python to run the contract reference writer')
def test_awkward_model_equals_the_contract_reference_writer() -> None:
    """furniture/fixtures/expected_csv.py (the contract's independent writer, pure Python) run read-only with the system
    Python and -B, on the awkward model: the same bytes (no chains of supports in it, so its recursion agrees)."""
    work = RUN / 'csv-reference'
    work.mkdir(parents=True, exist_ok=True)
    path = work / 'awkward_model.json'
    path.write_bytes(dumps_compact(awkward()))
    oracle = PROTOTYPES / 'furniture' / 'fixtures' / 'expected_csv.py'
    env = {k: v for k, v in os.environ.items() if k != 'PYTHONPATH'}
    env.update(PYTHONIOENCODING='utf-8', PYTHONDONTWRITEBYTECODE='1')
    r = subprocess.run([_system_python(), '-B', str(oracle), str(path)], capture_output=True, timeout=120, env=env,
                       cwd=work)
    assert r.returncode == 0, r.stderr.decode('utf-8', 'replace')
    assert r.stdout.decode('utf-8') == fc.model_csv_text(awkward())
    assert not (PROTOTYPES / 'furniture' / 'fixtures' / '__pycache__').exists()


def test_support_underside_is_one_level() -> None:
    m = model('mini')
    kinds = {k['key']: k for k in m['furnitureKinds']}
    rows = {line.split(',')[0]: line.split(',') for line in fc.model_csv_text(m).split('\r\n')[1:] if line}
    for p in m['furniture']:
        if p['on']:
            support = next(q for q in m['furniture'] if q['id'] == p['on'])
            assert int(rows[p['id']][13]) == kinds[support['kind']]['base'] + kinds[support['kind']]['height']
    typed = fc.model_csv_text(m, {'table': 640})
    on_table = [p for p in m['furniture'] if p['on'] and next(q for q in m['furniture'] if q['id'] == p['on'])['kind'] == 'table']
    assert on_table and all(f'{p["id"]},' in typed for p in on_table)
    rows2 = {line.split(',')[0]: line.split(',') for line in typed.split('\r\n')[1:] if line}
    assert all(int(rows2[p['id']][13]) == 640 for p in on_table)       # what stands on the table follows its typed height
