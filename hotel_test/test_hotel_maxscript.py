"""Checks of the REAL hotel 3ds Max script (hotel_test/Hotel_Lobby.ms) against the REAL model (hotel_test/src/hotel_model.json),
adapted from bank_test/test_bank_maxscript.py (the checks that apply here), with the parts, the stair lines, the room names, the
datum and a comparison with the bank's scripts added.  Plain python, no framework; prints PASS / FAIL per check and exits 1 if one
failed.  Run from anywhere:

    python -B hotel_test/test_hotel_maxscript.py

3ds Max is not installed on the machine that builds the script, so it is read back as text and everything that can be worked out from
the text and the model is worked out again here, from the model and the furniture README's formulas (not by calling the generator):
  1. the file: stamp = sha1 of hotel_model.json (and the viewer page's stamp, when the page is there), ASCII, line ends, brackets and
     quotes as MAXScript reads them, no placeholder left, every control of the window named once, no line longer than the script the
     3D team ran on 28 Oct, and (furniture/fixtures/maxscript_lite.py) the token lint, the argument counts and the names;
  2. the parts: one call per part of the model in its order, names unique, kind, floor, z0, z1 and follow the model's, a layer and a
     material per kind; every outline as Max gets it (its knots + its pivot) is the model's outline + the offset within 0.15 mm, valid,
     with 3 points or more per loop, no repeated point, the outer loop counter-clockwise and the holes clockwise, no hole within 0.5 mm
     of its outline or of another hole, and the pivot in the middle of its extents; the stair lines and the room names in place;
  3. the furniture data: one box call per piece in the model's order, every id once, names unique, a layer per floor and kind, a
     material and a height spinner per kind;
  4. every box: the four world corners of its base from the call's matrix3 numbers and its size = the README's corners from the model
     (x, y, w, d, rot + the offset) within 0.5 mm, and so are the corners the script carries for its own check; base z and top z;
  5. the code: "Furniture boxes only", "Apply furniture heights" and "Update levels and heights" are there, and no box is ever
     collapsed or converted (the owner's rule: live objects, never an Editable Poly);
  6. the generator: the script on disk is what it writes today; for a model without furniture it writes the script without any
     furniture line (and the real one differs from it only by inserted lines); it refuses outlines Extrude could not cap; and against
     the bank's scripts: once the prefix and the data are set aside, the code is the bank's, the structure part as the 3D team ran it
     on 28 Oct and the furniture part as written on 29 Oct, except a listed handful of lines (the header, the datum's Source and
     Picture properties, the tooltip of the placement tick box);
  7. the generated functions are RUN by the small MAXScript interpreter of the fixtures over a mock scene: Build (and the number of
     objects it announces), Apply, Update levels, Furniture boxes only, the datum with the pictures' placement, on the real script and
     the real model.
Slips put into the data and the text on purpose must be found, so that a clean run means something.

What this cannot show: that 3ds Max itself agrees. The mock knows only what is written in furniture/fixtures/maxscript_mock.py, the
lint only reads tokens, and the part builder (splines, Extrude, its own checks in Max) is not run here at all: it is the bank's code,
line for line (section 6), and what it is given is checked in section 2. The 3D team's run is the proof.
"""
import copy, difflib, hashlib, json, math, os, re, shutil, struct, subprocess, sys, tempfile, unicodedata
from pathlib import Path
from shapely.geometry import Polygon, LinearRing
from shapely.validation import explain_validity

sys.dont_write_bytecode = True
HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
sys.path.insert(0, str(ROOT / 'furniture' / 'fixtures'))
try:
    import maxscript_lite as ms                    # the token lint and the mock Max that furniture/test_furniture_max.py already uses
    import maxscript_mock as mk
except ImportError:
    ms = mk = None

SCRIPT = HERE / 'Hotel_Lobby.ms'
MODEL = HERE / 'src' / 'hotel_model.json'
GENERATOR = HERE / 'src' / 'generate_maxscript.py'
MODULE = ROOT / 'furniture' / 'furniture_max.py'
PAGE = HERE / 'hotel_3d_preview.html'              # the viewer page (another agent's); its stamp is compared when it is there
BANK_NOW = ROOT / 'bank_test' / 'Bangkok_Bank_Sampeng.ms'                                      # 29 Oct, with furniture (checked as text)
BANK_RUN = ROOT / 'bank_test' / 'previous_before_furniture_2026-10-28' / 'Bangkok_Bank_Sampeng.ms'   # 28 Oct, run in 3ds Max
BANK_RUN_SHA = '1a48f78342c369656609b2c9f81e1aa20bfe3fd5'
TOL = 5e-4                                         # corners: 0.5 mm
OUTLINE_TOL = 1.5e-4                               # a part's knot + its pivot, both written to 0.1 mm, against the model + offset

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
PX = M.get('maxPrefix', 'HL')
OX, OY = M['offset']
FLOORS = [f['key'] for f in M['floors']]
LEVEL = {f['key']: f['level'] for f in M['floors']}
KINDS = M.get('furnitureKinds') or []
KIND = {k['key']: k for k in KINDS}
PIECES = M.get('furniture') or []
BY_ID = {p['id']: p for p in PIECES}
PARTS = M['parts']
# the bank's table of part kinds: layer suffix and material (bank_test/src/generate_maxscript.py, KINDS)
PART_KINDS = {'wall': ('Walls', 'Wall'), 'column': ('Columns', 'Wall'), 'lintel': ('Lintels', 'Wall'), 'sill': ('Sills', 'Wall'),
              'parapet': ('Parapets', 'Wall'), 'glass': ('Glass', 'Glass'), 'mullion': ('GlassFrames', 'Frame'),
              'railing': ('Railings', 'Rail'), 'single': ('SingleLines', 'Single'), 'step': ('Steps', 'Step'), 'slab': ('Slab', 'Slab')}


# ---- the README's formulas, written out again here ----------------------------------------------------------------------------

def camel(key): return ''.join(w.capitalize() for w in key.split('-'))           # coffee-table -> CoffeeTable


def ascii_fold(s):
    """The rule for text in the Max script: plain ASCII (Thai and other letters drop out), no double quote or backslash, spaces collapsed."""
    s = s.replace(chr(0xb2), '2').replace(chr(0xb7), '-').replace(chr(0x110), 'D').replace(chr(0x111), 'd')       # superscript 2, middle dot, D and d with a stroke
    s = unicodedata.normalize('NFKD', s).encode('ascii', 'ignore').decode()
    return ' '.join(re.sub(r'[\x00-\x1f\x7f]', ' ', s).replace('"', "'").replace('\\', '/').split())


def none_text(s): return ascii_fold(s or '') or 'none'                         # a user property's text: ASCII, and the word none for nothing
def half_up(v): return int(math.floor(v + 0.5))                                  # whole mm, a half rounds up (Python's round() goes to even)
def is_unrotated(rot): return abs(math.sin(math.radians(rot))) < 1e-5 and math.cos(math.radians(rot)) > 0     # rot 0: the boxes whose node min / max are compared
def signed(loop): return sum(a[0] * b[1] - b[0] * a[1] for a, b in zip(loop, loop[1:] + loop[:1])) / 2     # > 0: counter-clockwise (plan, y up)


def caption_of(k):
    """A spinner's caption by the rule: the label when it has at most 16 characters, else the key in words, then a colon."""
    s = ascii_fold(k['label']).replace('&', 'and')
    return (s if 0 < len(s) <= 16 else k['key'].replace('-', ' ').capitalize()[:16]) + ':'


def readme_corners(p, shift=(0.0, 0.0)):
    """x, y = the centre, w >= d the sizes along its own long and short axis, rot = degrees counter-clockwise from +x (plan, y up);
    the drawing's own coordinates are the model's plus the offset; the corners run counter-clockwise from (-w/2, -d/2)."""
    a = math.radians(p['rot'])
    c, s = math.cos(a), math.sin(a)
    cx, cy = p['x'] + OX - shift[0], p['y'] + OY - shift[1]
    return [(cx + c * u - s * v, cy + s * u + c * v) for u, v in ((-p['w'] / 2, -p['d'] / 2), (p['w'] / 2, -p['d'] / 2), (p['w'] / 2, p['d'] / 2), (-p['w'] / 2, p['d'] / 2))]


def readme_z0(p, mm=None):
    """Metres above the level of its floor: the top of its support (that kind's base + height) or its own kind's base."""
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
def unquote(x): return x[1:-1] if len(x) >= 2 and x[0] == x[-1] == '"' else None


def loops_of(s):
    """#(#([x,y],...),#(...)) -> [[(x, y), ...], ...] (the numbers as written), or None when the text is not that shape."""
    if not (s.startswith('#(') and s.endswith(')')): return None
    out = []
    for m in re.finditer(r'#\(([^#]*)\)', s[2:-1]):
        pts = [floats(p) for p in re.findall(r'\[[^\]]*\]', m.group(1))]
        if any(len(p) != 2 for p in pts): return None
        out.append([tuple(p) for p in pts])
    return out or None


def parse_call(s):
    """One furnBox call: 16 arguments (kind name floor-index id support-id support-kind centre w d cos sin corners family block layer handle)."""
    try: a = split_args(s)
    except (ValueError, IndexError): a = []                  # an unclosed quote or bracket: not a call that can be read
    c = {'raw': s, 'n': len(a), 'ok': False}
    if len(a) != 16: return c
    c.update(kind=unquote(a[0]), name=unquote(a[1]), fi=int(a[2]) if a[2].isdigit() else None, id=unquote(a[3]), supId=unquote(a[4]), supKind=unquote(a[5]),
             c=floats(a[6]), w=floats(a[7]), d=floats(a[8]), ca=floats(a[9]), sa=floats(a[10]), cs=floats(a[11]),
             fam=unquote(a[12]), blk=unquote(a[13]), lay=unquote(a[14]), hnd=unquote(a[15]))
    texts = (c['kind'], c['name'], c['id'], c['supId'], c['supKind'], c['fam'], c['blk'], c['lay'], c['hnd'])
    c['ok'] = (all(t is not None for t in texts) and c['fi'] is not None and len(c['c']) == 2 and len(c['w']) == len(c['d']) == 1
               and len(c['ca']) == len(c['sa']) == 1 and len(c['cs']) == 8)
    return c


def parse_part(s):
    """One part call: 10 arguments (#kind name loops z0 z1 follow floor-index pivot extents-min extents-max)."""
    try: a = split_args(s)
    except (ValueError, IndexError): a = []
    c = {'raw': s, 'n': len(a), 'ok': False}
    if len(a) != 10: return c
    z0, z1 = floats(a[3]), floats(a[4])
    c.update(kind=a[0][1:] if re.fullmatch(r'#[a-z]+', a[0]) else None, name=unquote(a[1]), loops=loops_of(a[2]),
             follow={'true': True, 'false': False}.get(a[5]), fi=int(a[6]) if a[6].isdigit() else None, c=floats(a[7]), mn=floats(a[8]), mx=floats(a[9]))
    c['ok'] = (c['kind'] is not None and c['name'] is not None and c['loops'] is not None and len(z0) == len(z1) == 1 and c['follow'] is not None
               and c['fi'] is not None and len(c['c']) == len(c['mn']) == len(c['mx']) == 2)
    if c['ok']: c['z0'], c['z1'] = z0[0], z1[0]
    return c


def parse_lines(s):
    """One stair-lines call: name, segments #(#([x,y],[x,y]),...), floor index, pivot, layer kind."""
    try: a = split_args(s)
    except (ValueError, IndexError): a = []
    c = {'raw': s, 'ok': False}
    if len(a) != 5: return c
    c.update(name=unquote(a[0]), segs=loops_of(a[1]), fi=int(a[2]) if a[2].isdigit() else None, c=floats(a[3]), lay=unquote(a[4]))
    c['ok'] = c['name'] is not None and c['segs'] is not None and c['fi'] is not None and len(c['c']) == 2 and c['lay'] is not None
    return c


