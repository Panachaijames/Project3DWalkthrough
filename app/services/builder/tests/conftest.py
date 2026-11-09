"""Fixtures and markers of the builder's tests (scaffold U0; ACCEPTANCE 2.1; docs/upload/DESIGN.md U-3.5).

Markers (the machine run lock belongs to a PROCESS, so a test that holds it must never spawn a worker that waits on it):
  * `heavy`: a real drawing converted, read or built IN THE TEST PROCESS. An autouse fixture takes the machine run lock
    (%TEMP%\\walkthrough-run.lock, or WALKTHROUGH_RUN_LOCK) for the test and prints a line while it waits: another
    builder's drawing is running, let it wait. The presidential drawing needs about 1 GB and a minute: only in the tests
    that need it.
  * `worker`: a test that spawns the worker (job.py). It never takes the lock (the worker does); the `worker` fixture
    gives it a long timeout (kit.WORKER_TIMEOUT_S) and `report_queue()` to say "queued behind another run" instead of
    failing while the worker waits.
  A test marked both is refused.
Fixtures:
  * `ref`: the scaffold's `make:reference` folder (WT_REF, default %TEMP%\\wt-u0\\ref; read-only, never written, never
    re-made whole). Skips with a message when it is missing. A builder that needs a fresh copy of one drawing runs
    `npm run make:reference -- --only <drawing> --out <WT_TMP>\\ref` and points WT_REF there.
  * `private_lock`: WALKTHROUGH_RUN_LOCK set to a file under the test's tmp folder, for tests of the lock itself and of
    two workers on one lock.
Every test runs with WALKTHROUGH_DATA_DIR and WALKTHROUGH_CACHE_DIR under WT_TMP (set here when the run did not set them)
and pytest's tmp folders under WT_TMP\\pytest.
"""
from __future__ import annotations

import os
import shutil
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

import kit
from walkthrough_builder import oslock


def pytest_configure(config: pytest.Config) -> None:
    if not config.option.basetemp:
        config.option.basetemp = str(kit.RUN / 'pytest')
    os.environ.setdefault('WALKTHROUGH_DATA_DIR', str(kit.RUN / 'data'))
    os.environ.setdefault('WALKTHROUGH_CACHE_DIR', str(kit.RUN / 'cache'))
    sys.dont_write_bytecode = True
    for p in (os.environ['WALKTHROUGH_DATA_DIR'], os.environ['WALKTHROUGH_CACHE_DIR']):
        if Path(p).resolve() == (kit.APP / 'data').resolve():
            raise pytest.UsageError('WALKTHROUGH_DATA_DIR / CACHE_DIR must not be app/data in a test (WORK_BREAKDOWN 0)')


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        if item.get_closest_marker('heavy') and item.get_closest_marker('worker'):
            raise pytest.UsageError(f'{item.nodeid}: a test is `heavy` or `worker`, never both (the run lock belongs to '
                                    f'the process that holds it; ACCEPTANCE 2.1)')


@pytest.fixture(autouse=True)
def _heavy_lock(request: pytest.FixtureRequest) -> Iterator[None]:
    """Takes the machine run lock around a `heavy` test (U-3.5)."""
    if request.node.get_closest_marker('heavy') is None:
        yield
        return

    def waiting(secs: float) -> None:
        if int(secs) % 30 == 0:
            print(f'\n{request.node.nodeid}: waiting for the machine run lock {oslock.default_path()} '
                  f'({secs:.0f} s): another build or heavy test is running', file=sys.stderr, flush=True)

    with oslock.hold(wait=waiting):
        yield


class WorkerKit:
    """What a `worker` test gets: the timeout and a way to say the run is queued, not failing."""

    def __init__(self, node: str) -> None:
        self.node = node
        self.timeout = kit.WORKER_TIMEOUT_S
        self.queued_seconds = 0.0

    def report_queue(self, seconds: float) -> None:
        self.queued_seconds = seconds
        if int(seconds) % 30 == 0:
            print(f'\n{self.node}: the run is queued behind another run ({seconds:.0f} s); not a failure',
                  file=sys.stderr, flush=True)


@pytest.fixture
def worker(request: pytest.FixtureRequest) -> WorkerKit:
    if request.node.get_closest_marker('worker') is None:
        raise pytest.UsageError(f'{request.node.nodeid}: the `worker` fixture is for tests marked worker')
    return WorkerKit(request.node.nodeid)


@pytest.fixture(scope='session')
def ref() -> Path:
    """WT_REF (default %TEMP%\\wt-u0\\ref): the scaffold's make:reference output. Read-only."""
    if not (kit.REF / 'manifest.json').exists():
        pytest.skip(f'no reference folder at {kit.REF} (WT_REF): the scaffold makes it with '
                    f'`npm run make:reference -- --out %TEMP%\\wt-u0\\ref`')
    return kit.REF


@pytest.fixture
def private_lock(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """WALKTHROUGH_RUN_LOCK = a private file, for tests of the lock and of two workers on one lock."""
    p = tmp_path / 'private-run.lock'
    monkeypatch.setenv('WALKTHROUGH_RUN_LOCK', str(p))
    return p


@pytest.fixture
def libredwg() -> Path:
    """The vendored LibreDWG folder; skips when it is not extracted (npm run vendor:libredwg)."""
    if not (kit.LIBREDWG / 'dwg2dxf.exe').exists():
        pytest.skip(f'LibreDWG is not extracted at {kit.LIBREDWG}: run npm run vendor:libredwg')
    return kit.LIBREDWG


@pytest.fixture
def scratch(tmp_path: Path) -> Iterator[Path]:
    """An empty folder of the test's own (removed after a pass)."""
    d = tmp_path / 'scratch'
    d.mkdir()
    yield d
    shutil.rmtree(d, ignore_errors=True)
