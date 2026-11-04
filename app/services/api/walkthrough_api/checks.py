"""Checks for the two sidecars the seed writes next to a model: ReplayData v1 (stages.json, DESIGN.md 7) and Presentation
v1 (version.json -> presentation, DESIGN.md 8), against contracts.ts sections 2 and 3. There is no JSON schema for them;
these hand-written checks mirror the TypeScript types, strictly (no unknown fields), with JSON Pointer paths like the
model's. The seed and create_version refuse anything with an issue (DESIGN.md 9.2: "fails loudly").
"""
from __future__ import annotations

import re
from collections.abc import Mapping
from typing import Any

from .builtmodel import ModelInvalid, ModelIssue, pointer

STEP_KEYS = ('read', 'sort', 'align', 'pair', 'merge', 'raise', 'finish')
TOGGLE_NAMES = ('plates', 'glass', 'rooms', 'single', 'picture')
PART_KINDS = ('wall', 'column', 'lintel', 'sill', 'parapet', 'glass', 'mullion', 'railing', 'single', 'step', 'slab',
              'pane', 'balustrade', 'low', 'builtin', 'deck', 'post')
PART_STYLE_FIELDS = {'color': 'colour', 'edge': 'colour', 'mesh': 'str', 'glass': 'bool', 'see': 'num',
                     'renderOrder': 'num', 'opacity': 'num', 'roughness': 'num', 'metalness': 'num',
                     'edgeOpacity': 'num', 'collider': 'bool', 'single': 'bool'}
_COLOUR = re.compile(r'^#[0-9a-fA-F]{6}$')
_FLOOR_KEY = re.compile(r'^[A-Za-z0-9_]{1,32}$')


class _Issues:
    def __init__(self) -> None:
        self.out: list[ModelIssue] = []

    def add(self, path: list[Any], msg: str) -> None:
        self.out.append(ModelIssue(pointer(path), msg))

    @staticmethod
    def is_num(v: Any) -> bool:
        return isinstance(v, (int, float)) and not isinstance(v, bool)

    def obj(self, v: Any, path: list[Any], required: tuple[str, ...] = (), allowed: tuple[str, ...] | None = None) -> bool:
        if not isinstance(v, dict):
            self.add(path, 'must be an object')
            return False
        for k in required:
            if k not in v:
                self.add(path, f'{k!r} is a required property')
        if allowed is not None:
            for k in v:
                if k not in allowed:
                    self.add([*path, k], 'is not a known field')
        return True

    def string(self, v: Any, path: list[Any], nonempty: bool = False) -> None:
        if not isinstance(v, str):
            self.add(path, 'must be a string')
        elif nonempty and not v:
            self.add(path, 'must not be empty')

    def number(self, v: Any, path: list[Any], positive: bool = False) -> None:
        if not self.is_num(v):
            self.add(path, 'must be a number')
        elif positive and not v > 0:
            self.add(path, 'must be above 0')

    def boolean(self, v: Any, path: list[Any]) -> None:
        if not isinstance(v, bool):
            self.add(path, 'must be true or false')

    def colour(self, v: Any, path: list[Any]) -> None:
        if not isinstance(v, str) or _COLOUR.fullmatch(v) is None:
            self.add(path, "must be a colour '#rrggbb'")

    def vec(self, v: Any, n: int, path: list[Any]) -> None:
        if not isinstance(v, list) or len(v) != n or not all(self.is_num(x) for x in v):
            self.add(path, f'must be {n} numbers')

    def strings(self, v: Any, path: list[Any]) -> None:
        if not isinstance(v, list):
            self.add(path, 'must be a list of strings')
            return
        for i, s in enumerate(v):
            self.string(s, [*path, i])

    def ring(self, v: Any, path: list[Any]) -> None:
        if not isinstance(v, list) or len(v) < 3:
            self.add(path, 'must be an outline of at least 3 points')
            return
        for i, p in enumerate(v):
            self.vec(p, 2, [*path, i])

    def flat(self, v: Any, path: list[Any], multiple: int) -> None:
        if not isinstance(v, list) or not all(self.is_num(x) for x in v):
            self.add(path, 'must be a list of numbers')
        elif len(v) % multiple:
            self.add(path, f'{len(v)} numbers is not a multiple of {multiple}')


# ---------------------------------------------------------------------------------------------------- ReplayData v1
REPLAY_FIELDS = ('source', 'panelIntro', 'intro', 'layers', 'floors', 'captions', 'stats', 'introTitle', 'layersTitle',
                 'stepTitles', 'colors')


