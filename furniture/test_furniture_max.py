"""Tests of furniture_max.py without 3ds Max (Agent C).  Run from anywhere:  python -B furniture/test_furniture_max.py

What is proven here, and what is not:
  * the fragments are produced from fixtures/mini_model.json and spliced into the REAL templates of the two Max script generators
    (bank_test/src/generate_maxscript.py, presidential_test/src/generate_maxscript.py): the integration recipe in furniture_max.py
    is applied to a copy of each generator in a temporary folder and the copy is run on a small synthetic model, so the anchors,
    the placeholders and the generator's own flow are exercised; the two COMPLETE test scripts are written to fixtures/. A generator
    that carries the recipe already (the bank's since 29 Oct, the suite's since 2 Nov) is run as it is, and its text from before the
    recipe is rebuilt by taking the recipe's insertions out again next to their anchors (unpatch), so the same checks hold in both
    states. The suite's generator names its one level 'suite' (the key its builder writes), so the suite's fixture is the mini
    model's level L1 under that key (suite-seat-001 ...);
  * a model without furniture gives exactly the script the unpatched generator gives; with furniture, the patched script differs
    only by inserted lines (nothing of the existing template is changed);
  * static checks of the scripts (lint, identifiers, argument counts, ASCII, brackets, every piece once, names, layers, spinners,
    the matrix3 numbers re-computed from the model, supports, no collapse / convert / modifier on boxes);
  * the rules of 29 Oct 2026 (audit): a spinner's start value rounds a half up and its range is 10 - 5000, the spinners stand two to
    a row with captions that fit, a user property with nothing to say holds the word none (never empty text), the node's bounding
    box is compared only for an unrotated box (rot 0: only there are the node's extents certainly the object's; for a turned box, a
    quarter turn included, it must not matter what Max reports as min / max, and base z, top z and the four corners must still catch a
    mirrored, wrongly turned, wrong-size or 90-versus-0-degree box), and "Furniture boxes only" reports in a message of its own;
  * the generated functions are RUN by a small MAXScript interpreter over a mock scene (fixtures/maxscript_lite.py): build,
    Apply, Update levels, Furniture-boxes-only, refusals.  That shows the logic does what is meant under the reading of 3ds Max
    written down in MockMax; it cannot show that Max agrees (3ds Max is not installed here, the 3D team runs the scripts).
"""
import ast, copy, difflib, json, math, os, re, shutil, subprocess, sys, tempfile
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(HERE)); sys.path.insert(0, str(HERE / 'fixtures'))
import furniture_max as fm
import maxscript_lite as ms
import maxscript_mock as mk

RESULTS = []


def check(name, ok, detail=''):
    RESULTS.append((name, bool(ok)))
    print(('PASS  ' if ok else 'FAIL  ') + name + (f'   [{detail}]' if detail and not ok else ''))
    return ok


def info(text): print('      ' + text)
def section(title): print(f'\n== {title}')


MINI = json.loads((HERE / 'fixtures' / 'mini_model.json').read_text(encoding='utf-8'))
OX, OY = MINI['offset']
PIECES = {p['id']: p for p in MINI['furniture']}
KINDS = {k['key']: k for k in MINI['furnitureKinds']}
BANK_SRC = ROOT / 'bank_test' / 'src' / 'generate_maxscript.py'
PRES_SRC = ROOT / 'presidential_test' / 'src' / 'generate_maxscript.py'
PRES_FLOOR = 'suite'                       # the suite's one level as its generator names it (the key its builder writes)


# ---- independent helpers (the README's formulas, not the module's code) ---------------------------------------------------

def matrix_rows(rot_deg, X, Y, Z):
    """README: matrix3 [cos,sin,0] [-sin,cos,0] [0,0,1] [X,Y,Z] (rows: the box's X, Y, Z axes, then its pivot)."""
    c, s = math.cos(math.radians(rot_deg)), math.sin(math.radians(rot_deg))
    return [[c, s, 0.0], [-s, c, 0.0], [0.0, 0.0, 1.0], [X, Y, Z]]


def xform(p, rows):
    """A point times a matrix3 (Max: row vector times matrix; the 4th row is the translation)."""
    return tuple(sum(p[i] * rows[i][j] for i in range(3)) + rows[3][j] for j in range(3))


def box_corners(w, d, rows):
    """The four base corners of a box (pivot in the middle of its base), counter-clockwise from (-w/2, -d/2)."""
    return [xform(q, rows)[:2] for q in ((-w / 2, -d / 2, 0), (w / 2, -d / 2, 0), (w / 2, d / 2, 0), (-w / 2, d / 2, 0))]


def split_atoms(s):
    """The space-separated arguments of a MAXScript command call: "strings", numbers, (groups), [points], #(arrays)."""
    atoms, i = [], 0
    while i < len(s):
        if s[i] == ' ': i += 1; continue
        j = i
        if s[i] == '"': j = s.index('"', i + 1) + 1
        elif s[i] in '([' or s.startswith('#(', i):
            j, depth = (i + 1 if s[i] == '#' else i), 0
            while True:
                if s[j] == '"': j = s.index('"', j + 1)
                elif s[j] in '([': depth += 1
                elif s[j] in ')]': depth -= 1
                j += 1
                if depth == 0: break
        else:
            while j < len(s) and s[j] != ' ': j += 1
        atoms.append(s[i:j]); i = j
    return atoms


def nums(s): return [float(x.strip('()')) for x in re.findall(r'\(?-?\d+\.\d+\)?', s)]
def strs(s): return re.findall(r'"([^"]*)"', s)
def camel(key): return ''.join(w.capitalize() for w in key.split('-'))
def half_up(v): return int(math.floor(v + 0.5))                      # README: whole mm, a half rounds up (Python's round() goes to even)
def is_unrotated(rot): return abs(math.sin(math.radians(rot))) < 1e-5 and math.cos(math.radians(rot)) > 0      # rot 0: the boxes whose node min / max are compared
def none_text(s): return fm.ascii_name(s or '') or 'none'            # a user property's text: ASCII, and the word none for nothing


def caption_of(k):
    """A spinner's caption by the rule, written out again: the label when it has at most 16 characters, else the key in words."""
    s = fm.ascii_name(k['label']).replace('&', 'and')
    return (s if 0 < len(s) <= 16 else k['key'].replace('-', ' ').capitalize()[:16]) + ':'


def global_array(text, name):
    m = re.search(rf'^global {name} = (#\(.*\))$', text, re.M)
    return m.group(1) if m else ''


# ---- the real generators, patched in a temporary folder -----------------------------------------------------------------

BANK_EDITS = [      # (anchor, where, inserted): the integration recipe of furniture_max.py, as edits of the generator's text
    ('global __PX___mats\n', 'after', '__FURN_GLOBALS__\n'),
    ('fn __PX___build =\n', 'before', '__FURN_FUNCTIONS__\n'),
    ('fn __PX___build =\n(\n', 'after', '__FURN_ADDONLY__\n'),
    ('    local origin = point name:"__PX___ORIGIN_DWG"', 'before', '__FURN_BUILD__\n'),
    ('__SPINNERS__\n', 'after', '__FURN_UI__\n'),
    ('        button col "Collapse all now (Editable Mesh)" width:300\n', 'after', '__FURN_UI_AFTER__\n'),
    ('        __PX___shift = if dwg.checked then [0.0, 0.0] else [__OX__, __OY__]\n', 'after', '__FURN_READ__\n'),
    (')\ncreateDialog __PX___UI\n', 'before', '__FURN_HANDLERS__\n'),
    ('HERE = Path(__file__).resolve().parent\n', 'after',
     "sys.path.insert(0, str(HERE.parent.parent / 'furniture')); import furniture_max\n"),
    ('levels = arr([f"{f[\'level\']:.2f}" for f in FLOORS])\n', 'before',
     "FURN, furn_problems = furniture_max.fragments(M, PX, FLOORS, f'{PX}_levels', ascii_name(M.get('shortName', M['project'])))\n"
     "problems += furn_problems\n"),
    ("script = (header + '\\n'.join(calls + lines + rooms) + footer)\n", 'after', 'script = furniture_max.splice(script, FURN)\n'),
    ("out.write_text(script, encoding='utf-8')\n", 'after', "print(FURN['summary'])\n"),
]
PRES_EDITS = [
    ('global PS_mats\n', 'after', '__FURN_GLOBALS__\n'),
    ('fn PS_build =\n', 'before', '__FURN_FUNCTIONS__\n'),
    ('fn PS_build =\n(\n', 'after', '__FURN_ADDONLY__\n'),
    ('    local origin = point name:"PS_ORIGIN_DWG"', 'before', '__FURN_BUILD__\n'),
    ('    spinner ht "Floor to floor (m):" range:[2.2, 15, __FTF__] type:#float fieldwidth:70\n', 'after', '__FURN_UI__\n'),
    ('        button col "Collapse all now (Editable Mesh)" width:300\n', 'after', '__FURN_UI_AFTER__\n'),
    ('        PS_shift = if dwg.checked then [0.0, 0.0] else [__OX__, __OY__]\n', 'after', '__FURN_READ__\n'),
    (')\ncreateDialog PS_UI\n', 'before', '__FURN_HANDLERS__\n'),
    ('HERE = Path(__file__).resolve().parent\n', 'after',
     "sys.path.insert(0, str(HERE.parent.parent / 'furniture')); import furniture_max\n"),
    ("rooms = [f'    PS_room \"{ascii_name(r[\"name\"])}\" {pt((r[\"x\"] + ox, r[\"y\"] + oy))}' for r in M['rooms']]\n", 'after',
     f"FURN, furn_problems = furniture_max.fragments(M, 'PS', [{{'key': '{PRES_FLOOR}'}}], '#(PS_level)', 'Presidential suite')\n"
     "problems += furn_problems\n"),
    ('out = Path(sys.argv[1])\n', 'before', 'script = furniture_max.splice(script, FURN)\n'),
    ("out.write_text(script, encoding='utf-8')\n", 'after', "print(FURN['summary'])\n"),
]


def patch(source, edits):
    """Apply the edits; every anchor must be found exactly once (None = the text already carries the integration)."""
    if 'furniture_max' in source: return None
    for anchor, where, text in edits:
        if source.count(anchor) != 1: raise AssertionError(f'anchor found {source.count(anchor)} times: {anchor[:60]!r}')
        source = source.replace(anchor, text + anchor if where == 'before' else anchor + text)
    return source


def unpatch(source, edits):
    """The generator as it was before the recipe: every inserted text taken out again next to its anchor (each found exactly once)."""
    for anchor, where, text in edits:
        joined = text + anchor if where == 'before' else anchor + text
        if source.count(joined) != 1: raise AssertionError(f'anchor with its inserted text found {source.count(joined)} times: {anchor[:60]!r}')
        source = source.replace(joined, anchor)
    return source


def rect(x0, y0, x1, y1): return [[round(x0, 3), round(y0, 3)], [round(x1, 3), round(y0, 3)], [round(x1, 3), round(y1, 3)], [round(x0, 3), round(y1, 3)]]


def mini_parts(floor_keys):
    """A slab and a wall per level around the furniture (a scene the furniture-only mode can read its levels from)."""
    parts = []
    for f in MINI['floors']:
        ps = [p for p in MINI['furniture'] if p['floor'] == f['key'] and f['key'] in floor_keys]
        if not ps: continue
        r = max(max(p['w'], p['d']) for p in ps) / 2 + 1.0
        x0, x1 = min(p['x'] for p in ps) - r, max(p['x'] for p in ps) + r
        y0, y1 = min(p['y'] for p in ps) - r, max(p['y'] for p in ps) + r
        parts.append({'kind': 'slab', 'floor': f['key'], 'label': '', 'o': rect(x0, y0, x1, y1), 'h': [], 'z0': -0.25, 'z1': 0.0, 'follow': False})
        parts.append({'kind': 'wall', 'floor': f['key'], 'label': '', 'o': rect(x0, y0 - 0.2, x1, y0), 'h': [], 'z0': 0.0, 'z1': f['wallHeight'], 'follow': True})
    return parts


def bank_model(with_furniture=True):
    B = {'project': MINI['project'], 'shortName': MINI['shortName'], 'source': ['mini_model.json'], 'units': 'm', 'offset': MINI['offset'],
         'maxPrefix': MINI['maxPrefix'], 'floors': MINI['floors'], 'parts': mini_parts({'L1', 'L2'}), 'stairs': {},
         'rooms': [{'label': 'Room A', 'x': 0.0, 'y': 0.0, 'floor': 'L1'}, {'label': 'Room B', 'x': 1.0, 'y': 1.0, 'floor': 'L2'}]}
    if with_furniture: B['furnitureKinds'], B['furniture'] = MINI['furnitureKinds'], MINI['furniture']
    return B


def on_level(pid, floor):
    """A fixture id of level L1 as it is on the first level of the script under test (L1 in the bank's, PRES_FLOOR in the suite's)."""
    return floor + pid[2:] if pid.startswith('L1-') else pid


def suite_furniture():
    """The mini model's level L1 as the suite's one level: floor PRES_FLOOR, ids and supports renamed (L1-seat-001 -> suite-seat-001)."""
    return [dict(p, floor=PRES_FLOOR, id=on_level(p['id'], PRES_FLOOR), on=p['on'] and on_level(p['on'], PRES_FLOOR))
            for p in MINI['furniture'] if p['floor'] == 'L1']


