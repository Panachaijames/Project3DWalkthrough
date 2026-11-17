"""Deleted furniture boxes (step BX, 16 Nov 2026; docs/boxes/DESIGN.md 3 - 5 and 8.3, docs/contract-issues/BX.md).

The `pieceEdits` record beside the saved heights (PUT / GET / getVersion; left out = kept; {} = none and the file byte for
byte a heights-only one; the 422s; closure and order; the 412's details), lenient reads of an odd file, the downloads (the
CSV = its golden minus the deleted rows; the 3ds Max script filtered with its comment, or the same FileResponse; the
offline payload, Node = Python), the carry-over into a new version (fingerprint, one-to-one, tops only,
source/carried-edits.json, the version detail's `carriedEdits`), the seed's re-map, and the closure rule against the
viewer's shared case file."""
from __future__ import annotations

import copy
import os
import shutil
from collections import Counter
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient

from kit import APP, FIXTURES, PROTOTYPES, make_client, read_json, tree
from test_offline import BUILT_TEMPLATE, compare_with_node, missing, parse_page
from test_seed import copy_prototype_files
from test_u5_builds import bank_for, save_settings, start
from upkit import FakeJobRunner
from walkthrough_api import piece_edits
from walkthrough_api.jsonio import dumps_compact, dumps_pretty, loads_strict
from walkthrough_api.seed.build import SeedError, seed
from walkthrough_api.store.base import NewProject, StoreError, VersionDraft
from walkthrough_api.store.local import LocalStore

P = '/api/projects'
BANK = f'{P}/bank-sampeng/versions/2'
HEIGHTS = f'{BANK}/furniture-heights'
MAX = f'{BANK}/downloads/max-script'
CSV = f'{BANK}/downloads/furniture-csv'
REMOVED = {'removed': True}
BOM = b'\xef\xbb\xbf'
CASES = APP / 'packages' / 'viewer' / 'test' / 'fixtures' / 'furniture' / 'close-removed.cases.json'
PRES = read_json(FIXTURES / 'presentation' / 'bank-sampeng-v2.json')
quiet = {'log': lambda _line: None}


# ---------------------------------------------------------------------------------------------------- helpers
def err(r, status: int, code: str) -> dict:
    assert r.status_code == status, (r.status_code, r.text[:300])
    body = r.json()
    assert set(body) == {'error'} and body['error']['code'] == code and body['error']['message'], body
    return body['error']


def edits(*ids: str) -> dict[str, dict[str, bool]]:
    return {pid: dict(REMOVED) for pid in ids}


def vdir(data: Path, project_id: str, n: int) -> Path:
    return data / 'projects' / project_id / 'versions' / str(n)


def model_of(data: Path, project_id: str, n: int) -> dict:
    return read_json(vdir(data, project_id, n) / 'model.json')  # type: ignore[return-value]


def standing_on(model: dict, pid: str) -> list[str]:
    return [p['id'] for p in model['furniture'] if p['on'] == pid]


def piece(model: dict, pid: str) -> dict:
    return next(p for p in model['furniture'] if p['id'] == pid)


def csv_order(model: dict, ids) -> list[str]:
    """The CSV's row order, written out here (not piece_edits.order): floor in model order, kind in table order, id."""
    floors = [f['key'] for f in model['floors']]
    kinds = [k['key'] for k in model['furnitureKinds']]
    return sorted(set(ids), key=lambda i: (floors.index(piece(model, i)['floor']), kinds.index(piece(model, i)['kind']), i))


def golden_minus(golden: bytes, removed) -> bytes:
    """A CSV golden without the rows of `removed` (an id is the row's first field; the header's starts with the BOM)."""
    rows = golden.split(b'\r\n')
    return b'\r\n'.join(r for r in rows if r.split(b',')[0].decode('utf-8') not in set(removed))


def max_calls(script: bytes, prefix: str) -> list[tuple[int, str, str]]:
    """(line index, Max object name, piece id) of each furnBox call, read by splitting on the quotes (names never hold one)."""
    out = []
    for i, line in enumerate(script.split(b'\n')):
        if line.startswith(f'    {prefix}_furnBox "'.encode()):
            parts = line.decode('utf-8').split('"')
            out.append((i, parts[3], parts[5]))
    return out


def add_piece(model: dict, src: str, new_id: str, **change: Any) -> dict:
    """A copy of piece `src` as `new_id` (its kind's count + 1), with `change` applied."""
    p = {**copy.deepcopy(piece(model, src)), 'id': new_id, **change}
    model['furniture'].append(p)
    next(k for k in model['furnitureKinds'] if k['key'] == p['kind'])['count'] += 1
    return p


# ---------------------------------------------------------------------------------------------------- the record, PUT, GET
def test_put_saves_closed_ordered_edits_and_every_reader_shows_them(client: TestClient, data_copy: Path,
                                                                    template_file: Path) -> None:
    assert client.get(HEIGHTS).json() == {'heights': {}, 'pieceEdits': {}, 'revision': 0, 'updatedAt': None}
    model = model_of(data_copy, 'bank-sampeng', 2)
    deps = standing_on(model, 'L1-table-001')
    assert deps == ['L1-computer-002', 'L1-phone-001']
    r = client.put(HEIGHTS, json={'heights': {'table': 600}, 'pieceEdits': edits('L2-seat-003', 'L1-table-001')})
    body = r.json()
    want = csv_order(model, ['L1-table-001', *deps, 'L2-seat-003'])
    assert r.status_code == 200 and list(body['pieceEdits']) == want and body['pieceEdits'] == edits(*want)
    assert body['heights'] == {'table': 600} and body['revision'] == 1
    assert client.get(HEIGHTS).json() == body
    assert client.get(BANK).json()['overrides'] == body
    path = vdir(data_copy, 'bank-sampeng', 2) / 'overrides.json'
    raw = path.read_bytes()
    saved = loads_strict(raw)
    assert list(saved) == ['format', 'heights', 'pieceEdits', 'revision', 'updatedAt'] and raw == dumps_pretty(saved)
    assert saved['pieceEdits'] == body['pieceEdits'] and list(saved['pieceEdits']) == want
    with make_client(data_copy, template_file) as fresh:                    # on disk, not only cached
        assert fresh.get(HEIGHTS).json() == body


def test_left_out_keeps_the_edits_and_an_empty_map_clears_them(client: TestClient, data_copy: Path) -> None:
    path = vdir(data_copy, 'bank-sampeng', 2) / 'overrides.json'
    assert client.put(HEIGHTS, json={'heights': {}, 'pieceEdits': edits('L2-seat-003')}).status_code == 200
    r = client.put(HEIGHTS, json={'heights': {'seat': 300}})                  # a heights-only save keeps them
    assert r.json()['pieceEdits'] == edits('L2-seat-003') and r.json()['revision'] == 2
    r = client.put(HEIGHTS, json={'heights': {'seat': 300}, 'pieceEdits': None})   # null: as left out
    assert r.json()['pieceEdits'] == edits('L2-seat-003') and r.json()['revision'] == 3
    r = client.put(HEIGHTS, json={'heights': {'seat': 300}, 'pieceEdits': {}})
    body = r.json()
    assert body['pieceEdits'] == {} and body['revision'] == 4
    # the file is byte for byte what a heights-only save writes: no pieceEdits key at all
    assert path.read_bytes() == dumps_pretty({'format': 'walkthrough-overrides/1', 'heights': {'seat': 300}, 'revision': 4,
                                              'updatedAt': body['updatedAt']})
    # an edit that removes nothing is dropped
    r = client.put(HEIGHTS, json={'heights': {}, 'pieceEdits': {'L2-seat-003': {'removed': False}, 'L2-seat-004': {}}})
    assert r.status_code == 200 and r.json()['pieceEdits'] == {} and 'pieceEdits' not in read_json(path)


