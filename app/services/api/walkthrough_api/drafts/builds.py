"""Builds (drafts): create, list, detail, settings, run, cancel, delete and the draft's raw files (docs/upload/DESIGN.md
U-3, U-7.4, U-8.3, U-13.1).

Locks: the per-build lock (Store.build_lock, an OS lock on builds/<id>/.api.lock) is held for adoption and validation,
for a settings save, for starting a run and for a save; never while a run works (U-3.2). Every request that reads a build
first `refresh`es it: a run found done is validated once (api.json), the first prepare's proposal adopted once, and a run
whose worker is gone marked interrupted, all under the lock and each recorded so two polling tabs never do it twice.
"""
from __future__ import annotations

import gzip
import logging
import os
import re
import secrets
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from .. import check_file, views
from ..errors import ApiError
from ..jobs.base import JobRunner
from ..jsonio import JsonError, iso_utc, loads_strict, read_bytes, sha1_hex
from ..models import VersionCounts
from ..models_upload import (BuildDetail, BuildFlagCounts, BuildFloorResult, BuildList, BuildResultInfo,
                             BuildResultUrls, BuildSettings, BuildSettingsUpdate, BuildSourceConversion,
                             BuildSourceInfo, BuildSourceUnits, BuildSourceUrls, BuildSummary, BuildUrls, JobRecord,
                             JobSpec, LayerSuggestion, NewBuildRequest, OpeningCounts, RunApiRecord)
from ..settings import Settings
from ..settings_check import settings_issues
from ..store.base import (BuildRecord, BuildSettingsFile, FromBuild, FromNone, FromVersion, NotFound, SourceRecord,
                          Store, StoreError)
from . import adopt as adoption
from . import cleanup
from .runs import (RunView, api_record, base_record, mark_interrupted, mark_invalid, read_run, read_runs,
                   run_info, write_record)
from .validate import run_issues

log = logging.getLogger('walkthrough_api.drafts')

WALL_CLOCK_S = 3600
LIMITS = {'convert': {'seconds': 120, 'memoryMB': 2048}, 'check': {'seconds': 180, 'memoryMB': 1024},
          'read': {'seconds': 300, 'memoryMB': 4096}, 'build': {'seconds': 900, 'memoryMB': 4096}}
OPENING_KINDS = ('door', 'window', 'passage')
_IF_MATCH = re.compile(r'\s*(?:W/)?"?(\d{1,9})"?\s*')


def never_alive(_record: dict[str, Any]) -> bool:
    return True


# ---------------------------------------------------------------------------------------------------- URLs
def build_url(project_id: str, build_id: str) -> str:
    return f'{views.project_url(project_id)}/builds/{build_id}'


def new_build_id() -> str:
    return f'{datetime.now(UTC).strftime("%Y%m%dT%H%M%S")}-{secrets.token_hex(3)}'


# ---------------------------------------------------------------------------------------------------- cached JSON
_JSON_CACHE: dict[str, tuple[tuple[int, int], Any, str]] = {}


def cached_json(path: Path) -> tuple[Any, str]:
    """(parsed, sha1) of a run output, cached by its mtime and size (getBuild is polled every second)."""
    st = os.stat(path)
    key = (st.st_mtime_ns, st.st_size)
    hit = _JSON_CACHE.get(str(path))
    if hit and hit[0] == key:
        return hit[1], hit[2]
    raw = read_bytes(path)
    if path.suffix == '.gz':
        raw = gzip.decompress(raw)
    value = loads_strict(raw)
    sha1 = sha1_hex(read_bytes(path))
    if len(_JSON_CACHE) > 256:
        _JSON_CACHE.clear()
    _JSON_CACHE[str(path)] = (key, value, sha1)
    return value, sha1


def _json_or_none(path: Path) -> Any:
    try:
        return cached_json(path)[0]
    except (FileNotFoundError, JsonError, OSError, EOFError):
        return None


