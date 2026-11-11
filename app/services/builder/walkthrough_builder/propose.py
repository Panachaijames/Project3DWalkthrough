"""The settings proposal: what a build's settings become when its first prepare run is done (docs/upload/DESIGN.md
U-3.3, U-7.4, U-9, U-10.4). The API adopts it as revision 1 (U5); staff change it on the Files, Layers and Floors steps.

    propose_settings(spec, drawings, suggestions, conversions, latest_version) -> BuildSettings

* sources: the spec's, in its order, with the units each read used; `unitsConfirmed` true when the reader's verdict is
  `agree` or `declared-only`, false for `votes-win` or `unknown` (staff confirm on the Files step, U-7.4);
* layers: every suggested layer with its suggested role (suggest.py);
* floors: one per source (the whole file) when there are several sources; one per area proposal that looks like a plan
  (a box, pad 0.5, match 'all') when one source holds several, pieces of one plan joined first (a plan-looking box
  that lies 30 % or more inside a larger one is part of it: the house's ground plan is a 92 % box and an overlapping
  sliver in the reader's clustering, which the browser repeats and so cannot join them itself); else one floor, the
  whole file. Keys L1, L2 ..., names Level 1 ..., levels 0, 3.00, 6.00 ..., wall heights 3.00, alignment auto. These
  are guesses (`notes()` says so in plain sentences: BuildSettings has no field for them);
* project, office, defaults, furniture, vocabulary, options and fixes: the spec's settings (revision 0, which the API
  writes from the project and project-settings.json) where they are there, else U-10.4's defaults; `exportedFrom` left
  as given, or 'Revit' when most of the drawings' blocks carry Revit element ids;
* `latest_version` = { model, msName } of a project with no project-settings.json and no project-data.json (the seeded
  four, U-3.3): the naming (photoName, maxPrefix from its model.json; maxFileName = its stored .ms download's name), the
  floor keys and names in model order, the levels and wall heights of those floors (when they still rise, the model's
  rule), and the pinned offset (options.offset = model.offset, U-9.6).
Every number is a float (U-10.4: the builder coerces anyway). Owner: U2.
"""
from __future__ import annotations

import copy
import math
import re
import unicodedata

from . import areas as A
from . import names, roles
from .contracts import NEW_RULES

DEFAULTS ={'doorHead': 2.1, 'windowSill': 0.9, 'windowHead': 2.1, 'railingHeight': 1.1, 'slabThickness': 0.25,
            'singleLineHeight': 1.0}
FURNITURE = {'heights': {}, 'bases': {}, 'words': {}, 'skip': [], 'minSize': 0.08, 'minDepth': None, 'looseLayers': [],
             'pieceLayer': 'insert'}
#: The rooms milestone (docs/rooms/DESIGN.md R-1.2, R-1.3): the proposal writes the NEW rules (floor plates from the
#: wall network, ceilings, stairs you can climb), so every new draft gets them; a recipe that carries the three keys,
#: old or new, is kept as it is (`_dict_like`). The builder's own OPTIONS (build/settings.py) fill the OLD rules for
#: a missing key, on purpose: the two dicts differ.
OPTIONS = {'revitWallTypes': 'auto', 'parapets': 'auto', 'objectClosures': True, 'liftShafts': True, 'plinth': 'auto',
           'outlineWalls': 'off', 'offset': 'auto', **NEW_RULES}
#: the three new fix lists (R-6.2) are carried over from a recipe like the old ones (empty in a new proposal)
FIXES = {'setAside': [], 'openings': [], 'outlineEdges': [], 'closings': [], 'rooms': [], 'stairs': []}
LEVEL_STEP = 3.0
WALL_HEIGHT = 3.0
PAD = 0.5
#: a plan-looking box that shares this much of its own area with a larger one is a piece of that plan
JOIN_SHARE = 0.3

