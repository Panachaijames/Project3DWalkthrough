"""contracts.py (docs/upload/DESIGN.md U-10.8): the TypedDicts equal the design's block field for field, the scaffold's
fixtures `build-result.bank.json` and `replay-input.bank.json` have exactly their key structure and types (a small
recursive key and type walker, no typeguard), and every module of U1 - U4 imports (stubs until their owners fill them).
U3 asserts its own bank BuildResult with `walk()` here; U4 reads only these fixtures.

The rooms milestone (docs/rooms/DESIGN.md R-12.3; extended by its scaffold R0, frozen again): the same for the rooms
block: classes declared with `(TypedDict)` have every key required, the three `total=False` subclasses add only
optional keys, the eight calls have the design's parameters, the two rule sets are the same in all four places, and
the rooms fixture (a build result with every new report key) has the typed shape."""
from __future__ import annotations

import ast
import importlib
import inspect
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
        # a value of the rooms subclass (the new rule's optional keys) is walked as that subclass
        tp = ROOMS_VARIANT.get(tp.__name__, tp) if set(value) - set(get_type_hints(tp)) else tp
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


#: the report types that have a rooms subclass (the keys the new rule adds, all optional)
ROOMS_VARIANT = {'FloorUploadReport': contracts.FloorUploadReportRooms, 'FixesReport': contracts.FixesReportRooms,
                 'ReplayFacts': contracts.ReplayFactsRooms}


# ------------------------------------------------------------------------------------------- the design's block, verbatim
def rooms_design_blocks() -> tuple[dict[str, list[str]], dict[str, tuple[str, list[str]]], dict[str, list[str]]]:
    """docs/rooms/DESIGN.md R-12.3 -> (classes declared with (TypedDict): name -> fields; the total=False subclasses:
    name -> (base, fields); the calls: name -> parameter names)."""
    text = (kit.ROOMS_DOCS / 'DESIGN.md').read_text(encoding='utf-8')
    section = text.split('### R-12.3')[1].split('### R-12.4')[0]
    blocks = section.split('```python')[1:]
    types_block, calls_block = blocks[0].split('```')[0], blocks[1].split('```')[0]
    classes: dict[str, list[str]] = {}
    subclasses: dict[str, tuple[str, list[str]]] = {}
    cur: list[str] | None = None
    for line in types_block.splitlines():
        m = re.match(r'^class (\w+)\((\w+)(, total=False)?\):', line)
        if m:
            cur = []
            if m.group(2) == 'TypedDict':
                classes[m.group(1)] = cur
            else:
                subclasses[m.group(1)] = (m.group(2), cur)
            continue
        if cur is None or not line.startswith('    '):
            continue
        for part in line.split('#')[0].split(';'):
            f = re.match(r'\s*(\w+)\s*:', part)
            if f:
                cur.append(f.group(1))
    calls = {m.group(1): [p.strip() for p in m.group(2).split(',') if p.strip()]
             for m in re.finditer(r'^def (\w+)\(([^)]*)\)', calls_block, flags=re.M)}
    return classes, subclasses, calls


def test_rooms_typeddicts_equal_the_design() -> None:
    classes, subclasses, _calls = rooms_design_blocks()
    assert list(classes) == ['PartGeo', 'FloorBuilt', 'Closing', 'Unfloored', 'SpaceGeo', 'NetworkResult', 'FlightFound',
                             'StairFound', 'StairCut', 'StairBuilt', 'StairLeft', 'StairsResult', 'FloorRoomsReport',
                             'FloorSlabReport']
    for name, fields in classes.items():
        tp = contracts.TYPES[name]
        assert list(get_type_hints(tp)) == fields, name
        assert tp.__total__ and set(tp.__required_keys__) == set(fields) and not tp.__optional_keys__, name
    assert {k: v[0] for k, v in subclasses.items()} == {'FloorUploadReportRooms': 'FloorUploadReport',
                                                        'FixesReportRooms': 'FixesReport', 'ReplayFactsRooms': 'ReplayFacts'}
    for name, (base, fields) in subclasses.items():
        tp, parent = contracts.TYPES[name], contracts.TYPES[base]
        assert set(tp.__optional_keys__) == set(fields), name                 # the new keys: all optional
        assert set(tp.__required_keys__) == set(parent.__required_keys__), name   # the old rule's keys: unchanged
        assert list(get_type_hints(tp)) == list(get_type_hints(parent)) + fields, name
        assert ROOMS_VARIANT[base] is tp