# ---------------------------------------------------------------------------------------------------- refresh
def _drawings(rv_list: list[RunView], sha1s: list[str]) -> dict[str, Any]:
    out = {}
    for sha1 in sha1s:
        out[sha1] = None
        for rv in reversed(rv_list):
            if rv.kind == 'prepare' and (rv.out / 'sources' / sha1 / 'drawing.json').is_file():
                out[sha1] = _json_or_none(rv.out / 'sources' / sha1 / 'drawing.json')
                break
    return out


def _adopt(store: Store, project_id: str, build: BuildRecord, rv: RunView, runs: list[RunView]) -> int | None:
    """Adopts this prepare's proposal as revision 1 when the settings are still at revision 0 (under the lock)."""
    sf = store.get_build_settings(project_id, build.id)
    if sf.revision != 0:
        return None
    proposal = loads_strict((rv.out / 'proposed-settings.json').read_bytes())
    frame = adoption.project_frame(store, project_id)
    current = sf.settings.model_dump(mode='json', by_alias=True)
    adopted = adoption.adopt(current, proposal, build.from_.kind, frame, _drawings(runs, build.sources))
    settings = BuildSettings.model_validate(adopted, by_alias=True, by_name=False)
    store.write_build_settings(project_id, build.id, BuildSettingsFile(revision=1, updated_at=iso_utc(),
                                                                       settings=settings))
    return 1


def refresh(store: Store, jobs: JobRunner, project_id: str, build_id: str) -> list[RunView]:
    """The build's runs after the API did what finished runs need: validation (once, api.json), the proposal's adoption
    (once) and the interrupted marking of runs whose worker is gone."""
    runs = read_runs(store, project_id, build_id, jobs.alive)
    if not any(r.gone or (r.status == 'done' and r.validated is None) for r in runs):
        return runs
    with store.build_lock(project_id, build_id):
        build = store.get_build(project_id, build_id)
        runs = read_runs(store, project_id, build_id, jobs.alive)
        for rv in runs:
            if rv.gone:
                mark_interrupted(rv)
            elif rv.status == 'done' and rv.validated is None:
                issues = run_issues(rv)
                adopted = None
                if not issues and rv.kind == 'prepare' and not rv.only:
                    try:
                        adopted = _adopt(store, project_id, build, rv, runs)
                    except (ValidationError, JsonError, KeyError, TypeError, ValueError) as exc:
                        issues = [f'proposed-settings.json: it could not be adopted: {exc}'[:500]]
                write_record(rv.dir / 'api.json', RunApiRecord, api_record(not issues, issues, adopted))
                if issues:
                    log.warning('run %s/%s/%s failed its checks: %s', project_id, build_id, rv.id, issues[:3])
                    mark_invalid(rv, issues)
        return read_runs(store, project_id, build_id, jobs.alive)


# ---------------------------------------------------------------------------------------------------- the detail
def _source_run(runs: list[RunView], sha1: str, name: str = 'drawing.json') -> RunView | None:
    """The newest validated prepare that read this source."""
    for rv in reversed(runs):
        if rv.kind == 'prepare' and rv.done_and_valid and (rv.out / 'sources' / sha1 / name).is_file():
            return rv
    return None


def failed_conversion(runs: list[RunView], sha1: str) -> dict[str, Any] | None:
    """The conversion report the worker published for this source when the draft's newest prepare failed on it (verdict
    'failed', U-6.3), checked like every worker record first; None otherwise (UR, V3-9: it was written 'so the Files step
    can say why' and never served, so the step said 'Not read yet')."""
    prepares = [r for r in runs if r.kind == 'prepare']
    if not prepares or prepares[-1].status != 'failed':
        return None
    try:
        data = (prepares[-1].out / 'sources' / sha1 / 'conversion.json').read_bytes()
    except OSError:
        return None
    if check_file.issues('conversion', data):
        return None
    try:
        rep = loads_strict(data)
    except JsonError:
        return None
    if rep.get('verdict') != 'failed' or (rep.get('source') or {}).get('sha1') != sha1:
        return None
    return rep


