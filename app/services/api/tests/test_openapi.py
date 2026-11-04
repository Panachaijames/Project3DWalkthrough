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
    assert {op['operationId'] for op in ops} == OPERATION_IDS and len(ops) == 13
    for op in ops:
        assert op['summary'] and op['description'] and op['responses']['200']['description']


def test_error_responses_are_typed() -> None:
    doc = json.loads(openapi_text())
    for path, item in doc['paths'].items():
        for op in item.values():
            for status, resp in op['responses'].items():
                if status in ('404', '503'):
                    assert resp['content']['application/json']['schema'] == {'$ref': '#/components/schemas/ErrorResponse'}, \
                        (path, status)
