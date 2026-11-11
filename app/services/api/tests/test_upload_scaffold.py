"""The upload milestone's frozen API part (docs/upload/DESIGN.md U-13; WORK_BREAKDOWN U0 step 5): every new route is wired
and answers (on an empty store: its 404s; step U5 replaced the scaffold's 501 expectations as it wrote the bodies), the
body guard answers 411 / 413 before a body is read, CORS takes POST and DELETE, the new settings read the environment,
`check_file` passes every upload fixture and refuses broken ones, and the models refuse what the contract does not
name."""
from __future__ import annotations

import copy
import gzip
import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from kit import APP, BASE_URL, make_client
from walkthrough_api import check_file
from walkthrough_api.bodyguard import DEFAULT_MAX, PART_BYTES, SETTINGS_MAX, limit_for
from walkthrough_api.deps import get_jobs
from walkthrough_api.jobs.local import LocalJobRunner
from walkthrough_api.main import create_app
from walkthrough_api.models_upload import RECORDS, BuildSettings, NewBuildRequest, OutlineEdgeFix
from walkthrough_api.settings import PART_BYTES as SETTINGS_PART_BYTES
from walkthrough_api.settings import Settings

FX = APP / 'fixtures' / 'upload'
P = '/api/projects/bank-sampeng'
B = f'{P}/builds/20261104T101500-0a1b2c'
SHA = '6551bdc6f0cff4e31e83b68a55d22cf42703029a'
U = '/api/uploads/u0123456789abcdef01234567'


def settings_json(name: str = 'bank') -> dict:
    return json.loads((FX / 'settings' / f'{name}.json').read_text(encoding='utf-8'))


@pytest.fixture
def empty_client(tmp_path: Path, template_file: Path):
    with make_client(tmp_path / 'data', template_file) as c:
        yield c


def answers(r, status: int, code: str | None) -> None:
    """The route ran its body: `status`, and with an error its ErrorResponse code (never 501 not_implemented)."""
    assert r.status_code == status, (r.status_code, r.text[:300])
    if code is not None:
        assert r.json()['error']['code'] == code, r.json()


# --------------------------------------------------------------------------------------------- every route is wired
ROUTES = [
    ('post', '/api/projects', {'json': {'name': 'A new project'}}, 'createProject', 201, None),
    ('get', '/api/offices', {}, 'listOffices', 200, None),
    ('post', '/api/uploads', {'json': {'projectId': 'bank-sampeng', 'fileName': 'a.dwg', 'bytes': 10}}, 'createUpload',
     404, 'project_not_found'),
    ('get', U, {}, 'getUpload', 404, 'upload_not_found'),
    ('put', f'{U}/parts/1', {'content': b'0123456789', 'headers': {'content-type': 'application/octet-stream'}},
     'putUploadPart', 404, 'upload_not_found'),
    ('post', f'{U}/complete', {'json': {}}, 'completeUpload', 404, 'upload_not_found'),
    ('delete', U, {}, 'cancelUpload', 404, 'upload_not_found'),
    ('post', f'{P}/builds', {'json': {'sources': [SHA]}}, 'createBuild', 404, 'project_not_found'),
    ('get', f'{P}/builds', {}, 'listBuilds', 404, 'project_not_found'),
    ('get', B, {}, 'getBuild', 404, 'project_not_found'),
    ('get', B + '?withSettings=false', {}, 'getBuild', 404, 'project_not_found'),
    ('put', f'{B}/settings', {'json': {'settings': settings_json(), 'layersReviewed': True},
                              'headers': {'If-Match': '"1"'}}, 'putBuildSettings', 404, 'project_not_found'),
    ('post', f'{B}/run', {'json': {}}, 'runBuild', 404, 'project_not_found'),
    ('post', f'{B}/cancel', {'json': {}}, 'cancelBuildRun', 404, 'project_not_found'),
    ('get', f'{B}/sources/{SHA}/conversion', {}, 'getBuildConversion', 404, 'project_not_found'),
    ('get', f'{B}/sources/{SHA}/drawing', {}, 'getBuildDrawing', 404, 'project_not_found'),
    ('get', f'{B}/sources/{SHA}/plan', {}, 'getBuildPlan', 404, 'project_not_found'),
    ('get', f'{B}/overlay', {}, 'getBuildOverlay', 404, 'project_not_found'),
    ('get', f'{B}/diff', {}, 'getBuildDiff', 404, 'project_not_found'),
    ('get', f'{B}/model', {}, 'getBuildModel', 404, 'project_not_found'),
    ('get', f'{B}/stages', {}, 'getBuildStages', 404, 'project_not_found'),
    ('get', f'{B}/topview', {}, 'getBuildTopview', 404, 'project_not_found'),
    ('get', f'{B}/max-script', {}, 'downloadBuildMaxScript', 404, 'project_not_found'),
    ('post', f'{B}/save', {'json': {'label': 'v3', 'carryHeights': True, 'rememberMapping': True}}, 'saveBuild', 404,
     'project_not_found'),
    ('delete', B, {}, 'deleteBuild', 404, 'project_not_found'),
]


