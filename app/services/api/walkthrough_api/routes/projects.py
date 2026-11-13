"""Health, the project list, one project, its thumbnail (DESIGN.md 10.2), and createProject (docs/upload/DESIGN.md U-13.3;
its decorator written by the scaffold U0, its body by U5). Bodies: builder E, U5. deleteProject: the owner's request of 12
Nov 2026 (docs/contract-issues/DEL.md; deletes.py)."""
from __future__ import annotations

import logging

from fastapi import APIRouter, Depends
from fastapi.responses import Response

from .. import API_VERSION, deletes, views
from ..deps import get_jobs, get_store
from ..drafts import projects as drafts_projects
from ..errors import ApiError
from ..jobs.base import JobRunner
from ..models import Health, ProjectDetail, ProjectList
from ..models_upload import NewProjectRequest
from ..store.base import Store, StoreError
from .params import NOT_MODIFIED, RAW_HEADERS, IfNoneMatch, ProjectId, error, error_or_validation

router = APIRouter()
log = logging.getLogger('walkthrough_api.routes')


@router.get(
    '/api/health',
    operation_id='health',
    tags=['health'],
    response_model=Health,
    summary='Health',
    description='Liveness and the number of projects in the store.',
    response_description='The API is up.',
)
def health(store: Store = Depends(get_store)) -> Health:
    return Health(status='ok', api_version=API_VERSION, projects=len(store.list_projects()))


@router.get(
    '/api/projects',
    operation_id='listProjects',
    tags=['projects'],
    response_model=ProjectList,
    summary='List projects',
    description='Every project with its latest version\'s counts and stamp, sorted by updatedAt, newest first.',
    response_description='The projects.',
)
def list_projects(store: Store = Depends(get_store)) -> ProjectList:
    # A project whose files are broken is left out (and logged), never taking the whole list down with it: the store
    # leaves out a broken meta.json, this a broken latest version.json (fix step, review finding "code" 4).
    found = []
    for p in store.list_projects():
        try:
            found.append(views.project_summary(store, p))
        except StoreError as exc:
            log.warning('project %s left out of the list: %s', p.id, exc)
    summaries = sorted(found, key=lambda s: s.id)
    summaries.sort(key=lambda s: s.updated_at, reverse=True)           # newest first; ties by id (stable sort)
    return ProjectList(projects=summaries)


@router.get(
    '/api/projects/{projectId}',
    operation_id='getProject',
    tags=['projects'],
    response_model=ProjectDetail,
    responses={404: error('project_not_found')},
    summary='Get a project',
    description='One project with every version, oldest first.',
    response_description='The project.',
)
def get_project(project_id: ProjectId, store: Store = Depends(get_store)) -> ProjectDetail:
    return views.project_detail(store, store.get_project(project_id))


@router.get(
    '/api/projects/{projectId}/thumbnail',
    operation_id='getThumbnail',
    tags=['projects'],
    response_class=Response,
    responses={
        200: {'content': {'image/png': {'schema': {'type': 'string', 'format': 'binary'}}}, 'headers': RAW_HEADERS},
        304: NOT_MODIFIED,
        404: error('project_not_found, no_thumbnail'),
    },
    summary="Get a project's thumbnail",
    description="The latest version's top view (topview.png), as stored, with an ETag.",
    response_description='The thumbnail (image/png).',
)
def get_thumbnail(project_id: ProjectId, if_none_match: IfNoneMatch = None, store: Store = Depends(get_store)) -> Response:
    p = store.get_project(project_id)
    latest = store.get_version(project_id, p.latest_version) if p.latest_version in p.versions else None
    thumb = latest.thumbnail() if latest else None
    if latest is None or thumb is None:
        raise ApiError(404, 'no_thumbnail', f'{project_id} has no top view')
    return views.raw_blob(store.asset(project_id, latest.version, thumb.name), if_none_match)


@router.post(
    '/api/projects',
    operation_id='createProject',
    tags=['projects'],
    status_code=201,
    response_model=ProjectDetail,
    responses={
        409: error('project_exists: the id is taken (details.suggested: the next free id)'),
        422: error_or_validation('bad_project: a name, short name or id that cannot be used (a new id is 2 - 40 '
                                 'characters, not reserved)'),
    },
    summary='Create a project',
    description='A new project with no version yet: its id (given, or a slug of the name), meta.json and '
                'project-settings.json (office and naming derived from the names, U-13.3); newOfficeName creates the '
                'office. Its first version comes from an upload and a build.',
    response_description='The new project.',
)
def create_project(body: NewProjectRequest, store: Store = Depends(get_store)) -> ProjectDetail:
    return drafts_projects.create_project(store, body)


# The owner's request of 12 Nov 2026 (docs/contract-issues/DEL.md): an additive route, authorised by the main session.
@router.delete(
    '/api/projects/{projectId}',
    operation_id='deleteProject',
    tags=['projects'],
    status_code=204,
    response_class=Response,
    responses={
        404: error('project_not_found'),
        409: error('busy: a file reading or a build of one of its drafts is queued or running (details.builds), or a '
                   'file of the project is in use; nothing was deleted'),
    },
    summary='Delete a project',
    description='Removes the project from this computer: every version, every draft with its runs, the uploaded '
                'drawings and the project settings. The offices\' layer memory and the converter\'s cache are shared '
                'and stay. Refused while a run of one of its drafts is going. Cannot be undone.',
    response_description='The project is gone.',
)
def delete_project(project_id: ProjectId, store: Store = Depends(get_store),
                   jobs: JobRunner = Depends(get_jobs)) -> Response:
    deletes.delete_project(store, jobs, project_id)
    return Response(status_code=204)
