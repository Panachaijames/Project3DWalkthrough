"""Checks of the REAL presidential suite 3ds Max script (presidential_test/Presidential_Suite.ms) against the REAL model
(presidential_test/src/pres2_model.json): the furniture proxy boxes, one coloured Box per piece (owner's decision of 28 Oct 2026; the
contract is furniture/README.md), spliced into the structure script that the owner ran in 3ds Max on 26 Oct 2026 (good).
Plain python, no framework; prints PASS / FAIL per check and exits 1 if one failed.  Run from anywhere:

    python -B presidential_test/test_presidential_maxscript.py

The pattern of bank_test/test_bank_maxscript.py, for the suite's one level (key 'suite', at the model's level) and its own template
(prefix PS; no "Update levels": "Update heights to Floor to floor" only changes the parts that follow the wall height). 3ds Max is not
installed on the machine that builds the script, so it is read back as text and everything that can be worked out from the text and
the model is worked out again here, from the README's formulas (not by calling furniture/furniture_max.py):
  1. the file: stamp = sha1 of pres2_model.json, ASCII, line ends, brackets and quotes, no placeholder left, every control of the window
     named once, and (furniture/fixtures/maxscript_lite.py) the token lint, the argument counts and the names;
  2. the data: one box call per piece in the model's order, every id once, names unique, a layer per kind, a material and a height
     spinner per kind (a half rounds up, range 10 - 5000, two to a row, captions that fit), the word none for nothing;
  3. every box: the matrix3 [cos,sin,0] [-sin,cos,0] [0,0,1] [x,y,z] from the call's numbers and its size give the four world corners
     of its base; they must equal the corners the README's formulas give from the model (x, y, w, d, rot + the offset), within 0.5 mm,
     and so must the corners the script carries for its own check; base z and top z, with the supports resolved from the kinds'
     heights (a lamp on a table stands at the table's top);
  4. the code: "Furniture boxes only", "Apply furniture heights" and "Update heights" are there, no box is ever collapsed or converted
     (the owner's rule: live objects, never an Editable Poly), and the node's min / max are compared only for an unrotated box (rot 0:
     nothing in Autodesk's text says what they are for a turned node, a quarter turn included);
  5. the generator and the script of 26 Oct (previous_before_furniture_2026-10-29/): the script on disk is what the generator writes
     today; the model of 26 Oct (the text of pres2_model.json before its furniture keys) gives the 26 Oct script back byte for byte, a
     model without furniture gives it back apart from the stamp line, and the real script differs from it only by lines inserted in the
     eight places of the recipe: every line of the 26 Oct script is still there, in its order;
  6. the generated functions are RUN by the small MAXScript interpreter of the fixtures over a mock scene: Build, Apply, Update heights,
     Collapse all, Furniture boxes only (the suite's parts carry no PS_floor, so that mode takes the level from the window and says so),
     the word none and the bounding-box rule, on the real script and the real model.
Slips put into the data and the text on purpose must be found, so that a clean run means something.

What this cannot show: that 3ds Max itself agrees. The mock knows only what is written in furniture/fixtures/maxscript_mock.py, and the
lint only reads tokens. The 3D team's run is the proof.
"""
import copy, difflib, hashlib, json, math, os, re, shutil, subprocess, sys, tempfile, unicodedata
from pathlib import Path

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / 'furniture' / 'fixtures'))
try:
    import maxscript_lite as ms                    # the token lint and the mock Max that furniture/test_furniture_max.py already uses
    import maxscript_mock as mk
except ImportError:
    ms = mk = None

SCRIPT = HERE / 'Presidential_Suite.ms'
MODEL = HERE / 'src' / 'pres2_model.json'
GENERATOR = HERE / 'src' / 'generate_maxscript.py'
MODULE = ROOT / 'furniture' / 'furniture_max.py'
PREVIOUS = HERE / 'previous_before_furniture_2026-10-29' / 'Presidential_Suite.ms'
PREVIOUS_SHA1 = '9361d1f2e3c2132cd0e58ce6e47fc2cb0f9c287d'     # the script the owner ran in 3ds Max on 26 Oct (written on 19 Oct)
MODEL_26OCT = '7f48db50ff58'                                    # the stamp of that script: sha1 of the model it was written from
TOL = 5e-4                                                      # corners: 0.5 mm
PX = 'PS'                                                       # the suite's prefix (its generator's own; the model has no maxPrefix)
FLOOR = 'suite'                                                 # the suite's one level, as its builder writes it in every piece

RESULTS, SKIPPED = [], []


def check(name, ok, detail=''):
    RESULTS.append((name, bool(ok)))
    print(('PASS  ' if ok else 'FAIL  ') + name + (f'   [{detail}]' if detail and not ok else ''))
    return ok


def skip(name, why):
    SKIPPED.append(name)
    print(f'SKIP  {name}   [{why}]')


def info(text): print('      ' + text)
def section(title): print(f'\n== {title}')


for f in (SCRIPT, MODEL):
    if not f.exists(): sys.exit(f'{f} not found')
RAW = SCRIPT.read_bytes()
MODEL_RAW = MODEL.read_bytes()
M = json.loads(MODEL_RAW.decode('utf-8'))
TEXT = RAW.decode('latin-1').replace('\r\n', '\n')            # (the ASCII check is a check of its own)
LINES = TEXT.split('\n')
OX, OY = M['offset']
FLOORS = [FLOOR]
LEVEL = {FLOOR: M['level']}
KINDS = M.get('furnitureKinds') or []
KIND = {k['key']: k for k in KINDS}
PIECES = M.get('furniture') or []
BY_ID = {p['id']: p for p in PIECES}


# ---- the README's formulas, written out again here ----------------------------------------------------------------------------

def camel(key): return ''.join(w.capitalize() for w in key.split('-'))           # coffee-table -> CoffeeTable


def ascii_fold(s):
    """The rule for text in the Max script: plain ASCII (Chinese and other letters drop out, a Vietnamese a with a dot below becomes a),
    no double quote or backslash, spaces collapsed."""
    s = s.replace(chr(0xb2), '2').replace(chr(0xb7), '-').replace(chr(0x110), 'D').replace(chr(0x111), 'd')       # superscript 2, middle dot, D and d with a stroke
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode()
    return ' '.join(re.sub(r'[\x00-\x1f\x7f]', ' ', s).replace('"', "'").replace('\\', '/').split())


def none_text(s): return ascii_fold(s or '') or 'none'                         # a user property's text: ASCII, and the word none for nothing
def half_up(v): return int(math.floor(v + 0.5))                                  # whole mm, a half rounds up (Python's round() goes to even)
def is_unrotated(rot): return abs(math.sin(math.radians(rot))) < 1e-5 and math.cos(math.radians(rot)) > 0     # rot 0: the boxes whose node min / max are compared


def caption_of(k):
    """A spinner's caption by the rule: the label when it has at most 16 characters, else the key in words, then a colon."""
    s = ascii_fold(k['label']).replace('&', 'and')
    return (s if 0 < len(s) <= 16 else k['key'].replace('-', ' ').capitalize()[:16]) + ':'


def readme_corners(p, shift=(0.0, 0.0)):
    """x, y = the centre, w >= d the sizes along its own long and short axis, rot = degrees counter-clockwise from +x (plan, y up);
    the DWG's own coordinates are the model's plus the offset; the corners run counter-clockwise from (-w/2, -d/2)."""
    a = math.radians(p['rot'])
    c, s = math.cos(a), math.sin(a)
    cx, cy = p['x'] + OX - shift[0], p['y'] + OY - shift[1]
    return [(cx + c * u - s * v, cy + s * u + c * v) for u, v in ((-p['w'] / 2, -p['d'] / 2), (p['w'] / 2, -p['d'] / 2), (p['w'] / 2, p['d'] / 2), (-p['w'] / 2, p['d'] / 2))]


def readme_z0(p, mm=None):
    """Metres above the level: the top of its support (that kind's base + height) or its own kind's base."""
    height = lambda key: (mm or {}).get(key, KIND[key]['height'])
    if p['on']:
        s = BY_ID[p['on']]['kind']
        return (KIND[s]['base'] + height(s)) / 1000
    return KIND[p['kind']]['base'] / 1000


def xform(p, rows):
    """3ds Max: a point is a row vector, p * matrix3 = x * row1 + y * row2 + z * row3 + row4."""
    return [sum(p[i] * rows[i][j] for i in range(3)) + rows[3][j] for j in range(3)]


# ---- reading the script back ------------------------------------------------------------------------------------------------

def split_args(s):
    """The space-separated arguments of a command-style MAXScript call: "strings", numbers, (groups), [points] and #(arrays)."""
    out, i = [], 0
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
        out.append(s[i:j]); i = j
    return out


def floats(s): return [float(x) for x in re.findall(r'-?\d+\.\d+', s)]
def quoted(s): return re.findall(r'"([^"]*)"', s)


def parse_call(s):
    """One furnBox call: 16 arguments (kind name floor-index id support-id support-kind centre w d cos sin corners family block layer handle)."""
    try: a = split_args(s)
    except (ValueError, IndexError): a = []                  # an unclosed quote or bracket: not a call that can be read
    c = {'raw': s, 'n': len(a), 'ok': False}
    if len(a) != 16: return c
    q = lambda x: x[1:-1] if len(x) >= 2 and x[0] == x[-1] == '"' else None
    c.update(kind=q(a[0]), name=q(a[1]), fi=int(a[2]) if a[2].isdigit() else None, id=q(a[3]), supId=q(a[4]), supKind=q(a[5]),
             c=floats(a[6]), w=floats(a[7]), d=floats(a[8]), ca=floats(a[9]), sa=floats(a[10]), cs=floats(a[11]),
             fam=q(a[12]), blk=q(a[13]), lay=q(a[14]), hnd=q(a[15]))
    texts = (c['kind'], c['name'], c['id'], c['supId'], c['supKind'], c['fam'], c['blk'], c['lay'], c['hnd'])
    c['ok'] = (all(t is not None for t in texts) and c['fi'] is not None and len(c['c']) == 2 and len(c['w']) == len(c['d']) == 1
               and len(c['ca']) == len(c['sa']) == 1 and len(c['cs']) == 8)
    return c


def global_array(name):
    m = re.search(rf'^global {PX}_furn{name} = (#\(.*\))$', TEXT, re.M)
    return m.group(1) if m else ''


def fn_text(name):
    m = re.search(rf'^fn {name}\b.*?(?=^fn |^try \(|\Z)', TEXT, re.M | re.S)
    return m.group(0) if m else ''


def code(s): return re.sub(r'^\s*--.*$', '', s, flags=re.M)                   # without the full-line comments


CALLS = [parse_call(m.group(1)) for m in re.finditer(rf'^    {PX}_furnBox (.*)$', TEXT, re.M)]
KEYS, LAYERS, FLOORS_S = (quoted(global_array(n)) for n in ('Keys', 'Layers', 'Floors'))
BASES, HEIGHTS = (floats(global_array(n)) for n in ('Bases', 'Heights'))
LEVELS_S = floats((re.search(rf'^global {PX}_level = (.*)$', TEXT, re.M) or (None, ''))[1])          # the script's own level (metres): the furniture's levels are #(PS_level)
SPINNER_LINE = re.compile(r'^        spinner (fh\d+) "([^"]*)"( across:2)? range:\[(\d+), (\d+), (\d+)\] type:#integer fieldwidth:40$', re.M)
SPINNERS = SPINNER_LINE.findall(TEXT)
MATERIALS = re.findall(rf'^    append {PX}_furnMats \(standardMaterial name:"{PX} Furn ([^"]*)" diffuse:\(color (\d+) (\d+) (\d+)\)\)$', TEXT, re.M)