def pres_model(with_furniture=True):
    P = {'source': 'mini.dwg', 'units': 'm', 'offset': MINI['offset'], 'level': 0.0, 'floorToFloor': 3.0,
         'parts': mini_parts({'L1'}), 'rooms': [{'name': 'Room A', 'x': 0.0, 'y': 0.0}]}
    if with_furniture:
        ps = suite_furniture()
        kinds = [dict(k, count=sum(1 for p in ps if p['kind'] == k['key'])) for k in MINI['furnitureKinds']]
        P['furnitureKinds'], P['furniture'] = [k for k in kinds if k['count']], ps
    return P


def run_generator(which, model, edits):
    """Run a copy of the real generator on a synthetic model; return (script text, stdout). With edits: the generator with the recipe
    (a patched copy, or the real one when it carries the recipe already); without: the generator as it was before the recipe."""
    src, model_name, folder = (BANK_SRC, 'bank_model.json', 'bank_test') if which == 'bank' else (PRES_SRC, 'pres2_model.json', 'presidential_test')
    text = src.read_text(encoding='utf-8')
    carries = 'furniture_max' in text                      # the real generator has the recipe already
    if edits and not carries: text = patch(text, edits)
    elif not edits and carries: text = unpatch(text, BANK_EDITS if which == 'bank' else PRES_EDITS)
    tmp = Path(tempfile.mkdtemp(prefix='furn_max_'))
    try:
        gen = tmp / folder / 'src' / 'generate_maxscript.py'
        gen.parent.mkdir(parents=True)
        gen.write_text(text, encoding='utf-8')
        (gen.parent / model_name).write_text(json.dumps(model), encoding='utf-8')
        (tmp / 'furniture').mkdir()
        shutil.copy(HERE / 'furniture_max.py', tmp / 'furniture' / 'furniture_max.py')
        out = tmp / 'out.ms'
        r = subprocess.run([sys.executable, '-B', str(gen), str(out)], capture_output=True, text=True, encoding='utf-8',
                           env={**os.environ, 'PYTHONIOENCODING': 'utf-8'}, cwd=str(tmp))
        if r.returncode != 0: raise RuntimeError(f'generator failed:\n{r.stdout[-600:]}\n{r.stderr[-1500:]}')
        return out.read_bytes().decode('utf-8').replace('\r\n', '\n'), r.stdout
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ---- the checks ---------------------------------------------------------------------------------------------------------

def test_fragments_api():
    section('fragments() and splice(): the API')
    FR, pr = fm.fragments(MINI, 'FX', MINI['floors'], 'FX_levels', 'Fixture')
    check('mini model: no problems', pr == [], str(pr))
    check('mini model: the eight placeholders are all filled, as whole lines with no final newline',
          all(FR[k] and not FR[k].endswith('\n') and '\r' not in FR[k] for k in fm.PLACEHOLDERS))
    check('mini model: one call per piece', len(FR['calls']) == len(MINI['furniture']) == 17, f"{len(FR['calls'])} calls")
    info(FR['summary'])
    none = {k: v for k, v in MINI.items() if k not in ('furniture', 'furnitureKinds')}
    E, pr = fm.fragments(none, 'FX', MINI['floors'], 'FX_levels', 'Fixture')
    check('no furniture: no problems, every fragment empty', pr == [] and all(E[k] == '' for k in fm.PLACEHOLDERS) and E['calls'] == [])
    E2, pr2 = fm.fragments(dict(MINI, furniture=[], furnitureKinds=[]), 'FX', MINI['floors'], 'FX_levels', 'Fixture')
    check('empty furniture list: same as no furniture', pr2 == [] and all(E2[k] == '' for k in fm.PLACEHOLDERS))
    tmpl = ''.join(f'a{i}\n__FURN_{k.upper()}__\n' for i, k in enumerate(fm.PLACEHOLDERS))
    check('splice: empty fragments remove the placeholder lines and leave the rest',
          fm.splice(tmpl, E) == ''.join(f'a{i}\n' for i in range(len(fm.PLACEHOLDERS))))
    full = fm.splice(tmpl, FR)
    check('splice: each placeholder line becomes its fragment (once, whole lines)',
          all(FR[k] + '\n' in full for k in fm.PLACEHOLDERS) and '__FURN_' not in full)
    for label, bad in (('missing', tmpl.replace('__FURN_UI__\n', '')), ('twice', tmpl + '__FURN_UI__\n')):
        try: fm.splice(bad, FR); raised = False
        except ValueError: raised = True
        check(f'splice: a template with a placeholder line {label} raises', raised)


def test_problems():
    section('invalid data is reported (the generator stops, as for parts)')
    def piece(M, pid): return next(p for p in M['furniture'] if p['id'] == pid)
    def kind(M, key): return next(k for k in M['furnitureKinds'] if k['key'] == key)
    cases = [
        ('unknown kind', lambda M: piece(M, 'L1-seat-001').update(kind='sofa'), "unknown kind 'sofa'"),
        ('unknown level', lambda M: piece(M, 'L1-seat-001').update(floor='L9'), "unknown level 'L9'"),
        ('id used twice', lambda M: piece(M, 'L1-seat-002').update(id='L1-seat-001'), 'id used twice'),
        ('id not <level>-<kind>-<nnn>', lambda M: piece(M, 'L1-seat-001').update(id='seat-1'), 'id is not'),
        ('colour not #rrggbb', lambda M: kind(M, 'seat').update(colour='orange'), 'colour'),
        ('size zero', lambda M: piece(M, 'L1-seat-001').update(w=0), 'must be above 0'),
        ('x not a number', lambda M: piece(M, 'L1-seat-001').update(x=float('nan')), 'must be numbers'),
        ('rot missing', lambda M: piece(M, 'L1-seat-001').pop('rot'), 'must be numbers'),
        ('a support on a support', lambda M: piece(M, 'L1-table-002').update(on='L1-table-001'), 'cannot stand on another piece'),
        ('standing on a non-support', lambda M: piece(M, 'L1-computer-001').update(on='L1-seat-001'), 'not a support kind'),
        ('standing on nothing in the list', lambda M: piece(M, 'L1-computer-001').update(on='L1-table-009'), 'not in the list'),
        ('standing on a support of another level', lambda M: piece(M, 'L2-computer-001').update(on='L1-table-001'), 'another level'),
        ('count does not match', lambda M: kind(M, 'seat').update(count=5), 'count 5 but 4 pieces'),
        ('kind table empty', lambda M: M.update(furnitureKinds=[]), 'unknown kind'),
        ('kind key not words-with-hyphens', lambda M: kind(M, 'seat').update(key='Seat'), 'key must be'),
        ('kind height zero', lambda M: kind(M, 'seat').update(height=0), 'height must be'),
        ('kind base negative', lambda M: kind(M, 'tv').update(base=-5), 'base must be'),
        ('floor listed twice', lambda M: M.update(floors=[MINI['floors'][0], MINI['floors'][0]]), 'listed twice'),
    ]
    for label, mutate, want in cases:
        M = copy.deepcopy(MINI); mutate(M)
        pr = fm.fragments(M, 'FX', M['floors'], 'FX_levels', 'Fixture')[1]
        check(f'problem: {label}', any(want in p for p in pr), f'wanted {want!r}, got {pr[:3]}')
    pr = fm.fragments(MINI, 'F X', MINI['floors'], 'FX_levels', 'Fixture')[1]
    check('problem: a prefix with a space', any('prefix' in p for p in pr))
    FR, pr = fm.fragments(copy.deepcopy(MINI), 'FX', MINI['floors'], 'FX_levels', 'Fixture')
    M = copy.deepcopy(MINI); piece(M, 'L1-seat-001').update(w=0)
    FR, pr = fm.fragments(M, 'FX', M['floors'], 'FX_levels', 'Fixture')
    check('with problems every fragment is empty (nothing half-built can be spliced)', all(FR[k] == '' for k in fm.PLACEHOLDERS))


def test_rules():
    section('the audit fixes of 29 Oct: rounding, range, captions, two columns, none for nothing')
    spin = re.compile(r'^        spinner (fh\d+) "([^"]*)"( across:2)? range:\[(\d+), (\d+), (\d+)\] type:#integer fieldwidth:40$', re.M)

    def run(mutate):
        M = copy.deepcopy(MINI); mutate(M)
        FR, pr = fm.fragments(M, 'FX', M['floors'], 'FX_levels', 'Fixture')
        return M, FR, pr, spin.findall(FR['ui'])
    def kind(M, key): return next(k for k in M['furnitureKinds'] if k['key'] == key)
    def piece(M, pid): return next(p for p in M['furniture'] if p['id'] == pid)

    # D4: a half rounds up, as the viewer and the CSV do (Python's round() would give 740 and 460 for these two)
    typed = {'table': 740.5, 'coffee-table': 460.5, 'seat': 450.5, 'tv': 600.5, 'plant': 600.49, 'computer': 449.5, 'cabinet': 899.9}
    def set_typed(M):
        for k in M['furnitureKinds']: k['height'] = typed.get(k['key'], k['height'])
    M, FR, pr, sp = run(set_typed)
    keys = [k['key'] for k in M['furnitureKinds']]
    got = {keys[i]: int(s[5]) for i, s in enumerate(sp)}
    want = {'table': 741, 'coffee-table': 461, 'seat': 451, 'tv': 601, 'plant': 600, 'computer': 450, 'cabinet': 900}
    check('D4: spinner start values round a half up: office heights 740.5 / 460.5 / 450.5 / 600.5 give 741 / 461 / 451 / 601 (Python round() gives '
          f'{round(740.5)} / {round(460.5)} / {round(450.5)} / {round(600.5)}), 600.49 gives 600, 449.5 gives 450, 899.9 gives 900', pr == [] and all(got.get(k) == v for k, v in want.items()), f'{got}')
    hs = nums(global_array(FR['globals'], 'FX_furnHeights'))
    check('D4: the heights the boxes are built with (FX_furnHeights, metres) are the same whole mm: 0.7410, 0.4610, 0.4510', len(hs) == len(keys) and all(abs(h - half_up(k['height']) / 1000) < 1e-9 for h, k in zip(hs, M['furnitureKinds'])) and abs(hs[keys.index('table')] - 0.741) < 1e-9, str(hs))
    check('D4: the viewer\'s whole() and the CSV agree: half_up(740.5) = 741, half_up(460.5) = 461', half_up(740.5) == 741 and half_up(460.5) == 461)

    # the range: 10 - 5000, widened only to hold a start value outside it
    M, FR, pr, sp = run(lambda M: None)
    check('the range of every spinner is 10 - 5000 mm, as in the viewer\'s text box (it was 10 - 6000)', pr == [] and sp and all((s[3], s[4]) == ('10', '5000') for s in sp), str([(s[3], s[4]) for s in sp][:3]))
    def extremes(M): kind(M, 'seat')['height'] = 5200; kind(M, 'plant')['height'] = 5.4; kind(M, 'tv')['height'] = 5000; kind(M, 'cabinet')['height'] = 10
    M, FR, pr, sp = run(extremes)
    by = {keys[i]: s[3:] for i, s in enumerate(sp)}
    check('a start value outside 10 - 5000 widens the range just enough to hold it (5200 -> [10, 5200, 5200], 5.4 -> [5, 5000, 5]); 5000 and 10 stay in 10 - 5000',
          by.get('seat') == ('10', '5200', '5200') and by.get('plant') == ('5', '5000', '5') and by.get('tv') == ('10', '5000', '5000') and by.get('cabinet') == ('10', '5000', '10'), str(by))
    for h, ok_expected in ((0.4, False), (0.5, True), (0, False), (-5, False)):
        M, FR, pr, sp = run(lambda M: kind(M, 'seat').update(height=h))
        check(f'a kind height of {h} mm is {"accepted (rounds to 1)" if ok_expected else "refused: it would round to a box of no height"}', (pr == []) == ok_expected, str(pr[:1]))

    # captions
    M, FR, pr, sp = run(lambda M: None)
    caps = [s[1] for s in sp]
    check('captions: the label when it has 16 characters at most, else the kind\'s key in words, then a colon (the group title says mm)',
          caps == ['Computer:', 'Printer / copier:', 'TV / wall screen:', 'Curtain:', 'Plant:', 'Chair / stool:', 'Table / desk:', 'Coffee table:', 'Cabinet:', 'Tall cabinet:'], str(caps))
    def labels(M):
        kind(M, 'seat')['label'] = 'Fish & chips'; kind(M, 'plant')['label'] = 'Salt & pepper mills'; kind(M, 'curtain')['label'] = ''
        kind(M, 'tv')['label'] = 'โต๊ะ'; kind(M, 'printer')['label'] = 'Sixteen letters!!'; kind(M, 'computer')['label'] = 'Sixteen letters!'
    M, FR, pr, sp = run(labels)
    by = {keys[i]: s[1] for i, s in enumerate(sp)}
    check('captions: & becomes "and" (it would underline a letter), a label that is too long, empty or not ASCII falls back to the key in words, a label of exactly 16 characters stays',
          by.get('seat') == 'Fish and chips:' and by.get('plant') == 'Plant:' and by.get('curtain') == 'Curtain:' and by.get('tv') == 'Tv:' and by.get('printer') == 'Printer:'
          and by.get('computer') == 'Sixteen letters!:' and all(len(c) <= 17 for c in by.values()), str(by))

    # two columns
    check('two columns: across:2 on spinners 1, 3, 5, 7, 9 of 10 (each has a partner), none on 2, 4, 6, 8, 10', [bool(s[2]) for s in sp] == [True, False] * 5)
    def one_less(M):                                                         # nine kinds: the last spinner stands alone
        M['furnitureKinds'] = [k for k in M['furnitureKinds'] if k['key'] != 'curtain']; M['furniture'] = [p for p in M['furniture'] if p['kind'] != 'curtain']
    M9, FR9, pr9, sp9 = run(one_less)
    check('two columns: with 9 kinds spinner 9 stands alone and has no across:2 (it would pull the next control into its row)', pr9 == [] and len(sp9) == 9 and [bool(s[2]) for s in sp9] == [True, False] * 4 + [False], str([bool(s[2]) for s in sp9]))
    check('two columns: every spinner keeps its name fhN, its order and its group (names fb, fo, fol and fap are untouched)',
          [s[0] for s in sp] == [f'fh{i + 1}' for i in range(10)] and all(w in FR['ui'] + FR['ui_after'] for w in ('checkbox fb ', 'checkbox fo ', 'label fol ')) and 'button fap ' in FR['ui_after'])

    # D5 / risk 6: none for nothing
    def nothing(M):
        p = piece(M, 'L1-seat-001'); p.update(block='', layer='', handle='', family='โต๊ะ')
    M, FR, pr, sp = run(nothing)
    call = next(c for c in FR['calls'] if '"L1-seat-001"' in c)
    a = split_atoms(call.split('FX_furnBox ', 1)[1])
    check('the word none for an absent value: a piece on nothing, with no block, layer or handle and a family that is not ASCII, passes "none" for support id, support kind, family, block, layer and handle',
          pr == [] and [strs(a[i])[0] for i in (4, 5, 12, 13, 14, 15)] == ['none'] * 6 and '""' not in call, call[-120:])
    on_call = next(c for c in FR['calls'] if '"L1-computer-001"' in c)
    b = split_atoms(on_call.split('FX_furnBox ', 1)[1])
    check('... and a piece on a support passes the support\'s id and kind', [strs(b[i])[0] for i in (4, 5)] == ['L1-table-001', 'table'])
    check('none is the module\'s word for it, and "none" is not a kind (a kind with that key is refused: the word would be a support)', fm.NONE == 'none')
    pr = fm.fragments(dict(MINI, furnitureKinds=[dict(k, key='none') if k['key'] == 'seat' else k for k in MINI['furnitureKinds']]), 'FX', MINI['floors'], 'FX_levels', 'Fixture')[1]
    check('problem: a kind called none', any('the word none' in x for x in pr), str(pr[:2]))


