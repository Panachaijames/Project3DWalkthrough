"""API models (DESIGN.md 10.3). JSON is camelCase; Python fields are snake_case.

Frozen at the scaffold: a change here changes `apps/web/openapi.json` and the generated client (DESIGN.md 10.1, 18.0).
All URLs in responses are root-relative (`/api/...`); the web app never builds API paths itself.

Step BX (deleting one furniture box, 16 Nov 2026; docs/boxes/DESIGN.md 3.2, docs/contract-issues/BX.md), additive and
authorised by the main session: `PieceEdit`, `HeightOverrides.piece_edits`, `HeightsUpdate.piece_edits`, and
`VersionDetail.carried_edits` (`CarriedEdits`, present only when deleted boxes of the previous version did not carry
over).
"""
from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, StrictBool, StrictInt
from pydantic.alias_generators import to_camel

SourceKind = Literal['cad', 'pictures']


class ApiModel(BaseModel):
    model_config = ConfigDict(alias_generator=to_camel, populate_by_name=True, serialize_by_alias=True)


class Health(ApiModel):
    status: Literal['ok']
    api_version: str
    projects: int = Field(description='Number of projects in the store.')


class FloorInfo(ApiModel):
    key: str = Field(description='Floor key, ^[A-Za-z0-9_]{1,32}$.')
    name: str
    level: float = Field(description='Level (m) of the floor top above the datum.')


class VersionCounts(ApiModel):
    floors: int
    parts: int
    openings: int
    furniture: int
    furniture_kinds: int
    rooms: int


class ProjectSummary(ApiModel):
    id: str = Field(description='Project id, ^[a-z0-9][a-z0-9-]{1,62}$.')
    name: str
    short_name: str
    project_no: str | None
    source_kind: SourceKind
    floors: list[FloorInfo] = Field(description='Floors of the latest version, lowest first.')
    furniture_count: int = Field(description='Furniture pieces in the latest version.')
    openings_count: int = Field(description='Openings in the latest version.')
    stamp: str = Field(description="The latest version's 12-hex model-data stamp.")
    latest_version: int
    version_count: int
    created_at: str = Field(description='ISO 8601 UTC.')
    updated_at: str = Field(description='ISO 8601 UTC.')
    thumbnail_url: str | None = Field(description="The latest version's top view, or null when it has none.")
    url: str = Field(description='/api/projects/<id>')


class VersionSummary(ApiModel):
    version: int
    label: str
    created_at: str = Field(description='ISO 8601 UTC.')
    stamp: str = Field(description='12-hex model-data stamp, shared with the 3ds Max script.')
    source_kind: SourceKind
    counts: VersionCounts
    has_stages: bool = Field(description='The version has build replay data.')
    has_max_script: bool
    has_furniture: bool
    url: str = Field(description='/api/projects/<id>/versions/<n>')


class ProjectDetail(ProjectSummary):
    versions: list[VersionSummary] = Field(description='Every version, oldest first.')


class AssetInfo(ApiModel):
    name: str = Field(description='File name, ^[A-Za-z0-9._-]+$.')
    role: Literal['plan-picture', 'thumbnail']
    floor: str | None = Field(description='The floor of a plan picture; null for the thumbnail.')
    media_type: str
    bytes: int
    sha1: str
    url: str


class DownloadInfo(ApiModel):
    url: str
    file_name: str
    media_type: str


class VersionUrls(ApiModel):
    model: str = Field(description='URL of model.json (BuiltModel v1).')
    stages: str | None = Field(description='URL of stages.json (ReplayData v1), or null when the version has no replay.')


class VersionDownloads(ApiModel):
    max_script: DownloadInfo | None
    furniture_csv: DownloadInfo | None
    offline_html: DownloadInfo


class PieceEdit(ApiModel):
    """One furniture piece's edit. Later steps add optional fields (re-kind, name, place); a field this server does not
    know is refused (422), never silently dropped."""

    model_config = ConfigDict(extra='forbid')
    removed: StrictBool | None = Field(default=None, description="true: the box is deleted from this version's view, "
                                                                 'furniture list, 3ds Max script and offline file')


class HeightOverrides(ApiModel):
    heights: dict[str, int] = Field(description="Furniture kind -> whole mm (10 - 5000), only kinds whose height differs from the model's.")
    piece_edits: dict[str, PieceEdit] = Field(default_factory=dict, description='Furniture piece id -> its edit; today '
                                                                                'only {removed: true}. Empty when none.')
    revision: int = Field(description='+1 per save; 0 when nothing was ever saved.')
    updated_at: str | None = Field(description='ISO 8601 UTC of the last save, or null.')


class CarriedEdits(ApiModel):
    """How the deleted furniture boxes of an earlier version fared when this version was saved with the carry tick (from
    versions/<n>/source/carried-edits.json)."""

    from_: int = Field(alias='from', description='The version whose deleted boxes were carried into this one.')
    not_carried: int = Field(description='How many of its deleted boxes did not carry over (not found one-to-one in the '
                                         'same place in this drawing): they show again in this version.')


class VersionDetail(VersionSummary):
    project_id: str
    model_sha1: str = Field(description='40 hex: sha1 of the stored model.json.')
    stamp_source: str = Field(description="The file (relative to the version folder) whose sha1 gives the stamp: 'model.json' or 'source/<file>'.")
    floors: list[FloorInfo]
    urls: VersionUrls
    assets: list[AssetInfo]
    downloads: VersionDownloads
    presentation: dict[str, Any] = Field(description='Presentation v1 (contracts.ts section 3); the viewer owns its type and parsePresentation checks it.')
    overrides: HeightOverrides
    # Left out of the answer when None (exclude_if): absent unless some deleted boxes did not carry over.
    carried_edits: CarriedEdits | None = Field(
        default=None, exclude_if=lambda v: v is None,
        description='Present only when this version was saved with the carry tick and some deleted boxes of that version '
                    'did not carry over (they show again here).')


class ProjectList(ApiModel):
    projects: list[ProjectSummary] = Field(description='Sorted by updatedAt, newest first.')


class HeightsUpdate(ApiModel):
    # StrictInt (integration, E-2b): a JSON string "600", true or 600.0 is refused (422), not taken as 600; the JSON
    # schema, and so openapi.json and the generated client, are the same as with int.
    heights: dict[str, StrictInt] = Field(description='Furniture kind -> whole mm (10 - 5000); replaces the saved map.')
    piece_edits: dict[str, PieceEdit] | None = Field(default=None, description='Piece id -> edit; replaces the saved edits '
                                                                              'when sent; left out, the saved edits stay.')


class ErrorBody(ApiModel):
    code: str = Field(description='Machine-readable error code, e.g. project_not_found.')
    message: str
    details: dict[str, Any] | None = None


class ErrorResponse(ApiModel):
    error: ErrorBody
