"""A tiny store that holds the reference building as one saved version (docs/rooms/ACCEPTANCE.md 2.5). Scaffold R0.
Run through tools/rooms/make-fixture-store.mjs (the API's Python):

    node tools/rooms/make-fixture-store.mjs --out <dir> [--id rooms-reference] [--stairs]

It makes a NEW store at <dir> (refused when <dir> exists and is not empty, and when it is app/data) with the project
`rooms-reference` (or --id): version 1 = fixtures/models/rooms-reference.model.json with its stages, presentation, top
view and 3ds Max script (fixtures/rooms/runs/reference-build/out/) and the BuildSettings it was built with, written by
the store's own create_project and create_version, so every check the API makes on a saved version has passed.
`--stairs` adds the projects stairs-straight, stairs-l and stairs-u (fixtures/models/stairs-*.model.json, a plain
presentation, no replay). For the browser specs: serve it with `node tools/run-api.mjs --port <p> --data <dir>` or
point WT_DATA_DIR at it; make the offline files from it with packages/viewer/scripts/make-offline.mjs.
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from walkthrough_api.store.base import NewProject, VersionDraft
from walkthrough_api.store.local import LocalStore

APP = Path(__file__).resolve().parents[2]
FX = APP / 'fixtures'
RUN = FX / 'rooms' / 'runs' / 'reference-build' / 'out'


def main(argv: list[str]) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--id', default='rooms-reference')
    ap.add_argument('--stairs', action='store_true')
    a = ap.parse_args(argv)
    out = Path(a.out).resolve()
    if out == (APP / 'data').resolve():
        print('refused: app/data is the owner\'s store', file=sys.stderr)
        return 2
    if out.exists() and any(out.iterdir()):
        print(f'refused: {out} exists and is not empty', file=sys.stderr)
        return 2
    out.mkdir(parents=True, exist_ok=True)
    store = LocalStore(out)
    model = (FX / 'models' / 'rooms-reference.model.json').read_bytes()
    m = json.loads(model)
    settings = (FX / 'rooms' / 'settings.reference.json').read_bytes()
    ms = json.loads(settings)['project']['maxFileName']
    store.create_project(NewProject(id=a.id, name=m['project'], short_name=m['shortName'], project_no=None, source_kind='cad'))
    v = store.create_version(a.id, VersionDraft(
        label='The reference building of the rooms milestone', source_kind='cad', source_files=list(m['source']),
        model_json=model, stages_json=(FX / 'stages' / 'rooms-reference.stages.json').read_bytes(),
        presentation=json.loads((FX / 'presentation' / 'rooms-reference.json').read_bytes()),
        assets={'topview.png': (RUN / 'topview.png').read_bytes()}, downloads={ms: (RUN / ms).read_bytes()},
        project_data=settings))
    print(f'{out}: {a.id} v{v.version}, stamp {v.stamp}, model format {v.model_format}')
    if a.stairs:
        for variant in ('straight', 'L', 'U'):
            data = (FX / 'models' / f'stairs-{variant}.model.json').read_bytes()
            sm = json.loads(data)
            pid = f'stairs-{variant.lower()}'
            store.create_project(NewProject(id=pid, name=sm['project'], short_name=sm['shortName'], project_no=None, source_kind='cad'))
            pres = {'documentTitle': sm['project'], 'heading': sm['project'], 'intro': [], 'accent': '#2f6f8f',
                    'legend': {'layout': 'inline', 'items': []},
                    'camera': {'kind': 'fitSlabs', 'away': [1, 0.9, 1], 'targetY': 2.5, 'panForPanel': True}}
            sv = store.create_version(pid, VersionDraft(label=f'A synthetic {variant} stair', source_kind='cad',
                                                        source_files=list(sm['source']), model_json=data, stages_json=None,
                                                        presentation=pres))
            print(f'{out}: {pid} v{sv.version}, stamp {sv.stamp}')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
