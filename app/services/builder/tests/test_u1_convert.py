"""convert.py without a real drawing (docs/upload/DESIGN.md U-5.1, U-6.1, U-6.2; ACCEPTANCE A-3): the header check refuses
DWGs older than R13 (`AC1009`, `AC1.50`, `AC2.10` ...) and anything that is not a DWG (a renamed text file, an empty file);
the converter's identity comes from the vendored folder; a truncated DWG fails with `convert_failed` (heavy: the real
converter runs)."""
from __future__ import annotations

from pathlib import Path

import pytest

import kit
from walkthrough_builder import convert, jsonfile


@pytest.mark.parametrize('head,version', [(b'AC1032\x00\x00', 'AC1032'), (b'AC1024', 'AC1024'), (b'AC1012....', 'AC1012'),
                                          (b'AC1015', 'AC1015'), (b'AC1040', 'AC1040')])
def test_supported_headers(tmp_path: Path, head: bytes, version: str) -> None:
    p = tmp_path / 'x.dwg'
    p.write_bytes(head + b'\x00' * 100)
    assert convert.check_header(p) == version


@pytest.mark.parametrize('head', [b'AC1009', b'AC1001', b'AC1011', b'AC1.50', b'AC1.40', b'AC2.10', b'AC2.22'])
def test_pre_r13_headers_are_unsupported(tmp_path: Path, head: bytes) -> None:
    p = tmp_path / 'old.dwg'
    p.write_bytes(head + b'\x00' * 100)
    with pytest.raises(convert.HeaderError) as e:
        convert.check_header(p)
    assert e.value.code == 'unsupported_version' and 'older than AutoCAD R13' in str(e.value)
    assert e.value.version == head.decode()


@pytest.mark.parametrize('data', [b'', b'hello, this is a text file\r\n', b'0\nSECTION\n2\nHEADER\n', b'%PDF-1.7',
                                  b'AC10', b'ACXXXX', b'\x00\x01\x02'])
def test_not_a_drawing(tmp_path: Path, data: bytes) -> None:
    p = tmp_path / 'renamed.dwg'
    p.write_bytes(data)
    with pytest.raises(convert.HeaderError) as e:
        convert.check_header(p)
    assert e.value.code == 'not_a_drawing'


def test_converter_info_from_the_vendored_folder(libredwg: Path) -> None:
    info = convert.converter_info(libredwg)
    manifest = jsonfile.read(kit.APP / 'vendor' / 'libredwg.manifest.json')
    exe = next(f for f in manifest['files'] if f['path'].endswith('dwg2dxf.exe'))
    assert info == {'name': 'libredwg', 'version': '0.14', 'exeSha1': exe['sha1']}


@pytest.mark.heavy
def test_truncated_dwg_fails_to_convert(libredwg: Path, tmp_path: Path) -> None:
    data = (kit.PROJECT / kit.DRAWINGS['bank1']).read_bytes()[:120_000]
    src = tmp_path / 'truncated.dwg'
    src.write_bytes(data)
    assert convert.check_header(src) == 'AC1024'                 # the header is fine: the converter finds the damage
    res = convert.convert(src, tmp_path / 'work', libredwg=libredwg, seconds=60, memory_mb=1024)
    assert res['code'] == 'convert_failed' and res['exit_code'] not in (0, None)
    assert 'exit code' in res['detail']
    assert 'Failed to decode' in Path(res['log']).read_text(encoding='utf-8', errors='replace')
    assert (tmp_path / 'work' / 'input.dwg').read_bytes() == data


@pytest.mark.heavy
def test_converter_time_limit(libredwg: Path, tmp_path: Path) -> None:
    """A converter that does not finish in time is killed: convert_timeout."""
    res = convert.convert(kit.PROJECT / kit.DRAWINGS['bank2'], tmp_path / 'w', libredwg=libredwg, seconds=0.05,
                          memory_mb=2048)
    assert res['code'] == 'convert_timeout' and 'longer than' in res['detail']


@pytest.mark.heavy
def test_converter_memory_limit(libredwg: Path, tmp_path: Path) -> None:
    """A converter that dies at its memory cap is convert_memory, not convert_failed (U-3.5)."""
    res = convert.convert(kit.PROJECT / kit.DRAWINGS['bank2'], tmp_path / 'w', libredwg=libredwg, seconds=120,
                          memory_mb=40)
    assert res['code'] == 'convert_memory', res
    assert res['memory_hit']
