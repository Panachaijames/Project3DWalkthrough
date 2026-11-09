"""DWG -> DXF with LibreDWG's dwg2dxf in a Job Object (docs/upload/DESIGN.md U-6.1, U-6.2).

Per DWG, in a fresh folder (the run's `out/tmp/convert-<i>/`): the upload copied in as `input.dwg` (the original name
never reaches the command line: the converter echoes paths), then `dwg2dxf.exe -y -o plan.dxf input.dwg` as a LEAF child
(`isolate.run`: ActiveProcessLimit 1, the time and memory caps of `JobSpec.limits.convert`, the DXF watched and killed
past 1.5 GB), stdout and stderr to files, joined into `convert.log`. Success = exit 0 **and** `plan.dxf` exists and is
not empty **and** `ezdxf.recover` opens it (`audit()`, run by the worker as the `audit` step child in its own Job
Object AT THE SAME TIME as the loss check, since both only read the DXF; its error and fix counts go into the report,
and a DXF it cannot open fails the conversion with `convert_*`). The exit code alone never decides: LibreDWG exits 0
with ERROR lines.

`check_header()` reads the first bytes before anything runs: `AC1012` (R13) or newer converts; `AC1001` - `AC1011` and
the pre-R10 prefixes `AC1.` / `AC2.` are `unsupported_version`; anything else `not_a_drawing` (U-5.1).

Owner: U1. LibreDWG is GPL-3.0-or-later and runs only as a separate program here (U-6.1): nothing links or loads it.
"""
from __future__ import annotations

import hashlib
import re
import shutil
import sys
from collections.abc import Callable
from pathlib import Path

from . import isolate
from .contracts import ConvertResult

#: the converted DXF may not grow past this (U-3.5: 1.5 GB on disk, killed beyond)
MAX_DXF_BYTES = 1536 * 1024 * 1024
#: the converter's messages (stdout and stderr together) may not grow past this (UR, V3-7: the largest convert.log of the
#: project's drawings is 440 KB, the presidential suite's): beyond it the converter is stopped and the conversion fails
MAX_TEXT_BYTES = 64 * 1024 * 1024
_DWG = re.compile(rb'^AC(\d{4})')
_PRE_R10 = re.compile(rb'^AC[12]\.\d')
_VERSION = re.compile(r'libredwg-(\d+(?:\.\d+)*)', re.IGNORECASE)


class HeaderError(ValueError):
    def __init__(self, code: str, message: str, version: str | None) -> None:
        super().__init__(message)
        self.code = code
        self.version = version


def check_header(path: Path) -> str:
    """The DWG's version string (`AC1032` ...) from its first 6 bytes; raises HeaderError with `unsupported_version`
    (before R13: AC1001 - AC1011, AC1.x, AC2.x) or `not_a_drawing`."""
    with open(path, 'rb') as f:
        head = f.read(6)
    m = _DWG.match(head)
    if m:
        version = head.decode('ascii')
        if int(m.group(1)) < 1012:
            raise HeaderError('unsupported_version', f'a DWG older than AutoCAD R13 ({version})', version)
        return version
    if _PRE_R10.match(head):
        version = head.decode('ascii', 'replace')
        raise HeaderError('unsupported_version', f'a DWG older than AutoCAD R13 ({version})', version)
    raise HeaderError('not_a_drawing', 'not a DWG drawing (its first bytes are not a DWG header)', None)


def exe(libredwg: Path, name: str) -> Path:
    return Path(libredwg) / (f'{name}.exe' if sys.platform == 'win32' else name)


def converter_info(libredwg: Path) -> dict:
    """ConversionReport.converter: {name: 'libredwg', version, exeSha1} (the version from the vendored folder's name,
    the sha1 of the dwg2dxf that runs)."""
    m = _VERSION.search(Path(libredwg).resolve().name)
    data = exe(libredwg, 'dwg2dxf').read_bytes()
    return {'name': 'libredwg', 'version': m.group(1) if m else 'unknown', 'exeSha1': hashlib.sha1(data).hexdigest()}