def test_a_dependent_alone_and_the_closure(client: TestClient, data_copy: Path) -> None:
    model = model_of(data_copy, 'bank-sampeng', 2)
    r = client.put(HEIGHTS, json={'heights': {}, 'pieceEdits': edits('L1-computer-002')})
    assert list(r.json()['pieceEdits']) == ['L1-computer-002']               # the table under it stays
    supports = sorted({p['on'] for p in model['furniture'] if p['on']})
    dependents = [p['id'] for p in model['furniture'] if p['on']]
    r = client.put(HEIGHTS, json={'heights': {}, 'pieceEdits': edits(*reversed(supports))})
    assert list(r.json()['pieceEdits']) == csv_order(model, [*supports, *dependents])
    err(client.put(f'{P}/bank-sampeng/versions/1/furniture-heights', json={'heights': {}, 'pieceEdits': edits('x')}), 404,
        'no_furniture')


def test_invalid_piece_edits(client: TestClient) -> None:
    e = err(client.put(HEIGHTS, json={'heights': {}, 'pieceEdits': {'L1-table-001': REMOVED, 'L9-ghost-001': REMOVED,
                                                                     'zz': {'removed': False}}}), 422, 'invalid_piece_edits')
    assert e['details'] == {'unknownIds': ['L9-ghost-001', 'zz'], 'count': 2}
    many = {f'ghost-{i:03d}': REMOVED for i in range(25)}
    e = err(client.put(HEIGHTS, json={'heights': {}, 'pieceEdits': many}), 422, 'invalid_piece_edits')
    assert e['details'] == {'unknownIds': sorted(many)[:20], 'count': 25} and e['message'].endswith('and 5 more')
    # the heights are checked first (invalid_heights as before)
    err(client.put(HEIGHTS, json={'heights': {'spaceship': 600}, 'pieceEdits': {'zz': REMOVED}}), 422, 'invalid_heights')
    # a malformed edit is FastAPI's own 422 (HTTPValidationError): a value that is not exactly a boolean, an unknown field
    # (a later step's client: refused, never silently dropped), a value that is not an object
    for bad in ({'L1-table-001': {'removed': 'yes'}}, {'L1-table-001': {'removed': 1}}, {'L1-table-001': {'kind': 'seat'}},
                {'L1-table-001': {'removed': True, 'kind': 'seat'}}, {'L1-table-001': True}, {'L1-table-001': None}, [],
                'all'):
        r = client.put(HEIGHTS, json={'heights': {}, 'pieceEdits': bad})
        assert r.status_code == 422 and 'detail' in r.json(), bad
    assert client.get(HEIGHTS).json()['revision'] == 0                       # nothing was saved


def test_412_details_carry_the_live_edits_only_when_there_are_any(client: TestClient) -> None:
    a = client.put(HEIGHTS, json={'heights': {}, 'pieceEdits': edits('L1-table-001')}, headers={'If-Match': '"0"'})
    assert a.status_code == 200 and len(a.json()['pieceEdits']) == 3
    e = err(client.put(HEIGHTS, json={'heights': {'table': 600}}, headers={'If-Match': '"0"'}), 412, 'revision_conflict')
    assert e['details'] == {'revision': 1, 'heights': {}, 'updatedAt': a.json()['updatedAt'],
                            'pieceEdits': a.json()['pieceEdits']}
    b = client.put(HEIGHTS, json={'heights': {'seat': 300}, 'pieceEdits': {}}, headers={'If-Match': '"1"'})
    assert b.status_code == 200
    e = err(client.put(HEIGHTS, json={'heights': {}}, headers={'If-Match': '"1"'}), 412, 'revision_conflict')
    assert e['details'] == {'revision': 2, 'heights': {'seat': 300}, 'updatedAt': b.json()['updatedAt']}   # as before BX


def test_an_odd_file_is_read_leniently_everywhere(client: TestClient, data_copy: Path) -> None:
    """A hand-edited, odd or later step's overrides.json: GET, getVersion, the 412, the CSV and the Max script keep only
    model ids whose `removed` is exactly true (closed), and never answer 500."""
    model = model_of(data_copy, 'bank-sampeng', 2)
    path = vdir(data_copy, 'bank-sampeng', 2) / 'overrides.json'
    path.write_bytes(dumps_pretty({'format': 'walkthrough-overrides/1', 'heights': {}, 'pieceEdits': {
        'L1-table-001': {'removed': True, 'kind': 'seat'},          # a later step's field beside it: the edit counts
        'L9-ghost-001': {'removed': True},                          # no such piece
        'L2-seat-003': {'removed': 'yes'}, 'L2-seat-004': 7, 'L2-seat-005': None, 'L2-seat-006': {'removed': False}},
        'revision': 5, 'updatedAt': '2026-11-16T09:12:03Z'}))
    want = edits(*csv_order(model, ['L1-table-001', *standing_on(model, 'L1-table-001')]))
    assert client.get(HEIGHTS).json()['pieceEdits'] == want
    assert client.get(BANK).json()['overrides']['pieceEdits'] == want
    csv = client.get(CSV)
    assert csv.status_code == 200 and csv.content == golden_minus((FIXTURES / 'csv' / 'bank-v2.csv').read_bytes(), want)
    stored = (vdir(data_copy, 'bank-sampeng', 2) / 'downloads' / 'Bangkok_Bank_Sampeng.ms').read_bytes()
    ms = client.get(MAX)
    assert ms.status_code == 200
    assert [i for _, _, i in max_calls(ms.content, 'BB')] == [i for _, _, i in max_calls(stored, 'BB') if i not in want]
    e = err(client.put(HEIGHTS, json={'heights': {}}, headers={'If-Match': '"0"'}), 412, 'revision_conflict')
    assert e['details']['pieceEdits'] == want
    # a heights-only save keeps the file's edits as they are (the store does not know the model; readers filter)
    assert client.put(HEIGHTS, json={'heights': {'seat': 300}}).json()['pieceEdits'] == want
    assert read_json(path)['pieceEdits']['L9-ghost-001'] == REMOVED
    for value in (None, {}):                                         # null or {} in the file: no edits
        path.write_bytes(dumps_pretty({'format': 'walkthrough-overrides/1', 'heights': {}, 'pieceEdits': value,
                                       'revision': 9, 'updatedAt': '2026-11-16T09:12:04Z'}))
        assert client.get(HEIGHTS).json()['pieceEdits'] == {}
        assert client.get(MAX).content == stored


