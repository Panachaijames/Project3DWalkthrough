"""The seed's work (DESIGN.md 9.2): one version folder per row of the seed table, built whole in a staging folder and
renamed into place, then each project's meta.json.

version.json: createdAt = the mtime of the version's model source file (the newest, for the house's two; UTC, seconds);
sourceFiles = the model's `source`; counts; floors; hasStages; assets with media type, bytes and sha1; downloads
{ maxScript: its file name or null, furnitureCsv: the model has furniture }; the presentation (DESIGN.md 8); seed { from:
the prototype paths read, seededAt, seedVersion }. meta.json: name, shortName, projectNo of the latest version's model,
sourceKind, createdAt = the first version's, updatedAt = the latest version's createdAt or a later overrides save,
latestVersion, versions.

Every model is validated (5.6, strict), every replay file and presentation checked, and each Max script's line 2 must carry
the version's stamp: anything wrong stops the seed before it changes the store (nothing is committed).
"""
from __future__ import annotations

import re
from collections.abc import Callable, Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .. import builtmodel
from ..checks import validate_presentation, validate_replay
from ..jsonio import dumps_compact, dumps_pretty, iso_utc, loads_strict, media_type_of, sha1_hex
from ..store.base import MODEL_FORMAT, PROJECT_FORMAT, VERSION_FORMAT, HeightOverridesFile, ProjectMeta, VersionMeta
from ..store.local import KEPT_ON_REBUILD, LocalStore
from . import convert_house, convert_suite, presentation, stages
from .sources import PROJECT_SOURCE_KIND, SEED_TABLE, VersionSource, reads

SEED_VERSION = '1'
_MS_STAMP = re.compile(rb'\(model data ([0-9a-f]{12})\)')


class SeedError(Exception):
    """The seed refuses a version (a model, replay file or presentation with issues, a stamp that does not pair...)."""

    #: False: nothing in the store was changed. True: some versions were put in place before the failure (SeedCommitError).
    partial = False


class SeedCommitError(SeedError):
    """Every version passed its checks, but a version folder could not be put in place (on Windows: a file in the old folder
    is open, e.g. the API is sending it). The versions before it are in place; the rest were not written."""

    partial = True


# ---------------------------------------------------------------------------------------------------- version.json
def version_record(*, project_id: str, n: int, label: str, created_at: str, source_kind: str, source_files: list[str],
                   model: Mapping[str, Any], model_sha1: str, stamp: str, stamp_source: str, has_stages: bool,
                   assets: Iterable[Mapping[str, Any]], max_script: str | None, presentation: Mapping[str, Any],
                   seed: Mapping[str, Any] | None) -> dict[str, Any]:
    """version.json in the order of contracts.ts VersionMeta (checked by parsing it into the record)."""
    record: dict[str, Any] = {
        'format': VERSION_FORMAT, 'projectId': project_id, 'version': n, 'label': label, 'createdAt': created_at,
        'sourceKind': source_kind, 'sourceFiles': list(source_files), 'modelFormat': MODEL_FORMAT,
        'modelSha1': model_sha1, 'stamp': stamp, 'stampSource': stamp_source,
        'counts': {'floors': len(model['floors']), 'parts': len(model['parts']), 'openings': len(model['openings']),
                   'furniture': len(model.get('furniture') or []), 'furnitureKinds': len(model.get('furnitureKinds') or []),
                   'rooms': len(model['rooms'])},
        'floors': [{'key': f['key'], 'name': f['name'], 'level': f['level']} for f in model['floors']],
        'hasStages': has_stages,
        'assets': [{k: v for k, v in a.items() if not (k in ('floor', 'modelRef') and v is None)} for a in assets],
        'downloads': {'maxScript': max_script, 'furnitureCsv': bool(model.get('furniture'))},
        'presentation': dict(presentation),
    }
    if seed is not None:
        record['seed'] = dict(seed)
    VersionMeta.model_validate(record)
    return record


def ms_stamp(script: bytes) -> str | None:
    """The `(model data <12 hex>)` stamp on line 2 of a generated 3ds Max script."""
    lines = script.split(b'\n')
    m = _MS_STAMP.search(lines[1]) if len(lines) > 1 else None
    return m.group(1).decode('ascii') if m else None


