"""Store records -> the API's models (DESIGN.md 10.3), and the HTTP details of the raw-file and download routes (10.1).

All URLs are root-relative (/api/...); the web app never builds API paths itself.
"""
from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path
from typing import Any
from urllib.parse import quote

from fastapi.responses import FileResponse, RedirectResponse, Response

from . import furniture_csv, offline
from .errors import ApiError
from .jsonio import JsonError, loads_strict, sha1_hex
from .models import (AssetInfo, DownloadInfo, FloorInfo, HeightOverrides, ProjectDetail, ProjectSummary, VersionCounts,
                     VersionDetail, VersionDownloads, VersionSummary, VersionUrls)
from .store.base import BlobRef, HeightOverridesFile, ProjectMeta, Store, StoreError, VersionMeta

MIN_MM, MAX_MM = 10, 5000          # a furniture height: whole mm, 10 - 5000 (DESIGN.md 13)
MAX_SCRIPT_MEDIA = 'text/plain; charset=utf-8'
CSV_MEDIA = 'text/csv; charset=utf-8'
HTML_MEDIA = 'text/html; charset=utf-8'


# ---------------------------------------------------------------------------------------------------- URLs
def project_url(project_id: str) -> str:
    return f'/api/projects/{project_id}'


def version_url(project_id: str, n: int) -> str:
    return f'{project_url(project_id)}/versions/{n}'


# ---------------------------------------------------------------------------------------------------- models
def floors_of(v: VersionMeta) -> list[FloorInfo]:
    return [FloorInfo(key=f.key, name=f.name, level=f.level) for f in v.floors]


def counts_of(v: VersionMeta) -> VersionCounts:
    c = v.counts
    return VersionCounts(floors=c.floors, parts=c.parts, openings=c.openings, furniture=c.furniture,
                         furniture_kinds=c.furniture_kinds, rooms=c.rooms)


def has_furniture(v: VersionMeta) -> bool:
    return v.downloads.furniture_csv


def project_summary_fields(store: Store, p: ProjectMeta) -> dict[str, Any]:
    latest = store.get_version(p.id, p.latest_version) if p.latest_version in p.versions else None
    return dict(
        id=p.id, name=p.name, short_name=p.short_name, project_no=p.project_no, source_kind=p.source_kind,
        floors=floors_of(latest) if latest else [],
        furniture_count=latest.counts.furniture if latest else 0,
        openings_count=latest.counts.openings if latest else 0,
        stamp=latest.stamp if latest else '',
        latest_version=p.latest_version, version_count=len(p.versions),
        created_at=p.created_at, updated_at=p.updated_at,
        thumbnail_url=f'{project_url(p.id)}/thumbnail' if latest and latest.thumbnail() else None,
        url=project_url(p.id),
    )


def project_summary(store: Store, p: ProjectMeta) -> ProjectSummary:
    return ProjectSummary(**project_summary_fields(store, p))


def project_detail(store: Store, p: ProjectMeta) -> ProjectDetail:
    return ProjectDetail(**project_summary_fields(store, p),
                         versions=[version_summary(v) for v in store.list_versions(p.id)])


def version_summary_fields(v: VersionMeta) -> dict[str, Any]:
    return dict(version=v.version, label=v.label, created_at=v.created_at, stamp=v.stamp, source_kind=v.source_kind,
                counts=counts_of(v), has_stages=v.has_stages, has_max_script=v.downloads.max_script is not None,
                has_furniture=has_furniture(v), url=version_url(v.project_id, v.version))


def version_summary(v: VersionMeta) -> VersionSummary:
    return VersionSummary(**version_summary_fields(v))


def overrides_of(o: HeightOverridesFile | None) -> HeightOverrides:
    if o is None:
        return HeightOverrides(heights={}, revision=0, updated_at=None)
    return HeightOverrides(heights=dict(o.heights), revision=o.revision, updated_at=o.updated_at)


def max_script_file_name(v: VersionMeta) -> str | None:
    """The 3ds Max script's attachment name: the seeded file's name with the version, `Bangkok_Bank_Sampeng_v2.ms`, so two
    versions' scripts never land on the same name in a Downloads folder (the prototypes kept them apart by folder; the
    stored file and its bytes are unchanged, line 2 still carries the model-data stamp). Fix step, review finding
    "parity-revit-pictures" 1."""
    name = v.downloads.max_script
    if not name:
        return None
    p = Path(name)
    return f'{p.stem}_v{v.version}{p.suffix}'


