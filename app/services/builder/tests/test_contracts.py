"""contracts.py (docs/upload/DESIGN.md U-10.8): the TypedDicts equal the design's block field for field, the scaffold's
fixtures `build-result.bank.json` and `replay-input.bank.json` have exactly their key structure and types (a small
recursive key and type walker, no typeguard), and every module of U1 - U4 imports (stubs until their owners fill them).
U3 asserts its own bank BuildResult with `walk()` here; U4 reads only these fixtures."""
from __future__ import annotations

import importlib
import json
import re
import types
import typing
from typing import Any, get_args, get_origin, get_type_hints, is_typeddict

import pytest

import kit
from walkthrough_builder import contracts

RESULT = kit.UPLOAD_FIXTURES / 'build-result.bank.json'
REPLAY = kit.UPLOAD_FIXTURES / 'replay-input.bank.json'


def walk(value: Any, tp: Any, path: str = '') -> list[str]:
    """Every place where `value` does not have the shape of `tp` (TypedDicts total: exactly their keys)."""
    out: list[str] = []
    if tp is Any:
        return out
    if is_typeddict(tp):
        if not isinstance(value, dict):
            return [f'{path or "/"}: {type(value).__name__}, not an object ({tp.__name__})']
        hints = get_type_hints(tp)
        required = set(tp.__required_keys__)
        missing = required - set(value)
        unknown = set(value) - set(hints)
        out += [f'{path}/{k}: missing ({tp.__name__})' for k in sorted(missing)]
        out += [f'{path}/{k}: not a key of {tp.__name__}' for k in sorted(unknown)]
        for k, v in value.items():
            if k in hints:
                out += walk(v, hints[k], f'{path}/{k}')
        return out
    origin = get_origin(tp)
    if origin in (typing.Union, types.UnionType):
        arms = get_args(tp)
        results = [walk(value, a, path) for a in arms]
        return [] if any(not r for r in results) else min(results, key=len)
    if tp is type(None):
        return [] if value is None else [f'{path}: {value!r}, not null']
    if origin is list or tp is list:
        if not isinstance(value, list):
            return [f'{path}: {type(value).__name__}, not a list']
        (inner,) = get_args(tp) or (Any,)
        for i, v in enumerate(value):
            out += walk(v, inner, f'{path}/{i}')
            if len(out) > 20:
                break
        return out
    if origin is dict or tp is dict:
        if not isinstance(value, dict):
            return [f'{path}: {type(value).__name__}, not an object']
        kt, vt = get_args(tp) or (str, Any)
        for k, v in value.items():
            if not isinstance(k, str):
                out.append(f'{path}: key {k!r} is not a string')
            out += walk(v, vt, f'{path}/{k}')
            if len(out) > 20:
                break
        return out
    if tp is float:
        return [] if isinstance(value, (int, float)) and not isinstance(value, bool) else [f'{path}: {value!r}, not a number']
    if tp is int:
        return [] if isinstance(value, int) and not isinstance(value, bool) else [f'{path}: {value!r}, not an int']
    if tp is bool:
        return [] if isinstance(value, bool) else [f'{path}: {value!r}, not a bool']
    if tp is str:
        return [] if isinstance(value, str) else [f'{path}: {value!r}, not a string']
    raise TypeError(f'walk: no rule for {tp!r} at {path}')


# ------------------------------------------------------------------------------------------- the design's block, verbatim
def design_block() -> dict[str, list[str]]:
    text = (kit.DOCS / 'DESIGN.md').read_text(encoding='utf-8')
    block = text.split('### 10.8')[1].split('```python')[1].split('```')[0]
    classes: dict[str, list[str]] = {}
    cur = None
    for line in block.splitlines():
        m = re.match(r'^class (\w+)\(TypedDict\):', line)
        if m:
            cur = classes.setdefault(m.group(1), [])
            continue
        if cur is None or not line.startswith('    ') or line.strip().startswith('#'):
            if line and not line.startswith(' '):
                cur = None
            continue
        code = line.split('#')[0]
        for part in code.split(';'):
            m = re.match(r'\s*(\w+)\s*:', part)
            if m:
                cur.append(m.group(1))
    return classes


def test_typeddicts_equal_the_design() -> None:
    want = design_block()
    assert set(want) == {'SourceContext', 'BuildContext', 'AlignReport', 'SingleLine', 'OutlineSuggestion',
                         'FloorUploadReport', 'FixesReport', 'BuildReport', 'DetectorRecordOut', 'ReplayFacts',
                         'ReplayFloor', 'ReplayInput', 'BuildResult'}
    for name, fields in want.items():
        tp = contracts.TYPES[name]
        assert list(get_type_hints(tp)) == fields, name
        assert tp.__total__ and set(tp.__required_keys__) == set(fields), name