def replay_issues(stages: Any, model: Mapping[str, Any]) -> list[ModelIssue]:
    c = _Issues()
    if not c.obj(stages, [], ('source', 'intro', 'layers', 'floors', 'captions'), REPLAY_FIELDS):
        return c.out
    if 'source' in stages and c.obj(stages['source'], ['source']):
        src = stages['source']
        if 'files' in src:
            c.strings(src['files'], ['source', 'files'])
        for k in ('file', 'units'):
            if k in src:
                c.string(src[k], ['source', k])
        for k in ('layers', 'layersUsed'):
            if k in src:
                c.number(src[k], ['source', k])
        if 'layersInUse' in src and (not isinstance(src['layersInUse'], list) or not all(c.is_num(x) for x in src['layersInUse'])):
            c.add(['source', 'layersInUse'], 'must be a list of numbers')
    for k in ('panelIntro', 'introTitle', 'layersTitle'):
        if k in stages:
            c.string(stages[k], [k])
    if 'intro' in stages:
        c.strings(stages['intro'], ['intro'])
    if 'layers' in stages:
        if not isinstance(stages['layers'], list):
            c.add(['layers'], 'must be a list of [label, detail] rows')
        else:
            for i, row in enumerate(stages['layers']):
                if not isinstance(row, list) or len(row) != 2 or not all(isinstance(x, str) for x in row):
                    c.add(['layers', i], 'must be [label, detail] (two strings)')
    model_keys = [f['key'] for f in model['floors']]
    if 'floors' in stages and c.obj(stages['floors'], ['floors']):
        for key in model_keys:
            if key not in stages['floors']:
                c.add(['floors'], f'no replay floor for the model floor {key!r}')
        for key, f in stages['floors'].items():
            path = ['floors', key]
            if key not in model_keys:
                c.add(path, f'{key!r} is not a floor of the model')
            if not c.obj(f, path, ('sheet', 'lines', 'pieces', 'rings'), ('sheet', 'lines', 'pieces', 'rings')):
                continue
            if 'sheet' in f:
                c.vec(f['sheet'], 2, [*path, 'sheet'])
            for prop, multiple in (('lines', 4), ('pieces', 8)):
                if prop in f and c.obj(f[prop], [*path, prop]):
                    for cat, a in f[prop].items():
                        c.flat(a, [*path, prop, cat], multiple)
            if 'rings' in f and c.obj(f['rings'], [*path, 'rings']):
                for kind, rings in f['rings'].items():
                    rp = [*path, 'rings', kind]
                    if not isinstance(rings, list):
                        c.add(rp, 'must be a list of {o, h}')
                        continue
                    for i, r in enumerate(rings):
                        if c.obj(r, [*rp, i], ('o', 'h'), ('o', 'h')):
                            if 'o' in r:
                                c.ring(r['o'], [*rp, i, 'o'])
                            if 'h' in r:
                                if not isinstance(r['h'], list):
                                    c.add([*rp, i, 'h'], 'must be a list of outlines')
                                else:
                                    for j, h in enumerate(r['h']):
                                        c.ring(h, [*rp, i, 'h', j])
    if 'captions' in stages and c.obj(stages['captions'], ['captions'], STEP_KEYS, STEP_KEYS):
        for k in STEP_KEYS:
            if k in stages['captions']:
                c.string(stages['captions'][k], ['captions', k])
    if 'stats' in stages:
        c.obj(stages['stats'], ['stats'])
    if 'stepTitles' in stages and c.obj(stages['stepTitles'], ['stepTitles'], (), STEP_KEYS):
        for k, v in stages['stepTitles'].items():
            c.string(v, ['stepTitles', k], nonempty=True)
    if 'colors' in stages and c.obj(stages['colors'], ['colors']):
        for k, v in stages['colors'].items():
            c.colour(v, ['colors', k])
    return c.out


def validate_replay(stages: Any, model: Mapping[str, Any], what: str = 'stages') -> Any:
    found = replay_issues(stages, model)
    if found:
        raise ModelInvalid(found, what)
    return stages


# ---------------------------------------------------------------------------------------------------- Presentation v1
PRESENTATION_FIELDS = ('documentTitle', 'heading', 'intro', 'accent', 'legend', 'floorButtons', 'labels', 'camera',
                       'partStyles', 'creaseAngle', 'groundPlane', 'toggles')