def test_ascii_name():
    section('ascii_name / num / pt agree with the generators')
    for label, path in (('bank', BANK_SRC), ('suite', PRES_SRC)):
        tree = ast.parse(path.read_text(encoding='utf-8'))
        ns = {'unicodedata': __import__('unicodedata')}
        for node in tree.body:
            if isinstance(node, ast.FunctionDef) and node.name in ('ascii_name', 'num', 'pt', 'arr'):
                exec(compile(ast.Module([node], []), str(path), 'exec'), ns)
        samples = ['Chair A685 2', 'say "hi" \\ back', 'Tổ hợp Khách Ăn', 'm² panel · low', 'tab\there  two  spaces', 'plain-ASCII_1.2', '']
        diffs = [s for s in samples if ns['ascii_name'](s) != fm.ascii_name(s)]
        # the module is the union of both spellings: it may differ only where the generator keeps a character the other one maps
        legit = {'bank': ['Tổ hợp Khách Ăn'], 'suite': ['m² panel · low']}[label]
        check(f'ascii_name vs the {label} generator (same except the other spelling\'s own characters)', all(d in legit for d in diffs), str(diffs))
        vals = [0.0, 1.0, -1.5, 3.14159, 190.523, -3494.655, 0.00004, 12.34565]
        check(f'num / pt vs the {label} generator', all(ns['num'](v) == fm.num(v) for v in vals if v != 0.00004) and
              ns['pt']((1.0, -2.5)) == fm.pt((1.0, -2.5)) and ns['arr'](['a', 'b']) == fm.arr(['a', 'b']))
    check('num never writes -0.0000 and numx keeps 9 decimals', fm.num(-0.00004) == '0.0000' and fm.numx(-1e-12) == '0.000000000' and fm.numx(-0.5) == '(-0.500000000)')
    check('ascii_name cleans quotes and backslashes like the generators', fm.ascii_name('a "b" \\ c') == "a 'b' / c")


def test_rehearsal():
    section('the recipe applied to the REAL generators (copies in a temporary folder, synthetic model)')
    out = {}
    for which, edits, model in (('bank', BANK_EDITS, bank_model), ('suite', PRES_EDITS, pres_model)):
        w = 'bank' if which == 'bank' else 'pres'
        try:
            base, _ = run_generator(w, model(False), None)
            same, _ = run_generator(w, model(False), edits)
            full, stdout = run_generator(w, model(True), edits)
        except AssertionError as e:
            check(f'{which}: every anchor of the recipe is found exactly once in the generator', False, str(e)); continue
        except RuntimeError as e:
            check(f'{which}: the generator runs', False, str(e)); continue
        check(f'{which}: every anchor of the recipe is found exactly once in the generator', True)
        check(f'{which}: a model without furniture gives byte for byte the script it gave before', same == base, f'{len(same)} vs {len(base)} chars')
        stamp = lambda t: re.sub(r'model data [0-9a-f]{12}', 'model data <sha1 of the model file>', t).splitlines()       # the model file changed: so does its stamp
        ops = [o for o in difflib.SequenceMatcher(None, stamp(base), stamp(full), autojunk=False).get_opcodes() if o[0] != 'equal']
        check(f'{which}: with furniture the script differs from the old one only by inserted lines', ops and all(o[0] == 'insert' for o in ops), str([o[0] for o in ops]))
        info(f'{which}: {len(ops)} insertions, {sum(o[4] - o[3] for o in ops)} new lines, {len(base)} -> {len(full)} characters')
        check(f'{which}: the generator printed the furniture summary', 'furniture boxes' in stdout, stdout[-200:])
        check(f'{which}: no placeholder is left', not re.search(r'__[A-Z]+(_[A-Z]+)*__', full), str(re.findall(r'__[A-Z_]+__', full)[:3]))
        out[which] = {'base': base, 'full': full}
    return out


def parse_script(text, px, pieces, kinds, floors):
    """Read the generated script back: arrays, call lines, spinners."""
    S = {}
    S['keys'], S['layers'], S['floors'] = (strs(global_array(text, f'{px}_furn{n}')) for n in ('Keys', 'Layers', 'Floors'))
    S['bases'], S['heights'] = (nums(global_array(text, f'{px}_furn{n}')) for n in ('Bases', 'Heights'))
    S['calls'] = []
    for m in re.finditer(rf'^    {px}_furnBox (.*)$', text, re.M):
        a = split_atoms(m.group(1))
        S['calls'].append({'raw': m.group(1), 'atoms': a, 'kind': strs(a[0])[0], 'name': strs(a[1])[0], 'fi': int(a[2]), 'pid': strs(a[3])[0],
                           'supId': strs(a[4])[0] if strs(a[4]) else '', 'supKind': strs(a[5])[0] if strs(a[5]) else '', 'c': nums(a[6]),
                           'w': nums(a[7])[0], 'd': nums(a[8])[0], 'ca': nums(a[9])[0], 'sa': nums(a[10])[0],
                           'cs': [tuple(nums(q)) for q in re.findall(r'\[[^\]]*\]', a[11])], 'fam': strs(a[12])[0] if strs(a[12]) else '',
                           'blk': strs(a[13])[0] if strs(a[13]) else '', 'lay': strs(a[14])[0] if strs(a[14]) else '',
                           'hnd': strs(a[15])[0] if strs(a[15]) else ''})
    S['spinners'] = re.findall(r'^        spinner (fh\d+) "([^"]*)"( across:2)? range:\[(\d+), (\d+), (\d+)\] type:#integer fieldwidth:40$', text, re.M)
    return S


