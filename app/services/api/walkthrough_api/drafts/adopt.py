"""A build's settings before and at the settings proposal (docs/upload/DESIGN.md U-3.3, U-7.4, U-9.6, U-10.4).

* **Revision 0** (createBuild): the project's names (meta.json), its office and naming (project-settings.json, else
  derived), sources with `units: null`, no floors and no layers, the defaults of U-10.4; or, for a build `from` a
  version or another build, that recipe with the new build's sources (a file the recipe had keeps its units) and its
  floors re-pointed by file name (same name -> same floor; a floor whose file is gone keeps its old source, and the
  Floors step shows it has none). Revision-0 settings exist only on the server.
* **Adoption** (once, when the first prepare is done and validated; under the build's lock): the worker's
  proposed-settings.json with the project's names, office and naming and the pinned offset; for a project with no
  project-settings.json and no project-data.json (the four seeded ones) its latest version gives the naming (photoName,
  maxPrefix from model.json; maxFileName = its .ms download's name), the floor keys and names in model order, and the
  offset (`model.offset`). A recipe build keeps its recipe, takes the units the reads used for the files that had none,
  and adds the proposal's role for every layer the recipe does not name.
* **Units change** (putBuildSettings): everything of that source in sheet metres is rescaled by newFactor / oldFactor
  about the sheet origin: its floors' boxes and pads, alignment points on its sheet, and the opening and outline-edge
  fixes of its floors (set-aside keys need nothing).
"""
from __future__ import annotations

import copy
import re
from dataclasses import dataclass
from typing import Any

from .. import views
from ..store.base import NotFound, SourceRecord, Store
from . import naming as names

#: Metres per drawing unit (U-7.4).
FACTORS = {'mm': 0.001, 'cm': 0.01, 'm': 1.0, 'in': 0.0254, 'ft': 0.3048}
DEFAULTS = {'doorHead': 2.1, 'windowSill': 0.9, 'windowHead': 2.1, 'railingHeight': 1.1, 'slabThickness': 0.25,
            'singleLineHeight': 1.0}
FURNITURE = {'heights': {}, 'bases': {}, 'words': {}, 'skip': [], 'minSize': 0.08, 'minDepth': None, 'looseLayers': [],
             'pieceLayer': 'insert'}
OPTIONS = {'revitWallTypes': 'auto', 'parapets': 'auto', 'objectClosures': True, 'liftShafts': True, 'plinth': 'auto',
           'outlineWalls': 'off', 'offset': 'auto'}
_PHOTO = re.compile(r'[A-Za-z0-9_.-]{1,64}')
_PREFIX = re.compile(r'[A-Z]{2,4}')
_MS = re.compile(r'[A-Za-z0-9_.-]{1,60}\.ms')
_KEY = re.compile(r'[A-Za-z0-9_]{1,32}')


@dataclass
class ProjectFrame:
    """What the project gives a new build: its office, naming and pinned offset; `latest_model` is the latest version's
    model when the project has no settings of its own (U-3.3: the floor keys and names come from it)."""
    office: str | None
    naming: dict[str, str]
    offset: list[float] | None
    latest_model: dict[str, Any] | None


