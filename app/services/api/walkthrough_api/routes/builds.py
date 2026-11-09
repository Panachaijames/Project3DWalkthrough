"""Builds (drafts): their settings, runs, draft outputs and save (docs/upload/DESIGN.md U-3, U-11.1, U-13.1).

A build is the staff member's work towards one new version: its sources, its settings (the recipe) and its runs. The API
never builds: it writes a run's spec.json, starts the worker through the JobRunner (`Depends(get_jobs)`), and reads the
run's job.json and outputs. Draft outputs are served only by name (U-18.25), as stored, with `ETag: "<sha1>"`,
`Cache-Control: no-cache` and If-None-Match -> 304, like a version's raw files (D-10.1).

Decorators frozen at the scaffold U0 (they are apps/web/openapi.json); the bodies are U5's and call drafts/builds.py and
drafts/save.py. putBuildSettings reads its If-Match header from the request (as putFurnitureHeights does: not a declared
parameter); getBuildPlan reads Accept-Encoding from the request (gzip as stored, else decompressed).
"""
from __future__ import annotations

import gzip
from pathlib import Path

from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response

from .. import views
from ..deps import get_jobs, get_settings, get_store
from ..drafts import builds as drafts_builds
from ..drafts import save as drafts_save
from ..jsonio import read_bytes, sha1_hex
from ..jobs.base import JobRunner
from ..models import VersionDetail
from ..models_upload import (BuildDetail, BuildList, BuildSettingsUpdate, CancelBuildRequest, NewBuildRequest,
                             RunBuildRequest, SaveBuildRequest)
from ..settings import Settings
from ..store.base import Store
from .params import (ATTACHMENT_HEADERS, NOT_MODIFIED, RAW_HEADERS, BuildId, IfNoneMatch, ProjectId, SourceSha1,
                     WithSettings, error, error_or_validation)

router = APIRouter()

_JSON_OBJECT = {'type': 'object', 'additionalProperties': True}
_BINARY = {'type': 'string', 'format': 'binary'}
_TEXT = {'type': 'string'}
_BUILD = '/api/projects/{projectId}/builds/{buildId}'


def _raw(what: str, missing: str, media: str = 'application/json', schema: dict | None = None,
         headers: dict | None = None) -> dict:
    return {
        200: {'content': {media: {'schema': schema or _JSON_OBJECT}}, 'headers': {**RAW_HEADERS, **(headers or {})}},
        304: NOT_MODIFIED,
        404: error(f'project_not_found, build_not_found, {missing}'),
    }


def _json_file(path: Path, if_none_match: str | None) -> Response:
    """A worker's JSON output as stored (ETag = its sha1; If-None-Match -> 304)."""
    data = read_bytes(path)
    return views.raw_bytes(data, 'application/json', sha1_hex(data), if_none_match)


def _accepts_gzip(accept_encoding: str | None) -> bool:
    """Accept-Encoding names gzip (or *) with a q above 0."""
    for item in (accept_encoding or '').split(','):
        token, _, params = item.strip().partition(';')
        if token.strip().lower() not in ('gzip', '*'):
            continue
        q = params.strip().lower()
        if q.startswith('q='):
            try:
                if float(q[2:]) <= 0:
                    continue
            except ValueError:
                continue
        return True
    return False


def _plan(raw: bytes, accept_encoding: str | None, if_none_match: str | None) -> Response:
    """plan.json.gz as stored with Content-Encoding: gzip when the request accepts it, else decompressed here
    (docs/upload/DESIGN.md U-7.5); each form has its own ETag."""
    vary = {'Vary': 'Accept-Encoding'}
    if raw[:2] != b'\x1f\x8b':                                       # stored plain: served plain
        return views.raw_bytes(raw, 'application/json', sha1_hex(raw), if_none_match, vary)
    if _accepts_gzip(accept_encoding):
        return views.raw_bytes(raw, 'application/json', sha1_hex(raw), if_none_match, {**vary, 'Content-Encoding': 'gzip'})
    data = gzip.decompress(raw)
    return views.raw_bytes(data, 'application/json', sha1_hex(data), if_none_match, vary)


