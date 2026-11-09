"""A version's outputs from the BuildResult (docs/upload/DESIGN.md U-10.9, U-11, U-12.2, U-12.4; owner U4).

`write_outputs(result, ctx, log)` writes into `ctx['outDir']`, reading BuildContext for everything that is not in the
result (the spec and its settings, the sources' conversion and drawing reports, the converter, the models to diff
against) and never building a cache path of its own:

| file | what |
| model.json | U-10.9: json.dumps(model, separators=(',', ':'), ensure_ascii=False) as UTF-8, no trailing newline |
| stages.json | ReplayData v1 from result.replay (out/replay.py), compact like the bank's |
| presentation.json | Presentation v1 from the model (out/presentation.py) |
| topview.png | the top view from the model alone (out/pictures.py) |
| <settings.project.maxFileName> | the 3ds Max script, `upload` profile, the build's date (out/maxscript.py) |
| overlay.json | BuildOverlay with every flag (out/overlay.py) |
| diff.json | BuildDiff against the previous run and the latest version (out/diff.py) |
| openings.json | OpeningsFile: the detector's records per floor with the model opening each became |
| pieces.json | FurniturePlacements: result.placements |
| report.json | the BuildReport as U3 returns it |
| inputs.json | VersionInputs: build, run, settings revision, built at, sources (bytes, kind, units, verdict, dxfSha1), converter,
|               builder (version, Python, packages, vendored files), seconds |

Everything is computed before anything is written (a Max script that refuses the model, MaxScriptRefused, leaves the
folder untouched), then each file is written atomically. Returns {output name: path}. The build's date (the script's
header) is the local date of `inputs.json builtAt` (contract issue U4-3). The Max generator alone, from the command line:
`node tools/run-builder-py.mjs -m walkthrough_builder.out <model.json> --date "4 Nov 2026" --sources dwg:mm --out x.ms`.
"""
from __future__ import annotations

import datetime as _dt
import hashlib
import json
import platform
import time
from importlib import metadata
from pathlib import Path
from typing import Any

from .. import BUILDER_VERSION
from ..contracts import BuildContext, BuildResult
from ..jsonfile import dumps, write_bytes
from ..vendor.load import manifest as vendor_manifest
from . import diff as _diff
from . import maxscript as _ms
from . import overlay as _overlay
from . import pictures as _pictures
from . import presentation as _presentation
from . import replay as _replay

PACKAGES = ('ezdxf', 'shapely', 'numpy', 'matplotlib', 'pillow')


def _now() -> _dt.datetime:
    """The build's moment (UTC, whole seconds); tests replace it."""
    return _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0)


def model_bytes(model: dict) -> bytes:
    """U-10.9: the prototype's bytes (the store keeps them as they are)."""
    return json.dumps(model, separators=(',', ':'), ensure_ascii=False).encode('utf-8')


def _read_json(path: str | None) -> Any:
    if not path:
        return None
    try:
        return json.loads(Path(path).read_bytes().decode('utf-8'))
    except (OSError, ValueError):
        return None


def _source_bytes(spec_source: dict | None, conversion: dict | None) -> int:
    if spec_source and spec_source.get('path'):
        try:
            return Path(spec_source['path']).stat().st_size
        except OSError:
            pass
    return int(((conversion or {}).get('source') or {}).get('bytes') or 0)