def test_script(label, text, px, pieces, kinds, floors, offset):
    section(f'static checks of the {label} script ({len(text) // 1024} KB, px {px})')
    ox, oy = offset
    FI = {f: i + 1 for i, f in enumerate(floors)}
    S = parse_script(text, px, pieces, kinds, floors)
    occurring = [k for k in MINI['furnitureKinds'] if any(p['kind'] == k['key'] for p in pieces.values())]

    # text hygiene and the lint
    check(f'{label}: ASCII only', all(ord(c) < 128 for c in text))
    toks, terr = ms.tokenize(text)
    check(f'{label}: every quote closes on its line, no unreadable character', terr == [], str(terr[:3]))
    _, _, serr = ms.structure(toks)
    check(f'{label}: brackets and parentheses balanced and nested right', serr == [], str(serr[:3]))
    check(f'{label}: ( ) [ ] and quote counts even (the generators\' own sanity line)', text.count('(') == text.count(')') and text.count('[') == text.count(']') and text.count('"') % 2 == 0)
    lerr = ms.lint(text)
    check(f'{label}: token lint (if/then/else, for/do, case/of, fn, try/catch, local/global)', lerr == [], str(lerr[:5]))
    aerr = ms.arity_errors(text)
    check(f'{label}: every call of a script function has as many arguments as the function has parameters', aerr == [], str(aerr[:5]))
    n_arity = len(S['calls'])
    check(f'{label}: the furnBox calls were found and checked ({n_arity})', n_arity == len(pieces))

    # pieces and names
    ids = [c['pid'] for c in S['calls']]
    check(f'{label}: every piece appears exactly once', sorted(ids) == sorted(pieces) and len(set(ids)) == len(ids), f'{len(ids)} calls for {len(pieces)} pieces')
    names = [c['name'] for c in S['calls']]
    check(f'{label}: object names are unique', len(set(n.lower() for n in names)) == len(names))
    ok = True
    for c in S['calls']:
        p = pieces[c['pid']]
        m = re.fullmatch(rf'{px}_{p["floor"]}_Furn_{re.escape(p["kind"])}_(\d{{3,}})(?:_(.{{1,40}}))?', c['name'])
        ok &= bool(m) and c['pid'].endswith('-' + m.group(1)) and fm.ascii_name(p['family'])[:40].rstrip(' _-') == (m.group(2) or '') and c['name'].isascii()
    check(f'{label}: name = <px>_<floor>_Furn_<kind>_<nnn>_<family, ASCII, at most 40 characters>, nnn = the id\'s number', ok)
    check(f'{label}: no double quote, backslash or control character in any argument', all(not re.search(r'[\\\x00-\x1f]', c['raw'].replace('"', '')) for c in S['calls']))

    # kinds, layers, spinners
    check(f'{label}: kind arrays in the model\'s order, only kinds that occur', S['keys'] == [k['key'] for k in occurring], str(S['keys']))
    check(f'{label}: layer suffix = the kind key in CamelCase', S['layers'] == [camel(k['key']) for k in occurring], str(S['layers']))
    check(f'{label}: floors array = the floor keys in order', S['floors'] == list(floors))
    layers = {f'{px}_{p["floor"]}_Furn_{camel(p["kind"])}' for p in pieces.values()}
    got = {f'{px}_{S["floors"][c["fi"] - 1]}_Furn_{S["layers"][S["keys"].index(c["kind"])]}' for c in S['calls']}
    check(f'{label}: layer of every box = <px>_<floor>_Furn_<Kind> ({len(got)} layers)', got == layers, f'{sorted(got ^ layers)}')
    check(f'{label}: spinner count = kinds that occur ({len(S["spinners"])})', len(S['spinners']) == len(occurring))
    ok = all(cap == caption_of(k) and int(d) == half_up(k['height']) and (int(lo), int(hi)) == (min(10, int(d)), max(5000, int(d))) and name == f'fh{i + 1}'
             for i, ((name, cap, _, lo, hi, d), k) in enumerate(zip(S['spinners'], occurring)))
    check(f'{label}: spinner i = kind i: start value = the kind\'s height in whole mm (a half rounds up), range 10 - 5000, caption = the label (16 characters at most) or the key in words', ok)
    n_sp = len(S['spinners'])
    check(f'{label}: the spinners stand two to a row: across:2 on each one that has a partner (1, 3, 5 ...), none on the partners and on a last one that stands alone ({n_sp} spinners, {(n_sp + 1) // 2} rows)',
          all((across == ' across:2') == (i % 2 == 0 and i + 1 < n_sp) for i, (_, _, across, _, _, _) in enumerate(S['spinners'])))
    width = int(re.search(rf'^rollout {px}_UI "[^"]*" width:(\d+)$', text, re.M).group(1))
    room = (width - 32) / 2 - (40 + 14 + 6)                      # half the window (an estimate of both margins: 32 px) less the 40 px field, its arrows and a gap
    check(f'{label}: every caption fits its half of the {width} px window (an estimate: {room:.0f} px beside the field at 5.5 px a character) and every spinner has a 40 px field',
          all(len(cap) * 5.5 <= room and line.endswith('fieldwidth:40') for (name, cap, *rest), line in zip(S['spinners'], re.findall(r'^        spinner fh\d+ .*$', text, re.M))))
    check(f'{label}: heights and bases arrays = the model\'s mm / 1000',
          all(abs(h - k['height'] / 1000) < 1e-9 and abs(b - k['base'] / 1000) < 1e-9 for h, b, k in zip(S['heights'], S['bases'], occurring)))
    reads = [re.findall(r'(fh\d+)\.value / 1000\.0', ln) for ln in re.findall(r'^\s+' + px + r'_furnHeights = (#\(\(fh.*)$', text, re.M)]
    want = [f'fh{i + 1}' for i in range(len(occurring))]
    check(f'{label}: the code that reads the spinners (Build and Apply) reads fh1..fh{len(occurring)} in kind order, in mm / 1000', len(reads) == 2 and all(r == want for r in reads), str(reads))
    check(f'{label}: material per kind named "<px> Furn <key>" with the kind\'s colour',
          all(re.search(rf'standardMaterial name:"{px} Furn {re.escape(k["key"])}" diffuse:\(color {" ".join(str(int(k["colour"][j:j + 2], 16)) for j in (1, 3, 5))}\)\)', text) for k in occurring))

    # the matrix and the corners, from the model by the README's formulas
    mline = re.search(r'^    o\.transform = (.*)$', text, re.M).group(1)
    want_m = f'(matrix3 [ca, sa, 0.0] [(0.0 - sa), ca, 0.0] [0.0, 0.0, 1.0] [c.x - {px}_shift.x, c.y - {px}_shift.y, zb])'
    check(f'{label}: the transform is the explicit matrix3 [cos,sin,0] [-sin,cos,0] [0,0,1] [X,Y,Z] with X = c.x - shift.x', mline == want_m, mline)
    fbox = fn_text(text, f'{px}_furnBox').split('\n')
    hits = [l for l in fbox if 'o.min.x' in l]
    check(f'{label}: the node\'s min / max in the plan are compared once, and only for an unrotated box (sin of the rotation below 0.00001 and cos positive); base z, top z and the four corners for every box',
          '    local unrotated = abs(sa) < 0.00001 and ca > 0.0' in fbox and len(hits) == 1 and hits[0].startswith('    else if unrotated and (abs(o.min.x') and hits[0].endswith('then why = "bounding box"')
          and any('then why = "base z"' in l for l in fbox) and any('then why = "top z"' in l for l in fbox) and any('why = "corner " + (k as string)' in l for l in fbox), hits[0][:80] if hits else 'no line')
    check(f'{label}: the script says the rule in its header and in the comment above the checks (only for an unrotated box) and nowhere speaks of a multiple of 90 degrees or of a quarter turn rule',
          text.count('only for an unrotated box') == 2 and 'multiple of 90' not in text and 'quarterTurn' not in text, str(text.count('only for an unrotated box')))
    worst = {'c': 0.0, 'cs': 0.0, 'cs_model': 0.0, 'ca': 0.0}
    for c in S['calls']:
        p = pieces[c['pid']]
        rows = matrix_rows(p['rot'], p['x'] + ox, p['y'] + oy, 0.0)                    # from the model (README)
        rows_e = [[c['ca'], c['sa'], 0.0], [-c['sa'], c['ca'], 0.0], [0.0, 0.0, 1.0], [c['c'][0], c['c'][1], 0.0]]           # from the emitted numbers
        model_c, emit_c, given = box_corners(p['w'], p['d'], rows), box_corners(c['w'], c['d'], rows_e), c['cs']
        worst['c'] = max(worst['c'], abs(c['c'][0] - (p['x'] + ox)), abs(c['c'][1] - (p['y'] + oy)), abs(c['w'] - p['w']), abs(c['d'] - p['d']))
        worst['ca'] = max(worst['ca'], abs(c['ca'] - rows[0][0]), abs(c['sa'] - rows[0][1]))
        for a, b, g in zip(model_c, emit_c, given):
            worst['cs'] = max(worst['cs'], math.dist(a, b), math.dist(b, g))
            worst['cs_model'] = max(worst['cs_model'], math.dist(a, g))
    check(f'{label}: centre and size = the model (+ offset), to 1e-4 m (worst {worst["c"]:.1e})', worst['c'] < 1e-4)
    check(f'{label}: cos and sin = the model\'s rot, to 1e-9 (worst {worst["ca"]:.1e})', worst['ca'] < 1e-9)
    check(f'{label}: corners implied by the emitted matrix3 and size = corners from the model by the README = the check corners (worst {worst["cs"]:.1e} m)', worst['cs'] < 2e-4 and worst['cs_model'] < 2e-4)
    check(f'{label}: the numbers have no stray minus (negative numbers are in brackets) and none is written in e-notation',
          all(not re.search(r'(?<![(\w.])-\d', c['raw'].replace('"', ' ')) and 'e-' not in re.sub(r'"[^"]*"', '', c['raw']) for c in S['calls']))

    # z: supports
    bad = []
    for c in S['calls']:
        p = pieces[c['pid']]; k = kinds[p['kind']]
        want_z = (kinds[pieces[p['on']]['kind']]['base'] + kinds[pieces[p['on']]['kind']]['height']) / 1000 if p['on'] else k['base'] / 1000
        ki = S['keys'].index(c['kind']); oki = S['keys'].index(c['supKind']) + 1 if c['supKind'] in S['keys'] else 0
        got = S['bases'][oki - 1] + S['heights'][oki - 1] if oki else S['bases'][ki]
        if abs(got - want_z) > 1e-9 or c['supId'] != (p['on'] or 'none') or (oki and c['supKind'] != pieces[p['on']]['kind']) or (not oki and p['on']): bad.append((c['pid'], got, want_z))
    n_on = sum(1 for p in pieces.values() if p['on'])
    check(f'{label}: z0 resolves right for all {len(pieces)} pieces ({n_on} stand on a support: its top = base + current height; the TV hangs at its base)', not bad, str(bad[:3]))
    absent = [(c['pid'], i) for c in S['calls'] for i, v in enumerate((c['supId'], c['supKind'], c['fam'], c['blk'], c['lay'], c['hnd'])) if v == '']
    n_none = sum(1 for c in S['calls'] if 'none' in (c['supId'], c['blk'], c['hnd']))
    check(f'{label}: a support, block, layer, handle or family that is absent is written as the word none, never as an empty string ({n_none} boxes carry one; 3ds Max documents no getUserProp value for empty text)',
          not absent and all('""' not in c['raw'] and c['supId'] == (pieces[c['pid']]['on'] or 'none') and c['blk'] == none_text(pieces[c['pid']]['block'])
                             and c['hnd'] == none_text(pieces[c['pid']]['handle']) and c['lay'] == none_text(pieces[c['pid']]['layer'])
                             and c['fam'] == none_text(pieces[c['pid']]['family']) for c in S['calls']), str(absent[:3]))
    fz = re.search(rf'^fn {px}_furnZ0 ki oki =\n\(\n(.*?)\n\)\n', text, re.M | re.S).group(1)
    check(f'{label}: furnZ0 = the kind\'s base, or the support kind\'s base + height, never a chain',
          fz == f'    local z0 = {px}_furnBases[ki]\n    if oki > 0 do z0 = {px}_furnBases[oki] + {px}_furnHeights[oki]\n    z0', fz)
    return S


def fn_text(text, name):
    m = re.search(rf'^fn {name}\b.*?(?=^fn |^try \(|\Z)', text, re.M | re.S)
    return m.group(0) if m else ''


def test_collapse_update(label, text, px, upd_name, collapse_name, has_floor_loop):
    section(f'{label}: collapse and update leave boxes alone, or move them as intended')
    furn = '\n'.join(fn_text(text, f'{px}_furn{n}') for n in ('Num', 'MakeMaterials', 'SetLevels', 'Z0', 'Box', 'All', 'Run', 'SceneLevels', 'Add', 'Apply'))
    check(f'{label}: the furniture code has no convertTo / collapseStack / Editable / addModifier / snapshot (a box stays a live Box)',
          not re.search(r'convertTo|collapseStack|Editable|addModifier|snapshotAsMesh|Extrude|splineShape', furn, re.I))
    check(f'{label}: nothing in the furniture code reads the collapse tick box or sets {px}_kind', f'{px}_collapse' not in furn and f'"{px}_kind"' not in furn)
    check(f'{label}: a box is created with the Box primitive, one per call', furn.count(' = box name:nm width:w length:d height:ht') == 1 and furn.count('box name:') == 1)
    col = fn_text(text, collapse_name)
    check(f'{label}: "Collapse all now" only picks objects that carry {px}_kind and have a modifier (a box has neither)',
          f'where (getUserProp o "{px}_kind") != undefined and o.modifiers.count > 0' in col, col[:200])
    parts_collapse = [m.start() for m in re.finditer(r'convertToMesh', text)]
    inside_part = fn_text(text, f'{px}_part')
    check(f'{label}: convertToMesh appears only in {px}_part (after the tick box) and {collapse_name}',
          len(parts_collapse) == inside_part.count('convertToMesh') + col.count('convertToMesh') and f'if {px}_collapse do convertToMesh o' in inside_part)
    box = fn_text(text, f'{px}_furnBox')
    props = dict(re.findall(rf'setUserProp o "{px}_(\w+)" (.*)$', box, re.M))
    check(f'{label}: a box carries {px}_floor (fi), {px}_base (z0) and {px}_follow = false, as the parts do',
          props.get('floor') == 'fi' and props.get('base') == 'z0' and props.get('follow') == 'false', str({k: props.get(k) for k in ('floor', 'base', 'follow')}))
    want_props = ['furn', 'furnKind', 'furnId', 'furnOn', 'furnOnKind', 'family', 'block', 'layer', 'handle', 'floor', 'base', 'follow', 'check']
    check(f'{label}: all the user properties of the task are set on every box: {", ".join(want_props)}', all(p in props for p in want_props), str(sorted(props)))
    check(f'{label}: {px}_furn is the string true; the box\'s z uses the same z0 as {px}_base', props.get('furn') == '"true"' and 'local zb = ' + f'{px}_furnLevels[fi] + z0' in box)
    upd = fn_text(text, upd_name)
    if has_floor_loop:
        check(f'{label}: "Update levels and heights" visits every object that carries {px}_floor and puts it at level + {px}_base',
              f'where (getUserProp o "{px}_floor") != undefined do' in upd and f'o.pos.z = newLevels[fi] + base' in upd)
        check(f'{label}: ... and only touches a height when {px}_follow is "true" (a box has false)', f'if ((getUserProp o "{px}_follow") as string) == "true" do' in upd)
    else:
        check(f'{label}: "Update heights" only visits objects whose {px}_follow is "true" (a box has false) and no level moves',
              f'where ((getUserProp o "{px}_follow") as string) == "true" do' in upd and 'pos.z' not in upd)
    return furn


def test_new_constructs(label, base_text, full_text):
    section(f'{label}: what the furniture code uses that the shipped script does not')
    shipped_names = ms.unresolved(base_text)
    mine = ms.unresolved(full_text)
    new_names = sorted(mine - shipped_names)
    _, props_b, kw_b = ms.words(ms.tokenize(base_text)[0])
    _, props_f, kw_f = ms.words(ms.tokenize(full_text)[0])
    new_props, new_kw = sorted(props_f - props_b, key=str.lower), sorted(kw_f - kw_b, key=str.lower)
    known_names = {'box', 'matrix3', 'findItem', 'floor', 'matchPattern', 'Box', 'integer'}      # integer: "as integer" (the bank script has it, the suite's not)
    known_props = {'transform', 'width', 'length', 'height', 'layer', 'name', 'systemScale', 'x', 'y', 'z', 'value', 'checked', 'count', 'min', 'max'}
    known_kw = {'width', 'length', 'height', 'pattern', 'tooltip', 'across'}              # across: the rollout layout keyword of the two-column spinners
    check(f'{label}: every word that is not a script name, a control or a word the shipped script uses was reviewed ({", ".join(new_names)})', set(new_names) <= known_names, str(set(new_names) - known_names))
    info('new functions / classes: ' + ', '.join(new_names))
    info('new properties after a dot: ' + ', '.join(new_props))
    info('new keyword arguments: ' + ', '.join(new_kw))
    check(f'{label}: new properties and keyword arguments were reviewed', set(new_props) <= known_props and set(new_kw) <= known_kw, f'{set(new_props) - known_props} {set(new_kw) - known_kw}')


def test_lint_sensitivity(full):
    section('the lint finds slips that are put in on purpose (so a clean result means something)')
    px = 'FX'
    slips = [
        ('a then is missing', lambda t: t.replace('if oki > 0 do z0', 'if oki > 0 z0', 1), 'lint'),
        ('an else without if', lambda t: t.replace('    local why = ""\n', '    local why = ""\n    else why = "x"\n', 1), 'lint'),
        ('a ) is missing', lambda t: t.replace('        local hw = o.width / 2.0\n', '        local hw = (o.width / 2.0\n', 1), 'lint'),
        ('a quote is missing', lambda t: t.replace('setUserProp o "FX_furnId" pid', 'setUserProp o "FX_furnId pid', 1), 'lint'),
        ('a for without do', lambda t: t.replace('for k = 1 to 4 do', 'for k = 1 to 4', 1), 'lint'),
        ('a name is misspelt once', lambda t: t.replace('FX_furnHeights[ki]\n    local zb', 'FX_furnHeigths[ki]\n    local zb', 1), 'names'),
        ('a parameter is dropped from a call', lambda t: re.sub(r'(\n    FX_furnBox "[^\n]*) "A1"\n', r'\1\n', t, count=1), 'arity'),
        ('a local is used before its name is typed right', lambda t: t.replace('local zb = ', 'local zbb = ', 1), 'names'),
        ('try without catch', lambda t: t.replace('        catch (messageBox (getCurrentException()) title:"Build stopped")\n', '', 1), 'lint'),
    ]
    base_unres = ms.unresolved(full)
    for label, f, kind in slips:
        t = f(full)
        check(f'lint sensitivity: {label}', t != full and ((kind == 'lint' and ms.lint(t)) or (kind == 'arity' and ms.arity_errors(t)) or
                                                      (kind == 'names' and ms.unresolved(t) - base_unres)), 'not noticed')