def project_frame(store: Store, project_id: str) -> ProjectFrame:
    meta = store.get_project(project_id)
    derived = names.naming(meta.name, meta.short_name)
    ps = store.project_settings(project_id)
    if ps is not None:
        return ProjectFrame(ps.office, {'photoName': ps.naming.photo_name, 'maxPrefix': ps.naming.max_prefix,
                                        'maxFileName': ps.naming.max_file_name},
                            list(ps.offset) if ps.offset is not None else None, None)
    if meta.latest_version in meta.versions:
        v = store.get_version(project_id, meta.latest_version)
        model = views.model_of(store, v)
        offset = model.get('offset')
        pinned = [float(offset[0]), float(offset[1])] if isinstance(offset, list) and len(offset) == 2 else None
        if store.version_project_data(project_id, meta.latest_version) is None:
            photo, prefix, ms = model.get('photoName'), model.get('maxPrefix'), v.downloads.max_script
            return ProjectFrame(None, {
                'photoName': photo if isinstance(photo, str) and _PHOTO.fullmatch(photo) else derived['photoName'],
                'maxPrefix': prefix if isinstance(prefix, str) and _PREFIX.fullmatch(prefix) else derived['maxPrefix'],
                'maxFileName': ms if isinstance(ms, str) and _MS.fullmatch(ms) else derived['maxFileName'],
            }, pinned, model)
        return ProjectFrame(None, derived, pinned, None)
    return ProjectFrame(None, derived, None, None)


def _source(rec: SourceRecord, units: str | None = None, confirmed: bool = False) -> dict[str, Any]:
    return {'sha1': rec.sha1, 'name': rec.name, 'kind': rec.kind, 'units': units, 'unitsConfirmed': confirmed}


def fresh_settings(store: Store, project_id: str, sources: list[SourceRecord], frame: ProjectFrame) -> dict[str, Any]:
    """Revision-0 settings of a build with no recipe."""
    meta = store.get_project(project_id)
    return {
        'format': 'build-settings/1', 'office': frame.office,
        'project': {'name': meta.name, 'shortName': meta.short_name, 'projectNo': meta.project_no, **frame.naming,
                    'exportedFrom': None},
        'sources': [_source(r) for r in sources], 'layers': {}, 'floors': [], 'defaults': dict(DEFAULTS),
        'furniture': copy.deepcopy(FURNITURE), 'vocabulary': {},
        'options': {**OPTIONS, 'offset': frame.offset if frame.offset is not None else 'auto'},
        'fixes': {'setAside': [], 'openings': [], 'outlineEdges': []},
    }


def recipe_settings(recipe: dict[str, Any], sources: list[SourceRecord], frame: ProjectFrame) -> dict[str, Any]:
    """Revision-0 settings of a build from a version's or another build's recipe: the new sources, the floors re-pointed
    by file name, the pinned offset when the recipe leaves it to 'auto'."""
    s = copy.deepcopy(recipe)
    old = {src['sha1']: src for src in recipe.get('sources', [])}
    new_by_name = {r.name: r.sha1 for r in sources}
    new = {r.sha1 for r in sources}
    s['sources'] = [_source(r, old[r.sha1]['units'], old[r.sha1]['unitsConfirmed']) if r.sha1 in old else _source(r)
                    for r in sources]
    for f in s.get('floors', []):
        if f['source'] in new:
            continue
        was = old.get(f['source'])
        if was is not None and was['name'] in new_by_name:
            f['source'] = new_by_name[was['name']]
    if frame.offset is not None and s.get('options', {}).get('offset') == 'auto':
        s['options']['offset'] = list(frame.offset)
    return s


def _unique_keys(floors: list[dict[str, Any]]) -> None:
    seen: set[str] = set()
    for f in floors:
        key = f['key']
        n = 2
        while key in seen:
            key = f'{f["key"][:28]}_{n}'
            n += 1
        f['key'] = key
        seen.add(key)


def _units_of(drawing: dict[str, Any] | None) -> tuple[str | None, bool]:
    units = (drawing or {}).get('units') or {}
    used = units.get('used')
    return (used if used in FACTORS else None), units.get('verdict') in ('agree', 'declared-only')


