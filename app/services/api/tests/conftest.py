"""Fixtures of the API's pytest suite (DESIGN.md 17.3); constants and helpers are in kit.py.

Everything a run writes goes under WT_TMP (builder E's row: %TEMP%\\wt-e; DESIGN.md 3): pytest's own tmp_path as well
(basetemp), the session's seeded store (from the real prototypes, which are only read) and every store copy a test
changes. Nothing imports prototype Python.
"""
from __future__ import annotations

import shutil
from collections.abc import Iterator
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from kit import PROTOTYPES, RUN, TEMPLATE, make_client, pycache_dirs
from walkthrough_api.seed.build import seed


def pytest_configure(config: pytest.Config) -> None:
    if not config.option.basetemp:
        config.option.basetemp = str(RUN / 'pytest')


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
