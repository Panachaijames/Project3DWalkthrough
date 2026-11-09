"""A step child: `python -B -P -m walkthrough_builder.step <read|suggest|build|check|audit> <args.json>`
(docs/upload/DESIGN.md U-3.2, U-3.5).

The worker (job.py) runs every heavy step as one of these, inside a Job Object (isolate.py). `args.json` names the
inputs and two files the child writes:
  * `events` (JSON lines, appended and flushed): `{"t": "log", "level", "text"}` from the step's `log()` and
    `{"t": "progress", "step", "f"}` from U3's `progress()`; the worker tails it for job.json;
  * `result` (JSON): `{"ok": true, ...}` or `{"ok": false, "code", "message", "type", "step"}`.
Exit code 0 when it worked, 1 when it raised, **75 on MemoryError** (isolate classifies `*_memory`, U-3.5). An exception
with a `code` attribute that is a RunErrorCode (`area_empty`, `align_failed`, `no_floors`, `bad_settings`, ...) keeps its
code and message (a plain sentence); any other becomes the step's `*_failed`.

Steps (U1 calls U2, U3 and U4 only through contracts.py):
  * read    contracts.read_source(dxf, units, out_dir, source=, log=)            -> {read: ReadResult}
  * suggest contracts.suggest(drawings, office); contracts.propose_settings(spec, drawings, suggestions, conversions,
            latest_version) -> writes suggestions.json and proposed-settings.json
  * build   contracts.build(ctx, log, progress); contracts.write_outputs(result, ctx, log) -> {outputs: {name: path}}
  * check   losscheck.check(...) (U1)                                           -> writes the ConversionReport
  * audit   convert.audit(dxf): ezdxf.recover opens the converted DXF (U1)      -> {audit: {...}}

**The test registry:** `REGISTRY` maps `read`, `suggest`, `propose`, `build`, `outputs` (and `check`, `audit`) to the
callables used in place of the real ones. A test points `WALKTHROUGH_STEP_FAKES` at a Python file; the child loads it
first (by path) and that file fills `REGISTRY` with fakes (same signatures). Production never sets it.

Owner: U1.
"""
from __future__ import annotations

import importlib.util
import json
import os
import sys
import time
import traceback
from pathlib import Path

from . import jsonfile

#: step name -> the callable run for it (tests register fakes here, through WALKTHROUGH_STEP_FAKES)
REGISTRY: dict = {}
EXIT_MEMORY = 75
FAKES_ENV = 'WALKTHROUGH_STEP_FAKES'
#: the codes a step may report as its own (upload-contracts.ts RunErrorCode)
RUN_ERROR_CODES = frozenset({
    'not_a_drawing', 'unsupported_version', 'convert_failed', 'convert_timeout', 'convert_memory',
    'check_failed', 'read_failed', 'read_timeout', 'read_memory',
    'no_floors', 'bad_settings', 'area_empty', 'align_failed',
    'detect_failed', 'build_failed', 'build_timeout', 'build_memory', 'invalid_output',
    'cancelled', 'interrupted', 'internal'})


def _default(name: str):
    from . import contracts
    if name == 'check':
        from .losscheck import check
        return check
    if name == 'audit':
        from .convert import audit
        return audit
    return {'read': contracts.read_source, 'suggest': contracts.suggest, 'propose': contracts.propose_settings,
            'build': contracts.build, 'outputs': contracts.write_outputs}[name]


def impl(name: str):
    """The callable for step `name`: a registered fake, else the real one."""
    return REGISTRY.get(name) or _default(name)


def load_fakes() -> None:
    """Loads the file WALKTHROUGH_STEP_FAKES names (tests only); it registers fakes in REGISTRY."""
    path = os.environ.get(FAKES_ENV)
    if not path:
        return
    # run as `python -m walkthrough_builder.step` this module is __main__: the fakes' `from walkthrough_builder import
    # step` must reach THIS module's REGISTRY, not a second copy of it
    me = sys.modules[__name__]
    if __name__ != 'walkthrough_builder.step':
        sys.modules['walkthrough_builder.step'] = me
        import walkthrough_builder
        walkthrough_builder.step = me                                  # type: ignore[attr-defined]
    spec = importlib.util.spec_from_file_location('walkthrough_step_fakes', path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f'cannot load the step fakes {path}')
    mod = importlib.util.module_from_spec(spec)
    sys.modules['walkthrough_step_fakes'] = mod
    spec.loader.exec_module(mod)