# ---------------------------------------------------------------------------------------------------- one version
@dataclass
class Built:
    source: VersionSource
    staging: Path
    record: dict[str, Any]
    model: dict[str, Any]


def _loads(raw: bytes, what: str) -> Any:
    try:
        return loads_strict(raw)
    except ValueError as exc:
        raise SeedError(f'{what}: {exc}') from exc


def make_files(protos: Path, v: VersionSource) -> tuple[bytes, dict[str, Any], bytes | None, dict[str, Any] | None,
                                                          dict[str, Any]]:
    """(model.json bytes, model, stages.json bytes, stages, presentation) of a seed-table version, all checked."""
    def read(rel: str) -> bytes:
        return (protos / v.path(rel)).read_bytes()

    def load(rel: str) -> Any:
        return _loads(read(rel), v.path(rel))

    name = f'{v.project_id} v{v.version}'
    try:
        if v.model == 'copy':
            model_raw = read(v.model_files[0])                      # byte for byte (DESIGN.md 6.1, 6.2)
        elif v.model == 'suite':
            model_raw = dumps_compact(convert_suite.convert(load('src/pres2_model.json')))
        elif v.model == 'house':
            model_raw = dumps_compact(convert_house.convert(load('src/house3d_merged.json'), load('src/furniture_house.json')))
        else:
            raise SeedError(f'{name}: no converter {v.model!r}')
    except (KeyError, TypeError, ValueError, AttributeError, IndexError) as exc:
        raise SeedError(f'{name}: the {v.model} conversion failed on the source files: {type(exc).__name__}: {exc}') from exc
    try:
        model = builtmodel.validate_bytes(model_raw, f'{name} model.json')
    except builtmodel.ModelInvalid as exc:
        raise SeedError(str(exc)) from exc

    stages_raw: bytes | None = None
    stages_obj: dict[str, Any] | None = None
    try:
        if v.stages == 'copy':
            assert v.stages_file
            stages_raw = read(v.stages_file)                        # byte for byte (DESIGN.md 7.1)
            stages_obj = _loads(stages_raw, v.path(v.stages_file))
        elif v.stages == 'suite':
            assert v.stages_file
            stages_obj = stages.suite(load(v.stages_file))
        elif v.stages == 'house':
            assert v.stages_file
            stages_obj = stages.house(load(v.stages_file), load('src/house3d_merged.json'), load('src/furniture_house.json'),
                                      [f['key'] for f in model['floors']])
    except (KeyError, TypeError, ValueError, AttributeError, IndexError) as exc:
        if isinstance(exc, SeedError):
            raise
        raise SeedError(f'{name}: the {v.stages} replay conversion failed: {type(exc).__name__}: {exc}') from exc
    if stages_obj is not None:
        if stages_raw is None:
            stages_raw = dumps_compact(stages_obj)
        try:
            validate_replay(stages_obj, model, f'{name} stages.json')
        except builtmodel.ModelInvalid as exc:
            raise SeedError(str(exc)) from exc

    ports: dict[str, Callable[[], dict[str, Any]]] = {
        'bank': lambda: presentation.bank(model, _loads(read(v.stages_file or ''), 'stages')),
        'suite': lambda: presentation.suite(load('src/pres2_model.json'), load('src/pres2_stages.json')),
        'house': lambda: presentation.house(load('src/house3d_stages.json'), load('src/furniture_house.json'), model['floors']),
        'hotel': lambda: presentation.hotel(model),
    }
    try:
        pres = ports[v.presentation]()
        validate_presentation(pres, model, f'{name} presentation')
    except (ValueError, KeyError, TypeError, AttributeError, IndexError) as exc:
        if isinstance(exc, SeedError):
            raise
        raise SeedError(f'{name} presentation: {type(exc).__name__}: {exc}') from exc
    return model_raw, model, stages_raw, stages_obj, pres