# -------------------------------------------------------------------------------------------------- builds and settings
@router.post(
    '/api/projects/{projectId}/builds',
    operation_id='createBuild',
    tags=['builds'],
    status_code=201,
    response_model=BuildDetail,
    responses={
        404: error('project_not_found, source_not_found, version_not_found, build_not_found'),
        422: error_or_validation('bad_sources: no source, or a source twice'),
        503: error('builder_missing: the builder Python or LibreDWG is not where the settings say'),
    },
    summary='Start a build',
    description='A new draft of the project from uploaded sources (or the sources of a version or build named by '
                '`from`), with its starting settings, and its first run: a prepare (convert, check and read each source; '
                'suggest layer roles). The settings proposal is adopted as revision 1 when the prepare is done (U-3.3).',
    response_description='The new build.',
)
def create_build(project_id: ProjectId, body: NewBuildRequest, store: Store = Depends(get_store),
                 jobs: JobRunner = Depends(get_jobs), settings: Settings = Depends(get_settings)) -> BuildDetail:
    return drafts_builds.create_build(store, jobs, settings, project_id, body)


@router.get(
    '/api/projects/{projectId}/builds',
    operation_id='listBuilds',
    tags=['builds'],
    response_model=BuildList,
    responses={404: error('project_not_found')},
    summary="List a project's builds",
    description='Every build (draft) of the project, open and saved, newest first.',
    response_description='The builds.',
)
def list_builds(project_id: ProjectId, store: Store = Depends(get_store), jobs: JobRunner = Depends(get_jobs)) -> BuildList:
    return drafts_builds.list_builds(store, jobs, project_id)


@router.get(
    _BUILD,
    operation_id='getBuild',
    tags=['builds'],
    response_model=BuildDetail,
    responses={404: error('project_not_found, build_not_found')},
    summary='Get a build',
    description="A build's sources with their conversion verdicts and units, its settings (null with "
                'withSettings=false), the layer suggestions, the run going now or the last one, and the last build '
                "run's result. A run found done is validated here once (U-3.2).",
    response_description='The build.',
)
def get_build(project_id: ProjectId, build_id: BuildId, with_settings: WithSettings = True,
              store: Store = Depends(get_store), jobs: JobRunner = Depends(get_jobs)) -> BuildDetail:
    return drafts_builds.detail(store, jobs, project_id, build_id, with_settings=with_settings)


@router.put(
    _BUILD + '/settings',
    operation_id='putBuildSettings',
    tags=['builds'],
    response_model=BuildDetail,
    responses={
        404: error('project_not_found, build_not_found'),
        409: error('build_saved, not_prepared (the proposal is not in yet), run_in_progress (a one-source prepare '
                   'after a units change is running)'),
        412: error('revision_conflict: If-Match does not name the saved revision (details: revision, settings)'),
        413: error('body_too_large: above 8 MiB (the body guard)'),
        422: error_or_validation('invalid_settings (details.issues: [{path, message}])'),
    },
    summary="Save a build's settings",
    description='Replaces the settings (send `If-Match: "<revision>"`; revision + 1). A change of a source\'s units '
                "rescales that source's boxes and points and starts a prepare that reads it again (U-7.4). "
                'layersReviewed: true from the Layers step marks the build reviewed (U-8.3).',
    response_description='The build after the change.',
)
def put_build_settings(project_id: ProjectId, build_id: BuildId, body: BuildSettingsUpdate, request: Request,
                       store: Store = Depends(get_store), jobs: JobRunner = Depends(get_jobs),
                       settings: Settings = Depends(get_settings)) -> BuildDetail:
    return drafts_builds.put_settings(store, jobs, settings, project_id, build_id, body,
                                      request.headers.get('if-match'))


@router.post(
    _BUILD + '/run',
    operation_id='runBuild',
    tags=['builds'],
    status_code=202,
    response_model=BuildDetail,
    responses={
        404: error('project_not_found, build_not_found'),
        409: error('run_in_progress, not_prepared, build_saved, units_unconfirmed, layers_not_reviewed'),
        503: error('builder_missing: the builder Python or LibreDWG is not where the settings say'),
    },
    summary='Build',
    description='Starts a build run with the saved settings: detect openings, build the model and write every output. '
                'Poll getBuild for its progress.',
    response_description='The build with its new run.',
)
def run_build(project_id: ProjectId, build_id: BuildId, body: RunBuildRequest, store: Store = Depends(get_store),
              jobs: JobRunner = Depends(get_jobs), settings: Settings = Depends(get_settings)) -> BuildDetail:
    return drafts_builds.run_build(store, jobs, settings, project_id, build_id)


@router.post(
    _BUILD + '/cancel',
    operation_id='cancelBuildRun',
    tags=['builds'],
    response_model=BuildDetail,
    responses={
        404: error('project_not_found, build_not_found'),
        409: error('no_run: nothing is queued or running'),
    },
    summary='Cancel the run',
    description='Asks the queued or running run to stop (run.cancelRequested turns true: "Stopping..."); it ends '
                'cancelled within 15 s (U-3.4).',
    response_description='The build.',
)
def cancel_build_run(project_id: ProjectId, build_id: BuildId, body: CancelBuildRequest,
                     store: Store = Depends(get_store), jobs: JobRunner = Depends(get_jobs)) -> BuildDetail:
    return drafts_builds.cancel_run(store, jobs, project_id, build_id)