def test_rooms_calls_have_the_design_signatures() -> None:
    _classes, _subclasses, calls = rooms_design_blocks()
    assert list(calls) == ['prepare_floors', 'floor_walls', 'network_of', 'plate_of', 'find_stairs', 'build_stairs',
                           'cut_slab', 'ceilings_of']
    owners = {'prepare_floors': 'build', 'floor_walls': 'build.bank', 'network_of': 'build.network',
              'plate_of': 'build.network', 'find_stairs': 'build.stairs_read', 'build_stairs': 'build.stairs_build',
              'cut_slab': 'build.slabs', 'ceilings_of': 'build.ceilings'}
    for name, params in calls.items():
        for where in (contracts, importlib.import_module(f'walkthrough_builder.{owners[name]}')):
            sig = inspect.signature(getattr(where, name))
            got = list(sig.parameters)
            assert got[:len(params)] == params, (where.__name__, name)
            assert all(sig.parameters[p].default is not inspect.Parameter.empty for p in got[len(params):]), name


def test_the_rule_sets_are_the_same_in_all_four_places() -> None:
    assert contracts.OLD_RULES == {'slabs': 'closed-rooms', 'ceilings': 'off', 'stairs': 'lines'}
    assert contracts.NEW_RULES == {'slabs': 'network', 'ceilings': 'auto', 'stairs': 'climb'}
    api = (kit.APP / 'services' / 'api' / 'walkthrough_api' / 'models_upload.py').read_text(encoding='utf-8')
    for name in ('OLD_RULES', 'NEW_RULES'):
        m = re.search(rf'^{name}: dict\[str, str\] = (\{{[^}}]*\}})', api, flags=re.M)
        assert m and ast.literal_eval(m.group(1)) == getattr(contracts, name), name
        for ts_file in (kit.APP / 'docs' / 'upload' / 'upload-contracts.ts', kit.APP / 'apps' / 'web' / 'src' / 'upload' / 'contracts.ts'):
            t = re.search(rf'^export const {name} = \{{([^}}]*)\}} as const;', ts_file.read_text(encoding='utf-8'), flags=re.M)
            assert t and dict(re.findall(r"(\w+): '([^']*)'", t.group(1))) == getattr(contracts, name), (name, ts_file.name)
    from walkthrough_builder.build import settings as ST
    assert {k: ST.OPTIONS[k] for k in contracts.OLD_RULES} == contracts.OLD_RULES    # the builder fills the old values


def test_rooms_build_result_fixture_has_the_typed_shape() -> None:
    """fixtures/rooms/build-result.reference.json: a build result with every new report key (ACCEPTANCE 2.5)."""
    res = json.loads((kit.ROOMS_FIXTURES / 'build-result.reference.json').read_text(encoding='utf-8'))
    assert walk(res, contracts.BuildResult) == []
    for key, fl in res['report']['floors'].items():
        assert {'rooms', 'slab', 'stairways', 'stairClash'} <= set(fl), key
        assert walk(fl, contracts.FloorUploadReportRooms) == [], key
    assert {'closings', 'rooms', 'stairs'} <= set(res['report']['fixes'])
    assert {'rooms', 'climbable', 'ceilings'} <= set(res['replay']['facts'])
    assert 'stairways' in res['model'] and 'spaces' in res['model']


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
                'out', 'out.presentation', 'out.replay', 'out.pictures', 'out.maxscript', 'out.diff', 'out.overlay',
                # the rooms milestone's tracer modules (R0; R1 and R2 replace their bodies)
                'build.network', 'build.rooms', 'build.slabs', 'build.xmarks', 'build.ceilings', 'build.stairs_read',
                'build.stairs_build']


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
