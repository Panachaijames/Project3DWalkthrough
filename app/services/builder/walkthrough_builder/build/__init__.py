"""The general builder: the port of bank_test/src/build_model.py (docs/upload/DESIGN.md U-9, U-10). Owner: U3.

    build(ctx, log, progress) -> BuildResult          (contracts.build; the TypedDicts of contracts.py, exactly)

Steps (JobRecord step names in brackets, reported through `progress(step, fraction)`):
  1. the settings coerced (U-10.4) and checked; each source's cache items loaded;
  2. set-asides removed from the sources before anything else (U-10.6), the floors' two readings made (U-9.1);
  3. [align] each floor lined up on floor 0 (U-9.4), from the sources' DrawingRead grid labels;
  4. [detect:<floor>] the detector on each floor's per-item reading (U-10.7), opening fixes applied (U-10.6);
  5. [walls] the bank builder's reading of each floor (walls, glass, screens, outline suggestions);
  6. [openings] the openings cut, closures, parapets, stairs, railings, plates, voids;
  7. [furniture] offset, parts, openings, probes, self-check, skins, rooms, furniture, the model and its summary;
     the report, the replay input, the detector records, the placements.
The bank's settings give the v2 model byte for byte (sha1 c3a9408304a2) and its summary in content.
"""
from __future__ import annotations

import json
import statistics
import time
from pathlib import Path

from ..contracts import BuildContext, BuildResult
from . import align as AL
from . import bank as BK
from . import fixes as FX
from . import furniture as FU
from . import items as I
from . import outline as OL
from . import report as RP
from . import settings as ST
from .detect import detect
from .errors import BuildError
from .model import assemble

__all__ = ['build', 'prepare_floors', 'BuildError']


class Context:
    """What was module state in the prototype (CFG, DEF, FURN, DOMINANT ...)."""

    def __init__(self, settings: dict):
        self.settings = settings
        self.DEF = settings['defaults']
        self.FURN = settings['furniture']
        self.options = settings['options']
        self.V = BK.Vocab(settings.get('vocabulary'))
        self.role_of = I.RoleOf(settings['layers'])
        self.outline = None
        self.DOMINANT = None
        self.DEFAULT_HEAD = self.DEF['doorHead']
        self.named: list[float] = []
        self.source_names: list[str] = []
        #: set by bank.build_floors_network (options.slabs 'network'): { fixes: the three new fix lists' rows,
        #: ceilings: bool, pairs }; None with the old rule
        self.new_rule: dict | None = None


def _read_json(path) -> dict | None:
    if not path:
        return None
    p = Path(path)
    if not p.exists():
        return None
    return json.loads(p.read_text(encoding='utf-8'))


class Floors(list):
    """What prepare_floors returns: the floors' working dicts, lowest first (each ready for bank.floor_walls), with
    everything else the preparation made as attributes: X (the Context), S (the coerced settings), seconds, t_walls
    (when step 5 started), src_ctx, det, det_out, sugg_by, align_reps, setaside_rows, open_rows, edge_rows."""