def _source_info(project_id: str, build_id: str, rec: SourceRecord, runs: list[RunView]) -> BuildSourceInfo:
    rv = _source_run(runs, rec.sha1)
    conversion = units = urls = None
    if rv is None:
        failed = failed_conversion(runs, rec.sha1)
        if failed is not None:
            conversion = BuildSourceConversion(verdict='failed', notes=[str(n) for n in failed.get('notes') or []][:20],
                                               lost_in_model_space=0)
    if rv is not None:
        conv = _json_or_none(rv.out / 'sources' / rec.sha1 / 'conversion.json')
        drawing = _json_or_none(rv.out / 'sources' / rec.sha1 / 'drawing.json')
        if isinstance(conv, dict):
            lost = sum(len(b.get('inserts') or []) for b in conv.get('lostBlocks') or [])
            conversion = BuildSourceConversion(verdict=conv['verdict'], notes=conv.get('notes') or [],
                                               lost_in_model_space=lost)
        if isinstance(drawing, dict):
            u = drawing['units']
            units = BuildSourceUnits(declared=u.get('declared'), used=u['used'], verdict=u['verdict'], note=u['note'])
        base = f'{build_url(project_id, build_id)}/sources/{rec.sha1}'
        urls = BuildSourceUrls(conversion=f'{base}/conversion', drawing=f'{base}/drawing', plan=f'{base}/plan')
    return BuildSourceInfo(sha1=rec.sha1, name=rec.name, bytes=rec.bytes, kind=rec.kind, conversion=conversion,
                           units=units, urls=urls)


def result_run(runs: list[RunView]) -> RunView | None:
    """The last finished (done and validated) build run."""
    return next((rv for rv in reversed(runs) if rv.kind == 'build' and rv.done_and_valid), None)


def _recipe(settings: dict[str, Any]) -> dict[str, Any]:
    """The settings the model is made from: all but `office`, which only names the layer memory read at the prepare and
    written at save (U-8.4); no build step reads it."""
    return {k: v for k, v in settings.items() if k != 'office'}


def is_stale(rv: RunView, sf: BuildSettingsFile) -> bool:
    """The settings changed since this build run in a way that changes the model (U-11.1). A change of the office only
    (the Save step's office select of a project with none, U-8.4) leaves the build saveable: UR, V3-1 found that picking
    the office there made Save need a whole new build."""
    if rv.settings_revision == sf.revision:
        return False
    ran = (rv.spec or {}).get('settings')
    if not isinstance(ran, dict):
        return True
    return _recipe(ran) != _recipe(sf.settings.model_dump(mode='json', by_alias=True))