def geometry_problems(calls, keys, bases, heights, levels):
    """Every box against the README: the four corners of its base from the call's matrix3 numbers and size, the corners the script
    carries for its own check, cos and sin, centre, size, base z and top z (the script's own arrays resolve the supports).
    Returns (problems, worst corner error, worst check-corner error) in metres."""
    bad, worst, worst_cs = [], 0.0, 0.0
    for c in calls:
        p = BY_ID.get(c.get('id'))
        if p is None: bad.append(f"{c.get('id')}: not in the model"); continue
        if not c['ok']: bad.append(f"{c['id']}: the call is not 16 well-formed arguments"); continue
        ca, sa, w, d, (cx, cy) = c['ca'][0], c['sa'][0], c['w'][0], c['d'][0], c['c']
        if c['kind'] != p['kind']: bad.append(f"{c['id']}: kind {c['kind']} != {p['kind']}"); continue
        if c['kind'] not in keys or (c['supKind'] != 'none' and c['supKind'] not in keys): bad.append(f"{c['id']}: a kind that the arrays do not hold"); continue
        a = math.radians(p['rot'])
        # (9 decimals: cos and sin are within 5e-10 of the model's, their squares add up to 1 within 1.5e-9; Max's floats hold about 6e-8)
        if abs(ca - math.cos(a)) > 1e-9 or abs(sa - math.sin(a)) > 1e-9 or abs(ca * ca + sa * sa - 1) > 1e-8: bad.append(f"{c['id']}: cos / sin are not the model's rot {p['rot']}")
        if abs(cx - (p['x'] + OX)) > 1e-4 or abs(cy - (p['y'] + OY)) > 1e-4 or abs(w - p['w']) > 1e-4 or abs(d - p['d']) > 1e-4: bad.append(f"{c['id']}: centre or size differs from the model")
        # z: base and top from the script's own arrays (what the function computes) and from the README
        ki, oki = keys.index(c['kind']), (keys.index(c['supKind']) if c['supKind'] != 'none' else -1)
        z0 = bases[oki] + heights[oki] if oki >= 0 else bases[ki]
        zb = levels[c['fi'] - 1] + z0 if 1 <= c['fi'] <= len(levels) else float('nan')
        want_zb = LEVEL[p['floor']] + readme_z0(p) if p['floor'] in LEVEL else float('nan')
        want_zt = want_zb + KIND[p['kind']]['height'] / 1000
        if not abs(zb - want_zb) < 1e-6: bad.append(f"{c['id']}: base z {zb} != {want_zb}")
        if not abs(zb + heights[ki] - want_zt) < 1e-6: bad.append(f"{c['id']}: top z {zb + heights[ki]} != {want_zt}")
        if c['supId'] != (p['on'] or 'none') or c['supKind'] != (BY_ID[p['on']]['kind'] if p['on'] else 'none'): bad.append(f"{c['id']}: support {c['supId']!r}/{c['supKind']!r} != {p['on']!r}")
        # the box's corners: its own (+-w/2, +-d/2, 0) times matrix3 [cos,sin,0] [-sin,cos,0] [0,0,1] [centre, zb]
        rows = [[ca, sa, 0.0], [-sa, ca, 0.0], [0.0, 0.0, 1.0], [cx, cy, zb]]
        got = [xform(q, rows) for q in ((-w / 2, -d / 2, 0.0), (w / 2, -d / 2, 0.0), (w / 2, d / 2, 0.0), (-w / 2, d / 2, 0.0))]
        want = readme_corners(p)
        carried = list(zip(c['cs'][0::2], c['cs'][1::2]))
        for k in range(4):
            worst = max(worst, math.dist(got[k][:2], want[k]))
            worst_cs = max(worst_cs, math.dist(carried[k], want[k]))
        if max(math.dist(got[k][:2], want[k]) for k in range(4)) > TOL: bad.append(f"{c['id']}: the corners of the matrix3 differ from the README's by more than 0.5 mm")
        if max(math.dist(carried[k], want[k]) for k in range(4)) > TOL: bad.append(f"{c['id']}: the corners carried for the script's own check differ from the README's by more than 0.5 mm")
    return bad, worst, worst_cs


# ---- 1. the file ------------------------------------------------------------------------------------------------------------------

def test_file():
    section(f'the file ({len(RAW) // 1024} KB, {len(LINES) - 1} lines)')
    check('the model has furniture (furnitureKinds and furniture), and the script has the boxes', len(PIECES) > 0 and len(KINDS) > 0 and len(CALLS) > 0, f'{len(PIECES)} pieces, {len(KINDS)} kinds, {len(CALLS)} calls')
    check('ASCII only (3ds Max reads the script as plain text: Chinese and other letters are left out of it)', all(b < 128 for b in RAW), str([i for i, b in enumerate(RAW) if b > 127][:3]))
    crlf = RAW.count(b'\r\n')
    lf, cr = RAW.count(b'\n') - crlf, RAW.count(b'\r') - crlf
    check('line ends are all CRLF or all LF', cr == 0 and (crlf == 0 or lf == 0), f'{crlf} CRLF, {lf} bare LF, {cr} bare CR')
    stamp = re.search(r'^-- Same model as presidential_3d_preview\.html \(model data ([0-9a-f]{12})\)', TEXT, re.M)
    sha = hashlib.sha1(MODEL_RAW).hexdigest()[:12]
    check(f'the stamp in line 2 is the sha1 of pres2_model.json ({sha})', bool(stamp) and stamp.group(1) == sha and LINES[1].startswith(stamp.group(0)), f'script says {stamp and stamp.group(1)}')
    left = sorted(set(re.findall(r'__[A-Z]+(?:_[A-Z]+)*__', TEXT)))
    check('no placeholder is left (no __NAME__ and no __FURN_NAME__)', not left, str(left[:4]))
    check('( ) [ ] and quote counts are even (the generator\'s own sanity line)', TEXT.count('(') == TEXT.count(')') and TEXT.count('[') == TEXT.count(']') and TEXT.count('"') % 2 == 0)
    names = re.findall(r'^\s+(?:checkbox|spinner|button|label|radiobuttons|dropdownlist|edittext|listbox|slider) (\w+)', TEXT[max(TEXT.find(f'rollout {PX}_UI'), 0):], re.M)
    dup = sorted({n for n in names if names.count(n) > 1})
    check(f'every control of the window has a name of its own ({len(names)} controls: the old ones, the 3 furniture ones and one spinner per kind)', not dup and {'fb', 'fo', 'fap'} <= set(names), str(dup))
    if ms is None: skip('token lint, argument counts, names', 'furniture/fixtures/maxscript_lite.py not found'); return
    toks, terr = ms.tokenize(TEXT)
    check('every quote closes on its line and every character is readable', terr == [], str(terr[:3]))
    _, _, serr = ms.structure(toks)
    check('brackets and parentheses are balanced and nested right (strings left out)', serr == [], str(serr[:3]))
    lerr = ms.lint(TEXT)
    check('token lint: if/then/else, for/do, case/of, fn, try/catch, local/global', lerr == [], str(lerr[:5]))
    aerr = ms.arity_errors(TEXT)
    check(f'every statement that calls one of the script\'s functions gives it as many arguments as it has parameters (the {len(CALLS)} furnBox calls included)', aerr == [], str(aerr[:5]))
    known = {'box', 'matrix3', 'finditem', 'floor', 'matchpattern', 'integer'}     # Max built-ins that the structure script did not use (integer: "as integer")
    ref = reference()
    base_unres = {w.lower() for w in ms.unresolved(ref[0])} if ref else None
    unres = {w.lower() for w in ms.unresolved(TEXT)}
    if base_unres is None: skip('no word the structure script does not use, except the reviewed ones', 'the generator run of the regression section failed')
    else: check(f'every name the script does not declare is a Max word the structure script already used, or one reviewed for this task ({", ".join(sorted(unres - base_unres))})', unres - base_unres <= known, str(sorted(unres - base_unres - known)))


# ---- 2. the data ------------------------------------------------------------------------------------------------------------------

