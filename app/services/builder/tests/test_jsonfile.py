"""jsonfile.py: atomic JSON writes that another process reads (docs/upload/DESIGN.md U-3.2; ACCEPTANCE 2.1 U0).

The key test holds the target open in a SECOND PROCESS (CPython opens files without FILE_SHARE_DELETE, so os.replace onto
an open file fails with PermissionError, WinError 5, as when the API reads job.json): the write is retried and succeeds
once the reader lets go."""
from __future__ import annotations

import sys
import time
from pathlib import Path

import pytest

import kit
from walkthrough_builder import jsonfile

HOLD = '''
import sys, time
f = open(sys.argv[1], 'rb')
print('held', flush=True)
time.sleep(float(sys.argv[2]))
f.close()
print('released', flush=True)
'''


def hold_open(path: Path, seconds: float):
    p = kit.python_child(HOLD, str(path), str(seconds))
    assert p.stdout.readline().strip() == 'held'
    return p


def test_round_trip_pretty_and_compact(tmp_path: Path) -> None:
    obj = {'a': [1, 2.5, None, True], 'ชื่อ': '<img src=x>', 'z': {}}
    jsonfile.write(tmp_path / 'p.json', obj)
    raw = (tmp_path / 'p.json').read_bytes()
    assert raw.endswith(b'}\n') and not raw.startswith(b'\xef\xbb\xbf') and b'\r' not in raw
    assert jsonfile.read(tmp_path / 'p.json') == obj
    jsonfile.write(tmp_path / 'c.json', obj, pretty=False)
    assert (tmp_path / 'c.json').read_bytes() == b'{"a":[1,2.5,null,true],"\xe0\xb8\x8a\xe0\xb8\xb7\xe0\xb9\x88\xe0\xb8\xad":"<img src=x>","z":{}}'


def test_no_temp_file_left(tmp_path: Path) -> None:
    for i in range(5):
        jsonfile.write(tmp_path / 'job.json', {'i': i})
    assert [p.name for p in tmp_path.iterdir()] == ['job.json']


@pytest.mark.parametrize('data,msg', [
    (b'\xef\xbb\xbf{}', 'byte-order mark'),
    (b'{"a": NaN}', 'NaN is not JSON'),
    (b'{"a": 1, "a": 2}', 'repeated key'),
    (b'{"a": \xff}', 'not UTF-8'),
    (b'{"a": ', None),
])
def test_strict_read(tmp_path: Path, data: bytes, msg: str | None) -> None:
    (tmp_path / 'x.json').write_bytes(data)
    with pytest.raises(jsonfile.JsonError, match=msg):
        jsonfile.read(tmp_path / 'x.json')


def test_nan_is_not_written(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        jsonfile.write(tmp_path / 'x.json', {'a': float('nan')})
    assert not (tmp_path / 'x.json').exists()


@pytest.mark.skipif(sys.platform != 'win32', reason='sharing violations are a Windows behaviour')
def test_replace_retried_while_a_second_process_holds_the_file(tmp_path: Path) -> None:
    target = tmp_path / 'job.json'
    jsonfile.write(target, {'status': 'running'})
    reader = hold_open(target, 1.5)
    try:
        # the plain replace fails while the reader holds the file: the condition this module exists for
        import os
        import tempfile
        fd, tmp = tempfile.mkstemp(dir=tmp_path)
        os.close(fd)
        with pytest.raises(PermissionError):
            os.replace(tmp, target)
        os.unlink(tmp)
        t0 = time.monotonic()
        jsonfile.write(target, {'status': 'done'})
        waited = time.monotonic() - t0
    finally:
        reader.wait(timeout=30)
    assert reader.returncode == 0
    assert jsonfile.read(target) == {'status': 'done'}
    assert waited >= 0.5, f'the write did not wait for the reader ({waited:.2f} s)'
    assert [p.name for p in tmp_path.iterdir()] == ['job.json']


@pytest.mark.skipif(sys.platform != 'win32', reason='sharing violations are a Windows behaviour')
def test_gives_up_with_sharing_timeout(tmp_path: Path) -> None:
    target = tmp_path / 'job.json'
    jsonfile.write(target, {'status': 'running'})
    reader = hold_open(target, 4.0)
    try:
        t0 = time.monotonic()
        with pytest.raises(jsonfile.SharingTimeout):
            jsonfile.write(target, {'status': 'done'}, timeout=0.6)
        assert time.monotonic() - t0 >= 0.6
    finally:
        reader.wait(timeout=30)
    assert jsonfile.read(target) == {'status': 'running'}           # the old file is intact
    assert [p.name for p in tmp_path.iterdir()] == ['job.json']     # and no temp file is left


def test_default_retry_lasts_at_least_five_seconds() -> None:
    assert jsonfile.RETRY_S >= 5.0
    calls: list[float] = []
    t = [0.0]

    def failing():
        raise PermissionError(13, 'shared')

    def fake_sleep(d: float) -> None:
        calls.append(d)
        t[0] += d

    import walkthrough_builder.jsonfile as jf
    real = jf.time.monotonic
    jf.time.monotonic = lambda: t[0]
    try:
        if sys.platform == 'win32':
            with pytest.raises(jsonfile.SharingTimeout):
                jsonfile.retry_on_sharing(failing, sleep=fake_sleep)
            assert sum(calls) >= 5.0
            assert calls[0] == pytest.approx(0.010) and calls[1] == pytest.approx(0.020)
            assert max(calls) <= jsonfile.MAX_DELAY_S
    finally:
        jf.time.monotonic = real


def test_read_while_writes_go_on_in_another_process(tmp_path: Path) -> None:
    """A reader polling job.json in a loop never sees a partial file while this process rewrites it."""
    target = tmp_path / 'job.json'
    jsonfile.write(target, {'n': 0, 'pad': 'x' * 20000})
    code = '''
import sys, time, json
from walkthrough_builder import jsonfile
bad = 0; ok = 0; t_end = time.monotonic() + float(sys.argv[2])
while time.monotonic() < t_end:
    try:
        jsonfile.read(sys.argv[1]); ok += 1
    except jsonfile.JsonError:
        bad += 1
    except (PermissionError, FileNotFoundError):
        pass
print(json.dumps({'ok': ok, 'bad': bad}))
'''
    reader = kit.python_child(code, str(target), '2.0')
    t_end = time.monotonic() + 2.0
    n = 0
    while time.monotonic() < t_end:
        n += 1
        jsonfile.write(target, {'n': n, 'pad': 'x' * 20000})
    out, err = reader.communicate(timeout=30)
    import json
    res = json.loads(out.strip().splitlines()[-1])
    assert res['bad'] == 0, err
    assert res['ok'] > 0 and n > 5