def _result(project_id: str, build_id: str, rv: RunView, sf: BuildSettingsFile) -> BuildResultInfo | None:
    try:
        model, model_sha1 = cached_json(rv.out / 'model.json')
        overlay, _ = cached_json(rv.out / 'overlay.json')
        presentation, _ = cached_json(rv.out / 'presentation.json')
    except (FileNotFoundError, JsonError, OSError) as exc:
        log.warning('run %s/%s/%s: its outputs could not be read: %s', project_id, build_id, rv.id, exc)
        return None
    parts, openings = model['parts'], model['openings']
    furniture, rooms = model.get('furniture') or [], model['rooms']
    floors = []
    for f in model['floors']:
        key = f['key']
        by_kind = {k: sum(1 for o in openings if o['floor'] == key and o.get('kind') == k) for k in OPENING_KINDS}
        floors.append(BuildFloorResult(
            key=key, name=f['name'], level=f['level'], parts=sum(1 for p in parts if p['floor'] == key),
            openings=OpeningCounts(**by_kind), furniture=sum(1 for p in furniture if p['floor'] == key),
            rooms=sum(1 for r in rooms if r['floor'] == key)))
    flags = overlay.get('flags') or []
    by_kind_flags: dict[str, int] = {}
    for fl in flags:
        by_kind_flags[fl['kind']] = by_kind_flags.get(fl['kind'], 0) + 1
    url = build_url(project_id, build_id)
    record = rv.job or {}
    seconds = {s['name']: float(s['seconds']) for s in record.get('steps') or [] if s.get('seconds') is not None}
    return BuildResultInfo(
        run_id=rv.id, finished_at=record.get('finishedAt') or '', stale=is_stale(rv, sf),
        settings_revision=rv.settings_revision or 0,
        counts=VersionCounts(floors=len(model['floors']), parts=len(parts), openings=len(openings),
                             furniture=len(furniture), furniture_kinds=len(model.get('furnitureKinds') or []),
                             rooms=len(rooms)),
        floors=floors,
        flags=BuildFlagCounts(total=len(flags), check=sum(1 for f in flags if f.get('severity') == 'check'),
                              by_kind=by_kind_flags),
        stamp=model_sha1[:12], presentation=presentation,
        urls=BuildResultUrls(model=f'{url}/model', stages=f'{url}/stages', overlay=f'{url}/overlay',
                             diff=f'{url}/diff', topview=f'{url}/topview', max_script=f'{url}/max-script'),
        seconds=seconds)


def _summary_fields(store: Store, build: BuildRecord, runs: list[RunView]) -> dict[str, Any]:
    names = []
    for sha1 in build.sources:
        try:
            names.append(store.get_source(build.project_id, sha1).name)
        except NotFound:
            names.append(sha1)
    return dict(id=build.id, project_id=build.project_id, created_at=build.created_at, updated_at=build.updated_at,
                status=build.status, saved_version=build.saved_version, source_names=names,
                run_status=runs[-1].status if runs else None, url=build_url(build.project_id, build.id))


def detail(store: Store, jobs: JobRunner, project_id: str, build_id: str, with_settings: bool = True,
           runs: list[RunView] | None = None) -> BuildDetail:
    if runs is None:
        runs = refresh(store, jobs, project_id, build_id)
    build = store.get_build(project_id, build_id)
    sf = store.get_build_settings(project_id, build_id)
    sources = [_source_info(project_id, build_id, store.get_source(project_id, s), runs) for s in build.sources]
    suggestions: dict[str, LayerSuggestion] = {}
    for rv in reversed(runs):
        if rv.kind == 'prepare' and rv.done_and_valid and not rv.only:
            found = _json_or_none(rv.out / 'suggestions.json')
            if isinstance(found, dict):
                suggestions = {k: LayerSuggestion.model_validate(v, by_alias=True, by_name=False)
                               for k, v in (found.get('layers') or {}).items()}
            break
    done = result_run(runs)
    url = build_url(project_id, build_id)
    return BuildDetail(
        **_summary_fields(store, build, runs), sources=sources, settings=sf.settings if with_settings else None,
        settings_revision=sf.revision, layers_reviewed_at=build.layers_reviewed_at, suggestions=suggestions,
        run=run_info(runs[-1]) if runs else None,
        result=_result(project_id, build_id, done, sf) if done is not None else None,
        urls=BuildUrls(settings=f'{url}/settings', run=f'{url}/run', cancel=f'{url}/cancel', save=f'{url}/save'))


def list_builds(store: Store, jobs: JobRunner, project_id: str) -> BuildList:
    out = []
    for build in store.list_builds(project_id):
        runs = read_runs(store, project_id, build.id, jobs.alive)
        out.append(BuildSummary(**_summary_fields(store, build, runs)))
    out.sort(key=lambda b: (b.created_at, b.id), reverse=True)
    return BuildList(builds=out)