def prepare_floors(ctx: BuildContext, log=None, progress=None) -> Floors:
    """Steps 1 - 5 of build(): the settings, the sources, the set-asides, the floors' readings, the alignment, the
    detector with the opening fixes, and the bank builder's reading of each floor. Extracted from build() by the rooms
    scaffold R0 with no change in behaviour (docs/rooms/DESIGN.md R-12.3), so that the network and the stairs can be
    tested on a floor without the rest of the build: `floors = prepare_floors(ctx)`, then
    `bank.floor_walls(floors[i], floors.X)`."""
    log = log or (lambda _m: None)
    progress = progress or (lambda _s, _f: None)
    seconds: dict[str, float] = {}
    spec = ctx['spec']
    S = ST.coerce(spec['settings'])
    project_id = spec.get('projectId') or 'project'
    src_ctx = {s['sha1']: s for s in ctx['sources']}
    ST.check(S, set(src_ctx))
    X = Context(S)
    floors_cfg = S['floors']
    settings_src = {s['sha1']: s for s in S['sources']}

    # 1. the sources of the floors, in floor order
    t0 = time.perf_counter()
    order = []
    for f in floors_cfg:
        if f['source'] not in order:
            order.append(f['source'])
    X.source_names = [settings_src.get(sha, src_ctx[sha])['name'] for sha in order]
    caches, units, k_of = {}, {}, {}
    for sha in order:
        sc = src_ctx[sha]
        u = settings_src.get(sha, {}).get('units') or sc['units']
        if u not in I.UNITS:
            raise BuildError('bad_settings', f'{sc["name"]}: unknown units {u!r}')
        units[sha], k_of[sha] = u, I.UNITS[u]
        D = I.load_cache(sc['items'])
        caches[sha] = D
    floor_source = {f['key']: f['source'] for f in floors_cfg}

    # 2. set-asides first (U-10.6), then the two readings per floor (U-9.1)
    kept, setaside_rows, setaside_keys = FX.set_aside({sha: caches[sha]['items'] for sha in order}, k_of,
                                                      S['fixes']['setAside'], floor_source)
    readings = {}
    for sha in order:
        fl = [f for f in floors_cfg if f['source'] == sha]
        readings.update(I.read_floors(kept[sha], fl, units[sha], X.role_of, caches[sha]['layers']))
    seconds['read'] = round(time.perf_counter() - t0, 2)

    floors = []
    for f in floors_cfg:
        r = readings[f['key']]
        if not any(d['roles'] & {'wall', 'column'} for d in r['items']):
            raise BuildError('area_empty', f'{f["name"]}: its area holds nothing on a wall or column layer (check its '
                             f'area on the Floors step and the layer roles)', step='align')
        F = {'cfg': {**f}, 'items': r['items'], 'src': r['src'], 'n_layers': r['n_layers'],
             'subtreesOutside': r['subtreesOutside'], 'noPoints': r['noPoints'], 'source': f['source'],
             'units': units[f['source']], 'unit_m': I.UNITS_M[units[f['source']]],
             'slabThickness': f['slabThickness'] if f['slabThickness'] is not None else X.DEF['slabThickness'],
             'layer_lt': caches[f['source']]['layers']}
        floors.append(F)
    if S['options']['plinth'] == 'auto' and floors[0]['cfg']['level'] > 0:
        floors[0]['plinth'] = True                                 # U-9.5

    # the bank summary's own grid reading (before any shift)
    for i, F in enumerate(floors):
        F['grid'] = BK.grid_summary(floors[0]['items'], F['items'], i == 0)

    # 3. alignment (U-9.4)
    progress('align', 0.0)
    t0 = time.perf_counter()
    labels = {}
    for sha in order:
        dr = _read_json(src_ctx[sha].get('drawing'))
        labels[sha] = (dr or {}).get('gridLabels') or []
    align_reps = AL.align(floors_cfg, labels)
    for F, rep in zip(floors, align_reps):
        s = (float(rep['shift'][0]), float(rep['shift'][1]))
        F['shift'] = s
        if s != (0.0, 0.0):
            ids, uniq = set(), []
            for d in F['items'] + F['src']:
                if id(d) not in ids:
                    ids.add(id(d)); uniq.append(d)
            I.shift_items(uniq, *s)
            F['sheetShift'] = [round(-s[0], 3) + 0.0, round(-s[1], 3) + 0.0]
            if F['sheetShift'] == [0.0, 0.0]:
                F['sheetShift'] = None
    seconds['align'] = round(time.perf_counter() - t0, 2)
    progress('align', 1.0)

    # 4. the detector per floor, on the per-item reading of the kept items (sheet metres, before the shift)
    tmp = Path(ctx['tmpDir'])
    tmp.mkdir(parents=True, exist_ok=True)
    det, det_out = {}, {}
    open_fixes = list(enumerate(S['fixes']['openings']))
    open_rows = []
    for F in floors:
        key = F['cfg']['key']
        progress(f'detect:{key}', 0.0)
        sha = F['source']
        tag = I.tagger([f for f in floors_cfg if f['source'] == sha], k_of[sha])
        raw = [d for d in kept[sha] if tag(d) == key]
        res = detect(key, F['cfg']['name'], raw, k_of[sha], caches[sha]['layers'], S['layers'], project_id, tmp, log)
        det[key] = res
        seconds[f'detect:{key}'] = res['seconds']
        log(f'{F["cfg"]["name"]}: {len(res["records"])} openings found in {res["seconds"]:.1f} s')
        # opening fixes (U-10.6): matched on the records as detected (sheet m)
        mine = [(fi, f) for fi, f in open_fixes if f.get('floor') == key]
        matched = FX.match_openings(res['records'], mine)
        by_rec = {j: fi for fi, j in matched.items()}
        for fi, f in mine:
            j = matched.get(fi)
            open_rows.append({'fix': fi, 'matched': res['records'][j]['id'] if j is not None else None})
        ops, outs = [], []
        s = F['shift']
        for j, rec in enumerate(res['records']):
            fi = by_rec.get(j)
            fix = S['fixes']['openings'][fi] if fi is not None else None
            if fix is not None and fix.get('kind') == 'none':
                outs.append({'record': rec, 'modelId': None, 'fix': fi})
                continue
            o = dict(rec)
            o['a'] = [rec['a'][0] + s[0], rec['a'][1] + s[1]]; o['b'] = [rec['b'][0] + s[0], rec['b'][1] + s[1]]
            if fix is not None:
                if fix.get('kind'): o['kind'] = fix['kind']
                if fix.get('head') is not None: o['_head'] = fix['head']
                if fix.get('sill') is not None: o['_sill'] = fix['sill']
            ops.append(o)
            outs.append({'record': rec, 'modelId': rec['id'], 'fix': fi})
        F['ops'] = ops
        det_out[key] = outs
        progress(f'detect:{key}', 1.0)
    open_rows.sort(key=lambda r: r['fix'])
    for fi, f in open_fixes:
        if f.get('floor') not in det:
            open_rows.append({'fix': fi, 'matched': None})
    open_rows.sort(key=lambda r: r['fix'])

    # 5. the bank builder's reading of each floor; outline suggestions on the way (U-10.5)
    t0 = time.perf_counter()
    progress('walls', 0.0)
    edge_fixes = list(enumerate(S['fixes']['outlineEdges']))
    edge_rows, sugg_by = [], {}

    def outline(F, W):
        key = F['cfg']['key']
        mine = [(fi, f) for fi, f in edge_fixes if f.get('floor') == key]
        if S['options']['outlineWalls'] != 'suggest' and not mine:
            sugg_by[key] = []
            return [], []
        sg = OL.suggestions(F['items'], W, F['shift'])
        walls, glass, rows = OL.apply_fixes(sg, mine)
        edge_rows.extend(rows)
        sugg_by[key] = sg
        return walls, glass
    X.outline = outline
    for i, F in enumerate(floors):
        BK.read_floor(F, X)
        progress('walls', (i + 1) / len(floors))
    for fi, f in edge_fixes:
        if not any(r['fix'] == fi for r in edge_rows):
            edge_rows.append({'fix': fi, 'matched': False})
    edge_rows.sort(key=lambda r: r['fix'])
    # the most common door height among the door names of the whole drawing (U-10.4)
    X.named = [b['head'] for F in floors for b in F['door_blocks'] if b['head']]
    X.DOMINANT = statistics.mode(sorted(X.named)) if X.named else None
    X.DEFAULT_HEAD = X.DOMINANT or X.DEF['doorHead']
    log(f'door heads in the names: {len(X.named)}; doors without one get {X.DEFAULT_HEAD} '
        f'({"most common in the names" if X.DOMINANT else "project default"}) unless their floor gives one')

    seconds['walls'] = round(time.perf_counter() - t0, 2)
    BK.storeys(floors)                                   # what floor_walls reads: each floor's index and storey height
    out = Floors(floors)
    out.X, out.S, out.seconds, out.t_walls = X, S, seconds, t0
    out.src_ctx, out.det, out.det_out, out.sugg_by, out.align_reps = src_ctx, det, det_out, sugg_by, align_reps
    out.setaside_rows, out.open_rows, out.edge_rows = setaside_rows, open_rows, edge_rows
    return out