def downloads_of(v: VersionMeta, model_photo_name: str) -> VersionDownloads:
    base = version_url(v.project_id, v.version) + '/downloads'
    max_script = max_script_file_name(v)
    return VersionDownloads(
        max_script=DownloadInfo(url=f'{base}/max-script', file_name=max_script, media_type=MAX_SCRIPT_MEDIA)
        if max_script else None,
        furniture_csv=DownloadInfo(url=f'{base}/furniture-csv', file_name=furniture_csv.file_name({'photoName': model_photo_name}),
                                   media_type=CSV_MEDIA) if has_furniture(v) else None,
        offline_html=DownloadInfo(url=f'{base}/offline-html', file_name=offline.file_name(v.project_id, v.version),
                                  media_type=HTML_MEDIA),
    )


def version_detail(store: Store, v: VersionMeta) -> VersionDetail:
    url = version_url(v.project_id, v.version)
    model = model_of(store, v)
    return VersionDetail(
        **version_summary_fields(v),
        project_id=v.project_id, model_sha1=v.model_sha1, stamp_source=v.stamp_source, floors=floors_of(v),
        urls=VersionUrls(model=f'{url}/model', stages=f'{url}/stages' if v.has_stages else None),
        assets=[AssetInfo(name=a.name, role=a.role, floor=a.floor, media_type=a.media_type, bytes=a.bytes, sha1=a.sha1,
                          url=f'{url}/assets/{a.name}') for a in v.assets],
        downloads=downloads_of(v, model['photoName']),
        presentation=v.presentation,
        overrides=overrides_of(store.read_overrides(v.project_id, v.version)),
    )


# ---------------------------------------------------------------------------------------------------- the model's furniture
_MODELS: dict[str, dict[str, Any]] = {}       # parsed models by the sha1 of their bytes; read-only


def model_bytes(store: Store, v: VersionMeta) -> bytes:
    """model.json as stored, checked against version.json's modelSha1: a model replaced or damaged on disk is a broken
    store (500 store_error on every route), never served or used as if it were the version's."""
    data = store.read_json_bytes(v.project_id, v.version, 'model.json')
    if sha1_hex(data) != v.model_sha1:
        raise StoreError(f'projects/{v.project_id}/versions/{v.version}/model.json does not match the modelSha1 of its '
                         f'version.json (changed on disk?)')
    return data


def model_of(store: Store, v: VersionMeta) -> dict[str, Any]:
    """The version's model, parsed strictly and cached by its bytes' sha1. A model that is not strict JSON, or lacks what
    the routes read (photoName, a furnitureKinds list), is a StoreError (500 store_error), like every other broken store
    file (fix step, review finding "code" 3)."""
    data = model_bytes(store, v)
    model = _MODELS.get(v.model_sha1)
    if model is None:
        where = f'projects/{v.project_id}/versions/{v.version}/model.json'
        try:
            parsed = loads_strict(data)
        except JsonError as exc:
            raise StoreError(f'{where} is not strict JSON: {exc}') from exc
        if not isinstance(parsed, dict) or not isinstance(parsed.get('photoName'), str):
            raise StoreError(f'{where} is not a BuiltModel (no photoName)')
        kinds = parsed.get('furnitureKinds', [])
        if not isinstance(kinds, list) or not all(isinstance(k, dict) and isinstance(k.get('key'), str) for k in kinds):
            raise StoreError(f'{where} is not a BuiltModel (furnitureKinds is not a list of kinds)')
        model = parsed
        if len(_MODELS) >= 32:
            _MODELS.clear()
        _MODELS[v.model_sha1] = model
    return model


def no_furniture(v: VersionMeta) -> ApiError:
    return ApiError(404, 'no_furniture', f'{v.project_id} v{v.version} has no furniture')