# ---------------------------------------------------------------------------------------------------- runs
def _spec(store: Store, settings: Settings, project_id: str, build: BuildRecord, sf: BuildSettingsFile, kind: str,
          run_id: str, run_dir: Path, only: list[str] | None, runs: list[RunView]) -> dict[str, Any]:
    s = sf.settings.model_dump(mode='json', by_alias=True)
    units = {src['sha1']: src['units'] for src in s['sources']}
    sources = []
    for sha1 in build.sources:
        rec = store.get_source(project_id, sha1)
        sources.append({'sha1': sha1, 'name': rec.name, 'kind': rec.kind,
                        'path': str(store.source_path(project_id, sha1)), 'units': units.get(sha1)})
    office = None
    if kind == 'prepare' and s.get('office'):
        mapping = store.get_office(s['office'])
        office = mapping.model_dump(mode='json', by_alias=True) if mapping is not None else None
    previous = result_run(runs) if kind == 'build' else None
    meta = store.get_project(project_id)
    version_model = (str(store.version_file_path(project_id, meta.latest_version, 'model.json'))
                     if meta.latest_version in meta.versions else None)
    return {
        'format': 'job-spec/1', 'kind': kind, 'runId': run_id, 'buildId': build.id, 'projectId': project_id,
        'settings': s, 'settingsRevision': sf.revision, 'sources': sources, 'only': only, 'office': office,
        'paths': {'out': str(run_dir / 'out'), 'cache': str(settings.cache_dir), 'libredwg': str(settings.libredwg_dir),
                  'previousRun': str(previous.dir) if previous is not None else None, 'versionModel': version_model},
        'limits': LIMITS, 'wallClockSeconds': WALL_CLOCK_S,
    }


def start_run(store: Store, jobs: JobRunner, settings: Settings, project_id: str, build: BuildRecord, kind: str,
              only: list[str] | None = None) -> str:
    """A new run of the build: its folder, spec.json, then the worker (call it under the build's lock). A worker that
    cannot be started leaves the run failed with the reason (the build page shows it), never a half-made run."""
    runs = read_runs(store, project_id, build.id, jobs.alive)
    sf = store.get_build_settings(project_id, build.id)
    run_id, run_dir = store.new_run_dir(project_id, build.id, kind)
    write_record(run_dir / 'spec.json', JobSpec, _spec(store, settings, project_id, build, sf, kind, run_id, run_dir,
                                                       only, runs))
    try:
        jobs.start(run_dir)
    except OSError as exc:
        log.error('run %s/%s/%s: the worker could not be started: %s', project_id, build.id, run_id, exc)
        rv = read_run(run_dir, never_alive)
        record = base_record(rv)
        text = f'The builder could not be started ({exc.strerror or type(exc).__name__}): check the builder settings.'
        record.update(status='failed', finishedAt=iso_utc(),
                      error={'code': 'internal', 'message': text, 'step': None},
                      messages=[{'at': iso_utc(), 'level': 'error', 'text': text}])
        write_record(run_dir / 'job.json', JobRecord, record)
    return run_id


def _builder_missing(jobs: JobRunner, kinds: set[str]) -> None:
    missing = jobs.missing(kinds)
    if missing:
        raise ApiError(503, 'builder_missing', 'the builder cannot run here: ' + '; '.join(missing),
                       {'missing': missing})


