"""Every route of DESIGN.md 10.2 on a TestClient over a temp copy of the seeded store: status, headers, ETag / 304,
attachment names, camelCase, the error codes, PUT validation; the routes are plain `def` and reach the store only through
Depends(get_store) (9.3)."""
from __future__ import annotations

import inspect
import re
from pathlib import Path

import pytest
from fastapi.routing import APIRoute
from fastapi.testclient import TestClient

from kit import BASE_URL, FIXTURES, PROTOTYPES, VERSION_IDS, VERSIONS, make_client, read_json
from walkthrough_api import routes as routes_pkg
from walkthrough_api.deps import get_store
from walkthrough_api.routes import downloads, furniture, projects, versions
from walkthrough_api.jsonio import sha1_hex
from walkthrough_api.main import create_app
from walkthrough_api.seed.sources import SEED_TABLE
from walkthrough_api.settings import Settings
from walkthrough_api.store.base import NotFound

API = '/api/projects'
SUMMARY_KEYS = {'id', 'name', 'shortName', 'projectNo', 'sourceKind', 'floors', 'furnitureCount', 'openingsCount', 'stamp',
                'latestVersion', 'versionCount', 'createdAt', 'updatedAt', 'thumbnailUrl', 'url'}
VERSION_SUMMARY_KEYS = {'version', 'label', 'createdAt', 'stamp', 'sourceKind', 'counts', 'hasStages', 'hasMaxScript',
                        'hasFurniture', 'url'}
DETAIL_KEYS = VERSION_SUMMARY_KEYS | {'projectId', 'modelSha1', 'stampSource', 'floors', 'urls', 'assets', 'downloads',
                                      'presentation', 'overrides'}


def err(r, status: int, code: str) -> dict:
    assert r.status_code == status, (r.status_code, r.text[:300])
    body = r.json()
    assert set(body) == {'error'} and body['error']['code'] == code and body['error']['message'], body
    return body['error']


def camel(obj, path='') -> None:
    """Every key of the API's own JSON is camelCase (the presentation and saved heights carry data keys)."""
    if isinstance(obj, dict):
        for k, v in obj.items():
            if path.endswith(('/presentation', '/heights')):
                continue
            assert '_' not in k, f'{path}/{k}'
            camel(v, f'{path}/{k}')
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            camel(v, f'{path}/{i}')


def src_of(project_id: str, n: int):
    return next(v for v in SEED_TABLE if (v.project_id, v.version) == (project_id, n))


# ---------------------------------------------------------------------------------------------------- health, projects
def test_health(client: TestClient) -> None:
    r = client.get('/api/health')
    assert r.status_code == 200 and r.json() == {'status': 'ok', 'apiVersion': '0.1.0', 'projects': 4}


def test_list_projects(client: TestClient, data_copy: Path) -> None:
    r = client.get(API)
    assert r.status_code == 200
    projects = r.json()['projects']
    camel(r.json())
    metas = [read_json(p / 'meta.json') for p in sorted((data_copy / 'projects').iterdir())]
    newest_first = sorted(sorted(metas, key=lambda m: m['id']), key=lambda m: m['updatedAt'], reverse=True)
    assert [p['id'] for p in projects] == [m['id'] for m in newest_first]          # updatedAt, newest first (ties by id)
    assert {p['id'] for p in projects} == {'hotel-lobby', 'sukhumvit-house', 'presidential-suite', 'bank-sampeng'}
    assert [p['updatedAt'] for p in projects] == [m['updatedAt'] for m in newest_first]
    for p in projects:
        assert set(p) == SUMMARY_KEYS and p['url'] == f"{API}/{p['id']}"
        latest = read_json(data_copy / 'projects' / p['id'] / 'versions' / str(p['latestVersion']) / 'version.json')
        assert (p['stamp'], p['furnitureCount'], p['openingsCount']) == \
               (latest['stamp'], latest['counts']['furniture'], latest['counts']['openings'])
        assert p['floors'] == latest['floors'] and p['versionCount'] == len(read_json(data_copy / 'projects' / p['id'] / 'meta.json')['versions'])
        assert p['thumbnailUrl'] == (None if p['id'] == 'sukhumvit-house' else f"{API}/{p['id']}/thumbnail")
    by_id = {p['id']: p for p in projects}
    bank = by_id['bank-sampeng']
    assert (bank['name'], bank['shortName'], bank['projectNo'], bank['sourceKind'], bank['latestVersion'], bank['versionCount']) == \
           ('Bangkok Bank, Sampeng Branch', 'Bank branch', '26-0216', 'cad', 2, 2)
    assert by_id['hotel-lobby']['sourceKind'] == 'pictures'
    assert {p['sourceKind'] for i, p in by_id.items() if i != 'hotel-lobby'} == {'cad'}


