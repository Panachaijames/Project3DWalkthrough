"""The offline single HTML on request (DESIGN.md 16): template from settings.offline_template, each marker exactly once,
the stamp first, then str.split on __WTV_DATA__ (never a replace over the payload).

The payload is plain concatenation of the stored files' text, so that Node (packages/viewer/scripts/make-offline.mjs) and
Python give the same bytes:

    {"format":"walkthrough-offline/1","project":<meta.json>,"version":<version.json>,"model":<model.json>,
     "stages":<stages.json or null>,"pictures":{"<floor>":"data:<mediaType>;base64,<base64>",...},
     "overrides":<overrides.json or null>}

no line breaks added (each file's text as stored, its own trailing newline included, UTF-8); the plan pictures in the
model's floor order (the version's plan-picture assets); then every '<' becomes the six characters \\u003c, so the data
element can never be closed or commented out by drawing text (`</script>`, `<!--`). Assembly substitutes in the TEMPLATE
only: each marker must occur exactly once (else OfflineTemplateError), __WTV_STAMP__ is replaced by the 12-hex stamp, and
the stamped template is split on __WTV_DATA__ into two pieces: piece0 + payload + piece1. Python's str.replace would
rewrite every occurrence (a drawing name containing a marker's text included) and JavaScript's would expand $' $& $` $$;
splitting the template once avoids both.
"""
from __future__ import annotations

import base64
import json
import re
from collections.abc import Mapping
from typing import Any

from .jsonio import JsonError, loads_strict, sha1_hex
from .store.base import NotFound, Store, StoreError

STAMP_MARKER = '__WTV_STAMP__'
DATA_MARKER = '__WTV_DATA__'
FORMAT = 'walkthrough-offline/1'
_STAMP = re.compile(r'[0-9a-f]{12}')
# The plan pictures' floor key and media type go into the payload as they are: the same checks as make-offline.mjs
# (FLOOR_KEY, MEDIA_TYPE), so a store file one side refuses is refused by the other too, and a damaged version.json can
# never give a page whose payload does not parse (fix step, first code review finding 16). fullmatch: whole strings.
_FLOOR_KEY = re.compile(r'[A-Za-z0-9_]{1,32}')
_MEDIA_TYPE = re.compile(r'[A-Za-z0-9.+-]+/[A-Za-z0-9.+-]+')


class OfflineTemplateError(ValueError):
    """The template does not have each marker exactly once."""


def check_template(template: str) -> None:
    for marker in (STAMP_MARKER, DATA_MARKER):
        n = template.count(marker)
        if n != 1:
            raise OfflineTemplateError(f'the offline template has {n} {marker} markers (exactly 1 expected)')


def assemble(template: str, stamp: str, payload: str) -> str:
    """Markers checked once each, the stamp put in first, then split on the data marker: piece0 + payload + piece1."""
    check_template(template)
    if not _STAMP.fullmatch(stamp):
        raise ValueError(f'the stamp must be 12 hex characters, not {stamp!r}')
    stamped = template.replace(STAMP_MARKER, stamp)     # the template only: the payload is never searched or rewritten
    pieces = stamped.split(DATA_MARKER)
    if len(pieces) != 2:                                 # cannot happen after the check (a stamp is 12 hex)
        raise OfflineTemplateError(f'the stamped template splits into {len(pieces)} pieces on {DATA_MARKER}')
    return pieces[0] + payload + pieces[1]


def escape_payload(raw: str) -> str:
    """Every '<' as \\u003c (valid JSON: '<' can only occur inside strings). No '</script' and no '<!--' remain."""
    return raw.replace('<', '\\u003c')


def payload_text(meta: str, version: str, model: str, stages: str | None, pictures: list[tuple[str, str, bytes]],
                 overrides: str | None) -> str:
    """The raw payload (before escaping): the files' text glued by plain concatenation. `pictures`: (floor, mediaType,
    bytes) in the model's floor order."""
    pics = ','.join(f'{json.dumps(floor)}:"data:{media};base64,{base64.b64encode(data).decode("ascii")}"'
                    for floor, media, data in pictures)
    return (f'{{"format":"{FORMAT}","project":{meta},"version":{version},"model":{model},'
            f'"stages":{stages if stages is not None else "null"},"pictures":{{{pics}}},'
            f'"overrides":{overrides if overrides is not None else "null"}}}')