# ---------------------------------------------------------------------------------------------------- createBuild
def create_build(store: Store, jobs: JobRunner, settings: Settings, project_id: str, body: NewBuildRequest) -> BuildDetail:
    meta = store.get_project(project_id)
    wanted = body.from_.kind if body.from_ is not None else 'latest'
    recipe: dict[str, Any] | None = None
    from_record: FromNone | FromVersion | FromBuild = FromNone(kind='none')
    reviewed = False
    recipe_sources: list[str] = []
    if wanted in ('latest', 'version'):
        n = body.from_.version if wanted == 'version' else meta.latest_version          # type: ignore[union-attr]
        if wanted == 'version' or n in meta.versions:
            store.get_version(project_id, n)                                           # 404 version_not_found
            raw = store.version_project_data(project_id, n)
            if raw is None:
                if wanted == 'version':
                    raise NotFound('version_not_found', f'v{n} of {project_id} has no build settings: it was not built '
                                                        f'from uploaded drawings')
            else:
                try:
                    recipe = BuildSettings.model_validate(loads_strict(raw), by_alias=True, by_name=False).model_dump(
                        mode='json', by_alias=True)
                except (JsonError, ValidationError) as exc:
                    raise StoreError(f'projects/{project_id}/versions/{n}/project-data.json is not BuildSettings: '
                                     f'{exc}') from exc
                from_record, reviewed = FromVersion(kind='version', version=n), True
    elif wanted == 'build':
        other = store.get_build(project_id, body.from_.build)                             # type: ignore[union-attr]
        osf = store.get_build_settings(project_id, other.id)
        recipe_sources = list(other.sources)
        if osf.revision > 0:
            recipe = osf.settings.model_dump(mode='json', by_alias=True)
            from_record, reviewed = FromBuild(kind='build', build=other.id), other.layers_reviewed_at is not None
    sha1s = body.sources
    if sha1s is None:
        sha1s = [s['sha1'] for s in recipe['sources']] if recipe is not None else recipe_sources
        if not sha1s:
            raise ApiError(422, 'bad_sources', 'name the uploaded files to build (sources), or a version or build '
                                               'to take them from')
    if not sha1s:
        raise ApiError(422, 'bad_sources', 'a build needs at least one uploaded file')
    if len(set(sha1s)) != len(sha1s):
        raise ApiError(422, 'bad_sources', 'a file is listed twice')
    records = adoption.source_records(store, project_id, list(sha1s))
    for rec in records:
        store.source_path(project_id, rec.sha1)
    _builder_missing(jobs, {r.kind for r in records})
    cleanup.before_run(store, jobs)

    frame = adoption.project_frame(store, project_id)
    if recipe is not None:
        start = adoption.recipe_settings(recipe, records, frame)
    else:
        start = adoption.fresh_settings(store, project_id, records, frame)
    now = iso_utc()
    build = BuildRecord(id=new_build_id(), project_id=project_id, created_at=now, updated_at=now, status='open',
                        sources=[r.sha1 for r in records], from_=from_record, saved_version=None,
                        layers_reviewed_at=now if reviewed else None)
    store.create_build(build, BuildSettingsFile(revision=0, updated_at=now,
                                                settings=BuildSettings.model_validate(start, by_alias=True,
                                                                                      by_name=False)))
    with store.build_lock(project_id, build.id):
        start_run(store, jobs, settings, project_id, build, 'prepare')
    return detail(store, jobs, project_id, build.id)


# ---------------------------------------------------------------------------------------------------- settings
def if_match(raw: str | None) -> int | None:
    if raw is None:
        return None
    m = _IF_MATCH.fullmatch(raw)
    if not m:
        raise ApiError(412, 'revision_conflict', f'If-Match {raw!r} does not name a revision of the settings')
    return int(m.group(1))


def _source_issues(build: BuildRecord, records: list[SourceRecord], new: dict[str, Any]) -> list[dict[str, str]]:
    given = [src['sha1'] for src in new['sources']]
    if given != build.sources:
        return [{'path': '/sources', 'message': 'the sources are the build\'s own files, in their upload order: start a '
                                                'new build for other files'}]
    out = []
    for i, (src, rec) in enumerate(zip(new['sources'], records, strict=True)):
        if src['name'] != rec.name or src['kind'] != rec.kind:
            out.append({'path': f'/sources/{i}', 'message': f'the name and kind of {rec.name} are the uploaded file\'s'})
    return out