@pytest.mark.parametrize('method,url,kw,op,status,code', ROUTES, ids=[f'{r[3]}-{i}' for i, r in enumerate(ROUTES)])
def test_route_is_wired(empty_client: TestClient, method: str, url: str, kw: dict, op: str, status: int,
                        code: str | None) -> None:
    answers(getattr(empty_client, method)(url, **kw), status, code)


@pytest.mark.parametrize('url', [
    '/api/uploads/not-an-id', f'{U}/parts/0', f'{U}/parts/10001', f'{P}/builds/2026-11-04', f'{B}/sources/ABC/plan',
])
def test_path_patterns(empty_client: TestClient, url: str) -> None:
    method = 'put' if '/parts/' in url else 'get'
    r = getattr(empty_client, method)(url, content=b'x') if method == 'put' else empty_client.get(url)
    assert r.status_code == 422, (url, r.status_code)


def test_bodies_are_validated_first(empty_client: TestClient) -> None:
    bad = settings_json()
    bad['colour'] = 'red'                                                    # extra='forbid'
    assert empty_client.put(f'{B}/settings', json={'settings': bad}).status_code == 422
    assert empty_client.post(f'{B}/run', json={'x': 1}).status_code == 422   # {} only
    assert empty_client.post(f'{P}/builds', json={}).status_code == 422      # sources is required (null allowed)


def test_get_jobs_is_the_apps_runner(tmp_path: Path, template_file: Path) -> None:
    app = create_app(Settings(data_dir=tmp_path, offline_template=template_file, cors_origins=()))
    assert isinstance(app.state.jobs, LocalJobRunner)

    class Req:
        def __init__(self) -> None:
            self.app = app
    assert get_jobs(Req()) is app.state.jobs                                 # type: ignore[arg-type]


# ----------------------------------------------------------------------------------------------------- the body guard
def test_limits() -> None:
    assert limit_for('PUT', '/api/uploads/u1/parts/3') == (PART_BYTES, 'part_too_large')
    assert limit_for('PUT', f'{B}/settings') == (SETTINGS_MAX, 'body_too_large')
    assert limit_for('POST', '/api/projects') == (DEFAULT_MAX, 'body_too_large')
    assert limit_for('PUT', '/api/projects/x/versions/2/furniture-heights') == (DEFAULT_MAX, 'body_too_large')
    assert limit_for('GET', '/api/projects') is None and limit_for('DELETE', B) is None
    assert PART_BYTES == SETTINGS_PART_BYTES == 8 * 1024 * 1024 and SETTINGS_MAX == 8 * 1024 * 1024
    assert DEFAULT_MAX == 2 * 1024 * 1024


def guard_err(r, status: int, code: str) -> None:
    assert r.status_code == status, (r.status_code, r.text[:200])
    assert r.json()['error']['code'] == code


def test_part_needs_content_length(empty_client: TestClient) -> None:
    def chunks():
        yield b'abc'
    guard_err(empty_client.put(f'{U}/parts/1', content=chunks()), 411, 'length_required')


