"""BuiltModel v1 and v2 validation for the API and the seed (DESIGN.md 5.6; docs/rooms/DESIGN.md R-12.1): the schema
(schema/built-model.schema.json, identical to docs/) with jsonschema, then the cross-reference rules, strict (the
furniture rules included). Issue paths are JSON Pointers (/parts/12/z1), the same as the viewer's parseBuiltModel and ajv
report. The v2 rules (stairways, spaces, a part's `stair`, a name's `space`) were written by the rooms scaffold R0
together with the schema and the viewer's parse.ts: the three checkers change together.

Conventions (fixtures/models/broken/expected.json, DESIGN.md 18.49): a missing property is reported at its parent object
(as jsonschema and ajv do); a repeated id at its LATER occurrence (/openings/5/id). The rules run only on a model that
passes the schema (schema first, then the rules), so they never meet a value of the wrong type.

    issues(model)        -> [ModelIssue]   (empty: valid)
    validate(model)      -> model           raises ModelInvalid listing every issue
    validate_bytes(raw)  -> model           strict JSON first (UTF-8, no BOM, no NaN, no repeated keys), then validate
"""
from __future__ import annotations

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from jsonschema import Draft202012Validator, ValidationError, validators

from .jsonio import JsonError, loads_strict

SCHEMA_PATH = Path(__file__).resolve().parent / 'schema' / 'built-model.schema.json'


@dataclass(frozen=True)
class ModelIssue:
    path: str
    message: str

    def __str__(self) -> str:
        return f'{self.path or "/"}: {self.message}'


class ModelInvalid(ValueError):
    """The model is not BuiltModel v1 or breaks a 5.6 rule (or a sidecar fails its check); `issues` lists every problem."""

    def __init__(self, issues: list[ModelIssue], what: str = 'model') -> None:
        self.issues = issues
        self.what = what
        shown = '; '.join(str(i) for i in issues[:12]) + (f' (+{len(issues) - 12} more)' if len(issues) > 12 else '')
        super().__init__(f'{what}: {len(issues)} issue{"s" if len(issues) != 1 else ""}: {shown}')


def pointer(parts: Any) -> str:
    """A JSON Pointer (RFC 6901) from path segments: ~ -> ~0, / -> ~1."""
    return ''.join('/' + str(p).replace('~', '~0').replace('/', '~1') for p in parts)


@lru_cache(maxsize=1)
def schema() -> dict[str, Any]:
    return json.loads(SCHEMA_PATH.read_bytes().decode('utf-8'))


def ecma_pattern(pattern: str) -> str:
    """A JSON Schema `pattern` (ECMA-262, no flags) as a Python regex: every `$` outside a character class and not
    escaped becomes `\\Z`. ECMA's `$` matches only at the very end; Python's also before a final newline, so with
    jsonschema's re.search 'BK\\n' passed ^[A-Z]{2,4}$ while the viewer (JavaScript) refused it (fix step, review finding
    "code" 5: the API must be the stricter one, DESIGN.md 5.6)."""
    out, in_class, i = [], False, 0
    while i < len(pattern):
        c = pattern[i]
        if c == '\\' and i + 1 < len(pattern):
            out.append(pattern[i:i + 2])
            i += 2
            continue
        if in_class:
            in_class = c != ']'
        elif c == '[':
            in_class = True
        elif c == '$':
            c = r'\Z'
        out.append(c)
        i += 1
    return ''.join(out)


def _pattern(validator: Any, pattern: str, instance: Any, schema_: Any) -> Any:
    """The `pattern` keyword with ECMA-262 semantics (ecma_pattern); otherwise as jsonschema's own."""
    del schema_
    if validator.is_type(instance, 'string') and not re.search(ecma_pattern(pattern), instance):
        yield ValidationError(f'{instance!r} does not match {pattern!r}')


_EcmaValidator = validators.extend(Draft202012Validator, {'pattern': _pattern})


@lru_cache(maxsize=1)
def _validator() -> Any:
    s = schema()
    Draft202012Validator.check_schema(s)
    return _EcmaValidator(s)