def put_settings(store: Store, jobs: JobRunner, settings: Settings, project_id: str, build_id: str,
                 body: BuildSettingsUpdate, if_match_header: str | None) -> BuildDetail:
    expected = if_match(if_match_header)
    refresh(store, jobs, project_id, build_id)
    with store.build_lock(project_id, build_id):
        build = store.get_build(project_id, build_id)
        if build.status == 'saved':
            raise ApiError(409, 'build_saved', f'this build was saved as v{build.saved_version}: start a new build',
                           {'version': build.saved_version})
        sf = store.get_build_settings(project_id, build_id)
        if sf.revision == 0:
            raise ApiError(409, 'not_prepared', 'the drawings are still being read: the settings can be changed once '
                                                'the proposal is in')
        if expected is not None and expected != sf.revision:
            raise ApiError(412, 'revision_conflict', f'the settings are at revision {sf.revision}, not {expected}: they '
                                                     f'were changed elsewhere',
                           {'revision': sf.revision, 'settings': sf.settings.model_dump(mode='json', by_alias=True)})
        runs = read_runs(store, project_id, build_id, jobs.alive)
        if any(r.in_progress and r.kind == 'prepare' for r in runs):
            raise ApiError(409, 'run_in_progress', 'a drawing is being read again: wait until it is done')
        new = body.settings.model_dump(mode='json', by_alias=True)
        records = [store.get_source(project_id, s) for s in build.sources]
        issues = _source_issues(build, records, new) + list(settings_issues(body.settings, adopted=True))
        if issues:
            raise ApiError(422, 'invalid_settings', f'the settings have {len(issues)} issue'
                                                    f'{"s" if len(issues) != 1 else ""}: {issues[0]["message"]}',
                           {'issues': issues})
        old = sf.settings.model_dump(mode='json', by_alias=True)
        changes = adoption.units_changes(old, new)
        if changes:
            if any(r.in_progress for r in runs):
                raise ApiError(409, 'run_in_progress', 'a run is going: change the units once it is done')
            for sha1, was, now in changes:
                adoption.rescale(new, sha1, adoption.FACTORS[now] / adoption.FACTORS[was])
            _builder_missing(jobs, {r.kind for r in records if r.sha1 in {c[0] for c in changes}})
        saved = BuildSettings.model_validate(new, by_alias=True, by_name=False)
        now_iso = iso_utc()
        store.write_build_settings(project_id, build_id, BuildSettingsFile(revision=sf.revision + 1, updated_at=now_iso,
                                                                           settings=saved))
        update: dict[str, Any] = {'updated_at': now_iso}
        if body.layers_reviewed and build.layers_reviewed_at is None:
            update['layers_reviewed_at'] = now_iso
        build = build.model_copy(update=update)
        store.write_build(build)
        if changes:
            start_run(store, jobs, settings, project_id, build, 'prepare', only=[c[0] for c in changes])
    return detail(store, jobs, project_id, build_id)


# ---------------------------------------------------------------------------------------------------- run, cancel
def run_build(store: Store, jobs: JobRunner, settings: Settings, project_id: str, build_id: str) -> BuildDetail:
    refresh(store, jobs, project_id, build_id)
    cleanup.before_run(store, jobs)
    with store.build_lock(project_id, build_id):
        build = store.get_build(project_id, build_id)
        if build.status == 'saved':
            raise ApiError(409, 'build_saved', f'this build was saved as v{build.saved_version}: start a new build',
                           {'version': build.saved_version})
        runs = read_runs(store, project_id, build_id, jobs.alive)
        if any(r.in_progress for r in runs):
            raise ApiError(409, 'run_in_progress', 'a run is going: wait until it is done, or cancel it')
        sf = store.get_build_settings(project_id, build_id)
        if sf.revision == 0:
            if not first_reading_ended(runs):
                raise ApiError(409, 'not_prepared', 'the drawings are still being read')
            # the first reading ended without a proposal (failed, cancelled, or interrupted by a restart, U-3.4): Build
            # reads the draft's files again instead of leaving a dead end (UR, V3-4)
            _builder_missing(jobs, {store.get_source(project_id, s).kind for s in build.sources})
            start_run(store, jobs, settings, project_id, build, 'prepare')
        else:
            unconfirmed = [s.name for s in sf.settings.sources if not s.units_confirmed]
            if unconfirmed:
                raise ApiError(409, 'units_unconfirmed', f'confirm the units of {", ".join(unconfirmed)} on the Files '
                                                         f'step', {'sources': unconfirmed})
            if build.layers_reviewed_at is None:
                raise ApiError(409, 'layers_not_reviewed', 'look through the Layers step once before the first build')
            _builder_missing(jobs, {s.kind for s in sf.settings.sources})
            cleanup.clean_runs(store, project_id, build_id, runs)
            start_run(store, jobs, settings, project_id, build, 'build')
        store.write_build(build.model_copy(update={'updated_at': iso_utc()}))
    return detail(store, jobs, project_id, build_id)


