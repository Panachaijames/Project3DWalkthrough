"""Constants and helpers shared by the API tests (fixtures are in conftest.py)."""
from __future__ import annotations

import os
import tempfile
from pathlib import Path

from fastapi.testclient import TestClient

from walkthrough_api.jsonio import loads_strict
from walkthrough_api.main import create_app
from walkthrough_api.settings import Settings

APP = Path(__file__).resolve().parents[3]
PROTOTYPES = APP.parent
FIXTURES = APP / 'fixtures'
WT_TMP = Path(os.environ.get('WT_TMP') or Path(os.environ.get('TEMP') or tempfile.gettempdir()) / 'wt-e')
RUN = WT_TMP / 'api-tests'
PROTOTYPE_FOLDERS = ('bank_test', 'presidential_test', 'cad_test', 'hotel_test')

# Every project version of the seed -> the names of its fixtures and captured facts.
VERSIONS = {
    ('bank-sampeng', 1): {'model': 'bank-v1', 'facts': 'bank-sampeng-v1', 'csv': None, 'stages': 'bank-v1'},
    ('bank-sampeng', 2): {'model': 'bank-v2', 'facts': 'bank-sampeng-v2', 'csv': 'bank-v2', 'stages': 'bank-v2'},
    ('presidential-suite', 1): {'model': 'suite', 'facts': 'presidential-suite', 'csv': 'suite', 'stages': None},
    ('sukhumvit-house', 1): {'model': 'house', 'facts': 'sukhumvit-house', 'csv': 'house', 'stages': None},
    ('hotel-lobby', 1): {'model': 'hotel', 'facts': 'hotel-lobby', 'csv': 'hotel', 'stages': None},
}
VERSION_IDS = [f'{p}-v{n}' for p, n in VERSIONS]

# A hand-made offline template: each marker once, and replacement patterns in its own tail (they must stay as they are).
TEMPLATE = ('<!doctype html><html><head><meta name="model-data" content="__WTV_STAMP__"><title>t</title></head>'
            '<body><div id="wtv-app"></div><script type="application/json" id="wtv-data">__WTV_DATA__</script>'
            "<script>/* $' $& $` $$ */</script></body></html>\n")


def read_json(path: Path) -> object:
    return loads_strict(Path(path).read_bytes())


def facts(name: str) -> dict:
    return read_json(FIXTURES / 'prototype' / f'{name}.json')  # type: ignore[return-value]


def pycache_dirs() -> set[str]:
    """Every __pycache__ folder in the prototype folders the seed reads (the seed must never add one)."""
    out = set()
    for name in PROTOTYPE_FOLDERS:
        for root, dirs, _files in os.walk(PROTOTYPES / name):
            out.update(str(Path(root, d).relative_to(PROTOTYPES)) for d in dirs if d == '__pycache__')
    return out


def tree(root: Path, skip_seeded_at: bool = False) -> dict[str, bytes]:
    """Every file under root (relative POSIX path -> bytes); version.json's seed.seededAt blanked when asked."""
    out = {}
    for p in sorted(Path(root).rglob('*')):
        if p.is_file():
            data = p.read_bytes()
            if skip_seeded_at and p.name == 'version.json':
                v = loads_strict(data)
                v['seed']['seededAt'] = '-'
                data = repr(v).encode()
            out[p.relative_to(root).as_posix()] = data
    return out


#: Every TestClient talks to the API as a browser on this machine does: Host 127.0.0.1 (the API refuses other names,
#: settings.allowed_hosts; TestClient's own default, 'testserver', is one of those).
BASE_URL = 'http://127.0.0.1'


def api_settings(data: Path, template: Path, **extra: object) -> Settings:
    """The API's settings in a test: the store given, the cache under WT_TMP (never the default one, WORK_BREAKDOWN 0)."""
    return Settings(data_dir=data, offline_template=template,
                    cors_origins=('http://127.0.0.1:5710', 'http://localhost:5710'),
                    cache_dir=RUN / 'cache', **extra)  # type: ignore[arg-type]


def make_client(data: Path, template: Path, raise_server_exceptions: bool = True, jobs: object = None,
                **settings: object) -> TestClient:
    """A client of a fresh app over `data`; `jobs` = the job runner (default: the LocalJobRunner)."""
    return TestClient(create_app(api_settings(data, template, **settings), jobs=jobs),  # type: ignore[arg-type]
                      base_url=BASE_URL, raise_server_exceptions=raise_server_exceptions)
