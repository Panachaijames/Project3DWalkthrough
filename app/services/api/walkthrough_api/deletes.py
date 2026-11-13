"""deleteProject and deleteVersion (the owner's request of 12 Nov 2026; docs/contract-issues/DEL.md).

* deleteProject: 404 project_not_found; 409 busy while a run of one of its drafts (a file reading or a build) is queued
  or running; else the whole project folder goes (versions, drafts and their runs, uploaded drawings, settings) and its
  upload sessions. The offices' memory and the converter's cache are shared and stay. A seeded project can be deleted
  too (`npm run seed` brings it back).
* deleteVersion: 404 project_not_found, version_not_found; 409 only_version (delete the project instead); 409 busy as
  above; else the version leaves the listings (latestVersion = the highest version left) and its folder keeps only a
  tombstone, so its number is never given again. The draft that was saved as that version (kept 7 days for "Use the
  files of v<n> again") goes with it; open drafts keep working (their recipe and files are their own); a new draft from
  the deleted version gets 404 version_not_found "version <n> of <project> was deleted".
Both answer 409 busy too when a file of the project stays open past the store's retries (a download being sent): nothing
was changed then.
"""
from __future__ import annotations

import logging
from collections.abc import Callable

from .errors import ApiError
from .drafts.runs import read_runs
from .jobs.base import JobRunner
from .store.base import NotFound, ProjectMeta, Store, StoreConflict, StoreError

log = logging.getLogger('walkthrough_api.deletes')

BUSY_PROJECT = 'Wait for the build to finish (or cancel it), then delete the project.'
BUSY_VERSION = 'Wait for the build to finish (or cancel it), then delete the version.'
FILE_OPEN = 'A file of this project is in use (a download being sent?): try again in a moment.'
ONLY_VERSION = "This is the project's only version: delete the project instead."


def running_drafts(store: Store, jobs: JobRunner, project_id: str) -> list[str]:
    """The ids of the project's drafts with a run queued or running (a file reading or a build)."""
    out = []
    for build in store.list_builds(project_id):
        if any(r.in_progress for r in read_runs(store, project_id, build.id, jobs.alive)):
            out.append(build.id)
    return out


def _not_busy(store: Store, jobs: JobRunner, message: str) -> Callable[[ProjectMeta], None]:
    """A check for the store's delete: 409 busy while a draft of the project has a run going."""
    def check(meta: ProjectMeta) -> None:
        busy = running_drafts(store, jobs, meta.id)
        if busy:
            raise ApiError(409, 'busy', message, {'builds': busy})
    return check


def delete_project(store: Store, jobs: JobRunner, project_id: str) -> None:
    try:
        store.delete_project(project_id, check=_not_busy(store, jobs, BUSY_PROJECT))
    except PermissionError as exc:
        log.warning('project %s was not deleted: a file in it is open (%s)', project_id, exc)
        raise ApiError(409, 'busy', FILE_OPEN) from None
    log.info('project %s deleted', project_id)


def delete_version(store: Store, jobs: JobRunner, project_id: str, n: int) -> None:
    def check(meta: ProjectMeta) -> None:
        if len(meta.versions) <= 1:
            raise ApiError(409, 'only_version', ONLY_VERSION)
        _not_busy(store, jobs, BUSY_VERSION)(meta)

    try:
        store.delete_version(project_id, n, check=check)
    except StoreConflict as exc:                         # the store's own guard (the check said it first)
        raise ApiError(409, 'only_version', ONLY_VERSION) from exc
    except PermissionError as exc:
        log.warning('%s v%d was not deleted: a file in it is open (%s)', project_id, n, exc)
        raise ApiError(409, 'busy', FILE_OPEN) from None
    log.info('%s v%d deleted', project_id, n)
    _drop_saved_drafts(store, project_id, n)


def _drop_saved_drafts(store: Store, project_id: str, n: int) -> None:
    """The draft saved as v<n> (status saved; kept 7 days for "Use the files of v<n> again") goes with its version.
    Best effort: one that cannot be removed now is removed by the 7-day clean-up, and nothing offers it meanwhile."""
    try:
        builds = store.list_builds(project_id)
    except (NotFound, StoreError, OSError) as exc:
        log.warning('the drafts of %s were not read after v%d was deleted: %s', project_id, n, exc)
        return
    for build in builds:
        if build.status != 'saved' or build.saved_version != n:
            continue
        try:
            with store.build_lock(project_id, build.id):
                store.delete_build(project_id, build.id)
            store.remove_build_dir(project_id, build.id)
        except (NotFound, StoreError, OSError) as exc:
            log.warning('draft %s/%s (saved as the deleted v%d) was not removed: %s', project_id, build.id, n, exc)
