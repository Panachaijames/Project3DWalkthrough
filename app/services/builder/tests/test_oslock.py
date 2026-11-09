"""oslock.py: one run at a time on the machine (docs/upload/DESIGN.md U-3.5). Every test uses a private lock file."""
from __future__ import annotations

import os
import time
from pathlib import Path

import pytest

import kit
from walkthrough_builder import oslock

TRY = '''
import sys
from walkthrough_builder import oslock
fd = oslock.try_acquire(sys.argv[1])
print('got' if fd is not None else 'busy', flush=True)
'''

HOLD = '''
import sys, time
from walkthrough_builder import oslock
with oslock.hold(sys.argv[1]):
    print('holding', flush=True)
    time.sleep(float(sys.argv[2]))
print('done', flush=True)
'''


def other_process_tries(path: Path) -> str:
    p = kit.python_child(TRY, str(path))
    out, err = p.communicate(timeout=60)
    assert p.returncode == 0, err
    return out.strip()


def test_default_path(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> None:
    monkeypatch.delenv('WALKTHROUGH_RUN_LOCK', raising=False)
    import tempfile
    assert oslock.default_path() == Path(tempfile.gettempdir()) / 'walkthrough-run.lock'
    monkeypatch.setenv('WALKTHROUGH_RUN_LOCK', str(tmp_path / 'x.lock'))
    assert oslock.default_path() == tmp_path / 'x.lock'


def test_private_lock_fixture(private_lock: Path) -> None:
    assert oslock.default_path() == private_lock


def test_held_here_busy_elsewhere_then_free(private_lock: Path) -> None:
    with oslock.hold() as p:
        assert p == private_lock
        assert other_process_tries(private_lock) == 'busy'
    assert other_process_tries(private_lock) == 'got'


def test_two_holds_in_one_process_wait_for_each_other(private_lock: Path) -> None:
    fd = oslock.try_acquire(private_lock)
    assert fd is not None
    try:
        assert oslock.try_acquire(private_lock) is None
    finally:
        oslock.release(fd)


def test_waits_for_another_process_and_reports(private_lock: Path) -> None:
    holder = kit.python_child(HOLD, str(private_lock), '1.6')
    assert holder.stdout.readline().strip() == 'holding'
    calls: list[float] = []
    t0 = time.monotonic()
    with oslock.hold(private_lock, wait=calls.append):
        waited = time.monotonic() - t0
    holder.wait(timeout=30)
    assert waited >= 1.0
    assert calls and calls[0] < 0.2          # called at once, then about once a second
    assert len(calls) <= 3


def test_released_when_the_holder_dies(private_lock: Path) -> None:
    holder = kit.python_child(HOLD, str(private_lock), '60')
    assert holder.stdout.readline().strip() == 'holding'
    assert oslock.try_acquire(private_lock) is None
    holder.kill()
    holder.wait(timeout=30)
    t0 = time.monotonic()
    with oslock.hold(private_lock, timeout=10):
        assert time.monotonic() - t0 < 10


def test_timeout_and_cancel(private_lock: Path) -> None:
    holder = kit.python_child(HOLD, str(private_lock), '30')
    assert holder.stdout.readline().strip() == 'holding'
    try:
        with pytest.raises(oslock.LockTimeout):
            with oslock.hold(private_lock, timeout=0.5):
                pass
        flag = {'n': 0}

        def cancelled() -> bool:
            flag['n'] += 1
            return flag['n'] > 3
        with pytest.raises(oslock.LockCancelled):
            with oslock.hold(private_lock, cancelled=cancelled):
                pass
    finally:
        holder.kill()
        holder.wait(timeout=30)


def test_lock_file_is_not_inherited_by_children(private_lock: Path) -> None:
    """A child started while the lock is held does not keep it after this process lets go (O_NOINHERIT)."""
    with oslock.hold(private_lock):
        sleeper = kit.python_child('import time; time.sleep(30)')
    try:
        assert other_process_tries(private_lock) == 'got'
    finally:
        sleeper.kill()
        sleeper.wait(timeout=30)


@pytest.mark.heavy
def test_heavy_marker_takes_the_machine_lock() -> None:
    """The autouse fixture holds the machine run lock (WALKTHROUGH_RUN_LOCK or %TEMP%\\walkthrough-run.lock) for a heavy
    test: another process finds it busy. (No private_lock here: autouse fixtures run before it.)"""
    assert other_process_tries(oslock.default_path()) == 'busy'


def test_a_test_is_never_both_heavy_and_worker(pytester_like=None) -> None:
    import conftest

    class Item:
        nodeid = 'x::y'

        def get_closest_marker(self, name: str):
            return object()
    with pytest.raises(pytest.UsageError, match='never both'):
        conftest.pytest_collection_modifyitems([Item()])
    assert os.environ['WALKTHROUGH_CACHE_DIR'] and os.environ['WALKTHROUGH_DATA_DIR']