def test_data():
    section(f'the data: {len(PIECES)} pieces, {len(KINDS)} kinds, one level ({FLOOR})')
    check('every furnBox call has 16 well-formed arguments', all(c['ok'] for c in CALLS), str([c['raw'][:60] for c in CALLS if not c['ok']][:2]))
    check(f'one box call per piece ({len(CALLS)} calls for {len(PIECES)} pieces)', len(CALLS) == len(PIECES))
    ids = [c.get('id') for c in CALLS]
    check('every id exactly once, in the model\'s order', ids == [p['id'] for p in PIECES] and len(set(ids)) == len(ids))
    names = [c.get('name') for c in CALLS]
    check('object names are unique (to the letter case)', len({str(n).lower() for n in names}) == len(names))
    ok, why = True, ''
    for c in CALLS:
        p = BY_ID.get(c.get('id'))
        if not p or not c['ok']: ok = False; continue
        fam = ascii_fold(p['family'])[:40].rstrip(' _-')
        want = f"{PX}_{p['floor']}_Furn_{p['kind']}_{p['id'].rsplit('-', 1)[1]}" + (f'_{fam}' if fam else '')
        if c['name'] != want: ok, why = False, why or f"{c['id']}: {c['name']!r} != {want!r}"
    check(f'name = {PX}_{FLOOR}_Furn_<kind>_<nnn> (the id\'s number) + _<family, ASCII, at most 40 characters>', ok, why)
    ok = all(c['fam'] == none_text(BY_ID[c['id']]['family']) and c['blk'] == none_text(BY_ID[c['id']]['block']) and c['lay'] == none_text(BY_ID[c['id']]['layer'])
             and c['hnd'] == none_text(BY_ID[c['id']]['handle']) for c in CALLS if c['ok'] and c['id'] in BY_ID)
    check('the family, block, DWG layer and handle that every box carries are the model\'s (ASCII; the word none where the model has nothing)', ok)
    wide = [p['id'] for p in PIECES if not (p['family'] + p['block'] + p['layer']).isascii()]
    info(f'{len(wide)} pieces have letters outside ASCII in their family, block or layer ({", ".join(wide[:4])}): the script keeps the ASCII part, the CSV the full name')
    check('no double quote, backslash or control character inside any call, no bare minus before a number, no e-notation',
          all(not re.search(r'[\\\x00-\x1f]', c['raw'].replace('"', '')) and not re.search(r'(?<![(\w.])-\d', re.sub(r'"[^"]*"', '', c['raw'])) and 'e-' not in re.sub(r'"[^"]*"', '', c['raw']) for c in CALLS))
    # kinds, layers, the level
    check('the kind arrays are the model\'s kinds, in its order (only kinds that occur)', KEYS == [k['key'] for k in KINDS] and all(any(p['kind'] == k for p in PIECES) for k in KEYS), str(KEYS))
    check('layer suffix = the kind key in CamelCase (coffee-table -> CoffeeTable)', LAYERS == [camel(k) for k in KEYS], str(LAYERS))
    check('heights and bases (metres) = the model\'s mm / 1000 per kind', len(HEIGHTS) == len(BASES) == len(KINDS) and all(abs(h - k['height'] / 1000) < 1e-9 and abs(b - k['base'] / 1000) < 1e-9 for h, b, k in zip(HEIGHTS, BASES, KINDS)))
    lv = re.search(r'^    spinner lv "Floor level \(m\):" range:\[-50, 500, (-?\d+\.\d+)\]', TEXT, re.M)
    check(f'one level: every piece is on level {FLOOR!r}, the floors array is #("{FLOOR}") (the call\'s floor index is 1), and the script\'s level (PS_level and the window\'s Floor level) is the model\'s ({M["level"]} m)',
          all(p['floor'] == FLOOR for p in PIECES) and FLOORS_S == FLOORS and all(c['fi'] == 1 for c in CALLS if c['ok']) and LEVELS_S == [M['level']]
          and bool(lv) and float(lv.group(1)) == M['level'], f'{FLOORS_S} {LEVELS_S} {lv and lv.group(1)}')
    check(f'the furniture takes its level from the window\'s Floor level, as the parts do (the level expression is #({PX}_level))', f'    for z in (#({PX}_level)) do append {PX}_furnLevels z' in fn_text(f'{PX}_furnSetLevels'))
    layers = {}
    for c in CALLS:
        if c['ok'] and 1 <= c['fi'] <= len(FLOORS_S) and c['kind'] in KEYS: layers.setdefault(f"{PX}_{FLOORS_S[c['fi'] - 1]}_Furn_{LAYERS[KEYS.index(c['kind'])]}", []).append(c['id'])
    want = {f"{PX}_{p['floor']}_Furn_{camel(p['kind'])}" for p in PIECES}
    check(f'every box lands on layer {PX}_{FLOOR}_Furn_<Kind>: {len(layers)} layers, one per kind that occurs', set(layers) == want and len(want) == len(KINDS) and all(l == f"{PX}_{BY_ID[i]['floor']}_Furn_{camel(BY_ID[i]['kind'])}" for l, v in layers.items() for i in v))
    # materials: one per kind, indexed like the kinds
    check('one material per kind, "PS Furn <key>" with the kind\'s colour, in the kinds\' order (the box takes material[kind index])',
          [m[0] for m in MATERIALS] == KEYS and all(tuple(int(x) for x in m[1:]) == tuple(int(k['colour'][j:j + 2], 16) for j in (1, 3, 5)) for m, k in zip(MATERIALS, KINDS)), str(MATERIALS[:2]))
    # spinners
    n_occur = len({p['kind'] for p in PIECES})
    check(f'{len(SPINNERS)} height spinners = the kinds that occur ({n_occur}) = the model\'s kinds ({len(KINDS)})', len(SPINNERS) == n_occur == len(KINDS))
    ok = all(name == f'fh{i + 1}' and cap == caption_of(k) and int(d) == half_up(k['height']) and (int(lo), int(hi)) == (min(10, int(d)), max(5000, int(d)))
             for i, ((name, cap, _, lo, hi, d), k) in enumerate(zip(SPINNERS, KINDS)))
    check('spinner i belongs to kind i: its start value is the kind\'s height in whole mm (a half rounds up), its range 10 - 5000, its caption the label (16 characters at most) or the key in words', ok, str(SPINNERS[:2]))
    n_sp = len(SPINNERS)
    check(f'the spinners stand two to a row: across:2 on spinners 1, 3, 5 ... that have a partner, none on the partners and on a last one that stands alone ({n_sp} spinners, {(n_sp + 1) // 2} rows)',
          all((across == ' across:2') == (i % 2 == 0 and i + 1 < n_sp) for i, (_, _, across, _, _, _) in enumerate(SPINNERS)))
    width = int(re.search(rf'^rollout {PX}_UI "[^"]*" width:(\d+)$', TEXT, re.M).group(1))
    room = (width - 32) / 2 - (40 + 14 + 6)                                  # half the window (an estimate of both margins: 32 px) less the 40 px field, its arrows and a gap
    check(f'every caption fits its half of the {width} px window (an estimate: {room:.0f} px beside the 40 px field at 5.5 px a character: the longest caption is {max(len(c[1]) for c in SPINNERS)} characters) and the window is as wide as on 26 Oct',
          width == 340 and all(len(cap) * 5.5 <= room for _, cap, *rest in SPINNERS) and all(line.endswith('fieldwidth:40') for line in re.findall(r'^        spinner fh\d+ .*$', TEXT, re.M)))
    reads = [re.findall(r'(fh\d+)\.value / 1000\.0', ln) for ln in re.findall(r'^\s+' + PX + r'_furnHeights = (#\(\(fh.*)$', TEXT, re.M)]
    check(f'the code that reads the window (Build and Apply) reads fh1..fh{len(KINDS)} in the kinds\' order, in mm / 1000', len(reads) == 2 and all(r == [f'fh{i + 1}' for i in range(len(KINDS))] for r in reads), str([len(r) for r in reads]))
    sup = [c for c in CALLS if c['ok'] and c['supId'] != 'none']
    check(f'{len(sup)} boxes stand on a support: its id is one of the calls\' ids and it is a support kind', len(sup) == sum(1 for p in PIECES if p['on']) and all(c['supId'] in ids and KIND.get(c['supKind'], {}).get('support') for c in sup))


# ---- 3. every box -------------------------------------------------------------------------------------------------------------------

def test_geometry():
    section('every box: corners, base z and top z against the README\'s formulas')
    check('the transform is the explicit matrix3 [cos,sin,0] [-sin,cos,0] [0,0,1] [centre - shift, level + z0]',
          f'    o.transform = (matrix3 [ca, sa, 0.0] [(0.0 - sa), ca, 0.0] [0.0, 0.0, 1.0] [c.x - {PX}_shift.x, c.y - {PX}_shift.y, zb])' in LINES)
    fz = re.search(rf'^fn {PX}_furnZ0 ki oki =\n\(\n(.*?)\n\)\n', TEXT, re.M | re.S)
    check('z0 = the kind\'s base, or the support kind\'s base + height (a support never stands on anything)',
          bool(fz) and fz.group(1) == f'    local z0 = {PX}_furnBases[ki]\n    if oki > 0 do z0 = {PX}_furnBases[oki] + {PX}_furnHeights[oki]\n    z0')
    box = fn_text(f'{PX}_furnBox')
    check('base z = the level + z0, top z = base z + its kind\'s height', f'local zb = {PX}_furnLevels[fi] + z0' in box and f'local ht = {PX}_furnHeights[ki]' in box and 'height:ht' in box)
    bad, worst, worst_cs = geometry_problems(CALLS, KEYS, BASES, HEIGHTS, LEVELS_S)
    check(f'all {len(CALLS)} boxes: the four world corners from the matrix3 numbers and the size = the README\'s corners, the corners the script checks against = the README\'s (worst {worst * 1000:.3f} mm and {worst_cs * 1000:.3f} mm, limit 0.5 mm), cos / sin, centre, size, supports, base z and top z',
          not bad and len(CALLS) == len(PIECES), '; '.join(bad[:3]))
    n_on = sum(1 for p in PIECES if p['on'])
    tops = sorted({round(LEVEL[p['floor']] + readme_z0(p), 3) for p in PIECES if p['on']})
    info(f'{n_on} boxes stand on a support (base z values {", ".join(str(t) for t in tops)} m); the TV hangs at {KIND["tv"]["base"] / 1000 if "tv" in KIND else "-"} m')
    # slips in the data must be found
    rot = next(c for c in CALLS if c['ok'] and abs(c['sa'][0]) > 0.05 and abs(c['ca'][0]) > 0.05)
    flat = next(c for c in CALLS if c['ok'] and c['w'][0] > c['d'][0] + 0.05)
    onsup = next(c for c in CALLS if c['ok'] and c['supId'] != 'none' and c['supKind'] in KIND)
    nosup = next(c for c in CALLS if c['ok'] and c['supId'] == 'none')
    slips = [
        ('a rotation of the wrong sign (sin negated) on a turned box', lambda c: c[rot['id']]['sa'].__setitem__(0, -rot['sa'][0])),
        ('a centre moved by 1 mm', lambda c: c[flat['id']]['c'].__setitem__(0, flat['c'][0] + 0.001)),
        ('width and depth swapped', lambda c: (c[flat['id']]['w'].__setitem__(0, flat['d'][0]), c[flat['id']]['d'].__setitem__(0, flat['w'][0]))),
        ('a corner of the script\'s own check moved by 1 mm', lambda c: c[flat['id']]['cs'].__setitem__(0, flat['cs'][0] + 0.001)),
        ('a floor index that the suite does not have (2)', lambda c: c[flat['id']].__setitem__('fi', 2)),
        ('a box on a support that does not know its support', lambda c: c[onsup['id']].__setitem__('supKind', 'none')),
        ('a box on nothing whose support kind is an empty string, not the word none', lambda c: c[nosup['id']].__setitem__('supKind', '')),
        ('a box on nothing whose support id is an empty string, not the word none', lambda c: c[nosup['id']].__setitem__('supId', '')),
        ('a box on the wrong kind of support', lambda c: c[onsup['id']].__setitem__('supKind', next(k for k in KEYS if k != onsup['supKind'] and KIND[k]['height'] != KIND[onsup['supKind']]['height']))),
        ('a box of another kind', lambda c: c[flat['id']].__setitem__('kind', next(k for k in KEYS if k != flat['kind']))),
    ]
    for label, f in slips:
        by = {c['id']: copy.deepcopy(c) for c in CALLS if c['ok']}
        f(by)
        got = geometry_problems(list(by.values()), KEYS, BASES, HEIGHTS, LEVELS_S)[0]
        check(f'slip found: {label}', bool(got), 'NOT noticed')
    got = geometry_problems(CALLS, KEYS, BASES, HEIGHTS, [LEVELS_S[0] + 0.01] if LEVELS_S else [])[0]
    check('slip found: the script\'s level 1 cm off the model\'s', bool(got), 'NOT noticed')


# ---- 4. the code ------------------------------------------------------------------------------------------------------------------

