"""The store, seed and CSV changes of the upload milestone (docs/upload/DESIGN.md U-11.1, U-15.3, U-11.6; ACCEPTANCE 2.2):
create_version checks a `.ms` stamp after its name checks and writes project-data.json; the seed never replaces an
uploaded version, even with --force, and a fresh seed is still ['.lock', 'projects']; the CSV formula guard."""
from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from kit import FIXTURES, PROTOTYPES, read_json
from walkthrough_api import furniture_csv as fc
from walkthrough_api.jsonio import dumps_pretty, sha1_hex
from walkthrough_api.seed.build import SeedError, seed, uploaded_version
from walkthrough_api.store.base import NewProject, VersionDraft
from walkthrough_api.store.local import LocalStore

quiet = {'log': lambda _line: None}


def draft(raw: bytes, ms: bytes, **kw) -> VersionDraft:
    pres = read_json(FIXTURES / 'presentation' / 'bank-sampeng-v2.json')
    return VersionDraft(label='x', source_kind='cad', source_files=[], model_json=raw, stages_json=None, presentation=pres,
                        downloads={'a.ms': ms}, **kw)


def test_create_version_checks_the_stamp_after_the_names(tmp_path: Path) -> None:
    store = LocalStore(tmp_path / 'data')
    store.create_project(NewProject(id='stamps', name='x', short_name='x', source_kind='cad'))
    raw = (FIXTURES / 'models' / 'bank-v2.model.json').read_bytes()
    wrong = b'-- title\n-- (model data 000000000000)\n'
    named = draft(raw, wrong)
    named.downloads = {'a b.ms': wrong}
    with pytest.raises(ValueError, match='does not match'):                    # the name error first
        store.create_version('stamps', named)
    with pytest.raises(ValueError, match='line 2 says model data 000000000000'):
        store.create_version('stamps', draft(raw, wrong))
    staged = store.stage('a.ms', [wrong])                                    # a staged script is read for its stamp
    staged_draft = draft(raw, wrong)
    staged_draft.downloads = {'a.ms': staged}
    with pytest.raises(ValueError, match='line 2 says'):
        store.create_version('stamps', staged_draft)
    assert store.get_project('stamps').versions == []
    settings = (FIXTURES / 'upload' / 'settings' / 'bank.json').read_bytes()
    good = b'-- title\n-- (model data c3a9408304a2)\n'
    v = store.create_version('stamps', draft(raw, good, project_data=settings))
    folder = tmp_path / 'data' / 'projects' / 'stamps' / 'versions' / '1'
    assert v.version == 1 and (folder / 'project-data.json').read_bytes() == settings
    assert store.version_project_data('stamps', 1) == settings


def test_the_seed_never_replaces_an_uploaded_version(data_copy: Path) -> None:
    v2 = data_copy / 'projects' / 'bank-sampeng' / 'versions' / '2' / 'version.json'
    assert not uploaded_version(LocalStore(data_copy), 'bank-sampeng', 2)
    record = read_json(v2)
    del record['seed']
    v2.write_bytes(dumps_pretty(record))
    before = v2.read_bytes()
    with pytest.raises(SeedError, match='bank-sampeng v2: an uploaded version'):
        seed(PROTOTYPES, data_copy, force=True, **quiet)
    assert v2.read_bytes() == before
    result = seed(PROTOTYPES, data_copy, **quiet)                            # without --force: left alone, no error
    assert not result.built and v2.read_bytes() == before


def test_an_uploaded_version_beside_the_seeded_ones_is_kept_and_counted(data_copy: Path) -> None:
    """A v3 saved from an upload is not in the seed table: --force rebuilds v1, v2 and keeps v3 (meta.json counts it)."""
    store = LocalStore(data_copy)
    raw = (FIXTURES / 'models' / 'bank-v2.model.json').read_bytes()
    v3 = store.create_version('bank-sampeng', draft(raw, (PROTOTYPES / 'bank_test' / 'Bangkok_Bank_Sampeng.ms').read_bytes()))
    assert v3.version == 3 and v3.seed is None
    seed(PROTOTYPES, data_copy, force=True, **quiet)
    meta = read_json(data_copy / 'projects' / 'bank-sampeng' / 'meta.json')
    assert meta['versions'] == [1, 2, 3] and meta['latestVersion'] == 3
    assert (data_copy / 'projects' / 'bank-sampeng' / 'versions' / '3' / 'model.json').read_bytes() == raw


def test_a_fresh_seed_is_still_lock_and_projects(seeded: Path) -> None:
    assert sorted(p.name for p in seeded.iterdir()) == ['.lock', 'projects']


HOSTILE = {'family': '=HYPERLINK("http://x","y")', 'block': '+cmd|" /C calc"!A0', 'layer': '-2+3', 'note': '@SUM(1)',
           'handle': '\tTAB', 'kind_label': '\rCR'}


def test_the_csv_guard() -> None:
    m = copy.deepcopy(read_json(FIXTURES / 'models' / 'bank-v2.model.json'))
    p = m['furniture'][0]
    p.update(family=HYPERLINK, block=HOSTILE['block'], layer=HOSTILE['layer'], note=HOSTILE['note'], handle=HOSTILE['handle'])
    m['furnitureKinds'][[k['key'] for k in m['furnitureKinds']].index(p['kind'])]['label'] = HOSTILE['kind_label']
    text = fc.model_csv_text(m)
    row = next(line for line in text.split('\r\n')[1:] if line.startswith(p['id'] + ','))
    assert "'=HYPERLINK(" in row and '"\'=HYPERLINK(""http://x"",""y"")"' in row       # guarded, then quoted
    assert "'+cmd|" in row and ",'-2+3," in row and ",'@SUM(1)" in row and ",'\tTAB," in row
    assert '"\'\rCR"' in text                                                     # CR: guarded and quoted
    clean = fc.model_csv_text(read_json(FIXTURES / 'models' / 'bank-v2.model.json'))
    assert len(clean.split('\r\n')) == len(text.split('\r\n'))
    numbers = [fc.CSV_COLUMNS.index(c) for c in ('x_m', 'y_m', 'width_mm', 'depth_mm', 'height_mm', 'base_mm',
                                                  'rotation_deg', 'merged')]
    plain_row = next(line for line in clean.split('\r\n') if line.startswith(p['id'] + ',')).split(',')
    assert [plain_row[i] for i in numbers] == [row.split(',')[i - len(fc.CSV_COLUMNS)] for i in numbers]
    assert fc.guard('-0.5') == "'-0.5" and fc.guard('plain') == 'plain' and fc.guard('') == ''
    assert fc.guard(12) == '12'                                                   # numbers only through text columns


@pytest.mark.parametrize('name', ['bank-v2', 'suite', 'house', 'hotel'])
def test_the_four_csvs_are_unchanged(name: str) -> None:
    assert fc.csv_bytes(read_json(FIXTURES / 'models' / f'{name}.model.json')) == \
        (FIXTURES / 'csv' / f'{name}.csv').read_bytes()


def test_number_columns_never_change() -> None:
    m = copy.deepcopy(read_json(FIXTURES / 'models' / 'bank-v2.model.json'))
    for p in m['furniture']:
        p['x'] = -abs(p['x']) - 1.0                                               # negative coordinates: '-...'
    rows = [line.split(',') for line in fc.model_csv_text(m).split('\r\n')[1:-1]]
    x_col = fc.CSV_COLUMNS.index('x_m')
    assert all(r[x_col].startswith('-') for r in rows if len(r) == len(fc.CSV_COLUMNS))
    assert sha1_hex(json.dumps(rows).encode())


HYPERLINK = HOSTILE['family']