# ---- the generated functions, run by the interpreter over a mock scene ---------------------------------------------------------

def rgb(colour): return tuple(int(colour[j:j + 2], 16) for j in (1, 3, 5))
def close(a, b, tol): return abs(a - b) <= tol


def controls_for(S, values=None, want=True, only=False):
    """The rollout controls the handlers read: spinners fh1..fhN (mm, default = the model's heights) and the two tick boxes."""
    vals = values or [int(s[-1]) for s in S['spinners']]
    c = {f'fh{i + 1}': mk.Control(value=v) for i, v in enumerate(vals)}
    c.update(fb=mk.Control(checked=want), fo=mk.Control(checked=only))
    return c


def install_fakes(it, px, suite, part_floor=True):
    """The template's own part and room builders need splines and modifiers; stand-ins make the same nodes the real ones do
    (position = level + z0, user properties <px>_kind / _floor / _base / _follow) so that Update levels and the datum can be tried."""
    def level(fi): return it.get('PS_level') if suite else it.get(f'{px}_levels')[fi - 1]

    def part(it, kind, nm, loops, z0, z1, follow, *rest):
        fi, c = (1, rest[0]) if suite else (rest[0], rest[1])
        sh, n = it.get(f'{px}_shift'), mk.Node(it.scene, mk.Cls('SplineShape'), nm)
        n.tm.rows[3] = mk.P(c.v[0] - sh.v[0], c.v[1] - sh.v[1], level(fi) + z0)
        n.props.update({f'{px}_kind': str(kind), f'{px}_base': mk.tostr(z0), f'{px}_follow': mk.tostr(follow)})
        if part_floor: n.props[f'{px}_floor'] = str(fi)
        it.get(f'{px}_nodes').append(n)
        return n

    def room(it, nm, p, *rest):
        fi = 1 if suite else rest[0]
        sh, n = it.get(f'{px}_shift'), mk.Node(it.scene, mk.Cls('Text'), f'{px}_Room_{nm}')
        n.tm.rows[3] = mk.P(p.v[0] - sh.v[0], p.v[1] - sh.v[1], level(fi) + 0.02)
        n.props.update({f'{px}_base': '0.02'})
        if part_floor: n.props[f'{px}_floor'] = str(fi)
        it.get(f'{px}_nodes').append(n)
        return n
    it.override(f'{px}_part', part); it.override(f'{px}_room', room)


def make_run(text, px, suite, frags, S, shift=(0.0, 0.0), values=None, want=True, only=False, scene=None, part_floor=True, level=None):
    it = mk.Interp(text, scene)
    install_fakes(it, px, suite, part_floor)
    it.run(frags['read'], **controls_for(S, values, want, only))            # the code of the Build handler that reads the window
    it.set(f'{px}_shift', mk.P(*shift))
    if level is not None: it.set('PS_level', level)
    return it


def boxes_of(it, px): return {n.props[f'{px}_furnId']: n for n in it.scene.objects if f'{px}_furn' in n.props}


READINGS = (('the true world box', {}),                    # what Max reports as min / max of a TURNED node: nothing in Autodesk's text says which
            ('x and y 5 m too far', {'bbox_error_turned': {'min': {'x': 5.0, 'y': 5.0}, 'max': {'x': 5.0, 'y': 5.0}}}),
            ('the box pulled in by 1 m on every side, as if it were not turned', {'bbox_error_turned': {'min': {'x': 1.0, 'y': 1.0}, 'max': {'x': -1.0, 'y': -1.0}}}),
            ('the extents of the box as if it were not turned', {'bbox_unturned': True}))


def angle_only(deg):
    """The call's cos and sin for another angle (the corners stay the model's): a box built at the wrong angle."""
    r = math.radians(deg)
    return {'ca': round(math.cos(r), 9), 'sa': round(math.sin(r), 9)}


def turned_to(a, deg):
    """A really different box: the same centre and size turned to `deg`, with its own cos, sin and corners (all consistent)."""
    ch = angle_only(deg)
    (cx, cy), hw, hd = a['c'], a['w'] / 2, a['d'] / 2
    ch['cs'] = [(cx + ch['ca'] * u - ch['sa'] * v, cy + ch['sa'] * u + ch['ca'] * v) for u, v in ((-hw, -hd), (hw, -hd), (hw, hd), (-hw, hd))]
    return ch


def build_one(text, px, suite, frags, S, levels, piece_id, flags=None, **change):
    """One box built from its call with some arguments changed (what a wrong build would look like), in a scene whose min / max
    behave as `flags` says: (its {px}_check property, the name of its layer)."""
    sc = mk.Scene()
    for flag, v in (flags or {}).items(): setattr(sc, flag, v)
    it = make_run(text, px, suite, frags, S, scene=sc, level=levels[0] if suite else None)
    it.run(f'{px}_furnMakeMaterials()\n{px}_furnSetLevels()')
    a = dict(next(c for c in S['calls'] if c['pid'] == piece_id), **change)
    it.call(f'{px}_furnBox', a['kind'], a['name'], a['fi'], a['pid'], a['supId'], a['supKind'], mk.P(*a['c']), a['w'], a['d'], a['ca'], a['sa'],
            [mk.P(*q) for q in a['cs']], a['fam'], a['blk'], a['lay'], a['hnd'])
    n = boxes_of(it, px)[piece_id]
    return n.props[f'{px}_check'], n.layer.name


def box_report(it, px, pieces, kinds, floors, levels, shift, mm=None, skip_props=()):
    """Compare every box of the scene with what the README says it must be; returns (problems, worst deviation in m)."""
    mm, bad, worst = mm or {}, [], 0.0
    FI = {f: i + 1 for i, f in enumerate(floors)}
    found = boxes_of(it, px)
    if sorted(found) != sorted(pieces): bad.append(f'boxes {len(found)} != pieces {len(pieces)}')
    for pid, n in found.items():
        p = pieces[pid]; k = kinds[p['kind']]
        z0 = (kinds[pieces[p['on']]['kind']]['base'] + mm.get(pieces[p['on']]['kind'], kinds[pieces[p['on']]['kind']]['height'])) / 1000 if p['on'] else k['base'] / 1000
        h, z = mm.get(p['kind'], k['height']) / 1000, levels[floors.index(p['floor'])] + z0
        rows = matrix_rows(p['rot'], p['x'] + OX - shift[0], p['y'] + OY - shift[1], z)
        if n.cls.name != 'Box': bad.append(f'{pid}: not a Box ({n.cls.name})')
        if n.modifiers: bad.append(f'{pid}: has modifiers')
        for i in range(4):
            d = max(abs(a - b) for a, b in zip(n.tm.rows[i].v, rows[i])); worst = max(worst, d if i == 3 else 0.0)
            if d > (2e-4 if i == 3 else 1e-8): bad.append(f'{pid}: matrix row {i + 1} off by {d:.2e}')
        for key, want in (('width', p['w']), ('length', p['d']), ('height', h)):
            if not close(n.params[key], want, 1e-9 if key == 'height' else 1e-4): bad.append(f'{pid}: {key} {n.params[key]} != {want}')
        base = sorted(c.v[:2] for c in n.corners() if abs(c.v[2] - z) < 1e-9)
        want_c = sorted(box_corners(p['w'], p['d'], rows))
        if len(base) != 4 or max(math.dist(a, b) for a, b in zip(base, want_c)) > 2e-4: bad.append(f'{pid}: base corners differ from the README\'s')
        lay = f'{px}_{p["floor"]}_Furn_{camel(p["kind"])}'
        if n.layer is None or n.layer.name != lay: bad.append(f'{pid}: layer {n.layer and n.layer.name} != {lay}')
        if n.material is None or n.material.name != f'{px} Furn {p["kind"]}' or n.material.diffuse != mk.Color(*rgb(k['colour'])) or n.wirecolor != n.material.diffuse:
            bad.append(f'{pid}: material / wire colour')
        want_props = {'furn': 'true', 'furnKind': p['kind'], 'furnId': pid, 'furnOn': p['on'] or 'none', 'furnOnKind': pieces[p['on']]['kind'] if p['on'] else 'none',
                      'family': none_text(p['family']), 'block': none_text(p['block']), 'layer': none_text(p['layer']), 'handle': none_text(p['handle']),
                      'floor': str(FI[p['floor']]), 'follow': 'false', 'check': 'ok'}
        for key, want in want_props.items():
            if key not in skip_props and n.props.get(f'{px}_{key}') != want: bad.append(f'{pid}: property {key} = {n.props.get(f"{px}_{key}")!r}, wanted {want!r}')
        if not close(float(n.props[f'{px}_base']), z0, 1e-5): bad.append(f'{pid}: {px}_base {n.props[f"{px}_base"]} != {z0}')
    return bad, worst