def test_a_save_moves_a_project_to_the_top(client: TestClient) -> None:
    assert client.put(f'{API}/bank-sampeng/versions/2/furniture-heights', json={'heights': {'table': 600}}).status_code == 200
    assert client.get(API).json()['projects'][0]['id'] == 'bank-sampeng'


def test_get_project(client: TestClient) -> None:
    r = client.get(f'{API}/bank-sampeng')
    body = r.json()
    assert r.status_code == 200 and set(body) == SUMMARY_KEYS | {'versions'}
    assert [v['version'] for v in body['versions']] == [1, 2]
    for v in body['versions']:
        assert set(v) == VERSION_SUMMARY_KEYS and v['url'] == f"{API}/bank-sampeng/versions/{v['version']}"
    v1, v2 = body['versions']
    assert (v1['hasFurniture'], v2['hasFurniture'], v1['hasMaxScript'], v1['hasStages']) == (False, True, True, True)
    assert v1['counts'] == {'floors': 2, 'parts': 124, 'openings': 55, 'furniture': 0, 'furnitureKinds': 0, 'rooms': 18}
    err(client.get(f'{API}/no-such-project'), 404, 'project_not_found')
    assert client.get(f'{API}/Not_A_Slug').status_code == 422            # malformed: FastAPI's own 422
    assert client.get(f'{API}/x').status_code == 422


# ---------------------------------------------------------------------------------------------------- raw files, ETag
def test_thumbnail(client: TestClient) -> None:
    r = client.get(f'{API}/bank-sampeng/thumbnail')
    want = (PROTOTYPES / 'bank_test' / 'bank_topview.png').read_bytes()        # the latest version's
    assert r.status_code == 200 and r.content == want and r.headers['content-type'] == 'image/png'
    assert r.headers['etag'] == f'"{sha1_hex(want)}"' and r.headers['cache-control'] == 'no-cache'
    again = client.get(f'{API}/bank-sampeng/thumbnail', headers={'If-None-Match': r.headers['etag']})
    assert again.status_code == 304 and again.content == b'' and again.headers['etag'] == r.headers['etag']
    err(client.get(f'{API}/sukhumvit-house/thumbnail'), 404, 'no_thumbnail')
    err(client.get(f'{API}/no-such-project/thumbnail'), 404, 'project_not_found')


@pytest.mark.parametrize('key', list(VERSIONS), ids=VERSION_IDS)
def test_version_detail(client: TestClient, data_copy: Path, key) -> None:
    project_id, n = key
    r = client.get(f'{API}/{project_id}/versions/{n}')
    assert r.status_code == 200
    d = r.json()
    camel(d)
    v = read_json(data_copy / 'projects' / project_id / 'versions' / str(n) / 'version.json')
    m = read_json(data_copy / 'projects' / project_id / 'versions' / str(n) / 'model.json')
    url = f'{API}/{project_id}/versions/{n}'
    assert set(d) == DETAIL_KEYS
    assert (d['projectId'], d['version'], d['label'], d['createdAt'], d['stamp'], d['stampSource'], d['modelSha1']) == \
           (project_id, n, v['label'], v['createdAt'], v['stamp'], v['stampSource'], v['modelSha1'])
    assert d['counts'] == v['counts'] and d['floors'] == v['floors'] and d['presentation'] == v['presentation']
    assert d['urls'] == {'model': f'{url}/model', 'stages': f'{url}/stages' if v['hasStages'] else None}
    assert d['assets'] == [{'name': a['name'], 'role': a['role'], 'floor': a.get('floor'), 'mediaType': a['mediaType'],
                            'bytes': a['bytes'], 'sha1': a['sha1'], 'url': f"{url}/assets/{a['name']}"} for a in v['assets']]
    dl = d['downloads']
    assert dl['offlineHtml'] == {'url': f'{url}/downloads/offline-html', 'fileName': f'{project_id}-v{n}.html',
                                 'mediaType': 'text/html; charset=utf-8'}
    ms = v['downloads']['maxScript']
    assert dl['maxScript'] == ({'url': f'{url}/downloads/max-script', 'fileName': ms.removesuffix('.ms') + f'_v{n}.ms',
                                'mediaType': 'text/plain; charset=utf-8'} if ms else None)
    assert dl['furnitureCsv'] == ({'url': f'{url}/downloads/furniture-csv', 'fileName': f"{m['photoName']}_furniture_list.csv",
                                   'mediaType': 'text/csv; charset=utf-8'} if m.get('furniture') else None)
    assert d['overrides'] == {'heights': {}, 'revision': 0, 'updatedAt': None}
    assert (d['hasStages'], d['hasMaxScript'], d['hasFurniture']) == \
           (v['hasStages'], v['downloads']['maxScript'] is not None, bool(m.get('furniture')))