def parse_room(s):
    try: a = split_args(s)
    except (ValueError, IndexError): a = []
    c = {'raw': s, 'ok': False}
    if len(a) != 3: return c
    c.update(text=unquote(a[0]), p=floats(a[1]), fi=int(a[2]) if a[2].isdigit() else None)
    c['ok'] = c['text'] is not None and len(c['p']) == 2 and c['fi'] is not None
    return c


def global_array(name):
    m = re.search(rf'^global {PX}_furn{name} = (#\(.*\))$', TEXT, re.M)
    return m.group(1) if m else ''


def fn_text(name, text=None):
    m = re.search(rf'^fn {name}\b.*?(?=^fn |^try \(|\Z)', text or TEXT, re.M | re.S)
    return m.group(0) if m else ''


def code(s): return re.sub(r'^\s*--.*$', '', s, flags=re.M)                   # without the full-line comments
def outside_strings(s): return re.sub(r'--[^\n]*', '', re.sub(r'"(?:[^"\\\n]|\\.)*"', '""', s))       # what MAXScript parses as code


CALLS = [parse_call(m.group(1)) for m in re.finditer(rf'^    {PX}_furnBox (.*)$', TEXT, re.M)]
PART_CALLS = [parse_part(m.group(1)) for m in re.finditer(rf'^    {PX}_part (.*)$', TEXT, re.M)]
LINE_CALLS = [parse_lines(m.group(1)) for m in re.finditer(rf'^    {PX}_lines (.*)$', TEXT, re.M)]
ROOM_CALLS = [parse_room(m.group(1)) for m in re.finditer(rf'^    {PX}_room (.*)$', TEXT, re.M)]
KEYS, LAYERS, FLOORS_S = (quoted(global_array(n)) for n in ('Keys', 'Layers', 'Floors'))
BASES, HEIGHTS = (floats(global_array(n)) for n in ('Bases', 'Heights'))
LEVELS_S = floats((re.search(rf'^global {PX}_levels = (#\(.*\))$', TEXT, re.M) or (None, ''))[1])         # the script's own floor levels (metres)
WALLS_S = floats((re.search(rf'^global {PX}_heights = (#\(.*\))$', TEXT, re.M) or (None, ''))[1])         # ... and wall heights
NAMES_S = quoted((re.search(rf'^global {PX}_floorNames = (#\(.*\))$', TEXT, re.M) or (None, ''))[1])
SPINNER_LINE = re.compile(r'^        spinner (fh\d+) "([^"]*)"( across:2)? range:\[(\d+), (\d+), (\d+)\] type:#integer fieldwidth:40$', re.M)
SPINNERS = SPINNER_LINE.findall(TEXT)
MATERIALS = re.findall(rf'^    append {PX}_furnMats \(standardMaterial name:"{PX} Furn ([^"]*)" diffuse:\(color (\d+) (\d+) (\d+)\)\)$', TEXT, re.M)
STAIR_KINDS = (('below', 'Stairs'), ('above', 'StairsAbove'))


def stair_shapes():
    """The stair-line shapes the model asks for: (floor, layer kind, its flat list of x1 y1 x2 y2 ...), in the generator's order."""
    return [(fl, lay, st[k]) for fl, st in M.get('stairs', {}).items() for k, lay in STAIR_KINDS if st.get(k)]


def announced():
    """The number of objects Build makes and announces (its node list): parts, stair shapes, room names, furniture boxes."""
    return len(PARTS) + len(stair_shapes()) + len(M['rooms']) + len(PIECES)


# ---- 1. the file ------------------------------------------------------------------------------------------------------------------

def test_file():
    section(f'the file ({len(RAW) // 1024} KB, {len(LINES) - 1} lines)')
    check('the model has parts, rooms and furniture, and the script has their calls', len(PARTS) > 0 and len(PART_CALLS) > 0 and len(ROOM_CALLS) > 0 and len(PIECES) > 0 and len(CALLS) > 0,
          f'{len(PARTS)} parts, {len(PIECES)} pieces, {len(PART_CALLS)} part calls, {len(CALLS)} box calls')
    check('ASCII only (3ds Max reads the script as plain text)', all(b < 128 for b in RAW), str([i for i, b in enumerate(RAW) if b > 127][:3]))
    crlf = RAW.count(b'\r\n')
    lf, cr = RAW.count(b'\n') - crlf, RAW.count(b'\r') - crlf
    check('line ends are all CRLF or all LF', cr == 0 and (crlf == 0 or lf == 0), f'{crlf} CRLF, {lf} bare LF, {cr} bare CR')
    check('no tab and no control character other than the line ends', not re.search(rb'[\x00-\x09\x0b\x0c\x0e-\x1f\x7f]', RAW))
    stamp = re.search(rf'^-- Same model as {re.escape(PAGE.name)} \(model data ([0-9a-f]{{12}})\)', TEXT, re.M)
    sha = hashlib.sha1(MODEL_RAW).hexdigest()[:12]
    check(f'the stamp in line 2 is the sha1 of hotel_model.json ({sha}) and names the viewer page {PAGE.name}', bool(stamp) and stamp.group(1) == sha and LINES[1].startswith('-- Same model as'), f'script says {stamp and stamp.group(1)}')
    first = re.search(r'model data ([0-9a-f]+)', TEXT)
    check('... and it is the first "model data" in the file (the page test reads the first one)', bool(first) and first.group(1) == sha)
    if PAGE.exists():
        meta = re.search(r'<meta name="model-data" content="([0-9a-f]+)">', PAGE.read_text(encoding='utf-8', errors='replace'))
        check(f'the viewer page beside the script carries the same model-data stamp ({meta and meta.group(1)})', bool(meta) and meta.group(1) == sha)
    else: skip(f'the viewer page carries the same stamp', f'{PAGE.name} is not there yet (another agent writes it)')
    left = sorted(set(re.findall(r'__[A-Z]+(?:_[A-Z]+)*__', TEXT)))
    check('no placeholder is left (no __NAME__ and no __FURN_NAME__)', not left, str(left[:4]))
    cd = outside_strings(TEXT)
    check('( ) and [ ] are balanced as MAXScript reads them (outside strings and comments), and the quote count is even',
          cd.count('(') == cd.count(')') and cd.count('[') == cd.count(']') and TEXT.count('"') % 2 == 0, f"( {cd.count('(')} ) {cd.count(')')} [ {cd.count('[')} ] {cd.count(']')}")
    half = [c['name'] for c in CALLS if c['ok'] and c['name'].count('(') != c['name'].count(')')]
    info(f'{len(half)} object names hold half a bracket, which is text inside a string (a family cut at 40 characters): {", ".join(half)}')
    names = re.findall(r'^\s+(?:checkbox|spinner|button|label|radiobuttons|dropdownlist|edittext|listbox|slider) (\w+)', TEXT[max(TEXT.find(f'rollout {PX}_UI'), 0):], re.M)
    dup = sorted({n for n in names if names.count(n) > 1})
    check(f'every control of the window has a name of its own ({len(names)} controls: the bank\'s, two spinners per floor, the 3 furniture ones and one spinner per kind)', not dup and {'fb', 'fo', 'fap', 'dwg', 'cm', 'build', 'upd', 'col'} <= set(names), str(dup))
    if BANK_RUN.exists():
        run_lines = BANK_RUN.read_bytes().decode('latin-1').replace('\r\n', '\n').split('\n')
        longest, run_longest = max(len(l) for l in LINES), max(len(l) for l in run_lines)
        knots = max(sum(len(l) for l in c['loops']) for c in PART_CALLS if c['ok'])
        run_knots = max(l.count('[') - 3 for l in run_lines if l.startswith('    BB_part '))
        check(f'no line is longer than the longest line of the script the 3D team ran on 28 Oct ({longest} vs {run_longest} characters), and no part has more knots ({knots} vs {run_knots})',
              longest <= run_longest and knots <= run_knots)
        loops, run_loops = max(len(c['loops']) for c in PART_CALLS if c['ok']), max(l.count('#(') - 1 for l in run_lines if l.startswith('    BB_part '))
        info(f'the most loops in one part: {loops} ({", ".join(c["name"] for c in PART_CALLS if c["ok"] and len(c["loops"]) == loops)}: an outline and {loops - 1} holes); '
             f'the 28 Oct script had at most {run_loops} (an outline and {run_loops - 1} holes): NEW in the data, see the report')
    else: skip('no line longer than in the script the 3D team ran', f'{BANK_RUN} not found')
    if ms is None: skip('token lint, argument counts, names', 'furniture/fixtures/maxscript_lite.py not found'); return
    toks, terr = ms.tokenize(TEXT)
    check('every quote closes on its line and every character is readable', terr == [], str(terr[:3]))
    _, _, serr = ms.structure(toks)
    check('brackets and parentheses are balanced and nested right (strings left out)', serr == [], str(serr[:3]))
    lerr = ms.lint(TEXT)
    check('token lint: if/then/else, for/do, case/of, fn, try/catch, local/global', lerr == [], str(lerr[:5]))
    aerr = ms.arity_errors(TEXT)
    check(f'every statement that calls one of the script\'s functions gives it as many arguments as it has parameters ({len(PART_CALLS)} part, {len(LINE_CALLS)} stair, {len(ROOM_CALLS)} room and {len(CALLS)} box calls included)', aerr == [], str(aerr[:5]))
    known = {'box', 'matrix3', 'finditem', 'floor', 'matchpattern'}                # Max built-ins that the structure script did not use
    ref = reference()
    base_unres = {w.lower() for w in ms.unresolved(ref[0])} if ref else None
    unres = {w.lower() for w in ms.unresolved(TEXT)}
    if base_unres is None: skip('no word the structure script does not use, except the reviewed ones', 'the generator run of the regression section failed')
    else: check(f'every name the script does not declare is a Max word the structure script already used, or one reviewed for the furniture ({", ".join(sorted(unres - base_unres))})', unres - base_unres <= known, str(sorted(unres - base_unres - known)))


# ---- 2. the parts, the stair lines and the room names ------------------------------------------------------------------------------

