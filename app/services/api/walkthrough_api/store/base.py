"""The storage interface routes use (DESIGN.md 9.3), and the store-file records (contracts.ts section 4).

Routes get the store only from `Depends(get_store)` and every route is a plain `def`, so a request-scoped, network-backed
store (Supabase rows + R2 objects, decision H) can replace LocalStore later without touching a route.

The records are the JSON files of DESIGN.md 9.1 (camelCase on disk, snake_case here): ProjectMeta (meta.json),
VersionMeta (version.json), HeightOverridesFile (overrides.json). NewProject and VersionDraft are the next milestone's
inputs (9.5); LocalStore implements them now, nothing routes them yet.

One method beyond the designed shape: `read_file_bytes` hands out the raw bytes of meta.json / version.json /
overrides.json, which the offline download needs because its payload is the stored files' text (DESIGN.md 16; recorded in
docs/contract-issues/E.md). A SupabaseR2Store gives the same text from its rows or objects.

The upload milestone (docs/upload/DESIGN.md U-4.1, U-13.4; step U5) adds the store records of upload-contracts.ts section 2
(ProjectSettingsFile, SourceRecord, UploadSessionFile, BuildRecord, BuildSettingsFile; OfficeMapping is
models_upload's, since the worker's JobSpec carries it), `VersionDraft.project_data`, and the methods for uploads,
sources, builds and their runs, settings files, offices and project settings (LocalStore: store/drafts.py). Run folders
are handed out as paths: the job runner and the worker meet only through a run folder's files (U-3.2).
"""
from __future__ import annotations

import re
from collections.abc import Iterable, Iterator
from contextlib import AbstractContextManager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Annotated, Any, ClassVar, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator
from pydantic.alias_generators import to_camel

from ..models_upload import BuildSettings, OfficeMapping

SourceKind = Literal['cad', 'pictures']
PROJECT_ID_PATTERN = r'^[a-z0-9][a-z0-9-]{1,62}$'
FILE_NAME_PATTERN = r'^[A-Za-z0-9._-]+$'

PROJECT_FORMAT = 'walkthrough-project/1'
VERSION_FORMAT = 'walkthrough-version/1'
OVERRIDES_FORMAT = 'walkthrough-overrides/1'
MODEL_FORMAT = 'built-model/1'
PROJECT_SETTINGS_FORMAT = 'walkthrough-project-settings/1'
SOURCE_FORMAT = 'walkthrough-source/1'
UPLOAD_FORMAT = 'walkthrough-upload/1'
BUILD_FORMAT = 'walkthrough-build/1'
BUILD_SETTINGS_FORMAT = 'walkthrough-build-settings/1'


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


class PathTooLong(StoreError):
    """A store or worker path would pass Windows' 260 characters (long paths are off on this laptop, U-4.1): the write
    is refused with a plain message before anything is written."""

    MESSAGE = 'the project folder is too deep for Windows: move it or shorten its path'

    def __init__(self, length: int) -> None:
        super().__init__(f'{self.MESSAGE} (a path of {length} characters would be needed; at most 259 work)')
        self.length = length


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
    # 'built-model/2' when the model has the `stairways` key (docs/rooms/DESIGN.md R-12.2; create_version decides, R5)
    model_format: Literal['built-model/1', 'built-model/2'] = MODEL_FORMAT
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
    #: The BuildSettings the version was built with (docs/upload/DESIGN.md U-11.1): versions/<n>/project-data.json.
    project_data: BlobSource | None = None


# ----------------------------------------------------------------------- the upload milestone's records (U-4.1, U-13.4)
class Naming(Record):
    """ProjectNaming (upload-contracts.ts section 1)."""

    photo_name: str
    max_prefix: str
    max_file_name: str


class ProjectSettingsFile(Record):
    """projects/<id>/project-settings.json: office, naming, the pinned offset (U-9.6)."""

    format: Literal['walkthrough-project-settings/1'] = PROJECT_SETTINGS_FORMAT
    office: str | None
    naming: Naming
    offset: tuple[float, float] | None
    updated_at: str


class SourceRecord(Record):
    """projects/<id>/sources/<sha1>/source.json."""

    format: Literal['walkthrough-source/1'] = SOURCE_FORMAT
    sha1: str
    name: str
    bytes: int
    kind: Literal['dwg', 'dxf']
    format_version: str | None
    uploaded_at: str
    file: Literal['original.dwg', 'original.dxf']