KEY_RE = re.compile(r'^[A-Za-z0-9_]{1,32}$')
PHOTO_RE = re.compile(r'^[A-Za-z0-9_.-]{1,64}$')
PREFIX_RE = re.compile(r'^[A-Z]{2,4}$')
MS_RE = re.compile(r'^[A-Za-z0-9_.-]{1,60}\.ms$')
OFFICE_RE = re.compile(r'^[a-z0-9][a-z0-9-]{1,62}$')
CONFIRMED = ('agree', 'declared-only')
REVIT_SHARE, REVIT_MIN = 0.3, 20


# --------------------------------------------------------------------------------------------------------- helpers
def _num(v, default: float | None = None) -> float | None:
    if isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v):
        return default
    return float(v)


def _ascii_words(text: str) -> list[str]:
    s = unicodedata.normalize('NFKD', text or '').encode('ascii', 'ignore').decode('ascii')
    return re.findall(r'[A-Za-z0-9]+', s)


def derived_naming(short_name: str, name: str) -> dict:
    """U-13.3's naming for a project that has none: photoName = the short name's ASCII with other runs as '-' (at most
    64, else 'Project'); maxPrefix = the initials of the first two to four ASCII words, upper case, padded with X to 2;
    maxFileName = the ASCII words joined by '_' + '.ms' (at most 60 before the extension)."""
    words = _ascii_words(short_name) or _ascii_words(name)
    photo = '-'.join(words)[:64].strip('-') or 'Project'
    letters = [w[0].upper() for w in words if w[0].isalpha()][:4]
    prefix = ''.join(letters)
    prefix = (prefix + 'XX')[:max(2, len(prefix))] if len(prefix) < 2 else prefix
    stem = '_'.join(_ascii_words(name) or words)[:57].strip('_') or 'Project'
    return {'photoName': photo, 'maxPrefix': prefix, 'maxFileName': f'{stem}.ms'}


def _project(base: dict | None, spec: dict, drawings: list[dict], model: dict | None, ms_name: str | None) -> dict:
    p = dict(base or {})
    m = model or {}
    name = p.get('name') if isinstance(p.get('name'), str) and p.get('name') else (m.get('project') or spec.get('projectId') or 'Project')
    short = p.get('shortName') if isinstance(p.get('shortName'), str) and p.get('shortName') else (m.get('shortName') or name)
    project_no = p['projectNo'] if 'projectNo' in p else m.get('projectNo')
    naming = derived_naming(short, name)
    for key in ('photoName', 'maxPrefix', 'maxFileName'):
        if isinstance(p.get(key), str) and p.get(key):
            naming[key] = p[key]
    if model is not None:                                    # a seeded project's latest version (U-3.3)
        if isinstance(m.get('photoName'), str) and PHOTO_RE.match(m['photoName']):
            naming['photoName'] = m['photoName']
        if isinstance(m.get('maxPrefix'), str) and PREFIX_RE.match(m['maxPrefix']):
            naming['maxPrefix'] = m['maxPrefix']
        if isinstance(ms_name, str) and MS_RE.match(ms_name):
            naming['maxFileName'] = ms_name
    exported = p.get('exportedFrom') if isinstance(p.get('exportedFrom'), str) else None
    if exported is None and looks_revit(drawings):
        exported = 'Revit'
    return {'name': str(name), 'shortName': str(short),
            'projectNo': str(project_no) if isinstance(project_no, (str, int)) and not isinstance(project_no, bool) else None,
            'photoName': naming['photoName'], 'maxPrefix': naming['maxPrefix'], 'maxFileName': naming['maxFileName'],
            'exportedFrom': exported}


def looks_revit(drawings: list[dict]) -> bool:
    """Most of the drawings' blocks carry a Revit element id (`-<5+ digits>-` in the name): a Revit export."""
    blocks = [b.get('name', '') for dr in drawings for b in dr.get('blocks') or []]
    with_id = sum(1 for n in blocks if names.element_id_of(str(n)) is not None)
    return with_id >= REVIT_MIN and with_id >= REVIT_SHARE * len(blocks)


def _floor(key: str, name: str, source: str, area: dict, level: float, wall: float) -> dict:
    return {'key': key, 'name': name, 'source': source, 'area': area, 'level': float(level), 'wallHeight': float(wall),
            'slabThickness': None, 'doorHead': None, 'windowSill': None, 'windowHead': None, 'align': {'method': 'auto'}}


