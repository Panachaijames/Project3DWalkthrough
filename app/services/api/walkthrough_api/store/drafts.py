"""LocalStore's files of the upload milestone (docs/upload/DESIGN.md U-4.1, U-5, U-13.4; step U5): a mixin LocalStore
inherits, so store/local.py keeps the foundation's code as it was.

    <root>/projects/<id>/project-settings.json          ProjectSettingsFile
    <root>/projects/<id>/sources/<sha1>/source.json     SourceRecord, + original.dwg | original.dxf (never served)
    <root>/projects/<id>/builds/<buildId>/build.json    BuildRecord (the build exists while this file does)
    <root>/projects/<id>/builds/<buildId>/settings.json BuildSettingsFile
    <root>/projects/<id>/builds/<buildId>/.api.lock     the per-build lock (adoption, validation, save; U-3.2)
    <root>/projects/<id>/builds/<buildId>/runs/<runId>/ spec.json, launch.json, api.json, job.json, cancel, log.txt, out/
    <root>/mappings/<officeId>.json                     OfficeMapping
    <root>/.uploads/<uploadId>/                         session.json + part-00001 ... (deleted on complete or cancel)

Folders are made when first used, so a freshly seeded store is still `['.lock', 'projects']`. Every JSON file is written
atomically (jsonio.atomic_write_bytes: temp file, os.replace retried on sharing violations), `indent=2` + newline. Every
write checks the full path first (U-4.1: long paths are off on this laptop): past 259 characters, with room for the
temp file's longer name, it fails with PathTooLong's plain message instead of a FileNotFoundError.
"""
from __future__ import annotations

import hashlib
import logging
import os
import re
import shutil
import time
import uuid
from collections.abc import Iterator
from contextlib import AbstractContextManager, contextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any

from pydantic import ValidationError

from ..jsonio import JsonError, atomic_write_bytes, dumps_pretty, loads_strict, retry_on_sharing
from ..models_upload import OfficeMapping
from .base import (BuildRecord, BuildSettingsFile, NotFound, PathTooLong, ProjectSettingsFile, SourceRecord, StoreError,
                   UploadSessionFile)
from .filelock import file_lock

if TYPE_CHECKING:
    from .base import ProjectMeta, VersionMeta

log = logging.getLogger('walkthrough_api.store')

#: Windows' MAX_PATH less its terminating NUL.
MAX_PATH_CHARS = 259
#: Room for an atomic write's temp name: '.tmp-' + 8 random characters + '-' + the file's name (+2 spare).
TEMP_MARGIN = 16
UPLOAD_ID = re.compile(r'u[0-9a-f]{24}')
BUILD_ID = re.compile(r'[0-9]{8}T[0-9]{6}-[0-9a-f]{6}')
RUN_ID = re.compile(r'([0-9]{4})-(prepare|build)')
SHA1 = re.compile(r'[0-9a-f]{40}')
OFFICE_ID = re.compile(r'[a-z0-9][a-z0-9-]{1,62}')
PART_FILE = re.compile(r'part-([0-9]{5})')
#: the longest names below a project folder that a prepare run writes (U-4.1's worked example)
_EXAMPLE_BUILD = '20261104T101500-0a1b2c'
_EXAMPLE_RUN = '0001-prepare'
BUILD_LOCK_TIMEOUT_S = 120.0


def rmtree(path: Path, tries: int = 10) -> None:
    """shutil.rmtree, retried for a moment on Windows' sharing violations (a file being read or replaced)."""
    for i in range(tries):
        try:
            shutil.rmtree(path)
            return
        except FileNotFoundError:
            return
        except PermissionError:
            if i == tries - 1:
                raise
            time.sleep(0.1 * (i + 1))


