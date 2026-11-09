"""saveBuild (docs/upload/DESIGN.md U-11.1) and the office memory (U-8.4).

Under the build's lock, so a double click or a client retry gets 409 build_saved (details.version) instead of a second
version: the build still open, no run going, a finished build run (409 not_built), not stale (409 stale), its outputs
checked again (422 invalid_output: the worker reads untrusted drawings), then `create_version` with VersionDraft
{ label, 'cad', model.source, model.json as built, stages, presentation, topview.png, the Max script, source/
{inputs.json, conversion-<sha12>.json per source, build-report.json, openings.json, pieces.json, flags.json},
carry the latest version's heights when asked, project_data = the settings }; the build is marked saved at once, then
project-settings.json (office, naming, the offset pinned to the model's, U-9.6) and, when asked and the build has an
office, the office memory.

Office memory: every layer of the build's sources (their drawing.json) with a role other than `other`, and `other`
too when it differs from the suggestion (set by hand), is upserted under its normalised name (upper case, xref prefix up
to the last `$0$` removed, whitespace runs as one space, trimmed): the role (latest wins; a changed one kept in `was`),
the exact name added to `names` (the newest 10), uses + 1, lastProject, lastUsedAt.
"""
from __future__ import annotations

import logging
import re
from collections import Counter
from typing import Any

from .. import views
from ..builtmodel import ModelInvalid
from ..errors import ApiError
from ..jobs.base import JobRunner
from ..jsonio import dumps_pretty, iso_utc, loads_strict
from ..models import VersionDetail
from ..models_upload import OfficeLayer, OfficeMapping, RunApiRecord, SaveBuildRequest
from ..store.base import Naming, ProjectSettingsFile, Store, VersionDraft
from .builds import _json_or_none, _source_run, refresh, result_run
from .runs import api_record, mark_invalid, read_runs, write_record
from .validate import run_issues

log = logging.getLogger('walkthrough_api.drafts')

MAX_LABEL = 200
MAX_NAMES = 10
_SPACES = re.compile(r'\s+')
XREF_SEP = '$0$'


def normalise_layer(name: str) -> str:
    """U-8.4 (the builder's names.normalise_layer, the same rule)."""
    i = name.rfind(XREF_SEP)
    return _SPACES.sub(' ', name[i + len(XREF_SEP):] if i >= 0 else name).strip().upper()


def remember(store: Store, office_id: str, project_id: str, layers: dict[str, str], layer_names: list[str],
             suggested: dict[str, str]) -> OfficeMapping:
    """Upserts the build's layer roles into the office's memory (see the module text) and writes it."""
    now = iso_utc()
    mapping = store.get_office(office_id) or OfficeMapping(format='office-mapping/1', id=office_id, name=office_id,
                                                           created_at=now, updated_at=now, layers={},
                                                           furniture_words={})
    found: dict[str, list[tuple[str, str]]] = {}
    for name in layer_names:
        role = layers.get(name, 'other')
        if role != 'other' or suggested.get(name, 'other') != 'other':
            found.setdefault(normalise_layer(name), []).append((name, role))
    out = dict(mapping.layers)
    for key, entries in found.items():
        if not key:
            continue
        counts = Counter(role for _, role in entries)
        role = max(counts, key=lambda r: (counts[r], -[x[1] for x in entries].index(r)))
        old = out.get(key)
        names = [n for n in (old.names if old else []) if n not in {e[0] for e in entries}] + [e[0] for e in entries]
        out[key] = OfficeLayer(role=role, names=list(dict.fromkeys(names))[-MAX_NAMES:],
                               uses=(old.uses if old else 0) + 1, last_project=project_id, last_used_at=now,
                               was=(old.role if old.role != role else old.was) if old else None)
    mapping = mapping.model_copy(update={'layers': out, 'updated_at': now})
    store.write_office(mapping)
    return mapping


