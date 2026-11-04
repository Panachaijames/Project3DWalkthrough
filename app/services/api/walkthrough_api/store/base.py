"""The storage interface routes use (DESIGN.md 9.3), and the store-file records (contracts.ts section 4).

Routes get the store only from `Depends(get_store)` and every route is a plain `def`, so a request-scoped, network-backed
store (Supabase rows + R2 objects, decision H) can replace LocalStore later without touching a route.

The records are the JSON files of DESIGN.md 9.1 (camelCase on disk, snake_case here): ProjectMeta (meta.json),
VersionMeta (version.json), HeightOverridesFile (overrides.json). NewProject and VersionDraft are the next milestone's
inputs (9.5); LocalStore implements them now, nothing routes them yet.

One method beyond the designed shape: `read_file_bytes` hands out the raw bytes of meta.json / version.json /
overrides.json, which the offline download needs because its payload is the stored files' text (DESIGN.md 16; recorded in
docs/contract-issues/E.md). A SupabaseR2Store gives the same text from its rows or objects.
"""
from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel

SourceKind = Literal['cad', 'pictures']
PROJECT_ID_PATTERN = r'^[a-z0-9][a-z0-9-]{1,62}$'
FILE_NAME_PATTERN = r'^[A-Za-z0-9._-]+$'

PROJECT_FORMAT = 'walkthrough-project/1'
VERSION_FORMAT = 'walkthrough-version/1'
OVERRIDES_FORMAT = 'walkthrough-overrides/1'
MODEL_FORMAT = 'built-model/1'


class NotFound(Exception):
    """Raised by a store for a missing project, version, file or asset; `code` is the API error code."""

    def __init__(self, code: str, message: str = '') -> None:
        super().__init__(message or code)
        self.code = code
        self.message = message or code


class StoreError(Exception):
    """The store's files are not what the store wrote (a broken meta.json, a version folder without its model ...)."""


class StoreConflict(StoreError):
    """A project or version that already exists."""


class RevisionConflict(StoreConflict):
    """write_overrides was asked to replace revision `expected`, but the saved heights are at another one now (a save from
    another tab or person came first). `current` is what is saved now (None: nothing saved)."""

    def __init__(self, expected: int, current: HeightOverridesFile | None) -> None:
        now = current.revision if current else 0
        super().__init__(f'the saved heights are at revision {now}, not {expected}: they were changed elsewhere')
        self.expected = expected
        self.current = current


@dataclass(frozen=True)
class BlobRef:
    """A stored file. A URL-backed store (Supabase + R2, later) answers `url`, served as a 307 redirect: a redirect cannot
    carry the API's own headers, so such a store signs download URLs with the attachment's file name
    (`response-content-disposition`) and asset URLs with their media type and `nosniff`; its bytes, where the API needs
    them (the offline payload), come from `Store.asset_bytes` / `read_file_bytes`, never from `path`."""

    media_type: str
    size: int
    sha1: str
    path: Path | None = None  # local store: served with FileResponse
    url: str | None = None    # object store later: a short-lived signed URL, served as a 307 redirect


@dataclass(frozen=True)
class StagedRef:
    """A file already written to the store's staging area (data/.staging/<key>; a private R2 prefix later)."""

    key: str


BlobSource = bytes | StagedRef


class Record(BaseModel):
    """A store file: camelCase JSON, snake_case attributes, nothing unknown, immutable (cached by mtime)."""

    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, serialize_by_alias=True, extra='forbid',
                              frozen=True)
    #: JSON names left out of the file when they are None (optional in contracts.ts).
    OPTIONAL: ClassVar[tuple[str, ...]] = ()

    def to_json(self) -> dict[str, Any]:
        d = self.model_dump(mode='json', by_alias=True)
        return {k: v for k, v in d.items() if not (k in self.OPTIONAL and v is None)}


class ProjectMeta(Record):
    """projects/<id>/meta.json (not 'project.json': that name is kept for the plan's project data, DESIGN.md 9.1)."""

    format: Literal['walkthrough-project/1'] = PROJECT_FORMAT
    id: str
    name: str
    short_name: str
    project_no: str | None
    source_kind: SourceKind
    created_at: str
    updated_at: str
    latest_version: int
    versions: list[int]


class AssetMeta(Record):
    OPTIONAL: ClassVar[tuple[str, ...]] = ('floor', 'modelRef')
    name: str
    role: Literal['plan-picture', 'thumbnail']
    floor: str | None = None
    media_type: str
    bytes: int
    sha1: str
    model_ref: str | None = None


class VersionCountsMeta(Record):
    floors: int
    parts: int
    openings: int
    furniture: int
    furniture_kinds: int
    rooms: int


class FloorRef(Record):
    key: str
    name: str
    level: float


class DownloadsMeta(Record):
    max_script: str | None
    furniture_csv: bool


class SeedInfo(Record):
    from_: list[str] = Field(alias='from')
    seeded_at: str
    seed_version: str


