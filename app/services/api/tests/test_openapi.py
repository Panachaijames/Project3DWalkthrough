"""The OpenAPI document is frozen at the scaffold (DESIGN.md 10.1, 18.50): re-exported, it must equal the committed
apps/web/openapi.json byte for byte (the route bodies, docstrings and helpers must not move it)."""
from __future__ import annotations

import json

from kit import APP
from walkthrough_api.main import create_app
from walkthrough_api.openapi_export import main as export_main
from walkthrough_api.openapi_export import openapi_text

OPERATION_IDS = {'health', 'listProjects', 'getProject', 'getThumbnail', 'getVersion', 'getModel', 'getStages', 'getAsset',
                 'downloadMaxScript', 'downloadFurnitureCsv', 'downloadOfflineHtml', 'getFurnitureHeights',
                 'putFurnitureHeights'}
# The upload milestone's 24 (docs/upload/DESIGN.md U-13.1; pinned by its scaffold U0, U-15.1)
UPLOAD_OPERATION_IDS = {'createProject', 'listOffices', 'createUpload', 'getUpload', 'putUploadPart', 'completeUpload',
                        'cancelUpload', 'createBuild', 'listBuilds', 'getBuild', 'putBuildSettings', 'runBuild',
                        'cancelBuildRun', 'getBuildConversion', 'getBuildDrawing', 'getBuildPlan', 'getBuildOverlay',
                        'getBuildDiff', 'getBuildModel', 'getBuildStages', 'getBuildTopview', 'downloadBuildMaxScript',
                        'saveBuild', 'deleteBuild'}
# The owner's request of 12 Nov 2026: delete a project and a version (docs/contract-issues/DEL.md; additive)
DELETE_OPERATION_IDS = {'deleteProject', 'deleteVersion'}


def test_openapi_json_is_byte_identical() -> None:
    assert openapi_text().encode('utf-8') == (APP / 'apps' / 'web' / 'openapi.json').read_bytes()


def test_export_writes_the_same_bytes(tmp_path) -> None:
    out = tmp_path / 'openapi.json'
    assert export_main([str(out)]) == 0
    assert out.read_bytes() == (APP / 'apps' / 'web' / 'openapi.json').read_bytes()
    assert export_main([]) == 2


def test_operation_ids_and_texts() -> None:
    doc = create_app().openapi()
    ops = [op for path in doc['paths'].values() for op in path.values()]
    assert len(UPLOAD_OPERATION_IDS) == 24 and not OPERATION_IDS & UPLOAD_OPERATION_IDS
    assert not DELETE_OPERATION_IDS & (OPERATION_IDS | UPLOAD_OPERATION_IDS)
    assert {op['operationId'] for op in ops} == OPERATION_IDS | UPLOAD_OPERATION_IDS | DELETE_OPERATION_IDS
    assert len(ops) == 39
    for op in ops:
        ok = [s for s in op['responses'] if s.startswith('2')]          # 200, or 201 / 202 / 204 (U-13.1)
        assert len(ok) == 1, op['operationId']
        assert op['summary'] and op['description'] and op['responses'][ok[0]]['description']


def test_error_responses_are_typed() -> None:
    doc = json.loads(openapi_text())
    for path, item in doc['paths'].items():
        for op in item.values():
            for status, resp in op['responses'].items():
                if status in ('404', '409', '411', '412', '413', '503'):
                    assert resp['content']['application/json']['schema'] == {'$ref': '#/components/schemas/ErrorResponse'}, \
                        (path, status)


def test_upload_statuses() -> None:
    """201 / 202 / 204 where U-13.1 says so; every domain 422 of U-13.1 is declared as ErrorResponse beside FastAPI's
    own HTTPValidationError (as putFurnitureHeights declares it); the part body is raw octet-stream (U-5.1)."""
    doc = json.loads(openapi_text())
    ops = {op['operationId']: op for item in doc['paths'].values() for op in item.values()}
    want = {'createProject': '201', 'createUpload': '201', 'completeUpload': '201', 'createBuild': '201',
            'saveBuild': '201', 'runBuild': '202', 'cancelUpload': '204', 'deleteBuild': '204'}
    for op_id in UPLOAD_OPERATION_IDS:
        ok = [s for s in ops[op_id]['responses'] if s.startswith('2')]
        assert ok == [want.get(op_id, '200')], op_id
    for op_id in ('createProject', 'createUpload', 'putUploadPart', 'completeUpload', 'createBuild', 'putBuildSettings',
                  'saveBuild'):
        refs = [s['$ref'] for s in ops[op_id]['responses']['422']['content']['application/json']['schema']['anyOf']]
        assert refs == ['#/components/schemas/ErrorResponse', '#/components/schemas/HTTPValidationError'], op_id
    assert list(ops['putUploadPart']['requestBody']['content']) == ['application/octet-stream']
    params = {p['name'] for p in ops['getBuild']['parameters']}
    assert params == {'projectId', 'buildId', 'withSettings'}