def test_code():
    section('the code: add-only, apply heights, update heights; no box is ever collapsed or converted')
    build, add, apply_ = fn_text(f'{PX}_build'), fn_text(f'{PX}_furnAdd'), fn_text(f'{PX}_furnApply')
    at = lambda s: build.find(s) if s in build else 10 ** 9
    check('"Furniture boxes only": the first thing Build does (before its empty-scene check) is to hand over to furnAdd when the tick box says so, and to return false: furnAdd says what it did in a message of its own',
          bool(add) and at(f'if {PX}_furnAddOnly then') < at('if objects.count > 0 then') and f'        {PX}_furnAdd()\n        return false' in build and 'furnDone' not in build)
    check('... its own messages: "Added N furniture boxes. Every box passed its height and position checks ..." when all passed, "M of the N furniture boxes failed a check ... layer PS_Check_Failed" when some did; the structure script\'s message about parts is not used for it',
          f'if {PX}_failed.count == 0 then messageBox ("Added " + ({PX}_nodes.count as string) + " furniture boxes. Every box passed its height and position checks. Nothing else in this scene was changed.' in add
          and f'else messageBox (({PX}_failed.count as string) + " of the " + ({PX}_nodes.count as string) + " furniture boxes failed a check and are on layer {PX}_Check_Failed' in add
          and 'closed-solid' not in add and 'part(s)' not in add)
    check('... furnAdd refuses (and changes nothing) when "Build furniture boxes" is off, when System Units are not metres, and when boxes are there already',
          all(s in add for s in (f'if {PX}_furnWant == false then', 'units.systemType != #meters', f'(getUserProp o "{PX}_furn") != undefined or (matchPattern o.layer.name pattern:"{PX}_*_Furn_*")', 'return false')))
    check(f'... it takes the placement from the hidden datum {PX}_ORIGIN_DWG and the level from the objects that carry {PX}_floor and {PX}_base, else from the window and says so, adds the boxes and says how many',
          all(s in add for s in (f'o.name == "{PX}_ORIGIN_DWG"', f'{PX}_shift = [0.0 - datum.pos.x, 0.0 - datum.pos.y]', f'{PX}_furnSceneLevels()', 'so the level spinners are used for it', f'{PX}_furnAll()', 'FURNITURE BOXES ADDED')))
    check('... and it builds no structure and sets no System Units', f'{PX}_part' not in add and f'{PX}_room' not in add and 'units.systemType =' not in add and 'units.systemScale =' not in add)
    part = fn_text(f'{PX}_part')
    check(f'the parts are the 26 Oct code: {PX}_part carries {PX}_kind, {PX}_base and {PX}_follow and no {PX}_floor (the recipe\'s optional line is not added, so that a model without furniture still gives the 26 Oct script byte for byte); "Furniture boxes only" then takes the level from the window',
          all(f'setUserProp o "{PX}_{w}"' in part for w in ('kind', 'base', 'follow', 'check')) and f'"{PX}_floor"' not in part)
    check('"Apply furniture heights": the button is in the group "After the build", its handler reads the window and calls furnApply',
          bool(re.search(r'group "After the build"\n    \(\n        button upd .*\n        button col .*\n        button fap "Apply furniture heights" width:300\n    \)\n', TEXT)) and
          bool(re.search(rf'    on fap pressed do\n    \(\n        {PX}_furnHeights = #\(\(fh1\.value.*\n        local r = {PX}_furnApply\(\)\n', TEXT)))
    check('... furnApply sets each box\'s height and puts it on its kind\'s base or its support\'s top, keeps its level, and leaves a box that is not a Box any more alone',
          all(s in apply_ for s in ('if (classOf o) != Box or ki == 0 then skipped += 1', f'o.pos.z = o.pos.z - ({PX}_furnNum (getUserProp o "{PX}_base")) + z0', f'o.height = {PX}_furnHeights[ki]', f'setUserProp o "{PX}_base" z0')))
    upd, col = fn_text(f'{PX}_updateHeights'), fn_text(f'{PX}_collapseAll')
    fbox = fn_text(f'{PX}_furnBox')
    props = dict(re.findall(rf'setUserProp o "{PX}_(\w+)" (.*)$', fbox, re.M))
    check('"Update heights to Floor to floor" (not changed) visits only the objects whose follow is "true" and moves no level: a box carries follow = false, so it is left alone',
          f'where ((getUserProp o "{PX}_follow") as string) == "true" do' in upd and 'pos.z' not in upd and props.get('follow') == 'false')
    hits = [l for l in fbox.split('\n') if 'o.min.x' in l]
    check('the node\'s min / max in the plan (the world bounding box) is compared once, and only for an unrotated box (unrotated: sin of the rotation within 0.00001 of 0 and cos positive); base z, top z and the four corners are compared for every box',
          'local unrotated = abs(sa) < 0.00001 and ca > 0.0' in fbox and len(hits) == 1 and hits[0].startswith('    else if unrotated and (abs(o.min.x')
          and hits[0].endswith('then why = "bounding box"') and 'then why = "base z"' in fbox and 'then why = "top z"' in fbox and 'why = "corner " + (k as string)' in fbox, hits[0][:80] if hits else 'no line')
    check('the script says the rule twice, in the header of the furniture code and in the comment above the checks (only for an unrotated box), and nowhere speaks of a multiple of 90 degrees or of quarterTurn',
          TEXT.count('only for an unrotated box') == 2 and 'multiple of 90' not in TEXT and 'quarterTurn' not in TEXT, str(TEXT.count('only for an unrotated box')))
    check('... and every box carries floor (its index), base (z0) and follow = false',
          props.get('floor') == 'fi' and props.get('base') == 'z0' and props.get('follow') == 'false', str({k: props.get(k) for k in ('floor', 'base', 'follow')}))
    want = ['furn', 'furnKind', 'furnId', 'furnOn', 'furnOnKind', 'family', 'block', 'layer', 'handle', 'floor', 'base', 'follow', 'check']
    check('every box carries the user properties ' + ', '.join(f'{PX}_{w}' for w in want), all(w in props for w in want), str(sorted(props)))
    check('"Collapse all now" takes only objects that carry kind and a modifier: a box has neither (no kind property, no modifier)',
          f'where (getUserProp o "{PX}_kind") != undefined and o.modifiers.count > 0' in col and 'kind' not in props)
    furn = code('\n'.join(fn_text(f'{PX}_furn{n}') for n in ('Num', 'MakeMaterials', 'SetLevels', 'Z0', 'Box', 'All', 'Run', 'SceneLevels', 'Add', 'Apply')))
    check('the furniture code has no convertTo, collapseStack, Editable, addModifier, snapshotAsMesh, Extrude or splineShape and never reads the collapse tick box: a box stays a live Box',
          bool(furn) and not re.search(r'convertTo|collapseStack|Editable|addModifier|snapshotAsMesh|Extrude|splineShape', furn, re.I) and f'{PX}_collapse' not in furn)
    check('a box is made with the Box primitive, once, in furnBox only', furn.count(' = box name:nm width:w length:d height:ht') == 1 and code(TEXT).count('box name:') == 1)
    parts_collapse = [m.start() for m in re.finditer(r'convertToMesh', code(TEXT))]
    check('convertToMesh appears only in the part builder (after the tick box) and in "Collapse all now"; convertToPoly and convertTo nowhere',
          len(parts_collapse) == part.count('convertToMesh') + col.count('convertToMesh') and f'if {PX}_collapse do convertToMesh o' in part and not re.search(r'convertToPoly|convertTo\b|Editable_?Poly', code(TEXT), re.I))
    check('the build calls the furniture step after the parts and the room names, before the datum, and only when "Build furniture boxes" is ticked',
          bool(re.search(rf'\n    {PX}_room [^\n]*\n    if {PX}_furnWant do {PX}_furnRun\(\)\n    local origin = point name:"{PX}_ORIGIN_DWG"', TEXT)))


# ---- 5. the generator and the script of 26 Oct --------------------------------------------------------------------------------

def run_generator(model_bytes):
    """The generator, copied to a temporary folder with the module and a model, run there; returns (script text with LF, stdout)."""
    tmp = Path(tempfile.mkdtemp(prefix='pres_ms_'))
    try:
        g = tmp / 'presidential_test' / 'src' / 'generate_maxscript.py'
        g.parent.mkdir(parents=True)
        shutil.copy(GENERATOR, g)
        (g.parent / 'pres2_model.json').write_bytes(model_bytes)
        (tmp / 'furniture').mkdir()
        shutil.copy(MODULE, tmp / 'furniture' / 'furniture_max.py')
        out = tmp / 'out.ms'
        r = subprocess.run([sys.executable, '-B', str(g), str(out)], capture_output=True, text=True, encoding='utf-8',
                           env={**os.environ, 'PYTHONIOENCODING': 'utf-8'}, cwd=str(tmp))
        if r.returncode != 0: raise RuntimeError(f'generator failed:\n{r.stdout[-500:]}\n{r.stderr[-1000:]}')
        return out.read_bytes().decode('latin-1').replace('\r\n', '\n'), r.stdout
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


_REFERENCE = []


def reference():
    """(script, stdout) the generator writes for the model without its furniture keys, or None when it fails; run once."""
    if not _REFERENCE:
        plain = {k: v for k, v in M.items() if k not in ('furnitureKinds', 'furniture')}
        try: _REFERENCE.append(run_generator(json.dumps(plain, ensure_ascii=False).encode('utf-8')))
        except RuntimeError as e: _REFERENCE.append(None); print('      the generator failed on the model without furniture: ' + str(e)[:300])
    return _REFERENCE[0]


def stamp_masked(t): return re.sub(r'model data [0-9a-f]{12}', 'model data <sha1 of the model file>', t).split('\n')


def is_subsequence(old, new):
    """Every line of `old` is in `new`, in the same order (a greedy walk); returns (True, -1) or (False, the first old line that is missing)."""
    j = 0
    for i, line in enumerate(old):
        while j < len(new) and new[j] != line: j += 1
        if j == len(new): return False, i
        j += 1
    return True, -1


