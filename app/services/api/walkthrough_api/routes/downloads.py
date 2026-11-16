"""Downloads: the 3ds Max script, the furniture list CSV, the offline single HTML (DESIGN.md 10.2, 16). Bodies: builder E.

Attachment headers: `Content-Disposition: attachment; filename="<ascii>"; filename*=UTF-8''<encoded>`.

Deleted furniture boxes (step BX, docs/boxes/DESIGN.md 4): the CSV leaves out the rows of the live removed pieces; the 3ds
Max script, when any piece is removed, is the stored script without their furnBox lines and with one comment naming
their Max objects as line 3 (piece_edits.filter_max_script; the prefix is the version's model.maxPrefix), sent from
bytes; with nothing removed both are exactly as before (the script the same FileResponse). The offline file needs no
change: it embeds overrides.json as stored. The frozen route texts ("byte for byte as seeded") under-describe this.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import Response

from .. import furniture_csv, offline, piece_edits, views
from ..deps import get_settings, get_store
from ..errors import ApiError
from ..settings import Settings
from ..store.base import Store, StoreError
from .params import ATTACHMENT_HEADERS, ProjectId, VersionNo, error

router = APIRouter()

_TEXT = {'type': 'string'}


@router.get(
    '/api/projects/{projectId}/versions/{version}/downloads/max-script',
    operation_id='downloadMaxScript',
    tags=['downloads'],
    response_class=Response,
    responses={
        200: {'content': {'text/plain': {'schema': _TEXT}}, 'headers': ATTACHMENT_HEADERS},
        404: error('project_not_found, version_not_found, no_max_script'),
    },
    summary='Download the 3ds Max script',
    description='The version\'s .ms script byte for byte as seeded (text/plain; charset=utf-8), as an attachment <file>.ms.',
    response_description='The 3ds Max script.',
)
def download_max_script(project_id: ProjectId, version: VersionNo, store: Store = Depends(get_store)) -> Response:
    v = store.get_version(project_id, version)
    name = v.downloads.max_script
    attachment = views.max_script_file_name(v)
    if not name or not attachment:
        raise ApiError(404, 'no_max_script', f'{project_id} v{version} has no 3ds Max script')
    saved = store.read_overrides(project_id, version)
    model = views.model_of(store, v) if saved is not None and saved.piece_edits else None
    removed = views.live_edits(saved, model)
    if model is None or not removed:
        # the stored file, byte for byte; its attachment name carries the version (Bangkok_Bank_Sampeng_v2.ms)
        return views.attachment_blob(store.download(project_id, version, name), attachment, views.MAX_SCRIPT_MEDIA)
    # deleted boxes (step BX): filtered, never regenerated; the prefix is the model's (never project-settings.json's)
    prefix = model.get('maxPrefix')
    if not isinstance(prefix, str) or not prefix:
        raise StoreError(f'the 3ds Max script does not match its model: {project_id} v{version} has no maxPrefix')
    data = piece_edits.filter_max_script(store.download_bytes(project_id, version, name), prefix, removed)
    return views.attachment_bytes(data, attachment, views.MAX_SCRIPT_MEDIA)


@router.get(
    '/api/projects/{projectId}/versions/{version}/downloads/furniture-csv',
    operation_id='downloadFurnitureCsv',
    tags=['downloads'],
    response_class=Response,
    responses={
        200: {'content': {'text/csv': {'schema': _TEXT}}, 'headers': ATTACHMENT_HEADERS},
        404: error('project_not_found, version_not_found, no_furniture'),
    },
    summary='Download the furniture list',
    description='BOM + the furniture list CSV with the saved heights (text/csv; charset=utf-8), as an attachment '
                '<photoName>_furniture_list.csv. With no saved heights it equals the prototype CSV byte for byte.',
    response_description='The furniture list.',
)
def download_furniture_csv(project_id: ProjectId, version: VersionNo, store: Store = Depends(get_store)) -> Response:
    v = store.get_version(project_id, version)
    if not views.has_furniture(v):
        raise views.no_furniture(v)
    model = views.model_of(store, v)
    saved = store.read_overrides(project_id, version)
    removed = views.live_edits(saved, model)                     # step BX: the deleted boxes' rows are left out
    data = furniture_csv.csv_bytes(model, saved.heights if saved else None, removed=set(removed) or None)
    return views.attachment_bytes(data, furniture_csv.file_name(model), views.CSV_MEDIA)


@router.get(
    '/api/projects/{projectId}/versions/{version}/downloads/offline-html',
    operation_id='downloadOfflineHtml',
    tags=['downloads'],
    response_class=Response,
    responses={
        200: {'content': {'text/html': {'schema': _TEXT}}, 'headers': ATTACHMENT_HEADERS},
        404: error('project_not_found, version_not_found'),
        503: error('offline_template_missing: run npm run build:offline:template'),
    },
    summary='Download the offline viewer',
    description='The offline single HTML of the version with the saved heights (text/html; charset=utf-8), as an '
                'attachment <projectId>-v<n>.html. It opens from disk with no network.',
    response_description='The offline viewer.',
)
def download_offline_html(project_id: ProjectId, version: VersionNo, store: Store = Depends(get_store),
                          settings: Settings = Depends(get_settings)) -> Response:
    store.get_version(project_id, version)                              # 404s first
    if not settings.offline_template.is_file():
        # the template named relative to app/ (no server paths in an answer; fix step, first code review finding 7)
        raise ApiError(503, 'offline_template_missing',
                       f'the offline template {settings.display_path(settings.offline_template)} is not built: run npm run '
                       f'build:offline:template')
    try:
        page = offline.offline_html(store, project_id, version, views.read_template(settings.offline_template))
    except offline.OfflineTemplateError as exc:
        raise ApiError(503, 'offline_template_invalid', f'{exc}: rebuild it with npm run build:offline:template') from exc
    return views.attachment_bytes(page.encode('utf-8'), offline.file_name(project_id, version), views.HTML_MEDIA)
