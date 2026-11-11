"""LocalStore: the files of DESIGN.md 9.1 under a root folder (app/data, or WALKTHROUGH_DATA_DIR).

    <root>/projects/<projectId>/meta.json
    <root>/projects/<projectId>/versions/<n>/{version.json, model.json, stages.json?, overrides.json?, assets/,
                                             downloads/, source/}
    versions/<n>/project-data.json (the BuildSettings an uploaded version was built with), <root>/.staging/
    (stage() writes there); <root>/mappings/, <root>/.uploads/, projects/<id>/{project-settings.json, sources/,
    builds/}: the upload milestone's files (store/drafts.py, docs/upload/DESIGN.md U-4.1)
    <root>/.lock: the cross-process lock (store/filelock.py), an empty file

meta.json and version.json are parsed into the records of store/base.py and cached by the file's mtime, size and id;
every write is atomic (temp file, then os.replace). A version folder is written whole into versions/.staging-<uuid>/ and
renamed into place (create_version, and the seed through stage_version / commit_version); versions are never edited in
place except overrides.json.

Writers (heights saves, the seed's folder swap, create_version / create_project) take `exclusive()`: the process's
threading lock and the store's cross-process file lock, so a save the API acknowledged can never land in a version folder
the seed is replacing, and two saves never hand out the same revision. Readers take no lock: on Windows a read that meets
a file being replaced (or a replace that meets a reader) is retried for a moment (jsonio.retry_on_sharing), and what still
fails is a StoreError (500 store_error), never a bare traceback. Error messages name files relative to the store root.
"""
from __future__ import annotations

import logging
import os
import re
import shutil
import threading
import time
import uuid
from collections.abc import Iterable, Iterator, Mapping
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Literal, TypeVar

from pydantic import BaseModel, ValidationError

from .. import builtmodel
from ..jsonio import (RASTER_MEDIA_TYPES, JsonError, atomic_write_bytes, dumps_pretty, iso_utc, loads_strict,
                      media_type_of, read_bytes, retry_on_sharing, sha1_hex)
from .base import (FILE_NAME_PATTERN, OVERRIDES_FORMAT, PROJECT_FORMAT, PROJECT_ID_PATTERN, BlobRef, BlobSource,
                   HeightOverridesFile, NewProject, NotFound, ProjectMeta, RevisionConflict, StagedRef, StoreConflict,
                   StoreError, StoreFileName, VersionDraft, VersionMeta)
from .drafts import DraftFiles
from .filelock import store_file_lock

log = logging.getLogger('walkthrough_api.store')

R = TypeVar('R', bound=BaseModel)
_ID = re.compile(PROJECT_ID_PATTERN)
_NAME = re.compile(FILE_NAME_PATTERN)
KEPT_ON_REBUILD = ('overrides.json', 'project-data.json')   # a rebuilt version folder keeps these (DESIGN.md 9.1, 9.2)

DOWNLOAD_MEDIA_TYPES = {
    '.ms': 'text/plain; charset=utf-8',
    '.csv': 'text/csv; charset=utf-8',
    '.txt': 'text/plain; charset=utf-8',
    '.md': 'text/markdown; charset=utf-8',
    '.json': 'application/json',
    '.html': 'text/html; charset=utf-8',
}


def download_media_type(name: str) -> str:
    return DOWNLOAD_MEDIA_TYPES.get(Path(name).suffix.lower(), 'application/octet-stream')


def is_project_id(value: object) -> bool:
    """^[a-z0-9][a-z0-9-]{1,62}$ over the WHOLE string (re.fullmatch: Python's `$` also matches before a final newline)."""
    return isinstance(value, str) and _ID.fullmatch(value) is not None


def safe_name(name: object) -> bool:
    """An asset / download / source file name: ^[A-Za-z0-9._-]+$ over the whole string (DESIGN.md 9.3), and not '.', '..'
    or a name ending in a dot (Windows drops trailing dots, so 'a.ms.' would open 'a.ms')."""
    return isinstance(name, str) and _NAME.fullmatch(name) is not None and not name.endswith('.')