def inputs_record(ctx: BuildContext, built_at: str, seconds: dict[str, float]) -> dict:
    """VersionInputs (upload-contracts.ts section 2)."""
    spec = ctx.get('spec') or {}
    by_sha = {s['sha1']: s for s in spec.get('sources') or []}
    sources = []
    for s in ctx['sources']:
        conv = _read_json(s.get('conversion'))
        verdict = (conv or {}).get('verdict') or ('not-converted' if s.get('kind') == 'dxf' else 'failed')
        sources.append({'sha1': s['sha1'], 'name': s['name'], 'bytes': _source_bytes(by_sha.get(s['sha1']), conv),
                        'kind': s['kind'], 'units': s['units'], 'verdict': verdict, 'dxfSha1': s.get('dxfSha1')})
    packages = {}
    for name in PACKAGES:
        try:
            packages[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            packages[name] = 'missing'
    conv = ctx.get('converter')
    return {
        'format': 'version-inputs/1',
        'buildId': spec.get('buildId', ''),
        'runId': spec.get('runId', ''),
        'settingsRevision': int(spec.get('settingsRevision') or 0),
        'builtAt': built_at,
        'sources': sources,
        'converter': ({'name': conv.get('name', 'libredwg'), 'version': conv['version'], 'exeSha1': conv['exeSha1']}
                      if conv else None),
        'builder': {'version': BUILDER_VERSION, 'python': platform.python_version(), 'packages': packages,
                    'vendor': {f['path']: f['sha1'] for f in vendor_manifest()['files']}},
        'seconds': {k: float(v) for k, v in seconds.items()},
    }


def max_file_name(result: BuildResult, ctx: BuildContext) -> str:
    project = (((ctx.get('spec') or {}).get('settings') or {}).get('project') or {})
    return project.get('maxFileName') or f"{result['model'].get('photoName') or 'Model'}.ms"


def _max_sources(model: dict, ctx: BuildContext) -> list[dict]:
    """The sources in the model's order (model.source = the floors' source names), for the upload profile's sentence."""
    by_name = {s['name']: s for s in ctx['sources']}
    out = [by_name[n] for n in model['source'] if n in by_name]
    return [{'kind': s['kind'], 'units': s['units']} for s in (out or ctx['sources'])]


def write_outputs(result: BuildResult, ctx: BuildContext, log, *, profile: str = 'upload') -> dict[str, Path]:
    """Writes every output file (contracts.write_outputs) -> {output name: path}."""
    t0 = time.perf_counter()
    out_dir = Path(ctx['outDir'])
    model = result['model']
    when = _now()
    built_at = when.strftime('%Y-%m-%dT%H:%M:%SZ')
    date = _ms.date_text(when.astimezone())               # the build's date, in this machine's time zone
    mb = model_bytes(model)
    stamp = hashlib.sha1(mb).hexdigest()[:12]
    files: dict[str, bytes] = {'model.json': mb}
    st = _replay.stages(result['replay'], model, result['report'])
    files['stages.json'] = _replay.stages_bytes(st)
    pres = _presentation.presentation(model)
    files['presentation.json'] = dumps(pres)
    log(f'model {stamp}: {len(model["parts"])} parts, {len(model["openings"])} openings, '
        f'{len(model.get("furniture") or [])} furniture boxes on {len(model["floors"])} floor(s)')
    ms_name = max_file_name(result, ctx)
    ms = _ms.maxscript(mb, _ms.load_profile(profile), date=date, sources=_max_sources(model, ctx),
                       converter=ctx.get('converter'))
    files[ms_name] = ms
    s = _ms.summary(model, ms)
    log(f'3ds Max script: {s["parts"]} live parts, {s["stairShapes"]} stair shapes, {s["rooms"]} room names, '
        f'{s["boxes"]} furniture boxes')
    files['topview.png'] = _pictures.topview_png(model)
    ov = _overlay.overlay(result, ctx)
    files['overlay.json'] = dumps(ov, pretty=False)
    fc = _overlay.flag_counts(ov)
    log(f'flags: {fc["total"]} ({fc["check"]} to check)' + (': ' + ', '.join(f'{k} {v}' for k, v in fc['byKind'].items())
                                                           if fc['byKind'] else ''))
    df = _diff.build_diff(model, ctx, log)
    files['diff.json'] = dumps(df, pretty=False)
    for a in df['against']:
        log(f'diff against {"the previous build" if a["kind"] == "previous-run" else "version " + a["ref"]}: '
            + ('no change' if _diff.empty(a['diff']) else
               f'{len(a["diff"]["partsAdded"])} parts added, {len(a["diff"]["partsRemoved"])} removed, '
               f'{len(a["diff"]["openingsAdded"])} openings added, {len(a["diff"]["openingsRemoved"])} removed, '
               f'{len(a["diff"]["openingsChanged"])} changed'))
    files['openings.json'] = dumps({'format': 'openings/1', 'floors': {k: list(v) for k, v in result['detector'].items()}},
                                   pretty=False)
    files['pieces.json'] = dumps({'format': 'furniture-placements/1', 'pieces': list(result['placements'])}, pretty=False)
    files['report.json'] = dumps(result['report'], pretty=False)
    seconds = dict(result.get('seconds') or {})
    seconds['outputs'] = round(time.perf_counter() - t0, 2)
    files['inputs.json'] = dumps(inputs_record(ctx, built_at, seconds))
    written: dict[str, Path] = {}
    for name, data in files.items():
        p = out_dir / name
        write_bytes(p, data)
        written[name] = p
    log(f'outputs written: {len(written)} files in {time.perf_counter() - t0:.1f} s')
    return written