# --------------------------------------------------------------------------------------------- raw files of the draft
@router.get(
    _BUILD + '/sources/{sha1}/conversion',
    operation_id='getBuildConversion',
    tags=['builds'],
    response_class=Response,
    responses=_raw('conversion', 'not_ready'),
    summary="Get a source's conversion report",
    description='The ConversionReport of one source of the build as the prepare run wrote it (upload-contracts.ts '
                'section 4): the verdict, the converter\'s messages by class, what was lost.',
    response_description='The conversion report (application/json).',
)
def get_build_conversion(project_id: ProjectId, build_id: BuildId, sha1: SourceSha1, if_none_match: IfNoneMatch = None,
                         store: Store = Depends(get_store)) -> Response:
    return _json_file(drafts_builds.source_file(store, project_id, build_id, sha1, 'conversion.json'),
                      if_none_match)


@router.get(
    _BUILD + '/sources/{sha1}/drawing',
    operation_id='getBuildDrawing',
    tags=['builds'],
    response_class=Response,
    responses=_raw('drawing', 'not_ready'),
    summary="Get a source's drawing read",
    description='The DrawingRead of one source (upload-contracts.ts section 4): units, layers with their statistics, '
                'blocks, texts, level tags, grid labels and area proposals.',
    response_description='The drawing read (application/json).',
)
def get_build_drawing(project_id: ProjectId, build_id: BuildId, sha1: SourceSha1, if_none_match: IfNoneMatch = None,
                      store: Store = Depends(get_store)) -> Response:
    return _json_file(drafts_builds.source_file(store, project_id, build_id, sha1, 'drawing.json'),
                      if_none_match)


@router.get(
    _BUILD + '/sources/{sha1}/plan',
    operation_id='getBuildPlan',
    tags=['builds'],
    response_class=Response,
    responses=_raw('plan', 'not_ready', headers={
        'Content-Encoding': {'description': 'gzip when the request accepts it (the file is stored gzipped), else absent.',
                             'schema': {'type': 'string'}}}),
    summary="Get a source's plan geometry",
    description='The PlanGeometry of one source (upload-contracts.ts section 4) for the plan canvas: every item of the '
                'sheet in centimetre quanta, with its key and signatures. Sent gzipped when the request accepts it.',
    response_description='The plan geometry (application/json).',
)
def get_build_plan(project_id: ProjectId, build_id: BuildId, sha1: SourceSha1, request: Request,
                   if_none_match: IfNoneMatch = None, store: Store = Depends(get_store)) -> Response:
    path = drafts_builds.source_file(store, project_id, build_id, sha1, 'plan.json.gz')
    return _plan(read_bytes(path), request.headers.get('accept-encoding'), if_none_match)


@router.get(
    _BUILD + '/overlay',
    operation_id='getBuildOverlay',
    tags=['builds'],
    response_class=Response,
    responses=_raw('overlay', 'not_built'),
    summary="Get the last build's overlay",
    description="What the check screen draws over each floor's plan: the built parts, slabs, openings, furniture, "
                'rooms and set-aside items in sheet coordinates, and the flags (BuildOverlay).',
    response_description='The overlay (application/json).',
)
def get_build_overlay(project_id: ProjectId, build_id: BuildId, if_none_match: IfNoneMatch = None,
                      store: Store = Depends(get_store)) -> Response:
    return _json_file(drafts_builds.result_file(store, project_id, build_id, 'overlay.json')[0], if_none_match)


@router.get(
    _BUILD + '/diff',
    operation_id='getBuildDiff',
    tags=['builds'],
    response_class=Response,
    responses=_raw('diff', 'not_built'),
    summary="Get the last build's diff",
    description='The last build against the previous build run of the draft and against the latest version, compared '
                'in sheet coordinates (BuildDiff).',
    response_description='The diff (application/json).',
)
def get_build_diff(project_id: ProjectId, build_id: BuildId, if_none_match: IfNoneMatch = None,
                   store: Store = Depends(get_store)) -> Response:
    return _json_file(drafts_builds.result_file(store, project_id, build_id, 'diff.json')[0], if_none_match)