def schema_issues(model: Any) -> list[ModelIssue]:
    out = [ModelIssue(pointer(e.absolute_path), e.message) for e in _validator().iter_errors(model)]
    return sorted(out, key=lambda i: (i.path, i.message))


PER_FLOOR_MAPS = ('stairs', 'voids', 'closures', 'stairOutlines', 'colliderSkins', 'pictureFrame')


def rule_issues(m: dict[str, Any]) -> list[ModelIssue]:
    """The 5.6 cross-reference rules, strict (the API refuses on any). Call only on a model that passes the schema."""
    out: list[ModelIssue] = []
    add = lambda path, msg: out.append(ModelIssue(path, msg))   # noqa: E731

    keys: set[str] = set()
    last_level: float | None = None
    for i, f in enumerate(m['floors']):
        if f['key'] in keys:
            add(f'/floors/{i}/key', f'floor key {f["key"]!r} is used twice')
        keys.add(f['key'])
        if last_level is not None and f['level'] < last_level:
            add(f'/floors/{i}/level', f'floors are not in level order ({f["level"]} after {last_level})')
        last_level = f['level']

    for i, p in enumerate(m['parts']):
        if p['floor'] not in keys:
            add(f'/parts/{i}/floor', f'unknown floor {p["floor"]!r}')
        if not p['z1'] > p['z0']:
            add(f'/parts/{i}/z1', f'z1 {p["z1"]} is not above z0 {p["z0"]}')
        if p.get('plinth') and p['kind'] != 'slab':
            add(f'/parts/{i}/plinth', f'plinth on a {p["kind"]} (only slabs stand on the ground)')

    for name in PER_FLOOR_MAPS:
        for key in (m.get(name) or {}):
            if key not in keys:
                add(pointer([name, key]), f'unknown floor {key!r}')
    for key, s in m['stairs'].items():
        for prop in ('below', 'above', 'panels'):
            if prop in s and len(s[prop]) % 4:
                add(pointer(['stairs', key, prop]), f'{len(s[prop])} numbers is not a multiple of 4 (x1, y1, x2, y2)')
    for key, skins in m['colliderSkins'].items():
        for i, s in enumerate(skins):
            if not s['z1'] > s['z0']:
                add(pointer(['colliderSkins', key, i, 'z1']), f'z1 {s["z1"]} is not above z0 {s["z0"]}')

    for coll in ('rooms', 'openings', 'probes'):
        for i, x in enumerate(m[coll]):
            if x['floor'] not in keys:
                add(f'/{coll}/{i}/floor', f'unknown floor {x["floor"]!r}')

    opening_ids: set[str] = set()
    for i, o in enumerate(m['openings']):
        if o['id'] in opening_ids:
            add(f'/openings/{i}/id', f'opening id {o["id"]!r} is used twice')
        opening_ids.add(o['id'])

    # BuiltModel v2 (docs/rooms/DESIGN.md R-12.1): stairways rise within one stack; a part's `stair` names a stairway and
    # the part lies on that stairway's `from` floor; every tread and landing has one; stairway and space ids are unique;
    # a drawn name's `space` names a space of its own floor. (`walk` has at least 2 points: the schema.)
    stack_of = {f['key']: f.get('stack', 'main') for f in m['floors']}
    level_of = {f['key']: f['level'] for f in m['floors']}
    stair_from: dict[str, str] = {}
    for i, s in enumerate(m.get('stairways') or []):
        if s['id'] in stair_from:
            add(f'/stairways/{i}/id', f'stairway id {s["id"]!r} is used twice')
        else:
            stair_from[s['id']] = s['from']
        if s['from'] not in keys:
            add(f'/stairways/{i}/from', f'unknown floor {s["from"]!r}')
        if s['to'] not in keys:
            add(f'/stairways/{i}/to', f'unknown floor {s["to"]!r}')
        elif s['from'] in keys:
            if stack_of[s['to']] != stack_of[s['from']]:
                add(f'/stairways/{i}/to', f'{s["to"]!r} is not in the stack of {s["from"]!r}')
            elif not level_of[s['to']] > level_of[s['from']]:
                add(f'/stairways/{i}/to', f'{s["to"]!r} is not above {s["from"]!r}')
    for i, p in enumerate(m['parts']):
        if 'stair' not in p:
            if p['kind'] in ('tread', 'landing'):
                add(f'/parts/{i}', f'a {p["kind"]} must name its stairway (stair)')
            continue
        if p['stair'] not in stair_from:
            add(f'/parts/{i}/stair', f'unknown stairway {p["stair"]!r}')
        elif stair_from[p['stair']] != p['floor']:
            add(f'/parts/{i}/stair', f'stairway {p["stair"]!r} rises from {stair_from[p["stair"]]!r}, but the part is '
                                     f'on {p["floor"]!r}')
    space_floor: dict[str, str] = {}
    for i, s in enumerate(m.get('spaces') or []):
        if s['floor'] not in keys:
            add(f'/spaces/{i}/floor', f'unknown floor {s["floor"]!r}')
        if s['id'] in space_floor:
            add(f'/spaces/{i}/id', f'space id {s["id"]!r} is used twice')
        else:
            space_floor[s['id']] = s['floor']
    for i, r in enumerate(m['rooms']):
        if 'space' not in r:
            continue
        if r['space'] not in space_floor:
            add(f'/rooms/{i}/space', f'unknown space {r["space"]!r}')
        elif space_floor[r['space']] != r['floor']:
            add(f'/rooms/{i}/space', f'space {r["space"]!r} is on {space_floor[r["space"]]!r}, but the name is on '
                                     f'{r["floor"]!r}')

    if 'furniture' in m or 'furnitureKinds' in m:
        kinds = m.get('furnitureKinds') or []
        pieces = m.get('furniture') or []
        kind_keys: set[str] = set()
        for i, k in enumerate(kinds):
            if k['key'] in kind_keys:
                add(f'/furnitureKinds/{i}/key', f'kind {k["key"]!r} is listed twice')
            kind_keys.add(k['key'])
        piece_ids: set[str] = set()
        for i, p in enumerate(pieces):
            if p['id'] in piece_ids:
                add(f'/furniture/{i}/id', f'furniture id {p["id"]!r} is used twice')
            piece_ids.add(p['id'])
        all_ids = {p['id'] for p in pieces}
        count: dict[str, int] = {}
        for i, p in enumerate(pieces):
            count[p['kind']] = count.get(p['kind'], 0) + 1
            if p['kind'] not in kind_keys:
                add(f'/furniture/{i}/kind', f'unknown furniture kind {p["kind"]!r}')
            if p['floor'] not in keys:
                add(f'/furniture/{i}/floor', f'unknown floor {p["floor"]!r}')
            if p['on'] is not None and p['on'] not in all_ids:
                add(f'/furniture/{i}/on', f'stands on {p["on"]!r}, which is no piece')
            for j, a in enumerate(p['approach']):
                if a not in opening_ids:
                    add(f'/furniture/{i}/approach/{j}', f'approach {a!r} is no opening')
        for i, k in enumerate(kinds):
            if count.get(k['key'], 0) != k['count']:
                add(f'/furnitureKinds/{i}/count', f'count {k["count"]}, but {count.get(k["key"], 0)} pieces')
    return out


def issues(model: Any) -> list[ModelIssue]:
    """Every issue: the schema's, else the 5.6 rules' (the rules need a model of the right shape)."""
    found = schema_issues(model)
    return found if found else rule_issues(model)


def validate(model: Any, what: str = 'model') -> dict[str, Any]:
    found = issues(model)
    if found:
        raise ModelInvalid(found, what)
    return model


def validate_bytes(raw: bytes, what: str = 'model') -> dict[str, Any]:
    try:
        model = loads_strict(raw)
    except JsonError as exc:
        raise ModelInvalid([ModelIssue('', f'not strict JSON: {exc}')], what) from exc
    return validate(model, what)