# ---------------------------------------------------------------------------------------------------- the CSV
@pytest.mark.parametrize('project_id, n, golden, support', [
    ('bank-sampeng', 2, 'bank-v2', 'L1-table-001'),
    ('presidential-suite', 1, 'suite', 'suite-coffee-table-002'),
], ids=['bank-v2', 'suite'])
def test_the_csv_is_its_golden_minus_the_deleted_rows(client: TestClient, data_copy: Path, project_id: str, n: int,
                                                      golden: str, support: str) -> None:
    model = model_of(data_copy, project_id, n)
    used = {p['on'] for p in model['furniture'] if p['on']}
    alone = next(p['id'] for p in model['furniture'] if not p['on'] and p['id'] not in used)
    url = f'{P}/{project_id}/versions/{n}'
    r = client.put(f'{url}/furniture-heights', json={'heights': {}, 'pieceEdits': edits(support, alone)})
    removed = set(r.json()['pieceEdits'])
    assert removed == {support, alone, *standing_on(model, support)} and len(standing_on(model, support)) >= 2
    csv = client.get(f'{url}/downloads/furniture-csv')
    assert csv.status_code == 200 and csv.content == golden_minus((FIXTURES / 'csv' / f'{golden}.csv').read_bytes(), removed)


def test_the_csv_with_heights_and_deletions(client: TestClient) -> None:
    r = client.put(HEIGHTS, json={'heights': {'table': 600, 'seat': 300, 'cabinet': 1000},
                                  'pieceEdits': edits('L1-table-001', 'L2-seat-003')})
    removed = set(r.json()['pieceEdits'])
    assert client.get(CSV).content == golden_minus((FIXTURES / 'csv' / 'bank-v2-typed.csv').read_bytes(), removed)
    assert client.put(HEIGHTS, json={'heights': {}, 'pieceEdits': {}}).status_code == 200      # Restore all
    assert client.get(CSV).content == (FIXTURES / 'csv' / 'bank-v2.csv').read_bytes()


# ---------------------------------------------------------------------------------------------------- the 3ds Max script
def _stored_scripts(seeded: Path) -> list[tuple[str, Path]]:
    out = [(f'{pid}-v{n}', vdir(seeded, pid, n)) for pid, n in (('bank-sampeng', 1), ('bank-sampeng', 2),
                                                                 ('presidential-suite', 1), ('hotel-lobby', 1))]
    # the owner's two uploaded versions in app/data (TB, PSL), READ ONLY, when they are there
    for pid in ('test-bank', 'presidential-suite-layout'):
        d = APP / 'data' / 'projects' / pid / 'versions' / '1'
        if (d / 'version.json').is_file():
            out.append((f'app-data-{pid}-v1', d))
    return out


def test_every_model_piece_has_exactly_one_max_line(seeded: Path) -> None:
    """The filter's premise, on every stored script (BB v1 / v2, PS, HL and, when app/data has them, TB and PSL): each
    model piece has exactly one furnBox line, carrying its id, and there is no other; deleting a support with what stands
    on it and one more piece leaves exactly their lines out and adds line 3."""
    scripts = _stored_scripts(seeded)
    prefixes = []
    for name, d in scripts:
        model = read_json(d / 'model.json')
        script = (d / 'downloads' / read_json(d / 'version.json')['downloads']['maxScript']).read_bytes()
        px = model['maxPrefix']
        prefixes.append(px)
        calls = max_calls(script, px)
        assert Counter(i for _, _, i in calls) == Counter(p['id'] for p in model.get('furniture') or []), name
        assert piece_edits.max_script_ids(script, px) == [i for _, _, i in calls], name
        if not model.get('furniture'):
            assert b'_furnAll' not in script, name                     # bank v1: no furniture functions at all
            continue
        assert f'fn {px}_furnAll =\r\n'.encode() in script, name
        used = [p['on'] for p in model['furniture'] if p['on']]
        alone = next(p['id'] for p in model['furniture'] if not p['on'] and p['id'] not in used)
        removed = piece_edits.live(model, edits(*used[:1], alone))
        out = piece_edits.filter_max_script(script, px, removed)
        lines, before = out.split(b'\n'), script.split(b'\n')
        assert len(lines) == len(before) - len(removed) + 1 and lines[:2] == before[:2], name
        assert lines[2].startswith(f'-- {len(removed)} furniture box'.encode()) and lines[2].endswith(b'\r'), name
        assert [i for _, _, i in max_calls(out, px)] == [i for _, _, i in calls if i not in removed], name
    assert {'BB', 'PS', 'HL'} <= set(prefixes)


def test_max_script_without_deletions_is_the_stored_file(client: TestClient) -> None:
    stored = (PROTOTYPES / 'bank_test' / 'Bangkok_Bank_Sampeng.ms').read_bytes()
    keys = ('content-type', 'content-disposition', 'content-length', 'etag', 'last-modified')

    def get() -> dict:
        r = client.get(MAX)
        assert r.status_code == 200 and r.content == stored
        return {k: r.headers[k] for k in keys}                                 # a FileResponse: etag and last-modified
    first = get()
    assert client.put(HEIGHTS, json={'heights': {'table': 600}}).status_code == 200     # heights only: the same file
    assert get() == first
    assert client.put(HEIGHTS, json={'heights': {}, 'pieceEdits': edits('L2-seat-003')}).status_code == 200
    assert client.get(MAX).content != stored
    assert client.put(HEIGHTS, json={'heights': {}, 'pieceEdits': {}}).status_code == 200  # Restore all
    assert get() == first


def test_max_script_with_deletions(client: TestClient, data_copy: Path) -> None:
    stored = (vdir(data_copy, 'bank-sampeng', 2) / 'downloads' / 'Bangkok_Bank_Sampeng.ms').read_bytes()
    before = client.get(MAX)
    r = client.put(HEIGHTS, json={'heights': {'table': 600}, 'pieceEdits': edits('L1-table-001', 'L2-seat-003')})
    removed = list(r.json()['pieceEdits'])
    assert len(removed) == 4
    ms = client.get(MAX)
    assert ms.status_code == 200 and ms.headers['content-type'] == 'text/plain; charset=utf-8'
    assert ms.headers['content-disposition'] == before.headers['content-disposition']      # Bangkok_Bank_Sampeng_v2.ms
    calls = max_calls(stored, 'BB')
    gone = [(i, name) for i, name, pid in calls if pid in removed]
    assert len(gone) == 4
    comment = ('-- 4 furniture boxes deleted in the walkthrough app are left out: '
               + ', '.join(name for _, name in gone)).encode() + b'\r'
    lines = stored.split(b'\n')
    dropped = {i for i, _ in gone}
    assert ms.content == b'\n'.join([*lines[:2], comment, *(x for i, x in enumerate(lines) if i >= 2 and i not in dropped)])
    out = ms.content.split(b'\r\n')
    assert out[1] == stored.split(b'\r\n')[1] and b'(model data c3a9408304a2)' in out[1]       # line 2: the stamp
    assert b'BB_L1_Furn_table_001' in out[2] and b'BB_L1_Furn_computer_002' in out[2]
    assert ms.content.count(b'\r\n') == stored.count(b'\r\n') - 4 + 1 and b'\n' not in ms.content.replace(b'\r\n', b'')