@router.get(
    _BUILD + '/model',
    operation_id='getBuildModel',
    tags=['builds'],
    response_class=Response,
    responses=_raw('model', 'not_built', headers={
        'X-Model-Stamp': {'description': 'The 12-hex model-data stamp.', 'schema': {'type': 'string'}}}),
    summary="Get the last build's model",
    description="The draft's model.json as built: BuiltModel v1 (built-model.schema.json).",
    response_description='The model (application/json).',
)
def get_build_model(project_id: ProjectId, build_id: BuildId, if_none_match: IfNoneMatch = None,
                    store: Store = Depends(get_store)) -> Response:
    data = read_bytes(drafts_builds.result_file(store, project_id, build_id, 'model.json')[0])
    sha1 = sha1_hex(data)
    return views.raw_bytes(data, 'application/json', sha1, if_none_match, {'X-Model-Stamp': sha1[:12]})


@router.get(
    _BUILD + '/stages',
    operation_id='getBuildStages',
    tags=['builds'],
    response_class=Response,
    responses=_raw('stages', 'not_built'),
    summary="Get the last build's replay data",
    description="The draft's stages.json as built: ReplayData v1, recorded from the build.",
    response_description='The replay data (application/json).',
)
def get_build_stages(project_id: ProjectId, build_id: BuildId, if_none_match: IfNoneMatch = None,
                     store: Store = Depends(get_store)) -> Response:
    return _json_file(drafts_builds.result_file(store, project_id, build_id, 'stages.json')[0], if_none_match)


@router.get(
    _BUILD + '/topview',
    operation_id='getBuildTopview',
    tags=['builds'],
    response_class=Response,
    responses=_raw('topview', 'not_built', media='image/png', schema=_BINARY),
    summary="Get the last build's top view",
    description="The draft's topview.png as built.",
    response_description='The top view (image/png).',
)
def get_build_topview(project_id: ProjectId, build_id: BuildId, if_none_match: IfNoneMatch = None,
                      store: Store = Depends(get_store)) -> Response:
    data = read_bytes(drafts_builds.result_file(store, project_id, build_id, 'topview.png')[0])
    return views.raw_bytes(data, 'image/png', sha1_hex(data), if_none_match, views.SANDBOX)


@router.get(
    _BUILD + '/max-script',
    operation_id='downloadBuildMaxScript',
    tags=['builds'],
    response_class=Response,
    responses={
        200: {'content': {'text/plain': {'schema': _TEXT}}, 'headers': ATTACHMENT_HEADERS},
        404: error('project_not_found, build_not_found, not_built'),
    },
    summary="Download the draft's 3ds Max script",
    description="The last build's .ms script as built (text/plain; charset=utf-8), as an attachment <stem>_draft.ms.",
    response_description='The draft 3ds Max script.',
)
def download_build_max_script(project_id: ProjectId, build_id: BuildId, store: Store = Depends(get_store)) -> Response:
    path, _run = drafts_builds.result_file(store, project_id, build_id, None)
    return views.attachment_bytes(read_bytes(path), f'{path.stem}_draft{path.suffix}', views.MAX_SCRIPT_MEDIA)


# -------------------------------------------------------------------------------------------------------- save, delete
@router.post(
    _BUILD + '/save',
    operation_id='saveBuild',
    tags=['builds'],
    status_code=201,
    response_model=VersionDetail,
    responses={
        404: error('project_not_found, build_not_found'),
        409: error('not_built, stale (the settings changed since the last build), run_in_progress, build_saved '
                   '(details.version)'),
        422: error_or_validation('invalid_output: the outputs failed their checks'),
    },
    summary='Save the build as a version',
    description="Makes the last build run's outputs the project's next version (create_version), writes the project "
                'settings and, when asked, the office memory, and marks the build saved. Idempotent: a second save of '
                'the same build gets 409 build_saved with the version.',
    response_description='The new version.',
)
def save_build(project_id: ProjectId, build_id: BuildId, body: SaveBuildRequest, store: Store = Depends(get_store),
               jobs: JobRunner = Depends(get_jobs)) -> VersionDetail:
    return drafts_save.save_build(store, jobs, project_id, build_id, body)


@router.delete(
    _BUILD,
    operation_id='deleteBuild',
    tags=['builds'],
    status_code=204,
    response_class=Response,
    responses={
        404: error('project_not_found, build_not_found'),
        409: error('run_in_progress, build_saved'),
    },
    summary='Delete a build',
    description='Removes an open draft with its runs and outputs (never a saved one; never while a run is going).',
    response_description='The build is gone.',
)
def delete_build(project_id: ProjectId, build_id: BuildId, store: Store = Depends(get_store),
                 jobs: JobRunner = Depends(get_jobs)) -> Response:
    drafts_builds.delete_build(store, jobs, project_id, build_id)
    return Response(status_code=204)
