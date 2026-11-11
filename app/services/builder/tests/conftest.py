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

The rooms milestone (docs/rooms/WORK_BREAKDOWN.md R0 item 10; added by its scaffold R0, frozen again):
  * marker `acceptance`: the costliest runs (every door undone, the two-process builds). Tests marked so are DESELECTED
    unless WT_ACCEPTANCE=1, so a plain run skips nothing.
  * `ref_r0`: R0's reference folder (WT_REF_R0, default %TEMP%\\wt-r0\\ref): the new suite read by the app's reader.
  * WT_INTEGRATION=1: a missing reference fails instead of skipping (`ref`, `ref_r0`).
  * session fixtures, each built ONCE per run with the machine run lock held while it builds (so the tests that use
    them need no `heavy` mark for the build itself; mark a test `heavy` when it builds again in the test):
      `bank_rooms`, `house_rooms`, `suite_rooms`, `tower_rooms`, `suite_revit_rooms`: the new-rule build of a
        reference drawing with fixtures/upload/settings/<name>-rooms.json -> { name, settings, sources, res, logs,
        tmp, project } (rooms_kit.rooms_build). Shared by R1's and R2's tests and RI's golden: READ ONLY, copy before
        you change anything;
      `reference_building`: the reference building's two plans made at test time and read by the app's reader, with
        the settings its fixtures were built with -> { plan, settings, sources, dir } (rooms_kit.reference_plan).
"""
from __future__ import annotations

import json
import os
import shutil
import sys
from collections.abc import Iterator
from pathlib import Path

import pytest

import kit
import rooms_kit
from walkthrough_builder import oslock


def pytest_configure(config: pytest.Config) -> None:
    if not config.option.basetemp:
        config.option.basetemp = str(kit.RUN / 'pytest')
    os.environ.setdefault('WALKTHROUGH_DATA_DIR', str(kit.RUN / 'data'))
    os.environ.setdefault('WALKTHROUGH_CACHE_DIR', str(kit.RUN / 'cache'))
    sys.dont_write_bytecode = True
    config.addinivalue_line('markers', 'acceptance: the costliest runs of the rooms milestone (every door undone, the '
                                       'two-process builds); deselected unless WT_ACCEPTANCE=1')
    for p in (os.environ['WALKTHROUGH_DATA_DIR'], os.environ['WALKTHROUGH_CACHE_DIR']):
        if Path(p).resolve() == (kit.APP / 'data').resolve():
            raise pytest.UsageError('WALKTHROUGH_DATA_DIR / CACHE_DIR must not be app/data in a test (WORK_BREAKDOWN 0)')


def pytest_collection_modifyitems(items: list[pytest.Item]) -> None:
    for item in items:
        if item.get_closest_marker('heavy') and item.get_closest_marker('worker'):
            raise pytest.UsageError(f'{item.nodeid}: a test is `heavy` or `worker`, never both (the run lock belongs to '
                                    f'the process that holds it; ACCEPTANCE 2.1)')
    if not kit.ACCEPTANCE:                                    # deselected, not skipped: a plain run skips nothing
        drop = [item for item in items if item.get_closest_marker('acceptance')]
        if drop:
            drop[0].config.hook.pytest_deselected(items=drop)
            items[:] = [item for item in items if item.get_closest_marker('acceptance') is None]


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
    """WT_REF (default %TEMP%\\wt-u0\\ref): the scaffold's make:reference output. Read-only. Missing: the test is
    skipped, or fails under WT_INTEGRATION=1 (docs/rooms/DESIGN.md R-13)."""
    if not (kit.REF / 'manifest.json').exists():
        kit.missing_reference(f'no reference folder at {kit.REF} (WT_REF): the scaffold makes it with '
                              f'`npm run make:reference -- --out %TEMP%\\wt-u0\\ref`')
    return kit.REF


@pytest.fixture(scope='session')
def ref_r0() -> Path:
    """WT_REF_R0 (default %TEMP%\\wt-r0\\ref): the rooms scaffold's reference folder, the new suite read by the app's
    reader (cache layout of U-4.2). Read-only. Missing: skipped, or failed under WT_INTEGRATION=1."""
    if not (kit.REF_R0 / 'suite-revit' / 'manifest.json').exists():
        kit.missing_reference(f'no new-suite reader cache at {kit.REF_R0}\\suite-revit (WT_REF_R0): make it with `node '
                              f'tools/run-builder-py.mjs tools/rooms/make-suite-cache.py`')
    return kit.REF_R0


def _rooms_build(name: str, ref: Path, tmp_path_factory: pytest.TempPathFactory) -> dict:
    tmp = tmp_path_factory.mktemp(f'rooms-{name}')
    with oslock.hold():                                       # the machine run lock while the session's build runs
        return rooms_kit.rooms_build(name, ref, tmp)


@pytest.fixture(scope='session')
def bank_rooms(ref: Path, tmp_path_factory: pytest.TempPathFactory) -> dict:
    """The bank built once with bank-rooms.json (the new rules). Read only."""
    return _rooms_build('bank', ref, tmp_path_factory)


@pytest.fixture(scope='session')
def house_rooms(ref: Path, tmp_path_factory: pytest.TempPathFactory) -> dict:
    """The house built once with house-rooms.json. Read only."""
    return _rooms_build('house', ref, tmp_path_factory)


@pytest.fixture(scope='session')
def suite_rooms(ref: Path, tmp_path_factory: pytest.TempPathFactory) -> dict:
    """The old suite built once with suite-rooms.json (about 1 GB and a minute at its worst). Read only."""
    return _rooms_build('suite', ref, tmp_path_factory)


@pytest.fixture(scope='session')
def tower_rooms(ref: Path, tmp_path_factory: pytest.TempPathFactory) -> dict:
    """The tower built once with tower-rooms.json. Read only."""
    return _rooms_build('tower', ref, tmp_path_factory)


@pytest.fixture(scope='session')
def suite_revit_rooms(ref: Path, ref_r0: Path, tmp_path_factory: pytest.TempPathFactory) -> dict:
    """The new suite built once with suite-revit-rooms.json, from R0's reader cache. Read only."""
    return _rooms_build('suite-revit', ref, tmp_path_factory)


@pytest.fixture(scope='session')
def reference_building(tmp_path_factory: pytest.TempPathFactory) -> dict:
    """The reference building (ACCEPTANCE 2.5): its two plans made at test time and read by the app's reader, and the
    BuildSettings its fixtures were built with -> { plan, settings, sources, dir }. Read only."""
    out = tmp_path_factory.mktemp('rooms-reference')
    plan = rooms_kit.reference_plan(out)
    s = json.loads((kit.ROOMS_FIXTURES / 'settings.reference.json').read_text(encoding='utf-8'))
    assert [x['sha1'] for x in s['sources']] == [x['sha1'] for x in plan['sources']], \
        'the reference drawings are not the bytes fixtures/rooms/settings.reference.json names'
    return {'plan': plan, 'settings': s, 'sources': plan['sources'], 'dir': out}


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