def test_a_max_script_that_does_not_match_its_model_is_refused(client: TestClient, data_copy: Path) -> None:
    path = vdir(data_copy, 'bank-sampeng', 2) / 'downloads' / 'Bangkok_Bank_Sampeng.ms'
    stored = path.read_bytes()
    lines = stored.split(b'\n')
    at = next(i for i, _, pid in max_calls(stored, 'BB') if pid == 'L2-seat-003')
    assert client.put(HEIGHTS, json={'heights': {}, 'pieceEdits': edits('L2-seat-003')}).status_code == 200
    for broken in (b'\n'.join(lines[:at] + lines[at + 1:]),                     # its line is missing
                   b'\n'.join(lines[:at + 1] + lines[at:]),                     # it has two
                   stored.replace(b'    BB_furnBox "', b'    XX_furnBox "')):   # another prefix: no line matches
        path.write_bytes(broken)
        e = err(client.get(MAX), 500, 'store_error')
        assert e['message'].startswith('the 3ds Max script does not match its model')
    path.write_bytes(stored)
    assert client.get(MAX).status_code == 200


def test_every_box_deleted(client: TestClient, data_copy: Path) -> None:
    url = f'{P}/hotel-lobby/versions/1'
    model = model_of(data_copy, 'hotel-lobby', 1)
    ids = [p['id'] for p in model['furniture']]
    r = client.put(f'{url}/furniture-heights', json={'heights': {}, 'pieceEdits': edits(*ids)})
    assert r.status_code == 200 and len(r.json()['pieceEdits']) == len(ids) == 159
    golden = (FIXTURES / 'csv' / 'hotel.csv').read_bytes()
    csv = client.get(f'{url}/downloads/furniture-csv').content
    assert csv == golden_minus(golden, ids) == golden.split(b'\r\n')[0] + b'\r\n' and csv.startswith(BOM)
    stored = (vdir(data_copy, 'hotel-lobby', 1) / 'downloads' / 'Hotel_Lobby.ms').read_bytes()
    ms = client.get(f'{url}/downloads/max-script').content
    assert b'fn HL_furnAll =\r\n(\r\n)\r\n' in ms and not max_calls(ms, 'HL')                  # an empty body
    names = [name for _, name, _ in max_calls(stored, 'HL')]
    assert ms.split(b'\r\n')[2].decode() == ('-- 159 furniture boxes deleted in the walkthrough app are left out: '
                                             + ', '.join(names[:30]) + ', and 129 more')
    detail = client.get(url).json()
    assert detail['hasFurniture'] and detail['counts']['furniture'] == 159          # the built counts stay as built


# ---------------------------------------------------------------------------------------------------- the offline file
def test_the_offline_file_embeds_the_edits(client: TestClient, data_copy: Path) -> None:
    r = client.put(HEIGHTS, json={'heights': {'table': 640}, 'pieceEdits': edits('L1-table-001')})
    page = client.get(f'{BANK}/downloads/offline-html').content.decode('utf-8')
    p = parse_page(page)
    assert p['overrides'] == read_json(vdir(data_copy, 'bank-sampeng', 2) / 'overrides.json')
    assert p['overrides']['pieceEdits'] == r.json()['pieceEdits']
    assert client.put(HEIGHTS, json={'heights': {}, 'pieceEdits': {}}).status_code == 200
    p = parse_page(client.get(f'{BANK}/downloads/offline-html').content.decode('utf-8'))
    assert 'pieceEdits' not in p['overrides']                                          # Restore all: the key is gone


def test_node_and_python_give_the_same_bytes_with_edits(data_copy: Path, tmp_path: Path) -> None:
    if not BUILT_TEMPLATE.is_file():
        missing(f'{BUILT_TEMPLATE} is missing (npm run build:offline:template)')
    store = LocalStore(data_copy)
    store.write_overrides('bank-sampeng', 2, {'table': 600},
                          piece_edits=edits('L1-computer-002', 'L1-phone-001', 'L1-table-001'))
    template = tmp_path / 'viewer-template.html'
    template.write_bytes(BUILT_TEMPLATE.read_bytes())
    assert len(compare_with_node(store, template, tmp_path / 'out')) == 5


# ---------------------------------------------------------------------------------------------------- carry-over (5.1)
@pytest.fixture
def bank() -> dict:
    return read_json(FIXTURES / 'models' / 'bank-v2.model.json')  # type: ignore[return-value]


def new_store(tmp_path: Path) -> LocalStore:
    store = LocalStore(tmp_path / 'data')
    store.create_project(NewProject(id='carry', name='Carry', short_name='carry', source_kind='cad'))
    return store


def add_version(store: LocalStore, model: dict, carry: int | None = None) -> int:
    return store.create_version('carry', VersionDraft(label='v', source_kind='cad', source_files=[],
                                                      model_json=dumps_compact(model), stages_json=None, presentation=PRES,
                                                      carry_overrides_from=carry)).version


def carry_case(tmp_path: Path, old: dict, removed: list[str], new: dict,
               heights: dict | None = None) -> tuple[LocalStore, dict | None, dict | None]:
    """v1 = old with `removed` deleted (closed), v2 = new saved with the carry tick: (store, carried-edits.json or None,
    v2's overrides.json or None)."""
    store = new_store(tmp_path)
    add_version(store, old)
    store.write_overrides('carry', 1, heights or {}, piece_edits=piece_edits.live(old, edits(*removed)))
    assert add_version(store, new, carry=1) == 2
    d = store.version_dir('carry', 2)
    record = read_json(d / 'source' / 'carried-edits.json') if (d / 'source' / 'carried-edits.json').is_file() else None
    o = read_json(d / 'overrides.json') if (d / 'overrides.json').is_file() else None
    return store, record, o  # type: ignore[return-value]


def why(record: dict) -> dict[str, str]:
    return {r['id']: r['why'] for r in record['notCarried']}


def floor_name(model: dict, key: str) -> str:
    return next(f['name'] for f in model['floors'] if f['key'] == key)


def kind_label(model: dict, key: str) -> str:
    return next(k['label'] for k in model['furnitureKinds'] if k['key'] == key)


def row_of(model: dict, pid: str, why_: str, **more: str) -> dict:
    """A not-carried row of carried-edits.json for the old piece `pid`, its floor and kind named as `model` names them."""
    p = piece(model, pid)
    return {'id': pid, 'floor': p['floor'], 'kind': p['kind'], 'family': p['family'], 'why': why_,
            'floorName': floor_name(model, p['floor']), 'kindLabel': kind_label(model, p['kind']), **more}


def box_of(model: dict, pid: str, reason: str, **more: str) -> dict:
    """The version detail's line for the old piece `pid` (carriedEdits.boxes)."""
    p = piece(model, pid)
    return {'kind': kind_label(model, p['kind']), 'family': p['family'], 'floor': floor_name(model, p['floor']),
            'reason': reason, **more}