def plan_boxes(areas: list[dict]) -> list[list[float]]:
    """The boxes of the plan-looking area proposals with the pieces of one plan joined: a box that shares JOIN_SHARE of
    its own area or more with a larger (or equal, earlier) box joins it, their union taking both, until nothing joins;
    in reading order (top edge first, then left edge)."""
    boxes = []
    for a in areas:
        if a.get('looks') != 'plan':
            continue
        b = a.get('bbox')
        if (isinstance(b, (list, tuple)) and len(b) == 4 and all(_num(v) is not None for v in b)
                and b[0] < b[2] and b[1] < b[3]):
            boxes.append([float(v) for v in b])
    joined = True
    while joined:
        joined = False
        for i in range(len(boxes)):
            for j in range(len(boxes)):
                a, b = boxes[i], boxes[j]
                if i != j and A.area_of(a) >= A.area_of(b) and A.overlap(a, b) >= JOIN_SHARE * A.area_of(b):
                    boxes[i] = [min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3])]
                    del boxes[j]
                    joined = True
                    break
            if joined:
                break
    return [boxes[i] for i in A.reading_order(boxes)]


def guess_floors(sources: list[dict], by_sha: dict[str, dict]) -> list[dict]:
    """U-3.3's floors: one per source when there are several; one per plan-looking area (pieces of one plan joined)
    when one source has several."""
    plans = []
    if len(sources) == 1:
        dr = by_sha.get(sources[0]['sha1']) or {}
        plans = plan_boxes(dr.get('areas') or [])
    if len(plans) >= 2:
        sha = sources[0]['sha1']
        return [_floor(f'L{i + 1}', f'Level {i + 1}', sha, {'kind': 'box', 'bbox': box, 'pad': PAD, 'match': 'all'},
                       i * LEVEL_STEP, WALL_HEIGHT) for i, box in enumerate(plans)]
    return [_floor(f'L{i + 1}', f'Level {i + 1}', s['sha1'], {'kind': 'wholeFile'}, i * LEVEL_STEP, WALL_HEIGHT)
            for i, s in enumerate(sources)]


def _from_model(floors: list[dict], model: dict) -> None:
    """Floor keys and names (and levels and wall heights while they still rise) from the latest version, in model
    order (U-3.3)."""
    mf = [f for f in (model.get('floors') or []) if isinstance(f, dict)]
    taken: set[str] = set()
    n = min(len(floors), len(mf))
    for i in range(n):
        key = mf[i].get('key')
        if isinstance(key, str) and KEY_RE.match(key) and key not in taken:
            floors[i]['key'] = key
            taken.add(key)
        if isinstance(mf[i].get('name'), str) and mf[i]['name'].strip():
            floors[i]['name'] = mf[i]['name']
    levels = [_num(mf[i].get('level')) for i in range(n)]
    walls = [_num(mf[i].get('wallHeight')) for i in range(n)]
    if n and all(v is not None for v in levels) and all(levels[i] < levels[i + 1] for i in range(n - 1)) \
            and all(w is not None and w > 0 for w in walls):
        for i in range(n):
            floors[i]['level'] = levels[i]
            floors[i]['wallHeight'] = walls[i]
        for i in range(n, len(floors)):                     # floors the model has not: above its top one
            floors[i]['level'] = floors[i - 1]['level'] + floors[i - 1]['wallHeight']
    # keys of the floors the model has not must not repeat the model's
    j = 1
    for i in range(n, len(floors)):
        while f'L{j}' in taken:
            j += 1
        floors[i]['key'] = f'L{j}'
        taken.add(f'L{j}')


def _dict_like(base: dict, key: str, default: dict) -> dict:
    """base[key] key by key over the default (only the contract's keys; a missing one takes its default)."""
    v = base.get(key)
    v = v if isinstance(v, dict) else {}
    return {k: copy.deepcopy(v[k] if k in v else d) for k, d in default.items()}


def _defaults(base: dict) -> dict:
    d = base.get('defaults') if isinstance(base.get('defaults'), dict) else {}
    return {k: _num(d.get(k), v) for k, v in DEFAULTS.items()}