def test_version_errors(client: TestClient) -> None:
    err(client.get(f'{API}/bank-sampeng/versions/3'), 404, 'version_not_found')
    err(client.get(f'{API}/no-such-project/versions/1'), 404, 'project_not_found')
    assert client.get(f'{API}/bank-sampeng/versions/0').status_code == 422
    assert client.get(f'{API}/bank-sampeng/versions/two').status_code == 422


@pytest.mark.parametrize('key', list(VERSIONS), ids=VERSION_IDS)
def test_model(client: TestClient, data_copy: Path, key) -> None:
    project_id, n = key
    stored = (data_copy / 'projects' / project_id / 'versions' / str(n) / 'model.json').read_bytes()
    v = read_json(data_copy / 'projects' / project_id / 'versions' / str(n) / 'version.json')
    r = client.get(f'{API}/{project_id}/versions/{n}/model')
    assert r.status_code == 200 and r.content == stored and r.headers['content-type'] == 'application/json'
    assert r.headers['etag'] == f'"{sha1_hex(stored)}"' == f'"{v["modelSha1"]}"'
    assert r.headers['x-model-stamp'] == v['stamp'] and r.headers['cache-control'] == 'no-cache'
    tag = r.headers['etag']
    for inm in (tag, f'W/{tag}', f'"abc", {tag}', '*'):
        nm = client.get(f'{API}/{project_id}/versions/{n}/model', headers={'If-None-Match': inm})
        assert nm.status_code == 304 and nm.content == b'' and nm.headers['etag'] == tag, inm
    assert client.get(f'{API}/{project_id}/versions/{n}/model', headers={'If-None-Match': '"other"'}).status_code == 200
    err(client.get(f'{API}/{project_id}/versions/9/model'), 404, 'version_not_found')


def test_stages(client: TestClient, data_copy: Path) -> None:
    stored = (data_copy / 'projects' / 'sukhumvit-house' / 'versions' / '1' / 'stages.json').read_bytes()
    r = client.get(f'{API}/sukhumvit-house/versions/1/stages')
    assert r.status_code == 200 and r.content == stored and r.headers['etag'] == f'"{sha1_hex(stored)}"'
    assert client.get(f'{API}/sukhumvit-house/versions/1/stages', headers={'If-None-Match': r.headers['etag']}).status_code == 304
    r = client.get(f'{API}/bank-sampeng/versions/1/stages')
    assert r.content == (FIXTURES / 'stages' / 'bank-v1.stages.json').read_bytes()
    err(client.get(f'{API}/hotel-lobby/versions/1/stages'), 404, 'no_stages')