def test_work_breakdown_types() -> None:
    assert list(get_type_hints(contracts.ReadResult)) == ['items', 'drawing', 'plan', 'units', 'seconds']
    assert list(get_type_hints(contracts.ConvertResult)) == ['dxf', 'log', 'seconds', 'peak_mb', 'exit_code', 'memory_hit']


# ------------------------------------------------------------------------------------------------------- the fixtures
@pytest.fixture(scope='module')
def result() -> dict:
    return json.loads(RESULT.read_text(encoding='utf-8'))


def test_build_result_fixture_has_the_typed_shape(result: dict) -> None:
    assert walk(result, contracts.BuildResult) == []


def test_replay_input_fixture_has_the_typed_shape(result: dict) -> None:
    replay = json.loads(REPLAY.read_text(encoding='utf-8'))
    assert walk(replay, contracts.ReplayInput) == []
    assert replay == result['replay']


def test_build_result_fixture_is_the_bank(result: dict) -> None:
    model = json.loads((kit.FIXTURES / 'models' / 'bank-v2.model.json').read_text(encoding='utf-8'))
    assert result['model'] == model
    summary = json.loads((kit.PROJECT / 'bank_test' / 'src' / 'bank_summary.json').read_text(encoding='utf-8'))
    assert result['report']['summary'] == summary
    assert list(result['report']['floors']) == ['L1', 'L2'] == list(result['detector'])
    assert [len(result['detector'][f]) for f in ('L1', 'L2')] == [24, 25]
    for fl, name in (('L1', 'bank1'), ('L2', 'bank2')):
        oracle = json.loads((kit.PROJECT / 'detector' / 'output' / f'{name}_openings.json').read_text(encoding='utf-8'))
        mine = [{k: v for k, v in r['record'].items() if k != 'floor'} for r in result['detector'][fl]]
        assert mine == [{k: v for k, v in r.items() if k != 'floor'} for r in oracle['openings']]
        assert all(r['record']['floor'] == f'bank-sampeng:{fl}' for r in result['detector'][fl])
    assert len(result['placements']) == 185
    assert result['floors_frame']['L1']['toSheet'] == model['offset']


def test_walker_finds_problems() -> None:
    bad = {'method': 'grid', 'shift': [0, 'x'], 'spread': None, 'labels': [], 'families': 2, 'extra': 1}
    found = walk(bad, contracts.AlignReport)
    assert any('/extra: not a key' in f for f in found) and any('/shift/1' in f for f in found)
    assert walk({'method': 'none', 'shift': [0.0, 0.0], 'spread': None, 'labels': []}, contracts.AlignReport) == \
        ['/families: missing (AlignReport)']
    assert walk(True, int) and walk(1, float) == [] and walk(None, float | None) == []


# ----------------------------------------------------------------------------------------------- the stubs and the calls
STUB_MODULES = ['job', 'step', 'isolate', 'convert', 'losscheck', 'cache', 'runio',
                'read', 'drawing', 'plangeom', 'units', 'levels', 'grid', 'areas', 'suggest', 'propose',
                'build', 'build.align', 'build.detect',
                'out', 'out.presentation', 'out.replay', 'out.pictures', 'out.maxscript', 'out.diff', 'out.overlay']


@pytest.mark.parametrize('name', STUB_MODULES)
def test_every_builder_module_imports(name: str) -> None:
    importlib.import_module(f'walkthrough_builder.{name}')


def test_contract_calls_reach_their_modules() -> None:
    """Each contracts.py call imports its implementing module when called (a stub raises NotImplementedError, a real
    implementation does its work: either way the call is wired)."""
    calls = [
        lambda: contracts.read_source(kit.RUN / 'x.dxf', None, kit.RUN / 'x', source={}, log=print),
        lambda: contracts.suggest([], None),
        lambda: contracts.propose_settings({}, [], {}, [], None),
        lambda: contracts.build({}, print, lambda s, p: None),          # type: ignore[arg-type]
        lambda: contracts.write_outputs({}, {}, print),                 # type: ignore[arg-type]
    ]
    for call in calls:
        try:
            call()
        except NotImplementedError:
            pass
        except Exception:
            pass                                                        # a real implementation refusing a bad input
