"""Uploads in raw parts (docs/upload/DESIGN.md U-5; ACCEPTANCE 2.2 "Uploads", A-3's upload line): createUpload's refusals,
part sizes, a part sent twice, completion with parts missing, the first bytes (DWG R13+, ASCII and binary DXF), dedupe
by sha1, cancel, expiry, and the body guard answering before a body is read."""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from kit import read_json
from upkit import BANK1, upload
from walkthrough_api.drafts.sourcefile import sniff
from walkthrough_api.errors import ApiError
from walkthrough_api.jsonio import dumps_pretty

U = '/api/uploads'
MIB = 1024 * 1024
DXF = b'999\nmade by a test\n  0\nSECTION\n  2\nHEADER\n  9\n$ACADVER\n  1\nAC1027\n  0\nENDSEC\n  0\nEOF\n'


def err(r, status: int, code: str) -> dict:
    assert r.status_code == status, (r.status_code, r.text[:400])
    assert r.json()['error']['code'] == code, r.json()
    return r.json()['error']


def session(client: TestClient, name: str, size: int, project: str = 'bank-sampeng') -> dict:
    r = client.post(U, json={'projectId': project, 'fileName': name, 'bytes': size})
    assert r.status_code == 201, r.text[:300]
    return r.json()


def test_create_upload(client: TestClient, data_copy: Path) -> None:
    s = session(client, 'Plan A.DWG', 17_797_665)
    assert s['id'].startswith('u') and len(s['id']) == 25 and s['partBytes'] == 8 * MIB and s['parts'] == 3
    assert s['received'] == [] and s['url'] == f'{U}/{s["id"]}' and s['completeUrl'] == f'{U}/{s["id"]}/complete'
    assert s['partUrls'] == [f'{U}/{s["id"]}/parts/{i}' for i in (1, 2, 3)]
    stored = read_json(data_copy / '.uploads' / s['id'] / 'session.json')
    assert stored['format'] == 'walkthrough-upload/1' and stored['fileName'] == 'Plan A.DWG'
    assert client.get(s['url']).json() == s
    err(client.post(U, json={'projectId': 'no-such-project', 'fileName': 'a.dwg', 'bytes': 1}), 404, 'project_not_found')
    err(client.post(U, json={'projectId': '../x', 'fileName': 'a.dwg', 'bytes': 1}), 404, 'project_not_found')
    err(client.post(U, json={'projectId': 'bank-sampeng', 'fileName': 'a.dwg', 'bytes': 300 * MIB + 1}), 413, 'too_large')
    for name in ('a.pdf', 'a.dwg.txt', '', 'x' * 252 + '.dwg', 'line\nbreak.dwg', 'no-extension'):
        err(client.post(U, json={'projectId': 'bank-sampeng', 'fileName': name, 'bytes': 10}), 422, 'bad_kind')
    err(client.post(U, json={'projectId': 'bank-sampeng', 'fileName': 'a.dxf', 'bytes': 0}), 422, 'bad_kind')
    assert client.post(U, json={'projectId': 'bank-sampeng', 'fileName': 'x' * 251 + '.dxf', 'bytes': 1}).status_code == 201
    err(client.get(f'{U}/u{"0" * 24}'), 404, 'upload_not_found')


