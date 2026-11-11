"""Fixtures of the API's pytest suite (DESIGN.md 17.3); constants and helpers are in kit.py.

Everything a run writes goes under WT_TMP (builder E's row: %TEMP%\\wt-e; DESIGN.md 3): pytest's own tmp_path as well
(basetemp), the session's seeded store (from the real prototypes, which are only read) and every store copy a test
changes. Nothing imports prototype Python.
"""
from __future__ import annotations

import os
import shutil
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from kit import PROTOTYPES, RUN, TEMPLATE, make_client, pycache_dirs
from walkthrough_api.seed.build import seed


def pytest_configure(config: pytest.Config) -> None:
    if not config.option.basetemp:
        RUN.mkdir(parents=True, exist_ok=True)           # pytest makes basetemp, not its parent (U0.md item 2)
        config.option.basetemp = str(RUN / 'pytest')
    # the upload milestone's integration tests: the real worker (docs/upload/ACCEPTANCE.md 2.2). They skip while the
    # builder is not built or missing, and fail instead under WT_INTEGRATION=1 (tests/builderkit.py).
    config.addinivalue_line('markers', 'builder: runs the real builder worker (never holds the machine run lock)')
    config.addinivalue_line('markers', 'rooms_worker: the rooms milestone\'s tests with the real worker (step R5); '
                                       'deselected without WT_INTEGRATION=1 until their module turns '
                                       'RUN_WITHOUT_THE_FLAG on')


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    """The rooms milestone's real-worker tests (test_r5_builder.py) run only under WT_INTEGRATION=1 until R1 - R3 have
    landed (their module's RUN_WITHOUT_THE_FLAG): without it they are deselected, not skipped, so a plain run skips
    nothing and does not depend on the state of the builder's modules being written in parallel."""
    if os.environ.get('WT_INTEGRATION') == '1':
        return
    keep: list[pytest.Item] = []
    drop: list[pytest.Item] = []
    for item in items:
        module = getattr(item, 'module', None)
        off = item.get_closest_marker('rooms_worker') is not None and not getattr(module, 'RUN_WITHOUT_THE_FLAG', False)
        (drop if off else keep).append(item)
    if drop:
        config.hook.pytest_deselected(items=drop)
        items[:] = keep


@pytest.fixture(scope='session')
def pycache_before() -> set[str]:
    return pycache_dirs()


@pytest.fixture(scope='session')
def seeded(pycache_before: set[str]) -> Path:
    """The store seeded once per session from the real prototype folders: %WT_TMP%/api-tests/seeded/data."""
    data = RUN / 'seeded' / 'data'
    if data.exists():
        shutil.rmtree(data)
    seed(PROTOTYPES, data, force=True, log=lambda _line: None)
    return data


@pytest.fixture
def data_copy(seeded: Path, tmp_path: Path) -> Path:
    """A private copy of the seeded store for a test that writes."""
    dst = tmp_path / 'data'
    shutil.copytree(seeded, dst)
    return dst


@pytest.fixture
def template_file(tmp_path: Path) -> Path:
    p = tmp_path / 'viewer-template.html'
    p.write_bytes(TEMPLATE.encode('utf-8'))
    return p


@pytest.fixture
def client(data_copy: Path, template_file: Path) -> Iterator[TestClient]:
    with make_client(data_copy, template_file) as c:
        yield c