def adopt(current: dict[str, Any], proposal: dict[str, Any], from_kind: str, frame: ProjectFrame,
          drawings: dict[str, dict[str, Any] | None]) -> dict[str, Any]:
    """The settings revision 1 of a build (see the module text). `current` = its revision-0 settings, `proposal` = the
    first prepare's proposed-settings.json, `drawings` = each source's drawing.json (for units the proposal lacks)."""
    proposed = {src['sha1']: src for src in proposal.get('sources', [])}

    def units_for(src: dict[str, Any]) -> dict[str, Any]:
        if src.get('units') is not None:
            return src
        p = proposed.get(src['sha1'])
        if p is not None and p.get('units') is not None:
            return {**src, 'units': p['units'], 'unitsConfirmed': bool(p.get('unitsConfirmed'))}
        used, confirmed = _units_of(drawings.get(src['sha1']))
        return {**src, 'units': used, 'unitsConfirmed': confirmed and used is not None}

    if from_kind != 'none':                                   # a recipe: it stays, the reads fill the gaps
        s = copy.deepcopy(current)
        s['sources'] = [units_for(src) for src in s['sources']]
        for name, role in proposal.get('layers', {}).items():
            s['layers'].setdefault(name, role)
        return s

    s = copy.deepcopy(proposal)
    s['project'] = {**proposal['project'], **{k: current['project'][k] for k in
                                              ('name', 'shortName', 'projectNo', 'photoName', 'maxPrefix', 'maxFileName')}}
    if current.get('office') is not None or frame.office is not None:
        s['office'] = current.get('office') or frame.office
    s['sources'] = [units_for({**src, 'units': None, 'unitsConfirmed': False}) for src in current['sources']]
    if frame.offset is not None:
        s['options']['offset'] = list(frame.offset)
    if frame.latest_model is not None:                        # a seeded project: its floor keys and names
        model_floors = frame.latest_model.get('floors') or []
        for f, mf in zip(s['floors'], model_floors, strict=False):
            if isinstance(mf.get('key'), str) and _KEY.fullmatch(mf['key']):
                f['key'], f['name'] = mf['key'], str(mf.get('name') or mf['key'])
        _unique_keys(s['floors'])
    return s


# ---------------------------------------------------------------------------------------------------- units change
def units_changes(old: dict[str, Any], new: dict[str, Any]) -> list[tuple[str, str, str]]:
    """(sha1, old units, new units) of every source whose units a save changes (old ones known)."""
    before = {src['sha1']: src.get('units') for src in old.get('sources', [])}
    out = []
    for src in new.get('sources', []):
        was = before.get(src['sha1'])
        now = src.get('units')
        if was is not None and now is not None and was != now:
            out.append((src['sha1'], was, now))
    return out


def _scale(point: list[float], r: float) -> list[float]:
    return [point[0] * r, point[1] * r]


def rescale(settings: dict[str, Any], sha1: str, ratio: float) -> None:
    """Everything of source `sha1` in sheet metres times `ratio`, about the sheet origin (in place)."""
    floors = settings.get('floors', [])
    keys = {f['key'] for f in floors if f['source'] == sha1}
    first_on_it = bool(floors) and floors[0]['source'] == sha1
    for f in floors:
        if f['source'] == sha1 and f['area'].get('kind') == 'box':
            f['area']['bbox'] = [v * ratio for v in f['area']['bbox']]
            f['area']['pad'] = f['area']['pad'] * ratio
        if f['align'].get('method') == 'points':
            pairs = f['align']['pairs']
            for pair in pairs:
                if first_on_it:
                    pair[0] = _scale(pair[0], ratio)
                if f['source'] == sha1:
                    pair[1] = _scale(pair[1], ratio)
    fixes = settings.get('fixes', {})
    for group in ('openings', 'outlineEdges'):
        for fix in fixes.get(group, []):
            if fix['floor'] in keys:
                fix['a'], fix['b'] = _scale(fix['a'], ratio), _scale(fix['b'], ratio)


def source_records(store: Store, project_id: str, sha1s: list[str]) -> list[SourceRecord]:
    out = []
    for sha1 in sha1s:
        try:
            out.append(store.get_source(project_id, sha1))
        except NotFound:
            raise NotFound('source_not_found', f'project {project_id!r} has no uploaded file {sha1}') from None
    return out
