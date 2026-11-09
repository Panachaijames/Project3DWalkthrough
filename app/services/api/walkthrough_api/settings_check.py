"""The checks of BuildSettings that pydantic's types do not make (docs/upload/DESIGN.md U-13.2): floor keys unique and
^[A-Za-z0-9_]{1,32}$; levels strictly increasing; every floor's source among the sources; boxes with x0 < x1, y0 < y1;
heights 0.05 - 50 m; the naming patterns (photoName, maxPrefix, maxFileName, office); at most 5,000 layers, 20,000
set-asides and 5,000 other fixes; strings at most 500 characters; every source's units set once adopted.

putBuildSettings answers 422 invalid_settings with `details.issues` = these, and `check_file settings` prints them.
Written by step U5 (the scaffold left a stub). Beyond the list above, because each would break a later step rather than
be refused here: every number finite (a body's NaN or Infinity, which Python's JSON reader takes, could not be written
back), source sha1s unique and 40 hex, the vocabulary's patterns compile (the builder runs them), set-aside signatures
in their 12-hex form, sills below heads, furniture heights in whole-mm range, pads and sizes not negative.

Paths are JSON Pointers into the settings by their JSON (camelCase) names: /floors/1/level.
"""
from __future__ import annotations

import math
import re
from typing import Any, TypedDict

from .models_upload import BuildSettings, FloorAlignPoints, FloorAreaBox

FLOOR_KEY = re.compile(r'[A-Za-z0-9_]{1,32}')
PHOTO_NAME = re.compile(r'[A-Za-z0-9_.-]{1,64}')
MAX_PREFIX = re.compile(r'[A-Z]{2,4}')
MAX_FILE_NAME = re.compile(r'[A-Za-z0-9_.-]{1,60}\.ms')
OFFICE_ID = re.compile(r'[a-z0-9][a-z0-9-]{1,62}')
SHA1 = re.compile(r'[0-9a-f]{40}')
SIG = re.compile(r'[0-9a-f]{12}')

MAX_LAYERS = 5_000
MAX_SET_ASIDES = 20_000
MAX_OTHER_FIXES = 5_000
MAX_STRING = 500
MIN_HEIGHT, MAX_HEIGHT = 0.05, 50.0
MAX_LEVEL = 10_000.0
MAX_PAD = 100.0
MAX_ISSUES = 200


class SettingsIssue(TypedDict):
    path: str          # JSON Pointer into the settings, e.g. /floors/1/level
    message: str       # a plain sentence


def _ptr(*parts: Any) -> str:
    return ''.join('/' + str(p).replace('~', '~0').replace('/', '~1') for p in parts)


class _Issues:
    def __init__(self) -> None:
        self.out: list[SettingsIssue] = []

    def add(self, path: str, message: str) -> None:
        if len(self.out) < MAX_ISSUES:
            self.out.append({'path': path, 'message': message})

    def height(self, value: float | None, path: str, what: str, low: float = MIN_HEIGHT) -> None:
        if value is None or not math.isfinite(value):
            return                                       # null: the default; non-finite: reported by the walk
        if not low <= value <= MAX_HEIGHT:
            self.add(path, f'{what} must be {low:g} - {MAX_HEIGHT:g} m, not {value:g}')


def _walk(value: Any, path: str, issues: _Issues) -> None:
    """Every string at most 500 characters (object keys included), every number finite."""
    if isinstance(value, str):
        if len(value) > MAX_STRING:
            issues.add(path, f'a text of {len(value)} characters; at most {MAX_STRING} are taken')
    elif isinstance(value, float):
        if not math.isfinite(value):
            issues.add(path, 'must be a finite number')
    elif isinstance(value, dict):
        for k, v in value.items():
            if isinstance(k, str) and len(k) > MAX_STRING:
                issues.add(_ptr_join(path, k[:40] + '...'), f'a name of {len(k)} characters; at most {MAX_STRING} are taken')
            _walk(v, _ptr_join(path, k), issues)
    elif isinstance(value, list | tuple):
        for i, v in enumerate(value):
            _walk(v, _ptr_join(path, i), issues)