def _rename_dir(src: Path, dst: Path, tries: int = 25) -> None:
    """os.replace for a folder, retried briefly: on Windows a file open in it (a download being served) blocks a rename."""
    for i in range(tries):
        try:
            os.replace(src, dst)
            return
        except PermissionError:
            if i == tries - 1:
                raise
            time.sleep(0.2)


class LocalStore(DraftFiles):
    def __init__(self, root: Path) -> None:
        self.root = Path(root)
        self._lock = threading.RLock()
        self._exclusive_depth = 0                  # exclusive() nesting in the thread that holds self._lock
        self._cache: dict[Path, tuple[tuple[int, int, int], Any]] = {}
        self._uploads_lock = threading.Lock()      # session.json rewrites after a part (two parts may arrive at once)

    # ------------------------------------------------------------------------------------------------ locking
    @contextmanager
    def exclusive(self) -> Iterator[None]:
        """The writers' lock: this process's threads one at a time, and the store's cross-process file lock (the seed in
        another process), re-entrant in the thread that holds it."""
        with self._lock:
            if self._exclusive_depth:
                self._exclusive_depth += 1
                try:
                    yield
                finally:
                    self._exclusive_depth -= 1
                return
            with store_file_lock(self.root):
                self._exclusive_depth = 1
                try:
                    yield
                finally:
                    self._exclusive_depth = 0

    # ------------------------------------------------------------------------------------------------ paths and reading
    @property
    def projects_dir(self) -> Path:
        return self.root / 'projects'

    @property
    def staging_dir(self) -> Path:
        return self.root / '.staging'

    def project_dir(self, project_id: str) -> Path:
        if not is_project_id(project_id):
            raise NotFound('project_not_found', f'no project {project_id!r}')
        return self.projects_dir / project_id

    def version_dir(self, project_id: str, n: int) -> Path:
        return self.project_dir(project_id) / 'versions' / str(int(n))

    def rel(self, path: Path) -> str:
        """A store file's name for messages: relative to the store root (no server paths in the API's answers)."""
        try:
            return Path(path).relative_to(self.root).as_posix()
        except ValueError:
            return Path(path).name

    def _stat(self, path: Path) -> os.stat_result:
        """os.stat, a sharing violation retried; FileNotFoundError passes through, a lasting PermissionError -> StoreError."""
        try:
            return retry_on_sharing(lambda: os.stat(path))
        except PermissionError as exc:
            raise StoreError(f'{self.rel(path)} could not be read: it is locked by another program ({exc.strerror})') from exc

    def _read(self, path: Path) -> bytes:
        """A file's bytes, a sharing violation retried; FileNotFoundError passes through, a lasting PermissionError ->
        StoreError."""
        try:
            return read_bytes(path)
        except PermissionError as exc:
            raise StoreError(f'{self.rel(path)} could not be read: it is locked by another program ({exc.strerror})') from exc
        except IsADirectoryError as exc:
            raise StoreError(f'{self.rel(path)} is a folder, not a file') from exc

    def _cached(self, path: Path, parse: Any) -> Any:
        """parse(bytes) of a file, cached by its mtime, size and id. The stat is taken before and after the read: a file
        replaced in between is parsed again next time rather than cached under the old stat. FileNotFoundError passes
        through."""
        st = self._stat(path)
        key = (st.st_mtime_ns, st.st_size, st.st_ino)
        hit = self._cache.get(path)
        if hit and hit[0] == key:
            return hit[1]
        data = self._read(path)
        value = parse(data)
        after = self._stat(path)
        if (after.st_mtime_ns, after.st_size, after.st_ino) == key:
            self._cache[path] = (key, value)
        return value

    def _record(self, path: Path, cls: type[R]) -> R:
        def parse(raw: bytes) -> R:
            try:
                return cls.model_validate(loads_strict(raw))
            except (JsonError, ValidationError) as exc:
                raise StoreError(f'{self.rel(path)}: not a valid {cls.__name__}: {exc}') from exc
        record: R = self._cached(path, parse)
        return record

    # ------------------------------------------------------------------------------------------------ projects, versions
    def list_projects(self) -> list[ProjectMeta]:
        """Every readable project. One whose meta.json is broken is left out (and logged), so one bad project never takes
        the list (or the health check) down with it."""
        if not self.projects_dir.is_dir():
            return []
        out = []
        for d in sorted(self.projects_dir.iterdir(), key=lambda p: p.name):
            if not (d.is_dir() and is_project_id(d.name)):
                continue
            try:
                out.append(self.get_project(d.name))
            except NotFound:
                continue                                   # a folder without meta.json (one being made, or rubbish)
            except StoreError as exc:
                log.warning('project %s left out of the list: %s', d.name, exc)
        return out

    def get_project(self, project_id: str) -> ProjectMeta:
        path = self.project_dir(project_id) / 'meta.json'
        try:
            meta = self._record(path, ProjectMeta)
        except FileNotFoundError:
            raise NotFound('project_not_found', f'no project {project_id!r}') from None
        if meta.id != project_id:
            raise StoreError(f'{self.rel(path)}: id {meta.id!r} in the folder of {project_id!r}')
        return meta

    def list_versions(self, project_id: str) -> list[VersionMeta]:
        return [self.get_version(project_id, n) for n in sorted(self.get_project(project_id).versions)]

    def get_version(self, project_id: str, n: int) -> VersionMeta:
        meta = self.get_project(project_id)
        if n not in meta.versions:
            raise NotFound('version_not_found', f'project {project_id!r} has no version {n}')
        path = self.version_dir(project_id, n) / 'version.json'
        try:
            version = self._record(path, VersionMeta)
        except FileNotFoundError:                # meta.json lists it, the disk does not have it: the store is broken
            raise StoreError(f'{self.rel(path)} is missing (meta.json of {project_id!r} lists version {n})') from None
        if version.project_id != project_id or version.version != n:
            raise StoreError(f'{self.rel(path)}: says {version.project_id} v{version.version}')
        return version

    # ------------------------------------------------------------------------------------------------ files
    def read_json_bytes(self, project_id: str, n: int, name: Literal['model.json', 'stages.json']) -> bytes:
        if name not in ('model.json', 'stages.json'):
            raise ValueError(f'read_json_bytes: {name!r} is neither model.json nor stages.json')
        self.get_version(project_id, n)
        path = self.version_dir(project_id, n) / name
        try:
            return self._read(path)
        except FileNotFoundError:
            if name == 'stages.json':
                raise NotFound('no_stages', f'{project_id} v{n} has no build replay') from None
            raise StoreError(f'{self.rel(path)} is missing') from None

    def read_file_bytes(self, project_id: str, n: int | None, name: StoreFileName, missing_ok: bool = False) -> bytes | None:
        if n is None:
            if name != 'meta.json':
                raise ValueError(f'read_file_bytes: {name!r} needs a version')
            self.get_project(project_id)
            path = self.project_dir(project_id) / 'meta.json'
        else:
            if name not in ('version.json', 'overrides.json', 'model.json', 'stages.json'):
                raise ValueError(f'read_file_bytes: {name!r} is not a version file')
            self.get_version(project_id, n)
            path = self.version_dir(project_id, n) / name
        try:
            return self._read(path)
        except FileNotFoundError:
            if missing_ok:
                return None
            raise NotFound('file_not_found', f'{project_id}{"" if n is None else f" v{n}"} has no {name}') from None

    def _asset_path(self, project_id: str, n: int, name: str) -> tuple[Path, Any]:
        if not safe_name(name):
            raise NotFound('asset_not_found', f'no asset {name!r}')
        version = self.get_version(project_id, n)
        meta = version.asset(name)
        path = self.version_dir(project_id, n) / 'assets' / name
        if meta is None or not path.is_file():
            raise NotFound('asset_not_found', f'{project_id} v{n} has no asset {name!r}')
        return path, meta

    def asset(self, project_id: str, n: int, name: str) -> BlobRef:
        path, meta = self._asset_path(project_id, n, name)
        return BlobRef(media_type=meta.media_type, size=self._stat(path).st_size, sha1=meta.sha1, path=path)

    def asset_bytes(self, project_id: str, n: int, name: str) -> bytes:
        path, _meta = self._asset_path(project_id, n, name)
        try:
            return self._read(path)
        except FileNotFoundError:
            raise NotFound('asset_not_found', f'{project_id} v{n} has no asset {name!r}') from None

    def download(self, project_id: str, n: int, name: str) -> BlobRef:
        if not safe_name(name):
            raise NotFound('download_not_found', f'no download {name!r}')
        self.get_version(project_id, n)
        path = self.version_dir(project_id, n) / 'downloads' / name
        try:
            sha1 = self._cached(path, sha1_hex)
            size = self._stat(path).st_size
        except FileNotFoundError:
            raise NotFound('download_not_found', f'{project_id} v{n} has no download {name!r}') from None
        return BlobRef(media_type=download_media_type(name), size=size, sha1=sha1, path=path)

    # ------------------------------------------------------------------------------------------------ saved heights
    def read_overrides(self, project_id: str, n: int) -> HeightOverridesFile | None:
        self.get_version(project_id, n)
        path = self.version_dir(project_id, n) / 'overrides.json'
        try:
            return self._record(path, HeightOverridesFile)
        except FileNotFoundError:
            return None

    def write_overrides(self, project_id: str, n: int, heights: dict[str, int],
                        if_revision: int | None = None) -> HeightOverridesFile:
        """Replaces the saved map (revision + 1, atomic); the project's updatedAt follows a later save. With `if_revision`
        (the request's If-Match), RevisionConflict unless the saved heights are at that revision now (0: none saved)."""
        with self.exclusive():
            old = self.read_overrides(project_id, n)
            if if_revision is not None and (old.revision if old else 0) != if_revision:
                raise RevisionConflict(if_revision, old)
            record = HeightOverridesFile(format=OVERRIDES_FORMAT, heights={k: int(v) for k, v in heights.items()},
                                         revision=(old.revision if old else 0) + 1, updated_at=iso_utc())
            path = self.version_dir(project_id, n) / 'overrides.json'
            atomic_write_bytes(path, dumps_pretty(record.to_json()))
            meta = self.get_project(project_id)
            if record.updated_at > meta.updated_at:
                self.write_project_meta(meta.model_copy(update={'updated_at': record.updated_at}))
            return record

    # ------------------------------------------------------------------------------------------------ writing (seed, next milestone)
    def write_project_meta(self, meta: ProjectMeta) -> None:
        path = self.project_dir(meta.id) / 'meta.json'
        data = dumps_pretty(meta.to_json())
        with self.exclusive():
            try:
                if self._read(path) == data:
                    return                                  # unchanged: keep the file (and its mtime) as it is
            except FileNotFoundError:
                pass
            atomic_write_bytes(path, data)

    def new_version_staging(self, project_id: str) -> Path:
        """An empty folder versions/.staging-<uuid>/ to write a whole version into (then commit_version)."""
        d = self.project_dir(project_id) / 'versions' / f'.staging-{uuid.uuid4().hex}'
        d.mkdir(parents=True)
        return d

    def commit_version(self, project_id: str, n: int, staging: Path, keep: Iterable[str] = KEPT_ON_REBUILD) -> None:
        """Rename a staged version folder to versions/<n>/. An existing folder is replaced, keeping the files named in
        `keep` (copied into the new folder before the swap, so it is whole the moment it appears). The copy and the swap
        happen under exclusive(): a heights save (any process) lands before the copy or after the swap, never between."""
        target = self.version_dir(project_id, n)
        with self.exclusive():
            if target.exists():
                for name in keep:
                    if (target / name).is_file() and not (staging / name).exists():
                        shutil.copy2(target / name, staging / name)
                trash = target.parent / f'.old-{uuid.uuid4().hex}'
                _rename_dir(target, trash)
                try:
                    _rename_dir(staging, target)
                except BaseException:
                    _rename_dir(trash, target)
                    raise
                # The new folder is in place: the old one is only rubbish now. A file still open in it on Windows must not
                # fail the commit (a leftover .old-* folder is never read: readers take versions/<digits>/ only).
                shutil.rmtree(trash, ignore_errors=True)
            else:
                _rename_dir(staging, target)

    def discard_staging(self, staging: Path) -> None:
        shutil.rmtree(staging, ignore_errors=True)

    def create_project(self, meta: NewProject) -> ProjectMeta:
        if not is_project_id(meta.id):
            raise ValueError(f'project id {meta.id!r} does not match {PROJECT_ID_PATTERN}')
        with self.exclusive():
            d = self.project_dir(meta.id)
            if (d / 'meta.json').exists():
                raise StoreConflict(f'project {meta.id!r} exists')
            now = iso_utc()
            record = ProjectMeta(format=PROJECT_FORMAT, id=meta.id, name=meta.name, short_name=meta.short_name,
                                 project_no=meta.project_no, source_kind=meta.source_kind, created_at=now, updated_at=now,
                                 latest_version=0, versions=[])
            (d / 'versions').mkdir(parents=True, exist_ok=True)
            self.write_project_meta(record)
            return record

    def stage(self, name: str, chunks: Iterable[bytes]) -> StagedRef:
        """Streams `chunks` to data/.staging/<key> (a .part file renamed when complete); the key names it in a draft."""
        safe = re.sub(r'[^A-Za-z0-9._-]+', '-', name or 'upload').strip('.-')[:64] or 'upload'
        key = f'{uuid.uuid4().hex}-{safe}'
        self.staging_dir.mkdir(parents=True, exist_ok=True)
        part = self.staging_dir / f'{key}.part'
        with open(part, 'wb') as f:
            for chunk in chunks:
                f.write(chunk)
        os.replace(part, self.staging_dir / key)
        return StagedRef(key)

    def staged_path(self, ref: StagedRef) -> Path:
        if not re.fullmatch(r'[0-9a-f]{32}-[A-Za-z0-9._-]{1,64}', ref.key):
            raise NotFound('staged_not_found', f'no staged file {ref.key!r}')
        path = self.staging_dir / ref.key
        if not path.is_file():
            raise NotFound('staged_not_found', f'no staged file {ref.key!r}')
        return path

    def _blob_bytes(self, src: BlobSource) -> bytes:
        return src if isinstance(src, bytes) else self.staged_path(src).read_bytes()

    def _place(self, src: BlobSource, dst: Path) -> bytes | None:
        """Writes bytes, or MOVES a staged file (it never passes through memory); returns the bytes when it had them."""
        dst.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(src, bytes):
            dst.write_bytes(src)
            return src
        os.replace(self.staged_path(src), dst)
        return None

    def create_version(self, project_id: str, draft: VersionDraft) -> VersionMeta:
        """DESIGN.md 9.5: validates the model (5.6) and the replay data, allocates n = latestVersion + 1, writes everything
        into versions/.staging-<uuid>/, renames it to versions/<n>/ (atomic), carries the previous saved heights for the
        kinds the new model still has (when asked), then updates meta.json last. The stamp is sha1(model.json)[:12].
        Assets are raster pictures only (PNG, JPEG, WebP, GIF by their bytes): an SVG or anything else is refused, so an
        asset URL can never serve a document that runs script in the staff app's origin.

        The upload milestone (docs/upload/DESIGN.md U-11.1): a `.ms` download whose line-2 stamp is not
        sha1(model.json)[:12] (seed.build.ms_stamp) is refused, checked AFTER the file-name checks; `project_data` (the
        BuildSettings the version was built with) is written as versions/<n>/project-data.json.

        The rooms milestone (docs/rooms/DESIGN.md R-12.2): version.json's `modelFormat` is 'built-model/2' when the
        model has the `stairways` key, else 'built-model/1' (builtmodel.model_format, through seed.build.version_record).
        The version's counts are unchanged: `rooms` still counts the drawn names (model.rooms)."""
        from ..checks import validate_presentation, validate_replay   # noqa: PLC0415 (checks imports the seed's helpers)
        from ..seed.build import ms_stamp, version_record             # noqa: PLC0415

        model_raw = self._blob_bytes(draft.model_json)
        model = builtmodel.validate_bytes(model_raw)
        stages_raw = self._blob_bytes(draft.stages_json) if draft.stages_json is not None else None
        if stages_raw is not None:
            validate_replay(loads_strict(stages_raw), model)
        validate_presentation(draft.presentation, model)
        for group in (draft.assets, draft.downloads, draft.source):
            for name in group:
                if not safe_name(name):
                    raise ValueError(f'file name {name!r} does not match {FILE_NAME_PATTERN} (or is only dots / ends in a dot)')
        stamp = sha1_hex(model_raw)[:12]
        for name, src in draft.downloads.items():
            if name.lower().endswith('.ms'):
                found = ms_stamp(self._blob_bytes(src))
                if found != stamp:
                    raise ValueError(f'{name}: line 2 says model data {found}, the model is {stamp} (U-11.1)')
        roles = asset_roles(model, draft.assets)
        with self.exclusive():
            meta = self.get_project(project_id)
            n = meta.latest_version + 1
            staging = self.new_version_staging(project_id)
            try:
                self._place(draft.model_json, staging / 'model.json')          # a staged file is moved into place
                if draft.stages_json is not None:
                    self._place(draft.stages_json, staging / 'stages.json')
                if (staging / 'model.json').read_bytes() != model_raw:
                    raise StoreError('the staged model changed while the version was written')
                assets = []
                for name, src in draft.assets.items():
                    dst = staging / 'assets' / name
                    self._place(src, dst)
                    data = dst.read_bytes()
                    media = media_type_of(data, name)
                    if media not in RASTER_MEDIA_TYPES:
                        raise ValueError(f'asset {name!r} is not a PNG, JPEG, WebP or GIF picture (by its bytes)')
                    role, floor, ref = roles[name]
                    assets.append({'name': name, 'role': role, 'floor': floor, 'mediaType': media,
                                   'bytes': len(data), 'sha1': sha1_hex(data), 'modelRef': ref})
                for folder, group in (('downloads', draft.downloads), ('source', draft.source)):
                    for name, src in group.items():
                        self._place(src, staging / folder / name)
                if draft.project_data is not None:
                    self._place(draft.project_data, staging / 'project-data.json')
                max_script = next((name for name in sorted(draft.downloads) if name.lower().endswith('.ms')), None)
                now = iso_utc()
                record = version_record(
                    project_id=project_id, n=n, label=draft.label, created_at=now, source_kind=draft.source_kind,
                    source_files=list(draft.source_files), model=model, model_sha1=sha1_hex(model_raw),
                    stamp=stamp, stamp_source='model.json', has_stages=stages_raw is not None,
                    assets=assets, max_script=max_script, presentation=draft.presentation, seed=None)
                (staging / 'version.json').write_bytes(dumps_pretty(record))
                if draft.carry_overrides_from is not None:
                    old = self.read_overrides(project_id, draft.carry_overrides_from)
                    carried = carry_heights(old.heights if old else {}, model)
                    if carried:
                        (staging / 'overrides.json').write_bytes(dumps_pretty(HeightOverridesFile(
                            format=OVERRIDES_FORMAT, heights=carried, revision=1, updated_at=now).to_json()))
                self.commit_version(project_id, n, staging, keep=())
            except BaseException:
                self.discard_staging(staging)
                raise
            self.write_project_meta(meta.model_copy(update={
                'latest_version': n, 'versions': sorted({*meta.versions, n}), 'updated_at': max(now, meta.updated_at)}))
            return self.get_version(project_id, n)


def asset_roles(model: Mapping[str, Any], assets: Iterable[str]) -> dict[str, tuple[str, str | None, str | None]]:
    """name -> (role, floor, modelRef): 'topview.png' is the thumbnail; a plan picture carries the name of its floor's
    pictureFrame file (its last path part). Anything else is refused (an asset is one of the two)."""
    by_file = {Path(pf['file'].replace('\\', '/')).name: (key, pf['file'])
               for key, pf in (model.get('pictureFrame') or {}).items()}
    out: dict[str, tuple[str, str | None, str | None]] = {}
    for name in assets:
        if name == 'topview.png':
            out[name] = ('thumbnail', None, None)
        elif name in by_file:
            out[name] = ('plan-picture', by_file[name][0], by_file[name][1])
        else:
            raise ValueError(f'asset {name!r} is neither topview.png nor a pictureFrame file of the model')
    return out


def carry_heights(heights: Mapping[str, int], model: Mapping[str, Any]) -> dict[str, int]:
    """The saved heights a new version keeps: kinds the model still has, values that still differ from its heights."""
    kinds = {k['key']: k for k in model.get('furnitureKinds') or []}
    return {key: int(heights[key]) for key in kinds if key in heights and heights[key] != kinds[key]['height']}