def test_the_same_drawing_carries_every_deletion(tmp_path: Path, bank: dict, template_file: Path) -> None:
    alone = standing_on(bank, 'L1-table-002')[0]                    # deleted on its own: a top although it stands on one
    store, record, o = carry_case(tmp_path, bank, ['L1-table-001', 'L2-seat-003', alone], bank, {'table': 600})
    tops = csv_order(bank, ['L1-table-001', 'L2-seat-003', alone])
    assert record == {'format': 'walkthrough-carried-edits/1', 'from': 1, 'carried': {t: t for t in tops},
                      'cascaded': standing_on(bank, 'L1-table-001'), 'notCarried': []}
    assert list(record['carried']) == tops
    assert o is not None and o['heights'] == {'table': 600} and o['revision'] == 1
    assert o['pieceEdits'] == read_json(store.version_dir('carry', 1) / 'overrides.json')['pieceEdits']
    with make_client(store.root, template_file) as c:
        d = c.get(f'{P}/carry/versions/2').json()
        assert 'carriedEdits' not in d and d['overrides']['pieceEdits'] == o['pieceEdits']
        assert 'carriedEdits' not in c.get(f'{P}/carry/versions/1').json()


def test_a_moved_resized_or_turned_box_is_not_carried(tmp_path: Path, bank: dict, template_file: Path) -> None:
    old, new = copy.deepcopy(bank), copy.deepcopy(bank)
    piece(new, 'L2-seat-001')['x'] += 0.011                          # 11 mm: another place
    piece(new, 'L2-seat-002')['x'] += 0.010                          # 10 mm: the same place
    piece(new, 'L2-seat-003')['y'] -= 0.011
    piece(new, 'L2-seat-004')['w'] += 0.011
    piece(old, 'L1-tv-001')['rot'], piece(new, 'L1-tv-001')['rot'] = 0.1, 179.8            # 0.3 degrees modulo 180
    piece(old, 'L1-atm-003')['rot'], piece(new, 'L1-atm-003')['rot'] = 0.1, 0.7             # 0.6 degrees
    piece(old, 'L2-seat-009')['rot'], piece(new, 'L2-seat-009')['rot'] = 0.2, 89.9           # square: modulo 90
    piece(old, 'L1-tv-002')['rot'], piece(new, 'L1-tv-002')['rot'] = 0.2, 89.9               # not square: 89.7
    assert piece(bank, 'L2-seat-009')['w'] == piece(bank, 'L2-seat-009')['d']
    removed = ['L2-seat-001', 'L2-seat-002', 'L2-seat-003', 'L2-seat-004', 'L1-tv-001', 'L1-atm-003', 'L2-seat-009',
               'L1-tv-002']
    store, record, o = carry_case(tmp_path, old, removed, new)
    assert record is not None and o is not None
    assert record['carried'] == {i: i for i in csv_order(bank, ['L2-seat-002', 'L1-tv-001', 'L2-seat-009'])}
    assert why(record) == {i: 'no match' for i in ('L2-seat-001', 'L2-seat-003', 'L2-seat-004', 'L1-atm-003', 'L1-tv-002')}
    assert [r['id'] for r in record['notCarried']] == csv_order(bank, why(record))
    assert record['notCarried'][0] == {'id': 'L1-atm-003', 'floor': 'L1', 'kind': 'atm',
                                       'family': piece(bank, 'L1-atm-003')['family'], 'why': 'no match',
                                       'floorName': 'Level 1', 'kindLabel': 'ATM / kiosk'}
    assert list(o['pieceEdits']) == list(record['carried'].values())
    with make_client(store.root, template_file) as c:                # the main session's decision of 16 Nov, point 2
        assert c.get(f'{P}/carry/versions/2').json()['carriedEdits'] == {
            'from': 1, 'notCarried': 5,                              # and which boxes (fix of 17 Nov)
            'boxes': [box_of(bank, r['id'], 'not found in the new drawing') for r in record['notCarried']]}


def test_duplicates_are_never_carried(tmp_path: Path, bank: dict) -> None:
    # a twin in the new drawing (5 mm away): two matches
    new = copy.deepcopy(bank)
    add_piece(new, 'L2-seat-005', 'L2-seat-901', x=piece(bank, 'L2-seat-005')['x'] + 0.005)
    _, record, o = carry_case(tmp_path / 'a', bank, ['L2-seat-005'], new)
    assert record is not None and record['carried'] == {} and why(record) == {'L2-seat-005': '2 matches'} and o is None
    # two old duplicates, one deleted, one left in the new drawing: nothing is carried (it may be the kept one)
    old = copy.deepcopy(bank)
    add_piece(old, 'L2-seat-006', 'L2-seat-902', x=piece(bank, 'L2-seat-006')['x'] + 0.005)
    for gone in ('L2-seat-006', 'L2-seat-902'):
        _, record, o = carry_case(tmp_path / gone, old, [gone], bank)
        assert record is not None and record['carried'] == {} and why(record) == {gone: 'matches 2 old pieces'}
        assert record['notCarried'][0]['newId'] == 'L2-seat-006'     # the one box of the new drawing in its place
        assert o is None                                             # nothing carried, no heights: no overrides.json


def test_a_renumbered_box_maps_to_its_new_id(tmp_path: Path, bank: dict) -> None:
    new = copy.deepcopy(bank)
    a, b = piece(new, 'L2-seat-014'), piece(new, 'L2-seat-015')
    a['id'], b['id'] = 'L2-seat-015', 'L2-seat-014'                  # the ranks shifted: the two chairs swap ids
    piece(new, 'L2-seat-016')['id'] = 'L2-seat-903'
    _, record, o = carry_case(tmp_path, bank, ['L2-seat-014', 'L2-seat-016'], new)
    assert record is not None and o is not None
    assert record['carried'] == {'L2-seat-014': 'L2-seat-015', 'L2-seat-016': 'L2-seat-903'}
    assert o['pieceEdits'] == edits('L2-seat-015', 'L2-seat-903')   # never the bare id: L2-seat-014 is another chair now


# Fixes after the review (17 Nov 2026): floors by level and stack, never by key; the kind is not compared.
def _rekeyed(model: dict, rekey: dict[str, str]) -> dict:
    """A copy of `model` whose floors have other keys (levels as they were) and whose pieces follow them (ids and `on`
    start with the floor key, as the builder makes them): what a new draft gives the same building after a floor was
    added in front or the floors were reordered, since it takes the latest model's keys by list position
    (propose._from_model, drafts/adopt.py)."""
    new = copy.deepcopy(model)
    new['floors'] = [{**f, 'key': rekey[f['key']]} for f in model['floors']]
    for p in new['furniture']:
        for k in ('id', 'on'):
            if p.get(k):
                p[k] = rekey[p['floor']] + p[k][len(p['floor']):]
        p['floor'] = rekey[p['floor']]
    return new


def test_floors_are_matched_by_level_and_stack_never_by_key(bank: dict) -> None:
    old = copy.deepcopy(bank)
    add_piece(old, 'L2-seat-003', 'L1-seat-901', floor='L1')          # the same chair in the same place on Level 1
    # the floors' keys swapped (levels as before): Level 2 is 'L1' now, Level 1 'L2'
    new = _rekeyed(old, {'L1': 'L2', 'L2': 'L1'})
    r = piece_edits.carry(old, edits('L2-seat-003'), new)
    assert r.carried == {'L2-seat-003': 'L1-seat-003'} and r.not_carried == []    # Level 2's chair, not 'L2-seat-901'
    assert piece(new, 'L1-seat-003')['x'] == piece(old, 'L2-seat-003')['x'] and floor_name(new, 'L1') == 'Level 2'
    # a floor added in front (a basement): the old keys move up one by position
    new = _rekeyed(old, {'L1': 'L2', 'L2': 'L3'})
    new['floors'].insert(0, {**new['floors'][0], 'key': 'L1', 'name': 'Basement', 'level': -3.7})
    r = piece_edits.carry(old, edits('L2-seat-003', 'L1-table-001'), new)
    assert r.carried == {'L1-table-001': 'L2-table-001', 'L2-seat-003': 'L3-seat-003'} and r.not_carried == []
    assert r.cascaded == [f'L2{pid[2:]}' for pid in standing_on(old, 'L1-table-001')]