def presentation_issues(p: Any, model: Mapping[str, Any]) -> list[ModelIssue]:
    c = _Issues()
    if not c.obj(p, [], ('documentTitle', 'heading', 'intro', 'accent', 'legend', 'camera'), PRESENTATION_FIELDS):
        return c.out
    for k in ('documentTitle', 'heading'):
        if k in p:
            c.string(p[k], [k], nonempty=True)
    if 'intro' in p:
        if not isinstance(p['intro'], list):
            c.add(['intro'], 'must be a list of text runs')
        else:
            for i, r in enumerate(p['intro']):
                if c.obj(r, ['intro', i], ('text',), ('text', 'bold')):
                    if 'text' in r:
                        c.string(r['text'], ['intro', i, 'text'])
                    if 'bold' in r:
                        c.boolean(r['bold'], ['intro', i, 'bold'])
    if 'accent' in p:
        c.colour(p['accent'], ['accent'])
    if 'legend' in p and c.obj(p['legend'], ['legend'], ('layout', 'items'), ('layout', 'items')):
        if p['legend'].get('layout') not in ('inline', 'lines'):
            c.add(['legend', 'layout'], "must be 'inline' or 'lines'")
        items = p['legend'].get('items')
        if not isinstance(items, list):
            c.add(['legend', 'items'], 'must be a list')
        else:
            for i, it in enumerate(items):
                if c.obj(it, ['legend', 'items', i], ('colour', 'text'), ('colour', 'text')):
                    c.colour(it.get('colour'), ['legend', 'items', i, 'colour'])
                    c.string(it.get('text'), ['legend', 'items', i, 'text'], nonempty=True)
    floor_keys = {f['key'] for f in model['floors']}
    if 'floorButtons' in p and c.obj(p['floorButtons'], ['floorButtons'], (), ('all', 'labels')):
        fb = p['floorButtons']
        if 'all' in fb:
            c.string(fb['all'], ['floorButtons', 'all'], nonempty=True)
        if 'labels' in fb and c.obj(fb['labels'], ['floorButtons', 'labels']):
            for k, v in fb['labels'].items():
                if k not in floor_keys:
                    c.add(['floorButtons', 'labels', k], f'{k!r} is not a floor of the model')
                c.string(v, ['floorButtons', 'labels', k], nonempty=True)
    if 'labels' in p and c.obj(p['labels'], ['labels'], (), (*TOGGLE_NAMES, 'pictureTitle')):
        for k, v in p['labels'].items():
            c.string(v, ['labels', k], nonempty=True)
    if 'camera' in p and c.obj(p['camera'], ['camera'], ('kind',)):
        cam = p['camera']
        if cam.get('kind') == 'fixed':
            c.obj(cam, ['camera'], ('position', 'target'), ('kind', 'position', 'target', 'far'))
            for k in ('position', 'target'):
                if k in cam:
                    c.vec(cam[k], 3, ['camera', k])
        elif cam.get('kind') == 'fitSlabs':
            c.obj(cam, ['camera'], ('away', 'targetY', 'panForPanel'), ('kind', 'away', 'targetY', 'panForPanel', 'far'))
            if 'away' in cam:
                c.vec(cam['away'], 3, ['camera', 'away'])
            if 'targetY' in cam:
                c.number(cam['targetY'], ['camera', 'targetY'])
            if 'panForPanel' in cam:
                c.boolean(cam['panForPanel'], ['camera', 'panForPanel'])
        else:
            c.add(['camera', 'kind'], "must be 'fixed' or 'fitSlabs'")
        if 'far' in cam:
            c.number(cam['far'], ['camera', 'far'], positive=True)
    if 'partStyles' in p and c.obj(p['partStyles'], ['partStyles'], (), PART_KINDS):
        for kind, st in p['partStyles'].items():
            if c.obj(st, ['partStyles', kind], (), tuple(PART_STYLE_FIELDS)):
                for k, v in st.items():
                    t = PART_STYLE_FIELDS.get(k)
                    path = ['partStyles', kind, k]
                    if t == 'colour':
                        c.colour(v, path)
                    elif t == 'str':
                        c.string(v, path, nonempty=True)
                    elif t == 'bool':
                        c.boolean(v, path)
                    elif t == 'num':
                        c.number(v, path)
    if 'creaseAngle' in p:
        c.number(p['creaseAngle'], ['creaseAngle'], positive=True)
    if 'groundPlane' in p and p['groundPlane'] is not None:
        if c.obj(p['groundPlane'], ['groundPlane'], ('size', 'colour'), ('size', 'colour')):
            gp = p['groundPlane']
            if 'size' in gp:
                c.vec(gp['size'], 2, ['groundPlane', 'size'])
                if isinstance(gp['size'], list) and not all(c.is_num(x) and x > 0 for x in gp['size']):
                    c.add(['groundPlane', 'size'], 'must be above 0')
            if 'colour' in gp:
                c.colour(gp['colour'], ['groundPlane', 'colour'])
    if 'toggles' in p and c.obj(p['toggles'], ['toggles'], (), TOGGLE_NAMES):
        for k, v in p['toggles'].items():
            c.boolean(v, ['toggles', k])
    return c.out


def validate_presentation(p: Any, model: Mapping[str, Any], what: str = 'presentation') -> Any:
    found = presentation_issues(p, model)
    if found:
        raise ModelInvalid(found, what)
    return p


def is_floor_key(k: str) -> bool:
    return _FLOOR_KEY.fullmatch(k) is not None
