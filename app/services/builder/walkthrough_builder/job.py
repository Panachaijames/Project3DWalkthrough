"""The worker: one run (prepare or build) of a build, as its own process (docs/upload/DESIGN.md U-3, U-4.2, U-6).

    python -B -P -m walkthrough_builder.job --run <run dir>

It reads `spec.json` (JobSpec), writes `job.json` (JobRecord) atomically after every status or step change and progress
at most twice a second (`pid` / `procStart` as runio.worker_identity gives them), and `log.txt` with every child's
stdout and stderr. The API reads job.json; nothing else passes between them (U-3.2).

* **Queue:** status `queued` while it waits for the machine lock (`oslock`, `WALKTHROUGH_RUN_LOCK`); holding it, it
  evicts the cache above `WALKTHROUGH_CACHE_MAX_GB` (never the run's own sources) and removes stale staging folders.
* **Steps (U-3.1):** prepare: per source `convert:i` (DWG: dwg2dxf), `check:i` (DWG: the loss check, and beside it in a
  second Job Object the ezdxf audit that completes the conversion's success rule; then the conversion is committed to
  the cache), `read:i` (U2's read_source into a staging folder renamed to read-<rv>-<used>), then `suggest` (U2's
  `suggest` and `propose_settings`, in one child) -> `out/sources/<sha1>/{conversion.json, drawing.json, plan.json.gz}`,
  `out/suggestions.json`, `out/proposed-settings.json`. A prepare with `spec.only` reads only those sources (their
  conversion a cache hit) and skips `suggest`. Build: `ensure` (re-converts and re-reads whatever the cache lacks for
  the settings' units), the BuildContext (contracts.py), one child running U3's `build` and U4's `write_outputs`
  (its `progress()` drives `align`, `detect:<floor>`, `walls`, `openings`, `furniture`, `outputs`), then `validate`
  (every output there, the model with floors and parts, the `.ms` stamp, the PNG, and every record through the API's
  `check_file` in the API's own Python when it is installed).
* **Children** (step.py, dwg2dxf, dwgread) run in Job Objects (isolate.py) with `JobSpec.limits`; their working folders
  are fresh folders under `out/tmp/`, removed at the end.
* **Stopping (U-3.4):** the `cancel` file, a missing `spec.json` or run folder, and the wall clock
  (`JobSpec.wallClockSeconds`, queue time included) are checked between steps, about twice a second while a child runs
  and while queued. Cancel: the child's job is ended, out/tmp removed, and `cancelled` is the LAST thing written. A
  missing spec or the wall clock: `interrupted` (when the folder is still there). A missing run folder: nothing more is
  written; the worker exits and frees the lock.
* **job.json on Windows (U-3.2):** jsonfile.write retries the replace while the API has the file open; a write that
  still fails is logged and written again at the next change, and never stops the worker.
* **Messages** are plain sentences naming files by their upload names (absolute paths are scrubbed out); the full
  detail goes to log.txt (never served).

Owner: U1.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import shutil
import sys
import threading
import time
import traceback
from pathlib import Path

from . import cache, convert, isolate, jsonfile, losscheck, oslock, runio

DEFAULT_LIMITS = {'convert': {'seconds': 120.0, 'memoryMB': 2048}, 'check': {'seconds': 180.0, 'memoryMB': 1024},
                  'read': {'seconds': 300.0, 'memoryMB': 4096}, 'build': {'seconds': 900.0, 'memoryMB': 4096}}
API_CHECK_LIMIT = {'seconds': 300.0, 'memoryMB': 2048}
DEFAULT_WALL_CLOCK_S = 3600.0
PROGRESS_EVERY_S = 0.5
STOP_EVERY_S = 0.4
FINAL_WRITE_S = 60.0
MESSAGES_KEPT = 200
APP = Path(__file__).resolve().parents[3]
API_PYTHON_ENV = 'WALKTHROUGH_API_PYTHON'

#: the build's outputs (U-3.1) besides `<maxFileName>`, and the check_file kind of each JSON record
BUILD_OUTPUTS = ('model.json', 'stages.json', 'presentation.json', 'report.json', 'overlay.json', 'diff.json',
                 'openings.json', 'pieces.json', 'topview.png', 'inputs.json')
CHECK_KIND = {'model.json': 'model', 'stages.json': 'stages', 'presentation.json': 'presentation',
              'overlay.json': 'overlay', 'diff.json': 'diff', 'openings.json': 'openings', 'pieces.json': 'pieces',
              'inputs.json': 'inputs'}
#: the steps the build child drives through progress() (U-3.1)
CHILD_STEPS_FIXED = ('align', 'walls', 'openings', 'furniture', 'outputs')
EXIT = {'done': 0, 'failed': 1, 'usage': 2, 'cancelled': 3, 'interrupted': 4, 'gone': 5}

_API_CHECK = r'''
import json, sys
from walkthrough_api.check_file import issues
req = json.load(open(sys.argv[1], encoding='utf-8'))
model = open(req['model'], 'rb').read() if req.get('model') else None
out = {}
for f in req['files']:
    try:
        data = open(f['path'], 'rb').read()
        out[f['name']] = issues(f['kind'], data, model if f['kind'] in ('stages', 'presentation') else None)
    except Exception as exc:
        out[f['name']] = ['could not be checked: %s: %s' % (type(exc).__name__, exc)]
with open(req['result'], 'w', encoding='utf-8') as fh:
    json.dump(out, fh, ensure_ascii=False)
'''


class Stop(Exception):
    """The run must stop: reason 'cancel', 'spec', 'wallclock' or 'gone'."""

    def __init__(self, reason: str) -> None:
        super().__init__(reason)
        self.reason = reason


class RunError(Exception):
    """A failure with its RunErrorCode and a plain sentence for the staff member."""

    def __init__(self, code: str, message: str, step: str | None = None) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.step = step


class ChildFailed(Exception):
    def __init__(self, code: str, detail: str, res: dict) -> None:
        super().__init__(detail)
        self.code = code
        self.detail = detail
        self.res = res


def _sha1_bytes(b: bytes) -> str:
    return hashlib.sha1(b).hexdigest()


def _safe(name: str) -> str:
    return re.sub(r'[^A-Za-z0-9_.-]+', '-', name)[:40]


def _limit(spec: dict, key: str) -> dict:
    got = ((spec.get('limits') or {}).get(key)) or {}
    d = DEFAULT_LIMITS[key]
    try:
        return {'seconds': float(got.get('seconds') or d['seconds']), 'memoryMB': int(got.get('memoryMB') or d['memoryMB'])}
    except (TypeError, ValueError):
        return dict(d)


def plan_steps(spec: dict) -> list[dict]:
    """The JobRecord.steps of a run (U-3.1), all `waiting`, each with its weight for the progress bar."""
    steps: list[tuple[str, str, float]] = []
    sources = spec.get('sources') or []
    if spec.get('kind') == 'prepare':
        only = spec.get('only')
        for i, s in enumerate(sources):
            if only is not None and s['sha1'] not in only:
                continue
            if only is None and s.get('kind') == 'dwg':
                steps += [(f'convert:{i}', f'Converting {s["name"]}', 1.0),
                          (f'check:{i}', f'Checking the conversion of {s["name"]}', 1.5)]
            steps.append((f'read:{i}', f'Reading {s["name"]}', 3.0))
        if only is None:
            steps.append(('suggest', 'Suggesting layer roles', 0.5))
    else:
        floors = ((spec.get('settings') or {}).get('floors')) or []
        steps.append(('ensure', 'Checking the readings', 0.5))
        steps.append(('align', 'Lining up the floors', 0.3))
        for f in floors:
            steps.append((f'detect:{f["key"]}', f'Finding doors and windows on {f.get("name") or f["key"]}', 1.0))
        steps += [('walls', 'Building walls and glass', 1.5), ('openings', 'Cutting the openings', 1.0),
                  ('furniture', 'Placing the furniture boxes', 0.7), ('outputs', 'Writing the outputs', 1.5),
                  ('validate', 'Checking the outputs', 0.5)]
    return [{'name': n, 'label': lab, 'status': 'waiting', 'seconds': None, 'note': '', '_w': w}
            for n, lab, w in steps]


class Run:
    def __init__(self, run_dir: Path) -> None:
        self.dir = Path(run_dir)
        self.spec_path = self.dir / 'spec.json'
        self.cancel_path = self.dir / 'cancel'
        self.log_path = self.dir / 'log.txt'
        self.t0 = time.monotonic()
        self.spec: dict = {}
        self.rec: dict = {}
        self.steps: list[dict] = []
        self.by_name: dict[str, dict] = {}
        self.cur: str | None = None
        self.frac = 0.0
        self.step_t: dict[str, float] = {}
        self.wall = DEFAULT_WALL_CLOCK_S
        self._stop: str | None = None
        self._stop_checked = 0.0
        self._last_write = 0.0
        self._dirty = False
        self._final = False
        self.events_path: Path | None = None
        self.events_pos = 0
        self.child_steps: set[str] = set()
        self.reported: set[str] = set()
        self.src: dict[str, dict] = {}
        self.out = self.dir / 'out'
        self.tmp = self.out / 'tmp'

    # ------------------------------------------------------------------------------------------------ log and record
    def log(self, text: str) -> None:
        try:
            with open(self.log_path, 'a', encoding='utf-8', newline='\n') as f:
                f.write(f'{runio.now()} {text}\n')
        except OSError:
            pass

    def append_child_log(self, title: str, res: dict | None, files: list[Path]) -> None:
        parts = [f'{runio.now()} ==== {title}' + (
            f': exit {res.get("raw_exit_code")}, {res.get("seconds")} s, peak {res.get("peak_mb")} MB'
            f'{", timed out" if res.get("timed_out") else ""}{", cancelled" if res.get("cancelled") else ""}'
            f'{", memory limit" if res.get("memory_hit") else ""}' if res else '')]
        for f in files:
            try:
                text = f.read_text(encoding='utf-8', errors='replace')
            except OSError:
                continue
            if text.strip():
                parts.append(f'---- {f.name}\n{text.rstrip()}')
        try:
            with open(self.log_path, 'a', encoding='utf-8', newline='\n') as fh:
                fh.write('\n'.join(parts) + '\n')
        except OSError:
            pass

    def message(self, text: str, level: str = 'info') -> None:
        msgs = self.rec.setdefault('messages', [])
        msgs.append({'at': runio.now(), 'level': level, 'text': losscheck.scrub(str(text))[:500]})
        del msgs[:-MESSAGES_KEPT]

    def _public(self) -> dict:
        rec = dict(self.rec)
        rec['steps'] = [{k: v for k, v in s.items() if not k.startswith('_')} for s in self.steps]
        return rec

    def save(self, *, timeout: float = jsonfile.RETRY_S) -> None:
        """Writes job.json now; a failure is logged and retried at the next change (never stops the worker)."""
        if self._final or self._stop == 'gone':
            return
        self._last_write = time.monotonic()
        try:
            runio.write_job(self.dir, self._public(), timeout=timeout)
            self._dirty = False
        except (OSError, ValueError) as exc:
            self._dirty = True
            self.log(f'job.json could not be written ({type(exc).__name__}: {exc}); written again at the next change')

    def save_progress(self) -> None:
        if time.monotonic() - self._last_write >= PROGRESS_EVERY_S:
            self.save(timeout=1.0)

    def update_progress(self) -> None:
        total = sum(s['_w'] for s in self.steps) or 1.0
        done = sum(s['_w'] for s in self.steps if s['status'] in ('done', 'skipped'))
        cur = self.by_name[self.cur]['_w'] * self.frac if self.cur in self.by_name else 0.0
        self.rec['progress'] = round(min(1.0, (done + cur) / total), 3)

    # ------------------------------------------------------------------------------------------------------- steps
    def step_start(self, name: str, note: str = '') -> None:
        st = self.by_name[name]
        st['status'] = 'running'
        st['note'] = note
        self.cur, self.frac = name, 0.0
        self.step_t[name] = time.monotonic()
        self.rec['step'] = name
        self.update_progress()
        self.save()

    def step_done(self, name: str, note: str | None = None, seconds: float | None = None) -> None:
        st = self.by_name[name]
        st['status'] = 'done'
        if seconds is None and name in self.step_t:
            seconds = time.monotonic() - self.step_t[name]
        st['seconds'] = None if seconds is None else round(float(seconds), 2)
        if note is not None:
            st['note'] = note
        if self.cur == name:
            self.cur, self.frac = None, 0.0
        self.update_progress()
        self.save()

    def set_fraction(self, f: float) -> None:
        self.frac = max(0.0, min(1.0, f))
        self.update_progress()
        self.save_progress()

    # -------------------------------------------------------------------------------------------------------- stop
    def stop_reason(self) -> str | None:
        """Why the run must stop now, or None (sticky once set; the files are looked at about twice a second)."""
        if self._stop is not None:
            return self._stop
        now = time.monotonic()
        if now - self._stop_checked < STOP_EVERY_S:
            return None
        self._stop_checked = now
        if not self.dir.is_dir():
            self._stop = 'gone'
        elif not self.spec_path.is_file():
            self._stop = 'spec'
        elif self.cancel_path.exists():
            self._stop = 'cancel'
        elif now - self.t0 > self.wall:
            self._stop = 'wallclock'
        return self._stop

    def check_stop(self) -> None:
        self._stop_checked = 0.0
        r = self.stop_reason()
        if r:
            raise Stop(r)

    def on_poll(self) -> None:
        self.drain_events()
        if self._dirty and time.monotonic() - self._last_write > 1.0:
            self.save(timeout=1.0)
        else:
            self.save_progress()

    # ------------------------------------------------------------------------------------------------------ children
    def fresh(self, path: Path) -> Path:
        if path.exists():
            shutil.rmtree(path, ignore_errors=True)
        path.mkdir(parents=True)
        return path

    def drain_events(self) -> None:
        p = self.events_path
        if p is None:
            return
        try:
            with open(p, 'rb') as f:
                f.seek(self.events_pos)
                data = f.read()
        except OSError:
            return
        end = data.rfind(b'\n')
        if end < 0:
            return
        self.events_pos += end + 1
        for line in data[:end + 1].splitlines():
            try:
                ev = json.loads(line)
            except ValueError:
                continue
            if not isinstance(ev, dict):
                continue
            if ev.get('t') == 'log' and isinstance(ev.get('text'), str):
                self.message(ev['text'], ev.get('level') if ev.get('level') in ('info', 'warn', 'error') else 'info')
            elif ev.get('t') == 'progress' and isinstance(ev.get('step'), str):
                self.on_child_progress(ev['step'], ev.get('f'))

    def on_child_progress(self, name: str, f) -> None:
        try:
            f = float(f)
        except (TypeError, ValueError):
            f = 0.0
        if name in self.child_steps and name in self.by_name:
            self.reported.add(name)
            if name != self.cur:
                if self.cur in self.child_steps and self.by_name[self.cur]['status'] == 'running':
                    self.step_done(self.cur)
                if self.by_name[name]['status'] == 'waiting':
                    self.step_start(name)
            self.set_fraction(f)
        elif name == self.cur:
            self.set_fraction(f)

    def child_env(self, **extra: str) -> dict:
        return isolate.child_env(**extra)

    def run_step(self, kind: str, args: dict, work: Path, limit: dict, *, cancelled, poll,
                 env_extra: dict | None = None) -> tuple[dict, dict]:
        """`step.py <kind>` in a Job Object in `work` -> (isolate result, the step's result.json or {})."""
        args = dict(args, events=str(work / 'events.jsonl'), result=str(work / 'result.json'))
        jsonfile.write(work / 'args.json', args)
        cmd = [sys.executable, '-B', '-P', '-m', 'walkthrough_builder.step', kind, str(work / 'args.json')]
        res = isolate.run(cmd, cwd=work, env=self.child_env(**(env_extra or {})), seconds=limit['seconds'],
                          memory_mb=limit['memoryMB'], stdout=work / 'stdout.txt', stderr=work / 'stderr.txt',
                          cancelled=cancelled, poll=poll)
        try:
            result = jsonfile.read(work / 'result.json')
        except (OSError, ValueError):
            result = {}
        return res, result

    @staticmethod
    def failure(res: dict, result: dict, prefix: str, work: Path) -> tuple[str, str] | None:
        """(code, detail) of a finished step child that failed, else None (U-3.5's classification; a step's own
        RunErrorCode kept)."""
        code = isolate.classify(res, prefix)
        if code is None and result.get('ok'):
            return None
        if code is None or (code == f'{prefix}_failed' and result.get('code')):
            code = result.get('code') or f'{prefix}_failed'
        detail = losscheck.scrub(str(result.get('message') or '')).strip()
        if not detail:
            err = work / 'stderr.txt'
            tail = [ln for ln in err.read_text(encoding='utf-8', errors='replace').splitlines()
                    if ln.strip()] if err.exists() else []
            detail = losscheck.scrub(tail[-1].strip()) if tail else f'it stopped with exit code {res["raw_exit_code"]}'
        return code, detail[:300]

    def child(self, kind: str, args: dict, *, step: str, limit: dict, prefix: str, env_extra: dict | None = None,
              child_steps: set[str] | None = None) -> dict:
        """Runs `step.py <kind>` in a Job Object; returns its result (ok) or raises ChildFailed(code, detail) / Stop."""
        work = self.fresh(self.tmp / f'{kind}-{_safe(step)}')
        self.events_path, self.events_pos = work / 'events.jsonl', 0
        self.child_steps = child_steps or set()
        try:
            res, result = self.run_step(kind, args, work, limit, cancelled=self.stop_reason, poll=self.on_poll,
                                        env_extra=env_extra)
        except isolate.IsolateError as exc:
            raise RunError('internal', f'A step could not be started: {exc}.', step) from exc
        finally:
            self.drain_events()
            self.events_path, self.child_steps = None, set()
        self.append_child_log(f'{kind} ({step})', res, [work / 'stdout.txt', work / 'stderr.txt'])
        if res['cancelled']:
            raise Stop(self._stop or 'cancel')
        failed = self.failure(res, result, prefix, work)
        if failed is None:
            return result
        raise ChildFailed(failed[0], failed[1], res)

    # --------------------------------------------------------------------------------------------------- the run
    def main(self) -> int:
        if not self.dir.is_dir():
            print(f'job: no run folder {self.dir}', file=sys.stderr)
            return EXIT['usage']
        try:
            self.spec = jsonfile.read(self.spec_path)
            if self.spec.get('kind') not in ('prepare', 'build') or not isinstance(self.spec.get('sources'), list):
                raise ValueError('kind or sources missing')
        except FileNotFoundError:
            print('job: no spec.json', file=sys.stderr)
            return EXIT['usage']
        except (OSError, ValueError, KeyError, TypeError) as exc:
            self.log(f'spec.json could not be read: {exc}')
            self.spec = self.spec if isinstance(self.spec, dict) else {}
            self.steps = []
            pid, ps = runio.worker_identity()
            self.rec = runio.new_record(self.spec.get('kind') if self.spec.get('kind') in ('prepare', 'build')
                                        else 'prepare', str(self.spec.get('runId') or self.dir.name), [], pid=pid,
                                        proc=ps)
            return self.finish('failed', {'code': 'internal', 'message': "The run's spec.json could not be read.",
                                          'step': None})
        try:
            self.wall = float(self.spec.get('wallClockSeconds') or DEFAULT_WALL_CLOCK_S)
        except (TypeError, ValueError):
            self.wall = DEFAULT_WALL_CLOCK_S
        out = (self.spec.get('paths') or {}).get('out')
        self.out = Path(out) if out else self.dir / 'out'
        self.tmp = self.out / 'tmp'
        self.steps = plan_steps(self.spec)
        self.by_name = {s['name']: s for s in self.steps}
        pid, ps = runio.worker_identity()
        self.rec = runio.new_record(self.spec['kind'], str(self.spec.get('runId') or self.dir.name), [], pid=pid,
                                    proc=ps)
        self.log(f'worker {os.getpid()} (reported pid {pid}) for {self.spec["kind"]} run {self.rec["runId"]}')
        self.save()
        waited = {'said': False}

        def on_wait(secs: float) -> None:
            if not waited['said']:
                waited['said'] = True
                self.message('Waiting: another build is running on this computer.')
                self.save()

        try:
            with oslock.hold(wait=on_wait, cancelled=lambda: self.stop_reason() is not None):
                return self.run_locked()
        except oslock.LockCancelled:
            return self.stopped(self._stop or 'cancel')
        except Stop as s:                                   # only reached when the lock was never taken
            return self.stopped(s.reason)

    def run_locked(self) -> int:
        try:
            self.check_stop()
            self.rec['status'] = 'running'
            self.rec['startedAt'] = runio.now()
            self.message('Started.')
            self.save()
            self.check_paths()
            self.fresh(self.tmp)
            self.housekeeping()
            if self.spec['kind'] == 'prepare':
                self.do_prepare()
            else:
                self.do_build()
            self.check_stop()
            self.rec['outputs'] = self.collect_outputs()
            return self.finish('done')
        except Stop as s:
            return self.stopped(s.reason)
        except RunError as e:
            self.log(f'failed: {e.code}: {e.message}')
            return self.finish('failed', {'code': e.code, 'message': e.message, 'step': e.step or self.cur})
        except Exception as exc:                            # noqa: BLE001 - every failure ends the run cleanly
            self.log('internal error:\n' + traceback.format_exc())
            if self._stop:
                return self.stopped(self._stop)
            return self.finish('failed', {'code': 'internal',
                                          'message': f'Something went wrong in the worker: '
                                                     f'{losscheck.scrub(f"{type(exc).__name__}: {exc}")[:250]}.',
                                          'step': self.cur})

    def stopped(self, reason: str) -> int:
        if reason == 'gone' or not self.dir.is_dir():
            self._stop = 'gone'
            self.cleanup()
            return EXIT['gone']
        if reason == 'cancel':
            return self.finish('cancelled', {'code': 'cancelled', 'message': 'The run was cancelled.',
                                             'step': self.cur})
        if reason == 'wallclock':
            msg = (f'The run took longer than {self.wall / 60:.0f} minutes, waiting time included, and was '
                   f'stopped.')
        else:
            msg = "The run was stopped: its files were removed."
        return self.finish('interrupted', {'code': 'interrupted', 'message': msg, 'step': self.cur})

    def cleanup(self) -> None:
        if self.tmp.exists():
            shutil.rmtree(self.tmp, ignore_errors=True)
            if self.tmp.exists():
                time.sleep(0.3)
                shutil.rmtree(self.tmp, ignore_errors=True)

    def finish(self, status: str, error: dict | None = None) -> int:
        """Cleans up, then writes the final job.json (retried; nothing is written after it). Returns the exit code."""
        self.cleanup()
        for st in self.steps:
            if st['status'] == 'running':
                st['status'] = {'done': 'done', 'failed': 'failed'}.get(status, 'skipped')
                if st['name'] in self.step_t:
                    st['seconds'] = round(time.monotonic() - self.step_t[st['name']], 2)
                if status in ('cancelled', 'interrupted'):
                    st['note'] = 'stopped'
            elif st['status'] == 'waiting':
                st['status'] = 'done' if status == 'done' else 'skipped'
        if error and error.get('step') in self.by_name and status == 'failed':
            self.by_name[error['step']]['status'] = 'failed'
        self.rec['status'] = status
        self.rec['finishedAt'] = runio.now()
        self.rec['error'] = error
        if status == 'done':
            self.rec['progress'] = 1.0
            self.message('Done.')
        elif error:
            self.message(error['message'], 'error' if status == 'failed' else 'warn')
        self.log(f'finished: {status}' + (f' ({error["code"]}: {error["message"]})' if error else ''))
        self.final_write()
        return EXIT.get(status, 1)

    def final_write(self) -> None:
        deadline = time.monotonic() + FINAL_WRITE_S
        while True:
            if not self.dir.is_dir():
                break
            try:
                runio.write_job(self.dir, self._public())
                break
            except (OSError, ValueError) as exc:
                self.log(f'the final job.json could not be written yet ({type(exc).__name__}): trying again')
                if time.monotonic() > deadline:
                    break
                time.sleep(0.5)
        self._final = True

    # ---------------------------------------------------------------------------------------------- housekeeping
    def check_paths(self) -> None:
        """U-4.1: every path the run writes stays under Windows' 260 characters, else a plain message at once."""
        try:
            runio.check_path(self.dir / 'job.json')
            runio.check_path(self.out / 'sources' / ('0' * 40) / 'conversion.json')
            ms = ((self.spec.get('settings') or {}).get('project') or {}).get('maxFileName')
            if ms:
                runio.check_path(self.out / str(ms))
            runio.check_path(self.tmp / 'build' / 'proposed-settings.json')
        except OSError as exc:
            raise RunError('internal', f'{str(exc)[0].upper()}{str(exc)[1:]}.') from exc

    def cache_root(self) -> Path:
        c = (self.spec.get('paths') or {}).get('cache')
        root = Path(c) if c else cache.cache_root()
        root.mkdir(parents=True, exist_ok=True)
        return root

    def housekeeping(self) -> None:
        """Holding the machine lock: the cache under its cap, stale staging folders gone (U-4.2)."""
        root = self.cache_root()
        keep = {s['sha1'] for s in self.spec.get('sources') or []}
        stale = cache.clean_stale(root)
        removed = cache.evict(root, keep, cache.max_gb())
        if stale:
            self.log(f'removed stale cache folders: {stale}')
        if removed:
            self.log(f'evicted from the cache: {removed}')
            self.message(f'Freed space in the drawing cache ({len(removed)} older drawing'
                         f'{"s" if len(removed) != 1 else ""}).')

    def libredwg(self) -> Path:
        p = (self.spec.get('paths') or {}).get('libredwg')
        return Path(p) if p else APP / 'vendor' / 'libredwg-0.14-win64'

    def converter(self) -> dict:
        info = self.src.get('_converter')
        if info is None:
            try:
                info = convert.converter_info(self.libredwg())
            except OSError as exc:
                raise RunError('convert_failed', f'The converter is not installed where the settings say ({exc}).')
            self.src['_converter'] = info
        return info

    def collect_outputs(self) -> dict:
        outs = {}
        if not self.out.is_dir():
            return outs
        for p in sorted(self.out.rglob('*')):
            if not p.is_file():
                continue
            rel = p.relative_to(self.out).as_posix()
            if rel.startswith('tmp/') or rel == 'tmp':
                continue
            outs[rel] = {'bytes': p.stat().st_size, 'sha1': cache.sha1_file(p)}
        return outs

    # ------------------------------------------------------------------------------------------------ the sources
    def state(self, s: dict) -> dict:
        return self.src.setdefault(s['sha1'], {})

    def source_info(self, s: dict) -> dict:
        st = self.state(s)
        try:
            size = os.path.getsize(s['path'])
        except OSError as exc:
            raise RunError('read_failed', f'The uploaded file {s["name"]} is missing from the project.') from exc
        return {'sha1': s['sha1'], 'name': s['name'], 'bytes': size, 'kind': s['kind'],
                'formatVersion': st.get('formatVersion')}

    def write_out(self, rel: str, obj) -> Path:
        p = self.out / rel
        runio.check_path(p)
        jsonfile.write(p, obj)
        return p

    def do_convert(self, i: int, s: dict, step: str, *, publish_failure: bool) -> None:
        """dwg2dxf and the ezdxf audit of its DXF, in out/tmp/convert-<i>/ (U-6.2)."""
        st = self.state(s)
        name = s['name']
        try:
            st['formatVersion'] = convert.check_header(Path(s['path']))
        except convert.HeaderError as exc:
            st['formatVersion'] = exc.version
            msg = (f'{name} is {exc}: save it as a newer DWG, or export a DXF.' if exc.code == 'unsupported_version'
                   else f'{name} is {exc}.')
            if publish_failure:
                self.write_out(f'sources/{s["sha1"]}/conversion.json', losscheck.failed_report(
                    self.source_info(s), self.converter(), {}, [], msg))
            raise RunError(exc.code, msg, step) from exc
        except OSError as exc:
            raise RunError('convert_failed', f'The uploaded file {name} cannot be opened.', step) from exc
        work = self.fresh(self.tmp / f'convert-{i}')
        shutil.copyfile(s['path'], work / 'input.dwg')
        lim = _limit(self.spec, 'convert')
        self.message(f'Converting {name}.')
        res = convert.convert(work / 'input.dwg', work, libredwg=self.libredwg(), seconds=lim['seconds'],
                              memory_mb=lim['memoryMB'], cancelled=self.stop_reason, poll=self.on_poll,
                              env=self.child_env())
        self.append_child_log(f'dwg2dxf ({step})', res['run'], [work / 'convert.log'])
        if res['code'] == 'cancelled':
            raise Stop(self._stop or 'cancel')
        if res['code']:
            msg = f'{name} could not be converted: {res["detail"]}. Export a DXF from AutoCAD and upload it instead.'
            if publish_failure:
                self.write_out(f'sources/{s["sha1"]}/conversion.json', losscheck.failed_report(
                    self.source_info(s), self.converter(), res, losscheck.read_log(work / 'convert.log'), msg))
            raise RunError(res['code'], msg, step)
        st.update(work=work, convert=res, convertStep=step, publishFailure=publish_failure)
        self.message(f'Converted {name} in {res["seconds"]:.1f} s.')

    def do_check(self, i: int, s: dict, step: str) -> None:
        """The loss check (U-6.3) in a child and, at the same time in a second Job Object, the last part of the
        conversion's success rule: ezdxf.recover opens the DXF (its audit counts go into the report). Then the
        conversion is committed to the cache."""
        st = self.state(s)
        work, res = st['work'], st['convert']
        name = s['name']
        args = {'dwg': str(work / 'input.dwg'), 'dxf': str(work / 'plan.dxf'), 'log': str(work / 'convert.log'),
                'libredwg': str(self.libredwg()), 'source': self.source_info(s), 'converter': self.converter(),
                'convert': {'seconds': res['seconds'], 'peak_mb': res['peak_mb'], 'exit_code': res['exit_code']},
                'audit': {}, 'report': str(work / 'conversion.json'),
                'dwgread_stderr': str(work / 'dwgread.err.txt')}
        audit_work = self.fresh(self.tmp / f'audit-{i}')
        abort = threading.Event()
        box: dict = {}

        def audit() -> None:
            try:
                box['res'] = self.run_step('audit', {'dxf': str(work / 'plan.dxf')}, audit_work,
                                           _limit(self.spec, 'read'), poll=None,
                                           cancelled=lambda: abort.is_set() or self._stop is not None)
            except BaseException as exc:                    # noqa: BLE001 - reported by the main thread
                box['exc'] = exc

        thread = threading.Thread(target=audit, name=f'audit-{i}', daemon=True)
        thread.start()
        try:
            try:
                self.child('check', args, step=step, limit=_limit(self.spec, 'check'), prefix='check')
            except ChildFailed as exc:
                why = {'check_timeout': 'it took too long',
                       'check_memory': 'it needed too much memory'}.get(exc.code, exc.detail)
                raise RunError('check_failed', f'The conversion of {name} could not be checked: {why}.',
                               step) from exc
            finally:
                if (work / 'dwgread.err.txt').exists():
                    self.append_child_log(f'dwgread ({step})', None, [work / 'dwgread.err.txt'])
            while thread.is_alive():
                thread.join(0.25)
                self.on_poll()
                self.stop_reason()
        finally:
            abort.set()
            thread.join()
        if 'exc' in box:
            raise RunError('internal', f'The converted drawing could not be opened: {box["exc"]}.', step)
        ares, aresult = box['res']
        self.append_child_log(f'audit ({step})', ares, [audit_work / 'stdout.txt', audit_work / 'stderr.txt'])
        if ares['cancelled']:
            raise Stop(self._stop or 'cancel')
        failed = self.failure(ares, aresult, 'convert', audit_work)
        if failed is not None:
            code = failed[0] if failed[0] in ('convert_timeout', 'convert_memory') else 'convert_failed'
            msg = f'{name} was converted, but the converted drawing cannot be opened ({failed[1]}).'
            if st.get('publishFailure'):
                self.write_out(f'sources/{s["sha1"]}/conversion.json', losscheck.failed_report(
                    self.source_info(s), self.converter(), res, losscheck.read_log(work / 'convert.log'), msg))
            raise RunError(code, msg, st.get('convertStep') or step)
        rep = jsonfile.read(work / 'conversion.json')
        aud = aresult.get('audit') or {}
        rep['dxf'].update(acadVersion=aud.get('acadVersion') or rep['dxf'].get('acadVersion'),
                          insUnits=aud['insUnits'] if aud.get('insUnits') is not None else rep['dxf'].get('insUnits'),
                          auditErrors=int(aud.get('auditErrors') or 0), auditFixes=int(aud.get('auditFixes') or 0))
        jsonfile.write(work / 'conversion.json', rep)
        st['conv'] = cache.commit_conversion(self.cache_root(), s['sha1'], self.conv_folder(), {
            'plan.dxf': work / 'plan.dxf', 'convert.log': work / 'convert.log',
            'conversion.json': work / 'conversion.json'}, self.rec['runId'])
        st['report'] = rep
        t = rep['totals']
        self.message(f'Conversion of {s["name"]}: {rep["verdict"]}' + (
            f' ({t["missing"]:,} of {t["dwgEntities"]:,} items did not come through).' if t['missing'] else '.'),
            'warn' if rep['verdict'] == 'loss' else 'info')

    def conv_folder(self) -> str:
        return cache.converter_folder(self.converter()['version'])

    def cached_conversion(self, s: dict) -> Path | None:
        st = self.state(s)
        if st.get('conv'):
            return st['conv']
        d = cache.conversion_entry(self.cache_root(), s['sha1'], self.conv_folder())
        if d is not None:
            st['conv'] = d
            st['report'] = jsonfile.read(d / 'conversion.json')
        return d

    def ensure_dxf(self, i: int, s: dict, step: str) -> Path:
        """The DXF to read: the upload itself, the cached conversion, or a new conversion (checked) when the cache was
        cleared."""
        if s['kind'] == 'dxf':
            return Path(s['path'])
        d = self.cached_conversion(s)
        if d is None:
            self.message(f'{s["name"]} is converted again (the drawing cache no longer had it).')
            self.do_convert(i, s, step, publish_failure=False)
            self.do_check(i, s, step)
            d = self.state(s)['conv']
        return d / 'plan.dxf'

    def ensure_read(self, i: int, s: dict, units: str | None, step: str) -> Path:
        """The cache's read folder of `s` in `units` (None: what the reader chooses), reading it when missing.
        `state(s)['readHit']` says whether it was a cache hit."""
        st = self.state(s)
        root = self.cache_root()
        hit = cache.read_entry(root, s['sha1'], units)
        st['readHit'] = hit is not None
        if hit is not None:
            st['read'] = hit
            return hit
        dxf = self.ensure_dxf(i, s, step)
        staging = cache.read_staging(root, s['sha1'], self.rec['runId'])
        self.message(f'Reading {s["name"]}' + (f' in {units}.' if units else '.'))
        try:
            res = self.child('read', {'dxf': str(dxf), 'units': units, 'out_dir': str(staging),
                                      'source': {'sha1': s['sha1'], 'name': s['name']}},
                             step=step, limit=_limit(self.spec, 'read'), prefix='read')
        except ChildFailed as exc:
            shutil.rmtree(staging, ignore_errors=True)
            lim = _limit(self.spec, 'read')
            msg = {'read_timeout': f'Reading {s["name"]} took longer than {lim["seconds"]:.0f} s and was stopped.',
                   'read_memory': f'Reading {s["name"]} needed more than {lim["memoryMB"]:,} MB and was stopped.'}.get(
                exc.code, f'{s["name"]} could not be read: {exc.detail}.')
            raise RunError(exc.code, msg, step) from exc
        used = ((res.get('read') or {}).get('units') or {}).get('used')
        if used not in cache.UNITS:
            try:
                used = jsonfile.read(staging / 'drawing.json')['units']['used']
            except (OSError, ValueError, KeyError, TypeError):
                used = None
        if used not in cache.UNITS:
            raise RunError('read_failed', f'{s["name"]} was read, but the reader named no units.', step)
        try:
            d = cache.commit_read(root, s['sha1'], staging, used, auto=units is None)
        except FileNotFoundError as exc:
            raise RunError('read_failed', f'{s["name"]} was read, but {exc}.', step) from exc
        st['read'] = d
        secs = (res.get('read') or {}).get('seconds')
        self.message(f'Read {s["name"]}' + (f' in {float(secs):.1f} s' if isinstance(secs, (int, float)) else '')
                     + f' (units {used}).')
        return d

    def published_conversion(self, s: dict, drawing: dict) -> dict:
        """The source's ConversionReport in sheet metres (a DWG's cached report published in the read's units; a DXF
        upload's `not-converted` report)."""
        units = drawing['units']['used']
        if s['kind'] == 'dxf':
            info = self.source_info(s)
            info['formatVersion'] = (drawing.get('dxf') or {}).get('acadVersion')
            return losscheck.not_converted(info, drawing, s['sha1'], info['bytes'])
        rep = self.state(s).get('report')
        if rep is None:
            self.cached_conversion(s)
            rep = self.state(s).get('report')
        if rep is None:
            raise RunError('check_failed', f'The conversion report of {s["name"]} is missing.')
        return losscheck.publish(rep, units)

    # ------------------------------------------------------------------------------------------------- prepare
    def do_prepare(self) -> None:
        sources = self.spec['sources']
        only = self.spec.get('only')
        for i, s in enumerate(sources):
            if only is not None and s['sha1'] not in only:
                continue
            if only is None and s['kind'] == 'dwg':
                self.check_stop()
                self.step_start(f'convert:{i}')
                if self.cached_conversion(s) is not None:
                    self.step_done(f'convert:{i}', 'already converted')
                    self.check_stop()
                    self.step_start(f'check:{i}')
                    self.step_done(f'check:{i}', 'already checked')
                else:
                    self.do_convert(i, s, f'convert:{i}', publish_failure=True)
                    self.step_done(f'convert:{i}')
                    self.check_stop()
                    self.step_start(f'check:{i}')
                    self.do_check(i, s, f'check:{i}')
                    rep = self.state(s)['report']
                    self.step_done(f'check:{i}', rep['verdict'])
            self.check_stop()
            step = f'read:{i}'
            self.step_start(step)
            d = self.ensure_read(i, s, s.get('units'), step)
            hit_before = self.state(s).get('readHit', False)
            drawing = jsonfile.read(d / 'drawing.json')
            base = f'sources/{s["sha1"]}'
            self.write_out(f'{base}/conversion.json', self.published_conversion(s, drawing))
            for n in ('drawing.json', 'plan.json.gz'):
                runio.check_path(self.out / base / n)
                shutil.copyfile(d / n, self.out / base / n)
            self.step_done(step, 'already read' if hit_before else drawing['units']['used'])
        if only is None:
            self.check_stop()
            self.step_start('suggest')
            self.do_suggest()
            self.step_done('suggest')

    def latest_version(self) -> dict | None:
        """{model: path, msName} of the project's latest version when it has no project-data.json (U-3.3), else
        None."""
        vm = (self.spec.get('paths') or {}).get('versionModel')
        if not vm or not Path(vm).is_file():
            return None
        vdir = Path(vm).parent
        if (vdir / 'project-data.json').exists():
            return None
        ms = None
        try:
            ms = (jsonfile.read(vdir / 'version.json').get('downloads') or {}).get('maxScript')
        except (OSError, ValueError, AttributeError):
            pass
        return {'model': str(vm), 'msName': ms}

    def do_suggest(self) -> None:
        sources = self.spec['sources']
        args = {'drawings': [str(self.out / 'sources' / s['sha1'] / 'drawing.json') for s in sources],
                'conversions': [str(self.out / 'sources' / s['sha1'] / 'conversion.json') for s in sources],
                'spec': str(self.spec_path), 'office': self.spec.get('office'),
                'latest_version': self.latest_version(),
                'suggestions_out': str(self.out / 'suggestions.json'),
                'proposed_out': str(self.out / 'proposed-settings.json')}
        try:
            self.child('suggest', args, step='suggest', limit=_limit(self.spec, 'read'), prefix='read',
                       child_steps={'suggest'})
        except ChildFailed as exc:
            raise RunError('internal', f'The layer roles could not be suggested: {exc.detail}.', 'suggest') from exc
        for n in ('suggestions.json', 'proposed-settings.json'):
            if not (self.out / n).is_file():
                raise RunError('internal', f'The layer roles could not be suggested: {n} was not written.', 'suggest')

    # --------------------------------------------------------------------------------------------------- build
    def do_build(self) -> None:
        settings = self.spec.get('settings') or {}
        floors = settings.get('floors') or []
        if not floors:
            raise RunError('no_floors', 'Set up at least one floor on the Floors step.', 'ensure')
        by_sha = {s['sha1']: (i, s) for i, s in enumerate(self.spec['sources'])}
        self.check_stop()
        self.step_start('ensure')
        contexts = []
        for setting in settings.get('sources') or []:
            self.check_stop()
            if setting.get('sha1') not in by_sha:
                raise RunError('bad_settings', f'The settings name a file the build does not have '
                                               f'({setting.get("name")}).', 'ensure')
            i, s = by_sha[setting['sha1']]
            units = setting.get('units') or s.get('units')
            if units not in cache.UNITS:
                raise RunError('bad_settings', f'{s["name"]} has no units yet: confirm them on the Files step.',
                               'ensure')
            d = self.ensure_read(i, s, units, 'ensure')
            drawing = jsonfile.read(d / 'drawing.json')
            conv_path = None
            dxf_sha1 = None
            if s['kind'] == 'dwg':
                rep = self.published_conversion(s, drawing)
                conv_path = self.tmp / 'sources' / s['sha1'] / 'conversion.json'
                jsonfile.write(conv_path, rep)
                dxf_sha1 = (rep.get('dxf') or {}).get('sha1')
            contexts.append({'sha1': s['sha1'], 'name': s['name'], 'kind': s['kind'],
                             'units': drawing['units']['used'], 'conversion': None if conv_path is None else
                             str(conv_path), 'drawing': str(d / 'drawing.json'), 'items': str(d / 'items.pkl'),
                             'plan': str(d / 'plan.json.gz'), 'dxfSha1': dxf_sha1})
        if not contexts:
            raise RunError('bad_settings', 'The settings name no files.', 'ensure')
        paths = self.spec.get('paths') or {}
        build_tmp = self.fresh(self.tmp / 'build')
        (build_tmp / 'openings-data').mkdir()
        ctx = {'spec': self.spec, 'sources': contexts,
               'converter': self.converter() if any(c['kind'] == 'dwg' for c in contexts) else None,
               'previousRunModel': self.previous_model(paths.get('previousRun')),
               'versionModel': paths.get('versionModel') if paths.get('versionModel') and
               Path(paths['versionModel']).is_file() else None,
               'outDir': str(self.out), 'tmpDir': str(build_tmp)}
        jsonfile.write(build_tmp / 'context.json', ctx)
        self.step_done('ensure')
        self.check_stop()
        child_steps = set(CHILD_STEPS_FIXED) | {f'detect:{f["key"]}' for f in floors}
        self.step_start('align')
        lim = _limit(self.spec, 'build')
        try:
            res = self.child('build', {'context': str(build_tmp / 'context.json')}, step='build', limit=lim,
                             prefix='build', child_steps=child_steps,
                             env_extra={'OPENINGS_DATA': str(build_tmp / 'openings-data')})
        except ChildFailed as exc:
            msg = {'build_timeout': f'The build took longer than {lim["seconds"]:.0f} s and was stopped.',
                   'build_memory': f'The build needed more than {lim["memoryMB"]:,} MB and was stopped.'}.get(
                exc.code, f'The build failed: {exc.detail}' if exc.code == 'build_failed' else exc.detail)
            if not msg.endswith('.'):
                msg += '.'
            raise RunError(exc.code, msg, self.cur) from exc
        seconds = res.get('seconds') or {}
        for name in [s['name'] for s in self.steps if s['name'] in child_steps]:
            st = self.by_name[name]
            sec = seconds.get(name) if isinstance(seconds.get(name), (int, float)) else None
            if st['status'] == 'running':
                self.step_done(name, seconds=sec)
                if sec is None and name not in self.reported:
                    st['seconds'] = None                    # the child never said: the time is not this step's
            elif st['status'] == 'waiting':
                st['status'] = 'done'
                st['seconds'] = None if sec is None else round(float(sec), 2)
            elif sec is not None:
                st['seconds'] = round(float(sec), 2)
        self.update_progress()
        self.save()
        self.check_stop()
        self.step_start('validate')
        self.validate(res.get('outputs') or {})
        self.step_done('validate')

    def previous_model(self, prev: str | None) -> str | None:
        if not prev:
            return None
        p = Path(prev)
        for cand in (p, p / 'out' / 'model.json', p / 'model.json'):
            if cand.is_file():
                return str(cand)
        return None

    # ------------------------------------------------------------------------------------------------- validate
    def api_python(self) -> Path | None:
        set_ = os.environ.get(API_PYTHON_ENV)
        cands = [Path(set_)] if set_ else [APP / 'services' / 'api' / '.venv' / 'Scripts' / 'python.exe',
                                           APP / 'services' / 'api' / '.venv' / 'bin' / 'python']
        return next((c for c in cands if c.is_file()), None)

    def validate(self, written: dict) -> None:
        """Every output there and sound (U-3.1 `validate`); raises RunError invalid_output."""
        ms_name = ((self.spec.get('settings') or {}).get('project') or {}).get('maxFileName')
        required = list(BUILD_OUTPUTS) + ([ms_name] if ms_name else [])
        missing = [n for n in required if not (self.out / n).is_file()]
        if missing:
            raise RunError('invalid_output', f'The build did not write {", ".join(missing)}.', 'validate')
        problems: list[str] = []
        model_bytes = (self.out / 'model.json').read_bytes()
        try:
            model = jsonfile.loads(model_bytes)
            if not model.get('floors'):
                problems.append('model.json: the model has no floors')
            if not model.get('parts'):
                problems.append('model.json: the model has no parts')
        except (ValueError, AttributeError) as exc:
            problems.append(f'model.json: not strict JSON ({exc})')
        try:
            jsonfile.read(self.out / 'report.json')
        except ValueError as exc:
            problems.append(f'report.json: not strict JSON ({exc})')
        if not (self.out / 'topview.png').read_bytes()[:8] == b'\x89PNG\r\n\x1a\n':
            problems.append('topview.png: not a PNG picture')
        if ms_name:
            ms = (self.out / ms_name).read_bytes()
            lines = ms.split(b'\r\n')
            stamp = _sha1_bytes(model_bytes)[:12]
            if len(lines) < 2 or f'(model data {stamp})'.encode('ascii') not in lines[1]:
                problems.append(f'{ms_name}: line 2 does not carry the model stamp {stamp}')
            if b'\n' in ms.replace(b'\r\n', b''):
                problems.append(f'{ms_name}: a line does not end with CRLF')
        if not problems:
            problems += self.api_checks()
        if problems:
            more = f' (and {len(problems) - 3} more)' if len(problems) > 3 else ''
            raise RunError('invalid_output', 'The build wrote outputs that do not pass their checks: '
                           + '; '.join(losscheck.scrub(p) for p in problems[:3]) + more + '.', 'validate')

    def api_checks(self) -> list[str]:
        """The API's record checks (check_file.issues) on every JSON output, in the API's own Python (one child)."""
        py = self.api_python()
        if py is None:
            self.message("The API's record checks were not run here (the API checks the outputs when the run is "
                         "done).", 'warn')
            return []
        work = self.fresh(self.tmp / 'validate')
        files = [{'name': n, 'kind': k, 'path': str(self.out / n)} for n, k in CHECK_KIND.items()
                 if (self.out / n).is_file()]
        req = {'files': files, 'model': str(self.out / 'model.json'), 'result': str(work / 'result.json')}
        jsonfile.write(work / 'request.json', req)
        env = isolate.child_env()
        env['PYTHONPATH'] = str(APP / 'services' / 'api')
        try:
            res = isolate.run([str(py), '-B', '-P', '-c', _API_CHECK, str(work / 'request.json')], cwd=work, env=env,
                              seconds=API_CHECK_LIMIT['seconds'], memory_mb=API_CHECK_LIMIT['memoryMB'],
                              stdout=work / 'stdout.txt', stderr=work / 'stderr.txt', cancelled=self.stop_reason,
                              poll=self.on_poll)
        except isolate.IsolateError as exc:
            return [f'the record checks could not start ({exc})']
        self.append_child_log('check_file (validate)', res, [work / 'stdout.txt', work / 'stderr.txt'])
        if res['cancelled']:
            raise Stop(self._stop or 'cancel')
        try:
            found = jsonfile.read(work / 'result.json')
        except (OSError, ValueError):
            return [f'the record checks did not finish (exit code {res["raw_exit_code"]})']
        out = []
        for name, issues in found.items():
            for issue in issues[:5]:
                out.append(f'{name}: {issue}')
        return out


def run(run_dir: Path) -> int:
    """Reads spec.json, takes the machine lock (status queued while waiting), runs the steps of U-3.1 for its kind,
    writes job.json atomically after every status or step change; returns the exit code (0 done, 1 failed, 2 nothing to
    run, 3 cancelled, 4 interrupted, 5 the run folder was removed)."""
    sys.dont_write_bytecode = True
    return Run(Path(run_dir).resolve()).main()


def main(argv: list[str] | None = None) -> int:
    """Command line: --run <run dir>."""
    ap = argparse.ArgumentParser(prog='python -B -P -m walkthrough_builder.job',
                                 description='Runs one prepare or build run of a build (docs/upload/DESIGN.md U-3).')
    ap.add_argument('--run', required=True, help='the run folder holding spec.json')
    a = ap.parse_args(argv)
    return run(Path(a.run))


if __name__ == '__main__':
    sys.exit(main())
