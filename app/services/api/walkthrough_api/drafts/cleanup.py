"""Clean-up (docs/upload/DESIGN.md U-4.1) and the start-up marking of runs whose worker is gone (U-3.4).

At API start-up and before each new run:
* upload sessions older than 24 h;
* per build, finished runs older than the two newest `done` build runs (the diff's previous run among them) and the
  newest `done` prepare runs (the newest one that read each source, and the newest one with the layer suggestions);
  the build's last run (the one its page shows) and anything queued or running are never removed;
* builds saved more than 7 days ago (their version keeps what matters);
* open builds untouched for 30 days, their ids logged first.
A build with a run going is never touched. At start-up every queued or running run whose worker is gone (pid dead, or
a different creation time), and every run with a spec.json, no job.json, older than 60 s and whose launch.json pid is
not alive (or with no launch.json), is marked `interrupted`: Build runs it again.
"""
from __future__ import annotations

import logging
from datetime import UTC, datetime, timedelta

from ..jobs.base import JobRunner
from ..jsonio import iso_utc
from ..store.base import BuildRecord, NotFound, Store, StoreError
from .runs import FINISHED, RunView, mark_interrupted, read_runs

log = logging.getLogger('walkthrough_api.drafts')

SAVED_KEEP_DAYS = 7
UNTOUCHED_DAYS = 30


def _when(iso: str) -> datetime:
    return datetime.strptime(iso, '%Y-%m-%dT%H:%M:%SZ').replace(tzinfo=UTC)


def clean_runs(store: Store, project_id: str, build_id: str, runs: list[RunView]) -> list[str]:
    """Removes the build's finished runs that are no longer needed (see the module text); returns their ids."""
    if not runs:
        return []
    keep = {runs[-1].id} | {r.id for r in runs if not r.status in FINISHED}
    builds = [r for r in runs if r.kind == 'build' and r.status == 'done']
    keep |= {r.id for r in builds[-2:]}
    prepares = [r for r in runs if r.kind == 'prepare' and r.status == 'done']
    covered: set[str] = set()
    for r in reversed(prepares):
        read = set(r.only or [s['sha1'] for s in (r.spec or {}).get('sources', [])])
        if read - covered:
            keep.add(r.id)
            covered |= read
    full = [r for r in prepares if not r.only]
    if full:
        keep.add(full[-1].id)
    oldest_build = builds[-2].number if len(builds) >= 2 else 0
    newest_prepare = prepares[-1].number if prepares else 0
    gone = []
    for r in runs:
        if r.id in keep or r.status not in FINISHED:
            continue
        if (r.kind == 'build' and r.number < oldest_build) or (r.kind == 'prepare' and r.number < newest_prepare):
            try:
                store.remove_run(project_id, build_id, r.id)
                gone.append(r.id)
            except OSError as exc:
                log.warning('run %s/%s/%s could not be removed: %s', project_id, build_id, r.id, exc)
    return gone


def _drop(store: Store, build: BuildRecord, why: str) -> None:
    try:
        with store.build_lock(build.project_id, build.id):
            store.delete_build(build.project_id, build.id)
        store.remove_build_dir(build.project_id, build.id)
        log.info('build %s/%s removed: %s', build.project_id, build.id, why)
    except (NotFound, StoreError, OSError) as exc:
        log.warning('build %s/%s was not removed (%s): %s', build.project_id, build.id, why, exc)


def before_run(store: Store, jobs: JobRunner) -> None:
    """Upload sessions past 24 h, builds saved over 7 days ago, open builds untouched for 30 days."""
    now = datetime.now(UTC)
    try:
        store.clean_uploads(iso_utc(now))
    except OSError as exc:
        log.warning('upload sessions were not cleaned: %s', exc)
    for build in list(store.iter_builds()):
        try:
            if any(not r.status in FINISHED for r in read_runs(store, build.project_id, build.id, jobs.alive)):
                continue
            age = now - _when(build.updated_at)
        except (NotFound, StoreError, ValueError, OSError):
            continue
        if build.status == 'saved' and age > timedelta(days=SAVED_KEEP_DAYS):
            _drop(store, build, f'saved as v{build.saved_version} more than {SAVED_KEEP_DAYS} days ago')
        elif build.status == 'open' and age > timedelta(days=UNTOUCHED_DAYS):
            log.warning('build %s/%s untouched for %d days: removing it', build.project_id, build.id, UNTOUCHED_DAYS)
            _drop(store, build, f'untouched for {UNTOUCHED_DAYS} days')


def mark_gone_runs(store: Store, jobs: JobRunner) -> list[str]:
    """Marks `interrupted` every run of every build whose worker is gone (U-3.4); returns '<project>/<build>/<run>'."""
    marked = []
    for build in list(store.iter_builds()):
        try:
            runs = read_runs(store, build.project_id, build.id, jobs.alive)
            if not any(r.gone for r in runs):
                continue
            with store.build_lock(build.project_id, build.id):
                for r in read_runs(store, build.project_id, build.id, jobs.alive):
                    if r.gone:
                        mark_interrupted(r)
                        marked.append(f'{build.project_id}/{build.id}/{r.id}')
        except (NotFound, StoreError, OSError) as exc:
            log.warning('the runs of build %s/%s were not checked: %s', build.project_id, build.id, exc)
    return marked


def startup(store: Store, jobs: JobRunner) -> None:
    """At API start-up: the interrupted marking, then the clean-up (U-3.4, U-4.1)."""
    marked = mark_gone_runs(store, jobs)
    if marked:
        log.warning('runs marked interrupted at start-up (their worker is gone): %s', ', '.join(marked))
    before_run(store, jobs)
    for build in list(store.iter_builds()):
        try:
            with store.build_lock(build.project_id, build.id):
                clean_runs(store, build.project_id, build.id,
                           read_runs(store, build.project_id, build.id, jobs.alive))
        except (NotFound, StoreError, OSError) as exc:
            log.warning('the runs of build %s/%s were not cleaned: %s', build.project_id, build.id, exc)