def canonical_heights(model: Mapping[str, Any], heights: Mapping[str, int]) -> dict[str, int]:
    """PUT semantics (DESIGN.md 10.2): every key a kind of the model, every value a whole mm 10 - 5000, else 422
    invalid_heights; values equal to the model's height are dropped; the kinds in the model's order."""
    kinds = {k['key']: k for k in model.get('furnitureKinds') or []}
    unknown = sorted(k for k in heights if k not in kinds)
    out_of_range = sorted(k for k, mm in heights.items() if k in kinds and not MIN_MM <= mm <= MAX_MM)
    if unknown or out_of_range:
        parts = []
        if unknown:
            parts.append('not a furniture kind of the model: ' + ', '.join(unknown))
        if out_of_range:
            parts.append(f'outside {MIN_MM} - {MAX_MM} mm: ' + ', '.join(f'{k} {heights[k]}' for k in out_of_range))
        raise ApiError(422, 'invalid_heights', '; '.join(parts), {'unknownKinds': unknown, 'outOfRange': out_of_range})
    return {key: int(heights[key]) for key in kinds if key in heights and heights[key] != kinds[key]['height']}


# ---------------------------------------------------------------------------------------------------- HTTP details
def etag(sha1: str) -> str:
    return f'"{sha1}"'


def etag_matches(if_none_match: str | None, tag: str) -> bool:
    """If-None-Match: '*', or a list of (weak or strong) tags compared by their opaque value."""
    if not if_none_match:
        return False
    value = if_none_match.strip()
    if value == '*':
        return True
    for t in value.split(','):
        t = t.strip()
        if t.startswith('W/'):
            t = t[2:]
        if t == tag:
            return True
    return False


def raw_headers(sha1: str, extra: Mapping[str, str] | None = None) -> dict[str, str]:
    return {'ETag': etag(sha1), 'Cache-Control': 'no-cache', **(extra or {})}


def not_modified(sha1: str, extra: Mapping[str, str] | None = None) -> Response:
    return Response(status_code=304, headers=raw_headers(sha1, extra))


def raw_bytes(data: bytes, media_type: str, sha1: str, if_none_match: str | None,
              extra: Mapping[str, str] | None = None) -> Response:
    if etag_matches(if_none_match, etag(sha1)):
        return not_modified(sha1, extra)
    return Response(content=data, media_type=media_type, headers=raw_headers(sha1, extra))


#: Stored files (assets, downloads) opened as a page of their own run nothing: whatever a file turns out to be, the API's
#: origin (the staff app's, through the dev and preview proxy) never runs script from it (with nosniff, main.py).
SANDBOX = {'Content-Security-Policy': 'sandbox'}


def raw_blob(blob: BlobRef, if_none_match: str | None) -> Response:
    """A stored file as it is: FileResponse for the local store, a 307 to a signed URL for an object store (later)."""
    if etag_matches(if_none_match, etag(blob.sha1)):
        return not_modified(blob.sha1)
    if blob.url is not None:
        return RedirectResponse(blob.url, status_code=307, headers={'Cache-Control': 'no-cache'})
    assert blob.path is not None
    return FileResponse(blob.path, media_type=blob.media_type, headers=raw_headers(blob.sha1, SANDBOX))


def content_disposition(file_name: str) -> str:
    """attachment; filename="<ascii>"; filename*=UTF-8''<encoded> (RFC 6266 / 5987)."""
    ascii_name = ''.join(c if 0x20 <= ord(c) < 0x7F and c not in '"\\' else '_' for c in file_name)
    return f'attachment; filename="{ascii_name}"; filename*=UTF-8\'\'{quote(file_name, safe="")}'


def attachment_headers(file_name: str) -> dict[str, str]:
    return {'Content-Disposition': content_disposition(file_name), 'Cache-Control': 'no-cache', **SANDBOX}


def attachment_blob(blob: BlobRef, file_name: str, media_type: str) -> Response:
    if blob.url is not None:
        return RedirectResponse(blob.url, status_code=307)
    assert blob.path is not None
    return FileResponse(blob.path, media_type=media_type, headers=attachment_headers(file_name))


def attachment_bytes(data: bytes, file_name: str, media_type: str) -> Response:
    return Response(content=data, media_type=media_type, headers=attachment_headers(file_name))


def read_template(path: Path) -> str:
    """The built offline template, as stored (bytes decoded: no newline translation)."""
    return path.read_bytes().decode('utf-8')