def test_floor_map() -> None:
    def f(key: str, level: float, stack: str | None = None) -> dict:
        return {'key': key, 'level': level, **({'stack': stack} if stack else {})}
    old = {'floors': [f('A', 0), f('B', 3.7), f('C', 3.7, 'annex'), f('D', 7.4)]}
    new = {'floors': [f('X', 0.010), f('Y', 3.7, 'main'), f('Z', 3.7, 'annex'), f('W', 7.411)]}
    assert piece_edits.floor_map(old, new) == {'A': 'X', 'B': 'Y', 'C': 'Z'}       # 10 mm is the same level, 11 mm not
    assert piece_edits.floor_map({'floors': [f('A', 0)]}, {'floors': [f('X', 0), f('Y', 0.005)]}) == {}   # two: neither
    assert piece_edits.floor_map({'floors': [f('A', 0), f('B', 0.005)]}, {'floors': [f('X', 0)]}) == {}
    assert piece_edits.floor_map({'floors': [f('A', 0, 'annex')]}, {'floors': [f('A', 0)]}) == {}         # another stack


def test_a_box_whose_floor_changed_is_not_carried(tmp_path: Path, bank: dict, template_file: Path) -> None:
    new = copy.deepcopy(bank)
    next(f for f in new['floors'] if f['key'] == 'L2')['level'] = 3.75            # Level 2 is 50 mm higher now
    store, record, o = carry_case(tmp_path, bank, ['L1-table-001', 'L2-seat-003'], new)
    assert record is not None and o is not None
    assert record['carried'] == {'L1-table-001': 'L1-table-001'}
    assert record['notCarried'] == [row_of(bank, 'L2-seat-003', 'floor changed')]
    assert 'L2-seat-003' not in o['pieceEdits']
    with make_client(store.root, template_file) as c:
        assert c.get(f'{P}/carry/versions/2').json()['carriedEdits'] == {
            'from': 1, 'notCarried': 1, 'boxes': [box_of(bank, 'L2-seat-003', 'its floor changed')]}


def test_a_kind_change_alone_still_carries(tmp_path: Path, bank: dict) -> None:
    """A family given a kind on the Check step (the reviewer's case: other -> seat): same floor, family, place and size,
    a new kind and so a new id. The deletion carries to the new id; the kind is not compared."""
    new = copy.deepcopy(bank)
    p = piece(new, 'L2-seat-003')
    p['kind'], p['id'] = 'sofa', 'L2-sofa-901'
    for k in new['furnitureKinds']:
        k['count'] += {'seat': -1, 'sofa': 1}.get(k['key'], 0)
    _, record, o = carry_case(tmp_path, bank, ['L2-seat-003'], new)
    assert record is not None and o is not None
    assert record['carried'] == {'L2-seat-003': 'L2-sofa-901'} and record['notCarried'] == []
    assert o['pieceEdits'] == edits('L2-sofa-901')


def test_only_tops_are_carried_and_the_new_closure_cascades(tmp_path: Path, bank: dict, template_file: Path) -> None:
    new = copy.deepcopy(bank)
    piece(new, 'L1-computer-002')['on'] = 'L1-table-002'             # the new drawing puts it on a kept table
    add_piece(new, 'L1-phone-001', 'L1-phone-901', x=piece(bank, 'L1-phone-001')['x'] + 0.2)   # a new piece on the table
    store, record, o = carry_case(tmp_path, bank, ['L1-table-001'], new)
    assert record is not None and o is not None
    assert record['carried'] == {'L1-table-001': 'L1-table-001'}
    assert record['cascaded'] == ['L1-phone-001', 'L1-phone-901']
    assert record['notCarried'] == [{'id': 'L1-computer-002', 'floor': 'L1', 'kind': 'computer',
                                     'family': piece(bank, 'L1-computer-002')['family'],
                                     'why': 'was on a deleted support', 'floorName': 'Level 1',
                                     'kindLabel': 'Computer / monitor', 'newId': 'L1-computer-002'}]
    assert o['pieceEdits'] == edits('L1-phone-001', 'L1-phone-901', 'L1-table-001')          # the computer stays
    with make_client(store.root, template_file) as c:
        assert c.get(f'{P}/carry/versions/2').json()['carriedEdits'] == {
            'from': 1, 'notCarried': 1,
            'boxes': [box_of(bank, 'L1-computer-002', 'it went with the box it stood on', newId='L1-computer-002')]}


def test_heights_only_carry_and_no_carry(tmp_path: Path, bank: dict) -> None:
    store = new_store(tmp_path)
    add_version(store, bank)
    store.write_overrides('carry', 1, {'table': 600})
    add_version(store, bank, carry=1)
    d = store.version_dir('carry', 2)
    assert read_json(d / 'overrides.json') == {'format': 'walkthrough-overrides/1', 'heights': {'table': 600}, 'revision': 1,
                                               'updatedAt': read_json(d / 'overrides.json')['updatedAt']}
    assert not (d / 'source').exists()
    store.write_overrides('carry', 2, {'table': 600}, piece_edits=edits('L2-seat-003'))
    add_version(store, bank)                                         # the carry tick off: nothing carried, no record
    assert not (store.version_dir('carry', 3) / 'overrides.json').exists()
    assert not (store.version_dir('carry', 3) / 'source').exists()
    with pytest.raises(ValueError, match='carried-edits record'):    # the record's name is the store's own
        store.create_version('carry', VersionDraft(label='v', source_kind='cad', source_files=[],
                                                   model_json=dumps_compact(bank), stages_json=None, presentation=PRES,
                                                   source={'carried-edits.json': b'{}'}))


@pytest.fixture
def fake() -> FakeJobRunner:
    return FakeJobRunner()


@pytest.fixture
def api(data_copy: Path, template_file: Path, fake: FakeJobRunner) -> Iterator[TestClient]:
    with make_client(data_copy, template_file, jobs=fake) as c:
        yield c