def test_dynamic(label, text, px, suite, frags, S, pieces, floors, levels, update_levels=None):
    section(f'{label}: the generated functions run on a mock 3ds Max (interpreter in fixtures/maxscript_mock.py)')
    kinds = KINDS
    build = f'{px}_build'
    default_mm = {k['key']: half_up(k['height']) for k in MINI['furnitureKinds']}
    # 1. a whole Build (normal mode) in an empty scene, the dialog's own reading code first
    try:
        it = make_run(text, px, suite, frags, S, shift=(0.0, 0.0), level=levels[0] if suite else None)
        ok = it.call(build)
    except mk.MaxError as e:
        check(f'{label}: Build runs to the end in an empty scene', False, str(e)); return
    check(f'{label}: Build runs to the end in an empty scene and returns true', ok is True, str(ok))
    bad, worst = box_report(it, px, pieces, kinds, floors, levels, (0.0, 0.0))
    check(f'{label}: Build (DWG coordinates): all {len(pieces)} boxes are Box objects with the README\'s position, rotation, size, z, layer, material, wire colour and properties (worst position error {worst:.1e} m)', not bad, '; '.join(bad[:4]))
    failed = it.get(f'{px}_failed')
    check(f'{label}: Build: every box passed its checks (nothing in {px}_failed, nothing on {px}_Check_Failed, no message box)', failed == [] and px.lower() + '_check_failed' not in it.scene.layers and it.scene.messages == [], str(failed[:2]))
    nodes = it.get(f'{px}_nodes')
    check(f'{label}: Build: the furniture is part of the node list the footer selects and counts ({len(nodes)} nodes: parts, rooms and {len(pieces)} boxes), and the hidden datum is made after it',
          sum(1 for n in nodes if f'{px}_furn' in n.props) == len(pieces) and any(n.name == f'{px}_ORIGIN_DWG' for n in it.scene.objects))
    check(f'{label}: Build: the Listener says how many objects were built and how many checks failed', any('BUILD COMPLETE' in s and s.rstrip().endswith('0 failed checks') for s in it.scene.listener), str(it.scene.listener[-2:]))
    # 2. the same with the drawing's own coordinates switched off (shift = the offset)
    it2 = make_run(text, px, suite, frags, S, shift=(OX, OY), level=levels[0] if suite else None)
    it2.call(build)
    bad, worst = box_report(it2, px, pieces, kinds, floors, levels, (OX, OY))
    check(f'{label}: Build centred on the origin (shift = offset): positions follow, no check fails', not bad and it2.get(f'{px}_failed') == [], '; '.join(bad[:3]))
    # 3. furniture unticked: Build is the old Build
    it3 = make_run(text, px, suite, frags, S, want=False, level=levels[0] if suite else None)
    it3.call(build)
    check(f'{label}: "Build furniture boxes" unticked: no box, no furniture layer, no furniture material', boxes_of(it3, px) == {} and not any('_furn_' in k for k in it3.scene.layers) and not any(m for m in [it3.get(f'{px}_furnMats')]))
    # 4. the spinners: spinner i is kind i, mm / 1000
    odd = [1000 + 10 * i for i in range(len(S['spinners']))]
    it4 = make_run(text, px, suite, frags, S, values=odd, level=levels[0] if suite else None)
    keys = S['keys']
    check(f'{label}: the code that reads the window sets each kind\'s height from its own spinner (spinner i -> kind i, mm / 1000)',
          all(close(h, odd[i] / 1000, 1e-9) for i, h in enumerate(it4.get(f'{px}_furnHeights'))) and it4.get(f'{px}_furnWant') is True and it4.get(f'{px}_furnAddOnly') is False)
    it4.call(build)
    bad, _ = box_report(it4, px, pieces, kinds, floors, levels, (0.0, 0.0), mm={k: odd[i] for i, k in enumerate(keys)})
    check(f'{label}: Build with other heights typed in: every box has its kind\'s typed height and the boxes on supports stand on the typed support heights', not bad, '; '.join(bad[:3]))
    # 5. Apply furniture heights after the build
    mm = {k: 1000 + 10 * i for i, k in enumerate(keys)}
    mm.update(table=800, **{'coffee-table': 400})
    vals = [mm[k] for k in keys]
    def lose(value):                                                  # after the build the boxes on nothing hold `value` (None: no such property) as their support
        def f(it):
            for pid, n in boxes_of(it, px).items():
                if pieces[pid]['on']: continue
                for key in (f'{px}_furnOn', f'{px}_furnOnKind'):
                    if value is None: n.props.pop(key, None)
                    else: n.props[key] = value
        return f
    variants = (('the word none reads back as the text', {}, None),
                ('the word none reads back as undefined: Max may not read it', {'none_is_undefined': True}, None),
                ('the support properties are missing: undefined', {}, lose(None)),
                ('the support properties are empty text, read back as text', {}, lose('')),
                ('the support properties are empty text, read back as undefined', {'empty_prop_is_undefined': True}, lose('')))
    for how, flags, after in variants:
        sc = mk.Scene()
        for flag, v in flags.items(): setattr(sc, flag, v)
        it5 = make_run(text, px, suite, frags, S, scene=sc, level=levels[0] if suite else None)
        it5.call(build)
        if after: after(it5)
        it5.run(frags['handlers'].split('\n', 1)[1], **controls_for(S, vals))        # the body of  on fap pressed do
        bad, _ = box_report(it5, px, pieces, kinds, floors, levels, (0.0, 0.0), mm=mm, skip_props=('furnOn', 'furnOnKind') if after else ())
        msg = it5.scene.messages[-1][0] if it5.scene.messages else ''
        check(f'{label}: "Apply furniture heights" ({how}): new heights, boxes re-seated on their supports or on their kind\'s base, message "{len(pieces)} furniture boxes set ..."',
              not bad and msg.startswith(f'{len(pieces)} furniture boxes set to the heights') and 'left alone' not in msg, '; '.join(bad[:3]) + msg)
    n_on = [(pid, n) for pid, n in boxes_of(it5, px).items() if pieces[pid]['on']]
    sup_top = {pid: boxes_of(it5, px)[pieces[pid]['on']].params['height'] for pid, _ in n_on}
    check(f'{label}: Apply: a box on a table sits at the table\'s new top (table 750 -> 800 mm: z = level + 0.800), a box on nothing stays at its base ({len(n_on)} on supports)',
          all(close(n.tm.rows[3].v[2], levels[floors.index(pieces[pid]['floor'])] + 0.8, 1e-5) for pid, n in n_on if pieces[pid]['kind'] != 'x' and pieces[pieces[pid]['on']]['kind'] == 'table')
          and close(boxes_of(it5, px)[on_level('L1-tv-001', floors[0])].tm.rows[3].v[2], levels[0] + 0.9, 1e-9))
    # 6. Apply leaves a box that is no longer a Box, and a kind it does not know, alone
    sc = mk.Scene(); it6 = make_run(text, px, suite, frags, S, scene=sc, level=levels[0] if suite else None); it6.call(build)
    b = boxes_of(it6, px)
    victim = b[on_level('L1-seat-001', floors[0])]; victim.cls = mk.Cls('Editable_Mesh'); victim.props[f'{px}_furnKind'] = 'sofa-bed'
    it6.run(frags['handlers'].split('\n', 1)[1], **controls_for(S, vals))
    msg = it6.scene.messages[-1][0]
    check(f'{label}: Apply leaves objects alone that are not Boxes any more or of an unknown kind, and says how many', msg.startswith(f'{len(pieces) - 1} furniture boxes') and '1 were left alone' in msg and victim.params['height'] == 0.45)
    # 7. Collapse all now: boxes are never picked; a part with a modifier is
    it7 = make_run(text, px, suite, frags, S, level=levels[0] if suite else None); it7.call(build)
    part = next(n for n in it7.scene.objects if f'{px}_kind' in n.props); part.modifiers.append('Extrude')
    got = it7.call(f'{px}_collapseAll')
    check(f'{label}: "Collapse all now" converts the part that has a modifier and no box (converted: {got}, boxes converted: {sum(1 for n in it7.scene.converted if f"{px}_furn" in n.props)})', got == 1 and it7.scene.converted == [part])
    # 8. Update levels (bank): the shipped function moves every object that carries <px>_floor, boxes included, heights untouched
    if update_levels:
        new_levels, new_heights = [0.0, 4.5], [3.7, 3.7]
        it8 = make_run(text, px, suite, frags, S, level=None); it8.call(build)
        it8.run(frags['handlers'].split('\n', 1)[1], **controls_for(S, vals))
        before = {pid: (n.tm.rows[3].v[2], n.params['height']) for pid, n in boxes_of(it8, px).items()}
        r = it8.call(update_levels, list(new_levels), list(new_heights))
        after = {pid: (n.tm.rows[3].v[2], n.params['height']) for pid, n in boxes_of(it8, px).items()}
        moved = all(close(after[pid][0] - before[pid][0], (4.5 - 3.7) if pieces[pid]['floor'] == 'L2' else 0.0, 1e-5) and after[pid][1] == before[pid][1] for pid in pieces)
        check(f'{label}: "Update levels and heights" (level 2 from 3.70 to 4.50 m) moves the {sum(1 for p in pieces.values() if p["floor"] == "L2")} boxes of level 2 up 0.80 m and touches no box height', moved, str([(k, before[k], after[k]) for k in pieces if not close(after[k][0] - before[k][0], 0.8 if pieces[k]['floor'] == 'L2' else 0.0, 1e-5)][:2]))
        it8.run(frags['handlers'].split('\n', 1)[1], **controls_for(S, [d + 5 for d in vals]))
        bad, _ = box_report(it8, px, pieces, kinds, floors, new_levels, (0.0, 0.0), mm={k: vals[i] + 5 for i, k in enumerate(keys)})
        check(f'{label}: ... and Apply after it keeps each box on its moved level (z = level + new support top)', not bad, '; '.join(bad[:3]))
    return kinds


def test_failure_paths(label, text, px, suite, frags, S, pieces, floors, levels):
    section(f'{label}: a box that fails its check goes on {px}_Check_Failed, is listed, and the rest is still built')
    own_id = lambda pid: on_level(pid, floors[0])                           # the fixture's L1 ids on this script's first level
    p = pieces[own_id('L1-seat-002')]                                       # rotated 30 degrees
    cases = [('base z', {'min': {'z': 0.01}}, 'base z'), ('top z', {'max': {'z': -0.01}}, 'top z')]
    for name, err, reason in cases:
        sc = mk.Scene()
        it = make_run(text, px, suite, frags, S, scene=sc, level=levels[0] if suite else None)
        sc.bbox_error = err                                                  # the mock Max reports a wrong bounding box for every box
        ok = it.call(f'{px}_build')
        failed = it.get(f'{px}_failed')
        b = boxes_of(it, px)
        check(f'{label}: reason "{reason}": all boxes still built ({len(b)}), all on {px}_Check_Failed with that reason, all listed, Listener lists them, Build still returns true',
              ok is True and len(b) == len(pieces) and len(failed) == len(pieces) and all(n.layer.name == f'{px}_Check_Failed' and n.props[f'{px}_check'] == reason for n in b.values())
              and all(f.endswith(': ' + reason) for f in failed) and sum(1 for s in sc.listener if s.startswith('  check failed')) == len(pieces), f'{len(failed)} {failed[:1]}')
    # a wrong corner (the right bounding box, the wrong rotation): the corner check sees it
    sc = mk.Scene()
    it = make_run(text, px, suite, frags, S, scene=sc, level=levels[0] if suite else None)
    it.run(f'{px}_furnMakeMaterials()\n{px}_furnSetLevels()')
    a = S['calls'][0]
    cs = [mk.P(*q) for q in a['cs']]
    bad_cs = [cs[1], cs[0], cs[2], cs[3]]                                   # corners 1 and 2 swapped: the same bounding box
    it.call(f'{px}_furnBox', a['kind'], a['name'], a['fi'], a['pid'], a['supId'], a['supKind'], mk.P(*a['c']), a['w'], a['d'], a['ca'], a['sa'], bad_cs,
            a['fam'], a['blk'], a['lay'], a['hnd'])
    n = boxes_of(it, px)[a['pid']]
    check(f'{label}: reason "corner 1": the corner check notices a mirrored box that the bounding-box check cannot ({n.props[f"{px}_check"]!r}, layer {n.layer.name})',
          n.props[f'{px}_check'] == 'corner 1' and n.layer.name == f'{px}_Check_Failed')
    sc = mk.Scene()
    it = make_run(text, px, suite, frags, S, scene=sc, level=levels[0] if suite else None)
    it.run(f'{px}_furnMakeMaterials()\n{px}_furnSetLevels()')
    a = next(c for c in S['calls'] if c['pid'] == own_id('L1-seat-002'))    # turned 30 degrees: its mirror image has the same bounding box
    it.call(f'{px}_furnBox', a['kind'], a['name'], a['fi'], a['pid'], a['supId'], a['supKind'], mk.P(*a['c']), a['w'], a['d'], a['ca'], -a['sa'],
            [mk.P(*q) for q in a['cs']], a['fam'], a['blk'], a['lay'], a['hnd'])
    n = boxes_of(it, px)[a['pid']]
    check(f'{label}: a rotation of the wrong sign (sin negated, 30 degrees) is caught by the corner check ({n.props[f"{px}_check"]!r}), not by the bounding box',
          n.props[f'{px}_check'].startswith('corner') and n.layer.name == f'{px}_Check_Failed')
    # the bounding box (the node's min and max): compared for an unrotated box only
    unrot = {pid for pid, q in pieces.items() if is_unrotated(q['rot'])}
    n90 = sum(1 for q in pieces.values() if abs(q['rot'] - 90) < 1e-9)
    sc = mk.Scene()
    it = make_run(text, px, suite, frags, S, scene=sc, level=levels[0] if suite else None)
    sc.bbox_error = {'max': {'x': 0.01}}                                    # the mock Max reports a wrong bounding box for every box
    ok = it.call(f'{px}_build')
    b, failed = boxes_of(it, px), it.get(f'{px}_failed')
    check(f'{label}: reason "bounding box": the {len(unrot)} unrotated boxes fail with it (on {px}_Check_Failed, listed), the other {len(pieces) - len(unrot)} ({n90} of them turned by 90 degrees) are not compared with the node\'s min / max and stay on their layers; all still built, Build returns true',
          ok is True and len(b) == len(pieces) and len(failed) == len(unrot) and all(f.endswith(': bounding box') for f in failed)
          and all((n.layer.name == f'{px}_Check_Failed' and n.props[f'{px}_check'] == 'bounding box') if pid in unrot else (n.layer.name != f'{px}_Check_Failed' and n.props[f'{px}_check'] == 'ok')
                  for pid, n in b.items()), f'{len(failed)} {failed[:1]}')
    # what Max reports for a node that is turned is not documented, a quarter turn included: whatever it is, no such box fails for it
    for how, flags in READINGS:
        sc = mk.Scene()
        for flag, v in flags.items(): setattr(sc, flag, v)
        it = make_run(text, px, suite, frags, S, scene=sc, level=levels[0] if suite else None)
        ok = it.call(f'{px}_build')
        b = boxes_of(it, px)
        check(f'{label}: whatever Max reports as min / max of a turned box, a quarter turn included ({how}), none of the {len(pieces) - len(unrot)} fails and every box stays on its own layer',
              ok is True and len(b) == len(pieces) and it.get(f'{px}_failed') == [] and all(n.layer.name != f'{px}_Check_Failed' and n.props[f'{px}_check'] == 'ok' for n in b.values()))
    sc = mk.Scene(); sc.bbox_unturned = True                                # the mock's second reading must differ from the true one where it matters
    it = make_run(text, px, suite, frags, S, scene=sc, level=levels[0] if suite else None); it.call(f'{px}_build')
    q, tv = pieces[own_id('L1-tv-001')], boxes_of(it, px)[own_id('L1-tv-001')]
    ex = mk.getprop(tv, 'max').v[0] - mk.getprop(tv, 'min').v[0]
    check(f'{label}: (the mock) the second reading is not vacuous: a {q["w"]} x {q["d"]} m box turned by 90 degrees reports {ex:.2f} m along x, as if it were not turned ({q["w"]} m), not the true {q["d"]} m',
          abs(ex - q['w']) < 1e-6 and abs(ex - q['d']) > 0.1)

    # a box built wrong is caught by some check, whatever Max reports as min / max of a turned node
    call_of = lambda pid: next(c for c in S['calls'] if c['pid'] == pid)
    swap = lambda a: dict(w=a['d'], d=a['w'])
    mirror = lambda a: dict(cs=[a['cs'][1], a['cs'][0], a['cs'][2], a['cs'][3]])
    wide = lambda a: dict(w=a['w'] + 0.01)
    defects = [                         # (piece, what is wrong with the box as built, the change to its call, the check that must catch it)
        ('L1-seat-002', 'turned 30 degrees, built at 40 degrees', lambda a: angle_only(40), 'corner'),
        ('L1-seat-002', 'turned 30 degrees, width and length swapped', swap, 'corner'),
        ('L1-seat-002', 'turned 30 degrees, mirrored (corners 1 and 2 swapped)', mirror, 'corner'),
        ('L1-seat-002', 'turned 30 degrees, 1 cm too wide', wide, 'corner'),
        ('L1-tv-001', 'turned 90 degrees, built unrotated (0 degrees): as built it is unrotated, so its extents are compared', lambda a: dict(ca=1.0, sa=0.0), 'bounding box'),
        ('L1-tv-001', 'turned 90 degrees, built at 80 degrees', lambda a: angle_only(80), 'corner'),
        ('L1-tv-001', 'turned 90 degrees, width and length swapped', swap, 'corner'),
        ('L1-tv-001', 'turned 90 degrees, mirrored (corners 1 and 2 swapped)', mirror, 'corner'),
        ('L1-seat-001', 'unrotated, built turned by 90 degrees: as built it is turned, so only its corners can tell', lambda a: dict(ca=0.0, sa=1.0), 'corner'),
        ('L1-seat-001', 'unrotated, width and length swapped', swap, 'bounding box'),
        ('L1-seat-001', 'unrotated, 1 cm too wide', wide, 'bounding box'),
        ('L1-seat-001', 'unrotated, mirrored (corners 1 and 2 swapped): the same extents, so only a corner can tell', mirror, 'corner'),
    ]
    for pid, what, change, want in defects:
        pid = own_id(pid)
        got = [build_one(text, px, suite, frags, S, levels, pid, flags, **change(call_of(pid))) for _, flags in READINGS]
        check(f'{label}: caught by {"a corner" if want == "corner" else "the bounding box"} (on {px}_Check_Failed) under each of the {len(READINGS)} readings of a turned node\'s min / max: {pid}, {what} ({got[0][0]!r})',
              all(g[1] == f'{px}_Check_Failed' and (g[0].startswith('corner ') if want == 'corner' else g[0] == 'bounding box') for g in got), str(got))
    a = call_of(own_id('L1-seat-001'))
    for deg, why in ((0.01, 'rot is rounded to 0.01 degree, and that much is already turned'), (180.0, 'sin is 0 but cos is negative: turned')):
        got = [build_one(text, px, suite, frags, S, levels, own_id('L1-seat-001'), flags, **turned_to(a, deg)) for _, flags in READINGS]
        check(f'{label}: a box turned by {deg} degrees ({why}) is not compared with the node\'s min / max: it passes under each of the {len(READINGS)} readings ({got[0][0]!r})',
              all(g == ('ok', g[1]) and g[1] != f'{px}_Check_Failed' for g in got), str(got))
    got = build_one(text, px, suite, frags, S, levels, own_id('L1-seat-001'), {'bbox_error': {'max': {'x': 0.01}}})
    check(f'{label}: an unrotated box is compared with the node\'s min / max ({got[0]!r})', got[0] == 'bounding box' and got[1] == f'{px}_Check_Failed')