def _ptr_join(path: str, part: Any) -> str:
    return path + _ptr(part)


def settings_issues(settings: BuildSettings, *, adopted: bool = True) -> list[SettingsIssue]:
    """Every issue of `settings` (empty: they can be saved). `adopted` is false for revision-0 settings, whose sources
    may still have units null (U-3.3)."""
    issues = _Issues()
    s = settings
    _walk(s.model_dump(mode='python', by_alias=True), '', issues)

    # ---- office and naming
    if s.office is not None and not OFFICE_ID.fullmatch(s.office):
        issues.add('/office', 'an office id is 2 - 63 lower-case letters, digits and hyphens, starting with a letter or '
                              'digit')
    p = s.project
    if not p.name.strip():
        issues.add('/project/name', 'the project needs a name')
    if not p.short_name.strip():
        issues.add('/project/shortName', 'the project needs a short name')
    if not PHOTO_NAME.fullmatch(p.photo_name):
        issues.add('/project/photoName', 'the photo name is 1 - 64 letters, digits, dots, hyphens and underscores')
    if not MAX_PREFIX.fullmatch(p.max_prefix):
        issues.add('/project/maxPrefix', 'the 3ds Max prefix is 2 - 4 capital letters')
    if not MAX_FILE_NAME.fullmatch(p.max_file_name):
        issues.add('/project/maxFileName', 'the 3ds Max file name is 1 - 60 letters, digits, dots, hyphens and '
                                           'underscores, then .ms')

    # ---- sources
    seen_sources: set[str] = set()
    for i, src in enumerate(s.sources):
        if not SHA1.fullmatch(src.sha1):
            issues.add(_ptr('sources', i, 'sha1'), 'a source is named by its sha1: 40 lower-case hex characters')
        elif src.sha1 in seen_sources:
            issues.add(_ptr('sources', i, 'sha1'), 'this source is listed twice')
        seen_sources.add(src.sha1)
        if not src.name.strip():
            issues.add(_ptr('sources', i, 'name'), 'a source needs its file name')
        if adopted and src.units is None:
            issues.add(_ptr('sources', i, 'units'), f'the units of {src.name} are not set')

    # ---- layers
    if len(s.layers) > MAX_LAYERS:
        issues.add('/layers', f'{len(s.layers)} layers; at most {MAX_LAYERS:,} are taken')
    for name in s.layers:
        if not name:
            issues.add(_ptr('layers', name), 'a layer name cannot be empty')

    # ---- floors
    keys: set[str] = set()
    last_level: float | None = None
    for i, f in enumerate(s.floors):
        at = _ptr('floors', i)
        if not FLOOR_KEY.fullmatch(f.key):
            issues.add(at + '/key', 'a floor key is 1 - 32 letters, digits and underscores')
        elif f.key in keys:
            issues.add(at + '/key', f'the floor key {f.key} is used twice')
        keys.add(f.key)
        if not f.name.strip():
            issues.add(at + '/name', 'the floor needs a name')
        if f.source not in seen_sources:
            issues.add(at + '/source', 'the floor\'s file is not one of the build\'s files')
        if isinstance(f.area, FloorAreaBox):
            x0, y0, x1, y1 = f.area.bbox
            if all(math.isfinite(v) for v in (x0, y0, x1, y1)) and not (x0 < x1 and y0 < y1):
                issues.add(at + '/area/bbox', 'a box runs from its lower-left corner to its upper-right: x0 < x1 and '
                                              'y0 < y1')
            if math.isfinite(f.area.pad) and not 0 <= f.area.pad <= MAX_PAD:
                issues.add(at + '/area/pad', f'the pad must be 0 - {MAX_PAD:g} m')
        if math.isfinite(f.level):
            if abs(f.level) > MAX_LEVEL:
                issues.add(at + '/level', f'a level must lie within {MAX_LEVEL:,.0f} m of the datum')
            if last_level is not None and not f.level > last_level:
                issues.add(at + '/level', 'floors are listed lowest first: each level must be above the one before')
            last_level = f.level
        issues.height(f.wall_height, at + '/wallHeight', 'a wall height')
        issues.height(f.slab_thickness, at + '/slabThickness', 'a slab thickness')
        issues.height(f.door_head, at + '/doorHead', 'a door head')
        issues.height(f.window_head, at + '/windowHead', 'a window head')
        issues.height(f.window_sill, at + '/windowSill', 'a window sill', low=0.0)
        if f.window_sill is not None and f.window_head is not None and f.window_sill >= f.window_head:
            issues.add(at + '/windowSill', 'the window sill must be below the window head')
        if isinstance(f.align, FloorAlignPoints):
            for j, pair in enumerate(f.align.pairs):
                for k, point in enumerate(pair):
                    if not all(math.isfinite(v) for v in point):
                        issues.add(at + _ptr('align', 'pairs', j, k), 'a point needs two finite numbers')

    # ---- defaults
    d = s.defaults
    issues.height(d.door_head, '/defaults/doorHead', 'the door head')
    issues.height(d.window_head, '/defaults/windowHead', 'the window head')
    issues.height(d.window_sill, '/defaults/windowSill', 'the window sill', low=0.0)
    issues.height(d.railing_height, '/defaults/railingHeight', 'the railing height')
    issues.height(d.slab_thickness, '/defaults/slabThickness', 'the slab thickness')
    issues.height(d.single_line_height, '/defaults/singleLineHeight', 'the single-line height')
    if math.isfinite(d.window_sill) and math.isfinite(d.window_head) and d.window_sill >= d.window_head:
        issues.add('/defaults/windowSill', 'the window sill must be below the window head')

    # ---- furniture
    fu = s.furniture
    for kind, mm in fu.heights.items():
        if math.isfinite(mm) and not 10 <= mm <= 5000:
            issues.add(_ptr('furniture', 'heights', kind), 'a furniture height is 10 - 5,000 mm')
    for kind, mm in fu.bases.items():
        if math.isfinite(mm) and not 0 <= mm <= 5000:
            issues.add(_ptr('furniture', 'bases', kind), 'a furniture base is 0 - 5,000 mm')
    if math.isfinite(fu.min_size) and not 0 <= fu.min_size <= 10:
        issues.add('/furniture/minSize', 'the smallest piece is 0 - 10 m')
    if fu.min_depth is not None and math.isfinite(fu.min_depth) and not 0 <= fu.min_depth <= 10:
        issues.add('/furniture/minDepth', 'the smallest depth is 0 - 10 m')

    # ---- vocabulary: the builder runs these patterns
    for key, pattern in s.vocabulary.items():
        try:
            re.compile(pattern, re.IGNORECASE)
        except re.error as exc:
            issues.add(_ptr('vocabulary', key), f'not a pattern the builder can use: {exc}')

    # ---- fixes
    fx = s.fixes
    if len(fx.set_aside) > MAX_SET_ASIDES:
        issues.add('/fixes/setAside', f'{len(fx.set_aside):,} items set aside; at most {MAX_SET_ASIDES:,} are taken: set '
                                      'aside whole blocks instead')
    else:
        for i, ref in enumerate(fx.set_aside):
            at = _ptr('fixes', 'setAside', i)
            if not ref.key:
                issues.add(at + '/key', 'an item set aside needs its key')
            if not SIG.fullmatch(ref.sig):
                issues.add(at + '/sig', 'a signature is 12 hex characters')
            if ref.rsig and not SIG.fullmatch(ref.rsig):
                issues.add(at + '/rsig', 'a relative signature is 12 hex characters or empty')
    others = len(fx.openings) + len(fx.outline_edges)
    if others > MAX_OTHER_FIXES:
        issues.add('/fixes', f'{others:,} opening and outline fixes; at most {MAX_OTHER_FIXES:,} are taken')
    for i, o in enumerate(fx.openings):
        at = _ptr('fixes', 'openings', i)
        issues.height(o.head, at + '/head', 'an opening head')
        issues.height(o.sill, at + '/sill', 'an opening sill', low=0.0)
        if o.head is not None and o.sill is not None and o.sill >= o.head:
            issues.add(at + '/sill', 'the sill must be below the head')
    return issues.out