def convert(dwg: Path, work_dir: Path, *, libredwg: Path, seconds: float, memory_mb: int,
            cancelled: Callable[[], object] | None = None, poll: Callable[[], None] | None = None,
            env: dict | None = None, max_bytes: int = MAX_DXF_BYTES, max_text: int = MAX_TEXT_BYTES) -> ConvertResult:
    """Copies `dwg` in as `work_dir/input.dwg` (unless it is that file) and runs `dwg2dxf -y -o plan.dxf input.dwg`
    (U-6.2). Returns the ConvertResult (contracts.py) plus `code` (None when the DXF was written; else a RunErrorCode
    or 'cancelled'), `detail` (a plain sentence) and the raw isolate result under `run`."""
    work_dir = Path(work_dir)
    work_dir.mkdir(parents=True, exist_ok=True)
    src = work_dir / 'input.dwg'
    if Path(dwg).resolve() != src.resolve():
        shutil.copyfile(dwg, src)
    out, err = work_dir / 'dwg2dxf.out.txt', work_dir / 'dwg2dxf.err.txt'
    dxf, log = work_dir / 'plan.dxf', work_dir / 'convert.log'
    if dxf.exists():
        dxf.unlink()
    res = isolate.run([str(exe(libredwg, 'dwg2dxf')), '-y', '-o', 'plan.dxf', 'input.dwg'], cwd=work_dir,
                      env=env if env is not None else isolate.child_env(), seconds=seconds, memory_mb=memory_mb,
                      stdout=out, stderr=err, cancelled=cancelled, watch_file=dxf, watch_max_bytes=max_bytes,
                      leaf=True, poll=poll, watch_text_max_bytes=max_text)
    with open(log, 'wb') as fl:                                    # streamed: never the whole text in memory
        for part in (out, err):
            with open(part, 'rb') as fp:
                shutil.copyfileobj(fp, fl, 1024 * 1024)
    code = isolate.classify(res, 'convert')
    detail = ''
    if res.get('killed_for_text'):
        code, detail = 'convert_failed', (f'the converter printed more than {max_text // 2 ** 20:,} MB of messages '
                                          f'and was stopped')
    elif res['killed_for_size']:
        code, detail = 'convert_failed', f'the converted file grew past {max_bytes // 2 ** 20:,} MB and was stopped'
    elif code == 'convert_timeout':
        detail = f'the converter took longer than {seconds:.0f} s and was stopped'
    elif code == 'convert_memory':
        detail = f'the converter needed more than {memory_mb:,} MB and was stopped'
    elif code == 'convert_failed':
        detail = f'the converter stopped with exit code {res["exit_code"]}'
    elif code is None and (not dxf.is_file() or dxf.stat().st_size == 0):
        code, detail = 'convert_failed', 'the converter wrote no drawing (an empty file)'
    return {'dxf': str(dxf), 'log': str(log), 'seconds': res['seconds'], 'peak_mb': res['peak_mb'],
            'exit_code': res['exit_code'], 'memory_hit': bool(res['memory_hit']),
            'code': code, 'detail': detail, 'run': res}                       # type: ignore[typeddict-unknown-key]


def audit(dxf: Path) -> dict:
    """ezdxf.recover opens the DXF (the last part of U-6.2's success rule): {acadVersion, insUnits, auditErrors,
    auditFixes}. Runs in the `audit` step child (step.py), never in the worker."""
    from ezdxf import recover
    doc, auditor = recover.readfile(str(dxf))
    ins = doc.header.get('$INSUNITS', None)
    return {'acadVersion': doc.dxfversion, 'insUnits': int(ins) if isinstance(ins, int) else None,
            'auditErrors': len(auditor.errors), 'auditFixes': len(auditor.fixes)}