def scene_with_structure(text, px, suite, frags, S, shift, part_floor=True, level=None):
    """A scene built from the model with 'Build furniture boxes' unticked: structure, rooms and the datum, as the 3D team has it."""
    it = make_run(text, px, suite, frags, S, shift=shift, want=False, part_floor=part_floor, level=level)
    it.call(f'{px}_build')
    return it


def test_add_only(label, text, px, suite, frags, S, pieces, floors, levels):
    section(f'{label}: "Furniture boxes only" (add to the scene already built from this model)')
    lv = levels[0] if suite else None
    kinds = KINDS
    # the reference: structure and furniture in one Build, shift = the offset
    ref = make_run(text, px, suite, frags, S, shift=(OX, OY), level=lv); ref.call(f'{px}_build')
    ref_boxes = {pid: (n.name, [r.v[:] for r in n.tm.rows], dict(n.params), n.layer.name, dict(n.props)) for pid, n in boxes_of(ref, px).items()}
    # a. structure first (centred on the origin: datum at -offset), then only the boxes; the window holds other numbers
    base = scene_with_structure(text, px, suite, frags, S, (OX, OY), part_floor=not suite, level=lv)
    n_before = len(base.scene.objects)
    base.run(frags['read'], **controls_for(S, None, True, True))             # the box ticks: furniture boxes only
    base.set(f'{px}_shift', mk.P(0.0, 0.0))                                  # the dialog says "drawing's own coordinates" (wrong for this scene)
    if suite: base.set('PS_level', 9.0)                                      # and a wrong level
    else: base.set(f'{px}_levels', [9.0, 9.0])
    ok = base.call(f'{px}_build')
    got = {pid: (n.name, [r.v[:] for r in n.tm.rows], dict(n.params), n.layer.name, dict(n.props)) for pid, n in boxes_of(base, px).items()}
    shift_ok = (suite is False)
    if not suite:
        msgs = [m[0] for m in base.scene.messages]
        check(f'{label}: add-only: adds {len(pieces)} boxes and nothing else (objects {n_before} -> {len(base.scene.objects)}), no empty-scene refusal, says "Added {len(pieces)} furniture boxes. Every box passed ..." in one message of its own, and Build returns false: nothing more for the Build button to say',
              ok is False and len(base.scene.objects) == n_before + len(pieces) and len(msgs) == 1
              and msgs[0].startswith(f'Added {len(pieces)} furniture boxes. Every box passed its height and position checks.') and 'closed-solid' not in msgs[0], str(msgs[:2]))
        check(f'{label}: add-only: the placement shift is read from the datum {px}_ORIGIN_DWG and each level from the objects (window said shift 0 / levels 9): boxes identical to a single Build',
              got == ref_boxes, 'differences: ' + str([k for k in ref_boxes if got.get(k) != ref_boxes[k]][:3]))
        check(f'{label}: add-only: the Listener reports it', any('FURNITURE BOXES ADDED' in s and s.rstrip().endswith('0 failed checks') for s in base.scene.listener))
    else:
        # the suite's parts carry no <px>_floor: the datum is read, the level comes from the window (and the window says so)
        msg = ' '.join(m[0] for m in base.scene.messages)
        check(f'{label}: add-only: the datum is read (boxes at the right x, y) and, as the suite\'s parts carry no PS_floor, the level of the window is used and the message says so',
              ok is False and 'level of 1 floor(s) was not found' in msg and 'Added ' in msg and len(boxes_of(base, px)) == len(pieces), msg[:120])
        bad, _ = box_report(base, px, pieces, kinds, floors, [9.0], (OX, OY))
        check(f'{label}: add-only: with the window\'s level (9.0) and the datum\'s shift, every box is where the README puts it', not bad, '; '.join(bad[:3]))
        # with the optional line setUserProp o "PS_floor" 1 in PS_part the level is read from the scene as well
        base2 = scene_with_structure(text, px, suite, frags, S, (OX, OY), part_floor=True, level=lv)
        base2.run(frags['read'], **controls_for(S, None, True, True)); base2.set('PS_level', 9.0)
        # (the faked part carries PS_floor here: the optional one-line change)
        ok2 = base2.call(f'{px}_build')
        bad, _ = box_report(base2, px, pieces, kinds, floors, levels, (OX, OY))
        check(f'{label}: add-only with the optional PS_floor line: the level is read from the scene (window said 9.0), only the success message', ok2 is False and not bad and len(base2.scene.messages) == 1 and base2.scene.messages[0][0].startswith('Added '), '; '.join(bad[:3]))
    if suite: return
    # b. refusals change nothing
    n_now = len(base.scene.objects)
    base.run(frags['read'], **controls_for(S, None, True, True))
    ok = base.call(f'{px}_build')
    msg = base.scene.messages[-1][0] if base.scene.messages else ''
    check(f'{label}: add-only twice: the second time refuses politely (boxes exist), returns false, changes nothing', ok is False and 'already has furniture boxes' in msg and len(base.scene.objects) == n_now, msg)
    other = scene_with_structure(text, px, suite, frags, S, (OX, OY))
    other.scene.units['systemtype'] = mk.Sym('millimeters')
    other.run(frags['read'], **controls_for(S, None, True, True)); n0 = len(other.scene.objects)
    ok = other.call(f'{px}_build')
    check(f'{label}: add-only in a scene whose System Units are not metres: refuses, changes nothing', ok is False and 'System Units are not metres' in other.scene.messages[-1][0] and len(other.scene.objects) == n0)
    other = scene_with_structure(text, px, suite, frags, S, (OX, OY)); n0 = len(other.scene.objects)
    other.run(frags['read'], **controls_for(S, None, False, True))
    ok = other.call(f'{px}_build')
    check(f'{label}: add-only with "Build furniture boxes" unticked: refuses, changes nothing', ok is False and 'Tick Build furniture boxes' in other.scene.messages[-1][0] and len(other.scene.objects) == n0)
    other = scene_with_structure(text, px, suite, frags, S, (OX, OY))
    own = mk.Node(other.scene, mk.Cls('Editable_Mesh'), 'their sofa'); other.scene.layer(f'{px}_L1_Furn_Seat').add(own)
    other.run(frags['read'], **controls_for(S, None, True, True)); n0 = len(other.scene.objects)
    ok = other.call(f'{px}_build')
    check(f'{label}: add-only when the 3D team already put their own models on a {px}_*_Furn_* layer: refuses (no second set of boxes)', ok is False and len(other.scene.objects) == n0 and 'already has furniture boxes (1 objects)' in other.scene.messages[-1][0])
    # c. what it cannot find, it says: no datum, one level missing, a part moved by hand
    other = scene_with_structure(text, px, suite, frags, S, (OX, OY))
    for n in list(other.scene.objects):
        if n.name == f'{px}_ORIGIN_DWG': other.scene.objects.remove(n)
    other.run(frags['read'], **controls_for(S, None, True, True)); other.set(f'{px}_shift', mk.P(OX, OY))
    ok = other.call(f'{px}_build')
    bad, _ = box_report(other, px, pieces, kinds, floors, levels, (OX, OY))
    check(f'{label}: add-only without the datum: the window\'s tick box decides the placement, a message says the datum was not found, then the success message', ok is False and not bad and 'origin datum' in other.scene.messages[0][0] and other.scene.messages[-1][0].startswith('Added '), '; '.join(bad[:2]))
    other = scene_with_structure(text, px, suite, frags, S, (OX, OY))
    for n in list(other.scene.objects):
        if n.props.get(f'{px}_floor') == '2': other.scene.objects.remove(n)
    other.run(frags['read'], **controls_for(S, None, True, True)); other.set(f'{px}_levels', [0.0, 3.7])
    ok = other.call(f'{px}_build')
    msg = ' '.join(m[0] for m in other.scene.messages)
    bad, _ = box_report(other, px, pieces, kinds, floors, levels, (OX, OY))
    check(f'{label}: add-only when one level has no objects left: its level comes from the window (3.70) and the message says so', ok is False and not bad and 'level of 1 floor(s) was not found' in msg and 'Added ' in msg, msg[:100])
    other = scene_with_structure(text, px, suite, frags, S, (OX, OY))
    first_l2 = next(n for n in other.scene.objects if n.props.get(f'{px}_floor') == '2')
    first_l2.tm.rows[3].v[2] += 0.3                                         # somebody moved one part of level 2 by hand
    other.run(frags['read'], **controls_for(S, None, True, True)); other.set(f'{px}_levels', [9.0, 9.0])
    ok = other.call(f'{px}_build')
    bad, _ = box_report(other, px, pieces, kinds, floors, levels, (OX, OY))
    check(f'{label}: add-only when one part was moved by hand (+0.30 m): the level is the most common one, so the boxes are right', ok is False and not bad and other.scene.messages[-1][0].startswith('Added '), '; '.join(bad[:2]))
    other = scene_with_structure(text, px, suite, frags, S, (OX, OY))
    other.scene.bbox_error = {'max': {'x': 0.01}}                           # the boxes that are compared with the node's min / max fail
    other.run(frags['read'], **controls_for(S, None, True, True)); n0 = len(other.scene.objects)
    ok = other.call(f'{px}_build')
    n_fail = sum(1 for p in pieces.values() if is_unrotated(p['rot']))
    msg = other.scene.messages[-1][0]
    check(f'{label}: add-only when {n_fail} boxes fail a check: all {len(pieces)} are added, the failed ones are on {px}_Check_Failed and listed in the Listener, and the message says "{n_fail} of the {len(pieces)} furniture boxes failed a check" instead of the structure script\'s message about parts',
          ok is False and len(other.scene.objects) == n0 + len(pieces) and msg.startswith(f'{n_fail} of the {len(pieces)} furniture boxes failed a check') and f'{px}_Check_Failed' in msg and 'part' not in msg
          and sum(1 for s in other.scene.listener if s.startswith('  check failed')) == n_fail, msg[:120])