def test_generator():
    section('the generator: what it writes today, for a model without furniture, and the script of 26 Oct')
    try:
        again, out = run_generator(MODEL_RAW)
    except RuntimeError as e:
        check('the generator runs on the real model', False, str(e)); return
    first = next((i for i, (a, b) in enumerate(zip(again.split('\n'), LINES)) if a != b), None)
    check('the script on disk is exactly what the generator writes today from this model (it is not stale)', again == TEXT, f'first difference at line {first and first + 1}')
    check('the generator printed the furniture summary and its five sanity flags are all True',
          f'furniture boxes {len(PIECES)} (' in out and f'height spinners {len(KINDS)}' in out and 'balanced ( ): True | [ ]: True | even quotes: True | ascii only: True | no placeholders left: True' in out, out[-300:])
    ref = reference()
    if not check('the generator runs on the model without its furniture keys', ref is not None): return
    base, out = ref
    check('a model without furniture: no furniture line at all (no furn / Furn / fh1 / fap anywhere), and the generator says so', not re.search(r'furn|fh\d|\bfap\b', base, re.I) and out.startswith('no furniture'), out[:60])
    ops = [o for o in difflib.SequenceMatcher(None, stamp_masked(base), stamp_masked(TEXT), autojunk=False).get_opcodes() if o[0] != 'equal']
    n_new = sum(o[4] - o[3] for o in ops)
    check('with furniture the script differs from the one without only by inserted lines (nothing of the structure script is changed or moved)', bool(ops) and all(o[0] == 'insert' for o in ops), str([o[0] for o in ops]))
    first_lines = [stamp_masked(TEXT)[o[3]][:44] for o in ops]
    want_first = ['-- Furniture boxes: one coloured placeholder', '-- Furniture boxes: one coloured Box per piece,', f'    if {PX}_furnAddOnly then', f'    if {PX}_furnWant do {PX}_furnRun()',
                  '    group "Furniture boxes (heights in mm)"', '        button fap "Apply furniture heights" width:300', f'        {PX}_furnHeights = #((fh1.value / 1000.0)', '    on fap pressed do']
    anchors = ['global PS_mats', ')', '(', '    PS_room ', '    spinner ht "Floor to floor (m):"', '        button col "Collapse all now', '        PS_shift = if dwg.checked', '    )']
    after = [stamp_masked(TEXT)[o[3] - 1] for o in ops]
    check(f'... in the eight places of the recipe (after global PS_mats, before fn PS_build, after its opening paren, after the room names, after the Floor to floor spinner, after the Collapse button, after the PS_shift line, before the rollout\'s closing paren): {len(ops)} hunks, {n_new} new lines',
          len(ops) == 8 and all(f.startswith(w[:44]) for f, w in zip(first_lines, want_first)) and all(a.startswith(w) for a, w in zip(after, anchors))
          and stamp_masked(TEXT)[ops[1][4]] == 'fn PS_build =' and stamp_masked(TEXT)[ops[7][4]] == ')' and stamp_masked(TEXT)[ops[7][4] + 1] == 'createDialog PS_UI', str(first_lines))
    info(f'{len(base)} -> {len(TEXT)} characters; the script without furniture is {len(stamp_masked(base)) - 1} lines, the real one {len(LINES) - 1}; new lines: '
         + ', '.join(f'{o[3] + 1}-{o[4]}' if o[4] - o[3] > 1 else f'{o[4]}' for o in ops))
    # the script of 26 Oct, the one the owner ran in 3ds Max
    if not PREVIOUS.exists(): skip('the script the owner ran on 26 Oct', f'{PREVIOUS.relative_to(ROOT)} not found')
    else:
        raw_prev = PREVIOUS.read_bytes()
        old = raw_prev.decode('latin-1').replace('\r\n', '\n')
        check(f'the fallback copy previous_before_furniture_2026-10-29/ is the script the owner ran in 3ds Max on 26 Oct (sha1 {PREVIOUS_SHA1[:8]}..., stamp {MODEL_26OCT})',
              hashlib.sha1(raw_prev).hexdigest() == PREVIOUS_SHA1 and f'(model data {MODEL_26OCT})' in old.split('\n')[1], hashlib.sha1(raw_prev).hexdigest())
        diff_lines = [i + 1 for i, (a, b) in enumerate(zip(old.split('\n'), base.split('\n'))) if a != b]
        check('a model without furniture gives the 26 Oct script back byte for byte, apart from the stamp line (line 2: the sha1 of the model data)',
              len(old.split('\n')) == len(base.split('\n')) and diff_lines == [2] and stamp_masked(old) == stamp_masked(base), f'lines that differ: {diff_lines[:5]}')
        cut = MODEL_RAW.find(b',"furnitureKinds"')
        model_26 = MODEL_RAW[:cut] + b'}' if cut > 0 else b''
        if hashlib.sha1(model_26).hexdigest()[:12] != MODEL_26OCT:
            skip('the model of 26 Oct gives the 26 Oct script back byte for byte, stamp included', f'the text of pres2_model.json before its furniture keys is not the model of 26 Oct any more (sha1 {hashlib.sha1(model_26).hexdigest()[:12]}): its structure was rebuilt')
        else:
            try: again26, _ = run_generator(model_26)
            except RuntimeError as e: again26 = None; info(str(e)[:200])
            check(f'the model of 26 Oct (the text of pres2_model.json before its furniture keys, sha1 {MODEL_26OCT}) gives the 26 Oct script back byte for byte, stamp included',
                  again26 is not None and again26.replace('\n', '\r\n').encode('latin-1') == raw_prev)
        ops26 = [o for o in difflib.SequenceMatcher(None, stamp_masked(old), stamp_masked(TEXT), autojunk=False).get_opcodes() if o[0] != 'equal']
        check('the real script differs from the 26 Oct script only by inserted lines (no line of it is changed, moved or deleted), in the eight places of the recipe, apart from the stamp line',
              len(ops26) == 8 and all(o[0] == 'insert' for o in ops26) and all(stamp_masked(TEXT)[o[3]].startswith(w[:44]) for o, w in zip(ops26, want_first)), str([o[0] for o in ops26]))
        sub, miss = is_subsequence(stamp_masked(old), stamp_masked(TEXT))
        n26, n_now = len(old.split('\n')) - 1, len(LINES) - 1
        check(f'every line of the 26 Oct script is still in the real script, in its order ({n26} lines; the real script has {n_now}, {n_now - n26} of them new, all in the 8 inserted blocks)',
              sub and n_now - n26 == sum(o[4] - o[3] for o in ops26), f'missing from line {miss + 1}' if not sub else f'{n_now - n26} new lines')
        info(f'26 Oct script: {n26} lines, stamp {re.search(r"model data ([0-9a-f]{12})", old).group(1)}; real script: {n_now} lines, stamp {re.search(r"model data ([0-9a-f]{12})", TEXT).group(1)}')
    # the vocabulary is the same one the module's own test reviewed
    if ms is not None:
        _, p0, k0 = ms.words(ms.tokenize(base)[0])
        _, p1, k1 = ms.words(ms.tokenize(TEXT)[0])
        new_p, new_k = sorted(p1 - p0, key=str.lower), sorted(k1 - k0, key=str.lower)
        check(f'the properties and keyword arguments the furniture code adds were reviewed (after a dot: {", ".join(new_p)}; keyword: {", ".join(new_k)})',
              {x.lower() for x in new_p} <= {'width', 'length', 'height', 'transform', 'layer'} and {x.lower() for x in new_k} <= {'length', 'pattern', 'across'}, f'{new_p} {new_k}')
    # a half rounds up: the real generator on the real model with office heights of 740.5 and 460.5 mm (the model's own heights are whole mm)
    M2 = copy.deepcopy(M)
    for k in M2['furnitureKinds']: k['height'] = {'table': 740.5, 'coffee-table': 460.5}.get(k['key'], k['height'])
    try: again2, _ = run_generator(json.dumps(M2, ensure_ascii=False).encode('utf-8'))
    except RuntimeError as e: check('the generator runs on the model with office heights of 740.5 and 460.5 mm', False, str(e)[:200]); return
    sp2 = {k['key']: int(s[5]) for k, s in zip(KINDS, SPINNER_LINE.findall(again2))}
    hs2 = floats((re.search(rf'^global {PX}_furnHeights = (#\(.*\))$', again2, re.M) or (None, ''))[1])
    check(f'office heights of 740.5 and 460.5 mm start the spinners at 741 and 461 and build the boxes {hs2[KEYS.index("table")] if hs2 else "?"} and {hs2[KEYS.index("coffee-table")] if hs2 else "?"} m high: a half rounds up, as in the viewer and the CSV (Python round() would say {round(740.5)} and {round(460.5)})',
          sp2.get('table') == 741 and sp2.get('coffee-table') == 461 and len(hs2) == len(KINDS) and abs(hs2[KEYS.index('table')] - 0.741) < 1e-9 and abs(hs2[KEYS.index('coffee-table')] - 0.461) < 1e-9, str(sp2))
    # invalid data stops the generator, as for parts (it prints DATA PROBLEMS and writes no script)
    M3 = copy.deepcopy(M)
    M3['furniture'][0]['floor'] = 'L1'
    try: run_generator(json.dumps(M3, ensure_ascii=False).encode('utf-8')); stopped = ''
    except RuntimeError as e: stopped = str(e)
    check(f'a piece on a level the suite does not have (L1 instead of {FLOOR}) stops the generator with DATA PROBLEMS, as a bad part does', 'DATA PROBLEMS' in stopped and "unknown level 'L1'" in stopped, stopped[:120])


# ---- lint with teeth -----------------------------------------------------------------------------------------------------------

def test_lint_teeth():
    section('the lint finds slips that are put into the real script on purpose')
    if ms is None: skip('lint sensitivity', 'maxscript_lite.py not found'); return
    last = CALLS[-1]['raw']
    slips = [
        ('a then is missing', lambda t: t.replace('if oki > 0 do z0', 'if oki > 0 z0', 1), 'lint'),
        ('an else without if', lambda t: t.replace('    local why = ""\n', '    local why = ""\n    else why = "x"\n', 1), 'lint'),
        ('a ) is missing', lambda t: t.replace('        local hw = o.width / 2.0\n', '        local hw = (o.width / 2.0\n', 1), 'lint'),
        ('a quote is missing', lambda t: t.replace(f'setUserProp o "{PX}_furnId" pid', f'setUserProp o "{PX}_furnId pid', 1), 'lint'),
        ('a for without do', lambda t: t.replace('for k = 1 to 4 do', 'for k = 1 to 4', 1), 'lint'),
        ('a global misspelt once', lambda t: t.replace(f'{PX}_furnHeights[ki]\n    local zb', f'{PX}_furnHeigths[ki]\n    local zb', 1), 'names'),
        ('a local misspelt once', lambda t: t.replace('local zb = ', 'local zbb = ', 1), 'names'),
        ('an argument dropped from the last real call', lambda t: t.replace(last, last.rsplit(' ', 1)[0], 1), 'arity'),
        ('an argument added to a real call', lambda t: t.replace(last, last + ' "x"', 1), 'arity'),
    ]
    base_unres = ms.unresolved(TEXT)
    for label, f, kind in slips:
        t = f(TEXT)
        found = t != TEXT and ((kind == 'lint' and ms.lint(t)) or (kind == 'arity' and ms.arity_errors(t)) or (kind == 'names' and ms.unresolved(t) - base_unres))
        check(f'lint slip found: {label}', found, 'NOT noticed')


# ---- 6. the generated functions, run by the interpreter over a mock scene ---------------------------------------------------------

def mock_read_text():
    i = next(k for k, l in enumerate(LINES) if l.startswith(f'        {PX}_shift = if dwg.checked'))
    return '\n'.join(LINES[i + 1:i + 4])                  # the three lines of "on build pressed" that read the window's furniture controls


def mock_apply_text():
    j = LINES.index('    on fap pressed do')
    k = next(k for k in range(j + 2, len(LINES)) if LINES[k] == '    )')
    return '\n'.join(LINES[j + 1:k + 1])                  # the block of "on fap pressed do"


def controls(values=None, want=True, only=False):
    vals = values or [half_up(k['height']) for k in KINDS]
    c = {f'fh{i + 1}': mk.Control(value=v) for i, v in enumerate(vals)}
    c.update(fb=mk.Control(checked=want), fo=mk.Control(checked=only))
    return c


def install_fakes(it):
    """The part and room builders need splines and modifiers; stand-ins make the nodes the real ones make: a part at the level + z0 with
    the user properties kind, base, follow and check (and no floor, as in the real PS_part), a room name at the level + 0.02 with none,
    so that Update heights, Collapse all and the datum can be tried. The furniture code is the real one."""
    def part(it, kind, nm, loops, z0, z1, follow, c, mn, mx):
        sh = it.get(f'{PX}_shift')
        n = mk.Node(it.scene, mk.Cls('SplineShape'), nm)
        n.tm.rows[3] = mk.P(c.v[0] - sh.v[0], c.v[1] - sh.v[1], it.get(f'{PX}_level') + z0)
        n.props.update({f'{PX}_kind': str(kind), f'{PX}_base': mk.tostr(z0), f'{PX}_follow': mk.tostr(follow), f'{PX}_check': 'ok'})
        it.get(f'{PX}_nodes').append(n)
        return n

    def room(it, nm, p):
        sh = it.get(f'{PX}_shift')
        n = mk.Node(it.scene, mk.Cls('Text'), f'{PX}_Room_{nm}')
        n.tm.rows[3] = mk.P(p.v[0] - sh.v[0], p.v[1] - sh.v[1], it.get(f'{PX}_level') + 0.02)
        it.get(f'{PX}_nodes').append(n)
        return n
    it.override(f'{PX}_part', part)
    it.override(f'{PX}_room', room)


def make_run(shift=(0.0, 0.0), values=None, want=True, only=False, scene=None, text=None, level=None):
    it = mk.Interp(text or TEXT, scene)             # (a damaged copy of the script's text, for the negative controls, or the real script)
    install_fakes(it)
    it.run(mock_read_text(), **controls(values, want, only))              # the code of "on build pressed" that reads the window
    it.set(f'{PX}_shift', mk.P(*shift))
    if level is not None: it.set(f'{PX}_level', level)                   # the window's Floor level (the script starts with the model's)
    return it


def boxes_of(it): return {n.props[f'{PX}_furnId']: n for n in it.scene.objects if f'{PX}_furn' in n.props}
def snap(it): return {pid: (n.name, [r.v[:] for r in n.tm.rows], dict(n.params), n.layer.name, dict(n.props)) for pid, n in boxes_of(it).items()}


