"""Upload sessions in raw parts (docs/upload/DESIGN.md U-5.1).

createUpload checks the project (404), the name (1 - 255 characters, no control character, ending in .dwg or .dxf: 422
bad_kind), the size (an empty file is bad_kind; above WALKTHROUGH_UPLOAD_MAX_BYTES 413 too_large) and opens
data/.uploads/<id>/ with parts of 8 MiB. A part must be exactly its size (every part but the last partBytes, the last
the rest; else 422 bad_part); sent again it replaces itself. completeUpload answers 409 incomplete (details.missing)
while parts are missing, joins the parts with their sha1, checks the first bytes (sourcefile.sniff) and stores the file
as the project's source sources/<sha1>/ (an existing sha1 keeps the stored file); the session is deleted on complete,
on a refused file, on cancel, and 24 h after it was made (expired sessions answer 404 upload_not_found and go).
"""
from __future__ import annotations

import math
import os
import secrets
import unicodedata
from datetime import UTC, datetime, timedelta

from ..errors import ApiError
from ..jsonio import iso_utc
from ..models_upload import SourceFile, UploadPartResult, UploadRequest, UploadSession
from ..settings import PART_BYTES, Settings
from ..store.base import NotFound, SourceRecord, Store, UploadSessionFile
from ..store.local import is_project_id
from .sourcefile import HEAD_BYTES, extension, sniff

SESSION_HOURS = 24
MAX_NAME = 255


def upload_url(upload_id: str) -> str:
    return f'/api/uploads/{upload_id}'


def session_model(record: UploadSessionFile) -> UploadSession:
    url = upload_url(record.id)
    return UploadSession(id=record.id, project_id=record.project_id, file_name=record.file_name, bytes=record.bytes,
                         part_bytes=record.part_bytes, parts=record.parts, received=list(record.received),
                         expires_at=record.expires_at, part_urls=[f'{url}/parts/{i}' for i in range(1, record.parts + 1)],
                         complete_url=f'{url}/complete', url=url)


def source_model(record: SourceRecord) -> SourceFile:
    return SourceFile(sha1=record.sha1, name=record.name, bytes=record.bytes, kind=record.kind,
                      format_version=record.format_version, uploaded_at=record.uploaded_at)


def name_problem(file_name: str) -> str | None:
    if not 1 <= len(file_name) <= MAX_NAME:
        return f'a file name is 1 - {MAX_NAME} characters'
    if any(unicodedata.category(c) == 'Cc' for c in file_name):
        return 'the file name holds a control character'
    if extension(file_name) is None:
        return f'{file_name} is neither a .dwg nor a .dxf file: upload the drawing itself (DWG), or a DXF'
    return None


def create_upload(store: Store, settings: Settings, body: UploadRequest) -> UploadSession:
    if not is_project_id(body.project_id):
        raise NotFound('project_not_found', f'no project {body.project_id!r}')
    store.get_project(body.project_id)
    problem = name_problem(body.file_name)
    if problem:
        raise ApiError(422, 'bad_kind', problem)
    if body.bytes < 1:
        raise ApiError(422, 'bad_kind', f'{body.file_name} is empty: it is not a drawing')
    if body.bytes > settings.upload_max_bytes:
        raise ApiError(413, 'too_large', f'{body.file_name} is {body.bytes:,} bytes; at most '
                                         f'{settings.upload_max_bytes:,} are taken')
    now = datetime.now(UTC)
    store.clean_uploads(iso_utc(now))
    record = UploadSessionFile(
        id=f'u{secrets.token_hex(12)}', project_id=body.project_id, file_name=body.file_name, bytes=body.bytes,
        part_bytes=PART_BYTES, parts=math.ceil(body.bytes / PART_BYTES), received=[], created_at=iso_utc(now),
        expires_at=iso_utc(now + timedelta(hours=SESSION_HOURS)))
    return session_model(store.create_upload(record))


def _session(store: Store, upload_id: str) -> UploadSessionFile:
    """The session; an expired one is removed and answers upload_not_found."""
    record = store.get_upload(upload_id)
    if record.expires_at <= iso_utc():
        try:
            store.delete_upload(upload_id)
        except (NotFound, OSError):
            pass
        raise NotFound('upload_not_found', f'upload {upload_id} expired (sessions last {SESSION_HOURS} h): start it again')
    return record


def get_upload(store: Store, upload_id: str) -> UploadSession:
    return session_model(_session(store, upload_id))


def part_size(record: UploadSessionFile, part: int) -> int:
    return record.part_bytes if part < record.parts else record.bytes - record.part_bytes * (record.parts - 1)


def put_part(store: Store, upload_id: str, part: int, data: bytes) -> UploadPartResult:
    record = _session(store, upload_id)
    if part > record.parts:
        raise ApiError(422, 'bad_part', f'part {part} is past the last part ({record.parts})')
    want = part_size(record, part)
    if len(data) != want:
        raise ApiError(422, 'bad_part', f'part {part} must be {want:,} bytes, not {len(data):,}')
    store.put_upload_part(upload_id, part, data)
    return UploadPartResult(part=part, bytes=len(data))


def complete(store: Store, upload_id: str) -> SourceFile:
    record = _session(store, upload_id)
    missing = [i for i in range(1, record.parts + 1) if i not in set(record.received)]
    if missing:
        raise ApiError(409, 'incomplete', f'{len(missing)} of {record.parts} parts are still missing',
                       {'missing': missing})
    temp, sha1, size = store.join_upload(upload_id)
    try:
        if size != record.bytes:
            raise ApiError(409, 'incomplete', f'the parts hold {size:,} bytes, not {record.bytes:,}: send them again',
                           {'missing': []})
        with open(temp, 'rb') as f:
            head = f.read(HEAD_BYTES)
        try:
            kind, version = sniff(head, record.file_name)
        except ApiError:
            os.unlink(temp)
            store.delete_upload(upload_id)                # its parts are no good: a new upload starts over
            raise
        stored = store.store_source(record.project_id, temp, SourceRecord(
            sha1=sha1, name=record.file_name, bytes=size, kind=kind, format_version=version, uploaded_at=iso_utc(),
            file=f'original.{kind}'))
    except BaseException:
        try:
            os.unlink(temp)
        except OSError:
            pass
        raise
    store.delete_upload(upload_id)
    return source_model(stored)


def cancel(store: Store, upload_id: str) -> None:
    store.delete_upload(upload_id)