class VersionMeta(Record):
    """projects/<id>/versions/<n>/version.json: metadata + the presentation."""

    OPTIONAL: ClassVar[tuple[str, ...]] = ('seed',)
    format: Literal['walkthrough-version/1'] = VERSION_FORMAT
    project_id: str
    version: int
    label: str
    created_at: str
    source_kind: SourceKind
    source_files: list[str]
    model_format: Literal['built-model/1'] = MODEL_FORMAT
    model_sha1: str
    stamp: str
    stamp_source: str
    counts: VersionCountsMeta
    floors: list[FloorRef]
    has_stages: bool
    assets: list[AssetMeta]
    downloads: DownloadsMeta
    presentation: dict[str, Any]
    seed: SeedInfo | None = None

    def asset(self, name: str) -> AssetMeta | None:
        return next((a for a in self.assets if a.name == name), None)

    def thumbnail(self) -> AssetMeta | None:
        return next((a for a in self.assets if a.role == 'thumbnail'), None)


class HeightOverridesFile(Record):
    """projects/<id>/versions/<n>/overrides.json: kind -> whole mm, only kinds whose height differs from the model's."""

    format: Literal['walkthrough-overrides/1'] = OVERRIDES_FORMAT
    heights: dict[str, int]
    revision: int
    updated_at: str


class NewProject(Record):
    """The next milestone's new project (DESIGN.md 9.5): meta.json without versions yet."""

    id: str
    name: str
    short_name: str
    project_no: str | None = None
    source_kind: SourceKind

    @field_validator('id')
    @classmethod
    def _id_is_a_slug(cls, v: str) -> str:
        # fullmatch, not match: Python's `$` also matches before a final newline, so 'new-upload\n' would pass and become
        # a folder name (fix step, review finding "code" 5)
        if not re.fullmatch(PROJECT_ID_PATTERN, v):
            raise ValueError(f'project id {v!r} does not match {PROJECT_ID_PATTERN}')
        return v


@dataclass
class VersionDraft:
    """What the next milestone's pipeline hands create_version (DESIGN.md 9.5). Small files may come as bytes; a large
    upload is staged once (Store.stage) and only named here, so it never passes through memory or a request body.
    Asset roles follow the names: 'topview.png' is the thumbnail; a plan picture is named after the file of its floor's
    model.pictureFrame entry (its last path part)."""

    label: str
    source_kind: SourceKind
    source_files: list[str]
    model_json: BlobSource
    stages_json: BlobSource | None
    presentation: dict[str, Any]
    assets: dict[str, BlobSource] = field(default_factory=dict)
    downloads: dict[str, BlobSource] = field(default_factory=dict)
    source: dict[str, BlobSource] = field(default_factory=dict)
    carry_overrides_from: int | None = None


StoreFileName = Literal['meta.json', 'version.json', 'overrides.json', 'model.json', 'stages.json']


class Store(Protocol):
    def list_projects(self) -> list[ProjectMeta]: ...
    def get_project(self, project_id: str) -> ProjectMeta: ...                       # NotFound('project_not_found')
    def list_versions(self, project_id: str) -> list[VersionMeta]: ...
    def get_version(self, project_id: str, n: int) -> VersionMeta: ...                # NotFound('version_not_found')
    def read_json_bytes(self, project_id: str, n: int, name: Literal['model.json', 'stages.json']) -> bytes: ...  # NotFound('no_stages')
    def asset(self, project_id: str, n: int, name: str) -> BlobRef: ...              # NotFound('asset_not_found')
    def download(self, project_id: str, n: int, name: str) -> BlobRef: ...           # NotFound('download_not_found')
    def read_overrides(self, project_id: str, n: int) -> HeightOverridesFile | None: ...
    # revision + 1, atomic; with if_revision, RevisionConflict unless the saved heights are at that revision now (If-Match)
    def write_overrides(self, project_id: str, n: int, heights: dict[str, int],
                        if_revision: int | None = None) -> HeightOverridesFile: ...
    # the raw text of a store file (meta.json when n is None), for the offline payload; None when missing_ok and absent
    def read_file_bytes(self, project_id: str, n: int | None, name: StoreFileName, missing_ok: bool = False) -> bytes | None: ...
    # an asset's bytes (the offline payload's plan pictures): a URL-backed store reads its object, so offline.py needs no
    # local path (fix step, review finding "code" 9)
    def asset_bytes(self, project_id: str, n: int, name: str) -> bytes: ...           # NotFound('asset_not_found')
    # next milestone (implemented by LocalStore now, not routed yet)
    def create_project(self, meta: NewProject) -> ProjectMeta: ...
    def stage(self, name: str, chunks: Iterable[bytes]) -> StagedRef: ...           # writes data/.staging/<key>, streamed
    def create_version(self, project_id: str, draft: VersionDraft) -> VersionMeta: ...