def test_a_17_8_mb_dwg_in_three_parts(client: TestClient, data_copy: Path) -> None:
    data = b'AC1032' + bytes(range(256)) * (17_797_665 // 256) + b'tail'
    s = session(client, 'big.dwg', len(data))
    assert s['parts'] == 3
    parts = [data[i * 8 * MIB:(i + 1) * 8 * MIB] for i in range(3)]
    err(client.put(s['partUrls'][0], content=parts[0][:-1]), 422, 'bad_part')           # a short part
    err(client.put(s['partUrls'][2], content=parts[2] + b'x'), 422, 'bad_part')          # the last part too long
    assert client.put(f'{s["url"]}/parts/4', content=b'x').status_code == 422            # past the last
    r = client.put(s['partUrls'][2], content=parts[2])
    assert r.json() == {'part': 3, 'bytes': len(parts[2])}
    e = err(client.post(s['completeUrl'], json={}), 409, 'incomplete')
    assert e['details'] == {'missing': [1, 2]}
    assert client.put(s['partUrls'][0], content=parts[0]).status_code == 200
    assert client.put(s['partUrls'][0], content=parts[0]).status_code == 200              # sent twice: replaces itself
    assert client.get(s['url']).json()['received'] == [1, 3]
    assert client.put(s['partUrls'][1], content=parts[1]).status_code == 200
    assert read_json(data_copy / '.uploads' / s['id'] / 'session.json')['received'] == [1, 2, 3]
    r = client.post(s['completeUrl'], json={})
    assert r.status_code == 201, r.text[:300]
    src = r.json()
    sha1 = hashlib.sha1(data).hexdigest()
    assert (src['sha1'], src['name'], src['bytes'], src['kind'], src['formatVersion']) == \
           (sha1, 'big.dwg', len(data), 'dwg', 'AC1032')
    folder = data_copy / 'projects' / 'bank-sampeng' / 'sources' / sha1
    assert (folder / 'original.dwg').read_bytes() == data
    assert read_json(folder / 'source.json') == {'format': 'walkthrough-source/1', **src, 'file': 'original.dwg'}
    assert not (data_copy / '.uploads' / s['id']).exists()
    err(client.get(s['url']), 404, 'upload_not_found')


def test_the_same_file_twice_is_one_source(client: TestClient, data_copy: Path) -> None:
    first = upload(client, 'bank-sampeng', BANK1.read_bytes(), BANK1.name)
    again = upload(client, 'bank-sampeng', BANK1.read_bytes(), 'renamed.dwg')
    assert again == first and first['sha1'] == '459d40fc230607ffe35e2ee9d443cd2b0105dc36'
    assert first['formatVersion'] == 'AC1024'
    assert [p.name for p in (data_copy / 'projects' / 'bank-sampeng' / 'sources').iterdir()] == [first['sha1']]


@pytest.mark.parametrize('head,name,code', [
    (b'AC1009' + b'\0' * 100, 'old.dwg', 'unsupported_version'),
    (b'AC1.50' + b'\0' * 100, 'older.dwg', 'unsupported_version'),
    (b'AC2.10' + b'\0' * 100, 'r2.dwg', 'unsupported_version'),
    (b'AC1011' + b'\0' * 100, 'r12.dwg', 'unsupported_version'),
    (b'This is only a text file renamed.\n', 'notes.dwg', 'bad_kind'),
    (b'This is only a text file renamed.\n', 'notes.dxf', 'bad_kind'),
    (DXF, 'a-dxf-named.dwg', 'bad_kind'),
    (b'AC1032' + b'\0' * 100, 'a-dwg-named.dxf', 'bad_kind'),
    (b'\x00' * 64, 'zeros.dwg', 'bad_kind'),
])
def test_first_bytes_refused(client: TestClient, data_copy: Path, head: bytes, name: str, code: str) -> None:
    s = session(client, name, len(head))
    assert client.put(s['partUrls'][0], content=head).status_code == 200
    e = err(client.post(s['completeUrl'], json={}), 422, code)
    assert name in e['message']
    assert not (data_copy / '.uploads' / s['id']).exists()                      # the parts are no good: gone
    assert not (data_copy / 'projects' / 'bank-sampeng' / 'sources').exists()


def test_dxf_files(client: TestClient) -> None:
    src = upload(client, 'bank-sampeng', DXF, 'ascii.dxf')
    assert (src['kind'], src['formatVersion']) == ('dxf', 'AC1027')
    src = upload(client, 'bank-sampeng', b'\xef\xbb\xbf  \r\n  0\r\nSECTION\r\n  2\r\nENTITIES\r\n', 'bom.DXF')
    assert (src['kind'], src['formatVersion']) == ('dxf', None)
    binary = b'AutoCAD Binary DXF\r\n\x1a\x00' + b'\x00\x00SECTION\x00\x02\x00HEADER\x00\x09\x00$ACADVER\x00\x01\x00AC1018\x00'
    src = upload(client, 'bank-sampeng', binary, 'binary.dxf')
    assert (src['kind'], src['formatVersion']) == ('dxf', 'AC1018')


def test_sniff_directly() -> None:
    assert sniff(b'AC1012' + b'\0', 'r13.dwg') == ('dwg', 'AC1012')
    with pytest.raises(ApiError) as e:
        sniff(b'', 'empty.dwg')
    assert e.value.code == 'bad_kind'
    with pytest.raises(ApiError):
        sniff(b'999\ncomment\n  2\nSECTION\n', 'a.dxf')                          # group code 2 first: not a DXF


def test_cancel_and_expiry(client: TestClient, data_copy: Path) -> None:
    s = session(client, 'a.dwg', 10)
    assert client.delete(s['url']).status_code == 204
    err(client.delete(s['url']), 404, 'upload_not_found')
    err(client.put(s['partUrls'][0], content=b'AC10320000'), 404, 'upload_not_found')
    old = session(client, 'old.dwg', 10)
    path = data_copy / '.uploads' / old['id'] / 'session.json'
    record = read_json(path)
    record['expiresAt'] = '2026-01-01T00:00:00Z'
    path.write_bytes(dumps_pretty(record))
    err(client.get(old['url']), 404, 'upload_not_found')                         # expired: gone
    assert not path.parent.exists()
    stale = session(client, 'stale.dwg', 10)
    path = data_copy / '.uploads' / stale['id'] / 'session.json'
    record = read_json(path)
    record['expiresAt'] = '2026-01-01T00:00:00Z'
    path.write_bytes(dumps_pretty(record))
    session(client, 'new.dwg', 10)                                                # a new session cleans old ones
    assert not path.parent.exists()


def test_the_body_guard_answers_before_the_body(client: TestClient) -> None:
    s = session(client, 'a.dwg', 10)

    def chunks():
        yield b'AC1032'
    err(client.put(s['partUrls'][0], content=chunks()), 411, 'length_required')
    err(client.put(s['partUrls'][0], content=b'x' * (8 * MIB + 1)), 413, 'part_too_large')
    err(client.post(U, content=b'{"projectId": "' + b'x' * (2 * MIB) + b'"}',
                    headers={'content-type': 'application/json'}), 413, 'body_too_large')
    assert client.get(s['url']).json()['received'] == []


def test_parts_of_two_sessions_never_mix(client: TestClient) -> None:
    a = session(client, 'a.dxf', len(DXF))
    b = session(client, 'b.dxf', len(DXF))
    assert client.put(a['partUrls'][0], content=DXF).status_code == 200
    err(client.post(b['completeUrl'], json={}), 409, 'incomplete')
    assert client.post(a['completeUrl'], json={}).status_code == 201
    assert json.loads(json.dumps(client.get(b['url']).json()))['received'] == []