def test_part_too_large_before_the_body_is_read(empty_client: TestClient) -> None:
    guard_err(empty_client.put(f'{U}/parts/1', content=b'x' * (PART_BYTES + 1)), 413, 'part_too_large')
    answers(empty_client.put(f'{U}/parts/1', content=b'x' * PART_BYTES), 404, 'upload_not_found')


def test_settings_limit_is_8_mib_and_others_2_mib(empty_client: TestClient) -> None:
    big = b'{"settings": "' + b'x' * (SETTINGS_MAX) + b'"}'
    guard_err(empty_client.put(f'{B}/settings', content=big, headers={'content-type': 'application/json'}), 413,
              'body_too_large')
    s = settings_json()
    s['fixes']['setAside'] = [{'floor': 'L1', 'source': SHA, 'key': f'BA/{i:X}', 'sig': 'a' * 12, 'rsig': '',
                               'elementId': None, 'layer': 'A-WALL', 'note': 'x' * 200} for i in range(12_000)]
    body = json.dumps({'settings': s}).encode()
    assert 3 * 1024 * 1024 < len(body) < SETTINGS_MAX                         # a 3+ MB settings PUT reaches the route
    answers(empty_client.put(f'{B}/settings', content=body, headers={'content-type': 'application/json'}), 404,
            'project_not_found')
    guard_err(empty_client.post('/api/projects', content=b'{"name": "' + b'x' * DEFAULT_MAX + b'"}',
                                headers={'content-type': 'application/json'}), 413, 'body_too_large')


def test_chunked_bodies_are_counted(empty_client: TestClient) -> None:
    def chunks(n: int, size: int):
        for _ in range(n):
            yield b' ' * size
        yield b'{"name": "x"}'
    guard_err(empty_client.post('/api/projects', content=chunks(3, 1024 * 1024), headers={'content-type': 'application/json'}),
              413, 'body_too_large')
    answers(empty_client.post('/api/projects', content=chunks(1, 1000), headers={'content-type': 'application/json'}),
            201, None)


def test_the_foundations_routes_still_answer(client: TestClient) -> None:
    assert client.get('/api/health').status_code == 200
    r = client.put('/api/projects/bank-sampeng/versions/2/furniture-heights', json={'heights': {'table': 600}})
    assert r.status_code == 200


def test_cors_takes_post_and_delete(empty_client: TestClient) -> None:
    for method in ('POST', 'DELETE', 'PUT'):
        r = empty_client.options('/api/uploads', headers={'Origin': 'http://127.0.0.1:5710',
                                                          'Access-Control-Request-Method': method,
                                                          'Access-Control-Request-Headers': 'content-type'})
        assert r.status_code == 200, method
        assert method in r.headers['access-control-allow-methods']
    r = empty_client.options('/api/uploads', headers={'Origin': 'http://evil.example', 'Access-Control-Request-Method': 'POST'})
    assert 'access-control-allow-origin' not in r.headers


# --------------------------------------------------------------------------------------------------------- settings
def test_new_settings_from_the_environment(tmp_path: Path) -> None:
    s = Settings.from_env({'WALKTHROUGH_DATA_DIR': str(tmp_path), 'WALKTHROUGH_CACHE_DIR': str(tmp_path / 'c'),
                           'WALKTHROUGH_CACHE_MAX_GB': '2.5', 'WALKTHROUGH_UPLOAD_MAX_BYTES': '1000',
                           'WALKTHROUGH_RUN_LOCK': str(tmp_path / 'r.lock'),
                           'WALKTHROUGH_BUILDER_PYTHON': 'x/python.exe', 'WALKTHROUGH_LIBREDWG_DIR': 'v/l'})
    assert (s.cache_dir, s.cache_max_gb, s.upload_max_bytes, s.run_lock) == (tmp_path / 'c', 2.5, 1000, tmp_path / 'r.lock')
    assert s.builder_python == (APP / 'x' / 'python.exe').resolve() and s.libredwg_dir == (APP / 'v' / 'l').resolve()
    d = Settings.from_env({})
    assert d.builder_python == (APP / 'services' / 'builder' / '.venv' / 'Scripts' / 'python.exe').resolve()
    assert d.libredwg_dir == (APP / 'vendor' / 'libredwg-0.14-win64').resolve()
    assert d.cache_max_gb == 5.0 and d.upload_max_bytes == 300 * 1024 * 1024
    assert d.cache_dir.parts[-2:] == ('walkthrough', 'cache') and d.run_lock.name == 'walkthrough-run.lock'