class DraftFiles:
    """The upload milestone's part of LocalStore (see the module text). Uses LocalStore's root, project_dir,
    version_dir, rel, _read, _record, _cached, exclusive, get_project and get_version."""

    root: Path
    _uploads_lock: Any

    if TYPE_CHECKING:                                    # LocalStore's own, used here
        def project_dir(self, project_id: str) -> Path: ...
        def version_dir(self, project_id: str, n: int) -> Path: ...
        def rel(self, path: Path) -> str: ...
        def _read(self, path: Path) -> bytes: ...
        def _record(self, path: Path, cls: Any) -> Any: ...
        def _cached(self, path: Path, parse: Any) -> Any: ...
        def exclusive(self) -> AbstractContextManager[None]: ...
        def get_project(self, project_id: str) -> ProjectMeta: ...
        def get_version(self, project_id: str, n: int) -> VersionMeta: ...
        def list_projects(self) -> list[ProjectMeta]: ...

    # ------------------------------------------------------------------------------------------------ paths
    def check_path(self, path: Path) -> Path:
        """`path` when it, and its temp file's longer name, stay within 259 characters; else PathTooLong (U-4.1)."""
        length = len(os.path.abspath(path)) + TEMP_MARGIN
        if length > MAX_PATH_CHARS:
            raise PathTooLong(length)
        return Path(path)

    def deepest_run_path(self, project_id: str) -> Path:
        """The longest path a prepare run of this project writes: .../builds/<buildId>/runs/0001-prepare/out/sources/
        <sha1>/conversion.json (U-4.1)."""
        return (self.project_dir(project_id) / 'builds' / _EXAMPLE_BUILD / 'runs' / _EXAMPLE_RUN / 'out' / 'sources'
                / ('0' * 40) / 'conversion.json')

    def _write_json(self, path: Path, obj: Any) -> None:
        self.check_path(path)
        atomic_write_bytes(path, dumps_pretty(obj))

    def _parsed(self, path: Path, cls: Any) -> Any:
        """A store file parsed into a pydantic model by its JSON names, cached by mtime; StoreError when broken,
        FileNotFoundError when absent."""
        def parse(raw: bytes) -> Any:
            try:
                return cls.model_validate(loads_strict(raw), by_alias=True, by_name=False)
            except (JsonError, ValidationError) as exc:
                raise StoreError(f'{self.rel(path)}: not a valid {cls.__name__}: {exc}') from exc
        return self._cached(path, parse)

    # ------------------------------------------------------------------------------------------------ project settings
    def project_settings(self, project_id: str) -> ProjectSettingsFile | None:
        self.get_project(project_id)
        try:
            return self._record(self.project_dir(project_id) / 'project-settings.json', ProjectSettingsFile)
        except FileNotFoundError:
            return None

    def write_project_settings(self, project_id: str, record: ProjectSettingsFile) -> None:
        self.get_project(project_id)
        self._write_json(self.project_dir(project_id) / 'project-settings.json', record.to_json())

    def version_project_data(self, project_id: str, n: int) -> bytes | None:
        """versions/<n>/project-data.json as stored (the BuildSettings the version was built with), or None."""
        self.get_version(project_id, n)
        try:
            return self._read(self.version_dir(project_id, n) / 'project-data.json')
        except FileNotFoundError:
            return None

    def version_file_path(self, project_id: str, n: int, name: str) -> Path:
        self.get_version(project_id, n)
        return self.version_dir(project_id, n) / name

    # ------------------------------------------------------------------------------------------------ offices
    @property
    def mappings_dir(self) -> Path:
        return self.root / 'mappings'

    def list_offices(self) -> list[OfficeMapping]:
        """Every readable office file, by id. A broken one is left out (and logged)."""
        if not self.mappings_dir.is_dir():
            return []
        out = []
        for p in sorted(self.mappings_dir.glob('*.json'), key=lambda q: q.name):
            if not OFFICE_ID.fullmatch(p.stem):
                continue
            try:
                found = self.get_office(p.stem)
            except StoreError as exc:
                log.warning('office %s left out of the list: %s', p.stem, exc)
                continue
            if found is not None:
                out.append(found)
        return out

    def get_office(self, office_id: str) -> OfficeMapping | None:
        if not isinstance(office_id, str) or not OFFICE_ID.fullmatch(office_id):
            return None
        path = self.mappings_dir / f'{office_id}.json'
        try:
            mapping: OfficeMapping = self._parsed(path, OfficeMapping)
        except FileNotFoundError:
            return None
        if mapping.id != office_id:
            raise StoreError(f'{self.rel(path)}: says office {mapping.id!r}')
        return mapping

    def write_office(self, mapping: OfficeMapping) -> None:
        if not OFFICE_ID.fullmatch(mapping.id):
            raise ValueError(f'office id {mapping.id!r} does not match ^[a-z0-9][a-z0-9-]{{1,62}}$')
        self._write_json(self.mappings_dir / f'{mapping.id}.json', mapping.model_dump(mode='json', by_alias=True))

    # ------------------------------------------------------------------------------------------------ upload sessions
    @property
    def uploads_dir(self) -> Path:
        return self.root / '.uploads'

    def _upload_dir(self, upload_id: str) -> Path:
        if not isinstance(upload_id, str) or not UPLOAD_ID.fullmatch(upload_id):
            raise NotFound('upload_not_found', f'no upload {upload_id!r}')
        return self.uploads_dir / upload_id

    def create_upload(self, record: UploadSessionFile) -> UploadSessionFile:
        d = self._upload_dir(record.id)
        self.check_path(d / 'part-00001.0123456789abcdef.tmp')
        d.mkdir(parents=True, exist_ok=False)
        self._write_json(d / 'session.json', record.to_json())
        return record

    def get_upload(self, upload_id: str) -> UploadSessionFile:
        """The session with `received` as the part files on disk say (two parts may arrive at once)."""
        d = self._upload_dir(upload_id)
        try:
            record = self._record(d / 'session.json', UploadSessionFile)
        except FileNotFoundError:
            raise NotFound('upload_not_found', f'no upload {upload_id!r}') from None
        if record.id != upload_id:
            raise StoreError(f'{self.rel(d / "session.json")}: says upload {record.id!r}')
        return record.model_copy(update={'received': self.upload_received(upload_id)})

    def upload_received(self, upload_id: str) -> list[int]:
        d = self._upload_dir(upload_id)
        try:
            names = os.listdir(d)
        except FileNotFoundError:
            raise NotFound('upload_not_found', f'no upload {upload_id!r}') from None
        return sorted(int(m.group(1)) for n in names if (m := PART_FILE.fullmatch(n)))

    def put_upload_part(self, upload_id: str, part: int, data: bytes) -> None:
        """Writes part-NNNNN.<random>.tmp, then renames it over part-NNNNN: a part sent again replaces itself, and two
        sends of one part never write into the same file."""
        d = self._upload_dir(upload_id)
        if not (d / 'session.json').is_file():
            raise NotFound('upload_not_found', f'no upload {upload_id!r}')
        tmp = d / f'part-{part:05d}.{uuid.uuid4().hex[:16]}.tmp'
        try:
            with open(tmp, 'wb') as f:
                f.write(data)
            retry_on_sharing(lambda: os.replace(tmp, d / f'part-{part:05d}'))
        except FileNotFoundError:                        # the session was cancelled meanwhile
            raise NotFound('upload_not_found', f'no upload {upload_id!r}') from None
        finally:
            try:
                os.unlink(tmp)
            except OSError:
                pass
        with self._uploads_lock:
            try:
                record = self.get_upload(upload_id)
                self._write_json(d / 'session.json', record.to_json())
            except (NotFound, FileNotFoundError):
                pass

    def join_upload(self, upload_id: str) -> tuple[Path, str, int]:
        """The parts streamed together into <session>/joined-<random>.tmp: (that file, its sha1, its size)."""
        record = self.get_upload(upload_id)
        d = self._upload_dir(upload_id)
        out = d / f'joined-{uuid.uuid4().hex[:12]}.tmp'
        h = hashlib.sha1()
        size = 0
        try:
            with open(out, 'wb') as f:
                for i in range(1, record.parts + 1):
                    with open(d / f'part-{i:05d}', 'rb') as part:
                        for chunk in iter(lambda: part.read(1 << 20), b''):
                            h.update(chunk)
                            f.write(chunk)
                            size += len(chunk)
        except FileNotFoundError:
            try:
                os.unlink(out)
            except OSError:
                pass
            raise NotFound('upload_not_found', f'upload {upload_id!r} lost a part while it was being joined') from None
        return out, h.hexdigest(), size

    def delete_upload(self, upload_id: str) -> None:
        d = self._upload_dir(upload_id)
        if not d.is_dir():
            raise NotFound('upload_not_found', f'no upload {upload_id!r}')
        rmtree(d)

    def clean_uploads(self, now: str) -> list[str]:
        """Removes every session whose expiresAt has passed (24 h after it was made), and folders with no readable
        session older than 24 h. Returns the ids removed."""
        if not self.uploads_dir.is_dir():
            return []
        gone = []
        for d in sorted(self.uploads_dir.iterdir()):
            if not d.is_dir():
                continue
            try:
                expired = self._record(d / 'session.json', UploadSessionFile).expires_at <= now
            except (FileNotFoundError, StoreError):
                expired = time.time() - d.stat().st_mtime > 24 * 3600
            if expired:
                try:
                    rmtree(d)
                    gone.append(d.name)
                except OSError as exc:
                    log.warning('upload %s could not be removed: %s', d.name, exc)
        return gone

    # ------------------------------------------------------------------------------------------------ sources
    def _source_dir(self, project_id: str, sha1: str) -> Path:
        if not isinstance(sha1, str) or not SHA1.fullmatch(sha1):
            raise NotFound('source_not_found', f'no source {sha1!r}')
        return self.project_dir(project_id) / 'sources' / sha1

    def store_source(self, project_id: str, temp: Path, record: SourceRecord) -> SourceRecord:
        """Moves the joined upload to sources/<sha1>/original.<ext> and writes source.json. A sha1 the project has already
        keeps the stored file and its record (the same drawing uploaded twice is one source, U-5.1)."""
        self.get_project(project_id)
        d = self._source_dir(project_id, record.sha1)
        with self.exclusive():
            try:
                existing = self.get_source(project_id, record.sha1)
            except NotFound:
                existing = None
            if existing is not None:
                os.unlink(temp)
                return existing
            dst = self.check_path(d / record.file)
            self.check_path(d / 'source.json')
            d.mkdir(parents=True, exist_ok=True)
            retry_on_sharing(lambda: os.replace(temp, dst))
            self._write_json(d / 'source.json', record.to_json())
            return record

    def get_source(self, project_id: str, sha1: str) -> SourceRecord:
        self.get_project(project_id)
        path = self._source_dir(project_id, sha1) / 'source.json'
        try:
            record = self._record(path, SourceRecord)
        except FileNotFoundError:
            raise NotFound('source_not_found', f'project {project_id!r} has no source {sha1}') from None
        if record.sha1 != sha1:
            raise StoreError(f'{self.rel(path)}: says source {record.sha1}')
        return record

    def source_path(self, project_id: str, sha1: str) -> Path:
        record = self.get_source(project_id, sha1)
        path = self._source_dir(project_id, sha1) / record.file
        if not path.is_file():
            raise StoreError(f'{self.rel(path)} is missing (its source.json is there)')
        return path

    # ------------------------------------------------------------------------------------------------ builds
    def builds_dir(self, project_id: str) -> Path:
        return self.project_dir(project_id) / 'builds'

    def build_dir(self, project_id: str, build_id: str) -> Path:
        if not isinstance(build_id, str) or not BUILD_ID.fullmatch(build_id):
            raise NotFound('build_not_found', f'no build {build_id!r}')
        return self.builds_dir(project_id) / build_id

    def create_build(self, record: BuildRecord, settings: BuildSettingsFile) -> None:
        d = self.build_dir(record.project_id, record.id)
        self.check_path(self.deepest_run_path(record.project_id))
        d.mkdir(parents=True, exist_ok=False)
        self._write_json(d / 'settings.json', settings.to_json())
        self._write_json(d / 'build.json', record.to_json())        # last: the build exists from now on

    def get_build(self, project_id: str, build_id: str) -> BuildRecord:
        self.get_project(project_id)
        path = self.build_dir(project_id, build_id) / 'build.json'
        try:
            record = self._record(path, BuildRecord)
        except FileNotFoundError:
            raise NotFound('build_not_found', f'project {project_id!r} has no build {build_id}') from None
        if record.id != build_id or record.project_id != project_id:
            raise StoreError(f'{self.rel(path)}: says {record.project_id} build {record.id}')
        return record

    def list_builds(self, project_id: str) -> list[BuildRecord]:
        self.get_project(project_id)
        d = self.builds_dir(project_id)
        if not d.is_dir():
            return []
        out = []
        for b in sorted(d.iterdir(), key=lambda p: p.name):
            if not (b.is_dir() and BUILD_ID.fullmatch(b.name)):
                continue
            try:
                out.append(self.get_build(project_id, b.name))
            except NotFound:
                continue                                   # being made, or being deleted
            except StoreError as exc:
                log.warning('build %s/%s left out of the list: %s', project_id, b.name, exc)
        return out

    def iter_builds(self) -> Iterator[BuildRecord]:
        for p in self.list_projects():
            try:
                yield from self.list_builds(p.id)
            except (NotFound, StoreError) as exc:
                log.warning('the builds of %s were not read: %s', p.id, exc)

    def write_build(self, record: BuildRecord) -> None:
        self._write_json(self.build_dir(record.project_id, record.id) / 'build.json', record.to_json())

    def get_build_settings(self, project_id: str, build_id: str) -> BuildSettingsFile:
        self.get_build(project_id, build_id)
        path = self.build_dir(project_id, build_id) / 'settings.json'
        try:
            return self._record(path, BuildSettingsFile)
        except FileNotFoundError:
            raise StoreError(f'{self.rel(path)} is missing (its build.json is there)') from None

    def write_build_settings(self, project_id: str, build_id: str, record: BuildSettingsFile) -> None:
        self._write_json(self.build_dir(project_id, build_id) / 'settings.json', record.to_json())

    def delete_build(self, project_id: str, build_id: str) -> None:
        """Removes build.json: the build is gone from then on (a request waiting on its lock gets build_not_found). The
        folder goes with remove_build_dir, called after the build's lock is released (Windows cannot remove a folder
        holding an open lock file)."""
        d = self.build_dir(project_id, build_id)
        try:
            retry_on_sharing(lambda: os.unlink(d / 'build.json'))
        except FileNotFoundError:
            raise NotFound('build_not_found', f'project {project_id!r} has no build {build_id}') from None

    def remove_build_dir(self, project_id: str, build_id: str) -> None:
        """The folder of a deleted build (no build.json): removed whole, or left as rubbish that is never listed."""
        d = self.build_dir(project_id, build_id)
        if (d / 'build.json').exists():
            raise StoreError(f'{self.rel(d)} still has its build.json: delete the build first')
        try:
            rmtree(d)
        except OSError as exc:
            log.warning('build folder %s was not removed whole: %s', self.rel(d), exc)

    def build_lock(self, project_id: str, build_id: str) -> AbstractContextManager[None]:
        """The per-build lock (U-3.2): an OS lock on builds/<buildId>/.api.lock, held for adoption, validation, a settings
        save, a run start and a save. NotFound when the build is not there (the lock never makes its folder again)."""
        @contextmanager
        def held() -> Iterator[None]:
            self.get_project(project_id)                 # project_not_found before build_not_found
            d = self.build_dir(project_id, build_id)
            if not (d / 'build.json').is_file():
                raise NotFound('build_not_found', f'project {project_id!r} has no build {build_id}')
            with file_lock(d / '.api.lock', BUILD_LOCK_TIMEOUT_S,
                           f'build {build_id} is busy: another request held its lock for over '
                           f'{BUILD_LOCK_TIMEOUT_S:.0f} s'):
                if not (d / 'build.json').is_file():     # deleted while this request waited
                    raise NotFound('build_not_found', f'project {project_id!r} has no build {build_id}')
                yield
        return held()

    # ------------------------------------------------------------------------------------------------ runs
    def run_ids(self, project_id: str, build_id: str) -> list[str]:
        d = self.build_dir(project_id, build_id) / 'runs'
        try:
            names = os.listdir(d)
        except FileNotFoundError:
            return []
        return sorted((n for n in names if RUN_ID.fullmatch(n)), key=lambda n: int(n[:4]))

    def run_dir(self, project_id: str, build_id: str, run_id: str) -> Path:
        if not isinstance(run_id, str) or not RUN_ID.fullmatch(run_id):
            raise NotFound('run_not_found', f'no run {run_id!r}')
        return self.build_dir(project_id, build_id) / 'runs' / run_id

    def new_run_dir(self, project_id: str, build_id: str, kind: str) -> tuple[str, Path]:
        """The next run's folder (numbered after every run the build ever had), with an empty out/. Call it under the
        build's lock."""
        if kind not in ('prepare', 'build'):
            raise ValueError(f'run kind {kind!r}')
        ids = self.run_ids(project_id, build_id)
        n = int(ids[-1][:4]) + 1 if ids else 1
        run_id = f'{n:04d}-{kind}'
        d = self.run_dir(project_id, build_id, run_id)
        self.check_path(d / 'out' / 'sources' / ('0' * 40) / 'conversion.json')
        (d / 'out').mkdir(parents=True, exist_ok=False)
        return run_id, d

    def remove_run(self, project_id: str, build_id: str, run_id: str) -> None:
        d = self.run_dir(project_id, build_id, run_id)
        rmtree(d)
