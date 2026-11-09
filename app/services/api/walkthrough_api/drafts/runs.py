"""Reading a run folder (docs/upload/DESIGN.md U-3.2, U-3.4): builds/<buildId>/runs/<runId>/{spec.json, launch.json,
job.json, api.json, cancel, out/}.

The worker writes job.json; the API writes it only to mark a run `interrupted` (its worker is gone), `cancelled` (the
runner had to kill it and the pid has exited) or `failed` with invalid_output (validate.py). The EFFECTIVE status of a
run is job.json's, except:
* queued / running in job.json while its worker is gone (pid dead, or a different creation time: `JobRunner.alive`) ->
  interrupted;
* no job.json yet: queued while the launch.json worker lives; interrupted when that pid is gone (it died before it wrote
  anything), or, with no launch.json at all, once spec.json is older than 60 s;
* a job.json that does not parse or is not a JobRecord: running while the worker lives, else interrupted.
`gone` marks such a run, so that the next request holding the build's lock writes `interrupted` into job.json (U-3.4).
"""
from __future__ import annotations

import os
import threading
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from ..jsonio import JsonError, atomic_write_bytes, dumps_pretty, iso_utc, loads_strict, read_bytes
from ..models_upload import JobRecord, JobSpec, LaunchRecord, RunApiRecord, RunInfo
from ..store.base import Store

LAUNCH_GRACE_S = 60.0
MESSAGES_SHOWN = 50
MESSAGES_KEPT = 200
IN_PROGRESS = ('queued', 'running')
FINISHED = ('done', 'failed', 'cancelled', 'interrupted')
INTERRUPTED_TEXT = ('The builder stopped before it finished (it was ended, or the computer or the API restarted): '
                    'build again.')
CANCELLED_TEXT = 'Cancelled: the run was stopped.'

Alive = Callable[[dict[str, Any]], bool]


_RECORDS: dict[str, tuple[tuple[int, int, int], dict[str, Any] | None]] = {}
_RECORDS_LOCK = threading.Lock()
_RECORDS_MAX = 512


def read_record(path: Path, cls: Any) -> dict[str, Any] | None:
    """A run file as its JSON (camelCase) after checking it against its record by JSON names; None when absent, not
    strict JSON or not that record. Cached by the file's mtime, size and id: getBuild is polled every second, and a
    spec.json (written once) can carry a settings snapshot of several MB."""
    try:
        st = os.stat(path)
    except (FileNotFoundError, NotADirectoryError):
        return None
    except OSError:
        return None
    key = (st.st_mtime_ns, st.st_size, st.st_ino)
    hit = _RECORDS.get(str(path))
    if hit is not None and hit[0] == key:
        return hit[1]
    try:
        obj = loads_strict(read_bytes(path))
        cls.model_validate(obj, by_alias=True, by_name=False)
        found = obj if isinstance(obj, dict) else None
    except (FileNotFoundError, NotADirectoryError):
        return None
    except (JsonError, ValidationError, PermissionError, IsADirectoryError):
        found = None
    try:
        after = os.stat(path)
    except OSError:
        return found
    if (after.st_mtime_ns, after.st_size, after.st_ino) == key:          # not replaced while it was read
        with _RECORDS_LOCK:
            if len(_RECORDS) >= _RECORDS_MAX:
                _RECORDS.clear()
            _RECORDS[str(path)] = (key, found)
    return found


def write_record(path: Path, cls: Any, obj: dict[str, Any]) -> None:
    """A run file the API writes (job.json in its three cases, launch.json, api.json, spec.json): checked against its
    record, then written atomically (os.replace retried while the worker or a poll has it open)."""
    cls.model_validate(obj, by_alias=True, by_name=False)
    atomic_write_bytes(path, dumps_pretty(obj))


def mtime_iso(path: Path) -> str | None:
    try:
        return iso_utc(os.stat(path).st_mtime)
    except OSError:
        return None


@dataclass
class RunView:
    id: str
    number: int
    kind: str
    dir: Path
    spec: dict[str, Any] | None
    job: dict[str, Any] | None
    job_broken: bool
    launch: dict[str, Any] | None
    api: dict[str, Any] | None
    cancel: bool
    status: str
    gone: bool = False
    extra: dict[str, Any] = field(default_factory=dict)

    @property
    def out(self) -> Path:
        return self.dir / 'out'

    @property
    def in_progress(self) -> bool:
        return self.status in IN_PROGRESS

    @property
    def validated(self) -> bool | None:
        return None if self.api is None else self.api.get('validated')

    @property
    def done_and_valid(self) -> bool:
        return self.status == 'done' and self.validated is True

    @property
    def settings_revision(self) -> int | None:
        return None if self.spec is None else self.spec.get('settingsRevision')

    @property
    def only(self) -> list[str] | None:
        return None if self.spec is None else self.spec.get('only')

    @property
    def finished_at(self) -> str | None:
        return None if self.job is None else self.job.get('finishedAt')


def _spec_age(run_dir: Path) -> float:
    try:
        return time.time() - os.stat(run_dir / 'spec.json').st_mtime
    except OSError:
        return 0.0