def part_problems(calls):
    """Every part call against the model: kind, name, floor, z0, z1, follow; the outline as Max gets it (knot + pivot) against the model's
    outline + offset; and what Extrude needs to cap it: valid, 3 points or more, no repeated point, outer counter-clockwise and holes
    clockwise, no hole within 0.5 mm of its outline or of another hole, extents and pivot. Returns (problems, worst outline error in m)."""
    bad, worst, count = [], 0.0, {}
    if len(calls) != len(PARTS): bad.append(f'{len(calls)} part calls for {len(PARTS)} parts')
    for c, p in zip(calls, PARTS):
        key = (p['floor'], p['kind'])
        count[key] = count.get(key, 0) + 1
        want_name = f"{PX}_{p['floor']}_{p['kind'].capitalize()}_{count[key]:03}" + (f"_{ascii_fold(p['label'])}" if p.get('label') else '')
        tag = c.get('name') or c['raw'][:40]
        if not c['ok']: bad.append(f'{tag}: not 10 well-formed arguments'); continue
        if c['name'] != want_name: bad.append(f'{tag}: name, wanted {want_name!r}')
        if c['kind'] != p['kind']: bad.append(f'{tag}: kind {c["kind"]} != {p["kind"]}')
        if c['fi'] != FLOORS.index(p['floor']) + 1: bad.append(f'{tag}: floor index {c["fi"]} != {FLOORS.index(p["floor"]) + 1}')
        if abs(c['z0'] - p['z0']) > 5e-5 or abs(c['z1'] - p['z1']) > 5e-5: bad.append(f'{tag}: z0 / z1 {c["z0"]} {c["z1"]} != {p["z0"]} {p["z1"]}')
        if c['follow'] != bool(p.get('follow')): bad.append(f'{tag}: follow {c["follow"]} != {bool(p.get("follow"))}')
        cx, cy = c['c']
        world = [[(x + cx, y + cy) for x, y in loop] for loop in c['loops']]
        want = [[(x + OX, y + OY) for x, y in ring] for ring in [p['o']] + p['h']]
        if len(world) != len(want): bad.append(f'{tag}: {len(world)} loops != {len(want)} (the outline and its holes)')
        for j, w in enumerate(world):
            if len(w) < 3: bad.append(f'{tag}: a loop of fewer than 3 points'); continue
            if any(math.dist(a, b) < 1e-4 for a, b in zip(w, w[1:] + w[:1])): bad.append(f'{tag}: repeated point in loop {j + 1}')
            if j == 0 and not signed(w) > 0: bad.append(f'{tag}: the outer loop is not counter-clockwise')
            if j > 0 and not signed(w) < 0: bad.append(f'{tag}: hole {j} is not clockwise')
            if j < len(want):
                m = want[j] if (signed(want[j]) > 0) == (j == 0) else want[j][::-1]          # the generator turns each loop the way Extrude wants it
                if len(m) != len(w): bad.append(f'{tag}: loop {j + 1} has {len(w)} points, the model {len(m)}'); continue
                d = max(math.dist(a, b) for a, b in zip(w, m))
                worst = max(worst, d)
                if d > OUTLINE_TOL: bad.append(f'{tag}: loop {j + 1} differs from the model\'s outline + offset by {d * 1000:.2f} mm')
        if not world or any(len(w) < 3 for w in world): continue
        poly = Polygon(world[0], world[1:])
        if not poly.is_valid: bad.append(f'{tag}: outline not valid ({explain_validity(poly)})')
        outer_ring, outer_poly = LinearRing(world[0]), Polygon(world[0])
        for j, h in enumerate(world[1:]):
            if LinearRing(h).distance(outer_ring) < 5e-4: bad.append(f'{tag}: hole {j + 1} touches its outline (within 0.5 mm)')
            if outer_poly.is_valid and not outer_poly.contains(Polygon(h)): bad.append(f'{tag}: hole {j + 1} lies outside its outline')
            for k in range(j + 1, len(world) - 1):
                if LinearRing(h).distance(LinearRing(world[k + 1])) < 5e-4: bad.append(f'{tag}: holes {j + 1} and {k + 1} touch (within 0.5 mm)')
        xs, ys = [x for x, _ in world[0]], [y for _, y in world[0]]
        if max(abs(min(xs) - c['mn'][0]), abs(min(ys) - c['mn'][1]), abs(max(xs) - c['mx'][0]), abs(max(ys) - c['mx'][1])) > OUTLINE_TOL: bad.append(f'{tag}: the extents mn / mx are not the outline\'s')
        if abs(cx - (c['mn'][0] + c['mx'][0]) / 2) > 1e-4 or abs(cy - (c['mn'][1] + c['mx'][1]) / 2) > 1e-4: bad.append(f'{tag}: the pivot is not the middle of the extents')
    return bad, worst