def _json_text(data: bytes, what: str) -> tuple[str, Any]:
    """A stored JSON file: (its text exactly as stored, its own trailing newline included; the parsed value). It must be
    strict JSON, UTF-8 without a byte-order mark (DESIGN.md 9.1): make-offline.mjs refuses a file that does not parse, and
    so does this (StoreError, the API's 500 store_error), rather than putting it into a page that could not start."""
    try:
        value = loads_strict(data)
    except JsonError as exc:
        raise StoreError(f'{what} is not strict JSON (DESIGN.md 9.1): {exc}') from exc
    return data.decode('utf-8'), value


def picture_assets(version_meta: Mapping[str, Any], model: Mapping[str, Any]) -> list[tuple[str, str, str]]:
    """(floor, asset name, mediaType) of the version's plan pictures, in the model's floor order."""
    by_floor: dict[str, tuple[str, str]] = {}
    for a in version_meta.get('assets', []):
        if a.get('role') == 'plan-picture' and a.get('floor') is not None and a['floor'] not in by_floor:
            by_floor[a['floor']] = (a['name'], a['mediaType'])
    return [(f['key'], *by_floor[f['key']]) for f in model['floors'] if f['key'] in by_floor]


def build_payload(store: Store, project_id: str, n: int) -> tuple[str, str]:
    """(stamp, escaped payload) of a version, from the store's files as stored (with the current overrides.json).
    Store.read_file_bytes is the raw-text seam the payload needs (DESIGN.md 9.3 extension, docs/contract-issues/E.md)."""
    where = f'{project_id} v{n}'
    meta, _ = _json_text(store.read_file_bytes(project_id, None, 'meta.json') or b'', f'{project_id} meta.json')
    version_text, version = _json_text(store.read_file_bytes(project_id, n, 'version.json') or b'', f'{where} version.json')
    model_raw = store.read_json_bytes(project_id, n, 'model.json')
    if sha1_hex(model_raw) != version.get('modelSha1'):       # the version's model, as every other route checks it
        raise StoreError(f'{where} model.json does not match the modelSha1 of its version.json (changed on disk?)')
    model_text, model = _json_text(model_raw, f'{where} model.json')
    try:                                                 # the file decides, as in make-offline.mjs
        stages: str | None = _json_text(store.read_json_bytes(project_id, n, 'stages.json'), f'{where} stages.json')[0]
    except NotFound:
        stages = None
    pictures = []
    for floor, name, media in picture_assets(version, model):
        if not isinstance(floor, str) or not _FLOOR_KEY.fullmatch(floor):
            raise StoreError(f'{where}: plan picture floor key {floor!r} is not a floor key')
        if not isinstance(media, str) or not _MEDIA_TYPE.fullmatch(media):
            raise StoreError(f'{where}: plan picture media type {media!r} is not a media type')
        try:                                             # the store's bytes (a URL-backed store reads its object)
            pictures.append((floor, media, store.asset_bytes(project_id, n, name)))
        except NotFound as exc:                          # version.json lists it, the store does not have it
            raise StoreError(f'{where}: the plan picture {name} listed in version.json is missing') from exc
    overrides_raw = store.read_file_bytes(project_id, n, 'overrides.json', missing_ok=True)
    overrides = _json_text(overrides_raw, f'{where} overrides.json')[0] if overrides_raw is not None else None
    raw = payload_text(meta, version_text, model_text, stages, pictures, overrides)
    return version['stamp'], escape_payload(raw)


def offline_html(store: Store, project_id: str, n: int, template: str) -> str:
    """The offline single HTML of a version (DESIGN.md 16), with the current saved heights."""
    check_template(template)
    stamp, payload = build_payload(store, project_id, n)
    return assemble(template, stamp, payload)


def file_name(project_id: str, n: int) -> str:
    return f'{project_id}-v{n}.html'
