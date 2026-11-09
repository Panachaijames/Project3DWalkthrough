"""The run-done validation of the worker's outputs (docs/upload/DESIGN.md U-3.2): the worker reads untrusted drawings, so
the API checks what it wrote before anything is served, adopted or saved, and again at save.

* prepare: per source it read (spec.only, else all), out/sources/<sha1>/{conversion.json, drawing.json, plan.json.gz}
  through check_file's records, each naming that source; unless it was a one-source prepare, suggestions.json and
  proposed-settings.json (BuildSettings, then settings_issues as adopted settings, its sources the run's).
* build: model.json (BuiltModel v1, schema and D-5.6; floors and parts present), stages.json (validate_replay against
  the model), presentation.json (validate_presentation), report.json (the four keys of BuildReport), overlay.json,
  diff.json, openings.json, pieces.json, inputs.json (their records), topview.png (a PNG), the Max script named by the
  run's settings (line 2's stamp = sha1(model.json)[:12]).
* both: every file job.json lists in `outputs` exists with that size and sha1.
Each issue is a plain line `<file>: <what>`; the list is empty when everything passes.
"""
from __future__ import annotations

import gzip
import hashlib
from pathlib import Path
from typing import Any

from .. import builtmodel, check_file, checks
from ..jsonio import JsonError, loads_strict
from ..seed.build import ms_stamp
from .runs import RunView

PNG = b'\x89PNG\r\n\x1a\n'
MAX_ISSUES = 50
SOURCE_FILES = (('conversion.json', 'conversion'), ('drawing.json', 'drawing'), ('plan.json.gz', 'plan'))
BUILD_RECORDS = (('overlay.json', 'overlay'), ('diff.json', 'diff'), ('openings.json', 'openings'),
                 ('pieces.json', 'pieces'), ('inputs.json', 'inputs'))
REPORT_KEYS = ('summary', 'floors', 'fixes', 'doorHeadsFrom')


def _read(path: Path) -> bytes | None:
    try:
        return path.read_bytes()
    except (FileNotFoundError, IsADirectoryError, NotADirectoryError):
        return None


def _outputs(rv: RunView, out: list[str]) -> None:
    for name, meta in ((rv.job or {}).get('outputs') or {}).items():
        path = rv.out / name
        if '..' in Path(name).parts or Path(name).is_absolute():
            out.append(f'{name}: an output outside the run\'s out folder')
            continue
        data = _read(path)
        if data is None:
            out.append(f'{name}: listed in job.json, not written')
        elif len(data) != meta.get('bytes') or hashlib.sha1(data).hexdigest() != meta.get('sha1'):
            out.append(f'{name}: not the file job.json lists (size or sha1 differ)')


def _record(out: list[str], label: str, kind: str, data: bytes | None) -> None:
    if data is None:
        out.append(f'{label}: missing')
        return
    found = check_file.issues(kind, data)
    out.extend(f'{label}: {i}' for i in found[:10])


def prepare_issues(rv: RunView) -> list[str]:
    out: list[str] = []
    spec = rv.spec or {}
    run_sources = [s['sha1'] for s in spec.get('sources', [])]
    names = {s['sha1']: s['name'] for s in spec.get('sources', [])}
    read = spec.get('only') or run_sources
    for sha1 in read:
        base = rv.out / 'sources' / sha1
        for file, kind in SOURCE_FILES:
            label = f'{names.get(sha1, sha1)} {file}'
            data = _read(base / file)
            _record(out, label, kind, data)
            if data is not None and kind != 'plan':
                try:
                    obj = loads_strict(data)
                    said = obj['source']['sha1']
                except (JsonError, KeyError, TypeError):
                    continue
                if said != sha1:
                    out.append(f'{label}: says source {said}, not {sha1}')
            elif data is not None:
                try:
                    obj = loads_strict(gzip.decompress(data) if data[:2] == b'\x1f\x8b' else data)
                    if obj.get('source') != sha1:
                        out.append(f'{label}: says source {obj.get("source")}, not {sha1}')
                except (JsonError, OSError, EOFError, AttributeError):
                    pass
    if not spec.get('only'):
        _record(out, 'suggestions.json', 'suggestions', _read(rv.out / 'suggestions.json'))
        proposal = _read(rv.out / 'proposed-settings.json')
        _record(out, 'proposed-settings.json', 'settings', proposal)
        if proposal is not None:
            try:
                srcs = [s.get('sha1') for s in loads_strict(proposal).get('sources', [])]
            except (JsonError, AttributeError):
                srcs = []
            if sorted(srcs) != sorted(run_sources):
                out.append('proposed-settings.json: its sources are not the run\'s files')
    _outputs(rv, out)
    return out[:MAX_ISSUES]


def build_issues(rv: RunView) -> list[str]:
    out: list[str] = []
    spec = rv.spec or {}
    model_raw = _read(rv.out / 'model.json')
    model: dict[str, Any] | None = None
    if model_raw is None:
        out.append('model.json: missing')
    else:
        try:
            model = builtmodel.validate_bytes(model_raw)
        except builtmodel.ModelInvalid as exc:
            out.extend(f'model.json: {i}' for i in exc.issues[:10])
        if model is not None and (not model.get('floors') or not model.get('parts')):
            out.append('model.json: no floors or no parts were built')
    if model_raw is not None and model is not None:
        # check_file's stages / presentation checks, against the model validated once above (each validation of the
        # model's schema costs a few tenths of a second)
        for file, found_in in (('stages.json', checks.replay_issues), ('presentation.json', checks.presentation_issues)):
            data = _read(rv.out / file)
            if data is None:
                out.append(f'{file}: missing')
                continue
            try:
                obj = loads_strict(data)
            except JsonError as exc:
                out.append(f'{file}: /: not strict JSON: {exc}')
                continue
            out.extend(f'{file}: {i}' for i in found_in(obj, model)[:10])
        ms_name = ((spec.get('settings') or {}).get('project') or {}).get('maxFileName') or ''
        script = _read(rv.out / ms_name) if ms_name else None
        if script is None:
            out.append(f'{ms_name or "the Max script"}: missing')
        else:
            stamp = hashlib.sha1(model_raw).hexdigest()[:12]
            found = ms_stamp(script)
            if found != stamp:
                out.append(f'{ms_name}: line 2 says model data {found}, the model is {stamp}')
    for file, kind in BUILD_RECORDS:
        _record(out, file, kind, _read(rv.out / file))
    report = _read(rv.out / 'report.json')
    if report is None:
        out.append('report.json: missing')
    else:
        try:
            obj = loads_strict(report)
            if not isinstance(obj, dict) or any(k not in obj for k in REPORT_KEYS):
                out.append(f'report.json: a build report has {", ".join(REPORT_KEYS)}')
        except JsonError as exc:
            out.append(f'report.json: not strict JSON: {exc}')
    top = _read(rv.out / 'topview.png')
    if top is None:
        out.append('topview.png: missing')
    elif not top.startswith(PNG):
        out.append('topview.png: not a PNG picture')
    _outputs(rv, out)
    return out[:MAX_ISSUES]


def run_issues(rv: RunView) -> list[str]:
    if rv.spec is None:
        return ['spec.json: missing or not a JobSpec']
    return prepare_issues(rv) if rv.kind == 'prepare' else build_issues(rv)