def first_reading_ended(runs: list[RunView]) -> bool:
    """The draft's first reading (its newest whole prepare) ended without a proposal: failed, cancelled or interrupted.
    runBuild then reads the files again (UR, V3-4)."""
    first = [r for r in runs if r.kind == 'prepare' and not r.only]
    return bool(first) and first[-1].status in ('failed', 'cancelled', 'interrupted')


def cancel_run(store: Store, jobs: JobRunner, project_id: str, build_id: str) -> BuildDetail:
    store.get_build(project_id, build_id)
    runs = read_runs(store, project_id, build_id, jobs.alive)
    going = [r for r in runs if r.in_progress]
    if not going:
        raise ApiError(409, 'no_run', 'nothing is queued or running')
    for rv in going:
        if not rv.cancel:
            jobs.cancel(rv.dir)
    return detail(store, jobs, project_id, build_id)


def delete_build(store: Store, jobs: JobRunner, project_id: str, build_id: str) -> None:
    refresh(store, jobs, project_id, build_id)
    with store.build_lock(project_id, build_id):
        build = store.get_build(project_id, build_id)
        if build.status == 'saved':
            raise ApiError(409, 'build_saved', f'this build was saved as v{build.saved_version}: it stays with its '
                                               f'version', {'version': build.saved_version})
        if any(r.in_progress for r in read_runs(store, project_id, build_id, jobs.alive)):
            raise ApiError(409, 'run_in_progress', 'a run is going: cancel it first')
        store.delete_build(project_id, build_id)
    store.remove_build_dir(project_id, build_id)


# ---------------------------------------------------------------------------------------------------- raw files
def _validated_runs(store: Store, project_id: str, build_id: str) -> list[RunView]:
    store.get_build(project_id, build_id)
    return read_runs(store, project_id, build_id, never_alive)


def source_file(store: Store, project_id: str, build_id: str, sha1: str, name: str) -> Path:
    """A source's conversion.json, drawing.json or plan.json.gz from the newest validated prepare that read it."""
    build = store.get_build(project_id, build_id)
    if sha1 in build.sources:
        rv = _source_run(_validated_runs(store, project_id, build_id), sha1, name)
        if rv is not None:
            return rv.out / 'sources' / sha1 / name
    raise ApiError(404, 'not_ready', f'{name} of that file is not ready: the drawings are still being read')


def result_file(store: Store, project_id: str, build_id: str, name: str | None) -> tuple[Path, RunView]:
    """An output of the last validated build run (name None: its Max script)."""
    rv = result_run(_validated_runs(store, project_id, build_id))
    if rv is not None:
        if name is None:
            name = ((rv.spec or {}).get('settings') or {}).get('project', {}).get('maxFileName') or ''
        path = rv.out / name
        if name and path.is_file():
            return path, rv
    raise ApiError(404, 'not_built', 'there is no finished build yet: build first')