def save_build(store: Store, jobs: JobRunner, project_id: str, build_id: str, body: SaveBuildRequest) -> VersionDetail:
    label = body.label.strip()
    if not 1 <= len(label) <= MAX_LABEL or any(ord(c) < 32 for c in label):
        raise ApiError(422, 'bad_label', f'a version\'s label is 1 - {MAX_LABEL} characters of text')
    refresh(store, jobs, project_id, build_id)
    with store.build_lock(project_id, build_id):
        build = store.get_build(project_id, build_id)
        if build.status == 'saved':
            raise ApiError(409, 'build_saved', f'this build was saved already, as v{build.saved_version}',
                           {'version': build.saved_version})
        runs = read_runs(store, project_id, build_id, jobs.alive)
        if any(r.in_progress for r in runs):
            raise ApiError(409, 'run_in_progress', 'a run is going: wait until it is done')
        rv = result_run(runs)
        if rv is None:
            raise ApiError(409, 'not_built', 'there is no finished build to save: build first')
        sf = store.get_build_settings(project_id, build_id)
        if rv.settings_revision != sf.revision:
            raise ApiError(409, 'stale', 'the settings changed since the last build: build again, then save')
        issues = run_issues(rv)
        if issues:
            write_record(rv.dir / 'api.json', RunApiRecord, api_record(False, issues, (rv.api or {}).get('adoptedRevision')))
            mark_invalid(rv, issues)
            raise ApiError(422, 'invalid_output', f'the build\'s outputs did not pass the checks: {issues[0]}',
                           {'issues': issues})
        settings: dict[str, Any] = (rv.spec or {})['settings']
        out = rv.out
        model_raw = (out / 'model.json').read_bytes()
        model = loads_strict(model_raw)
        overlay = loads_strict((out / 'overlay.json').read_bytes())
        source: dict[str, bytes] = {'inputs.json': (out / 'inputs.json').read_bytes()}
        for sha1 in build.sources:
            prepare = _source_run(runs, sha1, 'conversion.json')
            if prepare is not None:
                source[f'conversion-{sha1[:12]}.json'] = (prepare.out / 'sources' / sha1 / 'conversion.json').read_bytes()
        source['build-report.json'] = (out / 'report.json').read_bytes()
        source['openings.json'] = (out / 'openings.json').read_bytes()
        source['pieces.json'] = (out / 'pieces.json').read_bytes()
        source['flags.json'] = dumps_pretty({'format': 'build-flags/1', 'flags': overlay.get('flags') or []})
        meta = store.get_project(project_id)
        carry = meta.latest_version if body.carry_heights and meta.latest_version in meta.versions else None
        ms_name = settings['project']['maxFileName']
        draft = VersionDraft(
            label=label, source_kind='cad', source_files=list(model['source']), model_json=model_raw,
            stages_json=(out / 'stages.json').read_bytes(), presentation=loads_strict((out / 'presentation.json').read_bytes()),
            assets={'topview.png': (out / 'topview.png').read_bytes()}, downloads={ms_name: (out / ms_name).read_bytes()},
            source=source, carry_overrides_from=carry, project_data=dumps_pretty(settings))
        try:
            version = store.create_version(project_id, draft)
        except (ModelInvalid, ValueError) as exc:
            raise ApiError(422, 'invalid_output', f'the version was refused: {exc}'[:1000]) from exc
        now = iso_utc()
        store.write_build(build.model_copy(update={'status': 'saved', 'saved_version': version.version,
                                                    'updated_at': now}))
        p = settings['project']
        offset = model.get('offset')
        store.write_project_settings(project_id, ProjectSettingsFile(
            office=settings.get('office'),
            naming=Naming(photo_name=p['photoName'], max_prefix=p['maxPrefix'], max_file_name=p['maxFileName']),
            offset=(float(offset[0]), float(offset[1])) if isinstance(offset, list) and len(offset) == 2 else None,
            updated_at=now))
        if body.remember_mapping and settings.get('office'):
            names: list[str] = []
            for sha1 in build.sources:
                prepare = _source_run(runs, sha1)
                drawing = _json_or_none(prepare.out / 'sources' / sha1 / 'drawing.json') if prepare else None
                names.extend(layer['name'] for layer in (drawing or {}).get('layers') or [])
            if not names:
                names = list(settings.get('layers') or {})
            suggested: dict[str, str] = {}
            for prev in reversed(runs):
                if prev.kind == 'prepare' and prev.done_and_valid and not prev.only:
                    found = _json_or_none(prev.out / 'suggestions.json') or {}
                    suggested = {k: v.get('role', 'other') for k, v in (found.get('layers') or {}).items()}
                    break
            remember(store, settings['office'], project_id, settings.get('layers') or {}, list(dict.fromkeys(names)),
                     suggested)
    return views.version_detail(store, store.get_version(project_id, version.version))