def build_version(store: LocalStore, protos: Path, v: VersionSource, seeded_at: str) -> Built:
    """Writes the version into versions/.staging-<uuid>/ (not yet in place: commit_version does that)."""
    name = f'{v.project_id} v{v.version}'
    model_raw, model, stages_raw, _, pres = make_files(protos, v)
    staging = store.new_version_staging(v.project_id)
    try:
        (staging / 'model.json').write_bytes(model_raw)
        if stages_raw is not None:
            (staging / 'stages.json').write_bytes(stages_raw)
        assets = []
        frames = model.get('pictureFrame') or {}
        for a in v.assets:
            data = (protos / v.path(a.src)).read_bytes()
            if a.role == 'plan-picture':
                if a.floor not in frames or frames[a.floor]['file'] != a.model_ref:
                    raise SeedError(f'{name}: asset {a.name} is not the pictureFrame file of floor {a.floor}')
            (staging / 'assets').mkdir(exist_ok=True)
            (staging / 'assets' / a.name).write_bytes(data)
            assets.append({'name': a.name, 'role': a.role, 'floor': a.floor, 'mediaType': media_type_of(data, a.name),
                           'bytes': len(data), 'sha1': sha1_hex(data), 'modelRef': a.model_ref})
        for folder, files in (('downloads', v.downloads), ('source', v.source)):
            for rel in files:
                (staging / folder).mkdir(exist_ok=True)
                (staging / folder / Path(rel).name).write_bytes((protos / v.path(rel)).read_bytes())
        stamp_file = staging / v.stamp_source
        if not stamp_file.is_file():
            raise SeedError(f'{name}: stampSource {v.stamp_source} is not in the version folder')
        stamp = sha1_hex(stamp_file.read_bytes())[:12]
        if v.max_script:
            found = ms_stamp((staging / 'downloads' / v.max_script).read_bytes())
            if found != stamp:
                raise SeedError(f'{name}: {v.max_script} line 2 says model data {found}, the version is {stamp}')
        created = max((protos / v.path(rel)).stat().st_mtime for rel in v.model_files)
        record = version_record(
            project_id=v.project_id, n=v.version, label=v.label, created_at=iso_utc(created), source_kind=v.source_kind,
            source_files=list(model['source']), model=model, model_sha1=sha1_hex(model_raw), stamp=stamp,
            stamp_source=v.stamp_source, has_stages=stages_raw is not None, assets=assets, max_script=v.max_script,
            presentation=pres, seed={'from': reads(v), 'seededAt': seeded_at, 'seedVersion': SEED_VERSION})
        (staging / 'version.json').write_bytes(dumps_pretty(record))
    except BaseException:
        store.discard_staging(staging)
        raise
    return Built(v, staging, record, model)


# ---------------------------------------------------------------------------------------------------- meta.json
def version_folders(store: LocalStore, project_id: str) -> list[int]:
    d = store.project_dir(project_id) / 'versions'
    if not d.is_dir():
        return []
    return sorted(int(x.name) for x in d.iterdir() if x.is_dir() and x.name.isdigit() and (x / 'version.json').is_file())


def project_meta(store: LocalStore, project_id: str, source_kind: str) -> ProjectMeta:
    """meta.json from the version folders as they are now (seeded or added later)."""
    ns = version_folders(store, project_id)
    if not ns:
        raise SeedError(f'{project_id}: no versions')
    vdir = store.project_dir(project_id) / 'versions'
    records = [VersionMeta.model_validate(loads_strict((vdir / str(n) / 'version.json').read_bytes())) for n in ns]
    latest_model = loads_strict((vdir / str(ns[-1]) / 'model.json').read_bytes())
    updated = records[-1].created_at
    for n in ns:
        o = vdir / str(n) / 'overrides.json'
        if o.is_file():
            updated = max(updated, HeightOverridesFile.model_validate(loads_strict(o.read_bytes())).updated_at)
    return ProjectMeta(format=PROJECT_FORMAT, id=project_id, name=latest_model['project'],
                       short_name=latest_model['shortName'], project_no=latest_model.get('projectNo'),
                       source_kind=records[-1].source_kind or source_kind, created_at=records[0].created_at,
                       updated_at=updated, latest_version=ns[-1], versions=ns)