def test_a_version_saved_with_the_carry_tick_keeps_the_deletions(api: TestClient, data_copy: Path) -> None:
    """saveBuild with carryHeights (the web app's default): the fake worker builds the bank's model again, so every
    deletion of v2 carries into v3 (the same drawing), and v3's downloads leave them out."""
    r = api.put(HEIGHTS, json={'heights': {'table': 600}, 'pieceEdits': edits('L1-table-001', 'L2-seat-003')})
    saved = r.json()['pieceEdits']
    b = start(api, 'bank-sampeng')
    b = save_settings(api, b, bank_for(b) | {'options': {**bank_for(b)['options'], 'offset': [1.212, 0.348]}}).json()
    b = api.post(f'{b["url"]}/run', json={}).json()
    r = api.post(f'{b["url"]}/save', json={'label': '16 Nov 2026: carried', 'carryHeights': True, 'rememberMapping': False})
    assert r.status_code == 201, r.text[:400]
    v = r.json()
    assert v['version'] == 3 and v['overrides']['pieceEdits'] == saved and v['overrides']['heights'] == {'table': 600}
    assert 'carriedEdits' not in v                                   # everything carried: no note
    record = read_json(vdir(data_copy, 'bank-sampeng', 3) / 'source' / 'carried-edits.json')
    assert record['from'] == 2 and record['notCarried'] == []
    assert record['carried'] == {'L1-table-001': 'L1-table-001', 'L2-seat-003': 'L2-seat-003'}
    csv = api.get(f'{P}/bank-sampeng/versions/3/downloads/furniture-csv').content
    assert csv == api.get(CSV).content                               # v3's list is v2's (same model, edits and heights)
    assert not {row.split(b',')[0].decode() for row in csv.split(b'\r\n')} & set(saved)


# ---------------------------------------------------------------------------------------------------- the seed
def test_the_seed_keeps_the_edits_of_an_unchanged_model(data_copy: Path) -> None:
    store = LocalStore(data_copy)
    store.write_overrides('bank-sampeng', 2, {'table': 600},
                          piece_edits=edits('L1-computer-002', 'L1-phone-001', 'L1-table-001'))
    path = vdir(data_copy, 'bank-sampeng', 2) / 'overrides.json'
    kept = path.read_bytes()
    result = seed(PROTOTYPES, data_copy, force=True, **quiet)
    assert path.read_bytes() == kept and not result.remapped
    assert not (vdir(data_copy, 'bank-sampeng', 2) / 'source' / 'carried-edits.json').exists()
    seed(PROTOTYPES, data_copy, force=True, reset_overrides=True, **quiet)
    assert not path.exists()                                         # --reset-overrides drops them with the heights


def _house_with_a_moved_piece(tmp_path: Path, seeded: Path) -> tuple[Path, Path, LocalStore, str, str]:
    protos = tmp_path / 'prototypes'
    copy_prototype_files(protos)
    data = tmp_path / 'data'
    shutil.copytree(seeded, data)
    store = LocalStore(data)
    house = model_of(data, 'sukhumvit-house', 1)
    stays, moves = house['furniture'][0]['id'], house['furniture'][1]['id']
    store.write_overrides('sukhumvit-house', 1, {'bed': 500}, piece_edits=edits(stays, moves))
    src = protos / 'cad_test' / 'src' / 'furniture_house.json'
    fh = read_json(src)
    next(p for p in fh['furniture'] if p['id'] == moves)['x'] += 0.05            # the drawing changed: 50 mm
    src.write_bytes(dumps_compact(fh))
    return protos, data, store, stays, moves


def test_the_seed_remaps_the_edits_of_a_changed_model(tmp_path: Path, seeded: Path, template_file: Path) -> None:
    protos, data, store, stays, moves = _house_with_a_moved_piece(tmp_path, seeded)
    before = store.read_overrides('sukhumvit-house', 1)
    lines: list[str] = []
    result = seed(protos, data, force=True, log=lines.append)
    assert [(v.project_id, v.version) for v in result.remapped] == [('sukhumvit-house', 1)]
    d = vdir(data, 'sukhumvit-house', 1)
    o = read_json(d / 'overrides.json')
    assert o['pieceEdits'] == edits(stays) and o['heights'] == {'bed': 500} and o['revision'] == before.revision + 1
    old = read_json(vdir(seeded, 'sukhumvit-house', 1) / 'model.json')
    assert read_json(d / 'source' / 'carried-edits.json') == {
        'format': 'walkthrough-carried-edits/1', 'from': 1, 'carried': {stays: stays}, 'cascaded': [],
        'notCarried': [row_of(old, moves, 'no match')]}
    assert [x for x in lines if 'the model changed' in x] == [
        'sukhumvit-house v1: the model changed: deleted furniture boxes re-mapped, 1 carried, 0 with them, 1 not carried '
        '(source/carried-edits.json)']
    for other in ('bank-sampeng', 'hotel-lobby'):                    # the other versions' models did not change
        assert not (vdir(data, other, 1) / 'source' / 'carried-edits.json').exists()
    with make_client(data, template_file) as c:
        assert c.get(f'{P}/sukhumvit-house/versions/1').json()['carriedEdits'] == {
            'from': 1, 'notCarried': 1, 'boxes': [box_of(old, moves, 'not found in the new drawing')]}
    # the next --force (the model as it is now): both files kept as they are
    kept = (d / 'overrides.json').read_bytes(), (d / 'source' / 'carried-edits.json').read_bytes()
    assert not seed(protos, data, force=True, **quiet).remapped
    assert ((d / 'overrides.json').read_bytes(), (d / 'source' / 'carried-edits.json').read_bytes()) == kept


def test_the_seed_drops_odd_edits_when_the_model_changed(tmp_path: Path, seeded: Path) -> None:
    """Kept edits that name no live box of the old model (odd entries only) are dropped when the model changed, so they
    can never become live against the new model's ids; no carried-edits.json then (no deleted box to account for)."""
    protos, data, store, stays, _ = _house_with_a_moved_piece(tmp_path, seeded)
    path = vdir(data, 'sukhumvit-house', 1) / 'overrides.json'
    odd = {'L9-ghost-001': REMOVED, stays: {'removed': 'yes'}}
    path.write_bytes(dumps_pretty({'format': 'walkthrough-overrides/1', 'heights': {'bed': 500}, 'pieceEdits': odd,
                                   'revision': 3, 'updatedAt': '2026-11-16T09:12:03Z'}))
    lines: list[str] = []
    assert [v.project_id for v in seed(protos, data, force=True, log=lines.append).remapped] == ['sukhumvit-house']
    o = read_json(path)
    assert 'pieceEdits' not in o and o['heights'] == {'bed': 500} and o['revision'] == 4
    assert not (vdir(data, 'sukhumvit-house', 1) / 'source' / 'carried-edits.json').exists()
    assert 'sukhumvit-house v1: the model changed; its saved piece edits named no deleted box of the old model: dropped' \
        in lines
    assert store.read_overrides('sukhumvit-house', 1).piece_edits is None


def test_a_seed_that_cannot_remap_changes_nothing(tmp_path: Path, seeded: Path) -> None:
    protos, data, _, _, _ = _house_with_a_moved_piece(tmp_path, seeded)
    (vdir(data, 'sukhumvit-house', 1) / 'model.json').write_bytes(b'not json')
    before = tree(data)
    with pytest.raises(SeedError, match='cannot be read to re-map them'):
        seed(protos, data, force=True, **quiet)
    assert tree(data) == before and not list(data.rglob('.staging-*'))


# ---------------------------------------------------------------------------------------------------- the pure rules
def test_close_removed() -> None:
    pieces = [{'id': 't', 'on': None}, {'id': 'c', 'on': 't'}, {'id': 'p', 'on': 't'}, {'id': 'x', 'on': 'c'},
              {'id': 's', 'on': None}]
    assert piece_edits.close_removed(['t'], pieces) == {'t', 'c', 'p', 'x'}         # transitive
    assert piece_edits.close_removed(['c'], pieces) == {'c', 'x'}                   # never downwards
    assert piece_edits.close_removed(['s', 'p'], pieces) == {'s', 'p'}
    assert piece_edits.close_removed([], pieces) == set()