def probe(text, px, frags, S, pieces, floors):
    """A quiet run of the main scenarios of the bank script (no check() calls); returns the list of things that went wrong."""
    kinds, keys, bad = KINDS, S['keys'], []
    mm = {k: 1000 + 10 * i for i, k in enumerate(keys)}
    mm.update(table=800, **{'coffee-table': 400})
    vals = [mm[k] for k in keys]
    try:
        it = make_run(text, px, False, frags, S); it.call(f'{px}_build')
        b, _ = box_report(it, px, pieces, kinds, floors, [0.0, 3.7], (0.0, 0.0)); bad += [f'build: {x}' for x in b[:2]]
        if it.get(f'{px}_failed'): bad.append('build: a box failed its own check')
        it2 = make_run(text, px, False, frags, S, shift=(OX, OY)); it2.call(f'{px}_build')
        b, _ = box_report(it2, px, pieces, kinds, floors, [0.0, 3.7], (OX, OY)); bad += [f'shifted build: {x}' for x in b[:2]]
        it.run(frags['handlers'].split('\n', 1)[1], **controls_for(S, vals))
        b, _ = box_report(it, px, pieces, kinds, floors, [0.0, 3.7], (0.0, 0.0), mm=mm); bad += [f'apply: {x}' for x in b[:2]]
        it.call(f'{px}_updateLevels', [0.0, 4.5], [3.7, 3.7])
        it.run(frags['handlers'].split('\n', 1)[1], **controls_for(S, [v + 5 for v in vals]))
        b, _ = box_report(it, px, pieces, kinds, floors, [0.0, 4.5], (0.0, 0.0), mm={k: vals[i] + 5 for i, k in enumerate(keys)}); bad += [f'update + apply: {x}' for x in b[:2]]
        base = scene_with_structure(text, px, False, frags, S, (OX, OY))
        base.run(frags['read'], **controls_for(S, None, True, True)); base.set(f'{px}_shift', mk.P(0.0, 0.0)); base.set(f'{px}_levels', [9.0, 9.0])
        ok = base.call(f'{px}_build')
        if ok is not False or not base.scene.messages or not base.scene.messages[-1][0].startswith('Added '): bad.append('add-only: Build must return false after the message "Added N furniture boxes ..."')
        b, _ = box_report(base, px, pieces, kinds, floors, [0.0, 3.7], (OX, OY)); bad += [f'add-only: {x}' for x in b[:2]]
        n = len(base.scene.objects)
        if base.call(f'{px}_build') is not False or len(base.scene.objects) != n: bad.append('add-only twice: the second run was not refused')
        sc = mk.Scene(); sc.none_is_undefined = True                         # the word none that Max may not read, then Apply
        it6 = make_run(text, px, False, frags, S, scene=sc); it6.call(f'{px}_build')
        it6.run(frags['handlers'].split('\n', 1)[1], **controls_for(S, vals))
        b, _ = box_report(it6, px, pieces, kinds, floors, [0.0, 3.7], (0.0, 0.0), mm=mm); bad += [f'apply, none unreadable: {x}' for x in b[:2]]
        for how, flags in READINGS[1:]:                                      # what Max may report as min / max of a turned node: no turned box fails for it
            sc = mk.Scene()
            for flag, v in flags.items(): setattr(sc, flag, v)
            it7 = make_run(text, px, False, frags, S, scene=sc); it7.call(f'{px}_build')
            if it7.get(f'{px}_failed'): bad.append(f'min / max of a turned node ({how}) failed a box: the bounding box is compared for a turned box')
        sc = mk.Scene(); sc.bbox_error = {'max': {'x': 0.01}}                # a wrong min / max of every node: the unrotated boxes fail, and only they
        it8 = make_run(text, px, False, frags, S, scene=sc); it8.call(f'{px}_build')
        got = sorted(f[:-len(': bounding box')] for f in it8.get(f'{px}_failed') if f.endswith(': bounding box'))
        want = sorted(n.name for pid, n in boxes_of(it8, px).items() if is_unrotated(pieces[pid]['rot']))
        if got != want or len(it8.get(f'{px}_failed')) != len(want): bad.append('the bounding box is not compared for exactly the unrotated boxes')
        a = next(c for c in S['calls'] if c['pid'] == 'L1-seat-001')
        for deg in (180.0, 0.01):                                            # turned although sin is 0 or nearly 0: not compared, whatever Max reports
            got = build_one(text, px, False, frags, S, [0.0, 3.7], 'L1-seat-001', READINGS[1][1], **turned_to(a, deg))
            if got != ('ok', got[1]) or got[1] == f'{px}_Check_Failed': bad.append(f'a box turned by {deg} degrees was compared with the node\'s min / max: {got[0]!r}')
        mm_scene = scene_with_structure(text, px, False, frags, S, (OX, OY))
        mm_scene.scene.units['systemtype'] = mk.Sym('millimeters')
        mm_scene.run(frags['read'], **controls_for(S, None, True, True))
        if mm_scene.call(f'{px}_build') is not False or boxes_of(mm_scene, px): bad.append('add-only with other System Units was not refused')
    except mk.MaxError as e:
        bad.append(f'the interpreter stopped: {e}')
    return bad


def mutate_fn(text, px, fn, old, new):
    """Change the first `old` inside one function of the script (not the template's own functions that look alike)."""
    m = re.search(rf'^fn {px}_{fn}\b.*?(?=^fn |^try \(|\Z)', text, re.M | re.S)
    if not m or old not in m.group(0): return None
    return text[:m.start()] + m.group(0).replace(old, new, 1) + text[m.end():]


def test_mutations(text, px, frags, S, pieces, floors):
    section('the dynamic tests have teeth: slips put into the generated script are found (a clean run means something)')
    check('the unmodified script passes the probe', probe(text, px, frags, S, pieces, floors) == [])
    P_ = px
    mutations = [
        ('a support\'s top ignores its height', 'furnZ0', f'{P_}_furnBases[oki] + {P_}_furnHeights[oki]', f'{P_}_furnBases[oki]'),
        ('the shift is added instead of subtracted (x)', 'furnBox', f'c.x - {P_}_shift.x, c.y', f'c.x + {P_}_shift.x, c.y'),
        ('the shift is not subtracted in y', 'furnBox', f'c.y - {P_}_shift.y, zb', 'c.y, zb'),
        ('the matrix is transposed (rotation sign)', 'furnBox', '[ca, sa, 0.0] [(0.0 - sa), ca, 0.0]', '[ca, (0.0 - sa), 0.0] [sa, ca, 0.0]'),
        ('the first level is used for every box', 'furnBox', f'local zb = {P_}_furnLevels[fi] + z0', f'local zb = {P_}_furnLevels[1] + z0'),
        ('Apply forgets to take the old base off', 'furnApply', f'o.pos.z - ({P_}_furnNum (getUserProp o "{P_}_base")) + z0', 'o.pos.z + z0'),
        ('a box does not keep its base (Apply and Update levels then go wrong)', 'furnBox', f'setUserProp o "{P_}_base" z0', f'setUserProp o "{P_}_base" 0.0'),
        ('Apply sets the first kind\'s height on every box', 'furnApply', f'o.height = {P_}_furnHeights[ki]', f'o.height = {P_}_furnHeights[1]'),
        ('Apply forgets to store the new base', 'furnApply', f'setUserProp o "{P_}_base" z0', 'n += 0'),
        ('the level of floor 1 is stored for every floor (add-only)', 'furnSceneLevels', f'{P_}_furnLevels[f] = mms[j] / 1000.0', f'{P_}_furnLevels[1] = mms[j] / 1000.0'),
        ('the datum\'s shift has the wrong sign (add-only)', 'furnAdd', f'else {P_}_shift = [0.0 - datum.pos.x, 0.0 - datum.pos.y]', f'else {P_}_shift = [datum.pos.x, datum.pos.y]'),
        ('the datum is not read at all (add-only)', 'furnAdd', f'else {P_}_shift = [0.0 - datum.pos.x, 0.0 - datum.pos.y]', f'else {P_}_shift = {P_}_shift'),
        ('every box goes on the layer of the first kind', 'furnBox', f'{P_}_furnLayers[ki]', f'{P_}_furnLayers[1]'),
        ('every box carries floor 1', 'furnBox', f'setUserProp o "{P_}_floor" fi', f'setUserProp o "{P_}_floor" 1'),
        ('a box is called a follower of the wall height', 'furnBox', f'setUserProp o "{P_}_follow" false', f'setUserProp o "{P_}_follow" true'),
        ('the support kind is ignored', 'furnBox', f'local z0 = {P_}_furnZ0 ki (findItem {P_}_furnKeys supKind)', f'local z0 = {P_}_furnZ0 ki 0'),
        ('the check tolerance is far too tight', 'furnBox', 'local tol = 0.002', 'local tol = 0.0000001'),
        ('the level is the least common value, not the most common (add-only)', 'furnSceneLevels', 'and cnt[j] > best do', 'and cnt[j] < best + 1 do'),
        ('the material of the first kind is used for all', 'furnBox', f'local mt = {P_}_furnMats[ki]', f'local mt = {P_}_furnMats[1]'),
        ('the width and length are swapped', 'furnBox', 'width:w length:d height:ht', 'width:d length:w height:ht'),
        ('the box is made with a negative height', 'furnBox', 'height:ht', 'height:(0.0 - ht)'),
        ('boxes that are already there are not refused (add-only)', 'furnAdd', 'if existing > 0 then', 'if existing > 99999 then'),
        ('System Units are not checked (add-only)', 'furnAdd', 'or units.systemType != #meters then', 'or false then'),
        ('the floor index of a box is off by one', 'furnBox', f'local zb = {P_}_furnLevels[fi] + z0', f'local zb = {P_}_furnLevels[fi + 1 - 1 + 0] + z0 + 0.5'),
        ('the box is not added to the node list the footer selects', 'furnBox', f'append {P_}_nodes o', 'n = 0'),
        ('the bounding box is compared for every box, turned or not', 'furnBox', 'else if unrotated and (', 'else if ('),
        ('the bounding box is never compared', 'furnBox', 'else if unrotated and (', 'else if false and ('),
        ('the old rule: a quarter turn counts as unrotated too, so a box at 90 degrees is compared', 'furnBox', 'abs(sa) < 0.00001 and ca > 0.0', 'abs(ca) < 0.00001 or abs(sa) < 0.00001'),
        ('a box turned by 180 degrees counts as unrotated (the cosine is not looked at)', 'furnBox', 'abs(sa) < 0.00001 and ca > 0.0', 'abs(sa) < 0.00001'),
        ('a box turned by up to 36 degrees counts as unrotated', 'furnBox', 'abs(sa) < 0.00001 and ca > 0.0', 'abs(sa) < 0.6 and ca > 0.0'),
        ('a box turned by 0.01 degree counts as unrotated (a tolerance 100 times too loose)', 'furnBox', 'abs(sa) < 0.00001 and ca > 0.0', 'abs(sa) < 0.001 and ca > 0.0'),
        ('every box with a positive cosine counts as unrotated', 'furnBox', 'abs(sa) < 0.00001 and ca > 0.0', 'ca > 0.0'),
        ('the bounding box is compared without the placement shift', 'furnBox', f'abs(o.min.x - (mnx - {P_}_shift.x))', 'abs(o.min.x - mnx)'),
        ('the bounding box compares max x with the minimum', 'furnBox', f'abs(o.max.x - (mxx - {P_}_shift.x))', f'abs(o.max.x - (mnx - {P_}_shift.x))'),
        ('Apply puts a box whose support kind is none on the first kind', 'furnApply', f'(findItem {P_}_furnKeys ((getUserProp o "{P_}_furnOnKind") as string))', '1'),
        ('Build returns true after "Furniture boxes only": the Build button would add a message about parts', 'build', f'{P_}_furnAdd()\n        return false', f'local furnDone = {P_}_furnAdd()\n        return furnDone'),
        ('"Furniture boxes only" says "Built" like the structure script', 'furnAdd', 'messageBox ("Added "', 'messageBox ("Built "'),
    ]
    for label, fn, old, new in mutations:
        mutated = mutate_fn(text, px, fn, old, new)
        if mutated is None: check(f'mutation "{label}": the text to change was found in {fn}', False, old[:70]); continue
        got = probe(mutated, px, frags, S, pieces, floors)
        check(f'slip found by the dynamic tests: {label}', bool(got), 'NOT noticed')


def run_all():
    test_fragments_api()
    test_problems()
    test_rules()
    test_ascii_name()
    gens = test_rehearsal()
    suite_pieces = {p['id']: p for p in suite_furniture()}
    for label, key, px, floors, pieces, levels in (('bank', 'bank', 'FX', ['L1', 'L2'], PIECES, [0.0, 3.7]), ('suite', 'suite', 'PS', [PRES_FLOOR], suite_pieces, [0.0])):
        if key not in gens: continue
        text = gens[key]['full']
        S = test_script(label, text, px, pieces, KINDS, floors, (OX, OY))
        test_collapse_update(label, text, px, 'FX_updateLevels' if key == 'bank' else 'PS_updateHeights', 'FX_collapseAll' if key == 'bank' else 'PS_collapseAll', key == 'bank')
        test_new_constructs(label, gens[key]['base'], text)
        M = bank_model(True) if key == 'bank' else pres_model(True)
        frags, pr = fm.fragments(M, px, MINI['floors'] if key == 'bank' else [{'key': PRES_FLOOR}], 'FX_levels' if key == 'bank' else '#(PS_level)',
                                 'Fixture' if key == 'bank' else 'Presidential suite')
        suite = key == 'suite'
        test_dynamic(label, text, px, suite, frags, S, pieces, floors, levels, 'FX_updateLevels' if key == 'bank' else None)
        test_failure_paths(label, text, px, suite, frags, S, pieces, floors, levels)
        test_add_only(label, text, px, suite, frags, S, pieces, floors, levels)
        if not suite: test_mutations(text, px, frags, S, pieces, floors)
    if 'bank' in gens: test_lint_sensitivity(gens['bank']['full'])
    # the two COMPLETE test scripts, as the generators write them (CRLF on Windows)
    for key, fname in (('bank', 'mini_furniture.ms'), ('suite', 'mini_furniture_pres.ms')):
        if key in gens:
            (HERE / 'fixtures' / fname).write_bytes(gens[key]['full'].replace('\n', '\r\n').encode('ascii'))
            info(f'written fixtures/{fname} ({len(gens[key]["full"].splitlines())} lines)')


def main():
    try: run_all()
    except Exception as e:                 # a generator or a script that is damaged must end in a FAIL line and exit 1, never in a traceback
        check(f'the tests ran to the end ({type(e).__name__})', False, str(e)[:300])
    failed = [n for n, ok in RESULTS if not ok]
    print(f'\n{len(RESULTS)} checks, {len(failed)} failed')
    for n in failed: print('  FAILED:', n)
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