def read_run(run_dir: Path, alive: Alive) -> RunView:
    run_id = run_dir.name
    number, kind = int(run_id[:4]), run_id[5:]
    spec = read_record(run_dir / 'spec.json', JobSpec)
    launch = read_record(run_dir / 'launch.json', LaunchRecord)
    api = read_record(run_dir / 'api.json', RunApiRecord)
    job_path = run_dir / 'job.json'
    job = read_record(job_path, JobRecord)
    job_broken = job is None and job_path.exists()
    cancel = (run_dir / 'cancel').exists()

    def worker_lives() -> bool:
        record = job if job is not None and job.get('pid') and job.get('procStart') else launch
        if record is not None and record.get('pid'):
            return alive(record)
        return _spec_age(run_dir) < LAUNCH_GRACE_S          # never launched (yet): give it a minute

    gone = False
    if job is not None:
        status = job['status']
        if status in IN_PROGRESS and not worker_lives():
            status, gone = 'interrupted', True
    elif job_broken:
        status = 'running' if worker_lives() else 'interrupted'
        gone = status == 'interrupted'
    elif launch is not None:
        status = 'queued' if alive(launch) else 'interrupted'
        gone = status == 'interrupted'
    else:
        status = 'queued' if _spec_age(run_dir) < LAUNCH_GRACE_S else 'interrupted'
        gone = status == 'interrupted'
    return RunView(id=run_id, number=number, kind=kind, dir=run_dir, spec=spec, job=job, job_broken=job_broken,
                   launch=launch, api=api, cancel=cancel, status=status, gone=gone)


def read_runs(store: Store, project_id: str, build_id: str, alive: Alive) -> list[RunView]:
    """Every run of a build, oldest first."""
    return [read_run(store.run_dir(project_id, build_id, r), alive) for r in store.run_ids(project_id, build_id)]


# ------------------------------------------------------------------------------------------------ records the API writes
def base_record(rv: RunView) -> dict[str, Any]:
    """The run's JobRecord as the worker left it, or one made from spec.json and launch.json when it wrote none."""
    if rv.job is not None:
        return dict(rv.job)
    queued = (rv.launch or {}).get('launchedAt') or mtime_iso(rv.dir / 'spec.json') or iso_utc()
    return {'format': 'job/1', 'kind': rv.kind, 'runId': rv.id, 'status': 'queued',
            'pid': (rv.launch or {}).get('pid'), 'procStart': (rv.launch or {}).get('procStart'), 'queuedAt': queued,
            'startedAt': None, 'finishedAt': None, 'step': None, 'progress': 0.0, 'steps': [], 'messages': [],
            'error': None, 'outputs': {}}


def ended_record(rv: RunView, status: str, code: str, text: str, level: str = 'error') -> dict[str, Any]:
    """The run's record ended by the API: `status`, error {code, text, the step it was on}, a closing message."""
    record = base_record(rv)
    now = iso_utc()
    steps = [dict(s, status='failed' if s.get('status') == 'running' else s.get('status')) for s in record['steps']]
    messages = [*record['messages'], {'at': now, 'level': level, 'text': text}][-MESSAGES_KEPT:]
    record.update(status=status, finishedAt=now, steps=steps, messages=messages,
                  error={'code': code, 'message': text, 'step': record.get('step')})
    return record


def mark_interrupted(rv: RunView) -> None:
    write_record(rv.dir / 'job.json', JobRecord, ended_record(rv, 'interrupted', 'interrupted', INTERRUPTED_TEXT))


def mark_cancelled(run_dir: Path, alive: Alive) -> None:
    rv = read_run(run_dir, alive)
    write_record(run_dir / 'job.json', JobRecord, ended_record(rv, 'cancelled', 'cancelled', CANCELLED_TEXT, 'warn'))


def mark_invalid(rv: RunView, issues: list[str]) -> None:
    first = issues[0] if issues else 'an output is missing'
    text = (f'The builder\'s outputs did not pass the checks ({len(issues)} issue{"s" if len(issues) != 1 else ""}; the '
            f'first: {first}). Build again; if it happens again, the drawing needs a look.')
    record = ended_record(rv, 'failed', 'invalid_output', text)
    record['error']['step'] = 'validate'
    write_record(rv.dir / 'job.json', JobRecord, record)


def api_record(validated: bool | None, issues: list[str], adopted: int | None) -> dict[str, Any]:
    return {'format': 'run-api/1', 'validated': validated, 'issues': issues[:200], 'adoptedRevision': adopted,
            'at': iso_utc()}


# ------------------------------------------------------------------------------------------------ RunInfo
def run_info(rv: RunView) -> RunInfo:
    record = base_record(rv)
    error = record.get('error')
    if rv.status == 'interrupted' and rv.gone:
        error = {'code': 'interrupted', 'message': INTERRUPTED_TEXT, 'step': record.get('step')}
    if rv.job_broken and rv.status == 'running':
        error = None
    return RunInfo(
        id=rv.id, kind=rv.kind, status=rv.status, step=record.get('step'), progress=float(record.get('progress') or 0.0),
        steps=record['steps'], messages=record['messages'][-MESSAGES_SHOWN:], error=error,
        queued_at=record['queuedAt'], started_at=record.get('startedAt'),
        finished_at=record.get('finishedAt') if rv.status in FINISHED else None,
        cancel_requested=rv.cancel and rv.status in IN_PROGRESS, only=rv.only)


def now_utc() -> datetime:
    return datetime.now(UTC)
