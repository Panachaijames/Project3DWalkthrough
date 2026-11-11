"""Helpers of the upload milestone's API tests (step U5): a FakeJobRunner over fixtures/upload/runs/ and an upload through
the API. Not a test module (pytest collects test_*.py only)."""
from __future__ import annotations

import hashlib
import json
import os
import threading
from collections.abc import Callable
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

from kit import APP, PROTOTYPES
from walkthrough_api.jsonio import dumps_pretty

FX = APP / 'fixtures' / 'upload'
#: The rooms milestone's FakeJobRunner run folders (fixtures/README.md, the rooms section): `reference-build` is a build
#: of the reference building, a BuiltModel v2 with a stairway, spaces, ceilings and every new report key and flag.
ROOMS_RUNS = APP / 'fixtures' / 'rooms' / 'runs'
BANK1 = PROTOTYPES / 'I1201 - LEVEL 1 GENERAL ARRANGEMENT.dwg'
BANK2 = PROTOTYPES / 'I1202 - LEVEL 2 GENERAL ARRANGEMENT.dwg'
SHA1 = '459d40fc230607ffe35e2ee9d443cd2b0105dc36'
SHA2 = '6551bdc6f0cff4e31e83b68a55d22cf42703029a'
DEAD_PID = 999_999_999


def load(path: Path) -> Any:
    return json.loads(Path(path).read_bytes())


def fixture_source(folder: Path, src: dict[str, str]) -> Path:
    if 'fixture' in src:
        return APP / src['fixture']
    if 'prototype' in src:
        return PROTOTYPES / src['prototype']
    return folder / src['file']


class FakeJobRunner:
    """Answers a run at once from the fixtures of fixtures/upload/runs/bank-<kind>/: copies the outputs its spec asks for
    into out/ (a one-source prepare: that source only, no suggestions), the Max script under the spec's maxFileName,
    and writes job.json. `mode`: done | running | queued | silent (writes nothing). `mutate[name]` changes an output's
    bytes (None leaves it out). `alive()` is false only for DEAD_PID, so a record naming it is a gone worker.
    `build_run` (the rooms milestone, step R5): the folder a build run is answered from; default the bank's
    (fixtures/upload/runs/bank-build), `ROOMS_RUNS / 'reference-build'` for the reference building's v2 build."""

    def __init__(self, mode: str = 'done', build_run: Path | None = None) -> None:
        self.mode = mode
        self.build_run = build_run if build_run is not None else FX / 'runs' / 'bank-build'
        self.mutate: dict[str, Callable[[bytes], bytes | None]] = {}
        self.started: list[Path] = []
        self.cancelled: list[Path] = []
        self.missing_list: list[str] = []
        self.honour_cancel = True
        self.lock = threading.Lock()

    def missing(self, kinds: Any) -> list[str]:
        return list(self.missing_list)

    def alive(self, record: dict[str, Any]) -> bool:
        return record.get('pid') != DEAD_PID

    def cancel(self, run_dir: Path) -> None:
        (Path(run_dir) / 'cancel').touch()
        self.cancelled.append(Path(run_dir))
        if self.honour_cancel and (Path(run_dir) / 'job.json').is_file():
            job = load(Path(run_dir) / 'job.json')
            job.update(status='cancelled', finishedAt='2026-11-04T00:00:01Z',
                       error={'code': 'cancelled', 'message': 'Cancelled.', 'step': job.get('step')})
            (Path(run_dir) / 'job.json').write_bytes(dumps_pretty(job))

    def start(self, run_dir: Path) -> None:
        run_dir = Path(run_dir)
        with self.lock:
            self.started.append(run_dir)
        if self.mode == 'silent':
            return
        spec = load(run_dir / 'spec.json')
        kind = spec['kind']
        folder = FX / 'runs' / 'bank-prepare' if kind == 'prepare' else self.build_run
        run, job = load(folder / 'run.json'), load(folder / 'job.json')
        shas = [s['sha1'] for s in spec['sources']]
        read = set(spec['only'] or shas)
        outputs = {}
        for name, src in run['outputs'].items():
            if name.startswith('sources/') and name.split('/')[1] not in read:
                continue
            if spec['only'] and name in ('suggestions.json', 'proposed-settings.json'):
                continue
            data = fixture_source(folder, src).read_bytes()
            if name == 'proposed-settings.json':
                proposal = json.loads(data)
                proposal['sources'] = [s for s in proposal['sources'] if s['sha1'] in shas]
                proposal['floors'] = [f for f in proposal['floors'] if f['source'] in shas]
                data = dumps_pretty(proposal)
            target = spec['settings']['project']['maxFileName'] if name.endswith('.ms') else name
            if target in self.mutate:
                changed = self.mutate[target](data)
                if changed is None:
                    continue
                data = changed
            path = run_dir / 'out' / target
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
            outputs[target] = {'bytes': len(data), 'sha1': hashlib.sha1(data).hexdigest()}
        record = dict(job, runId=spec['runId'], kind=kind, outputs=outputs, pid=None, procStart=None)
        if self.mode in ('running', 'queued'):
            record.update(status=self.mode, finishedAt=None, outputs={}, progress=0.5)
        (run_dir / 'job.json').write_bytes(dumps_pretty(record))

    # ---- helpers for tests
    def finish(self, run_dir: Path) -> None:
        """A run started in `running` mode ends done (its outputs written as in done mode)."""
        mode, self.mode = self.mode, 'done'
        try:
            self.start(run_dir)
        finally:
            self.mode = mode
            self.started.pop()


def upload(client: TestClient, project_id: str, data: bytes, name: str) -> dict[str, Any]:
    """createUpload, every part, completeUpload: the SourceFile (asserts each step answers as expected)."""
    r = client.post('/api/uploads', json={'projectId': project_id, 'fileName': name, 'bytes': len(data)})
    assert r.status_code == 201, r.text[:300]
    session = r.json()
    step = session['partBytes']
    for i, url in enumerate(session['partUrls']):
        part = data[i * step:(i + 1) * step]
        r = client.put(url, content=part, headers={'content-type': 'application/octet-stream'})
        assert r.status_code == 200, r.text[:300]
    r = client.post(session['completeUrl'], json={})
    assert r.status_code == 201, r.text[:300]
    return r.json()


def upload_bank(client: TestClient, project_id: str, both: bool = True) -> list[str]:
    out = [upload(client, project_id, BANK1.read_bytes(), BANK1.name)['sha1']]
    if both:
        out.append(upload(client, project_id, BANK2.read_bytes(), BANK2.name)['sha1'])
    return out


def bank_settings() -> dict[str, Any]:
    return load(FX / 'settings' / 'bank.json')


def tree_paths(root: Path) -> list[str]:
    return [os.path.abspath(p) for p in Path(root).rglob('*')]