# ---------------------------------------------------------------------------------------------------- the whole seed
def uploaded_version(store: LocalStore, project_id: str, n: int) -> bool:
    """True when versions/<n>/version.json exists and has no `seed` record: a version saved from an upload (U-15.3), which
    the seed never replaces. A version.json that does not parse is not the seed's either: it is left for a person."""
    path = store.version_dir(project_id, n) / 'version.json'
    try:
        record = loads_strict(path.read_bytes())
    except FileNotFoundError:
        return False
    except ValueError:
        return True
    return not (isinstance(record, dict) and isinstance(record.get('seed'), dict))


@dataclass
class SeedResult:
    built: list[Built]
    left_alone: list[VersionSource]
    reset: list[VersionSource]


def seed(protos: Path, data: Path, *, force: bool = False, reset_overrides: bool = False,
         table: Iterable[VersionSource] = SEED_TABLE, log: Callable[[str], None] = print) -> SeedResult:
    """Rebuilds the store's seed-table versions (with `force`; else only the missing ones), keeping each overrides.json
    unless `reset_overrides`; writes nothing at all when any version fails its checks."""
    protos, data = Path(protos), Path(data)
    if not protos.is_dir():
        raise SeedError(f'--prototypes {protos} is not a folder')
    store = LocalStore(data)
    seeded_at = iso_utc()
    table = list(table)
    if force:
        uploaded = [v for v in table if uploaded_version(store, v.project_id, v.version)]
        if uploaded:
            names = ', '.join(f'{v.project_id} v{v.version}' for v in uploaded)
            raise SeedError(f'{names}: an uploaded version (its version.json has no seed record) is never replaced by '
                            f'the seed, even with --force (docs/upload/DESIGN.md U-15.3)')
    built: list[Built] = []
    left_alone: list[VersionSource] = []
    try:
        for v in table:
            if (store.version_dir(v.project_id, v.version) / 'version.json').is_file() and not force:
                left_alone.append(v)
                continue
            built.append(build_version(store, protos, v, seeded_at))
    except BaseException:
        for b in built:
            store.discard_staging(b.staging)
        raise
    keep = tuple(k for k in KEPT_ON_REBUILD if not (reset_overrides and k == 'overrides.json'))
    reset: list[VersionSource] = []
    # The commit phase holds the store's cross-process lock (the API may be serving and saving heights meanwhile): each
    # kept overrides.json is copied and its folder swapped with no save in between, and meta.json is computed from the
    # saved heights as they are (fix step, review finding "code" 2).
    with store.exclusive():
        for i, b in enumerate(built):
            try:
                store.commit_version(b.source.project_id, b.source.version, b.staging, keep=keep)
            except OSError as exc:
                for rest in built[i:]:
                    store.discard_staging(rest.staging)
                for project_id in dict.fromkeys(x.source.project_id for x in built[:i]):
                    store.write_project_meta(project_meta(store, project_id, PROJECT_SOURCE_KIND.get(project_id, 'cad')))
                done = ', '.join(f'{x.source.project_id} v{x.source.version}' for x in built[:i]) or 'none'
                raise SeedCommitError(
                    f'{b.source.project_id} v{b.source.version}: the new version folder could not be put in place ({exc}); '
                    f'is a file in it open (the API sending a download)? Written before it: {done}. Run the seed again.'
                ) from exc
        if reset_overrides:
            for v in left_alone:
                o = store.version_dir(v.project_id, v.version) / 'overrides.json'
                if o.is_file():
                    o.unlink()
                    reset.append(v)
        for project_id in dict.fromkeys(v.project_id for v in table):
            store.write_project_meta(project_meta(store, project_id, PROJECT_SOURCE_KIND.get(project_id, 'cad')))
    for b in built:
        c, r = b.record['counts'], b.record
        log(f"{b.source.project_id} v{b.source.version}: floors {c['floors']}, parts {c['parts']}, openings {c['openings']}, "
            f"probes {len(b.model['probes'])}, rooms {c['rooms']}, furniture {c['furniture']} ({c['furnitureKinds']} kinds), "
            f"stamp {r['stamp']} ({r['stampSource']}), replay {'yes' if r['hasStages'] else 'no'}, "
            f"assets {len(r['assets'])}, downloads {len(b.source.downloads)}")
    for v in left_alone:
        log(f'{v.project_id} v{v.version}: left alone (exists; --force rebuilds it)'
            + (' - saved heights reset' if v in reset else ''))
    return SeedResult(built, left_alone, reset)