def test_assets(client: TestClient) -> None:
    for name in ('floor1_plan.png', 'floor2_plan.png'):
        r = client.get(f'{API}/hotel-lobby/versions/1/assets/{name}')
        want = (FIXTURES / 'pictures' / name).read_bytes()
        assert r.status_code == 200 and r.content == want and r.headers['content-type'] == 'image/png'
        assert r.headers['etag'] == f'"{sha1_hex(want)}"' and r.headers['cache-control'] == 'no-cache'
        assert client.get(r.url, headers={'If-None-Match': r.headers['etag']}).status_code == 304
    err(client.get(f'{API}/hotel-lobby/versions/1/assets/nope.png'), 404, 'asset_not_found')
    err(client.get(f'{API}/hotel-lobby/versions/1/assets/model.json'), 404, 'asset_not_found')
    err(client.get(f'{API}/hotel-lobby/versions/1/assets/...'), 404, 'asset_not_found')    # (a client folds '..' itself)
    err(client.get(f'{API}/hotel-lobby/versions/1/assets/%2E%2E'), 404, 'asset_not_found')
    assert client.get(f'{API}/hotel-lobby/versions/1/assets/a%20b.png').status_code == 422
    assert client.get(f'{API}/hotel-lobby/versions/1/assets/..%2Fmodel.json').status_code in (404, 422)


# ---------------------------------------------------------------------------------------------------- downloads
@pytest.mark.parametrize('src', [s for s in SEED_TABLE if s.max_script], ids=lambda s: f'{s.project_id}-v{s.version}')
def test_max_script(client: TestClient, src) -> None:
    r = client.get(f'{API}/{src.project_id}/versions/{src.version}/downloads/max-script')
    assert r.status_code == 200 and r.content == (PROTOTYPES / src.folder / src.max_script).read_bytes()
    assert r.headers['content-type'] == 'text/plain; charset=utf-8'
    # the attachment name carries the version (fix step: bank v1 and v2 both saved as Bangkok_Bank_Sampeng.ms before)
    name = src.max_script.removesuffix('.ms') + f'_v{src.version}.ms'
    assert r.headers['content-disposition'] == f'attachment; filename="{name}"; filename*=UTF-8\'\'{name}'
    detail = client.get(f'{API}/{src.project_id}/versions/{src.version}').json()
    assert detail['downloads']['maxScript']['fileName'] == name


def test_max_script_names_of_two_versions_differ(client: TestClient) -> None:
    names = {client.get(f'{API}/bank-sampeng/versions/{n}').json()['downloads']['maxScript']['fileName'] for n in (1, 2)}
    assert names == {'Bangkok_Bank_Sampeng_v1.ms', 'Bangkok_Bank_Sampeng_v2.ms'}


def test_no_max_script(client: TestClient) -> None:
    err(client.get(f'{API}/sukhumvit-house/versions/1/downloads/max-script'), 404, 'no_max_script')


@pytest.mark.parametrize('key', [k for k in VERSIONS if VERSIONS[k]['csv']], ids=lambda k: f'{k[0]}-v{k[1]}')
def test_furniture_csv_equals_the_prototype_csv(client: TestClient, key) -> None:
    project_id, n = key
    src = src_of(project_id, n)
    prototype_csv = next(r for r in src.downloads if r.endswith('.csv'))
    r = client.get(f'{API}/{project_id}/versions/{n}/downloads/furniture-csv')
    assert r.status_code == 200 and r.headers['content-type'] == 'text/csv; charset=utf-8'
    assert r.content == (PROTOTYPES / src.folder / prototype_csv).read_bytes()           # BOM included
    assert r.content == (FIXTURES / 'csv' / f"{VERSIONS[key]['csv']}.csv").read_bytes()
    name = f"{read_json(FIXTURES / 'models' / (VERSIONS[key]['model'] + '.model.json'))['photoName']}_furniture_list.csv"
    assert r.headers['content-disposition'] == f'attachment; filename="{name}"; filename*=UTF-8\'\'{name}'


def test_furniture_csv_carries_the_saved_heights(client: TestClient) -> None:
    assert client.put(f'{API}/bank-sampeng/versions/2/furniture-heights',
                      json={'heights': {'table': 600, 'seat': 300, 'cabinet': 1000}}).status_code == 200
    r = client.get(f'{API}/bank-sampeng/versions/2/downloads/furniture-csv')
    assert r.content == (FIXTURES / 'csv' / 'bank-v2-typed.csv').read_bytes()