# ------------------------------------------------------------------------------------------------- models and records
def with_rooms_defaults(raw: dict) -> dict:
    """A settings document as the API gives it back since the rooms milestone (docs/rooms/DESIGN.md R-1.2, R-12.4;
    its scaffold R0): a key of that milestone that is missing is filled with the old rule, None, False or an empty list."""
    from walkthrough_api.models_upload import OLD_RULES
    s = copy.deepcopy(raw)
    s['options'] = {**OLD_RULES, **s['options']}
    s['floors'] = [{'ceilingHeight': None, **f} for f in s['floors']]
    s['fixes'] = {'closings': [], 'rooms': [], 'stairs': [], **s['fixes'],
                  'setAside': [{'floorPast': False, **x} for x in s['fixes']['setAside']]}
    return s


@pytest.mark.parametrize('name', ['bank', 'house', 'suite', 'tower', 'small',
                                  # the saved versions' recipes (no key of the rooms milestone) and the new-rule fixtures
                                  'recipes/house', 'recipes/suite', 'recipes/tower', 'recipes/suite-revit',
                                  'bank-rooms', 'house-rooms', 'suite-rooms', 'tower-rooms', 'suite-revit-rooms'])
def test_settings_fixtures_validate(name: str) -> None:
    raw = (FX / 'settings' / f'{name}.json').read_bytes()
    assert check_file.issues('settings', raw) == []
    s = BuildSettings.model_validate_json(raw)
    # nothing lost or renamed on a round trip; the rooms milestone's missing keys come back with their defaults
    assert json.loads(s.model_dump_json()) == with_rooms_defaults(json.loads(raw))
    old = name.split('/')[-1] in ('bank', 'house', 'suite', 'tower', 'small', 'suite-revit')
    assert (s.options.slabs, s.options.ceilings, s.options.stairs) == (
        ('closed-rooms', 'off', 'lines') if old else ('network', 'auto', 'climb'))


def test_settings_refuse_what_the_contract_does_not_name() -> None:
    s = settings_json()
    for change in (lambda x: x.update(colour='red'), lambda x: x['vocabulary'].update(stair='x'),
                   lambda x: x['layers'].update({'A': 'walls'}), lambda x: x['floors'][0]['area'].update(kind='circle'),
                   lambda x: x['floors'][1].update(align={'method': 'points', 'pairs': [[[0, 0], [1, 1]]]}),
                   lambda x: x['options'].update(offset='centre'), lambda x: x.update(format='build-settings/2')):
        bad = copy.deepcopy(s)
        change(bad)
        with pytest.raises(ValidationError):
            BuildSettings.model_validate(bad)


def test_integer_numbers_are_taken() -> None:
    s = settings_json()
    s['floors'][0]['level'] = 0
    s['floors'][1]['wallHeight'] = 4
    assert BuildSettings.model_validate(s).floors[0].level == 0.0


def test_keyword_fields() -> None:
    assert OutlineEdgeFix.model_validate({'floor': 'L1', 'a': [0, 0], 'b': [1, 0], 'as': 'wall'}).model_dump()['as'] == 'wall'
    assert NewBuildRequest.model_validate({'sources': None, 'from': {'kind': 'version', 'version': 2}}).model_dump()['from'] == \
        {'kind': 'version', 'version': 2}