def box_problems(it, levels, shift, mm=None, skip_props=()):
    """Every box of the scene against the README: class, matrix3, size, base corners, layer, material, wire colour, properties."""
    mm, bad = mm or {}, []
    found = boxes_of(it)
    if sorted(found) != sorted(BY_ID): bad.append(f'{len(found)} boxes for {len(BY_ID)} pieces')
    for pid, n in found.items():
        p = BY_ID.get(pid)
        if p is None: bad.append(f'{pid}: not in the model'); continue
        k = KIND[p['kind']]
        z = levels[FLOORS.index(p['floor'])] + readme_z0(p, mm)
        a = math.radians(p['rot'])
        rows = [[math.cos(a), math.sin(a), 0.0], [-math.sin(a), math.cos(a), 0.0], [0.0, 0.0, 1.0], [p['x'] + OX - shift[0], p['y'] + OY - shift[1], z]]
        if n.cls.name != 'Box' or n.modifiers: bad.append(f'{pid}: not a plain Box ({n.cls.name}, {len(n.modifiers)} modifiers)')
        for i in range(4):
            d = max(abs(x - y) for x, y in zip(n.tm.rows[i].v, rows[i]))
            if d > (1e-6 if i == 3 else 1e-8): bad.append(f'{pid}: matrix row {i + 1} off by {d:.2e}')
        for key, want in (('width', p['w']), ('length', p['d']), ('height', mm.get(p['kind'], k['height']) / 1000)):
            if abs(n.params[key] - want) > 1e-4: bad.append(f'{pid}: {key} {n.params[key]} != {want}')
        base, want = [c.v[:2] for c in n.corners() if abs(c.v[2] - z) < 1e-9], readme_corners(p, shift)
        if len(base) != 4 or any(min(math.dist(w, g) for g in base) > TOL for w in want) or any(min(math.dist(w, g) for w in want) > TOL for g in base): bad.append(f'{pid}: the corners of its base differ from the README\'s')
        lay = f"{PX}_{p['floor']}_Furn_{camel(p['kind'])}"
        if n.layer is None or n.layer.name != lay: bad.append(f'{pid}: layer {n.layer and n.layer.name} != {lay}')
        rgb = tuple(int(k['colour'][j:j + 2], 16) for j in (1, 3, 5))
        if n.material is None or n.material.name != f"{PX} Furn {p['kind']}" or n.material.diffuse != mk.Color(*rgb) or n.wirecolor != n.material.diffuse: bad.append(f'{pid}: material or wire colour')
        want_props = {'furn': 'true', 'furnKind': p['kind'], 'furnId': pid, 'furnOn': p['on'] or 'none', 'furnOnKind': BY_ID[p['on']]['kind'] if p['on'] else 'none',
                      'family': none_text(p['family']), 'block': none_text(p['block']), 'layer': none_text(p['layer']), 'handle': none_text(p['handle']),
                      'floor': str(FLOORS.index(p['floor']) + 1), 'follow': 'false', 'check': 'ok'}
        for key, want in want_props.items():
            if key not in skip_props and n.props.get(f'{PX}_{key}') != want: bad.append(f'{pid}: property {key} = {n.props.get(f"{PX}_{key}")!r}, wanted {want!r}')
        if abs(float(n.props[f'{PX}_base']) - readme_z0(p, mm)) > 1e-5: bad.append(f'{pid}: {PX}_base {n.props[f"{PX}_base"]}')
    return bad


def test_mock():
    section('the real script run by the interpreter of the fixtures over a mock 3ds Max (the part builders are stand-ins, the furniture code is the real one)')
    if mk is None: skip('mock Max run', 'furniture/fixtures/maxscript_mock.py not found'); return
    levels = [LEVEL[FLOOR]]
    default = {k['key']: half_up(k['height']) for k in KINDS}
    typed = {k['key']: default[k['key']] + 10 * (i + 1) for i, k in enumerate(KINDS)}
    typed.update({'table': 800, 'coffee-table': 400} if 'table' in typed else {})
    n_parts, n_rooms = len(M['parts']), len(M['rooms'])
    try:
        it = make_run()
        ok = it.call(f'{PX}_build')
        nodes = it.get(f'{PX}_nodes')
        check(f'Build (the drawing\'s own coordinates) runs to the end in an empty scene and returns true: {len(it.scene.objects)} objects ({n_parts} parts, {n_rooms} room names, {len(PIECES)} boxes, the datum)',
              ok is True and len(it.scene.objects) == n_parts + n_rooms + len(PIECES) + 1)
        bad = box_problems(it, levels, (0.0, 0.0))
        check(f'... all {len(PIECES)} boxes are plain Box objects with the README\'s matrix3, size, base corners, layer, material, wire colour and properties', not bad, '; '.join(bad[:3]))
        check(f'... every box passed its own checks (nothing in the failed list or on PS_Check_Failed, no message box), and the Listener says "{PX} BUILD COMPLETE: {len(nodes)} objects in ... s, 0 failed checks"',
              it.get(f'{PX}_failed') == [] and f'{PX}_check_failed'.lower() not in it.scene.layers and it.scene.messages == []
              and any(s.startswith(f'{PX} BUILD COMPLETE: {len(nodes)} objects in ') and s.rstrip().endswith(' 0 failed checks') for s in it.scene.listener), str(it.get(f'{PX}_failed')[:2]) + str(it.scene.listener[-1:]))
        check(f'... the boxes are part of the node list the footer selects and the final message counts ({len(nodes)} = {n_parts} + {n_rooms} + {len(PIECES)}: "Built {len(nodes)} objects"), and the hidden datum is made after them',
              len(nodes) == n_parts + n_rooms + len(PIECES) and sum(1 for n in nodes if f'{PX}_furn' in n.props) == len(PIECES) and any(n.name == f'{PX}_ORIGIN_DWG' for n in it.scene.objects)
              and it.scene.objects.index(next(n for n in it.scene.objects if n.name == f'{PX}_ORIGIN_DWG')) == len(it.scene.objects) - 1)
        check(f'... {len({n.layer.name for n in boxes_of(it).values()})} furniture layers {PX}_{FLOOR}_Furn_<Kind>, none of them holding anything but its boxes',
              {n.layer.name for n in boxes_of(it).values()} == {f'{PX}_{FLOOR}_Furn_{camel(k)}' for k in KEYS} and all(n.props.get(f'{PX}_furn') == 'true' for n in it.scene.objects if n.layer and '_Furn_' in n.layer.name))
        it2 = make_run(shift=(OX, OY))
        it2.call(f'{PX}_build')
        bad = box_problems(it2, levels, (OX, OY))
        check('Build centred on the origin (shift = the offset): every box follows, no check fails', not bad and it2.get(f'{PX}_failed') == [], '; '.join(bad[:3]))
        it3 = make_run(want=False)
        it3.call(f'{PX}_build')
        check(f'"Build furniture boxes" unticked: no box, no furniture layer, no furniture material: the 26 Oct build ({len(it3.scene.objects)} objects)',
              boxes_of(it3) == {} and not any('_furn_' in k for k in it3.scene.layers) and not it3.get(f'{PX}_furnMats') and len(it3.scene.objects) == n_parts + n_rooms + 1)
        it4 = make_run(values=[typed[k['key']] for k in KINDS])
        it4.call(f'{PX}_build')
        check('Build with other heights typed in the window: every box has its kind\'s typed height, the boxes on supports stand on the typed tops',
              not box_problems(it4, levels, (0.0, 0.0), typed))
        it4b = make_run(level=1.5)
        it4b.call(f'{PX}_build')
        check('Build with another Floor level in the window (1.50 m): every box stands on that level, as the parts do', not box_problems(it4b, [1.5], (0.0, 0.0)) and it4b.get(f'{PX}_failed') == [])
        # Apply after the build
        it5 = make_run()
        it5.call(f'{PX}_build')
        it5.run(mock_apply_text(), **controls([typed[k['key']] for k in KINDS]))
        bad = box_problems(it5, levels, (0.0, 0.0), typed)
        msg = it5.scene.messages[-1][0] if it5.scene.messages else ''
        check(f'"Apply furniture heights": new heights, boxes re-seated on their supports, the message says {len(PIECES)} boxes and nothing was left alone', not bad and msg.startswith(f'{len(PIECES)} furniture boxes set to the heights') and 'left alone' not in msg, '; '.join(bad[:3]) + msg[:80])
        # Update heights to Floor to floor: the parts that follow the wall height, never a box
        before = snap(it5)
        r = it5.call(f'{PX}_updateHeights', 3.5)
        n_follow = sum(1 for n in it5.scene.objects if n.props.get(f'{PX}_follow') == 'true')
        check(f'"Update heights to Floor to floor" (3.50 m) visits only the {n_follow} parts that follow the wall height (the stand-ins have no Extrude, so they count as skipped: {r}) and leaves every box where and as high as it was',
              snap(it5) == before and r == [0, n_follow] and n_follow > 0, str(r))
        it5.run(mock_apply_text(), **controls([typed[k['key']] + 5 for k in KINDS]))
        bad = box_problems(it5, levels, (0.0, 0.0), {k: v + 5 for k, v in typed.items()})
        check('... and "Apply furniture heights" after it still puts every box on its support or its kind\'s base', not bad, '; '.join(bad[:3]))
        # Collapse: the tick box before Build and the button after it never take a box
        it6 = make_run()
        it6.set(f'{PX}_collapse', True)
        it6.call(f'{PX}_build')
        part = next(n for n in it6.scene.objects if f'{PX}_kind' in n.props)
        part.modifiers.append('Extrude')
        got = it6.call(f'{PX}_collapseAll')
        conv_boxes = [n for n in it6.scene.converted if f'{PX}_furn' in n.props]
        check(f'"Collapse to Editable Mesh" ticked, then "Collapse all now": the part with a modifier is converted ({got}), no box ever is: every box is still a plain Box', got == 1 and it6.scene.converted == [part] and not conv_boxes and not box_problems(it6, levels, (0.0, 0.0)))
        # Furniture boxes only, on a scene built without furniture (centred on the origin)
        ref = make_run(shift=(OX, OY))
        ref.call(f'{PX}_build')
        base = make_run(shift=(OX, OY), want=False)
        base.call(f'{PX}_build')
        n_before = len(base.scene.objects)
        base.run(mock_read_text(), **controls(None, True, True))                           # the box ticks: furniture boxes only
        base.set(f'{PX}_shift', mk.P(0.0, 0.0))                                            # the window says "the drawing's own coordinates" (wrong for this scene)
        ok = base.call(f'{PX}_build')
        msgs = [m[0] for m in base.scene.messages]
        check(f'"Furniture boxes only" on a scene built without furniture: adds exactly the {len(PIECES)} boxes (objects {n_before} -> {len(base.scene.objects)}), no empty-scene refusal, says in a first message that the level was not found in the scene (the parts carry no {PX}_floor) so the window\'s level is used, then "Added {len(PIECES)} furniture boxes. Every box passed its height and position checks.", and Build returns false',
              ok is False and len(base.scene.objects) == n_before + len(PIECES) and len(msgs) == 2 and msgs[0].startswith('The level of 1 floor(s) was not found in the scene, so the level spinners are used for it.')
              and msgs[1].startswith(f'Added {len(PIECES)} furniture boxes. Every box passed its height and position checks.') and 'closed-solid' not in ' '.join(msgs), str(msgs[:2]))
        check('... the placement shift comes from the datum (the window said shift 0) and the level from the window (the same as the build\'s): the boxes are identical to those of a single Build', snap(base) == snap(ref))
        check('... the Listener reports it: "PS FURNITURE BOXES ADDED: N boxes ..., 0 failed checks"', any(s.startswith(f'{PX} FURNITURE BOXES ADDED: {len(PIECES)} boxes') and s.rstrip().endswith('0 failed checks') for s in base.scene.listener))
        n_now = len(base.scene.objects)
        base.run(mock_read_text(), **controls(None, True, True))
        ok = base.call(f'{PX}_build')
        check('... a second time it refuses politely (boxes exist), returns false and changes nothing', ok is False and 'already has furniture boxes' in base.scene.messages[-1][0] and len(base.scene.objects) == n_now)
        lv9 = make_run(shift=(OX, OY), want=False)
        lv9.call(f'{PX}_build')
        lv9.run(mock_read_text(), **controls(None, True, True))
        lv9.set(f'{PX}_level', 9.0)                                                        # the window's Floor level is not the one the scene was built at
        ok = lv9.call(f'{PX}_build')
        check('... with another level in the window (9.0) the boxes stand at that level (the scene cannot tell: the parts carry no PS_floor) and the first message says the window\'s level was used',
              ok is False and not box_problems(lv9, [9.0], (OX, OY)) and lv9.scene.messages[0][0].startswith('The level of 1 floor(s) was not found'))
        other = make_run(shift=(OX, OY), want=False)
        other.call(f'{PX}_build')
        other.scene.units['systemtype'] = mk.Sym('millimeters')
        other.run(mock_read_text(), **controls(None, True, True))
        n0 = len(other.scene.objects)
        ok = other.call(f'{PX}_build')
        check('... in a scene whose System Units are not metres it refuses and changes nothing', ok is False and 'System Units are not metres' in other.scene.messages[-1][0] and len(other.scene.objects) == n0)
        other = make_run(shift=(OX, OY), want=False)
        other.call(f'{PX}_build')
        other.run(mock_read_text(), **controls(None, False, True))
        n0 = len(other.scene.objects)
        ok = other.call(f'{PX}_build')
        check('... with "Build furniture boxes" unticked it refuses and changes nothing', ok is False and 'Tick Build furniture boxes' in other.scene.messages[-1][0] and len(other.scene.objects) == n0)
        other = make_run(shift=(OX, OY), want=False)
        other.call(f'{PX}_build')
        own = mk.Node(other.scene, mk.Cls('Editable_Mesh'), 'their sofa'); other.scene.layer(f'{PX}_{FLOOR}_Furn_Sofa').add(own)
        other.run(mock_read_text(), **controls(None, True, True))
        n0 = len(other.scene.objects)
        ok = other.call(f'{PX}_build')
        check(f'... when the 3D team already put their own model on a {PX}_*_Furn_* layer it refuses (no second set of boxes)', ok is False and len(other.scene.objects) == n0 and 'already has furniture boxes (1 objects)' in other.scene.messages[-1][0])
        other = make_run(shift=(OX, OY), want=False)
        other.call(f'{PX}_build')
        other.scene.objects[:] = [n for n in other.scene.objects if n.name != f'{PX}_ORIGIN_DWG']
        other.run(mock_read_text(), **controls(None, True, True))
        other.set(f'{PX}_shift', mk.P(OX, OY))                                             # the window's tick box: centred on the origin
        ok = other.call(f'{PX}_build')
        check('... without the datum the window\'s tick box decides the placement, a message says the datum was not found, then the success message',
              ok is False and not box_problems(other, levels, (OX, OY)) and 'origin datum' in other.scene.messages[0][0] and other.scene.messages[-1][0].startswith('Added '))
        # the 3D team's scene of 26 Oct: built by the 26 Oct script itself (centred on the origin), then the new script adds only the boxes
        if not PREVIOUS.exists(): skip('"Furniture boxes only" on a scene built by the 26 Oct script', f'{PREVIOUS.relative_to(ROOT)} not found')
        else:
            old = mk.Interp(PREVIOUS.read_bytes().decode('latin-1').replace('\r\n', '\n'))
            install_fakes(old)
            old.set(f'{PX}_shift', mk.P(OX, OY))
            built = old.call(f'{PX}_build')
            kept = {id(n): (n.name, [r.v[:] for r in n.tm.rows], dict(n.props), n.layer.name) for n in old.scene.objects}
            new = make_run(scene=old.scene, only=True)                                     # the new script in that scene, the window at its defaults
            ok = new.call(f'{PX}_build')
            msgs = [m[0] for m in new.scene.messages]
            check(f'"Furniture boxes only" with the new script on a scene built by the 26 Oct script itself ({len(kept)} objects, centred on the origin; the window at its defaults): the {len(PIECES)} boxes are added where the README puts them (the shift read from the datum), nothing of the 26 Oct scene moves or changes, two messages (the level from the window, then "Added {len(PIECES)} furniture boxes ...")',
                  built is True and ok is False and len(new.scene.objects) == len(kept) + len(PIECES) and not box_problems(new, levels, (OX, OY))
                  and all((n.name, [r.v[:] for r in n.tm.rows], dict(n.props), n.layer.name) == kept[id(n)] for n in new.scene.objects if id(n) in kept)
                  and len(msgs) == 2 and msgs[0].startswith('The level of 1 floor(s) was not found') and msgs[1].startswith(f'Added {len(PIECES)} furniture boxes.'), str(msgs[:2]))
    except mk.MaxError as e:
        check('the mock Max ran the real script to the end', False, str(e)[:300])