def test_no_furniture(client: TestClient) -> None:
    err(client.get(f'{API}/bank-sampeng/versions/1/downloads/furniture-csv'), 404, 'no_furniture')
    err(client.get(f'{API}/bank-sampeng/versions/1/furniture-heights'), 404, 'no_furniture')
    err(client.put(f'{API}/bank-sampeng/versions/1/furniture-heights', json={'heights': {}}), 404, 'no_furniture')


def test_offline_html(client: TestClient) -> None:
    r = client.get(f'{API}/hotel-lobby/versions/1/downloads/offline-html')
    assert r.status_code == 200 and r.headers['content-type'] == 'text/html; charset=utf-8'
    assert r.headers['content-disposition'] == 'attachment; filename="hotel-lobby-v1.html"; filename*=UTF-8\'\'hotel-lobby-v1.html'
    page = r.content.decode('utf-8')
    assert '<meta name="model-data" content="6ab030750886">' in page and '"overrides":null' in page
    assert client.put(f'{API}/hotel-lobby/versions/1/furniture-heights', json={'heights': {'table': 640}}).status_code == 200
    page = client.get(f'{API}/hotel-lobby/versions/1/downloads/offline-html').content.decode('utf-8')
    assert '"heights": {\n    "table": 640\n  }' in page                       # the current overrides.json, as stored


def test_offline_html_without_a_template(data_copy: Path, tmp_path: Path) -> None:
    with make_client(data_copy, tmp_path / 'missing' / 'viewer-template.html') as c:
        e = err(c.get(f'{API}/bank-sampeng/versions/2/downloads/offline-html'), 503, 'offline_template_missing')
        assert 'npm run build:offline:template' in e['message']
        # no server folders in the answer (fix step): only the file's name, as the template lies outside app/ here
        assert str(tmp_path) not in e['message'] and 'the offline template viewer-template.html is not built' in e['message']
        err(c.get(f'{API}/bank-sampeng/versions/9/downloads/offline-html'), 404, 'version_not_found')
    bad = tmp_path / 'bad.html'
    bad.write_bytes(b'<html>__WTV_DATA__ __WTV_DATA__ __WTV_STAMP__</html>')
    with make_client(data_copy, bad) as c:
        err(c.get(f'{API}/bank-sampeng/versions/2/downloads/offline-html'), 503, 'offline_template_invalid')


# ---------------------------------------------------------------------------------------------------- saved heights
def test_heights_get_put(client: TestClient, data_copy: Path, template_file: Path) -> None:
    url = f'{API}/presidential-suite/versions/1/furniture-heights'
    assert client.get(url).json() == {'heights': {}, 'revision': 0, 'updatedAt': None}
    model = read_json(FIXTURES / 'models' / 'suite.model.json')
    table = next(k for k in model['furnitureKinds'] if k['key'] == 'table')['height']
    r = client.put(url, json={'heights': {'seat': 300, 'table': table, 'tv': 650}})        # the model's value is dropped
    body = r.json()
    assert r.status_code == 200 and body['heights'] == {'tv': 650, 'seat': 300} and list(body['heights']) == ['tv', 'seat']
    assert body['revision'] == 1 and re.fullmatch(r'\d{4}-\d\d-\d\dT\d\d:\d\d:\d\dZ', body['updatedAt'])
    assert client.get(url).json() == body
    r2 = client.put(url, json={'heights': {'bed': 555}})                                   # replaces the map
    assert r2.json()['heights'] == {'bed': 555} and r2.json()['revision'] == 2
    with make_client(data_copy, template_file) as fresh:                                   # on disk
        assert fresh.get(url).json() == r2.json()
        assert fresh.get(f'{API}/presidential-suite/versions/1').json()['overrides'] == r2.json()
    r3 = client.put(url, json={'heights': {}})
    assert r3.json()['heights'] == {} and r3.json()['revision'] == 3