FIXTURE_KINDS = [
    ('drawing', 'drawing/bank1.drawing.json'), ('drawing', 'drawing/sukhumvit.drawing.json'),
    ('plan', 'plan/bank1.plan.json.gz'), ('plan', 'plan/sukhumvit.plan.json.gz'),
    ('conversion', 'conversion/bank1.conversion.json'), ('conversion', 'conversion/presidential.conversion.json'),
    ('overlay', 'overlay/bank.overlay.json'), ('office', 'mappings/dwp-revit.json'),
    ('job', 'runs/bank-prepare/job.json'), ('job', 'runs/bank-build/job.json'),
    ('suggestions', 'runs/bank-prepare/out/suggestions.json'), ('settings', 'runs/bank-prepare/out/proposed-settings.json'),
    ('diff', 'runs/bank-build/out/diff.json'), ('openings', 'runs/bank-build/out/openings.json'),
    ('pieces', 'runs/bank-build/out/pieces.json'), ('inputs', 'runs/bank-build/out/inputs.json'),
]


@pytest.mark.parametrize('kind,rel', FIXTURE_KINDS, ids=[r for _, r in FIXTURE_KINDS])
def test_fixture_passes_check_file(kind: str, rel: str) -> None:
    assert check_file.issues(kind, (FX / rel).read_bytes()) == []


def test_fake_runs_list_files_that_match_their_job() -> None:
    import hashlib
    for folder in ('bank-prepare', 'bank-build'):
        run = json.loads((FX / 'runs' / folder / 'run.json').read_text(encoding='utf-8'))
        job = json.loads((FX / 'runs' / folder / 'job.json').read_text(encoding='utf-8'))
        assert set(run['outputs']) == set(job['outputs'])
        for name, src in run['outputs'].items():
            p = (APP / src['fixture'] if 'fixture' in src else APP.parent / src['prototype'] if 'prototype' in src
                 else FX / 'runs' / folder / src['file'])
            data = p.read_bytes()
            assert job['outputs'][name] == {'bytes': len(data), 'sha1': hashlib.sha1(data).hexdigest()}, name


def test_check_file_model_stages_presentation() -> None:
    model = (APP / 'fixtures' / 'models' / 'bank-v2.model.json').read_bytes()
    assert check_file.issues('model', model) == []
    assert check_file.issues('stages', (APP / 'fixtures' / 'stages' / 'bank-v2.stages.json').read_bytes(), model) == []
    assert check_file.issues('presentation', (FX / 'runs' / 'bank-build' / 'out' / 'presentation.json').read_bytes(), model) == []
    with pytest.raises(ValueError, match='--model'):
        check_file.issues('stages', b'{}')
    assert check_file.issues('model', b'{"format": 1}')


def test_check_file_refuses_broken_records() -> None:
    job = json.loads((FX / 'runs' / 'bank-build' / 'job.json').read_text(encoding='utf-8'))
    snake = dict(job, run_id=job['runId'])
    del snake['runId']
    assert any('/runId' in i for i in check_file.issues('job', json.dumps(snake).encode()))       # JSON names only
    assert check_file.issues('job', json.dumps(dict(job, status='paused')).encode())
    assert check_file.issues('job', b'\xef\xbb\xbf{}') == ['/: not strict JSON: starts with a byte-order mark']
    plan = json.loads(gzip.decompress((FX / 'plan' / 'bank1.plan.json.gz').read_bytes()))
    plan['items']['sig'].pop()
    assert any('items.sig' in i for i in check_file.issues('plan', json.dumps(plan).encode()))
    plan = json.loads(gzip.decompress((FX / 'plan' / 'bank1.plan.json.gz').read_bytes()))
    plan['items']['first'][3] = 10 ** 9
    assert any('/items/3' in i for i in check_file.issues('plan', json.dumps(plan).encode()))
    assert check_file.issues('plan', b'\x1f\x8bnot gzip')[0].startswith('/: not a readable gzip file')


def test_check_file_cli(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert check_file.main(['settings', str(FX / 'settings' / 'bank.json')]) == 0
    bad = tmp_path / 'bad.json'
    bad.write_text('{"format": "job/1"}', encoding='utf-8')
    assert check_file.main(['job', str(bad)]) == 1
    assert '/runId: Field required' in capsys.readouterr().out
    assert check_file.main(['stages', str(bad)]) == 2


def test_every_record_kind_has_a_model() -> None:
    assert set(RECORDS) | {'model', 'stages', 'presentation'} == set(check_file.KINDS)
    assert BASE_URL.startswith('http://127.0.0.1')