def build(ctx: BuildContext, log, progress) -> BuildResult:
    t_all = time.perf_counter()
    floors = prepare_floors(ctx, log, progress)
    X, seconds, t0 = floors.X, floors.seconds, floors.t_walls
    src_ctx, det, det_out, sugg_by, align_reps = floors.src_ctx, floors.det, floors.det_out, floors.sugg_by, floors.align_reps
    setaside_rows, open_rows, edge_rows = floors.setaside_rows, floors.open_rows, floors.edge_rows

    # 6. openings, walls, stairs, railings, plates
    t1 = time.perf_counter()
    progress('openings', 0.0)
    parts_geo, built = BK.build_floors(floors, X, log)
    progress('openings', 1.0)
    seconds['openings'] = round(time.perf_counter() - t1, 2)

    # 7. the model, the summary, the furniture
    t1 = time.perf_counter()
    progress('furniture', 0.0)
    A = assemble(floors, X, parts_geo, built, log)
    variants = FU.drawn_variants(A['furniture'], A['furn_pieces'], A['perm'])
    progress('furniture', 1.0)
    seconds['furniture'] = round(time.perf_counter() - t1, 2)
    seconds['build'] = round(time.perf_counter() - t0, 2)

    cx, cy = A['cx'], A['cy']
    shift_of = {F['cfg']['key']: F['shift'] for F in floors}
    sources_of = {F['cfg']['key']: F['source'] for F in floors}
    placements = FU.placements(A['furniture'], A['furn_pieces'], A['perm'], sources_of, shift_of, variants)
    report_floors, frames, replay_floors = {}, {}, {}
    sheet = RP.sheets(floors, A)
    for i, F in enumerate(floors):
        key = F['cfg']['key']
        s = F['shift']
        conv = _read_json(src_ctx[F['source']].get('conversion'))
        report_floors[key] = RP.floor_report(F, A, built[key], det[key], align_reps[i],
                                             RP.lost_inserts(conv, F['cfg']['area']),
                                             OL.public(sugg_by.get(key, [])), s)
        if 'report' in built[key]:                           # the new rule's keys (contracts.FloorUploadReportRooms)
            report_floors[key].update(built[key]['report'])
        frames[key] = {'source': F['source'], 'toSheet': [cx - s[0], cy - s[1]], 'area': F['cfg']['area']}
        replay_floors[key] = RP.replay_floor(F, A, sheet[key])
    door_from = {'name': 'name', 'floor': 'floor', 'most common': 'drawing', 'default': 'default', 'fix': 'fix'}
    report = {
        'summary': A['summary'],
        'floors': report_floors,
        'fixes': {'setAside': setaside_rows, 'openings': open_rows, 'outlineEdges': edge_rows},
        'doorHeadsFrom': {o['id']: door_from.get(o['headFrom'], o['headFrom']) for o in A['openings'] if o['kind'] == 'door'},
    }
    facts = RP.facts(floors, A, built, X, align_reps, replay_floors)
    if X.new_rule is not None:                               # the new rule (contracts.FixesReportRooms, ReplayFactsRooms)
        report['fixes'].update(X.new_rule['fixes'])
        facts.update(rooms={key: {'spaces': built[key]['report']['rooms']['spaces'],
                                  'named': built[key]['report']['rooms']['named']} for key in built},
                     climbable=len(A['model']['stairways']), ceilings=X.new_rule['ceilings'])
    seconds['total'] = round(time.perf_counter() - t_all, 2)
    log(f'built: {len(A["model"]["parts"])} parts, {len(A["openings"])} openings, {len(A["furniture"])} furniture boxes, '
        f'offset ({cx}, {cy}) in {seconds["total"]:.1f} s')
    return {
        'model': A['model'],
        'report': report,
        'replay': {'floors': replay_floors, 'facts': facts},
        'detector': det_out,
        'placements': placements,
        'floors_frame': frames,
        'seconds': seconds,
    }