def _offset(model: dict) -> list[float] | None:
    off = model.get('offset')
    if isinstance(off, (list, tuple)) and len(off) == 2 and all(_num(v) is not None for v in off):
        return [float(off[0]), float(off[1])]
    return None


def _office(spec: dict, base: dict) -> str | None:
    o = base.get('office')
    if isinstance(o, str) and OFFICE_RE.match(o):
        return o
    mem = spec.get('office')
    if isinstance(mem, dict) and isinstance(mem.get('id'), str) and OFFICE_RE.match(mem['id']):
        return mem['id']
    return None


# ----------------------------------------------------------------------------------------------------------- proposal
def propose_settings(spec: dict, drawings: list[dict], suggestions: dict, conversions: list[dict],
                     latest_version: dict | None) -> dict:
    """-> BuildSettings (upload-contracts.ts section 1), revision 1's (U-3.3). `drawings` are the sources' DrawingRead,
    `suggestions` the LayerSuggestions, `conversions` their ConversionReports (not needed for the proposal: a `loss`
    verdict warns, never changes the recipe), `latest_version` = { model, msName } or None."""
    base = spec.get('settings') if isinstance(spec.get('settings'), dict) else {}
    by_sha = {dr['source']['sha1']: dr for dr in drawings if isinstance(dr, dict) and dr.get('source')}
    sources = []
    for s in spec.get('sources') or []:
        dr = by_sha.get(s['sha1'])
        u = (dr or {}).get('units') or {}
        used = u.get('used') or s.get('units') or 'mm'
        sources.append({'sha1': s['sha1'], 'name': s.get('name', ''), 'kind': s.get('kind', 'dwg'), 'units': used,
                        'unitsConfirmed': u.get('verdict') in CONFIRMED})
    layers = {}
    for name, sug in sorted((suggestions.get('layers') or {}).items()):
        role = sug.get('role') if isinstance(sug, dict) else None
        layers[name] = role if role in roles.STAFF_ROLES else roles.DEFAULT_ROLE
    floors = guess_floors(sources, by_sha)
    model = (latest_version or {}).get('model') if latest_version else None
    ms_name = (latest_version or {}).get('msName') if latest_version else None
    if isinstance(model, dict):
        _from_model(floors, model)
    else:
        model = None
    options = _dict_like(base, 'options', OPTIONS)
    if model is not None and _offset(model) is not None:
        options['offset'] = _offset(model)
    furniture = _dict_like(base, 'furniture', FURNITURE)
    vocabulary = copy.deepcopy(base['vocabulary']) if isinstance(base.get('vocabulary'), dict) else {}
    fixes = _dict_like(base, 'fixes', FIXES)
    return {
        'format': 'build-settings/1',
        'office': _office(spec, base),
        'project': _project(base.get('project') if isinstance(base.get('project'), dict) else None, spec, drawings,
                            model, ms_name),
        'sources': sources,
        'layers': layers,
        'floors': floors,
        'defaults': _defaults(base),
        'furniture': furniture,
        'vocabulary': vocabulary,
        'options': options,
        'fixes': fixes,
    }


def notes(settings: dict, drawings: list[dict]) -> list[str]:
    """Plain sentences saying what the proposal guessed (U-3.3), for the run's messages."""
    out = []
    floors = settings.get('floors') or []
    if any(f['area'].get('kind') == 'box' for f in floors):
        out.append(f'The floors are a guess: {len(floors)} plans were found side by side on one sheet; check their '
                   f'boxes, levels and wall heights on the Floors step.')
    elif floors:
        out.append(f'The floors are a guess: {len(floors)} floor{"" if len(floors) == 1 else "s"}, one per file, '
                   f'levels 3.00 m apart and walls 3.00 m high; check them on the Floors step.')
    for s in settings.get('sources') or []:
        if not s.get('unitsConfirmed'):
            dr = next((d for d in drawings if d.get('source', {}).get('sha1') == s['sha1']), None)
            note = ((dr or {}).get('units') or {}).get('note') or 'the units could not be checked'
            out.append(f'{s.get("name", "A file")}: {note}. Confirm its units on the Files step.')
    return out