def test_parts():
    section(f'the parts: {len(PARTS)} in the model, {len(PART_CALLS)} calls; stair lines and room names')
    check(f'every part call has 10 well-formed arguments, numbers written with 4 decimals and negative ones in brackets',
          all(c['ok'] for c in PART_CALLS) and all(not re.search(r'(?<![(\w.])-\d', re.sub(r'"[^"]*"', '', c['raw'])) and 'e-' not in re.sub(r'"[^"]*"', '', c['raw'])
                                                   and not re.search(r'(?<![\w.])\d+(?![\d.])(?=[,\])])', re.sub(r'"[^"]*"', '', c['raw'])) for c in PART_CALLS),
          str([c['raw'][:60] for c in PART_CALLS if not c['ok']][:2]))
    bad, worst = part_problems(PART_CALLS)
    n_loops = sum(len(c['loops']) for c in PART_CALLS if c['ok'])
    n_knots = sum(len(l) for c in PART_CALLS if c['ok'] for l in c['loops'])
    check(f'all {len(PARTS)} parts, {n_loops} loops, {n_knots} knots: in the model\'s order, kind, name, floor, z0, z1 and follow the model\'s; the outline as Max gets it (knots + pivot) is the model\'s + the offset (worst {worst * 1000:.3f} mm, limit {OUTLINE_TOL * 1000:.2f} mm); '
          'valid, 3 points or more per loop, no repeated point, outer loop counter-clockwise, holes clockwise and inside it, no hole within 0.5 mm of its outline or of another hole, the pivot in the middle of the extents',
          not bad and len(PART_CALLS) == len(PARTS), '; '.join(bad[:4]))
    names = [c['name'] for c in PART_CALLS if c['ok']]
    check('part names are unique (to the letter case)', len({n.lower() for n in names}) == len(names))
    by = {}
    for p in PARTS: by[(p['floor'], p['kind'])] = by.get((p['floor'], p['kind']), 0) + 1
    got = {}
    for c in PART_CALLS:
        if c['ok']: got[(FLOORS[c['fi'] - 1], c['kind'])] = got.get((FLOORS[c['fi'] - 1], c['kind']), 0) + 1
    check(f'the parts per floor and kind are the model\'s ({", ".join(f"{fl} {k} {n}" for (fl, k), n in by.items())})', got == by)
    case = {k: (s, m) for k, s, m in re.findall(r'^        #(\w+): #\("(\w+)", "(\w+)"\)$', fn_text(f'{PX}_part'), re.M)}
    mats = re.findall(rf'^    append {PX}_mats \(standardMaterial name:"{PX} (\w+)"', TEXT, re.M)
    kinds = sorted({p['kind'] for p in PARTS})
    check(f'every kind of part has the bank\'s layer and material (case kind of: {", ".join(f"{k} -> {case.get(k, ("?",))[0]}" for k in kinds)}), and every material is made',
          all(case.get(k) == PART_KINDS[k] for k in kinds) and case == PART_KINDS and all(PART_KINDS[k][1] in mats for k in kinds), str(case))
    layers = sorted({f'{PX}_{NAMES_S[c["fi"] - 1]}_{case[c["kind"]][0]}' for c in PART_CALLS if c['ok'] and c['kind'] in case})
    check(f'the floor names the layers are made from are the floor keys ({", ".join(NAMES_S)}): the parts land on {len(layers)} layers ({", ".join(layers)})', NAMES_S == FLOORS)
    check('the script\'s floor levels and wall heights are the model\'s (the window\'s spinners start at them)',
          len(LEVELS_S) == len(WALLS_S) == len(FLOORS) and all(abs(a - f['level']) < 1e-9 and abs(b - f['wallHeight']) < 1e-9 for a, b, f in zip(LEVELS_S, WALLS_S, M['floors']))
          and all(f'spinner lv{i + 1} "{f["name"]} floor level (m):" range:[-50, 500, {f["level"]:.2f}]' in TEXT and f'spinner ht{i + 1} "{f["name"]} wall height (m):" range:[2.2, 15, {f["wallHeight"]:.2f}]' in TEXT for i, f in enumerate(M['floors'])))
    follow = sorted({p['kind'] for p in PARTS if p.get('follow')})
    keep = sorted({p['kind'] for p in PARTS if not p.get('follow')})
    info(f'"Update levels and heights" sets the top of {sum(1 for p in PARTS if p.get("follow"))} parts ({", ".join(follow)}) to the wall height and keeps {sum(1 for p in PARTS if not p.get("follow"))} ({", ".join(keep)})')
    # slips in the data must be found, each for its own reason
    walls = [c for c in PART_CALLS if c['ok'] and c['kind'] == 'wall']
    holed = next(c for c in PART_CALLS if c['ok'] and len(c['loops']) > 2)                       # the slab of floor 2
    lintel = next(c for c in PART_CALLS if c['ok'] and c['kind'] == 'lintel' and len(c['loops'][0]) == 4)
    rail = next((c for c in PART_CALLS if c['ok'] and c['kind'] == 'railing'), lintel)
    idx = {c['name']: i for i, c in enumerate(PART_CALLS)}

    def on(name, f):
        def g(cs):
            f(cs[idx[name]])
        return g
    slips = [
        ('a hole moved onto its outline', on(holed['name'], lambda c: c['loops'][1].__setitem__(0, c['loops'][0][0])), 'touches its outline'),
        ('two holes that touch', on(holed['name'], lambda c: c['loops'][2].__setitem__(0, c['loops'][1][0])), 'touch (within'),
        ('a repeated point', on(walls[0]['name'], lambda c: c['loops'][0].insert(1, c['loops'][0][0])), 'repeated point'),
        ('the outer loop turned clockwise', on(walls[0]['name'], lambda c: c['loops'].__setitem__(0, c['loops'][0][::-1])), 'not counter-clockwise'),
        ('a hole turned counter-clockwise', on(holed['name'], lambda c: c['loops'].__setitem__(1, c['loops'][1][::-1])), 'is not clockwise'),
        ('two points swapped (a bow tie)', on(lintel['name'], lambda c: c['loops'][0].__setitem__(slice(1, 3), [c['loops'][0][2], c['loops'][0][1]])), 'not valid'),
        ('a knot moved by 1 mm', on(walls[0]['name'], lambda c: c['loops'][0].__setitem__(1, (c['loops'][0][1][0] + 0.001, c['loops'][0][1][1]))), 'differs from the model'),
        ('the pivot moved by 1 mm', on(walls[1]['name'], lambda c: c['c'].__setitem__(0, c['c'][0] + 0.001)), 'middle of the extents'),
        ('the extents moved by 1 mm', on(walls[1]['name'], lambda c: c['mx'].__setitem__(1, c['mx'][1] + 0.001)), 'extents mn / mx'),
        ('a loop of 2 points', on(lintel['name'], lambda c: c['loops'].__setitem__(0, c['loops'][0][:2])), 'fewer than 3 points'),
        ('a lintel 1 cm higher', on(lintel['name'], lambda c: c.__setitem__('z1', c['z1'] + 0.01)), 'z0 / z1'),
        ('a railing set to follow the wall height', on(rail['name'], lambda c: c.__setitem__('follow', not c['follow'])), 'follow'),
        ('the wrong floor index', on(lintel['name'], lambda c: c.__setitem__('fi', 3 - c['fi'])), 'floor index'),
        ('a part of another kind', on(lintel['name'], lambda c: c.__setitem__('kind', 'wall')), 'kind'),
        ('a part left out', lambda cs: cs.pop(5), 'part calls for'),
    ]
    for label, f, why in slips:
        cs = copy.deepcopy(PART_CALLS)
        f(cs)
        got = part_problems(cs)[0]
        check(f'slip found: {label} ({why!r})', any(why in g for g in got), 'NOT noticed' + (f': {got[:2]}' if got else ''))
    # stair lines
    shapes = stair_shapes()
    ok, why = len(LINE_CALLS) == len(shapes), f'{len(LINE_CALLS)} calls for {len(shapes)} shapes'
    worst = 0.0
    for c, (fl, lay, a) in zip(LINE_CALLS, shapes):
        if not c['ok'] or c['name'] != f'{PX}_{fl}_{lay}' or c['lay'] != lay or c['fi'] != FLOORS.index(fl) + 1: ok, why = False, f'{c.get("name")}: name, layer kind or floor'; continue
        segs = [((a[i] + OX, a[i + 1] + OY), (a[i + 2] + OX, a[i + 3] + OY)) for i in range(0, len(a), 4)]
        got = [[(x + c['c'][0], y + c['c'][1]) for x, y in s] for s in c['segs']]
        if len(got) != len(segs) or any(len(s) != 2 for s in got): ok, why = False, f'{c["name"]}: {len(got)} segments for {len(segs)}'; continue
        d = max(math.dist(p, q) for s, t in zip(got, segs) for p, q in zip(s, t))
        worst = max(worst, d)
        xs, ys = [p[0] for s in got for p in s], [p[1] for s in got for p in s]
        if d > OUTLINE_TOL or abs(c['c'][0] - (min(xs) + max(xs)) / 2) > 1e-4 or abs(c['c'][1] - (min(ys) + max(ys)) / 2) > 1e-4: ok, why = False, f'{c["name"]}: off by {d * 1000:.2f} mm or pivot'
        if any(math.dist(*s) < 1e-4 for s in got): ok, why = False, f'{c["name"]}: a segment of no length'
    n_segs = sum(len(a) // 4 for _, _, a in shapes)
    check(f'stair lines: one shape per floor and kind that has lines ({", ".join(f"{PX}_{fl}_{lay}" for fl, lay, _ in shapes)}, {n_segs} segments), each segment + the pivot = the model\'s + the offset (worst {worst * 1000:.3f} mm), the pivot in the middle', ok, why)
    # room names
    bad = room_problems(ROOM_CALLS)
    check(f'room names: one text per room of the model ({len(M["rooms"])}), its words in ASCII, its floor, at the model\'s place + the offset (within 0.1 mm); object names unique', not bad, '; '.join(bad[:3]))
    for label, f, why in (('a room name moved by 1 mm', lambda cs: cs[0]['p'].__setitem__(0, cs[0]['p'][0] + 0.001), 'place'),
                          ('a room name on the other floor', lambda cs: cs[-1].__setitem__('fi', 3 - cs[-1]['fi']), 'floor'),
                          ('a room name left out', lambda cs: cs.pop(3), 'calls for'),
                          ('two rooms of a floor with the same name', lambda cs: cs[1].__setitem__('text', cs[0]['text']), 'twice')):
        cs = copy.deepcopy(ROOM_CALLS)
        f(cs)
        got = room_problems(cs)
        check(f'slip found: {label} ({why!r})', any(why in g for g in got), 'NOT noticed')


def room_problems(calls):
    """Every room-name call against the model's rooms: its text (ASCII), floor and place; object names (Room_<floor>_<text>) unique."""
    bad = [] if len(calls) == len(M['rooms']) else [f'{len(calls)} room calls for {len(M["rooms"])} rooms']
    for c, r in zip(calls, M['rooms']):
        if not c['ok']: bad.append(f'{c["raw"][:40]}: not 3 well-formed arguments'); continue
        if c['text'] != ascii_fold(r['label']): bad.append(f'{c["text"]}: text, wanted {ascii_fold(r["label"])!r}')
        if c['fi'] != FLOORS.index(r['floor']) + 1: bad.append(f'{c["text"]}: floor index {c["fi"]}')
        if math.dist(c['p'], (r['x'] + OX, r['y'] + OY)) > 1e-4: bad.append(f'{c["text"]}: place off by {math.dist(c["p"], (r["x"] + OX, r["y"] + OY)) * 1000:.1f} mm')
    objs = [f'{PX}_Room_{FLOORS[c["fi"] - 1]}_{c["text"]}'.lower() for c in calls if c['ok'] and 1 <= c['fi'] <= len(FLOORS)]
    bad += [f'{o}: object name twice' for o in sorted({o for o in objs if objs.count(o) > 1})]
    return bad


# ---- 3. the furniture data ------------------------------------------------------------------------------------------------------

def test_data():
    section(f'the furniture data: {len(PIECES)} pieces, {len(KINDS)} kinds, {len(FLOORS)} floors')
    check('every furnBox call has 16 well-formed arguments', all(c['ok'] for c in CALLS), str([c['raw'][:60] for c in CALLS if not c['ok']][:2]))
    check(f'one box call per piece ({len(CALLS)} calls for {len(PIECES)} pieces)', len(CALLS) == len(PIECES))
    ids = [c.get('id') for c in CALLS]
    check('every id exactly once, in the model\'s order', ids == [p['id'] for p in PIECES] and len(set(ids)) == len(ids))
    names = [c.get('name') for c in CALLS]
    check('object names are unique (to the letter case), also against the parts\' names', len({str(n).lower() for n in names} | {c['name'].lower() for c in PART_CALLS if c['ok']}) == len(names) + sum(1 for c in PART_CALLS if c['ok']))
    ok, why = True, ''
    for c in CALLS:
        p = BY_ID.get(c.get('id'))
        if not p or not c['ok']: ok = False; continue
        fam = ascii_fold(p['family'])[:40].rstrip(' _-')
        want = f"{PX}_{p['floor']}_Furn_{p['kind']}_{p['id'].rsplit('-', 1)[1]}" + (f'_{fam}' if fam else '')
        if c['name'] != want: ok, why = False, why or f"{c['id']}: {c['name']!r} != {want!r}"
    check(f'name = {PX}_<floor>_Furn_<kind>_<nnn> (the id\'s number) + _<family, ASCII, at most 40 characters>', ok, why)
    ok = all(c['fam'] == none_text(BY_ID[c['id']]['family']) and c['blk'] == none_text(BY_ID[c['id']]['block']) and c['lay'] == none_text(BY_ID[c['id']]['layer'])
             and c['hnd'] == none_text(BY_ID[c['id']]['handle']) for c in CALLS if c['ok'] and c['id'] in BY_ID)
    check('the family, block, layer and handle that every box carries are the model\'s (ASCII; the word none where the model has nothing: a picture has no block and no handle)', ok)
    longfam = [p['id'] for p in PIECES if len(ascii_fold(p['family'])) > 40]
    info(f'{len(longfam)} families are longer than 40 characters and are cut in the object name ({", ".join(longfam[:6])}{" ..." if len(longfam) > 6 else ""}); the {PX}_family property holds the whole text')
    check('no double quote, backslash or control character inside any call, no bare minus before a number, no e-notation',
          all(not re.search(r'[\\\x00-\x1f]', c['raw'].replace('"', '')) and not re.search(r'(?<![(\w.])-\d', re.sub(r'"[^"]*"', '', c['raw'])) and 'e-' not in re.sub(r'"[^"]*"', '', c['raw']) for c in CALLS))
    check('the kind arrays are the model\'s kinds, in its order (only kinds that occur)', KEYS == [k['key'] for k in KINDS] and all(any(p['kind'] == k for p in PIECES) for k in KEYS), str(KEYS))
    check('layer suffix = the kind key in CamelCase (coffee-table -> CoffeeTable)', LAYERS == [camel(k) for k in KEYS], str(LAYERS))
    check('heights and bases (metres) = the model\'s mm / 1000 per kind', len(HEIGHTS) == len(BASES) == len(KINDS) and all(abs(h - k['height'] / 1000) < 1e-9 and abs(b - k['base'] / 1000) < 1e-9 for h, b, k in zip(HEIGHTS, BASES, KINDS)))
    check('the floors array is the floor keys in order (the call\'s floor index counts from 1), and the script\'s levels are the model\'s', FLOORS_S == FLOORS and len(LEVELS_S) == len(FLOORS) and all(abs(a - LEVEL[f]) < 1e-9 for a, f in zip(LEVELS_S, FLOORS)), f'{FLOORS_S} {LEVELS_S}')
    layers = {}
    for c in CALLS:
        if c['ok'] and 1 <= c['fi'] <= len(FLOORS_S) and c['kind'] in KEYS: layers.setdefault(f"{PX}_{FLOORS_S[c['fi'] - 1]}_Furn_{LAYERS[KEYS.index(c['kind'])]}", []).append(c['id'])
    want = {f"{PX}_{p['floor']}_Furn_{camel(p['kind'])}" for p in PIECES}
    check(f'every box lands on layer {PX}_<floor>_Furn_<Kind>: {len(layers)} layers, one per floor and kind that occurs ({", ".join(sorted(layers))})', set(layers) == want and all(l == f"{PX}_{BY_ID[i]['floor']}_Furn_{camel(BY_ID[i]['kind'])}" for l, v in layers.items() for i in v))
    check('one material per kind, "<px> Furn <key>" with the kind\'s colour, in the kinds\' order (the box takes material[kind index])',
          [m[0] for m in MATERIALS] == KEYS and all(tuple(int(x) for x in m[1:]) == tuple(int(k['colour'][j:j + 2], 16) for j in (1, 3, 5)) for m, k in zip(MATERIALS, KINDS)), str(MATERIALS[:2]))
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
    check(f'every caption fits its half of the {width} px window (an estimate: {room:.0f} px beside the 40 px field at 5.5 px a character: the longest caption is {max(len(c[1]) for c in SPINNERS)} characters) and the window is as wide as the bank\'s',
          width == 340 and all(len(cap) * 5.5 <= room for _, cap, *rest in SPINNERS) and all(line.endswith('fieldwidth:40') for line in re.findall(r'^        spinner fh\d+ .*$', TEXT, re.M)))
    reads = [re.findall(r'(fh\d+)\.value / 1000\.0', ln) for ln in re.findall(r'^\s+' + PX + r'_furnHeights = (#\(\(fh.*)$', TEXT, re.M)]
    check(f'the code that reads the window (Build and Apply) reads fh1..fh{len(KINDS)} in the kinds\' order, in mm / 1000', len(reads) == 2 and all(r == [f'fh{i + 1}' for i in range(len(KINDS))] for r in reads), str([len(r) for r in reads]))
    sup = [c for c in CALLS if c['ok'] and c['supId'] != 'none']
    n_on = sum(1 for p in PIECES if p['on'])
    check(f'{len(sup)} boxes stand on a support, as many as in the model ({n_on}): each support id is one of the calls\' ids and a support kind',
          len(sup) == n_on and all(c['supId'] in ids and KIND.get(c['supKind'], {}).get('support') for c in sup))


# ---- 4. every box -------------------------------------------------------------------------------------------------------------------

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
        ki, oki = keys.index(c['kind']), (keys.index(c['supKind']) if c['supKind'] != 'none' else -1)
        z0 = bases[oki] + heights[oki] if oki >= 0 else bases[ki]
        zb = levels[c['fi'] - 1] + z0 if 1 <= c['fi'] <= len(levels) else float('nan')
        want_zb = LEVEL[p['floor']] + readme_z0(p)
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


def test_geometry():
    section('every box: corners, base z and top z against the README\'s formulas')
    check('the transform is the explicit matrix3 [cos,sin,0] [-sin,cos,0] [0,0,1] [centre - shift, level + z0]',
          f'    o.transform = (matrix3 [ca, sa, 0.0] [(0.0 - sa), ca, 0.0] [0.0, 0.0, 1.0] [c.x - {PX}_shift.x, c.y - {PX}_shift.y, zb])' in TEXT.split('\n'))
    fz = re.search(rf'^fn {PX}_furnZ0 ki oki =\n\(\n(.*?)\n\)\n', TEXT, re.M | re.S)
    check('z0 = the kind\'s base, or the support kind\'s base + height (a support never stands on anything)',
          bool(fz) and fz.group(1) == f'    local z0 = {PX}_furnBases[ki]\n    if oki > 0 do z0 = {PX}_furnBases[oki] + {PX}_furnHeights[oki]\n    z0')
    box = fn_text(f'{PX}_furnBox')
    check('base z = the level of its floor + z0, top z = base z + its kind\'s height', f'local zb = {PX}_furnLevels[fi] + z0' in box and f'local ht = {PX}_furnHeights[ki]' in box and 'height:ht' in box)
    bad, worst, worst_cs = geometry_problems(CALLS, KEYS, BASES, HEIGHTS, LEVELS_S)
    check(f'all {len(CALLS)} boxes: the four world corners from the matrix3 numbers and the size = the README\'s corners, the corners the script checks against = the README\'s (worst {worst * 1000:.3f} mm and {worst_cs * 1000:.3f} mm, limit 0.5 mm), cos / sin, centre, size, supports, base z and top z',
          not bad and len(CALLS) == len(PIECES), '; '.join(bad[:3]))
    n_on = sum(1 for p in PIECES if p['on'])
    tops = sorted({round(LEVEL[p['floor']] + readme_z0(p), 3) for p in PIECES if p['on']})
    zs = sorted({round(LEVEL[p['floor']] + readme_z0(p), 3) for p in PIECES})
    info(f'{n_on} boxes stand on a support (base z {", ".join(str(t) for t in tops)} m); all bases: {", ".join(str(z) for z in zs)} m; tops up to {max(LEVEL[p["floor"]] + readme_z0(p) + KIND[p["kind"]]["height"] / 1000 for p in PIECES):.3f} m')
    rot = next(c for c in CALLS if c['ok'] and abs(c['sa'][0]) > 0.05 and abs(c['ca'][0]) > 0.05)
    flat = next(c for c in CALLS if c['ok'] and c['w'][0] > c['d'][0] + 0.05)
    onsup = next((c for c in CALLS if c['ok'] and c['supId'] != 'none'), None)
    nosup = next(c for c in CALLS if c['ok'] and c['supId'] == 'none')
    slips = [
        ('a rotation of the wrong sign (sin negated) on a turned box', lambda c: c[rot['id']]['sa'].__setitem__(0, -rot['sa'][0])),
        ('a centre moved by 1 mm', lambda c: c[flat['id']]['c'].__setitem__(0, flat['c'][0] + 0.001)),
        ('width and depth swapped', lambda c: (c[flat['id']]['w'].__setitem__(0, flat['d'][0]), c[flat['id']]['d'].__setitem__(0, flat['w'][0]))),
        ('a corner of the script\'s own check moved by 1 mm', lambda c: c[flat['id']]['cs'].__setitem__(0, flat['cs'][0] + 0.001)),
        ('the wrong floor index', lambda c: c[flat['id']].__setitem__('fi', 3 - flat['fi'])),
        ('a box on nothing whose support kind is an empty string, not the word none', lambda c: c[nosup['id']].__setitem__('supKind', '')),
        ('a box on nothing whose support id is an empty string, not the word none', lambda c: c[nosup['id']].__setitem__('supId', '')),
        ('a box of another kind', lambda c: c[flat['id']].__setitem__('kind', next(k for k in KEYS if k != flat['kind']))),
    ]
    if onsup:                                    # a box that stands on another: its support forgotten, or the wrong kind of support
        slips += [('a box on a support that does not know its support', lambda c: c[onsup['id']].__setitem__('supKind', 'none')),
                  ('a box on the wrong kind of support', lambda c: c[onsup['id']].__setitem__('supKind', next(k for k in KEYS if k != onsup['supKind'] and KIND[k]['height'] != KIND[onsup['supKind']]['height'])))]
    else:                                        # no box of the model stands on another (the hotel since 2 Nov): the same slips the other way round
        prop = next(c for c in CALLS if c['ok'] and KIND[c['kind']].get('support') and c['id'] != nosup['id'])
        info(f'no box of this model stands on another: the support slips are tried on {nosup["id"]}, a box on nothing, with {prop["id"]} ({prop["kind"]}) as the support it does not have')
        slips += [(f'a box on nothing said to stand on a {prop["kind"]} (id and kind given)', lambda c: (c[nosup['id']].__setitem__('supId', prop['id']), c[nosup['id']].__setitem__('supKind', prop['kind']))),
                  (f'a box on nothing given a support kind ({prop["kind"]}) but no support id', lambda c: c[nosup['id']].__setitem__('supKind', prop['kind']))]
    for label, f in slips:
        by = {c['id']: copy.deepcopy(c) for c in CALLS if c['ok']}
        f(by)
        got = geometry_problems(list(by.values()), KEYS, BASES, HEIGHTS, LEVELS_S)[0]
        check(f'slip found: {label}', bool(got), 'NOT noticed')


# ---- 5. the code ------------------------------------------------------------------------------------------------------------------

def test_code():
    section('the code: add-only, apply heights, update levels; no box is ever collapsed or converted')
    build, add, apply_ = fn_text(f'{PX}_build'), fn_text(f'{PX}_furnAdd'), fn_text(f'{PX}_furnApply')
    at = lambda s: build.find(s) if s in build else 10 ** 9
    check('"Furniture boxes only": the first thing Build does (before its empty-scene check) is to hand over to furnAdd when the tick box says so, and to return false: furnAdd says what it did in a message of its own',
          bool(add) and at(f'if {PX}_furnAddOnly then') < at('if objects.count > 0 then') and f'        {PX}_furnAdd()\n        return false' in build and 'furnDone' not in build)
    check('... its own messages: "Added N furniture boxes. Every box passed its height and position checks ..." when all passed, "M of the N furniture boxes failed a check ... layer Check_Failed" when some did; the message about parts is not used for it',
          f'if {PX}_failed.count == 0 then messageBox ("Added " + ({PX}_nodes.count as string) + " furniture boxes. Every box passed its height and position checks. Nothing else in this scene was changed.' in add
          and f'else messageBox (({PX}_failed.count as string) + " of the " + ({PX}_nodes.count as string) + " furniture boxes failed a check and are on layer {PX}_Check_Failed' in add
          and 'closed-solid' not in add and 'part(s)' not in add)
    check('... furnAdd refuses (and changes nothing) when "Build furniture boxes" is off, when System Units are not metres, and when boxes are there already',
          all(s in add for s in (f'if {PX}_furnWant == false then', 'units.systemType != #meters', f'(getUserProp o "{PX}_furn") != undefined or (matchPattern o.layer.name pattern:"{PX}_*_Furn_*")', 'return false')))
    check(f'... it takes the placement from the hidden datum {PX}_ORIGIN_DWG and each level from the objects that carry {PX}_floor and {PX}_base, adds the boxes and says how many',
          all(s in add for s in (f'o.name == "{PX}_ORIGIN_DWG"', f'{PX}_shift = [0.0 - datum.pos.x, 0.0 - datum.pos.y]', f'{PX}_furnSceneLevels()', f'{PX}_furnAll()', 'FURNITURE BOXES ADDED')))
    check('... and it builds no structure and sets no System Units', f'{PX}_part' not in add and f'{PX}_lines' not in add and f'{PX}_room' not in add and 'units.systemType =' not in add and 'units.systemScale =' not in add)
    check('Build refuses a scene that has objects (nothing changed) and sets System Units to metres before it builds',
          at('if objects.count > 0 then') < at('units.systemType = #meters') < at(f'{PX}_makeMaterials()') and 'Nothing in this scene has been changed.' in build and 'units.systemScale = 1.0' in build)
    check('"Apply furniture heights": the button is in the group "After the build", its handler reads the window and calls furnApply',
          bool(re.search(r'group "After the build"\n    \(\n        button upd .*\n        button col .*\n        button fap "Apply furniture heights" width:300\n    \)\n', TEXT)) and
          bool(re.search(rf'    on fap pressed do\n    \(\n        {PX}_furnHeights = #\(\(fh1\.value.*\n        local r = {PX}_furnApply\(\)\n', TEXT)))
    check('... furnApply sets each box\'s height and puts it on its kind\'s base or its support\'s top, keeps its level, and leaves a box that is not a Box any more alone',
          all(s in apply_ for s in ('if (classOf o) != Box or ki == 0 then skipped += 1', f'o.pos.z = o.pos.z - ({PX}_furnNum (getUserProp o "{PX}_base")) + z0', f'o.height = {PX}_furnHeights[ki]', f'setUserProp o "{PX}_base" z0')))
    upd, col = fn_text(f'{PX}_updateLevels'), fn_text(f'{PX}_collapseAll')
    check('"Update levels and heights" moves everything that carries a floor to level + base, and sets heights only where follow is "true"',
          f'where (getUserProp o "{PX}_floor") != undefined do' in upd and 'o.pos.z = newLevels[fi] + base' in upd and f'if ((getUserProp o "{PX}_follow") as string) == "true" do' in upd)
    fbox = fn_text(f'{PX}_furnBox')
    hits = [l for l in fbox.split('\n') if 'o.min.x' in l]
    check('the node\'s min / max in the plan (the world bounding box) is compared once, and only for an unrotated box (unrotated: sin of the rotation within 0.00001 of 0 and cos positive); base z, top z and the four corners are compared for every box',
          'local unrotated = abs(sa) < 0.00001 and ca > 0.0' in fbox and len(hits) == 1 and hits[0].startswith('    else if unrotated and (abs(o.min.x')
          and hits[0].endswith('then why = "bounding box"') and 'then why = "base z"' in fbox and 'then why = "top z"' in fbox and 'why = "corner " + (k as string)' in fbox, hits[0][:80] if hits else 'no line')
    check('the script says the rule twice, in the header of the furniture code and in the comment above the checks (only for an unrotated box), and nowhere speaks of a multiple of 90 degrees or of quarterTurn',
          TEXT.count('only for an unrotated box') == 2 and 'multiple of 90' not in TEXT and 'quarterTurn' not in TEXT, str(TEXT.count('only for an unrotated box')))
    props = dict(re.findall(rf'setUserProp o "{PX}_(\w+)" (.*)$', fbox, re.M))
    check('... and every box carries floor (its index), base (z0) and follow = false, so Update moves it with its level and leaves its height alone',
          props.get('floor') == 'fi' and props.get('base') == 'z0' and props.get('follow') == 'false', str({k: props.get(k) for k in ('floor', 'base', 'follow')}))
    want = ['furn', 'furnKind', 'furnId', 'furnOn', 'furnOnKind', 'family', 'block', 'layer', 'handle', 'floor', 'base', 'follow', 'check']
    check('every box carries the user properties ' + ', '.join(f'{PX}_{w}' for w in want), all(w in props for w in want), str(sorted(props)))
    check('"Collapse all now" takes only objects that carry kind and a modifier: a box has neither (no kind property, no modifier)',
          f'where (getUserProp o "{PX}_kind") != undefined and o.modifiers.count > 0' in col and 'kind' not in props)
    furn = code('\n'.join(fn_text(f'{PX}_furn{n}') for n in ('Num', 'MakeMaterials', 'SetLevels', 'Z0', 'Box', 'All', 'Run', 'SceneLevels', 'Add', 'Apply')))
    check('the furniture code has no convertTo, collapseStack, Editable, addModifier, snapshotAsMesh, Extrude or splineShape: a box stays a live Box',
          bool(furn) and not re.search(r'convertTo|collapseStack|Editable|addModifier|snapshotAsMesh|Extrude|splineShape', furn, re.I))
    check('a box is made with the Box primitive, once, in furnBox only', furn.count(' = box name:nm width:w length:d height:ht') == 1 and code(TEXT).count('box name:') == 1)
    parts_collapse = [m.start() for m in re.finditer(r'convertToMesh', code(TEXT))]
    inside = fn_text(f'{PX}_part')
    check('convertToMesh appears only in the part builder (after the tick box) and in "Collapse all now"; convertToPoly and convertTo nowhere',
          len(parts_collapse) == inside.count('convertToMesh') + col.count('convertToMesh') and f'if {PX}_collapse do convertToMesh o' in inside and not re.search(r'convertToPoly|convertTo\b|Editable_?Poly', code(TEXT), re.I))
    check('every part is a spline + Extrude (output: mesh, capped) + Smooth, checked as built (closed solid, height, position within 0.002 m)',
          'addModifier o (Extrude amount:ht segs:1 capStart:true capEnd:true output:1 smooth:false)' in inside and 'addModifier o (Smooth autoSmooth:true threshold:25.0)' in inside
          and '(meshop.getOpenEdges m).numberSet != 0' in inside and 'local tol = 0.002' in inside and 'then why = "height"' in inside and 'then why = "position"' in inside)
    check('the build calls the furniture step after the parts, stair lines and room names, before the datum, and only when "Build furniture boxes" is ticked',
          bool(re.search(rf'\n    {PX}_room [^\n]*\n    if {PX}_furnWant do {PX}_furnRun\(\)\n    local origin = point name:"{PX}_ORIGIN_DWG"', TEXT)))


# ---- 6. the generator ---------------------------------------------------------------------------------------------------------

def run_generator(model_bytes):
    """The generator, copied to a temporary folder with the module and a model, run there; returns (script text with LF, stdout)."""
    tmp = Path(tempfile.mkdtemp(prefix='hotel_ms_'))
    try:
        g = tmp / 'hotel_test' / 'src' / 'generate_maxscript.py'
        g.parent.mkdir(parents=True)
        shutil.copy(GENERATOR, g)
        (g.parent / 'hotel_model.json').write_bytes(model_bytes)
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


# Comparing with the bank's scripts: the prefix and the short name are set aside, and every line that only carries data (a part, stair,
# room or box call, the arrays of levels and kinds, a material or spinner of a kind, what the window reads) becomes <data>; runs of
# such lines become one. What is left is the code, and its comments, line for line.
DATA_LINES = [(re.compile(p), r) for p, r in (
    (r'^(    PX_part #).*', r'\1<data>'), (r'^(    PX_lines ").*', r'\1<data>'), (r'^(    PX_room ").*', r'\1<data>'),
    (r'^(    PX_furnBox ").*', r'\1<data>'),
    (r'^(global PX_(?:levels|heights|floorNames|furnFloors|furnKeys|furnLayers|furnBases|furnHeights) = ).*', r'\1<data>'),
    (r'^(    append PX_furnMats \(standardMaterial name:"PX Furn ).*', r'\1<data>'),
    (r'^(    spinner (?:lv|ht))\d+ .*', r'\1 <data>'), (r'^(        spinner fh)\d+ .*', r'\1 <data>'),
    (r'^(        PX_(?:levels|heights|furnHeights) = ).*', r'\1<data>'), (r'^(        local r = PX_updateLevels ).*', r'\1<data>'),
    (r'^(        PX_shift = if dwg\.checked then \[0\.0, 0\.0\] else ).*', r'\1<data>'))]
# The lines that differ from the bank's on purpose (besides the header comment block before the first global): the datum's Source
# (pictures, not a DWG converted with LibreDWG), its Picture properties (new: where each picture goes), and the tooltip of the
# placement tick box (what the drawing's own coordinates are here). Each is text in a string: no code changes.
REVIEWED = [re.compile(p) for p in (r'^    setUserProp origin "Source" "[^"]*"$', r'^    setUserProp origin "Picture_\w+" "[^"]*"$',
                                     r'^    checkbox dwg "At the drawing\'s own coordinates" checked:true tooltip:"[^"]*"$')]


def normalise(text):
    px = re.search(r'^global (\w+)_UI$', text, re.M).group(1)
    short = re.search(rf'^rollout {px}_UI "(.*) \(test\)" width:\d+$', text, re.M).group(1)
    out = []
    for line in text.split('\n'):
        line = re.sub(rf'\b{px}(?=[_ ])', 'PX', line).replace(f'title:"{short}"', 'title:"SHORT"').replace(f'"{short} (test)"', '"SHORT (test)"')
        for pat, rep in DATA_LINES:
            new = pat.sub(rep, line)
            if new != line: line = new; break
        if not (out and line == out[-1] and line.endswith('<data>')): out.append(line)
    return out


def code_diff(old, new):
    """The hunks between the bank's script `old` and `new` once normalised, and the lines of them that are not reviewed."""
    a, b = normalise(old), normalise(new)
    ga = next(i for i, l in enumerate(a) if l.startswith('global '))
    gb = next(i for i, l in enumerate(b) if l.startswith('global '))
    hunks = [o for o in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes() if o[0] != 'equal']
    loose = [f'- {a[i][:90]}' for _, i1, i2, _, _ in hunks for i in range(i1, i2) if not (i < ga or any(r.match(a[i]) for r in REVIEWED))]
    loose += [f'+ {b[j][:90]}' for _, _, _, j1, j2 in hunks for j in range(j1, j2) if not (j < gb or any(r.match(b[j]) for r in REVIEWED))]
    changed = {k: ([a[i] for _, i1, i2, _, _ in hunks for i in range(i1, i2) if r.match(a[i])], [b[j] for _, _, _, j1, j2 in hunks for j in range(j1, j2) if r.match(b[j])])
               for k, r in zip(('source', 'picture', 'tooltip'), REVIEWED)}
    return a, b, ga, gb, hunks, loose, changed


def test_generator():
    section('the generator: what it writes today, without furniture, what it refuses, and the bank\'s code')
    try:
        again, out = run_generator(MODEL_RAW)
    except RuntimeError as e:
        check('the generator runs on the real model', False, str(e)); return
    first = next((i for i, (a, b) in enumerate(zip(again.split('\n'), LINES)) if a != b), None)
    check('the script on disk is exactly what the generator writes today from this model (it is not stale)', again == TEXT, f'first difference at line {first and first + 1}')
    check('the generator printed the furniture summary and its four sanity flags are all True (brackets counted as MAXScript reads them)',
          f'furniture boxes {len(PIECES)} (' in out and f'height spinners {len(KINDS)}' in out and 'balanced ( ): True | [ ]: True | even quotes: True | ascii only: True | no placeholders left: True' in out, out[-300:])
    n = announced()
    check(f'the generator says how many objects Build makes: {n} ({len(PARTS)} parts, {len(stair_shapes())} stair shapes, {len(M["rooms"])} room names, {len(PIECES)} furniture boxes)',
          f'objects Build announces: {n} ({len(PARTS)} parts, {len(stair_shapes())} stair shapes, {len(M["rooms"])} room names, {len(PIECES)} furniture boxes)' in out, out[-300:])
    ref = reference()
    if not check('the generator runs on the model without its furniture keys', ref is not None): return
    base, out0 = ref
    check('a model without furniture: no furniture line at all (no furn / Furn / fh1 / fap anywhere), and the generator says so', not re.search(r'furn|fh\d|\bfap\b', base, re.I) and out0.startswith('no furniture'), out0[:60])
    stamp = lambda t: re.sub(r'model data [0-9a-f]{12}', 'model data <sha1 of the model file>', t).split('\n')
    ops = [o for o in difflib.SequenceMatcher(None, stamp(base), stamp(TEXT), autojunk=False).get_opcodes() if o[0] != 'equal']
    n_new = sum(o[4] - o[3] for o in ops)
    check('with furniture the script differs from the one without only by inserted lines (nothing of the structure script is changed or moved)', bool(ops) and all(o[0] == 'insert' for o in ops), str([o[0] for o in ops]))
    first_lines = [stamp(TEXT)[o[3]][:44] for o in ops]
    want_first = ['-- Furniture boxes: one coloured placeholder', '-- Furniture boxes: one coloured Box per piece,', f'    if {PX}_furnAddOnly then', f'    if {PX}_furnWant do {PX}_furnRun()',
                  '    group "Furniture boxes (heights in mm)"', '        button fap "Apply furniture heights" width:300', f'        {PX}_furnHeights = #((fh1.value / 1000.0)', '    on fap pressed do']
    check(f'... in the eight places of the recipe (globals, functions, add-only, build, window, apply button, read, handler): {len(ops)} hunks, {n_new} new lines',
          len(ops) == 8 and all(f.startswith(w[:44]) for f, w in zip(first_lines, want_first)), str(first_lines))
    info(f'{len(base)} -> {len(TEXT)} characters; the script without furniture is {len(stamp(base)) - 1} lines')
    # the bank's code: the structure part as the 3D team ran it on 28 Oct, the furniture part as written on 29 Oct
    if not BANK_RUN.exists() or not BANK_NOW.exists(): skip('the bank\'s code', f'{BANK_RUN.name} or {BANK_NOW.name} not found')
    else:
        raw_run = BANK_RUN.read_bytes()
        check(f'the bank\'s script the 3D team ran on 28 Oct is the one compared with ({BANK_RUN.parent.name}/, sha1 {BANK_RUN_SHA[:8]}...)', hashlib.sha1(raw_run).hexdigest() == BANK_RUN_SHA, hashlib.sha1(raw_run).hexdigest())
        run_text = raw_run.decode('latin-1').replace('\r\n', '\n')
        now_text = BANK_NOW.read_bytes().decode('latin-1').replace('\r\n', '\n')
        for label, old, new in (('the structure script (this model without furniture) against the script the 3D team ran on 28 Oct', run_text, base),
                                ('the real script against the bank\'s script with furniture of 29 Oct (its furniture part not yet run in Max)', now_text, TEXT)):
            a, b, ga, gb, hunks, loose, changed = code_diff(old, new)
            n_pic = sum(1 for f in M['floors'] if (M.get('pictureFrame') or {}).get(f['key']))
            check(f'{label}: once the prefix and the data are set aside, every line of code is the bank\'s ({len(b) - gb} lines after the header compared); the only other lines that differ are the header comments ({ga} lines -> {gb}), '
                  f'the datum\'s Source, its {n_pic} Picture properties (new) and the placement tick box\'s tooltip, each text in a string',
                  not loose and len(changed['source'][0]) == len(changed['source'][1]) == 1 and changed['picture'] == ([], changed['picture'][1]) and len(changed['picture'][1]) == n_pic
                  and len(changed['tooltip'][0]) == len(changed['tooltip'][1]) == 1, '; '.join(loose[:3]) or str({k: (len(v[0]), len(v[1])) for k, v in changed.items()}))
        a, b, ga, gb, hunks, loose, changed = code_diff(now_text, TEXT)
        for k in ('source', 'tooltip'):
            info(f'{k}, bank:  {changed[k][0][0].strip()[:150] if changed[k][0] else "-"}')
            info(f'{k}, hotel: {changed[k][1][0].strip()[:150] if changed[k][1] else "-"}')
        for line in changed['picture'][1]: info(f'new:  {line.strip()[:150]}')
        # the comparison has teeth: a change to one code line, to a comment inside the code, or one more statement is found
        slips = [('a tolerance changed in the part builder', lambda t: t.replace('    local tol = 0.002\n', '    local tol = 0.003\n', 1)),
                 ('a comment inside the code changed', lambda t: t.replace('-- the checks run on the evaluated mesh', '-- the checks run on the mesh', 1)),
                 ('one more statement in Build', lambda t: t.replace('    units.systemScale = 1.0\n', '    units.systemScale = 1.0\n    units.displayType = #generic\n', 1)),
                 ('one more datum property', lambda t: t.replace(f'    setUserProp origin "Source"', f'    setUserProp origin "Note" "x"\n    setUserProp origin "Source"', 1)),
                 ('a Picture property that is code, not text', lambda t: t.replace('    setUserProp origin "Picture_', '    setUserProp origin ("Picture_" + "x") "x"\n    setUserProp origin "Picture_', 1))]
        for label, f in slips:
            t2 = f(TEXT)
            check(f'slip found by the comparison with the bank: {label}', t2 != TEXT and bool(code_diff(now_text, t2)[5]), 'NOT noticed')
        if ms is not None:
            _, p_h, k_h = ms.words(ms.tokenize(TEXT)[0])
            _, p_b, k_b = ms.words(ms.tokenize(now_text)[0])
            u_h, u_b = {w.lower() for w in ms.unresolved(TEXT)}, {w.lower() for w in ms.unresolved(now_text)}
            low = lambda s: {x.lower() for x in s}
            check(f'the script uses no Max word that the bank\'s script does not: {len(u_h)} built-in names, {len(p_h)} properties after a dot, {len(k_h)} keyword arguments, all in the bank\'s',
                  u_h <= u_b and low(p_h) <= low(p_b) and low(k_h) <= low(k_b), f'{sorted(u_h - u_b)} {sorted(low(p_h) - low(p_b))} {sorted(low(k_h) - low(k_b))}')
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
    # the generator refuses outlines Extrude could not cap, and writes nothing
    holed = next(i for i, p in enumerate(PARTS) if len(p['h']) >= 2)
    lin = next(i for i, p in enumerate(PARTS) if p['kind'] == 'lintel')

    def bad_model(f):
        M3 = copy.deepcopy(M); f(M3['parts']); return json.dumps(M3, ensure_ascii=False).encode('utf-8')
    refusals = [('a hole touching its outline', lambda ps: ps[holed]['h'][0].__setitem__(0, ps[holed]['o'][0]), 'a hole touches the outline'),
                ('two holes touching each other', lambda ps: ps[holed]['h'][1].__setitem__(0, ps[holed]['h'][0][0]), 'two holes touch'),
                ('a repeated point', lambda ps: ps[lin]['o'].insert(1, ps[lin]['o'][0]), 'repeated point'),
                ('a bow-tie outline', lambda ps: ps[lin]['o'].__setitem__(slice(1, 3), [ps[lin]['o'][2], ps[lin]['o'][1]]), 'invalid polygon')]
    for label, f, why in refusals:
        try: run_generator(bad_model(f)); msg = 'it wrote a script'
        except RuntimeError as e: msg = str(e)
        check(f'the generator refuses {label} ("{why}") and writes no script', 'DATA PROBLEMS' in msg and why in msg, msg[:120])


# ---- lint with teeth -----------------------------------------------------------------------------------------------------------

def test_lint_teeth():
    section('the lint finds slips that are put into the real script on purpose')
    if ms is None: skip('lint sensitivity', 'maxscript_lite.py not found'); return
    last = CALLS[-1]['raw']
    lastp = PART_CALLS[-1]['raw']
    slips = [
        ('a then is missing', lambda t: t.replace('if oki > 0 do z0', 'if oki > 0 z0', 1), 'lint'),
        ('an else without if', lambda t: t.replace('    local why = ""\n', '    local why = ""\n    else why = "x"\n', 1), 'lint'),
        ('a ) is missing', lambda t: t.replace('        local hw = o.width / 2.0\n', '        local hw = (o.width / 2.0\n', 1), 'lint'),
        ('a quote is missing', lambda t: t.replace(f'setUserProp o "{PX}_furnId" pid', f'setUserProp o "{PX}_furnId pid', 1), 'lint'),
        ('a quote is missing in a Picture property', lambda t: t.replace('    setUserProp origin "Picture_', '    setUserProp origin "Picture_ "', 1), 'lint'),
        ('a for without do', lambda t: t.replace('for k = 1 to 4 do', 'for k = 1 to 4', 1), 'lint'),
        ('a global misspelt once', lambda t: t.replace(f'{PX}_furnHeights[ki]\n    local zb', f'{PX}_furnHeigths[ki]\n    local zb', 1), 'names'),
        ('a local misspelt once', lambda t: t.replace('local zb = ', 'local zbb = ', 1), 'names'),
        ('an argument dropped from the last real box call', lambda t: t.replace(last, last.rsplit(' ', 1)[0], 1), 'arity'),
        ('an argument added to a real box call', lambda t: t.replace(last, last + ' "x"', 1), 'arity'),
        ('an argument dropped from the last part call', lambda t: t.replace(lastp, lastp.rsplit(' ', 1)[0], 1), 'arity'),
    ]
    base_unres = ms.unresolved(TEXT)
    for label, f, kind in slips:
        t = f(TEXT)
        found = t != TEXT and ((kind == 'lint' and ms.lint(t)) or (kind == 'arity' and ms.arity_errors(t)) or (kind == 'names' and ms.unresolved(t) - base_unres))
        check(f'lint slip found: {label}', found, 'NOT noticed')


# ---- 7. the generated functions, run by the interpreter over a mock scene ---------------------------------------------------------

def mock_read_text():
    i = next(k for k, l in enumerate(LINES) if l.startswith(f'        {PX}_shift = if dwg.checked'))
    return '\n'.join(LINES[i + 1:i + 4])                  # the three lines of "on build pressed" that read the window


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
    """The part, stair-line and room builders need splines and modifiers; stand-ins make the nodes they make (position = level + z0,
    user properties kind / floor / base / follow) so that Update levels and the datum can be tried. The furniture code is the real one."""
    def node(cls, nm, fi, c, z, base, **props):
        sh = it.get(f'{PX}_shift')
        n = mk.Node(it.scene, mk.Cls(cls), nm)
        n.tm.rows[3] = mk.P(c.v[0] - sh.v[0], c.v[1] - sh.v[1], z)
        n.props.update({f'{PX}_floor': str(fi), f'{PX}_base': mk.tostr(base)}); n.props.update(props)
        it.get(f'{PX}_nodes').append(n)
        return n
    lv = lambda fi: it.get(f'{PX}_levels')[fi - 1]
    it.override(f'{PX}_part', lambda it, kind, nm, loops, z0, z1, follow, fi, c, mn, mx: node('SplineShape', nm, fi, c, lv(fi) + z0, z0, **{f'{PX}_kind': str(kind), f'{PX}_follow': mk.tostr(follow)}))
    it.override(f'{PX}_lines', lambda it, nm, segs, fi, c, lay: node('SplineShape', nm, fi, c, lv(fi), 0.0))
    it.override(f'{PX}_room', lambda it, nm, p, fi: node('Text', f'{PX}_Room_{nm}', fi, p, lv(fi) + 0.02, 0.02))


def make_run(shift=(0.0, 0.0), values=None, want=True, only=False, scene=None, text=None):
    it = mk.Interp(text or TEXT, scene)             # (a damaged copy of the script's text, for the negative controls, or the real script)
    install_fakes(it)
    it.run(mock_read_text(), **controls(values, want, only))              # the code of "on build pressed" that reads the window
    it.set(f'{PX}_shift', mk.P(*shift))
    return it


def boxes_of(it): return {n.props[f'{PX}_furnId']: n for n in it.scene.objects if f'{PX}_furn' in n.props}


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
    levels = [LEVEL[f] for f in FLOORS]
    default = {k['key']: half_up(k['height']) for k in KINDS}
    typed = {k['key']: default[k['key']] + 10 * (i + 1) for i, k in enumerate(KINDS)}
    typed.update({'table': 800, 'coffee-table': 400} if 'table' in typed else {})
    try:
        it = make_run()
        ok = it.call(f'{PX}_build')
        n_other = len(it.scene.objects) - len(PIECES) - 1                                   # the parts, stair lines and rooms of the stand-ins, and the datum
        check(f'Build (the drawing\'s own coordinates) runs to the end in an empty scene and returns true ({len(it.scene.objects)} objects: {n_other} structure, {len(PIECES)} boxes, the datum)', ok is True)
        n = announced()
        nodes = it.get(f'{PX}_nodes')
        check(f'... it announces {n} objects (the node list its message and the Listener count: {len(PARTS)} parts, {len(stair_shapes())} stair shape, {len(M["rooms"])} room names, {len(PIECES)} boxes; the hidden datum is not counted)',
              len(nodes) == n and any(s.startswith(f'{PX} BUILD COMPLETE: {n} objects in ') for s in it.scene.listener) and 'Built " + (' + f'{PX}_nodes.count as string) + " objects.' in TEXT, f'{len(nodes)} nodes; {it.scene.listener[-1:]}')
        bad = box_problems(it, levels, (0.0, 0.0))
        check(f'... all {len(PIECES)} boxes are plain Box objects with the README\'s matrix3, size, base corners, layer, material, wire colour and properties', not bad, '; '.join(bad[:3]))
        check('... every box passed its own checks (nothing in the failed list or on a Check_Failed layer, no message box), the Listener says 0 failed checks',
              it.get(f'{PX}_failed') == [] and f'{PX}_check_failed'.lower() not in it.scene.layers and it.scene.messages == [] and any(s.rstrip().endswith('0 failed checks') for s in it.scene.listener), str(it.get(f'{PX}_failed')[:2]))
        check('... the boxes are part of the node list the footer selects, and the hidden datum is made after them', sum(1 for n in nodes if f'{PX}_furn' in n.props) == len(PIECES) and any(n.name == f'{PX}_ORIGIN_DWG' for n in it.scene.objects))
        datum = next(n for n in it.scene.objects if n.name == f'{PX}_ORIGIN_DWG')
        pics = sorted(k for k in datum.props if k.startswith('Picture_'))
        check(f'... the datum is a hidden point at 0,0,0 on {PX}_Datums, outside the extents, carrying Source, Levels and {", ".join(pics)}',
              datum.cls.name == 'Point' and datum.flags.get('ishidden') is True and datum.flags.get('ignoreextents') is True and datum.layer.name == f'{PX}_Datums'
              and datum.tm.rows[3].v == [0.0, 0.0, 0.0] and {'Source', 'Levels'} <= set(datum.props) and pics == sorted(f'Picture_{f}' for f in FLOORS if (M.get('pictureFrame') or {}).get(f))
              and datum.props['Levels'] == f'floor levels {mk.tostr(levels)} m, wall heights {mk.tostr([f["wallHeight"] for f in M["floors"]])} m', str(datum.props)[:200])
        it2 = make_run(shift=(OX, OY))
        it2.call(f'{PX}_build')
        bad = box_problems(it2, levels, (OX, OY))
        d2 = next(n for n in it2.scene.objects if n.name == f'{PX}_ORIGIN_DWG')
        check('Build centred on the origin (shift = the offset): every box follows, no check fails, and the datum moves to minus the offset (the picture placement is given from it, so it follows too)',
              not bad and it2.get(f'{PX}_failed') == [] and max(abs(a - b) for a, b in zip(d2.tm.rows[3].v, (-OX, -OY, 0.0))) < 1e-9, '; '.join(bad[:3]))
        it3 = make_run(want=False)
        it3.call(f'{PX}_build')
        check('"Build furniture boxes" unticked: no box, no furniture layer, no furniture material', boxes_of(it3) == {} and not any('_furn_' in k for k in it3.scene.layers) and not it3.get(f'{PX}_furnMats'))
        it4 = make_run(values=[typed[k['key']] for k in KINDS])
        it4.call(f'{PX}_build')
        check('Build with other heights typed in the window: every box has its kind\'s typed height, the boxes on supports stand on the typed tops',
              not box_problems(it4, levels, (0.0, 0.0), typed))
        it5 = make_run()
        it5.call(f'{PX}_build')
        it5.run(mock_apply_text(), **controls([typed[k['key']] for k in KINDS]))
        bad = box_problems(it5, levels, (0.0, 0.0), typed)
        msg = it5.scene.messages[-1][0] if it5.scene.messages else ''
        check(f'"Apply furniture heights": new heights, boxes re-seated on their supports, the message says {len(PIECES)} boxes and nothing was left alone', not bad and msg.startswith(f'{len(PIECES)} furniture boxes set to the heights') and 'left alone' not in msg, '; '.join(bad[:3]) + msg[:80])
        new_levels = [0.0, 3.5]
        it5.call(f'{PX}_updateLevels', list(new_levels), [3.5, 3.0])
        after = boxes_of(it5)
        heights_kept = all(abs(after[pid].params['height'] - typed[BY_ID[pid]['kind']] / 1000) < 1e-9 for pid in after)
        bad = box_problems(it5, new_levels, (0.0, 0.0), typed)
        n_f2 = sum(1 for p in PIECES if p['floor'] == FLOORS[1])
        moved = [n for n in it5.scene.objects if n.props.get(f'{PX}_floor') == '2' and f'{PX}_furn' not in n.props]
        check(f'"Update levels and heights" (floor 2 from {levels[1]:.2f} to 3.50 m) moves the {n_f2} boxes of floor 2 up with it, their supports\' tops included, touches no box height, and moves the {len(moved)} stand-ins of floor 2 to 3.50 + their base',
              not bad and heights_kept and all(abs(n.tm.rows[3].v[2] - (3.5 + float(n.props[f'{PX}_base']))) < 1e-9 for n in moved), '; '.join(bad[:3]))
        it5.run(mock_apply_text(), **controls([typed[k['key']] + 5 for k in KINDS]))
        bad = box_problems(it5, new_levels, (0.0, 0.0), {k: v + 5 for k, v in typed.items()})
        check('... and "Apply furniture heights" after it keeps each box on the level it moved to (z = level + the new support top)', not bad, '; '.join(bad[:3]))
        ref = make_run(shift=(OX, OY))
        ref.call(f'{PX}_build')
        snap = lambda it: {pid: (n.name, [r.v[:] for r in n.tm.rows], dict(n.params), n.layer.name, dict(n.props)) for pid, n in boxes_of(it).items()}
        base = make_run(shift=(OX, OY), want=False)
        base.call(f'{PX}_build')
        n_before = len(base.scene.objects)
        base.run(mock_read_text(), **controls(None, True, True))                           # the box ticks: furniture boxes only
        base.set(f'{PX}_shift', mk.P(0.0, 0.0))                                            # the window says "the drawing's own coordinates" (wrong for this scene)
        base.set(f'{PX}_levels', [9.0] * len(FLOORS))                                      # and wrong levels
        ok = base.call(f'{PX}_build')
        msgs = [m[0] for m in base.scene.messages]
        check(f'"Furniture boxes only" on a scene built without furniture: adds exactly the {len(PIECES)} boxes (objects {n_before} -> {len(base.scene.objects)}), no empty-scene refusal, says "Added {len(PIECES)} furniture boxes. Every box passed its height and position checks." in one message of its own, and Build returns false',
              ok is False and len(base.scene.objects) == n_before + len(PIECES) and len(msgs) == 1
              and msgs[0].startswith(f'Added {len(PIECES)} furniture boxes. Every box passed its height and position checks.') and 'closed-solid' not in msgs[0], str(msgs[:1]))
        check('... the placement shift comes from the datum and each level from the objects (the window said shift 0 and levels 9): the boxes are identical to those of a single Build', snap(base) == snap(ref))
        n_now = len(base.scene.objects)
        base.run(mock_read_text(), **controls(None, True, True))
        ok = base.call(f'{PX}_build')
        check('... a second time it refuses politely (boxes exist), returns false and changes nothing', ok is False and 'already has furniture boxes' in base.scene.messages[-1][0] and len(base.scene.objects) == n_now)
        other = make_run(shift=(OX, OY), want=False)
        other.call(f'{PX}_build')
        other.scene.units['systemtype'] = mk.Sym('millimeters')
        other.run(mock_read_text(), **controls(None, True, True))
        n0 = len(other.scene.objects)
        ok = other.call(f'{PX}_build')
        check('... in a scene whose System Units are not metres it refuses and changes nothing', ok is False and 'System Units are not metres' in other.scene.messages[-1][0] and len(other.scene.objects) == n0)
        moved = make_run(shift=(OX, OY), want=False)
        moved.call(f'{PX}_build')
        next(n for n in moved.scene.objects if n.props.get(f'{PX}_floor') == '2').tm.rows[3].v[2] += 0.3
        moved.run(mock_read_text(), **controls(None, True, True))
        moved.set(f'{PX}_levels', [9.0] * len(FLOORS))
        ok = moved.call(f'{PX}_build')
        check('... one part of floor 2 moved by hand (+0.30 m): the level is the most common one, so the boxes are right', ok is False and not box_problems(moved, levels, (OX, OY)) and moved.scene.messages[-1][0].startswith('Added '))
        full = make_run()
        full.scene.objects.append(mk.Node(mk.Scene(), mk.Cls('Box'), 'something'))                      # a scene with one object in it
        full.scene.units['systemtype'] = mk.Sym('millimeters')
        n0 = len(full.scene.objects)
        ok = full.call(f'{PX}_build')
        check('Build in a scene that already has an object: refuses with "Open a NEW EMPTY scene first", returns false, adds nothing and leaves the System Units alone',
              ok is False and full.scene.messages and full.scene.messages[-1][0].startswith('Open a NEW EMPTY scene first') and len(full.scene.objects) == n0
              and full.get(f'{PX}_nodes') == [] and full.scene.units['systemtype'] == mk.Sym('millimeters'))
        empty = make_run()
        empty.scene.units['systemtype'] = mk.Sym('millimeters')
        empty.call(f'{PX}_build')
        check('... and in an empty scene Build sets System Units to metres (type metres, scale 1.0, display metric metres)',
              empty.scene.units['systemtype'] == mk.Sym('meters') and empty.scene.units['systemscale'] == 1.0 and empty.scene.units['displaytype'] == mk.Sym('metric') and empty.scene.units['metrictype'] == mk.Sym('meters'))
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
    levels = [LEVEL[f] for f in FLOORS]
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
    info(f'{len(unrot)} of {len(PIECES)} boxes are unrotated (rot 0), {len(q90)} are turned by 90 degrees, {len(other)} by another angle: the node\'s min / max are compared for the {len(unrot)} unrotated ones only')
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

        left = bbox_probe(TEXT)
        check('the real script passes the probe of the rule (the unrotated boxes are compared and only they; no box built right fails for what Max reports as min / max of a turned node)', left == [], '; '.join(left))
        rule = 'local unrotated = abs(sa) < 0.00001 and ca > 0.0'
        slips = [
            ('the old rule: a quarter turn counts as unrotated too, so the boxes turned by 90 degrees are compared', rule, 'local unrotated = abs(ca) < 0.00001 or abs(sa) < 0.00001'),
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


# ---- the datum: where each picture goes --------------------------------------------------------------------------------------

PICTURE_LINE = re.compile(r'^    setUserProp origin "Picture_(\w+)" "(\S+) \((\d+) x (\d+) px at (\d+\.\d+) px per m along x and (\d+\.\d+) along y\) is a plane (\d+\.\d+) m along x by '
                          r'(\d+\.\d+) m along y, its centre \[(-?\d+\.\d+), (-?\d+\.\d+)\] m from this point, under ([^"]*)"$', re.M)


def stair_width():
    """The owner's one real dimension (2 Nov 2026): the main stair's width, the steps of the flight from the lowest floor (each step's longer side)."""
    flight = [p for p in PARTS if p['kind'] == 'step' and p['floor'] == FLOORS[0]]
    return max(max(max(x for x, _ in p['o']) - min(x for x, _ in p['o']), max(y for _, y in p['o']) - min(y for _, y in p['o'])) for p in flight) if flight else None


def test_datum():
    section('the datum: the pictures\' frame, and where each picture goes')
    frames = M.get('pictureFrame') or {}
    got = {m.group(1): m for m in PICTURE_LINE.finditer(TEXT)}
    check(f'one Picture property per floor that has a picture ({", ".join(sorted(got))}), in the datum lines after Levels', sorted(got) == sorted(k for k in FLOORS if k in frames)
          and TEXT.index('setUserProp origin "Levels"') < min((m.start() for m in got.values()), default=-1))
    for key in FLOORS:
        pf, m = frames.get(key), got.get(key)
        if pf is None or m is None: continue
        (w, h), kx, ky, (px0, py0) = pf['size'], pf['pxPerMetreX'], pf['pxPerMetreY'], pf['originPx']
        cx, cy = floats(m.group(9))[0], floats(m.group(10))[0]
        want = (w / kx, h / ky, (w / 2 - px0) / kx, (py0 - h / 2) / ky)          # pixel x = originPx[0] + kx * X, y = originPx[1] - ky * Y: the picture's middle pixel in metres from 0,0
        gotv = (float(m.group(7)), float(m.group(8)), cx, cy)
        name = next(f['name'] for f in M['floors'] if f['key'] == key)
        check(f'{key}: {m.group(2)}, {m.group(3)} x {m.group(4)} px at {m.group(5)} px per m along x and {m.group(6)} along y = the model\'s pictureFrame (a scale per axis); a plane {gotv[0]:.4f} x {gotv[1]:.4f} m centred at ({cx:.4f}, {cy:.4f}) m from the datum = size / scale and the middle pixel '
              f'worked out again (within 0.1 mm), under {name}',
              (int(m.group(3)), int(m.group(4))) == (w, h) and abs(float(m.group(5)) - kx) < 5e-5 and abs(float(m.group(6)) - ky) < 5e-5 and max(abs(a - b) for a, b in zip(gotv, want)) < 1e-4 and m.group(11) == name
              and m.group(2) == os.path.normpath(os.path.join('src', pf['file'])).replace('\\', '/'), f'{gotv} vs {want}')
        # the plane's top-left corner is pixel (0, 0); the origin pixel lies at the datum: corner + originPx / scale per axis (y down) = 0, 0
        corner = (cx - gotv[0] / 2, cy + gotv[1] / 2)
        check(f'{key}: placed so, the picture\'s origin pixel {tuple(pf["originPx"])} lands on the datum (within 0.1 mm): {corner[0] + px0 / kx:+.5f}, {corner[1] - py0 / ky:+.5f}', abs(corner[0] + px0 / kx) < 1e-4 and abs(corner[1] - py0 / ky) < 1e-4)
        f = HERE / m.group(2)
        size = struct.unpack('>II', f.read_bytes()[16:24]) if f.exists() and f.read_bytes()[:8] == b'\x89PNG\r\n\x1a\n' else None
        check(f'{key}: the picture named is there beside the script ({m.group(2)}) and its size in pixels is the one written ({size})', size == (w, h))
    # the scale's words: the owner's stair width (from the model's steps), in the datum's Source and in the header, and no word of the old lift-door scale
    sw = stair_width()
    src = re.search(r'^    setUserProp origin "Source" "([^"]*)"$', TEXT, re.M)
    words_ = f"the main stair's width, {sw:.2f} m between its side walls" if sw else '?'
    per_axis = any(abs(pf['pxPerMetreX'] - pf['pxPerMetreY']) >= 0.005 for pf in frames.values())
    header = TEXT[:TEXT.index('\nglobal ')]
    check(f'the datum\'s Source names both pictures, says there is no CAD and how they were scaled ("{words_} (the owner\'s)"{", per axis" if per_axis else ""}), and gives the frame; the header says the same scale',
          bool(src) and all(s in src.group(1) for s in M['source']) and 'no CAD' in src.group(1) and f"scaled from {words_} (the owner's)" in src.group(1)
          and (('per axis' in src.group(1)) == per_axis) and "north-west corner" in src.group(1) and 'LibreDWG' not in TEXT
          and words_ in header and 'lift doors average' not in TEXT and 'lift door\n-- opening, 1.00 m' not in TEXT, src.group(1)[:200] if src else 'no Source')


def main():
    for section_test in (test_file, test_parts, test_data, test_geometry, test_code, test_generator, test_lint_teeth, test_mock, test_none, test_bounding_box, test_datum):
        try: section_test()
        except Exception as e:                # a damaged script must end in a FAIL line and exit 1, never in a traceback
            check(f'{section_test.__name__} could read what it needed from the script', False, f'{type(e).__name__}: {e}'[:300])
    failed = [n for n, ok in RESULTS if not ok]
    print(f'\n{len(RESULTS)} checks, {len(failed)} failed' + (f', {len(SKIPPED)} skipped' if SKIPPED else ''))
    for n in failed: print('  FAILED:', n)
    return 1 if failed else 0


if __name__ == '__main__':
    sys.exit(main())