def _cases(doc: Any) -> list[dict]:
    """The viewer's case file (C-owned): a list of cases, or {cases: [...]}, each with its pieces ({id, on}), the ids
    removed and the closed result, under the names the file uses."""
    cases = doc.get('cases') if isinstance(doc, dict) else doc
    assert isinstance(cases, list) and cases, 'close-removed.cases.json: no list of cases'
    shared = doc.get('pieces') if isinstance(doc, dict) else None
    out = []
    for i, c in enumerate(cases):
        pieces = c.get('pieces') or c.get('furniture') or (c.get('model') or {}).get('furniture') or shared
        given = next((c[k] for k in ('ids', 'removed', 'remove', 'input', 'given') if k in c), None)
        want = next((c[k] for k in ('closed', 'expected', 'want', 'result', 'output') if k in c), None)
        assert isinstance(pieces, list) and isinstance(given, list) and isinstance(want, list), \
            f'close-removed.cases.json case {i}: its pieces, ids and closed result were not found ({sorted(c)})'
        out.append({'name': c.get('name') or c.get('title') or str(i), 'pieces': pieces, 'ids': given, 'closed': want})
    return out


def test_close_removed_against_the_viewers_case_file() -> None:
    """DESIGN 2.5: one rule in TypeScript (furniture/logic.ts closeRemoved) and one in Python, tested against the same
    case file (packages/viewer/test/fixtures/furniture/close-removed.cases.json, the viewer's)."""
    if not CASES.is_file():
        reason = f'{CASES.relative_to(APP).as_posix()} is missing (the viewer part of step BX writes it)'
        if os.environ.get('WT_INTEGRATION') == '1':
            pytest.fail(f'{reason}; WT_INTEGRATION=1: the shared closure cases must run')
        pytest.skip(reason)
    for case in _cases(read_json(CASES)):
        assert piece_edits.close_removed(case['ids'], case['pieces']) == set(case['closed']), case['name']


def test_order_and_live() -> None:
    m = {'floors': [{'key': 'B'}, {'key': 'A'}], 'furnitureKinds': [{'key': 'seat'}, {'key': 'desk'}],
         'furniture': [{'id': 'A-desk-001', 'floor': 'A', 'kind': 'desk', 'on': None},
                       {'id': 'A-seat-002', 'floor': 'A', 'kind': 'seat', 'on': None},
                       {'id': 'B-desk-001', 'floor': 'B', 'kind': 'desk', 'on': None},
                       {'id': 'B-seat-001', 'floor': 'B', 'kind': 'seat', 'on': 'B-desk-001'}]}
    assert piece_edits.order(m, ['zz', 'A-desk-001', 'B-desk-001', 'A-seat-002', 'A-seat-002']) == \
        ['B-desk-001', 'A-seat-002', 'A-desk-001', 'zz']
    assert list(piece_edits.live(m, {'B-desk-001': REMOVED, 'zz': REMOVED})) == ['B-seat-001', 'B-desk-001']
    for odd in (None, [], 'x', {}, {'A-desk-001': 'removed'}, {'A-desk-001': {'removed': 1}}):
        assert piece_edits.live(m, odd) == {}
    unknown = {'kind': '?', 'family': '', 'floor': '?', 'reason': 'not found in the new drawing'}
    assert piece_edits.carried_note({'format': 'walkthrough-carried-edits/1', 'from': 2, 'notCarried': [{}, {}]}) == \
        (2, 2, [unknown, unknown])
    # a row of a record written before the labels (16 Nov) names its floor and kind by key; an odd row loses its line only
    old_row = {'id': 'L2-seat-001', 'floor': 'L2', 'kind': 'seat', 'family': 'F', 'why': '2 matches'}
    assert piece_edits.carried_note({'format': 'walkthrough-carried-edits/1', 'from': 3, 'notCarried': [old_row, 7]}) == \
        (3, 2, [{'kind': 'seat', 'family': 'F', 'floor': 'L2', 'reason': '2 boxes in the new drawing stand in its place'}])
    assert [piece_edits.reason_text(w) for w in ('no match', 'floor changed', 'was on a deleted support', '3 matches',
                                                  'matches 2 old pieces', 'a later reason', None)] == [
        'not found in the new drawing', 'its floor changed', 'it went with the box it stood on',
        '3 boxes in the new drawing stand in its place', 'its box in the new drawing matches 2 old boxes', 'a later reason',
        'not found in the new drawing']
    for odd in (None, 'x', {'format': 'walkthrough-carried-edits/1', 'from': 2, 'notCarried': []},
                {'format': 'other', 'from': 2, 'notCarried': [{}]}, {'format': 'walkthrough-carried-edits/1', 'from': True,
                                                                     'notCarried': [{}]}):
        assert piece_edits.carried_note(odd) is None


def test_filter_max_script_alone() -> None:
    script = (b'-- title\r\n-- Same model (model data 0123456789ab).\r\n-- three\r\nfn XX_furnAll =\r\n(\r\n'
              b'    XX_furnBox "seat" "XX_L1_Furn_seat_001" 1 "L1-seat-001" "none" "none" [0,0]\r\n'
              b'    XX_furnBox "seat" "XX_L1_Furn_seat_002_A, B" 1 "L1-seat-002" "none" "none" [0,0]\r\n)\r\n')
    assert piece_edits.filter_max_script(script, 'XX', set()) == script
    assert piece_edits.filter_max_script(script, 'XX', {'L1-seat-002'}) == (
        b'-- title\r\n-- Same model (model data 0123456789ab).\r\n'
        b'-- 1 furniture box deleted in the walkthrough app is left out: XX_L1_Furn_seat_002_A, B\r\n'
        b'-- three\r\nfn XX_furnAll =\r\n(\r\n'
        b'    XX_furnBox "seat" "XX_L1_Furn_seat_001" 1 "L1-seat-001" "none" "none" [0,0]\r\n)\r\n')
    lf = piece_edits.filter_max_script(script.replace(b'\r\n', b'\n'), 'XX', {'L1-seat-001', 'L1-seat-002'})
    assert lf.split(b'\n')[2] == b'-- 2 furniture boxes deleted in the walkthrough app are left out: XX_L1_Furn_seat_001, ' \
                                 b'XX_L1_Furn_seat_002_A, B' and b'\r' not in lf
    for prefix, removed in (('XX', {'L1-seat-003'}), ('YY', {'L1-seat-001'}), ('X', {'L1-seat-001'})):
        with pytest.raises(StoreError, match='does not match its model'):
            piece_edits.filter_max_script(script, prefix, removed)
    many = b'-- a\r\n-- b\r\n' + b''.join(f'    XX_furnBox "seat" "N{i}" 1 "L1-seat-{i:03d}" "none"\r\n'.encode()
                                          for i in range(35))
    out = piece_edits.filter_max_script(many, 'XX', {f'L1-seat-{i:03d}' for i in range(35)})
    assert out.split(b'\r\n')[2].decode() == ('-- 35 furniture boxes deleted in the walkthrough app are left out: '
                                              + ', '.join(f'N{i}' for i in range(30)) + ', and 5 more')