def test_heights_validation(client: TestClient) -> None:
    url = f'{API}/bank-sampeng/versions/2/furniture-heights'
    e = err(client.put(url, json={'heights': {'table': 9, 'spaceship': 600, 'seat': 5001, 'sofa': 10, 'atm': 5000}}), 422,
            'invalid_heights')
    assert e['details'] == {'unknownKinds': ['spaceship'], 'outOfRange': ['seat', 'table']}
    assert client.get(url).json()['revision'] == 0                                       # nothing saved
    # StrictInt (integration, E-2b): a string of digits, a boolean and an integral float are refused too, never taken as 600
    for body in ({'heights': {'table': 'tall'}}, {'heights': {'table': 600.5}}, {}, {'heights': [1]}, {'heights': {'table': None}},
                 {'heights': {'table': '600'}}, {'heights': {'table': True}}, {'heights': {'table': 600.0}}):
        r = client.put(url, json=body)
        assert r.status_code == 422 and 'detail' in r.json(), body                       # FastAPI's HTTPValidationError
    assert client.put(url, json={'heights': {'sofa': 10, 'atm': 5000}}).json()['heights'] == {'atm': 5000, 'sofa': 10}
    err(client.put(f'{API}/bank-sampeng/versions/7/furniture-heights', json={'heights': {}}), 404, 'version_not_found')
    err(client.get(f'{API}/no-such-project/versions/1/furniture-heights'), 404, 'project_not_found')


# ---------------------------------------------------------------------------------------------------- the seams
def test_routes_are_plain_def_and_take_the_store_from_the_dependency() -> None:
    routes = [r for m in (projects, versions, downloads, furniture) for r in m.router.routes if isinstance(r, APIRoute)]
    assert len(routes) == 13
    assert {r.operation_id for r in routes} == {op['operationId'] for p in create_app().openapi()['paths'].values()
                                                for op in p.values()}
    for r in routes:
        assert not inspect.iscoroutinefunction(r.endpoint), r.name
        params = inspect.signature(r.endpoint).parameters
        assert 'store' in params and params['store'].default.dependency is get_store, r.name
    for path in Path(routes_pkg.__file__).parent.glob('*.py'):
        text = path.read_text(encoding='utf-8')
        assert 'LocalStore' not in text and 'app.state' not in text, path.name


class FakeStore:
    """Only what the dependency override needs: the routes must use it, not app.state's LocalStore."""

    def list_projects(self):
        return []

    def get_project(self, project_id: str):
        raise NotFound('project_not_found', f'fake store: no {project_id}')


def test_get_store_is_the_only_way_to_the_store(data_copy: Path, template_file: Path) -> None:
    app = create_app(Settings(data_dir=data_copy, offline_template=template_file, cors_origins=()))
    app.dependency_overrides[get_store] = FakeStore
    with TestClient(app, base_url=BASE_URL) as c:
        assert c.get('/api/health').json()['projects'] == 0
        assert c.get(API).json() == {'projects': []}
        assert c.get(f'{API}/bank-sampeng').json()['error']['message'] == 'fake store: no bank-sampeng'


def test_cors_for_the_dev_origins(client: TestClient) -> None:
    r = client.options(f'{API}/bank-sampeng/versions/2/furniture-heights',
                       headers={'Origin': 'http://127.0.0.1:5710', 'Access-Control-Request-Method': 'PUT',
                                'Access-Control-Request-Headers': 'content-type'})
    assert r.status_code == 200 and r.headers['access-control-allow-origin'] == 'http://127.0.0.1:5710'
    r = client.get(f'{API}/bank-sampeng/versions/2/model', headers={'Origin': 'http://127.0.0.1:5710'})
    exposed = {h.strip() for h in r.headers['access-control-expose-headers'].split(',')}
    assert {'etag', 'x-model-stamp', 'content-disposition'} <= {h.lower() for h in exposed}
    r = client.get(API, headers={'Origin': 'http://evil.example'})
    assert 'access-control-allow-origin' not in r.headers


def test_a_broken_store_answers_500_store_error(data_copy: Path, template_file: Path) -> None:
    (data_copy / 'projects' / 'hotel-lobby' / 'meta.json').write_bytes(b'not json')
    (data_copy / 'projects' / 'bank-sampeng' / 'versions' / '2' / 'overrides.json').write_bytes(b'{"heights":')
    with make_client(data_copy, template_file) as c:
        err(c.get(f'{API}/hotel-lobby'), 500, 'store_error')
        err(c.get(f'{API}/bank-sampeng/versions/2/downloads/offline-html'), 500, 'store_error')     # never a broken page
        err(c.get(f'{API}/bank-sampeng/versions/2/furniture-heights'), 500, 'store_error')