class UploadSessionFile(Record):
    """data/.uploads/<uploadId>/session.json."""

    format: Literal['walkthrough-upload/1'] = UPLOAD_FORMAT
    id: str
    project_id: str
    file_name: str
    bytes: int
    part_bytes: int
    parts: int
    received: list[int]
    created_at: str
    expires_at: str


class FromNone(Record):
    kind: Literal['none']


class FromVersion(Record):
    kind: Literal['version']
    version: int


class FromBuild(Record):
    kind: Literal['build']
    build: str


BuildFromRecord = Annotated[FromNone | FromVersion | FromBuild, Field(discriminator='kind')]


class BuildRecord(Record):
    """projects/<id>/builds/<buildId>/build.json, written by the API only."""

    format: Literal['walkthrough-build/1'] = BUILD_FORMAT
    id: str
    project_id: str
    created_at: str
    updated_at: str
    status: Literal['open', 'saved']
    sources: list[str]
    from_: BuildFromRecord = Field(alias='from')
    saved_version: int | None
    layers_reviewed_at: str | None


class BuildSettingsFile(Record):
    """projects/<id>/builds/<buildId>/settings.json: revision 0 until the prepare's proposal is adopted (U-3.3)."""

    format: Literal['walkthrough-build-settings/1'] = BUILD_SETTINGS_FORMAT
    revision: int
    updated_at: str
    settings: BuildSettings


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

    # ---- the upload milestone (docs/upload/DESIGN.md U-4.1, U-13.4; LocalStore: store/drafts.py)
    def check_path(self, path: Path) -> Path: ...                                   # PathTooLong past 259 characters
    def deepest_run_path(self, project_id: str) -> Path: ...                        # the longest path a prepare writes
    # project settings, a version's recipe
    def project_settings(self, project_id: str) -> ProjectSettingsFile | None: ...
    def write_project_settings(self, project_id: str, record: ProjectSettingsFile) -> None: ...
    def version_project_data(self, project_id: str, n: int) -> bytes | None: ...    # versions/<n>/project-data.json
    def version_file_path(self, project_id: str, n: int, name: str) -> Path: ...
    # offices (data/mappings/<officeId>.json)
    def list_offices(self) -> list[OfficeMapping]: ...
    def get_office(self, office_id: str) -> OfficeMapping | None: ...
    def write_office(self, mapping: OfficeMapping) -> None: ...
    # upload sessions (data/.uploads/<uploadId>/)
    def create_upload(self, record: UploadSessionFile) -> UploadSessionFile: ...
    def get_upload(self, upload_id: str) -> UploadSessionFile: ...                   # NotFound('upload_not_found')
    def upload_received(self, upload_id: str) -> list[int]: ...
    def put_upload_part(self, upload_id: str, part: int, data: bytes) -> None: ...
    def join_upload(self, upload_id: str) -> tuple[Path, str, int]: ...             # (temp file, sha1, bytes)
    def delete_upload(self, upload_id: str) -> None: ...
    def clean_uploads(self, now: str) -> list[str]: ...
    # sources (projects/<id>/sources/<sha1>/)
    def store_source(self, project_id: str, temp: Path, record: SourceRecord) -> SourceRecord: ...
    def get_source(self, project_id: str, sha1: str) -> SourceRecord: ...            # NotFound('source_not_found')
    def source_path(self, project_id: str, sha1: str) -> Path: ...
    # builds and their runs (projects/<id>/builds/<buildId>/)
    def create_build(self, record: BuildRecord, settings: BuildSettingsFile) -> None: ...
    def get_build(self, project_id: str, build_id: str) -> BuildRecord: ...         # NotFound('build_not_found')
    def list_builds(self, project_id: str) -> list[BuildRecord]: ...
    def write_build(self, record: BuildRecord) -> None: ...
    def get_build_settings(self, project_id: str, build_id: str) -> BuildSettingsFile: ...
    def write_build_settings(self, project_id: str, build_id: str, record: BuildSettingsFile) -> None: ...
    def delete_build(self, project_id: str, build_id: str) -> None: ...
    def build_lock(self, project_id: str, build_id: str) -> AbstractContextManager[None]: ...   # builds/<id>/.api.lock
    def build_dir(self, project_id: str, build_id: str) -> Path: ...
    def run_ids(self, project_id: str, build_id: str) -> list[str]: ...             # oldest first
    def run_dir(self, project_id: str, build_id: str, run_id: str) -> Path: ...
    def new_run_dir(self, project_id: str, build_id: str, kind: str) -> tuple[str, Path]: ...
    def remove_run(self, project_id: str, build_id: str, run_id: str) -> None: ...
    def iter_builds(self) -> Iterator[BuildRecord]: ...                             # every project's