class Events:
    """The child's side of the events file: one JSON object per line, flushed at once."""

    def __init__(self, path: str | os.PathLike | None) -> None:
        self.f = open(path, 'a', encoding='utf-8', newline='\n') if path else None

    def _put(self, obj: dict) -> None:
        if self.f is not None:
            self.f.write(json.dumps(obj, ensure_ascii=False) + '\n')
            self.f.flush()

    def log(self, text: str, level: str = 'info') -> None:
        text = str(text)
        print(text, flush=True)
        self._put({'t': 'log', 'level': level if level in ('info', 'warn', 'error') else 'info', 'text': text,
                   'at': time.time()})

    def progress(self, step: str, f: float) -> None:
        try:
            f = float(f)
        except (TypeError, ValueError):
            f = 0.0
        self._put({'t': 'progress', 'step': str(step), 'f': min(1.0, max(0.0, f)), 'at': time.time()})

    def close(self) -> None:
        if self.f is not None:
            self.f.close()
            self.f = None


def _read(args: dict, ev: Events) -> dict:
    res = impl('read')(Path(args['dxf']), args.get('units'), Path(args['out_dir']), source=args['source'], log=ev.log)
    return {'read': dict(res)}


def _suggest(args: dict, ev: Events) -> dict:
    drawings = [jsonfile.read(p) for p in args['drawings']]
    conversions = [jsonfile.read(p) for p in args['conversions']]
    spec = jsonfile.read(args['spec'])
    latest = None
    if args.get('latest_version'):
        lv = args['latest_version']
        latest = {'model': jsonfile.read(lv['model']), 'msName': lv.get('msName')}
    ev.progress('suggest', 0.0)
    suggestions = impl('suggest')(drawings, args.get('office'))
    jsonfile.write(args['suggestions_out'], suggestions)
    ev.progress('suggest', 0.5)
    proposed = impl('propose')(spec, drawings, suggestions, conversions, latest)
    jsonfile.write(args['proposed_out'], proposed)
    ev.progress('suggest', 1.0)
    return {}


def _build(args: dict, ev: Events) -> dict:
    ctx = jsonfile.read(args['context'])
    result = impl('build')(ctx, ev.log, ev.progress)
    ev.progress('outputs', 0.0)
    outputs = impl('outputs')(result, ctx, ev.log)
    ev.progress('outputs', 1.0)
    seconds = result.get('seconds') if isinstance(result, dict) else None
    return {'outputs': {str(k): str(v) for k, v in dict(outputs).items()},
            'seconds': seconds if isinstance(seconds, dict) else {}}


def _check(args: dict, ev: Events) -> dict:
    rep = impl('check')(Path(args['dwg']), Path(args['dxf']), Path(args['log']), libredwg=Path(args['libredwg']),
                        source=args['source'], converter=args.get('converter'), convert=args['convert'],
                        audit=args.get('audit') or {}, log=ev.log, dwgread_stderr=Path(args['dwgread_stderr'])
                        if args.get('dwgread_stderr') else None)
    jsonfile.write(args['report'], rep)
    return {'verdict': rep.get('verdict')}


def _audit(args: dict, ev: Events) -> dict:
    return {'audit': impl('audit')(Path(args['dxf']))}


RUNNERS = {'read': _read, 'suggest': _suggest, 'build': _build, 'check': _check, 'audit': _audit}


def _write_result(path: str | None, obj: dict) -> None:
    if path:
        jsonfile.write(path, obj)


def main(argv: list[str] | None = None) -> int:
    """Runs one step from its args.json and writes its result; 75 on MemoryError."""
    argv = sys.argv[1:] if argv is None else argv
    if len(argv) != 2 or argv[0] not in RUNNERS:
        print(f'usage: python -m walkthrough_builder.step <{"|".join(RUNNERS)}> <args.json>', file=sys.stderr)
        return 2
    sys.dont_write_bytecode = True
    kind, args_path = argv
    args = jsonfile.read(args_path)
    ev = Events(args.get('events'))
    result_path = args.get('result')
    try:
        load_fakes()
        out = RUNNERS[kind](args, ev)
        ev.close()
        _write_result(result_path, {'ok': True, **out})
        return 0
    except MemoryError:
        try:
            ev.close()
            _write_result(result_path, {'ok': False, 'code': None, 'message': 'out of memory', 'type': 'MemoryError',
                                        'step': None})
        except BaseException:                                          # noqa: BLE001 - nothing more can be done
            pass
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(EXIT_MEMORY)
    except Exception as exc:                                           # noqa: BLE001 - every failure is reported
        traceback.print_exc()
        code = getattr(exc, 'code', None)
        try:
            ev.close()
            _write_result(result_path, {
                'ok': False, 'code': code if code in RUN_ERROR_CODES else None,
                'message': str(exc) or type(exc).__name__, 'type': type(exc).__name__,
                'step': getattr(exc, 'step', None) if isinstance(getattr(exc, 'step', None), str) else None})
        except Exception:                                              # noqa: BLE001
            traceback.print_exc()
        return 1


if __name__ == '__main__':
    sys.exit(main())
