"""Read one floor of a flattened plan (the prims cache that the openings detector reads) and tag every item with the
roles the layer mapping gives its layer. Nothing in here knows about a particular drawing.

The cache (tools/prims.py) holds every model-space item with blocks unpacked, in drawing metres (DXF units / 1000):
  {t, lay, depth, path, h, area, pts | loops | ins+text | name+ins+rot+sx+sy (INSERT), closed, lt}
Roles (from the project file's "layers": {role: [layer name or glob pattern, ...]}):
  wall, column, glass, window, door, stair, stair-above, railing, room-name, grid, furniture, other, ignore
  (grid: only to check that the floors line up; furniture: one box per piece (rule 12), shown fading in the replay like
  the rest; other / ignore / no role: never built, shown fading in the replay)
"""
import fnmatch, math, pickle
from pathlib import Path

ROLES = ('wall', 'column', 'glass', 'window', 'door', 'stair', 'stair-above', 'railing', 'room-name', 'grid', 'furniture', 'other', 'ignore')
UNITS = {'mm': 1.0, 'cm': 10.0, 'm': 1000.0, 'in': 25.4, 'inch': 25.4, 'ft': 304.8}   # the cache is DXF units / 1000
CONTINUOUS = {'CONTINUOUS', 'BYLAYER', 'BYBLOCK', ''}


def role_matcher(layer_roles):
    """{role: [layer or glob, ...]} -> function(layer) -> frozenset of roles (case-insensitive)."""
    exact, pats = {}, []
    for role, names in (layer_roles or {}).items():
        if role not in ROLES: raise SystemExit(f'unknown layer role {role!r} (allowed: {", ".join(ROLES)})')
        for n in names:
            if any(ch in n for ch in '*?['): pats.append((n.upper(), role))
            else: exact.setdefault(n.upper(), set()).add(role)
    cache = {}

    def roles(layer):
        if layer not in cache:
            U = layer.upper()
            r = set(exact.get(U, ()))
            r.update(role for p, role in pats if fnmatch.fnmatchcase(U, p))
            cache[layer] = frozenset(r)
        return cache[layer]
    return roles


def linetype(d, layer_lt):
    lt = d.get('lt') or 'BYLAYER'
    if lt.upper() == 'BYLAYER': lt = layer_lt.get(d['lay'], 'Continuous') or 'Continuous'
    if lt.upper() == 'BYBLOCK': lt = 'Continuous'
    return lt


def is_continuous(lt):
    u = lt.upper().split('$')[-1]
    return u in CONTINUOUS or u.startswith('CONTINUOUS')


def _signature(d, nd=3):
    """Identical geometry on the same layer (a block inserted twice, copies) -> the same signature."""
    t = d['t']
    if t == 'INSERT':
        return (t, d['lay'], d['name'], round(d['ins'][0], nd), round(d['ins'][1], nd), round(d['rot'], 1), d['sx'], d['sy'], d['path'])
    if 'pts' in d:
        p = [(round(x, nd), round(y, nd)) for x, y in d['pts']]
        if t == 'LINE' or (not d.get('closed') and len(p) > 1 and p[0] > p[-1]): p = p[::-1]
        if d.get('closed') and len(p) > 2:
            k = p.index(min(p)); p = p[k:] + p[:k]
        return (t, d['lay'], tuple(p))
    if 'loops' in d:
        return (t, d['lay'], tuple(tuple((round(x, nd), round(y, nd)) for x, y in l) for l in d['loops']))
    if 'text' in d:
        return (t, d['lay'], d['text'], round(d['ins'][0], nd), round(d['ins'][1], nd))
    return (t, d['lay'], id(d))


def _scaled(d, k):
    if k == 1.0: return d
    d = dict(d)
    if 'pts' in d: d['pts'] = [[x * k, y * k] for x, y in d['pts']]
    if 'loops' in d: d['loops'] = [[[x * k, y * k] for x, y in l] for l in d['loops']]
    if 'ins' in d: d['ins'] = [d['ins'][0] * k, d['ins'][1] * k]
    return d


def load_floor(cache_path, area, layer_roles, units='mm'):
    """-> (items, layer linetypes, number of layers in use on this floor). Each item gets 'roles' (frozenset) and 'cont'
    (continuous linetype); duplicates (a block inserted twice, copies) are dropped. Ignored layers stay in the list
    (tagged 'ignore'): the builder never uses them, the build replay shows them fading."""
    with open(cache_path, 'rb') as f: D = pickle.load(f)
    roles = role_matcher(layer_roles)
    if units not in UNITS: raise SystemExit(f'unknown units {units!r} (allowed: {", ".join(UNITS)})')
    k = UNITS[units]
    seen, out = set(), []
    for d in D['items']:
        if d.get('area') != area: continue
        s = _signature(d)
        if s in seen: continue
        seen.add(s)
        d = dict(_scaled(d, k))
        d['roles'] = roles(d['lay'])
        d['cont'] = is_continuous(linetype(d, D['layers']))
        out.append(d)
    n_layers = len({d['lay'] for d in out})                    # layers in use on this floor
    return out, D['layers'], n_layers


def closed_ring(d):
    """The closed outline of a polyline / circle item, or None."""
    p = d.get('pts')
    if not p or len(p) < 3: return None
    if d.get('closed') or (len(p) > 3 and math.dist(p[0], p[-1]) < 1e-3): return p
    return None


def item_points(d):
    return d.get('pts') or [q for l in d.get('loops', []) for q in l] or ([d['ins']] if 'ins' in d else [])


def cache_info(cache_path):
    p = Path(cache_path)
    return {'file': p.name, 'folder': p.parent.name, 'bytes': p.stat().st_size}
