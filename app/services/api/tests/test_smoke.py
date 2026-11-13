"""Scaffold smoke test: the stub app answers /api/health and its OpenAPI document has the 13 operationIds of DESIGN.md 10.2."""
from fastapi.testclient import TestClient

from test_openapi import DELETE_OPERATION_IDS, UPLOAD_OPERATION_IDS
from walkthrough_api.main import create_app

OPERATION_IDS = {
    'health', 'listProjects', 'getProject', 'getThumbnail', 'getVersion', 'getModel', 'getStages', 'getAsset',
    'downloadMaxScript', 'downloadFurnitureCsv', 'downloadOfflineHtml', 'getFurnitureHeights', 'putFurnitureHeights',
}


def test_health() -> None:
    client = TestClient(create_app(), base_url='http://127.0.0.1')
    r = client.get('/api/health')
    assert r.status_code == 200
    body = r.json()
    assert body['status'] == 'ok'
    assert set(body) == {'status', 'apiVersion', 'projects'}


def test_openapi_operation_ids() -> None:
    doc = create_app().openapi()
    ids = [op['operationId'] for path in doc['paths'].values() for op in path.values()]
    # + the upload milestone's 24 (U-15.1) and the two deletes of 12 Nov 2026 (docs/contract-issues/DEL.md)
    assert sorted(ids) == sorted(OPERATION_IDS | UPLOAD_OPERATION_IDS | DELETE_OPERATION_IDS)
    for path in doc['paths'].values():
        for op in path.values():
            assert op.get('summary') and op.get('description'), op['operationId']
            ok = [s for s in op['responses'] if s.startswith('2')]           # 200, or 201 / 202 / 204 (U-13.1)
            assert len(ok) == 1 and op['responses'][ok[0]]['description'], op['operationId']
