"""The API's record checks on one file, from the command line (docs/upload/DESIGN.md U-3.2, U-13.2; WORK_BREAKDOWN U0):

    node tools/run-py.mjs -m walkthrough_api.check_file <kind> <path> [--model <path of model.json>]

Kinds: model (BuiltModel v1: schema and D-5.6 rules), stages (ReplayData v1 against --model), presentation (Presentation
v1 against --model), drawing, plan (gzip or plain JSON), overlay, conversion, suggestions, settings (BuildSettings, then
settings_issues()), job, spec, launch, diff, pieces, openings (upload-contracts.ts sections 1, 3 and 4), and also api,
office, inputs. Exit 0 and "ok" when the file passes; exit 1 listing every issue as `<path>: <message>`; exit 2 on a
usage error. U1, U2 and U4 run it on their own outputs before integration; the API's run-done validation calls
`issues()` in-process (U5). Raw files are validated by their JSON names only (camelCase; a snake_case key is an issue).
Written by the scaffold U0.
"""
from __future__ import annotations

import argparse
import gzip
import sys
from pathlib import Path
from typing import Any

from pydantic import BaseModel, ValidationError

from . import builtmodel, checks
from .jsonio import JsonError, loads_strict
from .models_upload import RECORDS, BuildSettings, PlanGeometry
from .settings_check import settings_issues

KINDS = ('model', 'stages', 'presentation', 'drawing', 'plan', 'overlay', 'conversion', 'suggestions', 'settings', 'job',
         'spec', 'launch', 'diff', 'pieces', 'openings', 'api', 'office', 'inputs')
NEEDS_MODEL = ('stages', 'presentation')


def _pointer(loc: tuple[Any, ...]) -> str:
    return '/' + '/'.join(str(p) for p in loc) if loc else '/'


def _record_issues(cls: type[BaseModel], obj: Any) -> tuple[list[str], BaseModel | None]:
    try:
        return [], cls.model_validate(obj, by_alias=True, by_name=False)
    except ValidationError as exc:
        return [f'{_pointer(tuple(e["loc"]))}: {e["msg"]}' for e in exc.errors(include_url=False)], None


def _plan_issues(plan: PlanGeometry) -> list[str]:
    out = []
    it = plan.items
    if len(plan.pts) % 2:
        out.append('/pts: an odd number of values (x, y pairs)')
    npts = len(plan.pts) // 2
    if not plan.quantum > 0:
        out.append('/quantum: must be above 0')
    for i, (first, count, lay, typ, eid) in enumerate(zip(it.first, it.count, it.layer, it.type, it.eid, strict=True)):
        if first < 0 or count < 0 or first + count > npts:
            out.append(f'/items/{i}: points {first} + {count} lie outside pts ({npts} points)')
        if not 0 <= lay < len(plan.layers):
            out.append(f'/items/layer/{i}: layer index {lay} outside layers ({len(plan.layers)})')
        if typ not in (0, 1, 2, 3, 4, 5):
            out.append(f'/items/type/{i}: type {typ} is not 0 - 5')
        if not -1 <= eid < len(plan.element_ids):
            out.append(f'/items/eid/{i}: element index {eid} outside elementIds ({len(plan.element_ids)})')
        if len(out) > 50:
            out.append('... (stopped after 50 issues)')
            break
    if len(set(it.key)) != len(it.key):
        # hatch loops share their hatch's key: a repeated key must be a run of type 2 / 3 loops
        seen: dict[str, int] = {}
        for i, k in enumerate(it.key):
            if k in seen and not (it.type[i] in (2, 3) and it.type[seen[k]] in (2, 3)):
                out.append(f'/items/key/{i}: key {k!r} repeated (only the loops of one hatch share a key)')
                break
            seen.setdefault(k, i)
    return out


def issues(kind: str, data: bytes, model: bytes | None = None) -> list[str]:
    """Every issue of one file of `kind` given as bytes (empty: it passes). `model` (model.json bytes) is needed for
    stages and presentation."""
    if kind not in KINDS:
        raise ValueError(f'unknown kind {kind!r} (allowed: {", ".join(KINDS)})')
    if kind == 'plan' and data[:2] == b'\x1f\x8b':
        try:
            data = gzip.decompress(data)
        except (OSError, EOFError) as exc:
            return [f'/: not a readable gzip file: {exc}']
    if kind == 'model':
        try:
            builtmodel.validate_bytes(data)
        except builtmodel.ModelInvalid as exc:
            return [str(i) for i in exc.issues]
        return []
    try:
        obj = loads_strict(data)
    except JsonError as exc:
        return [f'/: not strict JSON: {exc}']
    if kind in NEEDS_MODEL:
        if model is None:
            raise ValueError(f'{kind} is checked against its model: give --model')
        try:
            m = builtmodel.validate_bytes(model)
        except builtmodel.ModelInvalid as exc:
            return [f'(the model) {i}' for i in exc.issues]
        found = checks.replay_issues(obj, m) if kind == 'stages' else checks.presentation_issues(obj, m)
        return [str(i) for i in found]
    out, rec = _record_issues(RECORDS[kind], obj)
    if rec is None:
        return out
    if kind == 'plan':
        assert isinstance(rec, PlanGeometry)
        return _plan_issues(rec)
    if kind in ('settings', 'spec'):
        s = rec if isinstance(rec, BuildSettings) else rec.settings      # type: ignore[attr-defined]
        prefix = '' if kind == 'settings' else '/settings'
        return [f'{prefix}{i["path"]}: {i["message"]}' for i in settings_issues(s, adopted=kind == 'settings' or
                                                                                 obj.get('kind') == 'build')]
    return []


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog='python -m walkthrough_api.check_file', description=__doc__.splitlines()[0])
    ap.add_argument('kind', choices=KINDS)
    ap.add_argument('path')
    ap.add_argument('--model', help='model.json, for stages and presentation')
    a = ap.parse_args(argv)
    try:
        data = Path(a.path).read_bytes()
        model = Path(a.model).read_bytes() if a.model else None
        found = issues(a.kind, data, model)
    except (OSError, ValueError) as exc:
        print(f'check_file: {exc}', file=sys.stderr)
        return 2
    if found:
        for line in found:
            print(line)
        print(f'check_file: {a.kind} {a.path}: {len(found)} issue{"s" if len(found) != 1 else ""}', file=sys.stderr)
        return 1
    print(f'check_file: {a.kind} {Path(a.path).name}: ok')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