def test_none():
    section('the word none: a user property with nothing to say is never empty text, and Apply reads none, undefined and empty text alike')
    n_nosup = sum(1 for p in PIECES if not p['on'])
    n_noblk = sum(1 for p in PIECES if not ascii_fold(p['block']))
    n_nohnd = sum(1 for p in PIECES if not ascii_fold(p['handle']))
    check(f'no furnBox call passes an empty string: {n_nosup} boxes stand on nothing, {n_noblk} have no block, {n_nohnd} no handle, and every one of those says none',
          all('""' not in c['raw'] for c in CALLS) and sum(1 for c in CALLS if c['supId'] == 'none' and c['supKind'] == 'none') == n_nosup
          and sum(1 for c in CALLS if c['blk'] == 'none') == n_noblk and sum(1 for c in CALLS if c['hnd'] == 'none') == n_nohnd)
    if mk is None: skip('mock Max run of none / undefined', 'furniture/fixtures/maxscript_mock.py not found'); return
    levels = [LEVEL[FLOOR]]
    typed = {k['key']: half_up(k['height']) + 10 * (i + 1) for i, k in enumerate(KINDS)}
    typed.update({'table': 800, 'coffee-table': 400} if 'table' in typed else {})
    try:
        it = make_run()
        it.call(f'{PX}_build')
        held = [(n.props[f'{PX}_furnOn'], n.props[f'{PX}_furnOnKind'], n.props[f'{PX}_block'], n.props[f'{PX}_handle']) for n in boxes_of(it).values()]
        check(f'in the scene no box carries an empty property: the {n_nosup} boxes on nothing hold none for {PX}_furnOn and {PX}_furnOnKind',
              all(v != '' for t in held for v in t) and sum(1 for t in held if t[0] == t[1] == 'none') == n_nosup)

        def lose(value):                                           # after the build the boxes on nothing hold `value` (None: no such property) as their support
            def f(scene_it):
                for pid, n in boxes_of(scene_it).items():
                    if BY_ID[pid]['on']: continue
                    for key in (f'{PX}_furnOn', f'{PX}_furnOnKind'):
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
            it = make_run(scene=sc)
            it.call(f'{PX}_build')
            if after: after(it)
            it.run(mock_apply_text(), **controls([typed[k['key']] for k in KINDS]))
            bad = box_problems(it, levels, (0.0, 0.0), typed, skip_props=('furnOn', 'furnOnKind') if after else ())
            msg = it.scene.messages[-1][0] if it.scene.messages else ''
            check(f'"Apply furniture heights" ({how}): every box gets its typed height and stands on its support or on its kind\'s base, "{len(PIECES)} furniture boxes set ..."',
                  not bad and msg.startswith(f'{len(PIECES)} furniture boxes set to the heights') and 'left alone' not in msg, '; '.join(bad[:3]) + msg[:60])
    except mk.MaxError as e:
        check('the mock Max ran the real script to the end', False, str(e)[:300])


READINGS = (('the true world box', {}),                    # what Max reports as min / max of a TURNED node: nothing in Autodesk's text says which
            ('x and y 5 m too far', {'bbox_error_turned': {'min': {'x': 5.0, 'y': 5.0}, 'max': {'x': 5.0, 'y': 5.0}}}),
            ('the box pulled in by 1 m on every side, as if it were not turned', {'bbox_error_turned': {'min': {'x': 1.0, 'y': 1.0}, 'max': {'x': -1.0, 'y': -1.0}}}),
            ('the extents of the box as if it were not turned', {'bbox_unturned': True}))


def angle_only(deg):
    """The call's cos and sin for another angle (the corners stay the model's): a box built at the wrong angle."""
    r = math.radians(deg)
    return {'ca': [round(math.cos(r), 9)], 'sa': [round(math.sin(r), 9)]}


def turned_to(c, deg):
    """A really different box: the same centre and size turned to `deg`, with its own cos, sin and corners (all consistent)."""
    ch = angle_only(deg)
    (cx, cy), hw, hd, ca, sa = c['c'], c['w'][0] / 2, c['d'][0] / 2, ch['ca'][0], ch['sa'][0]
    pts = [(cx + ca * u - sa * v, cy + sa * u + ca * v) for u, v in ((-hw, -hd), (hw, -hd), (hw, hd), (-hw, hd))]
    ch['cs'] = [x for p in pts for x in p]
    return ch


def run_build(text=None, **flags):
    """A whole Build of the script (or of a copy of its text) in a mock scene whose min / max behave as `flags` say: (interpreter, result)."""
    sc = mk.Scene()
    for flag, v in flags.items(): setattr(sc, flag, v)
    it = make_run(scene=sc, text=text)
    return it, it.call(f'{PX}_build')


def build_one(pid, flags=None, text=None, **change):
    """One box built from its call with some arguments changed (what a wrong build would look like): (its check property, its layer)."""
    sc = mk.Scene()
    for flag, v in (flags or {}).items(): setattr(sc, flag, v)
    it = make_run(scene=sc, text=text)
    it.run(f'{PX}_furnMakeMaterials()\n{PX}_furnSetLevels()')
    a = dict(next(c for c in CALLS if c['id'] == pid), **change)
    it.call(f'{PX}_furnBox', a['kind'], a['name'], a['fi'], a['id'], a['supId'], a['supKind'], mk.P(*a['c']), a['w'][0], a['d'][0], a['ca'][0], a['sa'][0],
            [mk.P(x, y) for x, y in zip(a['cs'][0::2], a['cs'][1::2])], a['fam'], a['blk'], a['lay'], a['hnd'])
    n = boxes_of(it)[pid]
    return n.props[f'{PX}_check'], n.layer.name


def bbox_probe(text):
    """What is wrong with the rule 'the node's min / max are compared for an unrotated box only' in this text of the script (nothing: [])."""
    bad = []
    want = sorted(i for i in BY_ID if is_unrotated(BY_ID[i]['rot']))
    it, ok = run_build(text, bbox_error={'max': {'x': 0.01}})                    # every node reports a wrong max.x: the unrotated boxes fail, and only they
    failed, b = it.get(f'{PX}_failed'), boxes_of(it)
    if ok is not True or sorted(f[:-len(': bounding box')] for f in failed if f.endswith(': bounding box')) != sorted(b[i].name for i in want) or len(failed) != len(want):
        bad.append(f'a wrong max.x on every node: {len(failed)} boxes failed, not exactly the {len(want)} unrotated ones')
    for how, flags in READINGS[1:]:                                           # what Max may report for a turned node: no box built right fails for it
        it, ok = run_build(text, **flags)
        if ok is not True or it.get(f'{PX}_failed'): bad.append(f'min / max of a turned node ({how}): {len(it.get(f"{PX}_failed"))} boxes failed')
    c = next(c for c in CALLS if c['ok'] and BY_ID[c['id']]['rot'] == 0 and c['w'][0] > c['d'][0] + 0.05)
    for deg in (180.0, 0.01):                                                 # turned although sin is 0 or nearly 0: not compared, whatever Max reports
        got = build_one(c['id'], READINGS[1][1], text, **turned_to(c, deg))
        if got != ('ok', got[1]) or got[1] == f'{PX}_Check_Failed': bad.append(f'a box turned by {deg} degrees was compared with the node\'s min / max: {got[0]!r}')
    return bad


def test_bounding_box():
    section('the node\'s bounding box is compared only for an unrotated box; a box built wrong is still caught by a corner, base z, top z or the bounding box')
    if mk is None: skip('mock Max run of the checks', 'furniture/fixtures/maxscript_mock.py not found'); return
    unrot = [p['id'] for p in PIECES if is_unrotated(p['rot'])]
    q90 = [p['id'] for p in PIECES if abs(p['rot'] - 90) < 1e-9]
    other = [p['id'] for p in PIECES if not is_unrotated(p['rot']) and abs(p['rot'] - 90) >= 1e-9]
    nearly = [i for i in other if abs(math.sin(math.radians(BY_ID[i]['rot']))) < 0.01]
    info(f'{len(unrot)} of {len(PIECES)} boxes are unrotated (rot 0), {len(q90)} are turned by 90 degrees, {len(other)} by another angle ({len(nearly)} of them lie within 0.6 degree of the x axis: '
         + ', '.join(f'{i} {BY_ID[i]["rot"]}' for i in nearly) + f'): the node\'s min / max are compared for the {len(unrot)} unrotated ones only')
    check('the model has boxes of all three kinds (unrotated, turned by 90 degrees, turned by another angle), so that the checks below mean something',
          len(unrot) > 0 and len(q90) > 0 and len(other) > 0 and len(unrot) + len(q90) + len(other) == len(PIECES))
    try:
        it, ok = run_build(bbox_error={'max': {'x': 0.01}})                        # every node reports a wrong max.x
        b, failed = boxes_of(it), it.get(f'{PX}_failed')
        got = sorted(f[:-len(': bounding box')] for f in failed if f.endswith(': bounding box'))
        check(f'every node reports a wrong max.x: exactly the {len(unrot)} unrotated boxes fail with "bounding box" (on {PX}_Check_Failed, listed), the {len(q90)} boxes turned by 90 degrees and the {len(other)} turned by another angle stay on their layers; all {len(PIECES)} are built and Build returns true',
              ok is True and len(b) == len(PIECES) and got == sorted(b[i].name for i in unrot) and len(failed) == len(unrot)
              and all((b[i].layer.name == f'{PX}_Check_Failed') == (i in unrot) for i in b), f'{len(failed)} failed')
        for how, flags in READINGS:                                                # what Max reports for a turned node is not documented: no box built right fails for it
            it, ok = run_build(**flags)
            b = boxes_of(it)
            check(f'whatever Max reports as min / max of a turned box, a quarter turn included ({how}): none of the {len(q90) + len(other)} fails and nothing is on {PX}_Check_Failed',
                  ok is True and len(b) == len(PIECES) and it.get(f'{PX}_failed') == [] and f'{PX}_check_failed' not in it.scene.layers and it.scene.messages == [])
        for what, err, reason in (('min z 1 cm too high', {'min': {'z': 0.01}}, 'base z'), ('max z 1 cm too low', {'max': {'z': -0.01}}, 'top z')):
            it, ok = run_build(bbox_error=err)                                      # base z and top z are compared for every box, turned ones included
            b, failed = boxes_of(it), it.get(f'{PX}_failed')
            check(f'every node reports its {what}: all {len(PIECES)} boxes, the {len(q90) + len(other)} turned ones too, fail with "{reason}" (on {PX}_Check_Failed, listed); all are built and Build returns true',
                  ok is True and len(b) == len(PIECES) and len(failed) == len(PIECES) and all(f.endswith(': ' + reason) for f in failed)
                  and all(n.layer.name == f'{PX}_Check_Failed' and n.props[f'{PX}_check'] == reason for n in b.values()), f'{len(failed)} failed')

        t = next(c for c in CALLS if c['ok'] and 20 < BY_ID[c['id']]['rot'] % 90 < 70 and c['w'][0] > c['d'][0] + 0.05)      # a box well away from a quarter turn
        q = next(c for c in CALLS if c['ok'] and BY_ID[c['id']]['rot'] == 90 and c['w'][0] > c['d'][0] + 0.05)                # turned by 90 degrees, not square
        z = next(c for c in CALLS if c['ok'] and BY_ID[c['id']]['rot'] == 0 and c['w'][0] > c['d'][0] + 0.05)                 # unrotated, not square
        it, ok = run_build(bbox_unturned=True)                                      # the mock's second reading must differ from the true one where it matters
        ex = mk.getprop(boxes_of(it)[q['id']], 'max').v[0] - mk.getprop(boxes_of(it)[q['id']], 'min').v[0]
        check(f'(the mock) the second reading is not vacuous: {q["id"]}, {q["w"][0]} x {q["d"][0]} m, turned by 90 degrees, reports {ex:.2f} m along x, as if it were not turned ({q["w"][0]} m), not the true {q["d"][0]} m',
              abs(ex - q['w'][0]) < 1e-3 and abs(ex - q['d'][0]) > 0.1)

        rt = BY_ID[t['id']]['rot']
        swap = lambda c: dict(w=c['d'], d=c['w'])
        mirror = lambda c: dict(cs=c['cs'][2:4] + c['cs'][0:2] + c['cs'][4:])
        wide = lambda c: dict(w=[c['w'][0] + 0.01])
        defects = [                     # (box, what is wrong with it as built, the change to its call, the check that must catch it)
            (t, f'turned {rt} degrees, rotation of the wrong sign (sin negated)', lambda c: dict(sa=[-c['sa'][0]]), 'corner'),
            (t, f'turned {rt} degrees, built 10 degrees off', lambda c: angle_only(rt + 10), 'corner'),
            (t, f'turned {rt} degrees, width and length swapped', swap, 'corner'),
            (t, f'turned {rt} degrees, mirrored (two corners swapped)', mirror, 'corner'),
            (t, f'turned {rt} degrees, 1 cm too wide', wide, 'corner'),
            (q, 'turned 90 degrees, built unrotated (0 degrees): as built it is unrotated, so its extents are compared', lambda c: dict(ca=[1.0], sa=[0.0]), 'bounding box'),
            (q, 'turned 90 degrees, built 10 degrees off', lambda c: angle_only(100), 'corner'),
            (q, 'turned 90 degrees, width and length swapped', swap, 'corner'),
            (q, 'turned 90 degrees, mirrored (two corners swapped)', mirror, 'corner'),
            (z, 'unrotated, built turned by 90 degrees: as built it is turned, so only its corners can tell', lambda c: dict(ca=[0.0], sa=[1.0]), 'corner'),
            (z, 'unrotated, width and length swapped', swap, 'bounding box'),
            (z, 'unrotated, 1 cm too wide', wide, 'bounding box'),
            (z, 'unrotated, mirrored (two corners swapped): the same extents, so only a corner can tell', mirror, 'corner'),
        ]
        for c, what, change, want in defects:
            got = [build_one(c['id'], flags, **change(c)) for _, flags in READINGS]
            check(f'caught by {"a corner" if want == "corner" else "the bounding box"} (on {PX}_Check_Failed) under each of the {len(READINGS)} readings of a turned node\'s min / max: {c["id"]}, {what} ({got[0][0]!r})',
                  all(g[1] == f'{PX}_Check_Failed' and (g[0].startswith('corner ') if want == 'corner' else g[0] == 'bounding box') for g in got), str(got))
        for deg, why in ((0.01, 'rot is rounded to 0.01 degree, and that much is already turned'), (180.0, 'sin is 0 but cos is negative: turned')):
            got = [build_one(z['id'], flags, **turned_to(z, deg)) for _, flags in READINGS]
            check(f'{z["id"]} turned by {deg} degrees ({why}) is not compared with the node\'s min / max: it passes under each of the {len(READINGS)} readings ({got[0][0]!r})',
                  all(g == ('ok', g[1]) and g[1] != f'{PX}_Check_Failed' for g in got), str(got))
        got = build_one(z['id'], {'bbox_error': {'max': {'x': 0.01}}})
        check(f'{z["id"]} (rot 0) is compared with the node\'s min / max ({got[0]!r})', got[0] == 'bounding box' and got[1] == f'{PX}_Check_Failed')
        got = build_one(q['id'])
        check(f'{q["id"]} (rot 90) as the script builds it passes ({got[0]!r})', got[0] == 'ok')

        # the probe has teeth: slips put into the script's text (the rule of 28 Oct, a missing or loose rule) are found
        left = bbox_probe(TEXT)
        check('the real script passes the probe of the rule (the unrotated boxes are compared and only they; no box built right fails for what Max reports as min / max of a turned node)', left == [], '; '.join(left))
        rule = 'local unrotated = abs(sa) < 0.00001 and ca > 0.0'
        slips = [
            ('the rule of 28 Oct: a quarter turn counts as unrotated too, so the boxes turned by 90 degrees are compared', rule, 'local unrotated = abs(ca) < 0.00001 or abs(sa) < 0.00001'),
            ('every box is compared with the node\'s min / max', 'else if unrotated and (', 'else if ('),
            ('no box is compared with the node\'s min / max', 'else if unrotated and (', 'else if false and ('),
            ('the cosine is not looked at: a box turned by 180 degrees counts as unrotated', rule, 'local unrotated = abs(sa) < 0.00001'),
            ('a tolerance 100 times too loose: 0.01 degree counts as unrotated', rule, 'local unrotated = abs(sa) < 0.001 and ca > 0.0'),
            ('a box turned by up to 36 degrees counts as unrotated', rule, 'local unrotated = abs(sa) < 0.6 and ca > 0.0'),
        ]
        for label, old, new in slips:
            t2 = TEXT.replace(old, new, 1)
            check(f'slip found: {label}', t2 != TEXT and bool(bbox_probe(t2)), 'NOT noticed')
    except mk.MaxError as e:
        check('the mock Max ran the real script to the end', False, str(e)[:300])


def main():
    for section_test in (test_file, test_data, test_geometry, test_code, test_generator, test_lint_teeth, test_mock, test_none, test_bounding_box):
        try: section_test()
        except Exception as e:                # a damaged script must end in a FAIL line and exit 1, never in a traceback
            check(f'{section_test.__name__} could read what it needed from the script', False, f'{type(e).__name__}: {e}'[:300])
    failed = [n for n, ok in RESULTS if not ok]
    print(f'\n{len(RESULTS)} checks, {len(failed)} failed' + (f', {len(SKIPPED)} skipped' if SKIPPED else ''))
    for n in failed: print('  FAILED:', n)
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
